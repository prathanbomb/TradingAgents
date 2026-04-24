"""FastAPI dependency injection providers."""

from functools import lru_cache

from fastapi import Depends

from tradingagents.api.config import APIConfig
from tradingagents.api.job_store import JobStore
from tradingagents.api.task_manager import BackgroundTaskManager


@lru_cache
def get_api_config() -> APIConfig:
    return APIConfig.from_env()


def get_job_store(config: APIConfig = Depends(get_api_config)) -> JobStore:
    return JobStore(db_path=config.db_path)


@lru_cache
def get_task_manager() -> BackgroundTaskManager:
    return BackgroundTaskManager()
