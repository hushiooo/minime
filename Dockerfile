# Builder image
FROM python:3.11-alpine AS builder-image

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    linux-headers

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Runner image
FROM python:3.11-alpine AS runner-image

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache libpq

# Copy only the necessary files from the builder image
COPY --from=builder-image /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder-image /usr/local/bin /usr/local/bin

# Copy only the application source code
COPY src /app/src

# Create logs directory
RUN mkdir /app/logs

# Run as non-root user
RUN adduser -D -u 1000 appuser
RUN chown appuser:appuser /app/logs
USER appuser

# Expose port
EXPOSE 8000

# Add labels
LABEL maintainer="hushiooo <hushio@proton.me>"
LABEL version="1.0"
LABEL description="MiniMe - URL Shortener"

# Run app
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
