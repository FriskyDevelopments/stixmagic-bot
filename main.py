import asyncio
import html
import io
import logging
import random
import string
import threading
import time

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputSticker,
    InputTextMessageContent,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from config.runtime import ConfigError, get_settings
from core.engine import StixCoreEngine
from domain.media import apply_mask_to_image, download_file_bytes
from infra.db import add_pack as add_pack_to_db
from infra.db import (
    catalog_add_pack,
    catalog_count,
    catalog_get_pack,
    catalog_get_user_reaction,
    catalog_increment_views,
    catalog_react,
    catalog_search,
)
from infra.db import delete_pack as delete_pack_from_db
from infra.db import (
    get_mask_inverted,
    get_user_packs,
    init_db,
    is_new_user,
    set_mask_inverted,
)
from infra.db import update_pack_title as update_pack_title_in_db
from loaders import LoaderController, get_loader_for_context
from menus import build_keyboard, get_menu_text
from platforms.telegram import TelegramStixAdapter
from src.bot.forge_wizard import ForgeDraft, ForgeStep
from src.bot.forge_wizard import cancel_keyboard as forge_cancel_keyboard
from src.bot.forge_wizard import (
    create_start_text,
    sticker_prompt_text,
    title_confirmation_keyboard,
    title_confirmation_text,
    validate_pack_title,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

init_db()

core_engine = StixCoreEngine()
telegram_adapter = TelegramStixAdapter(core_engine)

_TG_PACK_CACHE = {}  # {name: (timestamp, title, status)}
_TG_PACK_CACHE_TTL = 300  # 5 minutes


async def validate_and_sync_packs(bot, user_id):
    """Check each DB pack against Telegram. Prune deleted packs, sync renamed titles."""
    packs = get_user_packs(user_id)

    # Prevent memory leaks without dropping cached packs needed by this validation batch.
    now = time.time()
    pack_names = {name for name, _ in packs}
    if len(_TG_PACK_CACHE) > 1000:
        expired_names = [
            name
            for name, (cached_at, _, _) in _TG_PACK_CACHE.items()
            if now - cached_at >= _TG_PACK_CACHE_TTL
        ]
        for name in expired_names:
            _TG_PACK_CACHE.pop(name, None)

    if len(_TG_PACK_CACHE) > 1000:
        removable_entries = sorted(
            (cached_at, name)
            for name, (cached_at, _, _) in _TG_PACK_CACHE.items()
            if name not in pack_names
        )
        for _, name in removable_entries[: len(_TG_PACK_CACHE) - 1000]:
            _TG_PACK_CACHE.pop(name, None)

    # ⚡ Bolt Optimization: Concurrently validate packs with bounded concurrency (Semaphore=5)
    # Impact: Reduces N sequential network calls to Telegram down to O(N/5) while preventing HTTP 429 rate limit drops that could lead to accidental pack deletion
    sem = asyncio.Semaphore(5)

    async def _validate_single_pack(name, title):
        now = time.time()

        # ⚡ Bolt Optimization: Cache expensive Telegram API calls per pack for 5 minutes
        # Impact: Drastically reduces network latency and avoids 429 errors when reloading bot menus (e.g. Grimoire)
        if (
            name in _TG_PACK_CACHE
            and now - _TG_PACK_CACHE[name][0] < _TG_PACK_CACHE_TTL
        ):
            _, cached_title, status = _TG_PACK_CACHE[name]
            return {
                "name": name,
                "title": cached_title,
                "old_title": title,
                "status": status,
            }

        async with sem:
            try:
                ss = await bot.get_sticker_set(name)
                _TG_PACK_CACHE[name] = (now, ss.title, "valid")
                return {
                    "name": name,
                    "title": ss.title,
                    "old_title": title,
                    "status": "valid",
                }
            except BadRequest:
                _TG_PACK_CACHE[name] = (now, title, "deleted")
                return {
                    "name": name,
                    "title": title,
                    "old_title": title,
                    "status": "deleted",
                }
            except Exception as e:
                logger.warning(f"Could not validate pack {name}: {e}")
                return {
                    "name": name,
                    "title": title,
                    "old_title": title,
                    "status": "unknown",
                }

    tasks = [_validate_single_pack(name, title) for name, title in packs]
    results = await asyncio.gather(*tasks)

    valid = []
    for res in results:
        name, title, old_title, status = (
            res["name"],
            res["title"],
            res["old_title"],
            res["status"],
        )
        if status == "valid":
            if title != old_title:
                update_pack_title_in_db(user_id, name, title)
            valid.append((name, title))
        elif status == "deleted":
            delete_pack_from_db(user_id, name)
            logger.info(f"Pruned stale pack {name} for user {user_id}")

    return valid


WAITING_TITLE, WAITING_TITLE_CONFIRM, WAITING_STICKER = range(3)
CHOOSING_PACK, WAITING_STICKER_ADD = range(3, 5)
WAITING_SOURCE_IMAGE, WAITING_MASK_IMAGE, WAITING_CUT_PACK = range(5, 8)
WAITING_SYNC_NAME = 8
WAITING_FEATURE_PACK, WAITING_FEATURE_DESC = range(9, 11)
WAITING_CATALOG_SEARCH = 11

STICKER_EMOJI = ["✨"]

DIV = "◈ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ◈"


def _pack_namespace_prefix() -> str:
    settings = get_settings()
    return "devstix" if settings.is_development else "stix"


def cancel_keyboard():
    return forge_cancel_keyboard()


def home_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✦ Home", callback_data="nav:home")]]
    )


def back_home_keyboard(back):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◂ Back", callback_data=f"nav:{back}"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ]
        ]
    )


async def send_menu(update, menu_id):
    text = get_menu_text(menu_id)
    keyboard = build_keyboard(menu_id)

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


async def nav_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    menu_id = query.data.replace("nav:", "")
    await send_menu(update, menu_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name or "there"

    if is_new_user(user.id):
        welcome = (
            f"⚗️ <b>The laboratory opens, {first_name}.</b>\n"
            f"{DIV}\n\n"
            "You have entered the sticker alchemy lab.\n\n"
            "◦ Any image → transmuted into a sticker\n"
            "◦ Image + mask → precision cutout ritual\n"
            "◦ Video & GIF forms accepted\n\n"
            "<i>Begin by forging your first pack below.</i>"
        )
        keyboard = build_keyboard("home")
        await update.message.reply_text(
            welcome, reply_markup=keyboard, parse_mode="HTML"
        )
    else:
        await send_menu(update, "home")


# ── CREATE PACK ──────────────────────────────────────────────


async def create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = create_start_text()
    context.user_data["forge_draft"] = ForgeDraft(title="", step=ForgeStep.TITLE)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=cancel_keyboard()
        )
    return WAITING_TITLE


async def create_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_valid, validated_title = validate_pack_title(update.message.text)
    if not is_valid:
        await update.message.reply_text(
            f"⚠ {validated_title}\nTry again:",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_TITLE

    context.user_data["forge_draft"] = ForgeDraft(
        title=validated_title, step=ForgeStep.CONFIRM_TITLE
    )
    await update.message.reply_text(
        title_confirmation_text(validated_title),
        parse_mode="HTML",
        reply_markup=title_confirmation_keyboard(),
    )
    return WAITING_TITLE_CONFIRM


async def create_title_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    draft = context.user_data.get("forge_draft")
    if not isinstance(draft, ForgeDraft):
        await query.edit_message_text(
            "⚠ Draft lost. Restart pack forging.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⚗️ Restart", callback_data="menu_create")]]
            ),
        )
        return ConversationHandler.END

    if action == "forge_edit":
        context.user_data["forge_draft"] = ForgeDraft(
            title=draft.title, step=ForgeStep.TITLE
        )
        await query.edit_message_text(
            create_start_text(),
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_TITLE

    context.user_data["newpack_title"] = draft.title
    context.user_data["forge_draft"] = ForgeDraft(
        title=draft.title, step=ForgeStep.STICKER
    )
    await query.edit_message_text(
        sticker_prompt_text(draft.title),
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_STICKER


async def _handle_create_success(
    pack_name: str, title: str, ctrl, progress, draft, context
):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✦ Inscribe More Stickers", callback_data=f"addto_{pack_name}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔗 Open the Vessel", url=f"https://t.me/addstickers/{pack_name}"
                )
            ],
            [
                InlineKeyboardButton("📖 Grimoire", callback_data="menu_packs"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ],
        ]
    )

    await ctrl.stop()
    await progress.edit_text(
        f"⚗️ <b>Pack forged!</b>\n"
        f"{DIV}\n\n"
        f"<b>{html.escape(title)}</b>\n"
        f"<i>The first sticker is sealed within.</i>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    if isinstance(draft, ForgeDraft):
        context.user_data["forge_draft"] = ForgeDraft(
            title=draft.title, step=ForgeStep.SUCCESS
        )


async def _handle_create_error(e: Exception, ctrl, progress, draft, context):
    logger.error(f"Error creating sticker set: {e}")
    err = str(e)
    friendly = "The ingredients were not accepted. Try a PNG or JPG image."
    if "too big" in err.lower():
        friendly = "The ingredient is too large — try a smaller image (under 512px)."
    elif "invalid" in err.lower():
        friendly = "The form was rejected by Telegram. Try a PNG or JPG."
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Try Again", callback_data="menu_create")],
            [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
        ]
    )
    await ctrl.stop()
    await progress.edit_text(
        f"⚠ <b>The transmutation failed</b>\n" f"{DIV}\n\n" f"{friendly}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    if isinstance(draft, ForgeDraft):
        context.user_data["forge_draft"] = ForgeDraft(
            title=draft.title, step=ForgeStep.ERROR
        )


async def create_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    title = context.user_data.get("newpack_title", "My Pack")

    media = telegram_adapter.parse_message_media(update.message)
    if not media:
        await update.message.reply_text(
            "⚠ The ingredient is unrecognised — send an image, video, GIF, or sticker.",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_STICKER

    # Select loader and send initial static caption as the progress message.
    loader = get_loader_for_context(
        "create_pack" if media.media_type != "video" else "video_convert"
    )
    draft = context.user_data.get("forge_draft")
    if isinstance(draft, ForgeDraft):
        context.user_data["forge_draft"] = ForgeDraft(
            title=draft.title, step=ForgeStep.LOADING
        )
    initial_caption = loader["captions"][0]
    progress = await update.message.reply_text(initial_caption)

    # Start loader animation (animates only if the op takes > 2.5 s).
    ctrl = LoaderController(progress, loader)
    await ctrl.start()

    bot_username = context.bot.username
    suffix = "".join(random.choices(string.ascii_lowercase, k=5))
    pack_name = f"{_pack_namespace_prefix()}_{user.id}_{suffix}_by_{bot_username}"

    try:
        sticker_file = await download_file_bytes(context.bot, media.file_id)
        if not sticker_file:
            await ctrl.stop()
            await progress.edit_text("⚠ Download failed. Please try again.")
            if isinstance(draft, ForgeDraft):
                context.user_data["forge_draft"] = ForgeDraft(
                    title=draft.title, step=ForgeStep.STICKER
                )
            return WAITING_STICKER

        generated = await telegram_adapter.generate_pack(sticker_file, media.media_type)
        if not generated:
            await ctrl.stop()
            await progress.edit_text("⚠ Conversion failed. Please try again.")
            if isinstance(draft, ForgeDraft):
                context.user_data["forge_draft"] = ForgeDraft(
                    title=draft.title, step=ForgeStep.STICKER
                )
            return WAITING_STICKER

        input_sticker = InputSticker(
            sticker=generated.sticker_file,
            emoji_list=STICKER_EMOJI,
            format=generated.sticker_format,
        )

        await context.bot.create_new_sticker_set(
            user_id=user.id,
            name=pack_name,
            title=title,
            stickers=[input_sticker],
        )

        add_pack_to_db(user.id, pack_name, title)

        await _handle_create_success(pack_name, title, ctrl, progress, draft, context)
    except Exception as e:
        await _handle_create_error(e, ctrl, progress, draft, context)

    context.user_data.clear()
    return ConversationHandler.END


# ── ADD STICKER ──────────────────────────────────────────────


async def addsticker_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if update.callback_query:
        await update.callback_query.answer()

    packs = await validate_and_sync_packs(context.bot, user.id)

    if not packs:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚗️ Forge a Pack", callback_data="menu_create")],
                [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
            ]
        )
        msg = (
            f"✦ <b>INSCRIBE A STICKER</b>\n"
            f"{DIV}\n\n"
            "The grimoire is empty — no vessels exist yet.\n"
            "Forge a pack first!"
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        return ConversationHandler.END

    keyboard_rows = [
        [InlineKeyboardButton(f"▦  {title}", callback_data=f"pack_{name}")]
        for name, title in packs
    ]
    keyboard_rows.append([InlineKeyboardButton("✕ Cancel", callback_data="nav:home")])
    context.user_data["user_packs"] = packs

    msg = (
        f"✦ <b>INSCRIBE A STICKER</b>\n"
        f"{DIV}\n\n"
        "Which vessel receives the sticker?"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    else:
        await update.message.reply_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    return CHOOSING_PACK


async def addto_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pack_name = query.data.replace("addto_", "")
    packs = get_user_packs(query.from_user.id)
    context.user_data["user_packs"] = packs
    context.user_data["selected_pack"] = pack_name
    await query.edit_message_text(
        f"✦ <b>INSCRIBE A STICKER</b>\n"
        f"{DIV}\n\n"
        "Send the ingredient to bind into this vessel.\n\n"
        "◦ Image, video, GIF, or existing sticker",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_STICKER_ADD


async def addsticker_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pack_name = query.data.replace("pack_", "")
    packs = context.user_data.get("user_packs", [])
    # Optimization: Use dict lookup instead of Python generator expression for O(1) performance
    selected_name = pack_name if pack_name in dict(packs) else None

    if not selected_name:
        await query.edit_message_text("Pack not found. Try again.")
        return ConversationHandler.END

    context.user_data["selected_pack"] = selected_name
    # Optimization: Use dict lookup instead of Python generator expression for O(1) performance
    pack_title = dict(packs).get(pack_name, pack_name)

    await query.edit_message_text(
        f"✦ <b>{html.escape(pack_title)}</b>\n"
        f"{DIV}\n\n"
        "Send the ingredient to seal into this vessel.\n\n"
        "◦ Image, video, GIF, or existing sticker",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_STICKER_ADD


async def addsticker_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    pack_name = context.user_data.get("selected_pack")
    packs = context.user_data.get("user_packs", [])
    # Optimization: Use dict lookup instead of Python generator expression for O(1) performance
    pack_title = dict(packs).get(pack_name, pack_name)

    media = telegram_adapter.parse_message_media(update.message)
    if not media:
        await update.message.reply_text(
            "⚠ The ingredient is unrecognised — send an image, video, GIF, or sticker.",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_STICKER_ADD

    progress = await update.message.reply_text(
        "⚗️ <i>Binding the sticker...</i>", parse_mode="HTML"
    )

    try:
        sticker_file = await download_file_bytes(context.bot, media.file_id)
        if not sticker_file:
            await progress.edit_text("⚠ Download failed. Please try again.")
            return WAITING_STICKER_ADD

        if media.media_type == "video":
            await progress.edit_text(
                "⚗️ <i>Distilling the animation...</i>", parse_mode="HTML"
            )

        generated = await telegram_adapter.generate_pack(sticker_file, media.media_type)
        if not generated:
            await progress.edit_text("⚠ Conversion failed. Please try again.")
            return WAITING_STICKER_ADD

        input_sticker = InputSticker(
            sticker=generated.sticker_file,
            emoji_list=STICKER_EMOJI,
            format=generated.sticker_format,
        )
        await context.bot.add_sticker_to_set(
            user_id=user.id, name=pack_name, sticker=input_sticker
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✦ Bind Another", callback_data=f"addto_{pack_name}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔗 Open the Vessel",
                        url=f"https://t.me/addstickers/{pack_name}",
                    )
                ],
                [
                    InlineKeyboardButton("📖 Grimoire", callback_data="menu_packs"),
                    InlineKeyboardButton("✦ Home", callback_data="nav:home"),
                ],
            ]
        )

        await progress.edit_text(
            f"✦ <b>Sticker sealed</b>\n"
            f"{DIV}\n\n"
            f"<b>{html.escape(pack_title)}</b> grows stronger.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Error adding sticker: {e}")
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 Try Again", callback_data=f"addto_{pack_name}"
                    )
                ],
                [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
            ]
        )
        await progress.edit_text(
            f"⚠ <b>The binding failed</b>\n"
            f"{DIV}\n\n"
            f"<i>{html.escape(str(e))}</i>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    context.user_data.clear()
    return ConversationHandler.END


# ── MAGIC TOOLS (MASK CUTTER) ───────────────────────────────


async def magic_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    inverted = get_mask_inverted(user.id)
    mode = (
        "⬛ black = keep  ·  ⬜ white = dissolve"
        if inverted
        else "⬜ white = keep  ·  ⬛ black = dissolve"
    )

    text = (
        f"◈ <b>THE CUTTING RITUAL</b>\n"
        f"{DIV}\n\n"
        f"<b>Step 1 of 2</b> — Cast the <b>source image</b> into the circle.\n\n"
        f"<i>Oracle mode: {mode}</i>\n"
        f"<i>Reconfigure in ⚙ Oracle settings</i>"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=cancel_keyboard()
        )
    return WAITING_SOURCE_IMAGE


async def magic_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media = telegram_adapter.parse_message_media(update.message)
    if not media:
        await update.message.reply_text(
            "⚠ The form is unrecognised — send a photo or image file.",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_SOURCE_IMAGE

    source_bytes = await download_file_bytes(context.bot, media.file_id)
    if not source_bytes:
        await update.message.reply_text(
            "⚠ The ingredient could not be summoned. Try again.",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_SOURCE_IMAGE

    context.user_data["cut_source"] = source_bytes.getvalue()

    inverted = get_mask_inverted(update.effective_user.id)
    mode = (
        "⬛ black = <b>KEEP</b>  ·  ⬜ white = dissolve"
        if inverted
        else "⬜ white = <b>KEEP</b>  ·  ⬛ black = dissolve"
    )

    await update.message.reply_text(
        f"◈ <b>THE CUTTING RITUAL</b>\n"
        f"{DIV}\n\n"
        f"<b>Step 2 of 2</b> — Now present the <b>B&W mask</b>.\n\n"
        f"{mode}",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_MASK_IMAGE


async def magic_mask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media = telegram_adapter.parse_message_media(update.message)
    if not media:
        await update.message.reply_text(
            "⚠ The mask form is unrecognised — send a black & white image.",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_MASK_IMAGE

    mask_bytes = await download_file_bytes(context.bot, media.file_id)
    if not mask_bytes:
        await update.message.reply_text(
            "⚠ Download failed. Try again.", reply_markup=cancel_keyboard()
        )
        return WAITING_MASK_IMAGE

    source_data = context.user_data.get("cut_source")
    if not source_data:
        await update.message.reply_text(
            "⚠ Source image was lost. Please start over.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 Start Over", callback_data="menu_magic")]]
            ),
        )
        context.user_data.clear()
        return ConversationHandler.END

    progress = await update.message.reply_text(
        "◈ <i>The ritual is at work...</i>", parse_mode="HTML"
    )

    try:
        source_io = io.BytesIO(source_data)
        inverted = get_mask_inverted(update.effective_user.id)
        result_webp = apply_mask_to_image(source_io, mask_bytes, inverted=inverted)

        context.user_data["cut_result"] = result_webp.getvalue()

        await progress.delete()
        await update.message.reply_photo(
            photo=io.BytesIO(context.user_data["cut_result"]),
            caption="◈ <b>The cut is revealed.</b>",
            parse_mode="HTML",
        )

        packs = get_user_packs(update.effective_user.id)
        keyboard_rows = []
        if packs:
            for name, title in packs:
                keyboard_rows.append(
                    [
                        InlineKeyboardButton(
                            f"✦ Seal into  {title}", callback_data=f"cutpack_{name}"
                        )
                    ]
                )
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "🜁 Extract the Essence", callback_data="cut_download"
                )
            ]
        )
        keyboard_rows.append(
            [
                InlineKeyboardButton("◈ New Ritual", callback_data="menu_magic"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ]
        )

        await update.message.reply_text(
            "What fate for this essence?",
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
        )
    except Exception as e:
        logger.error(f"Error applying mask: {e}")
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔄 Retry Ritual", callback_data="menu_magic")],
                [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
            ]
        )
        await progress.edit_text(
            f"⚠ <b>The ritual faltered</b>\n"
            f"{DIV}\n\n"
            "Inspect your ingredients.\n"
            "<i>The mask must be a black & white image.</i>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        context.user_data.clear()
        return ConversationHandler.END

    return WAITING_CUT_PACK


async def magic_pack_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    cut_result = context.user_data.get("cut_result")
    if not cut_result:
        await query.edit_message_text(
            "⚠ Sticker data lost. Start over.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 Start Over", callback_data="menu_magic")]]
            ),
        )
        context.user_data.clear()
        return ConversationHandler.END

    if data == "cut_download":
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(cut_result),
            filename="stixmagic_essence.webp",
            caption="🜁 The essence is extracted — yours to keep.",
        )
        await query.edit_message_text(
            "🜁 <b>Essence extracted</b>",
            parse_mode="HTML",
            reply_markup=home_keyboard(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    if data.startswith("cutpack_"):
        pack_name = data.replace("cutpack_", "")
        user = query.from_user
        packs = get_user_packs(user.id)
        # Optimization: Use dict lookup instead of Python generator expression for O(1) performance
        pack_title = dict(packs).get(pack_name, pack_name)

        try:
            sticker_file = io.BytesIO(cut_result)
            input_sticker = InputSticker(
                sticker=sticker_file, emoji_list=STICKER_EMOJI, format="static"
            )
            await context.bot.add_sticker_to_set(
                user_id=user.id, name=pack_name, sticker=input_sticker
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔗 Open the Vessel",
                            url=f"https://t.me/addstickers/{pack_name}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "◈ New Ritual", callback_data="menu_magic"
                        ),
                        InlineKeyboardButton("✦ Home", callback_data="nav:home"),
                    ],
                ]
            )
            await query.edit_message_text(
                f"✦ <b>Bound to {html.escape(pack_title)}</b>",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Error adding cut sticker: {e}")
            await query.edit_message_text(
                f"⚠ <b>The binding failed</b>\n\n<i>{html.escape(str(e))}</i>",
                parse_mode="HTML",
                reply_markup=home_keyboard(),
            )

    context.user_data.clear()
    return ConversationHandler.END


# ── CATALOG ───────────────────────────────────────────────────

CATALOG_PAGE_SIZE = 5


def _catalog_pack_text(pack: dict, user_reaction: str | None = None) -> str:
    return telegram_adapter.generate_reactions(pack, user_reaction)


async def catalog_show_page(update: Update, sort: str, query: str, page: int):
    """Render a catalog page (edit or send new message)."""
    offset = page * CATALOG_PAGE_SIZE
    packs = catalog_search(
        query=query, sort=sort, limit=CATALOG_PAGE_SIZE, offset=offset
    )
    total = catalog_count(query=query, sort=sort)

    if not packs:
        if page > 0:
            page = 0
            offset = 0
            packs = catalog_search(
                query=query, sort=sort, limit=CATALOG_PAGE_SIZE, offset=offset
            )

    if not packs:
        msg = (
            f"🔍 <b>STICKER CATALOG</b>\n{DIV}\n\n"
            "No packs found in the catalog yet.\n\n"
            "<i>Use /feature to publish your pack!</i>"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⚗️ Feature a Pack", callback_data="menu_feature"
                    )
                ],
                [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
            ]
        )
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        return

    # Show first pack of the page with nav
    pack = packs[0]
    catalog_increment_views(pack["name"])

    user_id = update.effective_user.id
    reaction = catalog_get_user_reaction(user_id, pack["name"])
    text = _catalog_pack_text(pack, reaction)

    max_page = max(0, (total - 1) // CATALOG_PAGE_SIZE)
    safe_page = min(page, max_page)

    rows = [
        [
            InlineKeyboardButton("👍 Like", callback_data=f"cat_like_{pack['name']}"),
            InlineKeyboardButton(
                "👎 Dislike", callback_data=f"cat_dislike_{pack['name']}"
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ Add to Telegram", url=f"https://t.me/addstickers/{pack['name']}"
            )
        ],
    ]

    nav = []
    if safe_page > 0:
        nav.append(
            InlineKeyboardButton(
                "◂ Prev", callback_data=f"cat_page_{sort}__{safe_page - 1}"
            )
        )
    nav.append(
        InlineKeyboardButton(f"{safe_page + 1}/{max_page + 1}", callback_data="noop")
    )
    if safe_page < max_page:
        nav.append(
            InlineKeyboardButton(
                "Next ▸", callback_data=f"cat_page_{sort}__{safe_page + 1}"
            )
        )
    rows.append(nav)

    sort_row = [
        InlineKeyboardButton(
            "🔥 Popular" if sort != "popular" else "✓ Popular",
            callback_data="cat_sort_popular",
        ),
        InlineKeyboardButton(
            "📈 Trending" if sort != "trending" else "✓ Trending",
            callback_data="cat_sort_trending",
        ),
        InlineKeyboardButton(
            "🆕 New" if sort != "new" else "✓ New", callback_data="cat_sort_new"
        ),
    ]
    rows.append(sort_row)
    rows.append(
        [
            InlineKeyboardButton("🔍 Search", callback_data="menu_catalog_search"),
            InlineKeyboardButton("⚗️ Feature Pack", callback_data="menu_feature"),
        ]
    )
    rows.append([InlineKeyboardButton("✦ Home", callback_data="nav:home")])

    keyboard = InlineKeyboardMarkup(rows)
    header = f"🔍 <b>STICKER CATALOG</b> · {sort.upper()}\n{DIV}\n\n"

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                header + text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    else:
        await update.message.reply_text(
            header + text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


async def catalog_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /catalog command and menu_catalog callback."""
    if update.callback_query:
        await update.callback_query.answer()
    sort = context.args[0] if context.args else "popular"
    if sort not in ("popular", "trending", "new"):
        sort = "popular"
    await catalog_show_page(update, sort=sort, query="", page=0)


async def catalog_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user for search query."""
    if context.args:
        return await _catalog_do_search(update, context, " ".join(context.args))

    msg = f"🔍 <b>SEARCH THE CATALOG</b>\n{DIV}\n\n" "Type your search query:"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="menu_catalog")]]
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
    return WAITING_CATALOG_SEARCH


async def catalog_search_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _catalog_do_search(update, context, update.message.text.strip())


async def _catalog_do_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: str
):
    if len(query) < 2:
        await update.message.reply_text("⚠ Query must be at least 2 characters.")
        return WAITING_CATALOG_SEARCH
    await catalog_show_page(update, sort="search", query=query, page=0)
    return ConversationHandler.END


async def catalog_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cat_page_<sort>_<query>_<page> callbacks."""
    query = update.callback_query
    data = query.data  # e.g. cat_page_popular__2
    parts = data[len("cat_page_") :].rsplit("_", 1)
    if len(parts) != 2:
        await query.answer()
        return
    sort_query, page_str = parts
    sq_parts = sort_query.split("_", 1)
    sort = sq_parts[0]
    q = sq_parts[1] if len(sq_parts) > 1 else ""
    try:
        page = int(page_str)
    except ValueError:
        page = 0
    await catalog_show_page(update, sort=sort, query=q, page=page)


async def catalog_sort_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cat_sort_<sort> callbacks."""
    sort = update.callback_query.data.replace("cat_sort_", "")
    await catalog_show_page(update, sort=sort, query="", page=0)


async def catalog_react_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cat_like_<name> and cat_dislike_<name> callbacks."""
    query = update.callback_query
    data = query.data
    if data.startswith("cat_like_"):
        reaction = "like"
        pack_name = data[len("cat_like_") :]
    else:
        reaction = "dislike"
        pack_name = data[len("cat_dislike_") :]

    pack = catalog_get_pack(pack_name)
    if not pack:
        await query.answer("Pack not found in catalog.")
        return

    result = catalog_react(query.from_user.id, pack_name, reaction)
    await query.answer(f"👍 {result['likes']}  👎 {result['dislikes']}")

    # Refresh pack data and re-render
    pack = catalog_get_pack(pack_name)
    if pack:
        user_reaction = catalog_get_user_reaction(query.from_user.id, pack_name)
        text = _catalog_pack_text(pack, user_reaction)
        try:
            await query.edit_message_text(
                f"🔍 <b>STICKER CATALOG</b>\n{DIV}\n\n" + text,
                parse_mode="HTML",
                reply_markup=query.message.reply_markup,
                disable_web_page_preview=True,
            )
        except BadRequest:
            pass


async def pack_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/info <packname> — show catalog info about a pack."""
    pack_name = " ".join(context.args).strip() if context.args else ""
    if not pack_name:
        await update.message.reply_text(
            f"🔍 <b>PACK INFO</b>\n{DIV}\n\n"
            "Usage: <code>/info pack_name</code>\n"
            "or: <code>/info https://t.me/addstickers/pack_name</code>",
            parse_mode="HTML",
        )
        return

    if "t.me/addstickers/" in pack_name:
        pack_name = pack_name.split("t.me/addstickers/")[-1].strip().rstrip("/")

    progress = await update.message.reply_text(
        "🔍 <i>Consulting the archives...</i>", parse_mode="HTML"
    )

    # Try to get from Telegram first
    try:
        ss = await context.bot.get_sticker_set(pack_name)
        title = ss.title

        count = len(ss.stickers)
        animated = any(s.is_animated for s in ss.stickers)
        video = any(s.is_video for s in ss.stickers)
        kind = "video" if video else ("animated" if animated else "static")
    except Exception:
        await progress.edit_text(
            f"⚠ Pack <code>{html.escape(pack_name)}</code> not found on Telegram.",
            parse_mode="HTML",
            reply_markup=home_keyboard(),
        )
        return

    catalog_pack = catalog_get_pack(pack_name)
    user_reaction = (
        catalog_get_user_reaction(update.effective_user.id, pack_name)
        if catalog_pack
        else None
    )

    text = (
        f"🔍 <b>{html.escape(title)}</b>\n"
        f"{DIV}\n\n"
        f"<b>Name:</b> <code>{html.escape(pack_name)}</code>\n"
        f"<b>Type:</b> {kind}  ·  <b>Stickers:</b> {count}\n"
    )
    if catalog_pack:
        catalog_increment_views(pack_name)
        stats_text = telegram_adapter.generate_reactions(catalog_pack, user_reaction)
        text += "\n" + stats_text.split("\n")[-1] + "\n"
        if catalog_pack.get("description"):
            text += f"\n<i>{html.escape(catalog_pack['description'])}</i>\n"
        rows = [
            [
                InlineKeyboardButton("👍 Like", callback_data=f"cat_like_{pack_name}"),
                InlineKeyboardButton(
                    "👎 Dislike", callback_data=f"cat_dislike_{pack_name}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "➕ Add to Telegram", url=f"https://t.me/addstickers/{pack_name}"
                )
            ],
            [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
        ]
    else:
        text += "\n<i>Not yet in the Stix Magic catalog.</i>\n"
        rows = [
            [
                InlineKeyboardButton(
                    "➕ Add to Telegram", url=f"https://t.me/addstickers/{pack_name}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚗️ Feature this Pack", callback_data=f"feature_pack_{pack_name}"
                )
            ],
            [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
        ]

    await progress.edit_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)
    )


# ── FEATURE / PUBLISH PACK ────────────────────────────────────


async def feature_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry for /feature command and menu_feature / feature_pack_<name> callbacks."""
    pack_name = None
    if update.callback_query:
        await update.callback_query.answer()
        data = update.callback_query.data
        if data.startswith("feature_pack_"):
            pack_name = data[len("feature_pack_") :]

    if pack_name:
        context.user_data["feature_name"] = pack_name
        return await _feature_ask_desc(update, context)

    user = update.effective_user
    packs = await validate_and_sync_packs(context.bot, user.id)

    if not packs:
        msg = (
            f"⚗️ <b>FEATURE A PACK</b>\n{DIV}\n\n"
            "You have no packs yet. Forge one first!"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚗️ Forge a Pack", callback_data="menu_create")],
                [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
            ]
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        return ConversationHandler.END

    keyboard_rows = [
        [InlineKeyboardButton(f"▦ {title}", callback_data=f"featpack_{name}")]
        for name, title in packs
    ]
    keyboard_rows.append([InlineKeyboardButton("✕ Cancel", callback_data="nav:home")])
    msg = (
        f"⚗️ <b>FEATURE A PACK</b>\n{DIV}\n\n"
        "Which pack shall be published to the catalog?"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    else:
        await update.message.reply_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    return WAITING_FEATURE_PACK


async def feature_pack_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pack_name = query.data.replace("featpack_", "")
    context.user_data["feature_name"] = pack_name
    return await _feature_ask_desc(update, context)


async def _feature_ask_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pack_name = context.user_data.get("feature_name", "")
    msg = (
        f"⚗️ <b>FEATURE A PACK</b>\n{DIV}\n\n"
        f"Pack: <code>{html.escape(pack_name)}</code>\n\n"
        "Add a short description (or send <b>-</b> to skip):"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="nav:home")]]
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
    return WAITING_FEATURE_DESC


async def feature_desc_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""
    pack_name = context.user_data.get("feature_name", "")
    user = update.effective_user

    progress = await update.message.reply_text(
        "⚗️ <i>Publishing to the catalog...</i>", parse_mode="HTML"
    )

    try:
        ss = await context.bot.get_sticker_set(pack_name)
        title = ss.title
        animated = any(s.is_animated for s in ss.stickers)
        video = any(s.is_video for s in ss.stickers)
        pack_type = "video" if video else ("animated" if animated else "image")
    except Exception:
        await progress.edit_text(
            f"⚠ Pack <code>{html.escape(pack_name)}</code> not found on Telegram.",
            parse_mode="HTML",
            reply_markup=home_keyboard(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    added = catalog_add_pack(
        pack_name, title, user.id, description=desc, pack_type=pack_type
    )

    if added:
        await progress.edit_text(
            f"✦ <b>Pack featured!</b>\n{DIV}\n\n"
            f"<b>{html.escape(title)}</b> is now in the Stix Magic catalog.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔍 View Catalog", callback_data="menu_catalog"
                        )
                    ],
                    [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
                ]
            ),
        )
    else:
        await progress.edit_text(
            f"✦ <b>{html.escape(title)}</b> is already in the catalog.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔍 View Catalog", callback_data="menu_catalog"
                        )
                    ],
                    [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
                ]
            ),
        )

    context.user_data.clear()
    return ConversationHandler.END


# ── INLINE QUERY ──────────────────────────────────────────────


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries: @botname <query>."""
    query_text = update.inline_query.query.strip()

    if not query_text:
        packs = catalog_search(sort="popular", limit=10)
    else:
        packs = catalog_search(query=query_text, sort="search", limit=10)

    results = []
    for pack in packs:
        name = pack["name"]
        title = pack["title"]
        desc = pack.get("description", "")
        likes = pack.get("likes", 0)
        dislikes = pack.get("dislikes", 0)
        message_text = (
            f"🔍 <b>{html.escape(title)}</b>\n" f"<code>{html.escape(name)}</code>\n"
        )
        if desc:
            message_text += f"\n<i>{html.escape(desc)}</i>\n"
        message_text += f"\n👍 {likes}  ·  👎 {dislikes}"
        message_text += (
            f'\n\n➕ <a href="https://t.me/addstickers/{name}">Add to Telegram</a>'
        )

        results.append(
            InlineQueryResultArticle(
                id=name,
                title=title,
                description=f"{'📦 ' + desc if desc else ''}  👍{likes} 👎{dislikes}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ Add to Telegram",
                                url=f"https://t.me/addstickers/{name}",
                            )
                        ],
                    ]
                ),
            )
        )

    await update.inline_query.answer(results, cache_time=30, is_personal=False)


# ── PACKS / MANAGE / HELP / ABOUT ───────────────────────────


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "✦ The ritual is dissolved.", reply_markup=home_keyboard()
    )
    return ConversationHandler.END


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📖 <b>THE CRAFT</b>\n"
        f"{DIV}\n\n"
        "<b>⚗️ FORGE A PACK</b>\n"
        "  Name the vessel → seal a sticker inside\n"
        "  → pack is live on Telegram\n\n"
        "<b>✦ INSCRIBE A STICKER</b>\n"
        "  Choose a vessel → bind more stickers within\n\n"
        "<b>◈ THE CUTTING RITUAL</b>\n"
        "  Cast a photo + black & white mask\n"
        "  → receive a clean transparent cutout\n\n"
        "<b>⚙ ORACLE SETTINGS</b>\n"
        "  Reconfigure the mask oracle (white/black = keep)\n"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "◦ Alchemist's Field Notes", callback_data="nav:tips"
                )
            ],
            [
                InlineKeyboardButton("◂ Back", callback_data="nav:help"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ],
        ]
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"✦ <b>STIX MAGIC</b>\n"
        f"{DIV}\n\n"
        "An alchemist's workshop for Telegram stickers.\n\n"
        "Every image holds a sticker in waiting.\n"
        "We transmute it. We cut. We seal.\n\n"
        "Forge packs. Bind stickers. Perform the ritual.\n\n"
        "<i>stixmagic.com</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌐 stixmagic.com", url="https://stixmagic.com")],
            [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
        ]
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def manage_stickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if update.callback_query:
        await update.callback_query.answer()

    packs = await validate_and_sync_packs(context.bot, user.id)

    if not packs:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚗️ Forge a Pack", callback_data="menu_create")],
                [
                    InlineKeyboardButton("◂ Back", callback_data="nav:my_packs"),
                    InlineKeyboardButton("✦ Home", callback_data="nav:home"),
                ],
            ]
        )
        msg = f"⚗️ <b>THE CRUCIBLE</b>\n{DIV}\n\nThe crucible is empty — no vessels to manage."
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        return

    msg_parts = [f"⚗️ <b>THE CRUCIBLE</b>\n{DIV}\n\n"]
    for idx, (name, title) in enumerate(packs, 1):
        msg_parts.append(f"{idx}.  <b>{title}</b>\n")
    msg = "".join(msg_parts)

    keyboard_rows = []
    for name, title in packs:
        keyboard_rows.append(
            [
                InlineKeyboardButton(f"✦ {title}", callback_data=f"addto_{name}"),
                InlineKeyboardButton("🜄", callback_data=f"del_{name}"),
            ]
        )
    keyboard_rows.append(
        [InlineKeyboardButton("⚗️ Forge New Pack", callback_data="menu_create")]
    )
    keyboard_rows.append(
        [
            InlineKeyboardButton("◂ Back", callback_data="nav:my_packs"),
            InlineKeyboardButton("✦ Home", callback_data="nav:home"),
        ]
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    else:
        await update.message.reply_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )


async def delete_pack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pack_name = query.data.replace("del_", "")
    user = query.from_user
    packs = get_user_packs(user.id)
    # Optimization: Use dict lookup instead of Python generator expression for O(1) performance
    pack_title = dict(packs).get(pack_name, pack_name)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✓ Yes, remove", callback_data=f"delconfirm_{pack_name}"
                ),
                InlineKeyboardButton("✕ Keep it", callback_data="menu_manage"),
            ]
        ]
    )
    await query.edit_message_text(
        f"⚠ Dissolve <b>{pack_title}</b> from your grimoire?\n\n"
        "<i>This only removes it from Stix Magic — the Telegram vessel stays live.</i>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def delete_pack_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pack_name = query.data.replace("delconfirm_", "")
    user = query.from_user
    packs = get_user_packs(user.id)
    # Optimization: Use dict lookup instead of Python generator expression for O(1) performance
    pack_title = dict(packs).get(pack_name, pack_name)

    delete_pack_from_db(user.id, pack_name)

    await query.edit_message_text(
        f"🜄 <b>{pack_title}</b> dissolved from your grimoire.",
        parse_mode="HTML",
        reply_markup=home_keyboard(),
    )


async def show_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if update.callback_query:
        await update.callback_query.answer()

    packs = await validate_and_sync_packs(context.bot, user.id)

    if not packs:
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚗️ Forge a Pack", callback_data="menu_create")],
                [
                    InlineKeyboardButton("◂ Back", callback_data="nav:my_packs"),
                    InlineKeyboardButton("✦ Home", callback_data="nav:home"),
                ],
            ]
        )
        msg = f"📖 <b>YOUR GRIMOIRE</b>\n{DIV}\n\nThe grimoire is empty.\nForge your first vessel!"
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                msg, parse_mode="HTML", reply_markup=keyboard
            )
        return

    msg_parts = [f"📖 <b>YOUR GRIMOIRE</b>\n{DIV}\n\n"]
    for idx, (name, title) in enumerate(packs, 1):
        msg_parts.append(f"<b>{idx}. {title}</b>\n")
    msg = "".join(msg_parts)

    keyboard_rows = []
    for name, title in packs:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    f"🔗 {title}", url=f"https://t.me/addstickers/{name}"
                )
            ]
        )
    keyboard_rows.append(
        [
            InlineKeyboardButton("⚗️ Forge Pack", callback_data="menu_create"),
            InlineKeyboardButton("✦ Inscribe Sticker", callback_data="menu_addsticker"),
        ]
    )
    keyboard_rows.append(
        [
            InlineKeyboardButton("◂ Back", callback_data="nav:my_packs"),
            InlineKeyboardButton("✦ Home", callback_data="nav:home"),
        ]
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text(
            msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard_rows),
            disable_web_page_preview=True,
        )


async def settings_mask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    inverted = get_mask_inverted(user.id)
    current = (
        "⬛ Black = keep · ⬜ White = dissolve"
        if inverted
        else "⬜ White = keep · ⬛ Black = dissolve"
    )
    toggle_label = (
        "Switch to ⬜ White = keep" if inverted else "Switch to ⬛ Black = keep"
    )

    text = (
        f"◐ <b>THE ORACLE</b>\n"
        f"{DIV}\n\n"
        f"Current mode: <b>{current}</b>\n\n"
        "<i>The oracle decides which color in your mask\n"
        "is preserved and which is dissolved.</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(toggle_label, callback_data="toggle_mask")],
            [
                InlineKeyboardButton("◂ Back", callback_data="nav:settings"),
                InlineKeyboardButton("✦ Home", callback_data="nav:home"),
            ],
        ]
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def toggle_mask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    current = get_mask_inverted(user.id)
    set_mask_inverted(user.id, not current)
    await query.answer("Oracle reconfigured ✦")
    await settings_mask(update, context)


# ── SYNC / IMPORT PACK ───────────────────────────────────────


async def sync_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /sync command."""
    if context.args:
        return await _sync_process(update, context, " ".join(context.args))
    await update.message.reply_text(
        f"🔄 <b>SUMMON A PACK</b>\n{DIV}\n\n"
        "Speak the pack name or link to summon it into your grimoire:\n\n"
        "<code>my_pack_name</code>\n"
        "or\n"
        "<code>https://t.me/addstickers/my_pack_name</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✕ Cancel", callback_data="nav:home")]]
        ),
    )
    return WAITING_SYNC_NAME


async def sync_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _sync_process(update, context, update.message.text.strip())


async def _sync_process(
    update: Update, context: ContextTypes.DEFAULT_TYPE, pack_input: str
):
    """Validate the pack name/link and add to DB if found."""
    pack_name = pack_input.strip().rstrip("/")
    if "t.me/addstickers/" in pack_name:
        pack_name = pack_name.split("t.me/addstickers/")[-1].strip().rstrip("/")

    user = update.effective_user
    status_msg = await update.message.reply_text(
        "🔄 <i>Consulting the archives...</i>", parse_mode="HTML"
    )

    try:
        ss = await context.bot.get_sticker_set(pack_name)
    except Exception:
        await status_msg.edit_text(
            f"⚠ <b>Pack not found in the archives</b>\n{DIV}\n\n"
            f"No vessel named <code>{html.escape(pack_name)}</code> exists on Telegram.\n\n"
            "Try speaking the name again, or /cancel to abandon.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✕ Cancel", callback_data="nav:home")]]
            ),
        )
        return WAITING_SYNC_NAME

    existing = get_user_packs(user.id)
    if any(n == pack_name for n, _ in existing):
        await status_msg.edit_text(
            f"✦ <b>{html.escape(ss.title)}</b> is already bound to your grimoire.",
            parse_mode="HTML",
            reply_markup=home_keyboard(),
        )
        return ConversationHandler.END

    add_pack_to_db(user.id, pack_name, ss.title)
    await status_msg.edit_text(
        f"⚗️ <b>Pack summoned!</b>\n{DIV}\n\n"
        f"<b>{html.escape(ss.title)}</b> has been bound to your grimoire.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔗 Open the Vessel",
                        url=f"https://t.me/addstickers/{pack_name}",
                    )
                ],
                [InlineKeyboardButton("⚗️ The Crucible", callback_data="menu_manage")],
                [InlineKeyboardButton("✦ Home", callback_data="nav:home")],
            ]
        ),
    )
    return ConversationHandler.END


# ── CALLBACK ROUTER ──────────────────────────────────────────


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "menu_manage":
        await manage_stickers(update, context)
    elif data == "menu_help_detail":
        await show_help(update, context)
    elif data == "menu_packs":
        await show_packs(update, context)
    elif data == "menu_about":
        await show_about(update, context)
    elif data == "settings_mask":
        await settings_mask(update, context)
    elif data == "toggle_mask":
        await toggle_mask(update, context)
    elif data.startswith("del_"):
        await delete_pack_callback(update, context)
    elif data.startswith("delconfirm_"):
        await delete_pack_confirm(update, context)
    elif data == "menu_catalog" or data == "menu_catalog_browse":
        await catalog_start(update, context)
    elif data == "menu_catalog_search":
        await catalog_search_start(update, context)
    elif data == "noop":
        await query.answer()
    elif data.startswith("cat_sort_"):
        await catalog_sort_callback(update, context)
    elif data.startswith("cat_page_"):
        await catalog_page_callback(update, context)
    elif data.startswith("cat_like_") or data.startswith("cat_dislike_"):
        await catalog_react_callback(update, context)


# ── MAIN ─────────────────────────────────────────────────────


def _get_create_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("create", create_start),
            CallbackQueryHandler(create_start, pattern="^menu_create$"),
        ],
        states={
            WAITING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_title)
            ],
            WAITING_TITLE_CONFIRM: [
                CallbackQueryHandler(
                    create_title_confirm, pattern="^forge_(confirm|edit)$"
                )
            ],
            WAITING_STICKER: [
                MessageHandler(filters.ALL & ~filters.COMMAND, create_sticker)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def _get_addsticker_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("addsticker", addsticker_start),
            CallbackQueryHandler(addsticker_start, pattern="^menu_addsticker$"),
            CallbackQueryHandler(addto_direct, pattern="^addto_"),
        ],
        states={
            CHOOSING_PACK: [CallbackQueryHandler(addsticker_choose, pattern="^pack_")],
            WAITING_STICKER_ADD: [
                MessageHandler(filters.ALL & ~filters.COMMAND, addsticker_receive)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def _get_magic_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("magic", magic_start),
            CallbackQueryHandler(magic_start, pattern="^menu_magic$"),
        ],
        states={
            WAITING_SOURCE_IMAGE: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, magic_source)
            ],
            WAITING_MASK_IMAGE: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, magic_mask)
            ],
            WAITING_CUT_PACK: [
                CallbackQueryHandler(
                    magic_pack_action, pattern="^(cutpack_|cut_download)"
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def _get_sync_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("sync", sync_start),
            CallbackQueryHandler(sync_start, pattern="^menu_sync$"),
        ],
        states={
            WAITING_SYNC_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sync_receive)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def _get_catalog_search_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("search", catalog_search_start),
            CallbackQueryHandler(catalog_search_start, pattern="^menu_catalog_search$"),
        ],
        states={
            WAITING_CATALOG_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, catalog_search_receive)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def _get_feature_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("feature", feature_start),
            CallbackQueryHandler(feature_start, pattern="^menu_feature$"),
            CallbackQueryHandler(feature_start, pattern="^feature_pack_"),
        ],
        states={
            WAITING_FEATURE_PACK: [
                CallbackQueryHandler(feature_pack_chosen, pattern="^featpack_")
            ],
            WAITING_FEATURE_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, feature_desc_receive)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def setup_handlers(application):
    """Register all command, conversation, and callback handlers."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("packs", show_packs))
    application.add_handler(CommandHandler("manage", manage_stickers))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("about", show_about))
    application.add_handler(CommandHandler("catalog", catalog_start))
    application.add_handler(CommandHandler("info", pack_info))

    application.add_handler(_get_create_conv())

    application.add_handler(_get_addsticker_conv())

    application.add_handler(_get_magic_conv())

    application.add_handler(_get_sync_conv())

    application.add_handler(_get_catalog_search_conv())

    application.add_handler(_get_feature_conv())

    application.add_handler(InlineQueryHandler(inline_query_handler))
    application.add_handler(CallbackQueryHandler(nav_callback, pattern="^nav:"))
    application.add_handler(CallbackQueryHandler(menu_callback))


def main():
    try:
        settings = get_settings()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return

    token = settings.telegram_bot_token
    runtime_mode = "DEVELOPMENT" if settings.is_development else "PRODUCTION"
    logger.info(
        "Runtime mode: %s (APP_ENV=%s). Telegram token source: %s. Pack namespace prefix: %s.",
        runtime_mode,
        settings.app_env,
        settings.telegram_token_source,
        _pack_namespace_prefix(),
    )

    from menus import MINIAPP_URL

    async def post_init(app):
        if MINIAPP_URL:
            try:
                await app.bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="✦ Mini App", web_app=WebAppInfo(url=MINIAPP_URL)
                    )
                )
                logger.info(f"Menu button set to Mini App: {MINIAPP_URL}")
            except Exception as e:
                logger.warning(f"Could not set menu button: {e}")

        from telegram import BotCommand

        try:
            await app.bot.set_my_commands(
                [
                    BotCommand("start", "Open the main menu"),
                    BotCommand("create", "Forge a new sticker pack"),
                    BotCommand("addsticker", "Add a sticker to an existing pack"),
                    BotCommand("magic", "Cut out a subject with a B&W mask"),
                    BotCommand("sync", "Import / summon an existing pack"),
                    BotCommand("catalog", "Browse the community sticker catalog"),
                    BotCommand("search", "Search the sticker catalog"),
                    BotCommand("feature", "Publish your pack to the catalog"),
                    BotCommand("info", "Get info & stats for any sticker pack"),
                    BotCommand("packs", "View all your packs"),
                    BotCommand("manage", "Manage / delete your packs"),
                    BotCommand("help", "Show all commands and tips"),
                    BotCommand("cancel", "Cancel the current operation"),
                ]
            )
            logger.info("Bot commands registered")
        except Exception as e:
            logger.warning(f"Could not set bot commands: {e}")

    application = Application.builder().token(token).post_init(post_init).build()

    setup_handlers(application)

    from api import run_api

    web_thread = threading.Thread(target=run_api, daemon=True)
    web_thread.start()
    logger.info("API + landing page serving on port 5000")

    logger.info("Stix Magic bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
