# Release and Production Promotion Guide

This repository now uses a **validate in PR → merge to `main` → manual production promotion** model.
That is the safest fit for the current bot because the codebase does not yet include a native deployment target that GitHub Actions can update directly, and the bot process itself is a long-running Telegram polling worker.

## Release model

1. **Pull request validation**
   - Workflow: **PR Validation**
   - Trigger: `pull_request` targeting `main`
   - Purpose: compile the code, install runtime dependencies, and run a local smoke test without requiring secrets.

2. **Post-merge validation**
   - Workflow: **Main Branch Validation**
   - Trigger: `push` to `main`
   - Purpose: confirm the exact merged revision is still healthy before promotion.

3. **Controlled production promotion**
   - Workflow: **Production Promotion**
   - Trigger: manual `workflow_dispatch`
   - Purpose: validate production secrets, confirm the production bot token can authenticate with Telegram, and give the operator a clean handoff for the persistent production host.

## Secrets and configuration

### GitHub Actions secrets

| Secret | Required | Used by | Notes |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Production Promotion | Production Telegram bot token. |
| `STIXMAGIC_API_KEY` | Yes | Production Promotion | API authentication key for the deployed app. |
| `TELEGRAM_WEBHOOK_SECRET` | Yes | Production Promotion | Used as Flask secret key and webhook verifier shared secret. |
| `TELEGRAM_BOT_USERNAME` | Recommended | Production Promotion | Enables deterministic deep links in Mini App bootstrap/intent responses. |
| `STIXMAGIC_PUBLIC_BASE_URL` | Optional | Production Promotion | Enables strict Mini App CORS allowlist and absolute API URLs. |

> Recommended hardening: scope all production secrets to the GitHub **production environment** so dispatches inherit environment protections and approvals.

### Runtime variable mapping

- Development and production both use `TELEGRAM_BOT_TOKEN`; isolate values by environment/secrets manager, not by variable name.
- `TELEGRAM_WEBHOOK_SECRET` should always be set in production to avoid ephemeral process-local Flask secrets.

## Why promotion is manual

The repository does not currently include infrastructure credentials or a repo-native deploy target that GitHub Actions can safely mutate.
Running `python main.py` on a GitHub-hosted runner would only start a temporary process and is **not** a real deployment.

Because of that, the safest honest model is:

- validate the code in PR,
- validate the merged revision on `main`,
- manually run a production preflight that uses the production token safely,
- then restart or redeploy the long-running production host outside GitHub Actions.

## Operator workflow

### Before approving a PR

- Confirm **PR Validation** is green.
- Review workflow or secret changes carefully.
- Confirm no development token or `.env` data is committed.
- Confirm the change does not require additional production secrets.

### After merge

- Confirm **Main Branch Validation** is green on `main`.
- Run **Production Promotion** with `git_ref=main`.
- Wait for the workflow to pass.
- Update or restart the persistent production host so it runs the merged code with:
  - `TELEGRAM_BOT_TOKEN` = production Telegram token
  - `STIXMAGIC_API_KEY` = production API key
  - `TELEGRAM_WEBHOOK_SECRET` = production webhook/session secret
  - `STIXMAGIC_PUBLIC_BASE_URL` = production HTTPS origin, if Mini App/browser clients are used

### Manual production verification

After the production host is restarted:

1. Open the bot in Telegram.
2. Send `/start` and confirm the home menu renders.
3. Run one low-risk user flow, such as opening `/help` or `/packs`.
4. Load the production health endpoint (`/api/health`) and confirm it returns `ok`.
5. If the Mini App is enabled, open it from Telegram and confirm it loads.

## Rollback guidance

If promotion fails after restart:

1. Stop the production process.
2. Redeploy or restart the last known-good revision.
3. Reapply the same production secrets.
4. Re-run the manual checks above.
5. Investigate the failing merged revision before attempting promotion again.