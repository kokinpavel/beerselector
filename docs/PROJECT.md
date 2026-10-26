# UntapptSelector — Product Specification

## Objective

Help a Telegram user choose beer from a real menu based on their current wishes,
for example: “strong, Belgian-style”. No Untappd account, historical ratings or
pre-existing database of beer brands is required.

## Target journey

1. User sends a menu photo, optionally with wishes in the caption.
2. Bot recognizes the text, passes it through an LLM and presents only beer names.
3. User may optionally correct the list.
4. Bot asks for wishes if absent, then interprets style and strength criteria.
5. Bot offers up to three matching entries with understandable explanations.

Steps 4–5 are planned. The current development scope is steps 1–3.

## Implemented

- Telegram `/start` persists a user with an internal UUID.
- A private-chat photo handler uses a replaceable local Tesseract OCR adapter.
- Local Ollama LLM cleanup extracts only beer product names with a strict JSON schema.
- Source references and name words are validated; raw OCR, ABV and prices are
  not sent to the user. Original text remains internal.
- User can replace the list with corrected text, display it or cancel.
- Captions are retained in the draft but not yet interpreted.
- Drafts are in memory, scoped by Telegram user and chat, and lost on restart.
- PostgreSQL, Alembic, FastAPI health check and tests are available.

## Current limits

LLM extraction depends on OCR quality and may omit unreadable names. It does
not verify canonical beer identity. Optional editing is available, with no
confirmation requirement. The Ollama model must be downloaded; no paid API key is required.
No recommendations, taste predictions, style inference or preference extraction
are implemented. No representative real-menu recognition quality is claimed.
Tesseract and English/Russian language data are installed in the Docker image.
Use the Compose bot service; no host OCR installation is required.

## Next scope

Interpret free-text wishes using an explicit small vocabulary and a documented
style reference; ask for clarification when the request is unclear. Rank only
recognized menu entries and expose missing information. Do not infer specific
beer properties from an unfamiliar brand name.

Durable menu history and background workers can be added when required; they
are not part of the current in-memory review flow.

## Legacy Untappd functionality

`/untappd` still saves a user-supplied profile. It neither verifies ownership nor
imports ratings, and is not required for menu recognition. API import is blocked
pending commercial access and permission for the proposed use. See
[integration findings](untappd-integration.md).

## Out of scope

Web frontend, mobile app, social features, payments, collaborative filtering,
large ML models, distributed infrastructure and automatic external catalog imports.
