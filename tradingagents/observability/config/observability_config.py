"""Observability configuration model for data collection.

This module defines ObservabilityConfig for controlling observability
behavior including storage, pipeline, and event filtering options.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ObservabilityConfig(BaseModel):
    """Configuration for observability data collection.

    Controls how observability data is captured, filtered, and stored.
    All settings are optional with sensible defaults for non-intrusive operation.

    Attributes:
        enabled: Enable/disable observability data collection (default: False)
        db_path: Path to SQLite database for decision storage
        max_queue_size: Maximum queue size for backpressure control
        batch_size: Number of events to batch before writing
        flush_interval: Flush interval in seconds
        capture_full_transcripts: Capture full LLM transcripts (expensive)
        sample_rate: Sample rate for full transcript capture (0.0-1.0)
        structured_logging: Enable structured JSON logging
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # Enable/disable observability
    enabled: bool = Field(
        default=False, description="Enable observability data collection"
    )

    # Storage configuration
    db_path: Optional[Path] = Field(
        default=None, description="Path to SQLite database for decision storage"
    )

    # Pipeline configuration
    max_queue_size: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum queue size for backpressure",
    )
    batch_size: int = Field(
        default=50, ge=1, le=500, description="Number of events to batch before writing"
    )
    flush_interval: float = Field(
        default=1.0, ge=0.1, le=60.0, description="Flush interval in seconds"
    )

    # Event filtering (avoid information overload)
    capture_full_transcripts: bool = Field(
        default=False, description="Capture full LLM transcripts (expensive)"
    )
    sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sample rate for full transcript capture",
    )

    # Logging configuration
    structured_logging: bool = Field(
        default=True, description="Enable structured JSON logging"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    @model_validator(mode="after")
    def set_default_db_path(self) -> "ObservabilityConfig":
        """Set default database path if not provided."""
        if self.db_path is None:
            self.db_path = Path("./data/observability.db")
        return self

    @property
    def is_configured(self) -> bool:
        """Check if observability is properly configured."""
        return self.enabled and self.db_path is not None

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Create config from environment variables.

        Environment variables:
            OBSERVABILITY_ENABLED: "true" or "false" (default: false)
            OBSERVABILITY_DB_PATH: Path to SQLite database
            OBSERVABILITY_MAX_QUEUE_SIZE: Max queue size (default: 1000)
            OBSERVABILITY_BATCH_SIZE: Batch size (default: 50)
            OBSERVABILITY_FLUSH_INTERVAL: Flush interval in seconds (default: 1.0)
            OBSERVABILITY_FULL_TRANSCRIPTS: "true" or "false" (default: false)
            OBSERVABILITY_SAMPLE_RATE: Sample rate 0.0-1.0 (default: 0.1)
            OBSERVABILITY_STRUCTURED_LOGGING: "true" or "false" (default: true)
            OBSERVABILITY_LOG_LEVEL: Log level (default: INFO)

        Returns:
            ObservabilityConfig instance
        """
        return cls(
            enabled=os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true",
            db_path=Path(os.getenv("OBSERVABILITY_DB_PATH"))
            if os.getenv("OBSERVABILITY_DB_PATH")
            else None,
            max_queue_size=int(os.getenv("OBSERVABILITY_MAX_QUEUE_SIZE", "1000")),
            batch_size=int(os.getenv("OBSERVABILITY_BATCH_SIZE", "50")),
            flush_interval=float(os.getenv("OBSERVABILITY_FLUSH_INTERVAL", "1.0")),
            capture_full_transcripts=os.getenv("OBSERVABILITY_FULL_TRANSCRIPTS", "false")
            .lower()
            == "true",
            sample_rate=float(os.getenv("OBSERVABILITY_SAMPLE_RATE", "0.1")),
            structured_logging=os.getenv("OBSERVABILITY_STRUCTURED_LOGGING", "true")
            .lower()
            == "true",
            log_level=os.getenv("OBSERVABILITY_LOG_LEVEL", "INFO"),
        )
