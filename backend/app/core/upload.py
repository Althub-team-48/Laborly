"""
core/upload.py

Handles file uploads securely by:
- Validating file MIME type using content sniffing
- Storing uploaded files in structured subfolders
- Enforcing upload directory structure and safety
"""

import os
import uuid
import filetype

from fastapi import UploadFile, HTTPException
from typing import Literal

# Upload storage path
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Supported file types (safe for KYC and similar purposes)
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf"
}


def save_upload_file(file: UploadFile, subfolder: Literal["kyc"] = "kyc") -> str:
    """
    Validates and saves an uploaded file into a secure subfolder.

    Args:
        file (UploadFile): Uploaded file from FastAPI request
        subfolder (str): Destination subfolder within uploads/ (e.g., "kyc")

    Returns:
        str: Full path to saved file

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

    # Sanitize filename and generate a unique path
    safe_filename = file.filename.replace(" ", "_").replace("/", "_")
    unique_name = f"{uuid.uuid4()}_{safe_filename}"
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)

    full_path = os.path.join(folder_path, unique_name)

    try:
        with open(full_path, "wb") as destination:
            destination.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return full_path
