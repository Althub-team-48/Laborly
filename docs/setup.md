# 🛠️ Project Setup Guide

## 📦 Prerequisites
Make sure the following tools are installed:

- **Python 3.10+**
- **PostgreSQL** (v13 or higher recommended)
- **Virtualenv** (optional but recommended)
- **Git**

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-org>/laborly-api.git
cd laborly-api
```

### 2. Create and activate a virtual environment (optional)
```bash
python -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your own values:
```bash
cp .env.example .env
```

Then open `.env` and set your database credentials and secret key:
```dotenv
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/laborly
SECRET_KEY=<your-generated-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. Initialize the database

Ensure PostgreSQL is running and then:
```bash
python app/database/init_db.py
```

To reset, migrate, and seed:
```bash
python app/database/reset.py --auto
```

### 6. Run the API server
```bash
uvicorn main:app --reload
```

> Your API should now be running at: `http://localhost:8000`

---

## 📘 Additional Commands

### Run Alembic Migrations
```bash
alembic revision --autogenerate -m "your message"
alembic upgrade head
```

### Generate a secure secret key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🧪 Testing
_Tests folder and pytest configuration coming soon._

---

## 💬 Support
If you encounter any issues, please open an issue or contact the maintainers.

---

Happy coding! 🚀

