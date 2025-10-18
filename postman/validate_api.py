#!/usr/bin/env python3
"""
Postman Collection Validator
Quick validation script to test API endpoints before using Postman collection
"""

import requests
import json
import base64
import time
from datetime import datetime

class APIValidator:
    """Validate Fresh Start API endpoints"""
    
    def __init__(self, base_url="http://localhost:7071"):
        self.base_url = base_url.rstrip('/')
        self.headers = {'X-User-ID': 'validator-user'}
        
    def test_health(self):
        """Test health endpoint"""
        print("🏥 Testing Health Endpoint...")
        try:
            response = requests.get(f"{self.base_url}/api/health", headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Health check passed - Status: {data.get('status')}")
                return True
            else:
                print(f"   ❌ Health check failed - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False
    
    def test_document_processing_health(self):
        """Test document processing health"""
        print("🧠 Testing Document Processing Health...")
        try:
            response = requests.get(f"{self.base_url}/api/process_document", headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                ai_available = data.get('ai_services_available', False)
                print(f"   ✅ Processing endpoint healthy - AI Services: {'Available' if ai_available else 'Unavailable'}")
                return True
            else:
                print(f"   ❌ Processing health failed - Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Processing health error: {e}")
            return False
    
    def test_file_upload(self):
        """Test file upload with sample content"""
        print("📁 Testing File Upload...")
        try:
            # Create sample file content
            sample_content = b"""EMPLOYEE HANDBOOK

SECTION 1: COMPANY OVERVIEW
Our company values integrity and innovation.

SECTION 2: POLICIES  
All employees must follow guidelines.

SECTION 3: BENEFITS
Health insurance and retirement plans available."""
            
            files = {'file': ('test_document.txt', sample_content, 'text/plain')}
            response = requests.post(f"{self.base_url}/api/upload", files=files, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    file_id = data.get('file_id')
                    print(f"   ✅ File upload successful - File ID: {file_id}")
                    print(f"   📄 Filename: {data.get('filename')}, Size: {data.get('size')} bytes")
                    return file_id
                else:
                    print(f"   ❌ Upload failed: {data.get('message')}")
                    return None
            else:
                print(f"   ❌ Upload failed - Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
            return None
    
    def test_document_processing(self):
        """Test document processing with base64 content"""
        print("🔄 Testing Document Processing...")
        
        # Create sample document
        sample_doc = """EMPLOYEE HANDBOOK

SECTION 1: COMPANY OVERVIEW
Our company was founded with a mission to provide excellent service.

Mission Statement  
To deliver value through innovation and collaboration.

SECTION 2: EMPLOYMENT POLICIES
All employees must adhere to professional standards.

Code of Conduct
Respectful communication and punctuality are required.

SECTION 3: BENEFITS PACKAGE
Comprehensive health insurance and retirement planning available."""
        
        # Test different chunking methods
        methods = [
            ("intelligent", "🧠 Intelligent AI"),
            ("heading", "📋 Heading-based"),  
            ("fixed", "📏 Fixed-size"),
            ("paragraph", "📝 Paragraph")
        ]
        
        results = {}
        
        for method, description in methods:
            print(f"   Testing {description} chunking...")
            try:
                base64_content = base64.b64encode(sample_doc.encode()).decode()
                
                payload = {
                    "file_content": base64_content,
                    "filename": f"test_document_{method}.txt",
                    "force_reindex": True,
                    "chunking_method": method
                }
                
                response = requests.post(
                    f"{self.base_url}/api/process_document", 
                    json=payload, 
                    headers={**self.headers, 'Content-Type': 'application/json'}, 
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        chunks_created = data.get('chunks_created', 0)
                        processing_time = data.get('processing_time_ms', 0)
                        print(f"      ✅ {chunks_created} chunks created in {processing_time}ms")
                        results[method] = {
                            'success': True,
                            'chunks': chunks_created,
                            'time': processing_time
                        }
                    else:
                        print(f"      ❌ Processing failed: {data.get('message')}")
                        results[method] = {'success': False, 'error': data.get('message')}
                else:
                    print(f"      ❌ Request failed - Status: {response.status_code}")
                    results[method] = {'success': False, 'error': f"HTTP {response.status_code}"}
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
                results[method] = {'success': False, 'error': str(e)}
        
        return results
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        print("🚨 Testing Error Handling...")
        
        # Test upload without file
        print("   Testing upload without file...")
        try:
            response = requests.post(f"{self.base_url}/api/upload", headers=self.headers, timeout=10)
            if response.status_code == 400:
                print("      ✅ Correctly rejected upload without file")
            else:
                print(f"      ⚠️ Unexpected response: {response.status_code}")
        except Exception as e:
            print(f"      ❌ Error testing upload: {e}")
        
        # Test processing without content
        print("   Testing processing without file content...")
        try:
            payload = {"filename": "test.txt"}
            response = requests.post(
                f"{self.base_url}/api/process_document", 
                json=payload, 
                headers={**self.headers, 'Content-Type': 'application/json'}, 
                timeout=10
            )
            if response.status_code == 400:
                print("      ✅ Correctly rejected processing without content")
            else:
                print(f"      ⚠️ Unexpected response: {response.status_code}")
        except Exception as e:
            print(f"      ❌ Error testing processing: {e}")
    
    def run_full_validation(self):
        """Run complete API validation"""
        print("🚀 Fresh Start API Validation")
        print("=" * 50)
        
        # Basic health checks
        health_ok = self.test_health()
        processing_health_ok = self.test_document_processing_health()
        
        if not health_ok:
            print("❌ Basic health checks failed. Check if Azure Functions is running.")
            return False
        
        # File operations
        file_id = self.test_file_upload()
        
        # Document processing
        processing_results = self.test_document_processing()
        
        # Error handling
        self.test_error_handling()
        
        # Summary
        print("\n📊 Validation Summary")
        print("=" * 30)
        print(f"✅ Health Check: {'Pass' if health_ok else 'Fail'}")
        print(f"✅ Processing Health: {'Pass' if processing_health_ok else 'Fail'}")
        print(f"✅ File Upload: {'Pass' if file_id else 'Fail'}")
        
        successful_methods = sum(1 for result in processing_results.values() if result.get('success'))
        print(f"✅ Document Processing: {successful_methods}/4 methods successful")
        
        for method, result in processing_results.items():
            status = "✅" if result.get('success') else "❌"
            if result.get('success'):
                print(f"   {status} {method.upper()}: {result.get('chunks', 0)} chunks, {result.get('time', 0)}ms")
            else:
                print(f"   {status} {method.upper()}: {result.get('error', 'Unknown error')}")
        
        print(f"\n🎉 API Validation {'Complete' if health_ok and file_id else 'Failed'}")
        print("📚 Your Postman collection is ready to use!")
        
        return health_ok and file_id and successful_methods > 0

if __name__ == "__main__":
    validator = APIValidator()
    validator.run_full_validation()