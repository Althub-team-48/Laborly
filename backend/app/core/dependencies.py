from ..database.config import SessionLocal

def get_db_session():
    """
    Dependency to provide a database session.
    Yields a session and ensures it is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()