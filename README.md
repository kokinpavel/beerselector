# UntapptSelector

Telegram assistant for choosing beer from a photographed menu and the user's current wishes.

Implemented: PostgreSQL user registration through `/start`, user-supplied Untappd
profiles through `/untappd`, local photo OCR, LLM extraction of beer names, optional menu correction,
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
    modules/menu_recognition/ # OCR contracts, menu rows and draft validation
    infrastructure/database/ # SQLAlchemy sessions and repositories
    infrastructure/ocr/     # Local Tesseract adapter
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
   OLLAMA_MODEL=qwen2.5:3b
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

5. Build and run the bot in Docker, including English/Russian Tesseract:

   ```sh
   docker compose build bot
   docker compose --profile bot up -d bot
   docker compose logs -f bot
   ```

   Compose passes `TELEGRAM_BOT_TOKEN` from `.env` to the bot container and uses
   `db:5432` for PostgreSQL. No Homebrew installation or native OCR is needed on
   the host. Optional setting: `OCR_LANGUAGES=eng+rus` in `.env`.
   Stop any locally running polling process before starting the container.
   Stop the container with `docker compose stop bot`.

   For local API development only, use `uv run uvicorn src.main:app --reload`.
   Health check: `http://localhost:8000/health` checks the API, not database readiness.

## Photo recognition

In a private chat, send one clear photo of a menu (or a JPEG/PNG/WebP image as a file, without Telegram compression). The bot downloads the largest
Telegram photo, runs local Tesseract, then sends its text to the LLM and shows
only extracted beer names. Raw OCR, prices, volumes and ABV are not shown.
No confirmation is required.
The optional caption is kept with the draft for future preference handling;
it does not affect recognition or trigger recommendations yet.

- Optionally use `/editmenu`, then send the entire corrected list, one item per line.
- No confirmation command is required; the recognized list is available immediately.
- `/menu` displays the current list.
- `/editmenu` starts manual entry or editing, including when OCR is unavailable.
- `/cancel` deletes the current draft.

Before OCR, Pillow fixes EXIF orientation, enlarges small images, normalizes contrast
and sharpens text. Tesseract defaults to automatic page layout (`OCR_PAGE_SEGMENTATION=3`);
`6` (one block) or `11` (sparse text) can be selected in `.env` for a particular menu.
The prepared-image pass is compared with an original-image block pass using
Tesseract word confidence (a heuristic, not a probability of correctness).
These changes do not guarantee correct recognition of skewed or complex menus.

The LLM cleaner uses the local Ollama chat API with a JSON schema, then
validates source-line references, name words and duplicate entries. It removes
menu headings, descriptions, prices, ABV/IBU and volumes. Meaningful numbers in
product names (such as Rochefort 10) remain. It does not look up brands or guess
missing names; uncertain/unreadable names should be omitted. These checks reduce
but cannot eliminate incorrect extraction or omissions from poor OCR.

The production bot uses local Ollama, default model `qwen2.5:3b`. No API key,
prepaid balance or paid cloud call is required. The old OpenAI adapter remains
available in code for tests but is not instantiated by the bot; there is no
fallback to a paid provider. Existing `OPENAI_*` entries in `.env` are unused.

Compose starts `ollama`, waits for it to be healthy, then `ollama-init` downloads
`OLLAMA_MODEL` before the bot starts. The model is saved in `ollama_data` and is
reused on subsequent runs. Initial setup downloads the server image plus about
1.9 GB of model weights. Local CPU inference consumes RAM/CPU and may be slow;
allow the bot time to finish. The local cleanup deadline is 180 seconds.

OCR text stays in the Docker network and is not sent to OpenAI. Ollama has no
published host port. Caption and Telegram identity are not included in the LLM
request. API/validation failures never fall back to raw OCR in Telegram.
Manual corrections also pass through the local cleaner.

Limits: 10 MB per photo, 30-second OCR timeout, 60 rows, 300 characters per row.
Truncation is reported. Tesseract processes one photo at a time. OCR runs in a
subprocess without blocking the event loop; a timeout kills and reaps it.
Images are not retained. Raw OCR and corrections remain in per-user, per-chat
in-memory FSM state, and disappear when the bot restarts. This is not durable
menu storage or a background-job system. New photos replace the current draft
only after successful processing. This change adds no database tables.

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
and OCR in the same application image, with Tesseract installed at build time:

```sh
docker compose build bot
docker compose --profile bot up -d bot
docker compose logs -f bot ollama-init ollama
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
uv run mypy src
uv build
```

OCR, LLM API and Telegram calls are mocked in ordinary tests; passing them does
not establish recognition quality on real photos. Real OCR runs in the Docker image; no host installation is required.

PostgreSQL tests are skipped unless `TEST_DATABASE_URL` points to a disposable
PostgreSQL database using `postgresql+asyncpg://`. They apply and roll back
migrations, including dropping application tables. Never point this variable at
your working or production database. Telegram API calls are mocked in tests.

## Local LLM troubleshooting

```sh
docker compose --profile bot ps -a
docker compose exec ollama ollama list
docker compose logs --tail 50 ollama-init ollama bot
```

If a model download fails, rerun `docker compose --profile bot up -d bot`.
To choose another locally available Ollama model, set `OLLAMA_MODEL` in `.env`
and recreate the bot with `docker compose --profile bot up -d --build bot`.
Do not use `docker compose down -v` to restart: it deletes stored models and DB data.
