-- Migration: Sync original_data JSONB to normalized columns
-- Date: 2025-11-28
-- This script extracts data from original_data JSONB column to individual columns

-- ============================================================================
-- DEALS TABLE
-- ============================================================================

UPDATE bitrix.deals SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'ID'),
    title = COALESCE(title, original_data->>'TITLE'),
    stage_id = COALESCE(stage_id, original_data->>'STAGE_ID'),
    stage_semantic_id = COALESCE(stage_semantic_id, original_data->>'STAGE_SEMANTIC_ID'),
    opportunity = COALESCE(opportunity, (original_data->>'OPPORTUNITY')::numeric),
    currency_id = COALESCE(currency_id, original_data->>'CURRENCY_ID'),
    tax_value = COALESCE(tax_value, (original_data->>'TAX_VALUE')::numeric),
    company_id = COALESCE(company_id, original_data->>'COMPANY_ID'),
    contact_id = COALESCE(contact_id, original_data->>'CONTACT_ID'),
    quote_id = COALESCE(quote_id, original_data->>'QUOTE_ID'),
    category_id = COALESCE(category_id, original_data->>'CATEGORY_ID'),
    type_id = COALESCE(type_id, original_data->>'TYPE_ID'),
    source_id = COALESCE(source_id, original_data->>'SOURCE_ID'),
    source_description = COALESCE(source_description, original_data->>'SOURCE_DESCRIPTION'),
    begindate = COALESCE(begindate, (original_data->>'BEGINDATE')::date),
    closedate = COALESCE(closedate, (original_data->>'CLOSEDATE')::date),
    date_create = COALESCE(date_create, (original_data->>'DATE_CREATE')::timestamptz),
    date_modify = COALESCE(date_modify, (original_data->>'DATE_MODIFY')::timestamptz),
    assigned_by_id = COALESCE(assigned_by_id, original_data->>'ASSIGNED_BY_ID'),
    created_by_id = COALESCE(created_by_id, original_data->>'CREATED_BY_ID'),
    modify_by_id = COALESCE(modify_by_id, original_data->>'MODIFY_BY_ID'),
    opened = COALESCE(opened, (original_data->>'OPENED')::boolean),
    closed = COALESCE(closed, (original_data->>'CLOSED')::boolean),
    probability = COALESCE(probability, (original_data->>'PROBABILITY')::integer),
    comments = COALESCE(comments, original_data->>'COMMENTS'),
    utm_source = COALESCE(utm_source, original_data->>'UTM_SOURCE'),
    utm_medium = COALESCE(utm_medium, original_data->>'UTM_MEDIUM'),
    utm_campaign = COALESCE(utm_campaign, original_data->>'UTM_CAMPAIGN'),
    utm_content = COALESCE(utm_content, original_data->>'UTM_CONTENT'),
    utm_term = COALESCE(utm_term, original_data->>'UTM_TERM')
WHERE original_data IS NOT NULL;

-- ============================================================================
-- CONTACTS TABLE
-- ============================================================================

UPDATE bitrix.contacts SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'ID'),
    name = COALESCE(name, original_data->>'NAME'),
    second_name = COALESCE(second_name, original_data->>'SECOND_NAME'),
    last_name = COALESCE(last_name, original_data->>'LAST_NAME'),
    full_name = COALESCE(full_name, 
        TRIM(CONCAT_WS(' ', 
            original_data->>'NAME', 
            original_data->>'SECOND_NAME', 
            original_data->>'LAST_NAME'
        ))
    ),
    post = COALESCE(post, original_data->>'POST'),
    phone = COALESCE(phone, 
        CASE 
            WHEN original_data->'PHONE' IS NOT NULL AND jsonb_array_length(original_data->'PHONE') > 0 
            THEN original_data->'PHONE'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    email = COALESCE(email, 
        CASE 
            WHEN original_data->'EMAIL' IS NOT NULL AND jsonb_array_length(original_data->'EMAIL') > 0 
            THEN original_data->'EMAIL'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    web = COALESCE(web, 
        CASE 
            WHEN original_data->'WEB' IS NOT NULL AND jsonb_array_length(original_data->'WEB') > 0 
            THEN original_data->'WEB'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    address = COALESCE(address, original_data->>'ADDRESS'),
    address_city = COALESCE(address_city, original_data->>'ADDRESS_CITY'),
    address_postal_code = COALESCE(address_postal_code, original_data->>'ADDRESS_POSTAL_CODE'),
    address_region = COALESCE(address_region, original_data->>'ADDRESS_REGION'),
    address_province = COALESCE(address_province, original_data->>'ADDRESS_PROVINCE'),
    address_country = COALESCE(address_country, original_data->>'ADDRESS_COUNTRY'),
    company_id = COALESCE(company_id, original_data->>'COMPANY_ID'),
    company_title = COALESCE(company_title, original_data->>'COMPANY_TITLE'),
    type_id = COALESCE(type_id, original_data->>'TYPE_ID'),
    source_id = COALESCE(source_id, original_data->>'SOURCE_ID'),
    source_description = COALESCE(source_description, original_data->>'SOURCE_DESCRIPTION'),
    birthdate = COALESCE(birthdate, (original_data->>'BIRTHDATE')::date),
    date_create = COALESCE(date_create, (original_data->>'DATE_CREATE')::timestamptz),
    date_modify = COALESCE(date_modify, (original_data->>'DATE_MODIFY')::timestamptz),
    assigned_by_id = COALESCE(assigned_by_id, original_data->>'ASSIGNED_BY_ID'),
    created_by_id = COALESCE(created_by_id, original_data->>'CREATED_BY_ID'),
    modify_by_id = COALESCE(modify_by_id, original_data->>'MODIFY_BY_ID'),
    comments = COALESCE(comments, original_data->>'COMMENTS'),
    opened = COALESCE(opened, (original_data->>'OPENED')::boolean),
    utm_source = COALESCE(utm_source, original_data->>'UTM_SOURCE'),
    utm_medium = COALESCE(utm_medium, original_data->>'UTM_MEDIUM'),
    utm_campaign = COALESCE(utm_campaign, original_data->>'UTM_CAMPAIGN'),
    utm_content = COALESCE(utm_content, original_data->>'UTM_CONTENT'),
    utm_term = COALESCE(utm_term, original_data->>'UTM_TERM')
WHERE original_data IS NOT NULL;

-- ============================================================================
-- COMPANIES TABLE
-- ============================================================================

UPDATE bitrix.companies SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'ID'),
    title = COALESCE(title, original_data->>'TITLE'),
    company_type = COALESCE(company_type, original_data->>'COMPANY_TYPE'),
    industry = COALESCE(industry, original_data->>'INDUSTRY'),
    phone = COALESCE(phone, 
        CASE 
            WHEN original_data->'PHONE' IS NOT NULL AND jsonb_array_length(original_data->'PHONE') > 0 
            THEN original_data->'PHONE'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    email = COALESCE(email, 
        CASE 
            WHEN original_data->'EMAIL' IS NOT NULL AND jsonb_array_length(original_data->'EMAIL') > 0 
            THEN original_data->'EMAIL'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    web = COALESCE(web, 
        CASE 
            WHEN original_data->'WEB' IS NOT NULL AND jsonb_array_length(original_data->'WEB') > 0 
            THEN original_data->'WEB'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    address = COALESCE(address, original_data->>'ADDRESS'),
    address_city = COALESCE(address_city, original_data->>'ADDRESS_CITY'),
    address_postal_code = COALESCE(address_postal_code, original_data->>'ADDRESS_POSTAL_CODE'),
    address_region = COALESCE(address_region, original_data->>'ADDRESS_REGION'),
    address_province = COALESCE(address_province, original_data->>'ADDRESS_PROVINCE'),
    address_country = COALESCE(address_country, original_data->>'ADDRESS_COUNTRY'),
    revenue = COALESCE(revenue, (original_data->>'REVENUE')::numeric),
    currency_id = COALESCE(currency_id, original_data->>'CURRENCY_ID'),
    employees = COALESCE(employees, (original_data->>'EMPLOYEES')::integer),
    banking_details = COALESCE(banking_details, original_data->>'BANKING_DETAILS'),
    date_create = COALESCE(date_create, (original_data->>'DATE_CREATE')::timestamptz),
    date_modify = COALESCE(date_modify, (original_data->>'DATE_MODIFY')::timestamptz),
    assigned_by_id = COALESCE(assigned_by_id, original_data->>'ASSIGNED_BY_ID'),
    created_by_id = COALESCE(created_by_id, original_data->>'CREATED_BY_ID'),
    modify_by_id = COALESCE(modify_by_id, original_data->>'MODIFY_BY_ID'),
    opened = COALESCE(opened, (original_data->>'OPENED')::boolean),
    comments = COALESCE(comments, original_data->>'COMMENTS'),
    utm_source = COALESCE(utm_source, original_data->>'UTM_SOURCE'),
    utm_medium = COALESCE(utm_medium, original_data->>'UTM_MEDIUM'),
    utm_campaign = COALESCE(utm_campaign, original_data->>'UTM_CAMPAIGN')
WHERE original_data IS NOT NULL;

-- ============================================================================
-- ACTIVITIES TABLE
-- ============================================================================

UPDATE bitrix.activities SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'ID'),
    type_id = COALESCE(type_id, original_data->>'TYPE_ID'),
    provider_id = COALESCE(provider_id, original_data->>'PROVIDER_ID'),
    provider_type_id = COALESCE(provider_type_id, original_data->>'PROVIDER_TYPE_ID'),
    subject = COALESCE(subject, original_data->>'SUBJECT'),
    description = COALESCE(description, original_data->>'DESCRIPTION'),
    owner_type_id = COALESCE(owner_type_id, (original_data->>'OWNER_TYPE_ID')::integer),
    owner_id = COALESCE(owner_id, original_data->>'OWNER_ID'),
    responsible_id = COALESCE(responsible_id, original_data->>'RESPONSIBLE_ID'),
    created_by = COALESCE(created_by, original_data->>'CREATED'),
    priority = COALESCE(priority, original_data->>'PRIORITY'),
    direction = COALESCE(direction, original_data->>'DIRECTION'),
    completed = COALESCE(completed, (original_data->>'COMPLETED')::boolean),
    start_time = COALESCE(start_time, (original_data->>'START_TIME')::timestamptz),
    end_time = COALESCE(end_time, (original_data->>'END_TIME')::timestamptz),
    deadline = COALESCE(deadline, (original_data->>'DEADLINE')::timestamptz),
    date_create = COALESCE(date_create, (original_data->>'CREATED')::timestamptz),
    date_modify = COALESCE(date_modify, (original_data->>'LAST_UPDATED')::timestamptz)
WHERE original_data IS NOT NULL;

-- ============================================================================
-- TASKS TABLE
-- ============================================================================

UPDATE bitrix.tasks SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'id'),
    title = COALESCE(title, original_data->>'title'),
    description = COALESCE(description, original_data->>'description'),
    status = COALESCE(status, original_data->>'status'),
    priority = COALESCE(priority, original_data->>'priority'),
    responsible_id = COALESCE(responsible_id, original_data->>'responsibleId'),
    created_by = COALESCE(created_by, original_data->>'createdBy'),
    group_id = COALESCE(group_id, original_data->>'groupId'),
    deadline = COALESCE(deadline, (original_data->>'deadline')::timestamptz),
    start_date_plan = COALESCE(start_date_plan, (original_data->>'startDatePlan')::timestamptz),
    end_date_plan = COALESCE(end_date_plan, (original_data->>'endDatePlan')::timestamptz),
    date_start = COALESCE(date_start, (original_data->>'dateStart')::timestamptz),
    closed_date = COALESCE(closed_date, (original_data->>'closedDate')::timestamptz),
    date_create = COALESCE(date_create, (original_data->>'createdDate')::timestamptz),
    changed_date = COALESCE(changed_date, (original_data->>'changedDate')::timestamptz),
    time_estimate = COALESCE(time_estimate, (original_data->>'timeEstimate')::integer),
    allow_change_deadline = COALESCE(allow_change_deadline, (original_data->>'allowChangeDeadline')::boolean),
    allow_time_tracking = COALESCE(allow_time_tracking, (original_data->>'allowTimeTracking')::boolean),
    task_control = COALESCE(task_control, (original_data->>'taskControl')::boolean),
    comments_count = COALESCE(comments_count, (original_data->>'commentsCount')::integer)
WHERE original_data IS NOT NULL;

-- ============================================================================
-- LEADS TABLE (if exists)
-- ============================================================================

UPDATE bitrix.leads SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'ID'),
    title = COALESCE(title, original_data->>'TITLE'),
    name = COALESCE(name, original_data->>'NAME'),
    second_name = COALESCE(second_name, original_data->>'SECOND_NAME'),
    last_name = COALESCE(last_name, original_data->>'LAST_NAME'),
    status_id = COALESCE(status_id, original_data->>'STATUS_ID'),
    status_semantic_id = COALESCE(status_semantic_id, original_data->>'STATUS_SEMANTIC_ID'),
    opportunity = COALESCE(opportunity, (original_data->>'OPPORTUNITY')::numeric),
    currency_id = COALESCE(currency_id, original_data->>'CURRENCY_ID'),
    phone = COALESCE(phone, 
        CASE 
            WHEN original_data->'PHONE' IS NOT NULL AND jsonb_array_length(original_data->'PHONE') > 0 
            THEN original_data->'PHONE'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    email = COALESCE(email, 
        CASE 
            WHEN original_data->'EMAIL' IS NOT NULL AND jsonb_array_length(original_data->'EMAIL') > 0 
            THEN original_data->'EMAIL'->0->>'VALUE'
            ELSE NULL 
        END
    ),
    company_title = COALESCE(company_title, original_data->>'COMPANY_TITLE'),
    source_id = COALESCE(source_id, original_data->>'SOURCE_ID'),
    source_description = COALESCE(source_description, original_data->>'SOURCE_DESCRIPTION'),
    date_create = COALESCE(date_create, (original_data->>'DATE_CREATE')::timestamptz),
    date_modify = COALESCE(date_modify, (original_data->>'DATE_MODIFY')::timestamptz),
    assigned_by_id = COALESCE(assigned_by_id, original_data->>'ASSIGNED_BY_ID'),
    created_by_id = COALESCE(created_by_id, original_data->>'CREATED_BY_ID'),
    modify_by_id = COALESCE(modify_by_id, original_data->>'MODIFY_BY_ID'),
    comments = COALESCE(comments, original_data->>'COMMENTS'),
    opened = COALESCE(opened, (original_data->>'OPENED')::boolean),
    utm_source = COALESCE(utm_source, original_data->>'UTM_SOURCE'),
    utm_medium = COALESCE(utm_medium, original_data->>'UTM_MEDIUM'),
    utm_campaign = COALESCE(utm_campaign, original_data->>'UTM_CAMPAIGN')
WHERE original_data IS NOT NULL;

-- ============================================================================
-- USERS TABLE
-- ============================================================================

UPDATE bitrix.users SET
    bitrix_id = COALESCE(bitrix_id, original_data->>'ID'),
    name = COALESCE(name, original_data->>'NAME'),
    last_name = COALESCE(last_name, original_data->>'LAST_NAME'),
    second_name = COALESCE(second_name, original_data->>'SECOND_NAME'),
    full_name = COALESCE(full_name, 
        TRIM(CONCAT_WS(' ', 
            original_data->>'NAME', 
            original_data->>'SECOND_NAME', 
            original_data->>'LAST_NAME'
        ))
    ),
    email = COALESCE(email, original_data->>'EMAIL'),
    personal_phone = COALESCE(personal_phone, original_data->>'PERSONAL_PHONE'),
    work_phone = COALESCE(work_phone, original_data->>'WORK_PHONE'),
    work_position = COALESCE(work_position, original_data->>'WORK_POSITION'),
    work_department = COALESCE(work_department, original_data->>'UF_DEPARTMENT'),
    active = COALESCE(active, (original_data->>'ACTIVE')::boolean),
    last_login = COALESCE(last_login, (original_data->>'LAST_LOGIN')::timestamptz)
WHERE original_data IS NOT NULL;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check deals migration
SELECT 'Deals Migration Check' as check_type, 
    COUNT(*) as total,
    COUNT(title) as has_title,
    COUNT(stage_id) as has_stage_id,
    COUNT(date_create) as has_date_create
FROM bitrix.deals;

-- Check contacts migration
SELECT 'Contacts Migration Check' as check_type,
    COUNT(*) as total,
    COUNT(full_name) as has_full_name,
    COUNT(phone) as has_phone,
    COUNT(email) as has_email
FROM bitrix.contacts;

-- Check companies migration
SELECT 'Companies Migration Check' as check_type,
    COUNT(*) as total,
    COUNT(title) as has_title,
    COUNT(phone) as has_phone,
    COUNT(date_create) as has_date_create
FROM bitrix.companies;
