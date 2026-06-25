# stix — distinct message-card design

Differentiated visual identity (the bots used to share one template; this gives
**stix** its own look). Render: open `cards.html` or screenshot it with Playwright.

**What makes it distinct:** STIX MΛGIC animated-sticker studio (per frisky-design-system/brands/stix-magic + STIX-MAGIC-BRANDING.md): Twilight #1A1430 canvas, Magic Violet #B07DFF (primary) / Aura Rose #FF8AB3 (optional) / Spark Gold #FFCF70 (ready), Outfit display, soft-rounded cards, SYMBOL LAW (✦ primary, ✧ optional, ○ neutral, ◌ forming, △ transform), sticker-studio voice ('Pick a style ✦'). NO fantasy/runic/wizard wording (brandbook forbids it).

## Files
- `cards.html` — the four key message cards (welcome · status · action · error),
  rendered as the image the bot sends.
- `inline-buttons.json` — native **Telegram Bot API 9.4** `reply_markup` per
  message: `style` (primary|success|danger) + this bot's accent + emoji.
  `icon_custom_emoji_id` (sovereign-icons set) attaches only when
  `SOVEREIGN_PREMIUM_EMOJI=true`; the unicode emoji in `text` is the fallback.
- `cards-preview.png` — rendered preview.
- `_all-bots-comparison.png` — all five bots side by side (differentiation proof).

Design only. Not wired into the bot, not deployed.
