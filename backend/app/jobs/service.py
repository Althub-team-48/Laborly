"""
[jobs] service.py

Service layer for job-related business logic:
- Create, update, delete, retrieve jobs
- Apply to jobs and manage applications
- Access control for clients, workers, and admins
"""

from typing import List

from sqlalchemy.orm import Session

from database.models import (
    Job,
    User,
    JobApplication,
    JobStatus,
    ApplicationStatus,
    UserRole,
)
from jobs.schemas import (
    JobCreate,
    JobUpdate,
    JobOut,
    JobApplicationCreate,
    JobApplicationUpdate,
    JobApplicationOut,
)
from utils.logger import logger


class JobService:

    @staticmethod
    def create_job(db: Session, job: JobCreate, client_id: int) -> JobOut:
        """
        Creates a new job assigned to a client.
        """
        try:
            db_job = Job(
                title=job.title,
                description=job.description,
                client_id=client_id,
                status=JobStatus.PENDING
            )
            db.add(db_job)
            db.commit()
            db.refresh(db_job)
            logger.info(f"Job created: {db_job.id} by client {client_id}")
            return JobOut.model_validate(db_job)
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_job_by_id(db: Session, job_id: int) -> JobOut:
        """
        Retrieves a specific job by its ID.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")
        return JobOut.model_validate(job)

    @staticmethod
    def get_all_jobs(db: Session) -> List[JobOut]:
        """
        Returns all jobs in the system.
        """
        jobs = db.query(Job).all()
        return [JobOut.model_validate(job) for job in jobs]

    @staticmethod
    def get_jobs_by_user(db: Session, user_id: int, role: UserRole) -> List[JobOut]:
        """
        Returns jobs relevant to the user's role.
        - Clients see their own jobs
        - Workers see jobs assigned to them
        - Admins see all jobs
        """
        if role == UserRole.CLIENT:
            jobs = db.query(Job).filter(Job.client_id == user_id).all()
        elif role == UserRole.WORKER:
            jobs = db.query(Job).filter(Job.worker_id == user_id).all()
        else:  # Admin
            jobs = db.query(Job).all()

        return [JobOut.model_validate(job) for job in jobs]

    @staticmethod
    def update_job(db: Session, job_id: int, job_update: JobUpdate, user_id: int, role: UserRole) -> JobOut:
        """
        Updates a job.
        Only the job creator or an admin can perform the update.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")
        if role != UserRole.ADMIN and job.client_id != user_id:
            raise ValueError("Only the job creator or an admin can update this job")

        update_data = job_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(job, key, value)

        db.commit()
        db.refresh(job)
        logger.info(f"Job updated: {job_id} by user {user_id}")
        return JobOut.model_validate(job)

    @staticmethod
    def delete_job(db: Session, job_id: int, user_id: int, role: UserRole) -> None:
        """
        Deletes a job.
        Only the job creator or an admin can perform this operation.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")
        if role != UserRole.ADMIN and job.client_id != user_id:
            raise ValueError("Only the job creator or an admin can delete this job")

        db.delete(job)
        db.commit()
        logger.info(f"Job deleted: {job_id} by user {user_id}")

    @staticmethod
    def apply_for_job(db: Session, application: JobApplicationCreate, worker_id: int) -> JobApplicationOut:
        """
        Worker applies for a job.
        - Must not already be assigned
        - Worker must not have applied previously
        """
        job = db.query(Job).filter(Job.id == application.job_id).first()
        if not job:
            raise ValueError(f"Job with ID {application.job_id} not found")
        if job.worker_id:
            raise ValueError("This job is already assigned to a worker")
        if db.query(JobApplication).filter_by(job_id=application.job_id, worker_id=worker_id).first():
            raise ValueError("You have already applied for this job")

        db_application = JobApplication(
            job_id=application.job_id,
            worker_id=worker_id,
            status=ApplicationStatus.PENDING
        )
        db.add(db_application)
        db.commit()
        db.refresh(db_application)
        logger.info(f"Application created: {db_application.id} for job {application.job_id} by worker {worker_id}")
        return JobApplicationOut.model_validate(db_application)

    @staticmethod
    def get_application_by_id(db: Session, application_id: int) -> JobApplicationOut:
        """
        Retrieve a job application by its ID.
        """
        application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
        if not application:
            raise ValueError(f"Application with ID {application_id} not found")
        return JobApplicationOut.model_validate(application)

    @staticmethod
    def get_applications_by_job(db: Session, job_id: int) -> List[JobApplicationOut]:
        """
        Returns all applications for a given job.
        """
        applications = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()
        return [JobApplicationOut.model_validate(app) for app in applications]

    @staticmethod
    def update_application(
        db: Session,
        application_id: int,
        application_update: JobApplicationUpdate,
        user_id: int,
        role: UserRole
    ) -> JobApplicationOut:
        """
        Updates an application's status (ACCEPTED or REJECTED).
        If accepted, assigns the worker to the job.
        """
        application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
        if not application:
            raise ValueError(f"Application with ID {application_id} not found")

        job = db.query(Job).filter(Job.id == application.job_id).first()
        if role != UserRole.ADMIN and job.client_id != user_id:
            raise ValueError("Only the job creator or an admin can update this application")

        if application_update.status == ApplicationStatus.ACCEPTED:
            if job.worker_id:
                raise ValueError("This job is already assigned to a worker")
            job.worker_id = application.worker_id
            job.status = JobStatus.IN_PROGRESS
            application.status = ApplicationStatus.ACCEPTED

        elif application_update.status == ApplicationStatus.REJECTED:
            application.status = ApplicationStatus.REJECTED

        db.commit()
        db.refresh(application)
        db.refresh(job)
        logger.info(f"Application updated: {application_id} by user {user_id}")
        return JobApplicationOut.model_validate(application)
