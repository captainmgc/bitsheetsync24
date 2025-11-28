"""
AI Customer Journey Summarizer Service
Generates intelligent summaries of customer interactions using AI
Supports: OpenAI GPT-4, Claude, or local Ollama models
"""

import httpx
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import settings

logger = structlog.get_logger()


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
    for AI summarization
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_deal_details(self, deal_id: int) -> Optional[Dict[str, Any]]:
        """Get deal information"""
        query = text("""
            SELECT 
                d.id,
                d.data->>'TITLE' as title,
                d.data->>'STAGE_ID' as stage_id,
                d.data->>'OPPORTUNITY' as opportunity,
                d.data->>'CURRENCY_ID' as currency,
                d.data->>'DATE_CREATE' as date_create,
                d.data->>'DATE_MODIFY' as date_modify,
                d.data->>'ASSIGNED_BY_ID' as assigned_by_id,
                d.data->>'CONTACT_ID' as contact_id,
                d.data->>'COMPANY_ID' as company_id,
                d.data->>'COMMENTS' as comments,
                d.data->>'SOURCE_ID' as source_id,
                d.data->>'SOURCE_DESCRIPTION' as source_description,
                d.data as raw_data
            FROM bitrix.deals d
            WHERE d.id = :deal_id
        """)
        result = await self.db.execute(query, {"deal_id": deal_id})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    
    async def get_contact_details(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Get contact information"""
        query = text("""
            SELECT 
                c.id,
                c.data->>'NAME' as name,
                c.data->>'LAST_NAME' as last_name,
                c.data->>'PHONE' as phone,
                c.data->>'EMAIL' as email,
                c.data->>'POST' as post,
                c.data->>'COMMENTS' as comments,
                c.data->>'DATE_CREATE' as date_create
            FROM bitrix.contacts c
            WHERE c.id = :contact_id
        """)
        result = await self.db.execute(query, {"contact_id": contact_id})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    
    async def get_company_details(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company information"""
        query = text("""
            SELECT 
                c.id,
                c.data->>'TITLE' as title,
                c.data->>'INDUSTRY' as industry,
                c.data->>'PHONE' as phone,
                c.data->>'EMAIL' as email,
                c.data->>'ADDRESS' as address,
                c.data->>'COMMENTS' as comments
            FROM bitrix.companies c
            WHERE c.id = :company_id
        """)
        result = await self.db.execute(query, {"company_id": company_id})
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
            conditions.append("(a.data->>'OWNER_ID')::int = :deal_id AND a.data->>'OWNER_TYPE_ID' = '2'")
            params["deal_id"] = deal_id
        
        if contact_id:
            conditions.append("(a.data->>'OWNER_ID')::int = :contact_id AND a.data->>'OWNER_TYPE_ID' = '3'")
            params["contact_id"] = contact_id
        
        if not conditions:
            return []
        
        where_clause = " OR ".join(conditions)
        
        query = text(f"""
            SELECT 
                a.id,
                a.data->>'SUBJECT' as subject,
                a.data->>'DESCRIPTION' as description,
                a.data->>'TYPE_ID' as type_id,
                a.data->>'DIRECTION' as direction,
                a.data->>'COMPLETED' as completed,
                a.data->>'CREATED' as created,
                a.data->>'START_TIME' as start_time,
                a.data->>'END_TIME' as end_time,
                a.data->>'RESPONSIBLE_ID' as responsible_id
            FROM bitrix.activities a
            WHERE {where_clause}
            ORDER BY (a.data->>'CREATED')::timestamp DESC
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_tasks(
        self, 
        deal_id: Optional[int] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get tasks related to a deal"""
        
        # Tasks might be linked via UF_CRM_TASK field
        query = text("""
            SELECT 
                t.id,
                t.data->>'TITLE' as title,
                t.data->>'DESCRIPTION' as description,
                t.data->>'STATUS' as status,
                t.data->>'PRIORITY' as priority,
                t.data->>'CREATED_DATE' as created_date,
                t.data->>'DEADLINE' as deadline,
                t.data->>'CLOSED_DATE' as closed_date,
                t.data->>'RESPONSIBLE_ID' as responsible_id,
                t.data->>'CREATED_BY' as created_by
            FROM bitrix.tasks t
            WHERE t.data->>'UF_CRM_TASK' LIKE :deal_pattern
               OR t.data->'UF_CRM_TASK' @> :deal_json
            ORDER BY (t.data->>'CREATED_DATE')::timestamp DESC
            LIMIT :limit
        """)
        
        result = await self.db.execute(query, {
            "deal_pattern": f"%D_{deal_id}%",
            "deal_json": json.dumps([f"D_{deal_id}"]),
            "limit": limit
        })
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_task_comments(
        self, 
        task_ids: List[int],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get comments for specific tasks"""
        
        if not task_ids:
            return []
        
        query = text("""
            SELECT 
                tc.id,
                tc.data->>'TASK_ID' as task_id,
                tc.data->>'POST_MESSAGE' as message,
                tc.data->>'POST_DATE' as post_date,
                tc.data->>'AUTHOR_ID' as author_id,
                tc.data->>'AUTHOR_NAME' as author_name
            FROM bitrix.task_comments tc
            WHERE (tc.data->>'TASK_ID')::int = ANY(:task_ids)
            ORDER BY (tc.data->>'POST_DATE')::timestamp DESC
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
                CONCAT(data->>'NAME', ' ', data->>'LAST_NAME') as full_name
            FROM bitrix.users
            WHERE id = :user_id
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        if row:
            return row.full_name or f"Kullanıcı #{user_id}"
        return f"Kullanıcı #{user_id}"
    
    async def collect_all_data(self, deal_id: int) -> Dict[str, Any]:
        """
        Collect all data related to a deal for AI summarization
        """
        logger.info("collecting_customer_data", deal_id=deal_id)
        
        # Get deal details
        deal = await self.get_deal_details(deal_id)
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Get contact if linked
        contact = None
        if deal.get("contact_id"):
            try:
                contact = await self.get_contact_details(int(deal["contact_id"]))
            except (ValueError, TypeError):
                pass
        
        # Get company if linked
        company = None
        if deal.get("company_id"):
            try:
                company = await self.get_company_details(int(deal["company_id"]))
            except (ValueError, TypeError):
                pass
        
        # Get activities
        activities = await self.get_activities(
            deal_id=deal_id,
            contact_id=int(deal["contact_id"]) if deal.get("contact_id") else None
        )
        
        # Get tasks
        tasks = await self.get_tasks(deal_id=deal_id)
        
        # Get task comments
        task_ids = [t["id"] for t in tasks if t.get("id")]
        task_comments = await self.get_task_comments(task_ids) if task_ids else []
        
        # Get responsible user name
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
            AIProvider.OPENROUTER: "openai/gpt-4o-mini",
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
        """Build the summarization prompt"""
        
        deal = customer_data.get("deal", {})
        contact = customer_data.get("contact", {})
        company = customer_data.get("company", {})
        activities = customer_data.get("activities", [])
        tasks = customer_data.get("tasks", [])
        task_comments = customer_data.get("task_comments", [])
        responsible_name = customer_data.get("responsible_name", "Bilinmiyor")
        
        # Build context sections
        sections = []
        
        # Deal Info
        sections.append(f"""
## ANLAŞMA BİLGİLERİ
- Başlık: {deal.get('title', 'Belirtilmemiş')}
- Aşama: {deal.get('stage_id', 'Belirtilmemiş')}
- Tutar: {deal.get('opportunity', '0')} {deal.get('currency', 'TRY')}
- Oluşturma: {deal.get('date_create', 'Belirtilmemiş')}
- Son Güncelleme: {deal.get('date_modify', 'Belirtilmemiş')}
- Sorumlu: {responsible_name}
- Kaynak: {deal.get('source_id', 'Belirtilmemiş')}
- Notlar: {deal.get('comments', 'Yok')[:500] if deal.get('comments') else 'Yok'}
""")
        
        # Contact Info
        if contact:
            contact_name = f"{contact.get('name', '')} {contact.get('last_name', '')}".strip()
            sections.append(f"""
## MÜŞTERİ BİLGİLERİ
- Ad Soyad: {contact_name or 'Belirtilmemiş'}
- Telefon: {contact.get('phone', 'Belirtilmemiş')}
- E-posta: {contact.get('email', 'Belirtilmemiş')}
- Pozisyon: {contact.get('post', 'Belirtilmemiş')}
""")
        
        # Company Info
        if company:
            sections.append(f"""
## FİRMA BİLGİLERİ
- Firma: {company.get('title', 'Belirtilmemiş')}
- Sektör: {company.get('industry', 'Belirtilmemiş')}
- Adres: {company.get('address', 'Belirtilmemiş')}
""")
        
        # Activities
        if activities:
            activity_texts = []
            for a in activities[:20]:  # Limit to 20
                type_map = {
                    "1": "E-posta",
                    "2": "Arama",
                    "3": "Toplantı",
                    "4": "Görev"
                }
                a_type = type_map.get(str(a.get("type_id")), "Aktivite")
                direction = "Gelen" if a.get("direction") == "1" else "Giden"
                completed = "✓" if a.get("completed") == "Y" else "○"
                
                desc = a.get("description", "")[:200] if a.get("description") else ""
                activity_texts.append(
                    f"- [{completed}] {a.get('created', '')}: {a_type} ({direction}) - {a.get('subject', 'Konu yok')}"
                    + (f"\n  {desc}" if desc else "")
                )
            
            sections.append(f"""
## AKTİVİTELER ({len(activities)} kayıt)
{chr(10).join(activity_texts)}
""")
        
        # Tasks
        if tasks:
            task_texts = []
            for t in tasks[:15]:
                status_map = {
                    "1": "Yeni",
                    "2": "Bekliyor",
                    "3": "Devam Ediyor",
                    "4": "Ertelendi",
                    "5": "Tamamlandı",
                    "6": "İptal"
                }
                t_status = status_map.get(str(t.get("status")), "Bilinmiyor")
                task_texts.append(
                    f"- [{t_status}] {t.get('title', 'Başlık yok')} (Son: {t.get('deadline', 'Belirsiz')})"
                )
            
            sections.append(f"""
## GÖREVLER ({len(tasks)} kayıt)
{chr(10).join(task_texts)}
""")
        
        # Task Comments
        if task_comments:
            comment_texts = []
            for c in task_comments[:15]:
                msg = c.get("message", "")[:150] if c.get("message") else ""
                msg = msg.replace("\n", " ").strip()
                if msg:
                    comment_texts.append(f"- {c.get('post_date', '')}: {c.get('author_name', 'Anonim')}: {msg}")
            
            if comment_texts:
                sections.append(f"""
## GÖREV YORUMLARI ({len(task_comments)} kayıt)
{chr(10).join(comment_texts)}
""")
        
        context = "\n".join(sections)
        
        prompt = f"""Sen bir CRM analisti olarak görev yapıyorsun. Aşağıdaki müşteri verilerini analiz edip Türkçe olarak profesyonel bir özet hazırla.

{context}

---

Lütfen şu formatta bir özet hazırla:

### 📋 MÜŞTERİ SÜRECİ ÖZETİ

**Müşteri Profili:** (Kim olduğu, firma, pozisyon)

**Süreç Durumu:** (Hangi aşamada, ne kadar süredir)

**İletişim Özeti:** (Kaç kez iletişime geçildi, hangi kanallardan)

**Önemli Noktalar:**
- (Kritik bilgiler, öne çıkan detaylar)

**Açık Görevler:** (Tamamlanmamış işler varsa)

**Sonraki Adım Önerisi:** (Ne yapılmalı)

**Risk/Fırsat Değerlendirmesi:** (Kısa analiz)

---

Özet profesyonel, kısa ve aksiyona yönlendirici olmalı. Maksimum 400 kelime kullan.
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
                            "content": "Sen bir CRM ve satış süreçleri uzmanısın. Müşteri verilerini analiz edip Türkçe özetler hazırlıyorsun."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
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
                    "max_tokens": 1500,
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
                        "maxOutputTokens": 2000,
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
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2000,
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
