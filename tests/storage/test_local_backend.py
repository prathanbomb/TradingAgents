"""Tests for local storage backend."""

import tempfile
from pathlib import Path

import pytest

from tradingagents.storage.backends.local import LocalStorageBackend


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a LocalStorageBackend instance."""
        return LocalStorageBackend(temp_dir)

    def test_backend_name(self, storage):
        """Backend name should be 'local'."""
        assert storage.backend_name == "local"

    def test_base_path_created(self, temp_dir):
        """Base path should be created if it doesn't exist."""
        new_path = temp_dir / "new_dir"
        storage = LocalStorageBackend(new_path)
        assert new_path.exists()

    def test_upload_bytes(self, storage, temp_dir):
        """upload_bytes should write bytes to file."""
        content = b"# Test Report\n\nThis is a test."
        result = storage.upload_bytes(content, "reports/test.md")

        assert result == str(temp_dir / "reports/test.md")
        assert (temp_dir / "reports/test.md").exists()
        assert (temp_dir / "reports/test.md").read_bytes() == content

    def test_upload_bytes_creates_directories(self, storage, temp_dir):
        """upload_bytes should create parent directories."""
        content = b"test content"
        storage.upload_bytes(content, "deep/nested/path/file.txt")

        assert (temp_dir / "deep/nested/path/file.txt").exists()

    def test_upload_file(self, storage, temp_dir):
        """upload_file should copy file to storage."""
        # Create source file
        source = temp_dir / "source.txt"
        source.write_text("source content")

        result = storage.upload_file(source, "copied/file.txt")

        assert result == str(temp_dir / "copied/file.txt")
        assert (temp_dir / "copied/file.txt").exists()
        assert (temp_dir / "copied/file.txt").read_text() == "source content"

    def test_get_url_exists(self, storage, temp_dir):
        """get_url should return path for existing file."""
        (temp_dir / "test.md").write_text("content")

        result = storage.get_url("test.md")

        assert result == str(temp_dir / "test.md")

    def test_get_url_not_exists(self, storage):
        """get_url should return None for non-existent file."""
        result = storage.get_url("nonexistent.md")
        assert result is None

    def test_exists_true(self, storage, temp_dir):
        """exists should return True for existing file."""
        (temp_dir / "test.md").write_text("content")

        assert storage.exists("test.md") is True

    def test_exists_false(self, storage):
        """exists should return False for non-existent file."""
        assert storage.exists("nonexistent.md") is False

    def test_delete_existing_file(self, storage, temp_dir):
        """delete should remove existing file."""
        (temp_dir / "test.md").write_text("content")

        result = storage.delete("test.md")

        assert result is True
        assert not (temp_dir / "test.md").exists()

    def test_delete_nonexistent_file(self, storage):
        """delete should return False for non-existent file."""
        result = storage.delete("nonexistent.md")
        assert result is False

    def test_delete_directory(self, storage, temp_dir):
        """delete should remove directory."""
        (temp_dir / "reports").mkdir()
        (temp_dir / "reports/test.md").write_text("content")

        result = storage.delete("reports")

        assert result is True
        assert not (temp_dir / "reports").exists()

    def test_list_files_directory(self, storage, temp_dir):
        """list_files should list files in directory."""
        (temp_dir / "reports").mkdir()
        (temp_dir / "reports/a.md").write_text("a")
        (temp_dir / "reports/b.md").write_text("b")

        result = storage.list_files("reports")

        assert sorted(result) == ["reports/a.md", "reports/b.md"]

    def test_list_files_nested(self, storage, temp_dir):
        """list_files should list nested files."""
        (temp_dir / "reports/sub").mkdir(parents=True)
        (temp_dir / "reports/a.md").write_text("a")
        (temp_dir / "reports/sub/b.md").write_text("b")

        result = storage.list_files("reports")

        assert sorted(result) == ["reports/a.md", "reports/sub/b.md"]

    def test_list_files_single_file(self, storage, temp_dir):
        """list_files should return single file if prefix is a file."""
        (temp_dir / "test.md").write_text("content")

        result = storage.list_files("test.md")

        assert result == ["test.md"]

    def test_list_files_nonexistent(self, storage):
        """list_files should return empty list for non-existent prefix."""
        result = storage.list_files("nonexistent")
        assert result == []

    def test_content_type_ignored(self, storage, temp_dir):
        """content_type should be ignored for local storage."""
        content = b"test"
        result = storage.upload_bytes(content, "test.md", content_type="text/markdown")

        # Should succeed without error
        assert (temp_dir / "test.md").exists()
