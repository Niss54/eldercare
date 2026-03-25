"""M05.1 S3 Storage Provider - abstraction for document persistence."""

import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional

try:
    import boto3
except ImportError:
    boto3 = None


class S3Provider(ABC):
    """Abstract base class for S3 storage operations."""

    @abstractmethod
    def upload_file(self, file_path: str, s3_key: str, content_type: str = "application/octet-stream") -> dict:
        """Upload a file to S3 storage.
        
        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path)
            content_type: MIME type of the file
            
        Returns:
            dict with s3_key, file_hash, mime_type
        """
        pass

    @abstractmethod
    def get_presigned_url(self, s3_key: str, expiration_seconds: int = 3600) -> str:
        """Get a presigned URL for downloading a file.
        
        Args:
            s3_key: S3 object key
            expiration_seconds: URL expiration time in seconds
            
        Returns:
            Presigned URL string
        """
        pass

    @abstractmethod
    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        pass


class LocalS3Provider(S3Provider):
    """Local S3-compatible provider for development/testing."""

    def __init__(self, storage_dir: str = "/tmp/health_records"):
        """Initialize local storage provider.
        
        Args:
            storage_dir: Directory to store files locally
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def upload_file(
        self,
        file_path: str,
        s3_key: str,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """Upload file to local storage."""
        import shutil
        
        local_path = os.path.join(self.storage_dir, s3_key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy(file_path, local_path)

        # Calculate file hash
        file_hash = self._calculate_hash(file_path)

        return {
            "s3_key": s3_key,
            "file_hash": file_hash,
            "mime_type": content_type,
        }

    def get_presigned_url(self, s3_key: str, expiration_seconds: int = 3600) -> str:
        """Get URL for local file."""
        local_path = os.path.join(self.storage_dir, s3_key)
        return f"file://{local_path}"

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from local storage."""
        local_path = os.path.join(self.storage_dir, s3_key)
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            return True
        except Exception:
            return False

    @staticmethod
    def _calculate_hash(file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


class AwsS3Provider(S3Provider):
    """AWS S3 provider for production use."""

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """Initialize AWS S3 provider.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        if boto3 is None:
            raise ImportError("boto3 is required for AwsS3Provider. Install with: pip install boto3")
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", region_name=region)

    def upload_file(
        self,
        file_path: str,
        s3_key: str,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """Upload file to AWS S3."""
        # Calculate hash before upload
        file_hash = self._calculate_hash(file_path)

        # Upload to S3
        self.s3_client.upload_file(
            file_path,
            self.bucket_name,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )

        return {
            "s3_key": s3_key,
            "file_hash": file_hash,
            "mime_type": content_type,
        }

    def get_presigned_url(self, s3_key: str, expiration_seconds: int = 3600) -> str:
        """Get presigned URL for S3 object."""
        url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": s3_key},
            ExpiresIn=expiration_seconds,
        )
        return url

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from AWS S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception:
            return False

    @staticmethod
    def _calculate_hash(file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


# Factory function for provider selection
def get_s3_provider() -> S3Provider:
    """Get configured S3 provider based on environment.
    
    Returns:
        S3Provider instance
    """
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        bucket = os.getenv("AWS_S3_BUCKET", "eldercare-health-records")
        region = os.getenv("AWS_REGION", "us-east-1")
        return AwsS3Provider(bucket_name=bucket, region=region)
    else:
        storage_dir = os.getenv("LOCAL_STORAGE_DIR", "/tmp/health_records")
        return LocalS3Provider(storage_dir=storage_dir)
