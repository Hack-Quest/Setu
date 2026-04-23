FROM python:3.11-slim

WORKDIR /app

# 1. Install dependencies using the file in backend folder
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the entire project context into the container
COPY . .

# 3. Set PYTHONPATH so Python can find 'database' and 'ai_processing' modules
ENV PYTHONPATH=/app

EXPOSE 8080

# 4. Run uvicorn pointing to the main.py inside the backend folder
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}