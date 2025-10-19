#!/usr/bin/env python3
"""
Test script for the Azure Function file upload service
This script demonstrates how to test the function endpoints locally
"""

import requests
import json
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:7071/api"
TEST_FILE_PATH = "test_file.txt"


def create_test_file():
    """Create a test file for upload"""
    test_content = "This is a test file for Azure Function upload service.\nCreated for testing purposes."
    with open(TEST_FILE_PATH, 'w') as f:
        f.write(test_content)
    print(f"Created test file: {TEST_FILE_PATH}")


def test_health_check():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Health check failed: {e}")
        return False


def test_file_upload():
    """Test file upload endpoint"""
    print("\n=== Testing File Upload ===")
    
    if not os.path.exists(TEST_FILE_PATH):
        create_test_file()
    
    try:
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': (TEST_FILE_PATH, f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload Response: {json.dumps(result, indent=2)}")
            return result.get('id')
        else:
            print(f"Upload failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Upload test failed: {e}")
        return None


def test_get_file_info(file_id):
    """Test get file info endpoint"""
    print(f"\n=== Testing Get File Info (ID: {file_id}) ===")
    
    if file_id is None:
        print("No file ID provided, skipping test")
        return
    
    try:
        # Test without download URL
        response = requests.get(f"{BASE_URL}/files/{file_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Test with download URL
        print(f"\n--- Testing with download URL ---")
        response = requests.get(f"{BASE_URL}/files/{file_id}?download_url=true&expiry_hours=1")
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if 'download_url' in result:
            print(f"\nGenerated download URL: {result['download_url']}")
        
    except requests.exceptions.RequestException as e:
        print(f"Get file info test failed: {e}")


def cleanup():
    """Clean up test files"""
    if os.path.exists(TEST_FILE_PATH):
        os.remove(TEST_FILE_PATH)
        print(f"\nCleaned up test file: {TEST_FILE_PATH}")


def main():
    """Run all tests"""
    print("Azure Function File Upload Service - Test Suite")
    print("=" * 50)
    
    # Check if function is running
    health_ok = test_health_check()
    if not health_ok:
        print("\n❌ Health check failed. Make sure the Azure Function is running locally.")
        print("Run: func start")
        return
    
    # Test file upload
    file_id = test_file_upload()
    
    # Test file info retrieval
    if file_id:
        test_get_file_info(file_id)
        print(f"\n✅ All tests completed successfully!")
        print(f"File ID for further testing: {file_id}")
    else:
        print(f"\n❌ File upload failed, skipping file info test")
    
    # Cleanup
    cleanup()


if __name__ == "__main__":
    main()
