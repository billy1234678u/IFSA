# Multi-stage Dockerfile for IFSA Market Monitor
# Optimized for Hostinger VPS deployment

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for state persistence
RUN mkdir -p /app/data /app/logs && \
    chmod +x /app/scripts/*.sh || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command - can be overridden
# For API server mode (Hostinger VPS with Docker)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# Alternative commands:
# For bot-only mode (continuous monitoring loop):
# CMD ["python", "-m", "src.bot"]

# For combined mode (API + background scheduler):
# Use docker-compose.yml
