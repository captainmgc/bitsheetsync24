"""
Customer 360° Analysis API
Provides comprehensive view of all customer interactions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import structlog

from app.database import get_db

router = APIRouter()
logger = structlog.get_logger()

# Task status mapping
TASK_STATUS_NAMES = {
    1: "Yeni",
    2: "Bekliyor",
    3: "Devam Ediyor",
    4: "Onay Bekliyor",
    5: "Tamamlandı",
    6: "Ertelendi",
    7: "Reddedildi",
}

# Task priority mapping
TASK_PRIORITY_NAMES = {
    0: "Düşük",
    1: "Normal",
    2: "Yüksek",
}

# Activity type mapping
ACTIVITY_TYPE_NAMES = {
    "1": "Toplantı",
    "2": "Arama",
    "3": "Görev",
    "4": "E-posta",
    "5": "SMS",
    "6": "Randevu",
}


class CustomerSearchResult(BaseModel):
    id: int
    bitrix_id: str
    entity_type: str  # contact or company
    name: str
    phone: Optional[str]
    email: Optional[str]


class TimelineEvent(BaseModel):
    event_type: str
    event_date: Optional[datetime]
    title: str
    description: Optional[str]
    responsible_name: Optional[str]
    status: Optional[str]
    details: Dict[str, Any]


class DealSummary(BaseModel):
    bitrix_id: str
    title: str
    stage_name: str
    stage_color: Optional[str]
    opportunity: Optional[float]
    currency: Optional[str]
    responsible_name: Optional[str]
    created_date: Optional[datetime]
    close_date: Optional[datetime]
    is_closed: bool
    is_won: bool


class TaskSummary(BaseModel):
    bitrix_id: str
    title: str
    status_name: str
    priority_name: str
    responsible_name: Optional[str]
    created_by_name: Optional[str]
    deadline: Optional[datetime]
    created_date: Optional[datetime]
    comments_count: int


class ActivitySummary(BaseModel):
    bitrix_id: str
    subject: str
    type_name: str
    responsible_name: Optional[str]
    created: Optional[datetime]
    description: Optional[str]


class Customer360Response(BaseModel):
    customer: Dict[str, Any]
    summary: Dict[str, Any]
    deals: List[DealSummary]
    tasks: List[TaskSummary]
    activities: List[ActivitySummary]
    timeline: List[Dict[str, Any]]
    task_comments: List[Dict[str, Any]]


@router.get("/search")
async def search_customers(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[CustomerSearchResult]:
    """Search contacts and companies by name, phone, or email"""
    
    search_term = f"%{q}%"
    
    # Search contacts
    contacts_query = text("""
        SELECT 
            id,
            bitrix_id,
            'contact' as entity_type,
            COALESCE(full_name, CONCAT_WS(' ', name, last_name)) as name,
            phone,
            email
        FROM bitrix.contacts
        WHERE 
            full_name ILIKE :search
            OR name ILIKE :search
            OR last_name ILIKE :search
            OR phone ILIKE :search
            OR email ILIKE :search
        LIMIT :limit
    """)
    
    # Search companies
    companies_query = text("""
        SELECT 
            id,
            bitrix_id,
            'company' as entity_type,
            title as name,
            phone,
            email
        FROM bitrix.companies
        WHERE 
            title ILIKE :search
            OR phone ILIKE :search
            OR email ILIKE :search
        LIMIT :limit
    """)
    
    results = []
    
    # Execute both queries
    contacts_result = await db.execute(contacts_query, {"search": search_term, "limit": limit})
    for row in contacts_result.mappings():
        results.append(CustomerSearchResult(**dict(row)))
    
    companies_result = await db.execute(companies_query, {"search": search_term, "limit": limit})
    for row in companies_result.mappings():
        results.append(CustomerSearchResult(**dict(row)))
    
    return results[:limit]


@router.get("/list/contacts")
async def list_contacts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Optional search filter"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List contacts with pagination"""
    
    where_clause = ""
    params = {"limit": limit, "offset": offset}
    
    if search:
        where_clause = """
            WHERE full_name ILIKE :search
            OR name ILIKE :search
            OR last_name ILIKE :search
            OR phone ILIKE :search
            OR email ILIKE :search
        """
        params["search"] = f"%{search}%"
    
    # Get total count
    count_query = text(f"SELECT COUNT(*) FROM bitrix.contacts {where_clause}")
    count_result = await db.execute(count_query, params)
    total = count_result.scalar()
    
    # Get data
    query = text(f"""
        SELECT 
            id,
            bitrix_id,
            'contact' as entity_type,
            COALESCE(full_name, CONCAT_WS(' ', name, last_name)) as name,
            phone,
            email,
            company_title
        FROM bitrix.contacts
        {where_clause}
        ORDER BY full_name ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    
    result = await db.execute(query, params)
    items = [CustomerSearchResult(**dict(row)) for row in result.mappings()]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/list/companies")
async def list_companies(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Optional search filter"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List companies with pagination"""
    
    where_clause = ""
    params = {"limit": limit, "offset": offset}
    
    if search:
        where_clause = """
            WHERE title ILIKE :search
            OR phone ILIKE :search
            OR email ILIKE :search
        """
        params["search"] = f"%{search}%"
    
    # Get total count
    count_query = text(f"SELECT COUNT(*) FROM bitrix.companies {where_clause}")
    count_result = await db.execute(count_query, params)
    total = count_result.scalar()
    
    # Get data
    query = text(f"""
        SELECT 
            id,
            bitrix_id,
            'company' as entity_type,
            title as name,
            phone,
            email
        FROM bitrix.companies
        {where_clause}
        ORDER BY title ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    
    result = await db.execute(query, params)
    items = [CustomerSearchResult(**dict(row)) for row in result.mappings()]
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/contact/{bitrix_id}")
async def get_contact_360(
    bitrix_id: str,
    db: AsyncSession = Depends(get_db)
) -> Customer360Response:
    """Get 360° view for a contact"""
    return await _get_customer_360(db, "contact", bitrix_id)


@router.get("/company/{bitrix_id}")
async def get_company_360(
    bitrix_id: str,
    db: AsyncSession = Depends(get_db)
) -> Customer360Response:
    """Get 360° view for a company"""
    return await _get_customer_360(db, "company", bitrix_id)


async def _get_customer_360(
    db: AsyncSession,
    entity_type: str,
    bitrix_id: str
) -> Customer360Response:
    """Internal function to get 360° view"""
    
    # Get user name lookup
    users_cache = await _get_users_cache(db)
    
    # Get stage name lookup
    stages_cache = await _get_stages_cache(db)
    
    # Get customer info
    if entity_type == "contact":
        customer = await _get_contact_info(db, bitrix_id, users_cache)
    else:
        customer = await _get_company_info(db, bitrix_id, users_cache)
    
    if not customer:
        raise HTTPException(status_code=404, detail=f"{entity_type.capitalize()} not found")
    
    # Get related deals
    deals = await _get_related_deals(db, entity_type, bitrix_id, users_cache, stages_cache)
    
    # Get related activities
    activities = await _get_related_activities(db, entity_type, bitrix_id, users_cache)
    
    # Get related tasks (through deals or direct assignment)
    tasks = await _get_related_tasks(db, entity_type, bitrix_id, users_cache)
    
    # Get task comments
    task_comments = await _get_task_comments(db, [t["bitrix_id"] for t in tasks], users_cache)
    
    # Build timeline
    timeline = _build_timeline(deals, tasks, activities, task_comments)
    
    # Calculate summary
    summary = _calculate_summary(customer, deals, tasks, activities)
    
    return Customer360Response(
        customer=customer,
        summary=summary,
        deals=deals,
        tasks=tasks,
        activities=activities,
        timeline=timeline,
        task_comments=task_comments
    )


async def _get_users_cache(db: AsyncSession) -> Dict[str, str]:
    """Get user ID to name mapping"""
    query = text("""
        SELECT 
            id::text as user_id,
            COALESCE(
                CONCAT_WS(' ', name, last_name),
                data->>'NAME',
                'Kullanıcı ' || id
            ) as user_name
        FROM bitrix.users
    """)
    result = await db.execute(query)
    return {str(row.user_id): row.user_name for row in result}


async def _get_stages_cache(db: AsyncSession) -> Dict[str, Dict[str, str]]:
    """Get stage ID to name/color mapping - handles category-based stages like C24:LOSE"""
    query = text("""
        SELECT 
            status_id,
            category_id,
            name,
            COALESCE(extra->>'COLOR', color) as color,
            COALESCE(extra->>'SEMANTICS', semantics) as semantics
        FROM bitrix.lookup_values
        WHERE entity_type = 'DEAL_STAGE'
    """)
    result = await db.execute(query)
    cache = {}
    
    for row in result:
        stage_data = {
            "name": row.name,
            "color": row.color,
            "semantics": row.semantics
        }
        # Add with original status_id
        cache[row.status_id] = stage_data
        
        # Also add with category prefix format (e.g., C24:LOSE)
        if row.category_id:
            category_key = f"C{row.category_id}:{row.status_id}"
            cache[category_key] = stage_data
    
    return cache


async def _get_contact_info(db: AsyncSession, bitrix_id: str, users_cache: Dict) -> Optional[Dict]:
    """Get contact details"""
    query = text("""
        SELECT 
            c.*,
            comp.title as company_name
        FROM bitrix.contacts c
        LEFT JOIN bitrix.companies comp ON comp.bitrix_id = c.company_id
        WHERE c.bitrix_id = :bitrix_id
    """)
    result = await db.execute(query, {"bitrix_id": bitrix_id})
    row = result.mappings().first()
    
    if not row:
        return None
    
    data = dict(row)
    data["assigned_by_name"] = users_cache.get(data.get("assigned_by_id"), "Bilinmiyor")
    data["created_by_name"] = users_cache.get(data.get("created_by_id"), "Bilinmiyor")
    data["entity_type"] = "contact"
    data["display_name"] = data.get("full_name") or f"{data.get('name', '')} {data.get('last_name', '')}".strip()
    
    return data


async def _get_company_info(db: AsyncSession, bitrix_id: str, users_cache: Dict) -> Optional[Dict]:
    """Get company details"""
    query = text("""
        SELECT *
        FROM bitrix.companies
        WHERE bitrix_id = :bitrix_id
    """)
    result = await db.execute(query, {"bitrix_id": bitrix_id})
    row = result.mappings().first()
    
    if not row:
        return None
    
    data = dict(row)
    data["assigned_by_name"] = users_cache.get(data.get("assigned_by_id"), "Bilinmiyor")
    data["created_by_name"] = users_cache.get(data.get("created_by_id"), "Bilinmiyor")
    data["entity_type"] = "company"
    data["display_name"] = data.get("title", "")
    
    return data


async def _get_related_deals(
    db: AsyncSession,
    entity_type: str,
    bitrix_id: str,
    users_cache: Dict,
    stages_cache: Dict
) -> List[Dict]:
    """Get deals related to contact or company"""
    
    if entity_type == "contact":
        where_clause = "contact_id = :bitrix_id"
    else:
        where_clause = "company_id = :bitrix_id"
    
    query = text(f"""
        SELECT 
            bitrix_id,
            title,
            stage_id,
            stage_semantic_id,
            opportunity,
            currency_id,
            assigned_by_id,
            date_create,
            closedate,
            closed
        FROM bitrix.deals
        WHERE {where_clause}
        ORDER BY date_create DESC
    """)
    
    result = await db.execute(query, {"bitrix_id": bitrix_id})
    deals = []
    
    for row in result.mappings():
        stage_id = row["stage_id"]
        
        # Try to find stage info - first with full stage_id, then extract base part
        stage_info = stages_cache.get(stage_id)
        
        if not stage_info and stage_id and ":" in stage_id:
            # Extract base status from category format (e.g., C24:LOSE -> LOSE)
            base_status = stage_id.split(":")[-1]
            stage_info = stages_cache.get(base_status)
        
        if not stage_info:
            stage_info = {"name": stage_id or "Bilinmiyor", "color": "#999", "semantics": ""}
        
        deals.append({
            "bitrix_id": row["bitrix_id"],
            "title": row["title"],
            "stage_name": stage_info["name"],
            "stage_color": stage_info["color"],
            "opportunity": float(row["opportunity"]) if row["opportunity"] else None,
            "currency": row["currency_id"],
            "responsible_name": users_cache.get(row["assigned_by_id"], "Bilinmiyor"),
            "created_date": row["date_create"],
            "close_date": row["closedate"],
            "is_closed": row["closed"] or False,
            "is_won": stage_info.get("semantics") == "S"
        })
    
    return deals


async def _get_related_activities(
    db: AsyncSession,
    entity_type: str,
    bitrix_id: str,
    users_cache: Dict
) -> List[Dict]:
    """Get activities related to contact or company"""
    
    owner_type = "3" if entity_type == "contact" else "4"  # Bitrix owner type IDs
    
    query = text("""
        SELECT 
            bitrix_id,
            subject,
            description,
            type_id,
            responsible_id,
            author_id,
            created
        FROM bitrix.activities
        WHERE owner_id = :bitrix_id AND owner_type_id = :owner_type
        ORDER BY created DESC
        LIMIT 100
    """)
    
    result = await db.execute(query, {"bitrix_id": bitrix_id, "owner_type": owner_type})
    activities = []
    
    for row in result.mappings():
        activities.append({
            "bitrix_id": row["bitrix_id"],
            "subject": row["subject"] or "Aktivite",
            "type_name": ACTIVITY_TYPE_NAMES.get(str(row["type_id"]), f"Tip {row['type_id']}"),
            "responsible_name": users_cache.get(row["responsible_id"], "Bilinmiyor"),
            "author_name": users_cache.get(row["author_id"], "Bilinmiyor"),
            "created": row["created"],
            "description": row["description"]
        })
    
    return activities


async def _get_related_tasks(
    db: AsyncSession,
    entity_type: str,
    bitrix_id: str,
    users_cache: Dict
) -> List[Dict]:
    """Get tasks related to contact or company via deals or CRM binding"""
    
    # Get task IDs from deals
    if entity_type == "contact":
        where_clause = "d.contact_id = :bitrix_id"
    else:
        where_clause = "d.company_id = :bitrix_id"
    
    # Search in task title/description for CRM reference or via UF_CRM_TASK field
    query = text(f"""
        SELECT DISTINCT
            t.bitrix_id,
            t.title,
            t.status,
            t.status_name,
            t.priority,
            t.responsible_id,
            t.created_by,
            t.deadline,
            t.created_date,
            t.comments_count
        FROM bitrix.tasks t
        WHERE 
            t.title ILIKE '%CRM%' AND (
                t.original_data::text ILIKE '%' || :bitrix_id || '%'
            )
        ORDER BY t.created_date DESC
        LIMIT 100
    """)
    
    result = await db.execute(query, {"bitrix_id": bitrix_id})
    tasks = []
    
    for row in result.mappings():
        tasks.append({
            "bitrix_id": row["bitrix_id"],
            "title": row["title"],
            "status": row["status"],
            "status_name": row["status_name"] or TASK_STATUS_NAMES.get(row["status"], "Bilinmiyor"),
            "priority_name": TASK_PRIORITY_NAMES.get(row["priority"], "Normal"),
            "responsible_name": users_cache.get(row["responsible_id"], "Bilinmiyor"),
            "created_by_name": users_cache.get(row["created_by"], "Bilinmiyor"),
            "deadline": row["deadline"],
            "created_date": row["created_date"],
            "comments_count": row["comments_count"] or 0
        })
    
    return tasks


async def _get_task_comments(
    db: AsyncSession,
    task_ids: List[str],
    users_cache: Dict
) -> List[Dict]:
    """Get comments for tasks"""
    
    if not task_ids:
        return []
    
    query = text("""
        SELECT 
            tc.id,
            tc.task_id,
            tc.data->>'POST_MESSAGE' as message,
            tc.data->>'POST_MESSAGE_HTML' as message_html,
            tc.data->>'AUTHOR_ID' as author_id,
            tc.data->>'POST_DATE' as post_date,
            t.title as task_title
        FROM bitrix.task_comments tc
        JOIN bitrix.tasks t ON t.bitrix_id = tc.task_id::text
        WHERE tc.task_id::text = ANY(:task_ids)
        ORDER BY tc.data->>'POST_DATE' DESC
        LIMIT 50
    """)
    
    result = await db.execute(query, {"task_ids": task_ids})
    comments = []
    
    for row in result.mappings():
        comments.append({
            "id": row["id"],
            "task_id": row["task_id"],
            "task_title": row["task_title"],
            "message": row["message"],
            "author_name": users_cache.get(row["author_id"], "Bilinmiyor"),
            "post_date": row["post_date"]
        })
    
    return comments


def _build_timeline(
    deals: List[Dict],
    tasks: List[Dict],
    activities: List[Dict],
    comments: List[Dict]
) -> List[Dict]:
    """Build chronological timeline of all events"""
    
    timeline = []
    
    # Add deals
    for deal in deals:
        timeline.append({
            "event_type": "deal",
            "event_date": deal["created_date"],
            "title": deal["title"],
            "subtitle": deal["stage_name"],
            "icon": "💼",
            "color": deal["stage_color"],
            "responsible": deal["responsible_name"],
            "details": {
                "amount": f"{deal['opportunity']:,.0f} {deal['currency']}" if deal["opportunity"] else None,
                "status": "Kazanıldı" if deal["is_won"] else ("Kapatıldı" if deal["is_closed"] else "Açık")
            }
        })
    
    # Add tasks
    for task in tasks:
        deadline = task.get("deadline")
        timeline.append({
            "event_type": "task",
            "event_date": task["created_date"],
            "title": task["title"],
            "subtitle": task["status_name"],
            "icon": "✅" if task["status"] == 5 else "📋",
            "color": "#4CAF50" if task["status"] == 5 else "#2196F3",
            "responsible": task["responsible_name"],
            "details": {
                "deadline": deadline.isoformat() if deadline and hasattr(deadline, 'isoformat') else str(deadline) if deadline else None,
                "comments": task["comments_count"]
            }
        })
    
    # Add activities
    for activity in activities:
        icon_map = {"Arama": "📞", "E-posta": "📧", "Toplantı": "🤝", "Görev": "📋"}
        timeline.append({
            "event_type": "activity",
            "event_date": activity["created"],
            "title": activity["subject"],
            "subtitle": activity["type_name"],
            "icon": icon_map.get(activity["type_name"], "📌"),
            "color": "#FF9800",
            "responsible": activity["responsible_name"],
            "details": {}
        })
    
    # Add comments
    for comment in comments:
        timeline.append({
            "event_type": "comment",
            "event_date": comment["post_date"],
            "title": f"Yorum: {comment['task_title'][:30]}..." if comment.get('task_title') else "Yorum",
            "subtitle": comment["message"][:100] if comment.get("message") else "",
            "icon": "💬",
            "color": "#9C27B0",
            "responsible": comment["author_name"],
            "details": {}
        })
    
    # Sort by date descending - handle both datetime and string dates
    def get_sort_key(x):
        event_date = x.get("event_date")
        if event_date is None:
            return ""
        if isinstance(event_date, datetime):
            return event_date.isoformat()
        return str(event_date)
    
    timeline.sort(key=get_sort_key, reverse=True)
    
    return timeline


def _calculate_summary(
    customer: Dict,
    deals: List[Dict],
    tasks: List[Dict],
    activities: List[Dict]
) -> Dict:
    """Calculate summary statistics"""
    
    total_deals = len(deals)
    open_deals = sum(1 for d in deals if not d["is_closed"])
    won_deals = sum(1 for d in deals if d["is_won"])
    total_value = sum(d["opportunity"] or 0 for d in deals)
    won_value = sum(d["opportunity"] or 0 for d in deals if d["is_won"])
    
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t["status"] == 5)
    pending_tasks = sum(1 for t in tasks if t["status"] in [1, 2, 3])
    
    total_activities = len(activities)
    
    # Calculate health score (0-100)
    health_score = 50
    if total_deals > 0:
        health_score += (won_deals / total_deals) * 30
    if total_tasks > 0:
        health_score += (completed_tasks / total_tasks) * 20
    health_score = min(100, max(0, int(health_score)))
    
    return {
        "total_deals": total_deals,
        "open_deals": open_deals,
        "won_deals": won_deals,
        "lost_deals": total_deals - open_deals - won_deals,
        "total_value": total_value,
        "won_value": won_value,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_activities": total_activities,
        "health_score": health_score,
        "health_label": "İyi" if health_score >= 70 else ("Orta" if health_score >= 40 else "Dikkat")
    }
