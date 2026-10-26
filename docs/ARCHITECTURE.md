# UntapptSelector — System Architecture

## Architectural style

A modular Python monolith. Telegram and FastAPI are separate entry processes
from the same codebase. PostgreSQL stores users and optional external profiles.
The core photo-recognition flow has no dependency on Untappd or a beer catalog.

## Current photo flow

```text
Telegram photo
  -> in-memory download
  -> RecognizeMenu application operation
  -> ImageTextReader interface
  -> Pillow: EXIF orientation, resizing, contrast, sharpening
  -> local Tesseract subprocess (English + Russian)
  -> BeerNameCleaner interface
  -> Ollama chat API (JSON schema)
  -> validated names
  -> MenuDraft: internal raw OCR, names, caption
  -> immediate list
  -> optional correction
```

Tesseract is replaceable through `ImageTextReader`. The Telegram adapter handles
messages and state; it contains no OCR or recommendation algorithm. The application
validates size and coordinates recognition; the LLM adapter removes non-name information and validates the result without
external beer lookups. Raw OCR is never a user-visible fallback.

The caption is stored for later wish interpretation. Preference parsing and ranking
are not part of this implementation.

## Repository structure and responsibilities

```text
src/
    main.py                     # FastAPI /health and request logging
    core/config.py              # Environment and .env settings
    telegram/
        bot.py                  # Composition and polling startup
        start.py                # Registration command
        untappd.py              # Optional legacy profile commands
        menu.py                 # Photo/file download, immediate list and optional editing
    application/
        start.py                # User registration operation
        untappd.py              # Optional external-profile operation
        recognize_menu.py       # Image validation and OCR coordination
    modules/
        users/                  # Models, repository contracts and profile parsing
        menu_recognition/       # OCR contract/errors, draft model and line parser
    infrastructure/
        database/               # Async sessions and PostgreSQL repositories
        ocr/tesseract.py        # Local OCR subprocess adapter
        llm/ollama.py           # Local structured extraction
        # Shared schema and validation: modules/menu_recognition/beer_names.py
alembic/                        # Schema migration environment and revisions
tests/
    unit/                       # Parsing, application and adapter tests
    integration/                # Telegram flows and optional PostgreSQL tests
docs/
    AGENTS.md                   # Single source of development instructions
README.md                       # Installation and commands
pyproject.toml
uv.lock
Dockerfile
compose.yaml
```

The installed package is `src`; use `src.*` imports. Run the API with
`uv run uvicorn src.main:app --reload`, the bot with
`docker compose --profile bot up -d --build bot`. Run commands from the repository root.

## State, storage and concurrency

`users` and `external_accounts` use UUID primary keys and Alembic migrations.
`alembic_version` records the current revision. Recognition adds no tables.

Menu drafts use aiogram MemoryStorage with per-user/per-chat keys. SimpleEventIsolation
serializes updates for the same FSM key. New photos replace a draft after success;
failed recognition preserves the previous draft. Raw OCR remains separate from the
corrected list. `/cancel` clears it. No confirmation step exists; editing starts only with `/editmenu`.
Drafts are lost on process restart and are not shared between processes.
Images are kept only during processing and are not stored or sent to an external OCR API. Bounded OCR text is sent to the local Ollama service;
photos, captions and Telegram identities are not sent to the LLM. No paid cloud API is used.

Prepared-image automatic layout and original-image block layout are compared
using length-weighted OCR confidence. There is a 30-second deadline for the whole
recognition operation.

A semaphore allows one OCR subprocess at a time; async subprocess I/O keeps the
bot event loop responsive. Timeout/cancellation terminates and reaps the child.
No persistent background jobs, automatic retries or durable menu sessions exist.
If needed later, use PostgreSQL-backed jobs rather than adding a message broker.

## Technology

Python 3.14, aiogram 3, FastAPI, PostgreSQL 16, SQLAlchemy 2 with asyncpg,
Alembic, Pydantic Settings, Pillow, native Tesseract, uv, Docker Compose, pytest,
pytest-asyncio, Ruff and mypy. Pillow prepares images before recognition.
Existing optional ML and vision dependencies are not used by this flow.

Tesseract configuration: `OCR_EXECUTABLE` (default `tesseract`) and
`OCR_LANGUAGES` (default `eng+rus`), and `OCR_PAGE_SEGMENTATION` (default `3`, automatic layout; also `6` or `11`). Docker installs English/Russian language data. The `bot` Compose service runs
polling and OCR together and reads its token from `.env`; no Homebrew install is needed.
See [Tesseract command-line documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).

## Next modules

Preference interpretation and recommendation rules will consume recognized menu
items plus the current request. A small style reference may support interpretation;
unknown brand names must not become fabricated beer facts. No rating-history
module, external canonical beer database or ML taste profile is required.

## LLM cleanup

`BeerNameCleaner` is a replaceable async interface. The bot uses
`OllamaBeerNameCleaner` with local `qwen2.5:3b`. Requests go to
`http://ollama:11434/api/chat` with a JSON schema, no streaming, and temperature 0.
Shared prompts, schemas and source validation live in
`modules/menu_recognition/beer_names.py`. The old OpenAI adapter is not selected
and has no automatic fallback path from the local adapter.

The Ollama service and model-init container use the `bot` Compose profile.
`ollama-init` downloads `OLLAMA_MODEL` into the server's persistent `ollama_data`
volume before polling starts. No model-server port is published to the host.
All inference is local; Docker on this setup uses CPU. Cleanup is serialized and
has a 180-second deadline. CPU, RAM and disk are still required even though no
per-request API payment is made.

No raw OCR fallback is shown on errors. Manual corrections use the same cleaner.
Tests mock local API calls. Live smoke tests use synthetic menus, not user data.
See [Ollama chat API](https://docs.ollama.com/api/chat) and
[Docker setup](https://docs.ollama.com/docker).
