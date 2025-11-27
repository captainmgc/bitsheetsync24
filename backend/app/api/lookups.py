"""
Lookup Values API Endpoints
Bitrix24 ID -> Name çözümlemesi için endpoint'ler
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import structlog

from app.database import get_db

router = APIRouter()
logger = structlog.get_logger()


@router.get("/")
async def list_lookup_entity_types(db: AsyncSession = Depends(get_db)):
    """
    Mevcut lookup entity type'larını listeler.
    Her entity type için değer sayısını döner.
    """
    query = text("""
        SELECT 
            entity_type,
            COUNT(*) as value_count,
            MAX(updated_at) as last_updated
        FROM bitrix.lookup_values
        GROUP BY entity_type
        ORDER BY entity_type
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "entity_type": row.entity_type,
            "value_count": row.value_count,
            "last_updated": row.last_updated.isoformat() if row.last_updated else None
        }
        for row in rows
    ]


@router.get("/values/{entity_type}")
async def get_lookup_values(
    entity_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Belirli bir entity type için tüm lookup değerlerini döner.
    
    Örnek entity_type'lar:
    - STATUS: Lead aşamaları
    - SOURCE: Kaynaklar
    - DEAL_TYPE: Anlaşma türleri
    - DEAL_STAGE_24: Belirli kategori için deal aşamaları
    - CONTACT_TYPE: Kişi türleri
    - COMPANY_TYPE: Şirket türleri
    """
    query = text("""
        SELECT 
            status_id,
            name,
            name_init,
            color,
            sort,
            semantics,
            category_id
        FROM bitrix.lookup_values
        WHERE entity_type = :entity_type
        ORDER BY sort, name
    """)
    
    result = await db.execute(query, {"entity_type": entity_type.upper()})
    rows = result.fetchall()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"Entity type '{entity_type}' bulunamadı")
    
    return [
        {
            "id": row.status_id,
            "name": row.name,
            "name_init": row.name_init,
            "color": row.color,
            "sort": row.sort,
            "semantics": row.semantics,
            "category_id": row.category_id
        }
        for row in rows
    ]


@router.get("/resolve/{entity_type}/{status_id}")
async def resolve_lookup_value(
    entity_type: str,
    status_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Tek bir ID'yi name'e çözer.
    
    Örnek: /resolve/STATUS/NEW -> {"id": "NEW", "name": "YENİ TALEP", ...}
    """
    query = text("""
        SELECT 
            status_id,
            name,
            name_init,
            color,
            semantics
        FROM bitrix.lookup_values
        WHERE entity_type = :entity_type AND status_id = :status_id
    """)
    
    result = await db.execute(query, {
        "entity_type": entity_type.upper(),
        "status_id": status_id
    })
    row = result.fetchone()
    
    if not row:
        return {"id": status_id, "name": status_id, "resolved": False}
    
    return {
        "id": row.status_id,
        "name": row.name,
        "name_init": row.name_init,
        "color": row.color,
        "semantics": row.semantics,
        "resolved": True
    }


@router.post("/resolve-batch")
async def resolve_batch(
    items: List[Dict[str, str]],
    db: AsyncSession = Depends(get_db)
):
    """
    Birden fazla ID'yi toplu olarak çözer.
    
    Request body örneği:
    [
        {"entity_type": "STATUS", "status_id": "NEW"},
        {"entity_type": "SOURCE", "status_id": "CALLBACK"},
        {"entity_type": "DEAL_STAGE_24", "status_id": "C24:LOSE"}
    ]
    """
    results = []
    
    for item in items:
        entity_type = item.get("entity_type", "").upper()
        status_id = item.get("status_id", "")
        
        if not entity_type or not status_id:
            results.append({"id": status_id, "name": status_id, "resolved": False})
            continue
        
        query = text("""
            SELECT name, color, semantics
            FROM bitrix.lookup_values
            WHERE entity_type = :entity_type AND status_id = :status_id
        """)
        
        result = await db.execute(query, {
            "entity_type": entity_type,
            "status_id": status_id
        })
        row = result.fetchone()
        
        if row:
            results.append({
                "id": status_id,
                "entity_type": entity_type,
                "name": row.name,
                "color": row.color,
                "semantics": row.semantics,
                "resolved": True
            })
        else:
            results.append({
                "id": status_id,
                "entity_type": entity_type,
                "name": status_id,
                "resolved": False
            })
    
    return results


@router.get("/deal-categories")
async def get_deal_categories(db: AsyncSession = Depends(get_db)):
    """
    Tüm deal kategorilerini (pipeline'ları) döner.
    """
    query = text("""
        SELECT 
            bitrix_id as id,
            name,
            sort,
            is_locked
        FROM bitrix.deal_categories
        ORDER BY sort
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "id": row.id,
            "name": row.name,
            "sort": row.sort,
            "is_locked": row.is_locked
        }
        for row in rows
    ]


@router.get("/deal-stages")
async def get_deal_stages(
    category_id: Optional[str] = Query(None, description="Belirli kategori için filtreleme"),
    db: AsyncSession = Depends(get_db)
):
    """
    Deal aşamalarını kategorileriyle birlikte döner.
    category_id parametresi ile belirli bir pipeline'ın aşamalarını filtreleyebilirsiniz.
    """
    if category_id:
        # Belirli kategori için stage'leri getir
        entity_type = f"DEAL_STAGE_{category_id}" if category_id != "0" else "DEAL_STAGE"
        
        query = text("""
            SELECT 
                lv.status_id as stage_id,
                lv.name as stage_name,
                lv.color,
                lv.semantics,
                lv.sort,
                dc.bitrix_id as category_id,
                dc.name as category_name
            FROM bitrix.lookup_values lv
            LEFT JOIN bitrix.deal_categories dc ON lv.category_id = dc.bitrix_id
            WHERE lv.entity_type = :entity_type
            ORDER BY lv.sort
        """)
        
        result = await db.execute(query, {"entity_type": entity_type})
    else:
        # Tüm stage'leri getir
        query = text("""
            SELECT 
                lv.status_id as stage_id,
                lv.name as stage_name,
                lv.color,
                lv.semantics,
                lv.sort,
                dc.bitrix_id as category_id,
                dc.name as category_name,
                lv.entity_type
            FROM bitrix.lookup_values lv
            LEFT JOIN bitrix.deal_categories dc ON lv.category_id = dc.bitrix_id
            WHERE lv.entity_type LIKE 'DEAL_STAGE%'
            ORDER BY dc.sort, lv.sort
        """)
        
        result = await db.execute(query)
    
    rows = result.fetchall()
    
    return [
        {
            "stage_id": row.stage_id,
            "stage_name": row.stage_name,
            "color": row.color,
            "semantics": row.semantics,
            "sort": row.sort,
            "category_id": row.category_id,
            "category_name": row.category_name
        }
        for row in rows
    ]


@router.get("/entity-mappings")
async def get_entity_mappings(db: AsyncSession = Depends(get_db)):
    """
    Entity-Lookup eşleştirmelerini döner.
    Hangi entity'nin hangi alanı hangi lookup tablosunu kullanıyor.
    """
    query = text("""
        SELECT 
            entity_name,
            field_name,
            lookup_entity_type,
            description
        FROM bitrix.lookup_entity_mapping
        ORDER BY entity_name, field_name
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "entity_name": row.entity_name,
            "field_name": row.field_name,
            "lookup_entity_type": row.lookup_entity_type,
            "description": row.description
        }
        for row in rows
    ]


@router.get("/all")
async def get_all_lookups(db: AsyncSession = Depends(get_db)):
    """
    Tüm lookup değerlerini tek seferde döner.
    Frontend'de cache'lemek için kullanılabilir.
    """
    # Status values
    status_query = text("""
        SELECT 
            entity_type,
            status_id,
            name,
            color,
            semantics,
            category_id,
            sort
        FROM bitrix.lookup_values
        ORDER BY entity_type, sort
    """)
    
    status_result = await db.execute(status_query)
    status_rows = status_result.fetchall()
    
    # Deal categories
    category_query = text("""
        SELECT bitrix_id, name, sort
        FROM bitrix.deal_categories
        ORDER BY sort
    """)
    
    category_result = await db.execute(category_query)
    category_rows = category_result.fetchall()
    
    # Group by entity type
    lookups: Dict[str, List[Dict[str, Any]]] = {}
    for row in status_rows:
        entity_type = row.entity_type
        if entity_type not in lookups:
            lookups[entity_type] = []
        lookups[entity_type].append({
            "id": row.status_id,
            "name": row.name,
            "color": row.color,
            "semantics": row.semantics,
            "category_id": row.category_id,
            "sort": row.sort
        })
    
    return {
        "lookups": lookups,
        "deal_categories": [
            {"id": row.bitrix_id, "name": row.name, "sort": row.sort}
            for row in category_rows
        ],
        "total_count": len(status_rows),
        "entity_types": list(lookups.keys())
    }
