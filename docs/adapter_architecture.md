# STIX MΛGIC Adapter Architecture

## Why this split exists

STIX MΛGIC is now structured around a single shared core engine and thin platform adapters. That separation prevents Telegram-first logic from hard-coding assumptions into business rules, while still allowing polished platform-native UX.

The architectural intent is simple:

- **Core owns behavior** (generation, formatting decisions, trigger entry points, wizard/session primitives).
- **Adapters own transport** (Telegram or Discord API objects, message publishing, command wiring, callback payload shape).

This keeps sticker and reaction intelligence in one place and avoids drift as Discord support lands.

## What belongs in `core/`

The `core/` package is platform-agnostic and must not import Telegram or Discord SDK code.

- `core/types.py`
  - DTOs for sticker input/output, reaction input/output, pack request/result.
  - DTOs for platform event context and user/session context.
- `core/contracts.py`
  - Explicit protocols for platform adapter, media normalization, trigger execution entry, and wizard/flow rendering hooks.
- `core/engine.py`
  - `StixCoreEngine` with shared methods:
    - `normalize_generation_request(...)`
    - `generate_pack(...)`
    - `generate_reactions(...)`
  - Optional capability-aware formatting hook via `PackFormatter`.
- `core/capabilities.py`
  - Capability model (`PlatformCapabilities`) and current Telegram/Discord capability presets.
- `core/sessions.py`
  - Shared wizard-state primitives and session store contract implementation for isolated testing.

## What belongs in `platforms/*`

Each platform package is intentionally thin and should mostly:

1. Translate incoming platform events into `PlatformEventContext` + `UserSessionContext`.
2. Call `StixCoreEngine` methods.
3. Publish output back using platform APIs.

Current boundaries:

- `platforms/telegram/adapter.py`
  - Telegram capability surface.
  - Telegram-specific publish hooks.
- `platforms/discord/adapter.py`
  - Discord capability surface.
  - Discord-specific publish hooks (stubbed for integration wiring).

## What remains Telegram-specific for now

The live bot flow in `main.py` remains Telegram-native while migration is incremental:

- Telegram SDK update handlers and conversation wiring.
- Telegram UI composition details (inline keyboards, callback routing).
- Telegram-specific pack publishing lifecycle.

The new core layer allows these pieces to be progressively moved behind adapter calls without changing product behavior all at once.

## How Discord plugs in next

Discord integration can now be added as a minimal adapter track:

1. Implement event normalization from Discord interactions/messages to `core.types` DTOs.
2. Provide a Discord media normalizer implementation satisfying `MediaNormalizer`.
3. Invoke `StixCoreEngine.generate_pack(...)` / `generate_reactions(...)`.
4. Render responses using Discord-native components (buttons/modals/ephemeral response), guided by `PlatformCapabilities`.

This path keeps one magical STIX MΛGIC brain with multiple platform paws.
