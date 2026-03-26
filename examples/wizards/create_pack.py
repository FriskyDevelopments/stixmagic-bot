from __future__ import annotations

from wizard.model import WizardDefinition, WizardStep, WizardTransition


def _validate_pack_title(value, _values):
    title = (value or "").strip()
    if not title:
        return False, "Pack title is required."
    if len(title) > 64:
        return False, "Pack title must be 64 characters or fewer."
    return True, None


def _validate_seed_media(value, _values):
    allowed = {"photo", "video", "sticker", "gif"}
    media_type = (value or {}).get("media_type") if isinstance(value, dict) else None
    if media_type not in allowed:
        return False, "Send a photo, video, GIF, or sticker to continue."
    return True, None


def build_create_pack_wizard() -> WizardDefinition:
    """Shared create-pack flow used by Telegram and Discord adapters."""

    steps = {
        "ask_title": WizardStep(
            id="ask_title",
            prompt="⚗️ Name your new sticker pack (max 64 chars).",
            value_key="title",
            validation=_validate_pack_title,
            transition=WizardTransition(next_step="ask_seed_sticker"),
        ),
        "ask_seed_sticker": WizardStep(
            id="ask_seed_sticker",
            prompt="Send the first sticker ingredient (photo, GIF, video, or sticker).",
            value_key="seed_media",
            validation=_validate_seed_media,
            transition=WizardTransition(next_step="confirm"),
        ),
        "confirm": WizardStep(
            id="confirm",
            prompt="Confirm forge?",
            value_key="confirmed",
            validation=lambda v, _ctx: (v.strip().lower() in {"yes", "no"}, "Reply 'yes' or 'no'."),
            transition=WizardTransition(resolver=lambda v, _ctx: None if v.strip().lower() == "yes" else "ask_title"),
            side_effects=["create_pack"],
            completion_message="✨ Pack ritual completed.",
        ),
    }

    return WizardDefinition(id="create_pack", start_step="ask_title", steps=steps)