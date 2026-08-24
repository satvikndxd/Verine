FROM python:3.11-slim
WORKDIR /app
COPY backend /app/backend
COPY fixtures /app/fixtures
COPY apps/api /app/apps/api
RUN pip install --no-cache-dir -e backend
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
