"""RQ worker entry point.

Usage: python -m tradingagents.api.worker
"""

import logging

import redis
from rq import Worker, Queue

from tradingagents.api.config import APIConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    config = APIConfig.from_env()
    conn = redis.from_url(config.redis_url)

    logger.info(f"Starting RQ worker (queue={config.queue_name}, redis={config.redis_url})")
    worker = Worker(
        queues=[config.queue_name],
        connection=conn,
    )
    worker.work(logging_level="INFO")


if __name__ == "__main__":
    main()
