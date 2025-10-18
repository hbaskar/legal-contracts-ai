#!/usr/bin/env python3
"""
Script to add document deletion endpoints to the existing Postman collection
"""

import json

# Document deletion endpoints to add to the Postman collection
deletion_endpoints = {
    "name": "Document Deletion",
    "item": [
        {
            "name": "Delete Document by ID",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 404\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 404]);",
                            "});",
                            "",
                            "pm.test(\"Response has message field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('message');",
                            "});",
                            "",
                            "if (pm.response.code === 200) {",
                            "    pm.test(\"Successful deletion has chunk count\", function () {",
                            "        const jsonData = pm.response.json();",
                            "        pm.expect(jsonData).to.have.property('deleted_chunks');",
                            "    });",
                            "}"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "DELETE",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/api/search/delete/document?document_id={{document_id}}",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "delete", "document"],
                    "query": [
                        {
                            "key": "document_id",
                            "value": "{{document_id}}",
                            "description": "The specific document ID to delete"
                        }
                    ]
                }
            }
        },
        {
            "name": "Delete Document by Filename",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 404\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 404]);",
                            "});",
                            "",
                            "pm.test(\"Response has message field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('message');",
                            "});",
                            "",
                            "if (pm.response.code === 200) {",
                            "    pm.test(\"Successful deletion has chunk count\", function () {",
                            "        const jsonData = pm.response.json();",
                            "        pm.expect(jsonData).to.have.property('deleted_chunks');",
                            "    });",
                            "}"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "DELETE",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/api/search/delete/document?filename={{filename}}",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "delete", "document"],
                    "query": [
                        {
                            "key": "filename",
                            "value": "{{filename}}",
                            "description": "The filename to delete (all chunks)"
                        }
                    ]
                }
            }
        },
        {
            "name": "Batch Delete Documents",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200\", function () {",
                            "    pm.response.to.have.status(200);",
                            "});",
                            "",
                            "pm.test(\"Response has message field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('message');",
                            "});",
                            "",
                            "pm.test(\"Response has batch operation fields\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('deleted_chunks');",
                            "    pm.expect(jsonData).to.have.property('requested_count');",
                            "    pm.expect(jsonData).to.have.property('found_count');",
                            "});"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "DELETE",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"document_ids\": [\n        \"{{document_id_1}}\",\n        \"{{document_id_2}}\",\n        \"{{document_id_3}}\"\n    ]\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/search/delete/document",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "delete", "document"]
                }
            }
        },
        {
            "name": "Delete Persisted Chunk by ID",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 404\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 404]);",
                            "});",
                            "",
                            "pm.test(\"Response has message field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('message');",
                            "});",
                            "",
                            "if (pm.response.code === 200) {",
                            "    pm.test(\"Successful deletion has count\", function () {",
                            "        const jsonData = pm.response.json();",
                            "        pm.expect(jsonData).to.have.property('deleted_count');",
                            "    });",
                            "}"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "DELETE",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/api/search/delete/document/persisted?document_id={{document_id}}&confirm=yes",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "delete", "document", "persisted"],
                    "query": [
                        {
                            "key": "document_id",
                            "value": "{{document_id}}",
                            "description": "The specific document ID to delete from database"
                        },
                        {
                            "key": "confirm",
                            "value": "yes",
                            "description": "Required confirmation for deletion"
                        }
                    ]
                }
            }
        },
        {
            "name": "Delete Persisted Chunks by Filename",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 404\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 404]);",
                            "});",
                            "",
                            "pm.test(\"Response has message field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('message');",
                            "});",
                            "",
                            "if (pm.response.code === 200) {",
                            "    pm.test(\"Successful deletion has count\", function () {",
                            "        const jsonData = pm.response.json();",
                            "        pm.expect(jsonData).to.have.property('deleted_count');",
                            "    });",
                            "}"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "DELETE",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/api/search/delete/document/persisted?filename={{filename}}&confirm=yes",
                    "host": ["{{base_url}}"],
                    "path": ["api", "search", "delete", "document", "persisted"],
                    "query": [
                        {
                            "key": "filename",
                            "value": "{{filename}}",
                            "description": "The filename to delete from database (all chunks)"
                        },
                        {
                            "key": "confirm",
                            "value": "yes",
                            "description": "Required confirmation for deletion"
                        }
                    ]
                }
            }
        }
    ]
}

def update_postman_collection():
    """Add document deletion endpoints to the Postman collection"""
    
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
    
    # Check if deletion endpoints already exist
    existing_folders = [item.get('name', '') for item in collection.get('item', [])]
    if "Document Deletion" in existing_folders:
        print("⚠️  Document Deletion folder already exists, updating...")
        # Remove existing folder
        collection['item'] = [item for item in collection['item'] if item.get('name') != "Document Deletion"]
    
    # Add the deletion endpoints
    collection['item'].append(deletion_endpoints)
    
    # Save the updated collection
    try:
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        print("✅ Added Document Deletion endpoints to Postman collection")
        print("📋 New endpoints added:")
        for endpoint in deletion_endpoints['item']:
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
    
    print("\n🎯 Document Deletion Endpoints Summary:")
    print("✅ Delete Document by ID - Remove specific document from index")
    print("✅ Delete Document by Filename - Remove all chunks for a filename")  
    print("✅ Batch Delete Documents - Delete multiple documents at once")
    print("✅ Delete Persisted Chunk by ID - Remove from database")
    print("✅ Delete Persisted Chunks by Filename - Remove all persisted chunks for filename")
    
    print("\n📝 Usage Notes:")
    print("• Use environment variables for document_id and filename")
    print("• Persisted deletion requires confirm=yes parameter")
    print("• Batch deletion uses JSON body with document_ids array")
    print("• All endpoints return detailed operation results")