## Laborly Backend MVP Roadmap (Developer Guide)
---

## 1. Backend Project Setup & Folder Structure
- Scaffold the project using FastAPI.
- Set up PostgreSQL and SQLAlchemy ORM.
- Create `.env` file and configure environment variables.
- Enable CORS for frontend integration.
- Set up project structure:
  - `client/`, `worker/`, `admin/`, `auth/`, `job/`, `messaging/`, `review/`, `core/`, `database/`
  - Each module should contain: `models.py`, `schemas.py`, `services.py`, `routes.py`
- Set up Alembic for database migrations.
- Configure logging system.

## 2. Core Database Models
- Define shared models in the `database/` module:
  - `User` model with role (`client`, `worker`, `admin`)
  - `KYC` model
  - Shared enums/constants for status tracking
- Configure Alembic migrations
- Create ERD for Database models

## 3. Authentication Module (`auth/`)
- JWT-based email/password login and signup
- Google OAuth login (optional)
- Password hashing and validation
- Role-based token generation and decoding
- Dependency for role-based access control (RBAC):
  - Use FastAPI dependency injections to restrict access based on user roles.
  - Each module will group its routes and enforce RBAC at the router level.
  - Example: Only users with role `admin` can access routes in `admin/routes.py`, only `worker` users can manage services, and only `client` users can initiate messages and submit reviews.
  - Reusable dependencies should be used to keep enforcement centralized and consistent.
  - Use FastAPI dependency injections to restrict access based on user roles.
  - Each module will group its routes and enforce RBAC at the router level.
  - Example: Only users with role `admin` can access routes in `admin/routes.py`, only `worker` users can manage services, and only `client` users can initiate messages and submit reviews.
  - Reusable dependencies (e.g., `get_current_user_with_role`) should be used to keep enforcement centralized and consistent.

## 4. Client Module (`client/`)
- `ClientProfile` model and schema
- Services:
  - Profile retrieval and update service
  - Favorites management (add/remove/get)
  - Job history query service
- Endpoints for:
  - `GET /client/profile` - Retrieve own client profile
  - `PUT /client/profile` - Update client profile info
  - `GET /client/favorites` - List all favorited workers
  - `POST /client/favorites/{worker_id}` - Add a worker to favorites
  - `DELETE /client/favorites/{worker_id}` - Remove a worker from favorites
  - `GET /client/jobs` - View all current and past jobs
  - `GET /client/jobs/{job_id}` - View a specific job detail

## 5. Worker Module (`worker/`)
- `WorkerProfile` model and schema
- Services:
  - Worker profile management
  - Availability toggle logic
  - KYC submission handling
  - Assigned job lookup
- Endpoints for:
  - `GET /worker/profile` - Retrieve own worker profile
  - `PUT /worker/profile` - Update worker profile info
  - `PUT /worker/availability` - Toggle availability status
  - `GET /worker/kyc` - View current KYC status
  - `POST /worker/kyc` - Submit or resubmit KYC documents
  - `GET /worker/jobs` - View all assigned or completed jobs
  - `GET /worker/jobs/{job_id}` - View job details

## 6. Admin Module (`admin/`)
- Services:
  - KYC approval/rejection handler
  - Account freeze/ban/unban actions
  - Review moderation logic
- Endpoints for:
  - `GET /admin/kyc/pending` - List all pending KYC submissions
  - `PUT /admin/kyc/{user_id}/approve` - Approve KYC for a user
  - `PUT /admin/kyc/{user_id}/reject` - Reject KYC for a user
  - `PUT /admin/users/{user_id}/freeze` - Temporarily disable a user
  - `PUT /admin/users/{user_id}/unfreeze` - Re-enable a frozen user
  - `PUT /admin/users/{user_id}/ban` - Permanently disable a user
  - `PUT /admin/users/{user_id}/unban` - Lift a user ban
  - `DELETE /admin/users/{user_id}` - Process user deletion request
  - `GET /admin/reviews/flagged` - List flagged/inappropriate reviews
  - `DELETE /admin/reviews/{review_id}` - Remove inappropriate review

## 7. Service Listing Module (`service/`)
- Services:
  - Create/update/delete worker service listings
  - Filter/search worker services based on criteria
- Endpoints for:
- Endpoints for:
  - `POST /services` - Create a new service (worker only)
  - `PUT /services/{service_id}` - Update a worker's service
  - `DELETE /services/{service_id}` - Remove a service
  - `GET /services/my` - List services created by the current worker
  - `GET /services/search` - Search/filter workers by service type, rating, location

## 8. Messaging Module (`messaging/`)
- Services:
  - Message thread initiation
  - Message reply logic
  - Thread history retrieval
- Endpoints for:
- Endpoints for:
  - `POST /messages/{worker_id}` - Client initiates a message thread
  - `POST /messages/{thread_id}/reply` - Worker replies to an ongoing thread
  - `GET /messages/threads` - Get all threads related to current user
  - `GET /messages/threads/{thread_id}` - Get full conversation history

## 9. Job Module (`job/`)
- Services:
  - Job acceptance and creation logic
  - Completion and cancellation services
  - Job history and detail retrieval
- Endpoints for:
- Endpoints for:
  - `POST /jobs/{thread_id}/accept` - Accept a job offer (creates job entry)
  - `PUT /jobs/{job_id}/complete` - Mark job as completed (client or worker)
  - `PUT /jobs/{job_id}/cancel` - Cancel job with reason
  - `GET /jobs` - View all jobs involving current user
  - `GET /jobs/{job_id}` - View job details

## 10. Review Module (`review/`)
- Services:
  - Review submission and validation
  - Rating calculation and caching
  - Review filtering and retrieval
- Endpoints for:
- Endpoints for:
  - `POST /reviews/{job_id}` - Submit a review (client only)
  - `GET /reviews/worker/{worker_id}` - Fetch all reviews for a worker
  - `GET /reviews/my` - Get all reviews submitted by the current client
  - Average rating is updated and cached with every new review

## 11. Security & Compliance (`core/`)
- Validate all incoming request data using Pydantic schemas in their respective modules. Avoid bypassing these validation layers.
- Secure JWT handling including token expiration, refresh handling, and blacklist management (if implemented).
- Sanitize file uploads (e.g., KYC documents, profile pictures) to prevent malicious content.
- Apply rate limiting to protect against brute-force attacks and abuse.
- Implement structured logging for security-relevant actions such as login attempts, role changes, and admin actions.

### RBAC Utility (Reusable Role Enforcement)
- Define a reusable dependency function that checks if the current user has the required role.
- Use this function across modules to enforce that only authorized roles (e.g., `admin`, `client`, or `worker`) can access certain routes.
- This ensures consistent and secure role-based access control across the application. that checks if the current user has the required role. This function will be used in each module's routes to enforce access control, ensuring only users with the correct role (e.g., `admin`, `client`, or `worker`) can access specific endpoints.

## 12. Testing & Validation
- Unit tests for each module
- Integration tests simulating user flows
- Test all major failure paths
- Reusable test fixtures per module

## 13. API Documentation
- OpenAPI docs via FastAPI
- Add request/response examples for frontend integration
- Include authentication and role access requirements per endpoint
- Group documentation by module

## 14. Deployment Preparation
- Dockerize each service (single container for now)
- Set up `.env.staging` and `.env.production`
- Seed DB with initial admin and test users
- Health check and readiness probes

## 15. CI/CD Pipeline & Staging
- Set up GitHub Actions or equivalent
- Run tests and build image on push
- Deploy to staging server
- Enable logs and error reporting

## 16. Launch Readiness & Handoff
- Finalize staging tests and migrate to production
- Provide internal dev docs:
  - How to manage users
  - How to deploy and monitor
  - Admin moderation guide
- Confirm logging and alerts are functional in production
