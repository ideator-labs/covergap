#!/usr/bin/env bash
# CoverGap self-proving demo. SAMPLE / fictional Harbor Print & Cafe data.
# Usage: bash demo.sh [--break]
# --break sabotage CG 40 47 detection so SUMMARY fails (exit 1).
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

BREAK=0
if [ "${1:-}" = "--break" ]; then
  BREAK=1
fi

rm -rf data
mkdir -p data

passed=0
failed=0

record() {
  if [ "$1" -eq 0 ]; then
    echo "$2: PASS"
    passed=$((passed + 1))
  else
    echo "$2: FAIL"
    failed=$((failed + 1))
  fi
}

CLI=(python3 src/cli.py)
FIXTURE=fixtures/harbor_print.json

echo "CoverGap demo. SAMPLE / fictional org: Harbor Print & Cafe."
echo "Join CGL renewal endorsements to AI-use inventory before bind."
echo "Control policy trust_packet never inspects endorsements (all ok_bind)."
echo "Policy covergap flags excluded_ai, narrow_exclude, ask_broker, ok_bind."
echo "as_of from fixture (2026-10-12T09:00:00 local)."
if [ "$BREAK" -eq 1 ]; then
  echo "BREAK MODE: CG 40 47 detection is intentionally skipped on covergap run."
fi
echo

SKIP_CG=()
if [ "$BREAK" -eq 1 ]; then
  SKIP_CG=(--skip-cg4047)
fi

echo "=== trust_packet ==="
"${CLI[@]}" check \
  --fixture "$FIXTURE" \
  --policy trust_packet \
  --out data/trust_packet.json
echo

echo "=== covergap ==="
"${CLI[@]}" check \
  --fixture "$FIXTURE" \
  --policy covergap \
  --out data/covergap.json \
  "${SKIP_CG[@]}"
echo

echo "=== checks ==="

rc=0
python3 - <<'PY' || rc=1
import json
exp = json.load(open("fixtures/expected.json"))["trust_packet"]
run = json.load(open("data/trust_packet.json"))
by = run["primaries"]
ok = (
    by["shop_cafe"] == exp["shop_cafe"]
    and by["shop_salon"] == exp["shop_salon"]
    and by["shop_hvac"] == exp["shop_hvac"]
    and by["shop_bookshop"] == exp["shop_bookshop"]
    and run["exception_count"] == exp["exception_count"]
)
for row in run["flagged"]:
    if row["primary"] != "ok_bind" or row["flags"] != ["ok_bind"]:
        ok = False
print(f"  trust primaries={by} exceptions={run['exception_count']}")
raise SystemExit(0 if ok else 1)
PY
record $rc "CHECK 1 (trust_packet: all primary ok_bind, 0 exceptions)"

rc=0
python3 - <<'PY' || rc=1
import json
exp = json.load(open("fixtures/expected.json"))["covergap"]
run = json.load(open("data/covergap.json"))
by = run["primaries"]
ok = by.get("shop_cafe") == exp["shop_cafe"]
print(f"  cafe primary={by.get('shop_cafe')} expected={exp['shop_cafe']}")
raise SystemExit(0 if ok else 1)
PY
record $rc "CHECK 2 (covergap: cafe primary excluded_ai)"

rc=0
python3 - <<'PY' || rc=1
import json
exp = json.load(open("fixtures/expected.json"))["covergap"]
run = json.load(open("data/covergap.json"))
by = run["primaries"]
ok = by.get("shop_salon") == exp["shop_salon"]
print(f"  salon primary={by.get('shop_salon')} expected={exp['shop_salon']}")
raise SystemExit(0 if ok else 1)
PY
record $rc "CHECK 3 (covergap: salon primary narrow_exclude)"

rc=0
python3 - <<'PY' || rc=1
import json
exp = json.load(open("fixtures/expected.json"))["covergap"]
run = json.load(open("data/covergap.json"))
by = run["primaries"]
ok = by.get("shop_hvac") == exp["shop_hvac"]
print(f"  hvac primary={by.get('shop_hvac')} expected={exp['shop_hvac']}")
raise SystemExit(0 if ok else 1)
PY
record $rc "CHECK 4 (covergap: hvac primary excluded_ai)"

rc=0
python3 - <<'PY' || rc=1
import json
exp = json.load(open("fixtures/expected.json"))["covergap"]
run = json.load(open("data/covergap.json"))
by = run["primaries"]
ok = (
    by.get("shop_bookshop") == exp["shop_bookshop"]
    and run["exception_count"] == exp["exception_count"]
)
book = next(f for f in run["flagged"] if f["shop_id"] == "shop_bookshop")
ok = ok and book["primary"] == "ok_bind"
print(
    f"  bookshop primary={by.get('shop_bookshop')} flags={book['flags']} "
    f"exceptions={run['exception_count']}"
)
raise SystemExit(0 if ok else 1)
PY
record $rc "CHECK 5 (covergap: bookshop ok_bind; 3 exceptions)"

echo
echo "SUMMARY: ${passed} passed, ${failed} failed"
if [ "$failed" -ne 0 ]; then
  exit 1
fi
echo "ALL CLAIMS PASSED"
