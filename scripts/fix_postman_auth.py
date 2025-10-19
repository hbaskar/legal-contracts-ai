#!/usr/bin/env python3
"""
Script to add proper Azure Function authentication to the Postman collection
"""

import json
import os

def fix_postman_authentication():
    """Add proper authentication to all requests in the Postman collection"""
    
    collection_path = './postman/Fresh_Start_Document_Processing.postman_collection.json'
    
    # Load existing collection
    with open(collection_path, 'r') as f:
        collection = json.load(f)
    
    def add_auth_to_request(request):
        """Add authentication to a single request"""
        if 'url' in request:
            # Method 1: Add code parameter to URL
            url = request['url']
            if isinstance(url, dict) and 'raw' in url:
                raw_url = url['raw']
                # Only add auth if not already present and not health endpoint
                if '?code=' not in raw_url and '/api/health' not in raw_url:
                    separator = '&' if '?' in raw_url else '?'
                    url['raw'] = f"{raw_url}{separator}code={{{{function_key}}}}"
                    
                    # Also add to query parameters if they exist
                    if 'query' not in url:
                        url['query'] = []
                    
                    # Check if code parameter already exists
                    code_exists = any(param.get('key') == 'code' for param in url['query'])
                    if not code_exists:
                        url['query'].append({
                            "key": "code",
                            "value": "{{function_key}}",
                            "description": "Azure Function access key"
                        })
    
    def process_items(items):
        """Recursively process all items in the collection"""
        for item in items:
            if 'request' in item:
                add_auth_to_request(item['request'])
            elif 'item' in item:
                # This is a folder, process its items
                process_items(item['item'])
    
    # Process all items in the collection
    if 'item' in collection:
        process_items(collection['item'])
    
    # Update collection info
    collection['info']['description'] = collection['info']['description'].replace(
        'Includes admin functions for database and search index management.',
        'Includes admin functions for database and search index management. All protected endpoints include Azure Function authentication via function keys.'
    )
    
    # Save updated collection
    with open(collection_path, 'w') as f:
        json.dump(collection, f, indent=2)
    
    print("✅ Fixed Azure Function authentication in Postman collection")
    print("🔐 Added function key authentication to all protected endpoints")
    print("🏥 Health endpoint remains anonymous (no authentication needed)")
    print("📋 Authentication method: Query parameter ?code={{function_key}}")
    print("")
    print("🔄 To use:")
    print("1. Re-import the updated collection into Postman")
    print("2. Make sure your Azure Production environment has the function_key set")
    print("3. All requests will automatically include authentication")

if __name__ == "__main__":
    fix_postman_authentication()