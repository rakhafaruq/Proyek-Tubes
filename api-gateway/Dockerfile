FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gateway akan jalan di port 8000 (di dalam container)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]