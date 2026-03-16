"""
loaders/controller.py – Animation controller for Telegram loader messages.

Standard usage:
    loader = get_loader_for_context("create_pack")
    caption = random.choice(loader["captions"])
    msg = await update.message.reply_text(caption)

    ctrl = LoaderController(msg, loader)
    await ctrl.start()
    try:
        result = await do_slow_work()
    finally:
        await ctrl.stop()   # safe to call multiple times — idempotent

    await msg.edit_text(final_text, ...)

Cleaner alternative using the context manager:
    async with LoaderSession(msg, loader):
        result = await do_slow_work()
    await msg.edit_text(final_text, ...)

The controller:
  • waits min_duration_for_animation_ms before showing the first frame
    so fast operations never show animation at all.
  • edits the same Telegram message in a background asyncio Task.
  • stops cleanly on cancel or edit failure.
  • stop() is idempotent — safe to call from multiple paths (success,
    error, finally) without double-cancellation or race conditions.
  • is isolated per-call — no shared state between commands.
"""

import asyncio
import logging
import random

from .config import DEFAULT_CONFIG, LoaderConfig
from .render import render_frame

logger = logging.getLogger(__name__)


class LoaderController:
    """Animate a Telegram message through loader frames in the background."""

    def __init__(
        self,
        message,
        loader: dict,
        caption: str | None = None,
        config: LoaderConfig | None = None,
    ):
        self._message = message
        self._loader = loader
        # Pin a caption for the entire animation so it stays stable.
        self._caption = caption or random.choice(
            loader.get("captions") or DEFAULT_CONFIG.default_caption_set
        )
        self._config = config or DEFAULT_CONFIG
        self._task: asyncio.Task | None = None
        self._stop_called: bool = False

    async def start(self) -> None:
        """Spawn the background animation task (no-op if disabled)."""
        if not self._config.loaders_enabled:
            logger.debug("[loader] disabled globally, skipping '%s'", self._loader["name"])
            return
        self._task = asyncio.create_task(self._animate())
        logger.debug("[loader] started '%s'", self._loader["name"])

    async def stop(self) -> None:
        """Cancel the animation task and wait for it to finish cleanly.

        Idempotent — safe to call from multiple code paths (success block,
        error handler, finally clause) without causing double-cancellation
        or asyncio errors.
        """
        if self._stop_called:
            return
        self._stop_called = True

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        logger.debug("[loader] stopped '%s'", self._loader["name"])

    async def _animate(self) -> None:
        """Background loop: wait, then cycle through frames."""
        # Initial delay — if the operation finishes before this, no frames
        # are ever shown and the static caption remains unchanged.
        try:
            await asyncio.sleep(self._config.min_duration_for_animation_ms / 1000)
        except asyncio.CancelledError:
            logger.debug("[loader] cancelled before first frame (fast operation)")
            return

        max_frames = min(len(self._loader["frames"]), self._config.max_frames_per_loop)
        frame_idx = 0

        while True:
            text = render_frame(
                self._loader,
                frame_idx,
                caption=self._caption,
                config=self._config,
            )
            try:
                await self._message.edit_text(text, parse_mode=None)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                # Telegram can reject edits for various reasons (rate limit,
                # message deleted, "not modified", etc.).  Rather than
                # retrying and spamming the API, disable animation for this
                # run so the main handler always reaches its final edit.
                logger.debug("[loader] edit failed, disabling animation (%s)", exc)
                return

            frame_idx = (frame_idx + 1) % max_frames

            try:
                await asyncio.sleep(self._config.frame_interval_ms / 1000)
            except asyncio.CancelledError:
                return


class LoaderSession:
    """Async context manager wrapper around LoaderController.

    Automatically starts and stops the loader, ensuring stop() is always
    called even if the body raises.  Useful for keeping handler code clean.

    The context manager yields itself; use `.controller` if you need to
    access the underlying LoaderController inside the block (e.g. to call
    custom methods), but this is rarely needed.

    Example (simple):
        msg = await update.message.reply_text(loader["captions"][0])
        async with LoaderSession(msg, loader):
            result = await async_convert_to_sticker(file_bytes)
        await msg.edit_text(final_text, ...)

    Example (accessing the controller):
        async with LoaderSession(msg, loader) as session:
            # session.controller is the LoaderController instance
            result = await async_convert_to_sticker(file_bytes)
    """

    def __init__(
        self,
        message,
        loader: dict,
        caption: str | None = None,
        config: LoaderConfig | None = None,
    ):
        self.controller = LoaderController(message, loader, caption=caption, config=config)
        self._ctrl = self.controller  # internal alias

    async def __aenter__(self) -> "LoaderSession":
        await self._ctrl.start()
        return self

    async def __aexit__(self, *_) -> None:
        await self._ctrl.stop()
