# ==============================================================================
# WebRevive AI - Backend Multi-Stage Dockerfile
# Stage 1: Dependency builder & Playwright browser installation
# Stage 2: Production lean runtime image
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /build

# Install compilation build dependencies & curl for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Install Playwright browser dependencies and chromium binary
RUN playwright install --with-deps chromium

# ------------------------------------------------------------------------------
# Stage 2: Lean Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runner

LABEL maintainer="WebRevive AI Contributors <maintainers@webrevive.ai>"
LABEL description="WebRevive AI Backend Service - AI-Based Accessibility & Content Refactoring"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8000

WORKDIR /app

# Install runtime system libraries required by Chromium and curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and Playwright binaries from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /ms-playwright /ms-playwright

# Create dedicated non-root user
RUN groupadd -g 10001 webrevive && \
    useradd -u 10001 -g webrevive -m -s /bin/bash webrevive && \
    chown -R webrevive:webrevive /app /ms-playwright

# Copy application source code
COPY --chown=webrevive:webrevive . /app

# Switch to non-root user
USER webrevive

EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch FastAPI app with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
