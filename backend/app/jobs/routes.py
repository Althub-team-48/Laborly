from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.models import Job
from core.dependencies import get_db_session
from utils.logger import logger, log_system_action

router = APIRouter()

@router.post("/jobs")
def create_job(title: str, description: str, category: str, location: str, client_id: int, db: Session = Depends(get_db_session)):
    job = Job(
        client_id=client_id,
        title=title,
        description=description,
        category=category,
        location=location,
        status="Pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Log the action
    logger.info(f"Job created: {title} by client_id {client_id}")
    log_system_action(
        db=db,
        action_type="JOB_CREATED",
        details={"job_id": job.id, "title": job.title, "client_id": client_id},
        user_id=client_id
    )
    
    return {"message": "Job created successfully", "job_id": job.id}