"""
Advanced Views API Endpoints
Multi-table JOIN views with dynamic query building
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog
import json

from app.database import get_db

router = APIRouter()
logger = structlog.get_logger()


# =====================================================
# TABLE RELATIONS ENDPOINTS
# =====================================================

@router.get("/relations")
async def get_all_relations(db: AsyncSession = Depends(get_db)):
    """Get all defined table relations"""
    try:
        query = text("""
            SELECT 
                id, source_table, source_column,
                target_table, target_column,
                relation_type, display_name, is_active
            FROM bitrix.table_relations
            WHERE is_active = true
            ORDER BY source_table, target_table
        """)
        
        result = await db.execute(query)
        relations = []
        
        for row in result.fetchall():
            relations.append({
                "id": row[0],
                "source_table": row[1],
                "source_column": row[2],
                "target_table": row[3],
                "target_column": row[4],
                "relation_type": row[5],
                "display_name": row[6],
                "is_active": row[7]
            })
        
        return {"relations": relations, "total": len(relations)}
        
    except Exception as e:
        logger.error("get_relations_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relations/{table_name}")
async def get_table_relations(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all relations for a specific table (both as source and target)"""
    try:
        query = text("""
            SELECT 
                id, source_table, source_column,
                target_table, target_column,
                relation_type, display_name,
                CASE 
                    WHEN source_table = :table_name THEN 'outgoing'
                    ELSE 'incoming'
                END as direction
            FROM bitrix.table_relations
            WHERE (source_table = :table_name OR target_table = :table_name)
                AND is_active = true
            ORDER BY source_table, target_table
        """)
        
        result = await db.execute(query, {"table_name": table_name})
        relations = []
        
        for row in result.fetchall():
            relations.append({
                "id": row[0],
                "source_table": row[1],
                "source_column": row[2],
                "target_table": row[3],
                "target_column": row[4],
                "relation_type": row[5],
                "display_name": row[6],
                "direction": row[7]
            })
        
        return {
            "table_name": table_name,
            "relations": relations,
            "total": len(relations)
        }
        
    except Exception as e:
        logger.error("get_table_relations_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ADVANCED VIEWS ENDPOINTS
# =====================================================

@router.get("/")
async def get_advanced_views(
    primary_table: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all advanced views, optionally filtered by primary table"""
    try:
        if primary_table:
            query = text("""
                SELECT id, view_name, description, primary_table, 
                       joins, selected_columns, filters, sort_config,
                       is_default, is_system, created_at
                FROM bitrix.advanced_views
                WHERE primary_table = :primary_table
                ORDER BY is_system DESC, is_default DESC, view_name
            """)
            result = await db.execute(query, {"primary_table": primary_table})
        else:
            query = text("""
                SELECT id, view_name, description, primary_table, 
                       joins, selected_columns, filters, sort_config,
                       is_default, is_system, created_at
                FROM bitrix.advanced_views
                ORDER BY primary_table, is_system DESC, is_default DESC, view_name
            """)
            result = await db.execute(query)
        
        views = []
        for row in result.fetchall():
            views.append({
                "id": row[0],
                "view_name": row[1],
                "description": row[2],
                "primary_table": row[3],
                "joins": row[4] or [],
                "selected_columns": row[5] or [],
                "filters": row[6] or {},
                "sort_config": row[7] or {},
                "is_default": row[8],
                "is_system": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
                "join_count": len(row[4]) if row[4] else 0,
                "column_count": len(row[5]) if row[5] else 0
            })
        
        return {"views": views, "total": len(views)}
        
    except Exception as e:
        logger.error("get_advanced_views_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{view_id}")
async def get_advanced_view(
    view_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific advanced view with full details"""
    try:
        query = text("""
            SELECT id, view_name, description, primary_table, 
                   joins, selected_columns, filters, sort_config,
                   group_by, aggregations, is_default, is_system,
                   created_by, created_at, updated_at
            FROM bitrix.advanced_views
            WHERE id = :view_id
        """)
        
        result = await db.execute(query, {"view_id": view_id})
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="View not found")
        
        return {
            "id": row[0],
            "view_name": row[1],
            "description": row[2],
            "primary_table": row[3],
            "joins": row[4] or [],
            "selected_columns": row[5] or [],
            "filters": row[6] or {},
            "sort_config": row[7] or {},
            "group_by": row[8] or [],
            "aggregations": row[9] or [],
            "is_default": row[10],
            "is_system": row[11],
            "created_by": row[12],
            "created_at": row[13].isoformat() if row[13] else None,
            "updated_at": row[14].isoformat() if row[14] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_advanced_view_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_advanced_view(
    view_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new advanced view"""
    try:
        # Validate required fields
        if not view_data.get("view_name"):
            raise HTTPException(status_code=400, detail="view_name is required")
        if not view_data.get("primary_table"):
            raise HTTPException(status_code=400, detail="primary_table is required")
        
        insert_query = text("""
            INSERT INTO bitrix.advanced_views (
                view_name, description, primary_table,
                joins, selected_columns, filters, sort_config,
                group_by, aggregations, is_default, created_by, created_at, updated_at
            ) VALUES (
                :view_name, :description, :primary_table,
                :joins, :selected_columns, :filters, :sort_config,
                :group_by, :aggregations, :is_default, :created_by, :created_at, :updated_at
            ) RETURNING id
        """)
        
        result = await db.execute(insert_query, {
            "view_name": view_data.get("view_name"),
            "description": view_data.get("description"),
            "primary_table": view_data.get("primary_table"),
            "joins": json.dumps(view_data.get("joins", [])),
            "selected_columns": json.dumps(view_data.get("selected_columns", [])),
            "filters": json.dumps(view_data.get("filters", {})),
            "sort_config": json.dumps(view_data.get("sort_config", {})),
            "group_by": json.dumps(view_data.get("group_by", [])),
            "aggregations": json.dumps(view_data.get("aggregations", [])),
            "is_default": view_data.get("is_default", False),
            "created_by": view_data.get("created_by"),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        await db.commit()
        view_id = result.scalar()
        
        logger.info("advanced_view_created", view_id=view_id, name=view_data.get("view_name"))
        
        return {
            "id": view_id,
            "message": "Advanced view created successfully",
            "view_name": view_data.get("view_name")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("create_advanced_view_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{view_id}")
async def update_advanced_view(
    view_id: int,
    view_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update an advanced view"""
    try:
        # Check if view exists and is not system
        check_query = text("""
            SELECT is_system FROM bitrix.advanced_views WHERE id = :view_id
        """)
        result = await db.execute(check_query, {"view_id": view_id})
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="View not found")
        if row[0]:
            raise HTTPException(status_code=400, detail="System views cannot be modified")
        
        update_query = text("""
            UPDATE bitrix.advanced_views SET
                view_name = COALESCE(:view_name, view_name),
                description = COALESCE(:description, description),
                joins = COALESCE(:joins, joins),
                selected_columns = COALESCE(:selected_columns, selected_columns),
                filters = COALESCE(:filters, filters),
                sort_config = COALESCE(:sort_config, sort_config),
                group_by = COALESCE(:group_by, group_by),
                aggregations = COALESCE(:aggregations, aggregations),
                is_default = COALESCE(:is_default, is_default),
                updated_at = :updated_at
            WHERE id = :view_id
        """)
        
        await db.execute(update_query, {
            "view_id": view_id,
            "view_name": view_data.get("view_name"),
            "description": view_data.get("description"),
            "joins": json.dumps(view_data.get("joins")) if view_data.get("joins") else None,
            "selected_columns": json.dumps(view_data.get("selected_columns")) if view_data.get("selected_columns") else None,
            "filters": json.dumps(view_data.get("filters")) if view_data.get("filters") else None,
            "sort_config": json.dumps(view_data.get("sort_config")) if view_data.get("sort_config") else None,
            "group_by": json.dumps(view_data.get("group_by")) if view_data.get("group_by") else None,
            "aggregations": json.dumps(view_data.get("aggregations")) if view_data.get("aggregations") else None,
            "is_default": view_data.get("is_default"),
            "updated_at": datetime.now()
        })
        
        await db.commit()
        
        logger.info("advanced_view_updated", view_id=view_id)
        
        return {"message": "View updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("update_advanced_view_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{view_id}")
async def delete_advanced_view(
    view_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an advanced view"""
    try:
        # Check if view exists and is not system
        check_query = text("""
            SELECT is_system FROM bitrix.advanced_views WHERE id = :view_id
        """)
        result = await db.execute(check_query, {"view_id": view_id})
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="View not found")
        if row[0]:
            raise HTTPException(status_code=400, detail="System views cannot be deleted")
        
        delete_query = text("DELETE FROM bitrix.advanced_views WHERE id = :view_id")
        await db.execute(delete_query, {"view_id": view_id})
        await db.commit()
        
        logger.info("advanced_view_deleted", view_id=view_id)
        
        return {"message": "View deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("delete_advanced_view_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# QUERY EXECUTION ENDPOINT
# =====================================================

@router.get("/{view_id}/data")
async def execute_advanced_view(
    view_id: int,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Execute an advanced view and return data"""
    try:
        # Get view configuration
        view_query = text("""
            SELECT primary_table, joins, selected_columns, filters, sort_config
            FROM bitrix.advanced_views
            WHERE id = :view_id
        """)
        
        result = await db.execute(view_query, {"view_id": view_id})
        view = result.first()
        
        if not view:
            raise HTTPException(status_code=404, detail="View not found")
        
        primary_table = view[0]
        joins = view[1] or []
        selected_columns = view[2] or []
        filters = view[3] or {}
        sort_config = view[4] or {}
        
        # Build dynamic SQL query
        sql = build_advanced_view_query(
            primary_table=primary_table,
            joins=joins,
            selected_columns=selected_columns,
            filters=filters,
            sort_config=sort_config,
            limit=limit,
            offset=offset
        )
        
        logger.info("executing_advanced_view", view_id=view_id, sql=sql[:200])
        
        # Execute query
        data_result = await db.execute(text(sql))
        rows = data_result.fetchall()
        
        # Get column names from selected_columns
        column_names = []
        for col in selected_columns:
            alias = col.get("alias") or col.get("column")
            column_names.append(alias)
        
        # Convert to list of dicts
        data = []
        for row in rows:
            row_dict = {}
            for i, col_name in enumerate(column_names):
                if i < len(row):
                    value = row[i]
                    # Handle datetime serialization
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col_name] = value
            data.append(row_dict)
        
        # Get total count
        count_sql = build_advanced_view_count_query(primary_table, joins, filters)
        count_result = await db.execute(text(count_sql))
        total = count_result.scalar() or 0
        
        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "columns": column_names
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("execute_advanced_view_error", view_id=view_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# QUERY BUILDER FUNCTIONS
# =====================================================

def build_advanced_view_query(
    primary_table: str,
    joins: List[Dict],
    selected_columns: List[Dict],
    filters: Dict,
    sort_config: Dict,
    limit: int = 100,
    offset: int = 0
) -> str:
    """Build SQL query from view configuration"""
    
    # Build SELECT clause
    select_parts = []
    for col in selected_columns:
        table = col.get("table_alias") or col.get("table", primary_table)
        column = col.get("column")
        alias = col.get("alias", column)
        
        # Handle table alias for joins
        if col.get("table_alias"):
            select_parts.append(f'"{col["table_alias"]}".{column} AS "{alias}"')
        elif table == primary_table:
            select_parts.append(f'"{primary_table}".{column} AS "{alias}"')
        else:
            # Find the join alias for this table
            join_alias = None
            for j in joins:
                if j.get("table") == table:
                    join_alias = j.get("alias", table)
                    break
            if join_alias:
                select_parts.append(f'"{join_alias}".{column} AS "{alias}"')
            else:
                select_parts.append(f'"{table}".{column} AS "{alias}"')
    
    if not select_parts:
        select_parts = [f'"{primary_table}".*']
    
    select_clause = ", ".join(select_parts)
    
    # Build FROM clause
    from_clause = f'bitrix.{primary_table} AS "{primary_table}"'
    
    # Build JOIN clauses
    join_clauses = []
    for join in joins:
        join_type = join.get("join_type", "LEFT").upper()
        target_table = join.get("table")
        alias = join.get("alias", target_table)
        on_source = join.get("on_source")
        on_target = join.get("on_target")
        
        # Determine join direction
        if join.get("reverse"):
            # Reverse join (target.column = primary.column)
            join_condition = f'"{alias}".{on_target} = "{primary_table}".{on_source}'
        else:
            # Normal join (primary.column = target.column)
            join_condition = f'"{primary_table}".{on_source} = "{alias}".{on_target}'
        
        join_clauses.append(
            f'{join_type} JOIN bitrix.{target_table} AS "{alias}" ON {join_condition}'
        )
    
    join_clause = " ".join(join_clauses)
    
    # Build WHERE clause
    where_parts = []
    for field, config in filters.items():
        if isinstance(config, dict):
            operator = config.get("operator", "=")
            value = config.get("value")
            if value is not None:
                # Escape single quotes
                if isinstance(value, str):
                    value = value.replace("'", "''")
                    where_parts.append(f"{field} {operator} '{value}'")
                else:
                    where_parts.append(f"{field} {operator} {value}")
        else:
            if isinstance(config, str):
                config = config.replace("'", "''")
                where_parts.append(f"{field} = '{config}'")
            else:
                where_parts.append(f"{field} = {config}")
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    # Build ORDER BY clause
    order_clause = ""
    if sort_config:
        column = sort_config.get("column")
        order = sort_config.get("order", "ASC").upper()
        if column:
            order_clause = f'ORDER BY {column} {order}'
    
    # Build final query
    sql = f"""
        SELECT {select_clause}
        FROM {from_clause}
        {join_clause}
        WHERE {where_clause}
        {order_clause}
        LIMIT {limit} OFFSET {offset}
    """
    
    return sql.strip()


def build_advanced_view_count_query(
    primary_table: str,
    joins: List[Dict],
    filters: Dict
) -> str:
    """Build count query for pagination"""
    
    from_clause = f'bitrix.{primary_table} AS "{primary_table}"'
    
    # Build JOIN clauses (same as above but simplified)
    join_clauses = []
    for join in joins:
        join_type = join.get("join_type", "LEFT").upper()
        target_table = join.get("table")
        alias = join.get("alias", target_table)
        on_source = join.get("on_source")
        on_target = join.get("on_target")
        
        if join.get("reverse"):
            join_condition = f'"{alias}".{on_target} = "{primary_table}".{on_source}'
        else:
            join_condition = f'"{primary_table}".{on_source} = "{alias}".{on_target}'
        
        join_clauses.append(
            f'{join_type} JOIN bitrix.{target_table} AS "{alias}" ON {join_condition}'
        )
    
    join_clause = " ".join(join_clauses)
    
    # Build WHERE clause
    where_parts = []
    for field, config in filters.items():
        if isinstance(config, dict):
            operator = config.get("operator", "=")
            value = config.get("value")
            if value is not None:
                if isinstance(value, str):
                    value = value.replace("'", "''")
                    where_parts.append(f"{field} {operator} '{value}'")
                else:
                    where_parts.append(f"{field} {operator} {value}")
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    sql = f"""
        SELECT COUNT(DISTINCT "{primary_table}".bitrix_id)
        FROM {from_clause}
        {join_clause}
        WHERE {where_clause}
    """
    
    return sql.strip()


# =====================================================
# TABLE METADATA ENDPOINTS
# =====================================================

@router.get("/tables/columns/{table_name}")
async def get_table_columns(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all columns for a table"""
    try:
        # First check metadata table
        meta_query = text("""
            SELECT column_name, display_name, data_type, is_visible, sort_order
            FROM bitrix.table_metadata
            WHERE table_name = :table_name AND is_visible = true
            ORDER BY sort_order, column_name
        """)
        
        result = await db.execute(meta_query, {"table_name": table_name})
        rows = result.fetchall()
        
        if rows:
            columns = [
                {
                    "column_name": row[0],
                    "display_name": row[1] or row[0],
                    "data_type": row[2],
                    "is_visible": row[3],
                    "sort_order": row[4]
                }
                for row in rows
            ]
        else:
            # Fallback to information_schema
            schema_query = text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'bitrix' AND table_name = :table_name
                ORDER BY ordinal_position
            """)
            
            result = await db.execute(schema_query, {"table_name": table_name})
            columns = [
                {
                    "column_name": row[0],
                    "display_name": row[0],
                    "data_type": row[1],
                    "is_visible": True,
                    "sort_order": 0
                }
                for row in result.fetchall()
            ]
        
        return {"table_name": table_name, "columns": columns}
        
    except Exception as e:
        logger.error("get_table_columns_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/list")
async def get_available_tables(db: AsyncSession = Depends(get_db)):
    """Get list of available Bitrix tables"""
    try:
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'bitrix'
                AND table_type = 'BASE TABLE'
                AND table_name NOT IN ('data_views', 'advanced_views', 'table_relations', 'table_metadata')
            ORDER BY table_name
        """)
        
        result = await db.execute(query)
        
        # Table display names mapping
        display_names = {
            "contacts": "Müşteriler",
            "companies": "Şirketler",
            "deals": "Anlaşmalar",
            "activities": "Aktiviteler",
            "tasks": "Görevler",
            "task_comments": "Görev Yorumları",
            "leads": "Potansiyel Müşteriler",
            "users": "Kullanıcılar",
            "deal_categories": "Anlaşma Kategorileri",
            "departments": "Departmanlar"
        }
        
        tables = []
        for row in result.fetchall():
            table_name = row[0]
            tables.append({
                "name": table_name,
                "display_name": display_names.get(table_name, table_name.replace("_", " ").title())
            })
        
        return {"tables": tables}
        
    except Exception as e:
        logger.error("get_available_tables_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
