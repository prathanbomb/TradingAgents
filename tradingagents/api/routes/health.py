"""Health check route."""

from fastapi import APIRouter, Depends

from tradingagents.api.deps import get_api_config, get_job_store, get_task_manager
from tradingagents.api.models import HealthResponse
from tradingagents.api.task_manager import BackgroundTaskManager

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    config=Depends(get_api_config),
    store=Depends(get_job_store),
    manager: BackgroundTaskManager = Depends(get_task_manager),
):
    """Check API health and DB connectivity."""
    db_status = "ok"
    try:
        store.list_jobs(limit=1)
    except Exception as e:
        db_status = f"error: {e}"

    task_slot = "running" if manager.running_job_id else "idle"
    overall = "ok" if db_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        task_slot=task_slot,
        jobs_db=db_status,
    )
