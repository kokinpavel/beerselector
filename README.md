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

To include the PostgreSQL migration roundtrip, set `TEST_DATABASE_URL` to a
disposable database using the asyncpg URL format. The test applies and rolls back
migrations in that database.

## Database migrations

Alembic uses the same `DATABASE_URL` setting as the application, from the environment
or `.env`. Use a `postgresql+asyncpg://` URL. The initial revision is an empty
baseline because the scaffold has no application models yet.

```sh
uv run alembic upgrade head
uv run alembic current
uv run alembic downgrade -1
uv run alembic upgrade head --sql
```

After adding SQLAlchemy models derived from `Base`, import their modules in
`alembic/env.py`, then generate and review a migration:

```sh
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
uv run alembic check
```

For Docker, start the database with `docker compose up -d db`, then run
`docker compose run --rm app alembic upgrade head` before starting the app.
Migrations are explicit deployment steps; application startup does not change the schema.
The database service is only accessible inside Compose by default; run local CLI
commands against a PostgreSQL instance reachable through your configured URL.
