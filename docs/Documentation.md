# 🚀 Laborly Backend Project Documentation

A detailed overview of the Laborly backend's development process, architecture, and implemented features.

---

## Table of Contents

- [✅ Phase 1: Project Initialization & Structure](#-phase-1-project-initialization--structure)
- [✅ Phase 2: Core Database Models & Enums](#-phase-2-core-database-models--enums)
- [✅ Phase 3: Authentication & Authorization](#-phase-3-authentication--authorization)
- [✅ Phases 4–10: Module Implementation](#-phases-4–10-module-implementation)
- [✅ Phase 11: Security, Compliance & Core Enhancements](#-phase-11-security-compliance--core-enhancements)
- [✅ Phase 12: Async Architecture & Seeding](#-phase-12-async-architecture--seeding)
- [✅ Phase 13: Code Quality Integration](#-phase-13-code-quality-integration)
- [🧪 Testing Overview](#-testing-overview)

---

## ✅ Phase 1: Project Initialization & Structure

### 🛠 Setup Steps

- Initialized FastAPI project with Python 3.11+.
- Set up asynchronous operation with `uvicorn` and `anyio`.
- Created and activated a Python virtual environment (`venv` / `.venv`).
- Initialized Git for version control.

### 📦 Initial Dependencies Installed

- `fastapi`, `uvicorn`
- `sqlalchemy[asyncio]`, `asyncpg`
- `alembic`
- `pydantic`, `pydantic-settings`, `python-dotenv`
- `email-validator`
- `psycopg2-binary` (for synchronous scripts like seeding)

### 📁 Folder Structure

```
backend/
├── main.py
├── app/
│   ├── core/
│   ├── database/
│   ├── auth/
│   ├── admin/
│   ├── client/
│   ├── worker/
│   ├── service/
│   ├── job/
│   ├── messaging/
│   └── review/
├── alembic/
├── logs/
├── templates/
├── tests/
├── .env / .env.sample
└── requirements.txt
```

### 🔑 Configuration & Logging

- Environment settings via `.env`, loaded with `pydantic-settings`.
- Centralized structured logging (`logs/app.log`, `logs/error.log`) through `app/core/logging.py`.

### 🧱 Database & Migrations

- Async SQLAlchemy setup (`app/database/session.py`).
- Alembic configured for async engines.
- Standard migration commands:

```bash
alembic revision --autogenerate -m "Initial changes"
alembic upgrade head
```

---

## ✅ Phase 2: Core Database Models & Enums

### 📌 Shared Enums (`app/database/enums.py`)

- `UserRole`: CLIENT | WORKER | ADMIN
- `KYCStatus`: PENDING | APPROVED | REJECTED
- `JobStatus`: NEGOTIATING | ACCEPTED | COMPLETED | FINALIZED | CANCELLED | REJECTED

### 👤 Core Models (`app/database/models.py`)

- **User:** Main user table, linked to KYC, Profiles, Jobs, Reviews, Messaging.
- **KYC:** Identity verification storage.

### 🔗 Module-Specific Models

- **ClientProfile** / **FavoriteWorker**
- **WorkerProfile**
- **Service**
- **Job**
- **MessageThread**, **ThreadParticipant**, **Message**
- **Review**

### 🗺 ERD (Entity Relationship Diagram)

- Designed to map Users, Profiles, KYC, Services, Jobs, Messages, Favorites, Reviews.

---

## ✅ Phase 3: Authentication & Authorization

### 🔐 Authentication Flows

- **Signup:** Creates users, hashes passwords, sends verification emails.
- **Email Verification:** Validates user emails via token.
- **Login:** Supports Email/Password and Google OAuth2.
- **Logout:** Secure logout via JWT blacklisting.

### 🔑 Token Management

- Access Tokens: JWTs with user ID, role, expiration, and unique JTI.
- Verification Tokens: Used for email confirmation and password resets.

### 🔑 Password & Email Security

- **Password Reset:** Time-limited reset flow.
- **Email Update:** Secure new-email confirmation process.
- **Password Validation:** Enforced strong password rules.

### 🌐 Google OAuth2 Support

- OAuth2 flow implemented with FastAPI.
- State management for Client/Worker roles.
- New users created automatically after Google authentication.

### 🔐 Role-Based Access Control (RBAC)

- Endpoint access based on user role via dependency injection.

---

## ✅ Phases 4–10: Module Implementation

Each module includes Models, Schemas, Services, and Routes.

### 📦 Key Functionalities:

- **Client:** Favorites management, job history.
- **Worker:** KYC submission, availability toggle, service listing.
- **Admin:** User moderation, KYC approvals, review moderation.
- **Service:** Public search and listing management.
- **Messaging:** Real-time chat (WebSockets) + REST messaging.
- **Job:** Lifecycle management (Negotiate → Accept → Complete).
- **Review:** Review and rating system post-job completion.

---

## ✅ Phase 11: Security, Compliance & Core Enhancements

### ⏱ Rate Limiting

- `slowapi` used for protecting critical endpoints.

### 🛡 Security Headers

- Middleware adds safe headers like `X-Frame-Options: DENY`.

### ↔️ CORS Configuration

- Dynamically reads allowed origins from environment settings.

### 📄 File Upload Security

- MIME type validation during uploads.
- UUID-based file naming.
- Secure pre-signed URL generation for private file access.

### 📋 Pagination Standardization

- Generic `PaginatedResponse` schema for list APIs.

### ↩️ JWT Logout (Blacklist)

- Redis-based token blacklisting upon logout.
- JTI check enforced at authentication middleware.

---

## ✅ Phase 12: Async Architecture & Seeding

### ⚡ Full Async Refactor

- Database access and services use async/await.
- Testing updated with `pytest-asyncio` and `httpx.AsyncClient`.

### 🌱 Database Seeding

- `seed.py` script generates realistic fake data:
  - Admins, Clients, Workers
  - Services, Jobs, Threads, Messages, Reviews
- Nigerian locations used in Faker data.

### 🗑 Database Wipe Utility

- `wipe.py` script drops the database and clears Alembic versions.

---

## ✅ Phase 13: Code Quality Integration

### 🛠 Pre-commit Setup

- **ruff:** Linter and formatter.
- **black:** Code auto-formatting.
- **mypy:** Static type checking.

- Pre-commit hooks ensure checks run before each commit.

---

## 🧪 Testing Overview

- `pytest` configured with `pytest-asyncio`.
- Tests mirror `app/` folder structure.
- `conftest.py` defines fixtures for authentication, database session, and dummy data.
- **Status:**  
  Test scaffolding exists, but many test functions are placeholders or incomplete. Additional implementation needed for full coverage.

---
