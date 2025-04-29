"""
main.py

Application entrypoint for the Laborly API.
- Initializes structured logging
- Sets up FastAPI application and middlewares
- Registers all API routers
- Integrates rate limiting via SlowAPI
- Adds common security headers
- Configures CORS
"""

from typing import Any
from collections.abc import Callable, Awaitable
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from myapp.core.logging import init_logging
from myapp.core.config import settings

from myapp.auth.routes import router as auth_router
from myapp.client.routes import router as client_router
from myapp.worker.routes import router as worker_router
from myapp.admin.routes import router as admin_router
from myapp.service.routes import router as service_router
from myapp.review.routes import router as review_router
from myapp.job.routes import router as job_router
from myapp.messaging.routes import router as messaging_router
from myapp.core.limiter import limiter


# -----------------------------
# FastAPI App Initialization
# -----------------------------
app = FastAPI(title="Laborly API")

# -----------------------------
# Middleware Configuration
# -----------------------------
init_logging()
app.state.limiter = limiter


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


app.add_exception_handler(429, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


# -----------------------------
# Security Headers Middleware
# -----------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to responses.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response: Response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response


app.add_middleware(SecurityHeadersMiddleware)

# -----------------------------
# CORSMiddleware Configuration
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# API Router Registration
# -----------------------------
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(job_router)
app.include_router(review_router)
app.include_router(service_router)
app.include_router(worker_router)
app.include_router(messaging_router)


# -----------------------------
# Root Endpoint
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home() -> Any:
    return """
    <html>
        <head>
            <title>Welcome to Laborly</title>
        </head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
            <h1>👋 Welcome to <span style="color: #2c3e50;">Laborly</span></h1>
            <p>Your trusted API backend for jobs, clients, and workforce management.</p>
        </body>
    </html>
    """
