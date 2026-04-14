import sqlite3

conn = sqlite3.connect(':memory:')
c = conn.cursor()
c.execute("""
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
""")

c.execute("CREATE INDEX IF NOT EXISTS idx_catalog_packs_popular ON catalog_packs (public, likes DESC)")
c.execute("CREATE INDEX IF NOT EXISTS idx_catalog_packs_trending ON catalog_packs (public, view_count DESC, likes DESC)")
c.execute("CREATE INDEX IF NOT EXISTS idx_catalog_packs_new ON catalog_packs (public, added_at DESC)")

print("All indices created successfully.")
