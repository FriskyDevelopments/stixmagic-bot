# STIX Core + Adapter Architecture

## Proposed repository structure

```text
/core
  contracts.py      # shared interface used by all platform adapters
  engine.py         # platform-agnostic business logic (generation + reaction rendering)
  types.py          # explicit reusable DTOs
/platforms
  /telegram
    adapter.py      # telegram transport mapping to core contract
  /discord
    scaffold.py     # discord-ready adapter scaffold (same contract)
```

## Refactor plan implemented

1. Introduce explicit core contract (`generate_pack`, `generate_reactions`).
2. Move pack media conversion orchestration into shared `StixCoreEngine`.
3. Move catalog/reaction formatting into core so every platform gets consistent output.
4. Keep Telegram in production path by replacing direct media + formatting logic with adapter calls.
5. Add Discord scaffold with contract parity for fast follow deployment.

## Telegram deployment blockers (remaining)

1. End-to-end regression pass for all Telegram conversation paths in a live chat.
2. Add focused tests for `core.engine.StixCoreEngine` and adapter envelopes.
3. Add telemetry for conversion failures split by image/video/sticker inputs.

## Discord activation steps (after Telegram ships)

1. Wire `DiscordStixAdapter.handle_slash_generate` into `discord.py` slash command handlers.
2. Implement Discord transport response builders (ephemeral + attachment upload).
3. Add Discord bot token/env plumbing to runtime config.
4. Add integration smoke tests for Discord attachment upload + core invocation.
5. Deploy with feature flag and monitor conversion/error rates against Telegram baseline.


## Shared wizard/flow engine boundary

- Runtime: `wizard/` for the shared flow runtime.
- Wizard definitions: `examples/wizards/` for shared wizard definitions.
- Platform renderers: `platforms/telegram/wizard_renderer.py` and `platforms/discord/wizard_renderer.py`.

Rule: all step logic, validation, transitions, session state, and completion rules stay in shared wizard definitions/engine.
Only rendering mappings (inline keyboard vs buttons/modals) live in platform renderer/adapters.