"""Tests for R2 storage backend."""

from pathlib import Path
from unittest import mock

import pytest

from tradingagents.config import R2StorageConfig
from tradingagents.storage.backends.r2 import R2StorageBackend


class TestR2StorageBackend:
    """Tests for R2StorageBackend."""

    @pytest.fixture
    def r2_config(self):
        """Create a test R2 configuration."""
        return R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
            presigned_url_expiry=3600,
        )

    @pytest.fixture
    def mock_client(self):
        """Create a mock boto3 client."""
        return mock.MagicMock()

    @pytest.fixture
    def backend_with_mock(self, r2_config, mock_client):
        """Create backend with mocked client."""
        backend = R2StorageBackend(r2_config)
        backend._client = mock_client
        return backend, mock_client

    def test_backend_name(self, r2_config):
        """Backend name should be 'r2'."""
        backend = R2StorageBackend(r2_config)
        assert backend.backend_name == "r2"

    def test_config_stored(self, r2_config):
        """Config should be stored on backend."""
        backend = R2StorageBackend(r2_config)
        assert backend.config == r2_config
        assert backend.config.bucket_name == "test-bucket"

    def test_client_lazy_initialization(self, r2_config):
        """Client should not be initialized until accessed."""
        backend = R2StorageBackend(r2_config)
        assert backend._client is None

    def test_upload_bytes(self, backend_with_mock):
        """upload_bytes should call put_object."""
        backend, mock_client = backend_with_mock

        result = backend.upload_bytes(
            b"test content",
            "reports/test.md",
            content_type="text/markdown",
        )

        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="reports/test.md",
            Body=b"test content",
            ContentType="text/markdown",
        )
        assert result == "r2://test-bucket/reports/test.md"

    def test_upload_bytes_auto_content_type(self, backend_with_mock):
        """upload_bytes should auto-detect content type."""
        backend, mock_client = backend_with_mock

        backend.upload_bytes(b"test", "reports/test.pdf")

        call_args = mock_client.put_object.call_args
        assert call_args.kwargs["ContentType"] == "application/pdf"

    def test_upload_file(self, backend_with_mock, tmp_path):
        """upload_file should call upload_file on client."""
        backend, mock_client = backend_with_mock

        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("content")

        result = backend.upload_file(
            test_file,
            "reports/test.md",
            content_type="text/markdown",
        )

        mock_client.upload_file.assert_called_once()
        call_args = mock_client.upload_file.call_args
        assert call_args.args[0] == str(test_file)
        assert call_args.args[1] == "test-bucket"
        assert call_args.args[2] == "reports/test.md"
        assert result == "r2://test-bucket/reports/test.md"

    def test_get_url(self, backend_with_mock):
        """get_url should generate presigned URL."""
        backend, mock_client = backend_with_mock
        mock_client.generate_presigned_url.return_value = "https://presigned.url"

        result = backend.get_url("reports/test.md", expires_in=7200)

        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "reports/test.md"},
            ExpiresIn=7200,
        )
        assert result == "https://presigned.url"

    def test_get_url_default_expiry(self, backend_with_mock):
        """get_url should use config expiry if not specified."""
        backend, mock_client = backend_with_mock
        mock_client.generate_presigned_url.return_value = "https://presigned.url"

        backend.get_url("reports/test.md")

        call_args = mock_client.generate_presigned_url.call_args
        assert call_args.kwargs["ExpiresIn"] == 3600

    def test_get_url_error_returns_none(self, backend_with_mock):
        """get_url should return None on error."""
        backend, mock_client = backend_with_mock
        mock_client.generate_presigned_url.side_effect = Exception("Error")

        result = backend.get_url("reports/test.md")

        assert result is None

    def test_get_url_public(self):
        """get_url should return public URL when public_url is configured."""
        config = R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
            public_url="https://pub-abc123.r2.dev",
        )
        backend = R2StorageBackend(config)

        result = backend.get_url("reports/test.md")

        assert result == "https://pub-abc123.r2.dev/reports/test.md"

    def test_get_url_public_strips_trailing_slash(self):
        """get_url should handle trailing slash in public_url."""
        config = R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
            public_url="https://files.example.com/",
        )
        backend = R2StorageBackend(config)

        result = backend.get_url("folder/file.pdf")

        assert result == "https://files.example.com/folder/file.pdf"

    def test_exists_true(self, backend_with_mock):
        """exists should return True when object exists."""
        backend, mock_client = backend_with_mock

        result = backend.exists("reports/test.md")

        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="reports/test.md",
        )
        assert result is True

    def test_exists_false_on_error(self, backend_with_mock):
        """exists should return False on error."""
        backend, mock_client = backend_with_mock
        mock_client.head_object.side_effect = Exception("Not found")

        result = backend.exists("reports/test.md")

        assert result is False

    def test_delete(self, backend_with_mock):
        """delete should call delete_object."""
        backend, mock_client = backend_with_mock

        result = backend.delete("reports/test.md")

        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="reports/test.md",
        )
        assert result is True

    def test_delete_error_returns_false(self, backend_with_mock):
        """delete should return False on error."""
        backend, mock_client = backend_with_mock
        mock_client.delete_object.side_effect = Exception("Error")

        result = backend.delete("reports/test.md")

        assert result is False

    def test_list_files(self, backend_with_mock):
        """list_files should paginate through objects."""
        backend, mock_client = backend_with_mock

        paginator = mock.MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "prefix/a.md"}, {"Key": "prefix/b.md"}]},
            {"Contents": [{"Key": "prefix/c.md"}]},
        ]
        mock_client.get_paginator.return_value = paginator

        result = backend.list_files("prefix/")

        mock_client.get_paginator.assert_called_once_with("list_objects_v2")
        assert result == ["prefix/a.md", "prefix/b.md", "prefix/c.md"]

    def test_list_files_empty(self, backend_with_mock):
        """list_files should return empty list when no objects."""
        backend, mock_client = backend_with_mock

        paginator = mock.MagicMock()
        paginator.paginate.return_value = [{}]
        mock_client.get_paginator.return_value = paginator

        result = backend.list_files("prefix/")

        assert result == []

    def test_list_files_error_returns_empty(self, backend_with_mock):
        """list_files should return empty list on error."""
        backend, mock_client = backend_with_mock
        mock_client.get_paginator.side_effect = Exception("Error")

        result = backend.list_files("prefix/")

        assert result == []

    def test_guess_content_type(self, r2_config):
        """_guess_content_type should detect common types."""
        backend = R2StorageBackend(r2_config)

        assert backend._guess_content_type("file.md") == "text/markdown"
        assert backend._guess_content_type("file.pdf") == "application/pdf"
        assert backend._guess_content_type("file.json") == "application/json"
        assert backend._guess_content_type("file.txt") == "text/plain"
        assert backend._guess_content_type("file.html") == "text/html"
        assert backend._guess_content_type("file.png") == "image/png"
        assert backend._guess_content_type("file.jpg") == "image/jpeg"
        assert backend._guess_content_type("file.unknown") == "application/octet-stream"
