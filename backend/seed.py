"""
Laborly Seeder Script (Fully Populated)

- Truncates all tables using SQLAlchemy (sync)
- Seeds Admins, Clients, Workers, Services, Messages, Jobs, Reviews with fake data
- Uses realistic data via Faker and Nigerian locations
- All users have the same password: String@123
"""

import sys
import random
from uuid import uuid4
from datetime import datetime, timezone, timedelta  # Import timedelta
from pathlib import Path

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import Engine, create_engine, text
from faker import Faker

# -------------------------------------------------------
# Adjust path so that we can import app modules
# -------------------------------------------------------
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# -------------------------------------------------------
# App imports
# -------------------------------------------------------
from myapp.database.models import User
from myapp.database.enums import UserRole
from myapp.core.config import settings
from myapp.auth.services import get_password_hash as hash_password
from myapp.service.models import Service
from myapp.job.models import Job, JobStatus
from myapp.messaging.models import MessageThread, Message, ThreadParticipant
from myapp.review.models import Review

# Import profile models explicitly if needed later
from myapp.client.models import ClientProfile
from myapp.worker.models import WorkerProfile

# -------------------------------------------------------
# Number of records to seed
# -------------------------------------------------------
NUM_ADMINS = 5
NUM_CLIENTS = 30
NUM_WORKERS = 10

# -------------------------------------------------------
# Nigerian States List
# -------------------------------------------------------
NIGERIAN_STATES = [
    "Abia",
    "Adamawa",
    "Akwa Ibom",
    "Anambra",
    "Bauchi",
    "Bayelsa",
    "Benue",
    "Borno",
    "Cross River",
    "Delta",
    "Ebonyi",
    "Edo",
    "Ekiti",
    "Enugu",
    "Gombe",
    "Imo",
    "Jigawa",
    "Kaduna",
    "Kano",
    "Katsina",
    "Kebbi",
    "Kogi",
    "Kwara",
    "Lagos",
    "Nasarawa",
    "Niger",
    "Ogun",
    "Ondo",
    "Osun",
    "Oyo",
    "Plateau",
    "Rivers",
    "Sokoto",
    "Taraba",
    "Yobe",
    "Zamfara",
    "FCT",
]


class Seeder:
    def __init__(self) -> None:
        self.faker = Faker()
        self.sync_engine = self._get_sync_engine()
        self.db: Session = Session(bind=self.sync_engine)

    def _get_sync_engine(self) -> Engine:
        """Creates the synchronous engine for the database."""
        raw_url = settings.DATABASE_URL
        print(f"🔍 Using DATABASE URL: {raw_url}")
        # Ensure psycopg2 is used for sync operations if DATABASE_URL uses asyncpg
        sync_url = raw_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        print(f"🔁 Converted to sync URL: {sync_url}")
        return create_engine(sync_url)

    def truncate_all_tables(self) -> None:
        """Truncates all tables using SQLAlchemy."""
        print("🧹 Truncating all tables (sync)...")
        with self.sync_engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                AND table_name != 'alembic_version' -- Exclude alembic table
            """
                )
            )
            tables = result.fetchall()
            for table in tables:
                table_name = table[0]
                try:
                    conn.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE;'))
                    print(f"✅ Truncated {table_name}")
                except Exception as e:
                    print(f"⚠️ Could not truncate {table_name}: {e}")
            conn.commit()
        print("✅ All tables truncated.\n")

    def seed_admins(self) -> None:
        """Seeds admin users with fake data and Nigerian locations."""
        print(f"👤 Seeding {NUM_ADMINS} admin(s)...")
        for _ in range(NUM_ADMINS):
            first = self.faker.first_name()
            last = self.faker.last_name()
            phone = self.faker.msisdn()[:11]
            email = f"admin{random.randint(1000, 9999)}@example.com"
            location = random.choice(NIGERIAN_STATES)

            user = User(
                id=uuid4(),
                email=email,
                phone_number=phone,
                hashed_password=hash_password("String@123"),
                role=UserRole.ADMIN,
                first_name=first,
                last_name=last,
                middle_name=self.faker.first_name(),
                location=location,
                profile_picture=self.faker.image_url(),
                is_active=True,
                is_frozen=False,
                is_banned=False,
                is_deleted=False,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(user)
        self.db.commit()
        print("✅ Admins seeded.\n")

    def seed_clients(self) -> None:
        """Seeds client users with fake data and Nigerian locations."""
        print(f"👥 Seeding {NUM_CLIENTS} client(s)...")
        for _ in range(NUM_CLIENTS):
            first = self.faker.first_name()
            last = self.faker.last_name()
            phone = self.faker.msisdn()[:11]
            email = f"client{random.randint(1000, 9999)}@example.com"
            location = random.choice(NIGERIAN_STATES)
            address = f"{self.faker.street_address()}, {location}"

            user = User(
                id=uuid4(),
                email=email,
                phone_number=phone,
                hashed_password=hash_password("String@123"),
                role=UserRole.CLIENT,
                first_name=first,
                last_name=last,
                middle_name=self.faker.first_name(),
                location=location,
                profile_picture=self.faker.image_url(),
                is_active=True,
                is_frozen=False,
                is_banned=False,
                is_deleted=False,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(user)
            self.db.flush()

            profile = ClientProfile(
                user_id=user.id,
                profile_description=self.faker.sentence(nb_words=10),
                address=address,
            )
            self.db.add(profile)
        self.db.commit()
        print("✅ Clients and profiles seeded.\n")

    def seed_workers(self) -> None:
        """Seeds worker users with fake data and Nigerian locations."""
        print(f"🧑‍🔧 Seeding {NUM_WORKERS} worker(s)...")
        for _ in range(NUM_WORKERS):
            first = self.faker.first_name()
            last = self.faker.last_name()
            phone = self.faker.msisdn()[:11]
            email = f"worker{random.randint(1000, 9999)}@example.com"
            location = random.choice(NIGERIAN_STATES)

            user = User(
                id=uuid4(),
                email=email,
                phone_number=phone,
                hashed_password=hash_password("String@123"),
                role=UserRole.WORKER,
                first_name=first,
                last_name=last,
                middle_name=self.faker.first_name(),
                location=location,
                profile_picture=self.faker.image_url(),
                is_active=True,
                is_frozen=False,
                is_banned=False,
                is_deleted=False,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(user)
            self.db.flush()

            profile = WorkerProfile(
                user_id=user.id,
                professional_skills=", ".join(self.faker.words(nb=random.randint(2, 5))),
                work_experience=self.faker.sentence(nb_words=10),
                is_kyc_verified=random.choice([True, False]),
                is_available=random.choice([True, False]),
                years_experience=random.randint(1, 15),
                availability_note=self.faker.sentence(nb_words=5),
                bio=self.faker.sentence(nb_words=15),
            )
            self.db.add(profile)
        self.db.commit()
        print("✅ Workers and profiles seeded.\n")

    def seed_services(self) -> None:
        """Seeds service listings for workers with Nigerian locations."""
        print("🛠️ Seeding services for workers...")
        worker_users = self.db.query(User).filter(User.role == UserRole.WORKER).all()
        if not worker_users:
            print("⚠️ No workers found to seed services for.")
            return

        service_titles = [
            "Electrician",
            "Plumber",
            "House Cleaning",
            "Painting",
            "Carpentry",
            "Laundry Service",
            "Gardening",
            "Home Cooking",
            "Driving Service",
            "AC Repair",
            "Generator Repair",
            "Tiling",
            "Welding",
            "Event Ushering",
        ]
        service_count = 0
        for worker in worker_users:
            num_services = random.randint(1, 3)
            assigned_titles = random.sample(
                service_titles, k=min(num_services, len(service_titles))
            )
            for title in assigned_titles:
                service_location = random.choice([worker.location, random.choice(NIGERIAN_STATES)])
                service = Service(
                    worker_id=worker.id,
                    title=title,
                    description=self.faker.paragraph(nb_sentences=random.randint(1, 3)),
                    location=service_location,
                )
                self.db.add(service)
                service_count += 1
        self.db.commit()
        print(f"✅ {service_count} Services seeded.\n")

    def seed_jobs(self) -> None:
        """Seeds jobs for clients and assigns them to workers."""
        print("📝 Seeding jobs...")
        client_users = self.db.query(User).filter(User.role == UserRole.CLIENT).all()
        worker_users = self.db.query(User).filter(User.role == UserRole.WORKER).all()
        all_services = self.db.query(Service).all()

        if not client_users or not worker_users or not all_services:
            print("⚠️ Cannot seed jobs: Missing clients, workers, or services.")
            return

        job_count = 0
        for client in client_users:
            for _ in range(random.randint(1, 4)):
                service = random.choice(all_services)
                worker_id = service.worker_id

                # Create a message thread first
                thread = MessageThread(is_closed=False)
                self.db.add(thread)
                self.db.flush()  # Get thread.id

                # Create the job WITHOUT thread_id
                job_status = random.choice(list(JobStatus))
                job = Job(
                    client_id=client.id,
                    worker_id=worker_id,
                    service_id=service.id,
                    status=job_status,
                    # REMOVED: thread_id=thread.id,
                )
                self.db.add(job)
                self.db.flush()  # Get job.id

                # FIX: Update the thread with the job_id
                thread.job_id = job.id
                self.db.add(thread)  # Add thread again to mark it dirty for the update

                # Set timestamps based on status
                if job_status in [
                    JobStatus.ACCEPTED,
                    JobStatus.COMPLETED,
                    JobStatus.FINALIZED,
                    JobStatus.CANCELLED,
                ]:
                    job.started_at = self.faker.date_time_this_year(tzinfo=timezone.utc)
                if job_status in [JobStatus.COMPLETED, JobStatus.FINALIZED]:
                    job.completed_at = (
                        self.faker.date_time_between(start_date=job.started_at, tzinfo=timezone.utc)
                        if job.started_at
                        else self.faker.date_time_this_year(tzinfo=timezone.utc)
                    )
                if job_status == JobStatus.CANCELLED:
                    job.cancelled_at = (
                        self.faker.date_time_between(start_date=job.started_at, tzinfo=timezone.utc)
                        if job.started_at
                        else self.faker.date_time_this_year(tzinfo=timezone.utc)
                    )
                    job.cancel_reason = self.faker.sentence(nb_words=6)

                # No need to add job again, already added
                job_count += 1

        self.db.commit()  # Commit jobs and thread updates
        print(f"✅ {job_count} Jobs seeded.\n")

    def seed_messages(self) -> None:
        """Seeds message threads and messages for existing jobs."""
        print("💬 Seeding messages for jobs...")
        jobs_with_threads = (
            self.db.query(Job)
            .options(
                # Eager load thread to avoid separate queries per job
                selectinload(Job.thread)
            )
            .filter(Job.thread.has())
            .all()
        )  # Filter jobs that have an associated thread

        if not jobs_with_threads:
            print("⚠️ No jobs with threads found to seed messages for.")
            return

        message_count = 0
        for job in jobs_with_threads:
            thread = job.thread  # Access the eager-loaded thread
            if not thread:
                continue  # Skip if thread somehow wasn't loaded

            thread_id = thread.id
            client_id = job.client_id
            worker_id = job.worker_id

            if not client_id or not worker_id:
                continue

            # Add participants (should ideally be handled when thread is created)
            existing_participants_query = self.db.query(ThreadParticipant.user_id).filter(
                ThreadParticipant.thread_id == thread_id
            )
            existing_participants = {p[0] for p in existing_participants_query.all()}
            if client_id not in existing_participants:
                self.db.add(ThreadParticipant(thread_id=thread_id, user_id=client_id))
            if worker_id not in existing_participants:
                self.db.add(ThreadParticipant(thread_id=thread_id, user_id=worker_id))

            # Add messages
            num_messages = random.randint(2, 7)
            participants = [client_id, worker_id]
            last_timestamp = (
                job.created_at
                if isinstance(job.created_at, datetime)
                else datetime.now(timezone.utc)
            )

            for i in range(num_messages):
                sender_id = random.choice(participants)
                try:
                    min_start_date = last_timestamp + timedelta(seconds=1)
                    msg_timestamp = self.faker.date_time_between(
                        start_date=min_start_date, tzinfo=timezone.utc
                    )
                    last_timestamp = msg_timestamp
                except ValueError:
                    msg_timestamp = last_timestamp + timedelta(minutes=i + 1)
                    last_timestamp = msg_timestamp

                message = Message(
                    thread_id=thread_id,
                    sender_id=sender_id,
                    content=self.faker.sentence(nb_words=random.randint(5, 15)),
                    timestamp=msg_timestamp,
                )
                self.db.add(message)
                message_count += 1

        self.db.commit()
        print(f"✅ {message_count} Messages seeded.\n")

    def seed_reviews(self) -> None:
        """Seeds reviews for completed or finalized jobs."""
        print("⭐ Seeding reviews...")
        reviewable_jobs = (
            self.db.query(Job)
            .filter(Job.status.in_([JobStatus.COMPLETED, JobStatus.FINALIZED]))
            .all()
        )

        if not reviewable_jobs:
            print("⚠️ No completed/finalized jobs found to seed reviews for.")
            return

        review_count = 0
        for job in reviewable_jobs:
            existing_review = self.db.query(Review).filter_by(job_id=job.id).first()
            if existing_review:
                continue
            if not job.client_id or not job.worker_id:
                continue

            review = Review(
                client_id=job.client_id,
                worker_id=job.worker_id,
                job_id=job.id,
                rating=random.randint(1, 5),
                review_text=(
                    self.faker.paragraph(nb_sentences=random.randint(1, 3))
                    if random.choice([True, False])
                    else None
                ),
                is_flagged=random.choice([False, False, False, True]),
            )
            self.db.add(review)
            review_count += 1
        self.db.commit()
        print(f"✅ {review_count} Reviews seeded.\n")

    def run_all(self) -> None:
        """Runs all seeding steps in order."""
        self.truncate_all_tables()
        self.seed_admins()
        self.seed_clients()
        self.seed_workers()
        self.seed_services()
        self.seed_jobs()  # Seeds jobs and creates threads
        self.seed_messages()  # Seeds messages for the threads created in seed_jobs
        self.seed_reviews()
        print("🎉 Seeding completed successfully!")
        print("🔑 Default password for all seeded users: String@123")


if __name__ == "__main__":
    seeder = Seeder()
    try:
        seeder.run_all()
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if seeder.db:
            seeder.db.close()
            print("🔒 Database session closed.")
