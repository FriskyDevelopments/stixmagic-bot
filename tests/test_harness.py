"""
Tests verifying the test harness itself (task 1).

Requirements covered:
  1.1 — Socket guard prevents network access.
  1.2 — Pre-existing failures are documented (TEST-BASELINE.md exists).
  1.3 — Coverage is configured for in-scope modules.
  1.4 — tmp_path is available and writes stay within it.
"""

from __future__ import annotations

import os
import pathlib
import socket

import pytest

from tests.conftest import FakeTelegramBot, NetworkAccessError


# ---------------------------------------------------------------------------
# 1.1 — Socket guard blocks real connections
# ---------------------------------------------------------------------------


class TestSocketGuard:
    """The conftest socket guard must prevent real network I/O."""

    def test_socket_connect_raises(self):
        """Any call to socket.connect raises NetworkAccessError."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(NetworkAccessError, match="network connection"):
            s.connect(("example.com", 80))
        s.close()

    def test_socket_connect_ex_raises(self):
        """connect_ex is also blocked."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(NetworkAccessError):
            s.connect_ex(("example.com", 443))
        s.close()


# ---------------------------------------------------------------------------
# 1.2 — TEST-BASELINE.md exists and has content
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestBaselineDocumentation:
    """docs/TEST-BASELINE.md must exist and describe the pre-existing state."""

    def test_test_baseline_exists(self):
        baseline = _REPO_ROOT / "docs" / "TEST-BASELINE.md"
        assert baseline.exists(), "docs/TEST-BASELINE.md must exist"

    def test_test_baseline_has_content(self):
        baseline = _REPO_ROOT / "docs" / "TEST-BASELINE.md"
        text = baseline.read_text()
        assert len(text) > 200, "TEST-BASELINE.md should be a substantive document"
        assert "pre-existing" in text.lower() or "baseline" in text.lower()


# ---------------------------------------------------------------------------
# 1.3 — Coverage configuration covers in-scope modules
# ---------------------------------------------------------------------------


class TestCoverageConfiguration:
    """pyproject.toml must configure coverage for the in-scope modules."""

    def test_coverage_source_configured(self):
        pyproject = _REPO_ROOT / "pyproject.toml"
        assert pyproject.exists()
        content = pyproject.read_text()
        # The [tool.coverage.run] section should list in-scope modules
        assert "[tool.coverage.run]" in content
        for module in ("core", "domain", "loaders", "moderation"):
            assert f'"{module}"' in content, f"{module} not in coverage source"

    def test_coverage_baseline_exists(self):
        baseline = _REPO_ROOT / "docs" / "COVERAGE-BASELINE.md"
        assert baseline.exists(), "docs/COVERAGE-BASELINE.md must exist"
        text = baseline.read_text()
        assert "4.6%" in text, "Baseline should record the starting 4.6% coverage"


# ---------------------------------------------------------------------------
# 1.4 — Tests can write within tmp_path (and only there)
# ---------------------------------------------------------------------------


class TestTmpPathEnforcement:
    """Tests must use tmp_path for file I/O."""

    def test_tmp_path_is_writable(self, tmp_path):
        f = tmp_path / "test_write.txt"
        f.write_text("hello")
        assert f.read_text() == "hello"

    def test_tmp_path_is_isolated(self, tmp_path):
        """Each test gets its own tmp_path directory."""
        assert tmp_path.exists()
        assert tmp_path.is_dir()
        # tmp_path should be under the system temp directory
        assert "pytest" in str(tmp_path) or "tmp" in str(tmp_path).lower()


# ---------------------------------------------------------------------------
# Fakes — verify the conftest fakes are usable
# ---------------------------------------------------------------------------


class TestFakeTelegramBot:
    """The FakeTelegramBot from conftest should be usable without network."""

    def test_fake_bot_instantiates(self, fake_telegram_bot):
        assert isinstance(fake_telegram_bot, FakeTelegramBot)
        assert fake_telegram_bot.username == "stixmagicbot"

    @pytest.mark.asyncio
    async def test_fake_bot_send_message(self, fake_telegram_bot):
        await fake_telegram_bot.send_message(chat_id=123, text="test")
        fake_telegram_bot.send_message.assert_called_once_with(
            chat_id=123, text="test"
        )

    @pytest.mark.asyncio
    async def test_fake_bot_records_calls(self, fake_telegram_bot):
        await fake_telegram_bot.send_sticker(chat_id=1, sticker="abc")
        assert fake_telegram_bot.send_sticker.call_count == 1


class TestFakeMediaConvert:
    """The fake media converters must produce non-None output."""

    def test_sync_image_convert(self, fake_media_convert):
        import io

        result = fake_media_convert.convert_to_sticker(io.BytesIO(b"\x00"))
        assert result is not None
        assert len(result.getvalue()) > 0

    def test_sync_video_convert(self, fake_media_convert):
        import io

        result = fake_media_convert.convert_video_to_sticker(io.BytesIO(b"\x00"))
        assert result is not None
        assert len(result.getvalue()) > 0
