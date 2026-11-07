# ==============================================================================
# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
# Production Multi-Stage Dockerfile (Phase 8 Architecture)
# ==============================================================================

# STAGE 1: Builder stage for compiling wheels and preparing dependencies
FROM python:3.9-slim-bookworm AS builder

WORKDIR /build

# Install minimal build toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest and build wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# STAGE 2: Secure, Hardened Production Runtime
FROM python:3.9-slim-bookworm AS runner

# Set secure environment defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/lib" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    APP_ENV=production

WORKDIR /app

# Install runtime dependencies (curl for container healthcheck, sqlite3 for DB maintenance)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH="/home/appuser/.local/bin:$PATH"

# Create persistent storage mountpoints and assign ownership
RUN mkdir -p /app/data /app/logs /app/outputs /app/reports && \
    chown -R appuser:appgroup /app

# Copy application source code
COPY --chown=appuser:appgroup . /app

# Switch to non-root user
USER appuser

# Expose Streamlit default web port
EXPOSE 8501

# Container healthcheck: ping Streamlit core health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Production entrypoint
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
