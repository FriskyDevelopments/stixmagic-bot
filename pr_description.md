🧪 [testing improvement] Add tests for main.py navigation handlers

🎯 **What:**
The `send_menu` and `nav_callback` functions in `main.py` lacked test coverage. These functions are critical for routing and rendering UI state transitions (like inline keyboards and text menus) via the Telegram Bot API. Due to their tight coupling with the API, they were difficult to unit test and thus overlooked.

📊 **Coverage:**
Created `tests/test_main_nav.py` to test the missing functionalities using `unittest.IsolatedAsyncioTestCase` and `unittest.mock.patch`. The tests provide coverage for:
- Routing a callback query through `nav_callback` to `send_menu`
- Properly addressing callback query requests with `answer()`
- Editing the callback query message text, ignoring benign "Message is not modified" Telegram `BadRequest` errors but properly raising others
- Directly answering standalone messages by creating a new reply

✨ **Result:**
Significant improvement in test coverage for core navigation logic within `main.py`. The new isolated async tests handle API mocked dependencies securely without introducing cross-test pollution.
