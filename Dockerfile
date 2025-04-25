# Use Python 3.10 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY staff/src/staff/ .

COPY staff/src/staff/utilities/fac.json /app/fac.json

COPY staff/src/staff/utilities/gac.json /app/gac.json

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port Cloud Run will use
EXPOSE 8080

# Command to run the application with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app