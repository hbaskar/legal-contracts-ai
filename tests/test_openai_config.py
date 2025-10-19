#!/usr/bin/env python3
"""
Azure OpenAI Configuration Test
Validates Azure OpenAI configuration and connectivity
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    from config.config import config
    
    def test_azure_openai_config():
        """Test Azure OpenAI configuration"""
        print("🔧 Testing Azure OpenAI Configuration...")
        
        # Test 1: Check environment variables
        print("\n1. Checking environment variables...")
        
        required_vars = [
            ('AZURE_OPENAI_ENDPOINT', config.AZURE_OPENAI_ENDPOINT),
            ('AZURE_OPENAI_KEY', config.AZURE_OPENAI_KEY),
            ('AZURE_OPENAI_API_VERSION', config.AZURE_OPENAI_API_VERSION),
            ('AZURE_OPENAI_MODEL_DEPLOYMENT', config.AZURE_OPENAI_MODEL_DEPLOYMENT),
            ('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT),
        ]
        
        config_ok = True
        for var_name, var_value in required_vars:
            if var_value:
                if 'KEY' in var_name:
                    print(f"   ✅ {var_name}: {'*' * len(str(var_value))} (hidden)")
                else:
                    print(f"   ✅ {var_name}: {var_value}")
            else:
                print(f"   ❌ {var_name}: NOT SET")
                config_ok = False
        
        if not config_ok:
            print("\n❌ Configuration incomplete. Please check your .env file.")
            return False
        
        # Test 2: Try to initialize OpenAI client
        print("\n2. Testing OpenAI client initialization...")
        try:
            from contracts.ai_services import get_openai_client
            client = get_openai_client()
            print("   ✅ OpenAI client initialized successfully")
            
            # Test 3: Simple API call
            print("\n3. Testing basic API connectivity...")
            try:
                # Try a simple embedding call (less likely to have JSON issues)
                from contracts.ai_services import generate_text_embedding
                embedding = generate_text_embedding("test")
                print(f"   ✅ API call successful - embedding dimensions: {len(embedding)}")
                
                # Test 4: Try a chat completion
                print("\n4. Testing chat completion...")
                from openai import AzureOpenAI
                test_client = AzureOpenAI(
                    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                    api_key=config.AZURE_OPENAI_KEY,
                    api_version=config.AZURE_OPENAI_API_VERSION,
                )
                
                response = test_client.chat.completions.create(
                    model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                    messages=[{"role": "user", "content": "Say 'Hello' in exactly one word."}],
                    max_tokens=10,
                    temperature=0
                )
                
                if response and response.choices:
                    content = response.choices[0].message.content
                    print(f"   ✅ Chat completion successful: '{content}'")
                    
                    # Check if response is valid JSON-like when requested
                    print("\n5. Testing JSON response format...")
                    json_response = test_client.chat.completions.create(
                        model=config.AZURE_OPENAI_MODEL_DEPLOYMENT,
                        messages=[{"role": "user", "content": "Return a JSON object with one key 'test' and value 'success'"}],
                        response_format={"type": "json_object"},
                        max_tokens=50,
                        temperature=0
                    )
                    
                    if json_response and json_response.choices:
                        json_content = json_response.choices[0].message.content
                        print(f"   ✅ JSON response received: {json_content}")
                        
                        # Try to parse it
                        import json
                        try:
                            parsed = json.loads(json_content)
                            print(f"   ✅ JSON parsing successful: {parsed}")
                        except json.JSONDecodeError as e:
                            print(f"   ❌ JSON parsing failed: {e}")
                            print(f"   Raw content: {json_content}")
                    else:
                        print("   ❌ No JSON response received")
                else:
                    print("   ❌ No response received")
                    
            except Exception as e:
                print(f"   ❌ API call failed: {e}")
                return False
                
        except Exception as e:
            print(f"   ❌ OpenAI client initialization failed: {e}")
            return False
        
        print("\n✅ All configuration tests passed!")
        return True

    if __name__ == "__main__":
        success = test_azure_openai_config()
        if not success:
            print("\n💡 Troubleshooting tips:")
            print("   - Check your .env file has all required variables")
            print("   - Verify your Azure OpenAI endpoint URL is correct")
            print("   - Confirm your API key is valid and not expired")
            print("   - Make sure your model deployment names match exactly")
            print("   - Test your Azure OpenAI service in the Azure portal")
            sys.exit(1)
        else:
            print("\n🎉 Configuration is working correctly!")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the tests directory")
    sys.exit(1)
