"""
integrations/extension – Browser / Nebulosa extension integration scaffold.

STATUS: not yet implemented.

Planned functionality
---------------------
This module will provide the backend hooks required by the Nebulosa browser
extension to trigger MagicStix visual effects in response to browser events:

- Chat events (new message, mention)
- Hand-raise signals
- DJ cues
- Moderation signals (ban, timeout, highlight)

Integration points
------------------
The extension will communicate with MagicStix via:

1. A WebSocket endpoint (``/ws/extension``) served by the Flask API.
2. REST endpoints for asset/preset discovery (``/api/assets``, ``/api/presets``).
3. A shared event schema (``ExtensionEvent``) defined in this module.

See ``docs/future_integrations.md`` for the full specification.
"""

# Future: define ExtensionEvent dataclass and WebSocket handler here.
