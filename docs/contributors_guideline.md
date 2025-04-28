# 🛠️ Contributing to Laborly Backend

Thank you for contributing to the Laborly backend project!  
Following these guidelines helps maintain code quality, consistency, and effective collaboration.

---

## Table of Contents

- [1. Code Structure](#1-code-structure)
- [2. Getting Started](#2-getting-started)
- [3. Branching Strategy](#3-branching-strategy)
- [4. Coding Standards](#4-coding-standards)
- [5. Code Quality & Linting](#5-code-quality--linting)
- [6. Commit Guidelines](#6-commit-guidelines)
- [7. Pull Requests](#7-pull-requests)
- [8. Testing](#8-testing)
- [9. Documentation](#9-documentation)
- [10. Module Ownership](#10-module-ownership)
- [11. Communication](#11-communication)

---

## 1. Code Structure

The backend follows a modular architecture.  
Each primary domain (e.g., `auth`, `client`, `worker`, `job`) resides under the `app/` directory.

Each module typically contains:

- `models.py` – SQLAlchemy ORM models
- `schemas.py` – Pydantic schemas for validation and serialization
- `routes.py` – FastAPI routers/endpoints
- `services.py` – Business logic layer

Shared configurations, utilities, and database setup are located in:

- `app/core/`
- `app/database/`

---

## 2. Getting Started

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/laborly-backend.git
   cd laborly-backend
   ```

2. **Set up your environment:**  
   Choose between two options to create your virtual environment and install dependencies:

   ### ➤ Option A: Using `uv` (Recommended)

   [`uv`](https://github.com/astral-sh/uv) is a fast Python dependency and environment manager.

   ```bash
   uv venv
   # Activate the environment:
   # macOS/Linux:
   source .venv/bin/activate  
   # Windows:
   .venv\Scripts\activate  

   uv lock                   # Generate lockfile (if not already)
   uv sync                   # Install all dependencies
   ```

   - To add new packages:

     ```bash
     uv add package-name
     uv sync
     ```

   > `uv` automatically updates both your `pyproject.toml` and `uv.lock`.

   ### ➤ Option B: Using `pip` and `requirements.txt`

   Traditional `pip` setup:

   ```bash
   python -m venv venv
   # Activate the environment:
   # macOS/Linux:
   source venv/bin/activate  
   # Windows:
   venv\Scripts\activate  

   pip install -r requirements.txt
   ```

   - To update dependencies manually:

     ```bash
     pip freeze > requirements.txt
     ```

3. **Configure environment variables:**

   ```bash
   cp .env.sample .env
   ```

   Update `.env` with your database URL, secret keys, AWS credentials, and email server details.

4. **Apply database migrations:**

   ```bash
   alembic upgrade head
   ```

5. **Install pre-commit hooks (optional but recommended):**

   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. **Run the development server:**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation.

---

## 3. Branching Strategy

We follow a simple Gitflow-inspired model:

- `main`: Stable production-ready code. No direct commits.
- `dev`: Active development branch, always runnable.
- `feature/<feature-name>`, `fix/<issue-number>`, or `dev-<yourname>/<short-desc>`: Feature, bugfix, or personal branches.

**Workflow:**

```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-new-feature
```

Push your changes and open a Pull Request targeting `dev`.

---

## 4. Coding Standards

- **Service Layer:** Business logic belongs inside `services.py`. Keep route handlers clean.
- **Async Programming:** Use `async/await` consistently for database and I/O operations.
- **Type Hints:** Mandatory for all functions and variables.
- **Docstrings:** Required for all public modules, classes, and functions (Google or reStructuredText style).
- **Schemas:** Use `Field(..., description="...")` inside Pydantic models and set `ConfigDict(from_attributes=True)`.
- **Environment Settings:** Access via the `settings` object, not hardcoded values.
- **Error Handling:** Raise FastAPI `HTTPException` where appropriate, and log unexpected server errors.
- **Modularity:** Maintain clear module boundaries and minimize tight coupling.

---

## 5. Code Quality & Linting

Code quality is enforced using:

- `ruff`: Linting and static analysis
- `black`: Code formatting
- `mypy`: Type checking

Run manually if needed:

```bash
ruff check . --fix
black .
mypy app/
```

Pre-commit hooks will run these checks automatically if installed.

---

## 6. Commit Guidelines

Follow the **Conventional Commits** specification:

**Format:**

```
<type>[optional scope]: <description>
```

**Common types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, whitespace
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test-related changes
- `build`: Build process or dependencies
- `ci`: CI configuration changes
- `chore`: Maintenance tasks

**Examples:**

```
feat(auth): implement JWT blacklist for logout
fix(worker): correct logic for KYC status update
docs(readme): update setup instructions for uv
```

---

## 7. Pull Requests

- **Target:** Always create PRs into `dev`.
- **PR Title:** Clear and descriptive (optionally reference related issues).
- **PR Description:** Summarize changes, motivation, and how to test.
- **Linked Issues:** Mention with `Fixes #issue-number`.
- **Passing Checks:** Ensure linting, tests, and type checks pass before merging.
- **Small and Focused:** Each PR should cover a single feature or fix.

---

## 8. Testing

- Use `pytest` and `pytest-asyncio` for testing.
- Test files mirror the `app/` structure under `tests/`.
- Shared fixtures are placed in `tests/conftest.py`.

**Run tests locally:**

```bash
pytest
```

New features and bug fixes should include corresponding tests where possible.

---

## 9. Documentation

- **Docstrings:** Ensure all classes, methods, and services are documented.
- **README Updates:** Update `README.md` if changes affect setup or workflows.
- **Swagger API Docs:** Use `Field` descriptions in schemas and `summary`/`description` in route decorators to enhance auto-generated documentation.

---

## 10. Module Ownership

Each module inside `app/` should be:

- Self-contained
- Avoid circular imports
- Shared utilities should go into `app/core/` or `app/database/`

If unsure, discuss with the team before introducing cross-module dependencies.

---

## 11. Communication

- Use the designated project management tool (e.g., Jira, Trello, GitHub Issues) for tracking.
- Communicate clearly and proactively.
- Maintain professionalism and respect during discussions and code reviews.

---
