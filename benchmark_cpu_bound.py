import asyncio
import time
import sqlite3
import os
import timeit

from api import get_db, _validate_packs_async

# Mock Bot to simulate Telegram network responses
class DummyStickerSet:
    def __init__(self, title):
        self.title = title

class DummyBot:
    def __init__(self, token):
        self.token = token

    async def get_sticker_set(self, name):
        # NO DELAY, just CPU intensive mock
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

    # Insert 10000 packs
    for i in range(10000):
        name = f"pack_{i}"
        title = f"Title for pack_{i}"
        c.execute("INSERT INTO packs (user_id, name, title) VALUES (?, ?, ?)", (999, name, title))
    conn.commit()
    conn.close()

async def main():
    setup_db()

    start_time = time.perf_counter()
    await _validate_packs_async("dummy_token", 999)
    end_time = time.perf_counter()

    print(f"Validation took {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    os.environ["DEV_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    os.environ["STIXMAGIC_API_KEY_DEV"] = "dummy_key"
    os.environ["STICKER_BOT_ENV"] = "dev"
    asyncio.run(main())
