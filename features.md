# RAG with Docling - Features Documentation

## Overview
A Retrieval-Augmented Generation (RAG) system using Docling for document processing and Supabase with pgvector for vector storage and semantic search.

## Current Features

### ✅ Unified Command-Line Interface
- **Main Entry Point**: Single `main.py` script with subcommands for all operations
- **Process Command**: `python main.py process <pdf_path>` for document processing
- **Fast Processing Mode**: `--no-metadata` flag for skipping metadata extraction
- **Query Command**: `python main.py query` for interactive search with multiple modes
- **Extract Command**: `python main.py extract <pdf_path>` for standalone metadata extraction
- **List Command**: `python main.py list` for database document listing
- **Flexible Arguments**: Command-specific flags and options
- **Batch Processing**: `python batch_processor.py` for processing multiple documents

### ✅ Document Processing Pipeline
- **PDF Document Conversion**: Uses Docling library to convert PDF documents to structured format
- **Configurable PDF Paths**: Supports processing of any PDF with command-line arguments
- **Hybrid Chunking**: Implements intelligent text chunking with token-aware splitting
- **OpenAI Embeddings**: Generates embeddings using `text-embedding-3-small` model (cost-optimized)
- **Token Counting**: Tracks token count for each chunk for cost optimization
- **Fast Processing Mode**: Option to skip metadata extraction for faster processing

### ✅ Database Schema (Supabase + pgvector)
- **public.documents**: Stores document metadata (name, source, type, authors, published_year, description, created_at)
- **public.document_sections**: Stores chunks with embeddings and metadata
- **Vector Indexing**: Uses ivfflat index for efficient similarity search
- **Full-text Indexing**: GIN index for PostgreSQL text search
- **Foreign Key Relationships**: Proper relational structure between documents and sections

### ✅ Multi-Modal Search System
- **Vector Search**: Semantic similarity using pgvector cosine similarity
- **Text Search**: Full-text search using PostgreSQL tsvector
- **Hybrid Search**: Combined vector and text search with configurable weights
- **Configurable Thresholds**: Adjustable similarity thresholds and result limits
- **Rich Metadata**: Returns document context, source, type, authors, publication year, and scores
- **Multiple SQL Functions**: Optimized PostgreSQL functions for different search types

### ✅ Book Metadata Extraction (Optimized)
- **GPT-4o Integration**: Extracts title, authors, and publication year from first pages
- **Intelligent Fallback**: Filename-based metadata extraction when AI extraction fails
- **OpenAI Web Search**: Generates book descriptions using web search with knowledge-based fallback
- **Automatic Classification**: Categorizes books into therapy/psychology domains using GPT-4o-mini
- **Unified Processing**: Single optimized function for all metadata extraction needs
- **Standalone Usage**: Can be used independently via `python main.py extract <pdf_path>`
- **Database Integration**: Optional updating of document records with extracted metadata

### ✅ Interactive Query Interface
- **Multi-Search Interface**: Support for vector, text, and hybrid search modes
- **Command-Line Interface**: User-friendly menu-driven search system via `python main.py query`
- **Document Listing**: Browse available documents with metadata via `python main.py list`
- **Enhanced Results Display**: Shows different score types, authors, publication years
- **Similarity Scores**: Different scoring metrics based on search type (vector, text, hybrid)
- **Formatted Results**: Color-coded, structured result display
- **Content Truncation**: Smart content preview for readability
- **Configurable Parameters**: Adjustable similarity thresholds and result limits

### ✅ Batch Processing System
- **Directory Scanning**: Automatically finds all PDF files in the books directory
- **Multi-file Processing**: Sequential processing of all detected PDF files
- **File Testing**: Pre-checks file accessibility before batch processing
- **Detailed Logging**: Comprehensive logs of processing time, success/failure status, and errors
- **Command-line Options**: Support for test-only mode via `--test-only` flag
- **Progress Tracking**: Real-time progress display with success rate tracking
- **Error Recovery**: Continues processing despite individual file failures
- **Performance Metrics**: Tracking of total and average processing times

### ✅ Enhanced Logging System
- **File-based Logs**: Structured JSON and human-readable text logs in logs directory
- **Database Logs**: All processing results stored in Supabase `documents_import_logs` table
- **Detailed Metrics**: Processing time, file size, chunk counts, and error tracking
- **Performance Analysis**: Statistical data on processing efficiency and success rates
- **Document-Import Correlation**: Links import logs to document IDs for traceability
- **Chunk Statistics**: Records metrics on chunk sizes (min/max/avg) for optimization
- **Colorized Console Output**: Enhanced terminal output with status indicators

## Technical Architecture

### Libraries Used
- **docling**: Document conversion and processing
- **openai**: Embedding generation
- **supabase**: Database client and vector operations
- **pgvector**: PostgreSQL vector extension
- **termcolor**: Enhanced console output
- **tiktoken**: Token counting for cost management

### Database Schema
```sql
-- Documents table with enhanced metadata
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

-- Document sections table with full-text search support
CREATE TABLE document_sections (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Import logs table for batch processing
CREATE TABLE documents_import_logs (
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

-- Indexes for performance
CREATE INDEX idx_document_sections_embedding ON document_sections USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_document_sections_content_fts ON document_sections USING gin(to_tsvector('english', content));
CREATE INDEX idx_documents_import_logs_status ON documents_import_logs(status);
CREATE INDEX idx_documents_import_logs_document_id ON documents_import_logs(document_id);
CREATE INDEX idx_documents_import_logs_start_time ON documents_import_logs(start_time);
```

### Key Functions
- `generate_embedding()`: Creates OpenAI embeddings for text
- `extract_book_metadata()`: Extracts metadata using GPT-4o
- `get_book_description()`: Generates descriptions using OpenAI web search
- `store_document_and_sections()`: Batch inserts documents and chunks with metadata
- `vector_search()`: Performs semantic similarity search
- `text_search()`: Performs full-text search
- `hybrid_search()`: Combines vector and text search
- `match_document_sections_vectorsearch()`: PostgreSQL function for vector operations
- `match_document_sections_textsearch()`: PostgreSQL function for text search
- `match_document_sections_hybridsearch()`: PostgreSQL function for hybrid search
- `batch_process_books()`: Processes multiple PDF files with logging
- `log_to_supabase()`: Logs processing results to Supabase database

## Configuration

### Environment Variables Required
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key for database access
- `OPENAI_API_KEY`: OpenAI API key for embeddings

### Configurable Parameters
- `MAX_TOKENS`: Maximum tokens per chunk (default: 8192)
- `EMBEDDING_MODEL`: OpenAI model name (default: text-embedding-ada-002)
- `similarity_threshold`: Minimum similarity score for results (default: 0.7)

## Usage Examples

### Processing a Document
```python
python embedding.py
```

### Querying Documents
```python
python query_documents.py
```

## Performance Considerations
- **Batch Processing**: Chunks are processed and inserted in batches
- **Vector Indexing**: ivfflat index for sub-linear search performance
- **Token Optimization**: Tracks token usage for cost management
- **Connection Pooling**: Efficient database connection management

## Future Enhancements

### ✅ Performance Optimizations
- **Optimized Workflows**: Unified CLI for streamlined operations
- **Fast Processing Mode**: Skip metadata extraction for quicker processing
- **Token-aware Chunking**: Optimized for embedding model context limits
- **Cost-effective Models**: Using text-embedding-3-small for better cost/performance
- **Efficient Metadata Extraction**: First-page extraction to minimize processing
- **Intelligent Fallbacks**: Graceful degradation when services are unavailable

### 🔄 Planned Features
- **Multi-format Support**: Support for DOCX, TXT, and other formats
- **Advanced Chunking**: Semantic-aware chunking strategies
- **Reranking**: Cross-encoder models for improved precision
- **Caching Layer**: Redis for frequently accessed embeddings
- **API Endpoints**: REST API for document upload and search
- **Real-time Processing**: Async processing for large documents
- **Vector Optimization**: Experiment with different embedding models
- **Authentication**: User-based document access control
- **Batch Processing**: Large-scale book processing capabilities

### 🎯 Milestone Goals
1. **Phase 1**: Complete basic RAG functionality ✅
2. **Phase 2**: Advanced search capabilities ✅
3. **Phase 3**: Book metadata extraction ✅
4. **Phase 3.5**: Unified CLI and optimizations ✅
5. **Phase 4**: Production-ready API
6. **Phase 5**: Multi-user support and scaling

## Project Structure
```
RAG-with-Docling/
├── utils/
│   └── tokenizer.py              # OpenAI tokenizer wrapper
├── migrations/
│   ├── documents.sql             # Database schema
│   ├── search.sql                # Search functions
│   └── import_logs.sql           # Import logging schema
├── main.py                       # Unified CLI entry point
├── embedding.py                  # Document processing pipeline
├── query_documents.py            # Search interface
├── book_metadata_extractor.py    # Metadata extraction with web search
├── batch_processor.py            # Batch document processing
├── requirements.txt              # Python dependencies
├── features.md                   # Feature documentation
├── documentation.md              # Technical documentation
├── README.md                     # Project overview
├── .env                          # Environment variables
└── .gitignore                    # Git ignore rules
```

## Dependencies
See `requirements.txt` for complete dependency list:
- docling
- openai
- supabase
- python-dotenv
- termcolor
- tiktoken
- transformers

## Security Notes
- All API keys stored in `.env` file
- Service role key used for administrative operations
- Proper error handling with try-catch blocks
- Input validation for user queries
- Command-line argument validation