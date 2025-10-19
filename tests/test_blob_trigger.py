"""
Test script for blob trigger functionality
Simulates uploading a file directly to blob storage to trigger automatic processing
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.storage.blob import BlobServiceClient
from config.config import config
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_blob_trigger_upload():
    """
    Test uploading a file directly to blob storage
    This should trigger the blob trigger function for automatic processing
    """
    
    if not config.AZURE_STORAGE_CONNECTION_STRING:
        print("❌ AZURE_STORAGE_CONNECTION_STRING not configured")
        return
    
    try:
        # Create a test document
        test_content = """
        SAMPLE LEGAL CONTRACT
        
        This is a test contract for demonstrating automatic document processing.
        
        SECTION 1: PARTIES
        This agreement is between Company A and Company B.
        
        SECTION 2: TERMS
        The terms of this agreement include payment, delivery, and obligations.
        
        SECTION 3: PAYMENT
        Payment shall be made within 30 days of invoice receipt.
        
        SECTION 4: TERMINATION
        Either party may terminate this agreement with 30 days written notice.
        """
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload to blob storage
            blob_service = BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
            
            # Generate unique filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            blob_name = f"test_contract_{timestamp}.txt"
            
            blob_client = blob_service.get_blob_client(
                container=config.AZURE_STORAGE_CONTAINER_NAME,
                blob=blob_name
            )
            
            print(f"🚀 Uploading test document to blob storage...")
            print(f"   📁 Container: {config.AZURE_STORAGE_CONTAINER_NAME}")
            print(f"   📄 Filename: {blob_name}")
            
            with open(temp_file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True)
            
            print(f"✅ Successfully uploaded {blob_name}")
            print(f"📋 File size: {len(test_content)} bytes")
            print()
            print("🎯 Expected blob trigger behavior:")
            print("   1. Blob trigger function should fire automatically")
            print("   2. Document will be processed with AI services")
            print("   3. Content will be chunked intelligently")
            print("   4. Chunks will be indexed to Azure Search")
            print("   5. Check function logs for processing status")
            print()
            print("📊 To monitor processing:")
            print("   - Check Azure Function logs")
            print("   - Look for 'ProcessUploadedDocument' function execution")
            print("   - Verify chunks in Azure Search index")
            
            return blob_name
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error testing blob trigger: {str(e)}")
        return None

def check_blob_exists(blob_name: str) -> bool:
    """Check if the uploaded blob exists in storage"""
    try:
        blob_service = BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service.get_blob_client(
            container=config.AZURE_STORAGE_CONTAINER_NAME,
            blob=blob_name
        )
        
        properties = blob_client.get_blob_properties()
        print(f"✅ Blob exists: {blob_name}")
        print(f"   📏 Size: {properties.size} bytes")
        print(f"   📅 Created: {properties.creation_time}")
        return True
        
    except Exception as e:
        print(f"❌ Blob not found: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Blob Trigger for Automatic Document Processing")
    print("=" * 60)
    
    # Test configuration
    print("🔧 Configuration check:")
    print(f"   Storage configured: {'✅' if config.AZURE_STORAGE_CONNECTION_STRING else '❌'}")
    print(f"   Container: {config.AZURE_STORAGE_CONTAINER_NAME}")
    print(f"   OpenAI configured: {'✅' if config.AZURE_OPENAI_ENDPOINT else '❌'}")
    print(f"   Search configured: {'✅' if config.AZURE_SEARCH_ENDPOINT else '❌'}")
    print()
    
    if not config.AZURE_STORAGE_CONNECTION_STRING:
        print("❌ Cannot test without storage configuration")
        exit(1)
    
    # Upload test file
    blob_name = test_blob_trigger_upload()
    
    if blob_name:
        print()
        print("⏳ Waiting 5 seconds for blob trigger to process...")
        time.sleep(5)
        
        # Verify blob exists
        check_blob_exists(blob_name)
        
        print()
        print("📝 Next steps:")
        print("   1. Start Azure Functions locally: func start")
        print("   2. Upload another file to trigger processing")
        print("   3. Monitor logs for automatic processing")
        print("   4. Check Azure Search for indexed content")
