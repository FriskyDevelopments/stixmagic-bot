## 2024-04-14 - SQLite Temporary B-Tree Sorting
**Learning:** Found an O(N log N) sorting overhead for every catalog query (popular, trending, new) because `catalog_packs` had no indices covering `public`, `likes`, `view_count`, and `added_at`.
**Action:** Adding covering indices (`public, likes DESC`, etc.) turns this into an O(log N) lookup and avoids temporary B-Trees during sorting.
