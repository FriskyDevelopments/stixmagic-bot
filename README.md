# 🪄 Stix Magic Bot

  > **Telegram sticker alchemy bot** — create, cut, and manage sticker packs with ease.

  **Bot:** [@stixmagicbot](https://t.me/stixmagicbot) &nbsp;|&nbsp; **Website:** [stixmagic.com](https://stixmagic.com)

  ---

  ## What It Does

  Stix Magic lets you build and manage Telegram sticker packs without leaving the chat. Send any image or short video and it becomes a sticker instantly. The `/magic` command uses a black-and-white mask photo to cut a subject cleanly out of any background.

  ---

  ## Commands

  | Command | Description |
  |---|---|
  | `/start` | Open the main menu |
  | `/newpack` | Create a new sticker pack |
  | `/addsticker` | Add a sticker to one of your packs |
  | `/magic` | Cut a subject from its background using a B&W mask |
  | `/mypacks` | Browse and manage your packs |
  | `/settings` | Toggle mask inversion and other preferences |
  | `/help` | Show help information |
  | `/cancel` | Cancel the current operation |

  ---

  ## Features

  ### Sticker Pack Management
  - Create packs with a custom name and emoji
  - Add unlimited stickers to any of your packs
  - Delete packs with a confirmation step
  - Direct Telegram links on every pack button — tap to open in-app
  - "Add Another" shortcut after adding a sticker (no re-navigation required)

  ### Media Handling
  - **Static images** → converted to WEBP via Pillow, compressed to ≤ 64 KB
  - **Videos / GIFs** → converted to VP9 WEBM via ffmpeg (≤ 256 KB, max 3 s, 512 px)
  - Supports JPEG, PNG, GIF, MP4, and more

  ### Magic Cut (`/magic`)
  - Send a **subject photo** then a **black-and-white mask** (white = keep, black = remove)
  - The bot composites them and produces a clean cut-out sticker
  - Step 1 / Step 2 progress indicators in the flow
  - Mask inversion toggle in `/settings` (for dark-background masks)

  ### Inline Menu System
  - Color-coded button groups: 🟣 Create · 🔵 Explore · 🟠 Info
  - 2-column keyboard layout with context-aware body text
  - In-place message updates (no chat clutter)
  - Cancel buttons throughout every conversation flow

  ---

  ## REST API

  A Flask-based REST API runs alongside the bot.

  **Base URL:** `https://stixmagic.com/api`  
  **Auth:** `X-API-Key: <your-key>` header (or `?api_key=` param)  
  **Docs:** `/api` — interactive dark-themed reference page

  ### Endpoints

  | Method | Path | Auth | Description |
  |---|---|---|---|
  | GET | `/api/health` | Public | Service + DB status |
  | GET | `/api/stats` | Required | User and pack counts |
  | GET | `/api/search` | Required | Search packs by name/title |
  | GET | `/api/packs` | Required | List all packs (paginated) |
  | GET | `/api/packs/<id>` | Required | Get a single pack |
  | POST | `/api/packs` | Required | Create a pack |
  | DELETE | `/api/packs/<id>` | Required | Delete a pack |
  | GET | `/api/settings/<user_id>` | Required | Get user settings |
  | PATCH | `/api/settings/<user_id>` | Required | Update user settings |

  All responses use a consistent envelope:

  ```json
  { "ok": true, "data": { ... } }
  { "ok": false, "error": { "message": "...", "code": "..." } }
  ```

  ---

  ## Tech Stack

  | Layer | Technology |
  |---|---|
  | Bot framework | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v21 |
  | Image processing | [Pillow](https://python-pillow.org/) |
  | Video processing | [ffmpeg](https://ffmpeg.org/) (libvpx-vp9) |
  | Database | SQLite (via built-in `sqlite3`) |
  | Web server | [Flask](https://flask.palletsprojects.com/) |
  | Hosting | Replit |

  ---

  
## Runtime Boundaries

The repository now separates two related responsibilities:

- **Main bot system** in `src/bot`, `src/stickers`, `src/animations`, `src/core`, and `src/config` for shared sticker, timing, animation, and runtime logic.
- **The Truck Club plugin** in `src/plugins/truck_club` for community-specific commands, hooks, metrics, and configuration.

Legacy import paths such as `domain/media.py` and `pipeline_adapter.py` remain as compatibility shims, but new work should target the `src/` packages.

## Project Structure

  ```
  stixmagic-bot/
  ├── main.py              ← Bot entry-point (Layer 1 – Bot)
  ├── api.py               ← Flask REST API + web UI
  ├── menus.py             ← Inline keyboard registry
  ├── domain/              ← Bot media processing (Pillow, ffmpeg)
  ├── infra/               ← SQLite persistence layer
  ├── static/              ← Landing page + Mini App HTML
  │
  ├── pipeline/            ← Visual asset pipeline (Layers 2–5)
  │   ├── asset_model/     ← Asset dataclass, category/theme enums
  │   ├── metadata/        ← AssetCatalog (JSON I/O, assets/catalog.json)
  │   ├── motion_presets/  ← 10 built-in MotionPreset definitions
  │   ├── exporters/       ← GIF / WebP / WebM / MOV / PNG / thumbnail
  │   └── packager/        ← PackDefinition + build_pack()
  │
  ├── assets/              ← Raw and processed asset files
  │   ├── source/          ← Category sub-directories (letters, numbers, …)
  │   ├── processed/       ← Normalised base assets
  │   └── previews/        ← Static preview images
  │
  ├── renders/             ← Export pipeline outputs
  │   ├── gif/
  │   ├── webp/
  │   ├── webm/
  │   ├── mov/
  │   ├── png_sequences/
  │   └── thumbnails/
  │
  ├── packs/               ← Per-pack JSON metadata
  │   ├── motion_alphabet/ ← MagicStix Motion Alphabet
  │   ├── neon_signals/    ← MagicStix Neon Signals
  │   ├── dj_pack/         ← MagicStix DJ Pack
  │   ├── cloud_pack/      ← MagicStix Cloud Pack
  │   └── overlay_starter/ ← MagicStix Overlay Starter Pack
  │
  ├── integrations/        ← Future integration scaffolding
  │   ├── extension/       ← Browser / Nebulosa extension (future)
  │   ├── overlay_engine/  ← OBS-style compositor (future)
  │   └── virtual_camera/  ← Virtual camera output (future)
  │
  ├── docs/                ← Architecture and developer guides
  │   ├── architecture.md
  │   ├── pipeline.md
  │   ├── asset_schema.md
  │   ├── motion_system.md
  │   ├── export_formats.md
  │   ├── pack_generation.md
  │   └── future_integrations.md
  │
  ├── requirements.txt     ← Python dependencies
  └── pyproject.toml       ← Project metadata
  ```

  See [`docs/architecture.md`](docs/architecture.md) for the full five-layer architecture overview.

  ---

  ## Visual Asset Pipeline

  The MagicStix pipeline transforms bot-generated base assets into multiple
  export formats via reusable motion presets, then groups outputs into themed
  product packs.

  ```
  Base asset (PNG/WebP)
        │
        ▼  pipeline/motion_presets/
  Motion preset (pulse, glow, sparkle, …)
        │
        ▼  pipeline/exporters/
  Multiple outputs:
    letter_A_pulse.gif
    letter_A_pulse.webp
    letter_A_pulse.webm
    letter_A_pulse_thumb.png
        │
        ▼  pipeline/packager/
  Pack:  MagicStix Motion Alphabet
  ```

  **Quick start:**

  ```python
  from pipeline.metadata import AssetCatalog
  from pipeline.motion_presets import get_preset
  from pipeline.exporters import export_all

  catalog = AssetCatalog(auto_load=True)
  asset   = catalog.get("letter_A")
  result  = export_all(asset.id, asset.source_path, get_preset("pulse"))
  print(result.sticker_ready_outputs)
  ```

  ---

  ## Database Schema

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
  ```

  ---

  ## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | ✅ | Runtime target: `development`, `production`, or `test` |
| `BOT_TOKEN_DEV` / `BOT_TOKEN_PROD` | ✅ | Telegram bot token for the selected environment |
| `STIXMAGIC_API_KEY_DEV` / `STIXMAGIC_API_KEY_PROD` | ✅ | REST API authentication key for the selected environment |
| `SESSION_SECRET_DEV` / `SESSION_SECRET_PROD` | Recommended | Flask session secret; production should always set one |
| `MINIAPP_URL_DEV` / `MINIAPP_URL_PROD` | Optional | Telegram Mini App URL for the selected environment |

Legacy aliases remain supported for compatibility: `TELEGRAM_BOT_TOKEN`, `STIXMAGIC_API_KEY`, `SESSION_SECRET`, and `MINIAPP_URL`.

---

## Setup & Development Workflows

### Local development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy the example environment file and fill in only development values:
   ```bash
   cp .env.example .env
   ```
3. Validate configuration before starting the bot:
   ```bash
   APP_ENV=development python scripts/check_config.py
   ```
4. Run the bundled smoke test (config + DB init):
   ```bash
   APP_ENV=development python scripts/smoke_test.py
   ```
5. Start the bot and bundled Flask API together:
   ```bash
   APP_ENV=development python main.py
   ```

### GitHub Actions

The repository now uses three workflows:

- `ci.yml` — runs on pull requests and pushes to `main`; installs dependencies, runs a syntax check, validates runtime config, and performs the local smoke test.
- `development.yml` — manual/on-branch development workflow that validates the development secret set using `BOT_TOKEN_DEV`.
- `production.yml` — manual production-prep workflow that validates the production secret set using `BOT_TOKEN_PROD` without auto-deploying.

### Required GitHub Actions secrets

Required now:

| Secret | Purpose |
|---|---|
| `BOT_TOKEN_DEV` | Development Telegram bot token |
| `BOT_TOKEN_PROD` | Production Telegram bot token |

Recommended environment-specific secrets:

| Secret | Purpose |
|---|---|
| `STIXMAGIC_API_KEY_DEV` / `STIXMAGIC_API_KEY_PROD` | Separate API keys per environment |
| `SESSION_SECRET_DEV` / `SESSION_SECRET_PROD` | Separate Flask session secrets per environment |
| `MINIAPP_URL_DEV` / `MINIAPP_URL_PROD` | Separate Mini App URLs per environment |

If your repository still only has the legacy unsuffixed API, session, or Mini App secrets, the workflows and runtime still accept them as fallbacks. Bot token handling is now normalized around `BOT_TOKEN_DEV` and `BOT_TOKEN_PROD`.

### Automated verification scope

CI and the dev/prod workflows intentionally stop at safe validation and smoke testing. They do **not** start long-running Telegram polling in GitHub Actions, and they do **not** attempt flaky live Telegram end-to-end interactions. Manual verification is still required for: sticker creation, animated/video sticker uploads, Mini App button behavior, and production deployment wiring.

---

## License

  MIT
  