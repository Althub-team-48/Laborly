"""
reset.py

Description:
This script resets the database by:
- Dropping and recreating the public schema
- Running Alembic migrations
- Seeding the database

It supports multiple modes:
- --auto: runs purge, migration, and seed in sequence
- --purge-only: drops and recreates schema
- --migrate-only: runs migrations only
- --seed-only: runs seeding only
- --message <message>: sets the Alembic migration message

Usage:
python app/database/reset.py [--auto] [--purge-only] [--migrate-only] [--seed-only] [--message <message>]
"""

import os
import sys
import subprocess
import configparser
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment.")
    sys.exit(1)

print(f"Loaded DATABASE_URL: {DATABASE_URL}")

# Paths and constants
BASE_DIR = Path(__file__).resolve().parent
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
SEED_SCRIPT_PATH = BASE_DIR / "seed.py"
engine = create_engine(DATABASE_URL)

# Allow import of logger from app/utils
sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.logger import logger

# Tracks actions performed for summary
actions_performed = []


def purge_database() -> None:
    """Drops and recreates the public schema in the database."""
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE;"))
        connection.execute(text("CREATE SCHEMA public;"))
        connection.commit()

    print("Database successfully purged.")
    logger.info("Database purged.")
    actions_performed.append("Database Purged")


def run_migration(message: str = "initial migration") -> None:
    """Runs Alembic migrations, and generates one if none exist."""
    # Inject database URL into alembic.ini
    config = configparser.ConfigParser()
    config.read(ALEMBIC_INI_PATH)
    config.set("alembic", "sqlalchemy.url", DATABASE_URL)
    with open(ALEMBIC_INI_PATH, "w") as f:
        config.write(f)

    # Set up PYTHONPATH and environment for Alembic
    project_root = str(BASE_DIR.resolve().parents[2])
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    os.chdir(BASE_DIR)

    versions_dir = BASE_DIR / "migrations" / "versions"
    if not any(versions_dir.glob("*.py")):
        print("No existing migrations found. Generating initial migration.")
        logger.info("Generating initial migration.")
        subprocess.run(
            ["alembic", "-c", "alembic.ini", "revision", "--autogenerate", "-m", message],
            check=True,
            env=env
        )

    subprocess.run(["alembic", "-c", "alembic.ini", "upgrade", "head"], check=True, env=env)
    print("Migration applied.")
    logger.info("Migration applied.")
    actions_performed.append("Migration Applied")


def run_seeding() -> None:
    """Executes the seeding script."""
    project_root = str(BASE_DIR.resolve().parents[2])
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root

    print("Running seeder.")
    logger.info("Running database seeder.")
    subprocess.run([sys.executable, str(SEED_SCRIPT_PATH)], check=True, env=env)
    print("Seeding complete.")
    logger.info("Database seeding complete.")
    actions_performed.append("Database Seeded")


def print_summary() -> None:
    """Prints a summary of actions taken during the reset process."""
    print("\nSummary of Actions:")
    if actions_performed:
        for action in actions_performed:
            print(f" - {action}")
            logger.info(f"ACTION COMPLETED: {action}")
    else:
        print(" - No actions were performed.")
        logger.warning("No actions were performed during reset.")


if __name__ == "__main__":
    args = sys.argv[1:]
    auto_mode = "--auto" in args
    purge_only = "--purge-only" in args
    migrate_only = "--migrate-only" in args
    seed_only = "--seed-only" in args
    msg_arg = next((args[i + 1] for i, arg in enumerate(args) if arg == "--message" and i + 1 < len(args)), None)

    try:
        if auto_mode:
            print("Auto mode enabled.")
            logger.info("Auto mode started.")
            purge_database()
            run_migration(msg_arg or "initial migration")
            run_seeding()
            print_summary()
            sys.exit(0)

        if purge_only:
            purge_database()
            print_summary()
            sys.exit(0)

        if migrate_only:
            run_migration(msg_arg or "initial migration")
            print_summary()
            sys.exit(0)

        if seed_only:
            run_seeding()
            print_summary()
            sys.exit(0)

        # Interactive mode
        confirm = input("WARNING: This will DELETE ALL DATA. Type 'yes' to proceed: ")
        if confirm.lower() == "yes":
            purge_database()
            migration_message = msg_arg or input("Enter migration message (or press Enter for default): ") or "initial migration"
            run_migration(migration_message)

            seed = input("Do you want to seed the database now? (yes/no): ")
            if seed.lower() == "yes":
                run_seeding()
            else:
                print("Seeding skipped.")
                logger.info("Seeding skipped by user.")
        else:
            print("Operation cancelled.")
            logger.info("Reset operation cancelled by user.")

    finally:
        print_summary()
