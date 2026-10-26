# UntapptSelector — Agent Instructions

## Project Context

You are a software engineering agent working on UntapptSelector.

UntapptSelector is a Telegram-first beer recommendation system.

The current product direction is a photographed beer menu plus the user's
current wishes. Untappd history is not required. The present implementation
step is photo recognition and optional correction; preference parsing and recommendations
are subsequent steps.

Before implementing features or making architectural changes,
read these documents:

1. `docs/PROJECT.md` — product vision, MVP scope, requirements.
2. `docs/ARCHITECTURE.md` — system design and component boundaries.
3. `README.md` in the repository root — current setup and development commands.

All paths above are relative to the repository root. The application is the `src`
Python package; use imports such as `from src.core.config import get_settings`.
Run the API with `uv run uvicorn src.main:app --reload` and the bot with
`docker compose --profile bot up -d --build bot` from the repository root.
Run OCR in Docker; do not install Tesseract via Homebrew on the host.

If a document is missing, report it. Do not invent its contents.

## Primary Goal

Build a working, maintainable MVP that:

1. Accepts a beer-menu photo through Telegram.
2. Recognizes photo text with a replaceable OCR adapter and extracts only beer
   names with a replaceable LLM adapter. Never show raw OCR to the user.
3. Allows the user to optionally correct the list.
4. Subsequently interprets the user's wishes, such as strong Belgian-style beer.
5. Subsequently returns up to three matching menu items with explanations.

No Untappd account, historical ratings or external beer catalog is required.
Never invent missing beer characteristics. Unknown names remain unresolved.

## Architecture Rules

Use a modular monolith.

Core modules:

- telegram
- application
- users
- history
- catalog
- menu_recognition
- profiles
- recommendations
- infrastructure

Maintain separation of concerns.

Telegram must not contain ML, OCR, or database business logic.

The recommendation engine must not depend on Telegram,
Untappd APIs, or OCR implementation details.

External integrations must use replaceable adapters.

Do not introduce microservices, message brokers,
or unnecessary infrastructure without approval.

## Technology Stack

Preferred stack:

- Python 3.14
- FastAPI
- aiogram 3
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic
- Docker Compose
- pytest
- Ruff
- Tesseract for local OCR (English and Russian)

For OCR and beer matching, use simple replaceable
implementations. Select concrete libraries based on testing.

Follow the existing repository configuration when it differs
from these preferences. Explain material conflicts.

## Development Rules

1. Inspect relevant existing code before modifying it.
2. Respect the existing project structure.
3. Implement the smallest complete change needed.
4. Do not rewrite unrelated modules.
5. Use Python type hints.
6. Keep functions small and focused.
7. Prefer explicit, readable code.
8. Do not hardcode secrets or credentials.
9. Do not add dependencies without explaining why.
10. Do not claim tests passed unless they were executed.

## Recommendation Rules

Recommendation work is a later step, separate from OCR. Start with explicit,
interpretable rules using the current request and recognized menu entries.
Do not introduce ML, neural models, embeddings or external catalogs by default.
Explain matching criteria rather than presenting fabricated preference scores.

## OCR Rules

Separate image processing, OCR, menu parsing,
beer matching, and optional user correction. Do not require confirmation.

Keep original recognized text internally for debugging. Clean it through the LLM
before displaying names; on cleanup failure never fall back to displaying raw OCR.
Prices, ABV, volumes, headings and descriptions must not appear in the names list.

Do not silently replace uncertain matches with
supposedly correct beer identities.

Allow unrecognized beers to remain unresolved.

## Untappd Integration Rules

Untappd is optional legacy functionality, outside the core photo-menu flow.
The project must not depend on its API, Premium or CSV export.

Do not assume access to private or restricted APIs.

Verify technical availability and permitted use before
implementing an integration.

Do not bypass access controls, authentication, rate limits,
or service restrictions.

Keep history acquisition independent from the ML model.

If a compliant data source is unavailable, use clearly
marked test fixtures and report the blocker.

## Testing Rules

Add or update tests for meaningful behavior changes.

Use:

- Unit tests for domain logic.
- Integration tests for database operations.
- End-to-end tests for complete user flows.

Mock external services in ordinary automated tests.

Never run destructive database operations on production
or unknown databases.

## Workflow

For each development task:

1. Read the relevant project documentation.
2. Inspect the existing implementation.
3. Briefly explain the intended approach.
4. Implement the requested change.
5. Run relevant tests when possible.
6. Review the resulting diff.
7. Summarize changes and verification results.

Distinguish verified behavior from assumptions.

## Communication

Communicate with the user in Russian.

Use English for code, identifiers, and technical file names.

Explain architectural decisions briefly.

When blocked, describe the problem and propose a specific
next step.

## Scope Control

Do not implement future roadmap features without request.

Do not overengineer the MVP.

Do not make broad architectural changes silently.

Ask for approval before:

- Replacing core technologies.
- Introducing new infrastructure services.
- Making destructive database changes.
- Changing approved system boundaries.
