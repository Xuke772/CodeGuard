FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn python-dotenv openai pyyaml tiktoken

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD python -c "from codeguard.web import create_app; import uvicorn, os; uvicorn.run(create_app(), host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))"