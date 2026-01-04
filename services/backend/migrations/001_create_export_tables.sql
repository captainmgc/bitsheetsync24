-- Create Export Log Tables
-- Run this migration to set up export tracking

-- Export Logs Table
CREATE TABLE IF NOT EXISTS bitrix.export_logs (
    id SERIAL PRIMARY KEY,
    
    -- Export Configuration
    export_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    
    -- Date Range (for date_range export type)
    date_from TIMESTAMP,
    date_to TIMESTAMP,
    
    -- Related Tables
    related_entities JSONB,
    
    -- Full Configuration
    config JSONB NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    
    -- Progress
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    
    -- Batch Information
    total_batches INTEGER DEFAULT 0,
    completed_batches INTEGER DEFAULT 0,
    batch_size INTEGER DEFAULT 500,
    
    -- Google Sheets
    sheet_url VARCHAR(500),
    sheet_id VARCHAR(200),
    sheet_gid VARCHAR(50),
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Errors
    error_message TEXT,
    error_details JSONB,
    
    -- Webhook Trigger
    triggered_by_webhook BOOLEAN DEFAULT FALSE,
    webhook_event_type VARCHAR(100),
    webhook_entity_id INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    updated_at TIMESTAMP DEFAULT now() NOT NULL,
    created_by VARCHAR(100)
);

-- Indexes for export_logs
CREATE INDEX IF NOT EXISTS idx_export_logs_status ON bitrix.export_logs(status);
CREATE INDEX IF NOT EXISTS idx_export_logs_entity ON bitrix.export_logs(entity_name);
CREATE INDEX IF NOT EXISTS idx_export_logs_created ON bitrix.export_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_export_logs_webhook ON bitrix.export_logs(triggered_by_webhook) WHERE triggered_by_webhook = TRUE;

-- Export Batch Logs Table
CREATE TABLE IF NOT EXISTS bitrix.export_batch_logs (
    id SERIAL PRIMARY KEY,
    export_log_id INTEGER NOT NULL,
    
    batch_number INTEGER NOT NULL,
    batch_size INTEGER NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    
    -- Records
    record_ids JSONB,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Errors
    error_message TEXT,
    errors JSONB,
    
    -- Retry
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    updated_at TIMESTAMP DEFAULT now() NOT NULL
);

-- Indexes for export_batch_logs
CREATE INDEX IF NOT EXISTS idx_export_batch_logs_export ON bitrix.export_batch_logs(export_log_id);
CREATE INDEX IF NOT EXISTS idx_export_batch_logs_status ON bitrix.export_batch_logs(status);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_export_logs_updated_at
    BEFORE UPDATE ON bitrix.export_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_export_batch_logs_updated_at
    BEFORE UPDATE ON bitrix.export_batch_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON bitrix.export_logs TO bitsheet;
GRANT SELECT, INSERT, UPDATE, DELETE ON bitrix.export_batch_logs TO bitsheet;
GRANT USAGE, SELECT ON SEQUENCE bitrix.export_logs_id_seq TO bitsheet;
GRANT USAGE, SELECT ON SEQUENCE bitrix.export_batch_logs_id_seq TO bitsheet;
