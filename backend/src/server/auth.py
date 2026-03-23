from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from server.config import Settings


class AuthError(PermissionError):
    """Raised when the request is not authorized."""


def require_request_auth(request: Request, settings: Settings) -> None:
    if not settings.require_auth:
        return

    authorization = request.headers.get("authorization", "").strip()
    expected = settings.auth_token or ""

    if not expected:
        raise AuthError("Authentication is enabled but MCP_201_AUTH_TOKEN is not configured.")
    if authorization != f"Bearer {expected}":
        raise AuthError("Unauthorized request.")


class RequestAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/healthz"):
            return await call_next(request)

        try:
            require_request_auth(request, self.settings)
        except AuthError as exc:
            return JSONResponse({"error": str(exc)}, status_code=401)

        return await call_next(request)
