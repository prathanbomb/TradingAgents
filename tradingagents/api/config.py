"""API configuration model."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API server configuration loaded from environment variables."""

    redis_url: str = Field(default="redis://localhost:6379/0")
    api_port: int = Field(default=8000)
    max_workers: int = Field(default=2)
    job_timeout: int = Field(default=3600)
    db_path: str = Field(default="./data/jobs.db")
    api_keys: List[str] = Field(default_factory=list)
    queue_name: str = "trading"

    @property
    def auth_enabled(self) -> bool:
        return len(self.api_keys) > 0

    @classmethod
    def from_env(cls) -> "APIConfig":
        raw_keys = os.getenv("TRADING_API_KEYS", "").strip()
        api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()] if raw_keys else []

        return cls(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            max_workers=int(os.getenv("MAX_WORKERS", "2")),
            job_timeout=int(os.getenv("JOB_TIMEOUT", "3600")),
            db_path=os.getenv("DB_PATH", "./data/jobs.db"),
            api_keys=api_keys,
        )
