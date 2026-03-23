# STIX MΛGIC

STIX MΛGIC is now organized as **one Telegram-native product system** with two connected surfaces:

- **Bot surface** — owns sticker creation, media upload, pack mutation, Telegram-native flows, and automation.
- **Mini App surface** — owns authenticated account views, pack browsing, catalog discovery, and bot hand-off UX.
- **Shared backend/core** — owns environment resolution, SQLite persistence, API contracts, and Telegram Mini App auth validation.

## New architecture

```text
Telegram User
   ├─> Telegram Bot (main.py)
   │     ├─ creates / mutates sticker packs
   │     ├─ runs polling runtime today
   │     └─ exposes deep-link entrypoints used by the Mini App
   │
   └─> Telegram Mini App (static/miniapp.html)
         ├─ authenticates with Telegram initData
         ├─ calls /api/miniapp/* using shared auth rules
         ├─ reads the same packs/settings/catalog data model
         └─ hands the user back to the bot for pack-creation/media actions

Shared product backend
   ├─ api.py                  Flask API + landing/docs routes
   ├─ infra/db.py             shared SQLite persistence
   └─ stixmagic/
      ├─ settings.py          shared environment + deployment settings
      ├─ contracts.py         shared product constants / start payloads
      └─ telegram_auth.py     Telegram Mini App initData verification
```

## How the bot and Mini App now connect

1. The bot publishes the Mini App URL using the same shared settings resolver used by the backend.
2. The Mini App authenticates every private request with Telegram `initData` via `X-Telegram-Init-Data`.
3. The backend validates that signature against the bot token before returning packs/settings/bootstrap metadata.
4. The Mini App receives bot deep links from `/api/miniapp/bootstrap` and uses them for create/add/manage/feature hand-offs.
5. The bot understands shared `/start` payloads so the hand-off lands in the correct production flow.

## Production-minded environment model

The repo now treats configuration as shared product configuration instead of separate bot vs web guesses.

### Core variables

| Variable | Required | Purpose |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | yes | Used by the bot runtime and Mini App auth verification. |
| `TELEGRAM_BOT_USERNAME` | recommended | Canonical bot username used for deep links from the Mini App. |
| `STIXMAGIC_API_KEY` | yes for admin API | Auth for non-Mini-App admin API routes. |
| `STIXMAGIC_PUBLIC_BASE_URL` | recommended in prod | Canonical public origin for landing/API/Mini App URLs. |
| `STIXMAGIC_DB_PATH` | recommended | Shared database file path for bot + API. |
| `TELEGRAM_BOT_MODE` | recommended | Explicit runtime mode (`polling` today, `webhook` planned). |
| `TELEGRAM_WEBHOOK_URL` | optional | Reserved for future webhook runtime work. |
| `TELEGRAM_WEBHOOK_SECRET` | optional | Reserved for future webhook runtime work. |

Legacy `MINIAPP_URL` is still accepted as an override, but the preferred production path is `STIXMAGIC_PUBLIC_BASE_URL + /miniapp`.

## Deployments

### Bot deployment
- Starts in `main.py`.
- Uses the shared settings layer.
- Still runs `run_polling()` today.
- Sets the Telegram menu button to the shared Mini App URL when available.

### Web/API deployment
- Starts in `api.py`.
- Serves `/`, `/api`, `/miniapp`, `/api/*`.
- Uses the same DB file and the same env model as the bot.
- Owns Mini App bootstrap/auth endpoints.

## What changed in this refactor

- Added a shared `stixmagic/` module for settings, contracts, and Telegram Mini App auth.
- Unified DB path, public URL resolution, and bot username handling across bot/API/menu code.
- Replaced weak Mini App `sendData`/postMessage scaffolding for private pack data with authenticated API calls.
- Turned the Mini App into a real product surface for browsing + authenticated account state, while making bot hand-offs explicit for actions that still belong in Telegram bot flows.
- Added shared `/start` payload handling so Mini App actions open the correct bot flow.
- Updated production docs and env documentation to describe one system instead of separate experiments.

## What is still not production-ready

1. **Webhook runtime is not implemented yet.** `TELEGRAM_BOT_MODE=webhook` is now explicit in config, but the actual HTTP update ingress still needs to be built.
2. **Destructive pack management is still bot-only.** The Mini App does not yet have authenticated mutation endpoints for rename/delete.
3. **Pack creation still depends on conversational bot UX.** The Mini App can prepare and route users into it, but does not yet upload media directly to a shared backend workflow.
4. **SQLite is still the persistence layer.** Fine for lean deployments, but not ideal for multi-instance scaling.
5. **Operational hardening is still limited.** There is no structured secrets rotation, background job queue, or observability stack yet.

## Recommended next steps

1. Implement webhook ingestion and make `TELEGRAM_BOT_MODE=webhook` fully deployable.
2. Add authenticated Mini App mutation APIs for delete/rename/feature actions where Telegram permits safe server-side execution.
3. Extract shared application services from `main.py` / `api.py` so business logic no longer lives inside handlers.
4. Move from SQLite to a production database before multi-instance deployment.
5. Add request logging, error reporting, and deployment health instrumentation.

## Local development

```bash
python -m compileall main.py api.py stixmagic infra
python api.py        # serves landing page + Mini App + API
python main.py       # runs the bot polling worker
```

## Additional docs

- `docs/architecture.md` — updated repository/product architecture.
- `.env.example` — shared environment template.
