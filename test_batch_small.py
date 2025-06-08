#!/usr/bin/env python3
"""
Small test script to process just a few books to verify batch processing works
"""

import os
import subprocess
import time
from datetime import datetime
from termcolor import colored

def test_process_few_books():
    """Test processing just a few small books"""
    
    # Select a few smaller books for testing
    test_books = [
        "books/eating-disorders.pdf",  # 0.17 MB
        "books/The_Power_Of_Now_Eckhart_Tolle.pdf",  # 0.17 MB
        "books/autism-spectrum-disorder.pdf",  # 0.33 MB
    ]
    
    print(colored("Testing batch processing with 3 small books...", "cyan"))
    
    results = []
    
    for i, book_path in enumerate(test_books, 1):
        if not os.path.exists(book_path):
            print(colored(f"File not found: {book_path}", "red"))
            continue
            
        file_name = os.path.basename(book_path)
        file_size_mb = round(os.path.getsize(book_path) / (1024 * 1024), 2)
        
        print(colored(f"\n[{i}/3] Processing: {file_name} ({file_size_mb} MB)", "cyan"))
        
        start_time = time.time()
        
        try:
            # Run the main.py process command
            cmd = ["python", "main.py", "process", book_path]
            print(colored(f"Running: {' '.join(cmd)}", "yellow"))
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for test
            )
            
            end_time = time.time()
            processing_time_minutes = round((end_time - start_time) / 60, 2)
            
            result = {
                "file_name": file_name,
                "file_size_mb": file_size_mb,
                "processing_time_minutes": processing_time_minutes,
                "status": "success" if process.returncode == 0 else "failed",
                "error": process.stderr.strip() if process.stderr else None
            }
            
            if process.returncode == 0:
                print(colored(f"✓ Success in {processing_time_minutes:.2f} minutes", "green"))
                
                # Extract some info from output
                output_lines = process.stdout.split('\n')
                for line in output_lines:
                    if "Document ID:" in line:
                        result["document_id"] = line.split("Document ID:")[-1].strip()
                        print(colored(f"  Document ID: {result['document_id']}", "white"))
                    elif "Optimized Chunks:" in line:
                        chunks = line.split("Optimized Chunks:")[-1].strip()
                        result["chunks"] = chunks
                        print(colored(f"  Chunks: {chunks}", "white"))
            else:
                print(colored(f"✗ Failed in {processing_time_minutes:.2f} minutes", "red"))
                if result["error"]:
                    print(colored(f"  Error: {result['error']}", "red"))
            
            results.append(result)
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            processing_time_minutes = round((end_time - start_time) / 60, 2)
            print(colored(f"✗ Timeout after {processing_time_minutes:.2f} minutes", "red"))
            
            results.append({
                "file_name": file_name,
                "file_size_mb": file_size_mb,
                "processing_time_minutes": processing_time_minutes,
                "status": "timeout",
                "error": "Processing timeout"
            })
        
        except Exception as e:
            end_time = time.time()
            processing_time_minutes = round((end_time - start_time) / 60, 2)
            print(colored(f"✗ Error after {processing_time_minutes:.2f} minutes: {e}", "red"))
            
            results.append({
                "file_name": file_name,
                "file_size_mb": file_size_mb,
                "processing_time_minutes": processing_time_minutes,
                "status": "error",
                "error": str(e)
            })
    
    # Print summary
    print(colored("\n" + "="*60, "cyan"))
    print(colored("TEST SUMMARY", "cyan"))
    print(colored("="*60, "cyan"))
    
    successful = sum(1 for r in results if r["status"] == "success")
    total_time = sum(r["processing_time_minutes"] for r in results)
    
    print(colored(f"Files processed: {len(results)}", "white"))
    print(colored(f"Successful: {successful}", "green"))
    print(colored(f"Failed: {len(results) - successful}", "red"))
    print(colored(f"Total time: {total_time:.2f} minutes", "white"))
    print(colored(f"Average time: {total_time/len(results):.2f} minutes per file", "white"))
    
    for result in results:
        status_color = "green" if result["status"] == "success" else "red"
        print(colored(f"  {result['file_name']}: {result['status']} ({result['processing_time_minutes']:.2f} min)", status_color))
    
    return results

if __name__ == "__main__":
    test_process_few_books() 