FROM python:3.11-slim

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry

COPY pyproject.toml ./
RUN poetry install --only main --no-interaction --no-ansi --no-root

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
