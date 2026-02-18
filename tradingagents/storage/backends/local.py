"""Local filesystem storage backend."""

import shutil
from pathlib import Path
from typing import List, Optional

from ..base import BaseStorageBackend


class LocalStorageBackend(BaseStorageBackend):
    """Storage backend using local filesystem."""

    backend_name = "local"

    def __init__(self, base_path: Path):
        """Initialize local storage backend.

        Args:
            base_path: Base directory for storing files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Copy a file to storage.

        Args:
            local_path: Path to the source file.
            remote_key: Relative path/key for the destination.
            content_type: Ignored for local storage.

        Returns:
            Absolute path to the stored file.
        """
        destination = self.base_path / remote_key

        # Skip if source and destination are the same file
        if local_path.resolve() == destination.resolve():
            return str(destination)

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, destination)
        return str(destination)

    def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Write bytes to storage.

        Args:
            data: Bytes to write.
            remote_key: Relative path/key for the destination.
            content_type: Ignored for local storage.

        Returns:
            Absolute path to the stored file.
        """
        destination = self.base_path / remote_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return str(destination)

    def get_url(
        self,
        remote_key: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """Get the file path for a stored file.

        Args:
            remote_key: Relative path/key of the file.
            expires_in: Ignored for local storage.

        Returns:
            Absolute path to the file if it exists, None otherwise.
        """
        file_path = self.base_path / remote_key
        return str(file_path) if file_path.exists() else None

    def exists(self, remote_key: str) -> bool:
        """Check if a file exists.

        Args:
            remote_key: Relative path/key to check.

        Returns:
            True if the file exists.
        """
        return (self.base_path / remote_key).exists()

    def delete(self, remote_key: str) -> bool:
        """Delete a file.

        Args:
            remote_key: Relative path/key of the file to delete.

        Returns:
            True if deletion was successful, False if file didn't exist.
        """
        path = self.base_path / remote_key
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return True
        return False

    def list_files(self, prefix: str) -> List[str]:
        """List files under a prefix.

        Args:
            prefix: Directory prefix to list files from.

        Returns:
            List of relative file paths.
        """
        base = self.base_path / prefix
        if base.is_dir():
            return [
                str(p.relative_to(self.base_path))
                for p in base.rglob("*")
                if p.is_file()
            ]
        elif base.is_file():
            return [prefix]
        return []
