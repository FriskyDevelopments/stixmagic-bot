"""
Shared test fixtures and guards for the Stix Magic test suite.

Provides:
- Socket guard: fails any test that attempts to open a real network socket.
- Fake Telegram client factory.
- Fake domain/media conversion functions.
- tmp_path enforcement (no writes outside pytest tmp_path).
"""

from __future__ import annotations

import io
import socket
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# 1.1 — Socket guard: fail any test that opens a real socket connection
# ---------------------------------------------------------------------------

_original_socket_connect = socket.socket.connect


class NetworkAccessError(Exception):
    """Raised when a test attempts real network I/O."""


def _blocked_connect(self, *args, **kwargs):
    """Replacement for socket.connect that always raises."""
    raise NetworkAccessError(
        f"Test attempted to open a network connection to {args!r}. "
        "All tests must run without network access."
    )


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """Auto-use fixture that prevents any socket.connect call in every test."""
    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked_connect)


# ---------------------------------------------------------------------------
# Fakes: Telegram client
# ---------------------------------------------------------------------------


class FakeTelegramBot:
    """
    A lightweight fake Telegram Bot that records calls without network I/O.

    Usage in tests:
        bot = fake_telegram_bot()
        await bot.send_message(chat_id=123, text="hi")
        assert bot.send_message.call_args.kwargs["text"] == "hi"
    """

    def __init__(self):
        self.send_message = AsyncMock()
        self.send_sticker = AsyncMock()
        self.create_new_sticker_set = AsyncMock()
        self.add_sticker_to_set = AsyncMock()
        self.delete_sticker_set = AsyncMock()
        self.get_sticker_set = AsyncMock()
        self.get_file = AsyncMock()
        self.answer_callback_query = AsyncMock()
        self.edit_message_text = AsyncMock()
        self.delete_message = AsyncMock()
        self.username = "stixmagicbot"
        self.id = 999999


@pytest.fixture()
def fake_telegram_bot():
    """Return a fresh FakeTelegramBot instance."""
    return FakeTelegramBot()


# ---------------------------------------------------------------------------
# Fakes: domain/media conversion
# ---------------------------------------------------------------------------

_FAKE_WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP"  # Minimal WEBP header stub


def _fake_convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Fake image→sticker conversion: returns a small WEBP-like buffer."""
    return io.BytesIO(_FAKE_WEBP_BYTES)


def _fake_convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Fake video→sticker conversion: returns a small buffer."""
    return io.BytesIO(b"\x1a\x45\xdf\xa3")  # Minimal EBML/WEBM header stub


async def _fake_async_convert_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Async fake image→sticker conversion."""
    return _fake_convert_to_sticker(file_bytes)


async def _fake_async_convert_video_to_sticker(file_bytes: io.BytesIO) -> io.BytesIO | None:
    """Async fake video→sticker conversion."""
    return _fake_convert_video_to_sticker(file_bytes)


@pytest.fixture()
def fake_media_convert(monkeypatch):
    """
    Patch domain.media conversion functions with fakes.

    Returns a namespace with the fake functions for assertion if needed.
    """
    import domain.media as media_mod

    monkeypatch.setattr(media_mod, "convert_to_sticker", _fake_convert_to_sticker)
    monkeypatch.setattr(media_mod, "convert_video_to_sticker", _fake_convert_video_to_sticker)
    monkeypatch.setattr(media_mod, "async_convert_to_sticker", _fake_async_convert_to_sticker)
    monkeypatch.setattr(
        media_mod, "async_convert_video_to_sticker", _fake_async_convert_video_to_sticker
    )

    class _Fakes:
        convert_to_sticker = staticmethod(_fake_convert_to_sticker)
        convert_video_to_sticker = staticmethod(_fake_convert_video_to_sticker)
        async_convert_to_sticker = staticmethod(_fake_async_convert_to_sticker)
        async_convert_video_to_sticker = staticmethod(_fake_async_convert_video_to_sticker)

    return _Fakes


# ---------------------------------------------------------------------------
# 1.4 — tmp_path enforcement hint
# ---------------------------------------------------------------------------
# pytest's tmp_path fixture already isolates file writes. This note serves as
# documentation: tests must use tmp_path for any file I/O.  The CI coverage
# configuration combined with code review enforces this.  A runtime check for
# "writes outside tmp_path" would require heavy OS-level tracing; instead we
# rely on the convention and PR review.
