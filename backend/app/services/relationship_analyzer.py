"""
Relationship Analyzer Service
Automatically detects foreign key relationships between tables
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Set
import structlog

logger = structlog.get_logger()


class RelationshipAnalyzer:
    """
    Analyzes JSONB data to detect foreign key relationships
    Based on BITRIX_RELATIONS.md documentation
    """
    
    # Known relationship patterns from Bitrix24
    RELATIONSHIP_MAP = {
        "leads": {
            "ASSIGNED_BY_ID": "users.ID",
            "CREATED_BY_ID": "users.ID",
            "MODIFY_BY_ID": "users.ID",
        },
        "contacts": {
            "ASSIGNED_BY_ID": "users.ID",
            "CREATED_BY_ID": "users.ID",
            "MODIFY_BY_ID": "users.ID",
            "COMPANY_ID": "companies.ID",
        },
        "companies": {
            "ASSIGNED_BY_ID": "users.ID",
            "CREATED_BY_ID": "users.ID",
            "MODIFY_BY_ID": "users.ID",
        },
        "deals": {
            "ASSIGNED_BY_ID": "users.ID",
            "CREATED_BY_ID": "users.ID",
            "MODIFY_BY_ID": "users.ID",
            "CONTACT_ID": "contacts.ID",
            "COMPANY_ID": "companies.ID",
        },
        "activities": {
            "RESPONSIBLE_ID": "users.ID",
            "CREATED_BY": "users.ID",
            # OWNER_TYPE_ID determines which table OWNER_ID references
            # 1=Lead, 2=Deal, 3=Contact, 4=Company
        },
        "tasks": {
            "responsibleId": "users.ID",  # camelCase from API
            "createdBy": "users.ID",
            "groupId": "departments.ID",
        },
        "task_comments": {
            "TASK_ID": "tasks.id",
            "AUTHOR_ID": "users.ID",
        }
    }
    
    # Activity OWNER_TYPE_ID mappings
    ACTIVITY_OWNER_TYPES = {
        1: "leads",
        2: "deals",
        3: "contacts",
        4: "companies",
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_related_tables(self, entity_name: str) -> List[str]:
        """
        Get all tables that should be included when exporting this entity
        
        Args:
            entity_name: Source table name (e.g., "deals")
            
        Returns:
            List of related table names
        """
        related = set()
        
        # Get direct relationships from map
        if entity_name in self.RELATIONSHIP_MAP:
            for fk_column, reference in self.RELATIONSHIP_MAP[entity_name].items():
                target_table = reference.split(".")[0]
                related.add(target_table)
        
        # Special handling for activities
        if entity_name == "activities":
            # Activities can reference multiple entity types via OWNER_TYPE_ID
            related.update(self.ACTIVITY_OWNER_TYPES.values())
            related.add("users")
        
        # Remove self-reference
        related.discard(entity_name)
        
        logger.info("detected_relationships", 
                   entity=entity_name, 
                   related_tables=list(related))
        
        return list(related)
    
    async def get_relationship_details(self, entity_name: str) -> Dict[str, Dict]:
        """
        Get detailed relationship information for an entity
        
        Returns:
            {
                "COMPANY_ID": {
                    "target_table": "companies",
                    "target_column": "ID",
                    "relationship_type": "many_to_one"
                }
            }
        """
        relationships = {}
        
        if entity_name in self.RELATIONSHIP_MAP:
            for fk_column, reference in self.RELATIONSHIP_MAP[entity_name].items():
                target_table, target_column = reference.split(".")
                relationships[fk_column] = {
                    "target_table": target_table,
                    "target_column": target_column,
                    "relationship_type": "many_to_one"
                }
        
        return relationships
    
    async def get_required_ids(
        self, 
        entity_name: str, 
        entity_ids: List[int]
    ) -> Dict[str, Set[int]]:
        """
        Get IDs of related records that need to be included
        
        Args:
            entity_name: Source table
            entity_ids: List of primary record IDs
            
        Returns:
            {
                "users": {1, 2, 3},
                "companies": {5, 10}
            }
        """
        related_ids: Dict[str, Set[int]] = {}
        
        if not entity_ids:
            return related_ids
        
        # Get relationship details
        relationships = await self.get_relationship_details(entity_name)
        
        # Map of column names (relationship key -> actual database column)
        column_mapping = {
            "ASSIGNED_BY_ID": "assigned_by_id",
            "CREATED_BY_ID": "created_by_id",
            "MODIFY_BY_ID": "modify_by_id",
            "COMPANY_ID": "company_id",
            "CONTACT_ID": "contact_id",
            "RESPONSIBLE_ID": "responsible_id",
            "CREATED_BY": "created_by",
            "responsibleId": "responsible_id",
            "createdBy": "created_by",
            "groupId": "group_id",
            "TASK_ID": "task_id",
            "AUTHOR_ID": "author_id",
        }
        
        # Query for foreign key values
        for fk_column, rel_info in relationships.items():
            target_table = rel_info["target_table"]
            
            # Get actual column name (normalized structure uses lowercase with underscores)
            db_column = column_mapping.get(fk_column, fk_column.lower())
            
            # Check if this is for old JSONB tables or new normalized tables
            # For normalized tables (contacts, deals, companies, tasks), use direct column
            # For old JSONB tables (leads, activities, etc.), use original_data
            normalized_tables = ["contacts", "deals", "companies", "tasks"]
            
            if entity_name in normalized_tables:
                # Use direct column access for normalized tables
                query = text(f"""
                    SELECT DISTINCT {db_column}::bigint as fk_id
                    FROM bitrix.{entity_name}
                    WHERE id = ANY(:entity_ids)
                    AND {db_column} IS NOT NULL
                    AND {db_column} != ''
                """)
            else:
                # Use original_data JSONB for non-normalized tables
                query = text(f"""
                    SELECT DISTINCT (original_data->>'{fk_column}')::bigint as fk_id
                    FROM bitrix.{entity_name}
                    WHERE (original_data->>'ID')::bigint = ANY(:entity_ids)
                    AND original_data->>'{fk_column}' IS NOT NULL
                    AND original_data->>'{fk_column}' != ''
                """)
            
            try:
                result = await self.db.execute(query, {"entity_ids": entity_ids})
                fk_values = {row.fk_id for row in result if row.fk_id}
                
                if fk_values:
                    if target_table not in related_ids:
                        related_ids[target_table] = set()
                    related_ids[target_table].update(fk_values)
            except Exception as e:
                logger.warning("failed_to_get_related_ids", 
                             entity=entity_name, 
                             fk_column=fk_column,
                             error=str(e))
        
        # Special handling for activities OWNER_TYPE_ID
        if entity_name == "activities":
            owner_query = text("""
                SELECT 
                    (original_data->>'OWNER_TYPE_ID')::integer as owner_type,
                    (original_data->>'OWNER_ID')::bigint as owner_id
                FROM bitrix.activities
                WHERE (original_data->>'ID')::bigint = ANY(:entity_ids)
                AND original_data->>'OWNER_ID' IS NOT NULL
            """)
            
            result = await self.db.execute(owner_query, {"entity_ids": entity_ids})
            for row in result:
                if row.owner_type in self.ACTIVITY_OWNER_TYPES:
                    target_table = self.ACTIVITY_OWNER_TYPES[row.owner_type]
                    if target_table not in related_ids:
                        related_ids[target_table] = set()
                    related_ids[target_table].add(row.owner_id)
        
        logger.info("collected_related_ids",
                   entity=entity_name,
                   related_counts={k: len(v) for k, v in related_ids.items()})
        
        return related_ids
    
    async def get_table_metadata(self, entity_name: str) -> Dict:
        """Get metadata about a table including columns and relationships"""
        
        # Get record count
        count_query = text(f"SELECT COUNT(*) as cnt FROM bitrix.{entity_name}")
        result = await self.db.execute(count_query)
        record_count = result.scalar()
        
        # Get actual table columns from information_schema
        columns_query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'bitrix' 
            AND table_name = :table_name
            AND column_name NOT IN ('id', 'original_data', 'fetched_at', 'source_hash')
            ORDER BY ordinal_position
        """)
        result = await self.db.execute(columns_query, {"table_name": entity_name})
        
        columns = []
        for row in result:
            # Map PostgreSQL types to simple types
            type_map = {
                "character varying": "string",
                "text": "string",
                "bigint": "integer",
                "integer": "integer",
                "numeric": "decimal",
                "boolean": "boolean",
                "date": "date",
                "timestamp with time zone": "datetime",
                "timestamp without time zone": "datetime",
                "jsonb": "json",
                "ARRAY": "array"
            }
            
            simple_type = type_map.get(row.data_type, "string")
            
            columns.append({
                "name": row.column_name,
                "type": simple_type,
                "nullable": row.is_nullable == "YES"
            })
        
        # Get relationships
        relationships = await self.get_relationship_details(entity_name)
        foreign_keys = [
            {
                "column": col,
                "references": f"{info['target_table']}.{info['target_column']}"
            }
            for col, info in relationships.items()
        ]
        
        return {
            "name": entity_name,
            "record_count": record_count,
            "columns": columns,
            "foreign_keys": foreign_keys,
            "relationships": relationships
        }
