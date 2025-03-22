'''
[seed] seed.py

Populates the database with semi-realistic data for local development or testing purposes:
- Creates admin, client, and worker users
- Generates jobs with various statuses (e.g., PENDING, IN_PROGRESS, COMPLETED)
- Assigns job applications with realistic timestamps
- Adds completed jobs with mutual reviews
- Introduces disputes with sample reasons
- Fills in availability slots for workers
All generated values follow structured naming conventions and valid formats (e.g., Nigerian phone numbers).
'''

import sys
from pathlib import Path

# Dynamically set the backend directory as the root module
current_file = Path(__file__).resolve()
project_root = current_file.parents[1]
sys.path.insert(0, str(project_root))

import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from database.config import SessionLocal
from database.models import (
    Dispute,
    Review,
    User,
    Job,
    JobApplication,
    WorkerAvailability,
    UserRole,
    JobStatus,
    ApplicationStatus,
    DisputeStatus
)

from reviews.service import ReviewService
from utils.logger import logger
from core.security import get_password_hash

# Configuration: number of records to generate
NUM_ADMINS = 1
NUM_CLIENTS = 10
NUM_WORKERS = 5
NUM_JOBS = 15
NUM_JOB_APPLICATIONS = 10
NUM_COMPLETED_JOBS_FOR_REVIEW = 4
NUM_DISPUTES = 3

class Seeder:
    def __init__(self):
        self.db: Session = SessionLocal()
        self.users = []
        self.jobs = []

    def now(self):
        return datetime.now(timezone.utc)

    def generate_phone_number(self) -> str:
        return f"+234{random.randint(7000000000, 9099999999)}"

    def create_users(self):
        roles = [(UserRole.ADMIN, NUM_ADMINS), (UserRole.CLIENT, NUM_CLIENTS), (UserRole.WORKER, NUM_WORKERS)]
        for role, count in roles:
            for i in range(1, count + 1):
                suffix = f"{role.value.lower()}{i}"
                user = User(
                    first_name="Test",
                    last_name=suffix,
                    email=f"{suffix}@example.com",
                    phone_number=self.generate_phone_number(),
                    password_hash=get_password_hash("string"),
                    role=role,
                    is_verified=True,
                    last_active=self.now(),
                    created_at=self.now(),
                    updated_at=self.now(),
                )
                self.db.add(user)
                self.users.append(user)
        self.db.commit()

    def split_users(self):
        self.admin = [u for u in self.users if u.role == UserRole.ADMIN][0]
        self.clients = [u for u in self.users if u.role == UserRole.CLIENT]
        self.workers = [u for u in self.users if u.role == UserRole.WORKER]

    def create_jobs(self):
        job_titles = ["Fix plumbing leak", "Paint bedroom", "Assemble furniture", "Install AC", "Repair generator"]
        for i in range(NUM_JOBS):
            client = random.choice(self.clients)
            job = Job(
                title=random.choice(job_titles),
                description=f"Detailed description for job {i+1}.",
                client_id=client.id,
                status=random.choice(list(JobStatus)),
                created_at=self.now() - timedelta(days=random.randint(1, 20)),
                updated_at=self.now(),
            )
            self.db.add(job)
            self.jobs.append(job)
        self.db.commit()

    def assign_workers_to_jobs(self):
        for job in random.sample(self.jobs, min(5, len(self.jobs))):
            worker = random.choice(self.workers)
            job.worker_id = worker.id
            job.status = JobStatus.IN_PROGRESS
        self.db.commit()

    def complete_some_jobs(self):
        completed_jobs = random.sample(self.jobs, min(NUM_COMPLETED_JOBS_FOR_REVIEW, len(self.jobs)))
        for job in completed_jobs:
            job.status = JobStatus.COMPLETED
            job.client_completed = True
            job.worker_completed = True
            job.worker_id = random.choice(self.workers).id if not job.worker_id else job.worker_id
        self.db.commit()
        return completed_jobs

    def add_reviews(self, completed_jobs):
        for job in completed_jobs:
            if job.worker_id:
                self.db.add_all([
                    Review(job_id=job.id, reviewer_id=job.client_id, reviewee_id=job.worker_id, rating=random.randint(1, 5)),
                    Review(job_id=job.id, reviewer_id=job.worker_id, reviewee_id=job.client_id, rating=random.randint(1, 5)),
                ])
        self.db.commit()

        for user in self.clients + self.workers:
            ReviewService.update_average_rating(self.db, user.id)

    def create_job_applications(self):
        for job in random.sample(self.jobs, min(NUM_JOB_APPLICATIONS, len(self.jobs))):
            worker = random.choice(self.workers)
            status = random.choice(list(ApplicationStatus))
            app = JobApplication(
                job_id=job.id,
                worker_id=worker.id,
                status=status,
                applied_at=self.now() - timedelta(days=random.randint(1, 10)),
                updated_at=self.now()
            )
            self.db.add(app)
            if status == ApplicationStatus.ACCEPTED:
                job.worker_id = worker.id
                job.status = JobStatus.IN_PROGRESS
        self.db.commit()

    def create_disputes(self):
        reasons = ["Incomplete job", "Payment issue", "Rude behavior"]
        for job in random.sample(self.jobs, min(NUM_DISPUTES, len(self.jobs))):
            dispute = Dispute(
                job_id=job.id,
                raised_by_id=job.client_id,
                reason=random.choice(reasons),
                status=random.choice(list(DisputeStatus))
            )
            self.db.add(dispute)
        self.db.commit()

    def create_availability(self):
        for worker in self.workers:
            for _ in range(random.randint(1, 3)):
                start = self.now() + timedelta(days=random.randint(1, 5), hours=random.randint(8, 10))
                end = start + timedelta(hours=random.randint(2, 4))
                slot = WorkerAvailability(worker_id=worker.id, start_time=start, end_time=end)
                self.db.add(slot)
        self.db.commit()

    def run(self):
        try:
            logger.info("Starting database seeding...")
            self.create_users()
            self.split_users()
            self.create_jobs()
            self.assign_workers_to_jobs()
            completed_jobs = self.complete_some_jobs()
            self.add_reviews(completed_jobs)
            self.create_job_applications()
            self.create_disputes()
            self.create_availability()
            logger.info("Seeding complete.")
            print("Seeding complete.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Seeding failed: {e}")
            print(f"Error: {e}")
        finally:
            self.db.close()


if __name__ == "__main__":
    Seeder().run()
