"""Pydantic request/response models for the API."""

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

JobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class JobRequest(BaseModel):
    ticker: Optional[str] = None
    tickers: Optional[List[str]] = None
    trade_date: Optional[str] = None
    analysts: Optional[List[str]] = None
    callback_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_tickers(self) -> "JobRequest":
        if not self.ticker and not self.tickers:
            raise ValueError("Either 'ticker' or 'tickers' must be provided")
        if self.ticker and self.tickers:
            raise ValueError("Provide either 'ticker' or 'tickers', not both")
        return self

    def get_tickers(self) -> List[str]:
        if self.tickers:
            return [t.upper().strip() for t in self.tickers]
        return [self.ticker.upper().strip()]

    def get_trade_date(self) -> str:
        return self.trade_date or date.today().strftime("%Y-%m-%d")

    def get_analysts(self) -> Optional[List[str]]:
        if self.analysts:
            return [a.strip() for a in self.analysts]
        return None


class JobResponse(BaseModel):
    job_id: str
    ticker: str
    trade_date: str
    status: JobStatus
    submitted_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    reports: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    _links: Optional[Dict[str, str]] = None


class JobSubmitResponse(BaseModel):
    job_id: str
    ticker: str
    trade_date: str
    message: str


class HealthResponse(BaseModel):
    status: str
    task_slot: str
    jobs_db: str


class ObservabilityQueryParams(BaseModel):
    ticker: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    run_id: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
