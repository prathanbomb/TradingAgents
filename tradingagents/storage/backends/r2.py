"""Cloudflare R2 storage backend (S3-compatible)."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from ..base import BaseStorageBackend

if TYPE_CHECKING:
    from tradingagents.config import R2StorageConfig

logger = logging.getLogger(__name__)


class R2StorageBackend(BaseStorageBackend):
    """Storage backend for Cloudflare R2 (S3-compatible).

    Uses boto3 with S3-compatible API to interact with Cloudflare R2.
    The boto3 client is lazily initialized on first use.
    """

    backend_name = "r2"

    def __init__(self, config: "R2StorageConfig"):
        """Initialize R2 storage backend.

        Args:
            config: R2 storage configuration with credentials and bucket info.
        """
        self.config = config
        self._client = None

    @property
    def client(self):
        """Lazy initialization of boto3 S3 client.

        Returns:
            boto3 S3 client configured for R2.

        Raises:
            ImportError: If boto3 is not installed.
        """
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError:
                raise ImportError(
                    "boto3 is required for R2 storage. "
                    "Install it with: pip install boto3"
                )

            self._client = boto3.client(
                "s3",
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "adaptive"},
                ),
            )
        return self._client

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to R2.

        Args:
            local_path: Path to the local file to upload.
            remote_key: The key/path to store the file under in R2.
            content_type: Optional MIME type. Auto-detected if not provided.

        Returns:
            R2 URI in format r2://bucket/key.
        """
        extra_args = {
            "ContentType": content_type or self._guess_content_type(remote_key)
        }

        self.client.upload_file(
            str(local_path),
            self.config.bucket_name,
            remote_key,
            ExtraArgs=extra_args,
        )

        logger.debug(f"Uploaded file to R2: {remote_key}")
        return f"r2://{self.config.bucket_name}/{remote_key}"

    def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload bytes directly to R2.

        Args:
            data: The bytes to upload.
            remote_key: The key/path to store the data under in R2.
            content_type: Optional MIME type. Auto-detected if not provided.

        Returns:
            R2 URI in format r2://bucket/key.
        """
        self.client.put_object(
            Bucket=self.config.bucket_name,
            Key=remote_key,
            Body=data,
            ContentType=content_type or self._guess_content_type(remote_key),
        )

        logger.debug(f"Uploaded bytes to R2: {remote_key}")
        return f"r2://{self.config.bucket_name}/{remote_key}"

    def get_url(
        self,
        remote_key: str,
        expires_in: Optional[int] = None,
    ) -> Optional[str]:
        """Generate a URL for accessing a file.

        If public_url is configured, returns a permanent public URL.
        Otherwise, generates a presigned URL with expiration.

        Args:
            remote_key: The key/path of the file in R2.
            expires_in: URL expiration time in seconds. Defaults to config value.
                       Ignored when public_url is configured.

        Returns:
            URL for accessing the file, or None on error.
        """
        # If public URL is configured, return permanent public URL
        if self.config.public_url:
            return f"{self.config.public_url.rstrip('/')}/{remote_key}"

        # Otherwise, generate presigned URL
        if expires_in is None:
            expires_in = self.config.presigned_url_expiry

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.config.bucket_name,
                    "Key": remote_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {remote_key}: {e}")
            return None

    def exists(self, remote_key: str) -> bool:
        """Check if a file exists in R2.

        Args:
            remote_key: The key/path to check.

        Returns:
            True if the file exists, False otherwise.
        """
        try:
            self.client.head_object(
                Bucket=self.config.bucket_name,
                Key=remote_key,
            )
            return True
        except Exception as e:
            # Check for 404 errors (ClientError with 404 code)
            error_code = getattr(getattr(e, "response", {}), "get", lambda *a: None)(
                "Error", {}
            ).get("Code")
            if error_code == "404":
                return False
            # For any other error, log and return False
            if hasattr(e, "response"):
                logger.debug(f"Error checking existence of {remote_key}: {e}")
            return False

    def delete(self, remote_key: str) -> bool:
        """Delete a file from R2.

        Args:
            remote_key: The key/path of the file to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        try:
            self.client.delete_object(
                Bucket=self.config.bucket_name,
                Key=remote_key,
            )
            logger.debug(f"Deleted from R2: {remote_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {remote_key} from R2: {e}")
            return False

    def list_files(self, prefix: str) -> List[str]:
        """List files with a given prefix in R2.

        Args:
            prefix: The prefix to filter files by.

        Returns:
            List of file keys matching the prefix.
        """
        try:
            keys = []
            paginator = self.client.get_paginator("list_objects_v2")

            for page in paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
            ):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])

            return keys
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []

    def _guess_content_type(self, key: str) -> str:
        """Guess content type based on file extension.

        Args:
            key: File key/path to guess content type for.

        Returns:
            MIME type string.
        """
        extension = Path(key).suffix.lower()
        content_types = {
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".txt": "text/plain",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
        }
        return content_types.get(extension, "application/octet-stream")
