"""Pytest compatibility helpers for synchronous wrappers and import isolation."""

import asyncio
import sys
from unittest.mock import Mock

import pytest


_STUB_MODULES_TO_RESET = (
    "config",
    "config.runtime",
    "moderation",
    "infra",
    "infra.db",
    "stixmagic",
    "stixmagic.settings",
    "domain",
    "domain.media",
    "core",
    "core.engine",
    "platforms",
    "platforms.telegram",
    "loaders",
    "menus",
    "flask",
    "telegram",
)


def _remove_mock_modules() -> None:
    """Remove MagicMock modules and restore real modules patched by legacy tests."""
    for module_name in _STUB_MODULES_TO_RESET:
        module = sys.modules.get(module_name)
        if isinstance(module, Mock):
            sys.modules.pop(module_name, None)

    for module_name in _STUB_MODULES_TO_RESET:
        if "." not in module_name:
            continue
        parent_name, child_name = module_name.rsplit(".", 1)
        parent = sys.modules.get(parent_name)
        if parent is not None:
            child = getattr(parent, child_name, None)
            if isinstance(child, Mock):
                try:
                    delattr(parent, child_name)
                except AttributeError:
                    pass

    import importlib

    real_infra_db = sys.modules.get("infra.db")
    if real_infra_db is not None and isinstance(getattr(real_infra_db, "init_db", None), Mock):
        importlib.reload(real_infra_db)

    real_runtime = sys.modules.get("config.runtime")
    if real_runtime is not None and isinstance(getattr(real_runtime, "get_settings", None), Mock):
        importlib.reload(real_runtime)


@pytest.fixture(autouse=True)
def ensure_default_event_loop():
    """Ensure legacy tests using get_event_loop() have a usable loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    yield


def pytest_collection_finish(session):
    _remove_mock_modules()


def pytest_runtest_setup(item):
    _remove_mock_modules()


def pytest_runtest_teardown(item, nextitem):
    _remove_mock_modules()
