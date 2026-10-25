
# UntapptSelector — System Architecture

## 1. Architectural Style

The system is a modular monolith.

One Python codebase hosts the application and its modules.

A separate background worker process may use the same
codebase and PostgreSQL database.

Do not introduce independent microservices by default.

## 2. System Components

### Telegram Adapter

Responsible for:
- Receiving Telegram messages.
- Accepting photos.
- Managing conversation states.
- Displaying recognition results.
- Displaying recommendations.

Does not implement domain algorithms.

### Application Core

Responsible for:
- Orchestrating user workflows.
- Coordinating modules.
- Managing application operations.
- Handling errors and state transitions.

### History Integration

Responsible for:
- Connecting to a permitted rating data source.
- Retrieving historical ratings.
- Normalizing imported records.
- Synchronizing rating history.

Implementation must not rely on Premium CSV exports.

### Menu Recognition

Pipeline:

Image Input
  -> Image Preprocessing
  -> OCR
  -> Text Structuring
  -> Beer Entity Extraction
  -> Beer Matching
  -> User Confirmation
  -> Confirmed Candidates

Preserve uncertainty and original OCR text.

### Beer Catalog

Responsible for:
- Canonical beer entities.
- Breweries.
- Beer aliases.
- Beer identifiers.
- Matching menu entries to beer records.

### User Profiles

Responsible for:
- Historical user ratings.
- Derived personal taste profiles.
- Updating profiles when data changes.

### Recommendation Engine

Inputs:
- User rating history or derived taste profile.
- Confirmed candidate beers.

Outputs:
- Ranked recommendations.
- Personal preference scores.
- Explanations.

The engine is independent of Telegram and OCR.

## 3. Primary Data Flow

Untappd History
    -> History Adapter
    -> Rating Normalization
    -> PostgreSQL
    -> Taste Profile

Telegram Photo
    -> Menu Recognition
    -> Beer Matching
    -> User Confirmation
    -> Confirmed Candidates

Taste Profile + Confirmed Candidates
    -> Recommendation Engine
    -> Ranked Results
    -> Telegram Bot

## 4. Data Storage

Primary database: PostgreSQL.

Main entities:

- users
- external_accounts
- breweries
- beers
- beer_aliases
- external_beer_ids
- user_ratings
- taste_profiles
- menus
- menu_photos
- menu_items
- recommendation_runs
- recommendation_items

Background job infrastructure may add a jobs table.

Store uploaded images separately from relational records.

Use internal UUID identifiers.

External provider identifiers must not be primary keys.

## 5. Repository Layout

Current implementation:

```text
src/                        # Installed Python package; imports use src.*
    __init__.py
    main.py                 # FastAPI application and /health
    core/                   # Shared settings
    telegram/               # Bot startup, /start and /untappd routers
    application/            # User registration and profile orchestration
    modules/
        users/              # Models, contracts and profile validation
    infrastructure/
        database/           # Async sessions and PostgreSQL repositories
alembic/                    # Migration environment and versioned schema changes
tests/
    unit/                   # Application, validation and handler tests
    integration/            # PostgreSQL and Telegram update processing tests
    test_health.py
    test_migrations.py
docs/                       # Project, architecture and integration documentation
    AGENTS.md               # Single source of development instructions
README.md                   # Setup, commands and current capabilities
pyproject.toml
uv.lock
Dockerfile
compose.yaml
```

Run commands from the repository root. The API entry point is `src.main:app`;
the bot entry point is `python -m src.telegram.bot`. The application package is
included in the wheel without an additional nested project-name directory.
Alembic adds the repository root to its import path and shares model metadata
with the application. Moving Python files does not change migration revisions
or require recreating the database.

Planned modules, not yet implemented: `modules/history`, `modules/catalog`,
`modules/menu_recognition`, `modules/profiles`, `modules/recommendations`,
`infrastructure/integrations`, `infrastructure/storage`, `infrastructure/jobs`,
and `workers`. Add `api` routers when there are endpoints beyond the current
health check. Add `tests/e2e` when the end-to-end product flow exists.
Do not create empty directories for future features.

## 6. Technology Decisions

Application language: Python 3.14.

API: FastAPI.

Telegram: aiogram 3.

Database: PostgreSQL.

ORM: SQLAlchemy 2.

Schema migrations: Alembic.

Configuration: Pydantic Settings.

Deployment: Docker Compose.

Unit testing: pytest.

Recommendation baseline: Python / scikit-learn.

OCR implementation is replaceable.

Beer matching may initially use RapidFuzz.

## 7. Background Processing

Use PostgreSQL-backed background jobs for the MVP.

Expected background operations:
- OCR processing.
- History synchronization.
- Profile rebuilding.

Use durable job states and idempotent operations.

Workers must safely handle retries, crashes and timeouts
before production deployment.

Do not add Redis, RabbitMQ or Celery unless justified.

## 8. API and Module Contracts

Modules exchange validated structured data.

The main contracts are:

- Ratings
- Menu Items
- Confirmed Beer Candidates
- Taste Profiles
- Recommendations

Avoid passing provider-specific representations
directly into domain logic.

## 9. Architectural Constraints

- Telegram must not perform SQL queries directly.
- OCR must not call the recommendation engine directly.
- RecSys must not retrieve Untappd history itself.
- Unknown beer matches must not be silently accepted.
- History retrieval must not run on every recommendation.
- External services must not be mandatory for unit tests.
- Personal user data must be isolated and protected.

## 10. Future Evolution

Potential later features:
- Improved recommendation algorithms.
- Better OCR and entity extraction.
- Personalized exploration strategies.
- Additional beer data providers.

These are future capabilities, not MVP requirements.
