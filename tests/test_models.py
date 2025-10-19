"""
Test file for the Azure Function file upload service
"""
import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, UTC
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the azure.functions module since it's not available in test environment
from unittest.mock import MagicMock
sys.modules['azure.functions'] = MagicMock()

from contracts.models import FileMetadata, UploadResponse


class TestFileMetadata(unittest.TestCase):
    """Test cases for FileMetadata model"""
    
    def test_file_metadata_creation(self):
        """Test creating a FileMetadata instance"""
        metadata = FileMetadata(
            filename="test_file.txt",
            original_filename="original.txt",
            file_size=1024,
            content_type="text/plain",
            blob_url="https://example.blob.core.windows.net/uploads/test_file.txt",
            container_name="uploads",
            upload_timestamp=datetime.now(UTC),
            checksum="abc123",
            user_id="user123"
        )
        
        self.assertEqual(metadata.filename, "test_file.txt")
        self.assertEqual(metadata.file_size, 1024)
        self.assertIsNotNone(metadata.upload_timestamp)
    
    def test_file_metadata_to_dict(self):
        """Test converting FileMetadata to dictionary"""
        timestamp = datetime.now(UTC)
        metadata = FileMetadata(
            id=1,
            filename="test.txt",
            original_filename="test.txt",
            file_size=500,
            content_type="text/plain",
            blob_url="https://example.com/test.txt",
            container_name="uploads",
            upload_timestamp=timestamp,
            checksum="hash123",
            user_id="user1"
        )
        
        result = metadata.to_dict()
        
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["filename"], "test.txt")
        self.assertEqual(result["upload_timestamp"], timestamp.isoformat())


class TestUploadResponse(unittest.TestCase):
    """Test cases for UploadResponse model"""
    
    def test_upload_response_success(self):
        """Test successful upload response"""
        metadata = FileMetadata(filename="test.txt", file_size=100)
        response = UploadResponse(
            success=True,
            message="Upload successful",
            file_metadata=metadata
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Upload successful")
        self.assertIsNotNone(response.file_metadata)
    
    def test_upload_response_failure(self):
        """Test failed upload response"""
        response = UploadResponse(
            success=False,
            message="Upload failed",
            error_details="Network error"
        )
        
        self.assertFalse(response.success)
        self.assertEqual(response.error_details, "Network error")


if __name__ == '__main__':
    unittest.main()
