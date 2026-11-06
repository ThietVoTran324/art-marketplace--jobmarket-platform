import json
import secrets
import time

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk import capture_exception, capture_message

from app.config import settings
from app.api.rest.security import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.logger import logger, requests_logger

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_EXEMPT_PATHS = {
    "/users/login",
    "/users/register",
    "/marketplace/webhooks/sepay",
}


def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _path_for_csrf(path: str) -> str:
    """Normalize path when clients hit /api/... directly (Swagger root_path)."""
    if path.startswith("/api/"):
        return path[4:]  # "/api/users/login" -> "/users/login"
    if path == "/api":
        return "/"
    return path


async def log_requests_and_server_http_exception_handler(request: Request, call_next):

    start_time = time.time()

    try:
        csrf_path = _path_for_csrf(request.url.path)
        if (
            request.method in STATE_CHANGING_METHODS
            and request.cookies.get("access_token")
            and csrf_path not in CSRF_EXEMPT_PATHS
        ):
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            if (
                not cookie_token
                or not header_token
                or not secrets.compare_digest(cookie_token, header_token)
            ):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed"},
                )

        response: Response = await call_next(request)
        elapsed_time = time.time() - start_time

        if settings.LOGGING_REQUESTS:
            log_data = {
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host,
                "status_code": response.status_code,
                "elapsed_time": round(elapsed_time, 4),
            }

            requests_logger.info(json.dumps(log_data, ensure_ascii=False))

            capture_message(json.dumps(log_data, ensure_ascii=False))

        return response
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(
            f"Error processing request {request.method} {request.url} {request.client.host} : {e}",
            exc_info=True,
        )

        capture_exception(e)

        if settings.LOGGING_REQUESTS:
            log_data = {
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host,
                "status_code": "ERROR",
                "elapsed_time": round(elapsed_time, 4),
                "error": str(e),
            }

            requests_logger.info(json.dumps(log_data, ensure_ascii=False))

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )


def register_middleware(app: FastAPI):
        
    app.middleware("http")(log_requests_and_server_http_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_csv_values(settings.TRUSTED_ORIGIN),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=_csv_values(settings.TRUSTED_HOST),
    )
