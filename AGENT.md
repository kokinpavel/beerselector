
# UntapptSelector — Agent Instructions

## Project Context

You are a software engineering agent working on UntapptSelector.

UntapptSelector is a Telegram-first beer recommendation system.

The system analyzes a user's personal Untappd beer ratings
and recommends the best beers from a menu photographed
by that user.

Before implementing features or making architectural changes,
read these documents:

1. PROJECT.md — product vision, MVP scope, requirements.
2. ARCHITECTURE.md — system design and component boundaries.
3. README.md — current setup and development commands.

If a document is missing, report it. Do not invent its contents.

## Primary Goal

Build a working, maintainable MVP that:

1. Identifies users through Telegram.
2. Obtains existing beer ratings from Untappd using a
   lawful, technically feasible method without Premium or CSV.
3. Accepts photos of beer menus through Telegram.
4. Extracts structured beer entries using OCR and parsing.
5. Matches recognized entries to canonical beer records.
6. Allows users to correct and confirm recognized entries.
7. Ranks available beers using a simple personalized RecSys.
8. Returns TOP-3 recommendations through Telegram.

The product is NOT a generic beer rating application.
It is a personalized beer selection assistant.

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

- Python 3.12
- FastAPI
- aiogram 3
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic
- Docker Compose
- pytest
- Ruff
- scikit-learn for the initial RecSys

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

## ML Rules

Start with a simple, interpretable recommendation algorithm.

Do not introduce neural networks, embeddings, vector
databases, or collaborative filtering without evidence
that they improve the MVP.

The recommendation engine should accept:

- A user's historical beer ratings.
- A list of available beer candidates.

It should return:

- Ranked candidate identifiers.
- Predicted preference scores.
- Short recommendation explanations.

## OCR Rules

Separate image processing, OCR, menu parsing,
beer matching, and user confirmation.

Keep original recognized text for debugging.

Do not silently replace uncertain matches with
supposedly correct beer identities.

Allow unrecognized beers to remain unresolved.

## Untappd Integration Rules

The project must not depend on Untappd Premium or CSV export.

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
