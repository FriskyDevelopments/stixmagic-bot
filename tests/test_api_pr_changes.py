"""
Tests for api.py – PR changes: new miniapp route behavior and helper functions.

Covers (focused on PR diff changes):
 - health endpoint: no bot_mode field, service="stixmagic"
 - CORS headers: now always wildcard (*) for all routes
 - miniapp_packs: requires user_id query param, returns 400 when missing/invalid
 - miniapp_settings_get: requires user_id query param, returns 400 when missing/invalid
 - miniapp_settings_patch: requires user_id query param, no miniapp auth
 - miniapp_settings_patch: returns 400 when no JSON body
 - _get_user_packs: returns list of row dicts
 - _update_pack_title: updates title in DB
 - _delete_pack: deletes pack from DB
 - ok() / err() response envelope helpers
 - paginate(): pagination math
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FAKE_BOT_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh"


def _make_mock_settings(**kwargs):
    s = MagicMock()
    s.api_key = kwargs.get("api_key", "test-api-key")
    s.telegram_bot_token = kwargs.get("telegram_bot_token", FAKE_BOT_TOKEN)
    s.session_secret = kwargs.get("session_secret", "test-session-secret")
    s.miniapp_url = kwargs.get("miniapp_url", "")
    s.port = kwargs.get("port", 5000)
    return s


def _init_test_db(db_path: str) -> None:
    """Initialize the test database tables."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            title TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            mask_inverted INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS catalog_packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            type TEXT DEFAULT 'image',
            public INTEGER DEFAULT 1,
            safe INTEGER DEFAULT 1,
            likes INTEGER DEFAULT 0,
            dislikes INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            added_at INTEGER NOT NULL,
            added_by INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS catalog_reactions (
            user_id INTEGER NOT NULL,
            pack_name TEXT NOT NULL,
            reaction TEXT NOT NULL,
            PRIMARY KEY (user_id, pack_name)
        )
    """)
    conn.commit()
    conn.close()


class NewApiTestBase(unittest.TestCase):
    """Base class for testing the new api.py with user_id-based miniapp routes."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        _init_test_db(self.db_path)

        self.mock_settings = _make_mock_settings()

        # Patch config.runtime.get_settings before any api.py imports
        self._patch_runtime = patch(
            "config.runtime.get_settings",
            return_value=self.mock_settings,
        )
        self._patch_runtime.start()

        # Patch create_default_harness to avoid real moderation setup
        self._patch_moderation = patch(
            "moderation.create_default_harness",
            return_value=MagicMock(
                state=MagicMock(return_value={"replay": []}),
                simulate_event=MagicMock(return_value={}),
            ),
        )
        self._patch_moderation.start()

        import api as api_mod
        # Override module-level settings and DB path
        api_mod.settings = self.mock_settings
        api_mod.API_KEY = self.mock_settings.api_key
        api_mod.DB_FILE = self.db_path

        self.api_mod = api_mod
        self.app = api_mod.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self._patch_runtime.stop()
        self._patch_moderation.stop()
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass


# ── Health endpoint (changed: no bot_mode, service name changed) ──────────────

class TestHealthEndpointPR(NewApiTestBase):

    def test_health_returns_200(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_service_is_stixmagic(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertEqual(data["data"]["service"], "stixmagic")

    def test_health_no_bot_mode_field(self):
        """PR removed bot_mode from health response."""
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertNotIn("bot_mode", data["data"])

    def test_health_includes_version(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertIn("version", data["data"])
        self.assertEqual(data["data"]["version"], "1.1")

    def test_health_includes_db_status(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertIn("db", data["data"])

    def test_health_includes_timestamp(self):
        resp = self.client.get("/api/health")
        data = json.loads(resp.data)
        self.assertIn("timestamp", data["data"])
        self.assertIsInstance(data["data"]["timestamp"], int)


# ── CORS headers (changed: now always wildcard) ──────────────────────────────

class TestCorsHeadersPR(NewApiTestBase):

    def test_health_has_wildcard_cors(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_miniapp_packs_has_wildcard_cors(self):
        """PR change: miniapp routes now return wildcard CORS, not restricted."""
        resp = self.client.get("/api/miniapp/packs?user_id=42")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_miniapp_settings_has_wildcard_cors(self):
        resp = self.client.get("/api/miniapp/settings?user_id=42")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_api_version_header_present(self):
        resp = self.client.get("/api/health")
        self.assertIn("X-API-Version", resp.headers)
        self.assertEqual(resp.headers["X-API-Version"], "1.1")

    def test_allowed_headers_match_simplified_set(self):
        """PR simplified Allow-Headers to just X-API-Key and Content-Type."""
        resp = self.client.get("/api/health")
        allow_headers = resp.headers.get("Access-Control-Allow-Headers", "")
        self.assertIn("X-API-Key", allow_headers)
        self.assertIn("Content-Type", allow_headers)

    def test_options_preflight_handled(self):
        resp = self.client.options("/api/health")
        self.assertIn(resp.status_code, (200, 204))


# ── miniapp_packs route (changed: user_id param instead of miniapp auth) ──────

class TestMiniappPacksRoute(NewApiTestBase):

    def test_missing_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs")
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "missing_param")

    def test_non_numeric_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs?user_id=abc")
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "missing_param")

    def test_empty_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs?user_id=")
        self.assertEqual(resp.status_code, 400)

    def test_valid_user_id_returns_200_empty_packs(self):
        # Token doesn't match the pattern so falls back to DB
        self.api_mod.settings.telegram_bot_token = "invalid-token-no-match"
        resp = self.client.get("/api/miniapp/packs?user_id=42")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"], [])

    def test_valid_user_id_returns_db_packs(self):
        self.api_mod.settings.telegram_bot_token = "invalid-token-no-match"
        # Insert a pack directly into the DB
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)",
            (42, "test_pack_xyz", "My Test Pack")
        )
        conn.commit()
        conn.close()

        resp = self.client.get("/api/miniapp/packs?user_id=42")
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["name"], "test_pack_xyz")
        self.assertEqual(data["data"][0]["title"], "My Test Pack")
        self.assertIn("link", data["data"][0])
        self.assertIn("t.me/addstickers", data["data"][0]["link"])

    def test_no_api_key_required(self):
        """Miniapp packs route doesn't require API key (PR removed require_miniapp_auth)."""
        self.api_mod.settings.telegram_bot_token = "invalid-token-no-match"
        resp = self.client.get("/api/miniapp/packs?user_id=42")
        self.assertNotEqual(resp.status_code, 401)

    def test_different_users_see_different_packs(self):
        self.api_mod.settings.telegram_bot_token = "invalid-token-no-match"
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", (1, "user1_pack", "User 1 Pack"))
        conn.execute("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", (2, "user2_pack", "User 2 Pack"))
        conn.commit()
        conn.close()

        resp1 = self.client.get("/api/miniapp/packs?user_id=1")
        resp2 = self.client.get("/api/miniapp/packs?user_id=2")
        data1 = json.loads(resp1.data)
        data2 = json.loads(resp2.data)
        self.assertEqual(len(data1["data"]), 1)
        self.assertEqual(data1["data"][0]["name"], "user1_pack")
        self.assertEqual(len(data2["data"]), 1)
        self.assertEqual(data2["data"][0]["name"], "user2_pack")


# ── miniapp_settings_get route (changed: user_id param) ──────────────────────

class TestMiniappSettingsGetRoute(NewApiTestBase):

    def test_missing_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/settings")
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "missing_param")

    def test_non_numeric_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/settings?user_id=abc")
        self.assertEqual(resp.status_code, 400)

    def test_valid_user_id_returns_200_defaults(self):
        resp = self.client.get("/api/miniapp/settings?user_id=42")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertIn("mask_inverted", data["data"])
        self.assertFalse(data["data"]["mask_inverted"])

    def test_user_id_in_response(self):
        resp = self.client.get("/api/miniapp/settings?user_id=99")
        data = json.loads(resp.data)
        self.assertEqual(data["data"]["user_id"], 99)

    def test_mask_inverted_reflects_db_value(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO user_settings (user_id, mask_inverted) VALUES (?, ?)",
            (55, 1)
        )
        conn.commit()
        conn.close()
        resp = self.client.get("/api/miniapp/settings?user_id=55")
        data = json.loads(resp.data)
        self.assertTrue(data["data"]["mask_inverted"])

    def test_no_api_key_required(self):
        resp = self.client.get("/api/miniapp/settings?user_id=42")
        self.assertNotEqual(resp.status_code, 401)


# ── miniapp_settings_patch route (changed: user_id param) ────────────────────

class TestMiniappSettingsPatchRoute(NewApiTestBase):

    def test_missing_user_id_returns_400(self):
        resp = self.client.patch(
            "/api/miniapp/settings",
            json={"mask_inverted": True},
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_user_id_returns_400(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=notanumber",
            json={"mask_inverted": True},
        )
        self.assertEqual(resp.status_code, 400)

    def test_no_json_body_returns_400(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=42",
            data="not-json",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "invalid_body")

    def test_patch_mask_inverted_true(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=42",
            json={"mask_inverted": True},
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["data"]["mask_inverted"])

    def test_patch_mask_inverted_false(self):
        # First set to True
        self.client.patch("/api/miniapp/settings?user_id=42", json={"mask_inverted": True})
        # Then set to False
        resp = self.client.patch("/api/miniapp/settings?user_id=42", json={"mask_inverted": False})
        data = json.loads(resp.data)
        self.assertFalse(data["data"]["mask_inverted"])

    def test_patch_persists_to_db(self):
        self.client.patch("/api/miniapp/settings?user_id=77", json={"mask_inverted": True})
        resp = self.client.get("/api/miniapp/settings?user_id=77")
        data = json.loads(resp.data)
        self.assertTrue(data["data"]["mask_inverted"])

    def test_patch_upsert_updates_existing(self):
        self.client.patch("/api/miniapp/settings?user_id=88", json={"mask_inverted": True})
        self.client.patch("/api/miniapp/settings?user_id=88", json={"mask_inverted": False})
        resp = self.client.get("/api/miniapp/settings?user_id=88")
        data = json.loads(resp.data)
        self.assertFalse(data["data"]["mask_inverted"])


# ── DB helper functions (_get_user_packs, _update_pack_title, _delete_pack) ───

class TestApiDbHelpers(NewApiTestBase):
    """Tests for the new DB helper functions added in this PR."""

    def _seed_pack(self, user_id, name, title):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)",
            (user_id, name, title)
        )
        conn.commit()
        conn.close()

    def _get_pack_title(self, user_id, name):
        conn = sqlite3.connect(self.db_path)
        c = conn.execute(
            "SELECT title FROM packs WHERE user_id = ? AND name = ?",
            (user_id, name)
        )
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    def test_get_user_packs_returns_empty_for_unknown_user(self):
        from api import _get_user_packs
        result = _get_user_packs(9999)
        self.assertEqual(result, [])

    def test_get_user_packs_returns_list_of_dicts(self):
        self._seed_pack(100, "pack_a", "Pack A")
        self._seed_pack(100, "pack_b", "Pack B")
        from api import _get_user_packs
        result = _get_user_packs(100)
        self.assertEqual(len(result), 2)
        # Each entry should have 'name' and 'title' keys
        for item in result:
            self.assertIn("name", item)
            self.assertIn("title", item)

    def test_get_user_packs_scoped_to_user(self):
        self._seed_pack(200, "user200_pack", "User 200 Pack")
        self._seed_pack(201, "user201_pack", "User 201 Pack")
        from api import _get_user_packs
        result = _get_user_packs(200)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "user200_pack")

    def test_update_pack_title_changes_title(self):
        self._seed_pack(300, "updateable_pack", "Old Title")
        from api import _update_pack_title
        _update_pack_title(300, "updateable_pack", "New Title")
        title = self._get_pack_title(300, "updateable_pack")
        self.assertEqual(title, "New Title")

    def test_update_pack_title_scoped_to_user(self):
        self._seed_pack(400, "shared_name", "User 400 Title")
        self._seed_pack(401, "shared_name", "User 401 Title")
        from api import _update_pack_title
        _update_pack_title(400, "shared_name", "Only User 400 Changed")
        # User 401's pack should be unchanged
        title_401 = self._get_pack_title(401, "shared_name")
        self.assertEqual(title_401, "User 401 Title")

    def test_delete_pack_removes_pack(self):
        self._seed_pack(500, "to_delete", "Will Be Gone")
        from api import _delete_pack
        _delete_pack(500, "to_delete")
        title = self._get_pack_title(500, "to_delete")
        self.assertIsNone(title)

    def test_delete_pack_only_removes_specified_pack(self):
        self._seed_pack(600, "pack_keep", "Keep This")
        self._seed_pack(600, "pack_remove", "Remove This")
        from api import _delete_pack
        _delete_pack(600, "pack_remove")
        title_keep = self._get_pack_title(600, "pack_keep")
        title_remove = self._get_pack_title(600, "pack_remove")
        self.assertEqual(title_keep, "Keep This")
        self.assertIsNone(title_remove)

    def test_delete_pack_nonexistent_no_error(self):
        from api import _delete_pack
        _delete_pack(700, "ghost_pack")  # Should not raise


# ── ok() / err() response helpers ────────────────────────────────────────────

class TestResponseHelpers(NewApiTestBase):

    def test_ok_sets_status_200_by_default(self):
        with self.app.test_request_context():
            from api import ok
            resp = ok({"key": "value"})
            self.assertEqual(resp.status_code, 200)

    def test_ok_response_has_ok_true(self):
        with self.app.test_request_context():
            from api import ok
            resp = ok({})
            data = json.loads(resp.data)
            self.assertTrue(data["ok"])

    def test_ok_includes_data(self):
        with self.app.test_request_context():
            from api import ok
            resp = ok({"answer": 42})
            data = json.loads(resp.data)
            self.assertEqual(data["data"]["answer"], 42)

    def test_ok_custom_status(self):
        with self.app.test_request_context():
            from api import ok
            resp = ok({}, status=201)
            self.assertEqual(resp.status_code, 201)

    def test_err_sets_status_400_by_default(self):
        with self.app.test_request_context():
            from api import err
            resp = err("Something wrong")
            self.assertEqual(resp.status_code, 400)

    def test_err_response_has_ok_false(self):
        with self.app.test_request_context():
            from api import err
            resp = err("Something wrong")
            data = json.loads(resp.data)
            self.assertFalse(data["ok"])

    def test_err_includes_message(self):
        with self.app.test_request_context():
            from api import err
            resp = err("Custom error message")
            data = json.loads(resp.data)
            self.assertEqual(data["error"]["message"], "Custom error message")

    def test_err_includes_code_when_provided(self):
        with self.app.test_request_context():
            from api import err
            resp = err("Not found", 404, "not_found")
            data = json.loads(resp.data)
            self.assertEqual(data["error"]["code"], "not_found")

    def test_err_custom_status(self):
        with self.app.test_request_context():
            from api import err
            resp = err("Unauthorized", 401, "unauthorized")
            self.assertEqual(resp.status_code, 401)


# ── paginate() function ───────────────────────────────────────────────────────

class TestPaginateFunction(NewApiTestBase):

    def _paginate(self, items, page=1, limit=None):
        from api import paginate, PAGE_SIZE
        query_string = f"page={page}"
        if limit is not None:
            query_string += f"&limit={limit}"
        with self.app.test_request_context(f"/test?{query_string}"):
            return paginate(items)

    def test_first_page_of_small_result(self):
        items = list(range(5))
        result_items, pagination = self._paginate(items, page=1, limit=5)
        self.assertEqual(result_items, list(range(5)))
        self.assertEqual(pagination["total"], 5)

    def test_pagination_page_2(self):
        items = list(range(25))
        result_items, pagination = self._paginate(items, page=2, limit=10)
        self.assertEqual(result_items, list(range(10, 20)))

    def test_pagination_total_pages(self):
        items = list(range(25))
        _, pagination = self._paginate(items, page=1, limit=10)
        self.assertEqual(pagination["pages"], 3)

    def test_pagination_empty_result(self):
        items = []
        result_items, pagination = self._paginate(items, page=1)
        self.assertEqual(result_items, [])
        self.assertEqual(pagination["total"], 0)
        self.assertEqual(pagination["pages"], 1)

    def test_invalid_page_defaults_to_1(self):
        items = list(range(5))
        with self.app.test_request_context("/test?page=abc"):
            from api import paginate
            result_items, pagination = paginate(items)
        self.assertEqual(pagination["page"], 1)

    def test_limit_capped_at_100(self):
        items = list(range(200))
        result_items, pagination = self._paginate(items, page=1, limit=200)
        self.assertEqual(pagination["limit"], 100)
        self.assertEqual(len(result_items), 100)

    def test_limit_minimum_is_1(self):
        items = list(range(10))
        result_items, pagination = self._paginate(items, page=1, limit=0)
        self.assertEqual(pagination["limit"], 1)


# ── require_api_key decorator ─────────────────────────────────────────────────

class TestRequireApiKey(NewApiTestBase):

    def test_missing_api_key_returns_401(self):
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "unauthorized")

    def test_wrong_api_key_returns_401(self):
        resp = self.client.get("/api/stats", headers={"X-API-Key": "wrong-key"})
        self.assertEqual(resp.status_code, 401)

    def test_correct_api_key_via_header(self):
        resp = self.client.get("/api/stats", headers={"X-API-Key": "test-api-key"})
        self.assertEqual(resp.status_code, 200)

    def test_correct_api_key_via_query_param(self):
        resp = self.client.get("/api/stats?api_key=test-api-key")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()