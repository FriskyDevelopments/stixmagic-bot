"""
loaders/selection.py – Loader selection helpers.

Public API:
  get_random_loader()              → random loader dict
  get_loader_by_name(name)         → named loader dict or None
  get_loader_for_context(action)   → best loader for an action type, or random
"""

import random

from .definitions import LOADERS

# Maps action type strings to preferred loader names.
# Add entries here when you want a specific loader for a new command.
ACTION_LOADER_MAP: dict[str, str] = {
    "create_pack": "magic_wand",
    "add_sticker": "dust",
    "video_convert": "thunder",
    "apply_effect": "stars",
    "apply_mask": "dust",
    "export": "stars",
    "publish": "magic_wand",
}

# Pre-built list for random.choice — avoids re-allocating on every call.
_LOADER_LIST: list = list(LOADERS.values())


def get_random_loader() -> dict:
    """Return a uniformly random loader."""
    return random.choice(_LOADER_LIST)


def get_loader_by_name(name: str) -> dict | None:
    """Return the loader with the given name, or None if not found."""
    return LOADERS.get(name)


def get_loader_for_context(action_type: str) -> dict:
    """
    Return the preferred loader for an action type.
    Falls back to a random loader if the action is not mapped.
    """
    name = ACTION_LOADER_MAP.get(action_type)
    if name:
        loader = LOADERS.get(name)
        if loader:
            return loader
    return get_random_loader()
