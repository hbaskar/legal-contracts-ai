# Document Deletion API Reference

This guide describes the comprehensive document deletion capabilities available in the Fresh Start Document Processing system.

## Overview

The system provides multiple ways to delete documents from both the Azure Search index and the local database:

- **Azure Search Index Deletion**: Removes documents from the searchable index
- **Persisted Database Deletion**: Removes chunk data from the local database
- **Single Document Deletion**: Delete specific documents by ID
- **Filename-based Deletion**: Delete all chunks associated with a filename
- **Batch Deletion**: Delete multiple documents in a single operation

## API Endpoints

### 1. Delete Document from Azure Search Index

**Endpoint**: `DELETE /api/search/delete/document`

This endpoint provides three deletion modes:

#### Mode 1: Delete by Document ID
```http
DELETE /api/search/delete/document?document_id={document_id}
```

**Parameters**:
- `document_id` (string, required): The specific document ID to delete

**Example**:
```bash
curl -X DELETE "http://localhost:7071/api/search/delete/document?document_id=doc_12345"
```

#### Mode 2: Delete by Filename
```http
DELETE /api/search/delete/document?filename={filename}
```

**Parameters**:
- `filename` (string, required): The filename to delete (removes all chunks)

**Example**:
```bash
curl -X DELETE "http://localhost:7071/api/search/delete/document?filename=sample.pdf"
```

#### Mode 3: Batch Delete Multiple Documents
```http
DELETE /api/search/delete/document
Content-Type: application/json

{
    "document_ids": ["doc_1", "doc_2", "doc_3"]
}
```

**Request Body**:
- `document_ids` (array, required): List of document IDs to delete

**Example**:
```bash
curl -X DELETE "http://localhost:7071/api/search/delete/document" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["doc_1", "doc_2", "doc_3"]}'
```

### 2. Delete Persisted Chunks from Database

**Endpoint**: `DELETE /api/search/delete/document/persisted`

This endpoint removes chunk data from the local database.

#### Delete by Document ID
```http
DELETE /api/search/delete/document/persisted?document_id={document_id}&confirm=yes
```

#### Delete by Filename
```http
DELETE /api/search/delete/document/persisted?filename={filename}&confirm=yes
```

**Parameters**:
- `document_id` (string): The specific document ID to delete
- `filename` (string): The filename to delete (all associated chunks)
- `confirm` (string, required): Must be "yes" for safety confirmation

**Examples**:
```bash
# Delete by document ID
curl -X DELETE "http://localhost:7071/api/search/delete/document/persisted?document_id=doc_12345&confirm=yes"

# Delete by filename
curl -X DELETE "http://localhost:7071/api/search/delete/document/persisted?filename=sample.pdf&confirm=yes"
```

## Response Formats

### Successful Deletion (Azure Search)
```json
{
    "message": "Successfully deleted 5 chunks for document doc_12345",
    "deleted_chunks": 5,
    "document_id": "doc_12345",
    "operation": "delete_document"
}
```

### Batch Deletion Response
```json
{
    "message": "Batch deletion completed: 15 chunks deleted for 3 documents",
    "deleted_chunks": 15,
    "requested_count": 3,
    "found_count": 3,
    "failed_deletions": 0,
    "operation": "batch_delete"
}
```

### Successful Deletion (Persisted Database)
```json
{
    "message": "Successfully deleted 5 persisted chunks for document doc_12345",
    "deleted_count": 5,
    "document_id": "doc_12345",
    "operation": "delete_persisted"
}
```

### Document Not Found
```json
{
    "error": "Document not found",
    "message": "No document found with ID: doc_12345",
    "document_id": "doc_12345",
    "operation": "delete_document"
}
```

### Error Response
```json
{
    "error": "Bad Request",
    "message": "Must provide either document_id, filename, or document_ids in request body",
    "operation": "delete_document"
}
```

## Status Codes

- **200 OK**: Successful deletion
- **400 Bad Request**: Invalid parameters or missing required fields
- **404 Not Found**: Document(s) not found
- **500 Internal Server Error**: Server error during deletion

## Usage Examples

### Python Examples

```python
import requests

BASE_URL = "http://localhost:7071"

# Delete single document by ID
response = requests.delete(f"{BASE_URL}/api/search/delete/document?document_id=doc_12345")
print(response.json())

# Delete all chunks for a filename
response = requests.delete(f"{BASE_URL}/api/search/delete/document?filename=sample.pdf")
print(response.json())

# Batch delete multiple documents
payload = {"document_ids": ["doc_1", "doc_2", "doc_3"]}
response = requests.delete(f"{BASE_URL}/api/search/delete/document", json=payload)
print(response.json())

# Delete persisted chunks
response = requests.delete(
    f"{BASE_URL}/api/search/delete/document/persisted?document_id=doc_12345&confirm=yes"
)
print(response.json())
```

### PowerShell Examples

```powershell
# Delete single document
$response = Invoke-RestMethod -Uri "http://localhost:7071/api/search/delete/document?document_id=doc_12345" -Method Delete
$response

# Delete by filename
$response = Invoke-RestMethod -Uri "http://localhost:7071/api/search/delete/document?filename=sample.pdf" -Method Delete
$response

# Batch delete
$body = @{
    document_ids = @("doc_1", "doc_2", "doc_3")
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:7071/api/search/delete/document" -Method Delete -Body $body -ContentType "application/json"
$response
```

## Safety Features

### Confirmation Requirement
- Persisted database deletions require `confirm=yes` parameter
- Prevents accidental data loss from local database

### Validation
- Document IDs and filenames are validated before deletion
- Batch operations validate all document IDs in the request
- Empty or invalid requests are rejected with appropriate error messages

### Error Handling
- Detailed error messages for debugging
- Graceful handling of non-existent documents
- Partial success reporting for batch operations

## Best Practices

### When to Use Each Method

1. **Delete by Document ID**: When you need to remove a specific document
2. **Delete by Filename**: When you want to remove all versions/chunks of a file
3. **Batch Delete**: When cleaning up multiple documents efficiently
4. **Persisted Database Deletion**: When you need to clean up local database storage

### Workflow Recommendations

1. **Check Before Delete**: Use search endpoints to verify documents exist
2. **Azure Search First**: Delete from Azure Search index before database cleanup
3. **Backup Strategy**: Consider backing up important data before deletion
4. **Monitor Results**: Check response messages and counts for validation

### Performance Considerations

- Batch deletions are more efficient than multiple single deletions
- Large batch operations may take longer to complete
- Database deletions are typically faster than Azure Search deletions
- Consider pagination for very large deletion operations

## Testing

Use the provided test script to validate deletion functionality:

```bash
python test_document_deletion.py
```

This script tests all deletion methods and validates proper error handling.

## Integration

### Postman Collection
The Postman collection includes pre-configured requests for all deletion methods:
- Delete Document by ID
- Delete Document by Filename  
- Batch Delete Documents
- Delete Persisted Chunk by ID
- Delete Persisted Chunks by Filename

### Environment Variables
Configure these Postman environment variables:
- `document_id`: Sample document ID for testing
- `filename`: Sample filename for testing
- `document_id_1`, `document_id_2`, `document_id_3`: For batch testing

## Troubleshooting

### Common Issues

1. **404 Not Found**: Document doesn't exist in the index
2. **400 Bad Request**: Missing required parameters
3. **Missing Confirmation**: Forgot `confirm=yes` for persisted deletions
4. **JSON Format**: Invalid JSON in batch delete requests

### Debug Steps

1. Verify document exists using search endpoints
2. Check parameter spelling and formatting
3. Validate JSON structure for batch operations
4. Review server logs for detailed error information

## Security Considerations

- Deletion operations are irreversible
- No authentication required in current implementation
- Consider adding authorization for production use
- Monitor deletion activities for audit purposes