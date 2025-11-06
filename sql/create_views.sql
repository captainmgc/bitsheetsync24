-- SQL Views for Google Sheets Export
-- Created based on Bitrix24 relationship analysis
-- These views normalize JSONB data into columns for easy export

-- ============================================================================
-- CRM Overview View
-- Joins deals with contacts, companies, and responsible users
-- ============================================================================
DROP VIEW IF EXISTS bitrix.v_crm_overview CASCADE;
CREATE VIEW bitrix.v_crm_overview AS
SELECT 
    d.data->>'ID' as deal_id,
    d.data->>'TITLE' as deal_title,
    d.data->>'STAGE_ID' as deal_stage,
    d.data->>'OPPORTUNITY' as deal_amount,
    d.data->>'CURRENCY_ID' as currency,
    TO_TIMESTAMP((d.data->>'DATE_CREATE')::bigint) as deal_created,
    TO_TIMESTAMP((d.data->>'DATE_MODIFY')::bigint) as deal_modified,
    
    -- Contact info
    c.data->>'ID' as contact_id,
    c.data->>'NAME' as contact_name,
    c.data->>'LAST_NAME' as contact_lastname,
    c.data->>'PHONE'->>0->>'VALUE' as contact_phone,
    c.data->>'EMAIL'->>0->>'VALUE' as contact_email,
    
    -- Company info
    comp.data->>'ID' as company_id,
    comp.data->>'TITLE' as company_name,
    comp.data->>'COMPANY_TYPE' as company_type,
    
    -- Responsible user
    u.data->>'ID' as responsible_id,
    u.data->>'NAME' as responsible_name,
    u.data->>'LAST_NAME' as responsible_lastname
FROM 
    bitrix.deals d
    LEFT JOIN bitrix.contacts c ON c.data->>'ID' = d.data->>'CONTACT_ID'
    LEFT JOIN bitrix.companies comp ON comp.data->>'ID' = d.data->>'COMPANY_ID'
    LEFT JOIN bitrix.users u ON u.data->>'ID' = d.data->>'ASSIGNED_BY_ID';

-- ============================================================================
-- Tasks Flat View
-- Normalizes task data with camelCase field names
-- ============================================================================
DROP VIEW IF EXISTS bitrix.v_tasks_flat CASCADE;
CREATE VIEW bitrix.v_tasks_flat AS
SELECT 
    (data->>'id')::bigint as task_id,
    data->>'title' as title,
    data->>'description' as description,
    data->>'status' as status,
    data->>'priority' as priority,
    
    -- Responsible user (camelCase from API)
    (data->>'responsibleId')::bigint as responsible_id,
    ru.data->>'NAME' as responsible_name,
    ru.data->>'LAST_NAME' as responsible_lastname,
    
    -- Creator (camelCase from API)
    (data->>'createdBy')::bigint as created_by_id,
    cu.data->>'NAME' as creator_name,
    cu.data->>'LAST_NAME' as creator_lastname,
    
    -- Group/Project
    (data->>'groupId')::bigint as group_id,
    
    -- Dates
    TO_TIMESTAMP((data->>'createdDate')::bigint) as created_date,
    TO_TIMESTAMP((data->>'changedDate')::bigint) as changed_date,
    TO_TIMESTAMP((data->>'closedDate')::bigint) as closed_date,
    
    -- Time tracking
    (data->>'timeEstimate')::integer as time_estimate,
    (data->>'timeSpentInLogs')::integer as time_spent
FROM 
    bitrix.tasks t
    LEFT JOIN bitrix.users ru ON ru.data->>'ID' = t.data->>'responsibleId'
    LEFT JOIN bitrix.users cu ON cu.data->>'ID' = t.data->>'createdBy';

-- ============================================================================
-- Activities Decoded View
-- Decodes OWNER_TYPE_ID to entity names
-- ============================================================================
DROP VIEW IF EXISTS bitrix.v_activities_decoded CASCADE;
CREATE VIEW bitrix.v_activities_decoded AS
SELECT 
    (data->>'ID')::bigint as activity_id,
    (data->>'OWNER_ID')::bigint as owner_id,
    (data->>'OWNER_TYPE_ID')::integer as owner_type_id,
    
    -- Decode owner type
    CASE (data->>'OWNER_TYPE_ID')::integer
        WHEN 1 THEN 'Lead'
        WHEN 2 THEN 'Deal'
        WHEN 3 THEN 'Contact'
        WHEN 4 THEN 'Company'
        WHEN 14 THEN 'Unknown'
        ELSE 'Other'
    END as owner_type_name,
    
    data->>'TYPE_ID' as activity_type,
    data->>'SUBJECT' as subject,
    data->>'DESCRIPTION' as description,
    data->>'DIRECTION' as direction,
    data->>'PRIORITY' as priority,
    data->>'STATUS' as status,
    
    -- Responsible user
    (data->>'RESPONSIBLE_ID')::bigint as responsible_id,
    u.data->>'NAME' as responsible_name,
    u.data->>'LAST_NAME' as responsible_lastname,
    
    -- Dates
    TO_TIMESTAMP((data->>'CREATED')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as created_at,
    TO_TIMESTAMP((data->>'LAST_UPDATED')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as updated_at,
    TO_TIMESTAMP((data->>'START_TIME')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as start_time,
    TO_TIMESTAMP((data->>'END_TIME')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as end_time
FROM 
    bitrix.activities a
    LEFT JOIN bitrix.users u ON u.data->>'ID' = a.data->>'RESPONSIBLE_ID';

-- ============================================================================
-- Leads Export View (for testing Google Sheets)
-- Turkish date format: DD/MM/YYYY and separate date/time columns
-- ============================================================================
DROP VIEW IF EXISTS bitrix.v_leads_export CASCADE;
CREATE VIEW bitrix.v_leads_export AS
SELECT 
    (data->>'ID')::bigint as id,
    data->>'TITLE' as baslik,
    data->>'NAME' as ad,
    data->>'LAST_NAME' as soyad,
    data->>'STATUS_ID' as durum,
    data->>'SOURCE_ID' as kaynak,
    
    -- Contact info
    data->'PHONE'->0->>'VALUE' as telefon,
    data->'EMAIL'->0->>'VALUE' as email,
    
    -- Responsible user
    (data->>'ASSIGNED_BY_ID')::bigint as sorumlu_id,
    u.data->>'NAME' as sorumlu_ad,
    u.data->>'LAST_NAME' as sorumlu_soyad,
    
    -- Turkish formatted dates (DD/MM/YYYY)
    TO_CHAR(TO_TIMESTAMP((data->>'DATE_CREATE')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'DD/MM/YYYY') as olusturma_tarihi,
    TO_CHAR(TO_TIMESTAMP((data->>'DATE_CREATE')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'HH24:MI:SS') as olusturma_saati,
    
    TO_CHAR(TO_TIMESTAMP((data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'DD/MM/YYYY') as guncelleme_tarihi,
    TO_CHAR(TO_TIMESTAMP((data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'HH24:MI:SS') as guncelleme_saati,
    
    -- Raw timestamps for filtering
    TO_TIMESTAMP((data->>'DATE_CREATE')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as created_at,
    TO_TIMESTAMP((data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as modified_at
FROM 
    bitrix.leads l
    LEFT JOIN bitrix.users u ON u.data->>'ID' = l.data->>'ASSIGNED_BY_ID';

-- ============================================================================
-- Deals Export View (for Google Sheets)
-- Turkish date format with company and contact relationships
-- ============================================================================
DROP VIEW IF EXISTS bitrix.v_deals_export CASCADE;
CREATE VIEW bitrix.v_deals_export AS
SELECT 
    (d.data->>'ID')::bigint as id,
    d.data->>'TITLE' as baslik,
    d.data->>'STAGE_ID' as asamasi,
    (d.data->>'OPPORTUNITY')::numeric as tutar,
    d.data->>'CURRENCY_ID' as para_birimi,
    
    -- Contact
    (d.data->>'CONTACT_ID')::bigint as iletisim_id,
    c.data->>'NAME' as iletisim_ad,
    c.data->>'LAST_NAME' as iletisim_soyad,
    
    -- Company
    (d.data->>'COMPANY_ID')::bigint as sirket_id,
    comp.data->>'TITLE' as sirket_adi,
    
    -- Responsible user
    (d.data->>'ASSIGNED_BY_ID')::bigint as sorumlu_id,
    u.data->>'NAME' as sorumlu_ad,
    u.data->>'LAST_NAME' as sorumlu_soyad,
    
    -- Turkish formatted dates
    TO_CHAR(TO_TIMESTAMP((d.data->>'DATE_CREATE')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'DD/MM/YYYY') as olusturma_tarihi,
    TO_CHAR(TO_TIMESTAMP((d.data->>'DATE_CREATE')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'HH24:MI:SS') as olusturma_saati,
    
    TO_CHAR(TO_TIMESTAMP((d.data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'DD/MM/YYYY') as guncelleme_tarihi,
    TO_CHAR(TO_TIMESTAMP((d.data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM'), 'HH24:MI:SS') as guncelleme_saati,
    
    -- Raw timestamps for filtering
    TO_TIMESTAMP((d.data->>'DATE_CREATE')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as created_at,
    TO_TIMESTAMP((d.data->>'DATE_MODIFY')::text, 'YYYY-MM-DD"T"HH24:MI:SS±TZH:TZM') as modified_at
FROM 
    bitrix.deals d
    LEFT JOIN bitrix.contacts c ON c.data->>'ID' = d.data->>'CONTACT_ID'
    LEFT JOIN bitrix.companies comp ON comp.data->>'ID' = d.data->>'COMPANY_ID'
    LEFT JOIN bitrix.users u ON u.data->>'ID' = d.data->>'ASSIGNED_BY_ID';

-- ============================================================================
-- Tasks Export View (for Google Sheets)
-- Turkish date format with responsible and creator info
-- ============================================================================
DROP VIEW IF EXISTS bitrix.v_tasks_export CASCADE;
CREATE VIEW bitrix.v_tasks_export AS
SELECT 
    (t.data->>'id')::bigint as id,
    t.data->>'title' as baslik,
    t.data->>'description' as aciklama,
    t.data->>'status' as durum,
    t.data->>'priority' as oncelik,
    
    -- Responsible user (camelCase from API)
    (t.data->>'responsibleId')::bigint as sorumlu_id,
    ru.data->>'NAME' as sorumlu_ad,
    ru.data->>'LAST_NAME' as sorumlu_soyad,
    
    -- Creator (camelCase from API)
    (t.data->>'createdBy')::bigint as olusturan_id,
    cu.data->>'NAME' as olusturan_ad,
    cu.data->>'LAST_NAME' as olusturan_soyad,
    
    -- Group
    (t.data->>'groupId')::bigint as grup_id,
    
    -- Time tracking
    (t.data->>'timeEstimate')::integer as tahmini_sure,
    (t.data->>'timeSpentInLogs')::integer as harcanan_sure,
    
    -- Turkish formatted dates
    TO_CHAR(TO_TIMESTAMP((t.data->>'createdDate')::bigint), 'DD/MM/YYYY') as olusturma_tarihi,
    TO_CHAR(TO_TIMESTAMP((t.data->>'createdDate')::bigint), 'HH24:MI:SS') as olusturma_saati,
    
    TO_CHAR(TO_TIMESTAMP((t.data->>'changedDate')::bigint), 'DD/MM/YYYY') as guncelleme_tarihi,
    TO_CHAR(TO_TIMESTAMP((t.data->>'changedDate')::bigint), 'HH24:MI:SS') as guncelleme_saati,
    
    TO_CHAR(TO_TIMESTAMP((t.data->>'closedDate')::bigint), 'DD/MM/YYYY') as kapanis_tarihi,
    TO_CHAR(TO_TIMESTAMP((t.data->>'closedDate')::bigint), 'HH24:MI:SS') as kapanis_saati,
    
    -- Raw timestamps for filtering
    TO_TIMESTAMP((t.data->>'createdDate')::bigint) as created_at,
    TO_TIMESTAMP((t.data->>'changedDate')::bigint) as modified_at
FROM 
    bitrix.tasks t
    LEFT JOIN bitrix.users ru ON ru.data->>'ID' = t.data->>'responsibleId'
    LEFT JOIN bitrix.users cu ON cu.data->>'ID' = t.data->>'createdBy';

-- ============================================================================
-- Grant access to views
-- ============================================================================
GRANT SELECT ON ALL TABLES IN SCHEMA bitrix TO bitsheet;
