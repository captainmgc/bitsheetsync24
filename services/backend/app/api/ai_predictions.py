"""
AI Predictions API Endpoints
Provides sales predictions, deal scoring, and risk analysis

Endpoints:
- GET /predictions/deal/{deal_id} - Get prediction for a single deal
- GET /predictions/batch - Get predictions for multiple deals
- GET /predictions/at-risk - Get deals at risk
- POST /predictions/ai-insight/{deal_id} - Get AI-enhanced insight
- GET /predictions/dashboard - Get prediction dashboard summary
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.database import get_db
from app.services.ai_predictions import (
    SalesPredictionService,
    AIEnhancedPrediction,
    DealScore,
    RiskLevel,
    CustomerSegmentationService,
    CustomerSegment
)

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class RiskLevelEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ScoreBreakdown(BaseModel):
    """Score breakdown by category"""
    stage: float = Field(..., description="Stage score (0-25)")
    activity: float = Field(..., description="Activity score (0-20)")
    recency: float = Field(..., description="Recency score (0-15)")
    amount: float = Field(..., description="Amount score (0-15)")
    velocity: float = Field(..., description="Velocity score (0-15)")
    engagement: float = Field(..., description="Engagement score (0-10)")


class DealPredictionResponse(BaseModel):
    """Response for deal prediction"""
    deal_id: int
    total_score: float = Field(..., description="Total score (0-100)")
    win_probability: float = Field(..., description="Win probability percentage")
    risk_level: RiskLevelEnum
    breakdown: ScoreBreakdown
    positive_factors: List[str]
    negative_factors: List[str]
    recommendations: List[str]
    calculated_at: str


class BatchPredictionResponse(BaseModel):
    """Response for batch predictions"""
    total_deals: int
    predictions: List[DealPredictionResponse]
    avg_win_probability: float
    risk_distribution: dict


class AIInsightRequest(BaseModel):
    """Request for AI-enhanced insight"""
    provider: str = Field(default="openai", description="AI provider (openai, claude, ollama)")
    model: str = Field(default="gpt-4o-mini", description="AI model to use")


class AIInsightResponse(BaseModel):
    """Response for AI-enhanced insight"""
    deal_id: int
    deal_title: Optional[str]
    score: dict
    positive_factors: List[str]
    negative_factors: List[str]
    recommendations: List[str]
    ai_insight: str
    calculated_at: str


class PredictionDashboardResponse(BaseModel):
    """Dashboard summary response"""
    total_active_deals: int
    avg_win_probability: float
    high_probability_deals: int  # >70%
    at_risk_deals: int
    critical_deals: int
    top_opportunities: List[dict]
    needs_attention: List[dict]
    risk_distribution: dict
    stage_performance: List[dict]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def score_to_response(score: DealScore) -> DealPredictionResponse:
    """Convert DealScore to API response"""
    return DealPredictionResponse(
        deal_id=score.deal_id,
        total_score=round(score.total_score, 1),
        win_probability=round(score.win_probability, 1),
        risk_level=RiskLevelEnum(score.risk_level.value),
        breakdown=ScoreBreakdown(
            stage=round(score.stage_score, 1),
            activity=round(score.activity_score, 1),
            recency=round(score.recency_score, 1),
            amount=round(score.amount_score, 1),
            velocity=round(score.velocity_score, 1),
            engagement=round(score.engagement_score, 1)
        ),
        positive_factors=score.positive_factors,
        negative_factors=score.negative_factors,
        recommendations=score.recommendations,
        calculated_at=score.calculated_at.isoformat()
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/deal/{deal_id}", response_model=DealPredictionResponse)
async def get_deal_prediction(
    deal_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get prediction for a single deal
    
    Returns:
    - Win probability (0-100%)
    - Total score (0-100)
    - Risk level (low, medium, high, critical)
    - Score breakdown by category
    - Positive and negative factors
    - Actionable recommendations
    """
    try:
        service = SalesPredictionService(db)
        score = await service.calculate_deal_score(deal_id)
        
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anlaşma bulunamadı: {deal_id}"
            )
        
        return score_to_response(score)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("prediction_error", deal_id=deal_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tahmin hesaplanırken hata: {str(e)}"
        )


@router.get("/batch", response_model=BatchPredictionResponse)
async def get_batch_predictions(
    limit: int = Query(default=50, le=100, description="Maximum deals to analyze"),
    stage_filter: Optional[str] = Query(default=None, description="Filter by stage"),
    min_amount: Optional[float] = Query(default=None, description="Minimum deal amount"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get predictions for multiple deals
    
    Filters:
    - stage_filter: Only analyze deals in specific stage
    - min_amount: Only analyze deals above certain amount
    
    Returns sorted by win probability (highest first)
    """
    try:
        service = SalesPredictionService(db)
        scores = await service.get_batch_predictions(
            limit=limit,
            stage_filter=stage_filter,
            min_amount=min_amount
        )
        
        if not scores:
            return BatchPredictionResponse(
                total_deals=0,
                predictions=[],
                avg_win_probability=0,
                risk_distribution={"low": 0, "medium": 0, "high": 0, "critical": 0}
            )
        
        predictions = [score_to_response(s) for s in scores]
        avg_prob = sum(s.win_probability for s in scores) / len(scores)
        
        # Calculate risk distribution
        risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for s in scores:
            risk_dist[s.risk_level.value] += 1
        
        return BatchPredictionResponse(
            total_deals=len(predictions),
            predictions=predictions,
            avg_win_probability=round(avg_prob, 1),
            risk_distribution=risk_dist
        )
        
    except Exception as e:
        logger.error("batch_prediction_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Toplu tahmin hesaplanırken hata: {str(e)}"
        )


@router.get("/at-risk")
async def get_at_risk_deals(
    threshold: float = Query(default=40, description="Win probability threshold"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get deals at risk (low win probability or high risk level)
    
    Returns deals that need immediate attention
    """
    try:
        service = SalesPredictionService(db)
        at_risk = await service.get_at_risk_deals(threshold=threshold)
        
        return {
            "total_at_risk": len(at_risk),
            "threshold": threshold,
            "deals": [
                {
                    "deal_id": s.deal_id,
                    "win_probability": round(s.win_probability, 1),
                    "risk_level": s.risk_level.value,
                    "negative_factors": s.negative_factors,
                    "recommendations": s.recommendations[:2]  # Top 2 recommendations
                }
                for s in at_risk
            ]
        }
        
    except Exception as e:
        logger.error("at_risk_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk analizi yapılırken hata: {str(e)}"
        )


@router.post("/ai-insight/{deal_id}", response_model=AIInsightResponse)
async def get_ai_insight(
    deal_id: int,
    request: AIInsightRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-enhanced insight for a deal
    
    Uses AI to generate natural language analysis and recommendations
    """
    if request is None:
        request = AIInsightRequest()
    
    try:
        service = AIEnhancedPrediction(db)
        result = await service.generate_ai_insight(
            deal_id=deal_id,
            provider=request.provider,
            model=request.model
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return AIInsightResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ai_insight_error", deal_id=deal_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analizi yapılırken hata: {str(e)}"
        )


@router.get("/dashboard", response_model=PredictionDashboardResponse)
async def get_prediction_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Get prediction dashboard summary
    
    Returns overview of all deal predictions for dashboard display
    """
    try:
        service = SalesPredictionService(db)
        
        # Get all predictions
        all_scores = await service.get_batch_predictions(limit=100)
        
        if not all_scores:
            return PredictionDashboardResponse(
                total_active_deals=0,
                avg_win_probability=0,
                high_probability_deals=0,
                at_risk_deals=0,
                critical_deals=0,
                top_opportunities=[],
                needs_attention=[],
                risk_distribution={"low": 0, "medium": 0, "high": 0, "critical": 0},
                stage_performance=[]
            )
        
        # Calculate metrics
        avg_prob = sum(s.win_probability for s in all_scores) / len(all_scores)
        high_prob = len([s for s in all_scores if s.win_probability >= 70])
        at_risk = len([s for s in all_scores if s.win_probability < 40])
        critical = len([s for s in all_scores if s.risk_level == RiskLevel.CRITICAL])
        
        # Risk distribution
        risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for s in all_scores:
            risk_dist[s.risk_level.value] += 1
        
        # Top opportunities (highest probability)
        top_opps = sorted(all_scores, key=lambda x: x.win_probability, reverse=True)[:5]
        top_opportunities = [
            {
                "deal_id": s.deal_id,
                "win_probability": round(s.win_probability, 1),
                "total_score": round(s.total_score, 1),
                "positive_factors": s.positive_factors[:2]
            }
            for s in top_opps
        ]
        
        # Needs attention (critical or high risk)
        needs_attn = [s for s in all_scores if s.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]][:5]
        needs_attention = [
            {
                "deal_id": s.deal_id,
                "win_probability": round(s.win_probability, 1),
                "risk_level": s.risk_level.value,
                "negative_factors": s.negative_factors[:2],
                "top_recommendation": s.recommendations[0] if s.recommendations else None
            }
            for s in needs_attn
        ]
        
        # Stage performance (group by stage score ranges)
        stage_groups = {
            "Erken Aşama (0-25%)": [],
            "Orta Aşama (25-50%)": [],
            "İleri Aşama (50-75%)": [],
            "Son Aşama (75-100%)": []
        }
        for s in all_scores:
            stage_pct = (s.stage_score / 25) * 100
            if stage_pct < 25:
                stage_groups["Erken Aşama (0-25%)"].append(s)
            elif stage_pct < 50:
                stage_groups["Orta Aşama (25-50%)"].append(s)
            elif stage_pct < 75:
                stage_groups["İleri Aşama (50-75%)"].append(s)
            else:
                stage_groups["Son Aşama (75-100%)"].append(s)
        
        stage_performance = [
            {
                "stage": name,
                "count": len(deals),
                "avg_probability": round(sum(d.win_probability for d in deals) / len(deals), 1) if deals else 0
            }
            for name, deals in stage_groups.items()
        ]
        
        return PredictionDashboardResponse(
            total_active_deals=len(all_scores),
            avg_win_probability=round(avg_prob, 1),
            high_probability_deals=high_prob,
            at_risk_deals=at_risk,
            critical_deals=critical,
            top_opportunities=top_opportunities,
            needs_attention=needs_attention,
            risk_distribution=risk_dist,
            stage_performance=stage_performance
        )
        
    except Exception as e:
        logger.error("dashboard_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard verisi alınırken hata: {str(e)}"
        )


# ============================================================================
# CUSTOMER SEGMENTATION ENDPOINTS
# ============================================================================

class CustomerSegmentEnum(str, Enum):
    vip = "vip"
    high_value = "high_value"
    regular = "regular"
    new = "new"
    at_risk = "at_risk"
    cold = "cold"


class CustomerProfileResponse(BaseModel):
    """Response for customer profile"""
    contact_id: int
    segment: CustomerSegmentEnum
    segment_label: str
    lifetime_value: float
    total_deals: int
    won_deals: int
    lost_deals: int
    active_deals: int
    avg_deal_value: float
    days_since_last_activity: int
    engagement_level: str
    churn_risk: float
    recommendations: List[str]


class SegmentationOverviewResponse(BaseModel):
    """Response for segmentation overview"""
    total_customers: int
    segment_distribution: dict
    total_lifetime_value: float
    avg_lifetime_value: float
    customers: List[dict]


SEGMENT_LABELS = {
    "vip": "💎 VIP",
    "high_value": "⭐ Yüksek Değer",
    "regular": "👤 Standart",
    "new": "🆕 Yeni",
    "at_risk": "⚠️ Risk Altında",
    "cold": "❄️ Soğuk"
}


@router.get("/segments/overview", response_model=SegmentationOverviewResponse)
async def get_segmentation_overview(
    limit: int = Query(default=100, le=500, description="Maximum customers to analyze"),
    segment: Optional[CustomerSegmentEnum] = Query(default=None, description="Filter by segment"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer segmentation overview
    
    Returns distribution of customers across segments with detailed profiles
    """
    try:
        service = CustomerSegmentationService(db)
        
        segment_filter = None
        if segment:
            segment_filter = CustomerSegment(segment.value)
        
        result = await service.get_all_customer_segments(
            limit=limit,
            segment_filter=segment_filter
        )
        
        return SegmentationOverviewResponse(**result)
        
    except Exception as e:
        logger.error("segmentation_overview_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Segmentasyon verisi alınırken hata: {str(e)}"
        )


@router.get("/segments/customer/{contact_id}", response_model=CustomerProfileResponse)
async def get_customer_profile(
    contact_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed customer profile with segmentation
    
    Returns:
    - Customer segment (VIP, High Value, Regular, New, At Risk, Cold)
    - Lifetime value and deal statistics
    - Engagement level and churn risk
    - Personalized recommendations
    """
    try:
        service = CustomerSegmentationService(db)
        profile = await service.get_contact_profile(contact_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Müşteri bulunamadı: {contact_id}"
            )
        
        # Get recommendations for this segment
        recommendations = await service.get_segment_recommendations(profile.segment)
        
        return CustomerProfileResponse(
            contact_id=profile.contact_id,
            segment=CustomerSegmentEnum(profile.segment.value),
            segment_label=SEGMENT_LABELS.get(profile.segment.value, profile.segment.value),
            lifetime_value=profile.lifetime_value,
            total_deals=profile.total_deals,
            won_deals=profile.won_deals,
            lost_deals=profile.lost_deals,
            active_deals=profile.active_deals,
            avg_deal_value=profile.avg_deal_value or 0,
            days_since_last_activity=profile.days_since_last_activity,
            engagement_level=profile.engagement_level,
            churn_risk=profile.churn_risk,
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("customer_profile_error", contact_id=contact_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Müşteri profili alınırken hata: {str(e)}"
        )


@router.get("/segments/recommendations/{segment}")
async def get_segment_recommendations(
    segment: CustomerSegmentEnum,
    db: AsyncSession = Depends(get_db)
):
    """
    Get action recommendations for a customer segment
    """
    try:
        service = CustomerSegmentationService(db)
        segment_enum = CustomerSegment(segment.value)
        recommendations = await service.get_segment_recommendations(segment_enum)
        
        return {
            "segment": segment.value,
            "segment_label": SEGMENT_LABELS.get(segment.value, segment.value),
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error("segment_recommendations_error", segment=segment, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Öneriler alınırken hata: {str(e)}"
        )
