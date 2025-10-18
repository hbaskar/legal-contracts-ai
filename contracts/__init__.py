# Azure Function File Upload Service - Contracts Module
# This module contains the core business logic, models, and data access layers

import os
import json
import logging
import tempfile
import base64

import azure.functions as func

# Import configuration (handles .env loading internally)
from contracts.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import AI services functionality
try:
    from contracts.ai_services import process_document_with_ai_keyphrases
    AI_SERVICES_AVAILABLE = True
    logger.info("✅ AI services module loaded successfully")
except ImportError as e:
    AI_SERVICES_AVAILABLE = False
    logger.warning(f"AI services not available: {e}")


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function main entry point for document processing with AI capabilities"""
    logger.info('🚀 Document processing function triggered')
    
    try:
        # Parse request
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
            chunking_method = req_body.get('chunking_method', 'intelligent')
            
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
                # Process the document using AI services
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
        logger.error(f"Unexpected error in function: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"Internal server error: {str(e)}"
            }),
            mimetype="application/json",
            status_code=500
        )
