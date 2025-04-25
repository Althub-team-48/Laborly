FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk update && apk add --no-cache build-base

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Pre-commit dependencies ---
RUN pip install pre-commit mypy ruff

# Install pre-commit hooks
COPY .pre-commit-config.yaml .pre-commit-config.yaml
RUN pre-commit install

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
