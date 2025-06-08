#!/usr/bin/env python3
"""
Test script for the optimized RAG system
Tests embedding dimensions, chunking optimization, and search capabilities
"""

import os
from termcolor import colored
from embedding import generate_embedding, count_tokens, is_content_meaningful, merge_small_chunks
from query_documents import vector_search, text_search, hybrid_search

def test_embedding_dimensions():
    """Test that embeddings have correct dimensions (1536 for text-embedding-3-small)"""
    print(colored("\n=== Testing Embedding Dimensions ===", "blue"))
    
    test_text = "This is a test sentence for embedding generation."
    embedding = generate_embedding(test_text)
    
    print(colored(f"Test text: {test_text}", "white"))
    print(colored(f"Embedding dimensions: {len(embedding)}", "green"))
    
    if len(embedding) == 1536:
        print(colored("✓ Embedding dimensions are correct (1536)", "green"))
        return True
    else:
        print(colored(f"✗ Expected 1536 dimensions, got {len(embedding)}", "red"))
        return False

def test_content_filtering():
    """Test content meaningfulness filtering"""
    print(colored("\n=== Testing Content Filtering ===", "blue"))
    
    test_cases = [
        ("This is a meaningful sentence with actual content.", True),
        ("^", False),
        ("CHAPTER ONE", False),
        ("Table of Contents\nChapter 1\nChapter 2", False),
        ("This is a real paragraph with meaningful content that should be included in our RAG system.", True),
        ("\t\t\n\n", False),
    ]
    
    all_passed = True
    for text, expected in test_cases:
        result = is_content_meaningful(text)
        status = "✓" if result == expected else "✗"
        color = "green" if result == expected else "red"
        print(colored(f"{status} '{text[:30]}...' -> {result} (expected {expected})", color))
        if result != expected:
            all_passed = False
    
    return all_passed

def test_token_counting():
    """Test token counting functionality"""
    print(colored("\n=== Testing Token Counting ===", "blue"))
    
    test_texts = [
        "Short text.",
        "This is a medium-length text that should have a reasonable token count.",
        "This is a much longer text that contains multiple sentences and should demonstrate how the token counting works with longer content. It includes various words and punctuation marks to simulate real document content."
    ]
    
    for text in test_texts:
        token_count = count_tokens(text)
        print(colored(f"Text: '{text[:50]}...'", "white"))
        print(colored(f"Token count: {token_count}", "green"))
        print()

def test_search_with_lower_threshold():
    """Test search functionality with lowered thresholds"""
    print(colored("\n=== Testing Search with Lower Thresholds ===", "blue"))
    
    test_queries = [
        "mindfulness meditation",
        "present moment awareness",
        "ego consciousness"
    ]
    
    for query in test_queries:
        print(colored(f"\nTesting query: '{query}'", "cyan"))
        
        try:
            # Test vector search with lower threshold
            vector_results = vector_search(query, limit=3, similarity_threshold=0.3)
            print(colored(f"Vector search found {len(vector_results)} results", "green"))
            
            # Test hybrid search
            hybrid_results = hybrid_search(query, limit=3, similarity_threshold=0.3)
            print(colored(f"Hybrid search found {len(hybrid_results)} results", "green"))
            
        except Exception as e:
            print(colored(f"Search test failed: {e}", "red"))
            return False
    
    return True

def test_chunk_merging():
    """Test the chunk merging functionality"""
    print(colored("\n=== Testing Chunk Merging ===", "blue"))
    
    # Create mock chunks
    class MockChunk:
        def __init__(self, text):
            self.text = text
    
    # Test chunks with various sizes
    test_chunks = [
        MockChunk("^"),  # Very small, should be filtered
        MockChunk("Short."),  # Small, should be merged
        MockChunk("Another short chunk."),  # Small, should be merged
        MockChunk("This is a medium-sized chunk that contains enough content to be meaningful and should probably be kept as-is since it has a good amount of content for semantic understanding."),  # Good size
        MockChunk("Small again."),  # Small, should be merged
        MockChunk("And another."),  # Small, should be merged
    ]
    
    print(colored(f"Input chunks: {len(test_chunks)}", "white"))
    for i, chunk in enumerate(test_chunks):
        token_count = count_tokens(chunk.text)
        print(colored(f"  Chunk {i+1}: {token_count} tokens - '{chunk.text[:30]}...'", "white"))
    
    # Test merging
    optimized_chunks = merge_small_chunks(test_chunks)
    
    print(colored(f"\nOptimized chunks: {len(optimized_chunks)}", "green"))
    for i, chunk in enumerate(optimized_chunks):
        token_count = count_tokens(chunk.text)
        print(colored(f"  Optimized {i+1}: {token_count} tokens - '{chunk.text[:50]}...'", "green"))
    
    return len(optimized_chunks) < len(test_chunks)  # Should have fewer chunks after optimization

def main():
    """Run all tests"""
    print(colored("🚀 Starting Optimized RAG System Tests", "blue", attrs=["bold"]))
    
    tests = [
        ("Embedding Dimensions", test_embedding_dimensions),
        ("Content Filtering", test_content_filtering),
        ("Token Counting", test_token_counting),
        ("Chunk Merging", test_chunk_merging),
        ("Search with Lower Thresholds", test_search_with_lower_threshold),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(colored(f"\n{'='*60}", "blue"))
            result = test_func()
            results.append((test_name, result))
            status = "PASSED" if result else "FAILED"
            color = "green" if result else "red"
            print(colored(f"\n{test_name}: {status}", color, attrs=["bold"]))
        except Exception as e:
            print(colored(f"\n{test_name}: ERROR - {e}", "red", attrs=["bold"]))
            results.append((test_name, False))
    
    # Summary
    print(colored(f"\n{'='*60}", "blue"))
    print(colored("TEST SUMMARY", "blue", attrs=["bold"]))
    print(colored("="*60, "blue"))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        color = "green" if result else "red"
        print(colored(f"{status:<12} {test_name}", color))
    
    print(colored(f"\nOverall: {passed}/{total} tests passed", "cyan", attrs=["bold"]))
    
    if passed == total:
        print(colored("🎉 All tests passed! RAG system is optimized and ready.", "green", attrs=["bold"]))
    else:
        print(colored("⚠️  Some tests failed. Please review the optimizations.", "yellow", attrs=["bold"]))

if __name__ == "__main__":
    main() 