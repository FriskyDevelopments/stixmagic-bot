# STIX MΛGIC architecture

## Product model

STIX MΛGIC is no longer documented as a loose bot plus experimental web UI.
It is a **single Telegram-native product** with two user surfaces and one shared backend/core.

### Surfaces

- **Bot surface (`main.py`)**
  - Telegram conversations
  - sticker pack creation / mutation
  - media processing
  - catalog publishing flow
  - Mini App entrypoint publishing via Telegram menu button

- **Mini App surface (`static/miniapp.html`)**
  - authenticated account view using Telegram Mini App `initData`
  - pack browsing and synced state
  - catalog discovery and reactions
  - clear hand-off back to bot for Telegram-native pack operations

- **Shared backend/core**
  - `api.py` for HTTP routes and Mini App bootstrap
  - `infra/db.py` for persistence
  - `stixmagic/settings.py` for env resolution
  - `stixmagic/contracts.py` for start payloads / constants
  - `stixmagic/telegram_auth.py` for Mini App request authentication

## Connection model

```text
Mini App launch inside Telegram
    -> sends initData to /api/miniapp/bootstrap
    -> backend validates signature with TELEGRAM_BOT_TOKEN
    -> backend returns user identity + bot deep links + deployment metadata
    -> Mini App loads packs/settings from authenticated /api/miniapp/* routes
    -> user hands off into bot deep links for create/add/manage/feature flows
```

## Deployment model

### Current state

- **Bot runtime:** polling worker only.
- **Web runtime:** Flask app for landing page, docs, Mini App, and JSON API.
- **Persistence:** single SQLite database shared by both runtimes.

### Explicit configuration

The code now expects one coherent environment strategy:

- public origin from `STIXMAGIC_PUBLIC_BASE_URL`
- DB path from `STIXMAGIC_DB_PATH`
- bot username from `TELEGRAM_BOT_USERNAME`
- runtime mode from `TELEGRAM_BOT_MODE`
- Mini App auth verified with `TELEGRAM_BOT_TOKEN`

## What still blocks full production deployment

1. Webhook ingestion for Telegram updates is still missing.
2. Mini App write operations are not fully server-backed yet.
3. SQLite remains a single-node constraint.
4. Shared service-layer extraction from handlers is still incomplete.
