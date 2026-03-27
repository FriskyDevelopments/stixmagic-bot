# Stix Magic — Environment & Release Model

## Overview

Stix Magic uses two runtime environments to keep development work isolated from
production users:

| Environment | Bot | Purpose |
|---|---|---|
| `development` | @StixMagicdevBot | Active development, QA, feature testing |
| `production` | @stixmagicbot | Live production service |

`APP_ENV` is the single switch that controls which environment is active.

---

## How environments work

### development (default)

- Uses `DEV_BOT_TOKEN` (required — no fallback to `TELEGRAM_BOT_TOKEN`).
  If `DEV_BOT_TOKEN` is not set the app refuses to start.
- Sticker pack names are prefixed with `dev_` so they are clearly separate from
  production packs (e.g. `dev_stix_123_abcde_by_stixmagicdevbot`).
- Debug logging is enabled (`DEBUG` level).
- The `dev_banner` feature flag is active by default, showing a visible
  `[DEV]` notice every time `/start` is called so testers know they are on
  the dev bot.
- Additional feature flags can be enabled freely without risk to production.

### production

- Uses `TELEGRAM_BOT_TOKEN` (required).
- Pack names have no prefix.
- `INFO`-level logging only.
- No experimental flags active by default.
- **Safety checks**:
  - If `APP_ENV=production` but the loaded token matches `DEV_BOT_TOKEN`, the
    app refuses to start.
  - If `EXPECTED_PROD_BOT_ID` is set, the token's numeric bot ID must match —
    deterministic identity check independent of `DEV_BOT_TOKEN` being present.
  - The `/env` command is blocked (fail-closed) when `ADMIN_USER_IDS` is empty.

---

## Configuration

All runtime config lives in **`config.py`**. It reads from environment variables
and exposes constants that the rest of the app imports:

| Symbol | Type | Description |
|---|---|---|
| `config.ENVIRONMENT` | `str` | `"development"` or `"production"` |
| `config.IS_PRODUCTION` | `bool` | shorthand |
| `config.IS_DEVELOPMENT` | `bool` | shorthand |
| `config.BOT_TOKEN` | `str` | resolved bot token |
| `config.PACK_NAME_PREFIX` | `str` | `""` (prod) or `"dev_"` (dev) |
| `config.DB_FILE` | `str` | `"bot.db"` (prod) or `"bot_dev.db"` (dev) |
| `config.LOG_LEVEL` | `int` | `logging.INFO` / `logging.DEBUG` |
| `config.FEATURES` | `dict` | feature-flag name → bool |
| `config.ADMIN_USER_IDS` | `list[int]` | Telegram IDs allowed admin commands |
| `config.EXPECTED_PROD_BOT_ID` | `str` | expected numeric bot ID for production (optional) |
| `config.EXPECTED_DEV_BOT_ID` | `str` | expected numeric bot ID for development (optional) |
| `config.is_feature_enabled(name)` | `bool` | check a flag |
| `config.validate_config()` | `None` | fail-fast startup check |

---

## Environment variables

See `.env.example` for a full annotated reference. Key variables:

```bash
APP_ENV=development          # or "production"
TELEGRAM_BOT_TOKEN=...       # production bot token
DEV_BOT_TOKEN=...            # development bot token (@StixMagicdevBot)
ADMIN_USER_IDS=123456,789012 # comma-separated Telegram user IDs
EXPECTED_PROD_BOT_ID=...     # (optional) numeric bot ID for production safety
EXPECTED_DEV_BOT_ID=...      # (optional) numeric bot ID for development safety
```

---

## Feature flags

Feature flags are controlled with `FEATURE_<NAME>` environment variables and
default values set in `config.py`.

### Adding a new feature flag

1. Add an entry to the `FEATURES` dict in `config.py`:

   ```python
   FEATURES: dict[str, bool] = {
       "dev_banner": _flag("DEV_BANNER", default=IS_DEVELOPMENT),
       "animated_loaders": _flag("ANIMATED_LOADERS", default=False),
       # Add your new flag here:
       "my_experiment": _flag("MY_EXPERIMENT", default=IS_DEVELOPMENT),
   }
   ```

2. Check the flag where needed:

   ```python
   import config

   if config.is_feature_enabled("my_experiment"):
       # experimental code path
   ```

3. To enable it in production, set `FEATURE_MY_EXPERIMENT=true` in the
   production environment.

### Current flags

| Flag | Dev default | Prod default | Description |
|---|---|---|---|
| `dev_banner` | `true` | `false` | Show `[DEV]` marker in `/start` welcome |
| `animated_loaders` | `false` | `false` | Experimental animated progress text |

---

## Running each environment

### Development (local)

```bash
APP_ENV=development DEV_BOT_TOKEN="<dev token>" python main.py
```

> **Note:** The app reads environment variables directly — it does not
> auto-load a `.env` file.  Export the variables in your shell or use a
> helper like `env $(cat .env | xargs)` to load them from `.env.example`
> (which you can copy and fill in locally).

### Production

```bash
APP_ENV=production TELEGRAM_BOT_TOKEN="<prod token>" python main.py
```

---

## Admin commands

`/env` — Displays the current environment, active/inactive feature flags, and
pack prefix. Admin-only command.

Access rules (fail-closed in production):

| Environment | `ADMIN_USER_IDS` | Result |
|---|---|---|
| production | empty | **blocked for everyone** (gate sealed) |
| production | set | restricted to those IDs |
| development | empty | open to any user (QA convenience) |
| development | set | restricted to those IDs |

> ⚠ Always set `ADMIN_USER_IDS` in production. A startup warning is logged
> when it is missing.

---

## Release / promotion workflow

```
1. Develop feature on a branch
2. Test via @StixMagicdevBot  (APP_ENV=development)
3. Verify bot responses, pack flows, and logs look correct
4. If gated behind a feature flag:
     a. Enable the flag on dev (FEATURE_<NAME>=true or set default=IS_DEVELOPMENT)
     b. Verify behaviour
     c. When ready, set default=True or enable via env var in production
5. Merge branch to main
6. Deploy to production (APP_ENV=production)
```

---

## Resource isolation summary

| Resource | Development | Production |
|---|---|---|
| Bot token | `DEV_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` |
| Sticker pack names | `dev_stix_...` prefix | `stix_...` (no prefix) |
| Database file | `bot_dev.db` | `bot.db` |
| Log level | `DEBUG` | `INFO` |
| Feature flags | dev-friendly defaults | conservative defaults |

Packs created on the dev bot are isolated from production because:
- They use a different bot username in the pack name suffix
  (`_by_stixmagicdevbot` vs `_by_stixmagicbot`).
- They carry the `dev_` prefix (configurable via `PACK_NAME_PREFIX`).