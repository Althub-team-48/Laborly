"""
backend/app/core/upload.py

File Upload Handling

Provides utilities to:
- Securely upload files to AWS S3 with MIME type validation
- Enforce size limits and structured subfolder storage
- Generate pre-signed URLs for temporary file access
- Extract S3 object keys from URLs
"""

import logging
import os
import uuid
from typing import Literal

import boto3
import filetype
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from fastapi import HTTPException, UploadFile, status
from urllib.parse import urlparse

from typing import cast

from myapp.core.config import settings

# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# Constants
# ---------------------------------------------------
ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# ---------------------------------------------------
# Initialize Boto3 S3 Client
# ---------------------------------------------------
try:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    logger.info("[UPLOAD] Boto3 S3 client initialized successfully.")
except (NoCredentialsError, PartialCredentialsError):
    logger.error("[UPLOAD] AWS credentials missing or incomplete.")
    s3_client = None
except Exception as e:
    logger.error(f"[UPLOAD] Unexpected error initializing Boto3 S3 client: {e}")
    s3_client = None

# ---------------------------------------------------
# Upload File to S3
# ---------------------------------------------------


async def upload_file_to_s3(
    file: UploadFile,
    subfolder: Literal["kyc", "profile_pictures"] = "kyc",
) -> str:
    """
    Validates and uploads a file to AWS S3.

    Args:
        file (UploadFile): File to upload.
        subfolder (Literal): Target subfolder within the bucket.

    Returns:
        str: Public URL of the uploaded file.

    Raises:
        HTTPException: If validation or upload fails.
    """
    if not s3_client:
        logger.error("[UPLOAD] S3 client unavailable during upload.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service unavailable.",
        )

    # Validate size
    size = 0
    chunk_size = 8192
    try:
        while chunk := await file.read(chunk_size):
            size += len(chunk)
        await file.seek(0)
    except Exception as e:
        logger.error(f"[UPLOAD] Error reading file '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not process file: {e}",
        )

    if size > MAX_FILE_SIZE:
        logger.warning(f"[UPLOAD] File '{file.filename}' exceeds size limit.")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit.",
        )
    if size == 0:
        logger.warning(f"[UPLOAD] Empty file received: '{file.filename}'.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Validate MIME type
    try:
        header_bytes = await file.read(261)
        await file.seek(0)
    except Exception as e:
        logger.error(f"[UPLOAD] Error reading header for '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read file header: {e}",
        )

    kind = filetype.guess(header_bytes)
    detected_mime = kind.mime if kind else "unknown"

    if not kind or detected_mime not in ALLOWED_MIME_TYPES:
        logger.warning(f"[UPLOAD] Invalid file type '{detected_mime}' for '{file.filename}'.")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{detected_mime}'. Allowed: {', '.join(mt.split('/')[1].upper() for mt in ALLOWED_MIME_TYPES)}.",
        )

    # Generate safe S3 key
    safe_filename = os.path.basename(file.filename or "untitled").replace(" ", "_")
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in ('_', '-', '.'))
    if not safe_filename:
        safe_filename = "uploaded_file"

    unique_name = f"{uuid.uuid4()}_{safe_filename}"
    s3_key = f"{subfolder}/{unique_name}".lstrip('/')

    logger.info(f"[UPLOAD] Uploading '{file.filename}' as '{s3_key}'.")

    # Upload to S3
    try:
        s3_client.upload_fileobj(
            Fileobj=file.file,
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            ExtraArgs={'ContentType': detected_mime},
        )
        logger.info(f"[UPLOAD] Successfully uploaded to S3. Key: {s3_key}")
    except ClientError as e:
        _handle_s3_client_error(e, s3_key)
    except Exception as e:
        logger.error(f"[UPLOAD] Unexpected upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file.",
        )
    finally:
        await file.close()

    # Return the public S3 URL
    file_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
    logger.debug(f"[UPLOAD] Generated file URL: {file_url}")
    return file_url


# ---------------------------------------------------
# Generate Pre-signed URL
# ---------------------------------------------------


def generate_presigned_url(
    s3_key: str,
    expiration: int = 3600,
) -> str | None:
    """
    Generate a temporary pre-signed S3 URL.

    Args:
        s3_key (str): Object key.
        expiration (int): Expiration time in seconds.

    Returns:
        str | None: Pre-signed URL or None if failed.
    """
    if not s3_client:
        logger.error("[UPLOAD] Cannot generate pre-signed URL: S3 client unavailable.")
        return None

    if not s3_key:
        logger.warning("[UPLOAD] Cannot generate pre-signed URL: Missing key.")
        return None

    logger.info(f"[UPLOAD] Generating pre-signed URL for '{s3_key}'.")
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.AWS_S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration,
        )
        return cast(str, response)
    except ClientError as e:
        logger.error(f"[UPLOAD] Pre-signed URL generation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"[UPLOAD] Unexpected error generating pre-signed URL: {e}", exc_info=True)
        return None


# ---------------------------------------------------
# Extract S3 Key from URL
# ---------------------------------------------------


def get_s3_key_from_url(s3_url: str) -> str | None:
    """
    Extracts the S3 object key from a full HTTPS URL.

    Args:
        s3_url (str): S3 object URL.

    Returns:
        str | None: S3 key or None if parsing fails.
    """
    if not s3_url:
        return None

    try:
        parsed_url = urlparse(s3_url)
        if not parsed_url.netloc.endswith("amazonaws.com"):
            logger.warning(f"[UPLOAD] Non-standard S3 URL: {s3_url}")
        key = parsed_url.path.lstrip('/')
        return key if key else None
    except Exception as e:
        logger.error(f"[UPLOAD] Failed parsing S3 key from URL: {e}")
        return None


# ---------------------------------------------------
# Internal Error Handlers
# ---------------------------------------------------


def _handle_s3_client_error(error: ClientError, s3_key: str) -> None:
    """
    Handle known S3 client errors gracefully.

    Args:
        error (ClientError): Boto3 client error.
        s3_key (str): Affected object key.

    Raises:
        HTTPException: Appropriately based on the error.
    """
    error_code = error.response.get("Error", {}).get("Code")
    logger.error(f"[UPLOAD] S3 ClientError on '{s3_key}': {error_code} - {error}")
    if error_code == "AccessDenied":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="S3 access denied. Check credentials and permissions.",
        )
    elif error_code == "NoSuchBucket":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"S3 bucket '{settings.AWS_S3_BUCKET}' not found.",
        )
    elif error_code in {"InvalidAccessKeyId", "SignatureDoesNotMatch"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid AWS credentials. Please check configuration.",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 client error occurred: {error_code}",
        )
