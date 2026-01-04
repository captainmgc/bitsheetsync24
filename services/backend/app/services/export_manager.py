"""
Export Manager - Main Orchestrator
Coordinates all export services for complete workflow
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from app.models.export_log import ExportLog, ExportBatchLog, ExportStatus, ExportType
from app.schemas.export import ExportConfigCreate, ExportProgressUpdate
from app.services.relationship_analyzer import RelationshipAnalyzer
from app.services.data_formatter import DataFormatter
from app.services.sheets_uploader import SheetsUploader
from app.services.batch_processor import BatchProcessor

logger = structlog.get_logger()


class ExportManager:
    """
    Main export orchestrator
    Handles complete export workflow from DB to Google Sheets
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.relationship_analyzer = RelationshipAnalyzer(db)
        self.sheets_uploader = SheetsUploader()
    
    async def create_export(self, config: ExportConfigCreate) -> ExportLog:
        """
        Create new export job
        
        Args:
            config: Export configuration
            
        Returns:
            Created ExportLog record
        """
        # Analyze relationships if auto-detect enabled
        related_entities = config.related_entities
        if config.include_related and not related_entities:
            related_entities = await self.relationship_analyzer.get_related_tables(
                config.entity_name
            )
        
        # Create export log
        export_log = ExportLog(
            export_type=config.export_type,
            entity_name=config.entity_name,
            date_from=config.date_range.date_from if config.date_range else None,
            date_to=config.date_range.date_to if config.date_range else None,
            related_entities=related_entities,
            config=config.model_dump(),
            status=ExportStatus.PENDING,
            batch_size=config.batch_size,
            sheet_url=config.sheet_url,
            sheet_gid=config.sheet_gid,
            created_by=config.created_by or "system"
        )
        
        self.db.add(export_log)
        await self.db.commit()
        await self.db.refresh(export_log)
        
        logger.info("export_created",
                   export_id=export_log.id,
                   entity=config.entity_name,
                   type=config.export_type)
        
        return export_log
    
    async def run_export(self, export_id: int) -> ExportLog:
        """
        Execute export job
        
        Args:
            export_id: Export log ID
            
        Returns:
            Updated ExportLog
        """
        # Get export log
        result = await self.db.execute(
            text("SELECT * FROM bitrix.export_logs WHERE id = :id"),
            {"id": export_id}
        )
        export_data = result.mappings().first()
        
        if not export_data:
            raise ValueError(f"Export {export_id} not found")
        
        # Update status to running
        await self.db.execute(
            text("""
                UPDATE bitrix.export_logs 
                SET status = :status, started_at = now()
                WHERE id = :id
            """),
            {"id": export_id, "status": ExportStatus.RUNNING.value}
        )
        await self.db.commit()
        
        try:
            config = export_data["config"]
            entity_name = export_data["entity_name"]
            
            # Fetch data from database
            logger.info("fetching_data", export_id=export_id, entity=entity_name)
            records = await self._fetch_records(
                entity_name=entity_name,
                export_type=ExportType(export_data["export_type"]),
                date_from=export_data["date_from"],
                date_to=export_data["date_to"],
                custom_filter=config.get("custom_filter")
            )
            
            total_records = len(records)
            
            # Update total count
            await self.db.execute(
                text("UPDATE bitrix.export_logs SET total_records = :total WHERE id = :id"),
                {"id": export_id, "total": total_records}
            )
            await self.db.commit()
            
            # Fetch related data if needed
            related_data = {}
            if export_data["related_entities"]:
                logger.info("fetching_related_data", 
                           export_id=export_id,
                           related=export_data["related_entities"])
                related_data = await self._fetch_related_data(
                    entity_name=entity_name,
                    entity_ids=[int(r["ID"] or r.get("id", 0)) for r in records],
                    related_entities=export_data["related_entities"]
                )
            
            # Format data
            formatter = DataFormatter(
                use_turkish_names=config.get("use_turkish_names", True),
                separate_date_time=config.get("separate_date_time", True)
            )
            
            # Format main records
            formatted_records = [
                formatter.format_row(record, entity_name) 
                for record in records
            ]
            
            # Add related data
            if related_data:
                formatted_records = formatter.add_related_data(
                    formatted_records,
                    related_data,
                    entity_name
                )
            
            # Convert to 2D array for Google Sheets
            sheet_data = formatter.format_batch(
                records=formatted_records,
                entity_name=entity_name,
                include_headers=True
            )
            
            # Process in batches
            batch_processor = BatchProcessor(
                batch_size=export_data["batch_size"],
                max_retries=3
            )
            
            total_batches = (len(sheet_data) + export_data["batch_size"] - 1) // export_data["batch_size"]
            
            await self.db.execute(
                text("UPDATE bitrix.export_logs SET total_batches = :total WHERE id = :id"),
                {"id": export_id, "total": total_batches}
            )
            await self.db.commit()
            
            # Process batches
            processed_count = 0
            
            async def process_batch(batch_data, batch_num, total_batches):
                nonlocal processed_count
                
                # Upload to Google Sheets
                await self.sheets_uploader.upload_batch(
                    data=batch_data,
                    sheet_gid=export_data["sheet_gid"] or "0",
                    operation="smart_merge" if batch_num > 1 else "replace"
                )
                
                processed_count += len(batch_data) - (1 if batch_num == 1 else 0)  # Exclude header
                
                # Update progress
                await self.db.execute(
                    text("""
                        UPDATE bitrix.export_logs 
                        SET processed_records = :processed, completed_batches = :batches
                        WHERE id = :id
                    """),
                    {
                        "id": export_id,
                        "processed": processed_count,
                        "batches": batch_num
                    }
                )
                await self.db.commit()
            
            # Split data into batches and process
            batches = batch_processor.chunk_list(sheet_data, export_data["batch_size"])
            
            for idx, batch in enumerate(batches):
                await process_batch(batch, idx + 1, len(batches))
            
            # Mark as completed
            await self.db.execute(
                text("""
                    UPDATE bitrix.export_logs 
                    SET 
                        status = :status,
                        completed_at = now(),
                        duration_seconds = EXTRACT(EPOCH FROM (now() - started_at))
                    WHERE id = :id
                """),
                {"id": export_id, "status": ExportStatus.COMPLETED.value}
            )
            await self.db.commit()
            
            logger.info("export_completed",
                       export_id=export_id,
                       records=processed_count)
            
        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            await self.db.execute(
                text("""
                    UPDATE bitrix.export_logs 
                    SET 
                        status = :status,
                        error_message = :error,
                        completed_at = now(),
                        duration_seconds = EXTRACT(EPOCH FROM (now() - started_at))
                    WHERE id = :id
                """),
                {
                    "id": export_id,
                    "status": ExportStatus.FAILED.value,
                    "error": error_msg
                }
            )
            await self.db.commit()
            
            logger.error("export_failed", export_id=export_id, error=error_msg)
            raise
        
        # Refresh and return
        result = await self.db.execute(
            text("SELECT * FROM bitrix.export_logs WHERE id = :id"),
            {"id": export_id}
        )
        return result.mappings().first()
    
    async def _fetch_records(
        self,
        entity_name: str,
        export_type: ExportType,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        custom_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Fetch records from database based on export type"""
        
        # Base query
        query_parts = [f"SELECT data FROM bitrix.{entity_name}"]
        params = {}
        
        # Build WHERE clause based on export type
        where_conditions = []
        
        if export_type == ExportType.DATE_RANGE and date_from and date_to:
            # Date range filter
            where_conditions.append(
                """
                TO_TIMESTAMP((data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') 
                BETWEEN :date_from AND :date_to
                """
            )
            params["date_from"] = date_from
            params["date_to"] = date_to
        
        if custom_filter:
            # Add custom filters
            pass  # TODO: implement custom filter logic
        
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))
        
        query = " ".join(query_parts)
        
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()
        
        records = [row[0] for row in rows]
        
        # Lookup çözümlemesi uygula - ID'leri isimlere çevir
        from app.services.lookup_service import get_lookup_service
        lookup_service = await get_lookup_service(self.db)
        
        resolved_records = []
        for record in records:
            resolved_record = await lookup_service.resolve_row(entity_name, record)
            resolved_records.append(resolved_record)
        
        return resolved_records
    
    async def _fetch_related_data(
        self,
        entity_name: str,
        entity_ids: List[int],
        related_entities: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch related table data"""
        
        # Get required IDs for each related table
        required_ids = await self.relationship_analyzer.get_required_ids(
            entity_name,
            entity_ids
        )
        
        related_data = {}
        
        for related_entity in related_entities:
            if related_entity not in required_ids:
                continue
            
            ids = list(required_ids[related_entity])
            
            query = text(f"""
                SELECT data 
                FROM bitrix.{related_entity}
                WHERE (data->>'ID')::bigint = ANY(:ids)
            """)
            
            result = await self.db.execute(query, {"ids": ids})
            rows = result.fetchall()
            
            related_data[related_entity] = [row[0] for row in rows]
        
        return related_data
