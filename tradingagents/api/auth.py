"""API key authentication middleware."""

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tradingagents.api.config import APIConfig

_security = HTTPBearer(auto_error=False)


def create_auth_dependency(config: APIConfig):
    """Create an auth dependency that enforces API key validation when configured."""

    async def authenticate(request: Request, credentials: HTTPAuthorizationCredentials = None):
        if not config.auth_enabled:
            return

        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing authorization header")

        if credentials.credentials not in config.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")

    return authenticate
