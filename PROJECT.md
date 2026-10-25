
# UntapptSelector — Product Specification

## 1. Vision

UntapptSelector is a personalized beer recommendation assistant
operated through a Telegram bot.

Its purpose is to help a user choose the beer they are most
likely to enjoy from a real-world beer menu.

Recommendations are based primarily on the user's personal
beer rating history from Untappd.

## 2. Problem

Users may encounter beer menus containing dozens of unfamiliar
beers.

Choosing based on general community ratings does not
necessarily reflect individual taste.

The user already has useful preference information stored
in their personal Untappd beer history.

UntapptSelector should use that information to make
personalized recommendations.

## 3. Primary User Journey

1. User opens the UntapptSelector Telegram bot.
2. User links or identifies their Untappd profile.
3. The system obtains historical beer ratings.
4. The system builds a personal taste profile.
5. User takes a photo of an available beer menu.
6. User sends the photo to the Telegram bot.
7. The system performs OCR on the photo.
8. The system extracts individual beer entries.
9. The system matches the entries to known beers.
10. The user reviews and corrects recognized beers.
11. The recommendation engine ranks available beers.
12. The bot presents the TOP-3 personalized choices.

Historical data acquisition must be implemented through
a verified, permitted mechanism that does not require
Untappd Premium or CSV export.

## 4. Main Product Capabilities

### User Management
- Telegram-based identification.
- Association with a personal Untappd profile.
- Persistent personal preferences.

### Beer History
- Import historical beer ratings.
- Normalize beer names and identifiers.
- Preserve individual ratings.
- Support future history updates.

### Menu Recognition
- Receive photos through Telegram.
- Recognize text using OCR.
- Extract individual beer entries.
- Identify breweries, beer names and available attributes.
- Support uncertain or incomplete recognition.
- Allow user confirmation and corrections.

### Recommendation System
- Build a profile from historical ratings.
- Evaluate beers available on the current menu.
- Predict personal preference scores.
- Rank candidate beers.
- Return TOP-3 with short explanations.

## 5. MVP Scope

The MVP includes:

- Telegram Bot.
- Beer history acquisition interface.
- Persistent database.
- Photo processing.
- OCR.
- Menu parsing.
- Beer matching.
- User confirmation.
- Simple personalized recommendation algorithm.
- TOP-3 results.

## 6. Out of Scope

Do not implement these unless explicitly requested:

- Web frontend.
- Mobile applications.
- Social recommendation features.
- Collaborative filtering.
- Complex neural recommendation models.
- Geolocation-based venue discovery.
- Subscription payments.
- Large distributed infrastructure.

## 7. Success Criteria

The MVP is successful when:

1. A Telegram user can start the bot.
2. The system can load a usable personal rating history.
3. The user can submit a photo of a beer menu.
4. The menu is converted into structured beer candidates.
5. The user can correct recognition errors.
6. The system produces a ranked recommendation list.
7. The bot displays TOP-3 recommendations.
8. The workflow is covered by automated tests.

## 8. Product Principles

Personalization over global popularity.

User confirmation over silent OCR assumptions.

Simplicity over algorithmic complexity.

Replaceable integrations over vendor lock-in.

Correctness and transparency over fabricated confidence.

## 9. Current Project Status

System architecture has been designed.

Data architecture has been designed.

Infrastructure scaffolding is in progress.

The full end-to-end MVP is not yet implemented.

Untappd history acquisition without Premium or CSV
remains an unresolved integration risk.

Update this section only when implementation progress
has actually been verified.
