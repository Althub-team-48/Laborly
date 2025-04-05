"""
core/upload.py

Handles secure file uploads:
- Generates unique filenames
- Stores in specified upload subdirectory
- Returns relative path for reference
"""

import os
import uuid
from fastapi import UploadFile
from typing import Literal

# Base directory where all uploads are stored
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload_file(file: UploadFile, subfolder: Literal["kyc"] = "kyc") -> str:
    """
    Save an uploaded file to a subfolder inside the uploads directory.

    Args:
        file (UploadFile): The uploaded file object from the request.
        subfolder (Literal["kyc"]): Subfolder under uploads/ where the file will be stored.

    Returns:
        str: Relative path to the saved file.
    """
    unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)

    full_path = os.path.join(folder_path, unique_name)

    with open(full_path, "wb") as destination:
        destination.write(file.file.read())

    return full_path
