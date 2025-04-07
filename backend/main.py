"""
main.py

Application entrypoint for the Laborly API.
- Initializes structured logging
- Sets up FastAPI application and middlewares
- Registers all API routers
- Integrates rate limiting via SlowAPI
"""

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.logging import init_logging
from app.core.config import settings

# Routers
from app.auth.routes import router as auth_router
from app.client.routes import router as client_router
from app.worker.routes import router as worker_router
from app.admin.routes import router as admin_router
from app.service.routes import router as service_router
from app.review.routes import router as review_router
from app.job.routes import router as job_router
from app.core.limiter import limiter


# -----------------------------
# FastAPI App Initialization
# -----------------------------
app = FastAPI(title="Laborly API")

# -----------------------------
# Middleware Configuration
# -----------------------------
init_logging()
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

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