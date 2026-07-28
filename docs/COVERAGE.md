# Coverage Report — Before / After

Recorded after all engine, loader, moderation, and menu tests landed (tasks 1–16).

Date: 2026-07-28

## In-scope modules — Before (baseline)

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

## In-scope modules — After (tasks 2–16 complete)

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| core/__init__.py | 3 | 0 | 100.0% |
| core/contracts.py | 6 | 0 | 100.0% |
| core/engine.py | 34 | 0 | 100.0% |
| core/types.py | 27 | 0 | 100.0% |
| domain/__init__.py | 0 | 0 | 100.0% |
| domain/media.py | 20 | 7 | 65.0% |
| loaders/__init__.py | 5 | 0 | 100.0% |
| loaders/config.py | 12 | 0 | 100.0% |
| loaders/controller.py | 66 | 4 | 93.9% |
| loaders/definitions.py | 1 | 0 | 100.0% |
| loaders/render.py | 15 | 0 | 100.0% |
| loaders/selection.py | 15 | 0 | 100.0% |
| moderation/__init__.py | 5 | 0 | 100.0% |
| moderation/dev_harness.py | 45 | 2 | 95.6% |
| moderation/host.py | 129 | 2 | 98.4% |
| moderation/plugin.py | 49 | 1 | 98.0% |
| moderation/wizard.py | 34 | 1 | 97.1% |
| **TOTAL** | **466** | **17** | **96.4%** |

## Additional in-scope module (project root)

| Module | Stmts | Miss | Cover (before) | Cover (after) |
|--------|-------|------|----------------|---------------|
| menus.py | 43 | 2 | 0.0% | 95.3% |

## Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total in-scope statements | 439 | 466 | +27 (new code) |
| Statements missed | 419 | 17 | −402 |
| Overall coverage | 4.6% | 96.4% | **+91.8 pp** |

Coverage was collected with:
```
pytest tests/ --cov --cov-report=term-missing
```

Configuration in `pyproject.toml` under `[tool.coverage.run]`.
