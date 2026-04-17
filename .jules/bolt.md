## 2024-04-14 - SQLite Temporary B-Tree Sorting
**Learning:** Found an O(N log N) sorting overhead for every catalog query (popular, trending, new) because `catalog_packs` had no indices covering `public`, `likes`, `view_count`, and `added_at`.
**Action:** Adding covering indices (`public, likes DESC`, etc.) turns this into an O(log N) lookup and avoids temporary B-Trees during sorting.
## 2024-04-15 - Missing index on packs table
**Learning:** The `packs` table lacked an index on `user_id` despite frequent API endpoints and bot queries filtering by it (`SELECT ... FROM packs WHERE user_id = ?`). As users create more packs, this leads to O(N) full table scans which can become a bottleneck.
**Action:** Always check the query patterns of core tables in `infra/db.py` to ensure covering indexes are present for heavily filtered columns.
## 2024-04-16 - Memory Inefficiency of Python Array Slicing for Pagination
**Learning:** Found that `api.py` was pulling the entire result set of user packs (`/api/packs/<user_id>`) and search results (`/api/search`) into a Python list and *then* applying pagination slicing using `paginate()`. This caused `O(N)` memory usage and query time for queries returning large sets (e.g. 100k rows took >0.3s).
**Action:** Replace `SELECT * ...` coupled with Python array slicing with `SELECT COUNT(*)` followed by `SELECT * ... LIMIT ? OFFSET ?` to reduce complexity from `O(N)` to `O(limit)`. This yielded up to ~30x performance improvement.
## 2024-04-17 - Sequential I/O causing N+1 performance bottleneck
**Learning:** Found that `_validate_packs_async` in `api.py` was awaiting `bot.get_sticker_set(name)` sequentially in a loop for each pack. For users with many packs, this blocking caused significant delays and poor overall API performance since each request blocked the next.
**Action:** Always batch independent I/O tasks using `asyncio.gather()` inside async functions to execute network calls concurrently, reducing total time from `O(N)` to `O(1)` request time.
## 2024-04-18 - Rate Limits and Unbounded Async Gather
**Learning:** While `asyncio.gather()` provides significant performance boost for I/O bound tasks, an unbounded gather can trigger API rate limits (e.g., HTTP 429). In code with broad error handlers (like deleting data on `except Exception:`), this can result in catastrophic silent data deletion.
**Action:** Always wrap concurrent network requests in an `asyncio.Semaphore` when using `asyncio.gather()` on an unbounded set of items to prevent rate limit exceptions from triggering unintended fallback logic.
