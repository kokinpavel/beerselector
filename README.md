# UntapptSelector

Telegram assistant for personalized beer selection from photographed menus.

Implemented: PostgreSQL user registration through `/start`, user-supplied Untappd
profiles through `/untappd`, a FastAPI health endpoint, and Alembic migrations.
History import, OCR, menu confirmation and recommendations are planned.
Untappd API access requires a commercial agreement according to the developer
portal notice supplied by the project owner; see [integration status](docs/untappd-integration.md).

## Structure

```text
src/
    main.py                 # FastAPI application
    core/                   # Configuration
    telegram/               # Bot startup and command handlers
    application/            # User workflows
    modules/users/          # User models, contracts and profile validation
    infrastructure/database/ # SQLAlchemy sessions and repositories
alembic/                    # Schema migrations
tests/                      # Unit and PostgreSQL integration tests
docs/                       # Product, architecture and integration notes
```

`src` is the application package. Use `src.*` imports and run commands below
from the repository root. See [architecture](docs/ARCHITECTURE.md),
[product specification](docs/PROJECT.md) and [development instructions](docs/AGENTS.md).

## Local setup

1. Install Python 3.14, uv and Docker Desktop. Start Docker Desktop.
2. Install dependencies:

   ```sh
   uv sync --extra dev
   ```

3. Create `.env` in the repository root, or keep your existing one:

   ```dotenv
   DATABASE_URL=postgresql+asyncpg://untappt:untappt@localhost:5432/untappt
   POSTGRES_PASSWORD=untappt
   TELEGRAM_BOT_TOKEN=your_botfather_token
   APP_ENV=development
   LOG_LEVEL=INFO
   ```

   The password in `DATABASE_URL` must match `POSTGRES_PASSWORD`.
   `.env` is ignored by Git. Never publish the bot token.

4. Start PostgreSQL and apply migrations:

   ```sh
   docker compose up -d --wait db
   uv run alembic upgrade head
   ```

5. Start the bot:

   ```sh
   uv run python -m src.telegram.bot
   ```

   API is a separate process, if needed:

   ```sh
   uv run uvicorn src.main:app --reload
   ```

   Health check: `http://localhost:8000/health`. It checks the API response, not database readiness.

## Bot commands

- `/start` saves a user with an internal UUID and unique Telegram ID. Repeated
  or concurrent commands reuse the same user.
- `/untappd username` or `/untappd https://untappd.com/user/username` saves or
  replaces the current user's Untappd profile in a private chat.
- `/untappd` shows the saved profile or instructions.

Profile existence and ownership are not verified. Saving a username does not
import ratings, and no Untappd password is requested.

## Docker

```sh
docker compose up -d --wait db
docker compose build app
docker compose run --rm app alembic upgrade head
docker compose up -d app
```

The `app` service runs the API. To run the bot in a separate container:

```sh
docker compose run --rm -e TELEGRAM_BOT_TOKEN app python -m src.telegram.bot
```

For this command, export `TELEGRAM_BOT_TOKEN` in the terminal first; Compose does
not automatically pass every `.env` variable into containers.
Do not run multiple polling processes with the same bot token.

## Database

Local processes connect to `localhost:5432`; containers use `db:5432`.
Database and user: `untappt`; password: `POSTGRES_PASSWORD`, default `untappt`.

```sh
docker compose exec db psql -U untappt -d untappt
```

Inside `psql`, use `\dt` to list tables, `\d users` for table structure, and `\q` to exit.
Current tables: `users`, `external_accounts`, `alembic_version`.

A connection-refused error on port 5432 usually means PostgreSQL is stopped.
Start Docker Desktop and run `docker compose up -d --wait db`.

## Migrations

Alembic shares `DATABASE_URL` and SQLAlchemy model metadata with the application.
Revisions: `0001` empty baseline, `0002` users, `0003` external accounts.

```sh
uv run alembic current
uv run alembic upgrade head
uv run alembic upgrade head --sql
```

After adding models, import their modules in `alembic/env.py`, then generate and review:

```sh
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
uv run alembic check
```

`uv run alembic downgrade -1` rolls back one revision and may delete its tables.
Migrations are explicit deployment steps; bot and API startup do not alter the schema.
Existing databases keep their data during the package restructure; no reset is needed.

## Checks

```sh
uv run pytest
uv run ruff check .
uv run mypy src
uv build
```

PostgreSQL tests are skipped unless `TEST_DATABASE_URL` points to a disposable
PostgreSQL database using `postgresql+asyncpg://`. They apply and roll back
migrations, including dropping application tables. Never point this variable at
your working or production database. Telegram API calls are mocked in tests.
