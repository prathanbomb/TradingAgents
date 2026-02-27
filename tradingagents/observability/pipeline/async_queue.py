"""Asynchronous data pipeline for non-blocking observability.

This module implements a producer-consumer pattern using asyncio.Queue
to decouple data capture from storage operations, ensuring the trading
pipeline never blocks on observability writes (DATA-02 requirement).
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Union

logger = logging.getLogger(__name__)


class AsyncDataPipeline:
    """Non-blocking data collection pipeline.

    Decouples event capture (producer) from storage (consumer) using
    asyncio.Queue with bounded size for backpressure control.

    Trading pipeline never blocks on I/O operations.

    Example:
        ```python
        async def mock_storage(batch):
            # Write to database
            pass

        pipeline = AsyncDataPipeline(
            storage_handler=mock_storage,
            max_queue_size=1000,
            batch_size=50
        )
        await pipeline.start()

        # Producer usage (non-blocking)
        await pipeline.producer(decision_record)

        # Cleanup
        await pipeline.stop()
        ```
    """

    def __init__(
        self,
        storage_handler: Callable,
        max_queue_size: int = 1000,
        batch_size: int = 50,
        flush_interval: float = 1.0,
    ):
        """Initialize the async data pipeline.

        Args:
            storage_handler: Async callable that accepts a batch of records
            max_queue_size: Maximum queue size for backpressure (default 1000)
            batch_size: Number of events to batch before writing (default 50)
            flush_interval: Maximum seconds between flushes (default 1.0)
        """
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.storage_handler = storage_handler
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.consumer_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._dropped_events = 0

        logger.debug(
            f"AsyncDataPipeline initialized: max_queue_size={max_queue_size}, "
            f"batch_size={batch_size}, flush_interval={flush_interval}"
        )

    async def producer(self, data: Union[Any, List[Any]]) -> bool:
        """Add data to queue (non-blocking with backpressure).

        Args:
            data: Single record or list of records to enqueue

        Returns:
            True if enqueued successfully, False if queue full (dropped)
        """
        # Handle batch input
        items = data if isinstance(data, list) else [data]

        try:
            for item in items:
                await asyncio.wait_for(
                    self.queue.put(item),
                    timeout=0.1,  # Brief wait for backpressure
                )
            return True
        except asyncio.TimeoutError:
            # Queue full, drop data rather than block trading
            self._dropped_events += len(items)
            logger.warning(
                f"Observability queue full, dropping {len(items)} event(s). "
                f"Total dropped: {self._dropped_events}"
            )
            return False

    async def consumer(self):
        """Process events from queue and write to storage.

        Runs in background task. Batches writes for efficiency.
        """
        batch: List[Any] = []
        last_flush = time.time()

        logger.info("Consumer task started")

        while not self._shutdown:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                batch.append(event)

                # Flush when batch size reached or interval elapsed
                if (
                    len(batch) >= self.batch_size
                    or time.time() - last_flush > self.flush_interval
                ):
                    await self._flush_batch(batch)
                    batch = []
                    last_flush = time.time()
                    self.queue.task_done()

            except asyncio.TimeoutError:
                # Flush remaining batch on timeout
                if batch:
                    await self._flush_batch(batch)
                    batch = []
                    last_flush = time.time()

        # Flush any remaining events on shutdown
        if batch:
            await self._flush_batch(batch)

        logger.info("Consumer task stopped")

    async def _flush_batch(self, batch: List[Any]):
        """Write batch to storage with error handling.

        Args:
            batch: List of records to write to storage
        """
        if not batch:
            return

        try:
            await self.storage_handler(batch)
            logger.debug(f"Flushed {len(batch)} events to storage")
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}", exc_info=True)
            # Could implement retry here or dead-letter queue
            # For now, we log and continue to avoid blocking

    async def start(self):
        """Start the background consumer task."""
        if self.consumer_task is None or self.consumer_task.done():
            self.consumer_task = asyncio.create_task(self.consumer())
            logger.info("Async data pipeline started")

    async def stop(self):
        """Gracefully shutdown consumer and flush remaining events."""
        logger.info("Stopping async data pipeline...")
        self._shutdown = True

        if self.consumer_task and not self.consumer_task.done():
            # Wait for queue to empty (with timeout)
            try:
                await asyncio.wait_for(self.queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Shutdown timeout: some events may not be flushed")

            # Cancel consumer task
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

        logger.info(
            f"Async data pipeline stopped. Dropped events: {self._dropped_events}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics.

        Returns:
            Dict with queue_size, max_queue_size, dropped_events, consumer_running
        """
        return {
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.queue.maxsize,
            "dropped_events": self._dropped_events,
            "consumer_running": (
                self.consumer_task is not None and not self.consumer_task.done()
            ),
        }

    def __repr__(self) -> str:
        """String representation of pipeline."""
        return (
            f"AsyncDataPipeline(queue_size={self.queue.qsize()}, "
            f"max_queue_size={self.queue.maxsize}, "
            f"dropped_events={self._dropped_events})"
        )


# Import Optional for type hint
from typing import Optional
