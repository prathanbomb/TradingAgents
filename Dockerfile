# ============================================================
# Stage 1: Builder - install Python dependencies
# ============================================================
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy build files and create minimal package structure for dependency resolution
COPY pyproject.toml setup.py ./
RUN mkdir tradingagents && touch tradingagents/__init__.py

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir .

# Copy full source and reinstall package only (deps already cached)
COPY tradingagents/ tradingagents/
RUN pip install --no-cache-dir --no-deps .

# ============================================================
# Stage 2: Runtime - minimal production image
# ============================================================
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r trading && useradd -r -g trading -u 1000 -m -s /bin/bash trading

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY tradingagents/ tradingagents/
COPY scripts/ scripts/
COPY tickers.txt ./

RUN mkdir -p /app/data /app/reports /app/results /app/eval_results && \
    chown -R trading:trading /app

USER trading

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    REPORTS_OUTPUT_DIR=/app/reports

CMD ["python", "scripts/run_scheduled_analysis.py"]
