import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, User
from database.config import get_db

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for testing
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_user(test_db):
    db = TestingSessionLocal()
    user = User(
        first_name="Test",
        last_name="User",
        email="test@laborly.com",
        password_hash="test_hash",
        role="Client",
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    assert user.id is not None
    assert user.email == "test@laborly.com"
    db.close()

def test_read_user(test_db):
    db = TestingSessionLocal()
    user = User(
        first_name="Test",
        last_name="User",
        email="test2@laborly.com",
        password_hash="test_hash",
        role="Client",
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    fetched_user = db.query(User).filter(User.email == "test2@laborly.com").first()
    assert fetched_user is not None
    assert fetched_user.email == "test2@laborly.com"
    db.close()