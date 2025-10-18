#!/usr/bin/env python3
"""
Script to add deletion endpoints to the existing Postman collection
"""

import json

# New admin functions to add to the Postman collection
admin_functions = {
    "name": "Admin Functions",
    "item": [
        {
            "name": "Database Reset",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 207\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 207]);",
                            "});",
                            "",
                            "pm.test(\"Response has status field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('status');",
                            "});",
                            "",
                            "pm.test(\"Reset operation completed\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.be.oneOf(['success', 'partial_success']);",
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
                    "raw": "{\n    \"confirm\": \"yes\"\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/database/reset",
                    "host": [
                        "{{base_url}}"
                    ],
                    "path": [
                        "api",
                        "database",
                        "reset"
                    ]
                }
            },
            "response": []
        },
        {
            "name": "Azure Search Index Reset",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 207\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 207]);",
                            "});",
                            "",
                            "pm.test(\"Response has status field\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('status');",
                            "});",
                            "",
                            "pm.test(\"Search reset completed\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.be.oneOf(['success', 'partial_success']);",
                            "});",
                            "",
                            "pm.test(\"Documents deleted count present\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData).to.have.property('deleted_documents');",
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
                    "raw": "{\n    \"confirm\": \"yes\"\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/search/reset",
                    "host": [
                        "{{base_url}}"
                    ],
                    "path": [
                        "api",
                        "search",
                        "reset"
                    ]
                }
            },
            "response": []
        },
        {
            "name": "Database Reset (Force)",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 207\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 207]);",
                            "});",
                            "",
                            "pm.test(\"Force reset completed\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.be.oneOf(['success', 'partial_success']);",
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
                    "raw": "{\n    \"force\": true\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/database/reset?force=true",
                    "host": [
                        "{{base_url}}"
                    ],
                    "path": [
                        "api",
                        "database",
                        "reset"
                    ],
                    "query": [
                        {
                            "key": "force",
                            "value": "true"
                        }
                    ]
                }
            },
            "response": []
        },
        {
            "name": "Azure Search Index Reset (Force)",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "pm.test(\"Status code is 200 or 207\", function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 207]);",
                            "});",
                            "",
                            "pm.test(\"Force search reset completed\", function () {",
                            "    const jsonData = pm.response.json();",
                            "    pm.expect(jsonData.status).to.be.oneOf(['success', 'partial_success']);",
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
                    "raw": "{\n    \"force\": true\n}"
                },
                "url": {
                    "raw": "{{base_url}}/api/search/reset?force=true",
                    "host": [
                        "{{base_url}}"
                    ],
                    "path": [
                        "api",
                        "search",
                        "reset"
                    ],
                    "query": [
                        {
                            "key": "force",
                            "value": "true"
                        }
                    ]
                }
            },
            "response": []
        }
    ]
}

def add_admin_functions_to_postman():
    """Add admin functions to the existing Postman collection"""
    
    # Load existing collection
    with open('./postman/Fresh_Start_Document_Processing.postman_collection.json', 'r') as f:
        collection = json.load(f)
    
    # Add admin functions section
    collection['item'].append(admin_functions)
    
    # Update collection info
    collection['info']['description'] += " Includes admin functions for database and search index management."
    
    # Save updated collection
    with open('./postman/Fresh_Start_Document_Processing.postman_collection.json', 'w') as f:
        json.dump(collection, f, indent=2)
    
    print("✅ Added Admin Functions to Postman collection")
    print("📋 New endpoints added:")
    print("   - Database Reset (POST)")
    print("   - Azure Search Index Reset (POST)")
    print("   - Database Reset Force (DELETE)")
    print("   - Azure Search Index Reset Force (DELETE)")

if __name__ == "__main__":
    add_admin_functions_to_postman()