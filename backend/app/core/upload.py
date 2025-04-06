# core/upload.py

import os
import uuid
import filetype
from fastapi import UploadFile, HTTPException
from typing import Literal

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf"
}


def save_upload_file(file: UploadFile, subfolder: Literal["kyc"] = "kyc") -> str:
    """
    Save a securely validated uploaded file to a subfolder inside the uploads directory.
    """
    content = file.file.read()

    # Detect actual file type
    kind = filetype.guess(content)
    if not kind or kind.mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported or unsafe file type. Allowed: JPG, PNG, PDF"
        )

    # Generate unique filename and save
    unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)

    full_path = os.path.join(folder_path, unique_name)
    with open(full_path, "wb") as destination:
        destination.write(content)

    return full_path
