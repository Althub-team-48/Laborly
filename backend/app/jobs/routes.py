"""
[jobs] routes.py

Defines the FastAPI routes for job-related operations:
- Job creation, listing, retrieval, update, and deletion
- Job application submission and status updates
- Access control based on user roles (Admin, Client, Worker)
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from jobs.schemas import (
    JobCreate, JobUpdate, JobOut, JobList,
    JobApplicationCreate, JobApplicationUpdate,
    JobApplicationOut, JobApplicationList,
)
from jobs.service import JobService
from core.dependencies import get_db, get_current_user
from users.schemas import UserOut, UserRole

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/create", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Create a new job.
    Only users with CLIENT or ADMIN roles are allowed.
    """
    if current_user.role not in [UserRole.CLIENT, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only clients or admins can create jobs")

    try:
        return JobService.create_job(db, job, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=JobList)
def list_jobs(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    List jobs based on user role.
    Clients see their jobs, workers see jobs they applied for, admins see all jobs.
    """
    return {"jobs": JobService.get_jobs_by_user(db, current_user.id, current_user.role)}


@router.get("/find/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Retrieve details of a job by ID.
    Accessible to admin, client who created it, or assigned worker.
    """
    try:
        job = JobService.get_job_by_id(db, job_id)

        if current_user.role != UserRole.ADMIN:
            is_client = job.client and job.client.id == current_user.id
            is_worker = job.worker and job.worker.id == current_user.id

            if not is_client and not is_worker:
                raise ValueError("You don’t have permission to view this job")

        return job
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Update an existing job.
    Only the job creator or an admin can update it.
    """
    try:
        return JobService.update_job(db, job_id, job_update, current_user.id, current_user.role)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Delete a job.
    Only the job creator or an admin can delete it.
    """
    try:
        JobService.delete_job(db, job_id, current_user.id, current_user.role)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply/{job_id}", response_model=JobApplicationOut, status_code=status.HTTP_201_CREATED)
def apply_for_job(
    job_id: int,
    application: JobApplicationCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Allows a worker to apply for a job.
    Verifies that the user is a worker and job_id matches.
    """
    if current_user.role != UserRole.WORKER:
        raise HTTPException(status_code=403, detail="Only workers can apply for jobs")

    if application.job_id != job_id:
        raise HTTPException(status_code=400, detail="Job ID mismatch")

    try:
        return JobService.apply_for_job(db, application, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications/{job_id}", response_model=JobApplicationList)
def list_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Returns applications for a job.
    Accessible only to the job creator or an admin.
    """
    job = JobService.get_job_by_id(db, job_id)

    if current_user.role != UserRole.ADMIN and job.client.id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the job creator or an admin can view applications")

    return {"applications": JobService.get_applications_by_job(db, job_id)}


@router.put("/{job_id}/applications/{application_id}", response_model=JobApplicationOut)
def update_application(
    job_id: int,
    application_id: int,
    application_update: JobApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Update the status of a job application (accept/reject).
    Restricted to the job creator or an admin.
    """
    try:
        application = JobService.get_application_by_id(db, application_id)

        if application.job_id != job_id:
            raise ValueError("Application does not belong to this job")

        return JobService.update_application(db, application_id, application_update, current_user.id, current_user.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
