"""
Database Operations Test for Policy Processing
Simple test without Unicode to check database connectivity
"""

import asyncio
import sys
import os

async def test_database():
    """Test database operations"""
    
    print("DATABASE CONNECTIVITY TEST")
    print("=" * 50)
    
    try:
        from contracts.ai_services import get_database_manager
        
        db_mgr = get_database_manager()
        
        if not db_mgr:
            print("ERROR: Database manager not available")
            return False
        
        print("SUCCESS: Database manager obtained")
        print(f"Database type: {db_mgr.db_type}")
        
        if hasattr(db_mgr, 'sqlite_path'):
            print(f"SQLite path: {db_mgr.sqlite_path}")
            print(f"SQLite exists: {os.path.exists(db_mgr.sqlite_path)}")
        
        # Test file metadata save
        print("\nTesting file metadata save...")
        try:
            from contracts.models import FileMetadata
            from datetime import datetime
            
            # Create FileMetadata object
            file_metadata = FileMetadata(
                filename="test_policy_debug.txt",
                original_filename="test_policy_debug.txt",
                file_size=1234,
                content_type="policy",
                checksum="debug_hash_12345",
                upload_timestamp=datetime.now()
            )
            
            file_id = await db_mgr.save_file_metadata(file_metadata)
            print(f"SUCCESS: File metadata saved with ID: {file_id}")
        except Exception as e:
            print(f"ERROR: File metadata save failed: {e}")
            return False
        
        # Test document chunk save
        print("\nTesting document chunk save...")
        try:
            chunk_id = await db_mgr.save_document_chunk(
                file_id=file_id,
                chunk_index=0,
                chunk_method="policy_debug_test",
                chunk_text="This is a debug test policy clause.",
                keyphrases=["debug", "policy", "test"],
                ai_summary="Debug policy summary",
                ai_title="Debug Policy Title"
            )
            print(f"SUCCESS: Document chunk saved with ID: {chunk_id}")
        except Exception as e:
            print(f"ERROR: Document chunk save failed: {e}")
            return False
        
        # Test Azure Search chunk save
        print("\nTesting Azure Search chunk save...")
        try:
            azure_chunk_id = await db_mgr.save_azure_search_chunk(
                document_chunk_id=chunk_id,
                search_document_id="debug-search-doc-123",
                index_name="rag-policy-index-v2",
                upload_status="success",
                paragraph_content="Debug policy clause content",
                paragraph_title="Debug Policy Title",
                paragraph_summary="Debug policy summary",
                filename="test_policy_debug.txt"
            )
            print(f"SUCCESS: Azure Search chunk saved with ID: {azure_chunk_id}")
        except Exception as e:
            print(f"ERROR: Azure Search chunk save failed: {e}")
            return False
        
        print("\nAll database operations completed successfully!")
        return True
        
    except Exception as e:
        print(f"CRITICAL ERROR: Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_database())
        if result:
            print("\nDATABASE TEST: PASSED")
        else:
            print("\nDATABASE TEST: FAILED")
    except Exception as e:
        print(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()