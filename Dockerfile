FROM python:3.14

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN uv pip install --system .

CMD ["uvicorn", "untappt_selector.main:app", "--host", "0.0.0.0", "--port", "8000"]
