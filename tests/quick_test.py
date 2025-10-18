#!/usr/bin/env python3
"""
Quick test script for Azure Function file upload

This is a simplified version for quick testing.
Run: python quick_test.py
"""

import requests
import json
import os
import tempfile
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:7071"
UPLOAD_URL = f"{BASE_URL}/api/upload"
HEALTH_URL = f"{BASE_URL}/api/health"
FILES_URL = f"{BASE_URL}/api/files"

def create_sample_file():
    """Create a sample file for testing"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Hello from Azure Function test!\n")
        f.write("This is a sample file for upload testing.\n")
        f.write("Timestamp: 2024-12-17\n")
        f.write("Content: Sample data for testing file upload functionality.\n")
        return f.name

def test_health():
    """Test the health endpoint"""
    print("🩺 Testing health check...")
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data.get('status')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def upload_file(file_path):
    """Upload a file"""
    print(f"📤 Uploading file: {Path(file_path).name}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f, 'text/plain')}
            headers = {'X-User-ID': 'test-user'}
            
            response = requests.post(UPLOAD_URL, files=files, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Upload successful!")
            print(f"   File ID: {data.get('file_id')}")
            print(f"   Size: {data.get('file_size')} bytes")
            print(f"   Blob URL: {data.get('blob_url', 'N/A')}")
            return data.get('file_id')
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def get_file_info(file_id):
    """Get file information"""
    print(f"📋 Getting file info for ID: {file_id}")
    
    try:
        params = {'download_url': 'true', 'expiry_hours': '24'}
        response = requests.get(f"{FILES_URL}/{file_id}", params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ File info retrieved!")
            print(f"   Filename: {data.get('filename')}")
            print(f"   Original: {data.get('original_filename')}")
            print(f"   Upload time: {data.get('upload_timestamp')}")
            if 'download_url' in data:
                print(f"   Download URL available: Yes")
            return True
        else:
            print(f"❌ Failed to get file info: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ File info error: {e}")
        return False

def main():
    """Run the quick test"""
    print("🚀 Quick Azure Function Upload Test")
    print("=" * 40)
    
    # Test health
    if not test_health():
        print("\n❌ Health check failed - make sure the function is running")
        print("   Run: func start")
        return
    
    # Create sample file
    sample_file = create_sample_file()
    print(f"📁 Created sample file: {sample_file}")
    
    try:
        # Upload file
        file_id = upload_file(sample_file)
        
        if file_id:
            # Get file info
            get_file_info(file_id)
            print(f"\n🎉 Test completed successfully!")
        else:
            print(f"\n❌ Test failed during upload")
            
    finally:
        # Clean up
        if os.path.exists(sample_file):
            os.unlink(sample_file)
            print(f"🧹 Cleaned up sample file")

if __name__ == "__main__":
    main()