from database.config import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

# Dependency to inject the database session into routes
def get_db_session(db: Session = Depends(get_db)):
    return db