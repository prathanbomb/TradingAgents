# Testing Patterns

**Analysis Date:** 2025-02-18

## Test Framework

**Runner:**
- pytest 8.4.1
- Config: No explicit pytest configuration file detected (uses defaults)

**Assertion Library:**
- pytest's built-in `assert` statement

**Run Commands:**
```bash
python3 -m pytest              # Run all tests
python3 -m pytest -v           # Verbose mode
python3 -m pytest tests/       # Run tests in tests directory
# No coverage command configured
```

**Current test count:** 70 tests collected

## Test File Organization

**Location:**
- Co-located pattern: Tests mirror source structure in `tests/` directory
- Source: `tradingagents/storage/service.py`
- Test: `tests/storage/test_service.py`

**Naming:**
- Test files prefixed with `test_`: `test_service.py`, `test_local_backend.py`, `test_config.py`
- Test classes prefixed with `Test`: `TestStorageService`, `TestLocalStorageBackend`, `TestR2StorageConfig`
- Test methods prefixed with `test_`: `test_upload_report`, `test_exists_true`

**Structure:**
```
tests/
├── __init__.py
└── storage/
    ├── __init__.py
    ├── test_service.py          # Tests for StorageService
    ├── test_local_backend.py    # Tests for LocalStorageBackend
    ├── test_config.py           # Tests for config models
    └── test_r2_backend.py       # Tests for R2StorageBackend
```

## Test Structure

**Suite Organization:**
Tests organized by class grouping related functionality:

```python
class TestStorageService:
    """Tests for StorageService."""
    # All tests for StorageService class

class TestStorageServiceWithR2:
    """Tests for StorageService with R2 configuration."""
    # Tests for R2-specific behavior

class TestStorageServiceR2ImportError:
    """Tests for StorageService when boto3 is not available."""
    # Tests for edge cases
```

**Patterns:**

**Setup with pytest fixtures:**
```python
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
```

**Teardown:**
- Context managers used for automatic cleanup: `with tempfile.TemporaryDirectory()`
- No explicit teardown methods needed

**Assertion pattern:**
```python
def test_upload_report(self, local_service, temp_dir):
    """upload_report should write to local backend."""
    content = "# Test Report\n\nContent here."
    results = local_service.upload_report(content, "AAPL/report.md")

    assert "local" in results
    assert (temp_dir / "AAPL/report.md").exists()
    assert (temp_dir / "AAPL/report.md").read_text() == content
```

**Test naming follows "should" pattern:**
- `test_upload_report_should_write_to_local_backend`
- `test_get_url_should_return_local_path`
- `test_exists_should_check_primary_backend`

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**

**Mocking external dependencies:**
```python
from unittest import mock

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
```

**Mocking errors:**
```python
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
```

**Mocking environment variables:**
```python
def test_from_env_empty(self):
    """from_env with no env vars should return unconfigured config."""
    with mock.patch.dict(os.environ, {}, clear=True):
        config = R2StorageConfig.from_env()
        assert config.is_configured is False
```

**What to Mock:**
- External service calls (R2 storage, Google Sheets)
- Environment variables
- File system operations (when testing business logic)
- Methods that would have side effects

**What NOT to Mock:**
- Simple data classes and value objects
- Configuration models (test actual validation logic)
- File system in integration tests (use temp directories)

## Fixtures and Factories

**Test Data:**

**In-line test data creation:**
```python
def test_upload_report(self, local_service, temp_dir):
    content = "# Test Report\n\nContent here."
    results = local_service.upload_report(content, "AAPL/report.md")
```

**Using pytest fixtures for setup:**
```python
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
```

**Location:**
- Fixtures defined within test classes
- Reusable fixtures at module level (not commonly used yet)
- No separate fixtures directory or factory modules

**Temp directory management:**
```python
@pytest.fixture
def temp_dir(self):
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

## Coverage

**Requirements:** None enforced (no coverage target configured)

**View Coverage:**
```bash
# No coverage tool configured
# To add coverage:
pip install pytest-cov
python3 -m pytest --cov=tradingagents --cov-report=html
```

**Current coverage status:** Unknown (not measured)

## Test Types

**Unit Tests:**
- Primary focus of current test suite
- Test individual classes and methods in isolation
- Use mocking for external dependencies
- Example: `tests/storage/test_config.py` tests configuration model validation

**Integration Tests:**
- Limited integration testing present
- Tests that exercise multiple components together
- Example: `tests/storage/test_service.py` tests service with multiple backends

**E2E Tests:**
- Not detected
- No end-to-end workflow tests

**Property-based tests:**
- Not used
- Consider adding hypothesis for complex data validation

## Common Patterns

**Testing exceptions:**
```python
def test_endpoint_url_without_account_id(self):
    """Config with endpoint_url but no account_id should be configured."""
    config = R2StorageConfig(
        endpoint_url="https://custom.endpoint.com",
        access_key_id="key",
        secret_access_key="secret",
        bucket_name="bucket",
    )
    assert config.is_configured is True
```

**Testing with file system:**
```python
def test_upload_bytes(self, storage, temp_dir):
    """upload_bytes should write bytes to file."""
    content = b"# Test Report\n\nThis is a test."
    result = storage.upload_bytes(content, "reports/test.md")

    assert result == str(temp_dir / "reports/test.md")
    assert (temp_dir / "reports/test.md").exists()
    assert (temp_dir / "reports/test.md").read_bytes() == content
```

**Testing conditional behavior:**
```python
def test_r2_backend_initialized(self, r2_config):
    """R2 backend should be initialized when configured."""
    service = StorageService(r2_config)

    assert "r2" in service.backends
    assert service.primary_backend == "r2"
    assert service.is_r2_enabled is True
```

**Testing error handling:**
```python
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
```

## Areas Needing More Tests

**Based on codebase analysis:**

**Missing test coverage:**
- `tradingagents/graph/` - No tests for trading graph logic
- `tradingagents/agents/` - No tests for agent implementations
- `tradingagents/dataflows/` - No tests for data flow logic
- `tradingagents/backtracking/` - No tests for performance tracking
- `tradingagents/portfolio/` - No tests for portfolio management

**Complex logic needing tests:**
- Graph state management and transitions
- Agent debate logic and reflection
- Memory system operations
- Signal processing logic

**Recommendations:**
1. Add pytest-cov for coverage measurement
2. Set minimum coverage threshold (e.g., 80%)
3. Add integration tests for graph execution
4. Add tests for agent decision-making logic
5. Add property-based tests for configuration validation

---

*Testing analysis: 2025-02-18*
