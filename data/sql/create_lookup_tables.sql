-- =====================================================
-- BitSheet24 - Bitrix24 Lookup Tabloları
-- ID -> Name çözümlemesi için dinamik referans tabloları
-- =====================================================

-- Ana lookup tablosu: Tüm Bitrix24 status/referans değerlerini tutar
CREATE TABLE IF NOT EXISTS bitrix.lookup_values (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,     -- STATUS, SOURCE, DEAL_TYPE, CONTACT_TYPE, COMPANY_TYPE, etc.
    status_id VARCHAR(100) NOT NULL,        -- UC_6PFNMS, CALLBACK, NEW, etc.
    name VARCHAR(500) NOT NULL,             -- İnsan okunabilir isim
    name_init VARCHAR(500),                 -- Orijinal isim (varsayılan)
    sort INTEGER DEFAULT 100,               -- Sıralama
    color VARCHAR(20),                      -- Renk kodu (#39a8ef)
    semantics VARCHAR(50),                  -- process, success, failure
    category_id VARCHAR(50),                -- Kategori ID (deal stage'ler için)
    is_system BOOLEAN DEFAULT FALSE,        -- Sistem tarafından oluşturuldu mu
    extra JSONB,                            -- Ekstra bilgiler
    bitrix_id VARCHAR(50),                  -- Bitrix'teki ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(entity_type, status_id)
);

-- Deal kategorileri (Pipeline'lar)
CREATE TABLE IF NOT EXISTS bitrix.deal_categories (
    id SERIAL PRIMARY KEY,
    bitrix_id VARCHAR(50) NOT NULL UNIQUE,  -- Bitrix'teki ID (24, 26, 30, etc.)
    name VARCHAR(255) NOT NULL,              -- SATIŞ YÖNETİMİ, FİNANS YÖNETİMİ, etc.
    sort INTEGER DEFAULT 100,
    is_locked BOOLEAN DEFAULT FALSE,
    created_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Kullanıcı lookup tablosu (users tablosu zaten var, ama bu basitleştirilmiş versiyon)
-- users tablosunu kullanacağız

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_lookup_entity_type ON bitrix.lookup_values(entity_type);
CREATE INDEX IF NOT EXISTS idx_lookup_status_id ON bitrix.lookup_values(status_id);
CREATE INDEX IF NOT EXISTS idx_lookup_entity_status ON bitrix.lookup_values(entity_type, status_id);
CREATE INDEX IF NOT EXISTS idx_lookup_category ON bitrix.lookup_values(category_id) WHERE category_id IS NOT NULL;

-- Entity type referans tablosu (hangi entity hangi lookup'ları kullanıyor)
CREATE TABLE IF NOT EXISTS bitrix.lookup_entity_mapping (
    id SERIAL PRIMARY KEY,
    entity_name VARCHAR(50) NOT NULL,       -- leads, deals, contacts, companies
    field_name VARCHAR(100) NOT NULL,       -- STATUS_ID, SOURCE_ID, TYPE_ID, STAGE_ID
    lookup_entity_type VARCHAR(100) NOT NULL, -- STATUS, SOURCE, DEAL_TYPE, CONTACT_TYPE
    description VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(entity_name, field_name)
);

-- Varsayılan entity-lookup mapping'leri
INSERT INTO bitrix.lookup_entity_mapping (entity_name, field_name, lookup_entity_type, description) VALUES
-- Leads
('leads', 'STATUS_ID', 'STATUS', 'Lead aşama durumu'),
('leads', 'SOURCE_ID', 'SOURCE', 'Lead kaynağı'),

-- Deals
('deals', 'STAGE_ID', 'DEAL_STAGE', 'Anlaşma aşaması (kategori prefix''i ile: DEAL_STAGE_XX)'),
('deals', 'CATEGORY_ID', 'DEAL_CATEGORY', 'Anlaşma kategorisi/pipeline'),
('deals', 'TYPE_ID', 'DEAL_TYPE', 'Anlaşma türü'),
('deals', 'SOURCE_ID', 'SOURCE', 'Anlaşma kaynağı'),

-- Contacts
('contacts', 'TYPE_ID', 'CONTACT_TYPE', 'Kişi türü'),
('contacts', 'SOURCE_ID', 'SOURCE', 'Kişi kaynağı'),
('contacts', 'HONORIFIC', 'HONORIFIC', 'Hitap'),

-- Companies
('companies', 'COMPANY_TYPE', 'COMPANY_TYPE', 'Şirket türü'),
('companies', 'INDUSTRY', 'INDUSTRY', 'Sektör'),
('companies', 'EMPLOYEES', 'EMPLOYEES', 'Çalışan sayısı')

ON CONFLICT (entity_name, field_name) DO UPDATE SET
    lookup_entity_type = EXCLUDED.lookup_entity_type,
    description = EXCLUDED.description;

-- Lookup değerlerini hızlı çekmek için view
CREATE OR REPLACE VIEW bitrix.v_lookup_summary AS
SELECT 
    entity_type,
    COUNT(*) as value_count,
    MIN(updated_at) as oldest_update,
    MAX(updated_at) as newest_update
FROM bitrix.lookup_values
GROUP BY entity_type
ORDER BY entity_type;

-- Deal stage lookup view (kategori ile birleştirilmiş)
CREATE OR REPLACE VIEW bitrix.v_deal_stages AS
SELECT 
    lv.status_id as stage_id,
    lv.name as stage_name,
    lv.color,
    lv.semantics,
    lv.sort,
    dc.bitrix_id as category_id,
    dc.name as category_name
FROM bitrix.lookup_values lv
LEFT JOIN bitrix.deal_categories dc ON lv.category_id = dc.bitrix_id
WHERE lv.entity_type LIKE 'DEAL_STAGE%'
ORDER BY dc.sort, lv.sort;

COMMENT ON TABLE bitrix.lookup_values IS 'Bitrix24 CRM status ve referans değerlerinin yerel kopyası';
COMMENT ON TABLE bitrix.deal_categories IS 'Bitrix24 Deal kategorileri (Pipeline''lar)';
COMMENT ON TABLE bitrix.lookup_entity_mapping IS 'Entity alanları ile lookup tabloları arasındaki ilişkiler';
