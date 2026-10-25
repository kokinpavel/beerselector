# UntapptSelector

Chapter 3 foundation scaffold. No Untappd integration, OCR or recommendation engine yet.

## Local run

1. Install Python 3.12 and uv.
2. `cp .env.example .env` and configure secrets.
3. `uv sync --extra dev`
4. `uv run uvicorn untappt_selector.main:app --reload`
5. Visit `http://localhost:8000/health`.

## Docker

`docker compose up --build -d`

## Telegram polling (separate process)

Set `TELEGRAM_BOT_TOKEN` and run `uv run python -m untappt_selector.telegram.bot`.

## Tests

`uv run pytest`

Database schema and Alembic migrations will be added with the Chapter 2 model implementation; this scaffold only supplies a SQLAlchemy base and session factory.
