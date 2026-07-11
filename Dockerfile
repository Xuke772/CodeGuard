FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn python-dotenv openai pyyaml tiktoken

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn codeguard.web:create_app --factory --host 0.0.0.0 --port 8080"]