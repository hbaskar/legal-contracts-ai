#!/usr/bin/env python3
"""
Test script to verify AI document processing is working
This simulates what the blob trigger should do
"""

import os
import sys
import tempfile
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ai_processing():
    """Test AI document processing functionality"""
    
    print("🧪 Testing AI Document Processing")
    print("=" * 50)
    
    # Check configuration
    print("🔧 Configuration check:")
    print(f"   OpenAI configured: {'✅' if config.AZURE_OPENAI_KEY else '❌'}")
    print(f"   Search configured: {'✅' if config.AZURE_SEARCH_KEY else '❌'}")
    
    try:
        # Import AI services
        from contracts.ai_services import process_document_with_ai_keyphrases
        print("   AI services: ✅")
    except ImportError as e:
        print(f"   AI services: ❌ ({e})")
        return
    
    # Create a test document
    test_content = """
    CONTRACT AGREEMENT
    
    This is a test contract document for AI processing.
    
    SECTION 1: PURPOSE
    This document serves as a test case for the automatic document processing system.
    The system should extract key phrases and chunk this content intelligently.
    
    SECTION 2: REQUIREMENTS
    - The document should be processed automatically when uploaded
    - Content should be chunked using intelligent methods
    - Key phrases should be extracted using AI services
    - Results should be indexed in Azure Search
    
    SECTION 3: CONCLUSION
    This test document contains various sections and content types to verify
    the AI processing capabilities of the system.
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(test_content)
        temp_file_path = temp_file.name
    
    try:
        print(f"\n📄 Processing test document...")
        print(f"   📁 File: {os.path.basename(temp_file_path)}")
        print(f"   📊 Content length: {len(test_content)} characters")
        
        # Process the document
        result = await process_document_with_ai_keyphrases(
            file_path=temp_file_path,
            filename="test_ai_processing.txt",
            force_reindex=True,
            chunking_method="intelligent"
        )
        
        print(f"\n📋 Processing Results:")
        print(f"   Status: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            print(f"   ✅ Chunks created: {result.get('chunks_created', 0)}")
            print(f"   ✅ Successful uploads: {result.get('successful_uploads', 0)}")
            print(f"   ✅ Total chunks: {result.get('total_chunks', 0)}")
            
            # Show chunk details
            chunks = result.get('chunk_details', [])
            if chunks:
                print(f"\n📝 Chunk Details:")
                for i, chunk in enumerate(chunks[:3]):  # Show first 3
                    print(f"   {i+1}. '{chunk['title']}' ({chunk['content_size']} chars)")
            
            print(f"\n🎯 Result: AI processing is working correctly! ✅")
            
        else:
            print(f"   ❌ Error: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        
    finally:
        # Clean up
        try:
            os.unlink(temp_file_path)
            print(f"\n🧹 Cleaned up temporary file")
        except:
            pass

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_processing())
