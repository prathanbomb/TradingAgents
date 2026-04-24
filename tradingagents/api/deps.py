"""FastAPI dependency injection providers."""

from functools import lru_cache

from tradingagents.api.config import APIConfig
from tradingagents.api.job_store import JobStore
from tradingagents.api.task_manager import BackgroundTaskManager


@lru_cache
def get_api_config() -> APIConfig:
    return APIConfig.from_env()


@lru_cache
def get_job_store(config: APIConfig = None) -> JobStore:
    if config is None:
        config = get_api_config()
    return JobStore(db_path=config.db_path)


@lru_cache
def get_task_manager() -> BackgroundTaskManager:
    return BackgroundTaskManager()
