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

    # ── Original four ──────────────────────────────────────────

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

    # ── Extended catalog ───────────────────────────────────────

    "crystal_ball": {
        "name": "crystal_ball",
        "frames": [
            # Frame 1 – wand aims at crystal
            "   ✨\n"
            "  🔮\n"
            "      🟣",
            # Frame 2 – crystal energised
            " ✨ ✨\n"
            "  🔮\n"
            "  ✨  🟣",
            # Frame 3 – full orbit
            "✨ 🔮 ✨\n"
            "   🟣\n"
            "   ✨",
        ],
        "captions": ["🔮 reading the crystal...", "🔮 weaving enchantment..."],
    },

    "fire": {
        "name": "fire",
        "frames": [
            # Frame 1 – small flame above
            "    🔥\n"
            "    🟣\n"
            "    🔥",
            # Frame 2 – flames flanking
            "  🔥 🔥\n"
            "    🟣\n"
            "  🔥 🔥",
            # Frame 3 – full blaze crown
            " 🔥🔥🔥\n"
            "    🟣\n"
            " 🔥🔥🔥",
        ],
        "captions": ["🔥 igniting essence...", "⚡ charging effect..."],
    },

    "moon": {
        "name": "moon",
        "frames": [
            # Frame 1 – moon top-left, star bottom-right
            "🌙      \n"
            "   🟣   \n"
            "      ⭐",
            # Frame 2 – moon centred top
            "   🌙   \n"
            "   🟣   \n"
            "   ⭐   ",
            # Frame 3 – moon top-right, star bottom-left
            "      🌙\n"
            "   🟣   \n"
            "⭐      ",
        ],
        "captions": ["🌙 moonlit weaving...", "🌟 applying magic..."],
    },

    "orbit": {
        "name": "orbit",
        "frames": [
            # Frame 1 – top/bottom poles
            "    ○   \n"
            "  ○ 🟣 ○\n"
            "    ○   ",
            # Frame 2 – diagonal
            "  ○   ○\n"
            "    🟣  \n"
            "  ○   ○",
            # Frame 3 – tighter ring
            "   ○○   \n"
            " ○  🟣 ○\n"
            "   ○○   ",
        ],
        "captions": ["◉ aligning essence...", "💫 polishing sparkle..."],
    },

    "snowflake": {
        "name": "snowflake",
        "frames": [
            # Frame 1 – four cardinal tips
            "    ❄️\n"
            "  ❄️🟣❄️\n"
            "    ❄️",
            # Frame 2 – diagonal arms
            "  ❄️ ❄️\n"
            "    🟣\n"
            "  ❄️ ❄️",
            # Frame 3 – mixed crystal lattice
            "❄️ ✨ ❄️\n"
            "    🟣\n"
            "❄️ ✨ ❄️",
        ],
        "captions": ["❄️ crystallising...", "☁️ shaping dream dust..."],
    },

    "comet": {
        "name": "comet",
        "frames": [
            # Frame 1 – comet arrives top-left
            "☄️  ✨  ·\n"
            "         🟣",
            # Frame 2 – comet overhead
            "   ☄️  ✨\n"
            "      🟣",
            # Frame 3 – comet exits top-right, tail lingers
            "·  ✨  ☄️\n"
            "🟣",
        ],
        "captions": ["☄️ comet passing...", "✨ summoning sticker..."],
    },

    "portal": {
        "name": "portal",
        "frames": [
            # Frame 1 – portal begins to open
            "   🌀\n"
            " 🌀🟣\n"
            "   🌀",
            # Frame 2 – portal widens
            "🌀   🌀\n"
            "  🟣\n"
            "🌀   🌀",
            # Frame 3 – portal fully open
            " 🌀🌀🌀\n"
            "   🟣\n"
            " 🌀🌀🌀",
        ],
        "captions": ["🌀 opening the portal...", "🔮 weaving enchantment..."],
    },

    "bloom": {
        "name": "bloom",
        "frames": [
            # Frame 1 – bud above
            "    🌸\n"
            "    🟣",
            # Frame 2 – two petals open
            "  🌸 🌸\n"
            "    🟣",
            # Frame 3 – full bloom
            "🌸  🟣  🌸\n"
            "    🌸",
        ],
        "captions": ["🌸 in full bloom...", "💫 polishing sparkle..."],
    },

    "prism": {
        "name": "prism",
        "frames": [
            # Frame 1 – gem above sticker
            "    💎\n"
            "    🟣\n"
            "    ✨",
            # Frame 2 – gem radiates light
            "  ✨💎✨\n"
            "    🟣\n"
            "  ✨ ✨",
            # Frame 3 – full refraction
            "✨ 💎 ✨\n"
            "    🟣\n"
            "✨ ✨ ✨",
        ],
        "captions": ["💎 refracting light...", "✨ summoning sticker..."],
    },

    "galaxy": {
        "name": "galaxy",
        "frames": [
            # Frame 1 – cardinal stars
            "    ⭐\n"
            "🌟  🟣  🌟\n"
            "    ⭐",
            # Frame 2 – diagonal stars
            "🌟    🌟\n"
            "    🟣\n"
            "⭐    ⭐",
            # Frame 3 – alternating ring
            "⭐ 🌟 ⭐\n"
            "    🟣\n"
            "🌟 ⭐ 🌟",
        ],
        "captions": ["🌟 star-forged...", "🌟 applying magic..."],
    },

    "lightning_ring": {
        "name": "lightning_ring",
        "frames": [
            # Frame 1 – top and bottom pair
            "  ⚡ ⚡\n"
            "    🟣\n"
            "  ⚡ ⚡",
            # Frame 2 – wide ring
            "⚡     ⚡\n"
            "    🟣\n"
            "⚡     ⚡",
            # Frame 3 – tight ring with sparkles
            "  ✨✨\n"
            "⚡  🟣  ⚡\n"
            "  ✨✨",
        ],
        "captions": ["⚡ lightning surges...", "⚡ charging effect..."],
    },

    "sparkle_burst": {
        "name": "sparkle_burst",
        "frames": [
            # Frame 1 – single sparkle ring
            "    ✨\n"
            " ✨ 🟣 ✨\n"
            "    ✨",
            # Frame 2 – double sparkle ring
            " ✨  ✨\n"
            "✨  🟣  ✨\n"
            " ✨  ✨",
            # Frame 3 – full burst
            "✨ ✨ ✨\n"
            "✨  🟣  ✨\n"
            "✨ ✨ ✨",
        ],
        "captions": ["✨ bursting with sparkle...", "💫 polishing sparkle..."],
    },

    "cloud_ring": {
        "name": "cloud_ring",
        "frames": [
            # Frame 1 – cloud halo
            "    ☁️\n"
            " ☁️🟣☁️\n"
            "    ☁️",
            # Frame 2 – clouds at corners
            "☁️    ☁️\n"
            "    🟣\n"
            "☁️    ☁️",
            # Frame 3 – dense cloud veil
            " ☁️☁️☁️\n"
            "    🟣\n"
            " ☁️☁️☁️",
        ],
        "captions": ["☁️ cloud-weaving...", "☁️ shaping dream dust..."],
    },

    "diamond": {
        "name": "diamond",
        "frames": [
            # Frame 1 – four cardinal diamonds
            "    💠\n"
            " 💠 🟣 💠\n"
            "    💠",
            # Frame 2 – diagonal diamonds
            "💠    💠\n"
            "    🟣\n"
            "💠    💠",
            # Frame 3 – tight inner ring
            "  💠💠\n"
            "💠  🟣  💠\n"
            "  💠💠",
        ],
        "captions": ["💠 crystalline binding...", "💎 refracting light..."],
    },

    "starfall": {
        "name": "starfall",
        "frames": [
            # Frame 1 – star top-left
            "⭐       \n"
            "    🟣   \n"
            "       ⭐",
            # Frame 2 – star centred
            "    ⭐   \n"
            "    🟣   \n"
            "    ⭐   ",
            # Frame 3 – star top-right
            "       ⭐\n"
            "    🟣   \n"
            "⭐       ",
        ],
        "captions": ["⭐ stardust falling...", "🌟 applying magic..."],
    },

    "vortex": {
        "name": "vortex",
        "frames": [
            # Frame 1 – spiral begins top-left/bottom-right
            "🌀         \n"
            "    🟣\n"
            "         🌀",
            # Frame 2 – spiral shifts
            "    🌀   \n"
            "    🟣\n"
            "    🌀   ",
            # Frame 3 – spiral fully wraps
            "         🌀\n"
            "    🟣\n"
            "🌀         ",
        ],
        "captions": ["🌀 spiralling through...", "🔮 weaving enchantment..."],
    },

}

