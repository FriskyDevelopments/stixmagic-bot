import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory

DB_FILE = "bot.db"

app = Flask(__name__, static_folder="static")

API_KEY = os.environ.get("STIXMAGIC_API_KEY", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_VERSION = "1.0"
PAGE_SIZE = 20


def get_db():
    conn = sqlite3.connect(DB_FILE)
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


@app.after_request
def add_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type"
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

def validate_miniapp_init_data(init_data):
    """Validate Telegram Mini App initData HMAC.

    Returns the ``user`` dict extracted from initData on success, or ``None``
    on failure.  When ``BOT_TOKEN`` is not configured (local development) the
    HMAC check is skipped and the user dict is parsed without verification so
    that the Mini App can still be tested in a plain browser.
    """
    if not init_data:
        return None
    try:
        params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None

    if not BOT_TOKEN:
        # Dev mode: accept without HMAC validation
        user_str = params.get("user")
        try:
            return json.loads(user_str) if user_str else {}
        except (TypeError, ValueError):
            return {}

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

    user_str = params.get("user")
    try:
        return json.loads(user_str) if user_str else {}
    except (TypeError, ValueError):
        return {}


def _get_miniapp_user():
    """Extract and validate the Mini App user from the current request.

    Checks (in order): ``X-Telegram-Init-Data`` header, ``initData`` form
    field, ``initData`` JSON body field, ``initData`` query param.

    Returns ``(user_dict, None)`` on success or ``(None, error_response)``
    when authentication fails.
    """
    init_data = (
        request.headers.get("X-Telegram-Init-Data", "")
        or request.form.get("initData", "")
        or (request.get_json(silent=True) or {}).get("initData", "")
        or request.args.get("initData", "")
    )
    user = validate_miniapp_init_data(init_data)
    if user is None:
        return None, err("Invalid or missing Telegram initData", 401, "unauthorized")
    return user, None


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
    """Register a new sticker-pack name in the database.

    The actual Telegram ``createNewStickerSet`` call is deferred until the
    first sticker is uploaded via ``POST /miniapp/api/stickers``.
    """
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    data = request.get_json(silent=True) or {}
    pack_name = str(data.get("pack_name", "")).strip()
    title = str(data.get("title", "")).strip()
    if not pack_name:
        return err("pack_name is required", 400, "missing_param")
    if not title:
        return err("title is required", 400, "missing_param")
    if not pack_name.replace("_", "").isalnum():
        return err(
            "pack_name may only contain letters, numbers and underscores",
            400,
            "invalid_pack_name",
        )

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM packs WHERE user_id = ? AND name = ?", (user_id, pack_name)
    )
    if c.fetchone():
        conn.close()
        return err("A pack with that name already exists", 409, "conflict")
    c.execute(
        "INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)",
        (user_id, pack_name, title),
    )
    conn.commit()
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

    data = request.get_json(silent=True) or {}
    new_title = str(data.get("title", "")).strip()
    if not new_title:
        return err("title is required", 400, "missing_param")

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


@app.route("/miniapp/api/stickers", methods=["POST"])
def miniapp_add_sticker():
    """Upload a sticker image and add it to an existing pack via Telegram Bot API.

    If the pack has not yet been created in Telegram (only registered in the DB),
    ``createNewStickerSet`` is called automatically with this sticker as the
    first entry.

    Expected multipart/form-data fields:
      - ``file``      – the sticker image (PNG / WebP / WEBM / TGS)
      - ``pack_name`` – the sticker-set short name
      - ``emoji``     – single emoji for the sticker (default: 😊)
      - ``initData``  – Telegram WebApp initData string (if not in header)
    """
    user, auth_err = _get_miniapp_user()
    if auth_err:
        return auth_err
    user_id = user.get("id")
    if not user_id:
        return err("User ID not found in initData", 400, "missing_user_id")

    pack_name = request.form.get("pack_name", "").strip()
    emoji = request.form.get("emoji", "😊").strip() or "😊"
    uploaded_file = request.files.get("file")

    if not pack_name:
        return err("pack_name is required", 400, "missing_param")
    if not uploaded_file:
        return err("file is required", 400, "missing_param")

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

    file_bytes = uploaded_file.read()
    content_type = uploaded_file.content_type or "image/png"
    filename = uploaded_file.filename or "sticker.png"

    # Determine sticker format from content type
    if content_type in ("application/x-tgsticker", "application/tgs"):
        sticker_format = "animated"
    elif content_type == "video/webm":
        sticker_format = "video"
    else:
        sticker_format = "static"

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
        files={"sticker_file": (filename, file_bytes, content_type)},
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
            files={"sticker_file": (filename, file_bytes, content_type)},
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
