# Import additional modules for index creation
import logging
from typing import Dict
from datetime import datetime
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    HnswParameters, VectorSearchProfile
)

# Import configuration
from config.config import config

# Configure logging
logger = logging.getLogger(__name__)

def create_document_index_if_not_exists(index_name: str = None) -> Dict:
    """
    Create the legal documents index if it doesn't exist
    Based on the schema from contract_indexing.py
    
    Returns:
        Dict with status, message, and operation details
    """
    if index_name is None:
        index_name = config.AZURE_SEARCH_DOC_INDEX
    
    try:
        logger.info(f"🔍 Checking if Azure Search index '{index_name}' exists...")
        
        client = SearchIndexClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
        )
        
        # Check if index already exists
        try:
            existing_index = client.get_index(index_name)
            if existing_index:
                logger.info(f"✅ Index '{index_name}' already exists")
                return {
                    "status": "exists",
                    "message": f"Index '{index_name}' already exists",
                    "index_name": index_name,
                    "operation": "check_existence"
                }
        except Exception:
            # Index doesn't exist, we'll create it
            logger.info(f"📋 Index '{index_name}' not found, creating new index...")
            pass
        
        # Define index fields (based on legal-documents schema)
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="ParagraphId", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SearchableField(name="title", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="paragraph", type=SearchFieldDataType.String),
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=1536, 
                vector_search_profile_name="vsProfile"
            ),
            SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="isCompliant", type=SearchFieldDataType.Boolean, filterable=True),
            SearchField(name="CompliantCollection", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchField(name="NonCompliantCollection", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchField(name="IrrelevantCollection", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchField(name="group", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchField(name="keyphrases", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
            SearchableField(name="summary", type=SearchFieldDataType.String),
            SimpleField(name="department", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="date", type=SearchFieldDataType.String, filterable=True, sortable=True),
        ]
        
        # Configure vector search with profiles (current SDK format)
        vector_config = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(
                name="vsAlgo",
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500
                )
            )],
            profiles=[VectorSearchProfile(
                name="vsProfile",
                algorithm_configuration_name="vsAlgo"
            )]
        )
        
        # Create the index
        logger.info(f"🏗️ Creating Azure Search index '{index_name}'...")
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_config
        )
        
        created_index = client.create_index(index)
        logger.info(f"✅ Successfully created index '{index_name}'")
        
        return {
            "status": "created",
            "message": f"Successfully created index '{index_name}'",
            "index_name": index_name,
            "fields_count": len(fields),
            "operation": "create_index"
        }
        
    except Exception as e:
        logging.error(f"Error creating document index: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "index_name": index_name
        }

def create_policy_index_if_not_exists(index_name: str = None) -> Dict:
    """
    Create the legal instructions/policies index if it doesn't exist
    Uses AZURE_SEARCH_POLICY_INDEX from configuration
    """
    if index_name is None:
        index_name = config.AZURE_SEARCH_POLICY_INDEX
    try:
        client = SearchIndexClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
        )
        
        # Check if index already exists
        existing_indexes = [idx.name for idx in client.list_indexes()]
        if index_name in existing_indexes:
            return {
                "status": "exists",
                "message": f"Index '{index_name}' already exists",
                "index_name": index_name
            }
        
        # Define index fields for policy index (with vector search support)
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True),
            SimpleField(name="PolicyId", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="instruction", type=SearchFieldDataType.String),  # Main policy content
            SearchableField(name="summary", type=SearchFieldDataType.String),
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=1536, 
                vector_search_profile_name="policyVsProfile"
            ),
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
        
        # Configure vector search for policies
        vector_config = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(
                name="policyVsAlgo",
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500
                )
            )],
            profiles=[VectorSearchProfile(
                name="policyVsProfile",
                algorithm_configuration_name="policyVsAlgo"
            )]
        )
        
        # Create the policy index with vector search support
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_config
        )
        
        client.create_index(index)
        
        return {
            "status": "created",
            "message": f"Successfully created index '{index_name}'",
            "index_name": index_name,
            "fields_count": len(fields)
        }
        
    except Exception as e:
        logging.error(f"Error creating policy index: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "index_name": index_name
        }

def ensure_search_index_exists(index_name: str = None) -> Dict:
    """
    Ensure the Azure Search index exists, creating it if necessary.
    This is the main function that should be called before any search operations.
    
    Args:
        index_name: Optional index name, defaults to configured index
        
    Returns:
        Dict with status and operation details
    """
    if index_name is None:
        index_name = config.AZURE_SEARCH_DOC_INDEX
    
    logger.info(f"🔍 Ensuring Azure Search index '{index_name}' is ready...")
    
    try:
        # Validate configuration first
        if not config.AZURE_SEARCH_ENDPOINT:
            return {
                "status": "error",
                "message": "AZURE_SEARCH_ENDPOINT not configured",
                "operation": "validate_config"
            }
        
        if not config.AZURE_SEARCH_KEY:
            return {
                "status": "error", 
                "message": "AZURE_SEARCH_KEY not configured",
                "operation": "validate_config"
            }
        
        # Create the index if it doesn't exist
        result = create_document_index_if_not_exists(index_name)
        
        if result["status"] in ["created", "exists"]:
            logger.info(f"✅ Index '{index_name}' is ready for use")
            return {
                **result,
                "ready": True
            }
        else:
            logger.error(f"❌ Failed to ensure index exists: {result['message']}")
            return {
                **result,
                "ready": False
            }
            
    except Exception as e:
        logger.error(f"❌ Error ensuring index exists: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to ensure index exists: {str(e)}",
            "operation": "ensure_index",
            "ready": False
        }

def setup_all_indexes() -> Dict:
    """
    Set up both document and policy indexes
    """
    results = {}
    
    print("Creating document index...")
    doc_result = create_document_index_if_not_exists()
    results["document_index"] = doc_result
    print(f"Document index: {doc_result['message']}")
    
    print("Creating policy index...")
    policy_result = create_policy_index_if_not_exists()
    results["policy_index"] = policy_result
    print(f"Policy index: {policy_result['message']}")
    
    return results

print("Index management functions defined successfully!")