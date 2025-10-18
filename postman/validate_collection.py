#!/usr/bin/env python3
"""
Postman Collection Validation Script

This script validates the updated Postman collection to ensure:
1. All new Azure Search Content Access endpoints are present
2. Proper test scripts are included
3. Collection structure is valid JSON
4. Required variables are defined

Run this after updating the Postman collection to verify integrity.
"""

import json
import sys
from pathlib import Path

def validate_collection():
    """Validate the Postman collection structure and new endpoints."""
    
    collection_path = Path(__file__).parent / "Fresh_Start_Document_Processing.postman_collection.json"
    
    if not collection_path.exists():
        print("❌ ERROR: Collection file not found!")
        return False
    
    try:
        with open(collection_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in collection file: {e}")
        return False
    
    print("🔍 Validating Postman Collection...")
    
    # Check basic structure
    if not collection.get('info', {}).get('name'):
        print("❌ Missing collection name")
        return False
    
    print(f"✅ Collection Name: {collection['info']['name']}")
    
    # Check for Azure Search Content Access section
    azure_search_section = None
    for item in collection.get('item', []):
        if item.get('name') == 'Azure Search Content Access':
            azure_search_section = item
            break
    
    if not azure_search_section:
        print("❌ Missing 'Azure Search Content Access' section")
        return False
    
    print("✅ Found 'Azure Search Content Access' section")
    
    # Check for expected endpoints
    expected_endpoints = [
        "Get All Documents from Search Index",
        "Get Documents with Limit", 
        "Get Documents by Filename",
        "Get Specific Document by ID",
        "Get Documents with Pagination"
    ]
    
    found_endpoints = []
    for endpoint in azure_search_section.get('item', []):
        endpoint_name = endpoint.get('name', '')
        found_endpoints.append(endpoint_name)
        
        # Validate endpoint structure
        request = endpoint.get('request', {})
        if not request.get('url', {}).get('path'):
            print(f"❌ Endpoint '{endpoint_name}' missing URL path")
            return False
            
        # Check for test scripts
        tests = endpoint.get('event', [])
        has_tests = any(event.get('listen') == 'test' for event in tests)
        if not has_tests:
            print(f"⚠️  Warning: Endpoint '{endpoint_name}' missing test scripts")
    
    print(f"✅ Found {len(found_endpoints)} Azure Search endpoints:")
    for endpoint in found_endpoints:
        print(f"   • {endpoint}")
    
    # Check if all expected endpoints are present
    missing_endpoints = set(expected_endpoints) - set(found_endpoints)
    if missing_endpoints:
        print(f"❌ Missing expected endpoints: {missing_endpoints}")
        return False
    
    # Check collection variables
    variables = collection.get('variable', [])
    variable_names = [var.get('key') for var in variables]
    
    required_variables = ['base_url', 'user_id']
    missing_variables = set(required_variables) - set(variable_names)
    
    if missing_variables:
        print(f"❌ Missing required variables: {missing_variables}")
        return False
    
    print(f"✅ Found {len(variables)} collection variables")
    
    # Check description update
    description = collection.get('info', {}).get('description', '')
    if 'Azure Search index content access' not in description:
        print("⚠️  Warning: Collection description may not mention new Azure Search features")
    else:
        print("✅ Collection description mentions Azure Search content access")
    
    print("\n🎉 Collection validation completed successfully!")
    print("\n📋 Summary:")
    print(f"   • Total sections: {len(collection.get('item', []))}")
    print(f"   • Azure Search endpoints: {len(found_endpoints)}")
    print(f"   • Collection variables: {len(variables)}")
    print(f"   • Valid JSON structure: ✅")
    
    return True

def check_api_endpoints():
    """Check if the expected API endpoints exist in the collection."""
    
    collection_path = Path(__file__).parent / "Fresh_Start_Document_Processing.postman_collection.json"
    
    with open(collection_path, 'r', encoding='utf-8') as f:
        collection = json.load(f)
    
    # Extract all URLs from the collection
    urls = []
    
    def extract_urls(items):
        for item in items:
            if 'request' in item:
                url_obj = item['request'].get('url', {})
                if isinstance(url_obj, dict):
                    path = url_obj.get('path', [])
                    if path:
                        urls.append('/' + '/'.join(path))
            elif 'item' in item:
                extract_urls(item['item'])
    
    extract_urls(collection.get('item', []))
    
    print("\n🔗 API Endpoints found in collection:")
    search_endpoints = [url for url in urls if 'search' in url]
    for url in sorted(set(search_endpoints)):
        print(f"   • {url}")
    
    expected_search_endpoint = '/api/search/documents'
    if expected_search_endpoint in urls:
        print(f"✅ Found expected Azure Search endpoint: {expected_search_endpoint}")
    else:
        print(f"❌ Missing expected Azure Search endpoint: {expected_search_endpoint}")
        return False
    
    return True

def main():
    """Main validation function."""
    
    print("🚀 Starting Postman Collection Validation")
    print("=" * 50)
    
    # Validate collection structure
    if not validate_collection():
        print("\n❌ Collection validation failed!")
        sys.exit(1)
    
    # Check API endpoints  
    if not check_api_endpoints():
        print("\n❌ API endpoint validation failed!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 ALL VALIDATIONS PASSED!")
    print("\n📚 Next Steps:")
    print("1. Import the updated collection into Postman")
    print("2. Test the new Azure Search Content Access endpoints")
    print("3. Verify the endpoints return expected data format")
    print("4. Update any custom environments if needed")

if __name__ == "__main__":
    main()