"""
Tests for api.py – changed helpers and routes.

Covers:
 - _normalize_origin: various URL shapes
 - CORS add_headers: wildcard for public routes, restricted for /api/miniapp/*
 - require_miniapp_auth: passes with valid session, 401 on TelegramInitDataError
 - ok() / err() response envelopes
 - health endpoint includes bot_mode
 - _telegram_init_data_from_request: Authorization header and X-Telegram-Init-Data header
 - miniapp_bootstrap route structure
"""

import asyncio
import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

# ── Helpers to build valid Telegram initData ──────────────────

FAKE_BOT_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh"
FAKE_USER = {"id": 42, "first_name": "Alice", "username": "alice"}


def _build_init_data(bot_token: str, user: dict, auth_date: int | None = None) -> str:
    if auth_date is None:
        auth_date = int(time.time())
    pairs = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(
        secret, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(pairs)


# ── _normalize_origin (pure function, importable separately) ──


class TestNormalizeOrigin(unittest.TestCase):
    """Tests for the api._normalize_origin helper."""

    def _get_fn(self):
        # Import lazily so we can patch SETTINGS before module load
        from api import _normalize_origin

        return _normalize_origin

    def test_empty_string_returns_empty(self):
        fn = self._get_fn()
        self.assertEqual(fn(""), "")

    def test_none_like_empty_returns_empty(self):
        # The function guards on `if not url`
        fn = self._get_fn()
        self.assertEqual(fn(""), "")

    def test_full_url_returns_origin(self):
        fn = self._get_fn()
        self.assertEqual(fn("https://example.com/some/path?q=1"), "https://example.com")

    def test_url_with_port(self):
        fn = self._get_fn()
        self.assertEqual(
            fn("http://localhost:5000/api/miniapp"), "http://localhost:5000"
        )

    def test_url_without_path(self):
        fn = self._get_fn()
        self.assertEqual(fn("https://example.com"), "https://example.com")

    def test_url_with_trailing_slash(self):
        fn = self._get_fn()
        # No scheme+netloc path → strips trailing slash
        self.assertEqual(fn("https://example.com/"), "https://example.com")

    def test_bare_string_without_scheme_strips_trailing_slash(self):
        fn = self._get_fn()
        result = fn("example.com/")
        self.assertFalse(result.endswith("/"))

    def test_https_scheme_preserved(self):
        fn = self._get_fn()
        result = fn("https://secure.example.com/path")
        self.assertTrue(result.startswith("https://"))

    def test_http_scheme_preserved(self):
        fn = self._get_fn()
        result = fn("http://insecure.example.com/path")
        self.assertTrue(result.startswith("http://"))

    def test_subdomain_preserved(self):
        fn = self._get_fn()
        self.assertEqual(
            fn("https://api.example.com/v1/data"), "https://api.example.com"
        )


# ── Flask application tests ───────────────────────────────────


def _make_mock_settings(db_path: str = ":memory:", **kwargs):
    s = MagicMock()
    s.database_path = db_path
    s.stixmagic_api_key = "test-api-key"
    s.telegram_bot_token = FAKE_BOT_TOKEN
    s.telegram_bot_username = "testbot"
    s.public_base_url = "https://example.com"
    s.miniapp_url = "https://example.com/miniapp"
    s.bot_mode = "polling"
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


class ApiTestBase(unittest.TestCase):
    """Base class that creates a Flask test client with a temp DB."""

    def setUp(self):
        # Create a real temp DB file (not :memory: since api.py uses get_db per request)
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.mock_settings = _make_mock_settings(db_path=self.db_path)

        # Patch get_settings in all relevant modules before importing api
        self._patch_settings = patch(
            "stixmagic.settings.get_settings", return_value=self.mock_settings
        )
        self._patch_settings.start()

        # Force re-import of api module with patched settings if already loaded
        if "api" in sys.modules:
            # Update SETTINGS directly in the already-loaded module
            import api as api_mod

            api_mod.SETTINGS = self.mock_settings
            api_mod.API_KEY = self.mock_settings.stixmagic_api_key
            self.app = api_mod.app
        else:
            import api as api_mod

            api_mod.SETTINGS = self.mock_settings
            api_mod.API_KEY = self.mock_settings.stixmagic_api_key
            self.app = api_mod.app

        # Initialize DB tables in the temp file so API routes can use them
        import infra.db as db_mod

        with patch("infra.db.get_settings", return_value=self.mock_settings):
            db_mod.init_db()

        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self._patch_settings.stop()
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass


class TestHealthEndpoint(ApiTestBase):

    def test_health_returns_200(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_ok_true(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])

    def test_health_includes_bot_mode(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertIn("bot_mode", data["data"])

    def test_health_service_name(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertEqual(data["data"]["service"], "stixmagic-product-backend")

    def test_health_includes_api_version(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertIn("version", data["data"])


class TestCORSHeaders(ApiTestBase):

    def test_public_route_has_wildcard_cors(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_api_version_header_present(self):
        resp = self.client.get("/api/health")
        self.assertIn("X-API-Version", resp.headers)

    def test_miniapp_route_with_trusted_origin_gets_cors(self):
        """A request from a trusted origin should get the CORS header set."""
        import api as api_mod

        # Add the origin to the allowlist
        api_mod._MINIAPP_CORS_ORIGINS = frozenset(["https://example.com"])

        valid_init_data = _build_init_data(FAKE_BOT_TOKEN, FAKE_USER)

        with patch(
            "api.validate_init_data",
            return_value={"user": FAKE_USER, "start_param": None},
        ):
            resp = self.client.get(
                "/api/miniapp/settings",
                headers={
                    "Origin": "https://example.com",
                    "X-Telegram-Init-Data": valid_init_data,
                },
            )
        # Should get the specific origin back, not wildcard
        origin_header = resp.headers.get("Access-Control-Allow-Origin")
        self.assertEqual(origin_header, "https://example.com")

    def test_miniapp_route_with_untrusted_origin_no_cors(self):
        """A request from an untrusted origin should not get a CORS header."""
        import api as api_mod

        api_mod._MINIAPP_CORS_ORIGINS = frozenset(["https://example.com"])

        with patch(
            "api.validate_init_data",
            return_value={"user": FAKE_USER, "start_param": None},
        ):
            resp = self.client.get(
                "/api/miniapp/settings",
                headers={
                    "Origin": "https://evil.com",
                    "X-Telegram-Init-Data": "fake",
                },
            )
        origin_header = resp.headers.get("Access-Control-Allow-Origin")
        self.assertNotEqual(origin_header, "https://evil.com")


class TestRequireMiniappAuth(ApiTestBase):

    def test_valid_init_data_proceeds(self):
        """Valid initData should pass the auth guard and reach the route."""
        fake_session = {"user": {"id": 42, "first_name": "Alice"}, "start_param": None}
        with patch("api.validate_init_data", return_value=fake_session):
            resp = self.client.get(
                "/api/miniapp/settings",
                headers={"X-Telegram-Init-Data": "any-value"},
            )
        # Route reached — not a 401
        self.assertNotEqual(resp.status_code, 401)

    def test_missing_init_data_returns_401(self):
        """Missing initData should return 401 with miniapp_unauthorized code."""
        from stixmagic.telegram_auth import TelegramInitDataError

        with patch(
            "api.validate_init_data", side_effect=TelegramInitDataError("Missing")
        ):
            resp = self.client.get("/api/miniapp/settings")
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"]["code"], "miniapp_unauthorized")

    def test_invalid_init_data_returns_401(self):
        from stixmagic.telegram_auth import TelegramInitDataError

        with patch(
            "api.validate_init_data",
            side_effect=TelegramInitDataError("Invalid signature"),
        ):
            resp = self.client.get(
                "/api/miniapp/settings",
                headers={"X-Telegram-Init-Data": "bad-data"},
            )
        self.assertEqual(resp.status_code, 401)


class TestTelegramInitDataFromRequest(ApiTestBase):

    def test_x_telegram_init_data_header_used(self):
        """X-Telegram-Init-Data header should be extracted."""
        captured = {}

        def _capture(init_data, token, **kwargs):
            captured["init_data"] = init_data
            raise __import__(
                "stixmagic.telegram_auth", fromlist=["TelegramInitDataError"]
            ).TelegramInitDataError("test")

        with patch("api.validate_init_data", side_effect=_capture):
            self.client.get(
                "/api/miniapp/settings",
                headers={"X-Telegram-Init-Data": "my-init-data"},
            )
        self.assertEqual(captured.get("init_data"), "my-init-data")

    def test_authorization_tma_prefix_extracted(self):
        """Authorization: TMA <data> header should strip the prefix."""
        captured = {}

        def _capture(init_data, token, **kwargs):
            captured["init_data"] = init_data
            raise __import__(
                "stixmagic.telegram_auth", fromlist=["TelegramInitDataError"]
            ).TelegramInitDataError("test")

        with patch("api.validate_init_data", side_effect=_capture):
            self.client.get(
                "/api/miniapp/settings",
                headers={"Authorization": "TMA my-actual-init-data"},
            )
        self.assertEqual(captured.get("init_data"), "my-actual-init-data")


class TestMiniappBootstrap(ApiTestBase):

    def _session(self, user_id: int = 42) -> dict:
        return {
            "user": {"id": user_id, "first_name": "Alice"},
            "start_param": "create-pack",
            "chat_type": None,
            "chat_instance": None,
            "query_id": None,
            "auth_date": int(time.time()),
        }

    def test_bootstrap_returns_200(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.get(
                "/api/miniapp/bootstrap",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        self.assertEqual(resp.status_code, 200)

    def test_bootstrap_includes_user(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.get(
                "/api/miniapp/bootstrap",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        data = json.loads(resp.data)
        self.assertIn("user", data["data"])
        self.assertEqual(data["data"]["user"]["id"], 42)

    def test_bootstrap_includes_bot_info(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.get(
                "/api/miniapp/bootstrap",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        data = json.loads(resp.data)
        self.assertIn("bot", data["data"])

    def test_bootstrap_includes_deep_links_when_username_set(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.get(
                "/api/miniapp/bootstrap",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        data = json.loads(resp.data)
        bot = data["data"]["bot"]
        self.assertIn("links", bot)
        links = bot["links"]
        self.assertIn("create_pack", links)
        self.assertIn("add_sticker", links)
        self.assertIn("manage_packs", links)
        self.assertIn("magic_cut", links)
        self.assertIn("feature_pack", links)

    def test_bootstrap_includes_launch_surface(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.get(
                "/api/miniapp/bootstrap",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        data = json.loads(resp.data)
        launch = data["data"]["launch"]
        self.assertEqual(launch["surface"], "miniapp")

    def test_bootstrap_without_bot_username_no_links(self):
        """When bot_username is empty, links should not be present."""
        import api as api_mod

        original = api_mod.SETTINGS.telegram_bot_username
        api_mod.SETTINGS = _make_mock_settings(
            db_path=self.db_path, telegram_bot_username=""
        )
        try:
            with patch("api.validate_init_data", return_value=self._session()):
                resp = self.client.get(
                    "/api/miniapp/bootstrap",
                    headers={"X-Telegram-Init-Data": "valid"},
                )
            data = json.loads(resp.data)
            bot = data["data"]["bot"]
            self.assertNotIn("links", bot)
        finally:
            api_mod.SETTINGS = self.mock_settings

    def test_bootstrap_requires_auth(self):
        from stixmagic.telegram_auth import TelegramInitDataError

        with patch(
            "api.validate_init_data", side_effect=TelegramInitDataError("No auth")
        ):
            resp = self.client.get("/api/miniapp/bootstrap")
        self.assertEqual(resp.status_code, 401)


class TestMiniappSettingsRoute(ApiTestBase):

    def _session(self, user_id: int = 42) -> dict:
        return {"user": {"id": user_id, "first_name": "Alice"}, "start_param": None}

    def test_settings_get_returns_defaults(self):
        with patch("api.validate_init_data", return_value=self._session(42)):
            resp = self.client.get(
                "/api/miniapp/settings",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("mask_inverted", data["data"])
        self.assertFalse(data["data"]["mask_inverted"])

    def test_settings_patch_updates_value(self):
        with patch("api.validate_init_data", return_value=self._session(42)):
            resp = self.client.patch(
                "/api/miniapp/settings",
                json={"mask_inverted": True},
                headers={"X-Telegram-Init-Data": "valid"},
            )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["data"]["mask_inverted"])

    def test_settings_patch_requires_json_body(self):
        with patch("api.validate_init_data", return_value=self._session(42)):
            resp = self.client.patch(
                "/api/miniapp/settings",
                data="not-json",
                content_type="text/plain",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        self.assertEqual(resp.status_code, 400)

    def test_settings_user_id_from_session_not_query_string(self):
        """user_id must come from the auth session, not query string (security)."""
        with patch("api.validate_init_data", return_value=self._session(42)):
            # Passing a different user_id in query string should be ignored
            resp = self.client.get(
                "/api/miniapp/settings?user_id=999",
                headers={"X-Telegram-Init-Data": "valid"},
            )
        data = json.loads(resp.data)
        self.assertEqual(data["data"]["user_id"], 42)


class TestMiniappIntentRoute(ApiTestBase):

    def _session(self, user_id: int = 42) -> dict:
        return {"user": {"id": user_id, "first_name": "Alice"}, "start_param": None}

    def test_intent_create_pack_returns_token_and_link(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.post(
                "/api/miniapp/intent",
                json={"action": "create_pack"},
                headers={"X-Telegram-Init-Data": "valid"},
            )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("token", data["data"])
        self.assertIn("deep_link", data["data"])
        self.assertIn("action", data["data"])

    def test_intent_deep_link_contains_bot_username(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.post(
                "/api/miniapp/intent",
                json={"action": "add_sticker"},
                headers={"X-Telegram-Init-Data": "valid"},
            )
        data = json.loads(resp.data)
        self.assertIn("testbot", data["data"]["deep_link"])

    def test_intent_invalid_action_returns_400(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.post(
                "/api/miniapp/intent",
                json={"action": "do_something_evil"},
                headers={"X-Telegram-Init-Data": "valid"},
            )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "invalid_action")

    def test_intent_without_body_returns_400(self):
        with patch("api.validate_init_data", return_value=self._session()):
            resp = self.client.post(
                "/api/miniapp/intent",
                headers={"X-Telegram-Init-Data": "valid"},
                content_type="text/plain",
                data="no json",
            )
        self.assertEqual(resp.status_code, 400)

    def test_intent_all_valid_actions(self):
        valid_actions = [
            "create_pack",
            "add_sticker",
            "manage_packs",
            "magic_cut",
            "feature_pack",
        ]
        for action in valid_actions:
            with self.subTest(action=action):
                with patch("api.validate_init_data", return_value=self._session()):
                    resp = self.client.post(
                        "/api/miniapp/intent",
                        json={"action": action},
                        headers={"X-Telegram-Init-Data": "valid"},
                    )
                self.assertEqual(
                    resp.status_code, 200, f"Action {action!r} should be valid"
                )

    def test_intent_requires_auth(self):
        from stixmagic.telegram_auth import TelegramInitDataError

        with patch(
            "api.validate_init_data", side_effect=TelegramInitDataError("No auth")
        ):
            resp = self.client.post(
                "/api/miniapp/intent",
                json={"action": "create_pack"},
            )
        self.assertEqual(resp.status_code, 401)


# ── _validate_packs_async tests ───────────────────────────────
#
# These tests exercise the N+1 DB connection optimization introduced in this PR.
# The function opens exactly ONE connection and reuses it across all
# pack-validation iterations, rather than opening a fresh connection for
# every UPDATE or DELETE operation.
#


def _ensure_api_importable():
    """Inject minimal stubs for api.py's top-level imports if not present."""
    if "flask" not in sys.modules:
        flask_stub = MagicMock()
        flask_stub.Flask = MagicMock(return_value=MagicMock())
        flask_stub.jsonify = MagicMock()
        flask_stub.request = MagicMock()
        flask_stub.send_from_directory = MagicMock()
        sys.modules["flask"] = flask_stub

    # telegram stub needed for _validate_packs_async's `from telegram import Bot`
    if "telegram" not in sys.modules:
        telegram_stub = MagicMock()
        telegram_stub.__name__ = "telegram"
        telegram_stub.Bot = MagicMock()
        sys.modules["telegram"] = telegram_stub

    for mod in ("config", "config.runtime", "moderation"):
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()

    # Ensure config.runtime.get_settings returns something safe
    sys.modules["config.runtime"].get_settings = MagicMock(
        return_value=MagicMock(
            api_key="test-key",
            session_secret="secret",
        )
    )
    sys.modules["moderation"].create_default_harness = MagicMock(
        return_value=MagicMock()
    )


def _make_db_row(name, title):
    """Return a MagicMock that behaves like a sqlite3.Row for name/title access."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: name if key == "name" else title
    return row


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestValidatePacksAsync(unittest.TestCase):
    """_validate_packs_async – connection-reuse and validation logic."""

    @classmethod
    def setUpClass(cls):
        _ensure_api_importable()
        # Force api into sys.modules so later patches on "api.get_db" resolve
        if "api" not in sys.modules:
            import importlib

            sys.modules["api"] = importlib.import_module("api")

    def _make_bot(self, sticker_sets=None, raise_for=None):
        """
        Build an AsyncMock Bot.

        sticker_sets  – dict mapping pack name → StickerSet stub (title attr)
        raise_for     – set of pack names for which get_sticker_set raises
        """
        bot = MagicMock()
        bot.close = AsyncMock()

        async def _get_sticker_set(name):
            if raise_for and name in raise_for:
                raise Exception(f"Pack {name} not found")
            ss = MagicMock()
            ss.title = (sticker_sets or {}).get(name, name)
            return ss

        bot.get_sticker_set = _get_sticker_set
        return bot

    def _make_conn(self, rows):
        """Return a mock connection/cursor pair with pre-loaded rows."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        conn.cursor.return_value = cursor
        return conn, cursor

    # ── happy-path: empty pack list ───────────────────────────

    def test_empty_packs_returns_empty_list(self):
        conn, cursor = self._make_conn([])
        bot = self._make_bot()

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 1))

        self.assertEqual(result, [])

    # ── happy-path: valid pack with matching title ─────────────

    def test_valid_pack_returned_when_title_matches(self):
        import api

        api._TG_PACK_CACHE.clear()
        row = _make_db_row("mypack", "My Pack")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"mypack": "My Pack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 1))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "mypack")
        self.assertEqual(result[0]["title"], "My Pack")

    def test_valid_pack_link_format(self):
        row = _make_db_row("coolpack", "Cool Pack")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"coolpack": "Cool Pack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 1))

        self.assertEqual(result[0]["link"], "https://t.me/addstickers/coolpack")

    # ── title-sync: updated title propagated to DB and result ─

    def test_title_update_when_telegram_title_differs(self):
        import api

        api._TG_PACK_CACHE.clear()
        row = _make_db_row("mypack", "Old Title")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"mypack": "New Title"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 1))

        self.assertEqual(result[0]["title"], "New Title")

    def test_title_update_executes_sql_update_on_same_cursor(self):
        import api

        api._TG_PACK_CACHE.clear()
        row = _make_db_row("mypack", "Old Title")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"mypack": "New Title"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 42))

        # cursor.executemany should have been called for UPDATE
        calls = cursor.executemany.call_args_list
        update_calls = [c for c in calls if "UPDATE" in str(c)]
        self.assertEqual(len(update_calls), 1)
        # The UPDATE must carry the new title and correct user_id / name
        update_args = update_calls[0][0]
        self.assertIn("UPDATE packs SET title", update_args[0])
        # Arguments to executemany are a list of tuples: [("New Title", 42, "mypack")]
        self.assertEqual(update_args[1][0][0], "New Title")
        self.assertEqual(update_args[1][0][1], 42)
        self.assertEqual(update_args[1][0][2], "mypack")

    def test_title_update_commits_on_existing_connection(self):
        """conn.commit() must be called for a title change (not a new connection)."""
        row = _make_db_row("mypack", "Old Title")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"mypack": "New Title"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        conn.commit.assert_called()

    # ── pack deletion when Telegram raises ────────────────────

    def test_missing_pack_deleted_from_db(self):
        row = _make_db_row("deadpack", "Dead Pack")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(raise_for={"deadpack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 7))

        self.assertEqual(result, [])

    def test_missing_pack_executes_delete_on_same_cursor(self):
        row = _make_db_row("deadpack", "Dead Pack")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(raise_for={"deadpack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 7))

        calls = cursor.executemany.call_args_list
        delete_calls = [c for c in calls if "DELETE" in str(c)]
        self.assertEqual(len(delete_calls), 1)
        delete_args = delete_calls[0][0]
        self.assertIn("DELETE FROM packs", delete_args[0])
        self.assertEqual(delete_args[1][0][0], 7)  # user_id
        self.assertEqual(delete_args[1][0][1], "deadpack")

    def test_missing_pack_commits_delete_on_existing_connection(self):
        row = _make_db_row("deadpack", "Dead Pack")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(raise_for={"deadpack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        conn.commit.assert_called()

    # ── single-connection guarantee (N+1 optimization) ─────────────────

    def test_get_db_called_exactly_once_for_multiple_packs(self):
        """Only one DB connection opened regardless of the number of packs."""
        rows = [
            _make_db_row("pack1", "Pack One"),
            _make_db_row("pack2", "Old Two"),  # title differs → UPDATE
            _make_db_row("pack3", "Pack Three"),
        ]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(
            sticker_sets={
                "pack1": "Pack One",
                "pack2": "New Two",
                "pack3": "Pack Three",
            }
        )

        with patch("api.get_db", return_value=conn) as mock_get_db, patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        mock_get_db.assert_called_once()

    def test_get_db_called_exactly_once_when_pack_deleted(self):
        """Deleting a stale pack must not open a second connection."""
        rows = [_make_db_row("deadpack", "Dead Pack")]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(raise_for={"deadpack"})

        with patch("api.get_db", return_value=conn) as mock_get_db, patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        mock_get_db.assert_called_once()

    def test_get_db_called_exactly_once_when_title_updated(self):
        """Syncing a renamed title must not open a second connection."""
        rows = [_make_db_row("renamed", "Old Name")]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(sticker_sets={"renamed": "New Name"})

        with patch("api.get_db", return_value=conn) as mock_get_db, patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        mock_get_db.assert_called_once()

    # ── connection lifecycle ───────────────────────────────────

    def test_conn_close_called_after_loop(self):
        rows = [_make_db_row("pack1", "Pack One")]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(sticker_sets={"pack1": "Pack One"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        conn.close.assert_called_once()

    def test_conn_close_called_when_all_packs_fail(self):
        """conn.close() is reached even if every pack raises on Telegram lookup."""
        rows = [
            _make_db_row("dead1", "Dead One"),
            _make_db_row("dead2", "Dead Two"),
        ]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(raise_for={"dead1", "dead2"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        conn.close.assert_called_once()

    def test_bot_close_called_in_finally(self):
        """bot.close() is always invoked regardless of outcome."""
        rows = [_make_db_row("pack1", "Pack One")]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(sticker_sets={"pack1": "Pack One"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        bot.close.assert_awaited_once()

    def test_bot_close_called_when_get_sticker_set_raises(self):
        """bot.close() must be awaited even when pack validation fails."""
        rows = [_make_db_row("deadpack", "Dead")]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(raise_for={"deadpack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        bot.close.assert_awaited_once()

    # ── mixed scenario ─────────────────────────────────────────

    def test_mixed_valid_renamed_and_deleted_packs(self):
        """All three branches (match / rename / delete) work in one call."""
        rows = [
            _make_db_row("good", "Good Pack"),
            _make_db_row("renamed", "Old Name"),
            _make_db_row("dead", "Dead Pack"),
        ]
        conn, cursor = self._make_conn(rows)
        bot = self._make_bot(
            sticker_sets={"good": "Good Pack", "renamed": "New Name"},
            raise_for={"dead"},
        )

        with patch("api.get_db", return_value=conn) as mock_get_db, patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 99))

        # Only one DB connection opened throughout
        mock_get_db.assert_called_once()

        # Two valid packs returned; deleted pack excluded
        self.assertEqual(len(result), 2)
        names = {r["name"] for r in result}
        self.assertIn("good", names)
        self.assertIn("renamed", names)
        self.assertNotIn("dead", names)

        # Renamed pack carries the updated title
        renamed = next(r for r in result if r["name"] == "renamed")
        self.assertEqual(renamed["title"], "New Name")

        # bot.close() called exactly once
        bot.close.assert_awaited_once()

    # ── boundary / regression cases ────────────────────────────

    def test_returns_all_packs_when_all_valid(self):
        rows = [_make_db_row(f"pack{i}", f"Pack {i}") for i in range(5)]
        conn, cursor = self._make_conn(rows)
        sticker_sets = {f"pack{i}": f"Pack {i}" for i in range(5)}
        bot = self._make_bot(sticker_sets=sticker_sets)

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 1))

        self.assertEqual(len(result), 5)

    def test_result_contains_all_expected_keys(self):
        row = _make_db_row("mypack", "My Pack")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"mypack": "My Pack"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            result = _run_async(_validate_packs_async("fake:token", 1))

        self.assertIn("name", result[0])
        self.assertIn("title", result[0])
        self.assertIn("link", result[0])

    def test_title_not_changed_when_titles_match(self):
        """No UPDATE executed when Telegram title equals the stored title."""
        row = _make_db_row("samepack", "Same Title")
        conn, cursor = self._make_conn([row])
        bot = self._make_bot(sticker_sets={"samepack": "Same Title"})

        with patch("api.get_db", return_value=conn), patch(
            "telegram.Bot", return_value=bot
        ):
            from api import _validate_packs_async

            _run_async(_validate_packs_async("fake:token", 1))

        calls = cursor.executemany.call_args_list
        update_calls = [c for c in calls if "UPDATE" in str(c)]
        self.assertEqual(len(update_calls), 0)


if __name__ == "__main__":
    unittest.main()
