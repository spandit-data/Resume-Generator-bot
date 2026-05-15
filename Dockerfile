FROM python:3.11-slim

# Install system dependencies for ffmpeg and libreoffice
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libreoffice \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv && uv sync

# Copy application code
COPY src ./src

# Create data directory for SQLite
RUN mkdir -p /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1

# Install dependencies and pin the version
RUN pip install uv && uv sync && uv pip install python-telegram-bot==22.7

# Start with plain python (not uv run) to avoid patched event loop
CMD ["/app/.venv/bin/python", "src/bot.py"]