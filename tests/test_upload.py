#!/usr/bin/env python3
"""
Test script for Azure Function file upload service

This script tests the file upload functionality by:
1. Creating test files
2. Uploading them to the Azure Function
3. Retrieving file information
4. Testing health check endpoint

Usage:
    python test_upload.py [--host localhost] [--port 7071] [--create-files]
"""

import os
import sys
import argparse
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


class FileUploadTester:
    """Test client for Azure Function file upload service"""
    
    def __init__(self, base_url: str = "http://localhost:7071"):
        """
        Initialize the test client
        
        Args:
            base_url: Base URL of the Azure Function (default: http://localhost:7071)
        """
        self.base_url = base_url.rstrip('/')
        self.upload_url = f"{self.base_url}/api/upload"
        self.health_url = f"{self.base_url}/api/health"
        self.files_url = f"{self.base_url}/api/files"
        
        # Default headers
        self.headers = {
            'X-User-ID': 'test-user-001'  # Optional user identification
        }
        
        print(f"🚀 Initialized test client for: {self.base_url}")
    
    def create_test_files(self, test_dir: str = "./test_files") -> Dict[str, str]:
        """
        Create test files for upload testing
        
        Args:
            test_dir: Directory to create test files in
            
        Returns:
            Dictionary mapping file types to file paths
        """
        test_path = Path(test_dir)
        test_path.mkdir(exist_ok=True)
        
        test_files = {}
        
        # Text file
        txt_file = test_path / "sample.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("This is a test text file for Azure Function upload.\n")
            f.write("Created for testing purposes.\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        test_files['text'] = str(txt_file)
        
        # JSON file
        json_file = test_path / "sample.json"
        sample_data = {
            "name": "Test Document",
            "type": "test",
            "created": time.strftime('%Y-%m-%d %H:%M:%S'),
            "data": ["item1", "item2", "item3"],
            "metadata": {
                "version": "1.0",
                "author": "Test Script"
            }
        }
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2)
        test_files['json'] = str(json_file)
        
        # Binary file (small image-like data)
        bin_file = test_path / "sample.bin"
        with open(bin_file, 'wb') as f:
            # Create some binary data
            f.write(b'\x89PNG\r\n\x1a\n')  # PNG header
            f.write(b'This is test binary data' * 10)
        test_files['binary'] = str(bin_file)
        
        # CSV file
        csv_file = test_path / "sample.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("id,name,email,created\n")
            f.write("1,John Doe,john@example.com,2024-01-01\n")
            f.write("2,Jane Smith,jane@example.com,2024-01-02\n")
            f.write("3,Bob Johnson,bob@example.com,2024-01-03\n")
        test_files['csv'] = str(csv_file)

        # Check for existing PDF file
        pdf_file = test_path / "employee.pdf"
        if pdf_file.exists():
            test_files['pdf'] = str(pdf_file)
            print(f"📄 Found existing PDF file: {pdf_file.name}")
        
        print(f"📁 Created test files in: {test_path.absolute()}")
        for file_type, file_path in test_files.items():
            size = os.path.getsize(file_path)
            print(f"  - {file_type}: {Path(file_path).name} ({size} bytes)")
        
        return test_files
    
    def test_health_check(self) -> bool:
        """
        Test the health check endpoint
        
        Returns:
            True if health check passes, False otherwise
        """
        print("\n🩺 Testing health check endpoint...")
        
        try:
            response = requests.get(self.health_url, timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed")
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Version: {health_data.get('version', 'unknown')}")
                print(f"   Environment: {health_data.get('environment', {}).get('DATABASE_TYPE', 'unknown')}")
                return True
            else:
                print(f"❌ Health check failed with status: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Health check failed with error: {e}")
            return False
    
    def upload_file(self, file_path: str, description: str = "") -> Optional[Dict[str, Any]]:
        """
        Upload a file to the Azure Function
        
        Args:
            file_path: Path to the file to upload
            description: Optional description for the test
            
        Returns:
            Response data if successful, None if failed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return None
        
        print(f"\n📤 Uploading file: {file_path.name} {description}")
        print(f"   Path: {file_path.absolute()}")
        print(f"   Size: {file_path.stat().st_size} bytes")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, self._get_content_type(file_path))}
                
                response = requests.post(
                    self.upload_url,
                    files=files,
                    headers=self.headers,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Upload successful!")
                print(f"   File ID: {data.get('file_id')}")
                print(f"   Original name: {data.get('original_filename')}")
                print(f"   Stored name: {data.get('filename')}")
                print(f"   Size: {data.get('file_size')} bytes")
                print(f"   Content type: {data.get('content_type')}")
                print(f"   Blob URL: {data.get('blob_url', 'N/A')}")
                return data
            else:
                print(f"❌ Upload failed with status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Upload failed with error: {e}")
            return None
    
    def get_file_info(self, file_id: str, include_download_url: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get file information from the Azure Function
        
        Args:
            file_id: ID of the file to retrieve info for
            include_download_url: Whether to include a download URL
            
        Returns:
            File information if successful, None if failed
        """
        print(f"\n📋 Getting file info for ID: {file_id}")
        
        try:
            params = {}
            if include_download_url:
                params['download_url'] = 'true'
                params['expiry_hours'] = '24'
            
            response = requests.get(
                f"{self.files_url}/{file_id}",
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ File info retrieved!")
                print(f"   ID: {data.get('id')}")
                print(f"   Filename: {data.get('filename')}")
                print(f"   Original: {data.get('original_filename')}")
                print(f"   Size: {data.get('file_size')} bytes")
                print(f"   Type: {data.get('content_type')}")
                print(f"   Uploaded: {data.get('upload_timestamp')}")
                print(f"   Container: {data.get('container_name')}")
                if 'download_url' in data:
                    print(f"   Download URL: {data['download_url'][:80]}...")
                return data
            else:
                print(f"❌ Failed to get file info, status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get file info, error: {e}")
            return None
    
    def test_pdf_file(self, pdf_path: str = "./test_files/employee.pdf") -> Optional[Dict[str, Any]]:
        """
        Test PDF file upload with enhanced validation
        
        Args:
            pdf_path: Path to the PDF file to test
            
        Returns:
            Test results including upload and processing information
        """
        print("\n📄 Testing PDF File Upload (employee.pdf)...")
        print("=" * 50)
        
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return None
        
        # Get file statistics
        file_size = pdf_file.stat().st_size
        print(f"📊 PDF File Information:")
        print(f"   File: {pdf_file.name}")
        print(f"   Path: {pdf_file.absolute()}")
        print(f"   Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
        
        # Test upload
        upload_result = self.upload_file(pdf_path, "(PDF document)")
        
        if not upload_result:
            print("❌ PDF upload failed")
            return None
        
        # Enhanced file info check for PDF
        file_info = self.get_file_info(upload_result['file_id'])
        
        if not file_info:
            print("❌ Failed to retrieve PDF file info")
            return None
        
        # Validate PDF-specific properties
        print(f"\n✅ PDF Upload Validation:")
        print(f"   Content Type: {file_info.get('content_type')} {'✅' if file_info.get('content_type') == 'application/pdf' else '❌'}")
        print(f"   File Size Match: {file_info.get('file_size')} bytes {'✅' if file_info.get('file_size') == file_size else '❌'}")
        print(f"   Blob URL: {'✅' if file_info.get('blob_url') else '❌'}")
        
        # Test document processing (if available)
        print(f"\n🔄 Testing document processing...")
        try:
            # Try to trigger document processing
            process_url = f"{self.base_url}/api/process_document"
            process_data = {
                'file_id': upload_result['file_id'],
                'force_reindex': True,
                'chunking_method': 'intelligent'
            }
            
            response = requests.post(
                process_url,
                json=process_data,
                headers=self.headers,
                timeout=120  # PDF processing can take longer
            )
            
            if response.status_code == 200:
                process_result = response.json()
                print(f"✅ Document processing successful!")
                print(f"   Status: {process_result.get('status')}")
                print(f"   Chunks Created: {process_result.get('chunks_created', 0)}")
                print(f"   Processing Time: {process_result.get('processing_time_ms', 0)}ms")
                print(f"   Successful Uploads: {process_result.get('successful_uploads', 0)}")
                
                return {
                    'upload_result': upload_result,
                    'file_info': file_info,
                    'processing_result': process_result,
                    'test_status': 'success'
                }
            else:
                print(f"⚠️ Document processing returned status: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Document processing test failed: {e}")
        
        return {
            'upload_result': upload_result,
            'file_info': file_info,
            'processing_result': None,
            'test_status': 'upload_only'
        }
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get content type based on file extension"""
        extension = file_path.suffix.lower()
        content_types = {
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.bin': 'application/octet-stream',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
            '.xml': 'application/xml'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def run_complete_test(self, test_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Run a complete test suite
        
        Args:
            test_files: Dictionary of test files to upload
            
        Returns:
            Test results summary
        """
        results = {
            'health_check': False,
            'uploads': {},
            'file_info_checks': {},
            'total_files': len(test_files),
            'successful_uploads': 0,
            'successful_info_checks': 0
        }
        
        print("🧪 Running complete test suite...")
        print("=" * 60)
        
        # Test health check first
        results['health_check'] = self.test_health_check()
        
        if not results['health_check']:
            print("\n❌ Health check failed - aborting remaining tests")
            return results
        
        # Test file uploads
        uploaded_files = {}
        for file_type, file_path in test_files.items():
            upload_result = self.upload_file(file_path, f"({file_type} file)")
            results['uploads'][file_type] = upload_result is not None
            
            if upload_result:
                results['successful_uploads'] += 1
                uploaded_files[file_type] = upload_result
        
        # Test file info retrieval
        for file_type, upload_data in uploaded_files.items():
            if upload_data and 'file_id' in upload_data:
                info_result = self.get_file_info(upload_data['file_id'])
                results['file_info_checks'][file_type] = info_result is not None
                
                if info_result:
                    results['successful_info_checks'] += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Health Check: {'✅ PASS' if results['health_check'] else '❌ FAIL'}")
        print(f"File Uploads: {results['successful_uploads']}/{results['total_files']} successful")
        print(f"File Info Checks: {results['successful_info_checks']}/{len(uploaded_files)} successful")
        
        if results['successful_uploads'] == results['total_files']:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed - check logs above")
        
        return results


def main():
    """Main function to run the upload tests"""
    parser = argparse.ArgumentParser(description='Test Azure Function file upload service')
    parser.add_argument('--host', default='localhost', help='Function host (default: localhost)')
    parser.add_argument('--port', default='7071', help='Function port (default: 7071)')
    parser.add_argument('--create-files', action='store_true', help='Create test files')
    parser.add_argument('--file', help='Upload a specific file')
    parser.add_argument('--health-only', action='store_true', help='Only test health check')
    parser.add_argument('--test-pdf', action='store_true', help='Test PDF file (employee.pdf) with document processing')
    parser.add_argument('--pdf-path', default='./test_files/employee.pdf', help='Path to PDF file for testing')
    
    args = parser.parse_args()
    
    # Build base URL
    base_url = f"http://{args.host}:{args.port}"
    
    # Initialize tester
    tester = FileUploadTester(base_url)
    
    if args.health_only:
        # Only test health check
        success = tester.test_health_check()
        sys.exit(0 if success else 1)
    
    if args.test_pdf:
        # Test PDF file specifically
        tester.test_health_check()
        result = tester.test_pdf_file(args.pdf_path)
        
        if result:
            print(f"\n🎯 PDF Test Summary:")
            print(f"   Upload Status: {'✅ Success' if result['upload_result'] else '❌ Failed'}")
            print(f"   File Info: {'✅ Success' if result['file_info'] else '❌ Failed'}")
            print(f"   Processing: {'✅ Success' if result['processing_result'] else '⚠️ Not Available'}")
            print(f"   Overall Status: {result['test_status']}")
        
        sys.exit(0 if result and result.get('upload_result') else 1)
    
    if args.file:
        # Upload a specific file
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        
        tester.test_health_check()
        result = tester.upload_file(args.file)
        
        if result and 'file_id' in result:
            tester.get_file_info(result['file_id'])
        
        sys.exit(0 if result else 1)
    
    # Full test suite
    test_files = {}
    
    if args.create_files:
        # Create test files
        test_files = tester.create_test_files()
    else:
        # Look for existing test files
        test_dir = Path("./test_files")
        if test_dir.exists():
            for file_path in test_dir.glob("*"):
                if file_path.is_file():
                    test_files[file_path.stem] = str(file_path)
        
        if not test_files:
            print("📁 No test files found. Use --create-files to create them, or --file to upload a specific file.")
            sys.exit(1)
    
    # Run complete test
    results = tester.run_complete_test(test_files)
    
    # Exit with appropriate code
    success = (results['health_check'] and 
              results['successful_uploads'] == results['total_files'] and
              results['successful_info_checks'] == results['successful_uploads'])
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()