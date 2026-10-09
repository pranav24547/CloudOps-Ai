FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend/
COPY agent /app/agent/
COPY workflows /app/workflows/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/backend

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
