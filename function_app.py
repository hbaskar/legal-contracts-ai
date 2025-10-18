"""
Azure Functions App for File Upload Service

This function provides endpoints for:
1. Uploading files to Azure Blob Storage
2. Storing file metadata in Azure SQL or SQLite
3. Retrieving file information and download URLs

Features:
- Supports both Azure SQL (production) and SQLite (local development)
- Uses managed identity for secure Azure resource access
- Implements proper error handling and logging
- Generates secure SAS URLs for file downloads
- Calculates file checksums for integrity verification

Project Structure:
- contracts/: Core business logic and data contracts
  - models.py: Data models and DTOs
  - database.py: Database operations layer
  - storage.py: Blob storage operations layer
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, UTC
from typing import Optional
import asyncio

# Import our custom modules
from contracts.config import config
from contracts.database import DatabaseManager
from contracts.storage import BlobStorageManager
from contracts.models import FileMetadata, UploadResponse


# Initialize the Function App with v2 programming model
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Configure logging
log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Validate configuration on startup
if not config.validate_config():
    logger.warning("Configuration validation failed. Some features may not work correctly.")
else:
    logger.info("Configuration validation passed")

# Initialize managers (will be done lazily)
db_manager: Optional[DatabaseManager] = None
storage_manager: Optional[BlobStorageManager] = None


async def get_db_manager() -> DatabaseManager:
    """Get or initialize database manager"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        await db_manager.initialize()
    return db_manager


async def get_storage_manager() -> BlobStorageManager:
    """Get or initialize storage manager"""
    global storage_manager
    if storage_manager is None:
        storage_manager = BlobStorageManager()
        await storage_manager.ensure_container_exists()
    return storage_manager


@app.function_name(name="UploadFile")
@app.route(route="upload", methods=["POST"])
async def upload_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Upload file endpoint
    
    Accepts multipart form data with file upload
    Returns JSON response with upload status and file metadata
    """
    try:
        logger.info("Processing file upload request")
        
        # Parse multipart form data
        if not req.files:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "No file provided in request",
                    "error_details": "Request must contain a file in multipart form data"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get the uploaded file
        file = req.files.get('file')
        if not file:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "File parameter is required",
                    "error_details": "Expected 'file' parameter in form data"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate file
        if not file.filename:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "File must have a filename",
                    "error_details": "Uploaded file does not have a valid filename"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        # Validate file size using configuration
        max_file_size = config.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_file_size:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB",
                    "error_details": f"File size: {file_size} bytes"
                }),
                status_code=413,
                mimetype="application/json"
            )
        
        if file_size == 0:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "File is empty",
                    "error_details": "Uploaded file has no content"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get managers
        storage_mgr = await get_storage_manager()
        db_mgr = await get_db_manager()
        
        # Upload to blob storage
        blob_url, blob_name = await storage_mgr.upload_file(
            file_content,
            file.filename,
            file.content_type or 'application/octet-stream'
        )
        
        # Calculate checksum
        checksum = storage_mgr.calculate_file_hash(file_content)
        
        # Create metadata object
        metadata = FileMetadata(
            filename=blob_name,
            original_filename=file.filename,
            file_size=file_size,
            content_type=file.content_type or 'application/octet-stream',
            blob_url=blob_url,
            container_name=storage_mgr.container_name,
            upload_timestamp=datetime.now(UTC),
            checksum=checksum,
            user_id=req.headers.get('X-User-ID')  # Optional user identification
        )
        
        # Save metadata to database
        record_id = await db_mgr.save_file_metadata(metadata)
        metadata.id = record_id
        
        # Create response
        response = UploadResponse(
            success=True,
            message="File uploaded successfully",
            file_metadata=metadata
        )
        
        logger.info(f"Successfully uploaded file: {file.filename} (ID: {record_id})")
        
        # Return the file metadata with additional response fields
        response_data = metadata.to_dict()
        response_data.update({
            "success": response.success,
            "message": response.message,
            "file_id": record_id  # Explicit file_id for backwards compatibility
        })
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        
        error_response = UploadResponse(
            success=False,
            message="Failed to upload file",
            error_details=str(e)
        )
        
        return func.HttpResponse(
            json.dumps({
                "success": error_response.success,
                "message": error_response.message,
                "error_details": error_response.error_details
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="GetFileInfo")
@app.route(route="files/{file_id}", methods=["GET"])
async def get_file_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get file information endpoint
    
    Returns file metadata and optionally generates a secure download URL
    """
    try:
        file_id = req.route_params.get('file_id')
        if not file_id:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "File ID is required"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        try:
            file_id = int(file_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "Invalid file ID format"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get database manager
        db_mgr = await get_db_manager()
        
        # Retrieve file metadata
        metadata = await db_mgr.get_file_metadata(file_id)
        
        if not metadata:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "File not found"
                }),
                status_code=404,
                mimetype="application/json"
            )
        
        # Check if download URL is requested
        include_download_url = req.params.get('download_url', 'false').lower() == 'true'
        
        response_data = metadata.to_dict()
        
        if include_download_url:
            # Generate SAS URL for secure download
            storage_mgr = await get_storage_manager()
            expiry_hours = int(req.params.get('expiry_hours', config.DEFAULT_SAS_EXPIRY_HOURS))
            
            download_url = await storage_mgr.get_file_url_with_sas(
                metadata.filename,
                expiry_hours
            )
            
            if download_url:
                response_data['download_url'] = download_url
                response_data['download_expires_in_hours'] = expiry_hours
            else:
                response_data['download_url_error'] = "Failed to generate download URL"
        
        logger.info(f"Retrieved file info for ID: {file_id}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving file info: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": "Failed to retrieve file information",
                "error_details": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="HealthCheck")
@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint
    
    Returns the health status of the service and its dependencies
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "1.0.0",
            "environment": config.get_environment_info(),
            "checks": {}
        }
        
        # Check database connectivity
        try:
            db_mgr = await get_db_manager()
            health_status["checks"]["database"] = {
                "status": "healthy",
                "type": db_mgr.db_type
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check blob storage connectivity
        try:
            storage_mgr = await get_storage_manager()
            health_status["checks"]["blob_storage"] = {
                "status": "healthy",
                "container": storage_mgr.container_name
            }
        except Exception as e:
            health_status["checks"]["blob_storage"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return func.HttpResponse(
            json.dumps(health_status),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e)
            }),
            status_code=503,
            mimetype="application/json"
        )


# Example of a blob trigger function using v2 model (commented out for now)
# Blob trigger for automatic document processing with AI services
@app.function_name(name="ProcessUploadedDocument")
@app.blob_trigger(
    arg_name="myblob",
    path="uploads/{name}",
    connection="AZURE_STORAGE_CONNECTION_STRING"
)
async def process_uploaded_document(myblob: func.InputStream) -> None:
    """
    Automatically process documents when uploaded to blob storage
    Uses AI services to extract content, chunk intelligently, and index to Azure Search
    """
    import tempfile
    import os
    
    try:
        blob_name = myblob.name
        logger.info(f'🚀 Blob trigger processing: {blob_name}')
        
        # Read the blob content first
        blob_content = myblob.read()
        blob_size = len(blob_content)
        
        logger.info(f'� Processing blob: {blob_name}, Size: {blob_size} bytes')
        
        # Extract filename from blob path (remove container path if present)
        filename = os.path.basename(blob_name)
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Check if this is a supported document type
        supported_extensions = ['txt', 'docx', 'pdf']
        if file_extension not in supported_extensions:
            logger.info(f"⏭️ Skipping unsupported file type: {file_extension} for {filename}")
            return
        
        # Check if AI services are available
        try:
            from contracts.ai_services import process_document_with_ai_keyphrases
            logger.info("✅ AI services available for document processing")
        except ImportError as e:
            logger.warning(f"⚠️ AI services not available: {e}")
            return
        
        # Create temporary file with the blob content
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            # Write the blob content we already read to temp file
            temp_file.write(blob_content)
            temp_file_path = temp_file.name
        
        try:
            logger.info(f"📄 Processing document with AI services: {filename}")
            
            # Process the document with AI services
            # Use config default chunking method for automatic processing
            result = await process_document_with_ai_keyphrases(
                file_path=temp_file_path,
                filename=filename,
                force_reindex=True,  # Always reindex to avoid duplicates
                chunking_method=None  # Use config default from environment
            )
            
            if result["status"] == "success":
                logger.info(f"✅ Successfully processed {filename}")
                logger.info(f"   📊 Created {result['chunks_created']} chunks")
                logger.info(f"   ☁️ Uploaded {result['successful_uploads']} to search index")
                logger.info(f"   🧠 Method: {result['chunking_method']}")
                logger.info(f"   🎯 Enhancement: {result['enhancement']}")
                
                # Log first few chunk titles for monitoring
                chunk_details = result.get('chunk_details', [])
                for i, chunk in enumerate(chunk_details[:3]):  # Show first 3
                    logger.info(f"   📝 Chunk {i+1}: '{chunk['title']}' ({chunk['content_size']} chars)")
                
                if result.get('failed_uploads', 0) > 0:
                    logger.warning(f"⚠️ {result['failed_uploads']} chunks failed to upload")
                    
            else:
                logger.error(f"❌ Failed to process {filename}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Error during AI processing of {filename}: {str(e)}")
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
                logger.debug(f"🧹 Cleaned up temporary file for {filename}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")
        
    except Exception as e:
        logger.error(f"❌ Blob trigger error for {myblob.name}: {str(e)}")
        # Don't re-raise to avoid infinite retries


@app.function_name(name="ProcessDocumentFunction")
@app.route(route="process_document", methods=["GET", "POST"])
async def process_document_function(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function HTTP endpoint for document processing with AI capabilities"""
    logger.info('🚀 Document processing HTTP function triggered')
    
    try:
        # Import here to avoid startup issues if AI services aren't available
        try:
            from contracts.ai_services import process_document_with_ai_keyphrases
            AI_SERVICES_AVAILABLE = True
        except ImportError as e:
            AI_SERVICES_AVAILABLE = False
            logger.warning(f"AI services not available: {e}")
        
        method = req.method.upper()
        
        if method == 'GET':
            # Health check or status endpoint
            return func.HttpResponse(
                json.dumps({
                    "status": "healthy",
                    "message": "Document Processing Function is running",
                    "version": "1.0.0",
                    "ai_services_available": AI_SERVICES_AVAILABLE,
                    "environment": config.get_environment_info()
                }),
                mimetype="application/json",
                status_code=200
            )
        
        elif method == 'POST':
            if not AI_SERVICES_AVAILABLE:
                return func.HttpResponse(
                    json.dumps({
                        "error": "AI services not available. Please check OpenAI and Search service configuration."
                    }),
                    mimetype="application/json",
                    status_code=503
                )
            
            # Process document request
            try:
                req_body = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON in request body"}),
                    mimetype="application/json",
                    status_code=400
                )
            
            if not req_body:
                return func.HttpResponse(
                    json.dumps({"error": "Request body is required"}),
                    mimetype="application/json",
                    status_code=400
                )
            
            # Extract parameters
            file_content = req_body.get('file_content')  # Base64 encoded file
            filename = req_body.get('filename')
            force_reindex = req_body.get('force_reindex', False)
            chunking_method = req_body.get('chunking_method')  # Use None to let ai_services use config default
            
            if not file_content or not filename:
                return func.HttpResponse(
                    json.dumps({
                        "error": "Both 'file_content' (base64 encoded) and 'filename' are required"
                    }),
                    mimetype="application/json",
                    status_code=400
                )
            
            # Validate file extension
            file_extension = filename.lower().split('.')[-1]
            if file_extension not in ['txt', 'docx', 'pdf']:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Unsupported file type: {file_extension}. Supported types: txt, docx, pdf"
                    }),
                    mimetype="application/json",
                    status_code=400
                )
            
            # Decode file content and save to temporary file
            import tempfile
            import base64
            try:
                file_data = base64.b64decode(file_content)
            except Exception as e:
                return func.HttpResponse(
                    json.dumps({"error": f"Invalid base64 file content: {str(e)}"}),
                    mimetype="application/json",
                    status_code=400
                )
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            try:
                # Process the document using AI services (now async)
                result = await process_document_with_ai_keyphrases(
                    file_path=temp_file_path,
                    filename=filename,
                    force_reindex=force_reindex,
                    chunking_method=chunking_method
                )
                
                return func.HttpResponse(
                    json.dumps(result),
                    mimetype="application/json",
                    status_code=200 if result["status"] == "success" else 500
                )
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
        
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {method} not allowed"}),
                mimetype="application/json",
                status_code=405
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in document processing function: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"Internal server error: {str(e)}"
            }),
            mimetype="application/json",
            status_code=500
        )


@app.function_name(name="ResetDatabase")
@app.route(route="database/reset", methods=["POST", "DELETE"])
async def reset_database(req: func.HttpRequest) -> func.HttpResponse:
    """
    Reset database tables - ADMIN FUNCTION
    
    Clears all data from the database tables for testing purposes.
    Use with caution - this will delete ALL data!
    """
    try:
        logger.info('🗑️ Database reset function triggered')
        
        # Security check - require confirmation parameter
        confirmation = req.params.get('confirm', '').lower()
        force_reset = req.params.get('force', '').lower() == 'true'
        
        # Check for confirmation in JSON body for POST requests
        if req.method == 'POST':
            try:
                req_body = req.get_json()
                if req_body:
                    confirmation = req_body.get('confirm', confirmation).lower()
                    force_reset = req_body.get('force', force_reset)
            except:
                pass
        
        # Require explicit confirmation
        if confirmation != 'yes' and not force_reset:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Database reset requires confirmation",
                    "instructions": "Add '?confirm=yes' parameter or set 'confirm': 'yes' in request body",
                    "warning": "This will delete ALL data from database tables"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get environment - extra safety for production
        environment = config.get_environment_info().get('environment', 'unknown').lower()
        
        if environment == 'production' and not force_reset:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Database reset is not allowed in production environment",
                    "environment": environment,
                    "instructions": "Use 'force=true' parameter only if absolutely necessary"
                }),
                status_code=403,
                mimetype="application/json"
            )
        
        # Initialize database manager
        db_mgr = await get_db_manager()
        
        # Use the DatabaseManager's built-in reset functionality
        logger.info("🗑️ Starting database reset operation")
        reset_results = await db_mgr.reset_all_tables()
        
        # Add metadata to response
        response_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": environment,
            "status": "success" if reset_results["summary"]["tables_with_errors"] == 0 else "partial_success",
            "message": "Database reset completed successfully" if reset_results["summary"]["tables_with_errors"] == 0 else f"Database reset completed with {reset_results['summary']['tables_with_errors']} errors",
            "tables_reset": reset_results["tables_reset"],
            "errors": reset_results["tables_with_errors"],
            "total_records_deleted": reset_results["total_records_deleted"],
            "summary": reset_results["summary"]
        }
        
        # Determine status code
        status_code = 200 if reset_results["summary"]["tables_with_errors"] == 0 else 207
        
        logger.info(f"🎉 Database reset completed: {response_data['summary']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Database reset failed",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="ResetAzureSearchIndex")
@app.route(route="search/reset", methods=["POST", "DELETE"])
async def reset_search_index(req: func.HttpRequest) -> func.HttpResponse:
    """
    Reset Azure Search index - Delete all documents from the search index
    ADMIN FUNCTION - Use with caution
    """
    
    logger.info('🗑️ Azure Search index reset function triggered')
    
    try:
        # Parse request parameters
        confirmation = req.params.get('confirm', '').lower()
        force_reset = req.params.get('force', '').lower() == 'true'
        
        # Try to get JSON body for additional parameters
        try:
            req_body = req.get_json()
            if req_body:
                confirmation = req_body.get('confirm', confirmation).lower()
                force_reset = req_body.get('force', force_reset)
        except ValueError:
            pass  # No JSON body or invalid JSON
        
        # Require confirmation unless force flag is set
        if confirmation != 'yes' and not force_reset:
            return func.HttpResponse(
                json.dumps({
                    "status": "confirmation_required",
                    "message": "Azure Search index reset requires confirmation",
                    "required_parameters": "confirm=yes OR force=true",
                    "warning": "This will delete ALL documents from the search index"
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get environment info to check if this is production
        environment = config.get_environment_info().get('database_type', 'unknown')
        
        # Extra protection for production (requires force flag)
        if environment == 'azuresql' and not force_reset:
            return func.HttpResponse(
                json.dumps({
                    "status": "protection_error",
                    "message": "Azure Search index reset requires force=true in production environment",
                    "environment": environment
                }),
                status_code=403,
                mimetype="application/json"
            )
        
        # Import and execute the reset function
        try:
            from contracts.ai_services import reset_azure_search_index
            SEARCH_SERVICES_AVAILABLE = True
        except ImportError as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Search services not available",
                    "error": str(e)
                }),
                status_code=503,
                mimetype="application/json"
            )
        
        # Execute the reset
        logger.info("🗑️ Starting Azure Search index reset operation")
        reset_results = reset_azure_search_index()
        
        # Prepare response
        response_data = {
            "status": reset_results["status"],
            "message": reset_results["message"],
            "deleted_documents": reset_results.get("deleted_documents", 0),
            "failed_deletions": reset_results.get("failed_deletions", 0),
            "total_found": reset_results.get("total_found", 0),
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": "azure_search_index_reset"
        }
        
        # Determine status code
        if reset_results["status"] == "success":
            status_code = 200
        elif reset_results["status"] == "partial_success":
            status_code = 207  # Multi-status
        else:
            status_code = 500
        
        logger.info(f"🎉 Azure Search index reset completed: {response_data['message']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Azure Search index reset failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Azure Search index reset failed",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="GetAzureSearchDocuments")
@app.route(route="search/documents", methods=["GET"])
async def get_azure_search_documents_function(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get documents directly from Azure Search index with their actual content
    Query parameters:
    - filename: Filter by specific filename
    - document_id: Get specific document by ID
    - limit: Limit number of results (default: 50)
    """
    
    logger.info('� Azure Search documents retrieval function triggered')
    
    try:
        # Parse query parameters
        filename = req.params.get('filename')
        document_id = req.params.get('document_id')
        limit = int(req.params.get('limit', '50'))
        
        # Validate limit
        if limit <= 0 or limit > 1000:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Invalid limit parameter. Must be between 1 and 1000."
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Check if search services are available
        try:
            from contracts.ai_services import get_documents_from_azure_search_index
            SEARCH_SERVICES_AVAILABLE = True
        except ImportError as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Search services not available",
                    "error": str(e)
                }),
                status_code=503,
                mimetype="application/json"
            )
        
        # Retrieve documents directly from Azure Search index
        logger.info(f"📊 Retrieving documents from Azure Search (filename={filename}, document_id={document_id}, limit={limit})")
        
        result = get_documents_from_azure_search_index(
            filename=filename,
            document_id=document_id,
            limit=limit
        )
        
        if result["status"] != "success":
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": result["message"],
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Prepare response data
        response_data = {
            "status": "success",
            "message": result["message"],
            "documents": result["documents"],
            "total_documents": result["total_documents"],
            "filters": result["filters"],
            "index_name": result["index_name"],
            "source": "azure_search_index",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ Successfully retrieved {len(result['documents'])} documents from Azure Search index")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve Azure Search documents: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Failed to retrieve Azure Search documents",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="search/chunks/persisted", methods=["GET"])
async def get_persisted_azure_search_chunks(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get Azure Search chunks with persisted paragraph data from local database
    
    Query Parameters:
    - filename: Filter by filename
    - document_id: Get specific document by search document ID
    - limit: Limit number of results (default: no limit)
    
    Returns JSON with persisted paragraph data from azure_search_chunks table
    """
    try:
        # Get query parameters
        filename = req.params.get('filename')
        document_id = req.params.get('document_id')
        limit_str = req.params.get('limit')
        limit = int(limit_str) if limit_str and limit_str.isdigit() else None
        
        logger.info(f"📊 Retrieving persisted Azure Search chunks (filename={filename}, document_id={document_id}, limit={limit})")
        
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        # Get persisted chunks from database
        chunks = await db_mgr.get_azure_search_chunks_persisted(
            filename=filename,
            search_document_id=document_id,
            limit=limit
        )
        
        # Prepare response data  
        response_data = {
            "status": "success",
            "message": f"Retrieved {len(chunks)} persisted Azure Search chunks from database",
            "documents": chunks,
            "total_documents": len(chunks),
            "filters": {
                "filename": filename,
                "document_id": document_id,
                "limit": limit
            },
            "source": "azure_search_chunks_table",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ Successfully retrieved {len(chunks)} persisted Azure Search chunks from database")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve persisted Azure Search chunks: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Failed to retrieve persisted Azure Search chunks",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="search/delete/document", methods=["DELETE"])
async def delete_specific_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a specific document from Azure Search index by document ID or filename
    
    Query Parameters:
    - document_id: Delete specific document by ID
    - filename: Delete all chunks for a specific filename
    
    Body (JSON):
    - document_ids: Array of document IDs to delete (for batch deletion)
    
    Returns JSON with deletion results
    """
    try:
        # Get query parameters
        document_id = req.params.get('document_id')
        filename = req.params.get('filename')
        
        # Check for batch deletion in request body
        document_ids = None
        try:
            req_body = req.get_json()
            if req_body and 'document_ids' in req_body:
                document_ids = req_body['document_ids']
        except Exception:
            pass  # No JSON body is fine
        
        if not document_id and not filename and not document_ids:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Either 'document_id', 'filename' query parameter, or 'document_ids' in request body is required",
                    "usage": {
                        "single_document": "DELETE /api/search/delete/document?document_id=xyz",
                        "by_filename": "DELETE /api/search/delete/document?filename=file.pdf",
                        "batch_deletion": "DELETE /api/search/delete/document with JSON body: {'document_ids': ['id1', 'id2']}"
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Import the deletion functions
        from contracts.ai_services import delete_document_by_id, delete_document_from_index, delete_multiple_documents_by_ids
        
        # Perform the appropriate deletion
        if document_ids:
            logger.info(f"🗑️ Batch deleting {len(document_ids)} documents from Azure Search index")
            result = delete_multiple_documents_by_ids(document_ids)
        elif document_id:
            logger.info(f"🗑️ Deleting document '{document_id}' from Azure Search index")
            result = delete_document_by_id(document_id)
        else:  # filename
            logger.info(f"🗑️ Deleting all chunks for filename '{filename}' from Azure Search index")
            result = delete_document_from_index(filename)
        
        # Determine HTTP status code based on result
        if result["status"] == "success":
            status_code = 200
        elif result["status"] == "not_found":
            status_code = 404
        else:
            status_code = 500
        
        # Prepare response data
        response_data = {
            **result,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.info(f"✅ Deletion operation completed: {result['message']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to delete documents from Azure Search: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Failed to delete documents from Azure Search",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="search/delete/document/persisted", methods=["DELETE"])
async def delete_persisted_chunks(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete persisted Azure Search chunks from local database
    
    Query Parameters:
    - document_id: Delete specific persisted chunk by search document ID
    - filename: Delete all persisted chunks for a specific filename
    - confirm: Must be 'yes' to proceed with deletion
    
    Returns JSON with deletion results
    """
    try:
        # Get query parameters
        document_id = req.params.get('document_id')
        filename = req.params.get('filename')
        confirm = req.params.get('confirm')
        
        if not document_id and not filename:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Either 'document_id' or 'filename' query parameter is required",
                    "usage": {
                        "single_document": "DELETE /api/search/delete/document/persisted?document_id=xyz&confirm=yes",
                        "by_filename": "DELETE /api/search/delete/document/persisted?filename=file.pdf&confirm=yes"
                    },
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        if confirm != 'yes':
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Deletion requires confirmation. Add '&confirm=yes' to the URL",
                    "warning": "This will permanently delete persisted paragraph data from the local database",
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        deleted_count = 0
        
        if db_mgr.db_type == 'sqlite':
            import aiosqlite
            async with aiosqlite.connect(db_mgr.sqlite_path) as db:
                if document_id:
                    logger.info(f"🗑️ Deleting persisted chunk '{document_id}' from database")
                    cursor = await db.execute(
                        "DELETE FROM azure_search_chunks WHERE search_document_id = ?",
                        (document_id,)
                    )
                    deleted_count = cursor.rowcount
                else:  # filename
                    logger.info(f"🗑️ Deleting all persisted chunks for filename '{filename}' from database")
                    cursor = await db.execute(
                        "DELETE FROM azure_search_chunks WHERE filename = ?",
                        (filename,)
                    )
                    deleted_count = cursor.rowcount
                
                await db.commit()
        
        elif db_mgr.db_type == 'azuresql':
            def _execute_delete():
                import pyodbc
                conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
                cursor = conn.cursor()
                
                if document_id:
                    cursor.execute(
                        "DELETE FROM azure_search_chunks WHERE search_document_id = ?",
                        (document_id,)
                    )
                else:  # filename
                    cursor.execute(
                        "DELETE FROM azure_search_chunks WHERE filename = ?",
                        (filename,)
                    )
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted_count
            
            import asyncio
            deleted_count = await asyncio.to_thread(_execute_delete)
        
        # Prepare response
        if deleted_count > 0:
            response_data = {
                "status": "success",
                "message": f"Successfully deleted {deleted_count} persisted chunks from database",
                "deleted_count": deleted_count,
                "document_id": document_id,
                "filename": filename,
                "operation": "delete_persisted_chunks",
                "timestamp": datetime.now(UTC).isoformat()
            }
            status_code = 200
        else:
            response_data = {
                "status": "not_found",
                "message": f"No persisted chunks found for {'document ID: ' + document_id if document_id else 'filename: ' + filename}",
                "deleted_count": 0,
                "document_id": document_id,
                "filename": filename,
                "operation": "delete_persisted_chunks",
                "timestamp": datetime.now(UTC).isoformat()
            }
            status_code = 404
        
        logger.info(f"✅ Persisted chunk deletion completed: {response_data['message']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to delete persisted chunks: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Failed to delete persisted chunks",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="SetupAzureSearchIndex")
@app.route(route="search/setup", methods=["POST"])
async def setup_azure_search_index(req: func.HttpRequest) -> func.HttpResponse:
    """
    Setup Azure Search index - Create the index if it doesn't exist
    ADMIN FUNCTION - Useful for initial setup and index management
    """
    
    logger.info('🏗️ Azure Search index setup function triggered')
    
    try:
        # Parse request parameters
        force_recreate = req.params.get('force_recreate', '').lower() == 'true'
        index_name = req.params.get('index_name')  # Optional custom index name
        
        # Try to get JSON body for additional parameters
        try:
            req_body = req.get_json()
            if req_body:
                force_recreate = req_body.get('force_recreate', force_recreate)
                index_name = req_body.get('index_name', index_name)
        except ValueError:
            pass  # No JSON body or invalid JSON
        
        # Import index creation functions
        try:
            from contracts.index_creation import ensure_search_index_exists, create_document_index_if_not_exists
            INDEX_CREATION_AVAILABLE = True
        except ImportError as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Index creation services not available",
                    "error": str(e)
                }),
                status_code=503,
                mimetype="application/json"
            )
        
        # If force recreate is requested, delete existing index first
        if force_recreate:
            logger.info("🗑️ Force recreate requested - deleting existing index")
            try:
                from azure.search.documents.indexes import SearchIndexClient
                from azure.core.credentials import AzureKeyCredential
                from contracts.config import config
                
                client = SearchIndexClient(
                    endpoint=config.AZURE_SEARCH_ENDPOINT,
                    credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
                )
                
                target_index = index_name or config.AZURE_SEARCH_INDEX
                
                try:
                    client.delete_index(target_index)
                    logger.info(f"✅ Deleted existing index: {target_index}")
                except Exception as e:
                    logger.info(f"ℹ️ Index {target_index} was not found or already deleted: {e}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete existing index: {e}")
        
        # Create or ensure the index exists
        logger.info("🏗️ Starting Azure Search index setup operation")
        
        if index_name:
            # Create specific index with custom name
            setup_results = create_document_index_if_not_exists(index_name)
        else:
            # Use the comprehensive ensure function
            setup_results = ensure_search_index_exists()
        
        # Prepare response
        response_data = {
            "status": setup_results["status"],
            "message": setup_results["message"],
            "index_name": setup_results.get("index_name"),
            "operation": setup_results.get("operation", "setup_index"),
            "fields_count": setup_results.get("fields_count"),
            "ready": setup_results.get("ready", setup_results["status"] in ["created", "exists"]),
            "force_recreate": force_recreate,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Determine status code
        if setup_results["status"] in ["created", "exists"]:
            status_code = 200 if setup_results["status"] == "exists" else 201
        else:
            status_code = 500
        
        logger.info(f"🎉 Azure Search index setup completed: {response_data['message']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Azure Search index setup failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Azure Search index setup failed",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )