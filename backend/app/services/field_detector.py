"""
Field Detection Service
Auto-detects field mappings from Google Sheets headers to Bitrix24 fields
"""

from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger()

# Common field name mappings (Sheets header → Bitrix24 field)
COMMON_FIELD_MAPPINGS = {
    # Contact/Deal fields
    "name": "TITLE",
    "title": "TITLE",
    "başlık": "TITLE",
    "ad": "TITLE",
    
    "email": "EMAIL",
    "e-mail": "EMAIL",
    "e-posta": "EMAIL",
    
    "phone": "PHONE",
    "telefon": "PHONE",
    "tel": "PHONE",
    
    "status": "STATUS_ID",
    "durum": "STATUS_ID",
    
    "description": "DESCRIPTION",
    "açıklama": "DESCRIPTION",
    
    "company": "COMPANY_ID",
    "company_id": "COMPANY_ID",
    "şirket": "COMPANY_ID",
    "şirket_id": "COMPANY_ID",
    
    "address": "ADDRESS",
    "adres": "ADDRESS",
    
    "website": "WEB",
    "web": "WEB",
    "site": "WEB",
    
    "notes": "COMMENTS",
    "notlar": "COMMENTS",
    "açıklamalar": "COMMENTS",
    
    "created_at": "DATE_CREATE",
    "oluşturulma": "DATE_CREATE",
    
    "modified_at": "DATE_MODIFY",
    "güncellenme": "DATE_MODIFY",
    
    "assigned_to": "ASSIGNED_BY_ID",
    "assigned_by": "ASSIGNED_BY_ID",
    "sorumlu": "ASSIGNED_BY_ID",
    
    # Deal specific
    "amount": "OPPORTUNITY",
    "tutar": "OPPORTUNITY",
    "stage": "STAGE_ID",
    "aşama": "STAGE_ID",
    "fırsat": "OPPORTUNITY",
    
    # Task specific
    "task_id": "id",
    "responsible": "responsibleId",
    "sorumlu_id": "responsibleId",
    "deadline": "deadline",
    "son_tarih": "deadline",
}

# Data type detection patterns
DATA_TYPE_PATTERNS = {
    "string": ["name", "title", "email", "phone", "address", "notes", "description", "website", "ad", "başlık", "telefon", "adres"],
    "date": ["date", "created", "modified", "deadline", "tarih", "oluşturulma", "güncellenme", "son_tarih"],
    "number": ["amount", "id", "count", "quantity", "tutar", "sayı", "miktar"],
    "boolean": ["active", "enabled", "completed", "aktif", "tamamlandı"],
}


class FieldDetector:
    """
    Automatically detects field mappings from Google Sheets headers
    to Bitrix24 fields based on common naming patterns
    """

    @staticmethod
    def normalize_field_name(field_name: str) -> str:
        """
        Normalize field name for comparison
        - lowercase
        - remove special chars
        - trim whitespace
        """
        return field_name.strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def detect_field_type(field_name: str) -> str:
        """
        Detect data type based on field name patterns
        
        Args:
            field_name: Field name from Sheets header
            
        Returns:
            Data type: "string", "number", "date", "boolean"
        """
        normalized = FieldDetector.normalize_field_name(field_name)

        for data_type, patterns in DATA_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in normalized:
                    return data_type

        return "string"  # Default

    @staticmethod
    def detect_bitrix_field(sheet_column_name: str) -> Optional[str]:
        """
        Detect Bitrix24 field name from Sheets column header
        
        Args:
            sheet_column_name: Column header from Google Sheets
            
        Returns:
            Bitrix24 field name or None if not found
        """
        normalized = FieldDetector.normalize_field_name(sheet_column_name)

        # Exact match
        if normalized in COMMON_FIELD_MAPPINGS:
            return COMMON_FIELD_MAPPINGS[normalized]

        # Partial match (first match wins)
        for key, bitrix_field in COMMON_FIELD_MAPPINGS.items():
            if key in normalized or normalized in key:
                return bitrix_field

        return None

    @staticmethod
    def auto_detect_mappings(headers: List[str]) -> List[Dict[str, any]]:
        """
        Auto-detect field mappings from Sheets headers
        
        Args:
            headers: List of column headers from Google Sheets
                    e.g., ["Name", "Email", "Phone", "Status"]
                    
        Returns:
            List of detected mappings:
            [
                {
                    "sheet_column_index": 0,
                    "sheet_column_name": "Name",
                    "bitrix_field": "TITLE",
                    "data_type": "string",
                    "confidence": 0.95
                },
                ...
            ]
        """
        mappings = []

        for idx, header in enumerate(headers):
            bitrix_field = FieldDetector.detect_bitrix_field(header)
            data_type = FieldDetector.detect_field_type(header)

            # Confidence score (higher = more confident)
            confidence = 0.9 if bitrix_field else 0.0

            mapping = {
                "sheet_column_index": idx,
                "sheet_column_name": header.strip(),
                "bitrix_field": bitrix_field,
                "data_type": data_type,
                "confidence": confidence,
            }

            mappings.append(mapping)

            logger.debug(
                "field_detected",
                column=header,
                index=idx,
                bitrix_field=bitrix_field,
                data_type=data_type,
            )

        return mappings

    @staticmethod
    def validate_mappings(mappings: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Validate auto-detected mappings
        
        Returns:
            {
                "total_fields": 5,
                "mapped_fields": 4,
                "unmapped_fields": 1,
                "confidence_score": 0.85,
                "mappings": [...]
            }
        """
        total = len(mappings)
        mapped = len([m for m in mappings if m["bitrix_field"]])
        unmapped = total - mapped

        confidence_scores = [m["confidence"] for m in mappings if m["bitrix_field"]]
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0
        )

        return {
            "total_fields": total,
            "mapped_fields": mapped,
            "unmapped_fields": unmapped,
            "confidence_score": avg_confidence,
            "mappings": mappings,
            "status": "ready" if mapped > 0 else "needs_manual_mapping",
        }

    @staticmethod
    def manual_map_field(
        sheet_column_name: str, bitrix_field: str
    ) -> Dict[str, any]:
        """
        Manually map a Sheets column to Bitrix field
        (User correction after auto-detection)
        
        Args:
            sheet_column_name: Column header
            bitrix_field: Bitrix24 field to map to
            
        Returns:
            Updated mapping dict
        """
        data_type = FieldDetector.detect_field_type(sheet_column_name)

        return {
            "sheet_column_name": sheet_column_name.strip(),
            "bitrix_field": bitrix_field,
            "data_type": data_type,
            "is_manual": True,
        }
