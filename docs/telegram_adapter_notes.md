# Telegram Adapter Refactor Notes

This branch introduces a Telegram adapter boundary and shared core engine so Telegram remains the first live platform while business logic is progressively transport-agnostic.

## What moved to shared STIX core

- Media conversion orchestration (image/video → sticker-ready payload) now lives in `core/engine.py` via `StixCoreEngine`.
- Platform-neutral media DTOs now live in `core/dtos.py`.
- Telegram handlers now delegate pack-seed/media processing through the adapter + core.

## What stays Telegram-specific (intentionally)

- Telegram update parsing (`message`, `callback_query`, file IDs).
- Telegram identity/session mapping (`effective_user`, `effective_chat`).
- Inline keyboard markup and callback payload formats.
- Telegram sticker-set publication calls:
  - `create_new_sticker_set`
  - `add_sticker_to_set`
- Telegram-native message tone/format and rich UX text.

## Remaining blockers before a Discord adapter can reuse more flows

1. **Conversation state and callback routing still live in `main.py`.**
   - Discord will need a transport-agnostic interaction state machine.
2. **Magic/mask and catalog flows are still directly wired to Telegram handlers.**
   - These should be moved into core use-cases/services next.
3. **Bot bootstrap still couples PTB registration semantics to top-level app startup.**
   - A future platform launcher abstraction should own this wiring.
4. **Pack publishing remains Telegram primitive-first.**
   - Discord analog (asset collection, emoji/sticker upload APIs) will require a shared publish contract.

## Discord divergence expectations (explicit)

- Discord has no direct equivalent to Telegram sticker pack links (`t.me/addstickers/...`), so response rendering must diverge.
- Callback-query UX maps to Discord component interactions; identifier format can stay shared conceptually but not byte-compatible.
- Telegram's sticker metadata fields (e.g., `is_video`) do not map 1:1 to Discord upload constraints.
