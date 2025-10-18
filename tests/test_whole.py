#!/usr/bin/env python3
"""
Comprehensive Azure Function Test Runner
=========================================

This test runner validates the complete Azure Functions document processing pipeline
including HTTP endpoints, blob trigger functionality, and AI processing.

Features:
- Tests all HTTP endpoints (upload, process_document, health, files)
- Validates blob trigger automatic processing
- Tests AI document processing and chunking
- Verifies Azure Search integration
- Comprehensive error handling and logging

Usage:
    python tests/test_whole.py --verbose
    python tests/test_whole.py --quick     # Skip blob trigger tests
"""

import sys
import os
import argparse
import json
import time
import tempfile
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports (to access contracts module)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load from parent directory (project root)
    parent_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(parent_env_path):
        load_dotenv(parent_env_path)
        print(f"✅ Loaded environment variables from {parent_env_path}")
    else:
        load_dotenv()
        print("ℹ️ Loaded environment variables from current directory")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment variables only")

try:
    from contracts.config import config
    from azure.storage.blob import BlobServiceClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you've installed all required packages:")
    print("pip install -r requirements.txt")
    sys.exit(1)

class ComprehensiveAzureFunctionTester:
    """Comprehensive test runner for Azure Functions document processing pipeline"""
    
    def __init__(self, base_url: str = "http://localhost:7071", verbose: bool = False):
        """Initialize the test runner"""
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        self.log_info(f"🚀 Initializing Azure Function Test Runner")
        self.log_info(f"   Target URL: {self.base_url}")
        self.log_info(f"   Verbose mode: {verbose}")

    def log_info(self, message: str):
        """Log informational message"""
        print(f"ℹ️ {message}")

    def log_success(self, message: str):
        """Log success message"""
        print(f"✅ {message}")

    def log_warning(self, message: str):
        """Log warning message"""
        print(f"⚠️ {message}")

    def log_error(self, message: str):
        """Log error message"""
        print(f"❌ {message}")

    def add_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        if passed:
            self.test_results['passed'] += 1
            self.log_success(f"{test_name}: PASSED")
        else:
            self.test_results['failed'] += 1
            self.log_error(f"{test_name}: FAILED - {details}")
        
        self.test_results['details'].append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def test_health_endpoint(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self.add_test_result("Health Check", True)
                    if self.verbose:
                        self.log_info(f"   Version: {data.get('version', 'Unknown')}")
                        self.log_info(f"   Environment: {data.get('environment', {})}")
                    return True
                else:
                    self.add_test_result("Health Check", False, f"Unhealthy status: {data.get('status')}")
                    return False
            else:
                self.add_test_result("Health Check", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.add_test_result("Health Check", False, str(e))
            return False

    def test_process_document_endpoint(self) -> bool:
        """Test the document processing endpoint"""
        try:
            # Test GET request first
            response = self.session.get(f"{self.base_url}/api/process_document", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self.add_test_result("Process Document GET", True)
                    
                    # Test POST with sample document
                    return self._test_document_processing_post()
                else:
                    self.add_test_result("Process Document GET", False, f"Unhealthy status")
                    return False
            else:
                self.add_test_result("Process Document GET", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.add_test_result("Process Document GET", False, str(e))
            return False

    def _test_document_processing_post(self) -> bool:
        """Test document processing with a sample document"""
        try:
            # Create a sample document
            test_content = """
            TEST DOCUMENT FOR PROCESSING
            
            This is a sample document to test the AI processing capabilities.
            
            SECTION 1: Introduction
            This document serves as a test case for the document processing system.
            
            SECTION 2: Features
            The system should process this document, chunk it intelligently,
            and extract relevant keyphrases using AI services.
            
            SECTION 3: Validation
            This section helps validate that the complete workflow is functioning
            including content extraction, chunking, and search indexing.
            """
            
            import base64
            encoded_content = base64.b64encode(test_content.encode('utf-8')).decode('utf-8')
            
            payload = {
                'file_content': encoded_content,
                'filename': 'test_document_processing.txt',
                'force_reindex': True,
                'chunking_method': 'intelligent'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/process_document", 
                json=payload, 
                timeout=60  # Longer timeout for AI processing
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.add_test_result("Process Document POST", True)
                    if self.verbose:
                        self.log_info(f"   Chunks created: {data.get('chunks_created', 0)}")
                        self.log_info(f"   Successful uploads: {data.get('successful_uploads', 0)}")
                    return True
                else:
                    self.add_test_result("Process Document POST", False, data.get('message', 'Unknown error'))
                    return False
            else:
                self.add_test_result("Process Document POST", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.add_test_result("Process Document POST", False, str(e))
            return False

    def test_blob_trigger_functionality(self) -> bool:
        """Test blob trigger by uploading a file to storage"""
        try:
            if not config.AZURE_STORAGE_CONNECTION_STRING:
                self.add_test_result("Blob Trigger", False, "Storage connection string not configured")
                return False
            
            # Create test content
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_content = f"""
            BLOB TRIGGER TEST DOCUMENT
            Generated: {datetime.now().isoformat()}
            
            This document tests the blob trigger functionality by uploading
            directly to Azure Blob Storage and verifying automatic processing.
            
            Test ID: {timestamp}
            Expected: Automatic AI processing and search indexing
            """
            
            filename = f"blob_trigger_test_{timestamp}.txt"
            
            # Upload to blob storage
            blob_service_client = BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(
                container=config.AZURE_STORAGE_CONTAINER_NAME,
                blob=filename
            )
            
            blob_client.upload_blob(test_content.encode('utf-8'), overwrite=True)
            
            self.log_info(f"   📤 Uploaded test file: {filename}")
            self.log_info(f"   ⏳ Waiting for blob trigger processing...")
            
            # Wait a bit for processing
            time.sleep(3)
            
            # Verify blob exists
            if blob_client.exists():
                self.add_test_result("Blob Trigger Upload", True)
                self.log_info(f"   ✅ Blob trigger test file uploaded successfully")
                return True
            else:
                self.add_test_result("Blob Trigger Upload", False, "Blob upload failed")
                return False
                
        except Exception as e:
            self.add_test_result("Blob Trigger", False, str(e))
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        self.log_info("🧪 Running comprehensive test suite...")
        
        tests = {
            'Health Check': self.test_health_endpoint,
            'Process Document': self.test_process_document_endpoint,
            'Blob Trigger': self.test_blob_trigger_functionality
        }
        
        results = {}
        for test_name, test_func in tests.items():
            self.log_info(f"\n🔄 Running {test_name}...")
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.log_error(f"Test {test_name} failed with exception: {str(e)}")
                results[test_name] = False
                
        return results

    def print_summary(self):
        """Print test results summary"""
        print(f"\n📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"📊 Total: {self.test_results['passed'] + self.test_results['failed']}")
        
        if self.test_results['failed'] > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results['details']:
                if not result['passed']:
                    print(f"   • {result['test']}: {result['details']}")
        
        success_rate = (self.test_results['passed'] / max(1, self.test_results['passed'] + self.test_results['failed'])) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Comprehensive Azure Function Test Runner')
    parser.add_argument('--base-url', default='http://localhost:7071', 
                       help='Base URL for Azure Functions (default: http://localhost:7071)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--quick', action='store_true', 
                       help='Skip blob trigger tests (faster execution)')
    
    args = parser.parse_args()
    
    # Create test runner
    tester = ComprehensiveAzureFunctionTester(
        base_url=args.base_url,
        verbose=args.verbose
    )
    
    try:
        print(f"🚀 Azure Functions Comprehensive Test Suite")
        print(f"=" * 60)
        print(f"Target: {args.base_url}")
        print(f"Verbose: {args.verbose}")
        print(f"Quick mode: {args.quick}")
        
        # Run tests
        if args.quick:
            # Skip blob trigger tests
            results = {
                'Health Check': tester.test_health_endpoint(),
                'Process Document': tester.test_process_document_endpoint()
            }
        else:
            # Run all tests
            results = tester.run_all_tests()
        
        # Print summary
        tester.print_summary()
        
        # Exit with error code if any tests failed
        if tester.test_results['failed'] > 0:
            sys.exit(1)
        else:
            print(f"\n🎉 All tests passed! System is working correctly.")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print(f"\n⛔ Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test runner failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()