"""
reset.py

Description:
This script resets the database by:
- Dropping and recreating the public schema
- Generating and applying Alembic migrations to reflect model changes
- Seeding the database

It supports multiple modes:
- --auto: runs purge, migration (generate + apply), and seed in sequence
- --purge-only: drops and recreates schema
- --migrate-only: generates and applies migrations
- --seed-only: runs seeding only
- --message <message>: sets the Alembic migration message

Usage:
python app/database/reset.py [--auto] [--purge-only] [--migrate-only] [--seed-only] [--message "message"]
"""

import os
import sys
import subprocess
import configparser
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime
import glob

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


def run_migration(message: str = None) -> None:
    """
    Generates a new Alembic migration only if there are model changes, and applies it.
    Auto-names the migration with a timestamp if no message is provided.
    """
    # Use timestamp-based message if none provided
    if not message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Auto migration - {timestamp}"

    # Update alembic.ini with latest DB URL
    config = configparser.ConfigParser()
    config.read(ALEMBIC_INI_PATH)
    config.set("alembic", "sqlalchemy.url", DATABASE_URL)
    with open(ALEMBIC_INI_PATH, "w") as f:
        config.write(f)

    # Set up environment
    project_root = str(BASE_DIR.resolve().parents[2])
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    os.chdir(BASE_DIR)

    # Apply existing migrations first (ensure up-to-date)
    subprocess.run(["alembic", "-c", "alembic.ini", "upgrade", "head"], env=env)

    # Get list of existing migration files before generating
    before_files = set(glob.glob(str(BASE_DIR / "migrations" / "versions" / "*.py")))

    print(f"Generating migration: {message}")
    logger.info(f"Generating migration with message: {message}")

    try:
        subprocess.run(
            ["alembic", "-c", "alembic.ini", "revision", "--autogenerate", "-m", message],
            check=True,
            env=env
        )
    except subprocess.CalledProcessError as e:
        print(f"Migration generation failed: {e}")
        logger.error(f"Migration generation failed: {e}")
        sys.exit(1)

    # Get list of migration files after generation
    after_files = set(glob.glob(str(BASE_DIR / "migrations" / "versions" / "*.py")))
    new_files = list(after_files - before_files)

    if not new_files:
        print("✅ No model changes detected. No new migration file created.")
        logger.info("No model changes detected. Skipping migration.")
        return

    # Check if generated file is empty (contains 'pass' only)
    migration_path = new_files[0]

    with open(migration_path, "r") as f:
        content = f.read()

    # Check for real schema operations
    if "op." not in content:
        print("⚠️  No schema changes detected. Skipping empty migration.")
        logger.info("Empty migration file detected.")

        try:
            # Ensure file is closed before deletion
            os.remove(migration_path)
            logger.info(f"Deleted empty migration file: {migration_path}")
        except PermissionError as e:
            logger.error(f"Could not delete empty migration file: {e}")
            print(f"❌ Could not delete empty migration file. You can remove it manually:\n{migration_path}")
        
        return

    print("✅ New migration created:", os.path.basename(new_files[0]))
    logger.info(f"New migration created: {new_files[0]}")
    actions_performed.append("Migration Generated")

    # Apply all migrations
    print("Applying migrations...")
    try:
        subprocess.run(["alembic", "-c", "alembic.ini", "upgrade", "head"], check=True, env=env)
        print("✅ Migrations applied.")
        logger.info("Migrations applied.")
        actions_performed.append("Migrations Applied")
    except subprocess.CalledProcessError as e:
        print(f"Migration apply failed: {e}")
        logger.error(f"Migration application failed: {e}")
        sys.exit(1)


def run_seeding() -> None:
    """Executes the seeding script."""
    project_root = str(BASE_DIR.resolve().parents[2])
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root

    print("Running seeder.")
    logger.info("Running database seeder.")

    try:
        subprocess.run([sys.executable, str(SEED_SCRIPT_PATH)], check=True, env=env)
        print("Seeding complete.")
        logger.info("Database seeding complete.")
        actions_performed.append("Database Seeded")
    except subprocess.CalledProcessError as e:
        print("Error occurred while running seeder.")
        logger.error(f"Seeder failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error occurred while running seeder: {e}")
        logger.error(f"Seeder failed: {e}")
        sys.exit(1)


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
            run_migration(msg_arg or "schema update")
            run_seeding()
            print_summary()
            sys.exit(0)

        if purge_only:
            purge_database()
            print_summary()
            sys.exit(0)

        if migrate_only:
            run_migration(msg_arg or "schema update")
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
            migration_message = msg_arg or input("Enter migration message (or press Enter for default): ") or "schema update"
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