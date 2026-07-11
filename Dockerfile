FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ripgrep && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn codeguard.web:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]