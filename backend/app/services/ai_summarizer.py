"""
AI Customer Journey Summarizer Service
Generates intelligent summaries of customer interactions using AI
Supports: OpenAI GPT-4, Claude, or local Ollama models
"""

import httpx
import json
import os
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from enum import Enum
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import settings

logger = structlog.get_logger()


def format_date(value: Union[datetime, str, None], fmt: str = "%Y-%m-%d") -> str:
    """Safely format a date value (datetime object or string) to string"""
    if value is None:
        return "Bilinmiyor"
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        return value[:10] if len(value) >= 10 else value
    return str(value)


def format_datetime(value: Union[datetime, str, None], fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Safely format a datetime value to string with time"""
    if value is None:
        return "Bilinmiyor"
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        return value[:16] if len(value) >= 16 else value
    return str(value)


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class CustomerDataCollector:
    """
    Collects all customer-related data from PostgreSQL
    for AI summarization - Enhanced for comprehensive contact analysis
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_contact_type_name(self, type_id: str) -> str:
        """Get human-readable contact type name from lookup_values"""
        if not type_id:
            return "Belirtilmemiş"
        
        query = text("""
            SELECT name FROM bitrix.lookup_values 
            WHERE entity_type = 'CONTACT_TYPE' AND status_id = :type_id
            LIMIT 1
        """)
        result = await self.db.execute(query, {"type_id": type_id})
        row = result.fetchone()
        if row:
            return row.name
        return type_id  # Return ID if no name found
    
    async def get_stage_name(self, stage_id: str) -> str:
        """Get human-readable stage name from v_deal_stages view"""
        if not stage_id:
            return "Belirtilmemiş"
        
        query = text("""
            SELECT stage_name FROM bitrix.v_deal_stages 
            WHERE stage_id = :stage_id
            LIMIT 1
        """)
        result = await self.db.execute(query, {"stage_id": stage_id})
        row = result.fetchone()
        if row:
            return row.stage_name
        return stage_id  # Return ID if no name found
    
    async def get_category_name(self, category_id: str) -> str:
        """Get human-readable category name"""
        if not category_id:
            return "Belirtilmemiş"
        
        query = text("""
            SELECT name FROM bitrix.deal_categories 
            WHERE bitrix_id = :category_id
            LIMIT 1
        """)
        result = await self.db.execute(query, {"category_id": category_id})
        row = result.fetchone()
        if row:
            return row.name
        return f"Kategori {category_id}"
    
    async def get_deal_details(self, deal_id: int) -> Optional[Dict[str, Any]]:
        """Get deal information with human-readable names"""
        query = text("""
            SELECT 
                d.id,
                d.title,
                d.stage_id,
                d.category_id,
                d.opportunity,
                d.currency_id as currency,
                d.date_create,
                d.date_modify,
                d.assigned_by_id,
                d.contact_id,
                d.company_id,
                d.comments,
                d.source_id,
                d.source_description,
                d.original_data as raw_data
            FROM bitrix.deals d
            WHERE d.id = :deal_id
        """)
        result = await self.db.execute(query, {"deal_id": deal_id})
        row = result.fetchone()
        if row:
            deal_data = dict(row._mapping)
            # Add human-readable names
            deal_data['stage_name'] = await self.get_stage_name(deal_data.get('stage_id'))
            deal_data['category_name'] = await self.get_category_name(deal_data.get('category_id'))
            return deal_data
        return None
    
    async def get_contact_details(self, contact_id) -> Optional[Dict[str, Any]]:
        """Get contact information with human-readable type name"""
        if contact_id is None:
            return None
        contact_id_str = str(contact_id)
        query = text("""
            SELECT 
                c.id,
                c.bitrix_id,
                c.name,
                c.second_name,
                c.last_name,
                c.full_name,
                c.phone,
                c.email,
                c.post,
                c.type_id,
                c.source_id,
                c.address,
                c.address_city,
                c.comments,
                c.date_create,
                c.date_modify,
                c.assigned_by_id
            FROM bitrix.contacts c
            WHERE c.bitrix_id = :contact_id_str
        """)
        result = await self.db.execute(query, {"contact_id_str": contact_id_str})
        row = result.fetchone()
        if row:
            contact_data = dict(row._mapping)
            # Add human-readable type name
            contact_data['type_name'] = await self.get_contact_type_name(contact_data.get('type_id'))
            return contact_data
        return None
    
    async def get_company_details(self, company_id) -> Optional[Dict[str, Any]]:
        """Get company information"""
        if company_id is None:
            return None
        company_id_str = str(company_id)
        query = text("""
            SELECT 
                c.id,
                c.title,
                c.industry,
                c.phone,
                c.email,
                c.address,
                c.comments
            FROM bitrix.companies c
            WHERE c.bitrix_id = :company_id_str
        """)
        result = await self.db.execute(query, {"company_id_str": company_id_str})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    
    async def get_activities(
        self, 
        deal_id: Optional[int] = None,
        contact_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get activities (calls, emails, meetings) related to deal or contact"""
        
        conditions = []
        params = {"limit": limit}
        
        if deal_id:
            conditions.append("a.owner_id = :deal_id AND a.owner_type_id = '2'")
            params["deal_id"] = str(deal_id)
        
        if contact_id:
            conditions.append("a.owner_id = :contact_id AND a.owner_type_id = '3'")
            params["contact_id"] = str(contact_id)
        
        if not conditions:
            return []
        
        where_clause = " OR ".join(conditions)
        
        query = text(f"""
            SELECT 
                a.id,
                a.subject,
                a.description,
                a.type_id,
                COALESCE(a.data->>'DIRECTION', '') as direction,
                COALESCE(a.data->>'COMPLETED', 'N') as completed,
                a.created,
                COALESCE(a.data->>'START_TIME', '') as start_time,
                COALESCE(a.data->>'END_TIME', '') as end_time,
                a.responsible_id
            FROM bitrix.activities a
            WHERE {where_clause}
            ORDER BY a.created DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_tasks(
        self, 
        deal_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get tasks related to a deal with responsible user names"""
        
        # Tasks might be linked via UF_CRM_TASK field in original_data
        query = text("""
            SELECT 
                t.id,
                t.bitrix_id,
                t.title,
                t.description,
                t.status,
                t.status_name,
                t.priority,
                t.created_date,
                t.deadline,
                t.closed_date,
                t.responsible_id,
                t.created_by,
                t.comments_count,
                CONCAT(u.name, ' ', u.last_name) as responsible_name,
                CONCAT(u2.name, ' ', u2.last_name) as created_by_name
            FROM bitrix.tasks t
            LEFT JOIN bitrix.users u ON t.responsible_id = u.id::varchar
            LEFT JOIN bitrix.users u2 ON t.created_by = u2.id::varchar
            WHERE t.original_data IS NOT NULL 
              AND t.original_data->>'UF_CRM_TASK' LIKE :deal_pattern
            ORDER BY t.created_date DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {
            "deal_pattern": f"%D_{deal_id}%",
            "limit": limit
        })
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_task_comments(
        self, 
        task_ids: List[int],
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get ALL comments for specific tasks - no limit on important data"""
        
        if not task_ids:
            return []
        
        query = text("""
            SELECT 
                tc.id,
                tc.task_id,
                tc.bitrix_id,
                tc.post_message as message,
                tc.post_message_html as message_html,
                tc.post_date,
                tc.author_id,
                tc.author_name,
                tc.author_email
            FROM bitrix.task_comments tc
            WHERE tc.task_id = ANY(:task_ids)
            ORDER BY tc.post_date ASC NULLS LAST
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {
            "task_ids": task_ids,
            "limit": limit
        })
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_user_name(self, user_id: int) -> str:
        """Get user name by ID"""
        query = text("""
            SELECT 
                CONCAT(name, ' ', last_name) as full_name
            FROM bitrix.users
            WHERE id = :user_id
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        if row:
            return row.full_name or f"Kullanıcı #{user_id}"
        return f"Kullanıcı #{user_id}"
    
    async def get_all_contact_deals(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get ALL deals for a contact with full details"""
        if not contact_id:
            return []
        
        query = text("""
            SELECT 
                d.id,
                d.title,
                d.stage_id,
                d.category_id,
                d.opportunity,
                d.currency_id as currency,
                d.date_create,
                d.date_modify,
                d.assigned_by_id,
                d.comments,
                d.source_id,
                CONCAT(u.name, ' ', u.last_name) as assigned_by_name
            FROM bitrix.deals d
            LEFT JOIN bitrix.users u ON d.assigned_by_id = u.id::varchar
            WHERE d.contact_id = :contact_id
            ORDER BY d.date_modify DESC NULLS LAST
        """)
        
        result = await self.db.execute(query, {"contact_id": contact_id})
        deals = []
        for row in result.fetchall():
            deal_data = dict(row._mapping)
            # Add human-readable names
            deal_data['stage_name'] = await self.get_stage_name(deal_data.get('stage_id'))
            deal_data['category_name'] = await self.get_category_name(deal_data.get('category_id'))
            deals.append(deal_data)
        
        return deals
    
    async def get_activities_for_deals(
        self, 
        deal_ids: List[int],
        contact_id: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get activities for multiple deals and/or contact"""
        
        conditions = []
        params = {"limit": limit}
        
        if deal_ids:
            deal_ids_str = [str(d) for d in deal_ids]
            conditions.append("(a.owner_id = ANY(:deal_ids) AND a.owner_type_id = '2')")
            params["deal_ids"] = deal_ids_str
        
        if contact_id:
            if conditions:
                conditions.append(f"(a.owner_id = :contact_id AND a.owner_type_id = '3')")
            else:
                conditions.append("a.owner_id = :contact_id AND a.owner_type_id = '3'")
            params["contact_id"] = contact_id
        
        if not conditions:
            return []
        
        where_clause = " OR ".join(conditions)
        
        query = text(f"""
            SELECT 
                a.id,
                a.bitrix_id,
                a.subject,
                a.description,
                a.type_id,
                a.owner_id,
                a.owner_type_id,
                COALESCE(a.data->>'DIRECTION', '') as direction,
                COALESCE(a.data->>'COMPLETED', 'N') as completed,
                a.created,
                COALESCE(a.data->>'START_TIME', '') as start_time,
                COALESCE(a.data->>'END_TIME', '') as end_time,
                a.responsible_id,
                CONCAT(u.name, ' ', u.last_name) as responsible_name
            FROM bitrix.activities a
            LEFT JOIN bitrix.users u ON a.responsible_id = u.id::varchar
            WHERE {where_clause}
            ORDER BY a.created DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_tasks_for_deals(
        self, 
        deal_ids: List[int],
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get tasks for multiple deals"""
        
        if not deal_ids:
            return []
        
        # Build pattern for multiple deals
        patterns = [f"D_{d}" for d in deal_ids]
        pattern_conditions = " OR ".join([f"t.original_data->>'UF_CRM_TASK' LIKE '%{p}%'" for p in patterns])
        
        query = text(f"""
            SELECT 
                t.id,
                t.bitrix_id,
                t.title,
                t.description,
                t.status,
                t.status_name,
                t.priority,
                t.created_date,
                t.deadline,
                t.closed_date,
                t.responsible_id,
                t.created_by,
                t.comments_count,
                t.original_data->>'UF_CRM_TASK' as crm_task_link,
                CONCAT(u.name, ' ', u.last_name) as responsible_name,
                CONCAT(u2.name, ' ', u2.last_name) as created_by_name
            FROM bitrix.tasks t
            LEFT JOIN bitrix.users u ON t.responsible_id = u.id::varchar
            LEFT JOIN bitrix.users u2 ON t.created_by = u2.id::varchar
            WHERE t.original_data IS NOT NULL 
              AND ({pattern_conditions})
            ORDER BY t.created_date DESC NULLS LAST
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {"limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def collect_all_data(self, deal_id: int) -> Dict[str, Any]:
        """
        Collect all data related to a deal for AI summarization
        Enhanced: Collects ALL deals for the contact with full details
        """
        logger.info("collecting_customer_data", deal_id=deal_id)
        
        # Get main deal details
        deal = await self.get_deal_details(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Get contact if linked
        contact = None
        all_contact_deals = []
        if deal.get("contact_id"):
            try:
                contact = await self.get_contact_details(deal["contact_id"])
                # Get ALL deals for this contact
                all_contact_deals = await self.get_all_contact_deals(str(deal["contact_id"]))
            except (ValueError, TypeError):
                pass
        
        # Get company if linked
        company = None
        if deal.get("company_id"):
            try:
                company = await self.get_company_details(int(deal["company_id"]))
            except (ValueError, TypeError):
                pass
        
        # Get all deal IDs for this contact
        all_deal_ids = [d["id"] for d in all_contact_deals] if all_contact_deals else [deal_id]
        
        # Get activities for ALL deals and contact
        activities = await self.get_activities_for_deals(
            deal_ids=all_deal_ids,
            contact_id=str(deal["contact_id"]) if deal.get("contact_id") else None
        )
        
        # Get tasks for ALL deals
        tasks = await self.get_tasks_for_deals(deal_ids=all_deal_ids)
        
        # Get ALL task comments
        task_ids = [t["id"] for t in tasks if t.get("id")]
        task_comments = await self.get_task_comments(task_ids) if task_ids else []
        
        # Get responsible user name for main deal
        responsible_name = None
        if deal.get("assigned_by_id"):
            try:
                responsible_name = await self.get_user_name(int(deal["assigned_by_id"]))
            except (ValueError, TypeError):
                pass
        
        return {
            "deal": deal,
            "contact": contact,
            "company": company,
            "all_contact_deals": all_contact_deals,
            "activities": activities,
            "tasks": tasks,
            "task_comments": task_comments,
            "responsible_name": responsible_name,
            "collected_at": datetime.now().isoformat()
        }


class AISummarizer:
    """
    AI-powered customer journey summarizer
    """
    
    def __init__(
        self,
        provider: AIProvider = AIProvider.OPENAI,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider
        self.api_key = api_key or self._get_default_api_key(provider)
        
        # Default models per provider
        self.model = model or {
            AIProvider.OPENAI: "gpt-4o-mini",
            AIProvider.CLAUDE: "claude-3-haiku-20240307",
            AIProvider.GEMINI: "gemini-1.5-flash",
            AIProvider.OPENROUTER: "x-ai/grok-4.1-fast:free",
            AIProvider.OLLAMA: "llama3.2"
        }.get(provider, "gpt-4o-mini")
        
        self.timeout = 60
    
    def _get_default_api_key(self, provider: AIProvider) -> Optional[str]:
        """Get default API key for provider from environment"""
        key_mapping = {
            AIProvider.OPENAI: "OPENAI_API_KEY",
            AIProvider.CLAUDE: "ANTHROPIC_API_KEY",
            AIProvider.GEMINI: "GEMINI_API_KEY",
            AIProvider.OPENROUTER: "OPENROUTER_API_KEY",
            AIProvider.OLLAMA: None  # Ollama doesn't need API key
        }
        env_key = key_mapping.get(provider)
        if env_key:
            return os.getenv(env_key)
        return None
    
    def _build_prompt(self, customer_data: Dict[str, Any]) -> str:
        """Build the summarization prompt - Real Estate Boss perspective"""
        
        deal = customer_data.get("deal", {})
        contact = customer_data.get("contact", {})
        company = customer_data.get("company", {})
        all_contact_deals = customer_data.get("all_contact_deals", [])
        activities = customer_data.get("activities", [])
        tasks = customer_data.get("tasks", [])
        task_comments = customer_data.get("task_comments", [])
        responsible_name = customer_data.get("responsible_name", "Bilinmiyor")
        
        # Build context sections
        sections = []
        
        # Contact Info - ENHANCED with type name
        if contact:
            contact_name = contact.get('full_name') or f"{contact.get('name', '')} {contact.get('second_name', '')} {contact.get('last_name', '')}".strip()
            contact_type = contact.get('type_name', contact.get('type_id', 'Belirtilmemiş'))
            
            sections.append(f"""
## 👤 KİŞİ BİLGİLERİ
- **Ad Soyad:** {contact_name or 'Belirtilmemiş'}
- **Kişi Türü:** {contact_type}
- **Telefon:** {contact.get('phone', 'Belirtilmemiş')}
- **E-posta:** {contact.get('email', 'Belirtilmemiş')}
- **Pozisyon/Unvan:** {contact.get('post', 'Belirtilmemiş')}
- **Adres:** {contact.get('address', '')} {contact.get('address_city', '')}
- **Kayıt Tarihi:** {contact.get('date_create', 'Belirtilmemiş')}
- **Son Güncelleme:** {contact.get('date_modify', 'Belirtilmemiş')}
- **Notlar:** {contact.get('comments', 'Yok')[:500] if contact.get('comments') else 'Yok'}
""")
        
        # Company Info
        if company:
            sections.append(f"""
## 🏢 FİRMA BİLGİLERİ
- **Firma Adı:** {company.get('title', 'Belirtilmemiş')}
- **Sektör:** {company.get('industry', 'Belirtilmemiş')}
- **Telefon:** {company.get('phone', 'Belirtilmemiş')}
- **E-posta:** {company.get('email', 'Belirtilmemiş')}
- **Adres:** {company.get('address', 'Belirtilmemiş')}
""")
        
        # ALL DEALS for this contact - ENHANCED with stage names
        if all_contact_deals:
            deals_texts = []
            total_opportunity = 0
            for d in all_contact_deals:
                stage_name = d.get('stage_name', d.get('stage_id', 'Bilinmiyor'))
                category_name = d.get('category_name', d.get('category_id', ''))
                opportunity = float(d.get('opportunity', 0) or 0)
                total_opportunity += opportunity
                currency = d.get('currency', 'TRY')
                assigned = d.get('assigned_by_name', 'Atanmamış')
                is_main = "⭐ " if d.get('id') == deal.get('id') else ""
                
                deals_texts.append(
                    f"- {is_main}**{d.get('title', 'Başlıksız')}**\n"
                    f"  - Kategori: {category_name}\n"
                    f"  - Aşama: {stage_name}\n"
                    f"  - Tutar: {opportunity:,.0f} {currency}\n"
                    f"  - Sorumlu: {assigned}\n"
                    f"  - Oluşturma: {format_date(d.get('date_create'))}\n"
                    f"  - Son Güncelleme: {format_date(d.get('date_modify'))}"
                )
            
            sections.append(f"""
## 📋 KİŞİYE AİT TÜM ANLAŞMALAR ({len(all_contact_deals)} adet)
**Toplam Potansiyel Değer:** {total_opportunity:,.0f} TRY

{chr(10).join(deals_texts)}
""")
        else:
            # Single deal info - ENHANCED with stage name
            stage_name = deal.get('stage_name', deal.get('stage_id', 'Belirtilmemiş'))
            category_name = deal.get('category_name', deal.get('category_id', ''))
            
            sections.append(f"""
## 📋 ANLAŞMA BİLGİLERİ
- **Başlık:** {deal.get('title', 'Belirtilmemiş')}
- **Kategori:** {category_name}
- **Aşama:** {stage_name}
- **Tutar:** {deal.get('opportunity', '0')} {deal.get('currency', 'TRY')}
- **Oluşturma:** {deal.get('date_create', 'Belirtilmemiş')}
- **Son Güncelleme:** {deal.get('date_modify', 'Belirtilmemiş')}
- **Sorumlu:** {responsible_name}
- **Notlar:** {deal.get('comments', 'Yok')[:500] if deal.get('comments') else 'Yok'}
""")
        
        # ALL Activities - ENHANCED with responsible names
        if activities:
            # Group activities by type
            calls = [a for a in activities if str(a.get("type_id")) == "2"]
            emails = [a for a in activities if str(a.get("type_id")) == "1"]
            meetings = [a for a in activities if str(a.get("type_id")) == "3"]
            other_activities = [a for a in activities if str(a.get("type_id")) not in ["1", "2", "3"]]
            
            activity_texts = []
            
            # Phone calls
            if calls:
                activity_texts.append(f"\n### 📞 ARAMALAR ({len(calls)} adet)")
                for a in calls[:30]:
                    direction = "📥 Gelen" if a.get("direction") == "1" else "📤 Giden"
                    completed = "✅" if a.get("completed") == "Y" else "⏳"
                    responsible = a.get('responsible_name', 'Bilinmiyor')
                    desc = a.get("description", "")[:300] if a.get("description") else ""
                    desc = desc.replace("\n", " ").strip()
                    
                    call_text = f"- {completed} **{format_datetime(a.get('created'))}** | {direction} | Sorumlu: {responsible}"
                    if a.get('subject'):
                        call_text += f"\n  - Konu: {a.get('subject')}"
                    if desc:
                        call_text += f"\n  - Not: {desc}"
                    activity_texts.append(call_text)
            
            # Emails
            if emails:
                activity_texts.append(f"\n### 📧 E-POSTALAR ({len(emails)} adet)")
                for a in emails[:20]:
                    direction = "📥 Gelen" if a.get("direction") == "1" else "📤 Giden"
                    completed = "✅" if a.get("completed") == "Y" else "⏳"
                    responsible = a.get('responsible_name', 'Bilinmiyor')
                    
                    activity_texts.append(
                        f"- {completed} **{format_datetime(a.get('created'))}** | {direction} | {a.get('subject', 'Konu yok')} | Sorumlu: {responsible}"
                    )
            
            # Meetings
            if meetings:
                activity_texts.append(f"\n### 🤝 TOPLANTI/GÖRÜŞMELer ({len(meetings)} adet)")
                for a in meetings[:20]:
                    completed = "✅" if a.get("completed") == "Y" else "⏳"
                    responsible = a.get('responsible_name', 'Bilinmiyor')
                    desc = a.get("description", "")[:200] if a.get("description") else ""
                    
                    meeting_text = f"- {completed} **{format_datetime(a.get('created'))}** | {a.get('subject', 'Konu yok')} | Sorumlu: {responsible}"
                    if desc:
                        meeting_text += f"\n  - Detay: {desc}"
                    activity_texts.append(meeting_text)
            
            # Other activities
            if other_activities:
                activity_texts.append(f"\n### 📌 DİĞER AKTİVİTELER ({len(other_activities)} adet)")
                for a in other_activities[:15]:
                    completed = "✅" if a.get("completed") == "Y" else "⏳"
                    responsible = a.get('responsible_name', 'Bilinmiyor')
                    activity_texts.append(
                        f"- {completed} {format_datetime(a.get('created'))} | {a.get('subject', 'Konu yok')} | Sorumlu: {responsible}"
                    )
            
            sections.append(f"""
## 📊 TÜM AKTİVİTELER ({len(activities)} kayıt)
- Toplam Arama: {len(calls)}
- Toplam E-posta: {len(emails)}
- Toplam Toplantı: {len(meetings)}
- Diğer: {len(other_activities)}

{chr(10).join(activity_texts)}
""")
        
        # ALL Tasks with full details - ENHANCED
        if tasks:
            task_texts = []
            for t in tasks:
                status_name = t.get('status_name') or {
                    1: "Yeni", 2: "Bekliyor", 3: "Devam Ediyor", 
                    4: "Ertelendi", 5: "Tamamlandı", 6: "İptal"
                }.get(t.get('status'), 'Bilinmiyor')
                
                priority_name = {1: "Düşük", 2: "Normal", 3: "Yüksek"}.get(t.get('priority'), '')
                
                status_icon = {
                    "Tamamlandı": "✅", "Yeni": "🆕", "Bekliyor": "⏳",
                    "Devam Ediyor": "🔄", "Ertelendi": "📅", "İptal": "❌"
                }.get(status_name, "📋")
                
                responsible = t.get('responsible_name', 'Atanmamış')
                created_by = t.get('created_by_name', 'Bilinmiyor')
                
                task_text = f"""
### {status_icon} {t.get('title', 'Başlık yok')}
- **Durum:** {status_name} | **Öncelik:** {priority_name}
- **Sorumlu:** {responsible}
- **Oluşturan:** {created_by}
- **Oluşturma:** {format_datetime(t.get('created_date'))}
- **Son Tarih:** {format_datetime(t.get('deadline')) if t.get('deadline') else 'Belirsiz'}
- **Yorum Sayısı:** {t.get('comments_count', 0)}"""
                
                # Add task description if exists
                if t.get('description'):
                    desc = t.get('description', '')[:500]
                    task_text += f"\n- **Açıklama:** {desc}"
                
                # Add related comments for this task
                task_id = t.get('id')
                related_comments = [c for c in task_comments if c.get('task_id') == task_id]
                if related_comments:
                    task_text += f"\n\n**Yorumlar ({len(related_comments)} adet):**"
                    for c in related_comments:
                        msg = c.get("message", "")[:400] if c.get("message") else ""
                        msg = msg.replace("\n", " ").strip()
                        if msg:
                            post_date = format_datetime(c.get('post_date'))
                            author = c.get('author_name', 'Anonim')
                            task_text += f"\n  - 💬 [{post_date}] **{author}:** {msg}"
                
                task_texts.append(task_text)
            
            # Task summary stats
            completed_tasks = len([t for t in tasks if t.get('status') == 5])
            pending_tasks = len([t for t in tasks if t.get('status') in [1, 2, 3]])
            overdue_tasks = len([t for t in tasks if t.get('deadline') and t.get('status') not in [5, 6] 
                               and format_date(t.get('deadline')) < datetime.now().strftime('%Y-%m-%d')])
            
            sections.append(f"""
## ✅ TÜM GÖREVLER ({len(tasks)} adet)

**Özet İstatistikler:**
- ✅ Tamamlanan: {completed_tasks}
- ⏳ Devam Eden/Bekleyen: {pending_tasks}
- ⚠️ Geciken: {overdue_tasks}
- 💬 Toplam Yorum: {len(task_comments)}

{chr(10).join(task_texts)}
""")
        
        context = "\n".join(sections)
        
        prompt = f"""Sen **Japon Konutları gayrimenkul şirketinin patronu/CEO'susun**. Deneyimli bir gayrimenkul yöneticisi olarak satış ekibinin performansını ve müşteri süreçlerini değerlendiriyorsun.

🏠 **GAYRİMENKUL PATRONU OLARAK ANALİZ ET:**
- Ekip üyelerinin performansını değerlendir
- Müşteri ile yapılan görüşmeleri, aramaları, toplantıları incele
- Görevlerin zamanında yapılıp yapılmadığını kontrol et
- Yorumlardan müşterinin durumunu ve potansiyelini anla
- Her personelin ne yaptığını görebilmek istiyorsun

{context}

---

**LÜTFEN AŞAĞIDAKİ FORMATTA DETAYLI ANALİZ HAZIRLA (Markdown formatı):**

## 🏠 GAYRİMENKUL PATRONU RAPORU

### 🎯 GENEL DEĞERLENDİRME
(Tek paragrafta: Müşterinin durumu, potansiyeli ve sürecin özeti)

---

### 👤 MÜŞTERİ PROFİLİ

| Bilgi | Değer |
|-------|-------|
| Ad Soyad | ... |
| Müşteri Tipi | ... |
| Telefon/E-posta | ... |
| Toplam Anlaşma Sayısı | ... |
| Toplam Potansiyel Değer | ... |

---

### 📊 ANLAŞMA DURUMU ANALİZİ
(Her anlaşma için aşama, değer ve son durumu belirt - ID yerine AŞAMA ADI kullan)

---

### 👥 PERSONEL PERFORMANSI

**Kim Ne Yapmış?**
(Her personelin yaptığı işleri listele - aramalar, toplantılar, görevler)

| Personel | Yaptığı İşler | Değerlendirme |
|----------|---------------|---------------|
| ... | ... | 👍/👎/⚠️ |

---

### 📞 İLETİŞİM ANALİZİ
- Toplam arama sayısı ve sonuçları
- Gelen vs Giden arama oranı
- Son iletişim ne zaman yapıldı?
- İletişim sıklığı yeterli mi?

---

### ✅ GÖREV TAKİBİ
- Tamamlanan görevler
- Geciken/bekleyen görevler
- Yorumlardan çıkan önemli notlar

---

### ⚠️ KRİTİK BULGULAR

**🔴 Dikkat Edilmesi Gerekenler:**
(Riskler, eksiklikler, geciken işler)

**🟢 İyi Giden Şeyler:**
(Başarılı çalışmalar, fırsatlar)

---

### 📋 PATRON OLARAK TALİMATLARIM

**Acil Yapılması Gerekenler (Bu Hafta):**
1. ...
2. ...

**Sorumlu Personele Notlar:**
- ...

---

### 💰 TAHMİN

**Satış Kapanma Olasılığı:** %X
**Tahmini Kapanma Süresi:** X hafta
**Önerilen Yaklaşım:** (Agresif takip / Bekle-gör / Yeniden değerlendir)

---

**🏠 PATRON'UN SON SÖZÜ:**
(Tek cümlede: Bu müşteri için ne yapmalıyız?)

---

**ÖNEMLI KURALLAR:**
- Türkçe yaz
- Patron/CEO gibi düşün, kritik ol, personeli değerlendir
- Aşama ID'leri yerine AŞAMA ADLARINI kullan
- Her personelin ne yaptığını göster
- Somut verilerle konuş
- Belirsiz bilgileri "Bilinmiyor" olarak belirt
- Markdown formatını düzgün kullan
"""
        
        return prompt
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Sen Japon Konutları gayrimenkul şirketinin patronu/CEO'susun. Satış ekibinin performansını değerlendiren, müşteri süreçlerini analiz eden, personelin yaptığı işleri inceleyen deneyimli bir gayrimenkul yöneticisisin. Türkçe Markdown formatında detaylı ve kritik raporlar hazırlarsın. Aşama ID'leri yerine aşama adlarını kullanırsın."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _call_claude(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 4000,
                    "system": "Sen Japon Konutları gayrimenkul şirketinin patronu/CEO'susun. Satış ekibinin performansını değerlendiren, müşteri süreçlerini analiz eden, personelin yaptığı işleri inceleyen deneyimli bir gayrimenkul yöneticisisin. Türkçe Markdown formatında detaylı ve kritik raporlar hazırlarsın.",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["content"][0]["text"]
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API"""
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # Ollama can be slower
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["response"]
    
    async def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "maxOutputTokens": 4000,
                        "temperature": 0.7
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
            
            data = response.json()
            # Gemini response structure: candidates[0].content.parts[0].text
            candidates = data.get("candidates", [])
            if not candidates:
                raise Exception("Gemini API returned no candidates")
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise Exception("Gemini API returned no content parts")
            
            return parts[0].get("text", "")
    
    async def _call_openrouter(self, prompt: str) -> str:
        """Call OpenRouter API (OpenAI-compatible)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://bitsheet24.local"),
                    "X-Title": "BitSheet24 AI Summary"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Sen Japon Konutları gayrimenkul şirketinin patronu/CEO'susun. Satış ekibinin performansını değerlendiren, müşteri süreçlerini analiz eden, personelin yaptığı işleri inceleyen deneyimli bir gayrimenkul yöneticisisin. Türkçe Markdown formatında detaylı ve kritik raporlar hazırlarsın. Aşama ID'leri yerine aşama adlarını kullanırsın."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.7
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def generate_summary(self, customer_data: Dict[str, Any]) -> str:
        """
        Generate AI summary from customer data
        """
        prompt = self._build_prompt(customer_data)
        
        logger.info(
            "generating_ai_summary",
            provider=self.provider,
            model=self.model,
            deal_id=customer_data.get("deal", {}).get("id")
        )
        
        try:
            if self.provider == AIProvider.OPENAI:
                summary = await self._call_openai(prompt)
            elif self.provider == AIProvider.CLAUDE:
                summary = await self._call_claude(prompt)
            elif self.provider == AIProvider.GEMINI:
                summary = await self._call_gemini(prompt)
            elif self.provider == AIProvider.OPENROUTER:
                summary = await self._call_openrouter(prompt)
            elif self.provider == AIProvider.OLLAMA:
                summary = await self._call_ollama(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            
            logger.info(
                "ai_summary_generated",
                provider=self.provider,
                summary_length=len(summary)
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "ai_summary_failed",
                provider=self.provider,
                error=str(e)
            )
            raise


class BitrixSummaryWriter:
    """
    Writes AI summaries back to Bitrix24 deals
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or settings.bitrix24_webhook_url
        self.timeout = 30
    
    async def update_deal_comment(
        self, 
        deal_id: int, 
        summary: str,
        append: bool = True
    ) -> Dict[str, Any]:
        """
        Update deal COMMENTS field with AI summary
        
        Args:
            deal_id: Bitrix24 deal ID
            summary: AI generated summary
            append: If True, append to existing comments; if False, replace
        """
        
        # Format the summary with timestamp
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        formatted_summary = f"""
═══════════════════════════════════════
🤖 AI MÜŞTERİ SÜRECİ ÖZETİ
📅 {timestamp}
═══════════════════════════════════════

{summary}

═══════════════════════════════════════
"""
        
        try:
            async with httpx.AsyncClient() as client:
                # If append mode, first get existing comments
                if append:
                    get_response = await client.post(
                        f"{self.webhook_url}/crm.deal.get",
                        data={"id": deal_id},
                        timeout=self.timeout
                    )
                    if get_response.status_code == 200:
                        deal_data = get_response.json().get("result", {})
                        existing_comments = deal_data.get("COMMENTS", "") or ""
                        formatted_summary = existing_comments + "\n\n" + formatted_summary
                
                # Update the deal
                response = await client.post(
                    f"{self.webhook_url}/crm.deal.update",
                    data={
                        "id": deal_id,
                        "fields[COMMENTS]": formatted_summary
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("result"):
                        logger.info(
                            "bitrix_deal_updated",
                            deal_id=deal_id,
                            success=True
                        )
                        return {
                            "success": True,
                            "deal_id": deal_id,
                            "message": "Özet başarıyla Bitrix24'e yazıldı"
                        }
                
                logger.warning(
                    "bitrix_deal_update_failed",
                    deal_id=deal_id,
                    response=response.text
                )
                return {
                    "success": False,
                    "deal_id": deal_id,
                    "error": "Bitrix24 güncelleme başarısız"
                }
                
        except Exception as e:
            logger.error(
                "bitrix_deal_update_error",
                deal_id=deal_id,
                error=str(e)
            )
            return {
                "success": False,
                "deal_id": deal_id,
                "error": str(e)
            }
    
    async def add_deal_timeline_comment(
        self,
        deal_id: int,
        summary: str
    ) -> Dict[str, Any]:
        """
        Add summary as a timeline comment (more visible in Bitrix24)
        """
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        comment_text = f"""🤖 <b>AI MÜŞTERİ SÜRECİ ÖZETİ</b>
<i>Oluşturulma: {timestamp}</i>

{summary}"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.webhook_url}/crm.timeline.comment.add",
                    data={
                        "fields[ENTITY_ID]": deal_id,
                        "fields[ENTITY_TYPE]": "deal",
                        "fields[COMMENT]": comment_text
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("result"):
                        logger.info(
                            "bitrix_timeline_comment_added",
                            deal_id=deal_id,
                            comment_id=result.get("result")
                        )
                        return {
                            "success": True,
                            "deal_id": deal_id,
                            "comment_id": result.get("result"),
                            "message": "Özet timeline'a eklendi"
                        }
                
                return {
                    "success": False,
                    "deal_id": deal_id,
                    "error": "Timeline yorumu eklenemedi"
                }
                
        except Exception as e:
            logger.error(
                "bitrix_timeline_error",
                deal_id=deal_id,
                error=str(e)
            )
            return {
                "success": False,
                "deal_id": deal_id,
                "error": str(e)
            }
