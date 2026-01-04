-- Migration 004: Normalize contacts table structure
-- Converts JSONB data column to proper SQL columns

-- First, let's see what fields we have in contacts
-- Run this to analyze: SELECT DISTINCT jsonb_object_keys(data) FROM bitrix.contacts;

-- Drop existing contacts table and recreate with proper columns
DROP TABLE IF EXISTS bitrix.contacts CASCADE;

CREATE TABLE bitrix.contacts (
    id BIGSERIAL PRIMARY KEY,
    
    -- Bitrix24 ID
    bitrix_id VARCHAR(50) UNIQUE,
    
    -- Basic Information
    name VARCHAR(255),
    second_name VARCHAR(255),
    last_name VARCHAR(255),
    full_name VARCHAR(500),
    
    -- Contact Details
    post VARCHAR(255),
    phone VARCHAR(100),
    email VARCHAR(255),
    web TEXT,
    im JSONB, -- Instant messengers as JSON
    
    -- Address
    address TEXT,
    address_2 TEXT,
    address_city VARCHAR(255),
    address_postal_code VARCHAR(50),
    address_region VARCHAR(255),
    address_province VARCHAR(255),
    address_country VARCHAR(255),
    
    -- Company Information
    company_id VARCHAR(50),
    company_title VARCHAR(500),
    
    -- Status & Type
    type_id VARCHAR(50),
    source_id VARCHAR(50),
    source_description TEXT,
    
    -- Dates
    birthdate DATE,
    date_create TIMESTAMP WITH TIME ZONE,
    date_modify TIMESTAMP WITH TIME ZONE,
    
    -- Assignment
    assigned_by_id VARCHAR(50),
    created_by_id VARCHAR(50),
    modify_by_id VARCHAR(50),
    
    -- Additional Fields
    comments TEXT,
    opened BOOLEAN DEFAULT true,
    export BOOLEAN DEFAULT true,
    has_phone BOOLEAN DEFAULT false,
    has_email BOOLEAN DEFAULT false,
    has_imol BOOLEAN DEFAULT false,
    
    -- Custom Fields (keep as JSON for flexibility)
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    utm_content VARCHAR(255),
    utm_term VARCHAR(255),
    
    -- Original data backup (for fields we haven't mapped)
    original_data JSONB,
    
    -- Sync metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_hash TEXT,
    
    -- Indexes for performance
    CONSTRAINT contacts_bitrix_id_key UNIQUE (bitrix_id)
);

-- Create indexes for common queries
CREATE INDEX idx_contacts_name ON bitrix.contacts(name);
CREATE INDEX idx_contacts_email ON bitrix.contacts(email);
CREATE INDEX idx_contacts_phone ON bitrix.contacts(phone);
CREATE INDEX idx_contacts_company_id ON bitrix.contacts(company_id);
CREATE INDEX idx_contacts_assigned_by ON bitrix.contacts(assigned_by_id);
CREATE INDEX idx_contacts_date_create ON bitrix.contacts(date_create);
CREATE INDEX idx_contacts_date_modify ON bitrix.contacts(date_modify);
CREATE INDEX idx_contacts_bitrix_id ON bitrix.contacts(bitrix_id);

-- Add comment
COMMENT ON TABLE bitrix.contacts IS 'Normalized Bitrix24 contacts with proper column structure';
