# Postman Requests for Blob Storage Delete Testing

## Option 1: Import these requests into your existing collection

### Request 1: Delete Blob via Query Parameters

```json
{
  "name": "Delete Blob File (Query Params)",
  "request": {
    "method": "DELETE",
    "header": [
      {
        "key": "x-functions-key",
        "value": "{{function_key}}",
        "type": "text",
        "description": "Required for Azure deployment"
      }
    ],
    "url": {
      "raw": "{{base_url}}/api/storage/delete?container={{test_container}}&blob_name={{test_blob_name}}",
      "host": ["{{base_url}}"],
      "path": ["api", "storage", "delete"],
      "query": [
        {
          "key": "container",
          "value": "{{test_container}}",
          "description": "Container name (uploads or contract-policies)"
        },
        {
          "key": "blob_name",
          "value": "{{test_blob_name}}",
          "description": "Name of the blob to delete"
        }
      ]
    }
  },
  "response": []
}
```

### Request 2: Delete Blob via JSON Body

```json
{
  "name": "Delete Blob File (JSON Body)",
  "request": {
    "method": "DELETE",
    "header": [
      {
        "key": "Content-Type",
        "value": "application/json",
        "type": "text"
      },
      {
        "key": "x-functions-key",
        "value": "{{function_key}}",
        "type": "text",
        "description": "Required for Azure deployment"
      }
    ],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"container\": \"{{test_container}}\",\n  \"blob_name\": \"{{test_blob_name}}\"\n}",
      "options": {
        "raw": {
          "language": "json"
        }
      }
    },
    "url": {
      "raw": "{{base_url}}/api/storage/delete",
      "host": ["{{base_url}}"],
      "path": ["api", "storage", "delete"]
    }
  },
  "response": []
}
```

## Option 2: Manual Testing Commands

### For Local Testing (Functions running on localhost:7071):

```bash
# Test 1: Query parameters
curl -X DELETE "http://localhost:7071/api/storage/delete?container=contract-policies&blob_name=test-file.txt"

# Test 2: JSON body
curl -X DELETE \
  -H "Content-Type: application/json" \
  -d '{"container":"contract-policies","blob_name":"test-file.txt"}' \
  "http://localhost:7071/api/storage/delete"
```

### For Azure Testing:

```bash
# Test 1: Query parameters
curl -X DELETE \
  -H "x-functions-key: YOUR_FUNCTION_KEY" \
  "https://aifnc.azurewebsites.net/api/storage/delete?container=contract-policies&blob_name=test-file.txt"

# Test 2: JSON body
curl -X DELETE \
  -H "x-functions-key: YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"container":"contract-policies","blob_name":"test-file.txt"}' \
  "https://aifnc.azurewebsites.net/api/storage/delete"
```

## Testing EventGrid Workflow

### Step 1: Upload a Test File
```bash
az storage blob upload \
  --file "test_policy_document.txt" \
  --container-name "contract-policies" \
  --name "eventgrid-test.txt" \
  --connection-string "YOUR_CONNECTION_STRING"
```

### Step 2: Verify File Exists
```bash
az storage blob list \
  --container-name "contract-policies" \
  --connection-string "YOUR_CONNECTION_STRING" \
  --output table
```

### Step 3: Delete File via API (triggers EventGrid)
Use the Postman requests above or curl commands

### Step 4: Check EventGrid Logs
- Go to Azure Portal → Function App → HandleBlobDeletion → Monitor
- Look for logs showing "🗑️ EventGrid blob event"

### Step 5: Verify Search Index Cleanup
```bash
# Search for policies that should have been deleted
curl "https://aifnc.azurewebsites.net/api/search/policies?search_text=eventgrid-test"
```

## Environment Variables to Add

Add these to your Postman environment for easy testing:

```json
{
  "key": "test_container",
  "value": "contract-policies",
  "description": "Container for testing blob operations"
},
{
  "key": "test_blob_name", 
  "value": "eventgrid-test.txt",
  "description": "Blob name for testing deletion"
}
```

## Expected Responses

### Success Response:
```json
{
  "status": "success",
  "message": "Successfully deleted blob 'test-file.txt' from container 'contract-policies'",
  "container": "contract-policies",
  "blob_name": "test-file.txt",
  "deleted_at": "2025-10-21T03:00:40.339537+00:00",
  "eventgrid_note": "This deletion should trigger EventGrid blob deletion events if configured"
}
```

### Error Response (Blob Not Found):
```json
{
  "error": "Blob not found",
  "message": "Blob 'test-file.txt' not found in container 'contract-policies'",
  "container": "contract-policies",
  "blob_name": "test-file.txt"
}
```

This endpoint makes it easy to test EventGrid blob deletion events without needing to manually navigate Azure Storage Explorer!