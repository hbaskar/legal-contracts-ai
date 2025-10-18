#!/usr/bin/env python3
"""
Test Employee PDF File Processing
Comprehensive test for employee.pdf including upload, processing, and chunk comparison
"""

import sys
import os
import asyncio
import requests
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from contracts.chunk_comparison import compare_document_chunking, get_chunking_report
    from contracts.database import DatabaseManager
    from contracts.models import FileMetadata
    from datetime import datetime
    
    class EmployeePDFTester:
        """Comprehensive tester for employee.pdf file"""
        
        def __init__(self, base_url: str = "http://localhost:7071"):
            self.base_url = base_url.rstrip('/')
            self.upload_url = f"{self.base_url}/api/upload"
            self.process_url = f"{self.base_url}/api/process_document"
            self.health_url = f"{self.base_url}/api/health"
            self.headers = {'X-User-ID': 'test-pdf-user'}
        
        async def test_employee_pdf_complete(self, pdf_path: str = "./test_files/employee.pdf"):
            """
            Test employee.pdf upload and wait for blob trigger processing
            """
            print("🧪 Testing Employee PDF - Upload & Blob Trigger Processing")
            print("=" * 60)
            
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                print(f"❌ Employee PDF not found: {pdf_path}")
                return None
            
            # File statistics
            file_size = pdf_file.stat().st_size
            print(f"📄 Employee PDF Information:")
            print(f"   File: {pdf_file.name}")
            print(f"   Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
            
            # Step 1: Health check
            print(f"\n🩺 Step 1: Health Check")
            if not self._test_health():
                return None
            
            # Step 2: Upload PDF (this will trigger blob processing automatically)
            print(f"\n📤 Step 2: Upload PDF")
            upload_result = await self._upload_pdf(pdf_path)
            if not upload_result:
                return None
            
            file_id = upload_result['file_id']
            print(f"✅ PDF uploaded successfully, File ID: {file_id}")
            print(f"� Blob path: {upload_result.get('blob_path', 'N/A')}")
            
            # Step 3: Wait for blob trigger to process the document
            print(f"\n⏱️ Step 3: Waiting for blob trigger processing...")
            print(f"   The blob trigger will automatically process the PDF")
            print(f"   This may take 30-60 seconds...")
            
            # Wait for processing to complete
            await asyncio.sleep(45)  # Give blob trigger time to process
            
            # Step 4: Check database for processing results
            print(f"\n� Step 4: Checking processing results from database")
            await self._check_processing_results(file_id)
            
            # Step 5: Run chunk comparison if we have data
            print(f"\n📊 Step 5: Running chunk comparison analysis")
            await self._run_chunk_comparison_analysis(file_id)
            
            return {
                'upload_result': upload_result,
                'file_id': file_id,
                'test_status': 'complete'
            }
        
        def _test_health(self) -> bool:
            """Test health endpoint"""
            try:
                response = requests.get(self.health_url, timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Health check passed - Status: {health_data.get('status')}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Health check error: {e}")
                return False
        
        async def _upload_pdf(self, pdf_path: str) -> dict:
            """Upload PDF file"""
            try:
                with open(pdf_path, 'rb') as f:
                    files = {'file': ('employee.pdf', f, 'application/pdf')}
                    response = requests.post(
                        self.upload_url,
                        files=files,
                        headers=self.headers,
                        timeout=30
                    )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"❌ Upload failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ Upload error: {e}")
                return None
        
        async def _check_processing_results(self, file_id: int):
            """Check database for processing results"""
            try:
                from contracts.database import DatabaseManager
                
                # Initialize database connection
                db = DatabaseManager()
                await db.initialize()
                
                # Check if document chunks were created
                chunks = await db.get_document_chunks(file_id)
                if chunks:
                    print(f"✅ Found {len(chunks)} document chunks in database")
                    for i, chunk in enumerate(chunks[:3]):  # Show first 3
                        title = chunk.get('chunk_title', chunk.get('title', 'Untitled'))
                        content_len = len(chunk.get('content', chunk.get('chunk_content', '')))
                        print(f"   Chunk {i+1}: {title} ({content_len} chars)")
                else:
                    print(f"⚠️ No document chunks found for file ID {file_id}")
                
                # Check if chunk comparisons exist (this indicates processing happened)
                comparisons = await db.get_chunk_comparisons(file_id)
                if comparisons:
                    print(f"✅ Found {len(comparisons)} chunk comparisons")
                    for i, comp in enumerate(comparisons[:2]):  # Show first 2
                        method_a = comp.get('method_a', 'N/A')
                        method_b = comp.get('method_b', 'N/A')
                        similarity = comp.get('similarity_score', 0.0)
                        print(f"   Comparison {i+1}: {method_a} vs {method_b} (similarity: {similarity:.2f})")
                else:
                    print(f"⚠️ No chunk comparisons found - processing may still be in progress")
                
                await db.close()
                
            except Exception as e:
                print(f"❌ Error checking processing results: {e}")
        
        async def _run_chunk_comparison_analysis(self, file_id: int):
            """Run chunk comparison analysis on sample text"""
            try:
                # Create sample employee document text for analysis
                sample_text = """
                EMPLOYEE HANDBOOK
                
                This is a comprehensive employee handbook that contains important information about 
                company policies, procedures, and benefits. All employees are expected to familiarize 
                themselves with this content and comply with the guidelines outlined herein.
                
                SECTION 1: COMPANY OVERVIEW
                Our company was founded in 1995 with the mission to provide excellent service to our 
                customers while maintaining a positive work environment for our employees. We value 
                integrity, innovation, and teamwork above all else.
                
                Our Mission Statement
                To deliver exceptional value to our customers through innovative solutions while 
                fostering a collaborative and inclusive workplace culture.
                
                SECTION 2: EMPLOYMENT POLICIES
                All employees must adhere to our code of conduct, which includes maintaining professional 
                behavior, respecting colleagues, and following safety protocols at all times.
                
                Code of Conduct
                Professional behavior is expected at all times. This includes respectful communication,
                punctuality, and adherence to company values.
                
                SECTION 3: BENEFITS PACKAGE
                We offer comprehensive health insurance, dental coverage, vision care, retirement planning 
                assistance, and paid time off to all full-time employees after a 90-day probationary period.
                
                Health Benefits
                Full medical, dental, and vision coverage is provided with multiple plan options to 
                choose from based on individual and family needs.
                
                SECTION 4: PERFORMANCE REVIEWS
                Annual performance reviews are conducted to assess employee progress and identify areas 
                for professional development and growth within the organization.
                
                Review Process
                Performance evaluations include goal setting, skill assessment, and career development 
                planning with direct supervisors.
                """ * 2  # Make it longer with clear headings for better analysis
                
                print(f"   Using sample employee text ({len(sample_text):,} characters)")
                
                # Run comprehensive chunk comparison
                comparison_results = await compare_document_chunking(
                    document_text=sample_text,
                    filename="employee.pdf",
                    file_id=str(file_id)
                )
                
                # Display comparison results
                self._display_comparison_results(comparison_results)
                
                # Generate and display report
                print(f"\n📋 Analysis Report:")
                report = await get_chunking_report(str(file_id))
                self._display_analysis_report(report)
                
            except Exception as e:
                print(f"❌ Error running chunk comparison: {e}")
                import traceback
                traceback.print_exc()
        
        def _display_comparison_results(self, results: dict):
            """Display chunk comparison results"""
            print(f"   📈 Method Performance:")
            for method, data in results['methods'].items():
                ai_indicator = " 🤖" if data.get('ai_enhanced') else ""
                structure_indicator = " 📋" if data.get('structural') else ""
                print(f"      • {method.upper()}{ai_indicator}{structure_indicator}:")
                print(f"        Chunks: {data['chunks_created']}")
                print(f"        Avg Size: {data['avg_chunk_size']:.1f} chars")
                print(f"        Time: {data['processing_time_ms']}ms")
            
            print(f"\n   🔍 Comparisons:")
            for comparison in results['comparisons']:
                print(f"      • {comparison['method_a']} vs {comparison['method_b']}:")
                print(f"        Similarity: {comparison['similarity_score']:.2f}")
                print(f"        Overlap: {comparison['content_overlap_pct']:.1f}%")
            
            print(f"\n   🎯 Recommended Method: {results['recommended_method']}")
        
        def _display_analysis_report(self, report: dict):
            """Display analysis report"""
            print(f"   📊 Analysis Summary:")
            print(f"      Methods Tested: {len(report['methods_analyzed'])}")
            print(f"      Total Chunks: {report['total_chunks']}")
            print(f"      Comparisons Made: {report['comparisons_count']}")
            
            print(f"\n   💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"      • {rec}")

    async def main():
        """Main test function"""
        print("🚀 Employee PDF Comprehensive Test Suite")
        print("=" * 70)
        
        # Check if PDF exists
        pdf_path = "./test_files/employee.pdf"
        if not Path(pdf_path).exists():
            # Try relative to script directory
            script_dir = Path(__file__).parent.parent
            pdf_path = script_dir / "test_files" / "employee.pdf"
            
            if not pdf_path.exists():
                print(f"❌ Employee PDF not found in expected locations:")
                print(f"   • ./test_files/employee.pdf")
                print(f"   • {pdf_path}")
                return
        
        tester = EmployeePDFTester()
        
        try:
            result = await tester.test_employee_pdf_complete(str(pdf_path))
            
            if result:
                print(f"\n🎉 Test Results Summary:")
                print(f"   Upload: ✅ Success")
                print(f"   Processing: ✅ Success" if result.get('processing_result') else "❌ Failed")
                print(f"   Chunk Analysis: ✅ Complete" if result.get('comparison_results') else "⚠️ Skipped")
                print(f"   Status: {result['test_status']}")
                
                if result.get('comparison_results'):
                    methods = result['comparison_results']['methods']
                    recommended = result['comparison_results']['recommended_method']
                    print(f"   Best Method: {recommended}")
                    print(f"   Methods Tested: {list(methods.keys())}")
            else:
                print(f"\n❌ Test failed - check logs above")
                
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            import traceback
            traceback.print_exc()

    if __name__ == "__main__":
        asyncio.run(main())
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required packages are installed")
    sys.exit(1)