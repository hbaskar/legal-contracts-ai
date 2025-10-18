#!/usr/bin/env python3
"""
Test Chunk Comparison Database Functions
Tests the new database functions for capturing and comparing document chunks
"""

import sys
import os
import asyncio
import logging
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    from contracts.database import DatabaseManager
    from contracts.models import FileMetadata
    from contracts.config import config
    
    async def test_chunk_comparison_functions():
        """Test the chunk comparison database functions"""
        print("🧪 Testing Chunk Comparison Database Functions...")
        
        # Initialize database
        db = DatabaseManager()
        await db.initialize()
        print("✅ Database initialized")
        
        # Create test file metadata
        test_metadata = FileMetadata(
            filename="test_chunk_comparison.txt",
            original_filename="test_chunk_comparison.txt",
            file_size=1000,
            content_type="text/plain",
            blob_url="https://test.blob.core.windows.net/uploads/test.txt",
            container_name="uploads",
            upload_timestamp=datetime.now(),
            checksum="abc123",
            user_id="test_user"
        )
        
        file_id = await db.save_file_metadata(test_metadata)
        print(f"✅ Test file metadata saved with ID: {file_id}")
        
        # Test 1: Save document chunks using different methods
        print("\n1. Testing document chunk storage...")
        
        # Method A: Fixed-size chunking
        method_a_chunks = [
            "This is the first chunk of the document. It contains some important information about the topic.",
            "This is the second chunk. It continues the discussion with more details and examples.",
            "The third chunk provides additional context and concludes the main points of the document."
        ]
        
        start_time = time.time()
        for i, chunk_text in enumerate(method_a_chunks):
            await db.save_document_chunk(
                file_id=file_id,
                chunk_index=i,
                chunk_method="fixed_size",
                chunk_text=chunk_text,
                start_pos=i * 100,
                end_pos=(i + 1) * 100,
                keyphrases=[f"keyword{i+1}", f"topic{i+1}"],
                ai_summary=f"Summary of chunk {i+1}",
                ai_title=f"Section {i+1}",
                processing_time_ms=50 + i * 10
            )
        method_a_time = int((time.time() - start_time) * 1000)
        
        # Method B: Intelligent chunking (different boundaries)
        method_b_chunks = [
            "This is the first chunk of the document. It contains some important information about the topic. This is the second chunk.",
            "It continues the discussion with more details and examples. The third chunk provides additional context.",
            "And concludes the main points of the document."
        ]
        
        start_time = time.time()
        for i, chunk_text in enumerate(method_b_chunks):
            await db.save_document_chunk(
                file_id=file_id,
                chunk_index=i,
                chunk_method="intelligent",
                chunk_text=chunk_text,
                start_pos=i * 120,
                end_pos=(i + 1) * 120,
                keyphrases=[f"smart_keyword{i+1}", f"ai_topic{i+1}"],
                ai_summary=f"AI summary of chunk {i+1}",
                ai_title=f"Intelligent Section {i+1}",
                processing_time_ms=75 + i * 15
            )
        method_b_time = int((time.time() - start_time) * 1000)
        
        print(f"   ✅ Saved {len(method_a_chunks)} chunks for 'fixed_size' method")
        print(f"   ✅ Saved {len(method_b_chunks)} chunks for 'intelligent' method")
        
        # Test 2: Retrieve document chunks
        print("\n2. Testing chunk retrieval...")
        
        fixed_chunks = await db.get_document_chunks(file_id, "fixed_size")
        intelligent_chunks = await db.get_document_chunks(file_id, "intelligent")
        all_chunks = await db.get_document_chunks(file_id)
        
        print(f"   ✅ Retrieved {len(fixed_chunks)} fixed-size chunks")
        print(f"   ✅ Retrieved {len(intelligent_chunks)} intelligent chunks")
        print(f"   ✅ Retrieved {len(all_chunks)} total chunks")
        
        # Test 3: Save Azure Search chunk information
        print("\n3. Testing Azure Search chunk tracking...")
        
        for chunk in fixed_chunks:
            await db.save_azure_search_chunk(
                document_chunk_id=chunk['id'],
                search_document_id=f"search_doc_{chunk['id']}",
                index_name="test-index",
                upload_status="success",
                upload_response='{"status": "success", "key": "uploaded"}',
                embedding_dimensions=1536
            )
        
        print(f"   ✅ Tracked {len(fixed_chunks)} chunks in Azure Search")
        
        # Test 4: Compare chunking methods
        print("\n4. Testing chunk comparison analysis...")
        
        comparison = await db.compare_chunking_methods(file_id, "fixed_size", "intelligent")
        
        print(f"   📊 Comparison Results:")
        print(f"      • Fixed Size: {comparison['total_chunks_a']} chunks, avg size: {comparison['avg_chunk_size_a']:.1f}")
        print(f"      • Intelligent: {comparison['total_chunks_b']} chunks, avg size: {comparison['avg_chunk_size_b']:.1f}")
        print(f"      • Similarity Score: {comparison['similarity_score']:.2f}")
        print(f"      • Content Overlap: {comparison['content_overlap_pct']:.1f}%")
        print(f"      • Processing Time Ratio: {comparison['processing_time_a_ms']}ms vs {comparison['processing_time_b_ms']}ms")
        
        # Test 5: Retrieve comparison history
        print("\n5. Testing comparison history retrieval...")
        
        comparisons = await db.get_chunk_comparisons(file_id)
        all_comparisons = await db.get_chunk_comparisons()
        
        print(f"   ✅ Retrieved {len(comparisons)} comparisons for this file")
        print(f"   ✅ Retrieved {len(all_comparisons)} total comparisons")
        
        if comparisons:
            latest = comparisons[0]
            print(f"   📊 Latest Comparison: {latest['comparison_name']}")
            print(f"      • Analysis Time: {latest['analysis_timestamp']}")
            print(f"      • Detailed Analysis Keys: {list(latest['detailed_analysis'].keys())}")
        
        print("\n🎉 All chunk comparison tests completed successfully!")
        
        return {
            'file_id': file_id,
            'chunks_saved': len(method_a_chunks) + len(method_b_chunks),
            'comparison_result': comparison,
            'test_status': 'success'
        }

    async def cleanup_test_data(file_id: int):
        """Clean up test data (optional)"""
        try:
            db = DatabaseManager()
            
            if db.db_type == 'sqlite':
                import aiosqlite
                async with aiosqlite.connect(db.sqlite_path) as conn:
                    # Delete in reverse order of dependencies
                    await conn.execute("DELETE FROM chunk_comparisons WHERE file_id = ?", (file_id,))
                    await conn.execute("DELETE FROM azure_search_chunks WHERE document_chunk_id IN (SELECT id FROM document_chunks WHERE file_id = ?)", (file_id,))
                    await conn.execute("DELETE FROM document_chunks WHERE file_id = ?", (file_id,))
                    await conn.execute("DELETE FROM file_metadata WHERE id = ?", (file_id,))
                    await conn.commit()
            
            print(f"✅ Cleaned up test data for file_id: {file_id}")
            
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

    async def main():
        """Main test runner"""
        try:
            print("🚀 Chunk Comparison Database Test Suite")
            print("=" * 60)
            
            # Run tests
            result = await test_chunk_comparison_functions()
            
            print(f"\n📋 Test Summary:")
            print(f"   File ID: {result['file_id']}")
            print(f"   Chunks Saved: {result['chunks_saved']}")
            print(f"   Status: {result['test_status']}")
            
            # Ask user if they want to clean up test data
            cleanup = input(f"\nClean up test data? (y/N): ").lower().strip()
            if cleanup in ['y', 'yes']:
                await cleanup_test_data(result['file_id'])
            else:
                print(f"Test data preserved. File ID: {result['file_id']}")
            
            print(f"\n✅ All tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

    if __name__ == "__main__":
        asyncio.run(main())
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the tests directory and all packages are installed")
    sys.exit(1)