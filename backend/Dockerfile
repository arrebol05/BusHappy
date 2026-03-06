# Use Python 3.11 official image
FROM python:3.11.7-slim

# Set working directory
WORKDIR /app

# Install system dependencies for lxml and pandas
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate GTFS data during build
RUN cd data_preprocessing && python generate_gtfs.py && cd ..

# Expose port (Render will set $PORT)
EXPOSE $PORT

# Run gunicorn
CMD gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
