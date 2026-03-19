from telegram import InlineKeyboardButton, InlineKeyboardMarkup


DIVIDER = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"

MENU_STRUCTURE = {

    "home": {
        "header": "✦ <b>STIX MAGIC</b>",
        "body": (
            "<i>sticker alchemy at your fingertips</i>\n\n"
            "🟣 <b>CREATE</b>  Pack · Magic Cut\n"
            "🔵 <b>EXPLORE</b>  My Packs · Settings\n"
            "🟠 <b>LEARN</b>  Help · Tips\n"
            "⭐ <b>PREMIUM</b>  AI Generate · Plans\n"
        ),
        "buttons": [
            [
                {"label": "🟣 CREATE PACK", "action": "menu_create"},
                {"label": "🟣 MAGIC CUT", "action": "menu_magic"},
            ],
            [
                {"label": "🔵 MY PACKS ▸", "nav": "my_packs"},
                {"label": "🔵 SETTINGS ▸", "nav": "settings"},
            ],
            [
                {"label": "⭐ AI GENERATE", "action": "menu_generate"},
                {"label": "⭐ PREMIUM ▸", "action": "menu_premium"},
            ],
            [
                {"label": "🟠 HELP ▸", "nav": "help"},
                {"label": "🟠 ABOUT", "action": "menu_about"},
            ],
        ],
        "parent": None,
    },

    "my_packs": {
        "header": "🔵 <b>MY PACKS</b>",
        "body": (
            "<i>your sticker collection lives here</i>\n\n"
            "🟦 <b>VIEW</b>  Browse all your packs\n"
            "🟦 <b>ADD</b>  Drop a new sticker into a pack\n"
            "🟦 <b>MANAGE</b>  Rename or remove packs\n"
        ),
        "buttons": [
            [
                {"label": "👁️ VIEW", "action": "menu_packs"},
                {"label": "＋ ADD", "action": "menu_addsticker"},
            ],
            [{"label": "⚡ MANAGE", "action": "menu_manage"}],
        ],
        "parent": "home",
    },

    "settings": {
        "header": "🔵 <b>SETTINGS</b>",
        "body": (
            "<i>tune the wizard to your liking</i>\n\n"
            "🟦 <b>MASK MODE</b>  Choose whether white or\n"
            "   black pixels are kept during Magic Cut\n"
        ),
        "buttons": [
            [{"label": "◐ MASK MODE", "action": "settings_mask"}],
        ],
        "parent": "home",
    },

    "help": {
        "header": "🟠 <b>HELP</b>",
        "body": (
            "<i>learn the craft</i>\n\n"
            "🟧 <b>HOW IT WORKS</b>\n"
            "   Send any image → bot strips the background\n"
            "   → scales to 512 px → saves as a Telegram sticker\n\n"
            "🟧 <b>MAGIC CUT</b>\n"
            "   Paint a white/black mask over your image to\n"
            "   cut out exactly the part you want\n\n"
            "⭐ <b>AI GENERATE</b>\n"
            "   Type a description — DALL-E 3 draws the sticker\n"
            "   <i>(Premium only)</i>\n"
        ),
        "buttons": [
            [
                {"label": "▸ HOW IT WORKS", "action": "menu_help_detail"},
                {"label": "△ TIPS", "nav": "tips"},
            ],
        ],
        "parent": "home",
    },

    "tips": {
        "header": "🟠 <b>TIPS & TRICKS</b>",
        "body": (
            "<i>get the most out of every cut</i>\n\n"
            "🟧 Use <b>PNG</b> with transparency for best results\n"
            "🟧 Ideal size: <b>512 × 512</b> px\n"
            "🟧 Mask: <b>white = keep</b> · black = remove\n"
            "   <i>(flip this in 🔵 Settings)</i>\n"
            "🟧 Videos & GIFs work as video stickers\n"
            "🟧 Emoji is auto-assigned  ✨\n"
        ),
        "buttons": [],
        "parent": "help",
    },
}


def build_keyboard(menu_id):
    menu = MENU_STRUCTURE.get(menu_id)
    if not menu:
        return InlineKeyboardMarkup([])

    rows = []
    for entry in menu["buttons"]:
        if entry == "spacer":
            continue

        row = []
        for btn in entry:
            if "nav" in btn:
                row.append(InlineKeyboardButton(btn["label"], callback_data=f"nav:{btn['nav']}"))
            elif "action" in btn:
                row.append(InlineKeyboardButton(btn["label"], callback_data=btn["action"]))
            elif "url" in btn:
                row.append(InlineKeyboardButton(btn["label"], url=btn["url"]))
        if row:
            rows.append(row)

    nav_row = []
    if menu["parent"]:
        nav_row.append(InlineKeyboardButton("◂ BACK", callback_data=f"nav:{menu['parent']}"))
    if menu_id != "home":
        nav_row.append(InlineKeyboardButton("✦ HOME", callback_data="nav:home"))
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(rows)


def get_menu_text(menu_id):
    menu = MENU_STRUCTURE.get(menu_id)
    if not menu:
        return "Menu not found."

    text = f"{menu['header']}\n{DIVIDER}\n\n"
    if menu.get("body"):
        text += menu["body"]

    return text
