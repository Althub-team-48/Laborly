from app.database.models import User, Job, JobApplication, JobAssignment, Review, WorkerAvailability, UserRole, JobStatus, ApplicationStatus, ActionType
from app.database.config import SessionLocal
from app.utils.logger import logger, log_system_action, log_admin_action
from datetime import datetime, timezone, timedelta
import random
import string

def generate_random_string(length=8):
    """Generate a random string of fixed length."""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))

def generate_random_phone():
    """Generate a random phone number in a realistic format."""
    return f"({random.randint(200, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"

def seed_data():
    db = SessionLocal()
    try:
        print("Seeding database...")

        # Create an admin user
        admin_user = User(
            first_name="Admin",
            last_name="User",
            email="admin@laborly.com",
            phone_number="1234567890",
            password_hash="hashed_password",  # In production, use a proper hashing function
            role=UserRole.ADMIN,
            is_verified=True,
            last_active=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Admin user created: {admin_user.email}")
        logger.info(f"Admin user created: {admin_user.email}")
        log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action_type=ActionType.CREATE,
            details={"user_id": admin_user.id, "email": admin_user.email, "role": admin_user.role.value}
        )

        # Create multiple client users
        client_users = []
        for i in range(10):  # Creating 10 clients for testing
            client_user = User(
                first_name=generate_random_string(5),
                last_name=generate_random_string(5),
                email=f"client{i+1}@laborly.com",  # Ensure unique emails
                phone_number=generate_random_phone(),
                password_hash="hashed_password",
                role=UserRole.CLIENT,
                is_verified=True,
                last_active=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(client_user)
            client_users.append(client_user)

        db.commit()
        for client_user in client_users:
            db.refresh(client_user)
            print(f"Client user created: {client_user.email}")
            logger.info(f"Client user created: {client_user.email}")
            log_system_action(
                db=db,
                action_type=ActionType.CREATE,
                details={"user_id": client_user.id, "email": client_user.email, "role": client_user.role.value},
                user_id=client_user.id
            )

        # Create multiple worker users
        worker_users = []
        for i in range(5):  # Creating 5 workers for testing
            worker_user = User(
                first_name=generate_random_string(5),
                last_name=generate_random_string(5),
                email=f"worker{i+1}@laborly.com",  # Ensure unique emails
                phone_number=generate_random_phone(),
                password_hash="hashed_password",
                role=UserRole.WORKER,
                is_verified=True,
                last_active=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(worker_user)
            worker_users.append(worker_user)

        db.commit()
        for worker_user in worker_users:
            db.refresh(worker_user)
            print(f"Worker user created: {worker_user.email}")
            logger.info(f"Worker user created: {worker_user.email}")
            log_system_action(
                db=db,
                action_type=ActionType.CREATE,
                details={"user_id": worker_user.id, "email": worker_user.email, "role": worker_user.role.value},
                user_id=worker_user.id
            )

        # Create worker availability for each worker
        for worker in worker_users:
            for _ in range(random.randint(1, 3)):  # Each worker has 1-3 availability slots
                available_from = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 7))
                available_to = available_from + timedelta(hours=random.randint(4, 8))
                availability = WorkerAvailability(
                    worker_id=worker.id,
                    available_from=available_from,
                    available_to=available_to,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(availability)

        db.commit()
        print("Worker availability created successfully.")

        # Create multiple jobs with varying categories and statuses
        job_titles = ["Fix my sink", "Paint the wall", "Install a door", "Repair the car", "Clean the house"]
        job_categories = ["Plumbing", "Electrical", "Carpentry", "Cleaning", "Gardening"]
        job_locations = ["New York", "Los Angeles", "Chicago", "Houston", "Miami"]

        jobs = []
        for i in range(20):  # Creating 20 jobs for testing
            client_user = random.choice(client_users)  # Assign a random client to a job
            job = Job(
                client_id=client_user.id,
                title=f"{random.choice(job_titles)} #{i+1}",
                description=f"Sample description for job #{i+1}.",
                category=random.choice(job_categories),
                location=random.choice(job_locations),
                status=random.choice(list(JobStatus)),
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(job)
            jobs.append(job)

        db.commit()
        for job in jobs:
            db.refresh(job)
            logger.info(f"Job created: {job.title} by client_id {job.client_id}")
            log_system_action(
                db=db,
                action_type=ActionType.CREATE,
                details={"job_id": job.id, "title": job.title, "client_id": job.client_id},
                user_id=job.client_id
            )
        print("Jobs created successfully.")

        # Create job applications for some jobs
        for job in random.sample(jobs, 10):  # Randomly select 10 jobs for applications
            worker = random.choice(worker_users)
            application = JobApplication(
                job_id=job.id,
                worker_id=worker.id,
                status=random.choice(list(ApplicationStatus)),
                applied_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10)),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(application)

        db.commit()
        print("Job applications created successfully.")

        # Create job assignments for some jobs
        for job in random.sample(jobs, 5):  # Randomly select 5 jobs for assignments
            if job.status in [JobStatus.COMPLETED, JobStatus.IN_PROGRESS]:
                worker = random.choice(worker_users)
                assignment = JobAssignment(
                    job_id=job.id,
                    worker_id=worker.id,
                    assigned_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5)),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(assignment)

        db.commit()
        print("Job assignments created successfully.")

        # Create reviews for completed jobs
        for job in jobs:
            if job.status == JobStatus.COMPLETED:
                client = next(user for user in client_users if user.id == job.client_id)
                worker = random.choice(worker_users)
                review = Review(
                    job_id=job.id,
                    reviewer_id=client.id,
                    reviewee_id=worker.id,
                    rating=random.randint(1, 5),
                    comment=f"Review for job #{job.id}: {generate_random_string(20)}",
                    created_at=datetime.now(timezone.utc)
                )
                db.add(review)

        db.commit()
        print("Reviews created successfully.")

        print("Database seeded successfully.")

    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        logger.error(f"Error seeding database: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()