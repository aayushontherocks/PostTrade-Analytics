FROM python:3.9-slim

WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt jupyterlab

# Copy application code
COPY . .

# Expose ports
EXPOSE 8501 8888

# Default command (can be overridden in compose)
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
