# 🚀 Laborly Backend

Laborly is a modular FastAPI-based backend for a job-matching platform that connects clients with verified workers.

---

## ✅ Prerequisites

Ensure the following are installed and available:

- **Python 3.11+**
- **PostgreSQL** (running and accessible)
- **Redis** (running locally on port `6379`)
- **Git**
- **Virtual Environment** (`venv` or equivalent)
- **[uv (optional)](https://github.com/astral-sh/uv)** – fast dependency & virtual environment manager

---

## ⚙️ Project Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Althub-team-48/Laborly.git
cd laborly-backend
```

---

### 2. Set Up the Environment

Choose **either** pip **or** uv as your environment manager:

#### ➤ Option A: Using `uv` (recommended)

```bash
uv venv                   # Create .venv automatically
# Activate the virtual environment:
# macOS/Linux:
source .venv/bin/activate  
# Windows:
.venv\Scripts\activate  
uv lock                   # Generate uv.lock from pyproject.toml
uv sync                   # Install dependencies from uv.lock
 
```

To **add** a new package (and update both `pyproject.toml` _and_ `uv.lock`):

```bash
uv add httpx               # Adds httpx to [tool.uv.dependencies], updates uv.lock
uv sync                    # Installs the newly added package
```

---

#### ➤ Option B: Using `pip` and `requirements.txt`

```bash
python -m venv venv
# Activate the virtual environment:
# macOS/Linux:
source venv/bin/activate  
# Windows:
venv\Scripts\activate     
pip install -r requirements.txt
```

To update dependencies:

```bash
pip freeze > requirements.txt
```

---

### 3. Configure Environment Variables

```bash
cp .env.sample .env   # Copy and customize
```

---

### 4. Run Database Migrations

```bash
alembic revision --autogenerate -m "initial schema"
```

### 5. Apply Migration

```bash
alembic upgrade head
```

---

### 6. Start the Server

```bash
uvicorn main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API docs.

---

## 🛠 Developer Tools

Run code checks and formatters:

```bash
# Windows
./run_checks.bat
# macOS/Linux
sh run_checks.sh
```

---

## 🧠 Notes

- **Redis** must be running before starting the server.  
- Alembic is used for managing database migrations.  
- You can use `uv` for modern, lockfile-based dependency management **or** stick with `pip` and `requirements.txt`.

---

## 🔄 Additional UV/PIP Workflow Tips

- **Compile a `requirements.txt`** from your lockfile:
  ```bash
  uv export --no-hashes -o requirements.txt
  ```
- **Sync your venv** from `requirements.txt`:
  ```bash
  uv pip sync requirements.txt   # replicates locked pins
  # or fall back to:
  pip install -r requirements.txt
  ```
