---
inclusion: always
---

# Rules of engagement

You are implementing the spec in `.kiro/specs/engine-loader-tests/`.

## Scope

- Implement **one numbered task from `tasks.md` at a time**, in order.
- Satisfy exactly the `_Requirements:_` listed on that task. Do not implement
  tasks that were not asked for, and do not refactor toward later ones.
- Tick a checkbox in `tasks.md` only when the task is genuinely implemented and
  its tests pass. Never mark done what you did not do.
- If a task is blocked on a credential, a provisioned external resource, or an
  owner decision: append it to `docs/BLOCKERS.md` with the task number and what
  is missing, leave the checkbox unchecked, and move on to the next task.

## Hard lines

- **Never deploy.** No `docker push`, no `wrangler deploy`, no remote restart,
  no migration against any remote database. Local and dry-run only.
- **Never call the Telegram Bot API for real.** Every call goes through a fake
  that records what was asked and performs nothing.
- **Never shell out to a real ffmpeg** against a file the test did not create,
  and never write outside `tmp_path`.
- **Do not touch** `integrations/virtual_camera/`, `integrations/extension/`,
  `integrations/overlay_engine/` — they front native/OS surfaces — or any
  payment or billing path.
- **Never weaken moderation.** If a test cannot pass without letting content
  through, the test is wrong.
- **Never write a real credential** into any file. Reference secrets by `op://`
  path or environment variable name only. Test fixtures use obviously fake
  values.
- **No network in tests.** A test that would contact Telegram or any host is
  wrong. Fakes only.
- Never send a message or publish a sticker pack during a test run.

## Git

- All work happens on the current branch. Never commit to `main`.
- One commit per completed task, message `task N: <short description>`.
- Never force-push, never rewrite history.

## Testing

- Do not weaken, skip, `xfail`, or delete an existing test to make the suite
  green. If an existing test breaks, the change is wrong — fix the change.
- Tests must not write outside a pytest `tmp_path`.
- A task is not done until the full `pytest` suite passes, not just the new file.

## Style

- Match the surrounding code: same naming, same import style, same docstring
  voice.
- Where a module's behaviour and its documentation disagree, **test the code as
  written** and say so in the commit message rather than silently picking one.
