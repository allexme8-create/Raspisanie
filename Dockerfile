FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

ENV ADMIN_PASSWORD=admin123
ENV PORT=8000
EXPOSE 8000

WORKDIR /app/backend
CMD ["python", "app.py"]
