FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /srv/alphalab

RUN pip install --no-cache-dir "poetry>=2.0,<3.0"

COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry install --only main --no-root --no-interaction

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
