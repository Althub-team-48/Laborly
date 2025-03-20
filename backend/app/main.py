from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import JSONResponse
from app.database.init_db import init_db
from app.utils.logger import log_request_response, logger
from app.core.dependencies import get_db_session
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

# Define lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up Laborly Backend...")
    init_db()  # Initialize the database
    yield
    # Shutdown logic
    logger.info("Shutting down Laborly Backend...")

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Middleware to log all requests and responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    db = next(get_db_session())  # Get the database session
    response = await call_next(request)
    await log_request_response(request, response, db)
    return response

@app.get("/")
def read_root():
    return {"message": "Laborly Backend is running!"}

# Global exception handler (optional, for better error handling)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"}
    )