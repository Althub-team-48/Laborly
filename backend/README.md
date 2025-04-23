# 🚀 Laborly Backend

Laborly is a modular FastAPI-based backend that powers a job-matching platform between clients and verified workers.

---

## ✅ Prerequisites

Make sure the following are installed and running:

- **Python 3.11+**
- **PostgreSQL** (running and accessible)
- **Redis** (must be running locally on port `6379`)
- **Git**
- **Virtual Environment** (`venv` or equivalent)

---

## ⚙️ Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/laborly-backend.git
cd laborly-backend
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Edit the `.env.sample` file with your environment details, then rename it to `.env`:

```bash
mv .env.sample .env
```

### 5. Generate Database Migration

```bash
alembic revision --autogenerate -m "initial schema"
```

### 6. Apply Migration

```bash
alembic upgrade head
```

### 7. Start the Server

```bash
uvicorn main:app --reload
```

Visit the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐘 Notes

- Redis **must be running** before launching the app.
- Database structure is managed via Alembic migrations.