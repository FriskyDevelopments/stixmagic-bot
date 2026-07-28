"""
Credential guard and network hygiene tests (task 16).

Requirements covered:
  7.1 — No credential literal anywhere; a test scans tracked source and fails
        with file and line.
  7.2 — Nothing in the suite reaches the network or the Telegram API.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 7.1 — Credential literal scanner
# ---------------------------------------------------------------------------

# Patterns that look like real credentials.  Each tuple is (description, regex).
# Test fixtures using obviously-fake values (e.g. "test-api-key", "supersecret",
# "smoke-test-secret") are excluded via an allowlist.
_CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "Telegram bot token (numeric_id:base64-secret)",
        re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    ),
    (
        "Generic long hex secret (40+ hex chars, no UUID format)",
        re.compile(r"""(?:token|secret|key|password|credential)\s*[:=]\s*['"]([0-9a-fA-F]{40,})['"]"""),
    ),
    (
        "AWS-style access key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "Private key block",
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
]

# Values that are obviously fake test fixtures — not real credentials.
_ALLOWLIST_VALUES = frozenset(
    {
        "test-api-key",
        "supersecret",
        "smoke-test-secret",
        "fake-bot-token",
        "test-token",
        "test-secret",
        "dummy-key",
        # Obviously-fake Telegram bot token used in test fixtures (sequential chars)
        "123456789:abcdefghijklmnopqrstuvwxyzabcdef_gh",
    }
)

# File paths (relative to repo root) that are expected to reference credential
# variable *names* but never contain real values.
_ALLOWLIST_FILES = frozenset(
    {
        ".env.example",
        "docs/BLOCKERS.md",
        "README.md",
    }
)

# Extensions to scan — source and config files only.
_SCAN_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".cfg",
        ".ini",
        ".sh",
        ".html",
        ".env",
    }
)


def _tracked_source_files() -> list[pathlib.Path]:
    """Return all git-tracked files with scannable extensions."""
    result = subprocess.run(
        ["git", "ls-files", "--cached"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    paths = []
    for line in result.stdout.strip().splitlines():
        p = pathlib.Path(line)
        if p.suffix in _SCAN_EXTENSIONS and p.name not in _ALLOWLIST_FILES:
            paths.append(_REPO_ROOT / p)
    return paths


def _is_allowlisted_value(line: str) -> bool:
    """Check if a line only contains allowlisted fake credential values."""
    lower = line.lower()
    return any(v in lower for v in _ALLOWLIST_VALUES)


def _is_env_var_reference(line: str) -> bool:
    """Check if the line is just referencing an env var name, not a real value."""
    # Lines like: os.environ["BOT_TOKEN"], getenv("KEY"), ${{ secrets.X }}
    env_patterns = [
        r"os\.environ",
        r"os\.getenv",
        r"getenv\(",
        r"\$\{\{\s*secrets\.",
        r"op://",
        r"#.*(?:token|key|secret)",  # Comments mentioning credential names
    ]
    return any(re.search(pat, line, re.IGNORECASE) for pat in env_patterns)


class TestCredentialGuard:
    """No credential literal may appear in tracked source."""

    def test_no_credential_literals_in_source(self):
        """Scan every tracked source file for credential-shaped literals.

        Fails with file path and line number for each violation.
        """
        violations: list[str] = []

        for filepath in _tracked_source_files():
            if not filepath.exists():
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue

            for lineno, line in enumerate(content.splitlines(), start=1):
                # Skip comments-only lines in yaml/config
                stripped = line.strip()
                if stripped.startswith("#") and not stripped.startswith("#!"):
                    continue
                # Skip obvious env-var references
                if _is_env_var_reference(line):
                    continue
                # Skip allowlisted fake values
                if _is_allowlisted_value(line):
                    continue

                for description, pattern in _CREDENTIAL_PATTERNS:
                    if pattern.search(line):
                        rel_path = filepath.relative_to(_REPO_ROOT)
                        violations.append(
                            f"  {rel_path}:{lineno}: {description}\n"
                            f"    → {stripped[:120]}"
                        )

        if violations:
            report = "\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} credential-shaped literal(s) in "
                f"tracked source:\n{report}\n\n"
                "If these are intentionally fake test fixtures, add them to "
                "_ALLOWLIST_VALUES in tests/test_credential_guard.py."
            )

    def test_scanner_covers_all_tracked_python_files(self):
        """The scanner must inspect at least all tracked .py files."""
        result = subprocess.run(
            ["git", "ls-files", "--cached", "*.py"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        py_count = len(result.stdout.strip().splitlines())
        scanned = [f for f in _tracked_source_files() if f.suffix == ".py"]
        assert len(scanned) >= py_count - len(_ALLOWLIST_FILES)


# ---------------------------------------------------------------------------
# 7.2 — Network isolation verification
# ---------------------------------------------------------------------------


class TestNetworkIsolation:
    """Verify the socket guard is active and comprehensive."""

    def test_socket_guard_is_autouse(self):
        """The socket guard fixture is autouse=True in conftest."""
        import socket as sock_mod

        # The guard replaces connect — verify it's active right now
        from tests.conftest import NetworkAccessError

        s = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
        with pytest.raises(NetworkAccessError):
            s.connect(("api.telegram.org", 443))
        s.close()

    def test_no_httplib_escape(self):
        """urllib/httplib cannot reach the network through the socket guard."""
        from tests.conftest import NetworkAccessError

        import urllib.request

        with pytest.raises((NetworkAccessError, OSError)):
            urllib.request.urlopen("https://api.telegram.org/bot/getMe")

    def test_no_requests_escape(self):
        """The requests library (if present) also cannot reach the network."""
        try:
            import requests
        except ImportError:
            pytest.skip("requests not installed")

        from tests.conftest import NetworkAccessError

        with pytest.raises((NetworkAccessError, requests.exceptions.ConnectionError)):
            requests.get("https://api.telegram.org/bot/getMe", timeout=1)

    def test_coverage_doc_exists(self):
        """docs/COVERAGE.md must exist after task 16."""
        coverage_doc = _REPO_ROOT / "docs" / "COVERAGE.md"
        assert coverage_doc.exists(), "docs/COVERAGE.md must exist"
        text = coverage_doc.read_text()
        assert "Before" in text or "before" in text
        assert "After" in text or "after" in text
