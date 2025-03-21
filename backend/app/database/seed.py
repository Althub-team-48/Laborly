"""
seed.py

This script populates the database with initial sample data for development/testing.
It creates:
- One admin user
- Multiple client and worker users
- Sample jobs assigned to clients
- Random job applications from workers
- Availability time slots for workers
"""

import random
import string
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from database.config import SessionLocal
from database.models import (
    User,
    SystemLog,
    Job,
    JobApplication,
    WorkerAvailability,
    UserRole,
    ActionType,
    JobStatus,
    ApplicationStatus,
)
from utils.logger import logger


def generate_random_string(length: int = 8) -> str:
    """Generate a random string of given length."""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))


def generate_random_phone() -> str:
    """Generate a random US-style phone number."""
    return f"({random.randint(200, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"


def seed_data() -> None:
    """Main function to seed the database with sample users, jobs, applications, and availability."""
    db: Session = SessionLocal()
    try:
        print("Seeding database...")
        logger.info("Starting database seeding...")

        # Create admin user
        admin_user = User(
            first_name="Admin",
            last_name="User",
            email="admin@laborly.com",
            phone_number="1234567890",
            password_hash="$2b$12$Kixz...examplehashedpassword",
            role=UserRole.ADMIN,
            is_verified=True,
            last_active=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Admin user created: {admin_user.email}")
        logger.info(f"Admin user created: {admin_user.email}")

        # Create client users
        client_users = []
        for i in range(10):
            client_user = User(
                first_name=generate_random_string(5),
                last_name=generate_random_string(5),
                email=f"client{i+1}@laborly.com",
                phone_number=generate_random_phone(),
                password_hash="$2b$12$Kixz...examplehashedpassword",
                role=UserRole.CLIENT,
                is_verified=True,
                last_active=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(client_user)
            client_users.append(client_user)
        db.commit()

        # Create worker users
        worker_users = []
        for i in range(5):
            worker_user = User(
                first_name=generate_random_string(5),
                last_name=generate_random_string(5),
                email=f"worker{i+1}@laborly.com",
                phone_number=generate_random_phone(),
                password_hash="$2b$12$Kixz...examplehashedpassword",
                role=UserRole.WORKER,
                is_verified=True,
                last_active=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(worker_user)
            worker_users.append(worker_user)
        db.commit()

        # Create sample jobs
        job_titles = ["Fix my sink", "Paint the wall", "Install a door", "Repair the car", "Clean the house"]
        jobs = []
        for i in range(20):
            client_user = random.choice(client_users)
            job = Job(
                client_id=client_user.id,
                title=f"{random.choice(job_titles)} #{i+1}",
                description=f"Sample description for job #{i+1}.",
                status=JobStatus.PENDING,
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(job)
            jobs.append(job)
        db.commit()

        # Create job applications for 10 jobs
        for job in random.sample(jobs, 10):
            worker = random.choice(worker_users)
            application = JobApplication(
                job_id=job.id,
                worker_id=worker.id,
                status=random.choice(list(ApplicationStatus)),
                applied_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10)),
                updated_at=datetime.now(timezone.utc),
            )

            # If application is accepted, assign worker to the job
            if application.status == ApplicationStatus.ACCEPTED:
                job.worker_id = worker.id
                job.status = JobStatus.IN_PROGRESS

            db.add(application)
        db.commit()

        # Create worker availability slots
        for worker in worker_users:
            for _ in range(random.randint(1, 3)):
                start_time = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 7), hours=random.randint(8, 12))
                end_time = start_time + timedelta(hours=random.randint(2, 6))
                availability = WorkerAvailability(
                    worker_id=worker.id,
                    start_time=start_time,
                    end_time=end_time,
                )
                db.add(availability)
        db.commit()

        print("Database seeded successfully.")
        logger.info("Database seeded successfully.")

    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        logger.error(f"Error seeding database: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
