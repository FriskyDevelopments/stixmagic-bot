"""
config.py – Centralized runtime configuration for Stix Magic.

Environment is controlled via the APP_ENV environment variable:
  - "development" (or "dev", "local", "qa") → dev/QA bot (@StixMagicdevBot)
  - "production" (or "prod")                → production bot

Token selection:
  - production  : TELEGRAM_BOT_TOKEN
  - development : DEV_BOT_TOKEN  (falls back to TELEGRAM_BOT_TOKEN if unset)

Quick reference:
  config.ENVIRONMENT          "development" | "production"
  config.IS_PRODUCTION        bool
  config.IS_DEVELOPMENT       bool
  config.BOT_TOKEN            resolved bot token string
  config.PACK_NAME_PREFIX     "" (prod) | "dev_" (dev)
  config.LOG_LEVEL            logging.INFO (prod) | logging.DEBUG (dev)
  config.FEATURES             dict of feature-flag name → bool
  config.is_feature_enabled() helper
  config.validate_config()    call once at startup to fail fast on bad config
"""

import logging
import os
import re
import sys

# ── Environment Detection ─────────────────────────────────────────────────────

_RAW_ENV = os.environ.get("APP_ENV", "development").lower().strip()

if _RAW_ENV in ("production", "prod"):
    ENVIRONMENT = "production"
else:
    # development / dev / local / qa → all treated as "development"
    ENVIRONMENT = "development"

IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = not IS_PRODUCTION


# ── Token Resolution ──────────────────────────────────────────────────────────

def _extract_token(raw: str) -> str:
    """Strip surrounding text (e.g. BotFather message) and return the bare token."""
    m = re.search(r'\d+:[A-Za-z0-9_-]+', raw)
    return m.group(0) if m else ""


def _resolve_token() -> str:
    """Return the bot token appropriate for the current environment."""
    if IS_PRODUCTION:
        raw = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    else:
        # Prefer DEV_BOT_TOKEN; fall back to TELEGRAM_BOT_TOKEN if not set.
        raw = os.environ.get("DEV_BOT_TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return _extract_token(raw)


BOT_TOKEN: str = _resolve_token()


# ── Resource Naming ───────────────────────────────────────────────────────────

# Sticker pack names created in development get this prefix so they are
# clearly isolated from production packs (e.g. "dev_stix_...").
PACK_NAME_PREFIX: str = "" if IS_PRODUCTION else "dev_"


# ── Feature Flags ─────────────────────────────────────────────────────────────

def _flag(name: str, *, default: bool) -> bool:
    """Read a FEATURE_<NAME> environment variable, falling back to *default*."""
    val = os.environ.get(f"FEATURE_{name.upper()}", "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# Feature flags.  Development defaults to True for flags that are safe/useful
# during QA.  Production defaults to False unless explicitly enabled.
FEATURES: dict[str, bool] = {
    # Show a visible "[DEV]" marker in bot messages so testers know they are
    # on the dev bot rather than production.
    "dev_banner": _flag("DEV_BANNER", default=IS_DEVELOPMENT),
    # Animated progress indicators (experimental UI).
    "animated_loaders": _flag("ANIMATED_LOADERS", default=False),
}


def is_feature_enabled(name: str) -> bool:
    """Return True if the named feature flag is active."""
    return FEATURES.get(name, False)


# ── Logging ───────────────────────────────────────────────────────────────────

LOG_LEVEL: int = logging.DEBUG if IS_DEVELOPMENT else logging.INFO


# ── Admin IDs ─────────────────────────────────────────────────────────────────

def _resolve_admin_ids() -> list[int]:
    """Parse ADMIN_USER_IDS (comma-separated) into a list of ints."""
    raw = os.environ.get("ADMIN_USER_IDS", "") or os.environ.get("ADMIN_USER_ID", "")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


ADMIN_USER_IDS: list[int] = _resolve_admin_ids()


# ── Startup Validation ────────────────────────────────────────────────────────

def validate_config() -> None:
    """
    Fail fast (sys.exit) if the runtime configuration is unsafe or incomplete.

    Checks performed:
    1. A bot token must be present.
    2. In production, the token must NOT match DEV_BOT_TOKEN — prevents
       accidentally running the dev bot as production.
    3. In development, the token must NOT match TELEGRAM_BOT_TOKEN when
       DEV_BOT_TOKEN is also set — prevents mixing bots.
    """
    _log = logging.getLogger(__name__)
    errors: list[str] = []

    # 1. Token must exist.
    if not BOT_TOKEN:
        if IS_PRODUCTION:
            errors.append(
                "TELEGRAM_BOT_TOKEN is not set. "
                "A production token is required when APP_ENV=production."
            )
        else:
            errors.append(
                "No bot token found. Set DEV_BOT_TOKEN (preferred for development) "
                "or TELEGRAM_BOT_TOKEN."
            )

    # 2. Production safety: reject if loaded token belongs to the dev bot.
    if IS_PRODUCTION and BOT_TOKEN:
        dev_raw = os.environ.get("DEV_BOT_TOKEN", "")
        dev_token = _extract_token(dev_raw)
        if dev_token and BOT_TOKEN == dev_token:
            errors.append(
                "SAFETY VIOLATION: APP_ENV=production but the active token matches "
                "DEV_BOT_TOKEN. Running the dev bot as production is not allowed. "
                "Set TELEGRAM_BOT_TOKEN to the production token or change APP_ENV."
            )

    # 3. Development warning: if both tokens exist and are the same, warn.
    if IS_DEVELOPMENT and BOT_TOKEN:
        prod_raw = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        dev_raw = os.environ.get("DEV_BOT_TOKEN", "")
        prod_token = _extract_token(prod_raw)
        dev_token = _extract_token(dev_raw)
        if dev_token and prod_token and dev_token == prod_token and BOT_TOKEN == prod_token:
            _log.warning(
                "[config] DEV_BOT_TOKEN and TELEGRAM_BOT_TOKEN are identical. "
                "Consider using separate bot tokens for development and production."
            )

    if errors:
        for msg in errors:
            _log.critical("[config] %s", msg)
        sys.exit(1)

    _log.info(
        "[config] Environment: %s | Pack prefix: '%s' | Features: %s",
        ENVIRONMENT,
        PACK_NAME_PREFIX,
        {k: v for k, v in FEATURES.items() if v},
    )
