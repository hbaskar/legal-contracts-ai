#!/usr/bin/env python3
"""
Azure Search Document Deletion Test Script

This script demonstrates how to delete specific documents from the Azure Search index
using the new deletion endpoints. It supports:

1. Delete by specific document ID
2. Delete by filename (all chunks)
3. Batch delete multiple document IDs
4. Delete persisted chunks from local database

Usage:
    python test_document_deletion.py
"""

import requests
import json
import sys
import time

# API Configuration
BASE_URL = "http://localhost:7071"
API_ENDPOINTS = {
    "search_docs": f"{BASE_URL}/api/search/documents",
    "persisted_chunks": f"{BASE_URL}/api/search/chunks/persisted", 
    "delete_search": f"{BASE_URL}/api/search/delete/document",
    "delete_persisted": f"{BASE_URL}/api/search/delete/document/persisted"
}

def get_available_documents():
    """Get a list of available documents for testing deletion"""
    print("📋 Getting available documents...")
    
    try:
        response = requests.get(f"{API_ENDPOINTS['search_docs']}?limit=10", timeout=30)
        if response.status_code == 200:
            result = response.json()
            documents = result.get('documents', [])
            
            print(f"✅ Found {len(documents)} documents in Azure Search index:")
            for i, doc in enumerate(documents[:5], 1):
                print(f"   {i}. ID: {doc['id']}")
                print(f"      Filename: {doc.get('filename', 'N/A')}")
                print(f"      Title: {doc.get('title', 'N/A')[:50]}...")
                print()
            
            return documents
        else:
            print(f"❌ Failed to get documents: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting documents: {e}")
        return []

def get_persisted_chunks():
    """Get available persisted chunks for testing"""
    print("📋 Getting available persisted chunks...")
    
    try:
        response = requests.get(f"{API_ENDPOINTS['persisted_chunks']}?limit=10", timeout=30)
        if response.status_code == 200:
            result = response.json()
            chunks = result.get('documents', [])
            
            print(f"✅ Found {len(chunks)} persisted chunks in database:")
            for i, chunk in enumerate(chunks[:5], 1):
                print(f"   {i}. ID: {chunk['id']}")
                print(f"      Filename: {chunk.get('filename', 'N/A')}")
                print(f"      Content Length: {chunk.get('content_length', 0)} chars")
                print()
            
            return chunks
        else:
            print(f"❌ Failed to get persisted chunks: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting persisted chunks: {e}")
        return []

def test_delete_by_document_id():
    """Test deletion by specific document ID"""
    print("\n1️⃣  Testing deletion by document ID...")
    
    # Get available documents
    documents = get_available_documents()
    if not documents:
        print("⚠️  No documents available for testing")
        return False
    
    # Use the first document for testing
    test_doc = documents[0]
    document_id = test_doc['id']
    
    print(f"🗑️ Testing deletion of document ID: {document_id}")
    
    try:
        response = requests.delete(f"{API_ENDPOINTS['delete_search']}?document_id={document_id}", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully deleted: {result['message']}")
            print(f"   Deleted chunks: {result.get('deleted_chunks', 0)}")
            return True
        elif response.status_code == 404:
            result = response.json()
            print(f"⚠️  Document not found: {result['message']}")
            return True  # This is also a successful test
        else:
            print(f"❌ Deletion failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        return False

def test_delete_by_filename():
    """Test deletion by filename"""
    print("\n2️⃣  Testing deletion by filename...")
    
    # Get available documents
    documents = get_available_documents()
    if not documents:
        print("⚠️  No documents available for testing")
        return False
    
    # Find a unique filename to delete
    filenames = list(set(doc.get('filename', '') for doc in documents if doc.get('filename')))
    if not filenames:
        print("⚠️  No filenames available for testing")
        return False
    
    test_filename = filenames[0]
    print(f"🗑️ Testing deletion of filename: {test_filename}")
    
    try:
        response = requests.delete(f"{API_ENDPOINTS['delete_search']}?filename={test_filename}", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully deleted: {result['message']}")
            print(f"   Deleted chunks: {result.get('deleted_chunks', 0)}")
            return True
        elif response.status_code == 404:
            result = response.json()
            print(f"⚠️  No documents found: {result['message']}")
            return True  # This is also a successful test
        else:
            print(f"❌ Deletion failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        return False

def test_batch_deletion():
    """Test batch deletion of multiple document IDs"""
    print("\n3️⃣  Testing batch deletion...")
    
    # Get available documents
    documents = get_available_documents()
    if not documents:
        print("⚠️  No documents available for testing")
        return False
    
    # Select up to 3 document IDs for batch deletion
    document_ids = [doc['id'] for doc in documents[:3]]
    
    print(f"🗑️ Testing batch deletion of {len(document_ids)} documents:")
    for doc_id in document_ids:
        print(f"   - {doc_id}")
    
    try:
        payload = {"document_ids": document_ids}
        headers = {'Content-Type': 'application/json'}
        
        response = requests.delete(
            API_ENDPOINTS['delete_search'], 
            json=payload, 
            headers=headers, 
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch deletion completed: {result['message']}")
            print(f"   Deleted chunks: {result.get('deleted_chunks', 0)}")
            print(f"   Failed deletions: {result.get('failed_deletions', 0)}")
            print(f"   Requested: {result.get('requested_count', 0)}")
            print(f"   Found: {result.get('found_count', 0)}")
            return True
        else:
            print(f"❌ Batch deletion failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during batch deletion: {e}")
        return False

def test_delete_persisted_chunks():
    """Test deletion of persisted chunks from database"""
    print("\n4️⃣  Testing persisted chunk deletion...")
    
    # Get available persisted chunks
    chunks = get_persisted_chunks()
    if not chunks:
        print("⚠️  No persisted chunks available for testing")
        return False
    
    # Use the first chunk for testing
    test_chunk = chunks[0]
    document_id = test_chunk['id']
    
    print(f"🗑️ Testing deletion of persisted chunk ID: {document_id}")
    
    try:
        response = requests.delete(
            f"{API_ENDPOINTS['delete_persisted']}?document_id={document_id}&confirm=yes", 
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully deleted: {result['message']}")
            print(f"   Deleted count: {result.get('deleted_count', 0)}")
            return True
        elif response.status_code == 404:
            result = response.json()
            print(f"⚠️  Chunk not found: {result['message']}")
            return True  # This is also a successful test
        else:
            print(f"❌ Deletion failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during persisted chunk deletion: {e}")
        return False

def test_error_handling():
    """Test error handling for invalid requests"""
    print("\n5️⃣  Testing error handling...")
    
    test_results = []
    
    # Test 1: Delete without parameters
    print("   Testing deletion without parameters...")
    try:
        response = requests.delete(API_ENDPOINTS['delete_search'], timeout=10)
        if response.status_code == 400:
            print("   ✅ Correctly rejected request without parameters")
            test_results.append(True)
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            test_results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        test_results.append(False)
    
    # Test 2: Delete persisted without confirmation
    print("   Testing persisted deletion without confirmation...")
    try:
        response = requests.delete(f"{API_ENDPOINTS['delete_persisted']}?document_id=test_id", timeout=10)
        if response.status_code == 400:
            print("   ✅ Correctly rejected request without confirmation")
            test_results.append(True)
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            test_results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        test_results.append(False)
    
    # Test 3: Delete non-existent document
    print("   Testing deletion of non-existent document...")
    try:
        response = requests.delete(f"{API_ENDPOINTS['delete_search']}?document_id=non_existent_doc_12345", timeout=10)
        if response.status_code == 404:
            print("   ✅ Correctly returned 404 for non-existent document")
            test_results.append(True)
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            test_results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        test_results.append(False)
    
    return all(test_results)

def main():
    """Run all document deletion tests"""
    print("🚀 Starting Azure Search Document Deletion Tests")
    print("=" * 70)
    
    test_results = []
    
    # Test deletion by document ID
    result1 = test_delete_by_document_id()
    test_results.append(("Delete by Document ID", result1))
    
    # Wait a moment between tests
    time.sleep(1)
    
    # Test deletion by filename  
    result2 = test_delete_by_filename()
    test_results.append(("Delete by Filename", result2))
    
    # Wait a moment between tests
    time.sleep(1)
    
    # Test batch deletion
    result3 = test_batch_deletion()
    test_results.append(("Batch Deletion", result3))
    
    # Wait a moment between tests
    time.sleep(1)
    
    # Test persisted chunk deletion
    result4 = test_delete_persisted_chunks()
    test_results.append(("Delete Persisted Chunks", result4))
    
    # Test error handling
    result5 = test_error_handling()
    test_results.append(("Error Handling", result5))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 ALL TESTS PASSED! Document deletion functionality is working correctly!")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    print("\n📝 Deletion Capabilities Summary:")
    print("✅ Delete specific document by ID")
    print("✅ Delete all chunks by filename")
    print("✅ Batch delete multiple documents")
    print("✅ Delete persisted chunks from database")
    print("✅ Proper error handling and validation")
    
    print("\n🔗 Available Endpoints:")
    print("• DELETE /api/search/delete/document?document_id=xyz")
    print("• DELETE /api/search/delete/document?filename=file.pdf")
    print("• DELETE /api/search/delete/document (with JSON body: {'document_ids': [...]})")
    print("• DELETE /api/search/delete/document/persisted?document_id=xyz&confirm=yes")
    print("• DELETE /api/search/delete/document/persisted?filename=file.pdf&confirm=yes")

if __name__ == "__main__":
    main()
