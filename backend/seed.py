"""
Laborly Seeder Script (Fully Populated)

- Truncates all tables using SQLAlchemy (sync)
- Seeds Admins, Clients, Workers, Services, Messages, Jobs, Reviews with fake data
- Uses realistic data via Faker
"""

import sys
import random
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from faker import Faker

# -------------------------------------------------------
# Adjust path so that we can import app modules
# -------------------------------------------------------
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# -------------------------------------------------------
# App imports
# -------------------------------------------------------
from app.database.models import User
from app.database.enums import UserRole
from app.core.config import settings
from app.auth.services import get_password_hash as hash_password
from app.service.models import Service
from app.job.models import Job, JobStatus
from app.messaging.models import MessageThread, Message, ThreadParticipant
from app.review.models import Review

# -------------------------------------------------------
# Number of records to seed
# -------------------------------------------------------
NUM_ADMINS = 5
NUM_CLIENTS = 30
NUM_WORKERS = 10

class Seeder:
    def __init__(self):
        self.faker = Faker()
        self.sync_engine = self._get_sync_engine()
        self.db: Session = Session(bind=self.sync_engine)

    def _get_sync_engine(self):
        """Creates the synchronous engine for the database."""
        raw_url = settings.DATABASE_URL
        print(f"🔍 Using DATABASE URL: {raw_url}")
        sync_url = raw_url.replace("+asyncpg", "+psycopg2")
        print(f"🔁 Converted to sync URL: {sync_url}")
        return create_engine(sync_url)

    def truncate_all_tables(self):
        """Truncates all tables using SQLAlchemy."""
        print("🧹 Truncating all tables (sync)...")
        with self.sync_engine.connect() as conn:
            result = conn.execute(text(""" 
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """))
            tables = result.fetchall()
            for table in tables:
                table_name = table[0]
                conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))
                print(f"✅ Truncated {table_name}")
            conn.commit()
        print("✅ All tables truncated.\n")

    def seed_admins(self):
        """Seeds admin users with fake data."""
        print(f"👤 Seeding {NUM_ADMINS} admin(s)...")
        for _ in range(NUM_ADMINS):
            first = self.faker.first_name()
            last = self.faker.last_name()
            phone = self.faker.msisdn()[:11]
            email = f"admin{random.randint(1000, 9999)}@example.com"

            user = User(
                id=uuid4(),
                email=email,
                phone_number=phone,
                hashed_password=hash_password("string"),
                role=UserRole.ADMIN,
                first_name=first,
                last_name=last,
                middle_name=self.faker.first_name(),
                location=self.faker.city(),
                profile_picture=self.faker.image_url(),
                is_active=True,
                is_frozen=False,
                is_banned=False,
                is_deleted=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(user)
        self.db.commit()
        print("✅ Admins seeded.\n")

    def seed_clients(self):
        """Seeds client users with fake data."""
        print(f"👥 Seeding {NUM_CLIENTS} client(s)...")
        from app.client.models import ClientProfile

        for _ in range(NUM_CLIENTS):
            first = self.faker.first_name()
            last = self.faker.last_name()
            phone = self.faker.msisdn()[:11]
            email = f"client{random.randint(1000, 9999)}@example.com"

            user = User(
                id=uuid4(),
                email=email,
                phone_number=phone,
                hashed_password=hash_password("string"),
                role=UserRole.CLIENT,
                first_name=first,
                last_name=last,
                middle_name=self.faker.first_name(),
                location=self.faker.city(),
                profile_picture=self.faker.image_url(),
                is_active=True,
                is_frozen=False,
                is_banned=False,
                is_deleted=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(user)
            self.db.flush()

            profile = ClientProfile(
                user_id=user.id,
                profile_description=self.faker.sentence(nb_words=10),
                address=self.faker.address()
            )
            self.db.add(profile)
        self.db.commit()
        print("✅ Clients and profiles seeded.\n")

    def seed_workers(self):
        """Seeds worker users with fake data."""
        print(f"🧑‍🔧 Seeding {NUM_WORKERS} worker(s)...")
        from app.worker.models import WorkerProfile

        for _ in range(NUM_WORKERS):
            first = self.faker.first_name()
            last = self.faker.last_name()
            phone = self.faker.msisdn()[:11]
            email = f"worker{random.randint(1000, 9999)}@example.com"

            user = User(
                id=uuid4(),
                email=email,
                phone_number=phone,
                hashed_password=hash_password("string"),
                role=UserRole.WORKER,
                first_name=first,
                last_name=last,
                middle_name=self.faker.first_name(),
                location=self.faker.city(),
                profile_picture=self.faker.image_url(),
                is_active=True,
                is_frozen=False,
                is_banned=False,
                is_deleted=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(user)
            self.db.flush()

            profile = WorkerProfile(
                user_id=user.id,
                professional_skills=", ".join(self.faker.words(nb=3)),
                work_experience=self.faker.sentence(nb_words=10),
                is_verified=True,
                is_available=True,
                years_experience=random.randint(1, 10),
                availability_note=self.faker.sentence(nb_words=5),
                bio=self.faker.sentence(nb_words=10),
            )
            self.db.add(profile)
        self.db.commit()
        print("✅ Workers and profiles seeded.\n")

    def seed_services(self):
        """Seeds service listings for workers."""
        print("🛠️ Seeding services for workers...")

        # Fetch all workers
        worker_users = self.db.query(User).filter(User.role == UserRole.WORKER).all()

        service_titles = [
            "Electrician", "Plumber", "House Cleaning", "Painting",
            "Carpentry", "Laundry", "Gardening", "Cooking", "Driving"
        ]

        for worker in worker_users:
            for _ in range(random.randint(2, 3)):
                title = random.choice(service_titles)
                service = Service(
                    worker_id=worker.id,
                    title=title,
                    description=self.faker.paragraph(nb_sentences=2),
                    location=self.faker.city()
                )
                self.db.add(service)

        self.db.commit()
        print("✅ Services seeded for all workers.\n")

    def seed_messages(self):
        """Seeds message threads and messages between clients and workers."""
        print(f"💬 Seeding message threads and messages...")

        # Fetch all jobs, clients, and workers
        jobs = self.db.query(Job).filter(Job.status == JobStatus.ACCEPTED).all()
        client_users = self.db.query(User).filter(User.role == UserRole.CLIENT).all()
        worker_users = self.db.query(User).filter(User.role == UserRole.WORKER).all()

        for job in jobs:
            # Create a new message thread for each job
            thread = MessageThread(
                job_id=job.id,
                is_closed=False,  # Threads are open until closed by either user
            )
            self.db.add(thread)
            self.db.flush()  # Ensure thread.id is available

            # Add participants to the thread (worker and client)
            thread_participant_client = ThreadParticipant(
                thread_id=thread.id,
                user_id=job.client_id
            )
            thread_participant_worker = ThreadParticipant(
                thread_id=thread.id,
                user_id=job.worker_id
            )

            self.db.add(thread_participant_client)
            self.db.add(thread_participant_worker)
            self.db.flush()  # Ensure thread participants are added

            # Add messages to the thread (simulating conversation)
            for _ in range(random.randint(3, 5)):  # 3–5 messages per thread
                sender = random.choice([job.client_id, job.worker_id])  # Random sender
                message_content = self.faker.sentence(nb_words=8)
                
                message = Message(
                    thread_id=thread.id,
                    sender_id=sender,
                    content=message_content
                )
                self.db.add(message)

        self.db.commit()
        print("✅ Message threads and messages seeded.\n")

    def seed_jobs(self):
        """Seeds jobs for clients and assigns them to workers."""
        print(f"📝 Seeding jobs for clients...")

        # Fetch all clients and workers
        client_users = self.db.query(User).filter(User.role == UserRole.CLIENT).all()
        worker_users = self.db.query(User).filter(User.role == UserRole.WORKER).all()
        service_items = self.db.query(Service).all()

        for client in client_users:
            for _ in range(random.randint(2, 3)):  # 2–3 jobs per client
                # Random worker and service assignment
                worker = random.choice(worker_users)
                service = random.choice(service_items) if service_items else None

                # First, create a message thread for the job
                thread = MessageThread(is_closed=False)
                self.db.add(thread)
                self.db.flush()  # Ensure thread.id is available

                # Create a job linked to the message thread
                job = Job(
                    client_id=client.id,
                    worker_id=worker.id,
                    service_id=service.id if service else None,
                    status=random.choice([JobStatus.NEGOTIATING, JobStatus.ACCEPTED, JobStatus.COMPLETED]),
                    thread_id=thread.id,  # Use the created thread's ID
                )

                # Optionally, set completed or cancelled timestamps based on status
                if job.status == JobStatus.COMPLETED:
                    job.completed_at = datetime.now(timezone.utc)
                elif job.status == JobStatus.CANCELLED:
                    job.cancelled_at = datetime.now(timezone.utc)
                    job.cancel_reason = "Client canceled the job."

                self.db.add(job)

        self.db.commit()
        print("✅ Jobs and threads seeded.\n")

    def seed_reviews(self):
        """Seeds reviews for completed jobs."""
        print(f"⭐ Seeding reviews for completed jobs...")

        # Fetch all completed jobs
        completed_jobs = self.db.query(Job).filter(Job.status == JobStatus.COMPLETED).all()

        for job in completed_jobs:
            # Random review content
            rating = random.randint(1, 5)
            review_text = self.faker.sentence(nb_words=15) if random.choice([True, False]) else None
            is_flagged = random.choice([True, False])  # Randomly flag some reviews

            review = Review(
                client_id=job.client_id,
                worker_id=job.worker_id,
                job=job,  # Set the relationship to the job
                rating=rating,
                review_text=review_text,
                is_flagged=is_flagged,
            )

            self.db.add(review)

        self.db.commit()
        print("✅ Reviews seeded for all completed jobs.\n")


if __name__ == "__main__":
    seeder = Seeder()
    seeder.truncate_all_tables()
    seeder.seed_admins()
    seeder.seed_clients()
    seeder.seed_workers()
    seeder.seed_services()
    seeder.seed_messages()
    seeder.seed_jobs()
    seeder.seed_reviews()
    print("🎉 Seeding completed successfully!")
