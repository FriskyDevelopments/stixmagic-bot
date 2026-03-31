# Deployment Guide

## Goals

- Keep development and production isolated.
- Validate all changes against the development bot first.
- Promote to production only after explicit manual approval.

## 1) Development deployment (first target)

Use `APP_ENV=development` and set development-only variables:
- `DEV_BOT_TOKEN` (or `TELEGRAM_BOT_TOKEN_DEV`)
- `STIXMAGIC_API_KEY_DEV`
- optional: `SESSION_SECRET_DEV`, `MINIAPP_URL_DEV`

### Local dev preflight

```bash
APP_ENV=development python scripts/check_config.py
APP_ENV=development python scripts/smoke_test.py
```

Expected behavior:
- Startup log states `Runtime mode: DEVELOPMENT`.
- Startup log shows dev token source variable.
- New sticker packs are named with `devstix_...` prefix.

## 2) Production deployment (explicit promotion)

Use `APP_ENV=production` and set production-only variables:
- `TELEGRAM_BOT_TOKEN` (or `BOT_TOKEN`)
- `STIXMAGIC_API_KEY_PROD` (or `STIXMAGIC_API_KEY`)
- `SESSION_SECRET_PROD` (or `SESSION_SECRET`)
- optional: `MINIAPP_URL_PROD` (or `MINIAPP_URL`)

### Production preflight

```bash
APP_ENV=production python scripts/check_config.py
APP_ENV=production python scripts/smoke_test.py
```

## 3) GitHub Actions usage

- `ci.yml`: runs on PR + push and requires no Telegram/API secrets.
- `development.yml`: manual/on-branch development readiness against development environment secrets.
- `production.yml`: manual production promotion preflight only, with production environment protection.
- `deploy.yml`: manual reminder workflow, no auto-deploy.

## 4) Hard safety checks

Runtime exits early on:
- invalid `APP_ENV`
- missing required vars for selected environment
- multiple alias vars set for one setting
- production token variables present while in development
- malformed bot token
