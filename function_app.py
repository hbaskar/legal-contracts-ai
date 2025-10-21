# Helper function for storage manager
async def get_storage_manager():
    from contracts.storage import BlobStorageManager
    from config.config import config
    storage_mgr = BlobStorageManager(
        connection_string=config.AZURE_STORAGE_CONNECTION_STRING,
        container_name=config.AZURE_CONTRACTS_CONTAINER
    )
    await storage_mgr.initialize()
    return storage_mgr
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

import os
import azure.functions as func
import logging
import json
from datetime import datetime, UTC
from typing import Optional
import asyncio

# Import our custom modules
from config.config import config
from config.database import DatabaseManager
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

# Upload file endpoint (fix indentation and structure)
@app.function_name(name="UploadFile")
@app.route(route="files/upload", methods=["POST"])
async def upload_file(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Check if file is present in request
        if not req.files or 'file' not in req.files:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "No file provided in request",
                    "error_details": "Request must contain a file in multipart form data"
                }),
                status_code=400,
                mimetype="application/json"
            )
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
        container_param = req.form.get('container', 'contracts')
        allowed_containers = [config.AZURE_CONTRACTS_CONTAINER, config.AZURE_CONTRACTS_POLICIES_CONTAINER]
        if container_param not in allowed_containers:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": f"Invalid container. Allowed containers: {', '.join(allowed_containers)}",
                    "error_details": f"Container '{container_param}' is not supported"
                }),
                status_code=400,
                mimetype="application/json"
            )
        file_content = file.read()
        file_size = len(file_content)
        max_file_size = config.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_file_size:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB",
                    "error_details": f"File size: {file_size} bytes"
                }),
                status_code=400,
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
        storage_mgr = await get_storage_manager()
        db_mgr = await get_db_manager()
        blob_url, blob_name = await storage_mgr.upload_file(
            file_content,
            file.filename,
            file.content_type or 'application/octet-stream'
        )
        checksum = storage_mgr.calculate_file_hash(file_content)
        metadata = FileMetadata(
            filename=blob_name,
            original_filename=file.filename,
            file_size=file_size,
            content_type=file.content_type or 'application/octet-stream',
            blob_url=blob_url,
            container_name=container_param,
            upload_timestamp=datetime.now(UTC),
            checksum=checksum,
            user_id=req.headers.get('X-User-ID')
        )
        record_id = await db_mgr.save_file_metadata(metadata)
        metadata.id = record_id
        response = UploadResponse(
            success=True,
            message="File uploaded successfully",
            file_metadata=metadata
        )
        logger.info(f"Successfully uploaded file: {file.filename} (ID: {record_id})")
        response_data = metadata.to_dict()
        response_data.update({
            "success": response.success,
            "message": response.message,
            "file_id": record_id
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
    path="contracts/{name}",
    connection="AZURE_STORAGE_CONNECTION_STRING"
)
async def process_uploaded_document(myblob: func.InputStream) -> None:

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
                force_reindex=False,  # Don't delete existing documents to preserve history
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


# Blob trigger for automatic policy document processing
@app.function_name(name="ProcessUploadedPolicy")
@app.blob_trigger(
    arg_name="myblob",
    path="contract-policies/{name}",
    connection="AZURE_STORAGE_CONNECTION_STRING"
)
async def process_uploaded_policy(myblob: func.InputStream) -> None:
    """
    Automatically process policy documents when uploaded to contract-policies container
    Uses AI services to extract policy clauses, analyze content, and index to Azure Search
    """
    import tempfile
    import os
    
    try:
        blob_name = myblob.name
        logger.info(f'📋 Policy blob trigger processing: {blob_name}')
        
        # Read the blob content first
        blob_content = myblob.read()
        blob_size = len(blob_content)
        
        logger.info(f'📄 Processing policy blob: {blob_name}, Size: {blob_size} bytes')
        
        # Extract filename from blob path (remove container path if present)
        filename = os.path.basename(blob_name)
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Check if this is a supported document type
        supported_extensions = ['txt', 'docx', 'pdf']
        if file_extension not in supported_extensions:
            logger.info(f"⏭️ Skipping unsupported policy file type: {file_extension} for {filename}")
            return
        
        # Check if policy processing services are available
        try:
            from contracts.policy_processing import process_policy_document_with_ai
            logger.info("✅ Policy processing services available")
        except ImportError as e:
            logger.warning(f"⚠️ Policy processing services not available: {e}")
            return
        
        # Create temporary file with the blob content
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            # Write the blob content we already read to temp file
            temp_file.write(blob_content)
            temp_file_path = temp_file.name
        
        try:
            logger.info(f"📋 Processing policy document with AI services: {filename}")
            
            # Generate policy ID from filename (remove extension)
            policy_id = os.path.splitext(filename)[0]
            
            # Process the policy document with AI services
            result = await process_policy_document_with_ai(
                file_path=temp_file_path,
                filename=filename,
                policy_id=policy_id,
                groups=['legal-team', 'compliance'],  # Default groups for contract policies
                upload_to_search=True  # Always upload to search for automatic processing
            )
            
            if result["status"] == "success":
                logger.info(f"✅ Successfully processed policy {filename}")
                logger.info(f"   📊 Processed {result['clauses_processed']} clauses")
                logger.info(f"   ☁️ Uploaded {result.get('search_uploaded_count', 0)} to policy search index")
                logger.info(f"   🎯 Policy ID: {result['policy_id']}")
                
                # Log policy clause details for monitoring
                policy_records = result.get('policy_records', [])
                for i, record in enumerate(policy_records[:3]):  # Show first 3
                    logger.info(f"   📝 Clause {i+1}: '{record['title']}' (Severity: {record['severity']})")
                
                if result.get('search_failed_count', 0) > 0:
                    logger.warning(f"⚠️ {result['search_failed_count']} policy clauses failed to upload to search")
                    
            else:
                logger.error(f"❌ Failed to process policy {filename}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Error during policy AI processing of {filename}: {str(e)}")
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
                logger.debug(f"🧹 Cleaned up temporary file for policy {filename}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")
        
    except Exception as e:
        logger.error(f"❌ Policy blob trigger error for {myblob.name}: {str(e)}")
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


@app.function_name(name="DatabaseSyncCheck")
@app.route(route="database/sync-check", methods=["GET"])
async def database_sync_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Check database synchronization status between SQLite and Azure SQL
    Validates that both systems can handle the same data consistently
    """
    
    logger.info('🔄 Database synchronization check function triggered')
    
    try:
        # Initialize database manager
        try:
            from config.database import DatabaseManager
            from config.config import config
            from contracts.models import FileMetadata
            DATABASE_AVAILABLE = True
        except ImportError as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Database services not available",
                    "error": str(e)
                }),
                status_code=503,
                mimetype="application/json"
            )
        
        # Get current database type
        db_type = config.DATABASE_TYPE
        sync_check_results = {
            "status": "healthy",
            "current_database_type": db_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": {},
            "schema_validation": {},
            "id_generation": {},
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "warnings": 0
            }
        }
        
        # Initialize database manager for testing
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        # Check 1: Database connectivity
        sync_check_results["checks"]["connectivity"] = {
            "test": "Database connection",
            "status": "passed",
            "message": f"Successfully connected to {db_type} database"
        }
        sync_check_results["summary"]["total_checks"] += 1
        sync_check_results["summary"]["passed_checks"] += 1
        
        # Check 2: Schema validation
        schema_tables = ["file_metadata", "document_chunks", "azure_search_chunks", "chunk_comparisons"]
        for table in schema_tables:
            try:
                if db_type == 'sqlite':
                    import aiosqlite
                    async with aiosqlite.connect(db_mgr.sqlite_path) as db:
                        cursor = await db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                        table_exists = await cursor.fetchone() is not None
                elif db_type == 'azuresql':
                    import asyncio
                    def check_table():
                        conn = db_mgr.get_azure_sql_connection()
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table}'")
                        exists = cursor.fetchone()[0] > 0
                        conn.close()
                        return exists
                    table_exists = await asyncio.to_thread(check_table)
                
                sync_check_results["schema_validation"][table] = {
                    "exists": table_exists,
                    "status": "passed" if table_exists else "failed"
                }
                
                sync_check_results["summary"]["total_checks"] += 1
                if table_exists:
                    sync_check_results["summary"]["passed_checks"] += 1
                else:
                    sync_check_results["summary"]["failed_checks"] += 1
                    
            except Exception as e:
                sync_check_results["schema_validation"][table] = {
                    "exists": False,
                    "status": "error",
                    "error": str(e)
                }
                sync_check_results["summary"]["total_checks"] += 1
                sync_check_results["summary"]["failed_checks"] += 1
        
        # Check 3: ID generation consistency test
        try:
            # Create a test file metadata record
            test_metadata = FileMetadata(
                filename="sync_test_file.txt",
                original_filename="sync_test_file.txt",
                file_size=100,
                content_type="text/plain",
                blob_url="test://sync-test",
                container_name="test-container",
                upload_timestamp=datetime.now(UTC),
                checksum="test_checksum",
                user_id="sync_test_user"
            )
            
            # Save the test record and get the ID
            test_file_id = await db_mgr.save_file_metadata(test_metadata)
            
            if test_file_id and test_file_id > 0:
                sync_check_results["id_generation"]["file_metadata"] = {
                    "status": "passed",
                    "generated_id": test_file_id,
                    "id_type": "integer",
                    "auto_increment": True
                }
                
                # Test document chunk ID generation
                chunk_id = await db_mgr.save_document_chunk(
                    file_id=test_file_id,
                    chunk_index=1,
                    chunk_method="sync_test",
                    chunk_text="This is a test chunk for synchronization validation.",
                    keyphrases=["sync", "test", "validation"],
                    ai_summary="Test chunk summary",
                    ai_title="Test Chunk"
                )
                
                if chunk_id and chunk_id > 0:
                    sync_check_results["id_generation"]["document_chunks"] = {
                        "status": "passed",
                        "generated_id": chunk_id,
                        "related_file_id": test_file_id
                    }
                    
                    # Test Azure Search chunk ID generation
                    search_chunk_id = await db_mgr.save_azure_search_chunk(
                        document_chunk_id=chunk_id,
                        search_document_id=f"test_doc_{test_file_id}_{chunk_id}",
                        index_name="test-index",
                        upload_status="success",
                        paragraph_content="Test paragraph content",
                        paragraph_title="Test Paragraph",
                        filename="sync_test_file.txt"
                    )
                    
                    if search_chunk_id and search_chunk_id > 0:
                        sync_check_results["id_generation"]["azure_search_chunks"] = {
                            "status": "passed",
                            "generated_id": search_chunk_id,
                            "related_chunk_id": chunk_id
                        }
                    else:
                        sync_check_results["id_generation"]["azure_search_chunks"] = {
                            "status": "failed",
                            "message": "Failed to generate search chunk ID"
                        }
                        sync_check_results["summary"]["failed_checks"] += 1
                else:
                    sync_check_results["id_generation"]["document_chunks"] = {
                        "status": "failed",
                        "message": "Failed to generate document chunk ID"
                    }
                    sync_check_results["summary"]["failed_checks"] += 1
                
                # Clean up test data
                try:
                    await db_mgr.reset_table("azure_search_chunks")
                    await db_mgr.reset_table("document_chunks") 
                    await db_mgr.reset_table("file_metadata")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up test data: {cleanup_error}")
                
                sync_check_results["summary"]["total_checks"] += 3
                sync_check_results["summary"]["passed_checks"] += 3
                
            else:
                sync_check_results["id_generation"]["file_metadata"] = {
                    "status": "failed",
                    "message": "Failed to generate file metadata ID"
                }
                sync_check_results["summary"]["total_checks"] += 1
                sync_check_results["summary"]["failed_checks"] += 1
                
        except Exception as e:
            sync_check_results["id_generation"]["error"] = {
                "status": "error",
                "message": f"ID generation test failed: {str(e)}"
            }
            sync_check_results["summary"]["total_checks"] += 1
            sync_check_results["summary"]["failed_checks"] += 1
        
        # Check 4: Content hash consistency validation
        try:
            import hashlib
            test_content = "This is test content for hash consistency validation."
            expected_hash = hashlib.sha256(test_content.encode('utf-8')).hexdigest()[:12]
            
            # Test that content hashing produces consistent results
            test_hash_1 = hashlib.sha256(test_content.encode('utf-8')).hexdigest()[:12]
            test_hash_2 = hashlib.sha256(test_content.encode('utf-8')).hexdigest()[:12]
            
            if test_hash_1 == test_hash_2 == expected_hash:
                sync_check_results["checks"]["content_hashing"] = {
                    "status": "passed",
                    "message": "Content hash generation is consistent",
                    "test_hash": expected_hash
                }
                sync_check_results["summary"]["passed_checks"] += 1
            else:
                sync_check_results["checks"]["content_hashing"] = {
                    "status": "failed",
                    "message": "Content hash generation is inconsistent"
                }
                sync_check_results["summary"]["failed_checks"] += 1
                
            sync_check_results["summary"]["total_checks"] += 1
            
        except Exception as e:
            sync_check_results["checks"]["content_hashing"] = {
                "status": "error",
                "message": f"Content hashing test failed: {str(e)}"
            }
            sync_check_results["summary"]["total_checks"] += 1
            sync_check_results["summary"]["failed_checks"] += 1
        
        # Overall status determination
        if sync_check_results["summary"]["failed_checks"] > 0:
            sync_check_results["status"] = "degraded"
            if sync_check_results["summary"]["failed_checks"] > sync_check_results["summary"]["passed_checks"]:
                sync_check_results["status"] = "unhealthy"
        
        # Add recommendations based on findings
        recommendations = []
        if sync_check_results["summary"]["failed_checks"] > 0:
            recommendations.append("Some database synchronization checks failed - review failed checks above")
        if db_type == 'sqlite':
            recommendations.append("Currently using SQLite for development - ensure Azure SQL compatibility for production")
        if sync_check_results["summary"]["passed_checks"] == sync_check_results["summary"]["total_checks"]:
            recommendations.append("All synchronization checks passed - databases are properly synchronized")
        
        sync_check_results["recommendations"] = recommendations
        
        return func.HttpResponse(
            json.dumps(sync_check_results),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Database sync check failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Database synchronization check failed",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="ValidateDatabaseSearchSync")
@app.route(route="database/validate-search-sync", methods=["GET"])
async def validate_database_search_sync(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validate that database records are synchronized with Azure Search documents
    Checks that all database chunks have corresponding Azure Search entries
    """
    
    logger.info('🔍 Database-Search synchronization validation function triggered')
    
    try:
        # Parse request parameters
        file_id = req.params.get('file_id')
        limit = int(req.params.get('limit', 50))
        
        # Initialize database manager
        try:
            from config.database import DatabaseManager
            from contracts.ai_services import get_search_client
            DATABASE_AVAILABLE = True
        except ImportError as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Required services not available",
                    "error": str(e)
                }),
                status_code=503,
                mimetype="application/json"
            )
        
        validation_results = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "validation_summary": {
                "total_database_chunks": 0,
                "chunks_with_search_records": 0,
                "chunks_missing_search_records": 0,
                "search_records_validated": 0,
                "search_records_with_errors": 0,
                "orphaned_search_records": 0
            },
            "database_chunks": [],
            "missing_search_records": [],
            "validation_errors": [],
            "recommendations": []
        }
        
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        # Get database chunks (with optional file_id filter)
        if file_id:
            try:
                file_id = int(file_id)
                chunks = await db_mgr.get_document_chunks(file_id)
                validation_results["filter"] = f"file_id={file_id}"
            except ValueError:
                return func.HttpResponse(
                    json.dumps({
                        "status": "error",
                        "message": "Invalid file_id parameter - must be an integer"
                    }),
                    status_code=400,
                    mimetype="application/json"
                )
        else:
            # Get chunks for all files (limited)
            chunks = []
            try:
                if db_mgr.db_type == 'sqlite':
                    import aiosqlite
                    async with aiosqlite.connect(db_mgr.sqlite_path) as db:
                        cursor = await db.execute(f"""
                            SELECT id, file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                                   start_position, end_position, keyphrases, ai_summary, ai_title, 
                                   created_timestamp, processing_time_ms
                            FROM document_chunks 
                            ORDER BY created_timestamp DESC 
                            LIMIT {limit}
                        """)
                        rows = await cursor.fetchall()
                        
                        for row in rows:
                            import json
                            keyphrases = json.loads(row[9]) if row[9] else []
                            chunks.append({
                                'id': row[0], 'file_id': row[1], 'chunk_index': row[2],
                                'chunk_method': row[3], 'chunk_size': row[4], 'chunk_text': row[5],
                                'chunk_hash': row[6], 'start_position': row[7], 'end_position': row[8],
                                'keyphrases': keyphrases, 'ai_summary': row[10], 'ai_title': row[11],
                                'created_timestamp': row[12], 'processing_time_ms': row[13]
                            })
                            
                elif db_mgr.db_type == 'azuresql':
                    import asyncio
                    def get_chunks():
                        conn = db_mgr.get_azure_sql_connection()
                        cursor = conn.cursor()
                        cursor.execute(f"""
                            SELECT TOP {limit} id, file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                                   start_position, end_position, keyphrases, ai_summary, ai_title, 
                                   created_timestamp, processing_time_ms
                            FROM document_chunks 
                            ORDER BY created_timestamp DESC
                        """)
                        rows = cursor.fetchall()
                        conn.close()
                        
                        chunk_list = []
                        for row in rows:
                            import json
                            keyphrases = json.loads(row[9]) if row[9] else []
                            chunk_list.append({
                                'id': row[0], 'file_id': row[1], 'chunk_index': row[2],
                                'chunk_method': row[3], 'chunk_size': row[4], 'chunk_text': row[5],
                                'chunk_hash': row[6], 'start_position': row[7], 'end_position': row[8],
                                'keyphrases': keyphrases, 'ai_summary': row[10], 'ai_title': row[11],
                                'created_timestamp': row[12], 'processing_time_ms': row[13]
                            })
                        return chunk_list
                    
                    chunks = await asyncio.to_thread(get_chunks)
                    
            except Exception as e:
                return func.HttpResponse(
                    json.dumps({
                        "status": "error",
                        "message": f"Failed to retrieve database chunks: {str(e)}"
                    }),
                    status_code=500,
                    mimetype="application/json"
                )
        
        validation_results["validation_summary"]["total_database_chunks"] = len(chunks)
        
        # Check each database chunk for corresponding Azure Search records
        for chunk in chunks:
            chunk_validation = {
                "chunk_id": chunk['id'],
                "file_id": chunk['file_id'],
                "chunk_index": chunk['chunk_index'],
                "chunk_method": chunk['chunk_method'],
                "has_search_record": False,
                "search_document_ids": [],
                "validation_status": "unknown"
            }
            
            try:
                # Get Azure Search chunks for this document chunk
                search_chunks = await db_mgr.get_azure_search_chunks_with_content(chunk['file_id'])
                
                # Find search records for this specific chunk
                matching_search_chunks = [
                    sc for sc in search_chunks 
                    if sc['document_chunk_id'] == chunk['id']
                ]
                
                if matching_search_chunks:
                    chunk_validation["has_search_record"] = True
                    chunk_validation["search_document_ids"] = [
                        sc['search_document_id'] for sc in matching_search_chunks
                    ]
                    chunk_validation["validation_status"] = "synced"
                    validation_results["validation_summary"]["chunks_with_search_records"] += 1
                    validation_results["validation_summary"]["search_records_validated"] += len(matching_search_chunks)
                else:
                    chunk_validation["validation_status"] = "missing_search_record"
                    validation_results["validation_summary"]["chunks_missing_search_records"] += 1
                    validation_results["missing_search_records"].append(chunk_validation)
                    
            except Exception as e:
                chunk_validation["validation_status"] = "error"
                chunk_validation["error"] = str(e)
                validation_results["validation_errors"].append(chunk_validation)
                validation_results["validation_summary"]["search_records_with_errors"] += 1
            
            validation_results["database_chunks"].append(chunk_validation)
        
        # Calculate sync percentage
        if validation_results["validation_summary"]["total_database_chunks"] > 0:
            sync_percentage = (
                validation_results["validation_summary"]["chunks_with_search_records"] / 
                validation_results["validation_summary"]["total_database_chunks"]
            )
            try:
                from azure.search.documents.indexes import SearchIndexClient
                from azure.core.credentials import AzureKeyCredential
                from config.config import config

                client = SearchIndexClient(
                    endpoint=config.AZURE_SEARCH_ENDPOINT,
                    credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
                )

                target_index = index_name or config.AZURE_SEARCH_DOC_INDEX

                try:
                    client.delete_index(target_index)
                    logger.info(f"✅ Deleted existing index: {target_index}")
                except Exception as e:
                    logger.info(f"ℹ️ Index {target_index} was not found or already deleted: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete existing index: {e}")
        else:
            validation_results["status"] = "degraded"
            validation_results["recommendations"].append("Significant synchronization issues detected - consider re-processing documents")
        
        return func.HttpResponse(
            json.dumps(validation_results),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Database-Search sync validation failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Database-Search synchronization validation failed",
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
            pass

        # Import the deletion functions
        from contracts.ai_services import delete_document_by_id, delete_document_from_index, delete_multiple_documents_by_ids

        # Perform the appropriate deletion
        if document_ids:
            logger.info(f"🗑️ Batch deleting {len(document_ids)} documents from Azure Search index")
            result = delete_multiple_documents_by_ids(document_ids)
        elif document_id:
            logger.info(f"🗑️ Deleting document '{document_id}' from Azure Search index")
            result = delete_document_by_id(document_id)
        elif filename:
            logger.info(f"🗑️ Deleting all chunks for filename '{filename}' from Azure Search index")
            result = delete_document_from_index(filename)
        else:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "Either 'document_id', 'filename', or 'document_ids' is required"
                }),
                status_code=400,
                mimetype="application/json"
            )

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
                from config.config import config

                client = SearchIndexClient(
                    endpoint=config.AZURE_SEARCH_ENDPOINT,
                    credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
                )

                target_index = index_name or config.AZURE_SEARCH_DOC_INDEX

                try:
                    client.delete_index(target_index)
                    logger.info(f"✅ Deleted existing index: {target_index}")
                except Exception as e:
                    logger.info(f"ℹ️ Index {target_index} was not found or already deleted: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete existing index: {e}")

        # ...existing code...
    except Exception as e:
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


@app.function_name(name="ResetStorage")
@app.route(route="storage/reset", methods=["POST", "DELETE"])
async def reset_storage(req: func.HttpRequest) -> func.HttpResponse:
    """
    Reset storage files - ADMIN FUNCTION
    
    Deletes all files from the Azure Storage container for testing purposes.
    Use with caution - this will delete ALL files!
    """
    try:
        logger.info('Storage reset function triggered')
        
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
                    "message": "Storage reset requires confirmation",
                    "instructions": "Add '?confirm=yes' parameter or set 'confirm': 'yes' in request body",
                    "warning": "This will delete ALL files from storage container"
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
                    "message": "Storage reset is not allowed in production environment",
                    "environment": environment,
                    "instructions": "Use 'force=true' parameter only if absolutely necessary"
                }),
                status_code=403,
                mimetype="application/json"
            )
        
        # Execute storage reset using our reset script functionality
        from scripts.reset_system import delete_all_storage_files
        
        logger.info("Starting storage reset operation")
        reset_results = delete_all_storage_files()
        
        # Add metadata to response
        response_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": environment,
            "status": reset_results["status"],
            "message": reset_results["message"],
            "deleted_count": reset_results["deleted_count"]
        }
        
        # Add failed deletions if any
        if "failed_deletions" in reset_results:
            response_data["failed_deletions"] = reset_results["failed_deletions"]
        
        # Determine status code
        status_code = 200 if reset_results["status"] == "success" else 207
        
        logger.info(f"Storage reset completed: {reset_results['status']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Storage reset failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "Storage reset failed",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="ProcessPolicyDocument")
@app.route(route="process_policy", methods=["GET", "POST"])
async def process_policy_document_function(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function HTTP endpoint for policy document processing with AI capabilities"""
    
    logger.info('📋 Policy processing HTTP function triggered')
    
    try:
        # Import here to avoid startup issues if AI services aren't available
        try:
            from contracts.policy_processing import process_policy_document_with_ai
            POLICY_SERVICES_AVAILABLE = True
        except ImportError as e:
            POLICY_SERVICES_AVAILABLE = False
            logger.warning(f"Policy processing services not available: {e}")
        
        method = req.method.upper()
        
        if method == 'GET':
            # Health check or status endpoint
            return func.HttpResponse(
                json.dumps({
                    "status": "healthy",
                    "message": "Policy Processing Function is running",
                    "version": "1.0.0",
                    "policy_services_available": POLICY_SERVICES_AVAILABLE,
                    "supported_file_types": ["txt", "docx", "pdf"],
                    "supported_upload_methods": ["JSON with base64 content", "Multipart form data file upload"],
                    "features": [
                        "AI policy clause extraction",
                        "Structured policy analysis", 
                        "Azure Search policy indexing",
                        "Policy severity classification",
                        "Direct file upload support"
                    ]
                }),
                mimetype="application/json",
                status_code=200
            )
        
        elif method == 'POST':
            if not POLICY_SERVICES_AVAILABLE:
                return func.HttpResponse(
                    json.dumps({
                        "error": "Policy processing services not available. Please check OpenAI and Search service configuration."
                    }),
                    mimetype="application/json",
                    status_code=503
                )
            
            # Check if this is a multipart form data request (file upload) or JSON request
            content_type = req.headers.get('Content-Type', '')
            temp_file_path = None
            filename = None
            policy_id = None
            groups = ['legal-team', 'compliance']
            upload_to_search = True
            
            if content_type.startswith('multipart/form-data'):
                # Handle file upload
                try:
                    # Get the uploaded file
                    files = req.files
                    if not files or 'file' not in files:
                        return func.HttpResponse(
                            json.dumps({"error": "No file uploaded. Please upload a file with key 'file'"}),
                            mimetype="application/json",
                            status_code=400
                        )
                    
                    uploaded_file = files['file']
                    filename = uploaded_file.filename
                    
                    if not filename:
                        return func.HttpResponse(
                            json.dumps({"error": "Uploaded file has no filename"}),
                            mimetype="application/json",
                            status_code=400
                        )
                    
                    # Get optional form parameters
                    form_data = req.form
                    policy_id = form_data.get('policy_id')
                    if form_data.get('groups'):
                        groups = form_data.get('groups').split(',')
                    upload_to_search = form_data.get('upload_to_search', 'true').lower() == 'true'
                    
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
                    
                    # Save uploaded file to temporary location
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                        temp_file.write(uploaded_file.read())
                        temp_file_path = temp_file.name
                    
                except Exception as e:
                    return func.HttpResponse(
                        json.dumps({"error": f"Error processing uploaded file: {str(e)}"}),
                        mimetype="application/json",
                        status_code=400
                    )
                    
            else:
                # Handle JSON request with base64 content
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
                policy_id = req_body.get('policy_id')  # Optional custom policy ID
                groups = req_body.get('groups', ['legal-team', 'compliance'])  # Default access groups
                upload_to_search = req_body.get('upload_to_search', True)  # Default to upload
                
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
            
            # Process the policy document using AI services
            try:
                result = await process_policy_document_with_ai(
                    file_path=temp_file_path,
                    filename=filename,
                    policy_id=policy_id,
                    groups=groups,
                    upload_to_search=upload_to_search
                )
                
                return func.HttpResponse(
                    json.dumps(result),
                    mimetype="application/json",
                    status_code=200 if result["status"] == "success" else 500
                )
                
            finally:
                # Clean up temporary file
                if temp_file_path:
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
        logger.error(f"Unexpected error in policy processing function: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"Internal server error: {str(e)}"
            }),
            mimetype="application/json",
            status_code=500
        )


@app.function_name(name="SearchPolicies")
@app.route(route="search/policies", methods=["GET"])
async def search_policies_function(req: func.HttpRequest) -> func.HttpResponse:
    """Search and retrieve policy documents from Azure Search policy index"""
    
    logger.info('🔍 Policy search function triggered')
    
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from contracts.index_creation import create_policy_index_if_not_exists
        
        # Ensure policy index exists
        index_result = create_policy_index_if_not_exists()
        if index_result['status'] == 'error':
            return func.HttpResponse(
                json.dumps({
                    "error": f"Policy index not available: {index_result['message']}"
                }),
                mimetype="application/json",
                status_code=503
            )
        
        # Initialize policy search client
        policy_client = SearchClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            index_name=config.AZURE_SEARCH_POLICY_INDEX,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
        )
        
        # Parse query parameters
        search_text = req.params.get('q', '*')  # Default to all
        limit = min(50, int(req.params.get('limit', 10)))  # Max 50, default 10
        policy_id = req.params.get('policy_id')
        filename = req.params.get('filename') 
        severity = req.params.get('severity')  # 1 or 2
        tags = req.params.get('tags')  # Comma-separated
        groups = req.params.get('groups')  # Comma-separated
        
        # Build filter conditions
        filters = []
        if policy_id:
            filters.append(f"PolicyId eq '{policy_id}'")
        if filename:
            filters.append(f"filename eq '{filename}'")
        if severity:
            try:
                sev_int = int(severity)
                if sev_int in [1, 2]:
                    filters.append(f"severity eq {sev_int}")
            except ValueError:
                pass
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            tag_filters = [f"tags/any(t: t eq '{tag}')" for tag in tag_list]
            if tag_filters:
                filters.append(f"({' or '.join(tag_filters)})")
        if groups:
            group_list = [group.strip() for group in groups.split(',')]
            group_filters = [f"groups/any(g: g eq '{group}')" for group in group_list]
            if group_filters:
                filters.append(f"({' or '.join(group_filters)})")
        
        # Combine filters
        filter_str = ' and '.join(filters) if filters else None
        
        logger.info(f"🔍 Policy search: '{search_text}' with {len(filters)} filters")
        
        # Execute search
        search_results = policy_client.search(
            search_text=search_text,
            filter=filter_str,
            top=limit,
            include_total_count=True,
            select=[
                "id", "PolicyId", "filename", "title", "instruction", 
                "summary", "tags", "groups", "severity", "language", "locked"
            ]
        )
        
        # Collect results
        policies = []
        for result in search_results:
            policy_doc = {
                "id": result.get("id"),
                "policy_id": result.get("PolicyId"), 
                "filename": result.get("filename"),
                "title": result.get("title"),
                "instruction": result.get("instruction"),
                "summary": result.get("summary"),
                "tags": result.get("tags", []),
                "groups": result.get("groups", []),
                "severity": result.get("severity"),
                "language": result.get("language"),
                "locked": result.get("locked", False),
                "search_score": getattr(result, '@search.score', None)
            }
            policies.append(policy_doc)
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": f"Retrieved {len(policies)} policy documents",
            "policies": policies,
            "total_policies": getattr(search_results, 'get_count', lambda: len(policies))(),
            "search_params": {
                "query": search_text,
                "limit": limit,
                "filters_applied": len(filters)
            },
            "index_name": config.AZURE_SEARCH_POLICY_INDEX,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Policy search completed: {len(policies)} results")
        
        return func.HttpResponse(
            json.dumps(response_data),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Error in policy search: {e}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"Policy search failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }),
            mimetype="application/json",
            status_code=500
        )


@app.function_name(name="ResetSystem")
@app.route(route="system/reset", methods=["POST", "DELETE"])
async def reset_system(req: func.HttpRequest) -> func.HttpResponse:
    """
    Complete system reset - ADMIN FUNCTION
    
    Performs comprehensive system reset including storage, database, and indexes.
    Use with extreme caution - this will delete ALL data!
    """
    try:
        logger.info('Complete system reset function triggered')
        
        # Security check - require confirmation parameter
        confirmation = req.params.get('confirm', '').lower()
        force_reset = req.params.get('force', '').lower() == 'true'
        
        # Check for confirmation in JSON body for POST requests
        components = ["storage", "database", "indexes"]  # Default components
        if req.method == 'POST':
            try:
                req_body = req.get_json()
                if req_body:
                    confirmation = req_body.get('confirm', confirmation).lower()
                    force_reset = req_body.get('force', force_reset)
                    components = req_body.get('components', components)
            except:
                pass
        
        # Require explicit confirmation
        if confirmation != 'yes' and not force_reset:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "message": "System reset requires confirmation",
                    "instructions": "Add '?confirm=yes' parameter or set 'confirm': 'yes' in request body",
                    "warning": "This will delete ALL data from storage, database, and search indexes"
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
                    "message": "System reset is not allowed in production environment",
                    "environment": environment,
                    "instructions": "Use 'force=true' parameter only if absolutely necessary"
                }),
                status_code=403,
                mimetype="application/json"
            )
        
        # Execute complete system reset using a combination of direct calls and script functions
        from scripts.reset_system import delete_all_storage_files, delete_search_indexes
        
        logger.info("Starting complete system reset operation")
        
        # Initialize results structure
        reset_results = {
            "status": "success",
            "message": "Complete system reset successful",
            "results": {
                "storage": {"status": "not_attempted"},
                "database": {"status": "not_attempted"},
                "indexes": {"status": "not_attempted"}
            },
            "summary": {"successful": 0, "partial": 0, "failed": 0}
        }
        
        # 1. Reset storage if requested
        if "storage" in components:
            storage_result = delete_all_storage_files()
            reset_results["results"]["storage"] = storage_result
            if storage_result["status"] == "success":
                reset_results["summary"]["successful"] += 1
            elif storage_result["status"] == "partial":
                reset_results["summary"]["partial"] += 1
            else:
                reset_results["summary"]["failed"] += 1
        
        # 2. Reset database if requested
        if "database" in components:
            try:
                db_mgr = await get_db_manager()
                db_reset_result = await db_mgr.reset_all_tables()
                
                if db_reset_result["summary"]["tables_with_errors"] == 0:
                    reset_results["results"]["database"] = {
                        "status": "success",
                        "message": f"Database reset complete. Reset {db_reset_result['summary']['tables_reset_successfully']} tables",
                        "tables_reset": db_reset_result["tables_reset"],
                        "total_records_deleted": db_reset_result["total_records_deleted"]
                    }
                    reset_results["summary"]["successful"] += 1
                else:
                    reset_results["results"]["database"] = {
                        "status": "partial",
                        "message": f"Database reset completed with errors. Reset {db_reset_result['summary']['tables_reset_successfully']} tables",
                        "tables_reset": db_reset_result["tables_reset"],
                        "tables_with_errors": db_reset_result["tables_with_errors"]
                    }
                    reset_results["summary"]["partial"] += 1
            except Exception as e:
                reset_results["results"]["database"] = {
                    "status": "error",
                    "message": f"Database reset failed: {str(e)}"
                }
                reset_results["summary"]["failed"] += 1
        
        # 3. Reset indexes if requested
        if "indexes" in components:
            indexes_result = delete_search_indexes()
            reset_results["results"]["indexes"] = indexes_result
            if indexes_result["status"] == "success":
                reset_results["summary"]["successful"] += 1
            elif indexes_result["status"] == "partial":
                reset_results["summary"]["partial"] += 1
            else:
                reset_results["summary"]["failed"] += 1
        
        # Determine overall status
        if reset_results["summary"]["failed"] > 0:
            reset_results["status"] = "error"
            reset_results["message"] = "System reset completed with errors"
        elif reset_results["summary"]["partial"] > 0:
            reset_results["status"] = "partial"
            reset_results["message"] = "System reset completed with warnings"
        
        # Add metadata to response
        response_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": environment,
            "status": reset_results["status"],
            "message": reset_results["message"],
            "results": reset_results["results"],
            "summary": reset_results["summary"]
        }
        
        # Determine status code
        status_code = 200 if reset_results["status"] == "success" else 207
        
        logger.info(f"System reset completed: {reset_results['status']}")
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"System reset failed: {str(e)}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": "System reset failed",
                "error_details": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


# EventGrid trigger for handling blob deletion events
@app.function_name(name="HandleBlobDeletion")
@app.event_grid_trigger(arg_name="event")
async def handle_blob_deletion(event: func.EventGridEvent) -> None:
    """
    Handle blob deletion events from EventGrid to automatically clean up corresponding Azure Search index entries
    Triggers when documents or policies are deleted from blob storage containers
    """
    from config.config import config
    
    try:
        event_data = event.get_json()
        event_type = event.event_type
        subject = event.subject
        
        logger.info(f'🗑️ EventGrid blob event: {event_type} for {subject}')
        
        # Only handle blob deletion events
        if event_type != "Microsoft.Storage.BlobDeleted":
            logger.info(f"⏭️ Ignoring non-deletion event: {event_type}")
            return
            
        # Extract blob information from the event
        blob_url = event_data.get('url', '')
        blob_name = subject.split('/')[-1] if '/' in subject else subject
        
        # Determine which container the blob was deleted from
        container_name = None
        if f'/blobs/{config.AZURE_CONTRACTS_CONTAINER}/' in subject:
            container_name = config.AZURE_CONTRACTS_CONTAINER
        elif f'/blobs/{config.AZURE_CONTRACTS_POLICIES_CONTAINER}/' in subject:
            container_name = config.AZURE_CONTRACTS_POLICIES_CONTAINER
        else:
            logger.info(f"⏭️ Blob deletion not in monitored containers: {subject}")
            return
            
        logger.info(f"🗑️ Processing deletion of {blob_name} from {container_name} container")
        
        # Import deletion functions
        try:
            from contracts.ai_services import delete_document_from_index
            logger.info("✅ Document deletion services available")
        except ImportError as e:
            logger.warning(f"⚠️ Document deletion services not available: {e}")
            return
        
        # Delete corresponding documents from Azure Search index based on filename
        try:
            if container_name == config.AZURE_CONTRACTS_CONTAINER:
                # Delete from main document index
                deletion_result = delete_document_from_index(blob_name)
                logger.info(f"📄 Document index cleanup result: {deletion_result}")
                
            elif container_name == config.AZURE_CONTRACTS_POLICIES_CONTAINER:
                # Delete from policy index - we need to handle this differently
                # Policy documents may have multiple clauses/records per file
                try:
                    from contracts.ai_services import get_search_client
                    from azure.search.documents import SearchClient
                    from azure.core.credentials import AzureKeyCredential
                    
                    # Initialize policy search client
                    policy_client = SearchClient(
                        endpoint=config.AZURE_SEARCH_ENDPOINT,
                        index_name=config.AZURE_SEARCH_POLICY_INDEX,
                        credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
                    )
                    
                    # Search for all policy records with this filename
                    search_results = policy_client.search(
                        search_text="*",
                        filter=f"filename eq '{blob_name}'",
                        select=["id", "PolicyId", "title"]
                    )
                    
                    # Collect document IDs to delete
                    ids_to_delete = []
                    for result in search_results:
                        ids_to_delete.append(result["id"])
                        logger.info(f"📋 Found policy clause to delete: {result.get('title', 'Unknown')} (ID: {result['id']})")
                    
                    if ids_to_delete:
                        # Delete documents from policy index
                        delete_batch = [{"@search.action": "delete", "id": doc_id} for doc_id in ids_to_delete]
                        policy_client.upload_documents(documents=delete_batch)
                        logger.info(f"✅ Successfully deleted {len(ids_to_delete)} policy clauses from search index")
                    else:
                        logger.info(f"ℹ️ No policy clauses found for {blob_name}")
                        
                except Exception as search_error:
                    logger.error(f"❌ Failed to delete policy clauses from search index: {str(search_error)}")
            
            # Also clean up database records if possible
            try:
                from contracts.ai_services import get_database_manager
                db_mgr = get_database_manager()
                if db_mgr:
                    # Find file record by filename
                    files = await db_mgr.get_files_by_filename(blob_name)
                    for file_record in files:
                        file_id = file_record.id
                        # Delete associated chunks
                        await db_mgr.delete_document_chunks(file_id)
                        logger.info(f"💾 Cleaned up database chunks for file ID: {file_id}")
                        
            except Exception as db_error:
                logger.warning(f"Could not clean up database records: {str(db_error)}")
            
            logger.info(f"✅ Completed cleanup for deleted blob: {blob_name}")
            
        except Exception as cleanup_error:
            logger.error(f"❌ Error during search index cleanup: {str(cleanup_error)}")
        
    except Exception as e:
        logger.error(f"❌ EventGrid blob deletion handler error: {str(e)}")
        # Don't re-raise to avoid EventGrid retries


@app.function_name(name="DeleteBlobFile")
@app.route(route="storage/delete", methods=["DELETE"])
async def delete_blob_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a file from Azure Blob Storage container
    Useful for testing EventGrid blob deletion events
    """
    from config.config import config
    
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
        allowed_containers = [config.AZURE_CONTRACTS_CONTAINER, config.AZURE_CONTRACTS_POLICIES_CONTAINER]
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
        
        # For local testing, also call the index deletion logic directly
        # since EventGrid only works with Azure-deployed functions
        index_deletion_result = None
        try:
            from contracts.ai_services import delete_document_from_index
            
            if container_name == config.AZURE_CONTRACTS_CONTAINER:
                # Delete from main document index
                index_deletion_result = delete_document_from_index(blob_name)
                logger.info(f"📄 Local test - Document index cleanup result: {index_deletion_result}")
                
            elif container_name == config.AZURE_CONTRACTS_POLICIES_CONTAINER:
                # Delete from policy index - we need to handle this differently
                try:
                    from contracts.ai_services import get_search_client
                    from azure.search.documents import SearchClient
                    from azure.core.credentials import AzureKeyCredential
                    
                    # Initialize policy search client
                    policy_client = SearchClient(
                        endpoint=config.AZURE_SEARCH_ENDPOINT,
                        index_name=config.AZURE_SEARCH_POLICY_INDEX,
                        credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
                    )
                    
                    # Search for all policy records with this filename
                    search_results = policy_client.search(
                        search_text="*",
                        filter=f"filename eq '{blob_name}'",
                        select=["id", "PolicyId", "title"]
                    )
                    
                    # Collect document IDs to delete
                    documents_to_delete = []
                    for result in search_results:
                        documents_to_delete.append({"@search.action": "delete", "id": result["id"]})
                    
                    if documents_to_delete:
                        # Execute batch deletion
                        upload_result = policy_client.upload_documents(documents_to_delete)
                        successful_deletes = sum(1 for r in upload_result if r.succeeded)
                        index_deletion_result = f"Deleted {successful_deletes} policy records for {blob_name}"
                        logger.info(f"🗑️ Local test - Policy index cleanup: {index_deletion_result}")
                    else:
                        index_deletion_result = f"No policy records found for {blob_name}"
                        logger.info(f"ℹ️ Local test - {index_deletion_result}")
                        
                except Exception as policy_delete_error:
                    index_deletion_result = f"Error deleting policy records: {str(policy_delete_error)}"
                    logger.error(f"❌ Local test - Policy deletion error: {policy_delete_error}")
                    
        except ImportError as e:
            index_deletion_result = f"Index deletion services not available: {e}"
            logger.warning(f"⚠️ Local test - {index_deletion_result}")
        except Exception as e:
            index_deletion_result = f"Error during index cleanup: {str(e)}"
            logger.error(f"❌ Local test - Index deletion error: {e}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": f"Successfully deleted blob '{blob_name}' from container '{container_name}'",
                "container": container_name,
                "blob_name": blob_name,
                "deleted_at": datetime.now(UTC).isoformat(),
                "index_cleanup": index_deletion_result,
                "eventgrid_note": "EventGrid blob deletion events only work with Azure-deployed functions. For local testing, index cleanup is performed directly.",
                "deployment_note": "Deploy to Azure with 'func azure functionapp publish aifnc' to enable automatic EventGrid-triggered index cleanup"
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


# Test endpoint for index cleanup (local testing only)
@app.route(route="test/index/cleanup", auth_level=func.AuthLevel.FUNCTION)
def test_index_cleanup(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test endpoint to directly test index cleanup functionality without EventGrid
    For local testing only - helps verify the index deletion logic works
    """
    from config.config import config
    
    try:
        # Get parameters
        filename = req.params.get('filename')
        container = req.params.get('container', config.AZURE_CONTRACTS_CONTAINER)
        
        if not filename:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing required parameter",
                    "message": "Filename parameter is required",
                    "usage": "GET /api/test/index/cleanup?filename=document.txt&container=uploads"
                }),
                mimetype="application/json",
                status_code=400
            )
        
        logger.info(f"🧪 Testing index cleanup for {filename} from {container}")
        
        # Test index deletion logic
        index_deletion_result = None
        try:
            from contracts.ai_services import delete_document_from_index
            
            if container == config.AZURE_CONTRACTS_CONTAINER:
                # Delete from main document index
                index_deletion_result = delete_document_from_index(filename)
                logger.info(f"📄 Test - Document index cleanup result: {index_deletion_result}")
                
            elif container == config.AZURE_CONTRACTS_POLICIES_CONTAINER:
                # Delete from policy index
                try:
                    from contracts.ai_services import get_search_client
                    from azure.search.documents import SearchClient
                    from azure.core.credentials import AzureKeyCredential
                    
                    # Initialize policy search client
                    policy_client = SearchClient(
                        endpoint=config.AZURE_SEARCH_ENDPOINT,
                        index_name=config.AZURE_SEARCH_POLICY_INDEX,
                        credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
                    )
                    
                    # Search for all policy records with this filename
                    search_results = policy_client.search(
                        search_text="*",
                        filter=f"filename eq '{filename}'",
                        select=["id", "PolicyId", "title"]
                    )
                    
                    # Collect document IDs to delete
                    documents_to_delete = []
                    for result in search_results:
                        documents_to_delete.append({"@search.action": "delete", "id": result["id"]})
                    
                    if documents_to_delete:
                        # Execute batch deletion
                        upload_result = policy_client.upload_documents(documents_to_delete)
                        successful_deletes = sum(1 for r in upload_result if r.succeeded)
                        index_deletion_result = f"Deleted {successful_deletes} policy records for {filename}"
                        logger.info(f"🗑️ Test - Policy index cleanup: {index_deletion_result}")
                    else:
                        index_deletion_result = f"No policy records found for {filename}"
                        logger.info(f"ℹ️ Test - {index_deletion_result}")
                        
                except Exception as policy_delete_error:
                    index_deletion_result = f"Error deleting policy records: {str(policy_delete_error)}"
                    logger.error(f"❌ Test - Policy deletion error: {policy_delete_error}")
                    
        except ImportError as e:
            index_deletion_result = f"Index deletion services not available: {e}"
            logger.warning(f"⚠️ Test - {index_deletion_result}")
        except Exception as e:
            index_deletion_result = f"Error during index cleanup: {str(e)}"
            logger.error(f"❌ Test - Index deletion error: {e}")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": "Index cleanup test completed",
                "filename": filename,
                "container": container,
                "index_cleanup_result": index_deletion_result,
                "note": "This is a test endpoint for local development. In production, EventGrid triggers automatic index cleanup when blobs are deleted."
            }),
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"❌ Test index cleanup error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Test failed",
                "message": str(e)
            }),
            mimetype="application/json",
            status_code=500
        )

# Endpoint to regenerate PDF from Azure Search chunks
@app.function_name(name="RegeneratePDF")
@app.route(route="pdf/regenerate", methods=["POST"])
async def regenerate_pdf_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Regenerate a PDF from Azure Search chunks and upload to blob storage.
    Request body: { "filename": "your_file.docx" }
    """
    import importlib.util
    import os
    import json

    try:
        req_body = req.get_json()
        filename = req_body.get("filename")
        if not filename:
            return func.HttpResponse(
                json.dumps({"success": False, "message": "Missing filename"}),
                status_code=400,
                mimetype="application/json"
            )

        # Dynamically import scripts/regenerate_pdf.py
        script_path = os.path.join(os.path.dirname(__file__), "scripts", "regenerate_pdf.py")
        spec = importlib.util.spec_from_file_location("regenerate_pdf", script_path)
        regen_pdf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(regen_pdf)

        # Call the regenerate_pdf function
        regen_pdf.regenerate_pdf(filename)

        return func.HttpResponse(
            json.dumps({"success": True, "message": f"PDF regenerated and uploaded for {filename}"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"success": False, "message": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
