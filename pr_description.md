## 🧹 [code health improvement] Refactor `setup_handlers` to extract conversation logic

🎯 **What:** The monolithic `setup_handlers` function in `main.py` was overly long and complex, heavily nested with large instantiations of `ConversationHandler` classes for various bot flows (create, addsticker, magic, sync, catalog, feature). These have been refactored and extracted into standalone, private helper functions (e.g., `_get_create_conv()`, `_get_addsticker_conv()`).

💡 **Why:** By breaking down the `setup_handlers` function, we significantly improve the readability and maintainability of the bot's core entry point. Developers can now easily observe all registered handlers at a high level without scrolling through verbose state dictionaries and callbacks. It also isolates the conversation logic, making it easier to mock or test individually in the future.

✅ **Verification:** I ran the `black` and `isort` formatters, and the `ruff` linter across the file to ensure stylistic correctness. Finally, I executed the full test suite (`python -m unittest discover tests`), which successfully passed with no regressions related to handler registrations, confirming that the functionality remains identical.

✨ **Result:** `setup_handlers` is now extremely clean, concise, and easy to maintain.
