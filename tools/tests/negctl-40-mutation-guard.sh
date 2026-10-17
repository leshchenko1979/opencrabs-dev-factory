#!/usr/bin/env bash
# Mutation guard for #40 — prove the Leg R selftest legs are LIVE.
#
# #40: a ported bare `#N` is a LIE upstream. The fork and upstream are different
# number spaces, so upstream autolinks the number to whatever issue happens to
# hold it there: DEAD when nothing does (#86, #116, #350, #352, #396 — 43 lines
# already shipped in upstream src), COLLISION when an unrelated issue does
# (fork #490 notify-tail-loss vs upstream #490 narration-leak). Leg R enforces
# the qualified form on the port's added lines, commit subjects and trailers.
#
# TWO ARMS, because the feature has two independent halves and one mutant can
# only reach one of them:
#   ARM A — remove the HEX EXCLUSION. The TUI theme packs carry colour literals
#           such as #86e1fc, which a naive #N matcher reads as a ref to #86 and
#           reports as 4 phantom violations (measured 2026-10-17: 3 in
#           tokyonight.toml, 1 in the json fixture). A matcher that cries wolf on
#           a colour table gets switched off — which is how the leak survived.
#           Must redden ONLY `leg-R hex-control`; the arms leg must SURVIVE,
#           because its fixture carries no colour literal.
#   ARM B — drop the DIFF row from the case dispatch. Must redden ONLY
#           `leg-R arms` (its finding count falls 3 -> 2); the hex control and
#           both cache arms must survive.
#
# ASSERTION SHAPE — oc-harvest-sweep's selftest writes its FAIL lines to STDERR
# (every capture below is `2>&1`), and each names its own token, so the guard
# convicts a NAMED leg rather than counting a red run. It ALSO asserts the exact
# pass-count drop: a token test alone cannot distinguish a leg that FAILED from a
# leg that was DELETED, and deleting a leg produces no FAIL line at all.
#
# Standalone by design — the negctl-* family is not wired into tools/tests/run.sh;
# it is run deliberately when the legs it guards change.
#
# Harness guards (AGENTS.md §Repro harnesses): explicit tool path, recursion
# guard, process budget cap, timeout.
set -u
[ "${OC_REPRO_DEPTH:-0}" -ge 1 ] && exit 99
export OC_REPRO_DEPTH=1
ulimit -u $(( $(ps -e --no-headers | wc -l) + 200 )) 2>/dev/null || true

SKILL_DIR="/root/.opencrabs/profiles/ops/skills/opencrabs-dev"
#: SRC is overridable so this guard can be pointed at a DELIBERATELY REVERTED
#: tree (OC_NEGCTL_SRC=...) and shown to exit non-zero — i.e. shown to detect a
#: real regression, not only to convict its own internal mutant.
SRC="${OC_NEGCTL_SRC:-$SKILL_DIR/tools}"
TOOL_REL="harvest/oc-harvest-sweep"
export OC_TOOLS_NOLOG=1 OC_NO_FLOODGUARD=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #40 mutation guard (fork-ref enforcement, Leg R) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "selftest OK: N/M legs"
  sed -n 's/^selftest OK: \([0-9][0-9]*\)\/.*/\1/p' "$1" | tail -1
}

# --- non-vacuity: the pristine tree must CARRY the legs the mutant reddens ---
# A renamed or deleted leg disarms the guard silently, so assert presence first.
for tok in 'leg-R arms' 'leg-R hex-control' 'leg-R no-cache' 'leg-R stale-set'; do
  grep -qF "FAIL $tok" "$SRC/$TOOL_REL" \
    && ok "baseline carries the '$tok' leg" \
    || bad "the '$tok' leg is MISSING from oc-harvest-sweep — the guard would be vacuous"
done
grep -qF 'fr4.toml' "$SRC/$TOOL_REL" \
  && ok "baseline carries the hex-literal control fixture" \
  || bad "the hex-literal control fixture is MISSING — ARM A would be vacuous"
grep -qF 'post !~ /^[0-9a-fA-F]$/' "$SRC/$TOOL_REL" \
  && ok "baseline carries the hex exclusion" \
  || bad "the hex exclusion is MISSING from the scan — nothing for ARM A to remove"

# --- baseline ----------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_b="$(run_st "$WORK/base/$TOOL_REL" "$WORK/base.out")"
n_b="$(passed_of "$WORK/base.out")"

[ "$rc_b" = 0 ] && ok "baseline oc-harvest-sweep GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-harvest-sweep rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# --- ARM A: remove the hex exclusion ----------------------------------------
mutate_hex() {  # mutate_hex <tools-tree> -> rc 0 on success
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = "post !~ /^[0-9a-fA-F]$/ && "
n = src.count(needle)
if n != 2:
    sys.stderr.write("mutation: %d hex-exclusion sites, need exactly 2\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, ""))
PYEOF
}

arm() {  # arm <name> <mutator> <expect-red-token> <expect-green-token>...
  local name="$1" mutator="$2" red="$3"; shift 3
  local mut="$WORK/mut-$name"
  cp -a "$SRC" "$mut" || { bad "[$name] could not copy the tools tree"; return; }
  if ! "$mutator" "$mut" 2>"$WORK/$name.err"; then
    bad "[$name] could not apply the mutation — guard is inert ($(cat "$WORK/$name.err"))"
    return
  fi
  if cmp -s "$SRC/$TOOL_REL" "$mut/$TOOL_REL"; then
    bad "[$name] mutant tool is byte-identical to the pristine one — no-op mutation"
    return
  fi
  ok "[$name] mutant applied ($(cmp -l "$SRC/$TOOL_REL" "$mut/$TOOL_REL" 2>/dev/null | wc -l) differing bytes)"
  local rc_m n_m
  rc_m="$(run_st "$mut/$TOOL_REL" "$WORK/$name.out")"
  n_m="$(passed_of "$WORK/$name.out")"
  [ "$rc_m" = 0 ] && bad "[$name] mutant selftest PASSED (rc=0) — the legs do not catch this regression" \
                  || ok "[$name] mutant selftest RED (rc=$rc_m)"
  grep -qF "FAIL $red" "$WORK/$name.out" \
    && ok "[$name] named leg '$red' reddened" \
    || bad "[$name] '$red' did NOT redden — that leg is decoration"
  for tok in "$@"; do
    grep -qF "FAIL $tok" "$WORK/$name.out" \
      && bad "[$name] control '$tok' reddened — it is not mutation-independent" \
      || ok "[$name] control '$tok' survived (mutation-independent)"
  done
  if [ -n "$n_b" ] && [ -n "$n_m" ]; then
    local drop=$(( n_b - n_m ))
    if [ "$drop" -eq 1 ]; then
      ok "[$name] CAUGHT — pass-count dropped by exactly 1 ($n_b -> $n_m)"
    else
      bad "[$name] pass-count dropped by $drop ($n_b -> $n_m), expected 1 — a leg is decoration or another leg is coupled"
    fi
  else
    bad "[$name] could not measure the drop (baseline='$n_b' mutant='$n_m')"
  fi
}

mutate_diag() {  # mutate_diag <tools-tree> -> drop the DIFF row from the dispatch
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = "      DIFF) echo -e "
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d DIFF dispatch arms, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, "      DIFFX) echo -e "))
PYEOF
}

arm hex mutate_hex 'leg-R hex-control' 'leg-R arms' 'leg-R stale-set'
arm diag mutate_diag 'leg-R arms' 'leg-R hex-control' 'leg-R no-cache' 'leg-R stale-set'

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — Leg R reddens under both mutants and the pristine tree stays green"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
