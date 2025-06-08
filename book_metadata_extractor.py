import os
import re
import json
from typing import Dict, Optional
from docling.document_converter import DocumentConverter
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client
from termcolor import colored

load_dotenv()

# Configuration variables at the top
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
METADATA_EXTRACTION_MODEL = "gpt-4o"
DESCRIPTION_MODEL = "gpt-4o"

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def extract_first_pages_content(pdf_path: str, max_pages: int = 3) -> str:
    """Extract content from the first few pages of a PDF for metadata extraction"""
    try:
        print(colored(f"Extracting content from first {max_pages} pages of: {os.path.basename(pdf_path)}", "cyan"))
        
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        
        # Get the full markdown content
        full_content = result.document.export_to_markdown()
        
        # Take approximately the first few pages worth of content
        # Assuming roughly 2500 characters per page for metadata extraction
        first_pages_content = full_content[:max_pages * 2500]
        
        print(colored(f"Extracted {len(first_pages_content)} characters from first pages", "green"))
        return first_pages_content
        
    except Exception as e:
        print(colored(f"Error extracting PDF content: {e}", "red"))
        raise

def extract_book_metadata(content: str, pdf_filename: str = None) -> Dict[str, Optional[str]]:
    """Extract book metadata using GPT-4o with intelligent fallback and enhanced year detection"""
    
    metadata_prompt = f"""
    Analyze the following content from the beginning of a book and extract the metadata.
    Look for the book title, author(s), and publication year.
    
    Content:
    {content[:4000]}
    
    Instructions:
    1. Extract the book title (main title, not chapter titles)
    2. Extract all authors (if multiple, separate with commas)
    3. Extract the publication year (if found) - look for copyright dates, publication dates, first edition dates
    4. Return ONLY valid JSON with keys: "title", "authors", "published_year"
    5. If any information is not found, use null for that field
    6. For published_year, return only the year as an integer (e.g., 1997, 2000)
    7. Be precise and only extract information that is clearly stated
    8. Look for patterns like "Copyright YYYY", "Published YYYY", "First published YYYY", "© YYYY"
    
    Example format: {{"title": "Book Title", "authors": "Author Name", "published_year": 2000}}
    """
    
    try:
        print(colored("Extracting book metadata using GPT-4o...", "cyan"))
        response = openai_client.chat.completions.create(
            model=METADATA_EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": "You are a book metadata extraction specialist. Return only valid JSON with the requested fields. Pay special attention to copyright and publication year information."},
                {"role": "user", "content": metadata_prompt}
            ],
            max_tokens=300,
            temperature=0.1
        )
        
        metadata_json = response.choices[0].message.content.strip()
        
        # Clean JSON response if needed
        if not metadata_json.startswith('{'):
            start_idx = metadata_json.find('{')
            end_idx = metadata_json.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                metadata_json = metadata_json[start_idx:end_idx]
        
        # Parse the JSON response
        metadata = json.loads(metadata_json)
        
        # If year is missing, try enhanced extraction
        if not metadata.get("published_year") and (metadata.get("title") or metadata.get("authors")):
            enhanced_year = extract_publication_year_enhanced(metadata.get("title"), metadata.get("authors"))
            if enhanced_year:
                metadata["published_year"] = enhanced_year
        
        print(colored(f"Extracted metadata: {metadata}", "green"))
        return metadata
        
    except (json.JSONDecodeError, Exception) as e:
        print(colored(f"Error extracting metadata: {e}", "yellow"))
        
        # Intelligent fallback based on filename if available
        if pdf_filename:
            fallback_metadata = _extract_metadata_from_filename(pdf_filename)
            print(colored(f"Using filename-based fallback: {fallback_metadata}", "yellow"))
            return fallback_metadata
        
        # Generic fallback
        return {"title": None, "authors": None, "published_year": None}

def extract_publication_year_enhanced(title: str, authors: str = None) -> Optional[int]:
    """Enhanced publication year extraction using OpenAI web search"""
    
    if not title:
        return None
    
    search_query = f'"{title}"'
    if authors:
        search_query += f' by "{authors}"'
    search_query += " publication year copyright date first published"
    
    try:
        print(colored(f"Searching for publication year: {title}", "cyan"))
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a bibliographic research assistant. Search for publication information and return only the publication year as a 4-digit integer, or 'null' if not found."
                },
                {
                    "role": "user", 
                    "content": f"""Find the original publication year for the book:
                    Title: {title}
                    {f'Author: {authors}' if authors else ''}
                    
                    Search for:
                    - Original publication date
                    - First edition year
                    - Copyright year
                    - Initial release date
                    
                    Return ONLY the 4-digit year (e.g., 1997) or 'null' if not found.
                    Do not include any other text or explanation."""
                }
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        year_response = response.choices[0].message.content.strip()
        
        # Try to extract year from response
        if year_response and year_response.lower() != 'null':
            # Extract 4-digit year
            year_match = re.search(r'\b(19|20)\d{2}\b', year_response)
            if year_match:
                year = int(year_match.group())
                print(colored(f"Found publication year: {year}", "green"))
                return year
        
        print(colored("No publication year found via web search", "yellow"))
        return None
        
    except Exception as e:
        print(colored(f"Error searching for publication year: {e}", "yellow"))
        return None

def _extract_metadata_from_filename(filename: str) -> Dict[str, Optional[str]]:
    """Extract metadata from PDF filename as fallback"""
    # Remove file extension and clean filename
    clean_name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
    
    # Simple patterns for common filename formats
    # Pattern: "Title Author" or "Title by Author" or "Author - Title"
    patterns = [
        r'^(.+?)\s+by\s+(.+)$',  # "Title by Author"
        r'^(.+?)\s+-\s+(.+)$',   # "Author - Title" 
        r'^(.+?)\s+(.+)$'        # "Title Author" (last resort)
    ]
    
    for pattern in patterns:
        match = re.match(pattern, clean_name, re.IGNORECASE)
        if match:
            if 'by' in pattern:
                title, author = match.groups()
            elif '-' in pattern:
                author, title = match.groups()
            else:
                # For generic pattern, assume first part is title
                parts = clean_name.split()
                if len(parts) >= 2:
                    title = ' '.join(parts[:-1])
                    author = parts[-1]
                else:
                    title = clean_name
                    author = None
            
            return {
                "title": title.strip(),
                "authors": author.strip() if author else None,
                "published_year": None
            }
    
    # If no pattern matches, use the whole filename as title
    return {
        "title": clean_name,
        "authors": None,
        "published_year": None
    }

def get_book_description(title: str, authors: str = None) -> Optional[str]:
    """Get book description using OpenAI with enhanced web search and improved fallback"""
    
    book_query = f'"{title}"'
    if authors:
        book_query += f' by "{authors}"'
    
    # Try enhanced web search first
    try:
        print(colored(f"Getting book description with enhanced web search for: {title}", "cyan"))
        
        # Use the latest OpenAI model with web browsing capability
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a book information specialist. Provide accurate, informative book descriptions based on reliable sources."
                },
                {
                    "role": "user",
                    "content": f"""Research and provide a comprehensive description for the book:
                    
                    Title: {title}
                    {f'Author: {authors}' if authors else ''}
                    
                    Provide a detailed description (200-300 words) that includes:
                    1. Brief summary of the book's main content and purpose
                    2. Key themes, concepts, or topics covered
                    3. Target audience (e.g., psychology students, therapists, general readers)
                    4. The book's approach or methodology
                    5. Its significance or impact in its field
                    
                    Focus on factual content about the book itself. Avoid reviews, ratings, or publication details.
                    Write in a professional, informative tone."""
                }
            ],
            max_tokens=500,
            temperature=0.2
        )
        
        description = response.choices[0].message.content.strip()
        
        # Clean any remaining citations or unwanted formatting
        cleaned_description = re.sub(r'\[(.*?)\]\(https?://[^\s\)]+\)', r'\1', description)
        cleaned_description = re.sub(r'https?://[^\s]+', '', cleaned_description)
        
        print(colored(f"Generated enhanced description", "green"))
        return cleaned_description
        
    except Exception as e:
        print(colored(f"Enhanced web search failed: {e}", "yellow"))
        print(colored("Falling back to knowledge-based description...", "yellow"))
        
        # Fallback to knowledge-based description with improved prompt
        try:
            description_prompt = f"""
            Based on your knowledge, provide a detailed description for the book "{title}" {f'by {authors}' if authors else ''}.
            
            Include:
            1. Brief summary of the book's content and main message (3-4 sentences)
            2. Primary themes, concepts, or therapeutic approaches covered
            3. Target audience (psychology professionals, general readers, specific therapy contexts)
            4. The book's significance or unique contribution to its field
            5. Practical applications or techniques discussed (if applicable)
            
            Write a comprehensive but concise description (200-250 words).
            Focus on the book's actual content and value to readers.
            """
            
            response = openai_client.chat.completions.create(
                model=DESCRIPTION_MODEL,
                messages=[
                    {"role": "system", "content": "You are a book information specialist with extensive knowledge about psychology, therapy, and self-help literature. Provide accurate, detailed descriptions."},
                    {"role": "user", "content": description_prompt}
                ],
                max_tokens=450,
                temperature=0.2
            )
            
            description = response.choices[0].message.content.strip()
            print(colored(f"Generated enhanced knowledge-based description", "green"))
            return description
            
        except Exception as inner_e:
            print(colored(f"Failed to generate description: {inner_e}", "red"))
            return None

def update_document_metadata(document_id: int, metadata: Dict, description: str = None) -> bool:
    """Update document with extracted metadata"""
    
    try:
        print(colored(f"Updating document {document_id} with metadata...", "cyan"))
        
        update_data = {}
        
        if metadata.get("authors"):
            update_data["authors"] = metadata["authors"]
        
        if metadata.get("published_year"):
            update_data["published_year"] = metadata["published_year"]
            
        if description:
            update_data["description"] = description
        
        if update_data:
            result = supabase.table("documents").update(update_data).eq("id", document_id).execute()
            
            if result.data:
                print(colored(f"Successfully updated document metadata", "green"))
                return True
            else:
                print(colored(f"No document found with ID {document_id}", "yellow"))
                return False
        else:
            print(colored("No metadata to update", "yellow"))
            return False
            
    except Exception as e:
        print(colored(f"Error updating document metadata: {e}", "red"))
        return False

def process_book_metadata(pdf_path: str, document_id: int = None) -> Dict:
    """Main function to process book metadata extraction"""
    
    print(colored("Starting book metadata extraction pipeline...", "cyan"))
    
    try:
        # Step 1: Extract content from first pages
        first_pages_content = extract_first_pages_content(pdf_path)
        
        # Step 2: Extract metadata using GPT-4o
        pdf_filename = os.path.basename(pdf_path)
        metadata = extract_book_metadata(first_pages_content, pdf_filename)
        
        # Step 3: Get book description if we have title
        description = None
        if metadata.get("title"):
            description = get_book_description(
                metadata["title"], 
                metadata.get("authors")
            )
        
        # Step 4: Update document if document_id provided
        if document_id:
            update_success = update_document_metadata(document_id, metadata, description)
            if not update_success:
                print(colored("Failed to update document in database", "red"))
        
        # Return all extracted information
        result = {
            "metadata": metadata,
            "description": description,
            "pdf_path": pdf_path
        }
        
        print(colored("Book metadata extraction completed!", "green"))
        return result
        
    except Exception as e:
        print(colored(f"Error in metadata extraction pipeline: {e}", "red"))
        raise

if __name__ == "__main__":
    # Test the metadata extraction with a sample file
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Default test file
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "The_Power_Of_Now_Eckhart_Tolle.pdf")
    
    if not os.path.exists(pdf_path):
        print(colored(f"PDF file not found: {pdf_path}", "red"))
        print(colored("Usage: python book_metadata_extractor.py [pdf_path]", "yellow"))
        sys.exit(1)
    
    # Test the metadata extraction
    result = process_book_metadata(pdf_path)
    
    print(colored("\n" + "="*50, "cyan"))
    print(colored("EXTRACTED METADATA:", "cyan"))
    print(colored("="*50, "cyan"))
    
    metadata = result["metadata"]
    print(colored(f"Title: {metadata.get('title', 'Not found')}", "white"))
    print(colored(f"Authors: {metadata.get('authors', 'Not found')}", "white"))
    print(colored(f"Published Year: {metadata.get('published_year', 'Not found')}", "white"))
    
    if result["description"]:
        print(colored(f"\nDescription:", "yellow"))
        print(colored(result["description"], "white")) 