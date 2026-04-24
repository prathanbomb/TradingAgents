"""Job management routes."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response

from tradingagents.api.config import APIConfig
from tradingagents.api.deps import get_api_config, get_job_store, get_task_manager
from tradingagents.api.errors import (
    IdempotencyConflictError,
    JobNotFoundError,
    JobStateConflictError,
)
from tradingagents.api.job_store import JobStore
from tradingagents.api.models import JobRequest, JobResponse, JobSubmitResponse
from tradingagents.api.pagination import add_pagination_headers, paginate
from tradingagents.api.task_manager import BackgroundTaskManager
from tradingagents.api.tasks import run_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _job_links(job_id: str, status: str) -> dict:
    links = {"self": f"/api/v1/jobs/{job_id}"}
    if status in ("pending", "running"):
        links["cancel"] = f"/api/v1/jobs/{job_id}/cancel"
    return links


def _record_to_response(record) -> JobResponse:
    data = record.model_dump()
    data["_links"] = _job_links(record.job_id, record.status)
    return JobResponse(**data)


def _run_and_release(
    job_id: str,
    manager: BackgroundTaskManager,
    store: JobStore,
    **kwargs,
):
    """Wrapper that re-checks cancellation, runs analysis, and releases the slot."""
    try:
        # Re-check status — might have been cancelled between submit and execution
        job = store.get(job_id)
        if job and job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled before execution started")
            return

        run_analysis(
            job_id=job_id,
            cancel_check=lambda: manager.is_cancelled(job_id),
            **kwargs,
        )
    finally:
        manager.release(job_id)


@router.post("", status_code=202, response_model=JobSubmitResponse)
async def submit_job(
    request: Request,
    response: Response,
    body: JobRequest,
    background_tasks: BackgroundTasks,
    store: JobStore = Depends(get_job_store),
    config: APIConfig = Depends(get_api_config),
    manager: BackgroundTaskManager = Depends(get_task_manager),
):
    """Submit analysis job. Accepts single ticker."""
    idempotency_key = request.headers.get("idempotency-key")

    if idempotency_key:
        existing = store.find_by_idempotency_key(idempotency_key)
        if existing:
            response.headers["Location"] = f"/api/v1/jobs/{existing.job_id}"
            raise IdempotencyConflictError(existing.job_id)

    # Concurrency guard
    if not manager.try_acquire("__placeholder__"):
        from tradingagents.api.errors import AppError
        raise AppError(
            title="Service at capacity",
            status=503,
            detail="A job is already running. Please try again later.",
            error_type="https://tradingagents.dev/errors/capacity",
        )

    tickers = body.get_tickers()
    trade_date = body.get_trade_date()
    analysts = body.get_analysts()
    ticker = tickers[0]

    job_id = uuid.uuid4().hex[:12]
    store.create(
        job_id,
        ticker,
        trade_date,
        config_snapshot=_build_config_snapshot(),
        idempotency_key=idempotency_key,
        analysts=analysts,
    )

    # Replace placeholder acquire with real job_id
    manager.release("__placeholder__")
    manager.try_acquire(job_id)

    background_tasks.add_task(
        _run_and_release,
        job_id=job_id,
        manager=manager,
        store=store,
        ticker=ticker,
        trade_date=trade_date,
        config_snapshot=_build_config_snapshot(),
        db_path=config.db_path,
        analysts=analysts,
    )

    response.headers["Location"] = f"/api/v1/jobs/{job_id}"
    response.headers["Retry-After"] = "5"

    return JobSubmitResponse(
        job_id=job_id,
        ticker=ticker,
        trade_date=trade_date,
        message="Job submitted",
    )


def _build_config_snapshot():
    try:
        from tradingagents.config.models import TradingAgentsConfig
        return TradingAgentsConfig.from_env().to_legacy_dict()
    except Exception:
        return None


@router.get("")
async def list_jobs(
    response: Response,
    status: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    trade_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    store: JobStore = Depends(get_job_store),
):
    """List jobs with optional filters and pagination envelope."""
    jobs, total = store.list_jobs(
        status=status, ticker=ticker, trade_date=trade_date, limit=limit, offset=offset
    )
    items = [_record_to_response(j) for j in jobs]
    add_pagination_headers(response, offset, limit, total, "/api/v1/jobs")
    return paginate(
        items=[r.model_dump() for r in items],
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
        raise JobNotFoundError(job_id)
    return _record_to_response(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    manager: BackgroundTaskManager = Depends(get_task_manager),
):
    """Cancel a pending or running job."""
    job = store.get(job_id)
    if not job:
        raise JobNotFoundError(job_id)
    if job.status in ("completed", "failed", "cancelled"):
        raise JobStateConflictError(job_id, job.status, action="cancel")

    # Set cooperative cancellation flag for running jobs
    if job.status == "running":
        manager.request_cancel(job_id)

    store.cancel(job_id)
    job = store.get(job_id)
    return _record_to_response(job)


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
):
    """Delete a job record (for cleanup, not cancellation)."""
    job = store.get(job_id)
    if not job:
        raise JobNotFoundError(job_id)
    store.delete(job_id)
