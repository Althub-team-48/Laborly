"""
worker/routes.py

Worker module endpoints for:
- Profile management
- KYC document submission
- Job history and detail view
"""

from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.worker.services import WorkerService
from app.worker import schemas
from app.core.dependencies import get_db, require_roles
from app.database.models import User, UserRole
from app.core.upload import save_upload_file

router = APIRouter(prefix="/worker", tags=["Worker"])


# ----------------------------
# Worker Profile Endpoints
# ----------------------------
@router.get("/profile", response_model=schemas.WorkerProfileRead)
def get_worker_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Retrieve the worker's profile.
    """
    return WorkerService(db).get_profile(current_user.id)


@router.patch("/profile", response_model=schemas.WorkerProfileRead)
def update_worker_profile(
    data: schemas.WorkerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Update the worker's profile.
    """
    return WorkerService(db).update_profile(current_user.id, data)


# ----------------------------
# KYC Submission Endpoints
# ----------------------------
@router.get("/kyc")
def get_worker_kyc(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Retrieve KYC status and submitted documents for the worker.
    """
    return WorkerService(db).get_kyc(current_user.id)


@router.post("/kyc")
def submit_worker_kyc(
    document_type: str = Form(...),
    document_file: UploadFile = File(...),
    selfie_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Submit KYC documents (ID and selfie) for verification.
    """
    document_path = save_upload_file(document_file, subfolder="kyc")
    selfie_path = save_upload_file(selfie_file, subfolder="kyc")
    return WorkerService(db).submit_kyc(
        user_id=current_user.id,
        document_type=document_type,
        document_path=document_path,
        selfie_path=selfie_path,
    )


# ----------------------------
# Worker Job Endpoints
# ----------------------------
@router.get("/jobs")
def list_worker_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    List all jobs assigned to the authenticated worker.
    """
    return WorkerService(db).get_jobs(current_user.id)


@router.get("/jobs/{job_id}")
def get_worker_job_detail(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.WORKER, UserRole.ADMIN)),
):
    """
    Retrieve detailed info for a specific job assigned to the worker.
    """
    return WorkerService(db).get_job_detail(current_user.id, job_id)
