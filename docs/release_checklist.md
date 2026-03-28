# Release Checklist

## Development-ready definition

A branch is **development ready** when:
- CI passes without secrets (`ci.yml`, `validate.yml`).
- `development.yml` passes with development environment secrets.
- Bot launches in `APP_ENV=development` and logs development mode/token source.
- Test-created sticker packs are visibly isolated (`devstix_` prefix).

## Production-ready definition

A revision is **production ready** when:
- Development-ready criteria are complete.
- `production.yml` passes against protected production environment secrets.
- Human review confirms no dev-only env values remain in production settings.
- Deployment runbook in `docs/deployment.md` is followed.

## Merge-to-main checklist

1. Confirm CI green on PR.
2. Confirm development workflow green on target branch.
3. Validate documentation updates for any new/changed env vars.
4. Confirm no secrets committed.
5. Merge to `main`.

## Enable production deployment checklist

1. Run `production.yml` with `git_ref=main`.
2. Confirm protected production environment approvals completed.
3. Confirm production runtime has:
   - `APP_ENV=production`
   - one production bot token variable only
   - one production API key variable
   - one production session secret variable
4. Restart production host/runtime.
5. Perform post-deploy smoke checks:
   - Telegram `/start`
   - API `/api/health`
   - sticker pack create flow on production bot

## Exact dev-to-prod promotion point

The promotion point is the **successful completion of `production.yml` for `git_ref=main` plus protected environment approval**. Do not deploy production before that point.
