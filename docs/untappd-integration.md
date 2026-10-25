# Untappd integration status

Reviewed on 2026-10-25 using official documentation and the developer-portal
notice supplied by the project owner.

## Implemented

The bot stores a user-supplied username in `external_accounts`, scoped by the
internal user UUID and provider. The username is normalized to lowercase. Repeated
commands reuse the same row; a new username replaces the previous one. These
records are unverified and do not contain passwords, API keys or OAuth tokens.
No request to Untappd is made, and no ratings are imported.

This identifies a profile chosen by the user; it does not establish account
ownership. Another Telegram user may independently enter the same public username.

## Verified documentation

[API documentation](https://untappd.com/api/docs) describes:

- User history at `/v4/user/checkins/USERNAME`, paginated with `max_id`, up to
  25 records per request.
- Application credentials (`client_id` and `client_secret`) or an OAuth access token
  for requests; an app-specific User-Agent is required.
- Server-side OAuth with a registered callback URL and the optional `state`
  parameter, which an implementation must use to bind authorization to its user.
- A default rate limit of 100 requests per hour, with response headers for remaining quota.

The documented history endpoint does not list Premium or CSV as prerequisites.
That alone does not establish permitted use or working access for this project.
[The developer portal](https://untappd.com/api) requires login. The project owner
provided its notice: API access is now available only under a commercial
agreement, and existing API tokens may stop working. Questions about access
should go to api.requests@untappd.com. No agreement or usable project
credentials have been confirmed. No authenticated API requests or real history
imports were tested.

## Blocking conditions for real history import

[API Terms of Use](https://untappd.com/terms/api), specifically items 13–16, impose
24-hour cache deletion, prohibit building a beer database from API data and
restrict analysis of API data. These restrictions may conflict with persistent
rating storage and personalized recommendations in the target architecture.

Arrange commercial access and obtain clarification or explicit permission from
Untappd for the proposed storage and recommendation use before implementing an
API importer. This is an unresolved integration condition, not an assumption that
OAuth or Premium resolves it. No private endpoints or scraping fallback is implemented.

Until then, future history and recommendation work should use explicitly synthetic
test fixtures, independent of live Untappd data. This change has no history adapter
or fake production import path.
