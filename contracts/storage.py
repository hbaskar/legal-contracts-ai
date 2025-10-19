"""
Azure Blob Storage operations for file uploads
Uses managed identity for authentication in production environments
"""
import os
import logging
import hashlib
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError


class BlobStorageManager:
    """Manages Azure Blob Storage operations"""
    
    def __init__(self):
        from config.config import config
        self.storage_connection_string = config.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = config.AZURE_STORAGE_CONTAINER_NAME
        self.logger = logging.getLogger(__name__)
        
        # Initialize blob service client
        if self.storage_connection_string and len(self.storage_connection_string.strip()) > 0:
            try:
                # Use connection string (works for both dev and production)
                self.blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection_string)
                self.logger.info("Initialized BlobServiceClient with connection string")
            except Exception as e:
                self.logger.error(f"Failed to initialize with connection string: {e}")
                # Fallback to managed identity if available
                if config.AZURE_STORAGE_ACCOUNT_URL:
                    credential = DefaultAzureCredential()
                    self.blob_service_client = BlobServiceClient(account_url=config.AZURE_STORAGE_ACCOUNT_URL, credential=credential)
                    self.logger.info("Initialized BlobServiceClient with managed identity fallback")
                else:
                    raise
        elif config.AZURE_STORAGE_ACCOUNT_URL:
            # Use managed identity for production
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=config.AZURE_STORAGE_ACCOUNT_URL, credential=credential)
            self.logger.info("Initialized BlobServiceClient with managed identity")
        else:
            raise ValueError("Either AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL must be configured")
    
    async def upload_file(self, file_data: bytes, filename: str, content_type: str) -> Tuple[str, str]:
        """
        Upload file to blob storage
        
        Args:
            file_data: File content as bytes
            filename: Name of the file
            content_type: MIME type of the file
            
        Returns:
            Tuple of (blob_url, blob_name)
        """
        try:
            # Generate unique blob name with timestamp
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            blob_name = f"{timestamp}_{filename}"
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Calculate MD5 hash for integrity check
            md5_hash = hashlib.md5(file_data).hexdigest()
            
            # Upload with metadata
            metadata = {
                'original_filename': filename,
                'upload_timestamp': datetime.now(UTC).isoformat(),
                'content_type': content_type,
                'md5_hash': md5_hash
            }
            
            # Upload the file
            blob_client.upload_blob(
                file_data,
                content_type=content_type,
                metadata=metadata,
                overwrite=True
            )
            
            self.logger.info(f"Successfully uploaded file: {blob_name}")
            
            return blob_client.url, blob_name
            
        except AzureError as e:
            self.logger.error(f"Azure storage error during upload: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during file upload: {str(e)}")
            raise
    
    async def delete_file(self, blob_name: str) -> bool:
        """
        Delete file from blob storage
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            await blob_client.delete_blob()
            self.logger.info(f"Successfully deleted blob: {blob_name}")
            return True
            
        except AzureError as e:
            self.logger.error(f"Azure storage error during deletion: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during file deletion: {str(e)}")
            return False
    
    async def get_file_url_with_sas(self, blob_name: str, expiry_hours: int = 24) -> Optional[str]:
        """
        Generate a SAS URL for secure file access
        
        Args:
            blob_name: Name of the blob
            expiry_hours: Hours until the SAS token expires
            
        Returns:
            SAS URL if successful, None otherwise
        """
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            
            # Calculate expiry time
            expiry_time = datetime.now(UTC) + timedelta(hours=expiry_hours)
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time
            )
            
            # Construct full URL
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            sas_url = f"{blob_client.url}?{sas_token}"
            
            self.logger.info(f"Generated SAS URL for blob: {blob_name}")
            return sas_url
            
        except Exception as e:
            self.logger.error(f"Error generating SAS URL: {str(e)}")
            return None
    
    async def ensure_container_exists(self):
        """Ensure the storage container exists"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # Check if container exists, create if not
            if not container_client.exists():
                container_client.create_container()
                self.logger.info(f"Created storage container: {self.container_name}")
            else:
                self.logger.info(f"Container already exists: {self.container_name}")
                
        except AzureError as e:
            self.logger.error(f"Error ensuring container exists: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error with container: {str(e)}")
            raise
    
    def calculate_file_hash(self, file_data: bytes) -> str:
        """Calculate MD5 hash of file content"""
        return hashlib.md5(file_data).hexdigest()