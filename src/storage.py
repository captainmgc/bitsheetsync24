from typing import Any, Dict, Optional
import hashlib
from datetime import datetime

from sqlalchemy import create_engine, Table, Column, MetaData, BigInteger, Text, JSON, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

from src.config import DATABASE_URL

metadata = MetaData(schema="bitrix")

# We'll operate via raw SQL for ON CONFLICT upsert to be explicit

def get_engine() -> Engine:
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def json_hash(data: Dict[str, Any]) -> str:
    # stable hash of JSON to detect changes
    import json
    s = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def choose_updated_at(item: Dict[str, Any]) -> Optional[datetime]:
    candidates = [
        item.get("DATE_MODIFY"),
        item.get("DATE_UPDATE"),
        item.get("UPDATED_TIME"),
        item.get("CHANGED_DATE"),
        item.get("LAST_UPDATED"),
    ]
    for v in candidates:
        if v:
            try:
                # Bitrix usually returns ISO 8601 or 'YYYY-MM-DD HH:MM:SS'
                from dateutil import parser  # type: ignore
                return parser.parse(v)
            except Exception:
                try:
                    return datetime.fromisoformat(v)
                except Exception:
                    continue
    return None


UPSERT_SQL = {
    "leads": """
    INSERT INTO bitrix.leads (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "contacts": """
    INSERT INTO bitrix.contacts (
        bitrix_id, name, second_name, last_name, full_name,
        post, phone, email, web, im,
        address, address_2, address_city, address_postal_code,
        address_region, address_province, address_country,
        company_id, company_title,
        type_id, source_id, source_description,
        birthdate, date_create, date_modify,
        assigned_by_id, created_by_id, modify_by_id,
        comments, opened, export, has_phone, has_email, has_imol,
        utm_source, utm_medium, utm_campaign, utm_content, utm_term,
        original_data, updated_at, fetched_at, source_hash
    )
    VALUES (
        :bitrix_id, :name, :second_name, :last_name, :full_name,
        :post, :phone, :email, :web, CAST(:im AS JSONB),
        :address, :address_2, :address_city, :address_postal_code,
        :address_region, :address_province, :address_country,
        :company_id, :company_title,
        :type_id, :source_id, :source_description,
        :birthdate, :date_create, :date_modify,
        :assigned_by_id, :created_by_id, :modify_by_id,
        :comments, :opened, :export, :has_phone, :has_email, :has_imol,
        :utm_source, :utm_medium, :utm_campaign, :utm_content, :utm_term,
        CAST(:original_data AS JSONB), :updated_at, now(), :source_hash
    )
    ON CONFLICT (bitrix_id) DO UPDATE SET
        name = EXCLUDED.name,
        second_name = EXCLUDED.second_name,
        last_name = EXCLUDED.last_name,
        full_name = EXCLUDED.full_name,
        post = EXCLUDED.post,
        phone = EXCLUDED.phone,
        email = EXCLUDED.email,
        web = EXCLUDED.web,
        im = EXCLUDED.im,
        address = EXCLUDED.address,
        address_2 = EXCLUDED.address_2,
        address_city = EXCLUDED.address_city,
        address_postal_code = EXCLUDED.address_postal_code,
        address_region = EXCLUDED.address_region,
        address_province = EXCLUDED.address_province,
        address_country = EXCLUDED.address_country,
        company_id = EXCLUDED.company_id,
        company_title = EXCLUDED.company_title,
        type_id = EXCLUDED.type_id,
        source_id = EXCLUDED.source_id,
        source_description = EXCLUDED.source_description,
        birthdate = EXCLUDED.birthdate,
        date_create = EXCLUDED.date_create,
        date_modify = EXCLUDED.date_modify,
        assigned_by_id = EXCLUDED.assigned_by_id,
        created_by_id = EXCLUDED.created_by_id,
        modify_by_id = EXCLUDED.modify_by_id,
        comments = EXCLUDED.comments,
        opened = EXCLUDED.opened,
        export = EXCLUDED.export,
        has_phone = EXCLUDED.has_phone,
        has_email = EXCLUDED.has_email,
        has_imol = EXCLUDED.has_imol,
        utm_source = EXCLUDED.utm_source,
        utm_medium = EXCLUDED.utm_medium,
        utm_campaign = EXCLUDED.utm_campaign,
        utm_content = EXCLUDED.utm_content,
        utm_term = EXCLUDED.utm_term,
        original_data = EXCLUDED.original_data,
        updated_at = EXCLUDED.updated_at,
        fetched_at = now(),
        source_hash = EXCLUDED.source_hash
    """,
    "companies": """
    INSERT INTO bitrix.companies (
        bitrix_id, title, company_type, industry,
        phone, email, web,
        address, address_2, address_city, address_postal_code,
        address_region, address_province, address_country, address_country_code,
        revenue, currency_id, employees, banking_details,
        date_create, date_modify,
        assigned_by_id, created_by_id, modify_by_id,
        comments, opened,
        utm_source, utm_medium, utm_campaign,
        original_data, updated_at, fetched_at, source_hash
    )
    VALUES (
        :bitrix_id, :title, :company_type, :industry,
        :phone, :email, :web,
        :address, :address_2, :address_city, :address_postal_code,
        :address_region, :address_province, :address_country, :address_country_code,
        :revenue, :currency_id, :employees, :banking_details,
        :date_create, :date_modify,
        :assigned_by_id, :created_by_id, :modify_by_id,
        :comments, :opened,
        :utm_source, :utm_medium, :utm_campaign,
        CAST(:original_data AS JSONB), :updated_at, now(), :source_hash
    )
    ON CONFLICT (bitrix_id) DO UPDATE SET
        title = EXCLUDED.title,
        company_type = EXCLUDED.company_type,
        industry = EXCLUDED.industry,
        phone = EXCLUDED.phone,
        email = EXCLUDED.email,
        web = EXCLUDED.web,
        address = EXCLUDED.address,
        address_2 = EXCLUDED.address_2,
        address_city = EXCLUDED.address_city,
        address_postal_code = EXCLUDED.address_postal_code,
        address_region = EXCLUDED.address_region,
        address_province = EXCLUDED.address_province,
        address_country = EXCLUDED.address_country,
        address_country_code = EXCLUDED.address_country_code,
        revenue = EXCLUDED.revenue,
        currency_id = EXCLUDED.currency_id,
        employees = EXCLUDED.employees,
        banking_details = EXCLUDED.banking_details,
        date_create = EXCLUDED.date_create,
        date_modify = EXCLUDED.date_modify,
        assigned_by_id = EXCLUDED.assigned_by_id,
        created_by_id = EXCLUDED.created_by_id,
        modify_by_id = EXCLUDED.modify_by_id,
        comments = EXCLUDED.comments,
        opened = EXCLUDED.opened,
        utm_source = EXCLUDED.utm_source,
        utm_medium = EXCLUDED.utm_medium,
        utm_campaign = EXCLUDED.utm_campaign,
        original_data = EXCLUDED.original_data,
        updated_at = EXCLUDED.updated_at,
        fetched_at = now(),
        source_hash = EXCLUDED.source_hash
    """,
    "deals": """
    INSERT INTO bitrix.deals (
        bitrix_id, title, stage_id, stage_semantic_id,
        opportunity, currency_id, tax_value,
        company_id, contact_id, quote_id,
        category_id, type_id, source_id,
        begindate, closedate, date_create, date_modify,
        assigned_by_id, created_by_id, modify_by_id,
        opened, closed, probability,
        comments,
        utm_source, utm_medium, utm_campaign, utm_content, utm_term,
        original_data, updated_at, fetched_at, source_hash
    )
    VALUES (
        :bitrix_id, :title, :stage_id, :stage_semantic_id,
        :opportunity, :currency_id, :tax_value,
        :company_id, :contact_id, :quote_id,
        :category_id, :type_id, :source_id,
        :begindate, :closedate, :date_create, :date_modify,
        :assigned_by_id, :created_by_id, :modify_by_id,
        :opened, :closed, :probability,
        :comments,
        :utm_source, :utm_medium, :utm_campaign, :utm_content, :utm_term,
        CAST(:original_data AS JSONB), :updated_at, now(), :source_hash
    )
    ON CONFLICT (bitrix_id) DO UPDATE SET
        title = EXCLUDED.title,
        stage_id = EXCLUDED.stage_id,
        stage_semantic_id = EXCLUDED.stage_semantic_id,
        opportunity = EXCLUDED.opportunity,
        currency_id = EXCLUDED.currency_id,
        tax_value = EXCLUDED.tax_value,
        company_id = EXCLUDED.company_id,
        contact_id = EXCLUDED.contact_id,
        quote_id = EXCLUDED.quote_id,
        category_id = EXCLUDED.category_id,
        type_id = EXCLUDED.type_id,
        source_id = EXCLUDED.source_id,
        begindate = EXCLUDED.begindate,
        closedate = EXCLUDED.closedate,
        date_create = EXCLUDED.date_create,
        date_modify = EXCLUDED.date_modify,
        assigned_by_id = EXCLUDED.assigned_by_id,
        created_by_id = EXCLUDED.created_by_id,
        modify_by_id = EXCLUDED.modify_by_id,
        opened = EXCLUDED.opened,
        closed = EXCLUDED.closed,
        probability = EXCLUDED.probability,
        comments = EXCLUDED.comments,
        utm_source = EXCLUDED.utm_source,
        utm_medium = EXCLUDED.utm_medium,
        utm_campaign = EXCLUDED.utm_campaign,
        utm_content = EXCLUDED.utm_content,
        utm_term = EXCLUDED.utm_term,
        original_data = EXCLUDED.original_data,
        updated_at = EXCLUDED.updated_at,
        fetched_at = now(),
        source_hash = EXCLUDED.source_hash
    """,
    "activities": """
    INSERT INTO bitrix.activities (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "tasks": """
    INSERT INTO bitrix.tasks (
        bitrix_id, title, description,
        status, priority,
        responsible_id, created_by, changed_by,
        deadline, start_date_plan, end_date_plan,
        created_date, changed_date, closed_date,
        duration_plan, duration_fact, time_estimate, time_spent_in_logs,
        parent_id, group_id, tags,
        allow_change_deadline, allow_time_tracking,
        comments_count, service_comments_count,
        original_data, updated_at, fetched_at, source_hash
    )
    VALUES (
        :bitrix_id, :title, :description,
        :status, :priority,
        :responsible_id, :created_by, :changed_by,
        :deadline, :start_date_plan, :end_date_plan,
        :created_date, :changed_date, :closed_date,
        :duration_plan, :duration_fact, :time_estimate, :time_spent_in_logs,
        :parent_id, :group_id, :tags,
        :allow_change_deadline, :allow_time_tracking,
        :comments_count, :service_comments_count,
        CAST(:original_data AS JSONB), :updated_at, now(), :source_hash
    )
    ON CONFLICT (bitrix_id) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        status = EXCLUDED.status,
        priority = EXCLUDED.priority,
        responsible_id = EXCLUDED.responsible_id,
        created_by = EXCLUDED.created_by,
        changed_by = EXCLUDED.changed_by,
        deadline = EXCLUDED.deadline,
        start_date_plan = EXCLUDED.start_date_plan,
        end_date_plan = EXCLUDED.end_date_plan,
        created_date = EXCLUDED.created_date,
        changed_date = EXCLUDED.changed_date,
        closed_date = EXCLUDED.closed_date,
        duration_plan = EXCLUDED.duration_plan,
        duration_fact = EXCLUDED.duration_fact,
        time_estimate = EXCLUDED.time_estimate,
        time_spent_in_logs = EXCLUDED.time_spent_in_logs,
        parent_id = EXCLUDED.parent_id,
        group_id = EXCLUDED.group_id,
        tags = EXCLUDED.tags,
        allow_change_deadline = EXCLUDED.allow_change_deadline,
        allow_time_tracking = EXCLUDED.allow_time_tracking,
        comments_count = EXCLUDED.comments_count,
        service_comments_count = EXCLUDED.service_comments_count,
        original_data = EXCLUDED.original_data,
        updated_at = EXCLUDED.updated_at,
        fetched_at = now(),
        source_hash = EXCLUDED.source_hash
    """,
    "task_comments": """
    INSERT INTO bitrix.task_comments (id, task_id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, :task_id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "users": """
    INSERT INTO bitrix.users (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
    "departments": """
    INSERT INTO bitrix.departments (id, data, updated_at, fetched_at, source_hash)
    VALUES (:id, CAST(:data AS JSONB), :updated_at, now(), :source_hash)
    ON CONFLICT (id) DO UPDATE SET
      data = EXCLUDED.data,
      updated_at = EXCLUDED.updated_at,
      fetched_at = now(),
      source_hash = EXCLUDED.source_hash
    """,
}


def upsert_entity(entity: str, item: Dict[str, Any], engine: Optional[Engine] = None, task_id: Optional[int] = None):
    import json as json_lib
    eng = engine or get_engine()
    with eng.begin() as conn:
        uid = int(item.get("ID") or item.get("id"))
        u_at = choose_updated_at(item)
        s_hash = json_hash(item)
        
        # Base params for old tables
        params = {
            "id": uid,
            "data": json_lib.dumps(item, ensure_ascii=False),
            "updated_at": u_at,
            "source_hash": s_hash,
        }
        
        # Extract fields for normalized tables
        if entity == "contacts":
            params = _extract_contact_params(item, u_at, s_hash)
        elif entity == "deals":
            params = _extract_deal_params(item, u_at, s_hash)
        elif entity == "companies":
            params = _extract_company_params(item, u_at, s_hash)
        elif entity == "tasks":
            params = _extract_task_params(item, u_at, s_hash)
        elif entity == "task_comments":
            params["task_id"] = task_id or int(item.get("TASK_ID") or 0)
        
        conn.execute(text(UPSERT_SQL[entity]), params)


def _extract_contact_params(item: Dict[str, Any], u_at: Optional[datetime], s_hash: str) -> Dict[str, Any]:
    """Extract contact fields from Bitrix24 data"""
    import json as json_lib
    from dateutil import parser
    
    # Helper to get first value from array fields
    def get_first_value(field_array):
        if isinstance(field_array, list) and len(field_array) > 0:
            return field_array[0].get("VALUE")
        return None
    
    # Parse date safely
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return parser.parse(date_str).date()
        except:
            return None
    
    # Parse timestamp safely
    def parse_timestamp(ts_str):
        if not ts_str:
            return None
        try:
            return parser.parse(ts_str)
        except:
            return None
    
    return {
        "bitrix_id": str(item.get("ID", "")),
        "name": item.get("NAME"),
        "second_name": item.get("SECOND_NAME"),
        "last_name": item.get("LAST_NAME"),
        "full_name": " ".join(filter(None, [
            item.get("NAME"), 
            item.get("SECOND_NAME"), 
            item.get("LAST_NAME")
        ])) or None,
        "post": item.get("POST"),
        "phone": get_first_value(item.get("PHONE")),
        "email": get_first_value(item.get("EMAIL")),
        "web": get_first_value(item.get("WEB")),
        "im": json_lib.dumps(item.get("IM", {})) if item.get("IM") else None,
        "address": item.get("ADDRESS"),
        "address_2": item.get("ADDRESS_2"),
        "address_city": item.get("ADDRESS_CITY"),
        "address_postal_code": item.get("ADDRESS_POSTAL_CODE"),
        "address_region": item.get("ADDRESS_REGION"),
        "address_province": item.get("ADDRESS_PROVINCE"),
        "address_country": item.get("ADDRESS_COUNTRY"),
        "company_id": str(item.get("COMPANY_ID")) if item.get("COMPANY_ID") else None,
        "company_title": item.get("COMPANY_TITLE"),
        "type_id": str(item.get("TYPE_ID")) if item.get("TYPE_ID") else None,
        "source_id": str(item.get("SOURCE_ID")) if item.get("SOURCE_ID") else None,
        "source_description": item.get("SOURCE_DESCRIPTION"),
        "birthdate": parse_date(item.get("BIRTHDATE")),
        "date_create": parse_timestamp(item.get("DATE_CREATE")),
        "date_modify": parse_timestamp(item.get("DATE_MODIFY")),
        "assigned_by_id": str(item.get("ASSIGNED_BY_ID")) if item.get("ASSIGNED_BY_ID") else None,
        "created_by_id": str(item.get("CREATED_BY_ID")) if item.get("CREATED_BY_ID") else None,
        "modify_by_id": str(item.get("MODIFY_BY_ID")) if item.get("MODIFY_BY_ID") else None,
        "comments": item.get("COMMENTS"),
        "opened": item.get("OPENED") == "Y" if item.get("OPENED") else True,
        "export": item.get("EXPORT") == "Y" if item.get("EXPORT") else True,
        "has_phone": item.get("HAS_PHONE") == "Y" if item.get("HAS_PHONE") else False,
        "has_email": item.get("HAS_EMAIL") == "Y" if item.get("HAS_EMAIL") else False,
        "has_imol": item.get("HAS_IMOL") == "Y" if item.get("HAS_IMOL") else False,
        "utm_source": item.get("UTM_SOURCE"),
        "utm_medium": item.get("UTM_MEDIUM"),
        "utm_campaign": item.get("UTM_CAMPAIGN"),
        "utm_content": item.get("UTM_CONTENT"),
        "utm_term": item.get("UTM_TERM"),
        "original_data": json_lib.dumps(item, ensure_ascii=False),
        "updated_at": u_at,
        "source_hash": s_hash,
    }


def _extract_deal_params(item: Dict[str, Any], u_at: Optional[datetime], s_hash: str) -> Dict[str, Any]:
    """Extract deal fields from Bitrix24 data"""
    import json as json_lib
    from dateutil import parser
    from decimal import Decimal
    
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return parser.parse(date_str).date()
        except:
            return None
    
    def parse_timestamp(ts_str):
        if not ts_str:
            return None
        try:
            return parser.parse(ts_str)
        except:
            return None
    
    def parse_decimal(val):
        if not val:
            return None
        try:
            return Decimal(str(val))
        except:
            return None
    
    return {
        "bitrix_id": str(item.get("ID", "")),
        "title": item.get("TITLE"),
        "stage_id": item.get("STAGE_ID"),
        "stage_semantic_id": item.get("STAGE_SEMANTIC_ID"),
        "opportunity": parse_decimal(item.get("OPPORTUNITY")),
        "currency_id": item.get("CURRENCY_ID"),
        "company_id": str(item.get("COMPANY_ID")) if item.get("COMPANY_ID") else None,
        "contact_id": str(item.get("CONTACT_ID")) if item.get("CONTACT_ID") else None,
        "quote_id": str(item.get("QUOTE_ID")) if item.get("QUOTE_ID") else None,
        "category_id": str(item.get("CATEGORY_ID")) if item.get("CATEGORY_ID") else None,
        "type_id": str(item.get("TYPE_ID")) if item.get("TYPE_ID") else None,
        "source_id": str(item.get("SOURCE_ID")) if item.get("SOURCE_ID") else None,
        "tax_value": parse_decimal(item.get("TAX_VALUE")),
        "begindate": parse_date(item.get("BEGINDATE")),
        "closedate": parse_date(item.get("CLOSEDATE")),
        "date_create": parse_timestamp(item.get("DATE_CREATE")),
        "date_modify": parse_timestamp(item.get("DATE_MODIFY")),
        "assigned_by_id": str(item.get("ASSIGNED_BY_ID")) if item.get("ASSIGNED_BY_ID") else None,
        "created_by_id": str(item.get("CREATED_BY_ID")) if item.get("CREATED_BY_ID") else None,
        "modify_by_id": str(item.get("MODIFY_BY_ID")) if item.get("MODIFY_BY_ID") else None,
        "opened": item.get("OPENED") == "Y" if item.get("OPENED") else True,
        "closed": item.get("CLOSED") == "Y" if item.get("CLOSED") else False,
        "probability": int(item.get("PROBABILITY", 0)) if item.get("PROBABILITY") else None,
        "comments": item.get("COMMENTS"),
        "utm_source": item.get("UTM_SOURCE"),
        "utm_medium": item.get("UTM_MEDIUM"),
        "utm_campaign": item.get("UTM_CAMPAIGN"),
        "utm_content": item.get("UTM_CONTENT"),
        "utm_term": item.get("UTM_TERM"),
        "original_data": json_lib.dumps(item, ensure_ascii=False),
        "updated_at": u_at,
        "source_hash": s_hash,
    }


def _extract_company_params(item: Dict[str, Any], u_at: Optional[datetime], s_hash: str) -> Dict[str, Any]:
    """Extract company fields from Bitrix24 data"""
    import json as json_lib
    from dateutil import parser
    from decimal import Decimal
    
    def get_first_value(field_array):
        if isinstance(field_array, list) and len(field_array) > 0:
            return field_array[0].get("VALUE")
        return None
    
    def parse_timestamp(ts_str):
        if not ts_str:
            return None
        try:
            return parser.parse(ts_str)
        except:
            return None
    
    def parse_decimal(val):
        if not val:
            return None
        try:
            return Decimal(str(val))
        except:
            return None
    
    def parse_int(val):
        if not val:
            return None
        try:
            return int(val)
        except:
            return None
    
    return {
        "bitrix_id": str(item.get("ID", "")),
        "title": item.get("TITLE"),
        "company_type": item.get("COMPANY_TYPE"),
        "industry": item.get("INDUSTRY"),
        "phone": get_first_value(item.get("PHONE")),
        "email": get_first_value(item.get("EMAIL")),
        "web": get_first_value(item.get("WEB")),
        "address": item.get("ADDRESS"),
        "address_2": item.get("ADDRESS_2"),
        "address_city": item.get("ADDRESS_CITY"),
        "address_postal_code": item.get("ADDRESS_POSTAL_CODE"),
        "address_region": item.get("ADDRESS_REGION"),
        "address_province": item.get("ADDRESS_PROVINCE"),
        "address_country": item.get("ADDRESS_COUNTRY"),
        "address_country_code": item.get("ADDRESS_COUNTRY_CODE"),
        "revenue": parse_decimal(item.get("REVENUE")),
        "currency_id": item.get("CURRENCY_ID"),
        "employees": parse_int(item.get("EMPLOYEES")),
        "banking_details": item.get("BANKING_DETAILS"),
        "date_create": parse_timestamp(item.get("DATE_CREATE")),
        "date_modify": parse_timestamp(item.get("DATE_MODIFY")),
        "assigned_by_id": str(item.get("ASSIGNED_BY_ID")) if item.get("ASSIGNED_BY_ID") else None,
        "created_by_id": str(item.get("CREATED_BY_ID")) if item.get("CREATED_BY_ID") else None,
        "modify_by_id": str(item.get("MODIFY_BY_ID")) if item.get("MODIFY_BY_ID") else None,
        "comments": item.get("COMMENTS"),
        "opened": item.get("OPENED") == "Y" if item.get("OPENED") else True,
        "utm_source": item.get("UTM_SOURCE"),
        "utm_medium": item.get("UTM_MEDIUM"),
        "utm_campaign": item.get("UTM_CAMPAIGN"),
        "original_data": json_lib.dumps(item, ensure_ascii=False),
        "updated_at": u_at,
        "source_hash": s_hash,
    }


def _extract_task_params(item: Dict[str, Any], u_at: Optional[datetime], s_hash: str) -> Dict[str, Any]:
    """Extract task fields from Bitrix24 data"""
    import json as json_lib
    from dateutil import parser
    
    def parse_timestamp(ts_str):
        if not ts_str:
            return None
        try:
            return parser.parse(ts_str)
        except:
            return None
    
    return {
        "bitrix_id": str(item.get("ID", "")),
        "title": item.get("TITLE"),
        "description": item.get("DESCRIPTION"),
        "status": int(item.get("STATUS", 1)) if item.get("STATUS") else 1,
        "priority": int(item.get("PRIORITY", 0)) if item.get("PRIORITY") else 0,
        "responsible_id": str(item.get("RESPONSIBLE_ID")) if item.get("RESPONSIBLE_ID") else None,
        "created_by": str(item.get("CREATED_BY")) if item.get("CREATED_BY") else None,
        "changed_by": str(item.get("CHANGED_BY")) if item.get("CHANGED_BY") else None,
        "deadline": parse_timestamp(item.get("DEADLINE")),
        "start_date_plan": parse_timestamp(item.get("START_DATE_PLAN")),
        "end_date_plan": parse_timestamp(item.get("END_DATE_PLAN")),
        "created_date": parse_timestamp(item.get("CREATED_DATE")),
        "changed_date": parse_timestamp(item.get("CHANGED_DATE")),
        "closed_date": parse_timestamp(item.get("CLOSED_DATE")),
        "duration_plan": int(item.get("DURATION_PLAN", 0)) if item.get("DURATION_PLAN") else None,
        "duration_fact": int(item.get("DURATION_FACT", 0)) if item.get("DURATION_FACT") else None,
        "time_estimate": int(item.get("TIME_ESTIMATE", 0)) if item.get("TIME_ESTIMATE") else None,
        "time_spent_in_logs": int(item.get("TIME_SPENT_IN_LOGS", 0)) if item.get("TIME_SPENT_IN_LOGS") else None,
        "parent_id": str(item.get("PARENT_ID")) if item.get("PARENT_ID") else None,
        "group_id": str(item.get("GROUP_ID")) if item.get("GROUP_ID") else None,
        "tags": item.get("TAGS", "").split(",") if item.get("TAGS") else [],
        "allow_change_deadline": item.get("ALLOW_CHANGE_DEADLINE") == "Y",
        "allow_time_tracking": item.get("ALLOW_TIME_TRACKING") == "Y",
        "comments_count": int(item.get("COMMENTS_COUNT", 0)) if item.get("COMMENTS_COUNT") else 0,
        "service_comments_count": int(item.get("SERVICE_COMMENTS_COUNT", 0)) if item.get("SERVICE_COMMENTS_COUNT") else 0,
        "original_data": json_lib.dumps(item, ensure_ascii=False),
        "updated_at": u_at,
        "source_hash": s_hash,
    }
