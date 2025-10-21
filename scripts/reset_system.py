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
        
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(
            config.AZURE_STORAGE_CONNECTION_STRING
        )
        
        container_name = config.AZURE_STORAGE_CONTAINER_NAME
        container_client = blob_service_client.get_container_client(container_name)
        
        # List all blobs in the container
        blob_list = list(container_client.list_blobs())
        
        if not blob_list:
            return {
                "status": "success",
                "message": f"Container '{container_name}' is already empty",
                "deleted_count": 0
            }
        
        # Delete all blobs
        deleted_count = 0
        failed_deletions = []
        
        for blob in blob_list:
            try:
                container_client.delete_blob(blob.name)
                deleted_count += 1
                logger.info(f"Deleted blob: {blob.name}")
            except Exception as e:
                failed_deletions.append(f"{blob.name}: {str(e)}")
                logger.error(f"Failed to delete blob {blob.name}: {str(e)}")
        
        if failed_deletions:
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

def reset_database() -> Dict:
    """Reset the database by clearing all tables using existing functionality"""
    try:
        from config.database import DatabaseManager
        
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
        
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to reset database: {str(e)}"
        }

def delete_search_indexes() -> Dict:
    """Delete both document and policy search indexes"""
    try:
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
                # Check if index exists first
                try:
                    client.get_index(index_name)
                    # Index exists, delete it
                    client.delete_index(index_name)
                    deleted_indexes.append(index_name)
                    logger.info(f"Deleted index: {index_name}")
                except Exception as get_error:
                    if "not found" in str(get_error).lower() or "404" in str(get_error):
                        logger.info(f"Index {index_name} does not exist, skipping")
                    else:
                        raise get_error
                        
            except Exception as e:
                failed_deletions.append(f"{index_name}: {str(e)}")
                logger.error(f"Failed to delete index {index_name}: {str(e)}")
        
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
            
    except Exception as e:
        logger.error(f"Error deleting search indexes: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to delete search indexes: {str(e)}"
        }

def full_system_reset(confirm: bool = False) -> Dict:
    """
    Perform a complete system reset
    
    Args:
        confirm: Must be True to actually perform the reset
    
    Returns:
        Dict with reset results
    """
    if not confirm:
        return {
            "status": "cancelled",
            "message": "Reset cancelled - confirmation required. Call with confirm=True to proceed."
        }
    
    print("PERFORMING COMPLETE SYSTEM RESET")
    print("=" * 50)
    
    results = {
        "storage": {"status": "not_attempted"},
        "database": {"status": "not_attempted"},
        "indexes": {"status": "not_attempted"}
    }
    
    # 1. Delete all storage files
    print("Deleting all files from Azure Storage...")
    results["storage"] = delete_all_storage_files()
    print(f"   Status: {results['storage']['status']}")
    print(f"   Message: {results['storage']['message']}")
    print()
    
    # 2. Reset database
    print("Resetting database...")
    results["database"] = reset_database()
    print(f"   Status: {results['database']['status']}")
    print(f"   Message: {results['database']['message']}")
    if results["database"].get("tables_reset"):
        print(f"   Tables reset: {', '.join(results['database']['tables_reset'])}")
    if results["database"].get("total_records_deleted"):
        print(f"   Records deleted: {results['database']['total_records_deleted']}")
    print()
    
    # 3. Delete search indexes
    print("Deleting Azure Search indexes...")
    results["indexes"] = delete_search_indexes()
    print(f"   Status: {results['indexes']['status']}")
    print(f"   Message: {results['indexes']['message']}")
    print()
    
    # Summary
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

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset Fresh Start Document Processing System')
    parser.add_argument('--storage', action='store_true', help='Delete all files from storage container')
    parser.add_argument('--database', action='store_true', help='Reset database')
    parser.add_argument('--indexes', action='store_true', help='Delete search indexes')
    parser.add_argument('--all', action='store_true', help='Perform complete system reset')
    parser.add_argument('--confirm', action='store_true', help='Confirm the reset operation')
    
    args = parser.parse_args()
    
    if not any([args.storage, args.database, args.indexes, args.all]):
        parser.print_help()
        print("\n⚠️ Please specify what to reset: --storage, --database, --indexes, or --all")
        return
    
    if not args.confirm:
        print("⚠️ This is a destructive operation!")
        print("Add --confirm to proceed with the reset.")
        return
    
    if args.all:
        result = full_system_reset(confirm=True)
    else:
        print("PERFORMING SELECTIVE RESET")
        print("=" * 40)
        
        if args.storage:
            print("Deleting storage files...")
            result = delete_all_storage_files()
            print(f"Status: {result['status']} - {result['message']}")
        
        if args.database:
            print("Resetting database...")
            result = reset_database()
            print(f"Status: {result['status']} - {result['message']}")
        
        if args.indexes:
            print("Deleting search indexes...")
            result = delete_search_indexes()
            print(f"Status: {result['status']} - {result['message']}")

if __name__ == "__main__":
    main()