def main():
    print("Starting system reset...")
    results = {}
    print("Deleting all blobs from Azure Storage container...")
    results["storage"] = delete_all_storage_files()
    print(f"   Status: {results['storage']['status']}")
    print(f"   Message: {results['storage']['message']}")
    print()
    print("Resetting database tables...")
    results["database"] = reset_database()
    db_status = results["database"].get("status", "unknown")
    db_message = results["database"].get("message", str(results["database"]))
    print(f"   Status: {db_status}")
    print(f"   Message: {db_message}")
    print()
    print("Deleting Azure Search indexes...")
    results["indexes"] = delete_search_indexes()
    print(f"   Status: {results['indexes']['status']}")
    print(f"   Message: {results['indexes']['message']}")
    print()
    successful_operations = sum(1 for r in results.values() if r["status"] == "success")
    partial_operations = sum(1 for r in results.values() if r["status"] == "partial")
    failed_operations = sum(1 for r in results.values() if r["status"] == "error")
    if failed_operations == 0 and partial_operations == 0:
        overall_status = "success"
        message = "Complete system reset successful!"
    elif failed_operations == 0:
        overall_status = "partial"
        message = "System reset completed with some warnings"
    else:
        overall_status = "error"
        message = "System reset completed with errors"
    print("RESET SUMMARY:")
    print(f"   Successful operations: {successful_operations}")
    print(f"   Partial operations: {partial_operations}")
    print(f"   Failed operations: {failed_operations}")
    print()
    print(message)
    return {
        "status": overall_status,
        "message": message,
        "results": results,
        "summary": {
            "successful": successful_operations,
            "partial": partial_operations,
            "failed": failed_operations
        }
    }
def reset_database() -> dict:
    """Reset all tables in the database using DatabaseManager"""
    try:
        from config.database import DatabaseManager
        import asyncio
        db_mgr = DatabaseManager()

        async def run_reset():
            await db_mgr.initialize() if hasattr(db_mgr, 'initialize') else None
            return await db_mgr.reset_all_tables()

        try:
            loop = asyncio.get_running_loop()
            # If already in an event loop, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_reset())
                reset_results = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            reset_results = asyncio.run(run_reset())
        return reset_results
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to reset database: {str(e)}"
        }
#!/usr/bin/env python3
"""
Reset Function for Fresh Start Document Processing System
Provides comprehensive reset functionality including:
- Delete all files from Azure Storage container
- Reset database (clear all tables)
- Delete Azure Search indexes
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def delete_all_storage_files() -> Dict:
    """Delete all files from the Azure Storage container"""
    try:
        from azure.storage.blob import BlobServiceClient
        from config.config import config
        blob_service_client = BlobServiceClient.from_connection_string(config.AZURE_STORAGE_CONNECTION_STRING)
        container_name = config.AZURE_CONTRACTS_CONTAINER
        container_client = blob_service_client.get_container_client(container_name)
        blob_list = list(container_client.list_blobs())
        deleted_count = 0
        failed_deletions = []
        for blob in blob_list:
            try:
                container_client.delete_blob(blob.name)
                deleted_count += 1
            except Exception as e:
                failed_deletions.append(blob.name)
                logger.error(f"Failed to delete blob {blob.name}: {str(e)}")
        if not blob_list:
            return {
                "status": "partial",
                "message": "No blobs found to delete.",
                "deleted_count": 0,
                "failed_deletions": []
            }
        elif failed_deletions:
            return {
                "status": "partial",
                "message": f"Deleted {deleted_count} files, {len(failed_deletions)} failed",
                "deleted_count": deleted_count,
                "failed_deletions": failed_deletions
            }
        else:
            return {
                "status": "success",
                "message": f"Successfully deleted all {deleted_count} files from container '{container_name}'",
                "deleted_count": deleted_count
            }
    except Exception as e:
        logger.error(f"Error deleting storage files: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to delete storage files: {str(e)}",
            "deleted_count": 0
        }
        
        db_mgr = DatabaseManager()
        
        # Check if we're already in an async context
        import asyncio
        
        async def reset_db():
            await db_mgr.initialize()
            
            # Use the existing reset_all_tables method
            reset_results = await db_mgr.reset_all_tables()
            
            return reset_results
        
        # Handle both sync and async contexts
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to run this differently
            # For now, we'll create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, reset_db())
                reset_results = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            reset_results = asyncio.run(reset_db())
        
        # Map the existing results to our expected format
        if reset_results["summary"]["tables_with_errors"] == 0:
            status = "success"
            message = f"Database reset complete. Reset {reset_results['summary']['tables_reset_successfully']} tables, deleted {reset_results['total_records_deleted']} records"
        else:
            status = "partial"
            message = f"Database reset completed with warnings. Reset {reset_results['summary']['tables_reset_successfully']} tables successfully, {reset_results['summary']['tables_with_errors']} with errors"
        
        return {
            "status": status,
            "message": message,
            "tables_reset": reset_results["tables_reset"],
            "tables_with_errors": reset_results["tables_with_errors"],
            "total_records_deleted": reset_results["total_records_deleted"],
            "summary": reset_results["summary"]
        }

def delete_search_indexes() -> Dict:
    """Delete both document and policy search indexes"""
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from config.config import config
    client = SearchIndexClient(
        endpoint=config.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(config.AZURE_SEARCH_KEY)
    )
    indexes_to_delete = [
        config.AZURE_SEARCH_DOC_INDEX,
        config.AZURE_SEARCH_POLICY_INDEX
    ]
    deleted_indexes = []
    failed_deletions = []
    for index_name in indexes_to_delete:
        try:
            client.get_index(index_name)
            client.delete_index(index_name)
            deleted_indexes.append(index_name)
            logger.info(f"Deleted index: {index_name}")
        except Exception as get_error:
            if "not found" in str(get_error).lower() or "404" in str(get_error):
                logger.info(f"Index {index_name} does not exist, skipping")
            else:
                failed_deletions.append(f"{index_name}: {str(get_error)}")
                logger.error(f"Failed to delete index {index_name}: {str(get_error)}")
    if failed_deletions:
        return {
            "status": "partial",
            "message": f"Deleted {len(deleted_indexes)} indexes, {len(failed_deletions)} failed",
            "deleted_indexes": deleted_indexes,
            "failed_deletions": failed_deletions
        }
    else:
        return {
            "status": "success",
            "message": f"Successfully deleted {len(deleted_indexes)} search indexes",
            "deleted_indexes": deleted_indexes
        }

if __name__ == "__main__":
    main()