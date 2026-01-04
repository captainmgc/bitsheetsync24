"""
AI Sales Prediction Service
Analyzes deal data to predict win probability and provide intelligent recommendations

Features:
- Win probability calculation based on historical data
- Deal scoring with multiple factors
- Risk assessment
- Next action recommendations
- Customer segmentation
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import structlog
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from app.config import settings

logger = structlog.get_logger()


class RiskLevel(str, Enum):
    """Risk levels for deals"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CustomerSegment(str, Enum):
    """Customer segments"""
    VIP = "vip"
    HIGH_VALUE = "high_value"
    REGULAR = "regular"
    NEW = "new"
    AT_RISK = "at_risk"
    COLD = "cold"


@dataclass
class DealScore:
    """Comprehensive deal score with breakdown"""
    deal_id: int
    total_score: float  # 0-100
    win_probability: float  # 0-100%
    risk_level: RiskLevel
    
    # Score breakdown
    stage_score: float = 0.0
    activity_score: float = 0.0
    recency_score: float = 0.0
    amount_score: float = 0.0
    velocity_score: float = 0.0
    engagement_score: float = 0.0
    
    # Factors
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CustomerProfile:
    """Customer profile with segmentation"""
    contact_id: int
    segment: CustomerSegment
    lifetime_value: float
    total_deals: int
    won_deals: int
    lost_deals: int
    active_deals: int
    avg_deal_value: float
    days_since_last_activity: int
    engagement_level: str  # high, medium, low
    churn_risk: float  # 0-100%


class DealAnalyzer:
    """
    Analyzes deal data from PostgreSQL to calculate predictions
    """
    
    # Stage progression weights (higher = closer to win)
    STAGE_WEIGHTS = {
        "NEW": 10,
        "PREPARATION": 20,
        "PREPAYMENT_INVOICE": 30,
        "EXECUTING": 50,
        "FINAL_INVOICE": 70,
        "WON": 100,
        "LOSE": 0,
        "APOLOGY": 0,
        # C prefixed stages (custom)
        "C1": 10, "C2": 20, "C3": 30, "C4": 40, "C5": 50,
        "C6": 60, "C7": 70, "C8": 80, "C9": 90,
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_deal_with_context(self, deal_id: int) -> Optional[Dict[str, Any]]:
        """Get deal with all related context"""
        query = text("""
            SELECT 
                d.id,
                d.title,
                d.stage_id,
                d.opportunity,
                d.currency_id as currency,
                d.date_create,
                d.date_modify,
                d.closedate as close_date,
                d.assigned_by_id,
                d.contact_id,
                d.company_id,
                d.probability,
                d.source_id,
                d.begindate as begin_date,
                d.original_data as raw_data
            FROM bitrix.deals d
            WHERE d.id = :deal_id
        """)
        result = await self.db.execute(query, {"deal_id": deal_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None
    
    async def get_deal_activities_count(self, deal_id: int) -> Dict[str, int]:
        """Get activity counts for a deal"""
        query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN COALESCE(a.data->>'COMPLETED', 'N') = 'Y' THEN 1 END) as completed,
                COUNT(CASE WHEN a.type_id = '2' THEN 1 END) as calls,
                COUNT(CASE WHEN a.type_id = '1' THEN 1 END) as emails,
                COUNT(CASE WHEN a.type_id = '3' THEN 1 END) as meetings,
                MAX(a.created) as last_activity_date
            FROM bitrix.activities a
            WHERE a.owner_id = :deal_id 
              AND a.owner_type_id = '2'
        """)
        result = await self.db.execute(query, {"deal_id": str(deal_id)})
        row = result.fetchone()
        if row:
            return {
                "total": row.total or 0,
                "completed": row.completed or 0,
                "calls": row.calls or 0,
                "emails": row.emails or 0,
                "meetings": row.meetings or 0,
                "last_activity_date": row.last_activity_date
            }
        return {"total": 0, "completed": 0, "calls": 0, "emails": 0, "meetings": 0, "last_activity_date": None}
    
    async def get_deal_tasks_count(self, deal_id: int) -> Dict[str, int]:
        """Get task counts for a deal"""
        query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN t.status = 5 THEN 1 END) as completed,
                COUNT(CASE WHEN t.status IN (1, 2, 3) THEN 1 END) as pending,
                COUNT(CASE WHEN t.deadline < NOW() 
                           AND t.status NOT IN (5, 6) THEN 1 END) as overdue
            FROM bitrix.tasks t
            WHERE t.original_data IS NOT NULL 
              AND t.original_data->>'UF_CRM_TASK' LIKE :deal_pattern
        """)
        result = await self.db.execute(query, {"deal_pattern": f"%D_{deal_id}%"})
        row = result.fetchone()
        if row:
            return {
                "total": row.total or 0,
                "completed": row.completed or 0,
                "pending": row.pending or 0,
                "overdue": row.overdue or 0
            }
        return {"total": 0, "completed": 0, "pending": 0, "overdue": 0}
    
    async def get_historical_win_rate(self, stage_id: str = None) -> Dict[str, float]:
        """Calculate historical win rates"""
        query = text("""
            SELECT 
                COUNT(*) as total_closed,
                COUNT(CASE WHEN d.stage_id LIKE '%WON%' 
                           OR d.stage_id = 'WON' THEN 1 END) as won,
                AVG(d.opportunity) as avg_deal_value
            FROM bitrix.deals d
            WHERE d.stage_id LIKE '%WON%' 
               OR d.stage_id LIKE '%LOSE%'
               OR d.stage_id = 'WON'
               OR d.stage_id = 'LOSE'
        """)
        result = await self.db.execute(query)
        row = result.fetchone()
        
        if row and row.total_closed > 0:
            return {
                "overall_win_rate": float(row.won) / float(row.total_closed) * 100,
                "total_closed": int(row.total_closed),
                "avg_deal_value": float(row.avg_deal_value) if row.avg_deal_value else 0.0
            }
        return {"overall_win_rate": 50.0, "total_closed": 0, "avg_deal_value": 0.0}
    
    async def get_avg_deal_cycle(self) -> float:
        """Calculate average deal cycle in days"""
        query = text("""
            SELECT 
                AVG(
                    EXTRACT(EPOCH FROM (
                        d.date_modify - d.date_create
                    )) / 86400
                ) as avg_cycle_days
            FROM bitrix.deals d
            WHERE (d.stage_id LIKE '%WON%' OR d.stage_id = 'WON')
              AND d.date_create IS NOT NULL
              AND d.date_modify IS NOT NULL
        """)
        result = await self.db.execute(query)
        row = result.fetchone()
        return row.avg_cycle_days if row and row.avg_cycle_days else 30.0


class SalesPredictionService:
    """
    Main service for sales predictions and deal scoring
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analyzer = DealAnalyzer(db)
    
    async def calculate_deal_score(self, deal_id: int) -> Optional[DealScore]:
        """
        Calculate comprehensive deal score with win probability
        """
        # Get deal data
        deal = await self.analyzer.get_deal_with_context(deal_id)
        if not deal:
            logger.warning("deal_not_found", deal_id=deal_id)
            return None
        
        # Get related data
        activities = await self.analyzer.get_deal_activities_count(deal_id)
        tasks = await self.analyzer.get_deal_tasks_count(deal_id)
        historical = await self.analyzer.get_historical_win_rate()
        avg_cycle = await self.analyzer.get_avg_deal_cycle()
        
        # Initialize score
        score = DealScore(deal_id=deal_id, total_score=0, win_probability=0, risk_level=RiskLevel.MEDIUM)
        
        # 1. Stage Score (25 points max)
        stage_id = deal.get("stage_id", "NEW")
        stage_score = self._calculate_stage_score(stage_id)
        score.stage_score = stage_score
        
        # 2. Activity Score (20 points max)
        activity_score = self._calculate_activity_score(activities)
        score.activity_score = activity_score
        
        # 3. Recency Score (15 points max)
        recency_score, days_since = self._calculate_recency_score(
            deal.get("date_modify"), 
            activities.get("last_activity_date")
        )
        score.recency_score = recency_score
        
        # 4. Amount Score (15 points max)
        amount_score = self._calculate_amount_score(deal.get("opportunity"), historical.get("avg_deal_value", 0))
        score.amount_score = amount_score
        
        # 5. Velocity Score (15 points max)
        velocity_score = self._calculate_velocity_score(deal.get("date_create"), stage_id, avg_cycle)
        score.velocity_score = velocity_score
        
        # 6. Engagement Score (10 points max)
        engagement_score = self._calculate_engagement_score(activities, tasks)
        score.engagement_score = engagement_score
        
        # Calculate total score
        total = stage_score + activity_score + recency_score + amount_score + velocity_score + engagement_score
        score.total_score = min(100, max(0, total))
        
        # Calculate win probability
        score.win_probability = self._calculate_win_probability(score, historical)
        
        # Determine risk level
        score.risk_level = self._determine_risk_level(score, days_since, tasks.get("overdue", 0))
        
        # Generate factors and recommendations
        self._generate_factors(score, deal, activities, tasks, days_since)
        self._generate_recommendations(score, deal, activities, tasks, days_since)
        
        logger.info(
            "deal_score_calculated",
            deal_id=deal_id,
            total_score=score.total_score,
            win_probability=score.win_probability,
            risk_level=score.risk_level
        )
        
        return score
    
    def _calculate_stage_score(self, stage_id: str) -> float:
        """Calculate score based on deal stage (0-25 points)"""
        # Normalize stage_id
        stage_upper = stage_id.upper() if stage_id else "NEW"
        
        # Check for known stages
        for key, weight in DealAnalyzer.STAGE_WEIGHTS.items():
            if key in stage_upper:
                return (weight / 100) * 25
        
        # Try to extract stage number from patterns like "C6:NEW" or "C3:EXECUTING"
        match = re.search(r'C(\d+)', stage_upper)
        if match:
            stage_num = int(match.group(1))
            return min(25, (stage_num / 10) * 25)
        
        return 5  # Default low score for unknown stages
    
    def _calculate_activity_score(self, activities: Dict[str, int]) -> float:
        """Calculate score based on activities (0-20 points)"""
        total = activities.get("total", 0)
        calls = activities.get("calls", 0)
        meetings = activities.get("meetings", 0)
        
        # Base score from total activities
        base_score = min(10, total * 1)
        
        # Bonus for calls and meetings (more valuable)
        call_bonus = min(5, calls * 1.5)
        meeting_bonus = min(5, meetings * 2)
        
        return min(20, base_score + call_bonus + meeting_bonus)
    
    def _calculate_recency_score(self, date_modify: str, last_activity: str) -> tuple[float, int]:
        """Calculate score based on recency (0-15 points)"""
        now = datetime.utcnow()
        days_since = 999
        
        # Check last modification
        if date_modify:
            try:
                modify_date = datetime.fromisoformat(date_modify.replace("Z", "+00:00").replace("+00:00", ""))
                days_since = min(days_since, (now - modify_date).days)
            except:
                pass
        
        # Check last activity
        if last_activity:
            try:
                activity_date = datetime.fromisoformat(last_activity.replace("Z", "+00:00").replace("+00:00", ""))
                days_since = min(days_since, (now - activity_date).days)
            except:
                pass
        
        if days_since == 999:
            return 5, 999  # Unknown, give medium score
        
        if days_since <= 3:
            return 15, days_since
        elif days_since <= 7:
            return 12, days_since
        elif days_since <= 14:
            return 9, days_since
        elif days_since <= 30:
            return 6, days_since
        elif days_since <= 60:
            return 3, days_since
        else:
            return 0, days_since
    
    def _calculate_amount_score(self, opportunity, avg_value) -> float:
        """Calculate score based on deal amount (0-15 points)"""
        if not opportunity:
            return 5  # Unknown amount
        
        try:
            amount = float(opportunity)
        except (ValueError, TypeError):
            return 5
        
        if amount <= 0:
            return 2
        
        if not avg_value or float(avg_value) <= 0:
            avg_value = 100000  # Default average
        
        # Score based on how deal compares to average
        ratio = float(amount) / float(avg_value)
        
        if ratio >= 2.0:
            return 15  # High value deal
        elif ratio >= 1.0:
            return 12
        elif ratio >= 0.5:
            return 9
        elif ratio >= 0.25:
            return 6
        else:
            return 3
    
    def _calculate_velocity_score(self, date_create: str, stage_id: str, avg_cycle: float) -> float:
        """Calculate score based on deal velocity (0-15 points)"""
        if not date_create:
            return 7  # Unknown, give medium score
        
        try:
            create_date = datetime.fromisoformat(date_create.replace("Z", "+00:00").replace("+00:00", ""))
            days_in_pipeline = (datetime.utcnow() - create_date).days
        except:
            return 7
        
        # Get expected progress based on stage
        stage_upper = stage_id.upper() if stage_id else "NEW"
        expected_progress = 0.1  # Default 10%
        
        for key, weight in DealAnalyzer.STAGE_WEIGHTS.items():
            if key in stage_upper:
                expected_progress = weight / 100
                break
        
        # Calculate expected days at this progress
        expected_days = avg_cycle * expected_progress
        
        if days_in_pipeline <= 0:
            return 15  # New deal
        
        # Compare actual vs expected
        velocity_ratio = expected_days / days_in_pipeline if days_in_pipeline > 0 else 1
        
        if velocity_ratio >= 1.5:
            return 15  # Moving fast
        elif velocity_ratio >= 1.0:
            return 12
        elif velocity_ratio >= 0.75:
            return 9
        elif velocity_ratio >= 0.5:
            return 6
        else:
            return 3  # Moving slow
    
    def _calculate_engagement_score(self, activities: Dict[str, int], tasks: Dict[str, int]) -> float:
        """Calculate engagement score (0-10 points)"""
        completed_activities = activities.get("completed", 0)
        completed_tasks = tasks.get("completed", 0)
        total_tasks = tasks.get("total", 0)
        
        # Task completion rate
        task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 50
        
        # Activity completion
        activity_bonus = min(4, completed_activities * 0.5)
        
        # Task bonus
        task_bonus = (task_completion_rate / 100) * 4
        
        # Penalty for no engagement
        if completed_activities == 0 and completed_tasks == 0:
            return 2
        
        return min(10, 2 + activity_bonus + task_bonus)
    
    def _calculate_win_probability(self, score: DealScore, historical: Dict[str, float]) -> float:
        """Calculate win probability based on score and historical data"""
        base_win_rate = historical.get("overall_win_rate", 50)
        
        # Score contribution (0-60% boost)
        score_boost = (score.total_score / 100) * 60
        
        # Combine base rate with score
        probability = (base_win_rate * 0.3) + (score_boost * 0.7)
        
        # Stage override for won/lost stages
        stage_score_pct = (score.stage_score / 25) * 100
        if stage_score_pct >= 95:
            probability = 95
        elif stage_score_pct <= 5:
            probability = 5
        
        return min(99, max(1, probability))
    
    def _determine_risk_level(self, score: DealScore, days_since: int, overdue_tasks: int) -> RiskLevel:
        """Determine risk level"""
        risk_points = 0
        
        # Low score = risk
        if score.total_score < 30:
            risk_points += 3
        elif score.total_score < 50:
            risk_points += 2
        elif score.total_score < 70:
            risk_points += 1
        
        # No recent activity = risk
        if days_since > 30:
            risk_points += 2
        elif days_since > 14:
            risk_points += 1
        
        # Overdue tasks = risk
        if overdue_tasks > 2:
            risk_points += 2
        elif overdue_tasks > 0:
            risk_points += 1
        
        if risk_points >= 5:
            return RiskLevel.CRITICAL
        elif risk_points >= 3:
            return RiskLevel.HIGH
        elif risk_points >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_factors(
        self, 
        score: DealScore, 
        deal: Dict, 
        activities: Dict, 
        tasks: Dict, 
        days_since: int
    ):
        """Generate positive and negative factors"""
        # Positive factors
        if score.stage_score >= 20:
            score.positive_factors.append("Anlaşma ileri aşamada")
        if activities.get("meetings", 0) > 0:
            score.positive_factors.append(f"{activities['meetings']} toplantı yapılmış")
        if activities.get("calls", 0) >= 3:
            score.positive_factors.append(f"Aktif iletişim ({activities['calls']} arama)")
        if days_since <= 7:
            score.positive_factors.append("Son 7 günde aktivite var")
        if tasks.get("completed", 0) > 0:
            score.positive_factors.append(f"{tasks['completed']} görev tamamlandı")
        if score.velocity_score >= 12:
            score.positive_factors.append("Anlaşma hızlı ilerliyor")
        
        # Negative factors
        if days_since > 14:
            score.negative_factors.append(f"{days_since} gündür aktivite yok")
        if activities.get("total", 0) == 0:
            score.negative_factors.append("Hiç aktivite kaydı yok")
        if tasks.get("overdue", 0) > 0:
            score.negative_factors.append(f"{tasks['overdue']} gecikmiş görev var")
        if score.stage_score <= 5:
            score.negative_factors.append("Anlaşma erken aşamada")
        if score.velocity_score <= 6:
            score.negative_factors.append("Anlaşma yavaş ilerliyor")
    
    def _generate_recommendations(
        self, 
        score: DealScore, 
        deal: Dict, 
        activities: Dict, 
        tasks: Dict, 
        days_since: int
    ):
        """Generate actionable recommendations"""
        # Priority recommendations based on issues
        if days_since > 7:
            score.recommendations.append("🔴 Müşteriyi arayarak durum güncellemesi alın")
        
        if activities.get("meetings", 0) == 0:
            score.recommendations.append("📅 Yüz yüze veya online toplantı planlayın")
        
        if tasks.get("overdue", 0) > 0:
            score.recommendations.append(f"⚠️ {tasks['overdue']} gecikmiş görevi tamamlayın")
        
        if score.stage_score < 15 and activities.get("total", 0) < 3:
            score.recommendations.append("📧 Ürün/hizmet tanıtımı için e-posta gönderin")
        
        if score.amount_score < 8:
            score.recommendations.append("💰 Ek satış fırsatlarını değerlendirin")
        
        if score.engagement_score < 5:
            score.recommendations.append("📋 Takip görevi oluşturun")
        
        # Always have at least one recommendation
        if not score.recommendations:
            score.recommendations.append("✅ Anlaşma iyi gidiyor, mevcut stratejiye devam edin")
    
    async def get_batch_predictions(
        self, 
        limit: int = 50, 
        stage_filter: str = None,
        min_amount: float = None
    ) -> List[DealScore]:
        """Get predictions for multiple deals"""
        # Build query
        conditions = ["d.stage_id NOT LIKE '%WON%'", 
                     "d.stage_id NOT LIKE '%LOSE%'",
                     "d.stage_id != 'WON'",
                     "d.stage_id != 'LOSE'"]
        params = {"limit": limit}
        
        if stage_filter:
            conditions.append("d.stage_id LIKE :stage")
            params["stage"] = f"%{stage_filter}%"
        
        if min_amount:
            conditions.append("d.opportunity >= :min_amount")
            params["min_amount"] = min_amount
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT d.id
            FROM bitrix.deals d
            WHERE {where_clause}
            ORDER BY d.date_modify DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, params)
        deal_ids = [row.id for row in result.fetchall()]
        
        # Calculate scores for each deal
        scores = []
        for deal_id in deal_ids:
            score = await self.calculate_deal_score(deal_id)
            if score:
                scores.append(score)
        
        # Sort by win probability (highest first)
        scores.sort(key=lambda x: x.win_probability, reverse=True)
        
        return scores
    
    async def get_at_risk_deals(self, threshold: float = 40) -> List[DealScore]:
        """Get deals at risk (low win probability)"""
        all_scores = await self.get_batch_predictions(limit=100)
        return [s for s in all_scores if s.win_probability < threshold or s.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]


class AIEnhancedPrediction:
    """
    Uses AI to enhance predictions with natural language insights
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.prediction_service = SalesPredictionService(db)
    
    async def generate_ai_insight(
        self, 
        deal_id: int, 
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """Generate AI-powered insight for a deal"""
        # Get score first
        score = await self.prediction_service.calculate_deal_score(deal_id)
        if not score:
            return {"error": "Deal not found"}
        
        # Get deal details
        deal = await self.prediction_service.analyzer.get_deal_with_context(deal_id)
        
        # Build context for AI
        context = f"""
Anlaşma Analizi:
- Anlaşma: {deal.get('title', 'Bilinmiyor')}
- Tutar: {deal.get('opportunity', '0')} {deal.get('currency', 'TRY')}
- Aşama: {deal.get('stage_id', 'Bilinmiyor')}
- Toplam Puan: {score.total_score:.1f}/100
- Kazanma Olasılığı: {score.win_probability:.1f}%
- Risk Seviyesi: {score.risk_level.value}

Puan Detayları:
- Aşama Puanı: {score.stage_score:.1f}/25
- Aktivite Puanı: {score.activity_score:.1f}/20
- Güncellik Puanı: {score.recency_score:.1f}/15
- Tutar Puanı: {score.amount_score:.1f}/15
- Hız Puanı: {score.velocity_score:.1f}/15
- Etkileşim Puanı: {score.engagement_score:.1f}/10

Olumlu Faktörler:
{chr(10).join('- ' + f for f in score.positive_factors) or '- Yok'}

Olumsuz Faktörler:
{chr(10).join('- ' + f for f in score.negative_factors) or '- Yok'}

Öneriler:
{chr(10).join('- ' + r for r in score.recommendations)}
"""
        
        prompt = f"""Sen bir satış uzmanısın. Aşağıdaki anlaşma analizini değerlendir ve kısa, aksiyona dönüştürülebilir bir özet hazırla.

{context}

Lütfen şu formatta yanıt ver:
1. **Durum Özeti** (1-2 cümle)
2. **En Kritik Aksiyon** (yapılması gereken ilk şey)
3. **Tahmin** (Bu anlaşmanın kapanma ihtimali ve süresi hakkında)
"""
        
        # Call AI provider
        ai_response = await self._call_ai(prompt, provider, model)
        
        return {
            "deal_id": deal_id,
            "deal_title": deal.get("title"),
            "score": {
                "total": score.total_score,
                "win_probability": score.win_probability,
                "risk_level": score.risk_level.value,
                "breakdown": {
                    "stage": score.stage_score,
                    "activity": score.activity_score,
                    "recency": score.recency_score,
                    "amount": score.amount_score,
                    "velocity": score.velocity_score,
                    "engagement": score.engagement_score
                }
            },
            "positive_factors": score.positive_factors,
            "negative_factors": score.negative_factors,
            "recommendations": score.recommendations,
            "ai_insight": ai_response,
            "calculated_at": score.calculated_at.isoformat()
        }
    
    async def _call_ai(self, prompt: str, provider: str, model: str) -> str:
        """Call AI provider for insight generation"""
        try:
            if provider == "openai":
                return await self._call_openai(prompt, model)
            elif provider == "claude":
                return await self._call_claude(prompt, model)
            elif provider == "ollama":
                return await self._call_ollama(prompt, model)
            else:
                return "AI servisi şu anda kullanılamıyor."
        except Exception as e:
            logger.error("ai_call_error", provider=provider, error=str(e))
            return f"AI analizi oluşturulamadı: {str(e)}"
    
    async def _call_openai(self, prompt: str, model: str) -> str:
        """Call OpenAI API"""
        api_key = settings.openai_api_key
        if not api_key:
            return "OpenAI API anahtarı yapılandırılmamış."
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "Sen bir satış analisti ve CRM uzmanısın. Türkçe yanıt ver."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _call_claude(self, prompt: str, model: str) -> str:
        """Call Anthropic Claude API"""
        api_key = settings.anthropic_api_key
        if not api_key:
            return "Claude API anahtarı yapılandırılmamış."
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": model or "claude-3-haiku-20240307",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
    
    async def _call_ollama(self, prompt: str, model: str) -> str:
        """Call local Ollama API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": model or "llama2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


class CustomerSegmentationService:
    """
    Service for customer segmentation and profiling
    Analyzes contacts/companies to categorize them into segments
    """
    
    # Segment thresholds
    VIP_THRESHOLD = 500000  # Total deal value for VIP
    HIGH_VALUE_THRESHOLD = 200000  # Total deal value for high value
    COLD_DAYS_THRESHOLD = 90  # Days without activity to be considered cold
    AT_RISK_DAYS_THRESHOLD = 45  # Days without activity to be at risk
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_contact_profile(self, contact_id: int) -> Optional[CustomerProfile]:
        """
        Get comprehensive customer profile with segmentation
        """
        # Get contact basic info
        contact_query = text("""
            SELECT 
                c.id,
                c.name,
                c.last_name,
                c.date_create
            FROM bitrix.contacts c
            WHERE c.id = :contact_id OR c.bitrix_id = :contact_id_str
        """)
        contact_result = await self.db.execute(contact_query, {
            "contact_id": contact_id,
            "contact_id_str": str(contact_id)
        })
        contact = contact_result.fetchone()
        
        if not contact:
            return None
        
        # Get deal statistics for this contact
        deals_query = text("""
            SELECT 
                COUNT(*) as total_deals,
                COUNT(CASE WHEN d.stage_id LIKE '%WON%' OR d.stage_id = 'WON' THEN 1 END) as won_deals,
                COUNT(CASE WHEN d.stage_id LIKE '%LOSE%' OR d.stage_id = 'LOSE' THEN 1 END) as lost_deals,
                COUNT(CASE WHEN d.stage_id NOT LIKE '%WON%' 
                           AND d.stage_id NOT LIKE '%LOSE%'
                           AND d.stage_id != 'WON'
                           AND d.stage_id != 'LOSE' THEN 1 END) as active_deals,
                COALESCE(SUM(
                    CASE WHEN d.stage_id LIKE '%WON%' OR d.stage_id = 'WON'
                    THEN COALESCE(d.opportunity, 0) ELSE 0 END
                ), 0) as total_won_value,
                AVG(d.opportunity) as avg_deal_value
            FROM bitrix.deals d
            WHERE d.contact_id = :contact_id_str
        """)
        deals_result = await self.db.execute(deals_query, {"contact_id_str": str(contact_id)})
        deals_stats = deals_result.fetchone()
        
        # Get last activity date
        activity_query = text("""
            SELECT MAX(a.created) as last_activity
            FROM bitrix.activities a
            WHERE a.owner_id = :contact_id_str
              AND a.owner_type_id = '3'
        """)
        activity_result = await self.db.execute(activity_query, {"contact_id_str": str(contact_id)})
        activity_row = activity_result.fetchone()
        
        # Calculate days since last activity
        days_since_activity = 999
        if activity_row and activity_row.last_activity:
            try:
                last_activity_date = datetime.fromisoformat(
                    activity_row.last_activity.replace("Z", "+00:00").replace("+00:00", "")
                )
                days_since_activity = (datetime.utcnow() - last_activity_date).days
            except:
                pass
        
        # Determine segment
        segment = self._determine_segment(
            total_value=float(deals_stats.total_won_value or 0),
            total_deals=int(deals_stats.total_deals or 0),
            won_deals=int(deals_stats.won_deals or 0),
            active_deals=int(deals_stats.active_deals or 0),
            days_since_activity=days_since_activity,
            date_create=contact.date_create
        )
        
        # Calculate engagement level
        engagement_level = self._calculate_engagement_level(
            total_deals=int(deals_stats.total_deals or 0),
            won_deals=int(deals_stats.won_deals or 0),
            days_since_activity=days_since_activity
        )
        
        # Calculate churn risk
        churn_risk = self._calculate_churn_risk(
            segment=segment,
            days_since_activity=days_since_activity,
            active_deals=int(deals_stats.active_deals or 0)
        )
        
        return CustomerProfile(
            contact_id=contact_id,
            segment=segment,
            lifetime_value=float(deals_stats.total_won_value or 0),
            total_deals=int(deals_stats.total_deals or 0),
            won_deals=int(deals_stats.won_deals or 0),
            lost_deals=int(deals_stats.lost_deals or 0),
            active_deals=int(deals_stats.active_deals or 0),
            avg_deal_value=float(deals_stats.avg_deal_value or 0),
            days_since_last_activity=days_since_activity,
            engagement_level=engagement_level,
            churn_risk=churn_risk
        )
    
    def _determine_segment(
        self,
        total_value: float,
        total_deals: int,
        won_deals: int,
        active_deals: int,
        days_since_activity: int,
        date_create: str
    ) -> CustomerSegment:
        """Determine customer segment based on various factors"""
        
        # Check if new customer (created in last 30 days and no completed deals)
        if date_create:
            try:
                create_date = datetime.fromisoformat(date_create.replace("Z", "+00:00").replace("+00:00", ""))
                if (datetime.utcnow() - create_date).days <= 30 and won_deals == 0:
                    return CustomerSegment.NEW
            except:
                pass
        
        # Check if cold (no activity for 90+ days)
        if days_since_activity >= self.COLD_DAYS_THRESHOLD and active_deals == 0:
            return CustomerSegment.COLD
        
        # Check if at risk (no activity for 45+ days but has history)
        if days_since_activity >= self.AT_RISK_DAYS_THRESHOLD and total_deals > 0:
            return CustomerSegment.AT_RISK
        
        # Check if VIP (high lifetime value)
        if total_value >= self.VIP_THRESHOLD:
            return CustomerSegment.VIP
        
        # Check if high value
        if total_value >= self.HIGH_VALUE_THRESHOLD:
            return CustomerSegment.HIGH_VALUE
        
        # Default to regular
        return CustomerSegment.REGULAR
    
    def _calculate_engagement_level(
        self,
        total_deals: int,
        won_deals: int,
        days_since_activity: int
    ) -> str:
        """Calculate engagement level (high, medium, low)"""
        
        score = 0
        
        # Deal count score
        if total_deals >= 5:
            score += 3
        elif total_deals >= 2:
            score += 2
        elif total_deals >= 1:
            score += 1
        
        # Win rate score
        if total_deals > 0:
            win_rate = (won_deals / total_deals) * 100
            if win_rate >= 50:
                score += 3
            elif win_rate >= 25:
                score += 2
            elif win_rate > 0:
                score += 1
        
        # Recency score
        if days_since_activity <= 7:
            score += 3
        elif days_since_activity <= 30:
            score += 2
        elif days_since_activity <= 60:
            score += 1
        
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"
    
    def _calculate_churn_risk(
        self,
        segment: CustomerSegment,
        days_since_activity: int,
        active_deals: int
    ) -> float:
        """Calculate churn risk percentage (0-100)"""
        
        risk = 0.0
        
        # Segment-based risk
        segment_risks = {
            CustomerSegment.COLD: 80,
            CustomerSegment.AT_RISK: 60,
            CustomerSegment.NEW: 40,
            CustomerSegment.REGULAR: 20,
            CustomerSegment.HIGH_VALUE: 10,
            CustomerSegment.VIP: 5
        }
        risk = segment_risks.get(segment, 20)
        
        # Adjust based on activity
        if days_since_activity > 60:
            risk += 20
        elif days_since_activity > 30:
            risk += 10
        elif days_since_activity <= 7:
            risk -= 10
        
        # Adjust based on active deals
        if active_deals > 0:
            risk -= 15
        
        return max(0, min(100, risk))
    
    async def get_all_customer_segments(
        self, 
        limit: int = 100,
        segment_filter: Optional[CustomerSegment] = None
    ) -> Dict[str, Any]:
        """
        Get segmentation overview for all customers
        """
        # Get all contacts with deal history
        query = text("""
            SELECT DISTINCT d.contact_id
            FROM bitrix.deals d
            WHERE d.contact_id IS NOT NULL
              AND d.contact_id != ''
              AND d.contact_id != '0'
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"limit": limit})
        contact_ids = []
        for row in result.fetchall():
            try:
                if row.contact_id:
                    contact_ids.append(int(row.contact_id))
            except (ValueError, TypeError):
                continue
        
        # Get profiles for each contact
        profiles = []
        segment_counts = {s.value: 0 for s in CustomerSegment}
        total_lifetime_value = 0.0
        
        for contact_id in contact_ids:
            try:
                profile = await self.get_contact_profile(contact_id)
                if profile:
                    if segment_filter is None or profile.segment == segment_filter:
                        profiles.append(profile)
                    segment_counts[profile.segment.value] += 1
                    total_lifetime_value += float(profile.lifetime_value)
            except Exception as e:
                logger.warning("profile_fetch_error", contact_id=contact_id, error=str(e))
                continue
        
        # Sort by lifetime value
        profiles.sort(key=lambda x: x.lifetime_value, reverse=True)
        
        return {
            "total_customers": len(contact_ids),
            "segment_distribution": segment_counts,
            "total_lifetime_value": total_lifetime_value,
            "avg_lifetime_value": total_lifetime_value / len(contact_ids) if contact_ids else 0,
            "customers": [
                {
                    "contact_id": p.contact_id,
                    "segment": p.segment.value,
                    "lifetime_value": p.lifetime_value,
                    "total_deals": p.total_deals,
                    "won_deals": p.won_deals,
                    "active_deals": p.active_deals,
                    "engagement_level": p.engagement_level,
                    "churn_risk": p.churn_risk,
                    "days_since_activity": p.days_since_last_activity
                }
                for p in profiles[:50]  # Return top 50
            ]
        }
    
    async def get_segment_recommendations(self, segment: CustomerSegment) -> List[str]:
        """Get action recommendations for a customer segment"""
        recommendations = {
            CustomerSegment.VIP: [
                "🌟 Özel indirim veya avantajlar sunun",
                "📞 Düzenli kişisel iletişim kurun",
                "🎁 Sadakat programı veya özel etkinliklere davet edin",
                "📊 Aylık hesap özeti ve kişiselleştirilmiş raporlar gönderin"
            ],
            CustomerSegment.HIGH_VALUE: [
                "⬆️ VIP statüsüne yükseltme fırsatlarını değerlendirin",
                "📈 Cross-sell ve up-sell fırsatlarını araştırın",
                "🤝 Referans programına davet edin",
                "📧 Kişiselleştirilmiş içerik ve teklifler gönderin"
            ],
            CustomerSegment.REGULAR: [
                "📊 Düzenli takip ve iletişim sürdürün",
                "💡 Değer katan içerikler paylaşın",
                "🎯 İhtiyaç analizi yaparak yeni fırsatlar yaratın",
                "📱 Sosyal medya etkileşimini artırın"
            ],
            CustomerSegment.NEW: [
                "👋 Hoş geldiniz e-postası ve tanıtım materyalleri gönderin",
                "📚 Ürün/hizmet eğitimi sunun",
                "🤝 İlk 30 gün içinde kişisel görüşme planlayın",
                "⭐ İlk satın alma için özel teklif sunun"
            ],
            CustomerSegment.AT_RISK: [
                "🚨 Acil iletişim kurun - telefon görüşmesi yapın",
                "❓ Memnuniyet anketi gönderin",
                "💰 Geri kazanım kampanyası başlatın",
                "🔍 Son etkileşimleri analiz edin ve sorunları tespit edin"
            ],
            CustomerSegment.COLD: [
                "📧 Yeniden aktivasyon e-posta kampanyası başlatın",
                "💎 Özel 'Sizi özledik' teklifi sunun",
                "📞 Kişisel telefon görüşmesi yapın",
                "🔄 Ürün/hizmet güncellemelerini paylaşın"
            ]
        }
        return recommendations.get(segment, [])

