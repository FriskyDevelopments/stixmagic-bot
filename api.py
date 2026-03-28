import os
import sqlite3
import time
import asyncio
import json
import secrets
from functools import wraps
from urllib.parse import urlparse
from flask import Flask, jsonify, request, send_from_directory
from stixmagic.contracts import (
    API_VERSION,
    MINIAPP_AUTH_HEADER,
    PACK_TYPES,
    PRODUCT_NAME,
    START_PAYLOAD_ADD,
    START_PAYLOAD_CREATE,
    START_PAYLOAD_FEATURE,
    START_PAYLOAD_MAGIC,
    START_PAYLOAD_MANAGE,
)
from dotenv import load_dotenv
from stixmagic.settings import get_settings
from stixmagic.telegram_auth import TelegramInitDataError, validate_init_data
from infra.db import init_db

load_dotenv()
SETTINGS = get_settings()

app = Flask(__name__, static_folder="static")

API_KEY = SETTINGS.stixmagic_api_key
PAGE_SIZE = 20


def _normalize_origin(url: str) -> str:
    """Normalize a URL to just its origin (scheme + netloc), stripping any path."""
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url.rstrip("/")


# Pre-compute the CORS allowlist for Mini App routes once at startup.
_MINIAPP_CORS_ORIGINS: frozenset[str] = frozenset(
    filter(None, [
        _normalize_origin(SETTINGS.public_base_url) if SETTINGS.public_base_url else None,
        _normalize_origin(os.environ.get("MINIAPP_URL", "")) or None,
    ])
)


def get_db():
    """Get a database connection with lazy path resolution."""
    conn = sqlite3.connect(SETTINGS.database_path)
    conn.row_factory = sqlite3.Row
    return conn


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


def _telegram_init_data_from_request() -> str:
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("tma "):
        return auth_header[4:].strip()
    return request.headers.get(MINIAPP_AUTH_HEADER, "").strip()


def get_miniapp_session():
    init_data = _telegram_init_data_from_request()
    return validate_init_data(init_data, SETTINGS.telegram_bot_token)


@app.after_request
def add_headers(response):
    origin = request.headers.get("Origin")
    is_miniapp_api = request.path.startswith("/api/miniapp/")

    if is_miniapp_api and origin:
        # Only allow trusted origins to access Mini App API responses.
        if origin.rstrip("/") in _MINIAPP_CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
    else:
        # Preserve existing wildcard CORS behavior for non-Mini App routes.
        response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Headers"] = f"X-API-Key, Content-Type, Authorization, {MINIAPP_AUTH_HEADER}"
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


def require_miniapp_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            request.miniapp_session = get_miniapp_session()
        except TelegramInitDataError as exc:
            return err(str(exc), 401, "miniapp_unauthorized")
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


# ── MINI APP (no API key — user_id comes from Telegram initData) ──
# Mini App routes use @require_miniapp_auth instead of @require_api_key because
# they validate the Telegram WebApp initData, which provides user authentication.
# This allows public Mini App access without requiring a server API key.

def _run_async(coro):
    """Run an async coroutine safely from a synchronous Flask route."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _validate_packs_async(token, user_id):
    """Validate all DB packs against Telegram; prune deleted, sync renamed titles."""
    from telegram import Bot as TelegramBot
    bot = TelegramBot(token=token)
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT name, title FROM packs WHERE user_id = ? ORDER BY id", (user_id,))
        rows = c.fetchall()
        conn.close()
        valid = []
        for row in rows:
            name, title = row["name"], row["title"]
            try:
                ss = await bot.get_sticker_set(name)
                if ss.title != title:
                    upd = get_db()
                    upd.execute(
                        "UPDATE packs SET title = ? WHERE user_id = ? AND name = ?",
                        (ss.title, user_id, name)
                    )
                    upd.commit()
                    upd.close()
                    title = ss.title
                valid.append({"name": name, "title": title, "link": f"https://t.me/addstickers/{name}"})
            except Exception:
                rm = get_db()
                rm.execute("DELETE FROM packs WHERE user_id = ? AND name = ?", (user_id, name))
                rm.commit()
                rm.close()
        return valid
    finally:
        await bot.close()


@app.route("/api/miniapp/bootstrap")
@require_miniapp_auth
def miniapp_bootstrap():
    session = request.miniapp_session
    user = session["user"]
    bot_username = SETTINGS.telegram_bot_username

    # Build bot object conditionally — only include links if bot_username is configured
    bot_info = {"username": bot_username}
    if bot_username:
        bot_info["links"] = {
            "create_pack": f"https://t.me/{bot_username}?start={START_PAYLOAD_CREATE}",
            "add_sticker": f"https://t.me/{bot_username}?start={START_PAYLOAD_ADD}",
            "manage_packs": f"https://t.me/{bot_username}?start={START_PAYLOAD_MANAGE}",
            "magic_cut": f"https://t.me/{bot_username}?start={START_PAYLOAD_MAGIC}",
            "feature_pack": f"https://t.me/{bot_username}?start={START_PAYLOAD_FEATURE}",
        }

    return ok({
        "product": PRODUCT_NAME,
        "api_version": API_VERSION,
        "user": user,
        "launch": {
            "surface": "miniapp",
            "start_param": session.get("start_param"),
        },
        "bot": bot_info,
        "deployment": {
            "public_base_url": SETTINGS.public_base_url,
            "miniapp_url": SETTINGS.miniapp_url,
            "bot_mode": SETTINGS.bot_mode,
        },
    })


@app.route("/api/miniapp/packs")
@require_miniapp_auth
def miniapp_packs():
    uid = int(request.miniapp_session["user"]["id"])

    if SETTINGS.telegram_bot_token:
        try:
            packs = _run_async(_validate_packs_async(SETTINGS.telegram_bot_token, uid))
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
    user_id = int(request.miniapp_session["user"]["id"])
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT mask_inverted FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return ok({"user_id": user_id, "mask_inverted": bool(row["mask_inverted"]) if row else False})


@app.route("/api/miniapp/settings", methods=["PATCH"])
@require_miniapp_auth
def miniapp_settings_patch():
    user_id = int(request.miniapp_session["user"]["id"])
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
    return ok({"user_id": user_id, "mask_inverted": bool(row["mask_inverted"]) if row else False})


@app.route("/api/miniapp/intent", methods=["POST"])
@require_miniapp_auth
def miniapp_intent():
    """
    Mint a one-time intent token for Mini App → Bot handoff with metadata.
    Body: {"action": "create_pack"|"add_sticker"|"manage_packs", "metadata": {...}}
    Returns: {"token": "...", "deep_link": "https://t.me/bot?start=..."}
    """
    user_id = int(request.miniapp_session["user"]["id"])
    data = request.get_json(silent=True)
    if not data:
        return err("JSON body required", 400, "invalid_body")

    action = data.get("action", "")
    metadata = data.get("metadata", {})

    # Validate action
    valid_actions = ["create_pack", "add_sticker", "manage_packs", "magic_cut", "feature_pack"]
    if action not in valid_actions:
        return err(f"Invalid action. Must be one of: {', '.join(valid_actions)}", 400, "invalid_action")

    # Generate a cryptographically-random unique token
    token = secrets.token_urlsafe(16)

    # Store intent in the database with expiry tracking
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO miniapp_intents (token, user_id, action, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
        (token, user_id, action, json.dumps(metadata), int(time.time()))
    )
    conn.commit()
    conn.close()

    # Build deep link using the appropriate START_PAYLOAD constant
    bot_username = SETTINGS.telegram_bot_username
    if not bot_username:
        return err("Bot username not configured", 500, "bot_not_configured")

    payload_map = {
        "create_pack": START_PAYLOAD_CREATE,
        "add_sticker": START_PAYLOAD_ADD,
        "manage_packs": START_PAYLOAD_MANAGE,
        "magic_cut": START_PAYLOAD_MAGIC,
        "feature_pack": START_PAYLOAD_FEATURE,
    }
    start_payload = payload_map.get(action, action)
    deep_link = f"https://t.me/{bot_username}?start={start_payload}_{token}"

    return ok({"token": token, "deep_link": deep_link, "action": action})


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
        "service": "stixmagic-product-backend",
        "version": API_VERSION,
        "db": "ok" if db_ok else "error",
        "timestamp": int(time.time()),
        "bot_mode": SETTINGS.bot_mode,
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
    if pack_type not in PACK_TYPES:
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
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_api()