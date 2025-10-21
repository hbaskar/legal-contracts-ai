#!/usr/bin/env python3
"""
Script to create the Azure Search Policy Index
Uses the AZURE_SEARCH_POLICY_INDEX configuration from environment
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Create the policy index using the specified fields"""
    try:
        # Import after setting up the path
        from contracts.index_creation import create_policy_index_if_not_exists
        from config.config import config
        
        print("🚀 Azure Search Policy Index Creation")
        print("=" * 50)
        print(f"📍 Search Endpoint: {config.AZURE_SEARCH_ENDPOINT}")
        print(f"📑 Policy Index Name: {config.AZURE_SEARCH_POLICY_INDEX}")
        print()
        
        # Create the policy index
        print("🔨 Creating policy index...")
        result = create_policy_index_if_not_exists()
        
        # Display results
        print(f"📊 Status: {result['status']}")
        print(f"💬 Message: {result['message']}")
        print(f"🏷️ Index Name: {result['index_name']}")
        
        if result['status'] == 'created':
            print(f"📈 Fields Count: {result['fields_count']}")
            print()
            print("✅ Policy index created successfully!")
            print()
            print("🔍 Index Fields:")
            print("- id (key field)")
            print("- PolicyId (filterable)")
            print("- filename (filterable)")
            print("- title (searchable)")
            print("- instruction (searchable - main policy content)")
            print("- summary (searchable)")
            print("- embedding (vector search, 1536 dimensions)")
            print("- tags (filterable, facetable collection)")
            print("- locked (boolean, filterable)")
            print("- groups (filterable collection - access control)")
            print("- severity (integer, filterable)")
            print("- language (filterable)")
            print("- original_text (searchable)")
        elif result['status'] == 'exists':
            print("ℹ️ Index already exists - no action needed")
        else:
            print("❌ Failed to create policy index")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error creating policy index: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    print("\n🎉 Policy index setup complete!")