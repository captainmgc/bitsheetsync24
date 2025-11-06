-- Create data_views table for storing custom view configurations
-- Migration: 003_create_data_views_table.sql

CREATE TABLE IF NOT EXISTS bitrix.data_views (
    id SERIAL PRIMARY KEY,
    view_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    filters JSONB DEFAULT '{}',
    sort_config JSONB DEFAULT '{}',
    columns_visible JSONB DEFAULT '[]',
    is_default BOOLEAN DEFAULT false,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_view_name_per_table UNIQUE (table_name, view_name)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_data_views_table_name ON bitrix.data_views(table_name);
CREATE INDEX IF NOT EXISTS idx_data_views_is_default ON bitrix.data_views(table_name, is_default);

-- Insert default views for each table
INSERT INTO bitrix.data_views (view_name, table_name, is_default, created_at) VALUES
    ('Tüm Kayıtlar', 'contacts', true, NOW()),
    ('Tüm Kayıtlar', 'companies', true, NOW()),
    ('Tüm Kayıtlar', 'deals', true, NOW()),
    ('Tüm Kayıtlar', 'activities', true, NOW()),
    ('Tüm Kayıtlar', 'tasks', true, NOW()),
    ('Tüm Kayıtlar', 'task_comments', true, NOW()),
    ('Tüm Kayıtlar', 'leads', true, NOW())
ON CONFLICT (table_name, view_name) DO NOTHING;

-- Add some example views
INSERT INTO bitrix.data_views (view_name, table_name, filters, sort_config, is_default, created_at) VALUES
    ('Aktif Görevler', 'tasks', '{"status": "active"}', '{"column": "deadline", "order": "asc"}', false, NOW()),
    ('Tamamlanan Görevler', 'tasks', '{"status": "completed"}', '{"column": "completed_at", "order": "desc"}', false, NOW()),
    ('Açık Anlaşmalar', 'deals', '{"stage": "open"}', '{"column": "opportunity", "order": "desc"}', false, NOW()),
    ('Kazanılan Anlaşmalar', 'deals', '{"stage": "won"}', '{"column": "close_date", "order": "desc"}', false, NOW())
ON CONFLICT (table_name, view_name) DO NOTHING;

COMMENT ON TABLE bitrix.data_views IS 'Stores custom view configurations for data tables';
COMMENT ON COLUMN bitrix.data_views.filters IS 'JSONB object containing filter conditions';
COMMENT ON COLUMN bitrix.data_views.sort_config IS 'JSONB object with column and order (asc/desc)';
COMMENT ON COLUMN bitrix.data_views.columns_visible IS 'JSONB array of visible column names';
