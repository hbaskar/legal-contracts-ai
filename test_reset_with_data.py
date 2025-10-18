"""
Simple test to validate reset functionality works with actual data
"""

import asyncio
import os
import sys
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from contracts.database import DatabaseManager
from contracts.models import FileMetadata
from datetime import datetime, UTC

async def test_reset_with_data():
    """Test reset functionality with actual data"""
    print("🧪 Testing Reset Functionality with Sample Data")
    print("=" * 50)
    
    # Initialize database manager
    db_mgr = DatabaseManager()
    await db_mgr.initialize()
    
    # Add some test data
    print("📥 Adding test data...")
    
    # Create sample file metadata
    test_metadata = FileMetadata(
        filename="test_reset_file.txt",
        original_filename="test_reset_file.txt",
        file_size=1234,
        content_type="text/plain",
        blob_url="test://blob/url",
        container_name="test-container",
        upload_timestamp=datetime.now(UTC),
        checksum="test-checksum",
        user_id="test-user"
    )
    
    # Save metadata
    file_id = await db_mgr.save_file_metadata(test_metadata)
    print(f"✅ Created file metadata with ID: {file_id}")
    
    # Add some document chunks
    chunk_id1 = await db_mgr.save_document_chunk(
        file_id=file_id,
        chunk_index=0,
        chunk_method="test",
        chunk_text="Test chunk 1",
        keyphrases=["test", "chunk"],
        ai_summary="Test summary 1"
    )
    print(f"✅ Created document chunk with ID: {chunk_id1}")
    
    chunk_id2 = await db_mgr.save_document_chunk(
        file_id=file_id,
        chunk_index=1,
        chunk_method="test",
        chunk_text="Test chunk 2",
        keyphrases=["another", "test"],
        ai_summary="Test summary 2"
    )
    print(f"✅ Created document chunk with ID: {chunk_id2}")
    
    # Check data exists
    print("\n📊 Checking data before reset...")
    chunks = await db_mgr.get_document_chunks(file_id)
    print(f"Found {len(chunks)} document chunks")
    
    file_metadata = await db_mgr.get_file_metadata(file_id)
    print(f"File metadata exists: {file_metadata is not None}")
    
    # Now perform reset
    print("\n🗑️ Performing database reset...")
    reset_results = await db_mgr.reset_all_tables()
    
    print(f"Reset completed:")
    print(f"  Tables processed: {reset_results['summary']['tables_processed']}")
    print(f"  Tables reset successfully: {reset_results['summary']['tables_reset_successfully']}")
    print(f"  Tables with errors: {reset_results['summary']['tables_with_errors']}")
    print(f"  Total records deleted: {reset_results['total_records_deleted']}")
    
    # Verify data is gone
    print("\n🔍 Verifying data is deleted...")
    chunks_after = await db_mgr.get_document_chunks(file_id)
    print(f"Document chunks after reset: {len(chunks_after)}")
    
    file_metadata_after = await db_mgr.get_file_metadata(file_id)
    print(f"File metadata after reset: {file_metadata_after is not None}")
    
    # Summary
    if len(chunks_after) == 0 and file_metadata_after is None:
        print("\n🎉 SUCCESS: Reset functionality working correctly!")
        print("   ✅ All test data was successfully deleted")
        return True
    else:
        print("\n❌ FAILURE: Reset did not delete all data")
        return False

async def main():
    try:
        success = await test_reset_with_data()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)