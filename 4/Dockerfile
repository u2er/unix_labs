FROM python:3.11-slim

ENV PYTHONPATH=/app
WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-root

RUN mkdir -p /app/logs /app/temp

COPY app/ ./app/

CMD ["python", "app/worker.py"]