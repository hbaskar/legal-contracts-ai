# Blob Storage Delete Endpoint for Azure Functions

This document describes how to add a blob deletion endpoint to your Azure Functions for testing EventGrid blob deletion events.

## New Azure Function: Delete Blob File

I'll create a new Azure Function endpoint that can delete files from blob storage containers to help test EventGrid functionality.

### Function Implementation

Add this function to your `function_app.py`:

```python
@app.function_name(name="DeleteBlobFile")
@app.route(route="storage/delete", methods=["DELETE"])
async def delete_blob_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a file from Azure Blob Storage container
    Useful for testing EventGrid blob deletion events
    """
    logger.info('🗑️ Blob deletion function triggered')
    
    try:
        # Get parameters from query string or JSON body
        container_name = req.params.get('container')
        blob_name = req.params.get('blob_name')
        
        if not container_name or not blob_name:
            # Try to get from JSON body
            try:
                req_body = req.get_json()
                container_name = req_body.get('container') if req_body else None
                blob_name = req_body.get('blob_name') if req_body else None
            except:
                pass
        
        if not container_name or not blob_name:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing required parameters",
                    "message": "Both 'container' and 'blob_name' parameters are required",
                    "usage": {
                        "query_string": "DELETE /api/storage/delete?container=uploads&blob_name=file.txt",
                        "json_body": "DELETE /api/storage/delete with JSON: {'container': 'uploads', 'blob_name': 'file.txt'}"
                    }
                }),
                mimetype="application/json",
                status_code=400
            )
        
        # Validate container names
        allowed_containers = ['uploads', 'contract-policies']
        if container_name not in allowed_containers:
            return func.HttpResponse(
                json.dumps({
                    "error": "Invalid container",
                    "message": f"Container must be one of: {allowed_containers}",
                    "provided": container_name
                }),
                mimetype="application/json",
                status_code=400
            )
        
        # Import Azure Storage components
        from azure.storage.blob import BlobServiceClient
        from config.config import config
        
        # Initialize blob service client
        blob_service_client = BlobServiceClient.from_connection_string(
            config.AZURE_STORAGE_CONNECTION_STRING
        )
        
        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Check if blob exists
        try:
            blob_properties = blob_client.get_blob_properties()
            logger.info(f"📄 Found blob: {blob_name} in {container_name} (Size: {blob_properties.size} bytes)")
        except Exception as e:
            if "BlobNotFound" in str(e):
                return func.HttpResponse(
                    json.dumps({
                        "error": "Blob not found",
                        "message": f"Blob '{blob_name}' not found in container '{container_name}'",
                        "container": container_name,
                        "blob_name": blob_name
                    }),
                    mimetype="application/json",
                    status_code=404
                )
            else:
                raise e
        
        # Delete the blob
        delete_result = blob_client.delete_blob()
        
        logger.info(f"✅ Successfully deleted blob: {blob_name} from {container_name}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": f"Successfully deleted blob '{blob_name}' from container '{container_name}'",
                "container": container_name,
                "blob_name": blob_name,
                "deleted_at": datetime.now(UTC).isoformat(),
                "eventgrid_note": "This deletion should trigger EventGrid blob deletion events if configured"
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error deleting blob: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"Failed to delete blob: {str(e)}",
                "container": container_name if 'container_name' in locals() else None,
                "blob_name": blob_name if 'blob_name' in locals() else None,
                "timestamp": datetime.now(UTC).isoformat()
            }),
            mimetype="application/json",
            status_code=500
        )
```

### Postman Request Configuration

#### Request 1: Delete via Query Parameters
- **Method**: DELETE
- **URL**: `{{base_url}}/api/storage/delete?container=contract-policies&blob_name=test-file.txt`
- **Headers**: 
  - `x-functions-key: {{function_key}}` (for Azure deployment)

#### Request 2: Delete via JSON Body
- **Method**: DELETE
- **URL**: `{{base_url}}/api/storage/delete`
- **Headers**: 
  - `Content-Type: application/json`
  - `x-functions-key: {{function_key}}` (for Azure deployment)
- **Body**:
```json
{
  "container": "contract-policies",
  "blob_name": "test-file.txt"
}
```

### Testing EventGrid Workflow

1. **Upload a file** using existing upload endpoints
2. **Verify file exists** in Azure Storage
3. **Delete file** using new delete endpoint
4. **Check EventGrid logs** to see if HandleBlobDeletion function was triggered
5. **Verify search index cleanup** happened automatically

This endpoint will make it easy to test the complete EventGrid blob deletion workflow!