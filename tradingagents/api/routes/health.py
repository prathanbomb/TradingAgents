"""Health check route."""

from fastapi import APIRouter, Depends

from tradingagents.api.deps import get_api_config, get_job_store
from tradingagents.api.models import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(config=Depends(get_api_config)):
    """Check API, Redis, and worker health."""
    import redis as redis_lib

    redis_status = "ok"
    worker_count = 0

    try:
        conn = redis_lib.from_url(config.redis_url)
        conn.ping()
        from rq import Queue
        q = Queue(name=config.queue_name, connection=conn)
        worker_count = len(q.workers)
    except Exception as e:
        redis_status = f"error: {e}"

    return HealthResponse(
        status="ok",
        redis=redis_status,
        workers=worker_count,
        jobs_db=config.db_path,
    )
