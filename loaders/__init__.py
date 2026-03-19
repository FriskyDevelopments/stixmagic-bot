"""
loaders/__init__.py – Public API for the Stix Magic loader system.

Quick-start (explicit controller):

    from loaders import LoaderController, get_loader_for_context
    import random

    loader  = get_loader_for_context("create_pack")
    caption = random.choice(loader["captions"])
    msg     = await update.message.reply_text(caption)

    ctrl = LoaderController(msg, loader)
    await ctrl.start()
    try:
        result = await do_slow_work()
    finally:
        await ctrl.stop()   # idempotent — safe to call multiple times

    await msg.edit_text(final_text, ...)

Quick-start (context manager):

    from loaders import LoaderSession, get_loader_for_context

    loader = get_loader_for_context("create_pack")
    msg    = await update.message.reply_text(loader["captions"][0])

    async with LoaderSession(msg, loader):
        result = await do_slow_work()

    await msg.edit_text(final_text, ...)
"""

from .config import DEFAULT_CONFIG, LoaderConfig
from .controller import LoaderController, LoaderSession
from .render import render_frame, render_static
from .selection import get_loader_by_name, get_loader_for_context, get_random_loader

__all__ = [
    "LoaderConfig",
    "DEFAULT_CONFIG",
    "LoaderController",
    "LoaderSession",
    "render_frame",
    "render_static",
    "get_random_loader",
    "get_loader_by_name",
    "get_loader_for_context",
]
