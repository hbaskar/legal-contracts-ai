"""
Blob Trigger Function for Automatic Document Processing
Automatically processes documents when uploaded to Azure Blob Storage
"""

import azure.functions as func
import logging
import tempfile
import os
from datetime import datetime

# Import AI services functionality
from contracts.ai_services import process_document_with_ai_keyphrases
from config.config import config

# Configure logging
logger = logging.getLogger(__name__)

async def blob_trigger_main(myblob: func.InputStream) -> None:
    """
    Azure Function triggered when a new blob is uploaded to the container
    Automatically processes the document using AI services
    """
    try:
        blob_name = myblob.name
        blob_size = len(myblob.read())
        myblob.seek(0)  # Reset stream position
        
        logger.info(f'🚀 Blob trigger function processed blob: {blob_name}, Size: {blob_size} bytes')
        
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
            ai_available = True
        except ImportError:
            logger.warning("⚠️ AI services not available, skipping document processing")
            return
        
        # Create temporary file with the blob content
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            # Read blob content and write to temp file
            blob_content = myblob.read()
            temp_file.write(blob_content)
            temp_file_path = temp_file.name
        
        try:
            logger.info(f"📄 Processing document: {filename} ({blob_size} bytes)")
            
            # Process the document with AI services
            # Use intelligent chunking by default for blob trigger
            result = await process_document_with_ai_keyphrases(
                file_path=temp_file_path,
                filename=filename,
                force_reindex=True,  # Always reindex for blob trigger to avoid duplicates
                chunking_method="intelligent"  # Use best chunking method
            )
            
            if result["status"] == "success":
                logger.info(f"✅ Successfully processed {filename}")
                logger.info(f"   📊 Created {result['chunks_created']} chunks")
                logger.info(f"   ☁️ Uploaded {result['successful_uploads']} to search index")
                logger.info(f"   🧠 Enhancement: {result['enhancement']}")
                
                # Log chunk details for monitoring
                for i, chunk_detail in enumerate(result.get('chunk_details', [])[:3]):  # Log first 3 chunks
                    logger.info(f"   Chunk {i+1}: {chunk_detail['title']} ({chunk_detail['content_size']} chars)")
                
                if result.get('failed_uploads', 0) > 0:
                    logger.warning(f"⚠️ {result['failed_uploads']} chunks failed to upload")
                    
            else:
                logger.error(f"❌ Failed to process {filename}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Error processing document {filename}: {str(e)}")
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
                logger.debug(f"🧹 Cleaned up temporary file for {filename}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")
        
    except Exception as e:
        logger.error(f"❌ Blob trigger error: {str(e)}")
        # Don't raise the exception to avoid infinite retries
        # The blob trigger will mark this as processed even if we don't raise