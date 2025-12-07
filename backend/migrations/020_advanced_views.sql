-- Advanced Views: Multi-table JOIN support
-- Migration: 020_advanced_views.sql

-- =====================================================
-- 1. TABLE RELATIONS - İlişki Tanımları
-- =====================================================
CREATE TABLE IF NOT EXISTS bitrix.table_relations (
    id SERIAL PRIMARY KEY,
    source_table VARCHAR(100) NOT NULL,
    source_column VARCHAR(100) NOT NULL,
    target_table VARCHAR(100) NOT NULL,
    target_column VARCHAR(100) NOT NULL,
    relation_type VARCHAR(50) DEFAULT 'one_to_many', -- one_to_one, one_to_many, many_to_many
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_relation UNIQUE (source_table, source_column, target_table, target_column)
);

-- Insert known Bitrix relations
INSERT INTO bitrix.table_relations (source_table, source_column, target_table, target_column, relation_type, display_name) VALUES
    -- Contact Relations
    ('contacts', 'company_id', 'companies', 'bitrix_id', 'many_to_one', 'Müşteri → Şirket'),
    ('contacts', 'assigned_by_id', 'users', 'bitrix_id', 'many_to_one', 'Müşteri → Sorumlu'),
    ('contacts', 'created_by_id', 'users', 'bitrix_id', 'many_to_one', 'Müşteri → Oluşturan'),
    
    -- Deal Relations
    ('deals', 'contact_id', 'contacts', 'bitrix_id', 'many_to_one', 'Anlaşma → Müşteri'),
    ('deals', 'company_id', 'companies', 'bitrix_id', 'many_to_one', 'Anlaşma → Şirket'),
    ('deals', 'assigned_by_id', 'users', 'bitrix_id', 'many_to_one', 'Anlaşma → Sorumlu'),
    ('deals', 'created_by_id', 'users', 'bitrix_id', 'many_to_one', 'Anlaşma → Oluşturan'),
    ('deals', 'category_id', 'deal_categories', 'bitrix_id', 'many_to_one', 'Anlaşma → Kategori'),
    
    -- Task Relations
    ('tasks', 'responsible_id', 'users', 'bitrix_id', 'many_to_one', 'Görev → Sorumlu'),
    ('tasks', 'created_by', 'users', 'bitrix_id', 'many_to_one', 'Görev → Oluşturan'),
    ('tasks', 'parent_id', 'tasks', 'bitrix_id', 'many_to_one', 'Görev → Ana Görev'),
    
    -- Task Comment Relations
    ('task_comments', 'task_id', 'tasks', 'bitrix_id', 'many_to_one', 'Yorum → Görev'),
    ('task_comments', 'author_id', 'users', 'bitrix_id', 'many_to_one', 'Yorum → Yazar'),
    
    -- Activity Relations (polymorphic)
    ('activities', 'responsible_id', 'users', 'bitrix_id', 'many_to_one', 'Aktivite → Sorumlu'),
    ('activities', 'author_id', 'users', 'bitrix_id', 'many_to_one', 'Aktivite → Yazar'),
    
    -- Lead Relations
    ('leads', 'assigned_by_id', 'users', 'bitrix_id', 'many_to_one', 'Lead → Sorumlu'),
    
    -- Company Relations
    ('companies', 'assigned_by_id', 'users', 'bitrix_id', 'many_to_one', 'Şirket → Sorumlu')
ON CONFLICT (source_table, source_column, target_table, target_column) DO NOTHING;

-- =====================================================
-- 2. ADVANCED VIEWS - Multi-table View Definitions
-- =====================================================
CREATE TABLE IF NOT EXISTS bitrix.advanced_views (
    id SERIAL PRIMARY KEY,
    view_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Primary table (FROM clause)
    primary_table VARCHAR(100) NOT NULL,
    
    -- JOIN definitions as JSONB array
    -- [{
    --     "table": "contacts",
    --     "alias": "c",
    --     "join_type": "LEFT",
    --     "on_source": "deals.contact_id",
    --     "on_target": "contacts.bitrix_id"
    -- }]
    joins JSONB DEFAULT '[]',
    
    -- Selected columns as JSONB array
    -- [{
    --     "table": "deals",
    --     "column": "title",
    --     "alias": "anlaşma_adı",
    --     "display_name": "Anlaşma Adı"
    -- }]
    selected_columns JSONB DEFAULT '[]',
    
    -- Filter conditions
    filters JSONB DEFAULT '{}',
    
    -- Sort configuration
    sort_config JSONB DEFAULT '{}',
    
    -- Group by columns
    group_by JSONB DEFAULT '[]',
    
    -- Aggregations
    aggregations JSONB DEFAULT '[]',
    
    is_default BOOLEAN DEFAULT false,
    is_system BOOLEAN DEFAULT false,  -- System-generated views
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_advanced_views_primary_table ON bitrix.advanced_views(primary_table);
CREATE INDEX IF NOT EXISTS idx_advanced_views_name ON bitrix.advanced_views(view_name);

-- =====================================================
-- 3. TABLE METADATA - Kolon Bilgileri Cache
-- =====================================================
CREATE TABLE IF NOT EXISTS bitrix.table_metadata (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    data_type VARCHAR(50),
    is_primary_key BOOLEAN DEFAULT false,
    is_foreign_key BOOLEAN DEFAULT false,
    foreign_table VARCHAR(100),
    foreign_column VARCHAR(100),
    is_visible BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_table_column UNIQUE (table_name, column_name)
);

-- =====================================================
-- 4. PREDEFINED SYSTEM VIEWS
-- =====================================================
INSERT INTO bitrix.advanced_views (view_name, description, primary_table, joins, selected_columns, is_system, created_at) VALUES
(
    'CRM Genel Görünüm',
    'Anlaşmalar + Müşteriler + Şirketler birleşik görünümü',
    'deals',
    '[
        {
            "table": "contacts",
            "alias": "c",
            "join_type": "LEFT",
            "on_source": "contact_id",
            "on_target": "bitrix_id"
        },
        {
            "table": "companies",
            "alias": "co",
            "join_type": "LEFT",
            "on_source": "company_id",
            "on_target": "bitrix_id"
        },
        {
            "table": "users",
            "alias": "u",
            "join_type": "LEFT",
            "on_source": "assigned_by_id",
            "on_target": "bitrix_id"
        }
    ]'::jsonb,
    '[
        {"table": "deals", "column": "bitrix_id", "alias": "deal_id", "display_name": "Anlaşma ID"},
        {"table": "deals", "column": "title", "alias": "deal_title", "display_name": "Anlaşma Adı"},
        {"table": "deals", "column": "opportunity", "alias": "amount", "display_name": "Tutar"},
        {"table": "deals", "column": "stage_id", "alias": "stage", "display_name": "Aşama"},
        {"table": "contacts", "column": "name", "alias": "contact_name", "display_name": "Müşteri Adı"},
        {"table": "contacts", "column": "phone", "alias": "contact_phone", "display_name": "Telefon"},
        {"table": "companies", "column": "title", "alias": "company_name", "display_name": "Şirket Adı"},
        {"table": "users", "column": "name", "alias": "assigned_to", "display_name": "Sorumlu"}
    ]'::jsonb,
    true,
    NOW()
),
(
    'Görev Takip Raporu',
    'Görevler + Yorumlar + Sorumlular birleşik görünümü',
    'tasks',
    '[
        {
            "table": "users",
            "alias": "responsible",
            "join_type": "LEFT",
            "on_source": "responsible_id",
            "on_target": "bitrix_id"
        },
        {
            "table": "users",
            "alias": "creator",
            "join_type": "LEFT",
            "on_source": "created_by",
            "on_target": "bitrix_id"
        }
    ]'::jsonb,
    '[
        {"table": "tasks", "column": "bitrix_id", "alias": "task_id", "display_name": "Görev ID"},
        {"table": "tasks", "column": "title", "alias": "task_title", "display_name": "Görev Adı"},
        {"table": "tasks", "column": "status", "alias": "status", "display_name": "Durum"},
        {"table": "tasks", "column": "deadline", "alias": "deadline", "display_name": "Son Tarih"},
        {"table": "tasks", "column": "priority", "alias": "priority", "display_name": "Öncelik"},
        {"table": "users", "column": "name", "alias": "responsible_name", "display_name": "Sorumlu", "table_alias": "responsible"},
        {"table": "users", "column": "name", "alias": "creator_name", "display_name": "Oluşturan", "table_alias": "creator"}
    ]'::jsonb,
    true,
    NOW()
),
(
    'Müşteri 360° Görünüm',
    'Müşteriler + Anlaşmalar + Aktiviteler tam görünümü',
    'contacts',
    '[
        {
            "table": "companies",
            "alias": "co",
            "join_type": "LEFT",
            "on_source": "company_id",
            "on_target": "bitrix_id"
        },
        {
            "table": "deals",
            "alias": "d",
            "join_type": "LEFT",
            "on_source": "bitrix_id",
            "on_target": "contact_id",
            "reverse": true
        },
        {
            "table": "users",
            "alias": "u",
            "join_type": "LEFT",
            "on_source": "assigned_by_id",
            "on_target": "bitrix_id"
        }
    ]'::jsonb,
    '[
        {"table": "contacts", "column": "bitrix_id", "alias": "contact_id", "display_name": "Müşteri ID"},
        {"table": "contacts", "column": "name", "alias": "contact_name", "display_name": "Müşteri Adı"},
        {"table": "contacts", "column": "phone", "alias": "phone", "display_name": "Telefon"},
        {"table": "contacts", "column": "email", "alias": "email", "display_name": "E-posta"},
        {"table": "companies", "column": "title", "alias": "company", "display_name": "Şirket"},
        {"table": "deals", "column": "title", "alias": "deal_title", "display_name": "Anlaşma"},
        {"table": "deals", "column": "opportunity", "alias": "deal_amount", "display_name": "Anlaşma Tutarı"},
        {"table": "users", "column": "name", "alias": "assigned_to", "display_name": "Sorumlu"}
    ]'::jsonb,
    true,
    NOW()
),
(
    'Aktivite Özeti',
    'Aktiviteler + İlişkili kayıtlar',
    'activities',
    '[
        {
            "table": "users",
            "alias": "u",
            "join_type": "LEFT",
            "on_source": "responsible_id",
            "on_target": "bitrix_id"
        }
    ]'::jsonb,
    '[
        {"table": "activities", "column": "bitrix_id", "alias": "activity_id", "display_name": "Aktivite ID"},
        {"table": "activities", "column": "subject", "alias": "subject", "display_name": "Konu"},
        {"table": "activities", "column": "type_id", "alias": "type", "display_name": "Tip"},
        {"table": "activities", "column": "owner_type_id", "alias": "owner_type", "display_name": "İlişkili Tür"},
        {"table": "activities", "column": "owner_id", "alias": "owner_id", "display_name": "İlişkili ID"},
        {"table": "activities", "column": "start_time", "alias": "start_time", "display_name": "Başlangıç"},
        {"table": "activities", "column": "end_time", "alias": "end_time", "display_name": "Bitiş"},
        {"table": "users", "column": "name", "alias": "responsible", "display_name": "Sorumlu"}
    ]'::jsonb,
    true,
    NOW()
)
ON CONFLICT DO NOTHING;

-- Comments
COMMENT ON TABLE bitrix.table_relations IS 'Tablolar arası ilişki tanımları';
COMMENT ON TABLE bitrix.advanced_views IS 'Multi-table JOIN destekli gelişmiş view tanımları';
COMMENT ON TABLE bitrix.table_metadata IS 'Tablo kolon bilgileri ve görünürlük ayarları';
