from __future__ import annotations

import html
from dataclasses import dataclass

from telegram import InputSticker, InlineKeyboardButton, InlineKeyboardMarkup

from core import CoreMediaRequest, StixCoreEngine
from domain.media import download_file_bytes, extract_file_info


@dataclass(frozen=True)
class TelegramIdentity:
    user_id: int
    chat_id: int | None


@dataclass(frozen=True)
class TelegramNormalizedEvent:
    identity: TelegramIdentity
    media: CoreMediaRequest | None
    callback_data: str | None


class TelegramAdapter:
    """Thin Telegram transport adapter over the shared STIX core engine."""

    def __init__(self, core_engine: StixCoreEngine, *, sticker_emoji: list[str], divider: str) -> None:
        self.core_engine = core_engine
        self.sticker_emoji = sticker_emoji
        self.divider = divider

    def parse_update(self, update) -> TelegramNormalizedEvent:
        user = update.effective_user
        chat_id = update.effective_chat.id if update.effective_chat else None

        media = None
        if update.message:
            file_id, media_type, sticker_format = extract_file_info(update.message)
            if file_id:
                media = CoreMediaRequest(
                    file_id=file_id,
                    media_type=media_type,
                    sticker_format=sticker_format,
                )

        callback_data = update.callback_query.data if update.callback_query else None

        return TelegramNormalizedEvent(
            identity=TelegramIdentity(user_id=user.id, chat_id=chat_id),
            media=media,
            callback_data=callback_data,
        )

    async def create_pack_from_event(self, *, update, context, title: str) -> tuple[bool, dict]:
        event = self.parse_update(update)
        if not event.media:
            return False, {"error": "⚠ The ingredient is unrecognised — send an image, video, GIF, or sticker."}

        media_file = await download_file_bytes(context.bot, event.media.file_id)
        if not media_file:
            return False, {"error": "⚠ Download failed. Please try again."}

        media_result = await self.core_engine.process_media_async(media_file, event.media)
        pack_name = self.core_engine.generate_pack_name(event.identity.user_id, context.bot.username)

        input_sticker = InputSticker(
            sticker=media_result.sticker_file,
            emoji_list=self.sticker_emoji,
            format=media_result.sticker_format,
        )

        await context.bot.create_new_sticker_set(
            user_id=event.identity.user_id,
            name=pack_name,
            title=title,
            stickers=[input_sticker],
        )

        return True, {
            "pack_name": pack_name,
            "title": title,
            "open_link": f"https://t.me/addstickers/{pack_name}",
        }

    async def add_sticker_from_event(self, *, update, context, pack_name: str) -> tuple[bool, dict]:
        event = self.parse_update(update)
        if not event.media:
            return False, {"error": "⚠ The ingredient is unrecognised — send an image, video, GIF, or sticker."}

        media_file = await download_file_bytes(context.bot, event.media.file_id)
        if not media_file:
            return False, {"error": "⚠ Download failed. Please try again."}

        media_result = self.core_engine.process_media_sync(media_file, event.media)

        input_sticker = InputSticker(
            sticker=media_result.sticker_file,
            emoji_list=self.sticker_emoji,
            format=media_result.sticker_format,
        )

        await context.bot.add_sticker_to_set(
            user_id=event.identity.user_id,
            name=pack_name,
            sticker=input_sticker,
        )

        return True, {
            "pack_name": pack_name,
            "open_link": f"https://t.me/addstickers/{pack_name}",
            "media_type": media_result.media_type,
        }

    def render_create_success_keyboard(self, pack_name: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✦ Inscribe More Stickers", callback_data=f"addto_{pack_name}")],
            [InlineKeyboardButton("🔗 Open the Vessel", url=f"https://t.me/addstickers/{pack_name}")],
            [
                InlineKeyboardButton("📖 Grimoire", callback_data="menu_packs"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ],
        ])

    def render_add_success_keyboard(self, pack_name: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✦ Bind Another", callback_data=f"addto_{pack_name}")],
            [InlineKeyboardButton("🔗 Open the Vessel", url=f"https://t.me/addstickers/{pack_name}")],
            [
                InlineKeyboardButton("📖 Grimoire", callback_data="menu_packs"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ],
        ])

    def render_failure_keyboard(self, retry_callback: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Try Again", callback_data=retry_callback)],
            [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
        ])

    def render_create_success_text(self, title: str) -> str:
        return (
            f"⚗️ <b>Pack forged!</b>\n"
            f"{self.divider}\n\n"
            f"<b>{html.escape(title)}</b>\n"
            f"<i>The first sticker is sealed within.</i>"
        )
