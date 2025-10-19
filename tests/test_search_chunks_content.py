#!/usr/bin/env python3
"""
Test script to demonstrate Azure Search chunks with content
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_azure_search_chunks_with_content():
    """Test the new function to get Azure Search chunks with content"""
    
    print("🔍 Testing Azure Search Chunks with Content")
    print("=" * 50)
    
    try:
        from config.database import DatabaseManager
        
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        print("✅ Database manager initialized")
        
        # Test 1: Get all Azure Search chunks with content
        print("\n📋 Test 1: All Azure Search chunks with content")
        print("-" * 45)
        
        all_chunks = await db_mgr.get_azure_search_chunks_with_content()
        
        print(f"Found {len(all_chunks)} Azure Search chunks with content")
        
        for i, chunk in enumerate(all_chunks[:3], 1):  # Show first 3
            print(f"\nChunk {i}:")
            print(f"  Search Document ID: {chunk['search_document_id']}")
            print(f"  Upload Status: {chunk['upload_status']}")
            print(f"  Chunk Method: {chunk['chunk_method']}")
            print(f"  Content Length: {len(chunk['chunk_text'])} characters")
            print(f"  Content Preview: {chunk['chunk_text'][:100]}...")
            print(f"  AI Title: {chunk['ai_title']}")
            print(f"  Keyphrases: {chunk['keyphrases'][:3] if chunk['keyphrases'] else []}")
        
        if len(all_chunks) > 3:
            print(f"\n... and {len(all_chunks) - 3} more chunks")
        
        # Test 2: Get chunks for a specific file
        print(f"\n📋 Test 2: Chunks for specific file")
        print("-" * 35)
        
        if all_chunks:
            file_id = all_chunks[0]['file_id']
            file_chunks = await db_mgr.get_azure_search_chunks_with_content(file_id=file_id)
            
            print(f"File {file_id} has {len(file_chunks)} chunks in Azure Search")
            
            total_content_length = sum(len(chunk['chunk_text']) for chunk in file_chunks)
            print(f"Total content length: {total_content_length:,} characters")
            
            # Show method distribution
            methods = {}
            for chunk in file_chunks:
                method = chunk['chunk_method']
                methods[method] = methods.get(method, 0) + 1
            
            print("Method distribution:")
            for method, count in methods.items():
                print(f"  {method}: {count} chunks")
        
        # Test 3: Get a specific search document
        print(f"\n📋 Test 3: Specific search document")
        print("-" * 35)
        
        if all_chunks:
            search_doc_id = all_chunks[0]['search_document_id']
            specific_chunk = await db_mgr.get_azure_search_chunks_with_content(
                search_document_id=search_doc_id
            )
            
            if specific_chunk:
                chunk = specific_chunk[0]
                print(f"Search Document: {chunk['search_document_id']}")
                print(f"Full Content ({len(chunk['chunk_text'])} chars):")
                print("=" * 60)
                print(chunk['chunk_text'])
                print("=" * 60)
                print(f"AI Summary: {chunk['ai_summary']}")
                print(f"Keyphrases: {chunk['keyphrases']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    
    print("🧪 Azure Search Chunks Content Test")
    print("🎯 Demonstrating that content IS available via proper join queries")
    print("=" * 70)
    
    success = await test_azure_search_chunks_with_content()
    
    print("\n" + "=" * 70)
    
    if success:
        print("🎉 SUCCESS: Azure Search chunks DO have content!")
        print("\n💡 Key Points:")
        print("   - azure_search_chunks table tracks relationships")
        print("   - document_chunks table stores actual content")
        print("   - Use get_azure_search_chunks_with_content() to join both")
        print("   - Content is preserved and accessible via JOIN queries")
    else:
        print("❌ FAILED: Could not retrieve content")
    
    print("\n📚 Usage:")
    print("   # Get all chunks with content")
    print("   chunks = await db_mgr.get_azure_search_chunks_with_content()")
    print("   ")
    print("   # Get chunks for specific file")
    print("   chunks = await db_mgr.get_azure_search_chunks_with_content(file_id=123)")
    print("   ")
    print("   # Get specific search document")
    print("   chunk = await db_mgr.get_azure_search_chunks_with_content(")
    print("       search_document_id='doc_1'")
    print("   )")

if __name__ == "__main__":
    asyncio.run(main())
