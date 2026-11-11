FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY evaluation_runtime evaluation_runtime
COPY migrations migrations
COPY alembic.ini .
RUN useradd --create-home app && mkdir -p /app/data && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
