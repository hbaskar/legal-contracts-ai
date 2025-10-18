# Azure Search Index Creation & Management

This document describes the refactored Azure Search index creation functionality that ensures the index exists before any document processing operations.

## Overview

The system now automatically ensures that the Azure Search index exists before attempting to upload documents. This prevents common errors related to missing indexes and provides better error handling and user experience.

## Key Improvements

### 1. **Automatic Index Creation**
- The `process_document_with_ai_keyphrases()` function now automatically checks for index existence
- Creates the index if it doesn't exist before uploading documents
- No manual index setup required for most operations

### 2. **Enhanced Error Handling**
- Validates Azure Search configuration before attempting operations
- Provides detailed error messages for configuration issues
- Graceful fallbacks when index operations fail

### 3. **Comprehensive Index Management**
- Multiple functions for different index management scenarios
- Support for custom index names and force recreation
- Detailed operation logging and status reporting

## Core Functions

### `ensure_search_index_exists(index_name=None)`
**Main function for ensuring index readiness**

```python
from contracts.index_creation import ensure_search_index_exists

result = ensure_search_index_exists()
print(f"Index ready: {result['ready']}")
```

**Returns:**
```json
{
    "status": "created|exists|error",
    "message": "Operation description",
    "index_name": "actual-index-name",
    "operation": "check_existence|create_index|validate_config",
    "ready": true|false
}
```

### `create_document_index_if_not_exists(index_name=None)`
**Creates the document index with full schema**

Features:
- **Vector Search Support**: Configured with HNSW algorithm for embeddings
- **Complete Field Schema**: All required fields for document processing
- **Optimized Configuration**: Proper indexing and filtering settings

```python
from contracts.index_creation import create_document_index_if_not_exists

result = create_document_index_if_not_exists("my-custom-index")
```

**Index Schema Includes:**
- `id` (key field)
- `title`, `paragraph`, `summary` (searchable text)
- `embedding` (vector field for AI search)
- `filename`, `language`, `department` (filterable)
- `keyphrases`, `group` (collections)
- `ParagraphId`, `date` (sortable)
- `isCompliant` (boolean filter)

## Integration with Document Processing

### Automatic Integration
The document processing workflow now includes automatic index creation:

```
1. Document received
2. Content extracted and chunked
3. → INDEX EXISTENCE CHECK ← (NEW)
4. → CREATE INDEX IF NEEDED ← (NEW)
5. AI processing and enhancement
6. Upload to Azure Search
7. Save to local database
```

### Process Function Enhancement
The `process_document_with_ai_keyphrases()` function includes:

```python
# Step 4: Ensure Azure Search index exists before uploading
logger.info("🔍 Ensuring Azure Search index exists...")
try:
    from contracts.index_creation import create_document_index_if_not_exists
    index_result = create_document_index_if_not_exists()
    if index_result["status"] in ["created", "exists"]:
        logger.info(f"✅ Index ready: {index_result['message']}")
    else:
        return {"status": "error", "message": f"Failed to create/verify Azure Search index"}
except Exception as e:
    return {"status": "error", "message": f"Failed to verify Azure Search index: {str(e)}"}
```

### Search Client Enhancement
The `get_search_client()` function now includes index verification:

```python
def get_search_client():
    """Initialize Search client lazily and ensure index exists"""
    global search_client
    if search_client is None:
        # ... initialize client ...
        
        # Ensure the index exists when initializing the client
        try:
            from contracts.index_creation import create_document_index_if_not_exists
            index_result = create_document_index_if_not_exists()
            logger.info(f"🏗️ Index status: {index_result['message']}")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify index existence: {str(e)}")
    
    return search_client
```

## API Endpoints

### 1. Setup Index Endpoint
**POST** `/api/search/setup`

Creates or verifies the Azure Search index.

**Parameters:**
- `force_recreate` (boolean): Delete and recreate index
- `index_name` (string): Custom index name (optional)

**Examples:**
```bash
# Basic setup
curl -X POST "http://localhost:7071/api/search/setup"

# Force recreation
curl -X POST "http://localhost:7071/api/search/setup?force_recreate=true"

# Custom index name
curl -X POST "http://localhost:7071/api/search/setup" \
  -H "Content-Type: application/json" \
  -d '{"index_name": "my-custom-index"}'
```

**Response:**
```json
{
    "status": "created",
    "message": "Successfully created index 'legal-documents'",
    "index_name": "legal-documents",
    "operation": "create_index",
    "fields_count": 16,
    "ready": true,
    "force_recreate": false,
    "timestamp": "2024-01-20T10:30:00Z"
}
```

## Configuration Requirements

### Environment Variables
Ensure these are configured in your `.env` file:

```env
# Azure Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-admin-key
AZURE_SEARCH_INDEX=legal-documents

# Azure OpenAI for embeddings
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

### Validation
The system validates configuration before attempting operations:

```python
if not config.AZURE_SEARCH_ENDPOINT:
    return {"status": "error", "message": "AZURE_SEARCH_ENDPOINT not configured"}

if not config.AZURE_SEARCH_KEY:
    return {"status": "error", "message": "AZURE_SEARCH_KEY not configured"}
```

## Error Handling and Troubleshooting

### Common Scenarios

1. **Index Already Exists**
   ```json
   {
       "status": "exists",
       "message": "Index 'legal-documents' already exists",
       "ready": true
   }
   ```

2. **Configuration Missing**
   ```json
   {
       "status": "error",
       "message": "AZURE_SEARCH_ENDPOINT not configured",
       "operation": "validate_config"
   }
   ```

3. **Index Creation Success**
   ```json
   {
       "status": "created",
       "message": "Successfully created index 'legal-documents'",
       "fields_count": 16,
       "ready": true
   }
   ```

### Troubleshooting Steps

1. **Check Configuration**
   ```bash
   # Test service health
   curl http://localhost:7071/api/health
   
   # Check process function status
   curl http://localhost:7071/api/process_document
   ```

2. **Verify Index Setup**
   ```bash
   # Test index setup
   curl -X POST http://localhost:7071/api/search/setup
   ```

3. **Test Document Processing**
   ```bash
   # Process a test document
   python test_index_creation.py
   ```

## Testing

### Automated Tests
Use the comprehensive test script:

```bash
python test_index_creation.py
```

**Tests Include:**
- Service health verification
- Index setup endpoint testing
- Force recreation functionality
- Document processing with automatic index creation
- Search functionality verification

### Manual Testing with Postman
The Postman collection includes:
- **Setup Azure Search Index** - Basic index creation
- **Force Recreate Azure Search Index** - Full recreation
- **Setup Custom Index** - Custom index names

## Best Practices

### 1. **Let Automation Handle It**
- Don't manually create indexes unless necessary
- The document processing function handles index creation automatically
- Use the setup endpoint only for troubleshooting or initial setup

### 2. **Monitor Index Operations**
- Check function logs for index creation messages
- Verify successful index operations in responses
- Use health check endpoint to validate service status

### 3. **Handle Errors Gracefully**
- Always check `ready` field in responses
- Validate configuration before processing documents
- Use force recreation sparingly (only for schema changes)

### 4. **Development Workflow**
```bash
# 1. Start the service
func start

# 2. Verify health
curl http://localhost:7071/api/health

# 3. Process a document (index created automatically)
# Use Postman "Process Document with AI" request

# 4. Verify documents in index
curl http://localhost:7071/api/search/documents?limit=5
```

## Migration Notes

### For Existing Deployments
- Existing indexes will continue to work
- No breaking changes to existing functionality
- Index creation is now automatic and transparent
- Manual index setup is still available if needed

### Upgrading
1. Deploy the new code
2. Existing indexes remain functional
3. New document processing automatically verifies index existence
4. No manual intervention required

## Performance Considerations

- Index existence check is cached with the search client
- Index creation is a one-time operation per deployment
- Minimal overhead added to document processing
- Force recreation should be used sparingly in production

This refactored approach ensures robust, automatic index management while maintaining flexibility for custom scenarios and troubleshooting.