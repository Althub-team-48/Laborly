# RUNNING THIS FILE WIPES THE ENTIRE DATABASE. USE WITH CAUTION!!!
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a database engine
engine = create_engine(DATABASE_URL)

def purge_database():
    """Drops all tables and wipes the entire database."""
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE;"))
        connection.execute(text("CREATE SCHEMA public;"))
        connection.commit()

    print("✅ Database successfully purged!")

if __name__ == "__main__":
    confirm = input("⚠️ WARNING: This will DELETE ALL DATA! Type 'yes' to proceed: ")
    if confirm.lower() == "yes":
        purge_database()
    else:
        print("❌ Purge operation cancelled.")
