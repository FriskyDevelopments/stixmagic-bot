# Shared Wizard Engine (Telegram + Discord)

This branch introduces a single, platform-agnostic wizard runtime so STIX MΛGIC flows are defined once and rendered per platform.

## Core flow logic (platform-agnostic)

- `wizard/model.py`
  - `WizardDefinition`, `WizardStep`, `WizardTransition`, `WizardSession`, `WizardEvent`
  - Encodes steps, prompts, transitions, validation hooks, side-effect labels, and completion state.
- `wizard/engine.py`
  - `WizardEngine.start()` and `WizardEngine.submit()`
  - Applies validation, updates shared session state, computes transitions, and emits events.

## Example shared wizard

- `examples/wizards/create_pack.py`
  - `build_create_pack_wizard()` defines:
    1. ask title
    2. ask seed media
    3. confirm + completion
  - Includes validation and side-effect declaration (`create_pack`) without embedding Telegram/Discord code.

## Platform rendering boundary

Rendering starts only at adapter renderer classes:

- Telegram renderer: `platforms/telegram/wizard_renderer.py`
- Discord renderer: `platforms/discord/wizard_renderer.py`

Both consume the same `WizardEvent` and return platform-ready rendering metadata (`RenderInstruction` from `wizard/rendering.py`).

## Adapter hooks

- `TelegramStixAdapter.render_wizard_event(event)`
- `DiscordStixAdapter.render_wizard_event(event)`

These methods are the explicit seam between shared flow logic and platform-specific rituals.

## Usage sketch

```python
from examples.wizards import build_create_pack_wizard
from wizard import WizardEngine

engine = WizardEngine(build_create_pack_wizard())
session, event = engine.start()

# render event in Telegram or Discord
next_event = engine.submit(session, "My Pack Title")
```

This keeps state transitions and flow decisions outside Telegram-only handlers while allowing each platform to render interaction controls differently.
