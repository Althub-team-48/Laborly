"""
logging_middleware.py

Defines custom middleware to log all HTTP requests and responses.
Captures request method, path, headers, body, and logs the response status and body.
Handles both regular and streaming responses.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from utils.logger import logger
import json


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Capture and log request details
        body = await request.body()
        body_str = body.decode('utf-8').strip()
        if body_str:
            try:
                parsed_body = json.loads(body_str)
            except json.JSONDecodeError:
                parsed_body = "Invalid JSON"
        else:
            parsed_body = "Empty body"

        logger.info(
            f"Request: {request.method} {request.url.path} "
            #f"Headers: {dict(request.headers)}"
            f"Body: {parsed_body}"
        )

        # Process the request and capture the response
        response = await call_next(request)

        # Handle StreamingResponse to access its body
        body = b""
        if isinstance(response, StreamingResponse):
            async for chunk in response.body_iterator:
                body += chunk

            response_body = body.decode("utf-8") if body else "No body"

            # Reconstruct the StreamingResponse after reading it
            response = StreamingResponse(
                iter([body]),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        else:
            response_body = "Non-streaming response"

        # Log the response depending on status
        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            f"Response: {request.method} {request.url.path} - "
            f"Status {response.status_code} - Body: {response_body}"
        )

        return response
