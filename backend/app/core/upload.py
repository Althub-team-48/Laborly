"""
core/upload.py

Handles file uploads securely by:
- Validating file MIME type using content sniffing
- Storing uploaded files in structured subfolders
- Enforcing upload directory structure and safety
"""

# backend/app/core/upload.py
import logging
import uuid
import os
from typing import Literal

import boto3
import filetype
from fastapi import UploadFile, HTTPException, status
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)  # Setup logger

# Supported file types (safe for KYC and similar purposes)
ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png", "application/pdf"}

MAX_FILE_SIZE = 10 * 1024 * 1024

try:
    # Initialize Boto3 S3 client with credentials from environment settings
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    logger.info("Boto3 S3 client initialized successfully.")
except (NoCredentialsError, PartialCredentialsError):
    logger.error("AWS credentials not found or incomplete in environment settings.")
    s3_client = None
except Exception as e:
    logger.error(f"Failed to initialize Boto3 S3 client: {e}")
    s3_client = None


async def upload_file_to_s3(
    file: UploadFile, subfolder: Literal["kyc", "profile_pictures"] = "kyc"
) -> str:
    """
    Validates MIME type, size and uploads file to S3 using streaming.

    Args:
        file (UploadFile): Uploaded file from FastAPI request.
        subfolder (str): Destination subfolder in the S3 bucket (e.g., "kyc", "profile_pictures").

    Returns:
        str: Public HTTPS URL of the uploaded file on S3.
             (Note: Returning just the S3 key is often safer practice).

    Raises:
        HTTPException: If S3 client is not configured, file type/size is invalid, or upload fails.
    """
    if not s3_client:
        logger.error("S3 client is not available. Check AWS configuration and credentials.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured or unavailable. Cannot upload file.",
        )

    size = 0
    chunk_size = 8192  # Process in 8KB chunks
    try:
        while chunk := await file.read(chunk_size):
            size += len(chunk)
        await file.seek(0)
    except Exception as e:
        logger.error(f"Error reading file '{file.filename}' to determine size: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read file: {e}",
        )

    if size > MAX_FILE_SIZE:
        logger.warning(
            f"Upload rejected: File '{file.filename}' size ({size} bytes) exceeds limit ({MAX_FILE_SIZE} bytes)."
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the limit of {MAX_FILE_SIZE // 1024 // 1024} MB.",
        )
    if size == 0:
        logger.warning(f"Upload rejected: Received an empty file '{file.filename}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Received an empty file.",
        )

    # --- MIME Type Validation ---
    try:
        header_bytes = await file.read(261)
        # IMPORTANT: Reset file pointer again for the actual upload
        await file.seek(0)
    except Exception as e:
        logger.error(f"Error reading file header for type checking '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read file header for type checking: {e}",
        )

    kind = filetype.guess(header_bytes)
    detected_mime = kind.mime if kind else "unknown"

    # Check against allowed types *and* the content type provided by the client
    # client_content_type = file.content_type
    # if client_content_type != detected_mime:
    #     logger.warning(f"Upload rejected: Mismatch between client content type ({client_content_type}) and detected type ({detected_mime}) for file '{file.filename}'.")
    #     raise HTTPException(
    #         status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    #         detail=f"File type mismatch detected. Please upload a valid file.",
    #     )

    if not kind or detected_mime not in ALLOWED_MIME_TYPES:
        logger.warning(
            f"Upload rejected: Invalid file type '{detected_mime}' for file '{file.filename}'. Allowed: {ALLOWED_MIME_TYPES}"
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: '{detected_mime}'. Allowed types: {', '.join(mt.split('/')[1].upper() for mt in ALLOWED_MIME_TYPES)}.",
        )

    # --- Generate S3 Key ---
    safe_filename = os.path.basename(file.filename or "untitled").replace(" ", "_")
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in ('_', '-', '.'))
    if not safe_filename:
        safe_filename = "uploaded_file"
    unique_name = f"{uuid.uuid4()}_{safe_filename}"
    s3_key = f"{subfolder}/{unique_name}".lstrip('/')

    logger.info(
        f"Attempting to upload '{file.filename}' (size: {size} bytes, type: {detected_mime}) as S3 key '{s3_key}' to bucket '{settings.AWS_S3_BUCKET}'"
    )

    # --- Perform Upload using streaming ---
    try:
        s3_client.upload_fileobj(
            Fileobj=file.file,
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            ExtraArgs={'ContentType': detected_mime},
        )
        logger.info(f"Successfully uploaded file to S3. Key: {s3_key}")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        logger.error(f"S3 ClientError uploading '{s3_key}': {error_code} - {e}")
        if error_code == "AccessDenied":
            detail = "S3 upload failed: Access denied. Please check server credentials and bucket permissions."
            status_code = status.HTTP_403_FORBIDDEN
        elif error_code == "NoSuchBucket":
            detail = f"S3 upload failed: Bucket '{settings.AWS_S3_BUCKET}' not found. Check configuration."
            status_code = status.HTTP_404_NOT_FOUND
        elif error_code == "InvalidAccessKeyId" or error_code == "SignatureDoesNotMatch":
            detail = "S3 upload failed: Invalid AWS credentials. Please check server configuration."
            status_code = status.HTTP_401_UNAUTHORIZED
        else:
            detail = f"S3 upload failed due to a client error: {error_code}"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload for '{s3_key}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file due to an unexpected server error.",
        )
    finally:
        await file.close()

    # --- Return URL ---
    file_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
    logger.debug(f"Generated file URL: {file_url}")
    return file_url


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str | None:
    """
    Generates a pre-signed URL for temporary, secure access to an S3 object.

    Args:
        s3_key (str): The object key (path within the bucket, e.g., 'kyc/uuid_file.png').
        expiration (int): Time in seconds for which the URL is valid (default: 1 hour).

    Returns:
        str | None: The pre-signed URL, or None if generation failed or S3 client is unavailable.
    """
    if not s3_client:
        logger.error("Cannot generate pre-signed URL: S3 client is not available.")
        return None
    if not s3_key:
        logger.warning("Cannot generate pre-signed URL: S3 key is empty.")
        return None

    logger.info(f"Generating pre-signed URL for key: {s3_key}, expiration: {expiration}s")
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration,
        )
        logger.info(f"Successfully generated pre-signed URL for key: {s3_key}")
        return response  # type: ignore[no-any-return]
    except ClientError as e:
        logger.error(f"Failed to generate pre-signed URL for key '{s3_key}': {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error generating pre-signed URL for key '{s3_key}': {e}", exc_info=True
        )
        return None


def get_s3_key_from_url(s3_url: str) -> str | None:
    """Extracts the object key from a standard S3 HTTPS URL."""
    if not s3_url:
        return None
    try:
        parsed_url = urlparse(s3_url)
        if not parsed_url.netloc.endswith('amazonaws.com'):
            logger.warning(f"URL '{s3_url}' does not look like a standard S3 URL.")
        key = parsed_url.path.lstrip('/')
        return key if key else None
    except Exception as e:
        logger.error(f"Failed to parse S3 key from URL '{s3_url}': {e}")
        return None
