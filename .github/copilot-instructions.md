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
| Hosting | Replit |

---

## Repository Structure

```
stixmagic-bot/
├── main.py                   # Bot entry point; conversation handlers; wires adapters
├── menus.py                  # Inline menu definitions (MENU_STRUCTURE dict + keyboard builder)
├── api.py                    # Flask REST API with auth, CORS, pagination
├── pipeline_adapter.py       # Bridges pipeline manifests to core engine
│
├── config/
│   └── runtime.py            # APP_ENV resolution, token/key/secret validation, get_settings()
│
├── core/
│   ├── engine.py             # StixCoreEngine — platform-agnostic sticker generation
│   ├── types.py              # Shared input/result dataclasses (PackGenerationInput, etc.)
│   └── contracts.py          # Abstract interfaces / protocols
│
├── domain/
│   └── media.py              # Re-exports src/stickers/media for backward compatibility
│
├── infra/
│   └── db.py                 # All raw SQL (init_db, CRUD for packs / catalog / settings)
│
├── src/
│   ├── bot/
│   │   ├── forge_wizard.py   # Pack creation wizard (ForgeDraft, ForgeStep, keyboards)
│   │   └── runtime.py        # build_runtime_summary() helper
│   ├── config/
│   │   └── settings.py       # RuntimeSettings dataclass + load_runtime_settings()
│   ├── core/
│   │   ├── runtime.py        # ApplicationRuntime + build_runtime()
│   │   └── plugins.py        # PluginRegistry
│   ├── plugins/              # Optional feature plugins (e.g. truck_club)
│   ├── stickers/
│   │   └── media.py          # Canonical media pipeline (convert_to_sticker, apply_mask, etc.)
│   ├── animations/           # Animation preset helpers
│   ├── adapters/             # Platform-agnostic adapter base classes
│   └── types/
│       └── plugin.py         # PluginManifest, PluginCommand dataclasses
│
├── platforms/
│   ├── telegram/
│   │   └── adapter.py        # TelegramStixAdapter (wraps StixCoreEngine for Telegram)
│   └── discord/              # Future Discord adapter
│
├── loaders/                  # Animated loader system shown during processing
│   ├── controller.py         # LoaderController
│   ├── definitions.py        # Loader animation definitions
│   ├── render.py             # Renders loader frames to Telegram messages
│   └── selection.py          # Picks loader for context
│
├── pipeline/                 # Asset pipeline for pre-built sticker pack manifests
│   ├── manifest.py
│   ├── packager/
│   ├── exporters/
│   └── metadata/
│
├── moderation/
│   └── plugin.py             # Content moderation plugin
│
├── packs/                    # Pre-built sticker pack definitions (manifests)
├── assets/                   # Source assets (source/, processed/, previews/)
├── renders/                  # Build output — webm, webp, gif, thumbnails (not committed)
├── scripts/
│   ├── smoke_test.py         # Quick import / config sanity check
│   ├── validate_runtime.py   # Validates runtime settings at startup
│   └── check_config.py       # Config validation helper
├── static/
│   ├── index.html            # Landing page
│   ├── api.html              # Interactive API docs
│   └── miniapp.html          # Telegram Mini App
├── tests/                    # Test suite
├── requirements.txt
└── pyproject.toml
```

---

## Core Principles

- **Bot commands** live in `main.py` as `ConversationHandler` or plain command handlers.
- **Pack creation wizard** lives in `src/bot/forge_wizard.py`; stores a `ForgeDraft` in `context.user_data['forge_draft']`.
- **Inline menus** are declared in `MENU_STRUCTURE` inside `menus.py`; `build_keyboard()` and `get_menu_text()` render them. Add new menu pages there, not inline.
- **API endpoints** follow the `/api/<resource>` pattern and use the `ok()` / `err()` helpers from `api.py`. All authenticated routes use `@require_api_key`.
- **Database** — all raw SQL lives in `infra/db.py`. Never use `sqlite3` directly outside that module. No ORM — use parameterised queries only.
- **Media pipeline**: static images → Pillow → WEBP ≤ 64 KB; video/GIF → ffmpeg VP9 WEBM ≤ 256 KB, max 3 s, 512 px. Canonical implementation is `src/stickers/media.py`; `domain/media.py` re-exports it for backward compatibility.
- **Config** — always call `config.runtime.get_settings()` to read settings; never read `os.environ` directly in handlers or business logic.
- **Platform adapters** wrap `StixCoreEngine` (in `core/engine.py`) for each platform (see `platforms/telegram/adapter.py`).

---

## Environment & Config

`config/runtime.py` validates and resolves all settings at startup.

| Variable | Required | Notes |
|---|---|---|
| `APP_ENV` | Yes | Must be exactly `development` or `production` (case-sensitive) |
| `TELEGRAM_BOT_TOKEN` | production | Used when `APP_ENV=production` |
| `DEV_BOT_TOKEN` | development | Used when `APP_ENV=development` |
| `STIXMAGIC_API_KEY` | Yes | API key for REST endpoints |
| `SESSION_SECRET` | Yes | Flask session secret |
| `MINIAPP_URL` | No | Overrides Mini App URL |
| `REPLIT_DOMAINS` | No | Replit-injected public hostname |

Rules:
- Never mix dev and prod tokens.
- Dev builds must not affect production data; prefix dev artifacts (e.g. `dev_*` packs).
- Exactly one of `TELEGRAM_BOT_TOKEN` / `DEV_BOT_TOKEN` must be set per environment.

---

## Coding Conventions

- Python 3.11+, async/await throughout bot handlers.
- Keep handlers small; delegate media processing to helper functions in `src/stickers/media.py`.
- Use `ConversationHandler` states as `int` constants at the top of `main.py`.
- API responses always use the `{"ok": true/false, "data": ...}` envelope.
- Inline keyboard buttons use `callback_data` strings like `"menu_<action>"` or `"nav:<menu_id>"`.
- Do not commit secrets or tokens; always read from `config.runtime.get_settings()`.
- Always escape user-supplied strings with `html.escape()` before interpolating into `parse_mode="HTML"` messages.

---

## Database Schema

All table creation is handled by `infra.db.init_db()`, called at bot startup.

```sql
CREATE TABLE packs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name    TEXT NOT NULL,   -- Telegram pack name (stix_<uid>_<rand>_by_<bot>)
    title   TEXT NOT NULL    -- Display title
);

CREATE TABLE user_settings (
    user_id         INTEGER PRIMARY KEY,
    mask_inverted   INTEGER DEFAULT 0
);

CREATE TABLE catalog_packs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    type        TEXT DEFAULT 'image',
    public      INTEGER DEFAULT 1,
    safe        INTEGER DEFAULT 1,
    likes       INTEGER DEFAULT 0,
    dislikes    INTEGER DEFAULT 0,
    view_count  INTEGER DEFAULT 0,
    added_at    INTEGER NOT NULL,
    added_by    INTEGER
);

CREATE TABLE catalog_reactions (
    user_id   INTEGER NOT NULL,
    pack_name TEXT NOT NULL,
    reaction  TEXT NOT NULL,   -- 'like' | 'dislike'
    PRIMARY KEY (user_id, pack_name)
);
```

---

## PR / Issue Workflow

- Keep PRs small and focused on a single feature or fix.
- Reference the related Issue number in the PR description.
- Preferred order of changes per PR: database (`infra/db.py`) → service logic → bot handler → menu → API endpoint → tests.
