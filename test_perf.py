import asyncio
import time
import sqlite3

def get_db():
    conn = sqlite3.connect("test.db")
    conn.row_factory = sqlite3.Row
    return conn

# Create dummy DB with 1000 rows
def setup_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS packs (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, title TEXT)")
    c.execute("DELETE FROM packs WHERE user_id = 999")

    # Insert 1000 packs
    for i in range(1000):
        name = f"pack_{i}"
        title = f"Title for pack_{i}"
        c.execute("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", (999, name, title))
    conn.commit()
    conn.close()

def sync_query():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, title FROM packs WHERE user_id = ? ORDER BY id", (999,))
    rows = c.fetchall()
    conn.close()
    return rows

async def async_query():
    return await asyncio.to_thread(sync_query)

async def test_performance():
    setup_db()

    # Sync test
    start = time.perf_counter()
    for _ in range(100):
        rows = sync_query()
    sync_time = time.perf_counter() - start

    # Async test
    start = time.perf_counter()
    for _ in range(100):
        rows = await async_query()
    async_time = time.perf_counter() - start

    print(f"Sync query time (100 runs): {sync_time:.6f} seconds")
    print(f"Async query time (100 runs): {async_time:.6f} seconds")
    print(f"Async overhead: {(async_time - sync_time):.6f} seconds")

if __name__ == "__main__":
    asyncio.run(test_performance())
