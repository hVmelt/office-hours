FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (Docker layer caching — deps only re-install when requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY *.py ./
COPY schema.sql ./

# Render provides the PORT env var; default to 8000 for local testing
ENV PORT=8000

# Render sets PORT; uvicorn can read it directly via --port using a small shell wrapper.
# Exec form for proper signal handling:
CMD ["sh", "-c", "exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]