-- ============================================================================
-- Migration: 009_add_ai_summary_tables.sql
-- Description: Add AI summary storage and tracking tables
-- Date: 2025-11-28
-- ============================================================================

-- AI Summaries Table
-- Stores generated AI summaries for deals
CREATE TABLE IF NOT EXISTS bitrix.ai_summaries (
    id BIGSERIAL PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    deal_title VARCHAR(500),
    summary TEXT NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- 'openai', 'claude', 'ollama'
    model VARCHAR(100) NOT NULL,     -- 'gpt-4o-mini', 'claude-3-haiku', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    written_to_bitrix BOOLEAN DEFAULT FALSE,
    bitrix_write_at TIMESTAMP WITH TIME ZONE,
    bitrix_comment_id BIGINT,        -- ID of timeline comment if created
    tokens_used INT,                  -- Token count for cost tracking
    generation_time_ms INT,           -- How long it took to generate
    
    -- Indexes
    CONSTRAINT fk_ai_summaries_deal FOREIGN KEY (deal_id) 
        REFERENCES bitrix.deals(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_ai_summaries_deal_id ON bitrix.ai_summaries(deal_id);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_created_at ON bitrix.ai_summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_provider ON bitrix.ai_summaries(provider);

-- AI Provider Settings Table
-- Stores user preferences for AI providers
CREATE TABLE IF NOT EXISTS bitrix.ai_provider_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100),  -- Optional: for multi-user support
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    custom_prompt TEXT,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INT DEFAULT 1500,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI Summary Templates
-- Custom prompts for different summary types
CREATE TABLE IF NOT EXISTS bitrix.ai_summary_templates (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default template
INSERT INTO bitrix.ai_summary_templates (name, description, prompt_template, is_default)
VALUES (
    'Standart Müşteri Özeti',
    'Varsayılan müşteri süreci özeti şablonu',
    'Sen bir CRM analisti olarak görev yapıyorsun. Aşağıdaki müşteri verilerini analiz edip Türkçe olarak profesyonel bir özet hazırla.

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

Özet profesyonel, kısa ve aksiyona yönlendirici olmalı. Maksimum 400 kelime kullan.',
    true
) ON CONFLICT DO NOTHING;

-- AI Usage Statistics View
-- Track AI usage for cost monitoring
CREATE OR REPLACE VIEW bitrix.v_ai_usage_stats AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    provider,
    model,
    COUNT(*) as summary_count,
    SUM(tokens_used) as total_tokens,
    AVG(generation_time_ms) as avg_generation_time_ms,
    COUNT(CASE WHEN written_to_bitrix THEN 1 END) as written_to_bitrix_count
FROM bitrix.ai_summaries
GROUP BY DATE_TRUNC('day', created_at), provider, model
ORDER BY date DESC;

-- Recent AI Summaries View
CREATE OR REPLACE VIEW bitrix.v_recent_ai_summaries AS
SELECT 
    s.id,
    s.deal_id,
    s.deal_title,
    LEFT(s.summary, 200) as summary_preview,
    s.provider,
    s.model,
    s.created_at,
    s.written_to_bitrix,
    d.data->>'STAGE_ID' as deal_stage,
    d.data->>'OPPORTUNITY' as deal_amount,
    CONCAT(c.data->>'NAME', ' ', c.data->>'LAST_NAME') as contact_name
FROM bitrix.ai_summaries s
LEFT JOIN bitrix.deals d ON s.deal_id = d.id
LEFT JOIN bitrix.contacts c ON (d.data->>'CONTACT_ID')::int = c.id
ORDER BY s.created_at DESC;

-- Add comment
COMMENT ON TABLE bitrix.ai_summaries IS 'AI-generated summaries for customer deals';
COMMENT ON TABLE bitrix.ai_provider_settings IS 'User preferences for AI providers';
COMMENT ON TABLE bitrix.ai_summary_templates IS 'Custom prompt templates for AI summaries';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bitrix.ai_summaries TO bitsheet;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bitrix.ai_provider_settings TO bitsheet;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON bitrix.ai_summary_templates TO bitsheet;
-- GRANT USAGE, SELECT ON SEQUENCE bitrix.ai_summaries_id_seq TO bitsheet;
-- GRANT USAGE, SELECT ON SEQUENCE bitrix.ai_provider_settings_id_seq TO bitsheet;
-- GRANT USAGE, SELECT ON SEQUENCE bitrix.ai_summary_templates_id_seq TO bitsheet;

SELECT 'Migration 009_add_ai_summary_tables completed successfully' as status;
