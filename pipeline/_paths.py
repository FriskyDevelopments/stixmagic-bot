"""
pipeline/_paths.py – Canonical path constants for the MagicStix pipeline.

Import these constants instead of constructing relative paths ad-hoc in
each module.  This module is the single source of truth for where the
``assets/``, ``renders/``, and ``packs/`` directories live relative to the
repository root.
"""

from pathlib import Path

# Absolute path of the repository root (the directory that contains
# ``main.py``, ``pipeline/``, ``assets/``, etc.).
REPO_ROOT: Path = Path(__file__).parent.parent.resolve()

# Default locations of the three main pipeline directories.
ASSETS_SOURCE_DIR: Path = REPO_ROOT / "assets" / "source"
RENDERS_DIR: Path = REPO_ROOT / "renders"
PACKS_DIR: Path = REPO_ROOT / "packs"
