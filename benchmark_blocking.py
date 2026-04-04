import asyncio
import time
import sqlite3
import os

from api import get_db, _validate_packs_async

# Mock Bot to simulate Telegram network responses without network delay
class DummyStickerSet:
    def __init__(self, title):
        self.title = title

class DummyBot:
    def __init__(self, token):
        self.token = token

    async def get_sticker_set(self, name):
        await asyncio.sleep(0.01) # Small delay
        if "deleted" in name:
            raise Exception("Sticker set not found")
        if "renamed" in name:
            return DummyStickerSet(title="New Title")
        return DummyStickerSet(title="Title for " + name)

    async def close(self):
        pass

import telegram
telegram.Bot = DummyBot

def setup_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS packs (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, title TEXT)")
    c.execute("DELETE FROM packs WHERE user_id = 999")

    # Insert a lot of packs to make the DB operations measurable
    for i in range(2000):
        if i % 10 == 0:
            name = f"deleted_pack_{i}"
            title = "Deleted"
        elif i % 5 == 0:
            name = f"renamed_pack_{i}"
            title = "Old Title"
        else:
            name = f"pack_{i}"
            title = f"Title for pack_{i}"
        c.execute("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", (999, name, title))
    conn.commit()
    conn.close()

async def jitter_monitor(results):
    """Monitors event loop jitter to detect blocking."""
    max_jitter = 0
    start = time.perf_counter()
    while not results.get("done"):
        t0 = time.perf_counter()
        await asyncio.sleep(0.01)
        t1 = time.perf_counter()
        jitter = t1 - t0 - 0.01
        if jitter > max_jitter:
            max_jitter = jitter
    results["max_jitter"] = max_jitter

async def main():
    setup_db()

    results = {"done": False}
    monitor_task = asyncio.create_task(jitter_monitor(results))

    start_time = time.perf_counter()
    await _validate_packs_async("dummy_token", 999)
    end_time = time.perf_counter()

    results["done"] = True
    await monitor_task

    print(f"Validation took {end_time - start_time:.4f} seconds")
    print(f"Max event loop jitter: {results['max_jitter']:.4f} seconds")

if __name__ == "__main__":
    import os
    os.environ["DEV_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    os.environ["STIXMAGIC_API_KEY_DEV"] = "dummy_key"
    os.environ["STICKER_BOT_ENV"] = "dev"
    asyncio.run(main())
