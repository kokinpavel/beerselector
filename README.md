# UntapptSelector

Telegram assistant for choosing beer from a photographed menu and the user's current wishes.

Implemented: PostgreSQL user registration through `/start`, user-supplied Untappd
profiles through `/untappd`, local Qwen3-VL menu recognition, optional menu correction,
a FastAPI health endpoint, and Alembic migrations.
Preference interpretation and recommendations are the next step. The main flow
does not require an Untappd account or rating history.
Untappd API access requires a commercial agreement according to the developer
portal notice supplied by the project owner; see [integration status](docs/untappd-integration.md).

## Structure

```text
src/
    main.py                 # FastAPI application
    core/                   # Configuration
    telegram/               # Bot startup and command handlers
    application/            # User workflows
    modules/users/          # User models and optional external profiles
    modules/menu_recognition/ # Menu contracts and draft validation
    infrastructure/database/ # SQLAlchemy sessions and repositories
    infrastructure/llm/     # Qwen3-VL through Ollama
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

5. Build and run the bot and Qwen3-VL 4B service in Docker:

   ```sh
   docker compose --profile bot build bot
   docker compose --profile bot up -d bot
   docker compose logs -f bot
   ```

   Compose passes `TELEGRAM_BOT_TOKEN` from `.env` to the bot container and uses
   `db:5432` for PostgreSQL. No Homebrew installation or native OCR is needed on
   the host. Model weights are downloaded on the first service startup.
   Stop any locally running polling process before starting the container.
   Stop the container with `docker compose stop bot`.

   For local API development only, use `uv run uvicorn src.main:app --reload`.
   Health check: `http://localhost:8000/health` checks the API, not database readiness.

## Photo recognition

Send a menu photo or JPEG/PNG/WebP file in a private chat. The bot passes the
image directly to **Qwen3-VL 4B Instruct** using Ollama's `/api/chat` endpoint.
The same model extracts names and corrects clear recognition/spelling errors in
one call. Text submitted through `/editmenu` uses the same model without an image.
No Tesseract or paid API participates in this path.

Default: `OLLAMA_MODEL=qwen3-vl:4b-instruct`. Ollama must be version 0.12.7 or newer.
Compose starts Ollama and downloads the model before starting the bot. Weights
are cached in `ollama_data`; the initial model download is approximately 3.3 GB.
CPU inference requires additional RAM and can be slow. Set `OLLAMA_MODEL` in
`.env` explicitly if an older value is already configured.
Model reference: https://ollama.com/library/qwen3-vl:4b-instruct

The model receives an extraction instruction and a JSON schema. Output must be
complete and pass count/length validation. Prices, ABV and volumes should be
omitted, meaningful numbers in names retained. Instructions permit only clear
corrections and forbid inventing products. Structural validation does not prove
that a name appears in the photo; real menu accuracy still needs evaluation.
There is no fallback to another model or to unvalidated raw output.

Use `/menu` to display the draft, `/editmenu` to replace it, and `/cancel` to
delete it. The caption is stored but is not sent to the model. Drafts live in
per-chat memory and disappear on restart. Photos are not saved. For photos,
`raw_text` contains the model JSON rather than a separate OCR transcription.
Limits: 10 MB per photo, 60 names, 300 characters per name, 180 seconds per request.
A timeout stops waiting but does not guarantee Ollama has cancelled inference.
Ollama has no published host port. Mocked tests do not establish photo quality.

## Bot commands

- `/start` saves a user with an internal UUID and unique Telegram ID. Repeated
  or concurrent commands reuse the same user; the welcome message invites a menu photo.
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

The `app` service runs the API. The optional `bot` profile runs Telegram polling
and a separate Ollama inference service:

```sh
docker compose --profile bot build bot
docker compose --profile bot up -d bot
docker compose logs -f bot ollama
```

The Telegram token and local model setting are read from `.env` by Compose; no manual export is required. Run only
one polling process per bot token. `docker compose up -d app` does not start the
bot unless it is explicitly selected or its profile is enabled.

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
uv run ruff format --check .
uv run mypy src
uv build
```

Ollama and Telegram calls are mocked in ordinary tests; passing them does
not establish recognition quality on real photos. Real Qwen3-VL inference requires the separate Docker service and model download.

Ruff is included in `uv sync --extra dev`. It checks imports, common errors,
Python upgrades and likely bugs; `uv run ruff check --fix .` applies safe fixes,
and `uv run ruff format .` formats code. Both checks run in GitHub Actions.
VS Code recommends the Ruff extension and enables formatting on save for Python;
accept the workspace extension recommendation to enable editor diagnostics.

PostgreSQL tests are skipped unless `TEST_DATABASE_URL` points to a disposable
PostgreSQL database using `postgresql+asyncpg://`. They apply and roll back
migrations, including dropping application tables. Never point this variable at
your working or production database. Telegram API calls are mocked in tests.

## Local model troubleshooting

```sh
docker compose --profile bot ps -a
docker compose logs --tail 50 ollama bot
```

Start Docker Desktop before building. Retry failed downloads with
`docker compose --profile bot up -d --build bot`.
Do not use `docker compose down -v`: it deletes model and database volumes.
