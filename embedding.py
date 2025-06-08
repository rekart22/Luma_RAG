import os
from typing import List, Dict, Any
import uuid

from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client
from utils.tokenizer import OpenAITokenizerWrapper
from termcolor import colored

load_dotenv()

# Configuration variables at the top - OPTIMIZED FOR RAG
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OPTIMAL CHUNKING PARAMETERS based on RAG best practices
MIN_CHUNK_SIZE = 100          # Minimum tokens per chunk (filter out very small chunks)
OPTIMAL_CHUNK_SIZE = 512      # Target chunk size for good semantic coherence
MAX_CHUNK_SIZE = 800          # Maximum tokens per chunk before splitting
OVERLAP_SIZE = 50             # Overlap between chunks for context preservation

EMBEDDING_MODEL = "text-embedding-3-small"  # More cost-effective, 1536 dimensions
CLASSIFICATION_MODEL = "gpt-4o-mini"

# Initialize clients
print(colored("Initializing clients...", "cyan"))
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Initialize tokenizer
tokenizer = OpenAITokenizerWrapper()

def generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI API - Returns 1536-dimensional vector"""
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        embedding = response.data[0].embedding
        
        # Verify correct dimensions for text-embedding-3-small
        if len(embedding) != 1536:
            print(colored(f"Warning: Unexpected embedding dimension: {len(embedding)}, expected 1536", "yellow"))
        
        return embedding
    except Exception as e:
        print(colored(f"Error generating embedding: {e}", "red"))
        raise

def count_tokens(text: str) -> int:
    """Count tokens in text using the tokenizer"""
    tokens = tokenizer.tokenize(text)
    return len(tokens)

def is_content_meaningful(text: str) -> bool:
    """Filter out table of contents, headers, and other non-meaningful content"""
    text_lower = text.lower().strip()
    
    # Skip very short content
    if len(text_lower) < 50:
        return False
    
    # Skip single characters or symbols
    if len(text_lower.strip()) <= 2:
        return False
        
    # Skip table of contents indicators
    toc_indicators = [
        'table of contents', 'contents', 'chapter', 'page', 
        'index', 'appendix', 'bibliography', 'references'
    ]
    
    # Check if content is primarily table of contents
    toc_ratio = sum(1 for indicator in toc_indicators if indicator in text_lower) / len(toc_indicators)
    if toc_ratio > 0.3:  # More than 30% TOC indicators
        return False
    
    # Skip content that's mostly formatting (tabs, newlines)
    formatting_chars = text.count('\t') + text.count('\n') + text.count(' ')
    if formatting_chars / len(text) > 0.7:  # More than 70% formatting
        return False
    
    # Check for actual sentences (content should have punctuation)
    sentence_indicators = ['.', '!', '?', ';', ':']
    has_sentences = any(punct in text for punct in sentence_indicators)
    
    return has_sentences

def merge_small_chunks(chunks: List) -> List:
    """
    Intelligently merge small neighboring chunks to create optimal-sized chunks
    Based on RAG best practices for semantic coherence
    """
    print(colored("Optimizing chunk sizes by merging small neighbors...", "cyan"))
    
    if not chunks:
        return chunks
    
    optimized_chunks = []
    current_merged_content = ""
    current_token_count = 0
    
    for i, chunk in enumerate(chunks):
        chunk_tokens = count_tokens(chunk.text)
        
        # Skip meaningless content
        if not is_content_meaningful(chunk.text):
            print(colored(f"Skipping non-meaningful chunk: {chunk.text[:50]}...", "yellow"))
            continue
        
        # If this chunk is large enough on its own
        if chunk_tokens >= MIN_CHUNK_SIZE and chunk_tokens <= MAX_CHUNK_SIZE:
            # Save any previously merged content first
            if current_merged_content and current_token_count >= MIN_CHUNK_SIZE:
                # Create a merged chunk object
                merged_chunk = type('Chunk', (), {
                    'text': current_merged_content.strip()
                })()
                optimized_chunks.append(merged_chunk)
                print(colored(f"Created merged chunk with {current_token_count} tokens", "green"))
            
            # Add this chunk as-is
            optimized_chunks.append(chunk)
            print(colored(f"Kept original chunk with {chunk_tokens} tokens", "green"))
            
            # Reset merger
            current_merged_content = ""
            current_token_count = 0
            
        # If chunk is too small, merge it
        elif chunk_tokens < MIN_CHUNK_SIZE:
            # Add to current merge
            if current_merged_content:
                current_merged_content += " " + chunk.text
            else:
                current_merged_content = chunk.text
            current_token_count += chunk_tokens
            
            # If merged content is now large enough, finalize it
            if current_token_count >= OPTIMAL_CHUNK_SIZE:
                merged_chunk = type('Chunk', (), {
                    'text': current_merged_content.strip()
                })()
                optimized_chunks.append(merged_chunk)
                print(colored(f"Created optimized merged chunk with {current_token_count} tokens", "green"))
                
                # Reset merger
                current_merged_content = ""
                current_token_count = 0
                
        # If chunk is too large, split it intelligently
        elif chunk_tokens > MAX_CHUNK_SIZE:
            # Save any previously merged content first
            if current_merged_content and current_token_count >= MIN_CHUNK_SIZE:
                merged_chunk = type('Chunk', (), {
                    'text': current_merged_content.strip()
                })()
                optimized_chunks.append(merged_chunk)
                print(colored(f"Created merged chunk with {current_token_count} tokens", "green"))
                current_merged_content = ""
                current_token_count = 0
            
            # Split large chunk intelligently
            split_chunks = split_large_chunk(chunk.text)
            optimized_chunks.extend(split_chunks)
            print(colored(f"Split large chunk into {len(split_chunks)} smaller chunks", "green"))
    
    # Handle any remaining merged content
    if current_merged_content and current_token_count >= MIN_CHUNK_SIZE:
        merged_chunk = type('Chunk', (), {
            'text': current_merged_content.strip()
        })()
        optimized_chunks.append(merged_chunk)
        print(colored(f"Created final merged chunk with {current_token_count} tokens", "green"))
    
    print(colored(f"Chunk optimization complete: {len(chunks)} → {len(optimized_chunks)} chunks", "cyan"))
    return optimized_chunks

def split_large_chunk(text: str) -> List:
    """Split large chunks intelligently at sentence boundaries"""
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Add period back if it was removed by split
        if not sentence.endswith('.') and sentence != sentences[-1]:
            sentence += '.'
        
        test_chunk = current_chunk + " " + sentence if current_chunk else sentence
        test_tokens = count_tokens(test_chunk)
        
        if test_tokens <= OPTIMAL_CHUNK_SIZE:
            current_chunk = test_chunk
        else:
            # Save current chunk if it's meaningful
            if current_chunk and count_tokens(current_chunk) >= MIN_CHUNK_SIZE:
                chunk_obj = type('Chunk', (), {'text': current_chunk.strip()})()
                chunks.append(chunk_obj)
            current_chunk = sentence
    
    # Add final chunk
    if current_chunk and count_tokens(current_chunk) >= MIN_CHUNK_SIZE:
        chunk_obj = type('Chunk', (), {'text': current_chunk.strip()})()
        chunks.append(chunk_obj)
    
    return chunks

def classify_document_type(content_sample: str) -> List[str]:
    """Classify document type using GPT-4o-mini based on content sample"""
    
    # Available document types based on the screenshot
    available_types = [
        "Anxiety Disorders", "Behavior Therapy", "Borderline Syndromes", "Brief Therapy",
        "Chapter eBooks", "Child Therapy", "Coming Soon", "Couple Therapy", "Crisis",
        "Depression", "Eating Disorders", "Family Therapy", "Group Therapy", "Mood Disorder",
        "New Original Works", "Object Relations", "Psychiatry", "Psychoanalysis",
        "Psychosomatic", "Psychotherapy", "Psychotherapy and Fiction", "Recently Added",
        "Schizophrenia", "Sex Therapy", "Substance Abuse", "Suicide", "Supervision"
    ]
    
    classification_prompt = f"""
    Based on the following document content, classify this document into one or more of the available categories.
    The document appears to be related to psychology, therapy, or mental health.
    
    Available categories:
    {', '.join(available_types)}
    
    Document content sample:
    {content_sample[:2000]}  # Limit to first 2000 characters
    
    Instructions:
    1. Analyze the content and determine which categories best fit this document
    2. Return 1-3 most relevant categories from the available list
    3. If the content doesn't clearly fit any category, choose the most general applicable one
    4. Return only the category names, separated by commas
    5. Do not add any explanation or additional text
    
    Categories:
    """
    
    try:
        print(colored("Classifying document type using GPT-4o-mini...", "cyan"))
        response = openai_client.chat.completions.create(
            model=CLASSIFICATION_MODEL,
            messages=[
                {"role": "system", "content": "You are a document classifier for psychology and therapy materials. Return only the category names separated by commas."},
                {"role": "user", "content": classification_prompt}
            ],
            max_tokens=100,
            temperature=0.1
        )
        
        classification_result = response.choices[0].message.content.strip()
        
        # Parse the result and validate against available types
        suggested_types = [t.strip() for t in classification_result.split(',')]
        valid_types = [t for t in suggested_types if t in available_types]
        
        if not valid_types:
            # Fallback to a general category
            valid_types = ["Psychotherapy"]
            
        print(colored(f"Document classified as: {', '.join(valid_types)}", "green"))
        return valid_types
        
    except Exception as e:
        print(colored(f"Error classifying document: {e}", "yellow"))
        # Fallback classification
        return ["Psychotherapy"]

def store_document_and_sections(chunks: List, filename: str, source: str = "pdf", doc_type: List[str] = None, 
                               authors: str = None, published_year: int = None, description: str = None) -> int:
    """Store document metadata and sections in Supabase with improved error handling"""
    
    if doc_type is None:
        doc_type = ["document"]
    
    try:
        # Insert document metadata
        print(colored(f"Storing document metadata for: {filename}", "cyan"))
        document_data = {
            "name": filename,
            "source": source,
            "type": doc_type,
            "authors": authors,
            "published_year": published_year,
            "description": description
        }
        
        doc_result = supabase.table("documents").insert(document_data).execute()
        
        if not doc_result.data:
            raise Exception("Failed to insert document")
            
        document_id = doc_result.data[0]["id"]
        print(colored(f"Document stored with ID: {document_id}", "green"))
        
        # Prepare document sections with improved processing
        print(colored(f"Processing {len(chunks)} optimized chunks...", "cyan"))
        sections_data = []
        successful_chunks = 0
        
        for i, chunk in enumerate(chunks):
            try:
                print(colored(f"Processing chunk {i+1}/{len(chunks)}", "yellow"))
                
                # Generate embedding for the chunk
                embedding = generate_embedding(chunk.text)
                
                # Verify embedding dimensions
                if len(embedding) != 1536:
                    print(colored(f"Warning: Chunk {i+1} has unexpected embedding size: {len(embedding)}", "yellow"))
                    continue
                
                # Count tokens
                token_count = count_tokens(chunk.text)
                
                # Skip chunks that are too small after optimization
                if token_count < MIN_CHUNK_SIZE:
                    print(colored(f"Skipping chunk {i+1} - too small ({token_count} tokens)", "yellow"))
                    continue
                
                section_data = {
                    "document_id": document_id,
                    "content": chunk.text,
                    "embedding": embedding,
                    "token_count": token_count
                }
                
                sections_data.append(section_data)
                successful_chunks += 1
                
            except Exception as e:
                print(colored(f"Error processing chunk {i+1}: {e}", "red"))
                continue
        
        # Insert all sections in batch
        if sections_data:
            print(colored(f"Inserting {len(sections_data)} document sections...", "cyan"))
            sections_result = supabase.table("document_sections").insert(sections_data).execute()
            
            if sections_result.data:
                print(colored(f"Successfully stored {len(sections_result.data)} document sections", "green"))
            else:
                raise Exception("Failed to insert document sections")
        else:
            print(colored("No valid sections to store after processing", "yellow"))
            
        return document_id
            
    except Exception as e:
        print(colored(f"Error storing document: {e}", "red"))
        raise

def main(pdf_path: str = None, skip_metadata: bool = False):
    """Main function to process document and store in Supabase with optimized chunking"""
    
    print(colored("Starting OPTIMIZED document processing pipeline...", "cyan"))
    
    # --------------------------------------------------------------
    # Extract the data from local PDF
    # --------------------------------------------------------------
    
    if pdf_path is None:
        PDF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "The_Power_Of_Now_Eckhart_Tolle.pdf")
    else:
        PDF_PATH = pdf_path
    
    print(colored(f"Converting document: {PDF_PATH}", "cyan"))
    converter = DocumentConverter()
    result = converter.convert(PDF_PATH)
    
    # --------------------------------------------------------------
    # Extract book metadata from first pages with enhanced web search
    # --------------------------------------------------------------
    
    if not skip_metadata:
        from book_metadata_extractor import process_book_metadata
        
        print(colored("Extracting book metadata with enhanced web search...", "cyan"))
        metadata_result = process_book_metadata(PDF_PATH)
        
        # Get extracted metadata and description
        metadata = metadata_result["metadata"]
        description = metadata_result["description"]
    else:
        print(colored("Skipping metadata extraction (--no-metadata flag)", "yellow"))
        # Use filename-based fallback
        filename_base = os.path.splitext(os.path.basename(PDF_PATH))[0]
        metadata = {
            "title": filename_base.replace('_', ' ').replace('-', ' '),
            "authors": None,
            "published_year": None
        }
        description = None
    
    # --------------------------------------------------------------
    # Apply OPTIMIZED hybrid chunking with intelligent merging
    # --------------------------------------------------------------
    
    print(colored("Applying initial chunking...", "cyan"))
    chunker = HybridChunker(
        tokenizer=tokenizer,
        max_tokens=OPTIMAL_CHUNK_SIZE,  # Use optimal size instead of max
        merge_peers=True,
    )
    
    chunk_iter = chunker.chunk(dl_doc=result.document)
    initial_chunks = list(chunk_iter)
    
    print(colored(f"Initial chunking generated {len(initial_chunks)} chunks", "green"))
    
    # Apply intelligent chunk optimization
    optimized_chunks = merge_small_chunks(initial_chunks)
    
    # --------------------------------------------------------------
    # Classify document type using optimized chunks
    # --------------------------------------------------------------
    
    # Get content sample from meaningful chunks for classification
    content_sample = ""
    meaningful_chunks = [chunk for chunk in optimized_chunks if is_content_meaningful(chunk.text)]
    
    for chunk in meaningful_chunks[:3]:  # Use first 3 meaningful chunks
        content_sample += chunk.text + "\n\n"
        if len(content_sample) > 3000:  # Limit sample size
            break
    
    # Classify document type
    document_types = classify_document_type(content_sample)
    
    # --------------------------------------------------------------
    # Store in Supabase with optimized chunks
    # --------------------------------------------------------------
    
    # Use extracted title or fallback to filename
    filename = metadata.get("title") or os.path.basename(PDF_PATH)
    
    document_id = store_document_and_sections(
        chunks=optimized_chunks,
        filename=filename,
        source="pdf",
        doc_type=document_types,
        authors=metadata.get("authors"),
        published_year=metadata.get("published_year"),
        description=description
    )
    
    print(colored(f"OPTIMIZED document processing completed successfully! Document ID: {document_id}", "green"))
    
    # Print detailed summary
    print(colored("\n" + "="*60, "cyan"))
    print(colored("OPTIMIZED PROCESSING SUMMARY:", "cyan"))
    print(colored("="*60, "cyan"))
    print(colored(f"Title: {metadata.get('title', 'Not found')}", "white"))
    print(colored(f"Authors: {metadata.get('authors', 'Not found')}", "white"))
    print(colored(f"Published Year: {metadata.get('published_year', 'Not found')}", "white"))
    print(colored(f"Document Types: {', '.join(document_types)}", "white"))
    print(colored(f"Initial Chunks: {len(initial_chunks)}", "white"))
    print(colored(f"Optimized Chunks: {len(optimized_chunks)}", "white"))
    print(colored(f"Document ID: {document_id}", "white"))
    
    # Print chunk size statistics
    token_counts = [count_tokens(chunk.text) for chunk in optimized_chunks]
    if token_counts:
        print(colored(f"Chunk size stats: Min={min(token_counts)}, Max={max(token_counts)}, Avg={sum(token_counts)//len(token_counts)}", "white"))
    
    if description:
        print(colored(f"\nDescription:", "yellow"))
        print(colored(description, "white"))

if __name__ == "__main__":
    main()