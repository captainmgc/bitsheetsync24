# Bitrix Sync Daemon Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sync daemon files (new structure)
COPY daemon.py .
COPY sync_bitrix.py .
COPY config.py .
COPY models.py .
COPY storage.py .
COPY main.py .
COPY __init__.py .
COPY bitrix/ ./bitrix/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the sync daemon
CMD ["python", "daemon.py"]
