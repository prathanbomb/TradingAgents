"""FastAPI dependency injection providers."""

from functools import lru_cache

from tradingagents.api.config import APIConfig
from tradingagents.api.job_store import JobStore


@lru_cache
def get_api_config() -> APIConfig:
    return APIConfig.from_env()


@lru_cache
def get_job_store(config: APIConfig = None) -> JobStore:
    if config is None:
        config = get_api_config()
    return JobStore(db_path=config.db_path)


def get_queue(config: APIConfig = None):
    """Get RQ Queue instance. Not cached — creates fresh connection per request."""
    import redis as redis_lib
    from rq import Queue

    if config is None:
        config = get_api_config()
    conn = redis_lib.from_url(config.redis_url)
    return Queue(name=config.queue_name, connection=conn)
