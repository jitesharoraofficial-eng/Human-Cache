FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build-essential and libxml2 if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, database migrations, and config
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create persistent storage folder
RUN mkdir -p storage

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
