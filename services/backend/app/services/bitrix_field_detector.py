"""
Bitrix24 Field Detection Service
Detects editable/read-only fields from Bitrix24 API
Fetches field metadata from crm.*.fields endpoints
"""

import httpx
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from functools import lru_cache

from app.config import settings

logger = structlog.get_logger()


# Cache for field metadata (entity_type -> fields)
_field_cache: Dict[str, Dict[str, Any]] = {}
_cache_expiry: Dict[str, datetime] = {}
CACHE_TTL = timedelta(hours=24)  # Cache for 24 hours


class Bitrix24FieldDetector:
    """
    Detects editable fields from Bitrix24 API
    Uses crm.*.fields endpoints to get field metadata
    """
    
    # Entity type to API method mapping
    ENTITY_FIELD_METHODS = {
        "leads": "crm.lead.fields",
        "contacts": "crm.contact.fields", 
        "companies": "crm.company.fields",
        "deals": "crm.deal.fields",
        "tasks": "tasks.task.getfields",
        "activities": "crm.activity.fields",
    }
    
    # Entity type to update API method mapping
    ENTITY_UPDATE_METHODS = {
        "leads": "crm.lead.update",
        "contacts": "crm.contact.update",
        "companies": "crm.company.update", 
        "deals": "crm.deal.update",
        "tasks": "tasks.task.update",
        "activities": "crm.activity.update",
    }
    
    # Known read-only fields (system fields that cannot be updated)
    READONLY_FIELDS = {
        "ID", "DATE_CREATE", "DATE_MODIFY", "CREATED_BY_ID", "MODIFY_BY_ID",
        "CREATED_BY", "MODIFIED_BY", "LEAD_ID", "CONTACT_ID", "COMPANY_ID",
        "HAS_PHONE", "HAS_EMAIL", "HAS_IMOL", "ORIGIN_ID", "ORIGINATOR_ID",
        "FACE_ID", "UTM_SOURCE", "UTM_MEDIUM", "UTM_CAMPAIGN", "UTM_CONTENT", "UTM_TERM"
    }
    
    # Fields that should never be updated from Sheets
    PROTECTED_FIELDS = {
        "ID", "DATE_CREATE", "CREATED_BY_ID", "ORIGINATOR_ID", "ORIGIN_ID"
    }

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize with Bitrix24 webhook URL
        
        Args:
            webhook_url: Bitrix24 REST webhook URL (from .env if not provided)
        """
        self.webhook_url = webhook_url or settings.bitrix24_webhook_url
        if self.webhook_url.endswith('/'):
            self.webhook_url = self.webhook_url[:-1]
        self.timeout = 30

    async def fetch_entity_fields(self, entity_type: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch field metadata from Bitrix24 API
        
        Args:
            entity_type: Entity type (leads, contacts, deals, companies, tasks, activities)
            force_refresh: Force refresh cache
            
        Returns:
            Dict of field_name -> field_metadata
        """
        # Check cache first
        cache_key = entity_type.lower()
        if not force_refresh and cache_key in _field_cache:
            if datetime.now() < _cache_expiry.get(cache_key, datetime.min):
                logger.debug("field_cache_hit", entity_type=entity_type)
                return _field_cache[cache_key]
        
        # Get API method
        method = self.ENTITY_FIELD_METHODS.get(cache_key)
        if not method:
            logger.error("unknown_entity_type", entity_type=entity_type)
            return {}
        
        try:
            url = f"{self.webhook_url}/{method}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
            
            # Extract fields from response
            fields = data.get("result", {})
            
            # Handle tasks.task.getfields different response format
            if entity_type == "tasks" and isinstance(fields, dict):
                # Tasks API returns different structure
                fields = fields.get("fields", fields)
            
            # Cache the result
            _field_cache[cache_key] = fields
            _cache_expiry[cache_key] = datetime.now() + CACHE_TTL
            
            logger.info(
                "bitrix_fields_fetched",
                entity_type=entity_type,
                field_count=len(fields)
            )
            
            return fields
            
        except httpx.HTTPError as e:
            logger.error("bitrix_fields_fetch_failed", entity_type=entity_type, error=str(e))
            return {}
        except Exception as e:
            logger.error("bitrix_fields_fetch_error", entity_type=entity_type, error=str(e))
            return {}

    def is_field_editable(self, field_name: str, field_meta: Dict[str, Any]) -> bool:
        """
        Check if a field is editable based on metadata
        
        Args:
            field_name: Field name (e.g., "TITLE", "EMAIL")
            field_meta: Field metadata from Bitrix24 API
            
        Returns:
            True if field can be updated
        """
        # Check protected fields
        if field_name.upper() in self.PROTECTED_FIELDS:
            return False
        
        # Check known read-only fields
        if field_name.upper() in self.READONLY_FIELDS:
            return False
        
        # Check field metadata
        if isinstance(field_meta, dict):
            # Check isReadOnly flag
            if field_meta.get("isReadOnly", False):
                return False
            
            # Check isImmutable flag
            if field_meta.get("isImmutable", False):
                return False
            
            # Check if field is computed
            if field_meta.get("isComputed", False):
                return False
                
            # Check type - some types are always read-only
            field_type = field_meta.get("type", "")
            if field_type in ["user", "file", "resourcebooking"]:
                return False
        
        return True

    async def get_editable_fields(self, entity_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all editable fields for an entity type
        
        Args:
            entity_type: Entity type (leads, contacts, etc.)
            
        Returns:
            Dict of editable field_name -> field_metadata
        """
        all_fields = await self.fetch_entity_fields(entity_type)
        
        editable_fields = {}
        for field_name, field_meta in all_fields.items():
            if self.is_field_editable(field_name, field_meta):
                editable_fields[field_name] = {
                    "name": field_name,
                    "title": field_meta.get("formLabel", field_meta.get("title", field_name)),
                    "type": field_meta.get("type", "string"),
                    "isRequired": field_meta.get("isRequired", False),
                    "isMultiple": field_meta.get("isMultiple", False),
                    "editable": True
                }
        
        logger.info(
            "editable_fields_detected",
            entity_type=entity_type,
            total_fields=len(all_fields),
            editable_count=len(editable_fields)
        )
        
        return editable_fields

    async def get_readonly_fields(self, entity_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all read-only fields for an entity type
        
        Args:
            entity_type: Entity type (leads, contacts, etc.)
            
        Returns:
            Dict of read-only field_name -> field_metadata
        """
        all_fields = await self.fetch_entity_fields(entity_type)
        
        readonly_fields = {}
        for field_name, field_meta in all_fields.items():
            if not self.is_field_editable(field_name, field_meta):
                readonly_fields[field_name] = {
                    "name": field_name,
                    "title": field_meta.get("formLabel", field_meta.get("title", field_name)),
                    "type": field_meta.get("type", "string"),
                    "editable": False,
                    "reason": self._get_readonly_reason(field_name, field_meta)
                }
        
        return readonly_fields

    def _get_readonly_reason(self, field_name: str, field_meta: Dict[str, Any]) -> str:
        """Get reason why field is read-only"""
        if field_name.upper() in self.PROTECTED_FIELDS:
            return "system_protected"
        if field_name.upper() in self.READONLY_FIELDS:
            return "system_readonly"
        if isinstance(field_meta, dict):
            if field_meta.get("isReadOnly"):
                return "api_readonly"
            if field_meta.get("isImmutable"):
                return "immutable"
            if field_meta.get("isComputed"):
                return "computed"
        return "unknown"

    async def classify_sheet_columns(
        self,
        entity_type: str,
        sheet_headers: List[str],
        field_mappings: Dict[str, str]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Classify sheet columns as editable or read-only
        
        Args:
            entity_type: Bitrix24 entity type
            sheet_headers: List of column headers from Google Sheet
            field_mappings: Mapping of sheet_header -> bitrix_field
            
        Returns:
            Tuple of (editable_columns, readonly_columns)
        """
        editable_fields = await self.get_editable_fields(entity_type)
        
        editable_columns = []
        readonly_columns = []
        
        for idx, header in enumerate(sheet_headers):
            bitrix_field = field_mappings.get(header, header.upper())
            
            column_info = {
                "index": idx,
                "header": header,
                "bitrix_field": bitrix_field,
            }
            
            if bitrix_field in editable_fields:
                column_info["editable"] = True
                column_info["field_type"] = editable_fields[bitrix_field].get("type", "string")
                editable_columns.append(column_info)
            else:
                column_info["editable"] = False
                readonly_columns.append(column_info)
        
        return editable_columns, readonly_columns

    async def get_all_entity_fields_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get summary of all entity fields
        
        Returns:
            Dict of entity_type -> {total, editable, readonly}
        """
        summary = {}
        
        for entity_type in self.ENTITY_FIELD_METHODS.keys():
            try:
                all_fields = await self.fetch_entity_fields(entity_type)
                editable = await self.get_editable_fields(entity_type)
                
                summary[entity_type] = {
                    "total": len(all_fields),
                    "editable": len(editable),
                    "readonly": len(all_fields) - len(editable)
                }
            except Exception as e:
                logger.error("entity_summary_failed", entity_type=entity_type, error=str(e))
                summary[entity_type] = {"total": 0, "editable": 0, "readonly": 0, "error": str(e)}
        
        return summary


# Singleton instance
_detector_instance: Optional[Bitrix24FieldDetector] = None


def get_bitrix_field_detector() -> Bitrix24FieldDetector:
    """Get singleton instance of Bitrix24FieldDetector"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = Bitrix24FieldDetector()
    return _detector_instance
