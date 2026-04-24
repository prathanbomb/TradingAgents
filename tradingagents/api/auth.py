"""API key authentication middleware."""

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from tradingagents.api.config import APIConfig


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates API key on every request when auth is enabled."""

    def __init__(self, app, api_keys: list[str]):
        super().__init__(app)
        self.api_keys = set(api_keys)

    async def dispatch(self, request: Request, call_next):
        if not self.api_keys:
            return await call_next(request)

        # Skip docs/openapi
        if request.url.path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
        else:
            token = auth

        if token not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

        return await call_next(request)


def add_auth_middleware(app, config: APIConfig):
    """Add auth middleware if API keys are configured."""
    if config.auth_enabled:
        app.add_middleware(AuthMiddleware, api_keys=config.api_keys)
