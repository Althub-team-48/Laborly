"""
[users] service.py

Handles all user-related business logic:
- Create, read, update, delete users
- Authenticate users
- Logs user actions for audit purposes
"""

from typing import List

from sqlalchemy.orm import Session

from database.models import User, ActionType
from users.schemas import UserCreate, UserUpdate, UserOut
from core.security import get_password_hash, verify_password
from utils.logger import logger, log_system_action


class UserService:

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> UserOut:
        """
        Registers a new user.
        Ensures unique email, hashes password, logs creation.
        """
        try:
            if db.query(User).filter(User.email == user.email).first():
                raise ValueError("Email already registered")

            hashed_password = get_password_hash(user.password)
            db_user = User(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone_number=user.phone_number,
                password_hash=hashed_password,
                role=user.role,
                is_verified=False,
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            log_system_action(db, db_user.id, ActionType.CREATE, f"User {db_user.email} registered")
            logger.info(f"User created: {db_user.email}")
            return UserOut.model_validate(db_user)

        except Exception as e:
            logger.error(f"Error creating user {user.email}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> UserOut:
        """
        Fetches a user by ID.
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")

            logger.info(f"Retrieved user: {user.email}")
            return UserOut.model_validate(user)

        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}")
            raise

    @staticmethod
    def get_all_users(db: Session) -> List[UserOut]:
        """
        Returns a list of all users in the system.
        """
        try:
            users = db.query(User).all()
            logger.info(f"Retrieved {len(users)} users")
            return [UserOut.model_validate(user) for user in users]

        except Exception as e:
            logger.error(f"Error retrieving all users: {str(e)}")
            raise

    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> UserOut:
        """
        Updates user details.
        Allows partial updates and logs the update action.
        """
        try:
            db_user = db.query(User).filter(User.id == user_id).first()
            if not db_user:
                raise ValueError("User not found")

            update_data = user_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_user, key, value)

            db.commit()
            db.refresh(db_user)

            log_system_action(db, db_user.id, ActionType.UPDATE, f"User {db_user.email} updated")
            logger.info(f"User updated: {db_user.email}")
            return UserOut.model_validate(db_user)

        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def delete_user(db: Session, user_id: int) -> None:
        """
        Deletes a user by ID and logs the action.
        """
        try:
            db_user = db.query(User).filter(User.id == user_id).first()
            if not db_user:
                raise ValueError("User not found")

            db.delete(db_user)
            db.commit()

            log_system_action(db, user_id, ActionType.DELETE, f"User {db_user.email} deleted")
            logger.info(f"User deleted: {db_user.email}")

        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> UserOut:
        """
        Authenticates a user by email and password.
        Logs successful login attempts.
        """
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user or not verify_password(password, user.password_hash):
                raise ValueError("Invalid email or password")

            log_system_action(db, user.id, ActionType.LOGIN, f"User {user.email} logged in")
            logger.info(f"User authenticated: {user.email}")
            return UserOut.model_validate(user)

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {str(e)}")
            raise
