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

  | Variable | Description |
  |---|---|
  | `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
  | `STIXMAGIC_API_KEY` | Auto-generated key for the REST API |
  | `SESSION_SECRET` | Flask session secret |

  ---

  ## License

  MIT
  