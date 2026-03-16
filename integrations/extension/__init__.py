"""
integrations/extension/__init__.py – Browser / Nebulosa extension scaffold.

FUTURE INTEGRATION — not yet implemented.

This module will provide the interface between the MagicStix asset pipeline
and a browser extension (codenamed "Nebulosa") that triggers visual assets
during chat events.

Planned trigger events
----------------------
- chat_message   : Display an animated sticker in response to a message
- hand_raise     : Overlay a signal asset when a user raises their hand
- dj_cue         : Fire a DJ-pack animation on a DJ event
- moderation     : Show a moderation signal on kick / mute events

Planned interface
-----------------
The extension will communicate with a local or remote MagicStix service
endpoint to fetch pre-rendered assets by pack_id, asset_id, and preset_id.

Example future call
-------------------
>>> from integrations.extension import trigger_asset
>>> trigger_asset(event="hand_raise", pack_id="neon_signals", asset_id="signal_hand")

Implementation notes
--------------------
- Assets must already be rendered and accessible via HTTP or local path.
- The extension communicates over WebSocket or REST with a MagicStix server.
- Authentication / API key integration will use the existing STIXMAGIC_API_KEY.
"""

# TODO: implement browser extension integration


def trigger_asset(
    event: str,
    pack_id: str,
    asset_id: str,
    preset_id: str = "pulse",
) -> None:
    """
    Trigger a visual asset in response to a browser/extension event.

    NOT YET IMPLEMENTED.
    """
    raise NotImplementedError(
        "integrations.extension.trigger_asset is not yet implemented. "
        "See the module docstring for the planned interface."
    )
