# Stix Magic Bot — Copilot Instructions

## Project Overview

**Stix Magic** is a Telegram-first sticker creation and management platform.
Users interact entirely through a Telegram bot (`@stixmagicbot`) to build, cut, and manage sticker packs.
A Flask REST API and a Telegram Mini App run alongside the bot.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | python-telegram-bot v21 (async) |
| Image processing | Pillow |
| Video processing | ffmpeg (libvpx-vp9) |
| Database | SQLite (`sqlite3`) |
| Web server | Flask |
| Hosting | Replit / Docker |

---

## Repository Structure

```
stixmagic-bot/
├── main.py          # Bot logic, conversation handlers, command routing
├── menus.py         # Inline menu definitions (MENU_STRUCTURE dict + keyboard builder)
├── api.py           # Flask REST API with auth, CORS, rate limiting, pagination
├── domain/
│   └── media.py     # Sticker media pipeline (image, video, mask); pure sync +
│                    # async_* wrappers for executor offloading
├── infra/
│   └── db.py        # SQLite layer: db_conn() context manager, WAL, event log
├── static/
│   ├── index.html   # Landing page
│   ├── api.html     # Interactive API docs
│   └── miniapp.html # Telegram Mini App
├── Dockerfile       # Container build (Python 3.11-slim + ffmpeg)
├── .env.example     # Environment variable template
├── ARCHITECTURE.md  # Platform architecture decision record
├── requirements.txt
└── pyproject.toml
```

---

## Core Principles

- **Bot commands** live in `main.py` as `ConversationHandler` or plain command handlers.
- **Inline menus** are declared in `MENU_STRUCTURE` inside `menus.py`; `build_keyboard()` and `get_menu_text()` render them. Add new menu pages there, not inline.
- **API endpoints** follow the `/api/<resource>` pattern and use the `ok()` / `err()` helpers from `api.py`. All authenticated routes use `@require_api_key`. All routes use `@rate_limit`.
- **Database** is accessed exclusively via `db_conn()` context manager from `infra/db.py`. Use parameterised queries only — never interpolate user input into SQL.
- **Media pipeline**: synchronous processing functions live in `domain/media.py`; bot handlers **must** call the `async_*` wrappers (e.g. `async_convert_to_sticker`) so blocking work runs in a thread-pool executor and never stalls the asyncio event loop.
- **Event logging**: call `log_event()` via `asyncio.get_running_loop().run_in_executor()` inside async handlers to keep it non-blocking.
- **Environment variables**: `TELEGRAM_BOT_TOKEN`, `STIXMAGIC_API_KEY`, `CORS_ALLOW_ORIGIN`, `TRUST_PROXY`, `ADMIN_USER_IDS`, `MINIAPP_URL` (optional), `REPLIT_DOMAINS` (optional).

---

## Coding Conventions

- Python 3.11+, `async`/`await` throughout bot handlers.
- Keep handlers small; delegate media processing to `domain/media.py` helpers.
- Use `ConversationHandler` states as `int` constants at the top of `main.py`.
- API responses always use the `{"ok": true/false, "data": ...}` envelope.
- Inline keyboard buttons use `callback_data` strings like `"menu_<action>"` or `"nav:<menu_id>"`.
- The `_MENU_DISPATCH` dict in `main.py` is populated once at startup — add new callback actions there rather than extending the if/elif chain.
- Do not commit secrets or tokens; always read from `os.environ`.
- Use `asyncio.get_running_loop()` (not `get_event_loop()`) inside async functions.

---

## Database Schema

```sql
CREATE TABLE packs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,    -- Telegram pack name (stix_<uid>_<rand>_by_<bot>)
    title      TEXT NOT NULL,    -- Display title
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE user_settings (
    user_id         INTEGER PRIMARY KEY,
    mask_inverted   INTEGER DEFAULT 0
);

CREATE TABLE event_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    event      TEXT NOT NULL,    -- e.g. "pack_created", "sticker_added"
    detail     TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
```

All DB access goes through `infra/db.py` helpers — never import `sqlite3` directly in `main.py` or `api.py`.

---

## API Endpoints

```
GET  /                         Landing page (public)
GET  /api/health               Health check (public, rate-limited)
GET  /api/miniapp/packs        Mini App: user packs (rate-limited)
GET  /api/miniapp/settings     Mini App: user settings (rate-limited)
PATCH /api/miniapp/settings    Mini App: update settings (rate-limited)

# Authenticated (X-API-Key header or ?api_key=)
GET  /api/stats                Platform usage stats
GET  /api/events               Top event counts (observability)
GET  /api/search?q=<query>     Search packs by name/title
GET  /api/packs/<user_id>      List user's packs
GET  /api/packs/<uid>/<name>   Pack detail
DELETE /api/packs/<uid>/<name> Remove pack record
GET  /api/settings/<user_id>   User settings
PATCH /api/settings/<user_id>  Update user settings
```

---

## PR / Issue Workflow

- Keep PRs small and focused on a single feature or fix.
- Reference the related Issue number in the PR description.
- Preferred order of changes per PR: `infra/db.py` → `domain/media.py` → `main.py` → `menus.py` → `api.py` → docs.
