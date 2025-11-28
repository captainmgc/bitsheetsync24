"""
Data API Endpoints
Provides paginated and filtered access to Bitrix24 tables
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, inspect
from typing import Optional, List, Dict, Any
import structlog

from app.database import get_db
from app.services.view_utils import (
    build_where_clause_from_view_filters,
    apply_view_sort_config,
    get_view_config
)

router = APIRouter()
logger = structlog.get_logger()

# Valid table names (whitelist for security)
VALID_TABLES = [
    'contacts',
    'companies',
    'deals',
    'activities',
    'tasks',
    'task_comments',
    'leads',
    'users',
    'statuses'
]


@router.get("/{table_name}")
async def get_table_data(
    table_name: str,
    limit: int = Query(20, ge=1, le=100, description="Number of records per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    sort_by: Optional[str] = Query(None, description="Column to sort by"),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    search: Optional[str] = Query(None, description="Search term (searches all text columns)"),
    view_id: Optional[int] = Query(None, description="View ID to apply filters and sort"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated data from a Bitrix24 table
    
    - **table_name**: Name of the table to query
    - **limit**: Number of records to return (max 100)
    - **offset**: Number of records to skip (for pagination)
    - **sort_by**: Column name to sort by
    - **sort_order**: Sort direction (asc or desc)
    - **search**: Search term to filter results
    - **view_id**: Apply saved view filters and sort
    
    Returns:
        {
            "data": [...],
            "total": 1234,
            "limit": 20,
            "offset": 0,
            "table": "contacts"
        }
    """
    
    # Validate table name
    if table_name not in VALID_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table name. Valid tables: {', '.join(VALID_TABLES)}"
        )
    
    try:
        # Build WHERE clause
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        # Apply view filters if specified
        if view_id:
            view_config = await get_view_config(db, table_name, view_id)
            
            if view_config.get("filters"):
                view_where = build_where_clause_from_view_filters(
                    view_config["filters"],
                    params,
                    f"view_{table_name}"
                )
                if view_where:
                    where_conditions.append(f"({view_where})")
                    logger.info("applying_view_filters", table=table_name, view_id=view_id)
        
        # Add search filter
        if search:
            # Get column names for search
            inspect_query = text(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'bitrix' 
                AND table_name = :table_name
                AND data_type IN ('character varying', 'text', 'varchar')
            """)
            
            result = await db.execute(inspect_query, {"table_name": table_name})
            text_columns = [row[0] for row in result.fetchall()]
            
            if text_columns:
                search_conditions = [
                    f"{col}::text ILIKE :search"
                    for col in text_columns
                ]
                where_conditions.append("(" + " OR ".join(search_conditions) + ")")
                params["search"] = f"%{search}%"
        
        # Build final WHERE clause
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Build ORDER BY clause
        order_clause = ""
        
        # Priority 1: View sort config
        if view_id:
            view_config = await get_view_config(db, table_name, view_id)
            if view_config.get("sort_config"):
                view_order = apply_view_sort_config(view_config["sort_config"])
                if view_order:
                    order_clause = f"ORDER BY {view_order}"
        
        # Priority 2: Manual sort parameters
        if not order_clause and sort_by:
            # Validate column exists
            check_column = text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'bitrix' 
                AND table_name = :table_name
                AND column_name = :column_name
            """)
            
            result = await db.execute(
                check_column,
                {"table_name": table_name, "column_name": sort_by}
            )
            
            if result.first():
                order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
            else:
                logger.warning(
                    "invalid_sort_column",
                    table=table_name,
                    column=sort_by
                )
        
        # Priority 3: Default to id
        if not order_clause:
            order_clause = "ORDER BY id ASC"
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM bitrix.{table_name}
            {where_clause}
        """)
        
        count_result = await db.execute(count_query, params)
        total = count_result.scalar()
        
        # Get column names excluding internal columns
        columns_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'bitrix' 
            AND table_name = :table_name
            AND column_name NOT IN ('original_data', 'data', 'source_hash', 'fetched_at')
            ORDER BY ordinal_position
        """)
        
        columns_result = await db.execute(columns_query, {"table_name": table_name})
        columns = [row[0] for row in columns_result.fetchall()]
        column_list = ", ".join(columns) if columns else "*"
        
        # Get data with specific columns (excluding original_data)
        data_query = text(f"""
            SELECT {column_list}
            FROM bitrix.{table_name}
            {where_clause}
            {order_clause}
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(data_query, params)
        data = [dict(row._mapping) for row in result.fetchall()]
        
        # Convert datetime objects to strings
        for row in data:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
        
        logger.info(
            "table_data_fetched",
            table=table_name,
            total=total,
            returned=len(data),
            offset=offset,
            limit=limit,
            view_id=view_id
        )
        
        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "table": table_name
        }
        
    except Exception as e:
        logger.error(
            "get_table_data_error",
            table=table_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch table data: {str(e)}"
        )


@router.get("/{table_name}/columns")
async def get_table_columns(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get column information for a table
    
    Returns column names, data types, and whether they're nullable
    """
    
    if table_name not in VALID_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table name. Valid tables: {', '.join(VALID_TABLES)}"
        )
    
    try:
        query = text("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'bitrix' 
            AND table_name = :table_name
            ORDER BY ordinal_position
        """)
        
        result = await db.execute(query, {"table_name": table_name})
        columns = [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3]
            }
            for row in result.fetchall()
        ]
        
        return {
            "table": table_name,
            "columns": columns
        }
        
    except Exception as e:
        logger.error(
            "get_table_columns_error",
            table=table_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch table columns: {str(e)}"
        )


@router.get("/{table_name}/stats")
async def get_table_stats(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics about a table
    
    Returns record count, disk size, and last update time
    """
    
    if table_name not in VALID_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table name. Valid tables: {', '.join(VALID_TABLES)}"
        )
    
    try:
        # Get record count
        count_query = text(f"SELECT COUNT(*) FROM bitrix.{table_name}")
        count_result = await db.execute(count_query)
        total_records = count_result.scalar()
        
        # Get table size
        size_query = text("""
            SELECT pg_size_pretty(pg_total_relation_size(:table_ref)) as size
        """)
        size_result = await db.execute(
            size_query,
            {"table_ref": f"bitrix.{table_name}"}
        )
        table_size = size_result.scalar()
        
        # Get last update time (from sync_history)
        last_sync_query = text("""
            SELECT completed_at
            FROM bitrix.sync_history
            WHERE entity_name = :entity_name
            AND status = 'completed'
            ORDER BY completed_at DESC
            LIMIT 1
        """)
        
        sync_result = await db.execute(
            last_sync_query,
            {"entity_name": table_name}
        )
        last_sync = sync_result.scalar()
        
        return {
            "table": table_name,
            "total_records": total_records,
            "table_size": table_size,
            "last_sync": last_sync.isoformat() if last_sync else None
        }
        
    except Exception as e:
        logger.error(
            "get_table_stats_error",
            table=table_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch table stats: {str(e)}"
        )
