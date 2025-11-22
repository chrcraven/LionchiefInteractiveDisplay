# Dockerfile for API service
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Bluetooth (required for pyLionChief)
RUN apt-get update && apt-get install -y \
    bluez \
    bluetooth \
    libbluetooth-dev \
    libglib2.0-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Try to install pyLionChief from git (will use the user's repo)
# This will fail gracefully if not available, allowing mock mode
RUN pip install git+https://github.com/chrcraven/pyLionChief.git || echo "pyLionChief not available, will run in mock mode"

# Copy application code
COPY . /app/api/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
