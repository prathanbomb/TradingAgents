# Coding Conventions

**Analysis Date:** 2025-02-18

## Naming Patterns

**Files:**
- `snake_case` for all Python modules and packages
- Test files prefixed with `test_` and located in `tests/` directory mirroring source structure
- Configuration files use descriptive names: `models.py`, `base.py`, `service.py`

**Functions:**
- `snake_case` for all function and method names
- Private methods prefixed with underscore: `_init_backends()`, `_log_state()`
- Factory functions use `create_*` pattern: `create_manager_from_config()`, `create_portfolio_manager_from_config()`

**Variables:**
- `snake_case` for local variables and parameters
- Private instance variables prefixed with underscore: `_backends`, `_config`, `_primary_backend`
- Constants use `UPPER_CASE`: Not widely used, but would be expected

**Types/Classes:**
- `PascalCase` for all class names
- Protocol classes ending with `Protocol` suffix: `StorageBackend`, `DataVendor`, `DataVendor(Protocol)`
- Exception classes ending with `Error` suffix: `StorageError`, `StorageUploadError`, `StorageConfigurationError`
- Abstract base classes prefixed with `Base`: `BaseStorageBackend`, `BaseVendor`, `BaseManager`
- Configuration classes ending with `Config`: `LLMConfig`, `StorageConfig`, `ManagerConfig`

## Code Style

**Formatting:**
- No explicit formatter configured (no black, ruff, or autopep8 in pyproject.toml)
- Standard Python indentation (4 spaces)
- Line length appears to follow PEP 8 guidelines (typically 79-88 characters)

**Linting:**
- No explicit linting configuration detected
- Standard Python coding practices followed

**Import Organization:**
Imports follow this order:

1. Standard library imports
2. Third-party imports (langchain, pydantic, etc.)
3. Local application imports

Example from `tradingagents/storage/service.py`:
```python
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .backends.local import LocalStorageBackend
from .base import BaseStorageBackend
from . import tldr
```

**Path Aliases:**
- No explicit path aliases configured
- Relative imports used within packages: `from .base import BaseStorageBackend`
- Absolute imports for cross-package references: `from tradingagents.config import StorageConfig`

## Error Handling

**Patterns:**
- Custom exception hierarchy with base exception class
- Specific exceptions for different error types: `StorageUploadError`, `StorageDownloadError`, `StorageConfigurationError`
- Exception classes include contextual information (backend name, file key)

**Graceful degradation:**
```python
# From tradingagents/storage/service.py
try:
    from .backends.r2 import R2StorageBackend
    self._backends["r2"] = R2StorageBackend(config.r2)
    self._primary_backend = "r2"
except ImportError:
    logger.warning("boto3 not installed, R2 storage unavailable.")
except Exception as e:
    logger.warning(f"Failed to initialize R2 backend: {e}")
```

**Return values for errors:**
- Empty dict returned on upload failure: `return results` (only successful backends)
- `None` returned for missing files: `return None` if file not found
- `False` returned for failed operations: `return False` if deletion unsuccessful

## Logging

**Framework:** Standard Python `logging` module

**Pattern for getting loggers:**
```python
# From tradingagents/logging_config.py
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# Usage in modules:
logger = logging.getLogger(__name__)
```

**Log levels used:**
- `logger.debug()`: Detailed operation tracking (file uploads, state changes)
- `logger.info()`: Important events (initialization, analysis start/completion)
- `logger.warning()`: Recoverable issues (missing dependencies, failed backends)
- `logger.error()`: Operation failures (upload failures, delete failures)

**Centralized logging configuration:**
- `tradingagents/logging_config.py` provides `setup_logging()` function
- Configurable via `LOG_LEVEL` environment variable (defaults to INFO)
- Format: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`

## Comments

**When to Comment:**
- Module-level docstrings explain purpose and functionality
- Class docstrings describe responsibility and usage
- Method docstrings follow Google style with Args/Returns sections

**JSDoc/TSDoc equivalent:**
- Google-style docstrings used consistently
- Args section documents parameters with types and descriptions
- Returns section documents return values with types
- Examples from `tradingagents/storage/base.py`:
```python
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
```

## Function Design

**Size:**
- Functions typically 10-50 lines
- Larger functions (100+ lines) are rare and usually involve complex orchestration
- Example: `_log_state()` in `trading_graph.py` (~40 lines)

**Parameters:**
- Type hints used consistently for all parameters
- Optional parameters use `Optional[T]` or default values
- Configuration objects used to group related parameters (e.g., `StorageConfig`, `LLMConfig`)

**Return Values:**
- All functions have return type annotations
- Complex returns use typed dicts or dataclasses
- Multiple returns use tuples: `return final_state, decision`
- Union types for variant returns: `Dict[str, str] | str`

## Module Design

**Exports:**
- `__all__` lists defined explicitly in `__init__.py` files
- Pattern from `tradingagents/storage/__init__.py`:
```python
__all__ = [
    "StorageBackend",
    "BaseStorageBackend",
    "StorageService",
    "StorageError",
    "StorageUploadError",
    "StorageDownloadError",
    "StorageConfigurationError",
]
```

**Barrel Files:**
- Each package has an `__init__.py` that exports public API
- Internal imports hidden: `from .base import BaseStorageBackend`
- Users import from package level: `from tradingagents.storage import StorageService`

**Package organization:**
- Related functionality grouped in subpackages: `storage/`, `config/`, `agents/`, `graph/`
- Each subpackage is self-contained with clear purpose
- Cross-package imports use absolute paths: `from tradingagents.config import StorageConfig`

## Type System Usage

**Type hints:**
- Used consistently throughout the codebase
- Standard library types: `Dict`, `List`, `Optional`, `Tuple`, `Union`
- New-style union syntax: `X | Y` (Python 3.10+)
- Literal types for enums: `Literal["local", "r2"]`

**Special typing patterns:**
- `TYPE_CHECKING` for imports needed only for type hints:
```python
if TYPE_CHECKING:
    from tradingagents.config import StorageConfig
```

- Protocol classes for structural subtyping: `DataVendor(Protocol)`, `StorageBackend(Protocol)`

**Dataclasses:**
- Heavily used for configuration and data models
- Pydantic models for validation: `LLMConfig(BaseModel)`, `StorageConfig(BaseModel)`
- Standard dataclasses for simple data containers: `@dataclass class PredictionRecord`

## Protocol-Based Design

**When to use Protocols:**
- Defining interfaces for multiple implementations
- `StorageBackend(Protocol)` defines storage interface
- `DataVendor(Protocol)` defines data vendor interface
- Allows duck-typing with explicit interface documentation

**Pattern:**
```python
@runtime_checkable
class StorageBackend(Protocol):
    backend_name: str
    def upload_bytes(self, data: bytes, remote_key: str) -> str: ...
```

---

*Convention analysis: 2025-02-18*
