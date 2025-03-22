"""
[admin] service.py

Service layer for admin operations:
- User management (listing, verification toggle)
- Job listings with optional status filtering
- Dispute resolution with job status updates
"""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from database.models import Dispute, Job, User, DisputeStatus, JobStatus
from admin.schemas import DisputeUpdate, DisputeOut, UserOut, JobOut
from utils.logger import logger, log_system_action


class AdminService:
    @staticmethod
    def get_users(db: Session) -> List[UserOut]:
        """Fetch all users for admin dashboard."""
        users = db.query(User).all()
        logger.info(f"Fetched {len(users)} users")
        return [UserOut.model_validate(user) for user in users]

    @staticmethod
    def update_user_verification(db: Session, user_id: int, is_verified: bool) -> UserOut:
        """Toggle user verification status."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        user.is_verified = is_verified
        db.commit()
        db.refresh(user)

        log_system_action(db, None, "UPDATE", f"User {user_id} verification set to {is_verified}")
        logger.info(f"User verification updated: {user_id} -> {is_verified}")
        return UserOut.model_validate(user)

    @staticmethod
    def get_jobs(db: Session, status: Optional[str] = None) -> List[JobOut]:
        """Fetch all jobs with optional status filter."""
        query = db.query(Job)
        if status:
            try:
                job_status = JobStatus[status.upper()]
                query = query.filter(Job.status == job_status)
            except KeyError:
                raise ValueError(f"Invalid job status: {status}")
        jobs = query.all()
        logger.info(f"Fetched {len(jobs)} jobs (status filter: {status})")
        return [JobOut.model_validate(job) for job in jobs]

    @staticmethod
    def get_disputes(db: Session) -> List[DisputeOut]:
        """Fetch all disputes."""
        disputes = db.query(Dispute).all()
        logger.info(f"Fetched {len(disputes)} disputes")
        return [DisputeOut.model_validate(dispute) for dispute in disputes]

    @staticmethod
    def resolve_dispute(db: Session, dispute_id: int, update: DisputeUpdate) -> DisputeOut:
        """Resolve a dispute and update the associated job status."""
        dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            raise ValueError("Dispute not found")

        if update.status:
            status_upper = update.status.upper()
            if status_upper not in DisputeStatus.__members__:
                raise ValueError(f"Invalid dispute status: {update.status}")
            dispute.status = DisputeStatus[status_upper]
            dispute.resolved_at = datetime.now(timezone.utc) if dispute.status != DisputeStatus.PENDING else None

            # Update related job status
            if dispute.status == DisputeStatus.RESOLVED:
                dispute.job.status = JobStatus.COMPLETED
            elif dispute.status == DisputeStatus.DISMISSED:
                dispute.job.status = JobStatus.CANCELLED

        db.commit()
        db.refresh(dispute)

        log_system_action(db, None, "UPDATE", f"Dispute {dispute_id} resolved with status {dispute.status}")
        logger.info(f"Dispute resolved: {dispute_id} -> {dispute.status}")
        return DisputeOut.model_validate(dispute)
