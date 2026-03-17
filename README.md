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
  ├── main.py           # Bot logic, conversation handlers, sticker processing
  ├── menus.py          # Inline menu definitions (color-coded groups, keyboard builder)
  ├── api.py            # Flask REST API with auth, CORS, pagination
  ├── static/
  │   ├── index.html    # Landing page (stixmagic.com)
  │   └── api.html      # Interactive API documentation
  ├── requirements.txt  # Python dependencies
  └── pyproject.toml    # Project metadata
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
  | `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from [@BotFather](https://t.me/BotFather) |
  | `STIXMAGIC_API_KEY` | ✅ | Secret key for authenticating REST API requests |
  | `SESSION_SECRET` | Recommended | Flask session secret (random string) |
  | `MINIAPP_URL` | Optional | URL of the Telegram Mini App |

  ---

  ## Setup & Deployment

  ### Local Development

  1. **Clone the repository** and install dependencies:
     ```bash
     git clone https://github.com/FriskyDevelopments/stixmagic-bot.git
     cd stixmagic-bot
     pip install -r requirements.txt
     ```

  2. **Create a `.env` file** from the template:
     ```bash
     cp .env.example .env
     ```
     Then fill in your values in `.env`. The file is git-ignored and will never be committed.

  3. **Run the bot:**
     ```bash
     python main.py
     ```
     The Flask API and the bot polling loop start together.

  ### Automated Deployment (GitHub Actions)

  The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that
  triggers automatically on every push to `main`. It:
  - Sets up Python 3.11 and installs all dependencies (including `ffmpeg`)
  - Validates the `TELEGRAM_BOT_TOKEN` format
  - Launches `main.py`

  **Required GitHub Secrets** — add these under *Settings → Secrets → Actions*:

  | Secret | Description |
  |---|---|
  | `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
  | `STIXMAGIC_API_KEY` | API authentication key |
  | `SESSION_SECRET` | Flask session secret |
  | `MINIAPP_URL` | (Optional) Mini App URL |

  ### Hosting on Replit

  1. Import the repo via *Create Repl → Import from GitHub*.
  2. Open the **Secrets** tab (🔒) and add the environment variables listed above.
  3. Click **Run** — the bot and API start automatically.
  4. To keep the bot alive on a free Replit plan, use [UptimeRobot](https://uptimerobot.com/)
     to ping your Repl URL every 5 minutes, or enable *Always On* in your Replit settings.

  ---

  ## License

  MIT
  