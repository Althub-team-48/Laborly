"""
core/upload.py

Handles file uploads securely by:
- Validating file MIME type using content sniffing
- Storing uploaded files in structured subfolders
- Enforcing upload directory structure and safety
"""

import uuid
import filetype
import boto3

from fastapi import UploadFile, HTTPException
from typing import Literal

from app.core.config import settings

# Supported file types (safe for KYC and similar purposes)
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf"
}

# Init Boto3 S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

def upload_file_to_s3(file: UploadFile, subfolder: Literal["kyc"] = "kyc") -> str:
    """
    Validates MIME type and uploads file to S3 in a structured path.

    Args:
        file (UploadFile): Uploaded file from FastAPI request
        subfolder (str): Destination subfolder in the S3 bucket (e.g., "kyc")

    Returns:
        str: Public URL to uploaded file on S3

    Raises:
        HTTPException: If file type is invalid or upload fails
    """
    content = file.file.read()

    # Use content-sniffing to validate MIME type
    kind = filetype.guess(content)
    if not kind or kind.mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported or unsafe file type. Allowed: JPG, PNG, PDF"
        )

    # Sanitize and generate unique filename
    safe_filename = file.filename.replace(" ", "_").replace("/", "_")
    unique_name = f"{uuid.uuid4()}_{safe_filename}"
    s3_key = f"{subfolder}/{unique_name}"

    try:
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=kind.mime
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {str(e)}")

    # Return full S3 URL
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
