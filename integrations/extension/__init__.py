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

    Parameters
    ----------
    event:
        Trigger type emitted by the extension.
    pack_id:
        Pack identifier where the asset lives.
    asset_id:
        Asset identifier inside the pack.
    preset_id:
        Optional motion preset id.

    Returns
    -------
    dict[str, str]
        Serialized payload that upstream integrations can forward to a
        browser extension transport.
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
