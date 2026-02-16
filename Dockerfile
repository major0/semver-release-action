FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/owner/semver-release-action"
LABEL org.opencontainers.image.description="Semantic Versioning Release Action"

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

ENTRYPOINT ["python", "-m", "src.main"]
