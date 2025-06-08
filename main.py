#!/usr/bin/env python3
"""
RAG with Docling - Main Entry Point

A unified command-line interface for the RAG system providing:
- Document processing and embedding
- Document querying with multiple search modes
- Book metadata extraction

Usage:
    python main.py process <pdf_path>           # Process and embed a document
    python main.py query                        # Interactive query interface
    python main.py extract <pdf_path>           # Extract metadata from a document
    python main.py list                         # List all documents in database
"""

import os
import sys
import argparse
from termcolor import colored

def main():
    """Main entry point with command-line interface"""
    
    parser = argparse.ArgumentParser(
        description="RAG with Docling - Document Processing and Query System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py process document.pdf     # Process and embed document
  python main.py query                    # Start interactive query session
  python main.py extract document.pdf     # Extract metadata only
  python main.py list                     # List all documents
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process and embed a PDF document')
    process_parser.add_argument('pdf_path', help='Path to the PDF file to process')
    process_parser.add_argument('--no-metadata', action='store_true', 
                               help='Skip metadata extraction (faster processing)')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Start interactive query interface')
    query_parser.add_argument('--mode', choices=['vector', 'text', 'hybrid'], 
                             help='Default search mode (can be changed interactively)')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract metadata from a PDF document')
    extract_parser.add_argument('pdf_path', help='Path to the PDF file')
    extract_parser.add_argument('--document-id', type=int, 
                               help='Document ID to update in database')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all documents in the database')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Import modules only when needed to improve startup time
    try:
        if args.command == 'process':
            from embedding import main as process_document
            
            print(colored(f"Processing document: {args.pdf_path}", "cyan"))
            
            if not os.path.exists(args.pdf_path):
                print(colored(f"Error: File not found: {args.pdf_path}", "red"))
                sys.exit(1)
            
            # Process the document with the specified PDF path
            process_document(args.pdf_path, args.no_metadata)
            
        elif args.command == 'query':
            from query_documents import main as query_interface
            
            print(colored("Starting interactive query interface...", "cyan"))
            query_interface()
            
        elif args.command == 'extract':
            from book_metadata_extractor import process_book_metadata
            
            print(colored(f"Extracting metadata from: {args.pdf_path}", "cyan"))
            
            if not os.path.exists(args.pdf_path):
                print(colored(f"Error: File not found: {args.pdf_path}", "red"))
                sys.exit(1)
            
            result = process_book_metadata(args.pdf_path, args.document_id)
            
            # Display results
            print(colored("\n" + "="*50, "cyan"))
            print(colored("EXTRACTION RESULTS:", "cyan"))
            print(colored("="*50, "cyan"))
            
            metadata = result["metadata"]
            print(colored(f"Title: {metadata.get('title', 'Not found')}", "white"))
            print(colored(f"Authors: {metadata.get('authors', 'Not found')}", "white"))
            print(colored(f"Published Year: {metadata.get('published_year', 'Not found')}", "white"))
            
            if result["description"]:
                print(colored(f"\nDescription:", "yellow"))
                print(colored(result["description"], "white"))
            
        elif args.command == 'list':
            from query_documents import list_documents
            
            print(colored("Listing all documents in database...", "cyan"))
            documents = list_documents()
            
            if documents:
                print(colored(f"\nTotal documents: {len(documents)}", "green"))
            else:
                print(colored("No documents found in database", "yellow"))
                
    except ImportError as e:
        print(colored(f"Error importing required modules: {e}", "red"))
        print(colored("Make sure all dependencies are installed: pip install -r requirements.txt", "yellow"))
        sys.exit(1)
    except Exception as e:
        print(colored(f"Error executing command: {e}", "red"))
        sys.exit(1)

if __name__ == "__main__":
    main() 