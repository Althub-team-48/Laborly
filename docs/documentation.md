## **Phase 1: Planning & Requirements Gathering - Documentation**

### 1. Backend Architecture Overview

- **Monolithic Structure:**  
  The project uses a monolithic approach to simplify initial development and deployment while retaining modularity within the codebase. The backend is built with FastAPI.

- **Technology Stack:**  
  - **Framework:** FastAPI  
  - **Database:** PostgreSQL  
  - **ORM:** SQLAlchemy  
  - **Migrations:** Alembic  
  - **Authentication:** JWT-based authentication  
  - **Other Tools:** Configuration management via dotenv, logging setup, and standard API error handling

- **Module Organization:**  
  The codebase follows the folder structure provided (e.g., modules for users, jobs, reviews, admin, core configuration, database setup, and utilities).

### 2. Database Schema Documentation

- **Core Tables:**  
  - **Users:** Manages client, worker, and admin profiles with fields for names, email, phone number, password hash, role, profile picture, bio, rating, verification status, and timestamps.  
  - **Jobs:** Stores job postings with foreign key reference to the user (client) along with title, description, category, location, status, and timestamps.  
  - **Job Applications:** Captures applications made by workers to jobs, linking workers to jobs with a status field and timestamp.  
  - **Job Assignments:** Manages assignment details including client approval and worker acceptance.  
  - **Reviews:** Stores review and rating details for completed jobs.  
  - **Worker Availability:** Tracks availability and last active time of workers.  
  - **Admin Logs:** Records administrative actions for accountability.

- **Relationships:**  
  Each table includes proper foreign key relationships, ensuring data integrity and traceability across the system.

### 3. API Specifications Outline

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

### 4. Version Control & Branching Strategy

- **Adoption of GitFlow:**  
  - **Main Branch:** `main` holds production-ready code.  
  - **Development Branch:** `dev` integrates all new features and fixes before release.  
  - **Personal Branches:** `dev-*` are used for individual features or tasks.  
---