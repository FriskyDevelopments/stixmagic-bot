# STIX Magic — engine, loaders and moderation tests: implementation plan

- [x] 1. Stand up the harness
  - Coverage reporting over the in-scope modules; record the baseline in
    `docs/COVERAGE-BASELINE.md`
  - Fakes for the Telegram client and for `domain/media.py`'s conversion calls; a
    conftest guard that fails any test opening a socket
  - Record the pre-existing failures in `docs/TEST-BASELINE.md` — the suite does
    not collect cleanly today (missing `telegram_bot_token` and other settings).
    Do not fix them and do not skip them; they are not your regression
  - Your new tests must run in isolation, without depending on that baseline
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Test `generate_pack` for image and video
  - Documented `PackGenerationResult` for each, with the right `sticker_format`
  - _Requirements: 2.1_

- [x] 3. Test engine failure paths
  - Unsupported `media_type` returns the documented failure, not a raise and not
    a silently-static sticker
  - A conversion failure surfaces as an actionable result, never an unhandled
    exception and never a success
  - _Requirements: 2.2, 2.3_

- [x] 4. Test reaction rendering
  - `render_reaction` / `ReactionRenderResult` follows the same contract as pack
    generation, including its failure path
  - _Requirements: 2.4_

- [x] 5. Test engine input edge cases and escaping
  - Empty, truncated and oversized `file_bytes` each handled explicitly
  - User-supplied text is HTML-escaped exactly once — assert a payload containing
    `&amp;` does not become `&amp;amp;`
  - _Requirements: 2.5, 2.6_

- [x] 6. Test the contracts
  - Every input dataclass rejects a missing required field rather than producing
    a half-built object
  - Optional defaults are as documented, and no default is a shared mutable
  - _Requirements: 3.1, 3.2_

- [x] 7. Test the loader catalogue
  - Every `LOADERS` entry has the keys the renderer reads; no duplicate names
  - `get_random_loader` only returns entries from `LOADERS`
  - _Requirements: 4.1, 4.2_

- [ ] 8. Test loader lookup
  - `get_loader_by_name` returns `None` for unknown rather than raising, and is
    exact-match unless documented otherwise
  - `get_loader_for_context` is context-appropriate per known action, random for
    unknown
  - _Requirements: 4.3, 4.4_

- [ ] 9. Test loader rendering
  - Every entry renders without raising, and output is escaped for its surface
  - _Requirements: 4.5_

- [ ] 10. Test the loader controller
  - Advances and stops cleanly; cannot be started twice for the same context
  - _Requirements: 4.6_

- [ ] 11. Test loader configuration
  - Documented defaults when config is absent; a malformed config falls back
    rather than crashing
  - _Requirements: 4.7_

- [ ] 12. Test that moderation fails closed
  - A check that errors, and a backend that is unreachable, must not approve
  - _Requirements: 5.1_

- [ ] 13. Test moderation verdicts
  - Each documented verdict produced by the condition described
  - _Requirements: 5.2_

- [ ] 14. Pin the dev harness shut
  - `moderation/dev_harness.py` cannot be enabled in a production configuration;
    assert it, so the harness can never become a bypass
  - _Requirements: 5.3_

- [ ] 15. Test the menus
  - Every menu builds a keyboard Telegram would accept: callback data within the
    length limit, no empty rows, no duplicate callback data
  - Menu text with user content is escaped
  - _Requirements: 6.1, 6.2_

- [ ] 16. Add the credential guard and record coverage
  - Scan tracked source for credential-shaped literals; fail with file and line
  - `docs/COVERAGE.md` with per-module before/after
  - _Requirements: 7.1, 7.2, 1.3_
