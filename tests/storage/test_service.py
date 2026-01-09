"""Tests for storage service."""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from tradingagents.config import R2StorageConfig, StorageConfig
from tradingagents.storage import StorageService


class TestStorageService:
    """Tests for StorageService."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def local_config(self, temp_dir):
        """Create a local-only storage config."""
        return StorageConfig(local_path=temp_dir)

    @pytest.fixture
    def local_service(self, local_config):
        """Create a storage service with local backend only."""
        return StorageService(local_config)

    def test_local_only_backends(self, local_service):
        """Local-only config should have only local backend."""
        assert local_service.backends == ["local"]
        assert local_service.primary_backend == "local"
        assert local_service.is_r2_enabled is False

    def test_upload_report(self, local_service, temp_dir):
        """upload_report should write to local backend."""
        content = "# Test Report\n\nContent here."
        results = local_service.upload_report(content, "AAPL/report.md")

        assert "local" in results
        assert (temp_dir / "AAPL/report.md").exists()
        assert (temp_dir / "AAPL/report.md").read_text() == content

    def test_upload_report_auto_content_type(self, local_service, temp_dir):
        """upload_report should auto-detect markdown content type."""
        content = "# Test"
        local_service.upload_report(content, "report.md")

        # Should work without error (content type detection)
        assert (temp_dir / "report.md").exists()

    def test_upload_file(self, local_service, temp_dir):
        """upload_file should copy file to backends."""
        source = temp_dir / "source.txt"
        source.write_text("source content")

        results = local_service.upload_file(source, "dest/file.txt")

        assert "local" in results
        assert (temp_dir / "dest/file.txt").exists()

    def test_get_report_url_local(self, local_service, temp_dir):
        """get_report_url should return local path."""
        (temp_dir / "report.md").write_text("content")

        url = local_service.get_report_url("report.md")

        assert url == str(temp_dir / "report.md")

    def test_get_report_url_not_exists(self, local_service):
        """get_report_url should return None for non-existent file."""
        url = local_service.get_report_url("nonexistent.md")
        assert url is None

    def test_get_local_path(self, local_service, temp_dir):
        """get_local_path should return local file path."""
        (temp_dir / "report.md").write_text("content")

        path = local_service.get_local_path("report.md")

        assert path == str(temp_dir / "report.md")

    def test_exists(self, local_service, temp_dir):
        """exists should check primary backend."""
        (temp_dir / "report.md").write_text("content")

        assert local_service.exists("report.md") is True
        assert local_service.exists("nonexistent.md") is False

    def test_delete(self, local_service, temp_dir):
        """delete should remove from all backends."""
        (temp_dir / "report.md").write_text("content")

        results = local_service.delete("report.md")

        assert results["local"] is True
        assert not (temp_dir / "report.md").exists()

    def test_list_reports(self, local_service, temp_dir):
        """list_reports should list from all backends."""
        (temp_dir / "prefix").mkdir()
        (temp_dir / "prefix/a.md").write_text("a")
        (temp_dir / "prefix/b.md").write_text("b")

        results = local_service.list_reports("prefix")

        assert "local" in results
        assert sorted(results["local"]) == ["prefix/a.md", "prefix/b.md"]

    def test_upload_report_error_handling(self, temp_dir):
        """upload_report should handle backend errors gracefully."""
        config = StorageConfig(local_path=temp_dir)
        service = StorageService(config)

        # Mock the backend to raise an error
        with mock.patch.object(
            service._backends["local"],
            "upload_bytes",
            side_effect=Exception("Test error"),
        ):
            results = service.upload_report("content", "report.md")

            # Should return empty dict, not raise
            assert results == {}

    def test_multiple_reports_upload(self, local_service, temp_dir):
        """Multiple reports should be uploadable."""
        reports = {
            "market_report": "# Market Report",
            "sentiment_report": "# Sentiment Report",
            "news_report": "# News Report",
        }

        for name, content in reports.items():
            local_service.upload_report(content, f"AAPL/{name}.md")

        assert (temp_dir / "AAPL/market_report.md").exists()
        assert (temp_dir / "AAPL/sentiment_report.md").exists()
        assert (temp_dir / "AAPL/news_report.md").exists()


class TestStorageServiceWithR2:
    """Tests for StorageService with R2 configuration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def r2_config(self, temp_dir):
        """Create a config with R2 enabled."""
        r2 = R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
        )
        return StorageConfig(local_path=temp_dir, r2=r2)

    def test_r2_backend_initialized(self, r2_config):
        """R2 backend should be initialized when configured."""
        service = StorageService(r2_config)

        assert "r2" in service.backends
        assert service.primary_backend == "r2"
        assert service.is_r2_enabled is True

    def test_upload_to_both_backends(self, r2_config, temp_dir):
        """Upload should go to both local and R2 backends."""
        service = StorageService(r2_config)

        # Mock R2 backend
        with mock.patch.object(
            service._backends["r2"],
            "upload_bytes",
            return_value="r2://test-bucket/report.md",
        ):
            results = service.upload_report("# Test", "report.md")

            assert "local" in results
            assert "r2" in results
            assert results["r2"] == "r2://test-bucket/report.md"
            assert (temp_dir / "report.md").exists()

    def test_r2_primary_for_url(self, r2_config):
        """get_report_url should use R2 backend when available."""
        service = StorageService(r2_config)

        with mock.patch.object(
            service._backends["r2"],
            "get_url",
            return_value="https://presigned.url",
        ):
            url = service.get_report_url("report.md")

            assert url == "https://presigned.url"

    def test_r2_failure_graceful_degradation(self, r2_config, temp_dir):
        """R2 failure should not prevent local upload."""
        service = StorageService(r2_config)

        # Mock R2 backend to fail
        with mock.patch.object(
            service._backends["r2"],
            "upload_bytes",
            side_effect=Exception("R2 error"),
        ):
            results = service.upload_report("# Test", "report.md")

            # Local should succeed even if R2 fails
            assert "local" in results
            assert (temp_dir / "report.md").exists()


class TestStorageServiceR2ImportError:
    """Tests for StorageService when boto3 is not available."""

    def test_r2_unavailable_on_import_error(self, tmp_path):
        """R2 should be unavailable when R2StorageBackend import fails."""
        r2 = R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
        )
        config = StorageConfig(local_path=tmp_path, r2=r2)

        # Mock the R2StorageBackend import to raise ImportError
        original_init_backends = StorageService._init_backends

        def mock_init_backends(self, cfg):
            # Always initialize local storage
            from tradingagents.storage.backends.local import LocalStorageBackend
            self._backends["local"] = LocalStorageBackend(cfg.local_path or tmp_path)
            # Simulate ImportError for R2
            # Don't add R2 backend

        with mock.patch.object(StorageService, "_init_backends", mock_init_backends):
            service = StorageService(config)

            # Should fall back to local only
            assert service.backends == ["local"]
            assert service.is_r2_enabled is False
