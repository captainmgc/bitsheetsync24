"""
Export API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import structlog
from datetime import datetime

from app.database import get_db
from app.schemas.export import (
    ExportConfigCreate,
    ExportConfigResponse,
    ExportListResponse,
    ExportProgressUpdate
)
from app.schemas.sheets import (
    SheetsExportRequest,
    SheetsExportResponse
)
from app.services.export_manager import ExportManager
from app.services.google_sheets_api import GoogleSheetsService
from app.services.view_utils import (
    build_where_clause_from_view_filters,
    apply_view_sort_config,
    get_view_config
)

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=ExportConfigResponse)
async def create_export(
    config: ExportConfigCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new export job
    
    - Automatically detects related tables
    - Runs export in background
    - Returns export log immediately
    """
    try:
        manager = ExportManager(db)
        
        # Create export log
        export_log = await manager.create_export(config)
        
        # Run export in background
        background_tasks.add_task(manager.run_export, export_log.id)
        
        return ExportConfigResponse.model_validate(export_log)
        
    except Exception as e:
        logger.error("create_export_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{export_id}", response_model=ExportConfigResponse)
async def get_export(
    export_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get export status and details"""
    result = await db.execute(
        text("SELECT * FROM bitrix.export_logs WHERE id = :id"),
        {"id": export_id}
    )
    export_data = result.mappings().first()
    
    if not export_data:
        raise HTTPException(status_code=404, detail="Export not found")
    
    return ExportConfigResponse.model_validate(export_data)


@router.get("/", response_model=ExportListResponse)
async def list_exports(
    page: int = 1,
    page_size: int = 20,
    entity_name: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List all exports with pagination and filters"""
    
    # Build WHERE clause
    where_conditions = []
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if entity_name:
        where_conditions.append("entity_name = :entity_name")
        params["entity_name"] = entity_name
    
    if status:
        where_conditions.append("status = :status")
        params["status"] = status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Get total count
    count_query = text(f"""
        SELECT COUNT(*) as total 
        FROM bitrix.export_logs 
        {where_clause}
    """)
    count_result = await db.execute(count_query, params)
    total = count_result.scalar()
    
    # Get exports
    query = text(f"""
        SELECT * 
        FROM bitrix.export_logs 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = await db.execute(query, params)
    exports = [ExportConfigResponse.model_validate(row) for row in result.mappings()]
    
    return ExportListResponse(
        exports=exports,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/{export_id}")
async def cancel_export(
    export_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running export"""
    await db.execute(
        text("""
            UPDATE bitrix.export_logs 
            SET status = 'cancelled', completed_at = now()
            WHERE id = :id AND status = 'running'
        """),
        {"id": export_id}
    )
    await db.commit()
    
    return {"message": "Export cancelled", "export_id": export_id}


@router.post("/{export_id}/retry")
async def retry_export(
    export_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed export"""
    
    # Check if export exists and is failed
    result = await db.execute(
        text("SELECT status FROM bitrix.export_logs WHERE id = :id"),
        {"id": export_id}
    )
    export_data = result.first()
    
    if not export_data:
        raise HTTPException(status_code=404, detail="Export not found")
    
    if export_data[0] != "failed":
        raise HTTPException(status_code=400, detail="Only failed exports can be retried")
    
    # Reset status
    await db.execute(
        text("""
            UPDATE bitrix.export_logs 
            SET 
                status = 'pending',
                error_message = NULL,
                error_details = NULL,
                processed_records = 0,
                failed_records = 0
            WHERE id = :id
        """),
        {"id": export_id}
    )
    await db.commit()
    
    # Run export in background
    manager = ExportManager(db)
    background_tasks.add_task(manager.run_export, export_id)
    
    return {"message": "Export queued for retry", "export_id": export_id}


@router.post("/sheets", response_model=SheetsExportResponse)
async def export_to_google_sheets(
    request: SheetsExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Export Bitrix24 data to Google Sheets
    
    - Creates new spreadsheet or uses existing one
    - Exports selected tables with relationships
    - Applies optional date range filter
    - Returns Google Sheets URL
    """
    try:
        # Initialize Google Sheets service with user's access token
        sheets_service = GoogleSheetsService(request.access_token)
        
        # Step 1: Create or get spreadsheet
        if request.sheet_mode == "new":
            if not request.sheet_name:
                raise HTTPException(status_code=400, detail="sheet_name required for new sheets")
            
            logger.info("creating_new_spreadsheet", name=request.sheet_name)
            
            spreadsheet = await sheets_service.create_spreadsheet(
                title=request.sheet_name,
                sheets=request.tables  # Create one sheet per table
            )
            
            spreadsheet_id = spreadsheet["spreadsheet_id"]
            spreadsheet_url = spreadsheet["spreadsheet_url"]
            created_sheets = spreadsheet["sheets"]
            
        else:  # existing
            if not request.sheet_id:
                raise HTTPException(status_code=400, detail="sheet_id required for existing sheets")
            
            spreadsheet_id = request.sheet_id
            
            logger.info("using_existing_spreadsheet", sheet_id=spreadsheet_id)
            
            # Get spreadsheet info
            spreadsheet = await sheets_service.get_spreadsheet_info(spreadsheet_id)
            spreadsheet_url = spreadsheet["spreadsheet_url"]
            existing_sheet_names = {s["title"] for s in spreadsheet["sheets"]}
            
            # Create missing sheets
            created_sheets = []
            for table_name in request.tables:
                if table_name not in existing_sheet_names:
                    new_sheet = await sheets_service.add_sheet(spreadsheet_id, table_name)
                    created_sheets.append(new_sheet)
                else:
                    # Find existing sheet
                    existing = next(s for s in spreadsheet["sheets"] if s["title"] == table_name)
                    created_sheets.append(existing)
        
        # Step 2: Export each table
        total_rows = 0
        tables_exported = []
        
        for table_name in request.tables:
            logger.info("exporting_table", table=table_name)
            
            # Build query with optional filters
            where_conditions = []
            params = {}
            
            # Apply view filters if specified
            if request.table_views and table_name in request.table_views:
                view_id = request.table_views[table_name]
                view_config = await get_view_config(db, table_name, view_id)
                
                if view_config.get("filters"):
                    view_where = build_where_clause_from_view_filters(
                        view_config["filters"],
                        params,
                        f"view_{table_name}"
                    )
                    if view_where:
                        where_conditions.append(f"({view_where})")
                        logger.info("applying_view_filters", 
                                   table=table_name, 
                                   view_id=view_id,
                                   filters=view_config["filters"])
            
            # Apply date range filter
            if request.date_range:
                where_conditions.append(
                    "created_at >= :from_date AND created_at <= :to_date"
                )
                params["from_date"] = request.date_range.from_date
                params["to_date"] = request.date_range.to_date
            
            # Build WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Build ORDER BY clause
            order_clause = "ORDER BY id"
            if request.table_views and table_name in request.table_views:
                view_id = request.table_views[table_name]
                view_config = await get_view_config(db, table_name, view_id)
                
                if view_config.get("sort_config"):
                    view_order = apply_view_sort_config(view_config["sort_config"])
                    if view_order:
                        order_clause = f"ORDER BY {view_order}"
            
            # Get data from database
            query = text(f"""
                SELECT * 
                FROM bitrix.{table_name}
                {where_clause}
                {order_clause}
            """)
            
            result = await db.execute(query, params)
            rows = result.mappings().all()
            
            if not rows:
                logger.warning("no_data_for_table", table=table_name)
                continue
            
            # Convert to 2D array with headers
            headers = list(rows[0].keys())
            data = [headers]
            
            for row in rows:
                data.append([
                    str(value) if value is not None else ""
                    for value in row.values()
                ])
            
            # Find sheet ID for this table
            sheet_info = next(
                (s for s in created_sheets if s["title"] == table_name),
                None
            )
            
            if not sheet_info:
                logger.error("sheet_not_found", table=table_name)
                continue
            
            # Upload to Google Sheets
            range_name = f"{table_name}!A1"
            
            if request.sheet_mode == "new":
                # New sheet: update values (overwrite)
                await sheets_service.update_values(
                    spreadsheet_id,
                    range_name,
                    data
                )
            else:
                # Existing sheet: append values
                await sheets_service.append_values(
                    spreadsheet_id,
                    range_name,
                    data
                )
            
            # Format header row
            await sheets_service.format_header_row(
                spreadsheet_id,
                sheet_info["sheet_id"]
            )
            
            rows_exported = len(data) - 1  # Exclude header
            total_rows += rows_exported
            tables_exported.append(table_name)
            
            logger.info("table_exported",
                       table=table_name,
                       rows=rows_exported)
        
        # Close the service
        await sheets_service.close()
        
        # Log export to database
        export_log_query = text("""
            INSERT INTO bitrix.export_logs (
                entity_name,
                export_type,
                destination,
                status,
                total_records,
                processed_records,
                created_at,
                completed_at
            ) VALUES (
                :entity_name,
                'google_sheets',
                :destination,
                'completed',
                :total_records,
                :processed_records,
                :created_at,
                :completed_at
            ) RETURNING id
        """)
        
        export_result = await db.execute(export_log_query, {
            "entity_name": ",".join(tables_exported),
            "destination": spreadsheet_url,
            "total_records": total_rows,
            "processed_records": total_rows,
            "created_at": datetime.now(),
            "completed_at": datetime.now()
        })
        
        await db.commit()
        export_id = export_result.scalar()
        
        logger.info("export_completed",
                   export_id=export_id,
                   total_rows=total_rows,
                   tables=len(tables_exported))
        
        return SheetsExportResponse(
            status="completed",
            sheet_url=spreadsheet_url,
            sheet_id=spreadsheet_id,
            total_rows=total_rows,
            tables_exported=tables_exported,
            export_id=export_id,
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("export_to_sheets_error", error=str(e), tables=request.tables)
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )
