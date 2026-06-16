# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (frontend is hosted on Firebase Hosting directly)
COPY backend/ ./backend/
COPY trained_model/ ./trained_model/

# Set default port
ENV PORT 8080
EXPOSE 8080

# Run the web service on container startup
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
