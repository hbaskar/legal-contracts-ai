#!/usr/bin/env python3
"""
Test Script for Azure Search Chunks Paragraph Data Persistence

This script tests the new functionality to persist paragraph data
in the azure_search_chunks table, ensuring that:

1. Paragraph data is stored during document processing
2. Data can be retrieved via the new API endpoint
3. Content matches what's stored in Azure Search index
4. Database schema changes are working correctly

Usage:
    python test_paragraph_persistence.py
"""

import asyncio
import json
import requests
import tempfile
import os
from datetime import datetime
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.database import DatabaseManager
from contracts.config import config

# API Configuration
BASE_URL = "http://localhost:7071"
API_ENDPOINTS = {
    "upload": f"{BASE_URL}/api/upload",
    "process": f"{BASE_URL}/api/process_document", 
    "persisted_chunks": f"{BASE_URL}/api/search/chunks/persisted",
    "azure_search_docs": f"{BASE_URL}/api/search/documents"
}

def create_test_document():
    """Create a test document for processing"""
    content = """
    # Paragraph Data Persistence Test Document

    ## Section 1: Introduction
    This document is specifically designed to test the new paragraph data persistence functionality 
    in the azure_search_chunks table. The system should now store the full paragraph content 
    along with metadata directly in the local database.

    ## Section 2: Technical Details
    The enhanced azure_search_chunks table now includes fields for paragraph_content, paragraph_title,
    paragraph_summary, paragraph_keyphrases, and other metadata that was previously only available 
    in the Azure Search index.

    ## Section 3: Verification Points
    We need to verify that:
    1. Data is persisted during document processing
    2. Content matches Azure Search index
    3. API endpoints return correct data
    4. Database queries work properly
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        return f.name

async def test_database_schema():
    """Test that the database schema has been updated correctly"""
    print("🔍 Testing database schema...")
    
    try:
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        # Test that we can query the new fields (this will fail if schema not updated)
        if db_mgr.db_type == 'sqlite':
            import aiosqlite
            async with aiosqlite.connect(db_mgr.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT paragraph_content, paragraph_title, paragraph_summary, 
                           paragraph_keyphrases, filename, paragraph_id, 
                           date_uploaded, group_tags, department, language,
                           is_compliant, content_length
                    FROM azure_search_chunks 
                    LIMIT 1
                """)
                # If this doesn't throw an error, schema is updated
                print("✅ Database schema updated successfully")
                return True
                
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False

def upload_test_document():
    """Upload the test document"""
    print("📤 Uploading test document...")
    
    test_file_path = create_test_document()
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': ('paragraph_persistence_test.txt', f, 'text/plain')}
            headers = {'X-User-ID': 'test-paragraph-persistence'}
            
            response = requests.post(API_ENDPOINTS["upload"], files=files, headers=headers, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful: {result['message']}")
            # Debug: print the full response to see structure
            print(f"   Response keys: {list(result.keys())}")
            
            # Try different possible filename locations
            filename = None
            if 'file_metadata' in result and result['file_metadata']:
                filename = result['file_metadata'].get('filename') or result['file_metadata'].get('original_filename')
            elif 'filename' in result:
                filename = result['filename']
            elif 'file_id' in result:
                # If we only have file_id, we can use the original filename
                filename = 'paragraph_persistence_test.txt'
            
            if filename:
                print(f"   Using filename: {filename}")
                return filename
            else:
                print(f"   Available response data: {result}")
                # Fallback to original filename
                return 'paragraph_persistence_test.txt'
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None
    finally:
        # Clean up temp file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)

def process_document(filename):
    """Process the uploaded document with AI chunking"""
    print("🧠 Processing document with AI chunking...")
    
    try:
        # Create the test content again for processing
        content = """
        # Paragraph Data Persistence Test Document

        ## Section 1: Introduction
        This document is specifically designed to test the new paragraph data persistence functionality 
        in the azure_search_chunks table. The system should now store the full paragraph content 
        along with metadata directly in the local database.

        ## Section 2: Technical Details
        The enhanced azure_search_chunks table now includes fields for paragraph_content, paragraph_title,
        paragraph_summary, paragraph_keyphrases, and other metadata that was previously only available 
        in the Azure Search index.

        ## Section 3: Verification Points
        We need to verify that:
        1. Data is persisted during document processing
        2. Content matches Azure Search index
        3. API endpoints return correct data
        4. Database queries work properly
        """
        
        # Encode content as base64
        import base64
        file_content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            "filename": filename,
            "file_content": file_content_base64,
            "chunking_method": "intelligent",
            "force_reindex": True
        }
        headers = {'Content-Type': 'application/json', 'X-User-ID': 'test-paragraph-persistence'}
        
        response = requests.post(API_ENDPOINTS["process"], json=data, headers=headers, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Processing successful: {result['message']}")
            print(f"   Created {result.get('chunks_created', 0)} chunks")
            print(f"   Uploaded {result.get('successful_uploads', 0)} to Azure Search")
            return True
        else:
            print(f"❌ Processing failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False

def test_persisted_chunks_api(filename):
    """Test the new persisted chunks API endpoint"""
    print("📊 Testing persisted chunks API...")
    
    try:
        # Test all documents
        response = requests.get(API_ENDPOINTS["persisted_chunks"], timeout=30)
        if response.status_code == 200:
            result = response.json()
            total_docs = result.get('total_documents', 0)
            print(f"✅ Retrieved {total_docs} total persisted chunks")
        else:
            print(f"❌ Failed to get all persisted chunks: {response.status_code}")
            return False
        
        # Test filtered by filename
        params = {'filename': filename}
        response = requests.get(API_ENDPOINTS["persisted_chunks"], params=params, timeout=30)
        if response.status_code == 200:
            result = response.json()
            filtered_docs = result.get('total_documents', 0)
            documents = result.get('documents', [])
            
            print(f"✅ Retrieved {filtered_docs} chunks for filename: {filename}")
            
            # Validate data structure
            if documents:
                first_doc = documents[0]
                required_fields = ['id', 'title', 'content', 'content_length', 'summary', 'keyphrases', 'filename']
                missing_fields = [field for field in required_fields if field not in first_doc]
                
                if missing_fields:
                    print(f"❌ Missing required fields: {missing_fields}")
                    return False
                else:
                    print("✅ All required fields present in response")
                    print(f"   Sample content length: {first_doc.get('content_length', 0)} characters")
                    print(f"   Sample title: {first_doc.get('title', 'N/A')}")
                    return True
            else:
                print("⚠️  No documents returned for filtered query")
                return False
        else:
            print(f"❌ Failed to get filtered persisted chunks: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Persisted chunks API test error: {e}")
        return False

def compare_with_azure_search(filename):
    """Compare persisted data with Azure Search index data"""
    print("🔄 Comparing persisted data with Azure Search index...")
    
    try:
        # Get data from persisted chunks
        params = {'filename': filename, 'limit': 5}
        response = requests.get(API_ENDPOINTS["persisted_chunks"], params=params, timeout=30)
        persisted_data = response.json() if response.status_code == 200 else {}
        
        # Get data from Azure Search index
        response = requests.get(API_ENDPOINTS["azure_search_docs"], params=params, timeout=30)
        search_data = response.json() if response.status_code == 200 else {}
        
        persisted_docs = persisted_data.get('documents', [])
        search_docs = search_data.get('documents', [])
        
        if not persisted_docs or not search_docs:
            print("⚠️  No data available for comparison")
            return False
        
        # Compare content
        matches = 0
        for p_doc in persisted_docs:
            for s_doc in search_docs:
                if p_doc['id'] == s_doc['id']:
                    if p_doc['content'] == s_doc['content']:
                        matches += 1
                    break
        
        print(f"✅ Content matches: {matches}/{len(persisted_docs)} documents")
        
        if matches == len(persisted_docs):
            print("🎉 Perfect match between persisted data and Azure Search index!")
            return True
        else:
            print("⚠️  Some content mismatches found")
            return False
            
    except Exception as e:
        print(f"❌ Comparison error: {e}")
        return False

async def test_database_queries():
    """Test direct database queries for persisted data"""
    print("🗄️  Testing direct database queries...")
    
    try:
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        # Test the new get_azure_search_chunks_persisted function
        chunks = await db_mgr.get_azure_search_chunks_persisted(limit=3)
        
        print(f"✅ Retrieved {len(chunks)} chunks from database")
        
        if chunks:
            first_chunk = chunks[0]
            print(f"   Sample ID: {first_chunk.get('id', 'N/A')}")
            print(f"   Sample title: {first_chunk.get('title', 'N/A')}")
            print(f"   Sample content length: {first_chunk.get('content_length', 0)}")
            print(f"   Sample filename: {first_chunk.get('filename', 'N/A')}")
            
            # Verify content is not None
            if first_chunk.get('content'):
                print("✅ Paragraph content successfully persisted")
                return True
            else:
                print("❌ Paragraph content is empty or None")
                return False
        else:
            print("⚠️  No chunks found in database")
            return False
            
    except Exception as e:
        print(f"❌ Database query test error: {e}")
        return False

async def main():
    """Run all paragraph persistence tests"""
    print("🚀 Starting Paragraph Data Persistence Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Database Schema
    print("\n1️⃣  Database Schema Test")
    result1 = await test_database_schema()
    test_results.append(("Database Schema", result1))
    
    if not result1:
        print("❌ Cannot proceed without proper database schema")
        return
    
    # Test 2: Upload Document
    print("\n2️⃣  Document Upload Test")
    filename = upload_test_document()
    result2 = filename is not None
    test_results.append(("Document Upload", result2))
    
    if not result2:
        print("❌ Cannot proceed without successful upload")
        return
    
    # Test 3: Process Document
    print("\n3️⃣  Document Processing Test")
    result3 = process_document(filename)
    test_results.append(("Document Processing", result3))
    
    if not result3:
        print("❌ Cannot proceed without successful processing")
        return
    
    # Wait a moment for processing to complete
    print("⏱️  Waiting for processing to complete...")
    await asyncio.sleep(5)
    
    # Test 4: Persisted Chunks API
    print("\n4️⃣  Persisted Chunks API Test")
    result4 = test_persisted_chunks_api(filename)
    test_results.append(("Persisted Chunks API", result4))
    
    # Test 5: Database Queries
    print("\n5️⃣  Direct Database Queries Test")
    result5 = await test_database_queries()
    test_results.append(("Database Queries", result5))
    
    # Test 6: Compare with Azure Search
    print("\n6️⃣  Azure Search Comparison Test")
    result6 = compare_with_azure_search(filename)
    test_results.append(("Azure Search Comparison", result6))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 ALL TESTS PASSED! Paragraph data persistence is working correctly!")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    print("\n📝 Next Steps:")
    print("1. Import the updated Postman collection")
    print("2. Test the new /api/search/chunks/persisted endpoint")
    print("3. Verify paragraph data is available in local database")
    print("4. Compare performance between direct index vs persisted data access")

if __name__ == "__main__":
    asyncio.run(main())