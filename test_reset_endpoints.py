#!/usr/bin/env python3
"""
Test script for separate reset operations
- Database reset
- Azure Search index reset
"""

import requests
import json

def test_database_reset():
    """Test the database reset endpoint"""
    print("🗑️ Testing Database Reset")
    print("=" * 40)
    
    response = requests.post('http://localhost:7071/api/database/reset', json={
        'confirm': 'yes'
    }, headers={'Content-Type': 'application/json'})
    
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 207]:
        result = response.json()
        print(f"✅ Status: {result.get('status')}")
        print(f"📋 Message: {result.get('message')}")
        print(f"📊 Tables Reset: {result.get('summary', {}).get('tables_processed', 0)}")
        print(f"🗑️ Records Deleted: {result.get('total_records_deleted', 0)}")
        if result.get('errors'):
            print(f"⚠️ Errors: {result.get('errors')}")
    else:
        print(f"❌ Error: {response.text}")
    
    print()

def test_search_index_reset():
    """Test the Azure Search index reset endpoint"""
    print("☁️ Testing Azure Search Index Reset")
    print("=" * 40)
    
    response = requests.post('http://localhost:7071/api/search/reset', json={
        'confirm': 'yes'
    }, headers={'Content-Type': 'application/json'})
    
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 207]:
        result = response.json()
        print(f"✅ Status: {result.get('status')}")
        print(f"📋 Message: {result.get('message')}")
        print(f"🗑️ Documents Deleted: {result.get('deleted_documents', 0)}")
        print(f"📊 Total Found: {result.get('total_found', 0)}")
        if result.get('failed_deletions', 0) > 0:
            print(f"⚠️ Failed Deletions: {result.get('failed_deletions')}")
    else:
        print(f"❌ Error: {response.text}")
    
    print()

def test_health_check():
    """Test health check to verify service is running"""
    print("🏥 Testing Health Check")
    print("=" * 40)
    
    response = requests.get('http://localhost:7071/api/health')
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Service Status: {result.get('status')}")
        print(f"📋 Environment: {result.get('environment', {}).get('database_type', 'unknown')}")
    else:
        print(f"❌ Service not available: {response.text}")
    
    print()

if __name__ == "__main__":
    print("🧪 Testing Separate Reset Functions")
    print("=" * 50)
    
    # Test health first
    test_health_check()
    
    # Test database reset
    test_database_reset()
    
    # Test search index reset
    test_search_index_reset()
    
    print("🎯 Reset Tests Complete!")
    print()
    print("💡 Usage Examples:")
    print("   Database Reset: POST /api/database/reset")
    print("   Search Reset: POST /api/search/reset")
    print("   Both require: {'confirm': 'yes'} in request body")
    print("   Or use query param: ?confirm=yes")
    print("   Force flag: {'force': true} bypasses confirmations")