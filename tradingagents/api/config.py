"""API configuration model."""

import os
from typing import List

from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API server configuration loaded from environment variables."""

    api_port: int = Field(default=8000)
    max_concurrent_jobs: int = Field(default=1)
    job_timeout: int = Field(default=3600)
    db_path: str = Field(default="./data/jobs.db")
    api_keys: List[str] = Field(default_factory=list)

    @property
    def auth_enabled(self) -> bool:
        return len(self.api_keys) > 0

    @classmethod
    def from_env(cls) -> "APIConfig":
        raw_keys = os.getenv("TRADING_API_KEYS", "").strip()
        api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()] if raw_keys else []

        return cls(
            api_port=int(os.getenv("API_PORT", "8000")),
            max_concurrent_jobs=int(os.getenv("MAX_CONCURRENT_JOBS", "1")),
            job_timeout=int(os.getenv("JOB_TIMEOUT", "3600")),
            db_path=os.getenv("DB_PATH", "./data/jobs.db"),
            api_keys=api_keys,
        )
