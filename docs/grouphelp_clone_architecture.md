# STIX MΛGIC GroupHelp Clone: Host + Plugin Forge

## 1) Host System Architecture

### Components
- **Moderation Host (`moderation/host.py`)**
  - Enforces authority model.
  - Owns action registry, policy checks, execution, and audit log.
  - Maintains moderation state (bans, mutes, warnings, message actions).
- **Plugin Bridge (`moderation/plugin.py`)**
  - Receives events from message/reply/admin surfaces.
  - Normalizes event payload into action requests.
  - Passes requests through host policy + execution.
- **Wizard Interpreter (`moderation/wizard.py`)**
  - Converts natural language and contextual shortcuts into normalized action intent.
  - Keeps action resolution UI-agnostic.
- **Dev Harness (`moderation/dev_harness.py`)**
  - Mock users + roles + group simulation.
  - Replayable event stream for deterministic testing.
- **Control Plane Endpoints (`api.py`)**
  - `/api/moderation/dev/state`
  - `/api/moderation/dev/events`
  - `/api/moderation/dev/replay`

### Enforcement Model
1. Event enters bridge.
2. Bridge converts to normalized `ActionRequest`.
3. Host checks:
   - action exists
   - actor role meets requirement
   - target is valid
   - actor cannot act on equal/higher role
   - confirmation token present for high-risk actions
4. Host executes action and writes audit entry.
5. Result returned to wizard/UI layer.

---

## 2) Permission + Action Matrix

| Action | Required Role | Target Rules | Confirmation | Notes |
|---|---|---|---|---|
| `ban_user` | `admin` | member/moderator only; never equal/higher | Yes | Owner still protected by hierarchy check |
| `mute_user` | `moderator` | member only | No | Duration defaults to 600s |
| `warn_user` | `moderator` | member only | No | Warning count increments |
| `delete_message` | `moderator` | member/moderator target context | No | Message ID tracked in state |
| `pin_message` | `moderator` | member/moderator/admin content context | No | Message ID tracked in state |

Role ordering:
- `owner` > `admin` > `moderator` > `member`

---

## 3) Plugin / Bridge Architecture

### Normalized Event Schema
```json
{
  "kind": "message|reply|admin_action",
  "actor_id": 3,
  "actor_role": "moderator",
  "text": "Mute 10m",
  "target_id": 4,
  "target_role": "member",
  "message_id": "12345",
  "confirmation_token": null,
  "metadata": {
    "reason": "spam"
  }
}
```

### Normalized Action Request
```json
{
  "action": "mute_user",
  "actor_id": 3,
  "actor_role": "moderator",
  "target_id": 4,
  "target_role": "member",
  "duration_seconds": 600,
  "ui_source": "reply"
}
```

### Bridge Guarantees
- **Permission pass-through:** host remains final authority.
- **Schema normalization:** UI-specific payloads become policy-ready requests.
- **Error handling:** unknown actor/action/intent returns structured fail result.
- **Observability:** event log + host audit log + replay buffer.

---

## 4) Wizard Interaction Model

### Non-command-first UX surfaces
- Reply actions: “Handle this”, “Mute 10m”, “Warn user”
- Inline contextual actions: delete/pin on message cards
- Admin panel actions: explicit action selectors

### Wizard pipeline
1. Resolve intent from text/selection.
2. Resolve target from reply context/admin panel.
3. Verify actor role and target role.
4. Dispatch to host via bridge.
5. Render result and optional confirmation prompt.

### Confirmation pattern
For risky actions (`ban_user`):
- First dispatch returns `confirmation_required`.
- UI asks operator to confirm.
- Second dispatch includes `confirmation_token: "CONFIRMED"`.

---

## 5) Dev-Test Harness Design

### Included capabilities
- Mock users:
  - owner/admin/moderator/member/member
- Mock group with deterministic IDs
- Event simulator (`simulate_event(payload)`)
- Action testing via API endpoint
- Full state inspection endpoint
- Replay log endpoint for regression/debug

### Example test payload
```json
{
  "kind": "reply",
  "actor_id": 3,
  "text": "Mute 10m",
  "target_id": 4,
  "message_id": "m-1001"
}
```

---

## 6) Deployment Setup (Vercel)

### Runtime approach
- Keep Flask API as control plane.
- Deploy via `@vercel/python` with `api.py` entrypoint.
- Secure dev moderation endpoints behind API key middleware.

### Config
- `vercel.json` routes `/api/*` and root static behavior.
- Env variables:
  - `API_KEY`
  - `SESSION_SECRET`
  - existing bot/runtime vars

---

## 7) End-to-End Example Action Flow

### Scenario: Moderator mutes a member from reply context
1. Moderator taps reply action: **Mute 10m**.
2. UI sends bridge event.
3. Wizard resolves `mute_user` + `duration_seconds=600`.
4. Host validates moderator permission + member target.
5. Host executes mute, stores state and audit entry.
6. UI receives success result and updates thread moderation status.

### Scenario: Admin bans moderator (with confirmation)
1. Admin chooses **Ban user** on moderator target.
2. Host returns `confirmation_required`.
3. UI prompts “Confirm ban?”
4. Admin confirms.
5. Bridge resends with `confirmation_token="CONFIRMED"`.
6. Host executes and logs audit trail.

---

## Design Principle Preserved

**The host is the guard. The wizard is the voice.**

All external UX layers remain advisory/orchestration layers; only the host can authorize and execute moderation actions.
