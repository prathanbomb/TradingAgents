"""TradingAgents API server."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from tradingagents.api.auth import create_auth_dependency
from tradingagents.api.config import APIConfig
from tradingagents.api.deps import get_api_config
from tradingagents.api.routes import health, jobs, observability

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_api_config()

    # Sweep stale running jobs on startup
    from tradingagents.api.job_store import JobStore
    store = JobStore(db_path=config.db_path)
    swept = store.mark_stale_running(timeout_seconds=config.job_timeout)
    if swept:
        logger.warning(f"Marked {swept} stale running job(s) as failed")

    logger.info(f"TradingAgents API started (port={config.api_port}, redis={config.redis_url})")
    yield
    logger.info("TradingAgents API shutting down")


def create_app() -> FastAPI:
    config = get_api_config()
    auth = create_auth_dependency(config)

    app = FastAPI(
        title="TradingAgents API",
        version="0.1.0",
        description="Multi-Agent LLM Financial Trading Framework",
        lifespan=lifespan,
        dependencies=[auth] if config.auth_enabled else [],
    )

    app.include_router(jobs.router)
    app.include_router(health.router)
    app.include_router(observability.router)

    return app


app = create_app()


if __name__ == "__main__":
    config = get_api_config()
    uvicorn.run(
        "tradingagents.api.main:app",
        host="0.0.0.0",
        port=config.api_port,
        log_level="info",
    )
