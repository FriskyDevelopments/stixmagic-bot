# Discord Adapter Capability Mapping (Scaffold)

This repository keeps Telegram as the active platform adapter while Discord remains a thin scaffold over shared core services.

## Contract alignment

`DiscordStixAdapter` intentionally mirrors the shared adapter surface:

- `generate_pack(...)` delegates to `StixCoreEngine.generate_pack(...)`
- `generate_reactions(...)` delegates to `StixCoreEngine.generate_reactions(...)`
- transport-only parsing/rendering remains inside `platforms/discord/scaffold.py`

## Discord-specific capability differences

- **Slash commands** replace Telegram-style text command entry points.
- **Buttons/modals** replace Telegram inline keyboard callback patterns.
- **Guild/channel context** is first-class and parsed into `DiscordContext`.
- **Attachment normalization** maps Discord `resolved.attachments` payloads to shared media types.
- **Reactions** are modeled as interaction/component events and should map to the same shared reaction text logic.
- **Sticker publishing assumptions differ**: no Telegram sticker-pack publishing behavior should be assumed by default.

## Planned activation wiring

When Discord is activated, keep this layering:

1. Discord gateway/webhook receives interaction payloads.
2. Transport layer calls `DiscordStixAdapter.handle_interaction(...)`.
3. Adapter normalizes payload data and delegates business operations to `StixCoreEngine`.
4. Shared engine returns generation/reaction results.
5. Adapter renders Discord-native interaction callback payloads.

## Next steps (post-scaffold)

1. Add runtime transport wiring (e.g. `discord.py`/HTTP interactions).
2. Implement attachment byte download callback and upload plumbing.
3. Route reaction button events into shared reaction logic and persistence.
4. Route guild message/member events into the shared trigger engine via `handle_trigger_event(...)`.
5. Connect moderation wizard definitions by mapping Discord modal/button flows to existing shared wizard contracts.
