FROM python:3.11-slim

WORKDIR /app

# Create non-root system user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser && \
    mkdir -p /app/data/uploads && \
    chown -R appuser:appuser /app

COPY apps/api/ ./
RUN pip install --no-cache-dir .
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
