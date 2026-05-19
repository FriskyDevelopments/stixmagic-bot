## 2024-05-19 - Added tests for pipeline.metadata.AssetCatalog
**Learning:** Pure logic functions and classes in `pipeline/metadata/__init__.py` such as `_validate_raw_asset` and `AssetCatalog` didn't have dedicated unit tests. By adding tests, we're ensuring regressions in asset catalog parsing and data structure are caught. The test verifies both strict and non-strict loading behavior.
**Action:** Always verify pre-existing test statuses in `memory` when testing to separate pre-existing errors from new ones, preventing rabbit hole debugging.
