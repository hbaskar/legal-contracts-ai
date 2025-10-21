#!/usr/bin/env python3
"""
Quick test script to debug why chunks aren't being saved to database
"""
import asyncio
import logging
import sys
import os

# Setup logging to see debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_database_chunk_saving():
    """Test if we can save chunks to database directly"""
    try:
        # Import database manager
        from config.database import DatabaseManager
        from contracts.models import FileMetadata
        from datetime import datetime
        
        print("🔍 Testing database chunk saving...")
        
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        print("✅ Database manager initialized")
        
        # Create test file metadata
        test_metadata = FileMetadata(
            filename="test_chunk_save.txt",
            original_filename="test_chunk_save.txt",
            file_size=100,
            content_type="text/plain",
            blob_url="test://test",
            container_name="test",
            upload_timestamp=datetime.now(),
            checksum="test",
            user_id="test"
        )
        
        # Save metadata
        file_id = await db_mgr.save_file_metadata(test_metadata)
        print(f"✅ Created file metadata with ID: {file_id}")
        
        # Save a test chunk
        chunk_id = await db_mgr.save_document_chunk(
            file_id=file_id,
            chunk_index=0,
            chunk_method="test",
            chunk_text="This is a test chunk for database saving",
            keyphrases=["test", "chunk", "database"],
            ai_summary="Test summary",
            ai_title="Test Title"
        )
        print(f"✅ Saved chunk with ID: {chunk_id}")
        
        # Verify chunk was saved
        chunks = await db_mgr.get_document_chunks(file_id)
        print(f"✅ Retrieved {len(chunks)} chunks from database")
        for chunk in chunks:
            print(f"   - Chunk {chunk['chunk_index']}: {chunk['chunk_text'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing database chunk saving: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_ai_services_database_integration():
    """Test if the AI services can get the database manager"""
    try:
        print("\n🔍 Testing AI services database integration...")
        
        # Test getting database manager from AI services
        from contracts.ai_services import get_database_manager
        
        db_mgr_class = get_database_manager()
        if db_mgr_class:
            print("✅ Database manager class retrieved from AI services")
            
            # Create instance
            db_mgr = db_mgr_class()
            await db_mgr.initialize()
            print("✅ Database manager instance created and initialized")
            
            return True
        else:
            print("❌ Database manager class is None")
            return False
            
    except Exception as e:
        print(f"❌ Error testing AI services database integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting database chunk saving tests...")
    
    async def run_tests():
        test1_passed = await test_database_chunk_saving()
        test2_passed = await test_ai_services_database_integration()
        
        print("\n📊 Test Results:")
        print(f"   Database chunk saving: {'✅ PASS' if test1_passed else '❌ FAIL'}")
        print(f"   AI services integration: {'✅ PASS' if test2_passed else '❌ FAIL'}")
        
        if test1_passed and test2_passed:
            print("\n✅ All tests passed - database integration should work")
        else:
            print("\n❌ Some tests failed - this explains why chunks aren't being saved")
    
    asyncio.run(run_tests())