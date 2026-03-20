"""
config.py – Centralized runtime configuration for Stix Magic.

Environment is controlled via the APP_ENV environment variable:
  - "development" (or "dev", "local", "qa") → dev/QA bot (@StixMagicdevBot)
  - "production" (or "prod")                → production bot
  Any other value causes an immediate startup failure.

Token selection:
  - production  : TELEGRAM_BOT_TOKEN (required)
  - development : DEV_BOT_TOKEN (required; falls back to nothing)

Quick reference:
  config.ENVIRONMENT          "development" | "production"
  config.IS_PRODUCTION        bool
  config.IS_DEVELOPMENT       bool
  config.BOT_TOKEN            resolved bot token string
  config.PACK_NAME_PREFIX     "" (prod) | "dev_" (dev)
  config.LOG_LEVEL            logging.INFO (prod) | logging.DEBUG (dev)
  config.FEATURES             dict of feature-flag name → bool
  config.is_feature_enabled() helper
  config.build_pack_name()    environment-aware pack short-name builder
  config.validate_config()    call once at startup to fail fast on bad config
"""

import logging
import os
import re
import sys

# ── Environment Detection ─────────────────────────────────────────────────────

_RAW_ENV = os.environ.get("APP_ENV", "development").lower().strip()

_ALLOWED_ENV_ALIASES: dict[str, str] = {
    "production": "production",
    "prod": "production",
    "development": "development",
    "dev": "development",
    "local": "development",
    "qa": "development",
}

if _RAW_ENV not in _ALLOWED_ENV_ALIASES:
    _allowed = ", ".join(repr(k) for k in sorted(_ALLOWED_ENV_ALIASES.keys()))
    sys.stderr.write(
        f"ERROR: Invalid APP_ENV value: {repr(_RAW_ENV)}. "
        f"Allowed values are: {_allowed}.\n"
    )
    sys.exit(1)

ENVIRONMENT: str = _ALLOWED_ENV_ALIASES[_RAW_ENV]

IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = not IS_PRODUCTION


# ── Token Resolution ──────────────────────────────────────────────────────────

def _extract_token(raw: str) -> str:
    """Strip surrounding text (e.g. BotFather message) and return the bare token.

    Requires the hash part to be between 35 and 100 characters to reject
    obviously invalid or partial tokens and guard against pathological inputs.
    """
    m = re.search(r'\d+:[A-Za-z0-9_-]{35,100}', raw)
    return m.group(0) if m else ""


def _resolve_token() -> str:
    """Return the bot token appropriate for the current environment.

    Development requires DEV_BOT_TOKEN.  There is no fallback to
    TELEGRAM_BOT_TOKEN in development — that would defeat the hard
    dev/prod separation.
    """
    if IS_PRODUCTION:
        raw = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    else:
        raw = os.environ.get("DEV_BOT_TOKEN", "")
    return _extract_token(raw)


BOT_TOKEN: str = _resolve_token()


# ── Resource Naming ───────────────────────────────────────────────────────────

# Sticker pack names created in development get this prefix so they are
# clearly isolated from production packs (e.g. "dev_stix_...").
PACK_NAME_PREFIX: str = "" if IS_PRODUCTION else "dev_"


def build_pack_name(user_id: int, suffix: str, bot_username: str) -> str:
    """Build an environment-aware sticker pack short name.

    Always go through this function so the correct prefix is applied
    regardless of which code path creates the pack.

    Example (development): "dev_stix_123456_abcde_by_stixmagicdevbot"
    Example (production):  "stix_123456_abcde_by_stixmagicbot"
    """
    return f"{PACK_NAME_PREFIX}stix_{user_id}_{suffix}_by_{bot_username}"


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
    1. A bot token must be present and well-formed.
    2. In production, the active token must NOT match DEV_BOT_TOKEN — prevents
       accidentally running the dev bot as production.
    3. In development, the active token must NOT match TELEGRAM_BOT_TOKEN —
       prevents accidentally running the production bot under dev settings.
    """
    _log = logging.getLogger(__name__)
    errors: list[str] = []

    # 1. Token must exist and be well-formed.
    if IS_PRODUCTION:
        raw_prod = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not raw_prod:
            errors.append(
                "TELEGRAM_BOT_TOKEN is not set. "
                "A production token is required when APP_ENV=production."
            )
        elif not BOT_TOKEN:
            errors.append(
                "TELEGRAM_BOT_TOKEN is set but does not contain a valid bot token. "
                "Expected format: <bot_id>:<hash>  (e.g. 123456789:AABBcc...)."
            )
    else:
        raw_dev = os.environ.get("DEV_BOT_TOKEN", "")
        if not raw_dev:
            errors.append(
                "DEV_BOT_TOKEN is not set. "
                "A dedicated development token is required when APP_ENV=development. "
                "Set DEV_BOT_TOKEN to the @StixMagicdevBot token."
            )
        elif not BOT_TOKEN:
            errors.append(
                "DEV_BOT_TOKEN is set but does not contain a valid bot token. "
                "Expected format: <bot_id>:<hash>  (e.g. 123456789:AABBcc...)."
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

    # 3. Development safety: reject if loaded token is the production token.
    if IS_DEVELOPMENT and BOT_TOKEN:
        prod_raw = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        prod_token = _extract_token(prod_raw)
        if prod_token and BOT_TOKEN == prod_token:
            errors.append(
                "SAFETY VIOLATION: APP_ENV=development but DEV_BOT_TOKEN matches "
                "TELEGRAM_BOT_TOKEN. Running the production bot under dev settings "
                "is not allowed. Use a separate @StixMagicdevBot token for DEV_BOT_TOKEN."
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
