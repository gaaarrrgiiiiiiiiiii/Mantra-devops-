FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner
WORKDIR /app

RUN useradd -m -u 1001 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY app/ ./app/
COPY regulatory_framework.json ./
RUN mkdir -p /app/.local && chown appuser:appuser /app/.local

ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
