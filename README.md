# RAG with Docling and Supabase

A modern Retrieval-Augmented Generation (RAG) system that processes PDF documents using the Docling library and stores embeddings in Supabase with pgvector for efficient semantic search.

## 🚀 Features

- **PDF Document Processing**: Intelligent document conversion and chunking using Docling
- **Vector Embeddings**: OpenAI embeddings with pgvector storage in Supabase
- **Semantic Search**: Fast similarity search with configurable thresholds
- **Interactive CLI**: User-friendly command-line interface for querying documents
- **Cloud-Native**: Scalable Supabase backend with managed PostgreSQL
- **Token Optimization**: Cost-effective embedding generation with token tracking
- **Batch Processing**: Process multiple PDF files with detailed logging
- **Database Logging**: All import operations logged to Supabase for analytics

## 📋 Prerequisites

- Python 3.7+
- Supabase account with a project
- OpenAI API key
- pgvector extension enabled in Supabase

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd RAG-with-Docling
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   OPENAI_API_KEY=your-openai-api-key
   ```

4. **Initialize the database:**
   The migration scripts will create the necessary tables and functions when you first run the embedding script.

## 📚 Usage

### Unified Command-Line Interface

The system now provides a unified entry point through `main.py`:

```bash
# Process and embed a PDF document
python main.py process document.pdf

# Start interactive query interface
python main.py query

# Extract metadata from a document
python main.py extract document.pdf

# List all documents in database
python main.py list
```

### Processing Documents

To process a PDF document and store its embeddings:

```bash
python main.py process your_document.pdf
```

This will:
- Convert the PDF using Docling
- Extract book metadata (title, authors, publication year)
- Generate book description using web search
- Chunk the document intelligently using hybrid chunking
- Generate OpenAI embeddings for each chunk
- Store everything in your Supabase database

### Querying Documents

To search through your processed documents:

```bash
python main.py query
```

The interactive interface allows you to:
- Choose between vector, text, or hybrid search modes
- Browse available documents with metadata
- Perform semantic searches with similarity scores
- View ranked results with document context
- See enhanced metadata including authors and publication years

### Example Queries

Try searching for:
- "machine learning techniques"
- "document processing methods"
- "artificial intelligence applications"

## 🏗️ Architecture

### Database Schema

The system uses a normalized schema in the `vecs` namespace:

```sql
-- Document metadata
CREATE TABLE vecs.documents (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT,
    type TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document chunks with embeddings
CREATE TABLE vecs.document_sections (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES vecs.documents(id),
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Key Components

- **`utils/tokenizer.py`**: OpenAI tokenizer wrapper for Docling compatibility
- **`embedding.py`**: Document processing and embedding pipeline
- **`query_documents.py`**: Interactive search interface
- **Migration scripts**: Database schema and function setup

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for admin access | Yes |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Yes |

### Configurable Parameters

In `embedding.py`:
- `MAX_TOKENS`: Maximum tokens per chunk (default: 8192)
- `EMBEDDING_MODEL`: OpenAI model for embeddings (default: text-embedding-ada-002)

In `query_documents.py`:
- `similarity_threshold`: Minimum similarity score (default: 0.7)
- `limit`: Maximum number of search results (default: 5)

## 🔧 Development

### Project Structure

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
├── .env                          # Environment variables (create this)
├── .gitignore                    # Git ignore rules
└── .cursorignore                 # Cursor AI ignore rules
```

### Adding New Documents

To process different documents, modify the `main()` function in `embedding.py`:

```python
# For local files
result = converter.convert("path/to/your/document.pdf")

# For URLs
result = converter.convert("https://example.com/document.pdf")
```

### Customizing Document Types

Update the document metadata when storing:

```python
store_document_and_sections(
    chunks=chunks,
    filename="Your Document Title",
    source="local",  # or "web", "manual", etc.
    doc_type=["category1", "category2", "custom_tag"]
)
```

## 📊 Performance

### Search Performance
- **Vector Index**: IVFFlat index for sub-linear search complexity
- **Batch Operations**: Efficient bulk inserts for large documents
- **Connection Pooling**: Managed by Supabase for scalability

### Batch Processing
- **Multi-file Processing**: Process entire directories of PDFs
- **Detailed Logging**: Track success rates, processing times, and errors
- **Database Integration**: All processing results logged to Supabase
- **Error Handling**: Robust recovery from processing failures

### Cost Optimization
- **Token Tracking**: Monitor OpenAI API usage per chunk
- **Embedding Reuse**: Avoid regenerating embeddings for identical content
- **Configurable Chunking**: Optimize chunk size for cost vs. accuracy

## 🧪 Testing

### Manual Testing

Test database connection:
```bash
python -c "from embedding import supabase; print('Connection successful!')"
```

Test embedding generation:
```bash
python -c "from embedding import generate_embedding; print(f'Embedding size: {len(generate_embedding('test'))}')"
```

## 📈 Monitoring

### Metrics to Track
- Search latency and accuracy
- Embedding generation costs
- Database storage growth
- Query patterns and success rates
- Import processing times and success rates

### Logs
The system uses color-coded logging via `termcolor`:
- 🔵 **Cyan**: Processing status
- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings and progress
- 🔴 **Red**: Errors and failures

### Batch Processing Logs
- **File-based Logs**:
  - `logs/detailed_processing_log.json`: Complete processing details
  - `logs/batch_processing_log.txt`: Human-readable summary
- **Database Logs**:
  - Table: `documents_import_logs`
  - Includes: status, timing, file details, error information
  - Enables analytics on processing performance

### Usage
```bash
# Process all PDFs in the books directory
python batch_processor.py

# Test file access without processing
python batch_processor.py --test-only
```

## 🚧 Roadmap

### Immediate Improvements
- [ ] Async processing for large documents
- [ ] Result caching with Redis
- [ ] REST API endpoints
- [ ] Support for additional file formats

### Advanced Features
- [ ] Hybrid search (semantic + keyword)
- [ ] Multi-modal support (images, tables)
- [ ] Real-time document updates
- [ ] User authentication and access control

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Update documentation as needed
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code style
- Add type hints to new functions
- Include docstrings for all public methods
- Update `features.md` for new capabilities

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Docling](https://github.com/DS4SD/docling) for document processing
- [Supabase](https://supabase.com/) for the backend infrastructure
- [pgvector](https://github.com/pgvector/pgvector) for vector similarity search
- [OpenAI](https://openai.com/) for embedding models

## 📞 Support

For questions and support:
- Check the `documentation.md` file for technical details
- Review `features.md` for current capabilities
- Open an issue for bugs or feature requests

---

**Built with ❤️ for efficient document retrieval and AI-powered search** 