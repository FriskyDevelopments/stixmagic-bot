"""
Tests for api.py – helpers and routes (post-refactor).

Covers:
 - ok() / err() response envelopes
 - paginate(): page/limit logic, total/pages metadata
 - require_api_key decorator: missing key, wrong key, correct key
 - add_headers (CORS): always wildcard "*" for all routes
 - /api/health endpoint: service name, no bot_mode, db status, version
 - /api/miniapp/packs: requires valid user_id query param
 - /api/miniapp/settings GET: requires user_id, returns mask_inverted
 - /api/miniapp/settings PATCH: requires user_id and JSON body
 - _get_user_packs, _update_pack_title, _delete_pack DB helpers
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# Minimal stubs so api.py can be imported without real Telegram / Flask deps
# ---------------------------------------------------------------------------

def _ensure_stubs():
    """Inject minimal stubs for api.py's module-level imports if needed."""
    if "moderation" not in sys.modules:
        mod_stub = MagicMock()
        mod_stub.create_default_harness = MagicMock(return_value=MagicMock())
        sys.modules["moderation"] = mod_stub


_ensure_stubs()


FAKE_BOT_TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef_gh"


def _make_mock_settings(**kwargs):
    s = MagicMock()
    s.api_key = kwargs.get("api_key", "test-api-key")
    s.telegram_bot_token = kwargs.get("telegram_bot_token", FAKE_BOT_TOKEN)
    s.session_secret = kwargs.get("session_secret", "test-secret")
    s.miniapp_url = kwargs.get("miniapp_url", "")
    s.port = kwargs.get("port", 5000)
    return s


class ApiTestBase(unittest.TestCase):
    """Base class: wires a temp SQLite DB and a Flask test client."""

    def setUp(self):
        # Create a real temp DB file
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        self.mock_settings = _make_mock_settings()

        # Patch get_settings from config.runtime before importing api
        self._patch_runtime = patch(
            "config.runtime.get_settings", return_value=self.mock_settings
        )
        self._patch_runtime.start()

        import importlib
        if "api" in sys.modules:
            import api as api_mod
        else:
            import api as api_mod

        # Overwrite module-level state to use mock settings + temp DB
        api_mod.settings = self.mock_settings
        api_mod.API_KEY = self.mock_settings.api_key
        api_mod.DB_FILE = self.db_path

        # Also patch DB_FILE in infra.db to the same temp file
        import infra.db as db_mod
        db_mod.DB_FILE = self.db_path
        db_mod.init_db()

        self.app = api_mod.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        # Restore DB_FILE to its default after each test
        import api as api_mod
        import infra.db as db_mod
        api_mod.DB_FILE = "bot.db"
        db_mod.DB_FILE = "bot.db"

        self._patch_runtime.stop()
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Response envelope helpers
# ---------------------------------------------------------------------------

class TestResponseEnvelopes(ApiTestBase):

    def test_ok_returns_200_by_default(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.ok({"key": "val"})
        self.assertEqual(resp.status_code, 200)

    def test_ok_body_structure(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.ok({"key": "val"})
        body = json.loads(resp.data)
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["key"], "val")

    def test_ok_custom_status(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.ok({}, status=201)
        self.assertEqual(resp.status_code, 201)

    def test_ok_includes_meta_fields(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.ok({}, pagination={"page": 1})
        body = json.loads(resp.data)
        self.assertIn("pagination", body)

    def test_err_returns_400_by_default(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.err("bad request")
        self.assertEqual(resp.status_code, 400)

    def test_err_body_structure(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.err("bad request", code="bad_req")
        body = json.loads(resp.data)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"]["message"], "bad request")
        self.assertEqual(body["error"]["code"], "bad_req")

    def test_err_without_code(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            resp = api_mod.err("simple error")
        body = json.loads(resp.data)
        self.assertNotIn("code", body["error"])


# ---------------------------------------------------------------------------
# paginate()
# ---------------------------------------------------------------------------

class TestPaginate(ApiTestBase):

    def test_first_page_default_limit(self):
        with self.app.test_request_context("/?page=1"):
            import api as api_mod
            items, meta = api_mod.paginate(list(range(50)))
        self.assertEqual(len(items), api_mod.PAGE_SIZE)
        self.assertEqual(meta["page"], 1)

    def test_page_2(self):
        with self.app.test_request_context("/?page=2&limit=10"):
            import api as api_mod
            items, meta = api_mod.paginate(list(range(25)))
        self.assertEqual(items[0], 10)
        self.assertEqual(meta["page"], 2)

    def test_limit_capped_at_100(self):
        with self.app.test_request_context("/?limit=200"):
            import api as api_mod
            items, meta = api_mod.paginate(list(range(150)))
        self.assertEqual(meta["limit"], 100)

    def test_invalid_page_defaults_to_1(self):
        with self.app.test_request_context("/?page=abc"):
            import api as api_mod
            items, meta = api_mod.paginate(list(range(5)))
        self.assertEqual(meta["page"], 1)

    def test_invalid_limit_uses_page_size(self):
        with self.app.test_request_context("/?limit=xyz"):
            import api as api_mod
            items, meta = api_mod.paginate(list(range(5)))
        self.assertEqual(meta["limit"], api_mod.PAGE_SIZE)

    def test_total_correct(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            _, meta = api_mod.paginate(list(range(37)))
        self.assertEqual(meta["total"], 37)

    def test_pages_ceiling_division(self):
        with self.app.test_request_context("/?limit=10"):
            import api as api_mod
            _, meta = api_mod.paginate(list(range(25)))
        self.assertEqual(meta["pages"], 3)

    def test_empty_result_one_page(self):
        with self.app.test_request_context("/"):
            import api as api_mod
            _, meta = api_mod.paginate([])
        self.assertEqual(meta["pages"], 1)
        self.assertEqual(meta["total"], 0)


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------

class TestCORSHeaders(ApiTestBase):

    def test_all_routes_get_wildcard_cors(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_miniapp_route_also_gets_wildcard_cors(self):
        resp = self.client.get("/api/miniapp/settings?user_id=42")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_api_version_header_always_present(self):
        resp = self.client.get("/api/health")
        self.assertIn("X-API-Version", resp.headers)

    def test_api_version_value(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.headers["X-API-Version"], "1.1")

    def test_allow_headers_includes_x_api_key(self):
        resp = self.client.get("/api/health")
        self.assertIn("X-API-Key", resp.headers.get("Access-Control-Allow-Headers", ""))

    def test_allow_methods_includes_patch(self):
        resp = self.client.get("/api/health")
        self.assertIn("PATCH", resp.headers.get("Access-Control-Allow-Methods", ""))


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------

class TestHealthEndpoint(ApiTestBase):

    def test_health_returns_200(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_ok_true(self):
        data = json.loads(self.client.get("/api/health").data)
        self.assertTrue(data["ok"])

    def test_health_service_is_stixmagic(self):
        data = json.loads(self.client.get("/api/health").data)
        self.assertEqual(data["data"]["service"], "stixmagic")

    def test_health_no_bot_mode_field(self):
        """bot_mode was removed from health response in this PR."""
        data = json.loads(self.client.get("/api/health").data)
        self.assertNotIn("bot_mode", data["data"])

    def test_health_includes_version(self):
        data = json.loads(self.client.get("/api/health").data)
        self.assertIn("version", data["data"])

    def test_health_db_ok(self):
        data = json.loads(self.client.get("/api/health").data)
        self.assertEqual(data["data"]["db"], "ok")

    def test_health_includes_timestamp(self):
        data = json.loads(self.client.get("/api/health").data)
        self.assertIn("timestamp", data["data"])


# ---------------------------------------------------------------------------
# require_api_key decorator
# ---------------------------------------------------------------------------

class TestRequireApiKey(ApiTestBase):

    def test_missing_key_returns_401(self):
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_key_returns_401(self):
        resp = self.client.get("/api/stats", headers={"X-API-Key": "wrong-key"})
        self.assertEqual(resp.status_code, 401)

    def test_correct_key_in_header_passes(self):
        resp = self.client.get("/api/stats", headers={"X-API-Key": "test-api-key"})
        self.assertNotEqual(resp.status_code, 401)

    def test_correct_key_as_query_param_passes(self):
        resp = self.client.get("/api/stats?api_key=test-api-key")
        self.assertNotEqual(resp.status_code, 401)

    def test_unauthorized_code_in_error(self):
        data = json.loads(self.client.get("/api/stats").data)
        self.assertEqual(data["error"]["code"], "unauthorized")


# ---------------------------------------------------------------------------
# /api/miniapp/packs
# ---------------------------------------------------------------------------

class TestMiniappPacksRoute(ApiTestBase):

    def test_missing_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs")
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs?user_id=abc")
        self.assertEqual(resp.status_code, 400)

    def test_empty_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs?user_id=")
        self.assertEqual(resp.status_code, 400)

    def test_missing_user_id_error_code(self):
        data = json.loads(self.client.get("/api/miniapp/packs").data)
        self.assertEqual(data["error"]["code"], "missing_param")

    def test_valid_user_id_returns_200_empty_list(self):
        # Bypass telegram validation by giving invalid-format token
        import api as api_mod
        api_mod.settings.telegram_bot_token = "no-token"
        resp = self.client.get("/api/miniapp/packs?user_id=42")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["data"], [])

    def test_valid_user_id_returns_packs_from_db(self):
        import infra.db as db_mod
        db_mod.add_pack(42, "pack_alpha", "Alpha Pack")

        import api as api_mod
        api_mod.settings.telegram_bot_token = "no-token"
        resp = self.client.get("/api/miniapp/packs?user_id=42")
        data = json.loads(resp.data)
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["name"], "pack_alpha")

    def test_packs_response_includes_link(self):
        import infra.db as db_mod
        db_mod.add_pack(99, "mypacks", "My Packs")

        import api as api_mod
        api_mod.settings.telegram_bot_token = "no-token"
        resp = self.client.get("/api/miniapp/packs?user_id=99")
        data = json.loads(resp.data)
        self.assertIn("link", data["data"][0])
        self.assertIn("t.me/addstickers", data["data"][0]["link"])

    def test_negative_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/packs?user_id=-5")
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# /api/miniapp/settings GET
# ---------------------------------------------------------------------------

class TestMiniappSettingsGet(ApiTestBase):

    def test_missing_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/settings")
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_user_id_returns_400(self):
        resp = self.client.get("/api/miniapp/settings?user_id=foo")
        self.assertEqual(resp.status_code, 400)

    def test_valid_user_id_default_mask_inverted_false(self):
        resp = self.client.get("/api/miniapp/settings?user_id=42")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data["data"]["mask_inverted"])

    def test_returns_correct_user_id_in_response(self):
        resp = self.client.get("/api/miniapp/settings?user_id=42")
        data = json.loads(resp.data)
        self.assertEqual(data["data"]["user_id"], 42)

    def test_reflects_existing_setting(self):
        import infra.db as db_mod
        db_mod.set_mask_inverted(77, True)
        resp = self.client.get("/api/miniapp/settings?user_id=77")
        data = json.loads(resp.data)
        self.assertTrue(data["data"]["mask_inverted"])


# ---------------------------------------------------------------------------
# /api/miniapp/settings PATCH
# ---------------------------------------------------------------------------

class TestMiniappSettingsPatch(ApiTestBase):

    def test_missing_user_id_returns_400(self):
        resp = self.client.patch(
            "/api/miniapp/settings",
            json={"mask_inverted": True},
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_user_id_returns_400(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=xyz",
            json={"mask_inverted": True},
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_json_body_returns_400(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=42",
            data="not-json",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "invalid_body")

    def test_patch_sets_mask_inverted_true(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=42",
            json={"mask_inverted": True},
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["data"]["mask_inverted"])

    def test_patch_sets_mask_inverted_false(self):
        import infra.db as db_mod
        db_mod.set_mask_inverted(42, True)
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=42",
            json={"mask_inverted": False},
        )
        data = json.loads(resp.data)
        self.assertFalse(data["data"]["mask_inverted"])

    def test_patch_returns_user_id(self):
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=55",
            json={"mask_inverted": True},
        )
        data = json.loads(resp.data)
        self.assertEqual(data["data"]["user_id"], 55)

    def test_patch_with_empty_json_body_returns_400(self):
        """Empty JSON dict {} is falsy – the route rejects it as invalid_body."""
        resp = self.client.patch(
            "/api/miniapp/settings?user_id=42",
            json={},
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data["error"]["code"], "invalid_body")


# ---------------------------------------------------------------------------
# _get_user_packs / _update_pack_title / _delete_pack DB helpers
# ---------------------------------------------------------------------------

class TestDbHelpers(ApiTestBase):

    def test_get_user_packs_returns_empty_for_new_user(self):
        import api as api_mod
        result = api_mod._get_user_packs(9999)
        self.assertEqual(result, [])

    def test_get_user_packs_returns_dicts(self):
        import infra.db as db_mod
        db_mod.add_pack(1, "pack_x", "Pack X")
        import api as api_mod
        result = api_mod._get_user_packs(1)
        self.assertEqual(len(result), 1)
        self.assertIn("name", result[0])
        self.assertIn("title", result[0])

    def test_update_pack_title(self):
        import infra.db as db_mod
        db_mod.add_pack(1, "pack_y", "Old Title")
        import api as api_mod
        api_mod._update_pack_title(1, "pack_y", "New Title")
        packs = db_mod.get_user_packs(1)
        self.assertEqual(packs[0][1], "New Title")

    def test_delete_pack_removes_row(self):
        import infra.db as db_mod
        db_mod.add_pack(1, "pack_z", "To Delete")
        import api as api_mod
        api_mod._delete_pack(1, "pack_z")
        packs = db_mod.get_user_packs(1)
        self.assertEqual(len(packs), 0)

    def test_delete_pack_only_affects_named_pack(self):
        import infra.db as db_mod
        db_mod.add_pack(1, "keep_this", "Keep")
        db_mod.add_pack(1, "remove_this", "Remove")
        import api as api_mod
        api_mod._delete_pack(1, "remove_this")
        packs = db_mod.get_user_packs(1)
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0][0], "keep_this")


if __name__ == "__main__":
    unittest.main()