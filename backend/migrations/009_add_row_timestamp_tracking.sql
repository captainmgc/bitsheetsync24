-- Migration: 009_add_row_timestamp_tracking.sql
-- Tarih: 27 Kasım 2025
-- Amaç: Sheet satır bazlı timestamp tracking için tablo
-- Çakışma tespiti (conflict resolution) için kullanılır

-- ============================================
-- 1. ROW TIMESTAMP TRACKING TABLE
-- ============================================

-- Her satırın son güncelleme zamanını takip et
CREATE TABLE IF NOT EXISTS bitrix.sheet_row_timestamps (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT NOT NULL,                     -- Hangi sync config'e ait?
    sheet_row_number INT NOT NULL,                 -- Sheet'teki satır numarası (1-indexed)
    entity_id VARCHAR(100),                        -- Bitrix24 entity ID
    
    -- Timestamp bilgileri
    sheet_modified_at TIMESTAMP,                   -- Sheet'te en son ne zaman değiştirildi?
    bitrix_modified_at TIMESTAMP,                  -- Bitrix'te en son ne zaman değiştirildi?
    last_sync_at TIMESTAMP,                        -- En son ne zaman senkronize edildi?
    
    -- Son değerler (çakışma tespiti için)
    last_sheet_values JSONB,                       -- Sheet'teki son değerler
    last_bitrix_values JSONB,                      -- Bitrix'teki son değerler
    
    -- Durum
    sync_status VARCHAR(20) DEFAULT 'synced',      -- synced, pending, conflict, error
    conflict_fields JSONB,                         -- Çakışan alanlar
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_row_timestamps_config FOREIGN KEY (config_id)
        REFERENCES bitrix.sheet_sync_config(id) ON DELETE CASCADE,
    CONSTRAINT uq_row_timestamps UNIQUE(config_id, sheet_row_number)
);

CREATE INDEX idx_row_timestamps_config ON bitrix.sheet_row_timestamps(config_id);
CREATE INDEX idx_row_timestamps_entity ON bitrix.sheet_row_timestamps(entity_id);
CREATE INDEX idx_row_timestamps_status ON bitrix.sheet_row_timestamps(sync_status);
CREATE INDEX idx_row_timestamps_modified ON bitrix.sheet_row_timestamps(sheet_modified_at DESC);

-- ============================================
-- 2. BITRIX FIELD CACHE TABLE
-- ============================================

-- Bitrix24 alan bilgilerini cache'le
CREATE TABLE IF NOT EXISTS bitrix.entity_field_cache (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,             -- leads, contacts, deals, vb.
    field_name VARCHAR(100) NOT NULL,
    
    -- Alan metadata
    field_title VARCHAR(255),                      -- İnsan-okunabilir alan adı
    field_type VARCHAR(50),                        -- string, number, date, select, vb.
    is_editable BOOLEAN DEFAULT true,
    is_required BOOLEAN DEFAULT false,
    is_multiple BOOLEAN DEFAULT false,
    
    -- Ek bilgiler
    list_values JSONB,                             -- Select alanları için seçenekler
    settings JSONB,                                -- Diğer ayarlar
    
    cached_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours',
    
    CONSTRAINT uq_entity_field_cache UNIQUE(entity_type, field_name)
);

CREATE INDEX idx_entity_field_cache_type ON bitrix.entity_field_cache(entity_type);
CREATE INDEX idx_entity_field_cache_editable ON bitrix.entity_field_cache(entity_type, is_editable);

-- ============================================
-- 3. SYNC STATUS COLUMN TRACKING
-- ============================================

-- Her config için status kolonu bilgisi
ALTER TABLE bitrix.sheet_sync_config 
ADD COLUMN IF NOT EXISTS status_column_index INT,
ADD COLUMN IF NOT EXISTS status_column_name VARCHAR(100) DEFAULT 'Senkronizasyon',
ADD COLUMN IF NOT EXISTS script_id VARCHAR(200),
ADD COLUMN IF NOT EXISTS script_installed_at TIMESTAMP;

-- ============================================
-- 4. FIELD MAPPING ENHANCEMENTS
-- ============================================

-- Field mapping tablosuna ek kolonlar
ALTER TABLE bitrix.field_mappings
ADD COLUMN IF NOT EXISTS is_readonly BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS color_code VARCHAR(7),
ADD COLUMN IF NOT EXISTS bitrix_field_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS bitrix_field_title VARCHAR(255);

-- ============================================
-- 5. REVERSE SYNC LOG ENHANCEMENTS
-- ============================================

-- Reverse sync log'a ek kolonlar
ALTER TABLE bitrix.reverse_sync_logs
ADD COLUMN IF NOT EXISTS conflict_detected BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS conflict_resolution VARCHAR(50),
ADD COLUMN IF NOT EXISTS sheet_timestamp TIMESTAMP,
ADD COLUMN IF NOT EXISTS bitrix_timestamp TIMESTAMP;

-- ============================================
-- 6. VIEWS - CONFLICT DETECTION
-- ============================================

-- Çakışma durumundaki satırlar
CREATE OR REPLACE VIEW bitrix.v_conflict_rows AS
SELECT
    rt.id,
    rt.config_id,
    ssc.sheet_name,
    ssc.entity_type,
    rt.sheet_row_number,
    rt.entity_id,
    rt.sheet_modified_at,
    rt.bitrix_modified_at,
    rt.conflict_fields,
    rt.sync_status
FROM bitrix.sheet_row_timestamps rt
JOIN bitrix.sheet_sync_config ssc ON rt.config_id = ssc.id
WHERE rt.sync_status = 'conflict';

-- Entity bazlı düzenlenebilir alanlar
CREATE OR REPLACE VIEW bitrix.v_editable_fields AS
SELECT
    entity_type,
    field_name,
    field_title,
    field_type,
    is_required,
    is_multiple
FROM bitrix.entity_field_cache
WHERE is_editable = true
ORDER BY entity_type, field_name;

-- ============================================
-- 7. FUNCTIONS
-- ============================================

-- Çakışma kontrolü fonksiyonu
CREATE OR REPLACE FUNCTION bitrix.check_row_conflict(
    p_config_id BIGINT,
    p_row_number INT,
    p_sheet_modified_at TIMESTAMP
) RETURNS BOOLEAN AS $$
DECLARE
    v_bitrix_modified_at TIMESTAMP;
    v_last_sync_at TIMESTAMP;
BEGIN
    SELECT bitrix_modified_at, last_sync_at
    INTO v_bitrix_modified_at, v_last_sync_at
    FROM bitrix.sheet_row_timestamps
    WHERE config_id = p_config_id AND sheet_row_number = p_row_number;
    
    -- Eğer bitrix_modified_at > last_sync_at ve sheet_modified_at > last_sync_at
    -- Her iki tarafta da değişiklik var = çakışma
    IF v_bitrix_modified_at IS NOT NULL AND v_last_sync_at IS NOT NULL THEN
        IF v_bitrix_modified_at > v_last_sync_at AND p_sheet_modified_at > v_last_sync_at THEN
            RETURN true;
        END IF;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Row timestamp güncelleme fonksiyonu
CREATE OR REPLACE FUNCTION bitrix.update_row_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
DROP TRIGGER IF EXISTS trg_row_timestamps_updated ON bitrix.sheet_row_timestamps;
CREATE TRIGGER trg_row_timestamps_updated
    BEFORE UPDATE ON bitrix.sheet_row_timestamps
    FOR EACH ROW
    EXECUTE FUNCTION bitrix.update_row_timestamp();

-- ============================================
-- 8. COMMENTS
-- ============================================

COMMENT ON TABLE bitrix.sheet_row_timestamps IS 'Sheet satır bazlı timestamp tracking - çakışma tespiti için';
COMMENT ON TABLE bitrix.entity_field_cache IS 'Bitrix24 alan bilgileri cache - performans için';
COMMENT ON VIEW bitrix.v_conflict_rows IS 'Çakışma durumundaki satırları gösterir';
COMMENT ON VIEW bitrix.v_editable_fields IS 'Düzenlenebilir alanları entity bazlı listeler';
COMMENT ON FUNCTION bitrix.check_row_conflict IS 'İki tarafta da değişiklik var mı kontrol eder';
