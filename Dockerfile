FROM python:3.11-slim AS builder
  WORKDIR /app
  RUN pip install poetry
  COPY pyproject.toml poetry.lock ./
  RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

  FROM python:3.11-slim
  WORKDIR /app
  RUN useradd -m -u 1000 appuser && chown appuser /app
  COPY --from=builder /app/requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  USER appuser
  EXPOSE 8080
  CMD ["python", "main.py"]
  