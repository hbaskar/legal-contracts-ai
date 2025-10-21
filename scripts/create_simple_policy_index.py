#!/usr/bin/env python3
"""
Simple script to create the Azure Search Policy Index without vector search
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

def create_simple_policy_index():
    """Create a simple policy index without vector search"""
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            SearchIndex, SimpleField, SearchableField, SearchField,
            SearchFieldDataType
        )
        from config.config import config
        
        # Create search client
        client = SearchIndexClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
        )
        
        index_name = config.AZURE_SEARCH_POLICY_INDEX
        
        # Check if index already exists
        try:
            existing_index = client.get_index(index_name)
            if existing_index:
                return {
                    "status": "exists",
                    "message": f"Index '{index_name}' already exists",
                    "index_name": index_name
                }
        except Exception:
            # Index doesn't exist, we'll create it
            pass
        
        # Define index fields (without vector search for compatibility)
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True),
            SimpleField(name="PolicyId", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="instruction", type=SearchFieldDataType.String),  # Main policy content
            SearchableField(name="summary", type=SearchFieldDataType.String),
            SearchField(
                name="tags", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.String), 
                filterable=True, 
                facetable=True
            ),
            SimpleField(name="locked", type=SearchFieldDataType.Boolean, filterable=True),
            SearchField(
                name="groups", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.String), 
                filterable=True
            ),  # Access control
            SimpleField(name="severity", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="original_text", type=SearchFieldDataType.String)
        ]
        
        # Create the index (without vector search for now)
        index = SearchIndex(
            name=index_name,
            fields=fields
        )
        
        client.create_index(index)
        
        return {
            "status": "created",
            "message": f"Successfully created policy index '{index_name}'",
            "index_name": index_name,
            "fields_count": len(fields)
        }
        
    except Exception as e:
        logger.error(f"Error creating policy index: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "index_name": index_name if 'index_name' in locals() else "unknown"
        }

def main():
    """Create the policy index"""
    try:
        print("🚀 Azure Search Policy Index Creation (Simple)")
        print("=" * 50)
        
        from config.config import config
        print(f"📍 Search Endpoint: {config.AZURE_SEARCH_ENDPOINT}")
        print(f"📑 Policy Index Name: {config.AZURE_SEARCH_POLICY_INDEX}")
        print()
        
        # Create the policy index
        print("🔨 Creating policy index...")
        result = create_simple_policy_index()
        
        # Display results
        print(f"📊 Status: {result['status']}")
        print(f"💬 Message: {result['message']}")
        print(f"🏷️ Index Name: {result['index_name']}")
        
        if result['status'] == 'created':
            print(f"📈 Fields Count: {result['fields_count']}")
            print()
            print("✅ Policy index created successfully!")
            print()
            print("🔍 Index Fields (without vector search):")
            print("- id (key field)")
            print("- PolicyId (filterable)")
            print("- filename (filterable)")
            print("- title (searchable)")
            print("- instruction (searchable - main policy content)")
            print("- summary (searchable)")
            print("- tags (filterable, facetable collection)")
            print("- locked (boolean, filterable)")
            print("- groups (filterable collection - access control)")
            print("- severity (integer, filterable)")
            print("- language (filterable)")
            print("- original_text (searchable)")
            print()
            print("⚠️ Note: Vector search (embeddings) not included due to SDK compatibility")
        elif result['status'] == 'exists':
            print("ℹ️ Index already exists - no action needed")
        else:
            print("❌ Failed to create policy index")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    print("\n🎉 Policy index setup complete!")