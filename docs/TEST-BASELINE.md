# Test Baseline

Recorded **before** new engine/loader/moderation tests land.

Date: 2026-07-28

## Summary

```
217 failed, 228 passed, 2 warnings, 23 errors
```

These failures and errors are **pre-existing**. They are not caused by this
spec's changes and must not be fixed, deleted, or skipped as part of this work.

## Collection Errors (3 files)

| File | Root cause |
|------|-----------|
| `tests/test_require_api_key.py` | `ModuleNotFoundError: No module named 'stixmagic.contracts'; 'stixmagic' is not a package` — the top-level `stixmagic/` directory shadows the `stixmagic` package when importing `api.py`. |
| `tests/test_stixmagic_contracts.py` | Same `stixmagic.contracts` import failure. |
| `tests/test_stixmagic_telegram_auth.py` | Same `stixmagic.telegram_auth` import failure. |

## Setup Errors (20 tests in `test_api_helpers.py`)

The `TestValidatePacksAsync` class calls `importlib.import_module("api")` in
`setUpClass`. That import triggers `stixmagic.contracts` which fails with the
same `ModuleNotFoundError` above, causing 20 tests to error at setup.

## Failures by file

| File | Failures | Primary cause |
|------|----------|---------------|
| `tests/test_infra_db.py` | 51 (in combined run; 0 in isolation) | Cross-test pollution: another file's import of `stixmagic.settings` raises `ValueError: Missing required telegram_bot_token` which poisons the process. Tests pass in isolation. |
| `tests/test_main_forge_handlers.py` | 45 | `RuntimeError: There is no current event loop in thread 'MainThread'` — `asyncio.get_event_loop()` fails under Python 3.14's stricter policy. Also some settings-import ValueError when run in combined suite. |
| `tests/test_api_helpers.py` | 41 | `ValueError: Missing required telegram_bot_token` via `stixmagic.settings` import chain. |
| `tests/test_stixmagic_settings.py` | 30 (5 in isolation) | 5 genuine failures (miniapp URL property assertions don't match current code). Remaining 25 fail only in combined run due to env pollution. |
| `tests/test_pipeline_motion_presets.py` | 18 | `ImportError: cannot import name 'BUILTIN_PRESETS' from 'pipeline.motion_presets'` — test expects a symbol that no longer exists. |
| `tests/test_main_pack_handlers.py` | 16 | Tests assert a message format ("grimoire header", numbered titles) that the current code no longer produces. |
| `tests/test_main_send_menu.py` | 10 | `RuntimeError: There is no current event loop in thread 'MainThread'` — same async event-loop issue. |
| `tests/test_config_runtime.py` | 6 (0 in isolation) | Pass in isolation; fail in combined run due to env/import pollution from other test files. |

## What passes

228 tests across these files pass reliably:

- `tests/test_infra_db.py` (all 56 when isolated)
- `tests/test_forge_wizard.py`
- `tests/test_domain_media.py`
- `tests/test_manifest.py`
- `tests/test_pipeline_manifest.py`
- `tests/test_pipeline_metadata_registry.py`
- `tests/test_motion_presets_preset.py`
- `tests/test_gif_exporter.py`
- `tests/test_pack_namespace_prefix.py`
- `tests/test_config_runtime.py` (all 6 when isolated)
- Subsets of `test_api_helpers.py`, `test_stixmagic_settings.py`, `test_main_forge_handlers.py`

## Key root causes

1. **Missing `telegram_bot_token` env var** — `stixmagic/settings.py` raises at
   import time when no token is set, poisoning any module that transitively
   imports it.
2. **Package-name shadow** — `stixmagic/` directory (with `__init__.py`) exists
   at project root but is not installed as a proper package, causing
   `ModuleNotFoundError` when `api.py` tries `from stixmagic.contracts import …`.
3. **Python 3.14 asyncio policy** — `asyncio.get_event_loop()` no longer
   auto-creates a loop in the main thread, breaking tests that rely on it.
4. **Stale assertions** — some tests assert UI text or symbols that have since
   changed in the source.

## Regression bar

New tests written for this spec must pass in isolation. The 228 currently-passing
tests must remain passing. The pre-existing 217 failures and 23 errors are not
this spec's responsibility.
