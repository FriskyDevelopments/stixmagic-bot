"""Shared emoji validation utilities for the bot and Mini App API."""
from __future__ import annotations

import regex

# Telegram allows emoji sequences up to ~32 bytes (ZWJ families, flags, skin-tones)
_MAX_EMOJI_INPUT_LEN = 32


def normalize_emoji(value: str | None) -> str:
    """Strip surrounding whitespace from an emoji string."""
    return (value or "").strip()


def is_single_emoji_grapheme(value: str) -> bool:
    """Return True only when *value* is exactly one grapheme cluster that
    contains emoji-pictographic content (including ZWJ sequences, regional
    indicator flag pairs, and skin-tone modifiers).

    Rejects empty strings, plain ASCII characters, whitespace, and any
    input with more than one grapheme cluster.
    """
    if not value or len(value) > _MAX_EMOJI_INPUT_LEN:
        return False

    graphemes = regex.findall(r"\X", value)
    if len(graphemes) != 1:
        return False

    grapheme = graphemes[0]

    # Accept pictographic emoji (includes ZWJ sequences / skin-tone variants)
    if regex.search(r"\p{Extended_Pictographic}", grapheme):
        return True

    # Accept regional indicator flag pairs (🇦🇦 … 🇿🇿)
    if regex.fullmatch(r"[\U0001F1E6-\U0001F1FF]{2}", grapheme):
        return True

    # Accept keycap sequences (#️⃣, *️⃣, 0️⃣ … 9️⃣)
    if regex.fullmatch(r"[#*0-9]\uFE0F?\u20E3", grapheme):
        return True

    return False


def validate_emoji(value: str | None) -> tuple[bool, str | None]:
    """Validate and normalise a single emoji.

    Normalisation strips leading/trailing whitespace only.
    Returns ``(True, normalised_value)`` on success or ``(False, None)``
    when the input is not a single valid emoji grapheme.
    """
    normalised = normalize_emoji(value)
    if not is_single_emoji_grapheme(normalised):
        return False, None
    return True, normalised