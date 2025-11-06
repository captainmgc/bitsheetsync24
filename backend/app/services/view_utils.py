"""
View Filter Utilities
Convert view filters to SQL WHERE clauses
"""
from typing import Dict, Any, Tuple, List


def build_where_clause_from_view_filters(
    view_filters: Dict[str, Any],
    params_dict: Dict[str, Any],
    param_prefix: str = "filter"
) -> str:
    """
    Convert view filters to SQL WHERE clause
    
    Args:
        view_filters: Dictionary of field -> {operator, value}
        params_dict: Dictionary to populate with SQL parameters
        param_prefix: Prefix for parameter names
        
    Returns:
        SQL WHERE clause string (without WHERE keyword)
        
    Example:
        filters = {
            "status": {"operator": "=", "value": "active"},
            "type": {"operator": "LIKE", "value": "%vip%"}
        }
        
        Returns: "status = :filter_status AND type LIKE :filter_type"
        params_dict gets: {"filter_status": "active", "filter_type": "%vip%"}
    """
    if not view_filters or not isinstance(view_filters, dict):
        return ""
    
    conditions = []
    
    for field, config in view_filters.items():
        if not isinstance(config, dict):
            # Old format: field -> value (assume equals)
            param_name = f"{param_prefix}_{field}"
            conditions.append(f"{field} = :{param_name}")
            params_dict[param_name] = config
        else:
            operator = config.get("operator", "=")
            value = config.get("value")
            
            if value is None:
                continue
            
            param_name = f"{param_prefix}_{field}"
            
            # Handle different operators
            if operator.upper() == "LIKE" or operator.upper() == "NOT LIKE":
                conditions.append(f"{field} {operator.upper()} :{param_name}")
                # Ensure value has wildcards for LIKE
                if "%" not in str(value):
                    params_dict[param_name] = f"%{value}%"
                else:
                    params_dict[param_name] = value
            elif operator.upper() in ("IN", "NOT IN"):
                # Handle IN operator with list
                if isinstance(value, list):
                    placeholders = []
                    for idx, val in enumerate(value):
                        placeholder = f"{param_name}_{idx}"
                        placeholders.append(f":{placeholder}")
                        params_dict[placeholder] = val
                    conditions.append(f"{field} {operator.upper()} ({','.join(placeholders)})")
                else:
                    conditions.append(f"{field} {operator.upper()} (:{param_name})")
                    params_dict[param_name] = value
            elif operator.upper() == "IS NULL":
                conditions.append(f"{field} IS NULL")
            elif operator.upper() == "IS NOT NULL":
                conditions.append(f"{field} IS NOT NULL")
            elif operator.upper() == "BETWEEN":
                # Expect value to be a list/tuple with 2 elements
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    param_name_start = f"{param_name}_start"
                    param_name_end = f"{param_name}_end"
                    conditions.append(f"{field} BETWEEN :{param_name_start} AND :{param_name_end}")
                    params_dict[param_name_start] = value[0]
                    params_dict[param_name_end] = value[1]
            else:
                # Standard operators: =, !=, >, <, >=, <=
                conditions.append(f"{field} {operator} :{param_name}")
                params_dict[param_name] = value
    
    return " AND ".join(conditions) if conditions else ""


def apply_view_sort_config(sort_config: Dict[str, Any]) -> str:
    """
    Convert view sort config to SQL ORDER BY clause
    
    Args:
        sort_config: {"column": "name", "order": "asc"}
        
    Returns:
        SQL ORDER BY clause (without ORDER BY keyword)
    """
    if not sort_config or not isinstance(sort_config, dict):
        return ""
    
    column = sort_config.get("column")
    order = sort_config.get("order", "asc").upper()
    
    if not column:
        return ""
    
    # Validate order
    if order not in ("ASC", "DESC"):
        order = "ASC"
    
    return f"{column} {order}"


async def get_view_config(db, table_name: str, view_id: int) -> Dict[str, Any]:
    """
    Fetch view configuration from database
    
    Args:
        db: AsyncSession
        table_name: Table name
        view_id: View ID
        
    Returns:
        View configuration dict
    """
    from sqlalchemy import text
    
    query = text("""
        SELECT filters, sort_config, columns_visible
        FROM bitrix.data_views
        WHERE id = :view_id AND table_name = :table_name
    """)
    
    result = await db.execute(query, {
        "view_id": view_id,
        "table_name": table_name
    })
    
    row = result.first()
    
    if not row:
        return {}
    
    return {
        "filters": row[0] or {},
        "sort_config": row[1] or {},
        "columns_visible": row[2] or []
    }
