#!/usr/bin/env bash
# Mutation guard for factory #39 — prove the --test-threads legs are LIVE.
#
# #39 (ASK from the lane "Telegram: Rich Text", 2026-10-15): oc-ship-chain had
# no way to hand libtest's `--test-threads N` to the LEG1 gate it dispatches, so
# the #1936 Stage-1 hang mitigation was UNREACHABLE through the chain — every
# fresh LEG1 dispatch was a coin flip. Measured, same turn: carrier run
# 38799188468 was CANCELLED at 2717 s against ci-lane-impl.yml's own
# `timeout-minutes: 45` (2700 s), its log carrying 3,971 `ok` lines and
# `running 10805 tests` — the gate had no thread cap to ask for.
#
# The fix adds --test-threads / OC_SHIPCHAIN_TEST_THREADS and nine selftest
# legs. THIS guard is the evidence that those legs are LIVE: a leg that cannot
# fail under a mutant which removes the behaviour it claims to test is
# decoration, and decoration is worse than no leg at all because it reads as
# coverage.
#
# TWO ARMS, because the feature has two independent halves and one mutant can
# only reach one of them:
#
#   ARM A — always-append (hardcoded default):
#     the ABSENCE control must redden. The inline comment above the legs calls
#     it load-bearing for exactly this reason: without it, a mutant that always
#     appends (a hardcoded default, say) passes the forward leg VACUOUSLY.
#     Expected drop: 1 leg (test-threads/absent).
#   ARM B — the forwarding line DISABLED:
#     the three FORWARDING legs must redden. This is the feature's CORE — the
#     flag has to actually reach the dispatch. Expected drop: 3 legs
#     (forwarded, journal-resolved-argv, env).
#
# Each arm also asserts the legs INDEPENDENT of its mutation SURVIVE it, so a
# mutant that simply broke the whole verb cannot be mistaken for a catch.
#
# ASSERTION SHAPE: oc-ship-chain's selftest defines
#   bad() { FAIL=$((FAIL+1)); echo "FAIL $1"; }        # STDOUT — not stderr
# (oc-ledger, guarded by negctl-38, writes its FAIL lines to STDERR; the two
# guards are NOT interchangeable). Every failing leg therefore names itself on
# stdout as `FAIL <token>`, and each of the nine new legs carries a
# `test-threads/...` token. The assertion is the TOKEN on a FAIL line, not
# merely "rc != 0", so the guard NAMES the regression instead of counting it —
# and the pass-count drop is asserted beside it, because a token test alone
# cannot tell a leg that failed from a leg that never ran.
#
# NO standalone probe: unlike negctl-38 (whose oc-ledger verb is drivable
# directly against a stub `gh`), a chain run needs the full fixture apparatus —
# a fork clone, a pushed branch, fake prchecks/deploy/issuelog bins and the
# freeze override. The selftest's own legs ARE that probe, so this guard drives
# the tool's selftest rather than re-implementing the harness.
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
TOOL_REL="ship/oc-ship-chain"
#: a guard fixture must never append to the shared tools log.
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #39 mutation guard (--test-threads rides the LEG1 dispatch) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "selftest: N passed, M failed"
  grep -Eo 'selftest: [0-9]+ passed' "$1" | tail -1 | awk '{print $2}'
}

reddened() { grep -qF "FAIL $2" "$1"; }

# --- mutation ----------------------------------------------------------------
mutate() {  # mutate <tools-tree> <arm>
  python3 - "$1/$TOOL_REL" "$2" <<'PYEOF'
import sys
path, arm = sys.argv[1], sys.argv[2]
lines = open(path, encoding="utf-8").read().split("\n")
# The ONE line that forwards the flag into LEG1's dispatch argv. Matched on the
# STRIPPED text so the mutation survives an indentation change, and required to
# be UNIQUE: two matches would mean the guard cannot say which it mutated.
needle = '[ -n "$TEST_THREADS" ] && PRCHECKS_CALL+=(--test-threads "$TEST_THREADS")'
hits = [i for i, l in enumerate(lines) if l.strip() == needle]
if len(hits) != 1:
    sys.stderr.write("mutation: %d forwarding lines, need exactly 1\n" % len(hits))
    sys.exit(2)
i = hits[0]
indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
if arm == "A":
    lines[i] = (indent + 'PRCHECKS_CALL+=(--test-threads "${TEST_THREADS:-4}")'
                '  # MUTANT A (factory #39): hardcoded default - ALWAYS appends')
elif arm == "B":
    lines[i] = (indent + 'true'
                '  # MUTANT B (factory #39): the forwarding line is DISABLED - never appends')
else:
    sys.stderr.write("mutation: unknown arm %r\n" % arm)
    sys.exit(2)
open(path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
}

# --- baseline ----------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_b="$(run_st "$WORK/base/$TOOL_REL" "$WORK/base.out")"
n_b="$(passed_of "$WORK/base.out")"

[ "$rc_b" = 0 ] && ok "baseline oc-ship-chain GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-ship-chain rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# The guard is vacuous unless the pristine tree carries the code AND the legs it
# later requires to redden: a renamed or deleted leg would silently disarm it.
grep -qF '[ -n "$TEST_THREADS" ] && PRCHECKS_CALL+=(--test-threads "$TEST_THREADS")' "$SRC/$TOOL_REL" \
  && ok "baseline carries the #39 forwarding line" \
  || bad "the #39 forwarding line is MISSING from oc-ship-chain — the guard would be vacuous"
grep -qF 'OC_SHIPCHAIN_TEST_THREADS needs a non-negative integer' "$SRC/$TOOL_REL" \
  && ok "baseline carries the env shape gate" \
  || bad "the env shape gate is MISSING from oc-ship-chain — the guard would be vacuous"
for leg in test-threads/forwarded test-threads/journal-resolved-argv test-threads/env \
           test-threads/absent test-threads/shape-usage test-threads/inert-carry-green; do
  grep -qF "$leg" "$SRC/$TOOL_REL" \
    && ok "baseline carries leg $leg" \
    || bad "leg $leg is MISSING from oc-ship-chain — the guard would be vacuous"
done

# --- arms --------------------------------------------------------------------
run_arm() {  # run_arm <A|B> <expected_drop>; reads REDDEN[]/SURVIVE[] from scope
  local arm="$1" want_drop="$2" dir="$WORK/mut$1"
  local rc_m n_m drop tok
  echo "--- ARM $arm"
  cp -a "$SRC" "$dir" || { bad "arm $arm: could not copy the tools tree"; return; }
  if ! mutate "$dir" "$arm" 2>"$WORK/mutate$arm.err"; then
    bad "arm $arm: could not apply the mutation — guard is inert ($(cat "$WORK/mutate$arm.err"))"
    return
  fi
  # A no-op mutation would make every assertion below vacuous while still passing.
  if cmp -s "$SRC/$TOOL_REL" "$dir/$TOOL_REL"; then
    bad "arm $arm: mutant is byte-identical to the pristine tool — no-op mutation"
  else
    ok "arm $arm: mutant applied ($(cmp -l "$SRC/$TOOL_REL" "$dir/$TOOL_REL" 2>/dev/null | wc -l) differing bytes)"
  fi
  # A syntactically broken mutant fails EVERY leg, which would read as a huge
  # bogus drop instead of the named regression this guard is measuring.
  bash -n "$dir/$TOOL_REL" 2>"$WORK/syntax$arm.err" \
    && ok "arm $arm: mutant parses (bash -n)" \
    || bad "arm $arm: mutant does not parse — $(head -1 "$WORK/syntax$arm.err")"

  rc_m="$(run_st "$dir/$TOOL_REL" "$WORK/mut$arm.out")"
  n_m="$(passed_of "$WORK/mut$arm.out")"

  [ "$rc_m" = 0 ] && bad "arm $arm: mutant selftest PASSED (rc=0) — the legs do not catch the regression" \
                  || ok "arm $arm: mutant selftest RED (rc=$rc_m)"

  for tok in ${REDDEN[@]+"${REDDEN[@]}"}; do
    reddened "$WORK/mut$arm.out" "$tok" \
      && ok "arm $arm [named] $tok is on a FAIL line under the mutant" \
      || bad "arm $arm [named] $tok did NOT redden — that leg is decoration"
  done
  for tok in ${SURVIVE[@]+"${SURVIVE[@]}"}; do
    reddened "$WORK/mut$arm.out" "$tok" \
      && bad "arm $arm [control] $tok reddened — it is not mutation-independent" \
      || ok "arm $arm [control] $tok survived the mutant"
  done

  if [ -n "$n_b" ] && [ -n "$n_m" ]; then
    drop=$(( n_b - n_m ))
    if [ "$drop" -eq "$want_drop" ]; then
      ok "arm $arm: CAUGHT — pass-count dropped by exactly $drop ($n_b -> $n_m)"
    else
      bad "arm $arm: pass-count dropped by $drop ($n_b -> $n_m), expected $want_drop — either a guarded leg is decoration or another leg is coupled to the emit"
    fi
  else
    bad "arm $arm: could not measure the drop (baseline='$n_b' mutant='$n_m')"
  fi
}

# ARM A: always-append. The absence control is the ONLY leg that may redden — the
# three forward legs pass a value, so appending a default changes nothing they
# assert; they are this arm's mutation-independent controls.
REDDEN=( test-threads/absent )
SURVIVE=( test-threads/forwarded test-threads/journal-resolved-argv test-threads/env \
          test-threads/shape-usage test-threads/inert-carry-green )
run_arm A 1

# ARM B: forwarding disabled. Now the three forward legs ARE the regression and
# the absence control is the one that cannot notice — the inverse of arm A.
REDDEN=( test-threads/forwarded test-threads/journal-resolved-argv test-threads/env )
SURVIVE=( test-threads/absent test-threads/shape-usage test-threads/inert-carry-green )
run_arm B 3

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #39 --test-threads legs fail under their mutants and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
