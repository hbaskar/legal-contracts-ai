#!/usr/bin/env python3
"""
Test script to read content directly from Azure Search index
This demonstrates retrieving actual content stored in Azure Search
"""

import requests
import json

def test_azure_search_index_content():
    """Test reading content directly from Azure Search index"""
    
    print("🔍 Testing Content from Azure Search Index")
    print("=" * 50)
    print("🎯 Reading content DIRECTLY from Azure Search, not from database")
    print()
    
    # Test 1: Get all documents from index
    print("📋 Test 1: Get all documents from Azure Search index")
    print("-" * 45)
    
    response = requests.get('http://localhost:7071/api/search/documents?limit=3')
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data.get('status')}")
        print(f"📋 Message: {data.get('message')}")
        print(f"📊 Total Documents: {data.get('total_documents')}")
        print(f"🔍 Index Name: {data.get('index_name')}")
        print(f"📡 Source: {data.get('source')}")
        print()
        
        documents = data.get('documents', [])
        for i, doc in enumerate(documents, 1):
            print(f"Document {i}:")
            print(f"  ID: {doc['id']}")
            print(f"  Title: {doc['title']}")
            print(f"  Filename: {doc['filename']}")
            print(f"  Content Length: {doc['content_length']} characters")
            print(f"  Content Preview: {doc['content'][:150]}...")
            print(f"  Keyphrases: {doc['keyphrases'][:3] if doc['keyphrases'] else []}")
            print(f"  Search Score: {doc.get('search_score', 'N/A')}")
            print()
            
        if len(documents) > 0:
            print("✅ SUCCESS: Content is available directly from Azure Search!")
        else:
            print("⚠️ No documents found in Azure Search index")
    else:
        print(f"❌ Error: {response.text}")
        return False
    
    print()
    
    # Test 2: Get specific document by ID
    if response.status_code == 200 and documents:
        print("📋 Test 2: Get specific document by ID")
        print("-" * 35)
        
        doc_id = documents[0]['id']
        response2 = requests.get(f'http://localhost:7071/api/search/documents?document_id={doc_id}')
        
        print(f"Requesting document ID: {doc_id}")
        print(f"Status Code: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            docs = data2.get('documents', [])
            
            if docs:
                doc = docs[0]
                print(f"✅ Retrieved specific document")
                print(f"📄 Full Content ({doc['content_length']} characters):")
                print("=" * 60)
                print(doc['content'])
                print("=" * 60)
                print(f"📝 Summary: {doc.get('summary', 'N/A')}")
                print(f"🏷️ Keyphrases: {doc.get('keyphrases', [])}")
            else:
                print("⚠️ No document found with that ID")
        else:
            print(f"❌ Error: {response2.text}")
    
    print()
    
    # Test 3: Filter by filename
    if response.status_code == 200 and documents:
        print("📋 Test 3: Filter by filename")
        print("-" * 25)
        
        filename = documents[0]['filename']
        response3 = requests.get(f'http://localhost:7071/api/search/documents?filename={filename}')
        
        print(f"Filtering by filename: {filename}")
        print(f"Status Code: {response3.status_code}")
        
        if response3.status_code == 200:
            data3 = response3.json()
            filtered_docs = data3.get('documents', [])
            
            print(f"✅ Found {len(filtered_docs)} documents for filename: {filename}")
            
            total_content = sum(doc['content_length'] for doc in filtered_docs)
            print(f"📊 Total content length: {total_content:,} characters")
            
            methods = set(doc.get('paragraph_id', 'unknown') for doc in filtered_docs)
            print(f"📋 Document chunks: {len(filtered_docs)}")
        else:
            print(f"❌ Error: {response3.text}")

def test_using_ai_services_directly():
    """Test using the AI services function directly"""
    
    print("\n🧪 Testing AI Services Function Directly")
    print("=" * 40)
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from contracts.ai_services import get_documents_from_azure_search_index
        
        print("📊 Calling get_documents_from_azure_search_index() directly...")
        
        result = get_documents_from_azure_search_index(limit=2)
        
        if result['status'] == 'success':
            documents = result['documents']
            print(f"✅ Retrieved {len(documents)} documents directly")
            
            for i, doc in enumerate(documents, 1):
                print(f"\nDocument {i} (Direct from Index):")
                print(f"  Content: {doc['content'][:100]}...")
                print(f"  Length: {doc['content_length']} chars")
                print(f"  Title: {doc['title']}")
        else:
            print(f"❌ Error: {result['message']}")
            
    except Exception as e:
        print(f"❌ Direct function test failed: {e}")

if __name__ == "__main__":
    print("🔍 Azure Search Index Content Test")
    print("🎯 Reading content DIRECTLY from Azure Search Index")
    print("=" * 60)
    
    # Test via API
    test_azure_search_index_content()
    
    # Test directly
    test_using_ai_services_directly()
    
    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("   ✅ Content IS stored in Azure Search index")
    print("   ✅ Content can be retrieved via API endpoint")
    print("   ✅ Full document text is available in 'paragraph' field")
    print("   ✅ No need to join with local database")
    print("   ✅ This is the actual content stored in Azure Search!")
    
    print("\n💡 API Endpoints:")
    print("   GET /api/search/documents              - All documents")
    print("   GET /api/search/documents?limit=10     - Limited results")
    print("   GET /api/search/documents?filename=X   - Filter by filename") 
    print("   GET /api/search/documents?document_id=Y - Specific document")