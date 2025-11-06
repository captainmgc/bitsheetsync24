-- Migration 005: Normalize deals table structure

DROP TABLE IF EXISTS bitrix.deals CASCADE;

CREATE TABLE bitrix.deals (
    id BIGSERIAL PRIMARY KEY,
    
    -- Bitrix24 ID
    bitrix_id VARCHAR(50) UNIQUE,
    
    -- Basic Information
    title VARCHAR(500),
    stage_id VARCHAR(50),
    stage_semantic_id VARCHAR(50), -- SUCCESS, FAILURE, PROCESS
    
    -- Financial
    opportunity DECIMAL(15, 2),
    currency_id VARCHAR(10),
    tax_value DECIMAL(15, 2),
    
    -- Relationships
    company_id VARCHAR(50),
    contact_id VARCHAR(50),
    quote_id VARCHAR(50),
    
    -- Category & Type
    category_id VARCHAR(50),
    type_id VARCHAR(50),
    source_id VARCHAR(50),
    source_description TEXT,
    
    -- Dates
    begindate DATE,
    closedate DATE,
    date_create TIMESTAMP WITH TIME ZONE,
    date_modify TIMESTAMP WITH TIME ZONE,
    
    -- Assignment
    assigned_by_id VARCHAR(50),
    created_by_id VARCHAR(50),
    modify_by_id VARCHAR(50),
    
    -- Status flags
    opened BOOLEAN DEFAULT true,
    closed BOOLEAN DEFAULT false,
    
    -- Probability
    probability INTEGER,
    
    -- Comments
    comments TEXT,
    
    -- UTM tracking
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255),
    
    -- Original data backup
    original_data JSONB,
    
    -- Sync metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_hash TEXT,
    
    CONSTRAINT deals_bitrix_id_key UNIQUE (bitrix_id)
);

-- Indexes
CREATE INDEX idx_deals_title ON bitrix.deals(title);
CREATE INDEX idx_deals_stage ON bitrix.deals(stage_id);
CREATE INDEX idx_deals_company ON bitrix.deals(company_id);
CREATE INDEX idx_deals_contact ON bitrix.deals(contact_id);
CREATE INDEX idx_deals_assigned_by ON bitrix.deals(assigned_by_id);
CREATE INDEX idx_deals_date_create ON bitrix.deals(date_create);
CREATE INDEX idx_deals_closedate ON bitrix.deals(closedate);
CREATE INDEX idx_deals_opportunity ON bitrix.deals(opportunity);
CREATE INDEX idx_deals_stage_semantic ON bitrix.deals(stage_semantic_id);

COMMENT ON TABLE bitrix.deals IS 'Normalized Bitrix24 deals (Anlaşmalar) with proper column structure';
