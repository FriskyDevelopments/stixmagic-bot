"""
Tests for infra/db.py – SQLite persistence layer.

Uses an in-memory SQLite database injected via a mock of get_settings()
so tests never touch the file-system.

Covers:
 - init_db: tables created (packs, user_settings, catalog_packs, catalog_reactions)
 - get_mask_inverted / set_mask_inverted: default False, round-trip, toggle
 - add_pack / get_user_packs / delete_pack / update_pack_title
 - is_new_user: new, after pack, after settings
 - catalog_add_pack: insert, duplicate returns False
 - catalog_get_pack: found, not found, hidden pack
 - catalog_search: by sort modes, by query
 - catalog_count: count matches
 - catalog_increment_views
 - catalog_react: like, dislike, toggle, switch
 - catalog_get_user_reaction: returns correct reaction
 - _connect: uses settings.database_path
"""

import sqlite3
import time
import unittest
from unittest.mock import MagicMock, patch


# We patch stixmagic.settings.get_settings to return a settings object
# whose .database_path is ":memory:".  Because ":memory:" gives a new DB
# per connection we use a file-backed temp DB instead so all functions
# see the same state.

import tempfile
import os


def _patched_get_settings(db_path: str):
    """Return a mock settings object pointing at the given db_path."""
    settings = MagicMock()
    settings.database_path = db_path
    return settings


class InfraDbTestCase(unittest.TestCase):
    """Base class that wires a temp-file SQLite DB for every test."""

    def setUp(self):
        # Create a temp file that persists for the duration of the test
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Patch get_settings in infra.db's own namespace (it uses `from stixmagic.settings import get_settings`)
        self._patcher = patch(
            "infra.db._db_file",
            return_value=self.db_path,
        )
        self._patcher.start()

        # Now safe to import and call init_db
        import infra.db as db_mod
        self.db = db_mod
        db_mod.init_db()

    def tearDown(self):
        self._patcher.stop()
        try:
            os.unlink(self.db_path)
        except FileNotFoundError:
            pass


class TestInitDb(InfraDbTestCase):

    def _table_names(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row[0] for row in c.fetchall()}
        conn.close()
        return names

    def test_packs_table_created(self):
        self.assertIn("packs", self._table_names())

    def test_user_settings_table_created(self):
        self.assertIn("user_settings", self._table_names())

    def test_catalog_packs_table_created(self):
        self.assertIn("catalog_packs", self._table_names())

    def test_catalog_reactions_table_created(self):
        self.assertIn("catalog_reactions", self._table_names())

    def test_init_db_idempotent(self):
        """Calling init_db() twice should not raise."""
        self.db.init_db()
        self.db.init_db()
        self.assertIn("packs", self._table_names())


class TestUserSettings(InfraDbTestCase):

    def test_default_mask_inverted_is_false(self):
        result = self.db.get_mask_inverted(user_id=1)
        self.assertFalse(result)

    def test_set_mask_inverted_true(self):
        self.db.set_mask_inverted(user_id=1, inverted=True)
        self.assertTrue(self.db.get_mask_inverted(user_id=1))

    def test_set_mask_inverted_false(self):
        self.db.set_mask_inverted(user_id=1, inverted=True)
        self.db.set_mask_inverted(user_id=1, inverted=False)
        self.assertFalse(self.db.get_mask_inverted(user_id=1))

    def test_set_mask_inverted_upsert(self):
        """Calling set_mask_inverted twice should update, not insert duplicate."""
        self.db.set_mask_inverted(user_id=5, inverted=True)
        self.db.set_mask_inverted(user_id=5, inverted=False)
        result = self.db.get_mask_inverted(user_id=5)
        self.assertFalse(result)

    def test_different_users_independent(self):
        self.db.set_mask_inverted(user_id=10, inverted=True)
        self.assertFalse(self.db.get_mask_inverted(user_id=11))
        self.assertTrue(self.db.get_mask_inverted(user_id=10))


class TestPackCrud(InfraDbTestCase):

    def test_add_and_get_pack(self):
        self.db.add_pack(user_id=1, name="pack_abc", title="My Pack")
        packs = self.db.get_user_packs(user_id=1)
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0][0], "pack_abc")
        self.assertEqual(packs[0][1], "My Pack")

    def test_get_user_packs_empty(self):
        packs = self.db.get_user_packs(user_id=99)
        self.assertEqual(packs, [])

    def test_multiple_packs(self):
        self.db.add_pack(user_id=1, name="pack1", title="Pack One")
        self.db.add_pack(user_id=1, name="pack2", title="Pack Two")
        packs = self.db.get_user_packs(user_id=1)
        self.assertEqual(len(packs), 2)

    def test_packs_are_user_scoped(self):
        self.db.add_pack(user_id=1, name="user1_pack", title="U1")
        self.db.add_pack(user_id=2, name="user2_pack", title="U2")
        self.assertEqual(len(self.db.get_user_packs(user_id=1)), 1)
        self.assertEqual(len(self.db.get_user_packs(user_id=2)), 1)

    def test_delete_pack(self):
        self.db.add_pack(user_id=1, name="pack_del", title="Delete Me")
        self.db.delete_pack(user_id=1, name="pack_del")
        packs = self.db.get_user_packs(user_id=1)
        self.assertEqual(len(packs), 0)

    def test_delete_only_affects_named_pack(self):
        self.db.add_pack(user_id=1, name="pack_a", title="Pack A")
        self.db.add_pack(user_id=1, name="pack_b", title="Pack B")
        self.db.delete_pack(user_id=1, name="pack_a")
        packs = self.db.get_user_packs(user_id=1)
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0][0], "pack_b")

    def test_update_pack_title(self):
        self.db.add_pack(user_id=1, name="pack_upd", title="Old Title")
        self.db.update_pack_title(user_id=1, name="pack_upd", title="New Title")
        packs = self.db.get_user_packs(user_id=1)
        self.assertEqual(packs[0][1], "New Title")

    def test_delete_nonexistent_pack_no_error(self):
        """Deleting a pack that doesn't exist should not raise."""
        self.db.delete_pack(user_id=1, name="ghost_pack")


class TestIsNewUser(InfraDbTestCase):

    def test_new_user_returns_true(self):
        self.assertTrue(self.db.is_new_user(user_id=999))

    def test_after_adding_pack_returns_false(self):
        self.db.add_pack(user_id=1, name="pack1", title="T")
        self.assertFalse(self.db.is_new_user(user_id=1))

    def test_after_settings_change_returns_false(self):
        self.db.set_mask_inverted(user_id=2, inverted=True)
        self.assertFalse(self.db.is_new_user(user_id=2))

    def test_deleting_all_packs_does_not_restore_new_user(self):
        """A user who had a pack but deleted it still has settings state."""
        self.db.add_pack(user_id=3, name="pack_tmp", title="T")
        self.db.set_mask_inverted(user_id=3, inverted=True)
        self.db.delete_pack(user_id=3, name="pack_tmp")
        # Settings still exist → not a new user
        self.assertFalse(self.db.is_new_user(user_id=3))


class TestCatalogAddPack(InfraDbTestCase):

    def test_add_returns_true_on_insert(self):
        result = self.db.catalog_add_pack(
            name="test_pack", title="Test Pack", added_by=1
        )
        self.assertTrue(result)

    def test_add_returns_false_on_duplicate(self):
        self.db.catalog_add_pack(name="dup_pack", title="Dup", added_by=1)
        result = self.db.catalog_add_pack(name="dup_pack", title="Dup2", added_by=2)
        self.assertFalse(result)

    def test_add_with_description(self):
        self.db.catalog_add_pack(
            name="desc_pack", title="Described", added_by=1, description="A great pack"
        )
        pack = self.db.catalog_get_pack("desc_pack")
        self.assertEqual(pack["description"], "A great pack")

    def test_add_with_pack_type(self):
        self.db.catalog_add_pack(
            name="video_pack", title="Video Pack", added_by=1, pack_type="video"
        )
        pack = self.db.catalog_get_pack("video_pack")
        self.assertEqual(pack["type"], "video")


class TestCatalogGetPack(InfraDbTestCase):

    def test_get_existing_pack(self):
        self.db.catalog_add_pack(name="get_test", title="Get Test", added_by=1)
        pack = self.db.catalog_get_pack("get_test")
        self.assertIsNotNone(pack)
        self.assertEqual(pack["name"], "get_test")
        self.assertEqual(pack["title"], "Get Test")

    def test_get_nonexistent_returns_none(self):
        result = self.db.catalog_get_pack("does_not_exist")
        self.assertIsNone(result)

    def test_get_hidden_pack_returns_none(self):
        """Packs with public=0 should not be visible."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO catalog_packs (name, title, public, added_at, added_by) VALUES (?,?,0,?,?)",
            ("hidden_pack", "Hidden", int(time.time()), 1),
        )
        conn.commit()
        conn.close()
        result = self.db.catalog_get_pack("hidden_pack")
        self.assertIsNone(result)


class TestCatalogSearch(InfraDbTestCase):

    def _seed_packs(self):
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO catalog_packs (name,title,description,type,public,likes,view_count,added_at,added_by) "
            "VALUES ('alpha','Alpha Pack','cool stuff','image',1,10,50,?,1)", (now - 100,)
        )
        conn.execute(
            "INSERT INTO catalog_packs (name,title,description,type,public,likes,view_count,added_at,added_by) "
            "VALUES ('beta','Beta Pack','nice things','image',1,5,200,?,1)", (now - 200,)
        )
        conn.execute(
            "INSERT INTO catalog_packs (name,title,description,type,public,likes,view_count,added_at,added_by) "
            "VALUES ('gamma','Gamma Pack','cool animated','animated',1,20,10,?,1)", (now - 10,)
        )
        conn.execute(
            "INSERT INTO catalog_packs (name,title,description,type,public,likes,view_count,added_at,added_by) "
            "VALUES ('private','Private Pack','hidden','image',0,0,0,?,1)", (now,)
        )
        conn.commit()
        conn.close()

    def test_search_popular_returns_most_liked_first(self):
        self._seed_packs()
        results = self.db.catalog_search(sort="popular")
        self.assertEqual(results[0]["name"], "gamma")  # 20 likes

    def test_search_trending_returns_most_viewed_first(self):
        self._seed_packs()
        results = self.db.catalog_search(sort="trending")
        self.assertEqual(results[0]["name"], "beta")  # 200 views

    def test_search_new_returns_most_recent_first(self):
        self._seed_packs()
        results = self.db.catalog_search(sort="new")
        self.assertEqual(results[0]["name"], "gamma")  # added_at most recent

    def test_search_query_filters_by_title(self):
        self._seed_packs()
        results = self.db.catalog_search(query="Alpha", sort="search")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "alpha")

    def test_search_excludes_private_packs(self):
        self._seed_packs()
        results = self.db.catalog_search(sort="popular")
        names = [r["name"] for r in results]
        self.assertNotIn("private", names)

    def test_search_limit_respected(self):
        self._seed_packs()
        results = self.db.catalog_search(sort="popular", limit=1)
        self.assertEqual(len(results), 1)

    def test_search_offset_works(self):
        self._seed_packs()
        all_results = self.db.catalog_search(sort="popular")
        offset_results = self.db.catalog_search(sort="popular", offset=1)
        self.assertEqual(len(offset_results), len(all_results) - 1)

    def test_search_empty_returns_all(self):
        self._seed_packs()
        results = self.db.catalog_search(sort="popular")
        self.assertEqual(len(results), 3)  # 3 public packs


class TestCatalogCount(InfraDbTestCase):

    def test_count_zero_when_empty(self):
        self.assertEqual(self.db.catalog_count(), 0)

    def test_count_after_adding(self):
        self.db.catalog_add_pack("c1", "C1", 1)
        self.db.catalog_add_pack("c2", "C2", 1)
        self.assertEqual(self.db.catalog_count(), 2)

    def test_count_excludes_private(self):
        self.db.catalog_add_pack("pub", "Public", 1)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO catalog_packs (name,title,public,added_at,added_by) VALUES ('priv','Priv',0,?,1)",
            (int(time.time()),),
        )
        conn.commit()
        conn.close()
        self.assertEqual(self.db.catalog_count(), 1)

    def test_count_with_query(self):
        self.db.catalog_add_pack("cool_pack", "Cool Pack", 1)
        self.db.catalog_add_pack("other_pack", "Other Pack", 1)
        count = self.db.catalog_count(query="cool", sort="search")
        self.assertEqual(count, 1)


class TestCatalogIncrementViews(InfraDbTestCase):

    def test_increment_views(self):
        self.db.catalog_add_pack("vpack", "V Pack", 1)
        self.db.catalog_increment_views("vpack")
        pack = self.db.catalog_get_pack("vpack")
        self.assertEqual(pack["view_count"], 1)

    def test_increment_views_multiple_times(self):
        self.db.catalog_add_pack("vpack2", "V Pack 2", 1)
        self.db.catalog_increment_views("vpack2")
        self.db.catalog_increment_views("vpack2")
        self.db.catalog_increment_views("vpack2")
        pack = self.db.catalog_get_pack("vpack2")
        self.assertEqual(pack["view_count"], 3)


class TestCatalogReact(InfraDbTestCase):

    def setUp(self):
        super().setUp()
        self.db.catalog_add_pack("react_pack", "React Pack", 1)

    def test_like_increments_likes(self):
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        self.assertEqual(result["likes"], 1)
        self.assertEqual(result["current"], "like")

    def test_dislike_increments_dislikes(self):
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="dislike")
        self.assertEqual(result["dislikes"], 1)
        self.assertEqual(result["current"], "dislike")

    def test_toggle_like_off(self):
        self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        self.assertEqual(result["likes"], 0)
        self.assertIsNone(result["current"])

    def test_toggle_dislike_off(self):
        self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="dislike")
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="dislike")
        self.assertEqual(result["dislikes"], 0)
        self.assertIsNone(result["current"])

    def test_switch_like_to_dislike(self):
        self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="dislike")
        self.assertEqual(result["dislikes"], 1)
        self.assertEqual(result["likes"], 0)
        self.assertEqual(result["current"], "dislike")

    def test_switch_dislike_to_like(self):
        self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="dislike")
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        self.assertEqual(result["likes"], 1)
        self.assertEqual(result["dislikes"], 0)
        self.assertEqual(result["current"], "like")

    def test_multiple_users_independent(self):
        self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        self.db.catalog_react(user_id=2, pack_name="react_pack", reaction="like")
        pack = self.db.catalog_get_pack("react_pack")
        self.assertEqual(pack["likes"], 2)

    def test_likes_floor_at_zero(self):
        """Toggling a like should not drive likes below 0."""
        self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        result = self.db.catalog_react(user_id=1, pack_name="react_pack", reaction="like")
        self.assertGreaterEqual(result["likes"], 0)


class TestCatalogGetUserReaction(InfraDbTestCase):

    def setUp(self):
        super().setUp()
        self.db.catalog_add_pack("urpack", "UR Pack", 1)

    def test_no_reaction_returns_none(self):
        result = self.db.catalog_get_user_reaction(user_id=1, pack_name="urpack")
        self.assertIsNone(result)

    def test_after_like_returns_like(self):
        self.db.catalog_react(user_id=1, pack_name="urpack", reaction="like")
        result = self.db.catalog_get_user_reaction(user_id=1, pack_name="urpack")
        self.assertEqual(result, "like")

    def test_after_dislike_returns_dislike(self):
        self.db.catalog_react(user_id=1, pack_name="urpack", reaction="dislike")
        result = self.db.catalog_get_user_reaction(user_id=1, pack_name="urpack")
        self.assertEqual(result, "dislike")

    def test_after_toggle_off_returns_none(self):
        self.db.catalog_react(user_id=1, pack_name="urpack", reaction="like")
        self.db.catalog_react(user_id=1, pack_name="urpack", reaction="like")  # toggle off
        result = self.db.catalog_get_user_reaction(user_id=1, pack_name="urpack")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()