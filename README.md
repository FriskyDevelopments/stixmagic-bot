# 🪄 Stix Magic — Visual Asset Platform

  > **Telegram sticker alchemy bot + multi-format visual asset pipeline.**
  >
  > Create animated stickers, letters, symbols, and overlays — one base asset,
  > many outputs.

  **Bot:** [@stixmagicbot](https://t.me/stixmagicbot) &nbsp;|&nbsp; **Website:** [stixmagic.com](https://stixmagic.com)

  ---

  ## What It Does

  Stix Magic lets you build and manage Telegram sticker packs without leaving the chat. Send any image or short video and it becomes a sticker instantly. The `/magic` command uses a black-and-white mask photo to cut a subject cleanly out of any background.

  Beyond stickers, the **MagicStix visual asset pipeline** transforms any base asset (letter, symbol, emoji, signal icon) into multiple export formats — GIF, animated WebP, WebM with alpha, MOV with alpha, PNG sequences — using a library of reusable motion presets (pulse, glow, glitch, sparkle, …).

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
  ├── main.py                  # Bot orchestration + conversation handlers
  ├── menus.py                 # Inline menu system (MENU_STRUCTURE)
  ├── api.py                   # Flask REST API
  ├── domain/
  │   └── media.py             # Image/video processing (Pillow, ffmpeg)
  ├── infra/
  │   └── db.py                # SQLite persistence layer
  │
  ├── pipeline/                # Visual asset pipeline
  │   ├── asset_model/         # Asset dataclass + category/theme/format constants
  │   ├── metadata/            # JSON-backed AssetRegistry
  │   ├── motion_presets/      # MotionPreset + 10 built-in presets
  │   ├── exporters/           # GIF / WebP / WebM / MOV / PNG / thumbnail exporters
  │   └── packager/            # Pack dataclass + PackGenerator
  │
  ├── assets/                  # Source asset library
  │   ├── source/
  │   │   ├── letters/
  │   │   ├── numbers/
  │   │   ├── emojis/
  │   │   ├── symbols/
  │   │   ├── signals/
  │   │   ├── frames/
  │   │   └── particles/
  │   ├── processed/
  │   └── previews/
  │
  ├── renders/                 # Pipeline output files
  │   ├── gif/
  │   ├── webp/
  │   ├── webm/
  │   ├── mov/
  │   ├── png_sequences/
  │   └── thumbnails/
  │
  ├── packs/                   # Product pack descriptors (pack.json)
  │   ├── motion_alphabet/
  │   ├── neon_signals/
  │   ├── dj_pack/
  │   ├── cloud_pack/
  │   └── overlay_starter/
  │
  ├── integrations/            # Future integration scaffolding
  │   ├── extension/           # Browser / Nebulosa extension
  │   ├── overlay_engine/      # OBS-style lightweight compositor
  │   └── virtual_camera/      # Virtual camera output
  │
  ├── docs/                    # Architecture documentation
  │   ├── architecture.md
  │   ├── pipeline.md
  │   ├── asset_schema.md
  │   ├── motion_system.md
  │   ├── export_formats.md
  │   ├── pack_generation.md
  │   └── future_integrations.md
  │
  ├── static/
  │   ├── index.html           # Landing page (stixmagic.com)
  │   └── api.html             # Interactive API documentation
  ├── requirements.txt
  └── pyproject.toml
  ```

  ---

  ## Pipeline: One Asset → Many Outputs

  ```
  base asset  +  motion preset  →  multiple output formats
  ─────────────────────────────────────────────────────────
  letter_a_neon  +  pulse  →  letter_a_neon_pulse.gif
                           →  letter_a_neon_pulse.webp
                           →  letter_a_neon_pulse.webm
                           →  letter_a_neon_pulse.mov
                           →  renders/png_sequences/letter_a_neon_pulse/
                           →  letter_a_neon_pulse_preview.jpg
  ```

  See [`docs/pipeline.md`](docs/pipeline.md) for the full walkthrough.

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
  