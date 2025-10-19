FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN python -m venv .venv && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Start app with Uvicorn
CMD /bin/bash -c "/app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"
