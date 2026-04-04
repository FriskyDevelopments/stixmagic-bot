import asyncio
import time
import sqlite3
import os

from api import get_db, _validate_packs_async

# Wait, `get_db()` and `c.execute()` and `c.fetchall()` are running synchronously inside `_validate_packs_async`.
# So the monitor task won't even run while those are executing! That means `monitor_event_loop`
# only starts measuring *after* the DB call is done, or it pauses completely and the *time elapsed* during
# that pause is recorded as the block length. Let's see if that's true.

class DummyStickerSet:
    def __init__(self, title):
        self.title = title

class DummyBot:
    def __init__(self, token):
        self.token = token

    async def get_sticker_set(self, name):
        # We want to measure the blocking time of the DB queries, so we make this fast
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

    # 500,000 rows
    print("Inserting rows...")
    batch = []
    for i in range(500000):
        name = f"pack_{i}"
        title = f"Title for pack_{i}"
        batch.append((999, name, title))
    c.executemany("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", batch)
    conn.commit()
    conn.close()
    print("Rows inserted.")

async def monitor_event_loop(done_event):
    max_delay = 0
    delays = []
    while not done_event.is_set():
        t0 = time.perf_counter()
        # Sleep slightly so the event loop switches
        await asyncio.sleep(0.001)
        delay = time.perf_counter() - t0 - 0.001
        delays.append(delay)
        if delay > max_delay:
            max_delay = delay
    return max_delay, delays

async def run_validation():
    # Wait a bit so monitor starts
    await asyncio.sleep(0.1)
    await _validate_packs_async("dummy_token", 999)

async def main():
    setup_db()

    print("Starting validation and monitoring...")
    done_event = asyncio.Event()

    monitor_task = asyncio.create_task(monitor_event_loop(done_event))

    start_time = time.perf_counter()
    await run_validation()
    end_time = time.perf_counter()

    done_event.set()
    max_block, delays = await monitor_task

    print(f"Validation took {end_time - start_time:.4f} seconds")
    print(f"Max event loop block: {max_block:.4f} seconds")
    # Print the top 5 longest blocks
    print(f"Top 5 blocks: {sorted(delays, reverse=True)[:5]}")

if __name__ == "__main__":
    os.environ["DEV_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    os.environ["STIXMAGIC_API_KEY_DEV"] = "dummy_key"
    os.environ["STICKER_BOT_ENV"] = "dev"
    asyncio.run(main())
