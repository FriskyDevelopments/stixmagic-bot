## 2024-04-14 - SQLite Temporary B-Tree Sorting
**Learning:** Found an O(N log N) sorting overhead for every catalog query (popular, trending, new) because `catalog_packs` had no indices covering `public`, `likes`, `view_count`, and `added_at`.
**Action:** Adding covering indices (`public, likes DESC`, etc.) turns this into an O(log N) lookup and avoids temporary B-Trees during sorting.
## 2024-04-15 - Missing index on packs table
**Learning:** The `packs` table lacked an index on `user_id` despite frequent API endpoints and bot queries filtering by it (`SELECT ... FROM packs WHERE user_id = ?`). As users create more packs, this leads to O(N) full table scans which can become a bottleneck.
**Action:** Always check the query patterns of core tables in `infra/db.py` to ensure covering indexes are present for heavily filtered columns.
