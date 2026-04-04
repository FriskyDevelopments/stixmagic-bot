import asyncio
import time
import sqlite3
import os

from api import get_db, _validate_packs_async

# Mock Bot to simulate slow Telegram network responses
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

    # Insert 100 packs
    for i in range(100):
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

async def main():
    setup_db()

    start_time = time.time()
    await _validate_packs_async("dummy_token", 999)
    end_time = time.time()

    print(f"Validation took {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
