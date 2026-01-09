"""Base storage protocol and abstract class for storage backends."""

from abc import ABC
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol defining the interface for storage backend implementations.

    All storage implementations must provide a backend_name and implement
    the methods they support. Methods not supported should raise NotImplementedError.
    """

    backend_name: str

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to storage.

        Args:
            local_path: Path to the local file to upload.
            remote_key: The key/path to store the file under.
            content_type: Optional MIME type for the file.

        Returns:
            The storage path or URI of the uploaded file.
        """
        ...

    def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload bytes directly to storage.

        Args:
            data: The bytes to upload.
            remote_key: The key/path to store the data under.
            content_type: Optional MIME type for the data.

        Returns:
            The storage path or URI of the uploaded data.
        """
        ...

    def get_url(
        self,
        remote_key: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """Get a URL for accessing a file.

        Args:
            remote_key: The key/path of the file.
            expires_in: URL expiration time in seconds (for presigned URLs).

        Returns:
            URL or file path for accessing the file, or None if not found.
        """
        ...

    def exists(self, remote_key: str) -> bool:
        """Check if a file exists in storage.

        Args:
            remote_key: The key/path to check.

        Returns:
            True if the file exists, False otherwise.
        """
        ...

    def delete(self, remote_key: str) -> bool:
        """Delete a file from storage.

        Args:
            remote_key: The key/path of the file to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        ...

    def list_files(self, prefix: str) -> List[str]:
        """List files with a given prefix.

        Args:
            prefix: The prefix to filter files by.

        Returns:
            List of file keys matching the prefix.
        """
        ...


class BaseStorageBackend(ABC):
    """Abstract base class for storage implementations.

    Provides default NotImplementedError for all methods.
    Subclasses should override the methods they support.
    """

    backend_name: str = "base"

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to storage."""
        raise NotImplementedError(f"{self.backend_name} does not support upload_file")

    def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload bytes directly to storage."""
        raise NotImplementedError(f"{self.backend_name} does not support upload_bytes")

    def get_url(
        self,
        remote_key: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """Get a URL for accessing a file."""
        raise NotImplementedError(f"{self.backend_name} does not support get_url")

    def exists(self, remote_key: str) -> bool:
        """Check if a file exists in storage."""
        raise NotImplementedError(f"{self.backend_name} does not support exists")

    def delete(self, remote_key: str) -> bool:
        """Delete a file from storage."""
        raise NotImplementedError(f"{self.backend_name} does not support delete")

    def list_files(self, prefix: str) -> List[str]:
        """List files with a given prefix."""
        raise NotImplementedError(f"{self.backend_name} does not support list_files")

    def supports(self, method: str) -> bool:
        """Check if this backend supports the given method.

        Args:
            method: The method name to check.

        Returns:
            True if the method is implemented, False otherwise.
        """
        try:
            func = getattr(self, method)
            base_func = getattr(BaseStorageBackend, method, None)
            return func.__func__ is not base_func
        except AttributeError:
            return False
