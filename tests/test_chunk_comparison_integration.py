#!/usr/bin/env python3
"""
Test Chunk Comparison Integration
Tests the integrated chunk comparison functionality with real document processing
"""

import sys
import os
import asyncio
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from contracts.chunk_comparison import compare_document_chunking, get_chunking_report
    from config.database import DatabaseManager
    from contracts.models import FileMetadata
    from datetime import datetime
    
    async def test_integrated_chunk_comparison():
        """Test the integrated chunk comparison functionality"""
        
        print("🧪 Testing Integrated Chunk Comparison...")
        
        # Sample legal document for testing
        sample_document = """
        AGREEMENT FOR PROFESSIONAL SERVICES
        
        This Agreement for Professional Services ("Agreement") is entered into as of the date last signed below ("Effective Date") by and between Company ABC, a Delaware corporation ("Company"), and Service Provider XYZ, a California limited liability company ("Provider").
        
        1. SCOPE OF SERVICES
        Provider shall provide the services described in Exhibit A attached hereto and incorporated herein by reference ("Services"). Provider represents and warrants that it has the necessary qualifications, experience, and expertise to perform the Services in a professional and workmanlike manner.
        
        2. COMPENSATION AND PAYMENT TERMS
        In consideration for the Services, Company shall pay Provider the fees set forth in Exhibit B attached hereto and incorporated herein by reference ("Fees"). Payment terms shall be net thirty (30) days from receipt of invoice. Late payments shall accrue interest at the rate of one and one-half percent (1.5%) per month.
        
        3. TERM AND TERMINATION
        This Agreement shall commence on the Effective Date and shall continue for a period of twelve (12) months, unless earlier terminated in accordance with the provisions hereof. Either party may terminate this Agreement upon thirty (30) days' written notice to the other party.
        
        4. INTELLECTUAL PROPERTY
        All work product, deliverables, and intellectual property created by Provider in connection with the Services shall be owned by Company. Provider hereby assigns all right, title, and interest in such work product to Company.
        
        5. CONFIDENTIALITY
        Each party acknowledges that it may receive certain confidential information from the other party. Each party agrees to maintain the confidentiality of such information and use it solely for the purposes contemplated by this Agreement.
        
        6. LIMITATION OF LIABILITY
        IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, REGARDLESS OF THE THEORY OF LIABILITY AND WHETHER OR NOT SUCH PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
        
        7. GOVERNING LAW
        This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law principles.
        
        IN WITNESS WHEREOF, the parties have executed this Agreement as of the date last signed below.
        """
        
        # Initialize database and create test file metadata
        db = DatabaseManager()
        await db.initialize()
        
        test_metadata = FileMetadata(
            filename="professional_services_agreement.txt",
            original_filename="professional_services_agreement.txt", 
            file_size=len(sample_document),
            content_type="text/plain",
            blob_url="https://test.blob.core.windows.net/uploads/agreement.txt",
            container_name="uploads",
            upload_timestamp=datetime.now(),
            checksum="legal_doc_123",
            user_id="test_user"
        )
        
        file_id = await db.save_file_metadata(test_metadata)
        print(f"✅ Test file saved with ID: {file_id}")
        
        # Test comprehensive chunk comparison
        print(f"\n🔄 Processing document with multiple chunking methods...")
        
        results = await compare_document_chunking(
            document_text=sample_document,
            filename="professional_services_agreement.txt",
            file_id=file_id
        )
        
        print(f"\n📊 Processing Results:")
        print(f"   Document Length: {results['document_length']} characters")
        print(f"   Methods Tested: {list(results['methods'].keys())}")
        print(f"   Recommended Method: {results['recommended_method']}")
        
        # Display method performance
        print(f"\n📈 Method Performance:")
        for method, data in results['methods'].items():
            print(f"   {method.upper()}:")
            print(f"      Chunks Created: {data['chunks_created']}")
            print(f"      Avg Chunk Size: {data['avg_chunk_size']:.1f} chars")
            print(f"      Processing Time: {data['processing_time_ms']}ms")
            if data.get('ai_enhanced'):
                print(f"      AI Enhanced: ✅")
        
        # Display comparisons
        print(f"\n🔍 Comparison Results:")
        for i, comparison in enumerate(results['comparisons'], 1):
            print(f"   Comparison {i}: {comparison['method_a']} vs {comparison['method_b']}")
            print(f"      Similarity Score: {comparison['similarity_score']:.2f}")
            print(f"      Content Overlap: {comparison['content_overlap_pct']:.1f}%")
            print(f"      Processing Time: {comparison['processing_time_a_ms']}ms vs {comparison['processing_time_b_ms']}ms")
        
        # Generate comprehensive report
        print(f"\n📋 Generating Comprehensive Report...")
        
        report = await get_chunking_report(file_id)
        
        print(f"\n📊 Chunking Analysis Report:")
        print(f"   File ID: {report['file_id']}")
        print(f"   Methods Analyzed: {report['methods_analyzed']}")
        print(f"   Total Chunks: {report['total_chunks']}")
        print(f"   Comparisons Made: {report['comparisons_count']}")
        
        print(f"\n📈 Method Summary:")
        for method, summary in report['methods_summary'].items():
            print(f"   {method.upper()}:")
            print(f"      Total Chunks: {summary['total_chunks']}")
            print(f"      Avg Size: {summary['avg_chunk_size']:.1f} chars")
            print(f"      Processing Time: {summary['total_processing_time']}ms")
            print(f"      AI Features: {'✅' if summary['has_ai_features'] else '❌'}")
            print(f"      Sample: {summary['sample_chunk']}")
        
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
        
        print(f"\n🎉 Integrated chunk comparison test completed successfully!")
        
        return {
            'file_id': file_id,
            'processing_results': results,
            'analysis_report': report,
            'test_status': 'success'
        }

    async def cleanup_test_data(file_id: int):
        """Clean up test data"""
        try:
            db = DatabaseManager()
            
            if db.db_type == 'sqlite':
                import aiosqlite
                async with aiosqlite.connect(db.sqlite_path) as conn:
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
            print("🚀 Integrated Chunk Comparison Test Suite")
            print("=" * 70)
            
            result = await test_integrated_chunk_comparison()
            
            print(f"\n📋 Test Summary:")
            print(f"   File ID: {result['file_id']}")
            print(f"   Methods Tested: {len(result['processing_results']['methods'])}")
            print(f"   Comparisons Made: {len(result['processing_results']['comparisons'])}")
            print(f"   Recommended Method: {result['processing_results']['recommended_method']}")
            print(f"   Status: {result['test_status']}")
            
            # Ask user if they want to clean up test data
            cleanup = input(f"\nClean up test data? (y/N): ").lower().strip()
            if cleanup in ['y', 'yes']:
                await cleanup_test_data(result['file_id'])
            else:
                print(f"Test data preserved. Use file_id {result['file_id']} for further analysis.")
            
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
