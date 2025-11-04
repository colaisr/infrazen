# Agent Service Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-agent.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-agent.txt

# Copy agent service code
COPY agent_service/ ./agent_service/

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/v1/health')"

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8001"]

