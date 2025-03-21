"""
init_db.py

Initializes the database by creating all tables defined in the SQLAlchemy models.
Used for setting up the initial schema in the connected database.
"""

from database.config import Base, engine


def init_db() -> None:
    """
    Creates all database tables based on SQLAlchemy models.
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
