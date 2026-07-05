FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY sdk ./sdk
RUN pip install --no-cache-dir -e ".[postgres]"

EXPOSE 8000
CMD exec uvicorn agent_finops.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
