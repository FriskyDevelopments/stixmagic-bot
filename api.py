import gzip
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

from emoji_utils import validate_emoji

DB_FILE = "bot.db"

app = Flask(__name__, static_folder="static")

API_KEY = os.environ.get("STIXMAGIC_API_KEY", "")

# ── Bot token: strip whitespace and validate format on startup ─
_RAW_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
_BOT_TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")
BOT_TOKEN = _RAW_BOT_TOKEN if _BOT_TOKEN_RE.fullmatch(_RAW_BOT_TOKEN) else ""

# ── Dev-mode auth bypass (requires explicit opt-in) ───────────
APP_ENV = os.environ.get("APP_ENV", "production").lower()
ALLOW_UNSIGNED = os.environ.get("ALLOW_UNSIGNED_MINIAPP_INIT_DATA", "").lower() in {
    "1", "true", "yes",
}

# ── Rate limiting configuration ────────────────────────────────
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("MINIAPP_RATE_LIMIT", "10"))
_rate_limit_store = defaultdict(list)

# ── Maximum sticker file size: 2 MB ──────────────────────────
MAX_STICKER_FILE_BYTES = 2 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_STICKER_FILE_BYTES + 64 * 1024

# ── Telegram sticker-set short-name suffix ────────────────────
_PACK_NAME_SUFFIX_RE = re.compile(r"^[a-zA-Z0-9_]+_by_[a-zA-Z0-9_]+$")
_MAX_PACK_NAME_LEN = 64
_MAX_TITLE_LEN = 64

API_VERSION = "1.0"
PAGE_SIZE = 20

# ── Cache bot username (populated lazily via getMe) ───────────
_bot_username: str | None = None


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_miniapp_schema():
    """Idempotently create the packs table and its performance index.

    Safe to call at module load time — both statements use ``IF NOT EXISTS``.
    This guarantees the Mini App API works even if the bot (main.py) has not
    been run to initialise the database yet.
    """
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS packs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name    TEXT,
            title   TEXT
        )
        """
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_packs_user_id ON packs (user_id)"
    )
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_packs_name_unique ON packs (name)"
    )
    conn.commit()
    conn.close()


try:
    _ensure_miniapp_schema()
except Exception as _schema_err:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "Could not ensure miniapp DB schema at startup: %s", _schema_err
    )


def get_bot_username() -> str | None:
    """Return the bot's username, fetching via ``getMe`` if needed."""
    global _bot_username
    if _bot_username:
        return _bot_username
    if not BOT_TOKEN:
        return None
    result = _tg_api_simple("getMe")
    if result.get("ok"):
        _bot_username = result["result"].get("username")
    return _bot_username


def ok(data, status=200, **meta):
    body = {"ok": True, "data": data}
    body.update(meta)
    resp = jsonify(body)
    resp.status_code = status
    return resp


def err(message, status=400, code=None):
    body = {"ok": False, "error": {"message": message}}
    if code:
        body["error"]["code"] = code
    resp = jsonify(body)
    resp.status_code = status
    return resp


@app.errorhandler(RequestEntityTooLarge)
def handle_413(_e):
    return err("File too large (max 2 MB)", 413, "payload_too_large")


@app.after_request
def add_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "X-API-Key, X-Telegram-Init-Data, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    response.headers["X-API-Version"] = API_VERSION
    return response


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        resp = app.make_default_options_response()
        return resp


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not API_KEY or key != API_KEY:
            return err("Valid API key required. Pass it as X-API-Key header or api_key param.", 401, "unauthorized")
        return f(*args, **kwargs)
    return decorated


def paginate(query_result):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        limit = min(100, max(1, int(request.args.get("limit", PAGE_SIZE))))
    except ValueError:
        limit = PAGE_SIZE

    total = len(query_result)
    start = (page - 1) * limit
    items = query_result[start:start + limit]
    return items, {"page": page, "limit": limit, "total": total, "pages": max(1, -(-total // limit))}


# ── PUBLIC ────────────────────────────────────────────────────

@app.route("/")
def landing():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api")
@app.route("/api/")
def api_docs():
    return send_from_directory(app.static_folder, "api.html")


@app.route("/miniapp")
@app.route("/miniapp/")
def miniapp():
    return send_from_directory(app.static_folder, "miniapp.html")


# ── MINI APP AUTH ─────────────────────────────────────────────

# Maximum acceptable age for Telegram initData (seconds).
_INIT_DATA_MAX_AGE_SECONDS = 86_400  # 24 hours


def _is_local_request() -> bool:
    """Return True when the request originates from localhost."""
    ip = request.remote_addr or ""
    return ip in {"127.0.0.1", "::1"}


def validate_miniapp_init_data(init_data: str) -> dict | None:
    """Validate Telegram Mini App initData HMAC and auth_date freshness.

    Returns the ``user`` dict on success, or ``None`` on any failure.

    **Fail-closed by default**: when ``BOT_TOKEN`` is not configured this
    function returns ``None`` (→ 401) unless *all three* of the following
    conditions are met:
    - ``APP_ENV=development``
    - ``ALLOW_UNSIGNED_MINIAPP_INIT_DATA=true``
    - The HTTP request comes from localhost (127.0.0.1 / ::1)
    """
    if not init_data:
        return None
    try:
        params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None

    if not BOT_TOKEN:
        # Fail closed unless all three opt-in conditions are satisfied.
        if not (APP_ENV == "development" and ALLOW_UNSIGNED and _is_local_request()):
            return None
        # Dev bypass: parse user without HMAC check
        user_str = params.get("user")
        try:
            return json.loads(user_str) if user_str else {"id": 0, "_dev": True}
        except (TypeError, ValueError):
            return {"id": 0, "_dev": True}

    hash_val = params.pop("hash", None)
    if not hash_val:
        return None

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )
    secret_key = hmac.new(
        b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256
    ).digest()
    computed = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed, hash_val):
        return None

    # Validate auth_date freshness to mitigate replay attacks.
    try:
        auth_date = int(params.get("auth_date", 0))
    except (TypeError, ValueError):
        return None
    if not auth_date or (time.time() - auth_date) > _INIT_DATA_MAX_AGE_SECONDS:
        return None

    user_str = params.get("user")
    try:
        return json.loads(user_str) if user_str else {}
    except (TypeError, ValueError):
        return {}


def _get_miniapp_user():
    """Extract and validate the Mini App user from the current request.

    Checks (in order): ``X-Telegram-Init-Data`` header, ``initData`` form
    field, and ``initData`` JSON body field.  The query-parameter fallback
    is deliberately omitted by default because query strings appear in
    server access logs, browser history, and ``Referer`` headers — leaking
    the signed initData.  Set ``MINIAPP_ALLOW_INITDATA_QUERY=true`` to
    re-enable it for development/testing only.

    Returns ``(user_dict, None)`` on success or ``(None, error_response)``
    when authentication fails.
    """
    allow_query = os.environ.get("MINIAPP_ALLOW_INITDATA_QUERY", "").lower() in {
        "1", "true", "yes",
    }
    init_data = (
        request.headers.get("X-Telegram-Init-Data", "")
        or request.form.get("initData", "")
        or (request.get_json(silent=True) or {}).get("initData", "")
        or (request.args.get("initData", "") if allow_query else "")
    )
    user = validate_miniapp_init_data(init_data)
    if user is None:
        return None, err("Invalid or missing Telegram initData", 401, "unauthorized")
    return user, None


def _check_rate_limit(user_id: int) -> tuple[bool, str | None]:
    """Check if the user has exceeded the rate limit.

    Returns ``(True, None)`` if within limit, or ``(False, error_response)``
    if the limit is exceeded.
    """
    key = f"user_{user_id}" if user_id else f"ip_{request.remote_addr}"
    now = time.time()

    # Clean up old entries
    _rate_limit_store[key] = [
        ts for ts in _rate_limit_store[key] if now - ts < RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(_rate_limit_store[key]) >= RATE_LIMIT_MAX_REQUESTS:
        return False, err(
            f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds.",
            429,
            "rate_limit_exceeded"
        )

    # Record this request
    _rate_limit_store[key].append(now)
    return True, None


def _tg_api_simple(method: str) -> dict:
    """Call a parameterless Telegram Bot API GET method (e.g. ``getMe``)."""
    if not BOT_TOKEN:
        return {"ok": False, "description": "Bot token not configured"}
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def _tg_api(method, data=None, files=None):
    """Call a Telegram Bot API method.

    ``files`` is a dict of ``{field_name: (filename, file_bytes, content_type)}``.
    Returns the decoded JSON response dict (may have ``"ok": False``).
    """
    if not BOT_TOKEN:
        return {"ok": False, "description": "Bot token not configured"}
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    if files:
        boundary = "----TelegramFormBoundary"
        body_parts = []
        for key, value in (data or {}).items():
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data;"
                f' name="{key}"\r\n\r\n{value}\r\n'.encode("utf-8")
            )
        for key, (filename, file_bytes, content_type) in files.items():
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data;"
                f' name="{key}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
                + file_bytes
                + b"\r\n"
            )
        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(body_parts)
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    else:
        body = json.dumps(data or {}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "description": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


# ── MINI APP ENDPOINTS ────────────────────────────────────────

@app.route("/miniapp/api/packs", methods=["GET"])
def miniapp_get_packs():
    """Return all sticker packs belonging to the authenticated Mini App user."""
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT name, title FROM packs WHERE user_id = ? ORDER BY id", (user_id,)
    )
    rows = c.fetchall()
    conn.close()

    packs = [
        {
            "name": r["name"],
            "title": r["title"],
            "link": f"https://t.me/addstickers/{r['name']}",
        }
        for r in rows
    ]
    return ok(packs)


@app.route("/miniapp/api/packs", methods=["POST"])
def miniapp_create_pack():
    """Register a new sticker-pack in the database.

    The client provides a *base name* (letters/numbers/underscores only).
    The server appends ``_by_<bot_username>`` to form the final Telegram
    sticker-set short name, ensuring it is always valid.

    The actual ``createNewStickerSet`` Telegram API call is deferred until
    the first sticker is uploaded via ``POST /miniapp/api/stickers``.
    """
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    # Rate limiting after authentication
    ok_limit, limit_err = _check_rate_limit(user_id)
    if not ok_limit:
        return limit_err

    data = request.get_json(silent=True) or {}
    base_name = str(data.get("pack_name", "")).strip().lower()
    title = str(data.get("title", "")).strip()

    if not base_name:
        return err("pack_name is required", 400, "missing_param")
    if not title:
        return err("title is required", 400, "missing_param")
    if len(title) > _MAX_TITLE_LEN:
        return err(
            f"title must be {_MAX_TITLE_LEN} characters or fewer",
            400,
            "invalid_title",
        )
    if not re.fullmatch(r"[a-z0-9_]+", base_name):
        return err(
            "pack_name may only contain letters, numbers and underscores",
            400,
            "invalid_pack_name",
        )

    # Build the final Telegram-compliant short name
    bot_uname = get_bot_username()
    if not bot_uname:
        return err(
            "Bot username could not be determined; cannot build pack name",
            502,
            "bot_username_unavailable",
        )
    pack_name = f"{base_name}_by_{bot_uname}"
    if len(pack_name) > _MAX_PACK_NAME_LEN:
        return err(
            f"pack_name is too long; the final name '{pack_name}' "
            f"exceeds {_MAX_PACK_NAME_LEN} characters",
            400,
            "invalid_pack_name",
        )

    conn = get_db()
    c = conn.cursor()
    # Check for global uniqueness of pack name
    c.execute("SELECT id FROM packs WHERE name = ?", (pack_name,))
    if c.fetchone():
        conn.close()
        return err("A pack with that name already exists", 409, "conflict")

    try:
        c.execute(
            "INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)",
            (user_id, pack_name, title),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Handle race condition where pack was created between SELECT and INSERT
        conn.close()
        return err("A pack with that name already exists", 409, "conflict")
    conn.close()
    return ok({"name": pack_name, "title": title}, status=201)


@app.route("/miniapp/api/packs/<pack_name>", methods=["PATCH"])
def miniapp_update_pack(pack_name):
    """Update the title of a sticker pack owned by the authenticated user."""
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    # Rate limiting after authentication
    ok_limit, limit_err = _check_rate_limit(user_id)
    if not ok_limit:
        return limit_err

    data = request.get_json(silent=True) or {}
    new_title = str(data.get("title", "")).strip()
    if not new_title:
        return err("title is required", 400, "missing_param")
    if len(new_title) > _MAX_TITLE_LEN:
        return err(
            f"title must be {_MAX_TITLE_LEN} characters or fewer",
            400,
            "invalid_title",
        )

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name)
    )
    if not c.fetchone():
        conn.close()
        return err("Pack not found", 404, "not_found")
    c.execute(
        "UPDATE packs SET title = ? WHERE user_id = ? AND name = ?",
        (new_title, user_id, pack_name),
    )
    conn.commit()
    conn.close()
    return ok({"name": pack_name, "title": new_title})


@app.route("/miniapp/api/packs/<pack_name>", methods=["DELETE"])
def miniapp_delete_pack(pack_name):
    """Remove a sticker pack record owned by the authenticated user."""
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    # Rate limiting after authentication
    ok_limit, limit_err = _check_rate_limit(user_id)
    if not ok_limit:
        return limit_err

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name)
    )
    if not c.fetchone():
        conn.close()
        return err("Pack not found", 404, "not_found")
    c.execute(
        "DELETE FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name)
    )
    conn.commit()
    conn.close()
    return ok({"deleted": True, "name": pack_name})


_STICKER_EXT_MAP = {
    ".webp": "static",
    ".png": "static",
    ".tgs": "animated",
    ".webm": "video",
}


def _detect_sticker_format(filename: str, content_type: str, file_head: bytes) -> str:
    """Return a Telegram sticker format string: 'static' | 'animated' | 'video'.

    Detection order:
    1. ``content_type`` (when unambiguous)
    2. Filename extension
    3. Magic-byte sniffing (most reliable for .tgs / .webm / .webp / .png)
    """
    ct = content_type.split(";")[0].strip().lower()
    if ct in ("application/x-tgsticker", "application/tgs"):
        return "animated"
    if ct == "video/webm":
        return "video"
    if ct in ("image/webp",):
        return "static"
    if ct == "image/png":
        return "static"

    # Fall back to extension
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext in _STICKER_EXT_MAP:
            return _STICKER_EXT_MAP[ext]

    # Magic-byte sniffing
    if file_head:
        # PNG: 8-byte signature
        if file_head[:8] == b"\x89PNG\r\n\x1a\n":
            return "static"
        # WebP: RIFF????WEBP
        if file_head[:4] == b"RIFF" and len(file_head) >= 12 and file_head[8:12] == b"WEBP":
            return "static"
        # WebM / Matroska EBML header
        if file_head[:4] == b"\x1a\x45\xdf\xa3":
            return "video"
        # TGS: gzip-compressed Lottie JSON (gzip magic = 0x1F 0x8B)
        if file_head[:2] == b"\x1f\x8b":
            try:
                head = gzip.decompress(file_head[:4096])
                if head.lstrip()[:1] == b"{":
                    return "animated"
            except Exception:
                pass

    return "static"


@app.route("/miniapp/api/stickers", methods=["POST"])
def miniapp_add_sticker():
    """Upload a sticker image and add it to an existing pack via Telegram Bot API.

    If the pack has not yet been created in Telegram (only registered in the DB),
    ``createNewStickerSet`` is called automatically with this sticker as the
    first entry.

    Expected multipart/form-data fields:
      - ``file``      – the sticker image (PNG / WebP / WEBM / TGS)
      - ``pack_name`` – the sticker-set short name (including ``_by_`` suffix)
      - ``emoji``     – single emoji for the sticker (default: 😊)
      - ``initData``  – Telegram WebApp initData string (if not in header)
    """
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    # Rate limiting after authentication
    ok_limit, limit_err = _check_rate_limit(user_id)
    if not ok_limit:
        return limit_err

    pack_name = request.form.get("pack_name", "").strip()
    raw_emoji = request.form.get("emoji", "😊")
    uploaded_file = request.files.get("file")

    if not pack_name:
        return err("pack_name is required", 400, "missing_param")
    if not uploaded_file:
        return err("file is required", 400, "missing_param")

    # Validate emoji server-side using the shared utility
    emoji_ok, emoji = validate_emoji(raw_emoji)
    if not emoji_ok:
        return err(
            "emoji must be exactly one valid emoji (e.g. 😊)",
            400,
            "invalid_emoji",
        )

    # Verify the pack is registered to this user
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT name, title FROM packs WHERE user_id = ? AND name = ?",
        (user_id, pack_name),
    )
    pack_row = c.fetchone()
    conn.close()
    if not pack_row:
        return err("Pack not found or not owned by you", 404, "not_found")

    if not BOT_TOKEN:
        return err(
            "Bot token not configured; cannot upload sticker in this environment",
            501,
            "not_implemented",
        )

    # Enforce file size limit before reading entire body into memory
    if request.content_length and request.content_length > MAX_STICKER_FILE_BYTES:
        return err("File too large (max 2 MB)", 413, "payload_too_large")
    file_bytes = uploaded_file.read(MAX_STICKER_FILE_BYTES + 1)
    if len(file_bytes) > MAX_STICKER_FILE_BYTES:
        return err("File too large (max 2 MB)", 413, "payload_too_large")

    content_type = (uploaded_file.content_type or "").strip().lower()
    filename = uploaded_file.filename or "sticker"

    # Multi-layer sticker format detection:
    # 1. Content-Type  2. File extension  3. Magic bytes
    sticker_format = _detect_sticker_format(filename, content_type, file_bytes)

    sticker_dict = {
        "sticker": "attach://sticker_file",
        "format": sticker_format,
        "emoji_list": [emoji],
    }

    # Try addStickerToSet first; if the set doesn't exist yet, create it
    result = _tg_api(
        "addStickerToSet",
        data={
            "user_id": str(user_id),
            "name": pack_name,
            "sticker": json.dumps(sticker_dict),
        },
        files={"sticker_file": (filename, file_bytes, content_type or "image/png")},
    )

    if not result.get("ok") and "STICKERSET_INVALID" in result.get("description", ""):
        pack_title = pack_row["title"]
        result = _tg_api(
            "createNewStickerSet",
            data={
                "user_id": str(user_id),
                "name": pack_name,
                "title": pack_title,
                "stickers": json.dumps([sticker_dict]),
                "sticker_type": "regular",
            },
            files={"sticker_file": (filename, file_bytes, content_type or "image/png")},
        )

    if not result.get("ok"):
        return err(
            result.get("description", "Telegram API error"),
            502,
            "telegram_api_error",
        )

    return ok({"added": True, "pack_name": pack_name})


@app.route("/api/health")
def health():
    conn = get_db()
    try:
        conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        conn.close()
    return ok({
        "status": "ok",
        "service": "stixmagic",
        "version": API_VERSION,
        "db": "ok" if db_ok else "error",
        "timestamp": int(time.time()),
    })


# ── AUTHENTICATED ─────────────────────────────────────────────

@app.route("/api/stats")
@require_api_key
def stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT user_id) FROM packs")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM packs")
    total_packs = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM user_settings")
    total_settings_users = c.fetchone()[0]
    conn.close()
    return ok({
        "users": total_users,
        "packs": total_packs,
        "users_with_settings": total_settings_users,
    })


@app.route("/api/search")
@require_api_key
def search_packs():
    q = request.args.get("q", "").strip()
    if not q:
        return err("Missing required query param 'q'", 400, "missing_param")
    if len(q) < 2:
        return err("Query must be at least 2 characters", 400, "query_too_short")

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT user_id, name, title FROM packs WHERE title LIKE ? OR name LIKE ? ORDER BY title",
        (f"%{q}%", f"%{q}%")
    )
    rows = c.fetchall()
    conn.close()

    all_results = [
        {"user_id": r["user_id"], "name": r["name"], "title": r["title"],
         "link": f"https://t.me/addstickers/{r['name']}"}
        for r in rows
    ]
    items, pagination = paginate(all_results)
    return ok(items, query=q, pagination=pagination)


@app.route("/api/packs/<int:user_id>")
@require_api_key
def user_packs(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, title FROM packs WHERE user_id = ? ORDER BY id", (user_id,))
    rows = c.fetchall()
    conn.close()

    all_packs = [
        {"name": r["name"], "title": r["title"], "link": f"https://t.me/addstickers/{r['name']}"}
        for r in rows
    ]
    items, pagination = paginate(all_packs)
    return ok(items, user_id=user_id, pagination=pagination)


@app.route("/api/packs/<int:user_id>/<pack_name>")
@require_api_key
def pack_detail(user_id, pack_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, title FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name))
    row = c.fetchone()
    conn.close()
    if not row:
        return err("Pack not found", 404, "not_found")
    return ok({
        "user_id": user_id,
        "name": row["name"],
        "title": row["title"],
        "link": f"https://t.me/addstickers/{row['name']}",
    })


@app.route("/api/packs/<int:user_id>/<pack_name>", methods=["DELETE"])
@require_api_key
def delete_pack(user_id, pack_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name))
    row = c.fetchone()
    if not row:
        conn.close()
        return err("Pack not found", 404, "not_found")
    c.execute("DELETE FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name))
    conn.commit()
    conn.close()
    return ok({"deleted": True, "name": pack_name})


@app.route("/api/settings/<int:user_id>")
@require_api_key
def user_settings_get(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT mask_inverted FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return ok({
        "user_id": user_id,
        "mask_inverted": bool(row["mask_inverted"]) if row else False,
    })


@app.route("/api/settings/<int:user_id>", methods=["PATCH"])
@require_api_key
def user_settings_update(user_id):
    data = request.get_json(silent=True)
    if not data:
        return err("JSON body required", 400, "invalid_body")

    conn = get_db()
    c = conn.cursor()

    if "mask_inverted" in data:
        val = int(bool(data["mask_inverted"]))
        c.execute(
            "INSERT INTO user_settings (user_id, mask_inverted) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET mask_inverted = ?",
            (user_id, val, val)
        )

    conn.commit()
    c.execute("SELECT mask_inverted FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return ok({
        "user_id": user_id,
        "mask_inverted": bool(row["mask_inverted"]) if row else False,
    })


# ── ERRORS ────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api") or request.path.startswith("/miniapp/api"):
        return err("Endpoint not found", 404, "not_found")
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(405)
def method_not_allowed(e):
    return err("Method not allowed", 405, "method_not_allowed")


@app.errorhandler(500)
def server_error(e):
    return err("Internal server error", 500, "server_error")


def run_api():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)