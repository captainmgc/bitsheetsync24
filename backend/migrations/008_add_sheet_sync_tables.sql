-- Migration: 008_add_sheet_sync_tables.sql
-- Tarih: 7 Kasım 2025
-- Amaç: Google Sheets ↔ Bitrix24 Real-time Senkronizasyonu
--
-- Özellikler:
-- 1. User OAuth Token Management
-- 2. Dinamik Tablo Senkronizasyon Konfigürasyonu
-- 3. Otomatik Alan Eşleme (Header Detection)
-- 4. Webhook Event Tracking
-- 5. Sync Log & History

-- ============================================
-- 0. SCHEMA OLUŞTUR
-- ============================================

CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS bitrix;

-- ============================================
-- 1. AUTH SCHEMA - USER SHEETS TOKENS
-- ============================================

-- Kullanıcının Google Sheets OAuth Tokens'ını sakla
CREATE TABLE IF NOT EXISTS auth.user_sheets_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,                 -- Google OAuth user ID
    user_email VARCHAR(255),                       -- User email (reference)
    access_token TEXT NOT NULL,                    -- Google Sheets API access token
    refresh_token TEXT,                            -- Refresh token (long-lived)
    token_expires_at TIMESTAMP,                    -- Token expiry time
    scopes TEXT[] DEFAULT ARRAY['https://www.googleapis.com/auth/spreadsheets',
                                'https://www.googleapis.com/auth/drive.file'],
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT uq_user_sheets_tokens_user UNIQUE(user_id)
);

CREATE INDEX idx_user_sheets_tokens_user ON auth.user_sheets_tokens(user_id);
CREATE INDEX idx_user_sheets_tokens_email ON auth.user_sheets_tokens(user_email);

-- ============================================
-- 2. BITRIX SCHEMA - SHEET SYNC CONFIG
-- ============================================

-- Hangi Sheet'ler, hangi Bitrix24 entity'ler ile senkronize ediliyor?
CREATE TABLE IF NOT EXISTS bitrix.sheet_sync_config (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,                 -- Hangi user?
    sheet_id VARCHAR(200) NOT NULL,                -- Google Sheet ID (dosya ID'si)
    sheet_gid VARCHAR(50) NOT NULL,                -- Sheet/Tab GID (tablo numarası)
    sheet_name VARCHAR(255),                       -- Orijinal Sheet adı (kullanıcı tarafından)
    entity_type VARCHAR(100) NOT NULL,             -- "leads", "contacts", "deals", "activities", "tasks"
    is_custom_view BOOLEAN DEFAULT false,          -- Custom view'den oluşturuldu mu?
    
    -- Görünüm Ayarları
    color_scheme JSONB,                            -- {bgColor: "#...", textColor: "#...", font: "Poppins"}
    
    -- Webhook Bilgileri
    webhook_url VARCHAR(500),                      -- Google Apps Script webhook endpoint
    webhook_registered BOOLEAN DEFAULT false,      -- Webhook başarıyla kaydedildi mi?
    webhook_registered_at TIMESTAMP,
    
    -- Senkronizasyon Durumu
    enabled BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP,
    sync_error_count INT DEFAULT 0,
    last_error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_sheet_sync_config_user FOREIGN KEY (user_id) 
        REFERENCES auth.user_sheets_tokens(user_id) ON DELETE CASCADE,
    CONSTRAINT uq_sheet_sync_config UNIQUE(user_id, sheet_id, sheet_gid, entity_type)
);

CREATE INDEX idx_sheet_sync_config_user ON bitrix.sheet_sync_config(user_id);
CREATE INDEX idx_sheet_sync_config_entity ON bitrix.sheet_sync_config(entity_type);
CREATE INDEX idx_sheet_sync_config_enabled ON bitrix.sheet_sync_config(enabled);

-- ============================================
-- 3. BITRIX SCHEMA - FIELD MAPPINGS
-- ============================================

-- Otomatik tespit edilen: Google Sheets kolonu ↔ Bitrix24 alanı
CREATE TABLE IF NOT EXISTS bitrix.field_mappings (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT NOT NULL,                     -- Hangi sync config'e ait?
    sheet_column_index INT NOT NULL,               -- Kolon numarası (0, 1, 2, ...)
    sheet_column_name VARCHAR(100) NOT NULL,       -- Sheets header ("Name", "Email", "Phone")
    bitrix_field VARCHAR(100) NOT NULL,            -- Bitrix24 alanı ("TITLE", "EMAIL", "PHONE")
    data_type VARCHAR(50),                         -- "string", "number", "date", "select", vb
    is_updatable BOOLEAN DEFAULT true,             -- Bu alanı güncelleyebilir mi?
    mapping_confidence DECIMAL(3,2),               -- 0.0 - 1.0 (otomatik tespitle başarı oranı)
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_field_mappings_config FOREIGN KEY (config_id)
        REFERENCES bitrix.sheet_sync_config(id) ON DELETE CASCADE,
    CONSTRAINT uq_field_mappings UNIQUE(config_id, sheet_column_index)
);

CREATE INDEX idx_field_mappings_config ON bitrix.field_mappings(config_id);

-- ============================================
-- 4. BITRIX SCHEMA - WEBHOOK EVENTS
-- ============================================

-- Google Apps Script'ten gelen her webhook event'i logla
CREATE TABLE IF NOT EXISTS bitrix.webhook_events (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT NOT NULL,                     -- Hangi sync config'ten?
    event_type VARCHAR(50) NOT NULL,               -- "row_edited", "row_inserted", "row_deleted"
    sheet_row_id INT,                              -- Google Sheet'teki satır numarası
    sheet_row_data JSONB,                          -- Tüm satırın ham verisi
    event_data JSONB,                              -- {field: {old: x, new: y}}
    
    -- İşleme Durumu
    status VARCHAR(20) DEFAULT 'pending',          -- "pending", "processing", "completed", "failed"
    processing_started_at TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT,
    
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_webhook_events_config ON bitrix.webhook_events(config_id);
CREATE INDEX idx_webhook_events_status ON bitrix.webhook_events(status);
CREATE INDEX idx_webhook_events_received ON bitrix.webhook_events(received_at DESC);

-- ============================================
-- 5. BITRIX SCHEMA - REVERSE SYNC LOGS
-- ============================================

-- Hangi veriler Sheets'ten Bitrix24'e yazıldı? (Audit trail)
CREATE TABLE IF NOT EXISTS bitrix.reverse_sync_logs (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT NOT NULL,                     -- Hangi config'ten?
    webhook_event_id BIGINT,                       -- Hangi webhook event'ten tetiklendi?
    user_id VARCHAR(100) NOT NULL,
    
    -- Entity Bilgisi
    entity_type VARCHAR(100),                      -- "leads", "contacts", "deals"
    entity_id BIGINT,                              -- Bitrix24 entity ID
    bitrix_entity_id VARCHAR(100),                 -- Bitrix24 API response ID
    
    -- Sheet Bilgisi
    sheet_row_id INT,
    sheet_row_number INT,                          -- Sheets'teki satır numarası
    
    -- Değişen Alanlar
    changed_fields JSONB,                          -- {
                                                   --   "TITLE": {old: "Eski", new: "Yeni"},
                                                   --   "EMAIL": {old: "old@mail.com", new: "new@mail.com"}
                                                   -- }
    
    -- Senkronizasyon Durumu
    status VARCHAR(20) DEFAULT 'pending',          -- "pending", "syncing", "completed", "failed"
    bitrix_response JSONB,                         -- Bitrix24 API response
    error_message TEXT,
    error_details JSONB,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    
    -- Zaman Bilgileri
    synced_at TIMESTAMP,
    failed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reverse_sync_logs_config ON bitrix.reverse_sync_logs(config_id);
CREATE INDEX idx_reverse_sync_logs_user ON bitrix.reverse_sync_logs(user_id);
CREATE INDEX idx_reverse_sync_logs_entity ON bitrix.reverse_sync_logs(entity_type, entity_id);
CREATE INDEX idx_reverse_sync_logs_status ON bitrix.reverse_sync_logs(status);
CREATE INDEX idx_reverse_sync_logs_synced ON bitrix.reverse_sync_logs(synced_at DESC);

-- ============================================
-- 6. VIEWS - REPORTING VE ANALYTICS
-- ============================================

-- Son 24 saatte yapılan senkronizasyonlar
CREATE OR REPLACE VIEW bitrix.v_recent_syncs AS
SELECT
    rsl.id,
    rsl.config_id,
    ssc.sheet_name,
    ssc.entity_type,
    rsl.entity_id,
    rsl.status,
    rsl.changed_fields,
    rsl.created_at,
    rsl.synced_at,
    rsl.error_message,
    EXTRACT(EPOCH FROM (rsl.synced_at - rsl.created_at)) as duration_seconds
FROM bitrix.reverse_sync_logs rsl
JOIN bitrix.sheet_sync_config ssc ON rsl.config_id = ssc.id
WHERE rsl.created_at > NOW() - INTERVAL '24 hours'
ORDER BY rsl.created_at DESC;

-- Sync config başına istatistikler
CREATE OR REPLACE VIEW bitrix.v_sync_statistics AS
SELECT
    ssc.id,
    ssc.sheet_name,
    ssc.entity_type,
    COUNT(rsl.id) as total_syncs,
    COUNT(CASE WHEN rsl.status = 'completed' THEN 1 END) as successful_syncs,
    COUNT(CASE WHEN rsl.status = 'failed' THEN 1 END) as failed_syncs,
    ROUND(100.0 * COUNT(CASE WHEN rsl.status = 'completed' THEN 1 END) / 
          NULLIF(COUNT(rsl.id), 0), 2) as success_rate,
    MAX(rsl.synced_at) as last_sync,
    ROUND(AVG(EXTRACT(EPOCH FROM (rsl.synced_at - rsl.created_at))), 2) as avg_sync_time_seconds
FROM bitrix.sheet_sync_config ssc
LEFT JOIN bitrix.reverse_sync_logs rsl ON ssc.id = rsl.config_id
GROUP BY ssc.id, ssc.sheet_name, ssc.entity_type;

-- Webhook events durumu
CREATE OR REPLACE VIEW bitrix.v_webhook_status AS
SELECT
    we.config_id,
    ssc.sheet_name,
    ssc.entity_type,
    COUNT(we.id) as total_events,
    COUNT(CASE WHEN we.status = 'pending' THEN 1 END) as pending_events,
    COUNT(CASE WHEN we.status = 'processing' THEN 1 END) as processing_events,
    COUNT(CASE WHEN we.status = 'completed' THEN 1 END) as completed_events,
    COUNT(CASE WHEN we.status = 'failed' THEN 1 END) as failed_events,
    MAX(we.received_at) as last_event
FROM bitrix.webhook_events we
JOIN bitrix.sheet_sync_config ssc ON we.config_id = ssc.id
GROUP BY we.config_id, ssc.sheet_name, ssc.entity_type;

-- ============================================
-- 7. TAMAMLANMA VERİFİKASYONU
-- ============================================

-- Tablolar başarıyla oluşturuldu mu?
SELECT 
    'user_sheets_tokens' as table_name, 
    COUNT(*) as row_count 
FROM auth.user_sheets_tokens
UNION ALL
SELECT 'sheet_sync_config', COUNT(*) FROM bitrix.sheet_sync_config
UNION ALL
SELECT 'field_mappings', COUNT(*) FROM bitrix.field_mappings
UNION ALL
SELECT 'webhook_events', COUNT(*) FROM bitrix.webhook_events
UNION ALL
SELECT 'reverse_sync_logs', COUNT(*) FROM bitrix.reverse_sync_logs;
