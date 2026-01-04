"""
AI Summary API Endpoints
Handles:
- Generate AI summaries for deals
- List summary history
- Write summaries to Bitrix24
- Manage AI provider settings
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, desc, text
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.database import get_db
from app.services.ai_summarizer import (
    CustomerDataCollector,
    AISummarizer,
    BitrixSummaryWriter,
    AIProvider
)
from app.config import settings

import structlog
import os

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/ai-summary", tags=["ai-summary"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AIProviderEnum(str, Enum):
    openai = "openai"
    claude = "claude"
    gemini = "gemini"
    openrouter = "openrouter"
    ollama = "ollama"


class GenerateSummaryRequest(BaseModel):
    """Request to generate AI summary"""
    deal_id: int = Field(..., description="Bitrix24 Deal ID")
    provider: AIProviderEnum = Field(default=AIProviderEnum.openai, description="AI provider to use")
    model: Optional[str] = Field(default=None, description="Specific model to use")
    write_to_bitrix: bool = Field(default=False, description="Write summary to Bitrix24 immediately")
    write_mode: str = Field(default="timeline", description="Where to write: 'timeline' or 'comments'")


class SummaryResponse(BaseModel):
    """AI Summary response"""
    id: Optional[int] = None
    deal_id: int
    deal_title: Optional[str] = None
    summary: str
    provider: str
    model: str
    created_at: datetime
    written_to_bitrix: bool = False
    bitrix_write_result: Optional[dict] = None


class DealListItem(BaseModel):
    """Deal item for listing"""
    id: int
    title: str
    stage_id: Optional[str] = None
    opportunity: Optional[str] = None
    currency: Optional[str] = None
    contact_name: Optional[str] = None
    company_name: Optional[str] = None
    assigned_by_name: Optional[str] = None
    date_create: Optional[str] = None
    date_modify: Optional[str] = None
    has_summary: bool = False
    last_summary_at: Optional[datetime] = None


class SummaryHistoryItem(BaseModel):
    """Summary history item"""
    id: int
    deal_id: int
    deal_title: str
    summary_preview: str
    provider: str
    model: str
    created_at: datetime
    written_to_bitrix: bool


class WriteToBitrixRequest(BaseModel):
    """Request to write existing summary to Bitrix24"""
    summary_id: int
    write_mode: str = Field(default="timeline", description="'timeline' or 'comments'")


class AIProviderConfig(BaseModel):
    """AI Provider configuration"""
    provider: AIProviderEnum
    api_key_configured: bool
    available_models: List[str]
    default_model: str


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/providers")
async def get_ai_providers() -> List[AIProviderConfig]:
    """
    Get available AI providers and their configuration status
    """
    providers = []
    
    # OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "")
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.openai,
        api_key_configured=bool(openai_key),
        available_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        default_model="gpt-4o-mini"
    ))
    
    # Claude
    claude_key = os.getenv("ANTHROPIC_API_KEY", "")
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.claude,
        api_key_configured=bool(claude_key),
        available_models=["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        default_model="claude-3-haiku-20240307"
    ))
    
    # Gemini
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.gemini,
        api_key_configured=bool(gemini_key),
        available_models=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
        default_model="gemini-1.5-flash"
    ))
    
    # OpenRouter (multi-model gateway) - Grok & others
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.openrouter,
        api_key_configured=bool(openrouter_key),
        available_models=[
            "x-ai/grok-4.1-fast:free",
            "x-ai/grok-4-fast",
            "x-ai/grok-3",
            "x-ai/grok-3-mini",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "google/gemini-pro-1.5",
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-70b-instruct",
            "deepseek/deepseek-chat"
        ],
        default_model="x-ai/grok-4.1-fast:free"
    ))
    
    # Ollama (local)
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.ollama,
        api_key_configured=True,  # No key needed for local
        available_models=["llama3.2", "llama3.1", "mistral", "mixtral"],
        default_model="llama3.2"
    ))
    
    return providers


# Stage ID to Name mapping for Bitrix24
STAGE_NAME_MAP = {
    # Genel aşamalar
    'NEW': 'Yeni',
    'PREPARATION': 'Hazırlık',
    'PREPAYMENT_INVOICE': 'Ön Ödeme Faturası',
    'EXECUTING': 'Yürütülüyor',
    'FINAL_INVOICE': 'Son Fatura',
    'WON': 'Kazanıldı',
    'LOSE': 'Kaybedildi',
    'APOLOGY': 'İptal',
    '1': 'Aşama 1',
    '2': 'Aşama 2',
    '3': 'Aşama 3',
    # C24 - Ana Satış Hattı
    'C24:NEW': 'Yeni Lead',
    'C24:PREPARATION': 'Hazırlık',
    'C24:PREPAYMENT_INVOICE': 'Ön Ödeme',
    'C24:EXECUTING': 'Yürütülüyor',
    'C24:FINAL_INVOICE': 'Son Fatura',
    'C24:WON': 'Kazanıldı',
    'C24:LOSE': 'Kaybedildi',
    'C24:UC_4C1LPV': 'İlk Görüşme',
    'C24:UC_UHK94F': 'Teklif Aşaması',
    'C24:UC_JCZELB': 'Müzakere',
    'C24:UC_C1GNUQ': 'Sözleşme Aşaması',
    'C24:UC_FC3310': 'Onay Bekliyor',
    'C24:UC_S9MBJL': 'Ödeme Bekliyor',
    'C24:UC_WOZ7C2': 'Evrak Tamamlama',
    'C24:UC_RID4CL': 'Tapu İşlemleri',
    'C24:UC_RU9Y2W': 'Teslim Aşaması',
    'C24:UC_L2DJM0': 'Satış Sonrası',
    'C24:UC_U14SJW': 'İade Süreci',
    'C24:UC_TVASL9': 'Beklemede',
    'C24:UC_A139H9': 'Yeniden İletişim',
    'C24:UC_DJCNLN': 'Referans',
    'C24:UC_UHEF2A': 'VIP Müşteri',
    'C24:UC_9XEXXQ': 'Özel Durum',
    'C24:UC_96TEM0': 'Arşiv',
    # C36 - İkinci Hat
    'C36:NEW': 'Yeni',
    'C36:PREPARATION': 'Hazırlık',
    'C36:PREPAYMENT_INVOIC': 'Ön Ödeme',
    'C36:EXECUTING': 'Yürütülüyor',
    'C36:WON': 'Kazanıldı',
    'C36:LOSE': 'Kaybedildi',
    'C36:UC_V2VISS': 'Değerlendirme',
    'C36:UC_62107M': 'Aktif Görüşme',
    'C36:UC_H50HMN': 'Teklif Hazır',
    'C36:UC_NEHO6L': 'Onay Süreci',
    'C36:UC_XHNV5V': 'Tamamlandı',
    'C36:1': 'Aşama 1',
    'C36:2': 'Aşama 2',
    'C36:3': 'Aşama 3',
    # C32
    'C32:NEW': 'Yeni',
    'C32:PREPARATION': 'Hazırlık',
    'C32:WON': 'Kazanıldı',
    'C32:LOSE': 'Kaybedildi',
    'C32:UC_MNIRUC': 'İşlemde',
    # C52
    'C52:NEW': 'Yeni',
    'C52:WON': 'Kazanıldı',
    'C52:LOSE': 'Kaybedildi',
    'C52:1': 'Aşama 1',
    # C54
    'C54:NEW': 'Yeni',
    'C54:PREPARATION': 'Hazırlık',
    'C54:WON': 'Kazanıldı',
    'C54:LOSE': 'Kaybedildi',
    'C54:UC_4Q99X9': 'İşlemde',
    # C56
    'C56:NEW': 'Yeni',
    'C56:PREPARATION': 'Hazırlık',
    'C56:UC_I1DOSH': 'İşlemde',
    # C58
    'C58:NEW': 'Yeni',
    'C58:PREPARATION': 'Hazırlık',
    'C58:PREPAYMENT_INVOIC': 'Ön Ödeme',
    'C58:EXECUTING': 'Yürütülüyor',
    'C58:LOSE': 'Kaybedildi',
    # C62
    'C62:NEW': 'Yeni',
    'C62:PREPARATION': 'Hazırlık',
    'C62:UC_TXHSGH': 'İşlemde',
    'C62:UC_A6EJVT': 'Değerlendirme',
    'C62:UC_HDI55O': 'Tamamlandı',
    # C64
    'C64:WON': 'Kazanıldı',
    'C64:LOSE': 'Kaybedildi',
    'C64:UC_02XUXE': 'İşlemde',
    'C64:UC_EKNJCK': 'Değerlendirme',
    'C64:UC_GCG8B9': 'Onay Bekliyor',
    'C64:UC_1PMEJU': 'Tamamlanıyor',
    'C64:UC_WV6G6Y': 'Kontrol',
    'C64:UC_H1126A': 'Son Aşama',
    # C66
    'C66:NEW': 'Yeni',
    'C66:PREPARATION': 'Hazırlık',
    'C66:WON': 'Kazanıldı',
    'C66:UC_SAT170': 'Satış Aşaması',
    # Diğer özel aşamalar
    'UC_12IFQ1': 'Aktif Takip',
    'UC_4WC54T': 'Fırsat',
    'UC_UFWXIW': 'Potansiyel',
    'UC_32QCCC': 'Değerlendirme',
    'UC_N1HRJX': 'Yeni Fırsat',
    'UC_IZZTCF': 'İletişim',
    'UC_P2WVHX': 'Takip',
}

def get_stage_name(stage_id: str) -> str:
    """Convert stage ID to human-readable name"""
    if not stage_id:
        return 'Bilinmeyen'
    
    # Direct match
    if stage_id in STAGE_NAME_MAP:
        return STAGE_NAME_MAP[stage_id]
    
    # Try to parse and create readable name
    if ':' in stage_id:
        parts = stage_id.split(':')
        prefix = parts[0]
        suffix = parts[1] if len(parts) > 1 else ''
        
        # Check if suffix is a known stage
        if suffix in STAGE_NAME_MAP:
            return STAGE_NAME_MAP[suffix]
        
        # Check with prefix
        if suffix.startswith('UC_'):
            return f'Özel Aşama ({prefix})'
        
        return suffix if suffix else stage_id
    
    return stage_id


# Category ID to Name mapping
CATEGORY_NAME_MAP = {
    '0': 'Genel',
    '24': 'Satış Yönetimi',
    '26': 'Müşteri İlişkileri',
    '30': 'Proje Yönetimi',
    '32': 'Servis',
    '36': 'Tedarik Yönetimi',
    '40': 'Finans',
    '42': 'İnsan Kaynakları',
    '44': 'Pazarlama',
    '46': 'Destek',
    '48': 'İş Geliştirme',
    '50': 'Operasyon',
    '52': 'Gayrimenkul',
    '54': 'İnşaat',
    '56': 'Mühendislik',
    '58': 'Lojistik',
    '62': 'Kalite Kontrol',
    '64': 'Satın Alma',
    '66': 'Üretim',
}

def get_category_name(category_id: str) -> str:
    """Get human-readable category name"""
    if not category_id:
        return 'Belirsiz'
    return CATEGORY_NAME_MAP.get(category_id, f'Kategori {category_id}')


@router.get("/categories")
async def get_deal_categories(
    status: Optional[str] = Query(default="active", description="Filter: 'active', 'won', 'lost', 'all'"),
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Get available deal categories (pipelines) for filtering
    """
    try:
        # Build status condition
        status_condition = ""
        if status == "active":
            status_condition = "AND stage_id NOT LIKE '%LOSE%' AND stage_id NOT LIKE '%WON%'"
        elif status == "won":
            status_condition = "AND stage_id LIKE '%WON%'"
        elif status == "lost":
            status_condition = "AND stage_id LIKE '%LOSE%'"
        
        query = text(f"""
            SELECT DISTINCT 
                category_id,
                COUNT(*) as deal_count
            FROM bitrix.deals
            WHERE category_id IS NOT NULL {status_condition}
            GROUP BY category_id
            ORDER BY deal_count DESC
        """)
        
        result = await db.execute(query)
        categories_raw = [dict(row._mapping) for row in result.fetchall()]
        
        # Add category_name to each category
        categories = []
        for cat in categories_raw:
            cat['category_name'] = get_category_name(cat.get('category_id'))
            categories.append(cat)
        
        return categories
        
    except Exception as e:
        logger.error("get_deal_categories_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/deals")
async def list_deals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    search: Optional[str] = Query(default=None),
    category_id: Optional[str] = Query(default=None, description="Filter by category/pipeline"),
    stage_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="active", description="Filter: 'active', 'won', 'lost', 'all'"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    List deals with summary status
    Status filter:
    - active: Exclude WON and LOSE stages (default)
    - won: Only WON stages
    - lost: Only LOSE stages
    - all: All deals
    """
    try:
        offset = (page - 1) * page_size
        
        # Build query
        conditions = []
        params = {"limit": page_size, "offset": offset}
        
        if search:
            conditions.append("d.title ILIKE :search")
            params["search"] = f"%{search}%"
        
        if category_id:
            conditions.append("d.category_id = :category_id")
            params["category_id"] = category_id
        
        if stage_id:
            conditions.append("d.stage_id = :stage_id")
            params["stage_id"] = stage_id
        
        # Status filter
        if status == "active":
            conditions.append("d.stage_id NOT LIKE '%LOSE%' AND d.stage_id NOT LIKE '%WON%'")
        elif status == "won":
            conditions.append("d.stage_id LIKE '%WON%'")
        elif status == "lost":
            conditions.append("d.stage_id LIKE '%LOSE%'")
        # status == "all" -> no filter
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get deals with contact/company names - using direct columns
        query = text(f"""
            SELECT 
                d.id,
                d.title,
                d.stage_id,
                d.opportunity,
                d.currency_id as currency,
                d.date_create,
                d.date_modify,
                COALESCE(c.full_name, CONCAT(c.name, ' ', c.last_name)) as contact_name,
                comp.title as company_name,
                CONCAT(u.name, ' ', u.last_name) as assigned_by_name,
                CASE WHEN s.id IS NOT NULL THEN true ELSE false END as has_summary,
                s.created_at as last_summary_at
            FROM bitrix.deals d
            LEFT JOIN bitrix.contacts c ON d.contact_id = c.bitrix_id
            LEFT JOIN bitrix.companies comp ON d.company_id = comp.bitrix_id
            LEFT JOIN bitrix.users u ON d.assigned_by_id::int = u.id
            LEFT JOIN LATERAL (
                SELECT id, created_at 
                FROM bitrix.ai_summaries 
                WHERE deal_id = d.id 
                ORDER BY created_at DESC 
                LIMIT 1
            ) s ON true
            WHERE {where_clause}
            ORDER BY d.date_modify DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(query, params)
        deals_raw = [dict(row._mapping) for row in result.fetchall()]
        
        # Add stage_name to each deal
        deals = []
        for deal in deals_raw:
            deal['stage_name'] = get_stage_name(deal.get('stage_id'))
            deals.append(deal)
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) FROM bitrix.deals d WHERE {where_clause}
        """)
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
        count_result = await db.execute(count_query, count_params)
        total = count_result.scalar()
        
        return {
            "items": deals,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error("list_deals_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/deals/{deal_id}")
async def get_deal_details(
    deal_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get detailed deal information including related data counts
    Enhanced: Returns all deals for the contact, contact type name, stage names
    """
    try:
        collector = CustomerDataCollector(db)
        data = await collector.collect_all_data(deal_id)
        
        all_contact_deals = data.get("all_contact_deals", [])
        
        return {
            "deal": data["deal"],
            "contact": data["contact"],
            "company": data["company"],
            "responsible_name": data["responsible_name"],
            "all_contact_deals": all_contact_deals,
            "stats": {
                "activities_count": len(data["activities"]),
                "tasks_count": len(data["tasks"]),
                "task_comments_count": len(data["task_comments"]),
                "total_deals_count": len(all_contact_deals)
            },
            "recent_activities": data["activities"][:10],
            "recent_tasks": data["tasks"][:10]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("get_deal_details_failed", deal_id=deal_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate")
async def generate_summary(
    request: GenerateSummaryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> SummaryResponse:
    """
    Generate AI summary for a deal
    """
    try:
        # Collect customer data
        collector = CustomerDataCollector(db)
        customer_data = await collector.collect_all_data(request.deal_id)
        
        # Map provider enum
        provider_map = {
            AIProviderEnum.openai: AIProvider.OPENAI,
            AIProviderEnum.claude: AIProvider.CLAUDE,
            AIProviderEnum.gemini: AIProvider.GEMINI,
            AIProviderEnum.openrouter: AIProvider.OPENROUTER,
            AIProviderEnum.ollama: AIProvider.OLLAMA
        }
        
        # Generate summary
        summarizer = AISummarizer(
            provider=provider_map[request.provider],
            model=request.model
        )
        
        summary_text = await summarizer.generate_summary(customer_data)
        
        # Save to database
        insert_query = text("""
            INSERT INTO bitrix.ai_summaries 
            (deal_id, deal_title, summary, provider, model, created_at, written_to_bitrix)
            VALUES (:deal_id, :deal_title, :summary, :provider, :model, NOW(), false)
            RETURNING id, created_at
        """)
        
        result = await db.execute(insert_query, {
            "deal_id": request.deal_id,
            "deal_title": customer_data["deal"].get("title", ""),
            "summary": summary_text,
            "provider": request.provider.value,
            "model": request.model or summarizer.model
        })
        await db.commit()
        
        row = result.fetchone()
        summary_id = row.id
        created_at = row.created_at
        
        # Write to Bitrix24 if requested
        bitrix_result = None
        if request.write_to_bitrix:
            writer = BitrixSummaryWriter()
            
            if request.write_mode == "timeline":
                bitrix_result = await writer.add_deal_timeline_comment(
                    request.deal_id, 
                    summary_text
                )
            else:
                bitrix_result = await writer.update_deal_comment(
                    request.deal_id, 
                    summary_text
                )
            
            # Update database
            if bitrix_result.get("success"):
                await db.execute(
                    text("UPDATE bitrix.ai_summaries SET written_to_bitrix = true WHERE id = :id"),
                    {"id": summary_id}
                )
                await db.commit()
        
        logger.info(
            "summary_generated",
            deal_id=request.deal_id,
            summary_id=summary_id,
            provider=request.provider.value,
            written_to_bitrix=request.write_to_bitrix
        )
        
        return SummaryResponse(
            id=summary_id,
            deal_id=request.deal_id,
            deal_title=customer_data["deal"].get("title"),
            summary=summary_text,
            provider=request.provider.value,
            model=request.model or summarizer.model,
            created_at=created_at,
            written_to_bitrix=bitrix_result.get("success", False) if bitrix_result else False,
            bitrix_write_result=bitrix_result
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("generate_summary_failed", deal_id=request.deal_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/history")
async def get_summary_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    deal_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get summary generation history
    """
    try:
        offset = (page - 1) * page_size
        
        conditions = []
        params = {"limit": page_size, "offset": offset}
        
        if deal_id:
            conditions.append("deal_id = :deal_id")
            params["deal_id"] = deal_id
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = text(f"""
            SELECT 
                id,
                deal_id,
                deal_title,
                LEFT(summary, 200) as summary_preview,
                provider,
                model,
                created_at,
                written_to_bitrix
            FROM bitrix.ai_summaries
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(query, params)
        items = [dict(row._mapping) for row in result.fetchall()]
        
        # Get total count
        count_query = text(f"SELECT COUNT(*) FROM bitrix.ai_summaries WHERE {where_clause}")
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
        count_result = await db.execute(count_query, count_params)
        total = count_result.scalar()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error("get_summary_history_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/history/{summary_id}")
async def get_summary_detail(
    summary_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get full summary detail
    """
    try:
        query = text("""
            SELECT 
                id,
                deal_id,
                deal_title,
                summary,
                provider,
                model,
                created_at,
                written_to_bitrix
            FROM bitrix.ai_summaries
            WHERE id = :summary_id
        """)
        
        result = await db.execute(query, {"summary_id": summary_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Summary {summary_id} not found"
            )
        
        return dict(row._mapping)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_summary_detail_failed", summary_id=summary_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/write-to-bitrix")
async def write_summary_to_bitrix(
    request: WriteToBitrixRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Write an existing summary to Bitrix24
    """
    try:
        # Get summary
        query = text("""
            SELECT deal_id, summary 
            FROM bitrix.ai_summaries 
            WHERE id = :summary_id
        """)
        result = await db.execute(query, {"summary_id": request.summary_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Summary {request.summary_id} not found"
            )
        
        deal_id = row.deal_id
        summary = row.summary
        
        # Write to Bitrix24
        writer = BitrixSummaryWriter()
        
        if request.write_mode == "timeline":
            bitrix_result = await writer.add_deal_timeline_comment(deal_id, summary)
        else:
            bitrix_result = await writer.update_deal_comment(deal_id, summary)
        
        # Update database
        if bitrix_result.get("success"):
            await db.execute(
                text("UPDATE bitrix.ai_summaries SET written_to_bitrix = true WHERE id = :id"),
                {"id": request.summary_id}
            )
            await db.commit()
        
        return bitrix_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("write_to_bitrix_failed", summary_id=request.summary_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/history/{summary_id}")
async def delete_summary(
    summary_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete a summary from history
    """
    try:
        query = text("DELETE FROM bitrix.ai_summaries WHERE id = :summary_id RETURNING id")
        result = await db.execute(query, {"summary_id": summary_id})
        await db.commit()
        
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Summary {summary_id} not found"
            )
        
        return {"success": True, "deleted_id": summary_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_summary_failed", summary_id=summary_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stages")
async def get_deal_stages(
    status: Optional[str] = Query(default="active", description="Filter: 'active', 'won', 'lost', 'all'"),
    category_id: Optional[str] = Query(default=None, description="Filter by category/pipeline"),
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Get available deal stages for filtering
    """
    try:
        # Build conditions
        conditions = ["stage_id IS NOT NULL"]
        
        if status == "active":
            conditions.append("stage_id NOT LIKE '%LOSE%' AND stage_id NOT LIKE '%WON%'")
        elif status == "won":
            conditions.append("stage_id LIKE '%WON%'")
        elif status == "lost":
            conditions.append("stage_id LIKE '%LOSE%'")
        
        if category_id:
            conditions.append(f"category_id = '{category_id}'")
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT DISTINCT 
                stage_id,
                COUNT(*) as deal_count
            FROM bitrix.deals
            WHERE {where_clause}
            GROUP BY stage_id
            ORDER BY deal_count DESC
        """)
        
        result = await db.execute(query)
        stages_raw = [dict(row._mapping) for row in result.fetchall()]
        
        # Add stage_name to each stage
        stages = []
        for stage in stages_raw:
            stage['stage_name'] = get_stage_name(stage.get('stage_id'))
            stages.append(stage)
        
        return stages
        
    except Exception as e:
        logger.error("get_deal_stages_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
