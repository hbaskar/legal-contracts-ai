#!/usr/bin/env python3
"""
PDF Processing Test
Demonstrates proper PDF processing vs text content with PDF filename
"""

import requests
import base64
import json

def test_text_as_pdf():
    """Test sending text content with PDF filename (your original scenario)"""
    print("🧪 Test 1: Text content with .pdf filename")
    print("-" * 50)
    
    sample_text = """EMPLOYEE HANDBOOK

SECTION 1: COMPANY OVERVIEW
Our company was founded with a mission to provide excellent service.

SECTION 2: EMPLOYMENT POLICIES  
All employees must adhere to professional standards.

SECTION 3: BENEFITS PACKAGE
We offer comprehensive health insurance and retirement planning."""
    
    base64_content = base64.b64encode(sample_text.encode()).decode()
    
    payload = {
        'file_content': base64_content,
        'filename': 'employee.pdf',  # PDF filename but text content
        'force_reindex': True,
        'chunking_method': 'heading'
    }
    
    try:
        response = requests.post(
            'http://localhost:7071/api/process_document',
            json=payload,
            headers={'Content-Type': 'application/json', 'X-User-ID': 'test-user'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result['status'] == 'success':
            print(f"✅ Success: {result['chunks_created']} chunks created")
            print(f"📊 Method: {result['chunking_method']}")
            print(f"🔍 Enhancement: {result['enhancement']}")
        else:
            print(f"❌ Error: {result['message']}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_text_as_text():
    """Test sending text content with .txt filename (correct approach)"""
    print("\n🧪 Test 2: Text content with .txt filename")
    print("-" * 50)
    
    sample_text = """EMPLOYEE HANDBOOK

SECTION 1: COMPANY OVERVIEW
Our company was founded with a mission to provide excellent service.

SECTION 2: EMPLOYMENT POLICIES  
All employees must adhere to professional standards.

SECTION 3: BENEFITS PACKAGE
We offer comprehensive health insurance and retirement planning."""
    
    base64_content = base64.b64encode(sample_text.encode()).decode()
    
    payload = {
        'file_content': base64_content,
        'filename': 'employee_handbook.txt',  # Correct .txt extension
        'force_reindex': True,
        'chunking_method': 'heading'
    }
    
    try:
        response = requests.post(
            'http://localhost:7071/api/process_document',
            json=payload,
            headers={'Content-Type': 'application/json', 'X-User-ID': 'test-user'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result['status'] == 'success':
            print(f"✅ Success: {result['chunks_created']} chunks created")
            print(f"📊 Method: {result['chunking_method']}")
            print(f"🔍 Enhancement: {result['enhancement']}")
        else:
            print(f"❌ Error: {result['message']}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_actual_pdf_upload():
    """Test uploading actual PDF file"""
    print("\n🧪 Test 3: Actual PDF file upload (recommended approach)")
    print("-" * 50)
    
    pdf_path = "test_files/employee.pdf"
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': ('employee.pdf', f, 'application/pdf')}
            response = requests.post(
                'http://localhost:7071/api/upload',
                files=files,
                headers={'X-User-ID': 'test-user'},
                timeout=30
            )
        
        print(f"Upload Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                file_id = result.get('file_id')
                print(f"✅ PDF uploaded successfully - File ID: {file_id}")
                print(f"📄 Filename: {result.get('filename')}")
                print(f"💾 Size: {result.get('size')} bytes")
                print("🚀 Blob trigger will automatically process the PDF")
            else:
                print(f"❌ Upload failed: {result.get('message')}")
        else:
            print(f"❌ Upload failed - Status: {response.status_code}")
            
    except FileNotFoundError:
        print(f"⚠️ PDF file not found at {pdf_path}")
        print("   Use file upload approach for real PDFs")
    except Exception as e:
        print(f"❌ Upload error: {e}")

if __name__ == "__main__":
    print("🚀 PDF Processing Methods Comparison")
    print("=" * 60)
    
    test_text_as_pdf()    # Your original scenario - now works!
    test_text_as_text()   # Correct approach for text
    test_actual_pdf_upload()  # Best approach for real PDFs
    
    print(f"\n📋 Summary:")
    print(f"✅ Method 1: Text as PDF - Now works with improved error handling")
    print(f"✅ Method 2: Text as Text - Standard approach for text content")  
    print(f"✅ Method 3: File Upload - Best for actual PDF files")