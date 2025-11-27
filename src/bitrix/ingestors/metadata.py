"""
Bitrix24 Metadata/Lookup Values Ingestor
Senkronize eder:
- CRM Status değerleri (lead stages, sources, types, etc.)
- Deal kategorileri (pipelines)
"""
from typing import Optional
import logging
import json
from src.bitrix.client import BitrixClient
from src.storage import get_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


def sync_status_values(client: BitrixClient) -> int:
    """
    crm.status.list API'sinden tüm status değerlerini çeker ve lookup_values tablosuna kaydeder.
    """
    logger.info("Syncing CRM status values...")
    
    count = 0
    eng = get_engine()
    
    # Tüm status değerlerini çek
    result = client.call("crm.status.list")
    items = result.get("result", [])
    
    with eng.begin() as conn:
        for item in items:
            entity_id = item.get("ENTITY_ID", "")
            status_id = item.get("STATUS_ID", "")
            name = item.get("NAME", "")
            
            if not entity_id or not status_id:
                continue
            
            # Extra bilgileri JSON olarak sakla
            extra = item.get("EXTRA")
            
            conn.execute(text("""
                INSERT INTO bitrix.lookup_values 
                    (entity_type, status_id, name, name_init, sort, color, semantics, category_id, is_system, extra, bitrix_id, updated_at)
                VALUES 
                    (:entity_type, :status_id, :name, :name_init, :sort, :color, :semantics, :category_id, :is_system, CAST(:extra AS jsonb), :bitrix_id, NOW())
                ON CONFLICT (entity_type, status_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    name_init = EXCLUDED.name_init,
                    sort = EXCLUDED.sort,
                    color = EXCLUDED.color,
                    semantics = EXCLUDED.semantics,
                    category_id = EXCLUDED.category_id,
                    is_system = EXCLUDED.is_system,
                    extra = EXCLUDED.extra,
                    bitrix_id = EXCLUDED.bitrix_id,
                    updated_at = NOW()
            """), {
                "entity_type": entity_id,
                "status_id": status_id,
                "name": name,
                "name_init": item.get("NAME_INIT", ""),
                "sort": int(item.get("SORT", 100)),
                "color": item.get("COLOR", ""),
                "semantics": item.get("SEMANTICS"),
                "category_id": item.get("CATEGORY_ID"),
                "is_system": item.get("SYSTEM") == "Y",
                "extra": json.dumps(extra) if extra else None,
                "bitrix_id": item.get("ID")
            })
            count += 1
    
    logger.info(f"Synced {count} status values")
    return count


def sync_deal_categories(client: BitrixClient) -> int:
    """
    crm.dealcategory.list API'sinden deal kategorilerini (pipeline) çeker.
    """
    logger.info("Syncing deal categories...")
    
    count = 0
    eng = get_engine()
    
    # Deal kategorilerini çek
    result = client.call("crm.dealcategory.list")
    items = result.get("result", [])
    
    with eng.begin() as conn:
        for item in items:
            bitrix_id = item.get("ID", "")
            name = item.get("NAME", "")
            
            if not bitrix_id:
                continue
            
            conn.execute(text("""
                INSERT INTO bitrix.deal_categories 
                    (bitrix_id, name, sort, is_locked, created_date, updated_at)
                VALUES 
                    (:bitrix_id, :name, :sort, :is_locked, :created_date, NOW())
                ON CONFLICT (bitrix_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    sort = EXCLUDED.sort,
                    is_locked = EXCLUDED.is_locked,
                    updated_at = NOW()
            """), {
                "bitrix_id": bitrix_id,
                "name": name,
                "sort": int(item.get("SORT", 100)),
                "is_locked": item.get("IS_LOCKED") == "Y",
                "created_date": item.get("CREATED_DATE")
            })
            count += 1
    
    logger.info(f"Synced {count} deal categories")
    return count


def sync_entity_types(client: BitrixClient) -> int:
    """
    crm.status.entity.types API'sinden entity type tanımlarını çeker.
    Bu, hangi entity_type'ların mevcut olduğunu bilmemizi sağlar.
    """
    logger.info("Syncing status entity types...")
    
    count = 0
    eng = get_engine()
    
    result = client.call("crm.status.entity.types")
    items = result.get("result", [])
    
    # Bu bilgiyi loglayalım, ileride kullanılabilir
    for item in items:
        entity_id = item.get("ID", "")
        entity_name = item.get("NAME", "")
        category_id = item.get("CATEGORY_ID")
        
        logger.debug(f"Entity type: {entity_id} - {entity_name} (category: {category_id})")
        count += 1
    
    logger.info(f"Found {count} entity types")
    return count


def full_sync(client: BitrixClient, limit: Optional[int] = None) -> int:
    """
    Tüm metadata/lookup değerlerini senkronize eder.
    """
    logger.info("Starting full metadata sync...")
    
    total = 0
    
    # Status değerlerini sync et
    total += sync_status_values(client)
    
    # Deal kategorilerini sync et
    total += sync_deal_categories(client)
    
    # Entity type'ları logla (isteğe bağlı)
    sync_entity_types(client)
    
    # Sync state güncelle
    _update_sync_state(total)
    
    logger.info(f"Metadata sync completed: {total} total records")
    return total


def _update_sync_state(count: int):
    """Sync state tablosunu güncelle"""
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(text("""
                INSERT INTO bitrix.sync_state (entity, last_sync_at, last_full_sync_at, record_count, status)
                VALUES ('metadata', now(), now(), :count, 'completed')
                ON CONFLICT (entity) DO UPDATE SET
                    last_sync_at = now(),
                    last_full_sync_at = now(),
                    record_count = :count,
                    status = 'completed',
                    updated_at = now()
            """), {"count": count})
    except Exception as e:
        logger.error(f"Failed to update sync state: {e}")
