"""
loaders/definitions.py – Magical loader frame definitions.

Each loader is a dict with:
  name     : str              unique identifier
  frames   : list[str]        exactly 3 frames (multi-line emoji text)
  captions : list[str]        one or more captions to pick from randomly

The default sticker placeholder is "🟣".  render.py can substitute it
with a different emoji via the `placeholder` argument.

──────────────────────────────────────────────────
HOW TO ADD A NEW LOADER
──────────────────────────────────────────────────
1. Add an entry to LOADERS below, following the existing format.
2. Give it a unique string key (the loader name).
3. Write exactly 3 frames using emojis and consistent whitespace.
   Keep line widths roughly equal across frames to reduce jumpiness.
4. Provide at least one caption string.
5. Optionally map it to an action type in loaders/selection.py
   (ACTION_LOADER_MAP).  Otherwise it will be returned by
   get_random_loader() automatically.
──────────────────────────────────────────────────
"""

LOADERS: dict = {

    "thunder": {
        "name": "thunder",
        "frames": [
            # Frame 1 – single bolts top and bottom
            "     ⚡\n"
            "      │\n"
            "      🟣\n"
            "      │\n"
            "     ⚡",
            # Frame 2 – corner bolts
            "   ⚡   ⚡\n"
            "      🟣\n"
            "   ⚡   ⚡",
            # Frame 3 – sparkle discharge
            "      ✨\n"
            "      🟣\n"
            "      ✨",
        ],
        "captions": ["⚡ charging effect..."],
    },

    "magic_wand": {
        "name": "magic_wand",
        "frames": [
            # Frame 1 – single sparkle above wand
            "   ✨\n"
            "  🪄\n"
            "      🟣",
            # Frame 2 – two sparkles
            " ✨ ✨\n"
            "  🪄\n"
            "      🟣",
            # Frame 3 – three sparkles, wand at full power
            "✨ ✨ ✨\n"
            "  🪄\n"
            "      🟣",
        ],
        "captions": ["🪄 weaving enchantment...", "🔮 weaving enchantment..."],
    },

    "dust": {
        "name": "dust",
        "frames": [
            # Frame 1 – sparse diagonal dust
            "   ☁️     ✨\n"
            "      🟣\n"
            "   ✨     ☁️",
            # Frame 2 – thicker cloud of dust
            "  ✨ ☁️ ✨\n"
            "      🟣\n"
            "  ✨ ☁️ ✨",
            # Frame 3 – full cloud wrap
            " ☁️  ✨  ☁️\n"
            "      🟣\n"
            " ☁️  ✨  ☁️",
        ],
        "captions": ["☁️ shaping dream dust...", "💫 polishing sparkle..."],
    },

    "stars": {
        "name": "stars",
        "frames": [
            # Frame 1 – star corners, sparkle tips
            "      ✨\n"
            "   🌟     🌟\n"
            "      🟣\n"
            "   🌟     🌟\n"
            "      ✨",
            # Frame 2 – inverted: star tips, sparkle corners
            "      🌟\n"
            "   ✨     ✨\n"
            "      🟣\n"
            "   ✨     ✨\n"
            "      🌟",
            # Frame 3 – compressed single row above/below
            "   🌟  ✨  🌟\n"
            "      🟣\n"
            "   ✨  🌟  ✨",
        ],
        "captions": ["✨ summoning sticker...", "🌟 applying magic..."],
    },

}
