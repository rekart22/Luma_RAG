#!/usr/bin/env python3
"""
Batch Processing Script for RAG System
Processes all PDF files in the books directory with detailed logging
"""

import os
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from termcolor import colored
import dotenv
import re
from supabase import create_client

# Load environment variables
dotenv.load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Configuration
BOOKS_DIR = "books"
LOG_DIR = "logs"
BATCH_LOG_FILE = "batch_processing_log.txt"
DETAILED_LOG_FILE = "detailed_processing_log.json"

def ensure_log_directory():
    """Create logs directory if it doesn't exist"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        print(colored(f"Created logs directory: {LOG_DIR}", "green"))

def get_supabase_client():
    """Get Supabase client"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print(colored("Warning: Supabase credentials not found in .env file", "yellow"))
        return None
    
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        print(colored(f"Error connecting to Supabase: {e}", "red"))
        return None

def get_pdf_files() -> List[str]:
    """Get all PDF files from the books directory"""
    books_path = Path(BOOKS_DIR)
    if not books_path.exists():
        print(colored(f"Books directory '{BOOKS_DIR}' not found!", "red"))
        return []
    
    pdf_files = []
    for file_path in books_path.glob("*.pdf"):
        pdf_files.append(str(file_path))
    
    return sorted(pdf_files)

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except OSError:
        return 0.0

def test_read_all_pdfs() -> Dict[str, Any]:
    """Test reading all PDF files and collect basic information"""
    print(colored("\n" + "="*80, "cyan"))
    print(colored("TESTING: Reading all PDF files in books directory", "cyan"))
    print(colored("="*80, "cyan"))
    
    pdf_files = get_pdf_files()
    
    if not pdf_files:
        print(colored("No PDF files found in books directory!", "red"))
        return {"success": False, "files": []}
    
    results = {
        "success": True,
        "total_files": len(pdf_files),
        "files": [],
        "total_size_mb": 0.0,
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(colored(f"Found {len(pdf_files)} PDF files:", "green"))
    
    for i, file_path in enumerate(pdf_files, 1):
        file_name = os.path.basename(file_path)
        file_size_mb = get_file_size_mb(file_path)
        
        file_info = {
            "index": i,
            "file_name": file_name,
            "file_path": file_path,
            "file_size_mb": file_size_mb,
            "readable": True,
            "error": None
        }
        
        try:
            # Test if file is readable
            with open(file_path, 'rb') as f:
                # Read first few bytes to test accessibility
                f.read(1024)
            
            print(colored(f"  {i:3d}. {file_name:<60} ({file_size_mb:>8.2f} MB) ✓", "white"))
            
        except Exception as e:
            file_info["readable"] = False
            file_info["error"] = str(e)
            print(colored(f"  {i:3d}. {file_name:<60} ({file_size_mb:>8.2f} MB) ✗ Error: {e}", "red"))
        
        results["files"].append(file_info)
        results["total_size_mb"] += file_size_mb
    
    print(colored(f"\nSummary:", "cyan"))
    print(colored(f"  Total files: {results['total_files']}", "white"))
    print(colored(f"  Total size: {results['total_size_mb']:.2f} MB", "white"))
    readable_count = sum(1 for f in results["files"] if f["readable"])
    print(colored(f"  Readable files: {readable_count}/{results['total_files']}", "green"))
    
    return results

def log_to_supabase(result: Dict[str, Any]) -> bool:
    """Log processing result to Supabase documents_import_logs table"""
    supabase = get_supabase_client()
    if not supabase:
        print(colored("Skipping Supabase logging: No connection available", "yellow"))
        return False
    
    try:
        # Prepare log data
        log_data = {
            "file_name": result["file_name"],
            "file_path": result["file_path"],
            "file_size_mb": result["file_size_mb"],
            "status": result["status"],
            "document_id": result["document_id"],
            "error": result["error"],
            "start_time": result["start_time"],
            "processing_time_minutes": result["processing_time_minutes"],
            "chunks_total": result["chunks"].get("total_count"),
            "chunks_avg_size": result["chunks"].get("avg_chunk_size"),
            "chunks_min_size": result["chunks"].get("min_size"),
            "chunks_max_size": result["chunks"].get("max_size")
        }
        
        # Insert log into Supabase
        response = supabase.table("documents_import_logs").insert(log_data).execute()
        
        if hasattr(response, 'error') and response.error:
            print(colored(f"Error logging to Supabase: {response.error}", "red"))
            return False
            
        print(colored("✓ Logged processing result to Supabase", "green"))
        return True
        
    except Exception as e:
        print(colored(f"Error logging to Supabase: {e}", "red"))
        return False

def process_single_book(file_path: str, index: int, total: int) -> Dict[str, Any]:
    """Process a single book using main.py process command"""
    file_name = os.path.basename(file_path)
    file_size_mb = get_file_size_mb(file_path)
    
    print(colored(f"\n[{index}/{total}] Processing: {file_name}", "cyan"))
    print(colored(f"File size: {file_size_mb:.2f} MB", "white"))
    
    start_time = time.time()
    start_datetime = datetime.now()
    
    result = {
        "file_name": file_name,
        "file_path": file_path,
        "file_size_mb": file_size_mb,
        "start_time": start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "failed",
        "error": None,
        "document_id": None,
        "metadata": None,
        "chunks": {
            "total_count": 0,
            "small_chunks_count": 0,
            "optimal_chunks_count": 0,
            "large_chunks_count": 0,
            "avg_chunk_size": 0,
            "min_size": 0,
            "max_size": 0
        },
        "processing_time_minutes": 0.0
    }
    
    try:
        # Run the main.py process command
        cmd = ["python", "main.py", "process", file_path]
        print(colored(f"Running: {' '.join(cmd)}", "yellow"))
        
        # Remove timeout and add real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Store output lines for later analysis
        output_lines = []

        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            output_lines.append(line)
            print(colored(line, "white"))

        process.stdout.close()
        process.wait()

        end_time = time.time()
        processing_time_minutes = round((end_time - start_time) / 60, 2)
        result["processing_time_minutes"] = processing_time_minutes
        
        if process.returncode == 0:
            result["status"] = "success"
            print(colored(f"✓ Successfully processed in {processing_time_minutes:.2f} minutes", "green"))
            
            # Process collected output for logging
            output_text = '\n'.join(output_lines)
            
            # Try to extract information from the output
            for line in output_lines:
                if "Document ID:" in line:
                    document_id_match = re.search(r"Document ID:\s*(\d+)", line)
                    if document_id_match:
                        result["document_id"] = int(document_id_match.group(1))
                elif "Initial Chunks:" in line:
                    try:
                        chunks_match = re.search(r"Initial Chunks:\s*(\d+)", line)
                        if chunks_match:
                            result["chunks"]["total_count"] = int(chunks_match.group(1))
                    except:
                        pass
                elif "Optimized Chunks:" in line:
                    try:
                        optimized_match = re.search(r"Optimized Chunks:\s*(\d+)", line)
                        if optimized_match:
                            result["chunks"]["optimized_count"] = int(optimized_match.group(1))
                    except:
                        pass
                elif "Chunk size stats:" in line:
                    # Parse chunk statistics
                    try:
                        stats_part = line.split("Chunk size stats:")[-1].strip()
                        if "Min=" in stats_part and "Max=" in stats_part and "Avg=" in stats_part:
                            # Extract Min, Max, Avg values
                            min_match = re.search(r"Min=(\d+)", stats_part)
                            max_match = re.search(r"Max=(\d+)", stats_part)
                            avg_match = re.search(r"Avg=(\d+)", stats_part)
                            
                            if min_match:
                                result["chunks"]["min_size"] = int(min_match.group(1))
                            if max_match:
                                result["chunks"]["max_size"] = int(max_match.group(1))
                            if avg_match:
                                result["chunks"]["avg_chunk_size"] = int(avg_match.group(1))
                    except:
                        pass
            
        else:
            result["status"] = "failed"
            stderr_output = process.stderr.read().strip() if process.stderr else "Unknown error"
            result["error"] = stderr_output
            print(colored(f"✗ Failed after {processing_time_minutes:.2f} minutes", "red"))
            print(colored(f"Error: {result['error']}", "red"))
    
    except Exception as e:
        end_time = time.time()
        processing_time_minutes = round((end_time - start_time) / 60, 2)
        result["processing_time_minutes"] = processing_time_minutes
        result["status"] = "error"
        result["error"] = str(e)
        print(colored(f"✗ Error after {processing_time_minutes:.2f} minutes: {e}", "red"))
    
    # Log to Supabase
    log_to_supabase(result)
    
    return result

def save_detailed_log(results: List[Dict[str, Any]]):
    """Save detailed processing results to JSON file"""
    ensure_log_directory()
    
    log_data = {
        "batch_processing_session": {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(results),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "timeout": sum(1 for r in results if r["status"] == "timeout"),
            "errors": sum(1 for r in results if r["status"] == "error"),
            "total_processing_time_minutes": sum(r["processing_time_minutes"] for r in results),
            "results": results
        }
    }
    
    detailed_log_path = os.path.join(LOG_DIR, DETAILED_LOG_FILE)
    with open(detailed_log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    print(colored(f"Detailed log saved to: {detailed_log_path}", "green"))

def save_summary_log(results: List[Dict[str, Any]]):
    """Save summary log to text file"""
    ensure_log_directory()
    
    summary_log_path = os.path.join(LOG_DIR, BATCH_LOG_FILE)
    
    with open(summary_log_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("BATCH PROCESSING SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Files: {len(results)}\n")
        
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        timeout = sum(1 for r in results if r["status"] == "timeout")
        errors = sum(1 for r in results if r["status"] == "error")
        
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Timeout: {timeout}\n")
        f.write(f"Errors: {errors}\n")
        
        total_time = sum(r["processing_time_minutes"] for r in results)
        f.write(f"Total Processing Time: {total_time:.2f} minutes\n")
        f.write(f"Average Time per File: {total_time/len(results):.2f} minutes\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("="*80 + "\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"\n{i:3d}. {result['file_name']}\n")
            f.write(f"     Status: {result['status'].upper()}\n")
            f.write(f"     Size: {result['file_size_mb']:.2f} MB\n")
            f.write(f"     Processing Time: {result['processing_time_minutes']:.2f} minutes\n")
            
            if result['status'] == 'success':
                if 'chunks' in result and result['chunks'].get('total_count', 0) > 0:
                    f.write(f"     Chunks: {result['chunks'].get('total_count', 'N/A')}\n")
                    f.write(f"     Avg Chunk Size: {result['chunks'].get('avg_chunk_size', 'N/A')} tokens\n")
            
            if result['error']:
                f.write(f"     Error: {result['error']}\n")
    
    print(colored(f"Summary log saved to: {summary_log_path}", "green"))

def batch_process_books(test_only: bool = False) -> List[Dict[str, Any]]:
    """Main batch processing function"""
    print(colored("\n" + "="*80, "cyan"))
    print(colored("BATCH PROCESSING: RAG System Book Processing", "cyan"))
    print(colored("="*80, "cyan"))
    
    # Check Supabase connection
    supabase = get_supabase_client()
    if supabase:
        print(colored("✓ Connected to Supabase database", "green"))
    else:
        print(colored("✗ Could not connect to Supabase - check .env file for SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY", "yellow"))
    
    # First test reading all files
    test_results = test_read_all_pdfs()
    
    if not test_results["success"]:
        print(colored("Test failed! Cannot proceed with batch processing.", "red"))
        return []
    
    if test_only:
        print(colored("\nTest completed successfully! All files are readable.", "green"))
        return []
    
    # Get readable files only
    readable_files = [f["file_path"] for f in test_results["files"] if f["readable"]]
    
    if not readable_files:
        print(colored("No readable files found!", "red"))
        return []
    
    print(colored(f"\nStarting batch processing of {len(readable_files)} files...", "cyan"))
    
    results = []
    total_start_time = time.time()
    
    for i, file_path in enumerate(readable_files, 1):
        result = process_single_book(file_path, i, len(readable_files))
        results.append(result)
        
        # Print progress
        successful = sum(1 for r in results if r["status"] == "success")
        print(colored(f"Progress: {i}/{len(readable_files)} files processed, {successful} successful", "cyan"))
    
    total_end_time = time.time()
    total_time_minutes = round((total_end_time - total_start_time) / 60, 2)
    
    # Print final summary
    print(colored("\n" + "="*80, "cyan"))
    print(colored("BATCH PROCESSING COMPLETED", "cyan"))
    print(colored("="*80, "cyan"))
    
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    timeout = sum(1 for r in results if r["status"] == "timeout")
    errors = sum(1 for r in results if r["status"] == "error")
    
    print(colored(f"Total Files Processed: {len(results)}", "white"))
    print(colored(f"Successful: {successful}", "green"))
    print(colored(f"Failed: {failed}", "red"))
    print(colored(f"Timeout: {timeout}", "yellow"))
    print(colored(f"Errors: {errors}", "red"))
    print(colored(f"Total Processing Time: {total_time_minutes:.2f} minutes", "white"))
    print(colored(f"Average Time per File: {total_time_minutes/len(results):.2f} minutes", "white"))
    
    # Save logs
    save_detailed_log(results)
    save_summary_log(results)
    
    return results

def main():
    """Main function with command line options"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        print(colored("Running in TEST ONLY mode", "yellow"))
        batch_process_books(test_only=True)
    else:
        print(colored("Running FULL BATCH PROCESSING", "green"))
        print(colored("Use --test-only flag to only test file reading", "yellow"))
        
        # Ask for confirmation
        response = input(colored("\nProceed with full batch processing? (y/N): ", "yellow"))
        if response.lower() in ['y', 'yes']:
            batch_process_books(test_only=False)
        else:
            print(colored("Batch processing cancelled.", "yellow"))

if __name__ == "__main__":
    main() 