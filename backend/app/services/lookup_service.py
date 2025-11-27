"""
Lookup Service
ID -> Name çözümlemesi için yardımcı servis
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

# Entity-Lookup mapping - hangi alan hangi lookup'ı kullanıyor
LOOKUP_FIELD_MAPPING = {
    "leads": {
        "STATUS_ID": "STATUS",
        "SOURCE_ID": "SOURCE",
    },
    "deals": {
        "STAGE_ID": "DEAL_STAGE",  # Özel: kategori prefix'i ile
        "CATEGORY_ID": "DEAL_CATEGORY",
        "TYPE_ID": "DEAL_TYPE",
        "SOURCE_ID": "SOURCE",
    },
    "contacts": {
        "TYPE_ID": "CONTACT_TYPE",
        "SOURCE_ID": "SOURCE",
        "HONORIFIC": "HONORIFIC",
    },
    "companies": {
        "COMPANY_TYPE": "COMPANY_TYPE",
        "INDUSTRY": "INDUSTRY",
        "EMPLOYEES": "EMPLOYEES",
    },
    "activities": {
        "TYPE_ID": "EVENT_TYPE",
    }
}


class LookupService:
    """
    Lookup değerlerini cache'leyip ID->Name çözümlemesi yapan servis
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Dict[str, str]] = {}
        self._deal_categories: Dict[str, str] = {}
        self._loaded = False
    
    async def load_all_lookups(self):
        """Tüm lookup değerlerini cache'e yükle"""
        if self._loaded:
            return
        
        logger.info("Loading lookup values...")
        
        # Status values
        query = text("""
            SELECT entity_type, status_id, name
            FROM bitrix.lookup_values
        """)
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        for row in rows:
            entity_type = row.entity_type
            if entity_type not in self._cache:
                self._cache[entity_type] = {}
            self._cache[entity_type][row.status_id] = row.name
        
        # Deal categories
        cat_query = text("""
            SELECT bitrix_id, name
            FROM bitrix.deal_categories
        """)
        cat_result = await self.db.execute(cat_query)
        cat_rows = cat_result.fetchall()
        
        for row in cat_rows:
            self._deal_categories[row.bitrix_id] = row.name
        
        self._loaded = True
        logger.info(f"Loaded {len(rows)} lookup values and {len(cat_rows)} deal categories")
    
    def resolve(self, entity_type: str, status_id: str) -> str:
        """
        ID'yi isme çevir
        Bulunamazsa orijinal ID'yi döner
        """
        if not status_id:
            return ""
        
        values = self._cache.get(entity_type.upper(), {})
        return values.get(status_id, status_id)
    
    def resolve_deal_stage(self, stage_id: str, category_id: str = None) -> str:
        """
        Deal stage ID'sini isme çevir
        Stage ID formatı: C24:LOSE gibi (C{category_id}:{stage_code})
        """
        if not stage_id:
            return ""
        
        # Stage ID'den category'yi çıkar
        entity_type = "DEAL_STAGE"
        if ":" in stage_id:
            prefix = stage_id.split(":")[0]
            if prefix.startswith("C"):
                cat_id = prefix[1:]
                entity_type = f"DEAL_STAGE_{cat_id}"
        elif category_id:
            entity_type = f"DEAL_STAGE_{category_id}" if category_id != "0" else "DEAL_STAGE"
        
        return self.resolve(entity_type, stage_id)
    
    def resolve_deal_category(self, category_id: str) -> str:
        """Deal category ID'sini isme çevir"""
        if not category_id or category_id == "0":
            return "Varsayılan"
        return self._deal_categories.get(category_id, f"Kategori {category_id}")
    
    def get_lookup_entity_type(self, table_name: str, field_name: str) -> Optional[str]:
        """Field için lookup entity type'ını bul"""
        table_map = LOOKUP_FIELD_MAPPING.get(table_name.lower(), {})
        return table_map.get(field_name.upper())
    
    async def resolve_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bir satırdaki tüm lookup alanlarını çöz
        Orijinal row'u değiştirmez, yeni dict döner
        """
        await self.load_all_lookups()
        
        resolved = dict(row)
        table_map = LOOKUP_FIELD_MAPPING.get(table_name.lower(), {})
        
        for field_name, lookup_type in table_map.items():
            if field_name in resolved and resolved[field_name]:
                original_value = str(resolved[field_name])
                
                # Deal stage için özel handling
                if field_name == "STAGE_ID" and table_name.lower() == "deals":
                    category_id = str(resolved.get("CATEGORY_ID", ""))
                    resolved[field_name] = self.resolve_deal_stage(original_value, category_id)
                
                # Deal category için özel handling
                elif field_name == "CATEGORY_ID" and table_name.lower() == "deals":
                    resolved[field_name] = self.resolve_deal_category(original_value)
                
                # Diğer lookup alanları
                else:
                    resolved[field_name] = self.resolve(lookup_type, original_value)
        
        return resolved
    
    async def resolve_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Birden fazla satırı çöz"""
        await self.load_all_lookups()
        
        return [await self.resolve_row(table_name, row) for row in rows]


async def get_lookup_service(db: AsyncSession) -> LookupService:
    """LookupService factory"""
    service = LookupService(db)
    await service.load_all_lookups()
    return service
