#!/usr/bin/env bash
# Mutation guard for factory #39 → RETIRED by factory #181 — prove the
# NON-FORWARDING legs are LIVE.
#
# #39 (2026-10-15): oc-ship gained --test-threads / OC_SHIPCHAIN_TEST_THREADS
# to carry the #1936 Stage-1 hang mitigation into LEG1's dispatch, with nine
# selftest legs and TWO mutants (always-append / forwarding-disabled) proving
# them live. That contract is DEAD: the carrier workflow declares `test_threads`
# and IGNORES it (pr-checks.yml: "RETIRED 2026-11-20 … Accepted and IGNORED —
# read by nothing"; the callee relay was deleted 2026-11-22), so factory #181
# (2026-11-25) removed the forward — the flag is accepted at the boundary,
# noted loudly, and NO dispatch ever carries it again.
#
# A retired input changes what "the legs are live" means: the regression this
# guard must catch is the FORWARD COMING BACK. One mutant, the inverse of the
# old ARM B:
#
#   ARM R — the RETIRED FORWARD RESTORED:
#     the retirement note's journal line is replaced with the old
#     `PRCHECKS_CALL+=(--test-threads "$TEST_THREADS")` append. The three legs
#     that assert the flag does NOT reach the dispatch (not-forwarded,
#     journal-resolved-argv, env) must redden; the absence control (no flag →
#     no append even under the mutant), the shape gate (dies at the boundary
#     before any dispatch) and the carry-path legs (no dispatch there at all)
#     must survive it. Expected drop: 3 legs.
#
# The old always-append arm (ARM A) has no separate identity any more: an
# unconditional append trips the same not-forwarded legs (they pass a value),
# so the absence control is exercised as this arm's SURVIVE control — under a
# restore-when-requested mutant a no-flag call still dispatches nothing.
#
# Each arm also asserts the legs INDEPENDENT of its mutation SURVIVE it, so a
# mutant that simply broke the whole verb cannot be mistaken for a catch.
#
# ASSERTION SHAPE: oc-ship's selftest defines
#   bad() { FAIL=$((FAIL+1)); echo "FAIL $1"; }        # STDOUT — not stderr
# (oc-ledger, guarded by negctl-38, writes its FAIL lines to STDERR; the two
# guards are NOT interchangeable). Every failing leg therefore names itself on
# stdout as `FAIL <token>`, and each leg carries a `test-threads/...` token.
# The assertion is the TOKEN on a FAIL line, not merely "rc != 0", so the guard
# NAMES the regression instead of counting it — and the pass-count drop is
# asserted beside it, because a token test alone cannot tell a leg that failed
# from a leg that never ran.
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
TOOL_REL="ship/oc-ship"
#: The legs live in the selftest BODY, which the T6 split (74244b21) moved
#: out of oc-ship into its own file; oc-ship now SOURCES it. A guard that greps
#: only TOOL_REL for them finds nothing and calls itself vacuous on a tree where
#: every leg is present — which is what it did, six FAILs per run, from that
#: refactor until this line existed. Both files are searched because the SPLIT
#: is what moved them: a future move back must not silently disarm the control.
BODY_REL="tests/ship-selftest.sh"
#: a guard fixture must never append to the shared tools log.
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #181 mutation guard (--test-threads retired: accepted, NOT forwarded) ==="

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
# The retirement journal line inside oc-ship's fresh-dispatch TEST_THREADS
# block. Matched on the STRIPPED text so the mutation survives an indentation
# change, and required to be UNIQUE: two matches would mean the guard cannot
# say which it mutated. Replacing it with the retired append restores the
# factory #39 forward EXACTLY where it used to live (inside the same
# `if [ -n "$TEST_THREADS" ]`), leaving the stderr note in place — so the
# mutant isolates the FORWARD, not the note.
needle = 'journal "LEG1 --test-threads $TEST_THREADS retired 2026-11-20 — accepted, not forwarded (factory #181)"'
hits = [i for i, l in enumerate(lines) if l.strip() == needle]
if len(hits) != 1:
    sys.stderr.write("mutation: %d retirement-journal lines, need exactly 1\n" % len(hits))
    sys.exit(2)
i = hits[0]
indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
if arm == "R":
    lines[i] = (indent + 'PRCHECKS_CALL+=(--test-threads "$TEST_THREADS")'
                '  # MUTANT R (factory #181): the RETIRED forward RESTORED')
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

[ "$rc_b" = 0 ] && ok "baseline oc-ship GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-ship rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# The guard is vacuous unless the pristine tree carries the RETIREMENT: the
# forward must be GONE and the loud note present. The old #39 check asserted
# the forwarding line EXISTS — that contract is retired with the input, and a
# guard still requiring it would red on every correct tree from now on.
if grep -qF 'PRCHECKS_CALL+=(--test-threads "$TEST_THREADS")' "$SRC/$TOOL_REL" \
   || grep -qF 'DISPATCH_ARGS+=(-f "test_threads=' "$SRC/harvest/oc-gate"; then
  bad "a test_threads forward is PRESENT in the pristine tree — the retirement (#181) has been reverted"
else
  ok "pristine tree carries NO test_threads forward (oc-ship + oc-gate)"
fi
grep -qF 'retired 2026-11-20 — the carrier declares the input and ignores it; accepted, not forwarded' "$SRC/$TOOL_REL" \
  && ok "baseline carries the oc-ship retirement note" \
  || bad "the oc-ship retirement note is MISSING — the guard would be vacuous"
grep -qF 'OC_SHIPCHAIN_TEST_THREADS needs a non-negative integer' "$SRC/$TOOL_REL" \
  && ok "baseline carries the env shape gate" \
  || bad "the env shape gate is MISSING from oc-ship — the guard would be vacuous"
for leg in test-threads/not-forwarded test-threads/journal-resolved-argv test-threads/env \
           test-threads/absent test-threads/shape-usage test-threads/inert-carry-green \
           test-threads/retired-note-on-fresh-path; do
  #: Search BOTH surfaces: the legs sit in the body since the T6 split, and the
  #: predicate must match every place the thing can live, not one phrasing of it.
  if grep -qF "$leg" "$SRC/$BODY_REL" 2>/dev/null || grep -qF "$leg" "$SRC/$TOOL_REL"; then
    ok "baseline carries leg $leg"
  else
    bad "leg $leg is MISSING from $TOOL_REL and $BODY_REL — the guard would be vacuous"
  fi
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

# ARM R: the RETIRED forward RESTORED. The three non-forwarding legs ARE the
# regression; the absence control cannot notice it (no flag -> the restored
# append still never fires), the shape gate dies before any dispatch, the
# carry-path legs never dispatch at all, and the retirement-note legs keep
# their note (the mutant only re-adds the forward beside it).
REDDEN=( test-threads/not-forwarded test-threads/journal-resolved-argv test-threads/env )
SURVIVE=( test-threads/absent test-threads/shape-usage test-threads/inert-carry-green \
          test-threads/retired-note-on-fresh-path test-threads/env-retired-note )
run_arm R 3

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #181 retirement legs fail under the restored-forward mutant and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
