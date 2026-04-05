"""
Tests for main.py – navigation and general menu callbacks.

Covers:
 - nav_callback: extraction of menu_id from query.data and delegation to send_menu.
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the stub setup from the forge handlers test
from tests.test_main_forge_handlers import _patch_heavy_imports

_patch_heavy_imports()

# Now we can import what we need from main
import main as _main_mod
from main import nav_callback

class TestNavCallback(unittest.IsolatedAsyncioTestCase):
    @patch("main.send_menu")
    async def test_nav_callback(self, mock_send_menu):
        """Test that nav_callback parses the query data and calls send_menu correctly."""
        # Setup mocks
        mock_send_menu.return_value = None

        update = MagicMock()
        update.callback_query.data = "nav:catalog"
        context = MagicMock()

        # Execute
        await nav_callback(update, context)

        # Verify
        mock_send_menu.assert_called_once_with(update, "catalog")

if __name__ == "__main__":
    unittest.main()
