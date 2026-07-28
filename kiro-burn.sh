#!/usr/bin/env bash
# kiro-burn.sh — drive the Kiro CLI headlessly through .kiro/specs/bruma/tasks.md,
# one numbered task at a time, committing after each.
#
#   ./kiro-burn.sh                 # run every unchecked task, in order
#   ./kiro-burn.sh --max 5         # run at most 5 tasks then stop
#   ./kiro-burn.sh --from 12       # skip ahead to task 12
#   ./kiro-burn.sh --only 7        # run exactly one task
#   ./kiro-burn.sh --skip 10,44    # never invoke these (owner-gated, see BLOCKERS.md)
#   ./kiro-burn.sh --dry-run       # print what would run, call nothing, spend nothing
#
# Auth: a browser login (`kiro-cli login`) is enough — verified on kiro-cli
# 2.15.0, which runs --no-interactive on the login token alone. KIRO_API_KEY is
# therefore optional; if set (directly or via an op:// reference in
# KIRO_API_KEY_REF) it is passed through, and it is never printed or committed.

set -uo pipefail

# macOS has no coreutils `timeout`. Fall back to gtimeout, then to a perl alarm,
# so the per-task ceiling is real everywhere rather than an rc=127 on every task.
if command -v timeout >/dev/null 2>&1; then
  run_capped() { timeout "$@"; }
elif command -v gtimeout >/dev/null 2>&1; then
  run_capped() { gtimeout "$@"; }
else
  run_capped() { local s="$1"; shift; perl -e 'alarm shift; exec @ARGV' "$s" "$@"; }
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO" || exit 1

# Which spec to walk. Every repo in the burn keeps its own under .kiro/specs/.
SPEC_DIR="${SPEC_DIR:-$(ls -d .kiro/specs/*/ 2>/dev/null | head -1 | sed 's:/$::')}"
[ -n "$SPEC_DIR" ] || SPEC_DIR=".kiro/specs/unknown"
TASKS="$SPEC_DIR/tasks.md"
LOG_DIR="logs"
STAMP="$(date +%Y%m%dT%H%M%S)"
RUN_LOG="$LOG_DIR/burn-$STAMP.log"
PROGRESS="$LOG_DIR/progress.tsv"

# Per-task wall-clock ceiling. A task that runs longer than this is almost
# certainly stuck in a loop and burning credits for nothing.
TASK_TIMEOUT="${TASK_TIMEOUT:-2700}"   # 45 min

# The service rate-limits requests independently of the credit balance. These
# control how long to wait it out before giving up on a task.
RATE_LIMIT_COOLDOWN="${RATE_LIMIT_COOLDOWN:-120}"
RATE_LIMIT_RETRIES="${RATE_LIMIT_RETRIES:-4}"

MAX_TASKS=0
FROM_TASK=0
ONLY_TASK=0
DRY_RUN=0
SKIP_TASKS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --max)     MAX_TASKS="$2"; shift 2 ;;
    --from)    FROM_TASK="$2"; shift 2 ;;
    --only)    ONLY_TASK="$2"; shift 2 ;;
    --skip)    SKIP_TASKS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

# A task that needs a credential or a provisioned external resource cannot be
# implemented, only blocked — and finding that out costs a full task's credits
# (task 5 spent 3.97 to produce a blocker). Skipping is cheaper and just as
# honest, provided the reason is written into BLOCKERS.md instead.
is_skipped() {
  case ",${SKIP_TASKS}," in
    *",$1,"*) return 0 ;;
    *) return 1 ;;
  esac
}

mkdir -p "$LOG_DIR"
log() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$RUN_LOG"; }
die() { log "FATAL: $*"; exit 1; }

# ---------------------------------------------------------------- preflight
[ -f "$TASKS" ] || die "missing $TASKS"
git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repo"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$BRANCH" = "main" ] && die "refusing to run on main. git switch -c build/kiro-spec-burn"

# A dry run touches neither the CLI nor the key, so it stays runnable before setup.
if [ "$DRY_RUN" = 0 ]; then
  command -v kiro-cli >/dev/null 2>&1 || die "kiro-cli not on PATH. Install: curl -fsSL https://cli.kiro.dev/install | bash"

  # Browser login is sufficient — verified on 2.15.0. An API key is only an
  # alternative credential, so it is passed through when present, never required.
  WHOAMI="$(kiro-cli user whoami 2>/dev/null)"
  printf '%s' "$WHOAMI" | grep -qi 'logged in' \
    || die "kiro-cli is not logged in. Run: kiro-cli login --license free"

  # The CLI can be signed in to a DIFFERENT account than the one holding the
  # credits, and nothing in its output says so — the burn just runs, succeeds,
  # and spends someone else's balance while the dashboard never moves. This
  # happened on 2026-07-28: `--use-device-flow` bound an AWS Builder ID
  # (founder@hostcasa.app) instead of the Google account that owns Kiro Pro.
  CLI_ACCOUNT="$(printf '%s' "$WHOAMI" | sed -n 's/^Email: *//p' | head -1)"
  log "account   ${CLI_ACCOUNT:-unknown} ($(printf '%s' "$WHOAMI" | sed -n 's/^Logged in with *//p' | head -1))"
  if [ -n "${KIRO_EXPECTED_ACCOUNT:-}" ] && [ "$CLI_ACCOUNT" != "$KIRO_EXPECTED_ACCOUNT" ]; then
    die "wrong account: kiro-cli is signed in as '${CLI_ACCOUNT:-none}', expected '$KIRO_EXPECTED_ACCOUNT'.
       Fix with:  kiro-cli logout && kiro-cli login --license free
       (plain browser login picks up the Google session; --use-device-flow
        binds AWS Builder ID instead, which is a different identity.)"
  fi

  if [ -z "${KIRO_API_KEY:-}" ] && [ -n "${KIRO_API_KEY_REF:-}" ]; then
    KIRO_API_KEY="$(op read "$KIRO_API_KEY_REF" 2>/dev/null)" \
      || die "op read failed for \$KIRO_API_KEY_REF (is 1Password unlocked?)"
    export KIRO_API_KEY
  fi

  # Hard money guard. With overages on, the run does not stop at the plan cap —
  # it keeps going and starts charging, up to overageCap. Never burn like that.
  [ -x ./kiro-usage.sh ] || die "missing ./kiro-usage.sh — the overage guard cannot run"
  USAGE_BEFORE="$(./kiro-usage.sh 2>&1)" || die "overage guard: $USAGE_BEFORE"
  case "$USAGE_BEFORE" in
    *overages=DISABLED*) : ;;
    *) die "overage guard: overages are not DISABLED. Turn them off at
       https://app.kiro.dev/settings/account before burning.
       $USAGE_BEFORE" ;;
  esac
fi

log "repo      $REPO"
log "branch    $BRANCH"
log "spec      $TASKS"
if [ -n "${KIRO_API_KEY:-}" ]; then
  log "auth      api key (${#KIRO_API_KEY} chars, value never logged)"
else
  log "auth      browser login (no api key needed)"
fi
log "timeout   ${TASK_TIMEOUT}s per task"
[ "$DRY_RUN" = 1 ] && log "MODE      dry run — no credits will be spent"

# Credit snapshot. /usage exists only in the interactive REPL, so this reads the
# same Get-Usage-Limits API the IDE account dashboard reads. Never blocks the run.
snapshot_credits() {
  local when="$1" out
  [ "$DRY_RUN" = 1 ] && { log "credits ($when): skipped in dry run"; return 0; }
  if out="$(./kiro-usage.sh 2>&1)"; then
    log "credits ($when): $out"
  else
    log "credits ($when): unavailable — $out"
  fi
}

# ------------------------------------------------------------ task selection
# Top-level tasks look like:  - [ ] 12. Implement the streaming Turn Pipeline
task_numbers() { grep -nE '^- \[ \] [0-9]+\.' "$TASKS" | sed -E 's/^([0-9]+):- \[ \] ([0-9]+)\..*/\2/'; }
task_title()   { grep -E "^- \[[ x]\] $1\. " "$TASKS" | head -1 | sed -E "s/^- \[[ x]\] $1\. //"; }
is_done()      { grep -qE "^- \[x\] $1\. " "$TASKS"; }

TOTAL_ALL="$(grep -cE '^- \[[ x]\] [0-9]+\.' "$TASKS")"
log "spec has $TOTAL_ALL numbered tasks; $(task_numbers | wc -l | tr -d ' ') still open"

[ -f "$PROGRESS" ] || printf 'ts\ttask\tstatus\tseconds\ttitle\n' > "$PROGRESS"

# ------------------------------------------------------------------- the burn
snapshot_credits before

RAN=0
STARTED_ALL="$(date +%s)"

for N in $(task_numbers); do
  [ "$ONLY_TASK" != 0 ] && [ "$N" != "$ONLY_TASK" ] && continue
  [ "$N" -lt "$FROM_TASK" ] && continue
  if is_skipped "$N"; then
    log "task $N SKIPPED by --skip (owner-gated; see docs/BLOCKERS.md)"
    continue
  fi
  [ "$MAX_TASKS" != 0 ] && [ "$RAN" -ge "$MAX_TASKS" ] && { log "hit --max $MAX_TASKS"; break; }

  TITLE="$(task_title "$N")"
  log "──────────────────────────────────────────────────────────"
  log "task $N: $TITLE"

  PROMPT="You are implementing the spec in $SPEC_DIR in this repository.

Read these three files first, in full:
  $SPEC_DIR/requirements.md
  $SPEC_DIR/design.md
  $SPEC_DIR/tasks.md

Implement EXACTLY ONE task: task number $N — \"$TITLE\".
Do not start, scaffold, or refactor toward any other numbered task.

Rules (also in .kiro/steering/, follow them):
  - Satisfy the requirement IDs listed on that task's _Requirements:_ line.
  - Write or update tests for the code you write, and make them pass.
  - Never deploy to production and never run a migration against a remote
    database. Local and dry-run only.
  - Never write a real credential into any file. Reference secrets by op:// path
    or variable name only.
  - If the task is blocked on a credential, an external resource that must be
    provisioned by the owner, or a decision you cannot make, then: append the
    blocker to docs/BLOCKERS.md with the task number and exactly what is
    missing, leave the checkbox unchecked, and stop. Do not fake it.
  - When and only when the task is genuinely implemented and its tests pass,
    edit $SPEC_DIR/tasks.md and change '- [ ] $N.' to '- [x] $N.'.

Finish by printing a 3-line summary: what you built, which files changed, and
whether task $N is DONE or BLOCKED."

  if [ "$DRY_RUN" = 1 ]; then
    log "dry run — would invoke kiro-cli for task $N"
    RAN=$((RAN+1))
    continue
  fi

  # The service enforces a requests-per-window rate limit that is separate from
  # the credit balance: it reports "Request quota exceeded. Please wait a
  # moment" while the plan still has hundreds of credits left. That is transient
  # — wait it out and re-run the task rather than ending the burn.
  T0="$(date +%s)"
  ATTEMPT=1
  GAVE_UP_TRANSIENT=0
  while :; do
    MARK="$(wc -c < "$RUN_LOG")"
    run_capped "$TASK_TIMEOUT" kiro-cli chat \
        --no-interactive \
        --trust-all-tools \
        "$PROMPT" 2>&1 | tee -a "$RUN_LOG"
    RC="${PIPESTATUS[0]}"

    # Only look at output produced by THIS attempt, so a rate-limit notice from
    # an earlier task cannot re-trigger the backoff forever.
    THIS_ATTEMPT="$(tail -c "+$((MARK+1))" "$RUN_LOG")"

    # The CLI exits 0 even when the service throttles it — it just prints the
    # notice and stops early. So the retry must key on the message, never on RC.
    # Transient transport failures get the same treatment: on this Mac NordVPN
    # runs tunnels at 1000-1420 MTU, and a large request body comes back as
    # "dispatch failure" against runtime.us-east-1.kiro.dev.
    if printf '%s' "$THIS_ATTEMPT" | grep -qiE 'request quota exceeded|rate limit|too many requests|throttl'; then
      REASON="a rate limit"
    elif printf '%s' "$THIS_ATTEMPT" | grep -qiE 'dispatch failure|having trouble responding|error sending request for url'; then
      REASON="a transport failure"
    else
      break
    fi
    if [ "$ATTEMPT" -ge "$RATE_LIMIT_RETRIES" ]; then
      log "task $N still failing on $REASON after $RATE_LIMIT_RETRIES attempts — giving up on this task"
      GAVE_UP_TRANSIENT=1
      break
    fi
    log "task $N hit $REASON (attempt $ATTEMPT/$RATE_LIMIT_RETRIES) — waiting ${RATE_LIMIT_COOLDOWN}s"
    sleep "$RATE_LIMIT_COOLDOWN"
    ATTEMPT=$((ATTEMPT+1))
  done
  T1="$(date +%s)"
  ELAPSED=$((T1-T0))

  # 124 = GNU timeout; 142 = killed by SIGALRM from the perl fallback.
  if [ "$RC" = 124 ] || [ "$RC" = 142 ]; then
    STATUS="timeout"
    log "task $N TIMED OUT after ${ELAPSED}s — stopping so it stops burning credits"
  elif [ "$RC" != 0 ]; then
    STATUS="error(rc=$RC)"
    log "task $N exited rc=$RC after ${ELAPSED}s"
  elif is_done "$N"; then
    STATUS="done"
    log "task $N DONE in ${ELAPSED}s"
  elif [ "${GAVE_UP_TRANSIENT:-0}" = 1 ]; then
    # Not a blocker. Nothing is missing and no owner action is owed — the service
    # simply would not answer. The checkbox stays open and a later pass retries.
    # Calling this "blocked" would report a throttle as an owner-gated dependency
    # and put work in the blockers list that nobody needs to act on.
    STATUS="transient"
    log "task $N gave up after ${ELAPSED}s on $REASON — retries on the next pass"
  else
    STATUS="blocked"
    log "task $N finished in ${ELAPSED}s but checkbox still open → treating as BLOCKED"
  fi

  printf '%s\t%s\t%s\t%s\t%s\n' "$(date +%FT%T)" "$N" "$STATUS" "$ELAPSED" "$TITLE" >> "$PROGRESS"

  # Commit whatever the task produced, so nothing is lost if we stop here.
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -q -m "task $N: $TITLE

status: $STATUS (${ELAPSED}s)
Implemented by Kiro CLI from .kiro/specs/bruma/tasks.md." \
      && log "committed $(git rev-parse --short HEAD)"
  else
    log "no file changes to commit for task $N"
  fi

  RAN=$((RAN+1))

  # Real credit exhaustion — stop. A transient rate limit is NOT this; it is
  # retried above and must not end the burn while the plan still has credits.
  if tail -60 "$RUN_LOG" | grep -qiE 'insufficient credit|out of credits|payment required|monthly limit|subscription (expired|required)'; then
    log "STOPPING: the CLI reported credit exhaustion. Check https://app.kiro.dev/settings/account"
    break
  fi
  [ "$STATUS" = "timeout" ] && break
done

ELAPSED_ALL=$(( $(date +%s) - STARTED_ALL ))
snapshot_credits after

log "──────────────────────────────────────────────────────────"
log "ran $RAN task(s) in ${ELAPSED_ALL}s"
log "remaining open: $(task_numbers | wc -l | tr -d ' ') of $TOTAL_ALL"
log "progress: $PROGRESS"
log "full log: $RUN_LOG"
