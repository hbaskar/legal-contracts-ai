#!/usr/bin/env python3
"""
Script to add index management endpoints to the Postman collection
"""

import json

# Index management endpoints to add to the Postman collection
index_management_endpoints = {
    "name": "Index Management",
    "item": [
        {
            "name": "Setup Azure Search Index",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 201\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
                            "});",
                            "",
                            "pm.test(\"Response has status field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('status');",
                            "});",
                            "",
                            "pm.test(\"Index setup completed\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.be.oneOf(['created', 'exists']);",
                            "});",
                            "",
                            "pm.test(\"Response has index details\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('index_name');",
                            "    pm.expect(jsonData).to.have.property('ready');",
                            "});"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"force_recreate\": false\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/search/setup",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "setup"]
                }
            }
        },
        {
            "name": "Force Recreate Azure Search Index",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 201\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
                            "});",
                            "",
                            "pm.test(\"Response has status field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('status');",
                            "});",
                            "",
                            "pm.test(\"Index recreation completed\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.equal('created');",
                            "});",
                            "",
                            "pm.test(\"Force recreate was used\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.force_recreate).to.equal(true);",
                            "});"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"force_recreate\": true\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/search/setup?force_recreate=true",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "setup"],
                    "query": [
                        {
                            "key": "force_recreate",
                            "value": "true",
                            "description": "Force recreation of the index"
                        }
                    ]
                }
            }
        },
        {
            "name": "Setup Custom Index",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 201\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
                            "});",
                            "",
                            "pm.test(\"Response has status field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('status');",
                            "});",
                            "",
                            "pm.test(\"Custom index created\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.be.oneOf(['created', 'exists']);",
                            "    pm.expect(jsonData.index_name).to.equal('custom-test-index');",
                            "});"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"index_name\": \"custom-test-index\",\n    \"force_recreate\": false\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/search/setup?index_name=custom-test-index",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "setup"],
                    "query": [
                        {
                            "key": "index_name",
                            "value": "custom-test-index",
                            "description": "Custom index name"
                        }
                    ]
                }
            }
        }
    ]
}

def update_postman_collection():
    """Add index management endpoints to the Postman collection"""
    
    # Read the existing collection
    collection_path = "postman/Fresh_Start_Document_Processing.postman_collection.json"
    
    try:
        with open(collection_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)
    except FileNotFoundError:
        print(f"❌ Collection file not found: {collection_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse collection JSON: {e}")
        return False
    
    # Check if index management endpoints already exist
    existing_folders = [item.get('name', '') for item in collection.get('item', [])]
    if "Index Management" in existing_folders:
        print("⚠️ Index Management folder already exists, updating...")
        # Remove existing folder
        collection['item'] = [item for item in collection['item'] if item.get('name') != "Index Management"]
    
    # Add the index management endpoints
    collection['item'].append(index_management_endpoints)
    
    # Save the updated collection
    try:
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        print("✅ Added Index Management endpoints to Postman collection")
        print("📋 New endpoints added:")
        for endpoint in index_management_endpoints['item']:
            method = endpoint['request']['method']
            name = endpoint['name']
            print(f"   - {name} ({method})")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save collection: {e}")
        return False

if __name__ == "__main__":
    success = update_postman_collection()
    if not success:
        exit(1)
    
    print("\n🎯 Index Management Endpoints Summary:")
    print("✅ Setup Azure Search Index - Create/verify the default index")
    print("✅ Force Recreate Azure Search Index - Delete and recreate index")  
    print("✅ Setup Custom Index - Create index with custom name")
    
    print("\n📝 Usage Notes:")
    print("• Setup endpoints ensure index exists before document processing")
    print("• Force recreate is useful for schema changes or troubleshooting")
    print("• Custom index allows testing with different index names")
    print("• All endpoints return detailed operation results and status")
    print("• Index creation is now automatic during document processing")