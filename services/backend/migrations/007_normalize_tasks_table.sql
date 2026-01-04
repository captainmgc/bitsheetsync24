-- Migration 007: Normalize tasks table structure

DROP TABLE IF EXISTS bitrix.tasks CASCADE;

CREATE TABLE bitrix.tasks (
    id BIGSERIAL PRIMARY KEY,
    
    -- Bitrix24 ID
    bitrix_id VARCHAR(50) UNIQUE,
    
    -- Basic Information
    title VARCHAR(500),
    description TEXT,
    
    -- Status & Priority
    status INTEGER, -- 1=Waiting, 2=In Progress, 3=Pending, 4=Supposedly complete, 5=Completed, 6=Deferred, 7=Declined
    status_name VARCHAR(100),
    priority INTEGER, -- 0=Low, 1=Medium, 2=High
    
    -- Assignment
    responsible_id VARCHAR(50),
    created_by VARCHAR(50),
    changed_by VARCHAR(50),
    
    -- Dates
    deadline TIMESTAMP WITH TIME ZONE,
    start_date_plan TIMESTAMP WITH TIME ZONE,
    end_date_plan TIMESTAMP WITH TIME ZONE,
    created_date TIMESTAMP WITH TIME ZONE,
    changed_date TIMESTAMP WITH TIME ZONE,
    closed_date TIMESTAMP WITH TIME ZONE,
    
    -- Time tracking
    duration_plan INTEGER, -- in minutes
    duration_fact INTEGER, -- in minutes
    time_estimate INTEGER, -- in seconds
    time_spent_in_logs INTEGER, -- in seconds
    
    -- Relationships
    parent_id VARCHAR(50),
    group_id VARCHAR(50),
    
    -- Flags
    allow_change_deadline BOOLEAN DEFAULT true,
    allow_time_tracking BOOLEAN DEFAULT true,
    match_work_time BOOLEAN DEFAULT false,
    
    -- Counters
    comments_count INTEGER DEFAULT 0,
    new_comments_count INTEGER DEFAULT 0,
    
    -- Tags
    tags TEXT[],
    
    -- Original data backup
    original_data JSONB,
    
    -- Sync metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_hash TEXT,
    
    CONSTRAINT tasks_bitrix_id_key UNIQUE (bitrix_id)
);

-- Indexes
CREATE INDEX idx_tasks_title ON bitrix.tasks(title);
CREATE INDEX idx_tasks_status ON bitrix.tasks(status);
CREATE INDEX idx_tasks_responsible ON bitrix.tasks(responsible_id);
CREATE INDEX idx_tasks_created_by ON bitrix.tasks(created_by);
CREATE INDEX idx_tasks_deadline ON bitrix.tasks(deadline);
CREATE INDEX idx_tasks_created_date ON bitrix.tasks(created_date);
CREATE INDEX idx_tasks_priority ON bitrix.tasks(priority);

COMMENT ON TABLE bitrix.tasks IS 'Normalized Bitrix24 tasks (Görevler) with proper column structure';
