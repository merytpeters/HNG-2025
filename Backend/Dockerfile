FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN python -m venv .venv && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

# Install spaCy models inside the container
RUN .venv/bin/python -m spacy download en_core_web_md && \
    .venv/bin/python -m spacy download en_core_web_sm

# Copy app source
COPY . .

# Expose port 80 (Sevalla expects this)
EXPOSE 80

# Start app with Uvicorn on dynamic port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
