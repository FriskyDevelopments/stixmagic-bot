# STIX MΛGIC Creator Forge Blueprint

## 1) System Architecture Diagram (textual)

```text
[Telegram User / Web User]
        |
        v
 apps/bot (Telegram runtime) -------> services/api (Flask Creator API)
        |                                       |
        |                                       +--> creator_* SQLite tables (users/workspaces/projects/artifacts/drafts)
        |                                       +--> feature flags + env gates
        |                                       +--> admin/debug endpoints
        |
        +-------------------------------> services/sticker-engine (mask/effect rendering)
                                                |
                                                +--> pack/publish output + previews

apps/web (Creator Mini App)
  Step UI: Forge -> Shape -> Enchant -> Preview -> Save Draft -> Publish
  calls /api/creator/* endpoints, stores local optimistic state

Background Worker
  scripts/creator_cleanup_worker.py (planned)
  runs TTL cleanup against creator_drafts.expires_at
```

## 2) Database Schema (tables + fields)

Implemented in `infra/db.py` via `init_db()`:

- `creator_users`
  - `id` (PK)
  - `telegram_user_id` (UNIQUE)
  - `display_name`
  - `created_at`, `updated_at`
- `creator_workspaces`
  - `id` (PK)
  - `owner_user_id` (FK -> creator_users.id)
  - `name`, `visibility`
  - `created_at`, `updated_at`
- `creator_projects`
  - `id` (PK)
  - `workspace_id` (FK)
  - `owner_user_id` (FK)
  - `name`, `status`
  - `created_at`, `updated_at`
- `creator_artifacts`
  - `id` (PK)
  - `project_id`, `owner_user_id` (FK)
  - `name`
  - `source_media_path`
  - `mask_config` (JSON text)
  - `effect_config` (JSON text)
  - `spell_slot` (JSON text, reserved future hook)
  - `permission_scope`
  - `publication_state`, `published_at`
  - `created_at`, `updated_at`
- `creator_drafts`
  - `id` (draft token, PK)
  - `project_id`, `artifact_id`, `owner_user_id` (FK)
  - `stage`
  - `payload` (JSON text)
  - `expires_at` (TTL)
  - `created_at`, `updated_at`, `published_at`

## 3) API Surface (routes + responsibilities)

Implemented in `api.py`:

- `GET /api/creator/flags`
  - public, exposes forge feature state
- `GET /api/debug/creator/flags`
  - API-key protected environment + flags view
- `GET /api/creator/flow`
  - returns canonical 6-step forge flow definition
- `POST /api/creator/drafts`
  - starts a new forge draft (user/workspace/project/artifact bootstrap)
- `GET /api/creator/drafts/<draft_id>`
  - returns current draft state
- `PATCH /api/creator/drafts/<draft_id>`
  - updates stage + payload (`shape`, `enchant`, etc.)
- `POST /api/creator/drafts/<draft_id>/publish`
  - transitions draft/artifact to published state
- `POST /api/admin/creator/cleanup`
  - API-key admin endpoint for TTL draft cleanup

## 4) Creator Flow Mapping (UI + API + state transitions)

1. **Forge**
   - UI: upload/import panel
   - API: `POST /api/creator/drafts`
   - state: `start`
2. **Shape**
   - UI: mask controls
   - API: `PATCH /api/creator/drafts/<id>` with `stage=shape`
   - state: `shape`
3. **Enchant**
   - UI: effect controls + presets
   - API: `PATCH ...` with `stage=enchant`
   - state: `enchant`
4. **Preview**
   - UI: artifact preview canvas
   - API: `PATCH ...` with `stage=preview`
   - state: `preview`
5. **Save Draft**
   - UI: save confirmation / auto-save signal
   - API: `PATCH ...` with `stage=save_draft`
   - state: `save_draft`
6. **Publish**
   - UI: final CTA + success sheet
   - API: `POST /api/creator/drafts/<id>/publish`
   - state: `publish` + `publication_state=published`

## 5) Storytelling / Copy System (STIX Voice)

Tone: controlled magic, precise, no roleplay.

### Onboarding
- Header: **Forge your first artifact**
- Subtext: **Start with a source image or clip. Then shape, enchant, and publish.**
- CTA: **Start Forge**

### Empty states
- No drafts: **No active forges yet. Start one and we’ll keep it warm.**
- No artifacts: **Your forge is ready. Shape your first artifact.**

### Success
- Draft saved: **Draft sealed. Your forge state is safe.**
- Published: **Artifact published. It’s now live in your pack.**

### Errors
- Upload failed: **Source couldn’t be forged. Try a new file.**
- Invalid mask: **Shape step failed. Adjust your mask edges and retry.**
- Effect conflict: **Enchant step has conflicting effects. Remove one and continue.**
- Publish blocked: **Publish is locked by feature flag in this environment.**

### Core CTAs
- **Start Forge**
- **Shape Artifact**
- **Apply Enchantments**
- **Preview Artifact**
- **Save Draft**
- **Publish Artifact**

## 6) Monorepo Structure (target)

```text
apps/
  web/                 # Creator UI (TypeScript, React/Vite or Next)
  bot/                 # Telegram runtime
services/
  api/                 # Creator + catalog API
  sticker-engine/      # Render, mask, effect pipelines
packages/
  types/               # Shared DTOs + stage enums
  config/              # Shared env + feature flag loader
  ui/                  # Shared STIX components + copy tokens
```

NodeNext hygiene recommendation:
- set explicit `"type": "module"` at package boundary where needed
- use explicit extensioned imports in emitted JS (`.js`)
- centralize tsconfig base in `packages/config/tsconfig.base.json`

## 7) Dev Setup Instructions

Environment variables added in `config/runtime.py`:

- `FEATURE_CREATOR_ENABLED_<ENV>` / fallback `FEATURE_CREATOR_ENABLED`
- `FEATURE_CREATOR_SHAPE_<ENV>` / fallback `FEATURE_CREATOR_SHAPE`
- `FEATURE_CREATOR_ENCHANT_<ENV>` / fallback `FEATURE_CREATOR_ENCHANT`
- `FEATURE_CREATOR_PUBLISH_<ENV>` / fallback `FEATURE_CREATOR_PUBLISH`
- `CREATOR_DRAFT_TTL_HOURS_<ENV>` / fallback `CREATOR_DRAFT_TTL_HOURS`

Local steps:
1. Set `APP_ENV=development`.
2. Set existing bot/API secrets.
3. Enable creator flags (`=1`) and TTL (for example `72`).
4. Run app startup path that calls `infra.db.init_db()`.
5. Use API key to create/update/publish drafts.
6. Schedule TTL cleanup through admin endpoint or periodic worker.

Seed/test artifacts:
- create draft via `POST /api/creator/drafts` with `owner_user_id`, `project_name`, `artifact_name`
- patch payloads per step to simulate end-to-end forge states

Logging strategy:
- cleanup function logs `creator.cleanup_deleted=<count>`
- recommended next step: add structured request logs with route + draft_id + stage transition

## 8) Future hooks for Spell System

Reserved with `creator_artifacts.spell_slot` JSON field.

Suggested schema inside `spell_slot`:

```json
{
  "spell_id": null,
  "version": 1,
  "params": {},
  "safety_profile": "default",
  "status": "inactive"
}
```

Upgrade path:
- introduce `creator_spells` registry table
- validate `spell_slot.spell_id` against registry
- add execution queue in `services/sticker-engine`

---

**Forge principle:** the creator is staged, stateful, and expressive by design — never a generic upload form.
