#!/usr/bin/env python3
"""
Test OpenAI Error Handling
Tests the improved error handling for OpenAI API calls
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging to see the detailed error messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    from contracts.ai_services import extract_keyphrases_with_openai, generate_text_embedding
    from config.config import config
    
    def test_openai_error_handling():
        """Test that the OpenAI error handling works correctly"""
        print("🧪 Testing OpenAI Error Handling...")
        
        # Test 1: Simple keyphrase extraction (most likely to trigger JSON parsing issues)
        print("\n1. Testing keyphrase extraction...")
        test_text = """
        This is a test document for validating OpenAI error handling.
        We want to make sure that JSON parsing errors are handled gracefully.
        """
        
        try:
            keyphrases = extract_keyphrases_with_openai(test_text, "test")
            print(f"   ✅ Keyphrase extraction successful: {len(keyphrases)} phrases")
            print(f"   📝 Sample phrases: {keyphrases[:3]}")
        except Exception as e:
            print(f"   ❌ Keyphrase extraction failed: {e}")
        
        # Test 2: Embedding generation
        print("\n2. Testing embedding generation...")
        try:
            embedding = generate_text_embedding("Test text for embedding")
            print(f"   ✅ Embedding generation successful: {len(embedding)} dimensions")
        except Exception as e:
            print(f"   ❌ Embedding generation failed: {e}")
        
        print("\n🎯 OpenAI error handling test completed!")

    if __name__ == "__main__":
        # Check configuration
        if not config.AZURE_OPENAI_ENDPOINT:
            print("❌ Azure OpenAI endpoint not configured")
            sys.exit(1)
        
        test_openai_error_handling()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the tests directory")
    sys.exit(1)
