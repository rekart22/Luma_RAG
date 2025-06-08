# RAG with Docling - Technical Documentation

## Project Overview

This project implements a Retrieval-Augmented Generation (RAG) system that processes PDF documents using the Docling library and stores embeddings in Supabase with pgvector for efficient semantic search.

## Architecture Changes

### Migration from LanceDB to Supabase

The original implementation used LanceDB for vector storage. We've refactored to use Supabase with pgvector for several advantages:

1. **Cloud-native**: Managed PostgreSQL with built-in vector support
2. **Scalability**: Enterprise-grade database with connection pooling
3. **Integration**: Seamless integration with web applications
4. **SQL Compatibility**: Full SQL support for complex queries
5. **Real-time Features**: Built-in subscriptions and real-time updates

### Database Design

The system uses a normalized schema in the `vecs` namespace:

#### Documents Table (`vecs.documents`)
```sql
CREATE TABLE vecs.documents (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,                -- Document title/filename
    source TEXT,                       -- Origin type (pdf, web, manual, etc.)
    type TEXT[] DEFAULT '{}',          -- Categories/tags for classification
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Document Sections Table (`vecs.document_sections`)
```sql
CREATE TABLE vecs.document_sections (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES vecs.documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,             -- Raw text chunk
    embedding VECTOR(1536),            -- OpenAI embedding vector
    token_count INTEGER,               -- Number of tokens in chunk
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexing Strategy

1. **Primary Indexes**: Standard B-tree indexes on IDs and foreign keys
2. **Vector Index**: IVFFlat index for cosine similarity search
   ```sql
   CREATE INDEX idx_document_sections_embedding 
   ON vecs.document_sections 
   USING ivfflat (embedding vector_cosine_ops);
   ```

## Implementation Details

### Core Components

#### 1. Unified CLI Interface (`main.py`)
- **Purpose**: Provides a unified command-line interface for all operations
- **Key Features**:
  - Process command: `python main.py process <pdf_path>` for document processing
  - Query command: `python main.py query` for interactive searching
  - Extract command: `python main.py extract <pdf_path>` for metadata extraction
  - List command: `python main.py list` for document management
  - Flexible flags: `--no-metadata` for faster processing

#### 2. Tokenizer Wrapper (`utils/tokenizer.py`)
- **Purpose**: Adapts OpenAI's tiktoken for use with Docling's HybridChunker
- **Key Features**:
  - Compatible with HuggingFace tokenizer interface
  - Uses cl100k_base encoding (GPT-3.5/GPT-4)
  - Handles token counting for cost optimization

#### 3. Embedding Pipeline (`embedding.py`)
- **Document Processing**: 
  - Converts PDFs using Docling with configurable paths
  - Applies hybrid chunking with configurable token limits
  - Generates OpenAI embeddings for each chunk (text-embedding-3-small)
- **Database Operations**:
  - Inserts document metadata with categorization
  - Batch processes chunks for efficiency
  - Stores embeddings with token counts

#### 4. Metadata Extraction (`book_metadata_extractor.py`)
- **Purpose**: Extracts book metadata from PDFs and enhances with web search
- **Key Features**:
  - GPT-4o extraction of title, authors, and publication year
  - Intelligent fallback to filename-based extraction
  - Web search for rich book descriptions with knowledge-based fallback
  - Database integration for metadata storage

#### 5. Search Interface (`query_documents.py`)
- **Multiple Search Methods**:
  - Vector search (semantic similarity)
  - Text search (full-text search)
  - Hybrid search (combined with configurable weights)
- **User Interface**:
  - Interactive command-line interface
  - Document browsing and search capabilities
  - Formatted result display with enhanced metadata

### Key Algorithms

#### Hybrid Chunking Strategy
```python
chunker = HybridChunker(
    tokenizer=tokenizer,
    max_tokens=MAX_TOKENS,
    merge_peers=True,
)
```
- **Token-aware Splitting**: Respects model context limits
- **Peer Merging**: Combines related sections for coherence
- **Boundary Preservation**: Maintains semantic boundaries

#### Vector Similarity Search
```sql
SELECT ds.*, d.*, 
       1 - (ds.embedding <=> query_embedding) as similarity
FROM vecs.document_sections ds
JOIN vecs.documents d ON ds.document_id = d.id
WHERE 1 - (ds.embedding <=> query_embedding) > match_threshold
ORDER BY ds.embedding <=> query_embedding
LIMIT match_count;
```
- **Cosine Distance**: Uses `<=>` operator for similarity
- **Threshold Filtering**: Eliminates low-relevance results
- **Efficient Ranking**: Leverages vector index for performance

## Configuration and Environment

### Required Environment Variables
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-api-key
```

### Configurable Parameters
- `MAX_TOKENS`: Chunk size limit (default: 8191 for text-embedding-3-small)
- `EMBEDDING_MODEL`: OpenAI model selection (default: text-embedding-3-small)
- `METADATA_EXTRACTION_MODEL`: Model for metadata extraction (default: gpt-4o)
- `CLASSIFICATION_MODEL`: Model for document classification (default: gpt-4o-mini)
- `similarity_threshold`: Search sensitivity (0.0-1.0)
- Command-line flags: `--no-metadata` for faster processing

## Performance Optimizations

### Database Level
1. **Vector Indexing**: IVFFlat for O(log n) search complexity
2. **Batch Operations**: Minimizes round-trips for large datasets
3. **Connection Pooling**: Managed by Supabase for scalability

### Application Level
1. **Token Counting**: Optimizes embedding costs
2. **Error Handling**: Robust exception management
3. **Memory Management**: Streaming for large documents

### Cost Optimization
- **Token Tracking**: Monitor OpenAI API usage
- **Batch Embeddings**: Reduce API calls
- **Caching Strategy**: Reuse embeddings when possible

## Error Handling and Logging

### Logging Strategy
```python
from termcolor import colored

print(colored("Processing chunk 1/10", "yellow"))
print(colored("Success: Document stored", "green"))
print(colored("Error: Failed to generate embedding", "red"))
```

### Batch Processing Logs
- **File-based Logs**: 
  - Detailed JSON logs: `logs/detailed_processing_log.json`
  - Summary text logs: `logs/batch_processing_log.txt`
- **Database Logs**:
  - All import operations logged to `documents_import_logs` table
  - Includes status, timing, file details, and error information
  - Supports advanced analytics on import performance

### Database Logging Schema
```sql
CREATE TABLE documents_import_logs (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_mb FLOAT NOT NULL,
    status TEXT NOT NULL,                   -- 'success', 'failed', 'timeout', 'error'
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
```

### Exception Management
- **API Failures**: Graceful OpenAI API error handling
- **Database Errors**: Transaction rollback and retry logic
- **Input Validation**: Sanitize user inputs and queries

## Security Considerations

### Authentication
- **Service Role Key**: Administrative database access
- **Environment Variables**: Secure secret management
- **Row Level Security**: Ready for multi-tenant implementations

### Data Protection
- **SQL Injection**: Parameterized queries via Supabase client
- **Input Sanitization**: Validate and escape user inputs
- **Access Control**: Schema-level permissions

## Testing and Validation

### Unit Tests (Planned)
- Tokenizer functionality
- Embedding generation
- Database operations
- Search accuracy

### Integration Tests (Planned)
- End-to-end document processing
- Search result relevance
- Performance benchmarks

## Migration Scripts

### Applied Migrations
1. **`create_vecs_schema_and_tables`**: Initial schema setup
2. **`create_semantic_search_function`**: Search function implementation

### Migration Strategy
- **Incremental Changes**: Version-controlled schema evolution
- **Rollback Support**: Reversible migration scripts
- **Data Preservation**: Safe schema modifications

## Monitoring and Analytics

### Performance Metrics
- **Search Latency**: Query response times
- **Embedding Cost**: Token usage tracking
- **Storage Growth**: Database size monitoring

### Quality Metrics
- **Search Relevance**: Result quality assessment
- **Chunk Quality**: Optimal chunk size analysis
- **User Satisfaction**: Query success rates

## Current Enhancements

### Recently Implemented
1. **Unified CLI**: Single command-line interface for all operations
2. **Intelligent Metadata Extraction**: GPT-4o extraction with filename fallback
3. **Optimized Processing**: Fast processing with `--no-metadata` flag
4. **Improved Book Descriptions**: Web search with knowledge-based fallback
5. **Multi-modal Search**: Vector, text, and hybrid search options

## Future Enhancements

### Immediate Improvements
1. **Async Processing**: Non-blocking document processing
2. **Result Caching**: Redis layer for frequent queries
3. **API Endpoints**: REST API for web integration

### Advanced Features
1. **Hybrid Search**: Combine semantic and keyword search
2. **Multi-modal**: Support for images and structured data
3. **Real-time Updates**: Live document synchronization

### Scalability Improvements
1. **Horizontal Scaling**: Multiple embedding workers
2. **Load Balancing**: Distribute search queries
3. **Sharding Strategy**: Partition large document collections

## Troubleshooting Guide

### Common Issues
1. **Connection Errors**: Check Supabase credentials
2. **Embedding Failures**: Verify OpenAI API key and quota
3. **Search Results**: Adjust similarity thresholds
4. **Performance**: Review index usage and query plans

### Debug Commands
```bash
# Test database connection
python -c "from embedding import supabase; print(supabase.table('documents').select('count').execute())"

# Verify embedding generation
python -c "from embedding import generate_embedding; print(len(generate_embedding('test')))"

# Test metadata extraction
python main.py extract your_document.pdf

# List all documents
python main.py list

# Process with no metadata (faster)
python main.py process your_document.pdf --no-metadata
```

## Contributing Guidelines

### Code Standards
- **PEP 8**: Python style guidelines
- **Type Hints**: Use type annotations
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Explicit exception management

### Development Workflow
1. **Feature Branches**: Isolate new development
2. **Code Review**: Peer review requirements
3. **Testing**: Unit and integration tests
4. **Documentation**: Update relevant docs

This documentation serves as the technical reference for the RAG system implementation and should be updated as the system evolves. 