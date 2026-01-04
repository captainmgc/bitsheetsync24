"""
Data Formatter Service
Converts JSONB data to Turkish-formatted export rows
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class DataFormatter:
    """
    Formats Bitrix24 JSONB data for Google Sheets export
    - Turkish column names
    - Separate date/time columns
    - Handles camelCase vs UPPERCASE fields
    """
    
    # Turkish column name mappings
    TURKISH_COLUMNS = {
        # Common fields
        "ID": "id",
        "TITLE": "baslik",
        "NAME": "ad",
        "LAST_NAME": "soyad",
        "DESCRIPTION": "aciklama",
        "STATUS": "durum",
        "STATUS_ID": "durum",
        "PRIORITY": "oncelik",
        
        # Contact info
        "PHONE": "telefon",
        "EMAIL": "email",
        "ADDRESS": "adres",
        
        # Company
        "COMPANY_TYPE": "sirket_tipi",
        "COMPANY_ID": "sirket_id",
        
        # Users
        "ASSIGNED_BY_ID": "sorumlu_id",
        "RESPONSIBLE_ID": "sorumlu_id",
        "responsibleId": "sorumlu_id",  # Tasks camelCase
        "CREATED_BY_ID": "olusturan_id",
        "CREATED_BY": "olusturan_id",
        "createdBy": "olusturan_id",  # Tasks camelCase
        "MODIFY_BY_ID": "duzenleyen_id",
        
        # Dates
        "DATE_CREATE": "olusturma_zamani",
        "DATE_MODIFY": "guncelleme_zamani",
        "createdDate": "olusturma_zamani",  # Tasks camelCase
        "changedDate": "guncelleme_zamani",  # Tasks camelCase
        "closedDate": "kapanis_zamani",  # Tasks camelCase
        
        # Deals
        "STAGE_ID": "asamasi",
        "OPPORTUNITY": "tutar",
        "CURRENCY_ID": "para_birimi",
        "CONTACT_ID": "iletisim_id",
        
        # Leads
        "SOURCE_ID": "kaynak",
        
        # Tasks
        "groupId": "grup_id",
        "timeEstimate": "tahmini_sure",
        "timeSpentInLogs": "harcanan_sure",
        
        # Activities
        "SUBJECT": "konu",
        "DIRECTION": "yon",
        "TYPE_ID": "tip",
        "OWNER_ID": "sahip_id",
        "OWNER_TYPE_ID": "sahip_tipi",
        "START_TIME": "baslangic",
        "END_TIME": "bitis",
    }
    
    # Date fields that need special formatting
    DATE_FIELDS = {
        "DATE_CREATE", "DATE_MODIFY", "DATE_CLOSE",
        "CREATED", "LAST_UPDATED", "START_TIME", "END_TIME",
        "createdDate", "changedDate", "closedDate",  # Tasks camelCase
    }
    
    # Fields that are timestamps (Unix epoch)
    TIMESTAMP_FIELDS = {
        "createdDate", "changedDate", "closedDate",  # Tasks use Unix timestamps
    }
    
    def __init__(self, use_turkish_names: bool = True, separate_date_time: bool = True):
        self.use_turkish_names = use_turkish_names
        self.separate_date_time = separate_date_time
    
    def format_row(self, record: Dict[str, Any], entity_name: str) -> Dict[str, Any]:
        """
        Format a single JSONB record for export
        
        Args:
            record: JSONB data dictionary
            entity_name: Table name (for field name handling)
            
        Returns:
            Formatted dictionary with Turkish names and split dates
        """
        formatted = {}
        
        for key, value in record.items():
            if value is None or value == "":
                continue
            
            # Get Turkish column name
            col_name = self.TURKISH_COLUMNS.get(key, key.lower()) if self.use_turkish_names else key
            
            # Handle date/time fields
            if key in self.DATE_FIELDS and self.separate_date_time:
                date_value = self._parse_date(value, key)
                if date_value:
                    # Separate date and time columns
                    formatted[f"{col_name}_tarihi"] = date_value.strftime("%d/%m/%Y")
                    formatted[f"{col_name}_saati"] = date_value.strftime("%H:%M:%S")
                continue
            
            # Handle nested JSONB (like PHONE, EMAIL arrays)
            if isinstance(value, list) and value:
                if isinstance(value[0], dict):
                    # Extract first value from array of objects
                    formatted[col_name] = value[0].get("VALUE", str(value[0]))
                else:
                    formatted[col_name] = str(value[0])
                continue
            
            if isinstance(value, dict):
                # Skip complex nested objects for now
                continue
            
            formatted[col_name] = value
        
        return formatted
    
    def _parse_date(self, value: Any, field_name: str) -> Optional[datetime]:
        """Parse date from various formats"""
        try:
            if field_name in self.TIMESTAMP_FIELDS:
                # Unix timestamp (tasks)
                if isinstance(value, (int, str)):
                    return datetime.fromtimestamp(int(value))
            else:
                # ISO 8601 format (CRM entities)
                if isinstance(value, str):
                    # Remove timezone info for simplicity
                    clean_value = value.split("+")[0].split("-")[0]
                    return datetime.fromisoformat(clean_value.replace("T", " "))
        except (ValueError, TypeError) as e:
            logger.warning("date_parse_error", field=field_name, value=value, error=str(e))
        
        return None
    
    def format_batch(
        self, 
        records: List[Dict[str, Any]], 
        entity_name: str,
        include_headers: bool = True
    ) -> List[List[Any]]:
        """
        Format a batch of records for Google Sheets
        
        Args:
            records: List of JSONB dictionaries
            entity_name: Table name
            include_headers: Include header row
            
        Returns:
            2D array for Google Sheets (header + data rows)
        """
        if not records:
            return []
        
        # Format all records
        formatted_records = [self.format_row(record, entity_name) for record in records]
        
        # Get all unique column names (union of all record keys)
        all_columns = set()
        for record in formatted_records:
            all_columns.update(record.keys())
        
        # Sort columns for consistency
        columns = sorted(all_columns)
        
        # Build 2D array
        result = []
        
        if include_headers:
            result.append(columns)
        
        # Add data rows
        for record in formatted_records:
            row = [record.get(col, "") for col in columns]
            result.append(row)
        
        return result
    
    def add_related_data(
        self,
        main_rows: List[Dict[str, Any]],
        related_data: Dict[str, List[Dict[str, Any]]],
        entity_name: str
    ) -> List[Dict[str, Any]]:
        """
        Join related table data (like users, companies) to main rows
        
        Args:
            main_rows: Main entity formatted rows
            related_data: {"users": [...], "companies": [...]}
            entity_name: Main entity name
            
        Returns:
            Enriched rows with related data
        """
        # Create lookup dictionaries for related data
        lookups = {}
        for related_entity, records in related_data.items():
            lookups[related_entity] = {
                str(r.get("ID", r.get("id"))): r 
                for r in records
            }
        
        # Enrich main rows
        enriched = []
        for row in main_rows:
            enriched_row = row.copy()
            
            # Find foreign key references and add related data
            if "sorumlu_id" in row and "users" in lookups:
                user_id = str(row["sorumlu_id"])
                if user_id in lookups["users"]:
                    user = lookups["users"][user_id]
                    enriched_row["sorumlu_ad"] = user.get("NAME", "")
                    enriched_row["sorumlu_soyad"] = user.get("LAST_NAME", "")
            
            if "sirket_id" in row and "companies" in lookups:
                company_id = str(row["sirket_id"])
                if company_id in lookups["companies"]:
                    company = lookups["companies"][company_id]
                    enriched_row["sirket_adi"] = company.get("TITLE", "")
            
            enriched.append(enriched_row)
        
        return enriched
