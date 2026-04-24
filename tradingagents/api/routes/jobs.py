"""Job management routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from rq import Queue
from rq.job import Job as RqJob

from tradingagents.api.auth import create_auth_dependency
from tradingagents.api.config import APIConfig
from tradingagents.api.deps import get_api_config, get_job_store, get_queue
from tradingagents.api.job_store import JobStore
from tradingagents.api.models import (
    JobListResponse,
    JobRequest,
    JobResponse,
    JobSubmitResponse,
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", status_code=202, response_model=JobSubmitResponse)
async def submit_job(
    request: JobRequest,
    queue: Queue = Depends(get_queue),
    store: JobStore = Depends(get_job_store),
    config: APIConfig = Depends(get_api_config),
):
    """Submit analysis job(s). Accepts single ticker or batch."""
    tickers = request.get_tickers()
    trade_date = request.get_trade_date()

    # Build config snapshot for the worker
    try:
        from tradingagents.config.models import TradingAgentsConfig
        ta_config = TradingAgentsConfig.from_env()
        config_snapshot = ta_config.to_legacy_dict()
    except Exception:
        config_snapshot = None

    job_ids = []
    for ticker in tickers:
        job_id = uuid.uuid4().hex[:12]
        store.create(job_id, ticker, trade_date, config_snapshot=config_snapshot)

        queue.enqueue(
            "tradingagents.api.tasks.run_analysis",
            job_id=job_id,
            ticker=ticker,
            trade_date=trade_date,
            config_snapshot=config_snapshot,
            db_path=config.db_path,
            job_timeout=config.job_timeout,
        )
        job_ids.append(job_id)

    return JobSubmitResponse(
        job_ids=job_ids,
        tickers=tickers,
        trade_date=trade_date,
        message=f"Submitted {len(job_ids)} job(s)",
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    store: JobStore = Depends(get_job_store),
):
    """List jobs with optional filters."""
    jobs, total = store.list_jobs(status=status, ticker=ticker, limit=limit, offset=offset)
    return JobListResponse(
        jobs=[JobResponse(**j.model_dump()) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
):
    """Get job status and result."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job.model_dump())


@router.delete("/{job_id}", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    queue: Queue = Depends(get_queue),
    store: JobStore = Depends(get_job_store),
):
    """Cancel a pending job."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending",):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in '{job.status}' state")

    # Try to remove from RQ queue
    try:
        for rq_job in queue.jobs:
            if rq_job.kwargs.get("job_id") == job_id:
                rq_job.cancel()
                break
    except Exception:
        pass

    store.cancel(job_id)
    job = store.get(job_id)
    return JobResponse(**job.model_dump())
