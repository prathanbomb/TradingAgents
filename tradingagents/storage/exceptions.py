"""Custom exceptions for storage operations."""


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class StorageUploadError(StorageError):
    """Raised when file upload fails."""

    def __init__(self, message: str, backend: str, key: str):
        self.backend = backend
        self.key = key
        super().__init__(f"[{backend}] Failed to upload {key}: {message}")


class StorageDownloadError(StorageError):
    """Raised when file download fails."""

    def __init__(self, message: str, backend: str, key: str):
        self.backend = backend
        self.key = key
        super().__init__(f"[{backend}] Failed to download {key}: {message}")


class StorageConfigurationError(StorageError):
    """Raised when storage configuration is invalid."""

    pass
