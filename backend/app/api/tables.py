"""
Table Metadata API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import structlog

from app.database import get_db
from app.schemas.export import TableMetadata, RelationshipInfo
from app.services.relationship_analyzer import RelationshipAnalyzer

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=List[TableMetadata])
async def list_tables(db: AsyncSession = Depends(get_db)):
    """
    Get list of all available tables with metadata
    """
    # Only return Bitrix entity tables (that have 'data' JSONB column)
    valid_tables = [
        'leads', 'contacts', 'companies', 'deals', 
        'activities', 'tasks', 'task_comments', 
        'users', 'departments'
    ]
    
    # Get metadata for each table
    analyzer = RelationshipAnalyzer(db)
    tables = []
    
    for table_name in valid_tables:
        try:
            metadata = await analyzer.get_table_metadata(table_name)
            
            # Get last updated timestamp
            last_updated_query = text(f"""
                SELECT MAX(updated_at) as last_updated
                FROM bitrix.{table_name}
            """)
            result = await db.execute(last_updated_query)
            last_updated = result.scalar()
            
            # Create display name mapping
            display_names = {
                "contacts": "Müşteriler (Contacts)",
                "companies": "Şirketler (Companies)",
                "deals": "Anlaşmalar",
                "activities": "Aktiviteler",
                "tasks": "Görevler",
                "task_comments": "Görev Yorumları",
                "leads": "Potansiyel Müşteriler",
                "users": "Kullanıcılar",
                "statuses": "Durumlar"
            }
            
            tables.append(TableMetadata(
                name=table_name,
                display_name=display_names.get(table_name, table_name.title()),
                record_count=metadata["record_count"],
                last_updated=last_updated,
                columns=metadata["columns"],
                foreign_keys=metadata["foreign_keys"]
            ))
        except Exception as e:
            logger.error("table_metadata_error", table=table_name, error=str(e))
            continue
    
    return tables


@router.get("/{table_name}", response_model=TableMetadata)
async def get_table_metadata(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed metadata for a specific table"""
    
    analyzer = RelationshipAnalyzer(db)
    metadata = await analyzer.get_table_metadata(table_name)
    
    # Get last updated
    query = text(f"""
        SELECT MAX(updated_at) as last_updated
        FROM bitrix.{table_name}
    """)
    result = await db.execute(query)
    last_updated = result.scalar()
    
    return TableMetadata(
        name=table_name,
        display_name=table_name.replace("_", " ").title(),
        record_count=metadata["record_count"],
        last_updated=last_updated,
        columns=metadata["columns"],
        foreign_keys=metadata["foreign_keys"]
    )


@router.get("/{table_name}/relationships", response_model=List[RelationshipInfo])
async def get_table_relationships(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get relationship details for a table"""
    
    analyzer = RelationshipAnalyzer(db)
    relationships = await analyzer.get_relationship_details(table_name)
    
    result = []
    for source_column, rel_info in relationships.items():
        result.append(RelationshipInfo(
            source_table=table_name,
            target_table=rel_info["target_table"],
            source_column=source_column,
            target_column=rel_info["target_column"],
            relationship_type=rel_info["relationship_type"]
        ))
    
    return result


@router.get("/{table_name}/related")
async def get_related_tables(
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get list of tables related to this table"""
    
    analyzer = RelationshipAnalyzer(db)
    related = await analyzer.get_related_tables(table_name)
    
    return {
        "table": table_name,
        "related_tables": related
    }
