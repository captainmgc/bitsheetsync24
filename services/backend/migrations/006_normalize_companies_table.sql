-- Migration 006: Normalize companies table structure

DROP TABLE IF EXISTS bitrix.companies CASCADE;

CREATE TABLE bitrix.companies (
    id BIGSERIAL PRIMARY KEY,
    
    -- Bitrix24 ID
    bitrix_id VARCHAR(50) UNIQUE,
    
    -- Basic Information
    title VARCHAR(500),
    company_type VARCHAR(100),
    industry VARCHAR(255),
    
    -- Contact Details
    phone VARCHAR(100),
    email VARCHAR(255),
    web TEXT,
    
    -- Address
    address TEXT,
    address_2 TEXT,
    address_city VARCHAR(255),
    address_postal_code VARCHAR(50),
    address_region VARCHAR(255),
    address_province VARCHAR(255),
    address_country VARCHAR(255),
    address_country_code VARCHAR(10),
    
    -- Legal & Financial
    revenue DECIMAL(15, 2),
    currency_id VARCHAR(10),
    employees INTEGER,
    
    -- Banking
    banking_details TEXT,
    
    -- Dates
    date_create TIMESTAMP WITH TIME ZONE,
    date_modify TIMESTAMP WITH TIME ZONE,
    
    -- Assignment
    assigned_by_id VARCHAR(50),
    created_by_id VARCHAR(50),
    modify_by_id VARCHAR(50),
    
    -- Status
    opened BOOLEAN DEFAULT true,
    
    -- Comments
    comments TEXT,
    
    -- UTM tracking
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    
    -- Original data backup
    original_data JSONB,
    
    -- Sync metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_hash TEXT,
    
    CONSTRAINT companies_bitrix_id_key UNIQUE (bitrix_id)
);

-- Indexes
CREATE INDEX idx_companies_title ON bitrix.companies(title);
CREATE INDEX idx_companies_email ON bitrix.companies(email);
CREATE INDEX idx_companies_phone ON bitrix.companies(phone);
CREATE INDEX idx_companies_assigned_by ON bitrix.companies(assigned_by_id);
CREATE INDEX idx_companies_date_create ON bitrix.companies(date_create);
CREATE INDEX idx_companies_industry ON bitrix.companies(industry);

COMMENT ON TABLE bitrix.companies IS 'Normalized Bitrix24 companies (Şirketler) with proper column structure';
