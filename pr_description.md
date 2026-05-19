🎯 **What:** `main.py` was missing tests for the `send_menu` handler which orchestrates keyboard assembly and bot response editing/sending. This addresses the testing gap for a critical interaction point in the bot.
📊 **Coverage:** The new test file (`tests/test_main_send_menu.py`) fully covers the `send_menu` function. It tests:
  - Both branches (when invoked from a `callback_query` and when invoked from a standard `message`).
  - Handling of the expected `BadRequest("Message is not modified")` which is safely ignored.
  - Verification that other, unexpected `BadRequest` errors are properly propagated.
✨ **Result:** Test coverage and reliability of the `main.py` menu sending logic are significantly improved, safeguarding against future regressions.
