"""
infra/db.py – SQLite persistence layer for Stix Magic.

All raw SQL lives here so the rest of the application never touches
sqlite3 directly. The database path is centralized via
stixmagic.settings.get_settings().database_path.
"""

import logging
import sqlite3
import time

from stixmagic.settings import get_settings


logger = logging.getLogger(__name__)


def _db_file() -> str:
    """
    Get the configured SQLite database file path.
    
    Returns:
        str: Filesystem path to the SQLite database as specified by application settings.
    """
    return get_settings().database_path


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS packs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name    TEXT    NOT NULL,
            title   TEXT    NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id       INTEGER PRIMARY KEY,
            mask_inverted INTEGER DEFAULT 0
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_packs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    UNIQUE NOT NULL,
            title       TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            type        TEXT    DEFAULT 'image',
            public      INTEGER DEFAULT 1,
            safe        INTEGER DEFAULT 1,
            likes       INTEGER DEFAULT 0,
            dislikes    INTEGER DEFAULT 0,
            view_count  INTEGER DEFAULT 0,
            added_at    INTEGER NOT NULL,
            added_by    INTEGER
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_reactions (
            user_id   INTEGER NOT NULL,
            pack_name TEXT    NOT NULL,
            reaction  TEXT    NOT NULL,
            PRIMARY KEY (user_id, pack_name)
        )
        """
    )
    # ⚡ Bolt Optimization: Add covering indices for common catalog_search modes
    # Impact: Turns O(N log N) full table scans and temporary B-tree sorting into O(log N) lookups
    c.execute("CREATE INDEX IF NOT EXISTS idx_catalog_packs_popular ON catalog_packs (public, likes DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_catalog_packs_trending ON catalog_packs (public, view_count DESC, likes DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_catalog_packs_new ON catalog_packs (public, added_at DESC)")

    conn.commit()
    conn.close()


# ── User Settings ─────────────────────────────────────────────

def get_mask_inverted(user_id: int) -> bool:
    """
    Determine whether the user's mask display is inverted.
    
    Parameters:
        user_id (int): The user's numeric identifier.
    
    Returns:
        `true` if the user's `mask_inverted` value is 1, `false` otherwise.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute("SELECT mask_inverted FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False


def set_mask_inverted(user_id: int, inverted: bool) -> None:
    """
    Set the user's mask inversion setting.
    
    Parameters:
        user_id (int): ID of the user whose setting will be updated.
        inverted (bool): Whether the mask should be inverted (True sets inverted, False clears it).
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute(
        "INSERT INTO user_settings (user_id, mask_inverted) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET mask_inverted = ?",
        (user_id, int(inverted), int(inverted)),
    )
    conn.commit()
    conn.close()


# ── Pack CRUD ─────────────────────────────────────────────────

def add_pack(user_id: int, name: str, title: str) -> None:
    """
    Create a new pack record for the specified user in the database.
    
    Parameters:
        user_id (int): ID of the user who owns the pack.
        name (str): Internal name or identifier for the pack.
        title (str): Human-readable title for the pack.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute(
        "INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)",
        (user_id, name, title),
    )
    conn.commit()
    conn.close()


def delete_pack(user_id: int, name: str) -> None:
    """
    Delete a user's pack identified by its name from the database.
    
    Parameters:
        user_id (int): ID of the user who owns the pack.
        name (str): Pack name to remove.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute("DELETE FROM packs WHERE user_id = ? AND name = ?", (user_id, name))
    conn.commit()
    conn.close()


def get_user_packs(user_id: int) -> list[tuple[str, str]]:
    """
    Retrieve the user's packs as a list of (name, title) tuples.
    
    Returns:
        list[tuple[str, str]]: List of (name, title) tuples for the given user; empty list if the user has no packs.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute("SELECT name, title FROM packs WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def update_pack_title(user_id: int, name: str, title: str) -> None:
    """
    Update the title of a pack belonging to a specific user.
    
    Parameters:
    	user_id (int): ID of the owner of the pack to update.
    	name (str): Unique name/identifier of the pack.
    	title (str): New title to set for the pack.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute(
        "UPDATE packs SET title = ? WHERE user_id = ? AND name = ?",
        (title, user_id, name),
    )
    conn.commit()
    conn.close()


# ── User state helpers ────────────────────────────────────────

def is_new_user(user_id: int) -> bool:
    """
    Check whether a user is new (has no packs and no stored user settings).
    
    Returns:
        True if the user has not created any packs and has no entry in user_settings, False otherwise.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM packs WHERE user_id = ?", (user_id,))
    packs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM user_settings WHERE user_id = ?", (user_id,))
    settings = c.fetchone()[0]
    conn.close()
    return packs == 0 and settings == 0


# ── Catalog CRUD ──────────────────────────────────────────────

def catalog_add_pack(
    name: str,
    title: str,
    added_by: int,
    description: str = "",
    pack_type: str = "image",
) -> bool:
    """
    Add a new pack to the public catalog.
    
    Parameters:
        name (str): Unique identifier for the pack.
        title (str): Human-readable title for the pack.
        added_by (int): User ID of the account adding the pack.
        description (str): Optional descriptive text for the pack (default: "").
        pack_type (str): Pack category/type (default: "image").
    
    Returns:
        bool: `True` if the pack was inserted, `False` if a pack with the same name already exists.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute("SELECT id FROM catalog_packs WHERE name = ?", (name,))
    if c.fetchone():
        conn.close()
        return False
    c.execute(
        """
        INSERT INTO catalog_packs (name, title, description, type, added_at, added_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, title, description, pack_type, int(time.time()), added_by),
    )
    conn.commit()
    conn.close()
    return True


def catalog_get_pack(name: str) -> dict | None:
    """
    Retrieve a public catalog pack by its name.
    
    Returns:
        dict: A mapping of the pack's columns (e.g., name, title, description, type, public, safe, likes, dislikes, view_count, added_at, added_by) if a public pack with the given name exists, `None` otherwise.
    """
    conn = sqlite3.connect(_db_file())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM catalog_packs WHERE name = ? AND public = 1", (name,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def catalog_search(
    query: str = "",
    sort: str = "popular",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """
    Search public catalog packs with optional text filtering, sorting, and pagination.
    
    When sort is "popular", "trending", or "new" results are ordered by likes, view_count then likes, or added_at respectively; for any other sort value the query string is matched against title, name, and description using SQL LIKE. Results include only packs marked public and are limited/offset by the provided pagination parameters.
    
    Parameters:
        query (str): Text to match against title, name, and description when performing a search; ignored for the predefined sort modes.
        sort (str): One of "popular", "trending", "new", or any other value to perform a text search.
        limit (int): Maximum number of results to return.
        offset (int): Number of results to skip before returning.
    
    Returns:
        list[dict]: A list of rows from `catalog_packs` converted to dictionaries (one dict per pack).
    """
    conn = sqlite3.connect(_db_file())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if sort == "popular":
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "ORDER BY likes DESC LIMIT ? OFFSET ?"
        )
        c.execute(sql, (limit, offset))
    elif sort == "trending":
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "ORDER BY view_count DESC, likes DESC LIMIT ? OFFSET ?"
        )
        c.execute(sql, (limit, offset))
    elif sort == "new":
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "ORDER BY added_at DESC LIMIT ? OFFSET ?"
        )
        c.execute(sql, (limit, offset))
    else:
        sql = (
            "SELECT * FROM catalog_packs WHERE public = 1 "
            "AND (title LIKE ? OR name LIKE ? OR description LIKE ?) "
            "ORDER BY likes DESC LIMIT ? OFFSET ?"
        )
        pattern = f"%{query}%"
        c.execute(sql, (pattern, pattern, pattern, limit, offset))

    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def catalog_count(query: str = "", sort: str = "popular") -> int:
    """
    Count catalog packs that match the given search and visibility criteria.
    
    Parameters:
        query (str): Substring to match against title, name, or description when used (ignored for certain sorts).
        sort (str): If "popular", "trending", or "new", the function counts all public packs and ignores `query`; otherwise it counts public packs whose title, name, or description contain `query`.
    
    Returns:
        int: Total number of matching catalog packs.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    if sort in ("popular", "trending", "new"):
        c.execute("SELECT COUNT(*) FROM catalog_packs WHERE public = 1")
    else:
        pattern = f"%{query}%"
        c.execute(
            "SELECT COUNT(*) FROM catalog_packs WHERE public = 1 "
            "AND (title LIKE ? OR name LIKE ? OR description LIKE ?)",
            (pattern, pattern, pattern),
        )
    total = c.fetchone()[0]
    conn.close()
    return total


def catalog_increment_views(name: str) -> None:
    """
    Increment the view count for the catalog pack identified by `name`.
    
    Parameters:
        name (str): The unique catalog pack name whose `view_count` will be incremented in the database.
    """
    conn = sqlite3.connect(_db_file())
    conn.execute(
        "UPDATE catalog_packs SET view_count = view_count + 1 WHERE name = ?", (name,)
    )
    conn.commit()
    conn.close()


def catalog_react(user_id: int, pack_name: str, reaction: str) -> dict:
    """
    Toggle a user's like or dislike reaction for a catalog pack.
    
    Adds, removes, or switches the user's reaction and updates the pack's like/dislike counters accordingly.
    
    Returns:
        result (dict): {
            "likes": int — current total likes for the pack,
            "dislikes": int — current total dislikes for the pack,
            "current": str | None — the user's current reaction ("like" or "dislike"), or None if no reaction
        }
    """
    conn = sqlite3.connect(_db_file())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Whitelist-only column name mapping — never interpolated from user input
    _COL = {"like": "likes", "dislike": "dislikes"}

    c.execute(
        "SELECT reaction FROM catalog_reactions WHERE user_id = ? AND pack_name = ?",
        (user_id, pack_name),
    )
    existing = c.fetchone()

    if existing:
        old = existing["reaction"]
        if old == reaction:
            # Toggle off
            c.execute(
                "DELETE FROM catalog_reactions WHERE user_id = ? AND pack_name = ?",
                (user_id, pack_name),
            )
            if reaction == "like":
                c.execute(
                    "UPDATE catalog_packs SET likes = MAX(0, likes - 1) WHERE name = ?",
                    (pack_name,),
                )
            else:
                c.execute(
                    "UPDATE catalog_packs SET dislikes = MAX(0, dislikes - 1) WHERE name = ?",
                    (pack_name,),
                )
            current = None
        else:
            # Switch reaction
            c.execute(
                "UPDATE catalog_reactions SET reaction = ? WHERE user_id = ? AND pack_name = ?",
                (reaction, user_id, pack_name),
            )
            if reaction == "like":
                c.execute(
                    "UPDATE catalog_packs SET likes = likes + 1, dislikes = MAX(0, dislikes - 1) WHERE name = ?",
                    (pack_name,),
                )
            else:
                c.execute(
                    "UPDATE catalog_packs SET dislikes = dislikes + 1, likes = MAX(0, likes - 1) WHERE name = ?",
                    (pack_name,),
                )
            current = reaction
    else:
        c.execute(
            "INSERT INTO catalog_reactions (user_id, pack_name, reaction) VALUES (?, ?, ?)",
            (user_id, pack_name, reaction),
        )
        if reaction == "like":
            c.execute(
                "UPDATE catalog_packs SET likes = likes + 1 WHERE name = ?",
                (pack_name,),
            )
        else:
            c.execute(
                "UPDATE catalog_packs SET dislikes = dislikes + 1 WHERE name = ?",
                (pack_name,),
            )
        current = reaction

    conn.commit()
    c.execute(
        "SELECT likes, dislikes FROM catalog_packs WHERE name = ?", (pack_name,)
    )
    row = c.fetchone()
    conn.close()
    return {
        "likes": row["likes"] if row else 0,
        "dislikes": row["dislikes"] if row else 0,
        "current": current,
    }


def catalog_get_user_reaction(user_id: int, pack_name: str) -> str | None:
    """
    Retrieve the reaction a user has recorded for a catalog pack.
    
    Parameters:
        user_id (int): ID of the user.
        pack_name (str): Name of the catalog pack.
    
    Returns:
        str | None: The reaction string (e.g., 'like' or 'dislike') if a reaction exists, `None` otherwise.
    """
    conn = sqlite3.connect(_db_file())
    c = conn.cursor()
    c.execute(
        "SELECT reaction FROM catalog_reactions WHERE user_id = ? AND pack_name = ?",
        (user_id, pack_name),
    )
    row = c.fetchone()
    conn.close()
    return row[0] if row else None