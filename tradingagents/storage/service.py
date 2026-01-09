"""Storage service facade for managing multiple storage backends."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .backends.local import LocalStorageBackend
from .base import BaseStorageBackend

if TYPE_CHECKING:
    from tradingagents.config import StorageConfig

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service supporting multiple backends.

    This service manages multiple storage backends and provides a unified
    interface for uploading reports. By default, it writes to all configured
    backends (local and R2 if configured).
    """

    def __init__(self, config: "StorageConfig"):
        """Initialize storage service from configuration.

        Args:
            config: Storage configuration with local path and optional R2 config.
        """
        self._backends: Dict[str, BaseStorageBackend] = {}
        self._primary_backend: str = "local"
        self._init_backends(config)

    def _init_backends(self, config: "StorageConfig") -> None:
        """Initialize storage backends from configuration.

        Args:
            config: Storage configuration.
        """
        # Always initialize local storage
        local_path = config.local_path or Path("./reports")
        self._backends["local"] = LocalStorageBackend(local_path)
        logger.info(f"Local storage backend initialized at {local_path}")

        # Initialize R2 if configured
        if config.r2 and config.r2.is_configured:
            try:
                from .backends.r2 import R2StorageBackend

                self._backends["r2"] = R2StorageBackend(config.r2)
                self._primary_backend = "r2"
                logger.info(
                    f"R2 storage backend initialized for bucket {config.r2.bucket_name}"
                )
            except ImportError:
                logger.warning(
                    "boto3 not installed, R2 storage unavailable. "
                    "Install with: pip install boto3"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize R2 backend: {e}")

    def upload_report(
        self,
        content: str,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        """Upload report content to all configured backends.

        Args:
            content: Report content as string.
            remote_key: The key/path to store the report under.
            content_type: Optional MIME type. Defaults to text/markdown for .md files.

        Returns:
            Dict mapping backend name to storage path/URI.
        """
        results = {}
        data = content.encode("utf-8")

        if content_type is None and remote_key.endswith(".md"):
            content_type = "text/markdown"

        for name, backend in self._backends.items():
            try:
                result = backend.upload_bytes(data, remote_key, content_type)
                results[name] = result
                logger.debug(f"Uploaded {remote_key} to {name}")
            except Exception as e:
                logger.error(f"Failed to upload {remote_key} to {name}: {e}")

        return results

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        """Upload a file to all configured backends.

        Args:
            local_path: Path to the local file to upload.
            remote_key: The key/path to store the file under.
            content_type: Optional MIME type.

        Returns:
            Dict mapping backend name to storage path/URI.
        """
        results = {}

        for name, backend in self._backends.items():
            try:
                result = backend.upload_file(local_path, remote_key, content_type)
                results[name] = result
                logger.debug(f"Uploaded file {remote_key} to {name}")
            except Exception as e:
                logger.error(f"Failed to upload file {remote_key} to {name}: {e}")

        return results

    def get_report_url(
        self,
        remote_key: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """Get URL for accessing a report from the primary backend.

        For R2, this returns a presigned URL. For local storage, this returns
        the file path.

        Args:
            remote_key: The key/path of the report.
            expires_in: URL expiration time in seconds (for presigned URLs).

        Returns:
            URL or path for accessing the report, or None if not found.
        """
        backend = self._backends.get(self._primary_backend)
        if backend:
            return backend.get_url(remote_key, expires_in)
        return None

    def get_local_path(self, remote_key: str) -> Optional[str]:
        """Get the local file path for a report.

        Args:
            remote_key: The key/path of the report.

        Returns:
            Local file path if it exists, None otherwise.
        """
        local_backend = self._backends.get("local")
        if local_backend:
            return local_backend.get_url(remote_key)
        return None

    def exists(self, remote_key: str, backend: Optional[str] = None) -> bool:
        """Check if a report exists.

        Args:
            remote_key: The key/path to check.
            backend: Specific backend to check. If None, checks primary backend.

        Returns:
            True if the report exists.
        """
        backend_name = backend or self._primary_backend
        storage_backend = self._backends.get(backend_name)
        if storage_backend:
            return storage_backend.exists(remote_key)
        return False

    def delete(self, remote_key: str) -> Dict[str, bool]:
        """Delete a report from all backends.

        Args:
            remote_key: The key/path of the report to delete.

        Returns:
            Dict mapping backend name to deletion success status.
        """
        results = {}
        for name, backend in self._backends.items():
            try:
                results[name] = backend.delete(remote_key)
            except Exception as e:
                logger.error(f"Failed to delete {remote_key} from {name}: {e}")
                results[name] = False
        return results

    def list_reports(self, prefix: str) -> Dict[str, List[str]]:
        """List reports with a given prefix from all backends.

        Args:
            prefix: The prefix to filter reports by.

        Returns:
            Dict mapping backend name to list of report keys.
        """
        results = {}
        for name, backend in self._backends.items():
            try:
                results[name] = backend.list_files(prefix)
            except Exception as e:
                logger.error(f"Failed to list reports from {name}: {e}")
                results[name] = []
        return results

    @property
    def primary_backend(self) -> str:
        """Get the name of the primary backend."""
        return self._primary_backend

    @property
    def backends(self) -> List[str]:
        """Get list of configured backend names."""
        return list(self._backends.keys())

    @property
    def is_r2_enabled(self) -> bool:
        """Check if R2 backend is enabled."""
        return "r2" in self._backends
