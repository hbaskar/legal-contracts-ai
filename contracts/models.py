"""
Data models for file upload metadata
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FileMetadata:
    """Represents file metadata to be stored in the database"""
    id: Optional[int] = None
    filename: str = ""
    original_filename: str = ""
    file_size: int = 0
    content_type: str = ""
    blob_url: str = ""
    container_name: str = ""
    upload_timestamp: Optional[datetime] = None
    checksum: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "blob_url": self.blob_url,
            "container_name": self.container_name,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "checksum": self.checksum,
            "user_id": self.user_id
        }


@dataclass
class UploadResponse:
    """Response model for file upload operations"""
    success: bool
    message: str
    file_metadata: Optional[FileMetadata] = None
    error_details: Optional[str] = None