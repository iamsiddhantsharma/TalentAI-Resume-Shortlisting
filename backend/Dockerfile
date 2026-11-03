# ==============================================================================
# TalentAI Backend — Production Container Image
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal OS dependencies for healthchecks and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python production dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Create non-root application user for least-privilege security
RUN groupadd -r talentai && useradd -r -g talentai -s /bin/bash -d /app talentai

# Create required persistent data and log directories
RUN mkdir -p /app/data/uploads /app/data/extracted /app/data/failed /app/logs && \
    chown -R talentai:talentai /app

# Copy application source code
COPY . /app
RUN chown -R talentai:talentai /app

# Run as non-root user
USER talentai

# FastAPI internal port (routed internally by reverse proxy, not published to host)
EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Production application server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
