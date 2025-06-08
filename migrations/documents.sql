-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables if they exist (be careful to only drop our specific tables)
DROP TABLE IF EXISTS document_sections CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- Create documents table in public schema with new columns
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT,
    type TEXT[] DEFAULT '{}',
    authors TEXT,
    published_year INTEGER,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create document_sections table in public schema
CREATE TABLE document_sections (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- text-embedding-3-small embeddings are 1536 dimensions
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_document_sections_document_id ON document_sections(document_id);
CREATE INDEX idx_document_sections_embedding ON document_sections USING ivfflat (embedding vector_cosine_ops);

-- Create full-text search index for hybrid search
CREATE INDEX idx_document_sections_content_fts ON document_sections USING gin(to_tsvector('english', content));

-- Grant necessary permissions (optional for public schema)
GRANT ALL ON documents TO anon, authenticated, service_role;
GRANT ALL ON document_sections TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;