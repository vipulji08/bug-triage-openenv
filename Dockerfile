# Dockerfile for Bug Triage OpenEnv
# Run with: docker build -t bug-triage-env . && docker run -p 7860:7860 bug-triage-env

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create __init__ files
RUN touch env/__init__.py

# Expose port (HuggingFace Spaces uses 7860)
EXPOSE 7860

# Set environment variables defaults
ENV API_BASE_URL="https://router.huggingface.co/v1"
ENV MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start the FastAPI server
CMD ["python", "app.py"]
