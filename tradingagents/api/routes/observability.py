"""Observability query routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response

from tradingagents.api.deps import get_api_config
from tradingagents.api.models import ObservabilityQueryParams
from tradingagents.api.pagination import add_pagination_headers, paginate

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


def _get_store(config=Depends(get_api_config)):
    from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore
    return SQLiteDecisionStore(str(config.db_path).replace("jobs.db", "observability.db"))


@router.get("/decisions")
async def get_decisions(
    response: Response,
    ticker: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    config=Depends(get_api_config),
):
    """Query decision records from observability store with pagination."""
    store = _get_store(config)
    records = store.get_decision_records(
        ticker=ticker, start_date=start_date, end_date=end_date, limit=limit
    )
    total = len(records)
    # Apply offset slicing
    page = records[offset : offset + limit]
    add_pagination_headers(response, offset, limit, total, "/api/v1/observability/decisions")
    return paginate(
        items=page,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/events")
async def get_events(
    run_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    config=Depends(get_api_config),
):
    """Query agent events from observability store."""
    store = _get_store(config)
    return store.get_agent_events(run_id=run_id, agent_name=agent_name)


@router.get("/stats")
async def get_stats(config=Depends(get_api_config)):
    """Get observability storage statistics."""
    store = _get_store(config)
    return store.get_stats()
