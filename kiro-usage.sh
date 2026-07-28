#!/usr/bin/env bash
# kiro-usage.sh — print the real Kiro credit balance and overage status.
#
# The CLI only exposes /usage inside the interactive REPL, so this reads the
# same data the IDE account dashboard reads: GET /Get-Usage-Limits on the Kiro
# management API, authenticated with the desktop auth token already on disk.
#
#   ./kiro-usage.sh          # human-readable line
#   ./kiro-usage.sh --json   # raw response
#
# Reads the token from ~/.aws/sso/cache/kiro-auth-token.json. Never prints it.

set -uo pipefail
exec python3 - "$@" <<'PY'
import json, sys, urllib.request, urllib.error, urllib.parse, datetime, pathlib, time, random

TOKEN = pathlib.Path.home() / ".aws/sso/cache/kiro-auth-token.json"
API = "https://management.us-east-1.kiro.dev/Get-Usage-Limits"

try:
    tok = json.loads(TOKEN.read_text())
except FileNotFoundError:
    sys.exit(f"no auth token at {TOKEN} — open Kiro.app and sign in")

expires = tok.get("expiresAt", "")
if expires and expires < datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"):
    print(f"warning: desktop token expired at {expires}; open Kiro.app to refresh", file=sys.stderr)

req = urllib.request.Request(
    API + "?" + urllib.parse.urlencode({"profileArn": tok["profileArn"]}),
    headers={
        "Authorization": "Bearer " + tok["accessToken"],
        "Accept": "application/json",
    },
)

# Several burns run at once and each checks the balance in preflight and around
# every task, so this endpoint gets bursty and answers 429. A throttled read says
# nothing about the account — retry rather than let a burn die on it.
body = None
last = ""
for attempt in range(5):
    try:
        body = urllib.request.urlopen(req, timeout=30).read().decode()
        break
    except urllib.error.HTTPError as e:
        last = f"{e.code} from Get-Usage-Limits: {e.read().decode(errors='replace')[:200]}"
        if e.code not in (429, 500, 502, 503, 504):
            sys.exit(last)
    except Exception as e:                      # transport hiccup, same treatment
        last = f"{type(e).__name__}: {e}"
    time.sleep(2 * (attempt + 1) + random.random())

if body is None:
    sys.exit(last)

if "--json" in sys.argv:
    print(json.dumps(json.loads(body), indent=2))
    raise SystemExit

d = json.loads(body)
status = d.get("overageConfiguration", {}).get("overageStatus", "UNKNOWN")
plan = d.get("subscriptionInfo", {}).get("subscriptionTitle", "?")
reset = datetime.datetime.fromtimestamp(d["nextDateReset"], datetime.timezone.utc).date()

for b in d.get("usageBreakdownList", []):
    if b.get("resourceType") != "CREDIT":
        continue
    used, cap = b["currentUsageWithPrecision"], b["usageLimitWithPrecision"]
    print(
        f"plan={plan}  used={used:.2f}/{cap:.0f}  remaining={cap - used:.2f}  "
        f"overages={status}  overage_rate=${b['overageRate']}/credit  "
        f"overage_charges=${b['overageCharges']:.2f}  resets={reset}"
    )

if status != "DISABLED":
    print("WARNING: overages are not DISABLED — a runaway burn can incur charges", file=sys.stderr)
    raise SystemExit(2)
PY
