"""
[jobs] routes.py

Defines the FastAPI routes for job-related operations:
- Job creation, listing, retrieval, update, and deletion
- Job application submission and status updates
- Access control based on user roles (Admin, Client, Worker)
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from admin.schemas import DisputeCreate, DisputeOut
from jobs.schemas import (
    JobCreate, JobUpdate, JobOut, JobList,
    JobApplicationCreate, JobApplicationUpdate,
    JobApplicationOut, JobApplicationList,
)
from jobs.service import JobService
from core.dependencies import get_db, get_current_user
from core.exceptions import APIError
from users.schemas import UserOut, UserRole
from utils.logger import logger

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/create", response_model=JobOut, status_code=status.HTTP_201_CREATED, responses={
    201: {"description": "Job successfully created"},
    403: {"description": "Only clients or admins can create jobs"},
    500: {"description": "Server error while creating job"}
})
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Create a new job. Clients and admins only."""
    if current_user.role not in [UserRole.CLIENT, UserRole.ADMIN]:
        raise APIError(status_code=403, message="Only clients or admins can create jobs")

    try:
        return JobService.create_job(db, job, current_user.id)
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.get("/list", response_model=JobList, responses={
    200: {"description": "List of jobs"},
    403: {"description": "Access denied"},
    500: {"description": "Failed to fetch jobs"}
})
def list_jobs(
    status: Optional[str] = None,
    title: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """List jobs with optional filters for status and title."""
    try:
        jobs = JobService.get_jobs_by_user(
            db,
            current_user.id,
            current_user.role,
            status=status,
            title=title
        )
        return {"jobs": jobs}
    except ValueError as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise APIError(status_code=500, message="Internal server error")


@router.get("/find/{job_id}", response_model=JobOut, responses={
    200: {"description": "Job details retrieved"},
    403: {"description": "Unauthorized access"},
    404: {"description": "Job not found"},
    500: {"description": "Server error"}
})
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Retrieve a job by ID (Admin, job creator, or assigned worker only)."""
    try:
        job = JobService.get_job_by_id(db, job_id)

        if current_user.role != UserRole.ADMIN:
            is_client = job.client and job.client.id == current_user.id
            is_worker = job.worker and job.worker.id == current_user.id

            if not is_client and not is_worker:
                raise ValueError("You don’t have permission to view this job")

        return job
    except ValueError as e:
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.put("/update/{job_id}", response_model=JobOut, responses={
    200: {"description": "Job updated"},
    403: {"description": "Unauthorized to update this job"},
    404: {"description": "Job not found"},
    500: {"description": "Update failed"}
})
def update_job(
    job_id: int,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Update a job. Only the creator or an admin may update."""
    try:
        return JobService.update_job(db, job_id, job_update, current_user.id, current_user.role)
    except ValueError as e:
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.delete("/delete/{job_id}", status_code=status.HTTP_204_NO_CONTENT, responses={
    204: {"description": "Job deleted"},
    403: {"description": "Unauthorized to delete this job"},
    500: {"description": "Server error during deletion"}
})
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Delete a job. Only the creator or an admin may delete."""
    try:
        JobService.delete_job(db, job_id, current_user.id, current_user.role)
    except ValueError as e:
        raise APIError(status_code=403, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=f"Failed to delete job: {str(e)}")


@router.post("/apply/{job_id}", response_model=JobApplicationOut, status_code=status.HTTP_201_CREATED, responses={
    201: {"description": "Application submitted"},
    400: {"description": "Job ID mismatch or already applied"},
    403: {"description": "Only workers can apply"},
    500: {"description": "Error submitting application"}
})
def apply_for_job(
    job_id: int,
    application: JobApplicationCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Apply for a job (workers only)."""
    if current_user.role != UserRole.WORKER:
        raise APIError(status_code=403, message="Only workers can apply for jobs")

    if application.job_id != job_id:
        raise APIError(status_code=400, message="Job ID mismatch")

    try:
        return JobService.apply_for_job(db, application, current_user.id)
    except ValueError as e:
        raise APIError(status_code=400, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.get("/applications/{job_id}", response_model=JobApplicationList, responses={
    200: {"description": "List of applications"},
    403: {"description": "Access denied"},
    404: {"description": "Job not found"},
    500: {"description": "Error retrieving applications"}
})
def list_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """List all applications for a job. Only job creator or admin may view."""
    job = JobService.get_job_by_id(db, job_id)

    if current_user.role != UserRole.ADMIN and job.client.id != current_user.id:
        raise APIError(status_code=403, message="Only the job creator or an admin can view applications")

    return {"applications": JobService.get_applications_by_job(db, job_id)}


@router.put("/{job_id}/applications/{application_id}", response_model=JobApplicationOut, responses={
    200: {"description": "Application status updated"},
    400: {"description": "Invalid application/job relationship"},
    403: {"description": "Access denied"},
    404: {"description": "Application not found"},
    500: {"description": "Update failed"}
})
def update_application(
    job_id: int,
    application_id: int,
    application_update: JobApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Update application status (accept/reject). Admin or job creator only."""
    try:
        application = JobService.get_application_by_id(db, application_id)

        if application.job_id != job_id:
            raise ValueError("Application does not belong to this job")

        return JobService.update_application(db, application_id, application_update, current_user.id, current_user.role)
    except ValueError as e:
        raise APIError(status_code=400, message=str(e))
    except Exception as e:
        raise APIError(status_code=500, message=str(e))


@router.patch("/{job_id}/complete", response_model=JobOut)
def mark_job_complete(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Mark job as completed by client or worker."""
    try:
        return JobService.mark_job_complete(db, job_id, current_user.id)
    except ValueError as e:
        raise APIError(status_code=400, message=str(e))

@router.post("/{job_id}/dispute", response_model=DisputeOut, status_code=status.HTTP_201_CREATED)
def raise_dispute(
    job_id: int,
    dispute: DisputeCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """Raise a dispute for a job."""
    try:
        return JobService.raise_dispute(db, job_id, dispute, current_user.id)
    except ValueError as e:
        raise APIError(status_code=400, message=str(e))