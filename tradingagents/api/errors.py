"""RFC 7807 Problem Details error handling."""

from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base error with RFC 7807 fields."""

    def __init__(
        self,
        title: str,
        status: int = 500,
        detail: Optional[str] = None,
        error_type: str = "about:blank",
        **extra: Any,
    ):
        self.title = title
        self.status = status
        self.detail = detail or title
        self.error_type = error_type
        self.extra = extra
        super().__init__(detail)


class JobNotFoundError(AppError):
    def __init__(self, job_id: str):
        super().__init__(
            title="Job not found",
            status=404,
            detail=f"Job '{job_id}' does not exist",
            error_type="https://tradingagents.dev/errors/job-not-found",
            job_id=job_id,
        )


class JobStateConflictError(AppError):
    def __init__(self, job_id: str, current_status: str, action: str = "cancel"):
        super().__init__(
            title="Job state conflict",
            status=409,
            detail=f"Cannot {action} job '{job_id}' in '{current_status}' state",
            error_type="https://tradingagents.dev/errors/job-state-conflict",
            job_id=job_id,
            current_status=current_status,
        )


class ValidationError(AppError):
    def __init__(self, detail: str):
        super().__init__(
            title="Validation error",
            status=400,
            detail=detail,
            error_type="https://tradingagents.dev/errors/validation",
        )


class IdempotencyConflictError(AppError):
    def __init__(self, job_id: str):
        super().__init__(
            title="Idempotent request already processed",
            status=200,
            detail=f"Request already processed as job '{job_id}'",
            error_type="https://tradingagents.dev/errors/idempotency-conflict",
            existing_job_id=job_id,
        )


def _build_problem_body(err: AppError, trace_id: str) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "type": err.error_type,
        "title": err.title,
        "status": err.status,
        "detail": err.detail,
        "trace_id": trace_id,
    }
    body.update(err.extra)
    return body


def register_error_handlers(app):
    """Register global RFC 7807 error handlers on a FastAPI app."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        trace_id = getattr(request.state, "trace_id", "unknown")
        return JSONResponse(
            status_code=exc.status,
            content=_build_problem_body(exc, trace_id),
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", "unknown")
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal server error",
                "status": 500,
                "detail": str(exc),
                "trace_id": trace_id,
            },
            media_type="application/problem+json",
        )
