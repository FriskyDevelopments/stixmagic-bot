import os
import re
import sqlite3
import time
import asyncio
import logging
from functools import wraps
from secrets import token_urlsafe
from urllib.parse import urlparse

from flask import Flask, g, jsonify, request, send_from_directory

from stixmagic.contracts import (
    API_VERSION,
    PRODUCT_NAME,
    START_PAYLOAD_ADD,
    START_PAYLOAD_CREATE,
    START_PAYLOAD_FEATURE,
    START_PAYLOAD_MAGIC,
    START_PAYLOAD_MANAGE,
)
from stixmagic.settings import get_settings
from stixmagic.telegram_auth import TelegramInitDataError, validate_init_data
from moderation import create_default_harness

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")

SETTINGS = get_settings()
API_KEY = SETTINGS.stixmagic_api_key
PAGE_SIZE = 20
if SETTINGS.webhook_secret:
    app.secret_key = SETTINGS.webhook_secret
else:
    app.secret_key = os.urandom(32).hex()
moderation_harness = create_default_harness()


def _normalize_origin(url: str) -> str:
    """
    Normalize an origin or URL to a canonical origin string.
    
    Parameters:
        url (str): The origin or URL to normalize; may be empty.
    
    Returns:
        str: The canonical origin as "scheme://host[:port]" when the input includes a scheme and netloc; otherwise the input with any trailing slashes removed, or an empty string if the input is falsy.
    """
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url.rstrip("/")


_MINIAPP_CORS_ORIGINS = frozenset(
    origin
    for origin in (
        _normalize_origin(SETTINGS.public_base_url),
        _normalize_origin(SETTINGS.miniapp_url),
    )
    if origin
)

if not _MINIAPP_CORS_ORIGINS:
    logger.warning(
        "CORS for miniapp routes is disabled: neither SETTINGS.public_base_url "
        "nor SETTINGS.miniapp_url are set. Consider setting STIXMAGIC_PUBLIC_BASE_URL."
    )


def get_db():
    """
    Open a SQLite connection to the configured database path.
    
    Returns:
        sqlite3.Connection: A connection to SETTINGS.database_path with `row_factory` set to `sqlite3.Row`.
    """
    conn = sqlite3.connect(SETTINGS.database_path)
    conn.row_factory = sqlite3.Row
    return conn


def _settings_str(name: str, default: str = "") -> str:
    """
    Get a SETTINGS attribute by name and return it as a string, falling back to a default if absent or not a string.
    
    Returns:
        The SETTINGS.<name> value if it exists and is a string, otherwise `default`.
    """
    value = getattr(SETTINGS, name, default)
    return value if isinstance(value, str) else default


def ok(data, status=200, **meta):
    """
    Create a Flask JSON response for a successful API call.
    
    Parameters:
        data: The payload to include under the "data" key.
        status (int): HTTP status code for the response (default 200).
        **meta: Additional top-level fields to merge into the JSON body.
    
    Returns:
        flask.Response: A JSON response with structure `{"ok": True, "data": <data>, ...}` and the given HTTP status code.
    """
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


@app.after_request
def add_headers(response):
    """
    Apply CORS, allowed headers/methods, and the API version header to the given Flask response.
    
    For requests under /api/miniapp/, set Access-Control-Allow-Origin to the request Origin only if that origin matches the configured miniapp CORS origins and set Vary: Origin; for other routes set Access-Control-Allow-Origin to "*". Always set Access-Control-Allow-Headers, Access-Control-Allow-Methods, and X-API-Version.
    
    Parameters:
        response: The Flask response object to modify.
    
    Returns:
        The modified Flask response object with CORS and version headers applied.
    """
    is_miniapp_route = request.path.startswith("/api/miniapp/")
    origin = _normalize_origin(request.headers.get("Origin", ""))

    if is_miniapp_route:
        if origin and origin in _MINIAPP_CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, X-Telegram-Init-Data, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    response.headers["X-API-Version"] = API_VERSION
    return response


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        resp = app.make_default_options_response()
        return resp


def require_api_key(f):
    """
    Decorator that requires the incoming request to present the configured API key.
    
    Parameters:
        f (callable): The Flask view function to wrap.
    
    Returns:
        callable: A wrapped view function that returns a 401 JSON error with code "unauthorized" when the `X-API-Key` header is missing or does not match the configured API key; otherwise calls the original view.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not API_KEY or key != API_KEY:
            return err("Valid API key required. Pass it as X-API-Key header.", 401, "unauthorized")
        return f(*args, **kwargs)
    return decorated


def _telegram_init_data_from_request() -> str:
    """
    Extract Telegram Mini App init data from the current Flask request.
    
    Checks the `X-Telegram-Init-Data` header first, then the `Authorization` header for a value prefixed with `tma `.
    Returns:
        str: The init data string if found, or an empty string otherwise.
    """
    header_value = request.headers.get("X-Telegram-Init-Data", "").strip()
    if header_value:
        return header_value

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("tma "):
        return auth_header[4:].strip()
    return ""


def require_miniapp_auth(f):
    """
    Require valid Telegram Mini App init data for a Flask route and attach the validated session to flask.g.
    
    Wraps a view function to:
    - extract Telegram init data from the request,
    - validate it using the configured Telegram bot token,
    - ensure the session contains an integer `user.id`,
    - store the validated session as `g.miniapp_session` and the user id as `g.miniapp_user_id` before calling the wrapped handler.
    
    Parameters:
        f (callable): The Flask view function to wrap.
    
    Returns:
        callable: A wrapper around `f` that enforces Mini App authentication. On invalid or missing init data the wrapper returns an HTTP 401 JSON error with code `"miniapp_unauthorized"`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = _telegram_init_data_from_request()
        try:
            session = validate_init_data(init_data, SETTINGS.telegram_bot_token)
        except TelegramInitDataError as exc:
            return err(str(exc), 401, "miniapp_unauthorized")

        user = session.get("user") or {}
        user_id = user.get("id")
        if not isinstance(user_id, int):
            return err("Invalid Telegram user in initData", 401, "miniapp_unauthorized")

        g.miniapp_session = session
        g.miniapp_user_id = user_id
        return f(*args, **kwargs)

    return decorated


def get_pagination_params():
    """
    Extracts and sanitizes `page` and `limit` URL query parameters.

    Returns:
        tuple: A pair (page, limit) where:
            - page (int): Requested page number, coerced to at least 1 (defaults to 1 on invalid input).
            - limit (int): Number of items per page, coerced to the range 1–100 (defaults to PAGE_SIZE on invalid input).
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        limit = min(100, max(1, int(request.args.get("limit", PAGE_SIZE))))
    except ValueError:
        limit = PAGE_SIZE
    return page, limit


def paginate(query_result):
    """
    Builds a paginated view of query_result according to `page` and `limit` URL query parameters.
    
    Parameters:
        query_result (Sequence): Full list-like sequence of items to paginate.
    
    Returns:
        tuple: A pair (items, pagination) where:
            - items (list): Slice of `query_result` for the requested page.
            - pagination (dict): Metadata with keys:
                - page (int): Requested page number, coerced to at least 1 (defaults to 1 on invalid input).
                - limit (int): Number of items per page, coerced to the range 1–100 (defaults to PAGE_SIZE on invalid input).
                - total (int): Total number of items in `query_result`.
                - pages (int): Total number of pages (at least 1).
    """
    page, limit = get_pagination_params()

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


# ── MINI APP (no API key — user_id comes from Telegram initData) ──

def _run_async(coro):
    """Run an async coroutine safely from a synchronous Flask route."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_TG_PACK_CACHE = {}  # {name: (timestamp, title, status)}
_TG_PACK_CACHE_TTL = 300  # 5 minutes

async def _validate_packs_async(token, user_id):
    """Validate all DB packs against Telegram; prune deleted, sync renamed titles."""
    from telegram import Bot as TelegramBot
    bot = TelegramBot(token=token)
    # ⚡ Bolt Optimization: Concurrently validate packs with bounded concurrency (Semaphore=5)
    # Impact: Reduces N sequential network calls to Telegram down to O(N/5) while preventing HTTP 429 rate limit drops that could lead to accidental pack deletion
    sem = asyncio.Semaphore(5)

    async def validate_pack(name, title):
        now = time.time()

        # Prevent memory leaks by periodically clearing the cache if it gets too large
        if len(_TG_PACK_CACHE) > 1000:
            _TG_PACK_CACHE.clear()

        # ⚡ Bolt Optimization: Cache expensive Telegram API calls per pack for 5 minutes
        # Impact: Drastically reduces network latency and avoids 429 errors when reloading /api/miniapp/packs
        if name in _TG_PACK_CACHE and now - _TG_PACK_CACHE[name][0] < _TG_PACK_CACHE_TTL:
            _, cached_title, status = _TG_PACK_CACHE[name]
            return {"name": name, "title": cached_title, "old_title": title, "status": status}

        async with sem:
            try:
                ss = await bot.get_sticker_set(name)
                _TG_PACK_CACHE[name] = (now, ss.title, "valid")
                return {"name": name, "title": ss.title, "old_title": title, "status": "valid"}
            except Exception:
                _TG_PACK_CACHE[name] = (now, title, "deleted")
                return {"name": name, "title": title, "old_title": title, "status": "deleted"}

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT name, title FROM packs WHERE user_id = ? ORDER BY id", (user_id,))
        rows = c.fetchall()

        # Gather network validations concurrently
        tasks = [validate_pack(row["name"], row["title"]) for row in rows]
        results = await asyncio.gather(*tasks)

        valid = []
        for res in results:
            name, title, old_title, status = res["name"], res["title"], res["old_title"], res["status"]
            if status == "valid":
                if title != old_title:
                    c.execute(
                        "UPDATE packs SET title = ? WHERE user_id = ? AND name = ?",
                        (title, user_id, name)
                    )
                valid.append({"name": name, "title": title, "link": f"https://t.me/addstickers/{name}"})
            else:
                c.execute("DELETE FROM packs WHERE user_id = ? AND name = ?", (user_id, name))
        conn.commit()
        conn.close()
        return valid
    finally:
        await bot.close()


@app.route("/api/miniapp/packs")
@require_miniapp_auth
def miniapp_packs():
    """
    Fetch the authenticated miniapp user's sticker packs, validating stored titles against Telegram when a valid bot token is available.
    
    If Telegram validation is unavailable or fails, returns the packs as read from the local database without external verification.
    
    Returns:
        A JSON `ok` payload whose data is a list of pack objects. Each object contains `name`, `title`, and `link` (a t.me addstickers URL).
    """
    uid = g.miniapp_user_id

    raw_token = SETTINGS.telegram_bot_token
    token_match = re.search(r'\d+:[A-Za-z0-9_-]{35,}', raw_token)
    if token_match:
        try:
            packs = _run_async(_validate_packs_async(token_match.group(0), uid))
            return ok(packs)
        except Exception:
            pass

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, title FROM packs WHERE user_id = ? ORDER BY id", (uid,))
    rows = c.fetchall()
    conn.close()
    return ok([
        {"name": r["name"], "title": r["title"],
         "link": f"https://t.me/addstickers/{r['name']}"}
        for r in rows
    ])


@app.route("/api/miniapp/settings")
@require_miniapp_auth
def miniapp_settings_get():
    """
    Return the miniapp settings for the currently authenticated miniapp user.
    
    Returns:
        dict: Contains `user_id` (int) and `mask_inverted` (`true` if the user's mask setting is inverted, `false` otherwise). Default `mask_inverted` is `false` when no settings exist for the user.
    """
    user_id = g.miniapp_user_id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT mask_inverted FROM user_settings WHERE user_id = ?", (int(user_id),))
    row = c.fetchone()
    conn.close()
    return ok({"user_id": int(user_id), "mask_inverted": bool(row["mask_inverted"]) if row else False})


@app.route("/api/miniapp/settings", methods=["PATCH"])
@require_miniapp_auth
def miniapp_settings_patch():
    """
    Update the authenticated miniapp user's `mask_inverted` setting and return the stored value.
    
    If `"mask_inverted"` is present in the JSON body it is coerced to a boolean and upserted into the user's settings; the handler then returns the resulting stored value. If the request has no JSON body, an error response is returned indicating a JSON body is required with code `"invalid_body"`.
    
    @returns
        On success: JSON object {"user_id": <int>, "mask_inverted": <bool>}.
        On error (missing JSON): JSON error response with message "JSON body required" and code "invalid_body".
    """
    user_id = g.miniapp_user_id
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
            (int(user_id), val, val)
        )
    conn.commit()
    c.execute("SELECT mask_inverted FROM user_settings WHERE user_id = ?", (int(user_id),))
    row = c.fetchone()
    conn.close()
    return ok({"user_id": int(user_id), "mask_inverted": bool(row["mask_inverted"]) if row else False})


@app.route("/api/miniapp/bootstrap")
@require_miniapp_auth
def miniapp_bootstrap():
    """
    Builds the bootstrap payload for the authenticated Telegram mini app session.
    
    The payload includes the authenticated user's session info, bot configuration (including deep links when a bot username is configured), launch metadata (surface and start parameter), and API base URLs.
    
    Returns:
    	A Flask JSON response containing the bootstrap payload with keys: `user`, `bot` (may include `username` and `links`), `launch`, and `api`.
    """
    session = g.miniapp_session
    user = session["user"]
    data = {
        "user": user,
        "bot": {"username": _settings_str("telegram_bot_username")},
        "launch": {"surface": "miniapp", "start_param": session.get("start_param")},
        "api": {
            "base_url": _settings_str("api_base_url", "/api"),
            "miniapp_base_url": _settings_str("miniapp_api_base_url"),
        },
    }
    if _settings_str("telegram_bot_username"):
        username = _settings_str("telegram_bot_username")
        data["bot"]["links"] = {
            "create_pack": f"https://t.me/{username}?start={START_PAYLOAD_CREATE}",
            "add_sticker": f"https://t.me/{username}?start={START_PAYLOAD_ADD}",
            "manage_packs": f"https://t.me/{username}?start={START_PAYLOAD_MANAGE}",
            "magic_cut": f"https://t.me/{username}?start={START_PAYLOAD_MAGIC}",
            "feature_pack": f"https://t.me/{username}?start={START_PAYLOAD_FEATURE}",
        }
    return ok(data)


@app.route("/api/miniapp/intent", methods=["POST"])
@require_miniapp_auth
def miniapp_intent():
    """
    Validate the miniapp intent request and return a generated action token and an optional Telegram deep link.
    
    Expects a JSON body with an "action" field matching one of: "create_pack", "add_sticker", "manage_packs", "magic_cut", "feature_pack".
    If the application setting `telegram_bot_username` is configured, the response includes a deep link to start the bot with the corresponding start payload.
    
    Returns:
        dict: Object with keys:
            - action (str): The validated action string.
            - token (str): A short, URL-safe token for the intent.
            - deep_link (str): A Telegram deep link when a bot username is configured, otherwise an empty string.
    
    Errors:
        Returns a 400 error with code "invalid_body" if the request body is missing or not JSON.
        Returns a 400 error with code "invalid_action" if the "action" value is missing or not one of the allowed actions.
    """
    payload = request.get_json(silent=True)
    if not payload:
        return err("JSON body required", 400, "invalid_body")
    action = (payload.get("action") or "").strip()
    action_to_start = {
        "create_pack": START_PAYLOAD_CREATE,
        "add_sticker": START_PAYLOAD_ADD,
        "manage_packs": START_PAYLOAD_MANAGE,
        "magic_cut": START_PAYLOAD_MAGIC,
        "feature_pack": START_PAYLOAD_FEATURE,
    }
    if action not in action_to_start:
        return err("Invalid miniapp intent action", 400, "invalid_action")

    deep_link = ""
    username = _settings_str("telegram_bot_username")
    if username:
        deep_link = f"https://t.me/{username}?start={action_to_start[action]}"
    return ok({"action": action, "token": token_urlsafe(18), "deep_link": deep_link})




@app.route("/api/moderation/dev/state")
@require_api_key
def moderation_dev_state():
    return ok(moderation_harness.state())


@app.route("/api/moderation/dev/events", methods=["POST"])
@require_api_key
def moderation_dev_event():
    payload = request.get_json(silent=True) or {}
    if "actor_id" not in payload:
        return err("actor_id is required", 400, "missing_param")
    try:
        result = moderation_harness.simulate_event(payload)
    except ValueError as ex:
        return err(str(ex), 400, "invalid_actor")
    return ok(result, status=201)


@app.route("/api/moderation/dev/replay")
@require_api_key
def moderation_dev_replay():
    state = moderation_harness.state()
    return ok({"replay": state["replay"], "count": len(state["replay"])})


@app.route("/api/health")
def health():
    """
    Return a JSON health-check payload summarizing service status.
    
    The response payload includes service name, API version, bot mode, database status, and the current UNIX timestamp.
    
    Returns:
        Flask response: JSON object with keys:
            - status: "ok"
            - service: product name
            - version: API version
            - bot_mode: current bot mode from settings
            - db: "ok" if the database query succeeded, "error" otherwise
            - timestamp: integer UNIX timestamp
    """
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
        "service": PRODUCT_NAME,
        "version": API_VERSION,
        "bot_mode": SETTINGS.bot_mode,
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

    page, limit = get_pagination_params()
    offset = (page - 1) * limit

    conn = get_db()
    c = conn.cursor()

    # ⚡ Bolt Optimization: Use SQL LIMIT/OFFSET instead of Python array slicing
    # Impact: Reduces memory usage and response time from O(N) to O(limit) for large result sets
    c.execute(
        "SELECT COUNT(*) FROM packs WHERE title LIKE ? OR name LIKE ?",
        (f"%{q}%", f"%{q}%")
    )
    total = c.fetchone()[0]

    c.execute(
        "SELECT user_id, name, title FROM packs WHERE title LIKE ? OR name LIKE ? ORDER BY title LIMIT ? OFFSET ?",
        (f"%{q}%", f"%{q}%", limit, offset)
    )
    rows = c.fetchall()
    conn.close()

    items = [
        {"user_id": r["user_id"], "name": r["name"], "title": r["title"],
         "link": f"https://t.me/addstickers/{r['name']}"}
        for r in rows
    ]
    pagination = {"page": page, "limit": limit, "total": total, "pages": max(1, -(-total // limit))}
    return ok(items, query=q, pagination=pagination)


@app.route("/api/packs/<int:user_id>")
@require_api_key
def user_packs(user_id):
    page, limit = get_pagination_params()
    offset = (page - 1) * limit

    conn = get_db()
    c = conn.cursor()

    # ⚡ Bolt Optimization: Use SQL LIMIT/OFFSET instead of Python array slicing
    # Impact: Reduces memory usage and response time from O(N) to O(limit) for large result sets
    c.execute("SELECT COUNT(*) FROM packs WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0]

    c.execute("SELECT name, title FROM packs WHERE user_id = ? ORDER BY id LIMIT ? OFFSET ?", (user_id, limit, offset))
    rows = c.fetchall()
    conn.close()

    items = [
        {"name": r["name"], "title": r["title"], "link": f"https://t.me/addstickers/{r['name']}"}
        for r in rows
    ]
    pagination = {"page": page, "limit": limit, "total": total, "pages": max(1, -(-total // limit))}
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


# ── CATALOG (public) ──────────────────────────────────────────

def _catalog_row_to_dict(row) -> dict:
    r = dict(row)
    return {
        "id": r.get("id"),
        "name": r.get("name"),
        "title": r.get("title"),
        "description": r.get("description", ""),
        "type": r.get("type", "image"),
        "public": bool(r.get("public", 1)),
        "safe": bool(r.get("safe", 1)),
        "likes": r.get("likes", 0),
        "dislikes": r.get("dislikes", 0),
        "view_count": r.get("view_count", 0),
        "added_at": r.get("added_at"),
        "link": f"https://t.me/addstickers/{r['name']}",
    }


@app.route("/api/catalog/packs")
def catalog_packs():
    """
    GET /api/catalog/packs?type=popular|trending|new|search&q=query&limit=25&skip=0
    Returns catalog packs. No API key required (public endpoint).
    """
    sort = request.args.get("type", "popular")
    if sort not in ("popular", "trending", "new", "search"):
        sort = "popular"
    query = request.args.get("q", "").strip()
    try:
        limit = min(100, max(1, int(request.args.get("limit", 25))))
    except ValueError:
        limit = 25
    try:
        skip = max(0, int(request.args.get("skip", 0)))
    except ValueError:
        skip = 0

    conn = get_db()
    if sort == "popular":
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "ORDER BY likes DESC LIMIT ? OFFSET ?"
        )
        rows = conn.execute(sql, (limit, skip)).fetchall()
        count_row = conn.execute("SELECT COUNT(*) FROM catalog_packs WHERE public = 1").fetchone()
    elif sort == "trending":
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "ORDER BY view_count DESC, likes DESC LIMIT ? OFFSET ?"
        )
        rows = conn.execute(sql, (limit, skip)).fetchall()
        count_row = conn.execute("SELECT COUNT(*) FROM catalog_packs WHERE public = 1").fetchone()
    elif sort == "new":
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "ORDER BY added_at DESC LIMIT ? OFFSET ?"
        )
        rows = conn.execute(sql, (limit, skip)).fetchall()
        count_row = conn.execute("SELECT COUNT(*) FROM catalog_packs WHERE public = 1").fetchone()
    else:
        if not query:
            conn.close()
            return err("Missing required param 'q' for search type", 400, "missing_param")
        pattern = f"%{query}%"
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "AND (title LIKE ? OR name LIKE ? OR description LIKE ?) "
            "ORDER BY likes DESC LIMIT ? OFFSET ?"
        )
        rows = conn.execute(sql, (pattern, pattern, pattern, limit, skip)).fetchall()
        count_row = conn.execute(
            "SELECT COUNT(*) FROM catalog_packs WHERE public = 1 "
            "AND (title LIKE ? OR name LIKE ? OR description LIKE ?)",
            (pattern, pattern, pattern),
        ).fetchone()
    conn.close()

    total = count_row[0] if count_row else 0
    packs = [_catalog_row_to_dict(r) for r in rows]
    return ok({"stickerSets": packs, "totalCount": total, "count": len(packs)})


@app.route("/api/catalog/packs/<pack_name>")
def catalog_pack_detail(pack_name):
    """GET /api/catalog/packs/<name> — get one catalog pack."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM catalog_packs WHERE name = ? AND public = 1", (pack_name,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE catalog_packs SET view_count = view_count + 1 WHERE name = ?",
            (pack_name,),
        )
        conn.commit()
    conn.close()
    if not row:
        return err("Pack not found in catalog", 404, "not_found")
    return ok(_catalog_row_to_dict(row))


@app.route("/api/catalog/packs/<pack_name>/react", methods=["POST"])
def catalog_pack_react(pack_name):
    """
    POST /api/catalog/packs/<name>/react
    Body: {"user_id": int, "type": "like"|"dislike"}
    No API key required (uses user_id from request body).
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    reaction = data.get("type", "")

    if not user_id or not str(user_id).lstrip("-").isdigit():
        return err("Missing or invalid user_id", 400, "missing_param")
    if reaction not in ("like", "dislike"):
        return err("type must be 'like' or 'dislike'", 400, "invalid_param")

    conn = get_db()
    row = conn.execute(
        "SELECT id FROM catalog_packs WHERE name = ? AND public = 1", (pack_name,)
    ).fetchone()
    if not row:
        conn.close()
        return err("Pack not found in catalog", 404, "not_found")

    uid = int(user_id)
    existing = conn.execute(
        "SELECT reaction FROM catalog_reactions WHERE user_id = ? AND pack_name = ?",
        (uid, pack_name),
    ).fetchone()

    if existing:
        old = existing["reaction"]
        if old == reaction:
            conn.execute(
                "DELETE FROM catalog_reactions WHERE user_id = ? AND pack_name = ?",
                (uid, pack_name),
            )
            if reaction == "like":
                conn.execute(
                    "UPDATE catalog_packs SET likes = MAX(0, likes - 1) WHERE name = ?",
                    (pack_name,),
                )
            else:
                conn.execute(
                    "UPDATE catalog_packs SET dislikes = MAX(0, dislikes - 1) WHERE name = ?",
                    (pack_name,),
                )
            current = None
        else:
            conn.execute(
                "UPDATE catalog_reactions SET reaction = ? WHERE user_id = ? AND pack_name = ?",
                (reaction, uid, pack_name),
            )
            if reaction == "like":
                conn.execute(
                    "UPDATE catalog_packs SET likes = likes + 1, dislikes = MAX(0, dislikes - 1) WHERE name = ?",
                    (pack_name,),
                )
            else:
                conn.execute(
                    "UPDATE catalog_packs SET dislikes = dislikes + 1, likes = MAX(0, likes - 1) WHERE name = ?",
                    (pack_name,),
                )
            current = reaction
    else:
        conn.execute(
            "INSERT INTO catalog_reactions (user_id, pack_name, reaction) VALUES (?, ?, ?)",
            (uid, pack_name, reaction),
        )
        if reaction == "like":
            conn.execute(
                "UPDATE catalog_packs SET likes = likes + 1 WHERE name = ?",
                (pack_name,),
            )
        else:
            conn.execute(
                "UPDATE catalog_packs SET dislikes = dislikes + 1 WHERE name = ?",
                (pack_name,),
            )
        current = reaction

    conn.commit()
    result_row = conn.execute(
        "SELECT likes, dislikes FROM catalog_packs WHERE name = ?", (pack_name,)
    ).fetchone()
    conn.close()

    return ok({
        "total": {
            "like": result_row["likes"] if result_row else 0,
            "dislike": result_row["dislikes"] if result_row else 0,
        },
        "current": current,
    })


@app.route("/api/catalog/packs/<pack_name>/feature", methods=["POST"])
def catalog_pack_feature(pack_name):
    """
    POST /api/catalog/packs/<name>/feature
    Body: {"user_id": int, "title": str, "description": str, "type": str}
    Allows a Mini App user to feature a pack in the catalog.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    pack_type = data.get("type", "image")

    if not user_id or not str(user_id).lstrip("-").isdigit():
        return err("Missing or invalid user_id", 400, "missing_param")
    if not title:
        return err("title is required", 400, "missing_param")
    if pack_type not in ("image", "animated", "video"):
        pack_type = "image"

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM catalog_packs WHERE name = ?", (pack_name,)
    ).fetchone()
    if existing:
        conn.close()
        return ok({"featured": False, "message": "Pack already in catalog"})

    conn.execute(
        "INSERT INTO catalog_packs (name, title, description, type, added_at, added_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (pack_name, title, description, pack_type, int(time.time()), int(user_id)),
    )
    conn.commit()
    conn.close()
    return ok({"featured": True, "name": pack_name, "title": title}, 201)


# ── ERRORS ────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api"):
        return err("Endpoint not found", 404, "not_found")
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(405)
def method_not_allowed(e):
    return err("Method not allowed", 405, "method_not_allowed")


@app.errorhandler(500)
def server_error(e):
    return err("Internal server error", 500, "server_error")


def run_api():
    """
    Start the Flask API server bound to all network interfaces using the PORT environment variable or 8080 by default.
    
    Runs the app with debug mode disabled and the reloader disabled; this call blocks the current thread until the server stops.
    """
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), debug=False, use_reloader=False)