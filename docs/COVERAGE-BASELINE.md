# Coverage Baseline

Recorded **before** new engine/loader/moderation tests land.

Date: 2026-07-28

## In-scope modules

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| core/__init__.py | 3 | 3 | 0.0% |
| core/contracts.py | 6 | 6 | 0.0% |
| core/engine.py | 25 | 25 | 0.0% |
| core/types.py | 27 | 27 | 0.0% |
| domain/__init__.py | 0 | 0 | 100.0% |
| domain/media.py | 20 | 0 | 100.0% |
| loaders/__init__.py | 5 | 5 | 0.0% |
| loaders/config.py | 12 | 12 | 0.0% |
| loaders/controller.py | 63 | 63 | 0.0% |
| loaders/definitions.py | 1 | 1 | 0.0% |
| loaders/render.py | 15 | 15 | 0.0% |
| loaders/selection.py | 15 | 15 | 0.0% |
| moderation/__init__.py | 5 | 5 | 0.0% |
| moderation/dev_harness.py | 40 | 40 | 0.0% |
| moderation/host.py | 124 | 124 | 0.0% |
| moderation/plugin.py | 44 | 44 | 0.0% |
| moderation/wizard.py | 34 | 34 | 0.0% |
| **TOTAL** | **439** | **419** | **4.6%** |

## Notes

- `domain/media.py` shows 100% because existing tests (in `tests/test_domain_media.py`)
  already exercise the shim layer's import paths.
- `menus.py` is at the project root; the coverage source configuration covers it
  but it is not imported by any passing test in the current suite.
- Coverage was collected with: `pytest tests/ --cov --cov-report=term-missing`
