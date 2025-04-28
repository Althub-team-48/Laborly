# Laborly Backend Glossary

---

## A

- **Admin:** A privileged user role responsible for platform management, KYC verification, user moderation (freeze, ban, delete), and review oversight.
- **Alembic:** Database migration tool used to version and manage changes to the PostgreSQL schema.
- **API (Application Programming Interface):** The defined methods through which different software components communicate. In Laborly, refers to FastAPI endpoints for frontend-backend interaction.
- **Async/Await:** Python keywords for asynchronous programming, enabling the server to handle multiple concurrent requests efficiently.
- **Auth Module (`app/auth/`):** Manages authentication, registration, login, password management, email verification, and OAuth integration.
- **AWS S3 (Amazon Simple Storage Service):** Cloud storage service for managing user uploads like KYC documents and profile pictures.

---

## B

- **Backend:** The server-side component built with FastAPI, handling business logic, database operations, and API interactions.
- **Base Model (`app/database/base.py`):** SQLAlchemy `DeclarativeBase` class from which all ORM models inherit.
- **Blacklist (`app/core/blacklist.py`):** Redis-based system for invalidating JWT tokens upon logout.
- **Boto3:** AWS SDK for Python, used for interactions with AWS services like S3.

---

## C

- **Client:** A user role representing individuals seeking services.
- **Client Module (`app/client/`):** Manages client profiles, favorite workers, and job history.
- **Client Profile (`ClientProfile` model):** Stores client-specific details linked to the `User` model.
- **Commit Guidelines:** Standards for writing Git commit messages for clarity and automation (e.g., Conventional Commits).
- **Configuration (`app/core/config.py`):** Loads application settings from environment variables using Pydantic Settings.
- **Conventional Commits:** A structured format for commit messages (e.g., `feat:`, `fix:`, `docs:`).
- **Core Module (`app/core/`):** Shared configurations, utilities, validators, and middleware components.
- **CORS (Cross-Origin Resource Sharing):** Security policy configured in FastAPI to restrict external domain access to the API.

---

## D

- **Database Module (`app/database/`):** Manages ORM setup, sessions, enums, and core models (`User`, `KYC`).
- **Dependencies (`app/core/dependencies.py`):** FastAPI `Depends` functions for injecting database sessions, enforcing RBAC, and pagination.
- **Docker / Docker Compose:** Containerization tools used for consistent environment setup across development and deployment.
- **Docstrings:** Inline documentation that describes the functionality of classes, methods, and modules.

---

## E

- **Email Verification:** Confirms user email addresses during registration or updates via tokenized links.
- **Endpoint:** A specific URL in the API mapped to a route handler function (e.g., `/auth/login`).
- **Enum (Enumeration):** A fixed set of named values (e.g., `UserRole`, `KYCStatus`, `JobStatus`) used for clarity and consistency.
- **ERD (Entity Relationship Diagram):** Visual diagram of the database schema showing relationships between tables.
- **Environment Variables:** Configuration keys (e.g., database URLs, API keys) loaded externally for security and flexibility.

---

## F

- **FastAPI:** High-performance Python web framework used to build the backend.
- **Favorite (`FavoriteWorker` model):** Represents a client marking a worker as a favorite.
- **Fixture (`tests/conftest.py`):** Reusable test data or setup logic provided to Pytest test cases.

---

## G

- **Git:** Version control system managing source code history.
- **`.gitignore`:** Specifies files and directories Git should not track (e.g., `.env`, `venv/`).

---

## H

- **Hashing:** Irreversible transformation of passwords (using bcrypt) for secure storage.
- **HTTPException:** FastAPI class for returning structured HTTP error responses (e.g., 401 Unauthorized, 404 Not Found).

---

## J

- **Job (`Job` model):** Represents a service task initiated by a client and performed by a worker.
- **Job Module (`app/job/`):** Manages job creation, negotiation, completion, and cancellation.
- **Job Status (`JobStatus` enum):** Represents job stages: `NEGOTIATING`, `ACCEPTED`, `COMPLETED`, `REJECTED`, `CANCELLED`.
- **JWT (JSON Web Token):** Compact, secure way of transmitting user identity and authorization claims.
- **jti (JWT ID):** Unique identifier within a JWT, used for blacklist-based logout validation.

---

## K

- **KYC (Know Your Customer):** Identity verification process requiring document and selfie submissions by workers.
- **KYC Status (`KYCStatus` enum):** Possible verification statuses: `PENDING`, `APPROVED`, `REJECTED`.

---

## L

- **Linting:** Automated analysis of source code to catch errors, style issues, and enforce standards (handled by `ruff`).
- **Logging (`app/core/logging.py`):** Centralized recording of application events for debugging and monitoring.

---

## M

- **Main (`main.py`):** FastAPI app entrypoint configuring middleware and routers.
- **Message (`Message` model):** An individual chat message sent between users.
- **Message Thread (`MessageThread` model):** Represents a chat thread between users, often linked to a job.
- **Messaging Module (`app/messaging/`):** Manages user conversations (REST + WebSocket real-time chat).
- **Middleware:** Processes requests and responses globally (e.g., security headers, session management).
- **Migration:** Versioned database schema change scripts managed by Alembic.
- **Model:** A Python class mapping database tables via SQLAlchemy ORM.
- **Module:** A distinct feature directory under `app/`, such as `auth`, `client`, `job`, etc.
- **MVP (Minimum Viable Product):** First working version with essential functionality for early users.
- **Mypy:** Static type checker used for enforcing type safety.

---

## N

- **Nginx:** Web server used as a reverse proxy and load balancer, configured in `docker-compose.yml`.

---

## O

- **OAuth2:** Authorization framework used for third-party login (e.g., Google sign-in).
- **ORM (Object-Relational Mapper):** Technique allowing database operations via Python objects.

---

## P

- **Pagination:** Dividing long lists into pages, using query parameters `skip` and `limit`.
- **Password Hashing:** See *Hashing*.
- **Password Policy:** Rules for strong passwords (enforced in `validators.py`).
- **PostgreSQL:** Relational database management system used for storing application data.
- **Pre-commit:** Tool for running code quality checks before Git commits.
- **Pre-signed URL:** Secure temporary link to private AWS S3 objects.
- **PRD (Product Requirements Document):** Specification document outlining project goals and features.
- **Profile:** Extended user information for Clients (`ClientProfile`) and Workers (`WorkerProfile`).
- **Pydantic:** Library used for data validation and serialization.
- **Pytest:** Framework for writing and running backend unit and integration tests.

---

## R

- **Rate Limiting:** Controls request frequency to prevent abuse (implemented with `SlowAPI` and Redis).
- **RBAC (Role-Based Access Control):** Restricts access based on user roles (`CLIENT`, `WORKER`, `ADMIN`).
- **Redis:** In-memory database used for rate limiting and JWT blacklisting.
- **REST (Representational State Transfer):** Design pattern for API architecture.
- **Review (`Review` model):** Client feedback about a worker after job completion.
- **Review Module (`app/review/`):** Manages creation and retrieval of worker reviews.
- **Route/Router:** FastAPI mechanism defining API endpoints.
- **Ruff:** Fast Python linter and formatter.

---

## S

- **Schema (Pydantic Schema):** Defines API request and response formats using Pydantic models.
- **Seed Script (`seed.py`):** Script for populating database with initial development data.
- **Service (Business Logic):** Core functionality inside `services.py` files.
- **Service Listing (`Service` model):** Represents services offered by workers.
- **Service Listing Module (`app/service/`):** Manages worker service offerings.
- **Session (Database):** SQLAlchemy session used for ORM operations.
- **Session (Middleware):** Starlette middleware handling OAuth session state.
- **SQLAlchemy:** Python ORM toolkit for database interaction.
- **Swagger UI:** Interactive API documentation interface provided by FastAPI.

---

## T

- **Template (`templates/`):** HTML layouts for transactional emails.
- **Tests (`tests/`):** Automated tests validating backend functionality.
- **Thread Participant (`ThreadParticipant` model):** Maps users to threads in the messaging system.
- **Token:** See *JWT*.

---

## U

- **User (`User` model):** Core model representing any registered Laborly user.
- **User Role (`UserRole` enum):** Defines roles: `CLIENT`, `WORKER`, `ADMIN`.
- **uv:** Fast package manager and virtual environment tool (alternative to `pip` and `venv`).
- **Uvicorn:** ASGI server used to run FastAPI apps.
- **UUID:** Universally Unique Identifier used as primary keys in database tables.

---

## V

- **Validation:** Process of checking incoming request data against expected formats.
- **`venv`:** Standard tool for creating isolated Python environments.

---

## W

- **WebSocket:** Real-time communication protocol used in the messaging system.
- **Wipe Script (`wipe.py`):** Script to reset the database schema and migration history.
- **Worker:** A user role offering professional services on the platform.
- **Worker Module (`app/worker/`):** Manages worker profiles, KYC submission, and job history.
- **Worker Profile (`WorkerProfile` model):** Stores skills, experience, bio, and availability for workers.

---
