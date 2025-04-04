# Contributing to Laborly Backend
---

## Table of Contents

- [Code Structure](#code-structure)
- [Getting Started](#getting-started)
- [Branching Strategy](#branching-strategy)
- [Coding Standards](#coding-standards)
- [Module Ownership](#module-ownership)
- [Pull Requests](#pull-requests)
- [Commit Guidelines](#commit-guidelines)
- [Testing](#testing)
- [Communication](#communication)

---

## Code Structure

The backend is modular and each domain (auth, client, worker, etc.) is self-contained:

```
app/
├── auth/
├── client/
├── worker/
├── admin/
├── service/
├── messaging/
├── job/
└── review/
```

Each module contains:

- `models.py` – SQLAlchemy models
- `schemas.py` – Pydantic schemas
- `routes.py` – FastAPI endpoints
- `services.py` – Business logic

---

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/laborly-backend.git
   cd laborly-backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up `.env` using `.env.example`.

5. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

---

## Branching Strategy

- `main`: production-ready code
- `dev`: active development base
- `dev-name`: personal workspace

Always branch off `dev` and submit PRs to `dev`.

---

## Coding Standards

- Keep logic out of routes; use service layer
- Add docstrings for all public classes/functions
- Use `Field(..., description="")` in all Pydantic models
- Avoid depreciated logics

---

## Module Ownership

Each module should be independently manageable. Avoid circular imports and keep all internal logic self-contained. If you require shared components, place them in:

```
app/core/       # Config, security, dependencies
app/database/   # Base models, enums, sessions
```

---

## Pull Requests

- Submit PRs to the `dev` branch
- Title format: `Completed Phase X: [desc]`, `[bugfix] Fix Y`
- Describe what what was done in a consice format

---

## Commit Guidelines

Use clear and meaningful commit messages:

---

## Testing

- Manual testing required for routes
- Use Swagger UI at `/docs`
- Automated tests coming in future phases

---