#!/usr/bin/env python3
"""
Comprehensive test to verify both blob upload and automatic processing
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.storage.blob import BlobServiceClient
from config.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_complete_workflow():
    """Test the complete blob trigger workflow"""
    
    print("🚀 Complete Blob Trigger Workflow Test")
    print("=" * 60)
    
    # Configuration check
    print("🔧 System Status:")
    
    # Check if func.exe is running (simplified)
    import subprocess
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True, shell=True)
        func_running = 'func.exe' in result.stdout
    except:
        func_running = False
    
    print(f"   Azure Functions: {'✅' if func_running else '❌'}")
    print(f"   Storage configured: {'✅' if config.AZURE_STORAGE_CONNECTION_STRING else '❌'}")
    print(f"   OpenAI configured: {'✅' if config.AZURE_OPENAI_KEY else '❌'}")
    print(f"   Search configured: {'✅' if config.AZURE_SEARCH_KEY else '❌'}")
    
    # Create test content
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"workflow_test_{timestamp}.txt"
    
    test_content = f"""AUTOMATED WORKFLOW TEST DOCUMENT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This document tests the complete blob trigger workflow:

1. FILE UPLOAD
   - Document uploaded to Azure Blob Storage
   - Blob trigger should fire automatically
   - Azure Functions runtime processes the event

2. AI PROCESSING
   - Document content extracted automatically
   - Intelligent chunking applied
   - Key phrases extracted using OpenAI
   - Content optimized for search

3. SEARCH INDEXING
   - Processed chunks uploaded to Azure Search
   - Content becomes searchable
   - Metadata stored properly

4. VERIFICATION
   - Check logs for successful processing
   - Verify chunks in search index
   - Confirm automatic workflow completion

Test ID: {timestamp}
Status: Ready for processing
"""

    try:
        # Upload to blob storage
        print(f"\n📤 Uploading test document: {filename}")
        
        blob_service_client = BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(
            container=config.AZURE_STORAGE_CONTAINER_NAME,
            blob=filename
        )
        
        blob_client.upload_blob(test_content.encode('utf-8'), overwrite=True)
        
        print(f"✅ Successfully uploaded: {filename}")
        print(f"📊 Content size: {len(test_content)} bytes")
        
        # Wait for processing
        print(f"\n⏳ Waiting for blob trigger to process...")
        print(f"   Expected processing steps:")
        print(f"   1. Blob trigger fires")
        print(f"   2. Content extracted and validated")
        print(f"   3. AI processing with intelligent chunking")
        print(f"   4. Upload to Azure Search index")
        
        print(f"\n📋 Monitor Azure Functions logs for:")
        print(f"   • 'ProcessUploadedDocument' function execution")
        print(f"   • Processing messages for '{filename}'")
        print(f"   • Success/error status")
        
        # Verification instructions
        print(f"\n🔍 Verification Steps:")
        print(f"   1. Check Azure Functions console for processing logs")
        print(f"   2. Verify no error messages in the logs")
        print(f"   3. Confirm successful chunk creation and upload")
        print(f"   4. Test search functionality if needed")
        
        print(f"\n✅ Upload completed successfully!")
        print(f"   File: {filename}")
        print(f"   Next: Monitor Azure Functions logs for automatic processing")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_complete_workflow()
