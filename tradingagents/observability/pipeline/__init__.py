"""Async data pipeline module for non-blocking observability.

This module provides the AsyncDataPipeline and helper functions for
easy integration with the trading system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from tradingagents.observability.pipeline.async_queue import AsyncDataPipeline
from tradingagents.observability.storage import SQLiteDecisionStore

logger = logging.getLogger(__name__)

__all__ = [
    "AsyncDataPipeline",
    "SQLiteDecisionStore",
    "create_pipeline",
    "managed_pipeline",
]


async def create_pipeline(
    db_path: str = "./data/observability.db",
    max_queue_size: int = 1000,
    batch_size: int = 50,
    flush_interval: float = 1.0,
    auto_start: bool = True,
) -> AsyncDataPipeline:
    """Create and configure a complete async data pipeline.

    This factory function sets up a complete observability pipeline with
    SQLite storage and async queue for non-blocking data capture.

    Args:
        db_path: Path to SQLite database (default: ./data/observability.db)
        max_queue_size: Maximum queue size for backpressure (default: 1000)
        batch_size: Number of events to batch before writing (default: 50)
        flush_interval: Maximum seconds between flushes (default: 1.0)
        auto_start: Whether to start consumer task immediately (default: True)

    Returns:
        Configured AsyncDataPipeline instance

    Example:
        ```python
        # Simple usage with auto-start
        pipeline = await create_pipeline()

        # Pass to instrumentation components
        await pipeline.producer(decision_record)

        # Cleanup on shutdown
        await pipeline.stop()
        ```

    Example with context manager:
        ```python
        async with managed_pipeline() as pipeline:
            # Pipeline auto-started
            await pipeline.producer(decision_record)
            # Pipeline auto-stopped on exit
        ```
    """
    store = SQLiteDecisionStore(db_path)
    pipeline = AsyncDataPipeline(
        storage_handler=store.store_batch,
        max_queue_size=max_queue_size,
        batch_size=batch_size,
        flush_interval=flush_interval,
    )

    if auto_start:
        await pipeline.start()

    logger.info(
        f"Pipeline created: db={db_path}, max_queue={max_queue_size}, "
        f"batch_size={batch_size}"
    )

    return pipeline


@asynccontextmanager
async def managed_pipeline(
    db_path: str = "./data/observability.db",
    max_queue_size: int = 1000,
    batch_size: int = 50,
    flush_interval: float = 1.0,
):
    """Context manager for automatic pipeline lifecycle management.

    Handles pipeline startup and graceful shutdown automatically.

    Args:
        db_path: Path to SQLite database (default: ./data/observability.db)
        max_queue_size: Maximum queue size for backpressure (default: 1000)
        batch_size: Number of events to batch before writing (default: 50)
        flush_interval: Maximum seconds between flushes (default: 1.0)

    Yields:
        AsyncDataPipeline instance

    Example:
        ```python
        async def trading_session():
            async with managed_pipeline() as pipeline:
                # Pipeline is auto-started
                for ticker in tickers:
                    decision = await analyze(ticker)
                    await pipeline.producer(decision)
            # Pipeline is auto-stopped with flush
        ```
    """
    pipeline = await create_pipeline(
        db_path=db_path,
        max_queue_size=max_queue_size,
        batch_size=batch_size,
        flush_interval=flush_interval,
        auto_start=True,
    )

    try:
        yield pipeline
    finally:
        await pipeline.stop()
        logger.info("Managed pipeline stopped gracefully")


def get_pipeline_config(
    max_queue_size: int = 1000,
    batch_size: int = 50,
    flush_interval: float = 1.0,
) -> dict:
    """Get default pipeline configuration.

    Helper function for configuration files and validation.

    Args:
        max_queue_size: Maximum queue size for backpressure
        batch_size: Number of events to batch before writing
        flush_interval: Maximum seconds between flushes

    Returns:
        Configuration dictionary
    """
    return {
        "max_queue_size": max_queue_size,
        "batch_size": batch_size,
        "flush_interval": flush_interval,
    }
