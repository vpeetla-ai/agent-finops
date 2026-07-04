FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY sdk ./sdk
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "agent_finops.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
