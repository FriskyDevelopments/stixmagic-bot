# STIX Magic — engine, loaders and moderation tests

## Why

The repo has 24 test files, and they cluster around the API helpers, the forge
wizard and the DB layer. The parts with no coverage are the ones every sticker
pack passes through: `core/engine.py` (the platform-agnostic generation engine),
`domain/media.py`'s conversion path, and the whole of `loaders/` — the
config→definitions→selection→render chain that decides what the user sees while
they wait.

`moderation/` is untested too, and moderation failing open is the kind of bug
that is invisible until it matters.

## Scope

**In scope:** `core/engine.py`, `core/contracts.py`, `core/types.py`,
`loaders/` (config, definitions, selection, controller, render), `menus.py`,
`moderation/`, and the untested parts of `domain/media.py`.

**Out of scope — do not edit or execute:** anything that calls the Telegram Bot
API for real, `integrations/virtual_camera/`, `integrations/extension/`,
`integrations/overlay_engine/` (they front native/OS surfaces), the deploy
workflows, and any payment or billing path. No test may convert media by
shelling out to a real ffmpeg binary against a real file it did not create.

## Requirements

### 1 — Harness

1.1 `pytest` runs green with **no network** and no real Telegram client; a
    conftest guard fails any test that opens a socket.
1.2 The existing 24 test files keep passing unchanged.
1.3 Coverage is measured and reported for the in-scope modules; the baseline is
    recorded before new tests land.
1.4 No test writes outside a pytest `tmp_path`.

### 2 — The generation engine (`core/engine.py`)

2.1 `generate_pack` produces the documented `PackGenerationResult` for an image
    input and for a video input, with the right `sticker_format` in each case.
2.2 An unsupported `media_type` returns the documented failure rather than
    raising or silently producing a static sticker.
2.3 A conversion failure in `domain/media.py` surfaces as a result the caller can
    act on — not as an unhandled exception and not as a success.
2.4 `render_reaction` / `ReactionRenderResult` follows the same contract.
2.5 Empty, truncated, and oversized `file_bytes` are each handled explicitly.
2.6 User-supplied text reaching the engine is HTML-escaped exactly once — never
    zero times, never twice.

### 3 — Contracts and types (`core/contracts.py`, `core/types.py`)

3.1 Every input dataclass rejects a missing required field rather than producing
    a half-built object.
3.2 Optional fields have the documented defaults, and a default is never a shared
    mutable.

### 4 — Loaders

4.1 `definitions.LOADERS` is well-formed: every entry has the keys the renderer
    reads, and no two entries share a name.
4.2 `get_random_loader` only ever returns an entry from `LOADERS`.
4.3 `get_loader_by_name` returns `None` for an unknown name rather than raising,
    and is exact-match (not prefix or case-insensitive) unless documented
    otherwise.
4.4 `get_loader_for_context` returns a context-appropriate loader for each known
    action type and falls back to random for an unknown one.
4.5 `loaders/render.py` renders every entry in `LOADERS` without raising, and its
    output is escaped for the surface it targets.
4.6 `loaders/controller.py` advances and stops cleanly, and cannot be started
    twice for the same context.
4.7 `loaders/config.py` applies documented defaults when config is absent, and a
    malformed config falls back rather than crashing.

### 5 — Moderation

5.1 Moderation **fails closed**: when a check errors or a backend is
    unreachable, content is not approved.
5.2 Each documented verdict is produced by the condition described.
5.3 `moderation/dev_harness.py` cannot be enabled in a production configuration —
    and a test asserts that, so the harness can never become a bypass.

### 6 — Menus (`menus.py`)

6.1 Every menu builds a keyboard the Telegram Bot API would accept: callback data
    within the length limit, no empty rows, no duplicate callback data.
6.2 Menu text with user-supplied content is escaped.

### 7 — Hygiene

7.1 No credential literal anywhere; a test scans tracked source and fails with
    file and line.
7.2 Nothing in the suite reaches the network or the Telegram API.
