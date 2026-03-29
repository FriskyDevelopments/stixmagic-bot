"""
integrations/extension/__init__.py – Browser / Nebulosa extension integration.

This module provides a lightweight local integration contract between the
MagicStix asset pipeline and an external browser extension process.

The function below intentionally avoids network side-effects so callers can
use it safely in tests and dry-runs.  It validates inputs and returns a
structured payload that can be sent over REST/WebSocket by higher layers.
"""

from __future__ import annotations

from datetime import datetime, timezone

_ALLOWED_EVENTS = {"chat_message", "hand_raise", "dj_cue", "moderation"}


def trigger_asset(
    event: str,
    pack_id: str,
    asset_id: str,
    preset_id: str = "pulse",
) -> dict[str, str]:
    """
    Build a normalized trigger payload for browser-extension consumers.
    
    Validates inputs and returns a dictionary suitable for forwarding to a browser/Nebulosa extension transport. Raises ValueError if any of `event`, `pack_id`, `asset_id`, or `preset_id` is not a non-empty string, or if the normalized `event` is not one of the allowed events.
    
    Parameters:
        event (str): Trigger type emitted by the extension; will be stripped and lowercased.
        pack_id (str): Pack identifier where the asset lives; will be stripped.
        asset_id (str): Asset identifier inside the pack; will be stripped.
        preset_id (str): Optional motion preset identifier; will be stripped. Defaults to "pulse".
    
    Returns:
        dict[str, str]: Payload with keys:
            - `event`: normalized event name
            - `pack_id`: stripped pack identifier
            - `asset_id`: stripped asset identifier
            - `preset_id`: stripped preset identifier
            - `triggered_at`: UTC ISO 8601 timestamp of when the trigger was created
    """
    for field_name, value in {
        "event": event,
        "pack_id": pack_id,
        "asset_id": asset_id,
        "preset_id": preset_id,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    normalized_event = event.strip().lower()
    if normalized_event not in _ALLOWED_EVENTS:
        allowed = ", ".join(sorted(_ALLOWED_EVENTS))
        raise ValueError(f"Unsupported event '{event}'. Allowed events: {allowed}")

    return {
        "event": normalized_event,
        "pack_id": pack_id.strip(),
        "asset_id": asset_id.strip(),
        "preset_id": preset_id.strip(),
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }
