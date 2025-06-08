import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client
from termcolor import colored

load_dotenv()

# Configuration variables at the top
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"  # More cost-effective embedding model

# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for query text"""
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query
        )
        return response.data[0].embedding
    except Exception as e:
        print(colored(f"Error generating query embedding: {e}", "red"))
        raise

def vector_search(query: str, limit: int = 5, similarity_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Perform vector search using pgvector cosine similarity
    
    Args:
        query: The search query text
        limit: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0-1) - LOWERED for better recall
        
    Returns:
        List of matching document sections with metadata
    """
    
    print(colored(f"Vector searching for: '{query}' (threshold: {similarity_threshold})", "cyan"))
    
    # Generate embedding for the query
    query_embedding = generate_query_embedding(query)
    
    try:
        # Execute the vector search using the new function
        result = supabase.rpc(
            'match_document_sections_vectorsearch',
            {
                'query_embedding': query_embedding,
                'match_threshold': similarity_threshold,
                'match_count': limit
            }
        ).execute()
        
        if result.data:
            print(colored(f"Found {len(result.data)} matching sections", "green"))
            return result.data
        else:
            print(colored("No matching sections found", "yellow"))
            return []
            
    except Exception as e:
        print(colored(f"Error performing vector search: {e}", "red"))
        raise

def text_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Perform full-text search using PostgreSQL text search
    
    Args:
        query: The search query text
        limit: Maximum number of results to return
        
    Returns:
        List of matching document sections with metadata
    """
    
    print(colored(f"Text searching for: '{query}'", "cyan"))
    
    try:
        # Execute the text search using the new function
        result = supabase.rpc(
            'match_document_sections_textsearch',
            {
                'query_text': query,
                'match_count': limit
            }
        ).execute()
        
        if result.data:
            print(colored(f"Found {len(result.data)} matching sections", "green"))
            return result.data
        else:
            print(colored("No matching sections found", "yellow"))
            return []
            
    except Exception as e:
        print(colored(f"Error performing text search: {e}", "red"))
        raise

def hybrid_search(query: str, limit: int = 5, similarity_threshold: float = 0.4, 
                 vector_weight: float = 0.7, text_weight: float = 0.3) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining vector and text search
    
    Args:
        query: The search query text
        limit: Maximum number of results to return
        similarity_threshold: Minimum similarity score for vector search (0-1) - LOWERED
        vector_weight: Weight for vector search results (0-1)
        text_weight: Weight for text search results (0-1)
        
    Returns:
        List of matching document sections with metadata
    """
    
    print(colored(f"Hybrid searching for: '{query}' (threshold: {similarity_threshold})", "cyan"))
    
    # Generate embedding for the query
    query_embedding = generate_query_embedding(query)
    
    try:
        # Execute the hybrid search using the new function
        result = supabase.rpc(
            'match_document_sections_hybridsearch',
            {
                'query_embedding': query_embedding,
                'query_text': query,
                'match_threshold': similarity_threshold,
                'match_count': limit,
                'vector_weight': vector_weight,
                'text_weight': text_weight
            }
        ).execute()
        
        if result.data:
            print(colored(f"Found {len(result.data)} matching sections", "green"))
            return result.data
        else:
            print(colored("No matching sections found", "yellow"))
            return []
            
    except Exception as e:
        print(colored(f"Error performing hybrid search: {e}", "red"))
        raise

# Keep semantic_search as an alias for backward compatibility - UPDATED THRESHOLD
def semantic_search(query: str, limit: int = 5, similarity_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """Alias for vector_search for backward compatibility"""
    return vector_search(query, limit, similarity_threshold)



def display_search_results(results: List[Dict[str, Any]], search_type: str = "vector"):
    """Display search results in a formatted way"""
    
    if not results:
        print(colored("No results to display", "yellow"))
        return
    
    print(colored("\n" + "="*80, "blue"))
    print(colored(f"SEARCH RESULTS ({search_type.upper()})", "blue", attrs=["bold"]))
    print(colored("="*80, "blue"))
    
    for i, result in enumerate(results, 1):
        # Display different score types based on search method
        if search_type == "vector":
            score_text = f"SIMILARITY: {result.get('similarity', 0):.3f}"
        elif search_type == "text":
            score_text = f"RANK: {result.get('rank', 0):.3f}"
        elif search_type == "hybrid":
            score_text = f"COMBINED: {result.get('combined_score', 0):.3f} (Vector: {result.get('vector_similarity', 0):.3f}, Text: {result.get('text_rank', 0):.3f})"
        else:
            score_text = f"SCORE: {result.get('similarity', result.get('rank', result.get('combined_score', 0))):.3f}"
            
        print(colored(f"\n[{i}] {score_text}", "green", attrs=["bold"]))
        print(colored(f"Document: {result['document_name']}", "cyan"))
        print(colored(f"Source: {result['document_source']}", "cyan"))
        print(colored(f"Type: {', '.join(result['document_type'])}", "cyan"))
        
        # Display new metadata fields if available
        if result.get('document_authors'):
            print(colored(f"Authors: {result['document_authors']}", "cyan"))
        if result.get('document_published_year'):
            print(colored(f"Published: {result['document_published_year']}", "cyan"))
        
        print(colored(f"Tokens: {result['token_count']}", "cyan"))
        print(colored("-" * 60, "white"))
        
        # Truncate content if too long
        content = result['content']
        if len(content) > 500:
            content = content[:500] + "..."
            
        print(colored(content, "white"))
        print(colored("-" * 80, "blue"))

def list_documents() -> List[Dict[str, Any]]:
    """List all documents in the database"""
    
    try:
        result = supabase.table("documents").select("*").execute()
        
        if result.data:
            print(colored(f"\nFound {len(result.data)} documents:", "green"))
            for doc in result.data:
                print(colored(f"- {doc['name']} ({doc['source']}) - {', '.join(doc['type'])}", "cyan"))
            return result.data
        else:
            print(colored("No documents found in database", "yellow"))
            return []
            
    except Exception as e:
        print(colored(f"Error listing documents: {e}", "red"))
        raise

def main():
    """Main function for interactive querying"""
    
    print(colored("Document Query System", "blue", attrs=["bold"]))
    print(colored("=" * 50, "blue"))
    
    # List available documents
    list_documents()
    
    while True:
        print(colored("\nOptions:", "cyan"))
        print(colored("1. Vector Search (semantic similarity)", "white"))
        print(colored("2. Text Search (full-text search)", "white"))
        print(colored("3. Hybrid Search (combined)", "white"))
        print(colored("4. List documents", "white"))
        print(colored("5. Exit", "white"))
        
        choice = input(colored("\nEnter your choice (1-5): ", "yellow")).strip()
        
        if choice in ["1", "2", "3"]:
            query = input(colored("Enter your search query: ", "yellow")).strip()
            if query:
                try:
                    if choice == "1":
                        results = vector_search(query)
                        display_search_results(results, "vector")
                    elif choice == "2":
                        results = text_search(query)
                        display_search_results(results, "text")
                    elif choice == "3":
                        results = hybrid_search(query)
                        display_search_results(results, "hybrid")
                except Exception as e:
                    print(colored(f"Search failed: {e}", "red"))
        
        elif choice == "4":
            list_documents()
        
        elif choice == "5":
            print(colored("Goodbye!", "green"))
            break
        
        else:
            print(colored("Invalid choice. Please try again.", "red"))

if __name__ == "__main__":
    main() 