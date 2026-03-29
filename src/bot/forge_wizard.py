from __future__ import annotations

import html
from dataclasses import dataclass
from enum import StrEnum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DIVIDER = "◈ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ◈"
TITLE_LIMIT = 64


class ForgeStep(StrEnum):
    TITLE = "title"
    CONFIRM_TITLE = "confirm_title"
    STICKER = "sticker"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(slots=True)
class ForgeDraft:
    title: str
    step: ForgeStep


def validate_pack_title(raw: str) -> tuple[bool, str]:
    title = (raw or "").strip()
    if not title:
        return False, "A vessel needs a name. Send a title to continue."
    if len(title) > TITLE_LIMIT:
        return False, f"Name too long — {len(title)} characters. Keep it under {TITLE_LIMIT}."
    return True, title


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✕ Cancel", callback_data="nav:home")]])


def title_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Seal Name", callback_data="forge_confirm")],
            [InlineKeyboardButton("✏️ Rename", callback_data="forge_edit")],
            [InlineKeyboardButton("✕ Cancel", callback_data="nav:home")],
        ]
    )


def create_start_text() -> str:
    return (
        f"⚗️ <b>FORGE A PACK</b>\n"
        f"{DIVIDER}\n\n"
        "Name the vessel — what shall this pack be called?\n\n"
        f"<i>Display title · up to {TITLE_LIMIT} characters.</i>"
    )


def title_confirmation_text(title: str) -> str:
    return (
        f"⚗️ <b>Confirm Vessel Name</b>\n"
        f"{DIVIDER}\n\n"
        f"<b>{html.escape(title)}</b>\n\n"
        "Seal this name, or refine it before the first sticker is bound."
    )


def sticker_prompt_text(title: str) -> str:
    return (
        f"⚗️ <b>{html.escape(title)}</b>\n"
        f"{DIVIDER}\n\n"
        "The vessel is named. Now send the <b>seed sticker</b>.\n\n"
        "◦ Any image, photo, or GIF\n"
        "◦ Videos transmute as animated stickers\n"
        "◦ Or forward an existing sticker"
    )