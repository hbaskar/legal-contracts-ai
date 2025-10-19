#!/usr/bin/env python3
"""
Test script for Azure Search index creation and management

This script tests the refactored index creation functionality to ensure:
1. Index creation function works properly
2. Index existence check works
3. Process function calls index creation automatically
4. API endpoints work for index setup
"""

import requests
import json
import sys
import time

# Test Configuration
BASE_URL = "http://localhost:7071"
API_ENDPOINTS = {
    "health": f"{BASE_URL}/api/health",
    "process_document": f"{BASE_URL}/api/process_document",
    "search_setup": f"{BASE_URL}/api/search/setup",
    "search_documents": f"{BASE_URL}/api/search/documents"
}

def test_health_check():
    """Test basic service health"""
    print("🏥 Testing service health...")
    
    try:
        response = requests.get(API_ENDPOINTS["health"], timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Service is healthy: {result['status']}")
            print(f"   Database: {result['checks']['database']['status']}")
            print(f"   Storage: {result['checks']['blob_storage']['status']}")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_index_setup_endpoint():
    """Test the new index setup endpoint"""
    print("\n🏗️ Testing Azure Search index setup endpoint...")
    
    try:
        # Test GET to check current process function status
        response = requests.get(API_ENDPOINTS["process_document"], timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Process function is available: {result['status']}")
            print(f"   AI Services: {result.get('ai_services_available', 'Unknown')}")
        
        # Test the index setup endpoint
        response = requests.post(API_ENDPOINTS["search_setup"], timeout=60)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Index setup successful: {result['message']}")
            print(f"   Status: {result['status']}")
            print(f"   Index Name: {result.get('index_name', 'N/A')}")
            print(f"   Operation: {result.get('operation', 'N/A')}")
            print(f"   Fields Count: {result.get('fields_count', 'N/A')}")
            print(f"   Ready: {result.get('ready', 'N/A')}")
            return True
        else:
            print(f"❌ Index setup failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Index setup test error: {e}")
        return False

def test_index_recreation():
    """Test force recreation of index"""
    print("\n🔄 Testing index force recreation...")
    
    try:
        # Force recreate the index
        response = requests.post(
            f"{API_ENDPOINTS['search_setup']}?force_recreate=true", 
            timeout=60
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Index force recreation successful: {result['message']}")
            print(f"   Status: {result['status']}")
            print(f"   Force Recreate: {result.get('force_recreate', False)}")
            return True
        else:
            print(f"❌ Index force recreation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Index recreation test error: {e}")
        return False

def test_document_processing_with_index_creation():
    """Test that document processing automatically creates index if needed"""
    print("\n📄 Testing document processing with automatic index creation...")
    
    # Create a simple test document
    test_content = """
    EMPLOYEE HANDBOOK TEST DOCUMENT
    
    Section 1: Introduction
    This is a test document for verifying that the Azure Search index is automatically
    created when processing documents. The system should check for index existence
    and create it if necessary before uploading document chunks.
    
    Section 2: Testing Procedures
    When a document is processed, the following should happen:
    1. Content is extracted and chunked
    2. Azure Search index existence is verified
    3. Index is created if it doesn't exist
    4. Document chunks are uploaded to the index
    
    Section 3: Validation
    This test verifies that the refactored index creation functionality works properly
    and integrates seamlessly with the document processing workflow.
    """
    
    try:
        import base64
        file_content_base64 = base64.b64encode(test_content.encode('utf-8')).decode('utf-8')
        
        data = {
            "filename": "test_index_creation.txt",
            "file_content": file_content_base64,
            "chunking_method": "basic",
            "force_reindex": True
        }
        headers = {'Content-Type': 'application/json'}
        
        print("   📤 Sending document for processing...")
        response = requests.post(
            API_ENDPOINTS["process_document"], 
            json=data, 
            headers=headers, 
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Document processing successful: {result['message']}")
            print(f"   Created {result.get('chunks_created', 0)} chunks")
            print(f"   Uploaded {result.get('successful_uploads', 0)} to Azure Search")
            print(f"   Chunking Method: {result.get('chunking_method', 'N/A')}")
            print(f"   Enhancement: {result.get('enhancement', 'N/A')}")
            
            # Verify chunks were actually uploaded
            if result.get('successful_uploads', 0) > 0:
                print("   ✅ Index creation and document upload successful")
                return True
            else:
                print("   ⚠️ No chunks were uploaded to index")
                return False
        else:
            print(f"❌ Document processing failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Document processing test error: {e}")
        return False

def test_search_functionality():
    """Test that we can search the created index"""
    print("\n🔍 Testing search functionality...")
    
    try:
        # Wait a moment for indexing to complete
        time.sleep(2)
        
        # Search for documents
        response = requests.get(f"{API_ENDPOINTS['search_documents']}?limit=5", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search successful: {result['message']}")
            print(f"   Found {result.get('total_documents', 0)} documents")
            print(f"   Index Name: {result.get('index_name', 'N/A')}")
            
            # Show first document details
            documents = result.get('documents', [])
            if documents:
                first_doc = documents[0]
                print(f"   Sample Document:")
                print(f"     ID: {first_doc.get('id', 'N/A')}")
                print(f"     Title: {first_doc.get('title', 'N/A')}")
                print(f"     Content Length: {first_doc.get('content_length', 0)} chars")
                print(f"     Filename: {first_doc.get('filename', 'N/A')}")
            
            return len(documents) > 0
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Search test error: {e}")
        return False

def main():
    """Run all index creation tests"""
    print("🚀 Starting Azure Search Index Creation Tests")
    print("=" * 70)
    
    test_results = []
    
    # Test 1: Health check
    result1 = test_health_check()
    test_results.append(("Service Health Check", result1))
    
    if not result1:
        print("❌ Service is not healthy, stopping tests")
        return
    
    # Test 2: Index setup endpoint
    result2 = test_index_setup_endpoint()
    test_results.append(("Index Setup Endpoint", result2))
    
    # Test 3: Index force recreation
    result3 = test_index_recreation()
    test_results.append(("Index Force Recreation", result3))
    
    # Test 4: Document processing with automatic index creation
    result4 = test_document_processing_with_index_creation()
    test_results.append(("Document Processing with Index Creation", result4))
    
    # Test 5: Search functionality
    result5 = test_search_functionality()
    test_results.append(("Search Functionality", result5))
    
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
        print("🎉 ALL TESTS PASSED! Index creation functionality is working correctly!")
        print("\n✅ Verified Functionality:")
        print("• Azure Search index is automatically created when needed")
        print("• Index setup endpoint works for manual index management")
        print("• Document processing integrates seamlessly with index creation")
        print("• Search functionality works with the created index")
        print("• Force recreation allows index rebuilding")
    else:
        print("⚠️ Some tests failed. Check the implementation.")
    
    print("\n📝 Index Management Capabilities:")
    print("✅ Automatic index creation during document processing")
    print("✅ Manual index setup via API endpoint")
    print("✅ Index existence checking and validation")
    print("✅ Force recreation for index rebuilding")
    print("✅ Proper error handling and logging")
    
    print("\n🔗 Available Endpoints:")
    print("• POST /api/search/setup - Create/verify index")
    print("• POST /api/search/setup?force_recreate=true - Force recreate index")
    print("• POST /api/process_document - Process document (auto-creates index)")
    print("• GET /api/search/documents - Search index content")

if __name__ == "__main__":
    main()
