# Laborly — Trust-Driven Service Marketplace

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Key Features](#2-key-features)
- [3. Technology Stack](#3-technology-stack)
- [4. Architecture Overview](#4-architecture-overview)
- [5. Prerequisites](#5-prerequisites)
- [6. Getting Started](#6-getting-started)
  - [6.1 Clone the Repository](#61-clone-the-repository)
  - [6.2 Environment Setup and Dependencies](#62-environment-setup-and-dependencies)
  - [6.3 Configure Environment Variables](#63-configure-environment-variables)
  - [6.4 Apply Database Migrations](#64-apply-database-migrations)
  - [6.5 Seed the Database (Optional)](#65-seed-the-database-optional)
- [7. Running the Application](#7-running-the-application)
- [8. API Documentation](#8-api-documentation)
- [9. Running Tests](#9-running-tests)
- [10. Code Quality and Linting](#10-code-quality-and-linting)
- [11. Contributing](#11-contributing)

---

## 1. Overview

Laborly is a backend platform developed with FastAPI, designed to connect clients seeking services with skilled, vetted workers.  
It offers a secure, transparent ecosystem for discovering talent, managing job engagements, and ensuring trust through verified identities (KYC) and user reviews.

The platform defines three primary roles: Clients, Workers, and Administrators, each with tailored permissions and dedicated dashboards.

### Core Objectives

- Enable clients to efficiently discover and hire trusted, verified workers.
- Establish a transparent, secure job lifecycle and review system.
- Provide administrative tools to maintain platform safety and integrity.

---

## 2. Key Features

- **Role-Based Access Control**  
  Segregated capabilities for Clients, Workers, and Admins, enforced through FastAPI dependencies.

- **Authentication and Authorization**  
  Secure email/password login with JWT tokens, optional Google OAuth2 integration, email verification, password recovery, and secured email updates.

- **Profile Management**  
  Independent profile structures for Clients and Workers. Workers manage service offerings, bios, skills, and availability.

- **KYC Verification System**  
  Mandatory ID and selfie verification for Workers, reviewed and managed by Admins.

- **Service Listings and Discovery**  
  Workers can create, update, and delete service listings; Clients can search and filter based on title and location.

- **Real-Time Messaging**  
  Thread-based messaging linked to job engagements, leveraging WebSocket technology for live communication.

- **Job Lifecycle Management**  
  Full job flow covering states like Negotiating, Accepted, Completed, Rejected, and Cancelled, with timestamped transitions and audit trails.

- **Ratings and Reviews**  
  Clients rate completed jobs and leave reviews, affecting Worker visibility and credibility.

- **Administrative Moderation**  
  Admins manage accounts (freeze, ban, unban, delete), oversee KYC submissions, and moderate user-generated reviews.

- **Security Infrastructure**  
  Features include input validation, secure file uploads to AWS S3 with MIME type enforcement, API rate limiting, JWT token blacklisting, security headers, and CORS configuration.

---

## 3. Technology Stack

| Category                  | Technology |
|:---------------------------|:-----------|
| Backend Framework          | FastAPI (Python 3.11+) |
| Database                   | PostgreSQL |
| ORM                        | SQLAlchemy (Async support via asyncpg) |
| Migrations                 | Alembic |
| Data Validation            | Pydantic, Pydantic-Settings |
| Asynchronous Libraries     | anyio, asyncpg, httpx |
| Authentication             | python-jose (JWT), passlib (hashing), Authlib (OAuth) |
| Caching/Blacklisting       | Redis (fakeredis for testing) |
| File Storage               | AWS S3 (boto3) |
| Email Delivery             | FastAPI-Mail, aiosmtplib |
| Real-Time Communication    | WebSockets |
| Code Quality               | ruff, black, mypy |
| Dependency Management      | pip or uv |
| Testing Frameworks         | pytest, pytest-asyncio, pytest-cov |
| Deployment Infrastructure  | Docker, Nginx, Certbot |

---

## 4. Architecture Overview

Laborly follows a clean, modular architecture:

- **Modules**: Each feature set (auth, client, worker, admin, job, service, messaging, review) is isolated into its own directory.
- **Component Structure**:
  - `models.py`: SQLAlchemy ORM models
  - `schemas.py`: Pydantic request and response models
  - `services.py`: Business logic layer
  - `routes.py`: FastAPI routers exposing API endpoints
- **Shared Utilities**:
  - `core/`: Authentication, config, dependencies, utilities
  - `database/`: Session handling, base models
- **Asynchronous Operations**: Full async support using `async/await` patterns throughout services and database layers.

---

## 5. Prerequisites

Before starting, ensure the following are installed:

- Python 3.11 or higher
- PostgreSQL Server
- Redis Server
- Git
- Virtual Environment Manager (`venv`, `conda`, or `uv`)
- AWS S3 Bucket and Credentials (Access Key ID, Secret Access Key, Region)
- SMTP Email Service Credentials

---

## 6. Getting Started

### 6.1 Clone the Repository

```bash
git clone https://github.com/Althub-team-48/Laborly.git
cd Laborly/backend
```

### 6.2 Environment Setup and Dependencies

**Using `uv` (recommended):**

```bash
uv venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\Activate.ps1    # Windows (PowerShell)

uv sync
```

**Using `pip`:**

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 6.3 Configure Environment Variables

Create your environment file:

```bash
cp .env.sample .env
```

Edit `.env` and ensure you configure:

- `DATABASE_URL` (using `postgresql+asyncpg://` format)
- `SECRET_KEY`
- AWS Credentials
- Email SMTP settings
- Frontend URL (`BASE_URL`)
- Allowed CORS origins

### 6.4 Apply Database Migrations

Ensure your PostgreSQL server is running, then:

```bash
alembic current   # Verify migration status
alembic upgrade head   # Apply all migrations
```

(If required, create a new migration:)

```bash
alembic revision --autogenerate -m "Initial schema setup"
```

### 6.5 Seed the Database (Optional)

Load sample data:

```bash
python seed.py
```

> **Note:** This will truncate existing data. Default seeded password: `String@123`.

---

## 7. Running the Application

Ensure PostgreSQL and Redis are active.

Start the application:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be accessible at: [http://localhost:8000](http://localhost:8000)

---

## 8. API Documentation

Access interactive documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

These tools allow direct API testing and exploration from your browser.

---

## 9. Running Tests

Ensure you have a separate test database defined via `TEST_DATABASE_URL` in `.env`.

To run the test suite:

```bash
pytest
```

To run with code coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

---

## 10. Code Quality and Linting

Maintain code quality using:

```bash
ruff check . --fix
black .
mypy app/
```

If `pre-commit` hooks are installed, these checks will run automatically before commits.

---

## 11. Contributing

We welcome contributions.  
Please refer to the contributing guidelines (`docs/contributors_guideline.md`) for:

- Development workflows
- Branching conventions
- Code style guides
- Pull request procedures

---
