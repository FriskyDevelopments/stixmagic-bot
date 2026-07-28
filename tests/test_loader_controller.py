"""
Tests for loaders/controller.py — LoaderController and LoaderSession.

Requirements covered:
  4.6 — loaders/controller.py advances and stops cleanly, and cannot be
        started twice for the same context.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from loaders.config import LoaderConfig
from loaders.controller import LoaderController, LoaderSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_LOADER: dict = {
    "name": "test_loader",
    "frames": ["frame0 🟣", "frame1 🟣", "frame2 🟣"],
    "captions": ["✨ testing magic..."],
}


def _make_message() -> AsyncMock:
    """Create a fake Telegram Message with an edit_text async method."""
    msg = AsyncMock()
    msg.edit_text = AsyncMock()
    return msg


def _fast_config(**overrides) -> LoaderConfig:
    """Config with very short timings for fast tests."""
    defaults = {
        "loaders_enabled": True,
        "min_duration_for_animation_ms": 10,  # 10 ms — near-instant
        "frame_interval_ms": 10,
        "max_frames_per_loop": 3,
    }
    defaults.update(overrides)
    return LoaderConfig(**defaults)


# ---------------------------------------------------------------------------
# 4.6 — Advances cleanly: start spawns a background task that edits the message
# ---------------------------------------------------------------------------


class TestLoaderControllerStart:
    """LoaderController.start() spawns an animation task."""

    @pytest.mark.asyncio
    async def test_start_creates_background_task(self):
        """start() creates an asyncio task that will animate the message."""
        msg = _make_message()
        cfg = _fast_config()
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()

        # The internal task should exist and be running
        assert ctrl._task is not None
        assert not ctrl._task.done()

        # Clean up
        await ctrl.stop()

    @pytest.mark.asyncio
    async def test_start_disabled_does_not_create_task(self):
        """When loaders_enabled=False, start() is a no-op."""
        msg = _make_message()
        cfg = _fast_config(loaders_enabled=False)
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()

        assert ctrl._task is None
        msg.edit_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_animation_edits_message_after_min_duration(self):
        """After min_duration_for_animation_ms, the controller edits the message."""
        msg = _make_message()
        cfg = _fast_config(min_duration_for_animation_ms=10)
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()
        # Wait long enough for at least the initial delay + one frame
        await asyncio.sleep(0.05)
        await ctrl.stop()

        # The message should have been edited at least once
        assert msg.edit_text.call_count >= 1


# ---------------------------------------------------------------------------
# 4.6 — Stops cleanly
# ---------------------------------------------------------------------------


class TestLoaderControllerStop:
    """LoaderController.stop() cancels cleanly without exceptions."""

    @pytest.mark.asyncio
    async def test_stop_cancels_running_task(self):
        """stop() cancels the background task and sets it to None."""
        msg = _make_message()
        cfg = _fast_config()
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()
        assert ctrl._task is not None

        await ctrl.stop()

        # Task should be cleaned up
        assert ctrl._task is None
        assert ctrl._stop_called is True

    @pytest.mark.asyncio
    async def test_stop_idempotent(self):
        """stop() can be called multiple times without raising."""
        msg = _make_message()
        cfg = _fast_config()
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()
        await ctrl.stop()
        # Second and third calls should be no-ops
        await ctrl.stop()
        await ctrl.stop()

        assert ctrl._stop_called is True

    @pytest.mark.asyncio
    async def test_stop_before_start_is_safe(self):
        """stop() before start() is safe — nothing to cancel."""
        msg = _make_message()
        cfg = _fast_config()
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        # stop without start should not raise
        await ctrl.stop()
        assert ctrl._stop_called is True

    @pytest.mark.asyncio
    async def test_stop_during_initial_delay_cancels_cleanly(self):
        """stop() during the initial delay period cancels without edits."""
        msg = _make_message()
        # Long initial delay — stop fires before any frame renders
        cfg = _fast_config(min_duration_for_animation_ms=5000)
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()
        # Immediately stop — should cancel during the initial sleep
        await ctrl.stop()

        # No frames should have been rendered
        msg.edit_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_animation_stops_on_edit_failure(self):
        """If edit_text raises a non-cancellation error, animation stops gracefully."""
        msg = _make_message()
        msg.edit_text.side_effect = RuntimeError("Telegram API error")
        cfg = _fast_config(min_duration_for_animation_ms=5)
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()
        # Wait for the animation to encounter the error and self-terminate
        await asyncio.sleep(0.05)

        # The task should have exited gracefully (returned, not raised)
        assert ctrl._task.done()
        # No unhandled exception from the task
        exc = ctrl._task.exception()
        assert exc is None

        await ctrl.stop()


# ---------------------------------------------------------------------------
# 4.6 — Cannot be started twice for the same context
# ---------------------------------------------------------------------------


class TestLoaderControllerDoubleStart:
    """A LoaderController cannot be started twice for the same context."""

    @pytest.mark.asyncio
    async def test_second_start_does_not_spawn_second_task(self):
        """Calling start() again after start() does not create a second task.

        The controller stores its task in self._task. If start() is called
        again, it would overwrite the reference to the first task, leaking it.
        The code should guard against this — either by being a no-op on the
        second call or by raising.
        """
        msg = _make_message()
        cfg = _fast_config(min_duration_for_animation_ms=5000)
        ctrl = LoaderController(msg, _SAMPLE_LOADER, config=cfg)

        await ctrl.start()
        first_task = ctrl._task
        assert first_task is not None

        # Second start — should not overwrite or create a new task
        await ctrl.start()
        second_task = ctrl._task

        # Either the second call was a no-op (same task) or it raised.
        # The key invariant: the first task is not leaked/orphaned.
        assert second_task is first_task, (
            "start() called twice created a second task — "
            "the first task would be leaked (orphaned, never cancelled)"
        )

        await ctrl.stop()


# ---------------------------------------------------------------------------
# LoaderSession context manager
# ---------------------------------------------------------------------------


class TestLoaderSession:
    """LoaderSession async context manager wraps start/stop."""

    @pytest.mark.asyncio
    async def test_context_manager_starts_and_stops(self):
        """Entering the context starts; exiting stops."""
        msg = _make_message()
        cfg = _fast_config(min_duration_for_animation_ms=5000)

        async with LoaderSession(msg, _SAMPLE_LOADER, config=cfg) as session:
            # Controller should be started (task exists)
            assert session.controller._task is not None
            assert not session.controller._stop_called

        # After exiting, stop should have been called
        assert session.controller._stop_called is True

    @pytest.mark.asyncio
    async def test_context_manager_stops_on_exception(self):
        """stop() is called even if the body raises."""
        msg = _make_message()
        cfg = _fast_config(min_duration_for_animation_ms=5000)

        with pytest.raises(ValueError, match="deliberate"):
            async with LoaderSession(msg, _SAMPLE_LOADER, config=cfg) as session:
                raise ValueError("deliberate error")

        # Stop should still have been called
        assert session.controller._stop_called is True

    @pytest.mark.asyncio
    async def test_context_manager_yields_session(self):
        """The context manager yields itself with .controller accessible."""
        msg = _make_message()
        cfg = _fast_config(loaders_enabled=False)

        async with LoaderSession(msg, _SAMPLE_LOADER, config=cfg) as session:
            assert isinstance(session, LoaderSession)
            assert isinstance(session.controller, LoaderController)


# ---------------------------------------------------------------------------
# Frame advancement
# ---------------------------------------------------------------------------


class TestLoaderControllerAdvancement:
    """The controller advances through frames sequentially."""

    @pytest.mark.asyncio
    async def test_edits_contain_frame_content(self):
        """Each edit_text call contains rendered frame content."""
        msg = _make_message()
        cfg = _fast_config(min_duration_for_animation_ms=5, frame_interval_ms=10)
        ctrl = LoaderController(msg, _SAMPLE_LOADER, caption="test cap", config=cfg)

        await ctrl.start()
        # Allow a few frames to render
        await asyncio.sleep(0.08)
        await ctrl.stop()

        # Should have edited at least once
        assert msg.edit_text.call_count >= 1
        # Each call should contain the caption
        for call in msg.edit_text.call_args_list:
            text = call.args[0] if call.args else call.kwargs.get("text", "")
            assert "test cap" in text

    @pytest.mark.asyncio
    async def test_frames_cycle_in_order(self):
        """Frames are shown in sequential order (0, 1, 2, 0, 1, ...)."""
        msg = _make_message()
        cfg = _fast_config(min_duration_for_animation_ms=5, frame_interval_ms=10)
        # Use distinct frames for easy identification
        loader = {
            "name": "order_test",
            "frames": ["AAA 🟣", "BBB 🟣", "CCC 🟣"],
            "captions": ["cap"],
        }
        ctrl = LoaderController(msg, loader, caption="cap", config=cfg)

        await ctrl.start()
        # Allow enough time for at least 3 frames
        await asyncio.sleep(0.08)
        await ctrl.stop()

        # Verify sequential ordering
        texts = [
            call.args[0] if call.args else call.kwargs.get("text", "")
            for call in msg.edit_text.call_args_list
        ]
        assert len(texts) >= 2, "Expected at least 2 frame edits"

        # Frames should follow the pattern: AAA, BBB, CCC, AAA, BBB, ...
        expected_cycle = ["AAA", "BBB", "CCC"]
        for i, text in enumerate(texts):
            expected_marker = expected_cycle[i % 3]
            assert expected_marker in text, (
                f"Frame {i} expected to contain '{expected_marker}' but got: {text}"
            )
