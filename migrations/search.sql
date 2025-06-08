-- Create function for semantic search using pgvector
CREATE OR REPLACE FUNCTION match_document_sections_vectorsearch (
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id bigint,
    document_id bigint,
    content text,
    token_count integer,
    similarity float,
    document_name text,
    document_source text,
    document_type text[],
    document_authors text,
    document_published_year integer,
    document_description text
)
LANGUAGE sql stable
AS $$
    SELECT
        ds.id,
        ds.document_id,
        ds.content,
        ds.token_count,
        1 - (ds.embedding <=> query_embedding) as similarity,
        d.name as document_name,
        d.source as document_source,
        d.type as document_type,
        d.authors as document_authors,
        d.published_year as document_published_year,
        d.description as document_description
    FROM document_sections ds
    JOIN documents d ON ds.document_id = d.id
    WHERE 1 - (ds.embedding <=> query_embedding) > match_threshold
    ORDER BY ds.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Create function for full-text search
CREATE OR REPLACE FUNCTION match_document_sections_textsearch (
    query_text text,
    match_count int
)
RETURNS TABLE (
    id bigint,
    document_id bigint,
    content text,
    token_count integer,
    rank float,
    document_name text,
    document_source text,
    document_type text[],
    document_authors text,
    document_published_year integer,
    document_description text
)
LANGUAGE sql stable
AS $$
    SELECT
        ds.id,
        ds.document_id,
        ds.content,
        ds.token_count,
        ts_rank(to_tsvector('english', ds.content), plainto_tsquery('english', query_text)) as rank,
        d.name as document_name,
        d.source as document_source,
        d.type as document_type,
        d.authors as document_authors,
        d.published_year as document_published_year,
        d.description as document_description
    FROM document_sections ds
    JOIN documents d ON ds.document_id = d.id
    WHERE to_tsvector('english', ds.content) @@ plainto_tsquery('english', query_text)
    ORDER BY ts_rank(to_tsvector('english', ds.content), plainto_tsquery('english', query_text)) DESC
    LIMIT match_count;
$$;

-- Create function for hybrid search (combines vector and text search)
CREATE OR REPLACE FUNCTION match_document_sections_hybridsearch (
    query_embedding vector(1536),
    query_text text,
    match_threshold float,
    match_count int,
    vector_weight float DEFAULT 0.7,
    text_weight float DEFAULT 0.3
)
RETURNS TABLE (
    id bigint,
    document_id bigint,
    content text,
    token_count integer,
    vector_similarity float,
    text_rank float,
    combined_score float,
    document_name text,
    document_source text,
    document_type text[],
    document_authors text,
    document_published_year integer,
    document_description text
)
LANGUAGE sql stable
AS $$
    SELECT
        ds.id,
        ds.document_id,
        ds.content,
        ds.token_count,
        1 - (ds.embedding <=> query_embedding) as vector_similarity,
        ts_rank(to_tsvector('english', ds.content), plainto_tsquery('english', query_text)) as text_rank,
        (vector_weight * (1 - (ds.embedding <=> query_embedding))) + 
        (text_weight * ts_rank(to_tsvector('english', ds.content), plainto_tsquery('english', query_text))) as combined_score,
        d.name as document_name,
        d.source as document_source,
        d.type as document_type,
        d.authors as document_authors,
        d.published_year as document_published_year,
        d.description as document_description
    FROM document_sections ds
    JOIN documents d ON ds.document_id = d.id
    WHERE 
        (1 - (ds.embedding <=> query_embedding) > match_threshold)
        OR 
        (to_tsvector('english', ds.content) @@ plainto_tsquery('english', query_text))
    ORDER BY combined_score DESC
    LIMIT match_count;
$$;