FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.lock .
RUN pip install --no-cache-dir --user -r requirements.lock

FROM python:3.11-slim AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip setuptools==84.2.1 wheel==0.48.0
RUN useradd -m -u 1001 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY app/ ./app/
COPY regulatory_framework.json ./regulatory_framework.json
COPY alembic.ini ./alembic.ini
COPY migrations/ ./migrations/

ENV PATH=/home/appuser/.local/bin:$PATH
RUN python -m pip uninstall --yes pip
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
