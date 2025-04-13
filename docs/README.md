# Laborly Backend

Laborly is a service-based platform connecting clients and workers. This backend provides a robust API that supports user registration, authentication, job posting and tracking, worker-client communication, and administrative functions.

---

## Overview

This repository contains the FastAPI backend for Laborly. It is modular, secure, but still in development, featuring:

- JWT and OAuth2-based authentication
- Role-based access control (RBAC)
- KYC verification with document uploads
- Job lifecycle tracking (accept, complete, cancel)
- Client-to-worker reviews and ratings
- Reusable messaging system with WebSocket support
- PostgreSQL with Alembic migrations

---

## Architecture

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Alembic** - Migrations
- **PostgreSQL** - Relational database
- **Redis** - Token blacklist handling
- **Pydantic** - Validation
- **SlowAPI** - Rate limiting
- **WebSocket** - Real-time messaging

---

## Modules

### Authentication (`auth/`)
- JWT login and logout
- Google OAuth support
- Token revocation using Redis
- Role-based access enforcement

### Clients (`client/`)
- Client profile management
- Favorite worker tracking
- Job history and job detail access

### Workers (`worker/`)
- Profile and availability management
- KYC document upload and verification
- View assigned jobs and job details

### Jobs (`job/`)
- Accept, complete, or cancel jobs
- Job history retrieval
- Role-specific job filtering

### Reviews (`review/`)
- Submit and read reviews
- Average rating calculation
- Admin flagging support

### Services (`service/`)
- Worker service listing creation and updates
- Public and private service searches

### Messaging (`messaging/`)
- Reusable and scalable messaging system
- Thread-based communication (client-worker or admin-user)
- WebSocket real-time chat support
- Role-based message initiation and reply

---

## Security

- JWT token blacklisting for secure logout
- Role-based access enforcement on all endpoints
- Rate limiting to prevent abuse (`SlowAPI`)
- KYC status management with admin review
- Input validation via Pydantic

---

## Database

- PostgreSQL
- SQLAlchemy ORM
- Alembic for migrations

**Entities include:**
- `User`
- `ClientProfile`, `WorkerProfile`
- `KYC`
- `Job`
- `Review`
- `FavoriteWorker`
- `Service`
- `MessageThread`, `ThreadParticipant`, `Message`

---

## Environment Variables (`.env`)

```env
APP_NAME=Laborly
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost/laborly
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

---

## Running Locally

1. Clone the repo:
   ```bash
   git clone https://github.com/Althub-team-48/Laborly.git
   cd laborly-backend
   ```

2. Create and activate a virtual environment (optional):
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   - Create a `.env` file with the required values.

5. Run migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

---

## WebSocket Endpoint

- **URL:** `/ws/{thread_id}`
- **Auth:** JWT required
- **Purpose:** Live messaging between thread participants

---

## Rate Limiting

- `POST /messages/{worker_id}` → 5 requests/minute
- `POST /messages/{thread_id}/reply` → 10 requests/minute

---

## Logging

Logs are stored in `logs/app.log` and also printed to the console.

---

## Folder Structure

```
app/
├── auth/
├── client/
├── worker/
├── job/
├── review/
├── service/
├── messaging/
├── core/             # Config, logging, security, rate limiting
├── database/         # Models, enums, sessions, base
main.py               # App entrypoint
.env
```

---
