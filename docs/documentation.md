### **Laborly Project Documentation**

#### **Phase 1: Planning & Requirements Gathering - Documentation**

##### 1. Backend Architecture Overview

- **Monolithic Structure:**  
  The project uses a monolithic approach to simplify initial development and deployment while retaining modularity within the codebase. The backend is built with FastAPI.

- **Technology Stack:**  
  - **Framework:** FastAPI  
  - **Database:** PostgreSQL  
  - **ORM:** SQLAlchemy  
  - **Migrations:** Alembic  
  - **Authentication:** JWT-based authentication (to be implemented in Phase 3)  
  - **Other Tools:** Configuration management via `python-dotenv`, logging setup, and standard API error handling

- **Module Organization:**  
  The codebase follows the folder structure below:  
  ```
  Laborly/
  │── backend/                     # Backend (FastAPI)
  │   │── app/                     # Main backend app
  │   │   │── database/            # Database connection and migrations
  │   │   │   ├── __init__.py      # Package initialization
  │   │   │   ├── config.py        # DB connection settings
  │   │   │   ├── models.py        # Database models
  │   │   │   ├── seed.py          # Database seeding script
  │   │   │   ├── purge.py         # Database purge script
  │   │   │   ├── alembic.ini      # Alembic configuration
  │   │   │   ├── migrate.bat      # Migration automation script
  │   │   │   ├── migrations/      # Alembic migrations
  │   │   │       ├── __init__.py  # Package initialization
  │   │   │       ├── env.py       # Alembic environment setup
  │   │   │       ├── versions/    # Migration versions
  │   │   │── jobs/                # Job module
  │   │   │   ├── __init__.py      # Package initialization
  │   │   │   ├── routes.py        # API endpoints for jobs
  │   │   │   ├── schemas.py       # Pydantic schemas
  │   │   │   ├── service.py       # Business logic
  │   │   │── reviews/             # Review module
  │   │   │   ├── __init__.py      # Package initialization
  │   │   │   ├── routes.py        # API endpoints for reviews
  │   │   │   ├── schemas.py       # Pydantic schemas
  │   │   │   ├── service.py       # Business logic
  │   │   │── users/               # User module
  │   │   │   ├── __init__.py      # Package initialization
  │   │   │   ├── routes.py        # API endpoints for users
  │   │   │   ├── schemas.py       # Pydantic schemas
  │   │   │   ├── service.py       # Business logic
  │   │   │── core/                # Core app configurations
  │   │   │   ├── __init__.py      # Package initialization
  │   │   │   ├── config.py        # Global settings
  │   │   │   ├── dependencies.py  # Dependency injection for DB, auth, etc.
  │   │   │   ├── security.py      # Authentication/security methods
  │   │   │── utils/               # Utility functions
  │   │   │   ├── __init__.py      # Package initialization
  │   │   │   ├── email.py         # Email sending utilities
  │   │   │   ├── hash.py          # Password hashing utilities
  │   │   │   ├── logger.py        # Logging setup
  │   │   │── main.py              # FastAPI entry point
  │   │   │── run.sh               # Backend startup script
  │   │── logs/                    # Log files
  │   │   │── laborly.log          # Application logs
  │   │── tests/                   # Unit and integration tests
  │   │   ├── __init__.py          # Package initialization
  │   │   ├── test_admin.py        # Admin-related tests
  │   │   ├── test_jobs.py         # Job-related tests
  │   │   ├── test_reviews.py      # Review-related tests
  │   │   ├── test_users.py        # User-related tests
  │   │── .env                     # Environment variables
  ```

##### 2. Database Schema Documentation

- **Core Tables:**  
  - **Users:** Manages client, worker, and admin profiles with fields for `id`, `first_name`, `last_name`, `email`, `phone_number`, `password_hash`, `role` (enum: Admin, Client, Worker), `is_verified`, `last_active`, `created_at`, and `updated_at`.  
  - **Jobs:** Stores job postings with fields `id`, `client_id` (foreign key to `users.id`), `title`, `description`, `category`, `location`, `status` (enum: Pending, In Progress, Completed, Canceled), `created_at`, and `updated_at`.  
  - **Job Applications:** Captures applications with fields `id`, `job_id` (foreign key to `jobs.id`), `worker_id` (foreign key to `users.id`), `status` (enum: Pending, Accepted, Rejected), `applied_at`, and `updated_at`.  
  - **Job Assignments:** Manages assignments with fields `id`, `job_id` (foreign key to `jobs.id`), `worker_id` (foreign key to `users.id`), `assigned_at`, and `updated_at`.  
  - **Reviews:** Stores reviews with fields `id`, `job_id` (foreign key to `jobs.id`), `reviewer_id` (foreign key to `users.id`), `reviewee_id` (foreign key to `users.id`), `rating`, `comment`, and `created_at`.  
  - **Worker Availability:** Tracks worker availability with fields `id`, `worker_id` (foreign key to `users.id`), `available_from`, `available_to`, `created_at`, and `updated_at`.  
  - **System Logs:** Logs system actions with fields `id`, `user_id` (foreign key to `users.id`, nullable), `action_type` (enum: Create, Update, Delete, Login, Logout), `details`, and `created_at`.  
  - **Admin Logs:** Records administrative actions with fields `id`, `admin_id` (foreign key to `users.id`), `action_type` (enum: Create, Update, Delete, Login, Logout), `details`, and `created_at`.

- **Relationships:**  
  - `Jobs.client` relates to `Users` via `client_id`.
  - `JobApplications.job` and `JobApplications.worker` relate to `Jobs` and `Users` via `job_id` and `worker_id`.
  - `JobAssignments.job` and `JobAssignments.worker` relate to `Jobs` and `Users` via `job_id` and `worker_id`.
  - `Reviews.job`, `Reviews.reviewer`, and `Reviews.reviewee` relate to `Jobs` and `Users` via `job_id`, `reviewer_id`, and `reviewee_id`.
  - `WorkerAvailability.worker` relates to `Users` via `worker_id`.
  - `SystemLogs.user` relates to `Users` via `user_id` (nullable).
  - `AdminLogs.admin` relates to `Users` via `admin_id`.

##### 3. API Specifications Outline

- **Endpoint Categories:**  
  - **User Management:**  
    - **Endpoints:** Registration, login, profile updates, and user verification.  
  - **Job Management:**  
    - **Endpoints:** Create, retrieve, update, and delete job postings; manage job status transitions; search and filter jobs.  
  - **Job Applications & Assignments:**  
    - **Endpoints:** Apply for a job, approve or reject applications, track assignment statuses.  
  - **Reviews & Ratings:**  
    - **Endpoints:** Submit reviews/ratings and fetch reviews for a particular job or user.

- **Documentation Format:**  
  The API will be documented interactively using OpenAPI/Swagger UI, ensuring clear and consistent response formats and error handling.

##### 4. Version Control & Branching Strategy

- **Adoption of GitFlow:**  
  - **Main Branch:** `main` holds production-ready code.  
  - **Development Branch:** `dev` integrates all new features and fixes before release.  
  - **Personal Branches:** `dev-*` are used for individual features or tasks.

---

#### **Phase 2: Database Setup, Models, Migrations, Logging, and Seeding**

##### 1. Database Setup

- **PostgreSQL Configuration:**  
  - Installed PostgreSQL and created a database named `laborly`.
  - Configured the database connection in a `.env` file with the `DATABASE_URL` (e.g., `postgresql://postgres:ayokunle@localhost:5432/laborly`).

- **SQLAlchemy Setup:**  
  - Created `config.py` in `backend/app/database/` to centralize database configuration:
    - Defined `Base` using `declarative_base()` for ORM models.
    - Set up `engine` using `create_engine(DATABASE_URL)`.
    - Created `SessionLocal` using `sessionmaker` for database sessions.

##### 2. Models

- **Defined Models in `models.py`:**  
  - Implemented models as described in the database schema section, using SQLAlchemy ORM.
  - Added enums (`UserRole`, `JobStatus`, `ApplicationStatus`, `ActionType`) for type-safe field values.
  - Used `extend_existing=True` in `__table_args__` for all models to resolve `InvalidRequestError: Table is already defined` issues during Alembic migrations.

- **File: `backend/app/database/models.py`:**  
  - Models include `User`, `Job`, `SystemLog`, `AdminLog`, `WorkerAvailability`, `JobApplication`, `JobAssignment`, and `Review`.
  - Each model includes appropriate fields, relationships, and timestamps with default values using `datetime.now(timezone.utc)`.

##### 3. Migrations

- **Alembic Setup:**  
  - Initialized Alembic in `backend/app/database/` with the `migrations/` directory.
  - Moved `alembic.ini` to `backend/app/database/` and updated `script_location = migrations`.
  - Customized `migrations/env.py` to:
    - Load the `DATABASE_URL` from the `.env` file using `python-dotenv`.
    - Import models explicitly (`User`, `Job`, `SystemLog`, `AdminLog`, `WorkerAvailability`, `JobApplication`, `JobAssignment`, `Review`) for autogeneration.
    - Set `target_metadata = Base.metadata`.

- **Migration Script:**  
  - Created `migrate.bat` in `backend/app/database/` to automate migration generation and application:
    ```bat
    @echo off
    if "%~1"=="" (
        echo Usage: migrate.bat "migration message"
        exit /b 1
    )
    rmdir /S /Q migrations\versions
    mkdir migrations\versions
    alembic -c alembic.ini revision --autogenerate -m "%~1"
    alembic -c alembic.ini upgrade head
    echo Migration applied successfully.
    ```
  - The script clears the `versions/` directory before generating a new migration to ensure a clean migration history.

- **Migration Execution:**  
  - Successfully ran migrations to create all tables in the `laborly` database.
  - Verified table creation using pgAdmin 4 with `\dt`.

##### 4. Logging System

- **File-Based Logging:**  
  - Implemented in `logger.py` in `backend/app/utils/`:
    - Configured a `RotatingFileHandler` to log to `logs/laborly.log` with a max size of 1MB and 5 backup files.
    - Log format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.

- **Database Logging:**  
  - Added `log_system_action` and `log_admin_action` functions to log actions to the `system_logs` and `admin_logs` tables.
  - Updated to use the `ActionType` enum for the `action_type` parameter.
  - Logs are written both to the file and the database for all major actions (e.g., user creation, job creation).

- **File: `backend/app/utils/logger.py`:**  
  - Ensures proper error handling and logging of failures if database logging fails.

##### 5. Database Seeding

- **Seeder Script:**  
  - Created `seed.py` in `backend/app/database/` to populate the database with test data:
    - **Admin User:** 1 admin user (`admin@laborly.com`).
    - **Client Users:** 10 clients with random names, emails (`client1@laborly.com` to `client10@laborly.com`), and phone numbers.
    - **Worker Users:** 5 workers with random names, emails (`worker1@laborly.com` to `worker5@laborly.com`), and phone numbers.
    - **Worker Availability:** Each worker has 1-3 availability slots with random future dates.
    - **Jobs:** 20 jobs with random titles, descriptions, categories, locations, and statuses, assigned to random clients.
    - **Job Applications:** 10 applications for random jobs by random workers.
    - **Job Assignments:** 5 assignments for jobs in "Completed" or "In Progress" status.
    - **Reviews:** Reviews for all completed jobs with random ratings and comments.

- **Logging Integration:**  
  - Integrated logging into the seeder script to log user creation, job creation, and other actions to both the file and database.

- **Execution:**  
  - Fixed module import issues by ensuring the `database` package is correctly structured with an `__init__.py` file.
  - Ran the seeder script from `backend/app/` with `python -m database.seed`.
  - Verified data in pgAdmin 4 across all tables.

##### 6. Database Purge Script

- **Purge Script:**  
  - Created `purge.py` in `backend/app/database/` to clear all data from the database for testing purposes.
  - Includes a confirmation prompt to prevent accidental data loss.
  - Drops all tables and recreates them using `Base.metadata.drop_all()` and `Base.metadata.create_all()`.

##### 7. Troubleshooting and Fixes

- **Alembic Issues:**  
  - Resolved `No config file 'alembic.ini' found` by adding `-c alembic.ini` to migration commands.
  - Fixed `Path doesn't exist: migrations` by correcting the `script_location` in `alembic.ini` and removing inline comments.
  - Addressed `Table 'admin_logs' is already defined` errors by adding `extend_existing=True` to all models.

- **ModuleNotFoundError:**  
  - Fixed `ModuleNotFoundError: No module named 'database'` by running scripts from the correct directory (`backend/app/`) and ensuring the `database` package is properly structured.

##### 8. Verification

- **Database Verification:**  
  - Used pgAdmin 4 to verify all tables and seeded data:
    - `SELECT * FROM users;`
    - `SELECT * FROM jobs;`
    - `SELECT * FROM job_applications;`
    - `SELECT * FROM job_assignments;`
    - `SELECT * FROM reviews;`
    - `SELECT * FROM worker_availability;`
    - `SELECT * FROM admin_logs;`
    - `SELECT * FROM system_logs;`

- **Log Verification:**  
  - Checked `logs/laborly.log` for file-based logs of all actions.
  - Verified database logs in `admin_logs` and `system_logs` tables.

---

### **Phase 3: Core API Development**

#### **Overview**
Phase 3 focused on building the core API functionality using FastAPI, integrating user management, job management, job applications, worker availability, and logging. We enhanced the API with search/filtering, availability integration, and polished it with consistent error handling and improved documentation.

#### **1. User Management**
- **Endpoints Implemented** (`users/routes.py`):
  - `POST /users/register`: Registers new users with role-based validation (client, worker, admin).
  - `POST /users/login` (JSON & form): Authenticates users, returning JWT tokens.
  - `PUT /users/me`: Updates authenticated user’s profile.
  - Admin-only: `GET /users/list`, `GET /users/find/{user_id}`, `DELETE /users/delete/{user_id}`.
- **Authentication** (`core/security.py`, `core/dependencies.py`):
  - Implemented JWT-based authentication with `create_access_token` and `get_current_user`.
  - Added role-based access control (RBAC) via `get_admin_user` dependency.
- **Service Layer** (`users/service.py`):
  - Handles user CRUD operations, password hashing (`utils/hash.py`), and authentication logic.

#### **2. Job Management**
- **Endpoints Implemented** (`jobs/routes.py`):
  - `POST /jobs/create`: Creates jobs (clients/admins only).
  - `GET /jobs/list`: Lists jobs based on role (clients: own jobs, workers: assigned, admins: all).
  - `GET /jobs/find/{job_id}`: Retrieves job details (role-restricted).
  - `PUT /jobs/update/{job_id}`: Updates jobs (clients/admins only).
  - `DELETE /jobs/delete/{job_id}`: Deletes jobs (clients/admins only).
- **Service Layer** (`jobs/service.py`):
  - Manages job CRUD with lifecycle transitions (e.g., `PENDING` → `IN_PROGRESS` on assignment).
- **Schema Enhancements** (`jobs/schemas.py`):
  - Added `start_time` and `end_time` with timezone-aware validation.

#### **3. Job Applications & Assignments**
- **Endpoints Implemented** (`jobs/routes.py`):
  - `POST /jobs/apply/{job_id}`: Workers apply to jobs.
  - `GET /jobs/applications/{job_id}`: Lists applications (clients/admins only).
  - `PUT /{job_id}/applications/{application_id}`: Approves/rejects applications, assigns workers on acceptance.
- **Service Layer** (`jobs/service.py`):
  - Ensures no duplicate applications, updates job status on acceptance.
- **Schema** (`jobs/schemas.py`):
  - Defined `JobApplicationCreate`, `JobApplicationUpdate`, `JobApplicationOut` for application workflows.

#### **4. Worker Availability System**
- **Endpoints Implemented** (`workers/routes.py`):
  - `POST /api/workers/availability/`: Creates availability slots (workers only).
  - `GET /api/workers/availability/me`: Lists worker’s slots.
  - `GET /api/workers/availability/{availability_id}`: Retrieves specific slot (admins or owner).
  - `PUT /api/workers/availability/{availability_id}`: Updates slots (workers only).
  - `DELETE /api/workers/availability/{availability_id}`: Deletes slots (workers only).
- **Service Layer** (`workers/service.py`):
  - CRUD operations for availability, restricted to worker ownership or admin access.
- **Integration**:
  - Updated `apply_for_job` in `jobs/service.py` to check worker availability against job `start_time`/`end_time`.
- **Schema Enhancements** (`workers/schemas.py`):
  - Added timezone-aware `start_time`/`end_time` validation, ensured `end_time > start_time`.

#### **5. Logging Implementation**
- **Enhanced Logging**:
  - File-based logs (`utils/logger.py`) capture all API actions (e.g., job creation, user login).
  - Database logs (`system_logs`, `admin_logs`) record CRUD and auth events via `log_system_action`/`log_admin_action`.
- **Middleware** (`utils/middleware.py`):
  - Added `LoggingMiddleware` to log request/response details in `main.py`.

#### **6. Job Search and Filtering**
- **Endpoint Update** (`jobs/routes.py`):
  - Enhanced `GET /jobs/list` with optional `status` and `title` query params for filtering.
- **Service Logic** (`jobs/service.py`):
  - Added filtering logic with SQLAlchemy `ilike` for titles and enum validation for status.

#### **7. Polish and Documentation**
- **Error Handling**:
  - Introduced `APIError` (`core/exceptions.py`) for consistent `{"error": "message"}` responses across all endpoints.
- **Schema Polish** (`jobs/schemas.py`, `users/schemas.py`, `workers/schemas.py`):
  - Added field validators: timezone-aware datetimes, `end_time > start_time`, enum normalization, phone number regex.
- **Route Polish**:
  - Added `response_model` and `responses` metadata to all endpoints for Swagger clarity.
  - Improved docstrings with role restrictions and behavior details.
- **Migration Management**:
  - Updated `reset.py` to purge, apply existing migrations, generate new ones, and seed, ensuring schema sync.

#### **8. Database Updates**
- **Model Changes** (`database/models.py`):
  - Added `start_time` and `end_time` to `Job` with migrations applied via Alembic.
- **Seeder Updates** (`database/seed.py`):
  - Included `start_time`/`end_time` in job data for testing availability integration.

#### **9. Tools and Scripts**
- **Reset Script** (`database/reset.py`):
  - Enhanced to apply existing migrations, autogenerate new ones, and clean up empty migrations with timestamped names.

#### **Verification**
- **API Testing**:
  - Tested endpoints manually here: [(http://localhost:8000/docs)]
- **Logs**: Verified file (`logs/laborly.log`) and database logs for all actions.
- **Swagger**: Confirmed enhanced docs at `/docs` with error examples.

---

### **Phase 4: Reviews & Ratings System**

#### **Overview**
Phase 4 focused on implementing the reviews and ratings system, enabling clients and workers to rate each other after job completion. This phase introduced a star-based rating system (1-5), stored average ratings per user, and provided admin controls for managing reviews, aligning with the PRD’s trust-building goals (Section 4.4).

#### **1. Database Updates**
- **Model Additions** (`database/models.py`):
  - Added `Review` model with fields: `id`, `job_id` (FK to `jobs.id`), `reviewer_id` (FK to `users.id`), `reviewee_id` (FK to `users.id`), `rating` (Integer, 1-5), `created_at` (timezone-aware).
  - Updated `User` model with `average_rating` (Float, default 0.0, nullable) to store dynamic averages.
  - Established relationships: `User.reviews_written` and `User.reviews_received` linking to `Review` via `reviewer_id` and `reviewee_id`.
- **Migration**:
  - Used `migrate.bat` to autogenerate and apply a migration adding the `reviews` table and `average_rating` column to `users`.

#### **2. Reviews & Ratings Implementation**
- **New Module** (`reviews/`):
  - Created `reviews/routes.py`, `reviews/schemas.py`, and `reviews/service.py` for review functionality.
- **Endpoints Implemented** (`reviews/routes.py`):
  - `POST /api/reviews/`: Submits a review for a completed job (clients/workers only, role-restricted).
  - `GET /api/reviews/job/{job_id}`: Retrieves reviews for a job (client/worker/admin access).
  - `GET /api/reviews/user/{user_id}`: Fetches reviews where a user is the reviewee, with filters (`rating`, `role`, `date_from`, `date_to`) (self/admin access).
  - `PUT /api/reviews/{review_id}`: Updates a review (admin-only).
  - `PATCH /api/reviews/{review_id}`: Partially updates a review (admin-only).
  - `DELETE /api/reviews/{review_id}`: Deletes a review (admin-only, returns 204 No Content).
- **Service Layer** (`reviews/service.py`):
  - `create_review`: Validates job completion, prevents duplicates, assigns `reviewee_id` based on job roles, updates `average_rating`.
  - `update_average_rating`: Recalculates and stores a user’s average rating (rounded to 1 decimal) after review creation, update, or deletion.
  - `get_reviews_by_job` and `get_reviews_by_user`: Fetch reviews with filtering logic.
  - `update_review` and `delete_review`: Admin-only operations with `average_rating` recalculation.
- **Schema** (`reviews/schemas.py`):
  - Defined `ReviewCreate` (input validation for `rating` 1-5), `ReviewUpdate` (optional fields), `ReviewOut` (output with nested `JobOut`, `UserOut`), and `ReviewList` (list wrapper).

#### **3. Business Logic**
- **Review Submission**:
  - Restricted to completed jobs (`Job.status == COMPLETED`).
  - Clients review workers, workers review clients; validated via `job.client_id` and `job.worker_id`.
  - Prevents duplicate reviews per job per reviewer.
- **Average Rating**:
  - Dynamically updated on review creation, update, or deletion using SQLAlchemy’s `func.avg`.
- **Access Control**:
  - `POST`: Authenticated users tied to the job.
  - `GET /job/{job_id}`: Job client, worker, or admin.
  - `GET /user/{user_id}`: Self or admin only (privacy-first).
  - `PUT`, `PATCH`, `DELETE`: Admin-only via `get_admin_user`.

#### **4. Integration**
- **Router Registration** (`main.py`):
  - Added `reviews_router` to the FastAPI app.
- **Logging**:
  - Integrated `log_system_action` for review creation, updates, and deletions; file-based logs via `logger`.
- **Seeder Updates** (`database/seed.py`):
  - Added reviews for completed jobs (client → worker, worker → client) with random ratings (1-5).
  - Calculated initial `average_rating` for seeded users.

#### **5. Polish and Documentation**
- **Error Handling**:
  - Extended `APIError` usage for review-specific errors (e.g., “Reviews can only be submitted for completed jobs”).
- **Schema Polish**:
  - Added `field_validator` for `rating` (1-5 range) in `ReviewCreate` and `ReviewUpdate`.
- **Route Polish**:
  - Included `response_model` (`ReviewOut`, `ReviewList`) and `responses` metadata for all endpoints.
  - Detailed docstrings with access restrictions and behavior.
- **Swagger**:
  - Enhanced interactive docs at `/docs` with review endpoints and error examples.

#### **Verification**
- **API Testing**:
  - Tested endpoints via Swagger (`http://localhost:8000/docs`):
    - Created reviews for completed jobs, verified `average_rating` updates.
    - Retrieved job/user reviews with filters.
    - Updated/deleted reviews as admin, confirmed rating recalculation.
- **Database**:
  - Verified `reviews` table and `users.average_rating` via pgAdmin 4 (`SELECT * FROM reviews;`, `SELECT id, average_rating FROM users;`).
- **Logs**:
  - Checked `laborly.log` and `system_logs` for review actions.

---