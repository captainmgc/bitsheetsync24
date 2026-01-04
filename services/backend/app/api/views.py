"""
Views API Endpoints
Manage custom data views (filtered, sorted subsets of tables)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from app.database import get_db

router = APIRouter()
logger = structlog.get_logger()


@router.get("/{table_name}")
async def get_views_for_table(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all saved views for a table
    
    Returns list of views with their filter and sort configurations
    """
    try:
        query = text("""
            SELECT 
                id,
                view_name,
                table_name,
                filters,
                sort_config,
                columns_visible,
                is_default,
                created_at,
                updated_at
            FROM bitrix.data_views
            WHERE table_name = :table_name
            ORDER BY is_default DESC, view_name ASC
        """)
        
        result = await db.execute(query, {"table_name": table_name})
        views = []
        
        for row in result.fetchall():
            views.append({
                "id": row[0],
                "view_name": row[1],
                "table_name": row[2],
                "filters": row[3],
                "sort_config": row[4],
                "columns_visible": row[5],
                "is_default": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None,
            })
        
        return {
            "table_name": table_name,
            "views": views,
            "total": len(views)
        }
        
    except Exception as e:
        logger.error("get_views_error", table=table_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get views: {str(e)}"
        )


@router.post("/{table_name}")
async def create_view(
    table_name: str,
    view_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new view for a table
    
    Body:
    {
        "view_name": "Aktif Müşteriler",
        "filters": {"status": "active"},
        "sort_config": {"column": "name", "order": "asc"},
        "columns_visible": ["id", "name", "email"],
        "is_default": false
    }
    """
    try:
        # Check if view name already exists
        check_query = text("""
            SELECT COUNT(*) FROM bitrix.data_views
            WHERE table_name = :table_name AND view_name = :view_name
        """)
        
        count = await db.execute(
            check_query,
            {
                "table_name": table_name,
                "view_name": view_data.get("view_name")
            }
        )
        
        if count.scalar() > 0:
            raise HTTPException(
                status_code=400,
                detail="View with this name already exists"
            )
        
        # If this is set as default, unset other defaults
        if view_data.get("is_default", False):
            await db.execute(
                text("""
                    UPDATE bitrix.data_views
                    SET is_default = false
                    WHERE table_name = :table_name
                """),
                {"table_name": table_name}
            )
        
        # Insert new view
        insert_query = text("""
            INSERT INTO bitrix.data_views (
                view_name,
                table_name,
                filters,
                sort_config,
                columns_visible,
                is_default,
                created_at,
                updated_at
            ) VALUES (
                :view_name,
                :table_name,
                :filters,
                :sort_config,
                :columns_visible,
                :is_default,
                :created_at,
                :updated_at
            ) RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "view_name": view_data.get("view_name"),
            "table_name": table_name,
            "filters": view_data.get("filters", {}),
            "sort_config": view_data.get("sort_config", {}),
            "columns_visible": view_data.get("columns_visible", []),
            "is_default": view_data.get("is_default", False),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        await db.commit()
        view_id = result.scalar()
        
        logger.info(
            "view_created",
            view_id=view_id,
            table=table_name,
            view_name=view_data.get("view_name")
        )
        
        return {
            "id": view_id,
            "message": "View created successfully",
            "view_name": view_data.get("view_name")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("create_view_error", table=table_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create view: {str(e)}"
        )


@router.put("/{table_name}/{view_id}")
async def update_view(
    table_name: str,
    view_id: int,
    view_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update an existing view"""
    try:
        # If setting as default, unset others
        if view_data.get("is_default", False):
            await db.execute(
                text("""
                    UPDATE bitrix.data_views
                    SET is_default = false
                    WHERE table_name = :table_name AND id != :view_id
                """),
                {"table_name": table_name, "view_id": view_id}
            )
        
        # Update view
        update_query = text("""
            UPDATE bitrix.data_views
            SET 
                view_name = COALESCE(:view_name, view_name),
                filters = COALESCE(:filters, filters),
                sort_config = COALESCE(:sort_config, sort_config),
                columns_visible = COALESCE(:columns_visible, columns_visible),
                is_default = COALESCE(:is_default, is_default),
                updated_at = :updated_at
            WHERE id = :view_id AND table_name = :table_name
        """)
        
        await db.execute(update_query, {
            "view_id": view_id,
            "table_name": table_name,
            "view_name": view_data.get("view_name"),
            "filters": view_data.get("filters"),
            "sort_config": view_data.get("sort_config"),
            "columns_visible": view_data.get("columns_visible"),
            "is_default": view_data.get("is_default"),
            "updated_at": datetime.now()
        })
        
        await db.commit()
        
        logger.info("view_updated", view_id=view_id, table=table_name)
        
        return {"message": "View updated successfully"}
        
    except Exception as e:
        await db.rollback()
        logger.error("update_view_error", view_id=view_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update view: {str(e)}"
        )


@router.delete("/{table_name}/{view_id}")
async def delete_view(
    table_name: str,
    view_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a view"""
    try:
        delete_query = text("""
            DELETE FROM bitrix.data_views
            WHERE id = :view_id AND table_name = :table_name
        """)
        
        await db.execute(delete_query, {
            "view_id": view_id,
            "table_name": table_name
        })
        
        await db.commit()
        
        logger.info("view_deleted", view_id=view_id, table=table_name)
        
        return {"message": "View deleted successfully"}
        
    except Exception as e:
        await db.rollback()
        logger.error("delete_view_error", view_id=view_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete view: {str(e)}"
        )


@router.get("/")
async def get_all_views(db: AsyncSession = Depends(get_db)):
    """Get all views across all tables"""
    try:
        query = text("""
            SELECT 
                id,
                view_name,
                table_name,
                is_default,
                created_at
            FROM bitrix.data_views
            ORDER BY table_name, view_name
        """)
        
        result = await db.execute(query)
        views = []
        
        for row in result.fetchall():
            views.append({
                "id": row[0],
                "view_name": row[1],
                "table_name": row[2],
                "is_default": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            })
        
        return {"views": views, "total": len(views)}
        
    except Exception as e:
        logger.error("get_all_views_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get views: {str(e)}"
        )
