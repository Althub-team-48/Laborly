from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import JSONResponse
from database.init_db import init_db
from utils.logger import log_request_response
from core.dependencies import get_db_session
from sqlalchemy.orm import Session

app = FastAPI()

# Middleware to log all requests and responses
@app.middleware("http")
async def log_requests(request: Request, call_next):
    db = next(get_db_session())  # Get the database session
    response = await call_next(request)
    await log_request_response(request, response, db)
    return response

# Initialize the database on startup
@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Laborly Backend is running!"}