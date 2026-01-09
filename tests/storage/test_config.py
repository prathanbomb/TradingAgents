"""Tests for storage configuration models."""

import os
from pathlib import Path
from unittest import mock

import pytest

from tradingagents.config import R2StorageConfig, StorageConfig


class TestR2StorageConfig:
    """Tests for R2StorageConfig."""

    def test_empty_config_not_configured(self):
        """Empty config should not be configured."""
        config = R2StorageConfig()
        assert config.is_configured is False

    def test_partial_config_not_configured(self):
        """Partial config should not be configured."""
        config = R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            # Missing secret and bucket
        )
        assert config.is_configured is False

    def test_full_config_is_configured(self):
        """Full config should be configured."""
        config = R2StorageConfig(
            account_id="test_account",
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket_name="test-bucket",
        )
        assert config.is_configured is True

    def test_endpoint_url_auto_generated(self):
        """Endpoint URL should be auto-generated from account_id."""
        config = R2StorageConfig(
            account_id="abc123",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name="bucket",
        )
        assert config.endpoint_url == "https://abc123.r2.cloudflarestorage.com"

    def test_custom_endpoint_url_not_overwritten(self):
        """Custom endpoint URL should not be overwritten."""
        config = R2StorageConfig(
            account_id="abc123",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name="bucket",
            endpoint_url="https://custom.endpoint.com",
        )
        assert config.endpoint_url == "https://custom.endpoint.com"

    def test_endpoint_url_without_account_id(self):
        """Config with endpoint_url but no account_id should be configured."""
        config = R2StorageConfig(
            endpoint_url="https://custom.endpoint.com",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name="bucket",
        )
        assert config.is_configured is True

    def test_default_presigned_url_expiry(self):
        """Default presigned URL expiry should be 3600."""
        config = R2StorageConfig()
        assert config.presigned_url_expiry == 3600

    def test_custom_presigned_url_expiry(self):
        """Custom presigned URL expiry should be respected."""
        config = R2StorageConfig(presigned_url_expiry=7200)
        assert config.presigned_url_expiry == 7200

    def test_from_env_empty(self):
        """from_env with no env vars should return unconfigured config."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = R2StorageConfig.from_env()
            assert config.is_configured is False

    def test_from_env_full(self):
        """from_env with all env vars should return configured config."""
        env_vars = {
            "R2_ACCOUNT_ID": "test_account",
            "R2_ACCESS_KEY_ID": "test_key",
            "R2_SECRET_ACCESS_KEY": "test_secret",
            "R2_BUCKET_NAME": "test-bucket",
            "R2_PRESIGNED_URL_EXPIRY": "7200",
        }
        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = R2StorageConfig.from_env()
            assert config.is_configured is True
            assert config.account_id == "test_account"
            assert config.access_key_id == "test_key"
            assert config.secret_access_key == "test_secret"
            assert config.bucket_name == "test-bucket"
            assert config.presigned_url_expiry == 7200


class TestStorageConfig:
    """Tests for StorageConfig."""

    def test_default_local_path(self):
        """Default local path should be ./reports."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = StorageConfig()
            assert config.local_path == Path("./reports")

    def test_custom_local_path(self):
        """Custom local path should be respected."""
        config = StorageConfig(local_path=Path("/custom/path"))
        assert config.local_path == Path("/custom/path")

    def test_local_path_from_env(self):
        """Local path should be read from REPORTS_OUTPUT_DIR."""
        with mock.patch.dict(os.environ, {"REPORTS_OUTPUT_DIR": "/env/path"}, clear=True):
            config = StorageConfig()
            assert config.local_path == Path("/env/path")

    def test_is_r2_enabled_false(self):
        """is_r2_enabled should be False when R2 not configured."""
        config = StorageConfig()
        assert config.is_r2_enabled is False

    def test_is_r2_enabled_true(self):
        """is_r2_enabled should be True when R2 is configured."""
        r2_config = R2StorageConfig(
            account_id="test",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name="bucket",
        )
        config = StorageConfig(r2=r2_config)
        assert config.is_r2_enabled is True

    def test_from_env_local_only(self):
        """from_env without R2 vars should return local-only config."""
        with mock.patch.dict(os.environ, {"REPORTS_OUTPUT_DIR": "/reports"}, clear=True):
            config = StorageConfig.from_env()
            assert config.local_path == Path("/reports")
            assert config.r2 is None
            assert config.is_r2_enabled is False

    def test_from_env_with_r2(self):
        """from_env with R2 vars should return config with R2."""
        env_vars = {
            "REPORTS_OUTPUT_DIR": "/reports",
            "R2_ACCOUNT_ID": "test_account",
            "R2_ACCESS_KEY_ID": "test_key",
            "R2_SECRET_ACCESS_KEY": "test_secret",
            "R2_BUCKET_NAME": "test-bucket",
        }
        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = StorageConfig.from_env()
            assert config.local_path == Path("/reports")
            assert config.r2 is not None
            assert config.is_r2_enabled is True
