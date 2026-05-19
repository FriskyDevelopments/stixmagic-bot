🧪 [testing improvement] Add tests for main.py helpers

🎯 **What:** The testing gap addressed
The issue identified a lack of unit tests for helper functions within `main.py` (specifically `_pack_namespace_prefix`, `cancel_keyboard`, `home_keyboard`, `back_home_keyboard`, and `send_menu`). Because these rely heavily on the Telegram Bot API and other application setup, they were difficult to test directly.

📊 **Coverage:** What scenarios are now tested
A new test file `tests/test_main_helpers.py` was created. It uses a robust set of stubs to bypass the need for a full Telegram application or database initialization, isolating the logic. The tests cover:
- Environment-specific logic in `_pack_namespace_prefix`.
- Structure and content of the generated keyboards (`cancel_keyboard`, `home_keyboard`, `back_home_keyboard`).
- Polymorphic routing of `send_menu` (handling both callback queries and standard messages).
- Error suppression for expected `BadRequest` exceptions (e.g., "Message is not modified") versus re-raising unexpected ones.

✨ **Result:** The improvement in test coverage
The critical navigation and rendering logic in the bot's presentation layer now has deterministic tests, ensuring changes to the menu system or state constants don't break the user experience.
