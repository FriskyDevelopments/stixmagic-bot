# Environment Matrix

This repository now uses a strict runtime model driven by `APP_ENV`.

Allowed values:
- `development`
- `production`

`APP_ENV` defaults to `development` if unset.

## Variable contract

| Variable | Development | Production | Notes |
|---|---|---|---|
| `APP_ENV` | **Required** | **Required** | Must be exactly `development` or `production`. |
| `DEV_BOT_TOKEN` | **Required** (preferred) | Forbidden | Development bot token. |
| `TELEGRAM_BOT_TOKEN_DEV` | Required alternative | Forbidden | Development token alias. |
| `BOT_TOKEN_DEV` | Legacy alternative | Forbidden | Kept for compatibility. |
| `TELEGRAM_BOT_TOKEN` | Forbidden | **Required** (preferred) | Production bot token. |
| `BOT_TOKEN` | Forbidden | Required alternative | Production token alias. |
| `STIXMAGIC_API_KEY_DEV` | **Required** | Forbidden | API key for development runtime. |
| `STIXMAGIC_API_KEY_PROD` | Forbidden | **Required** (preferred) | API key for production runtime. |
| `STIXMAGIC_API_KEY` | Forbidden | Required alternative | Production API key alias. |
| `SESSION_SECRET_DEV` | Optional | Forbidden | Optional for local dev sessions. |
| `SESSION_SECRET_PROD` | Forbidden | **Required** (preferred) | Required in production. |
| `SESSION_SECRET` | Forbidden | Required alternative | Production session secret alias. |
| `MINIAPP_URL_DEV` | Optional | Forbidden | Development Mini App URL. |
| `MINIAPP_URL_PROD` | Forbidden | Optional (preferred) | Production Mini App URL. |
| `MINIAPP_URL` | Forbidden | Optional alternative | Production Mini App URL alias. |
| `PORT` | Optional | Optional | API port (default `5000`). |

## Safety rules enforced by runtime

1. Exactly one token variable must be set for the selected environment.
2. If multiple aliases are set (even same value), startup fails.
3. If development is selected and production token vars are set, startup fails.
4. Runtime logs report environment mode + token source variable.
5. Development sticker packs use a `devstix_` namespace to stay visually distinct.

## Integration-only / future variables

The following variables are referenced only by planning docs or future integrations, not by runtime boot:
- `REPLIT_DOMAINS` (legacy miniapp host inference fallback in menu rendering)
