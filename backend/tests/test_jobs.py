import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, User, Job
from database.config import get_db

# Use the same in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_job(test_db):
    db = TestingSessionLocal()
    # Create a client user first
    client = User(
        first_name="Client",
        last_name="User",
        email="client_test@laborly.com",
        password_hash="test_hash",
        role="Client",
        is_verified=True
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    # Create a job
    job = Job(
        client_id=client.id,
        title="Test Job",
        description="Test Description",
        category="Test Category",
        location="Test Location",
        status="Pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    assert job.id is not None
    assert job.title == "Test Job"
    assert job.client_id == client.id
    db.close()

def test_read_job(test_db):
    db = TestingSessionLocal()
    client = User(
        first_name="Client",
        last_name="User",
        email="client_test2@laborly.com",
        password_hash="test_hash",
        role="Client",
        is_verified=True
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    job = Job(
        client_id=client.id,
        title="Test Job 2",
        description="Test Description 2",
        category="Test Category 2",
        location="Test Location 2",
        status="Pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    fetched_job = db.query(Job).filter(Job.title == "Test Job 2").first()
    assert fetched_job is not None
    assert fetched_job.title == "Test Job 2"
    db.close()