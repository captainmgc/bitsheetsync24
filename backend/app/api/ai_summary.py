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
    
    # OpenRouter (multi-model gateway)
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.openrouter,
        api_key_configured=bool(openrouter_key),
        available_models=[
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "google/gemini-pro-1.5",
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-70b-instruct",
            "meta-llama/llama-3.1-8b-instruct",
            "mistralai/mixtral-8x7b-instruct",
            "deepseek/deepseek-chat"
        ],
        default_model="openai/gpt-4o-mini"
    ))
    
    # Ollama (local)
    providers.append(AIProviderConfig(
        provider=AIProviderEnum.ollama,
        api_key_configured=True,  # No key needed for local
        available_models=["llama3.2", "llama3.1", "mistral", "mixtral"],
        default_model="llama3.2"
    ))
    
    return providers


@router.get("/deals")
async def list_deals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    search: Optional[str] = Query(default=None),
    stage_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    List deals with summary status
    """
    try:
        offset = (page - 1) * page_size
        
        # Build query
        conditions = []
        params = {"limit": page_size, "offset": offset}
        
        if search:
            conditions.append("d.data->>'TITLE' ILIKE :search")
            params["search"] = f"%{search}%"
        
        if stage_id:
            conditions.append("d.data->>'STAGE_ID' = :stage_id")
            params["stage_id"] = stage_id
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get deals with contact/company names
        query = text(f"""
            SELECT 
                d.id,
                d.data->>'TITLE' as title,
                d.data->>'STAGE_ID' as stage_id,
                d.data->>'OPPORTUNITY' as opportunity,
                d.data->>'CURRENCY_ID' as currency,
                d.data->>'DATE_CREATE' as date_create,
                d.data->>'DATE_MODIFY' as date_modify,
                CONCAT(c.data->>'NAME', ' ', c.data->>'LAST_NAME') as contact_name,
                comp.data->>'TITLE' as company_name,
                CONCAT(u.data->>'NAME', ' ', u.data->>'LAST_NAME') as assigned_by_name,
                CASE WHEN s.id IS NOT NULL THEN true ELSE false END as has_summary,
                s.created_at as last_summary_at
            FROM bitrix.deals d
            LEFT JOIN bitrix.contacts c ON (d.data->>'CONTACT_ID')::int = c.id
            LEFT JOIN bitrix.companies comp ON (d.data->>'COMPANY_ID')::int = comp.id
            LEFT JOIN bitrix.users u ON (d.data->>'ASSIGNED_BY_ID')::int = u.id
            LEFT JOIN LATERAL (
                SELECT id, created_at 
                FROM bitrix.ai_summaries 
                WHERE deal_id = d.id 
                ORDER BY created_at DESC 
                LIMIT 1
            ) s ON true
            WHERE {where_clause}
            ORDER BY d.data->>'DATE_MODIFY' DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(query, params)
        deals = [dict(row._mapping) for row in result.fetchall()]
        
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
    """
    try:
        collector = CustomerDataCollector(db)
        data = await collector.collect_all_data(deal_id)
        
        return {
            "deal": data["deal"],
            "contact": data["contact"],
            "company": data["company"],
            "responsible_name": data["responsible_name"],
            "stats": {
                "activities_count": len(data["activities"]),
                "tasks_count": len(data["tasks"]),
                "task_comments_count": len(data["task_comments"])
            },
            "recent_activities": data["activities"][:5],
            "recent_tasks": data["tasks"][:5]
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
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Get available deal stages for filtering
    """
    try:
        query = text("""
            SELECT DISTINCT 
                data->>'STAGE_ID' as stage_id,
                COUNT(*) as deal_count
            FROM bitrix.deals
            WHERE data->>'STAGE_ID' IS NOT NULL
            GROUP BY data->>'STAGE_ID'
            ORDER BY deal_count DESC
        """)
        
        result = await db.execute(query)
        return [dict(row._mapping) for row in result.fetchall()]
        
    except Exception as e:
        logger.error("get_deal_stages_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
