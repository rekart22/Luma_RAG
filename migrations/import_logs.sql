-- Create documents_import_logs table in public schema
CREATE TABLE IF NOT EXISTS documents_import_logs (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_mb FLOAT NOT NULL,
    status TEXT NOT NULL, -- 'success', 'failed', 'timeout', 'error'
    document_id BIGINT REFERENCES documents(id) ON DELETE SET NULL,
    error TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    processing_time_minutes FLOAT NOT NULL,
    chunks_total INTEGER,
    chunks_avg_size INTEGER,
    chunks_min_size INTEGER,
    chunks_max_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for better performance
CREATE INDEX idx_documents_import_logs_status ON documents_import_logs(status);
CREATE INDEX idx_documents_import_logs_document_id ON documents_import_logs(document_id);
CREATE INDEX idx_documents_import_logs_start_time ON documents_import_logs(start_time);

-- Grant necessary permissions
GRANT ALL ON documents_import_logs TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE documents_import_logs_id_seq TO anon, authenticated, service_role; 