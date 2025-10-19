#!/usr/bin/env python3
"""
Azure Storage Container Setup Script

This script will:
1. Check if the storage container exists
2. Create it if it doesn't exist
3. Test the connection
"""

import os
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from config.config import config

def setup_container():
    """Set up the Azure Storage container"""
    
    print("🔧 Azure Storage Container Setup")
    print("=" * 40)
    
    # Get configuration
    connection_string = config.AZURE_STORAGE_CONNECTION_STRING
    container_name = config.AZURE_STORAGE_CONTAINER_NAME
    
    print(f"📋 Configuration:")
    print(f"   Container name: {container_name}")
    print(f"   Connection string: {connection_string[:50]}...")
    
    if not connection_string or "your_storage_account" in connection_string:
        print("❌ Invalid storage connection string in .env file")
        print("   Please update AZURE_STORAGE_CONNECTION_STRING with your actual Azure Storage account details")
        return False
    
    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Check if container exists
        print(f"\n🔍 Checking if container '{container_name}' exists...")
        
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_properties = container_client.get_container_properties()
            print(f"✅ Container '{container_name}' already exists")
            print(f"   Created: {container_properties.last_modified}")
            return True
            
        except AzureError as e:
            if "ContainerNotFound" in str(e):
                print(f"📦 Container '{container_name}' does not exist. Creating...")
                
                # Create the container
                container_client = blob_service_client.create_container(container_name)
                print(f"✅ Successfully created container '{container_name}'")
                
                # Test upload a small file
                test_content = "Test file from container setup script"
                test_blob_name = "test_setup.txt"
                
                blob_client = container_client.get_blob_client(test_blob_name)
                blob_client.upload_blob(test_content, overwrite=True)
                print(f"✅ Test upload successful: {test_blob_name}")
                
                # Clean up test file
                blob_client.delete_blob()
                print(f"🧹 Cleaned up test file")
                
                return True
            else:
                print(f"❌ Error checking container: {e}")
                return False
    
    except Exception as e:
        print(f"❌ Failed to connect to Azure Storage: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your AZURE_STORAGE_CONNECTION_STRING in .env file")
        print("   2. Verify your Azure Storage account exists")
        print("   3. Ensure you have the correct access keys")
        return False

def test_database_connection():
    """Test database connection"""
    print(f"\n🗄️ Testing database connection...")
    print(f"   Database type: {config.DATABASE_TYPE}")
    
    if config.DATABASE_TYPE == 'sqlite':
        db_path = config.SQLITE_DATABASE_PATH
        print(f"   SQLite path: {db_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        print(f"✅ SQLite directory ready")
        
    elif config.DATABASE_TYPE == 'azuresql':
        print(f"   Azure SQL Server: {config.AZURE_SQL_SERVER}")
        print(f"   Database: {config.AZURE_SQL_DATABASE}")
        print(f"   Username: {config.AZURE_SQL_USERNAME}")
        
        # Test connection string construction
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        if conn_str:
            print(f"✅ Connection string constructed successfully")
            print(f"   Length: {len(conn_str)} characters")
        else:
            print(f"❌ Failed to construct connection string")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Setting up Azure Function dependencies...")
    
    # Test database
    db_success = test_database_connection()
    
    # Setup storage
    storage_success = setup_container()
    
    print("\n" + "=" * 40)
    print("📊 SETUP SUMMARY")
    print("=" * 40)
    print(f"Database: {'✅ Ready' if db_success else '❌ Failed'}")
    print(f"Storage: {'✅ Ready' if storage_success else '❌ Failed'}")
    
    if db_success and storage_success:
        print("\n🎉 All dependencies are ready!")
        print("You can now run the upload tests:")
        print("   python quick_test.py")
        print("   python test_upload.py --create-files")
    else:
        print("\n⚠️ Some dependencies failed - check errors above")