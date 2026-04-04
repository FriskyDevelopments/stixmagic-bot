import asyncio
import time
import sqlite3
import os

from api import get_db, _validate_packs_async

# In this benchmark, we'll see if the DB call blocks the event loop.

class DummyStickerSet:
    def __init__(self, title):
        self.title = title

class DummyBot:
    def __init__(self, token):
        self.token = token

    async def get_sticker_set(self, name):
        # fast return
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

    # Insert 100,000 packs to make the DB read explicitly slow
    print("Inserting rows...")
    batch = []
    for i in range(100000):
        name = f"pack_{i}"
        title = f"Title for pack_{i}"
        batch.append((999, name, title))
    c.executemany("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", batch)
    conn.commit()
    conn.close()
    print("Rows inserted.")

async def monitor_event_loop():
    max_delay = 0
    start = time.perf_counter()
    while time.perf_counter() - start < 5:  # Run for 5 seconds max
        t0 = time.perf_counter()
        await asyncio.sleep(0)  # Yield control
        delay = time.perf_counter() - t0
        if delay > max_delay:
            max_delay = delay
    return max_delay

async def run_validation():
    await _validate_packs_async("dummy_token", 999)

async def main():
    setup_db()

    print("Starting validation and monitoring...")

    monitor_task = asyncio.create_task(monitor_event_loop())

    start_time = time.perf_counter()
    await run_validation()
    end_time = time.perf_counter()

    max_block = await monitor_task

    print(f"Validation took {end_time - start_time:.4f} seconds")
    print(f"Max event loop block: {max_block:.4f} seconds")

if __name__ == "__main__":
    os.environ["DEV_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    os.environ["STIXMAGIC_API_KEY_DEV"] = "dummy_key"
    os.environ["STICKER_BOT_ENV"] = "dev"
    asyncio.run(main())
