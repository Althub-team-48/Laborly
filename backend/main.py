"""
main.py

Application entrypoint for Laborly API.
- Initializes logging
- Sets up FastAPI instance and middleware
- Registers API routers
"""

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.core.logging import init_logging
from app.core.config import settings
from app.auth.routes import router as auth_router
from app.client.routes import router as client_router

# -----------------------------
# App Initialization
# -----------------------------
app = FastAPI(title="Laborly API")

# Initialize structured logging
init_logging()

# -----------------------------
# Middleware
# -----------------------------
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# -----------------------------
# Routers
# -----------------------------
app.include_router(auth_router)
app.include_router(client_router)
