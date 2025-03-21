"""
main.py

Entry point for the Laborly API application.
- Initializes the FastAPI app with version and title
- Adds custom logging middleware
- Defines a custom 404 error handler
- Includes routers for users, jobs, and workers
"""

from fastapi import FastAPI, Request

from users.routes import router as users_router
from jobs.routes import router as jobs_router
from workers.routes import router as workers_router
from utils.middleware import LoggingMiddleware
from utils.logger import logger
from core.exceptions import APIError
# Initialize FastAPI app
app = FastAPI(
    title="Laborly API",
    version="1.0.0"
)

# Register middleware
app.add_middleware(LoggingMiddleware)

# Custom 404 error handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    """
    Logs and returns a standardized response for 404 errors.
    """
    logger.warning(f"404 Not Found: {request.method} {request.url.path}")
    return APIError(status_code=404, message="Not Found")

# Register application routers
app.include_router(users_router)
app.include_router(jobs_router)
app.include_router(workers_router)
