#!/usr/bin/env bash
# Mutation guard for factory #163 — prove the ANSWER-CONTAINMENT arm is LIVE.
#
# #163: `oc-poll status` built `answered` from `index.log` alone, so an answer
# written for a uuid that is NOT a frozen target raised the numerator. Measured
# on the pre-fix tool: targets {A,B,C} / sent {A,B,C} / index rows {A,Z} read
# `answered=2` (66.67 %) for a poll where exactly ONE target answered (33.33 %),
# and a targeted-but-never-delivered uuid could be named undelivered AND counted
# as answered in the same block (`answered=4` on 3 delivered = 133 %).
#
# The fix makes `answered` a set INTERSECTION (`index ∩ targets ∩ delivered`).
# This guard mutates that intersection BACK to the raw index.log count — the
# pre-#163 world, exactly — on a COPY of the tools tree, and requires the new
# arms to redden while the pristine copy stays green.
#
# ASSERTION SHAPE: oc-poll's selftest defines
#   chk() { ... echo "  FAIL oc-poll - $1 (want rc=$2 got rc=$3)" >&2; }
# so every failing leg NAMES ITSELF, on STDERR. Every capture below is `2>&1`,
# or the guard would read a silent green off a red run. The assertion is the
# TOKEN on a FAIL line, not merely "rc != 0", so the guard names the regression
# instead of counting it — and it ALSO asserts the pass-count drop, because a
# token test alone cannot tell a leg that failed from a leg that never ran.
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
TOOL_REL="state/oc-poll"
#: arms that depend on the containment. Arm 11 is the #163 reproducer itself;
#: arm 12 is the same defect on the DELIVERED leg. Everything else in the suite
#: (the write-integrity arms, the 3/3/3 positive control) is independent of the
#: mutation and must survive it — that is what stops a mutant that simply broke
#: `status` from being mistaken for a caught regression.
EXPECTED_DROP=2
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #163 mutation guard (answered must be CONTAINED in targets ∩ delivered) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN: chk writes there.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "oc-poll selftest: PASS=N FAIL=M"
  grep -Eo 'selftest: PASS=[0-9]+' "$1" | tail -1 | cut -d= -f2
}

# --- aimed scenario probe ----------------------------------------------------
# The #163 reproducer, hand-built and hermetic: three targets, all three sent,
# ONE target answers and a NON-TARGET answers too. On the pristine tree the
# counts line must read `answered=1` and name the non-target under its own
# section; on the mutant it reads `answered=2`.
probe() {  # probe <tools-tree> -> stdout+stderr of `status`
  local tree="$1" d="$WORK/probe"
  rm -rf "$d"; mkdir -p "$d"
  local A=11111111-1111-4111-8111-111111111111
  local B=22222222-2222-4222-8222-222222222222
  local C=33333333-3333-4333-8333-333333333333
  local Z=99999999-9999-4999-8999-999999999999
  printf '%s\n' "$A" "$B" "$C" > "$d/t.txt"
  printf 'a\n' > "$d/bodyA.md"; printf 'z\n' > "$d/bodyZ.md"
  bash "$tree/$TOOL_REL" open "$d/p" --targets "$d/t.txt" >/dev/null 2>&1
  printf '%s\n' "$A" "$B" "$C" > "$d/p/wave-001.targets"
  printf '%s\n' "$A" "$B" "$C" > "$d/p/wave-001.sent"
  bash "$tree/$TOOL_REL" answer "$d/p" "$A" "$d/bodyA.md" >/dev/null 2>&1
  bash "$tree/$TOOL_REL" answer "$d/p" "$Z" "$d/bodyZ.md" >/dev/null 2>&1
  bash "$tree/$TOOL_REL" status "$d/p" 2>&1
}

# --- mutation: restore the unconstrained answered count ----------------------
# The fix line is the SECOND intersection (answered := answered_targeted ∩
# delivered). Replacing it with a plain copy of the raw index.log set restores
# the pre-#163 numerator exactly, while leaving every printed section in place —
# so the mutant isolates the COUNT, not the emit.
mutate() {  # mutate <tools-tree> -> rc 0 on success
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
lines = open(path, encoding="utf-8").read().split("\n")
needle = 'comm -12 "$W/answered_targeted" "$W/delivered" > "$W/answered"'
hits = [i for i, l in enumerate(lines) if l.strip() == needle]
if len(hits) != 1:
    sys.stderr.write("mutation: %d containment lines, need exactly 1\n" % len(hits))
    sys.exit(2)
lines[hits[0]] = ('  cp "$W/answered_raw" "$W/answered"'
                  '   # MUTANT (factory #163): the unconstrained answered count RESTORED')
open(path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
}

# --- baseline ----------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_b="$(run_st "$WORK/base/$TOOL_REL" "$WORK/base.out")"
n_b="$(passed_of "$WORK/base.out")"

[ "$rc_b" = 0 ] && ok "baseline oc-poll GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-poll rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# The guard is vacuous unless the pristine tree carries the arms it later
# requires to redden: a renamed or deleted arm would silently disarm it.
grep -qF 'comm -12 "$W/answered_targeted" "$W/delivered" > "$W/answered"' "$SRC/$TOOL_REL" \
  && ok "baseline carries the answered containment" \
  || bad "the answered containment is MISSING from oc-poll — the guard would be vacuous"
grep -qF '11-non-target-not-counted' "$SRC/$TOOL_REL" \
  && ok "baseline carries the #163 non-target arm" \
  || bad "arm 11 is MISSING from oc-poll — the guard would be vacuous"
grep -qF '12-never-delivered-not-counted' "$SRC/$TOOL_REL" \
  && ok "baseline carries the #163 never-delivered arm" \
  || bad "arm 12 is MISSING from oc-poll — the guard would be vacuous"

# Baseline probe: the aimed scenario must read the CONTAINED count before the
# mutation means anything.
p_out="$(probe "$WORK/base")"
grep -qF 'targeted=3 delivered=3 answered=1' <<< "$p_out" \
  && ok "baseline probe: the non-target answer is NOT counted (answered=1 of 3)" \
  || bad "baseline probe: expected 'targeted=3 delivered=3 answered=1', got: $p_out"
grep -qF '99999999-9999-4999-8999-999999999999' <<< "$p_out" \
  && ok "baseline probe: the non-target uuid is NAMED, not dropped" \
  || bad "baseline probe: the non-target uuid is absent from the output"

# --- mutant ------------------------------------------------------------------
cp -a "$SRC" "$WORK/mut" || { bad "could not copy the tools tree"; echo "MUTATION GUARD FAILED (failures=$fails)"; exit 1; }
if ! mutate "$WORK/mut" 2>"$WORK/mutate.err"; then
  bad "could not apply the mutation — guard is inert ($(cat "$WORK/mutate.err"))"
else
  # A no-op mutation would make every assertion below vacuous while still passing.
  if cmp -s "$SRC/$TOOL_REL" "$WORK/mut/$TOOL_REL"; then
    bad "mutant tool is byte-identical to the pristine one — no-op mutation"
  else
    ok "mutant applied ($(cmp -l "$SRC/$TOOL_REL" "$WORK/mut/$TOOL_REL" 2>/dev/null | wc -l) differing bytes in $TOOL_REL)"
  fi
  grep -qF 'MUTANT (factory #163)' "$WORK/mut/$TOOL_REL" \
    && ok "mutant carries the marker and counts the raw index.log set" \
    || bad "mutant marker absent — the mutation did not land where expected"
  bash -n "$WORK/mut/$TOOL_REL" 2>"$WORK/syntax.err" \
    && ok "mutant parses (bash -n)" \
    || bad "mutant does not parse — $(head -1 "$WORK/syntax.err")"

  # The named regression, on the live reproducer.
  q_out="$(probe "$WORK/mut")"
  grep -qF 'targeted=3 delivered=3 answered=2' <<< "$q_out" \
    && ok "[aimed probe] mutant counts the non-target answer (this IS the #163 repro)" \
    || bad "[aimed probe] mutant did not restore answered=2 — the probe is not aimed at the mutation"

  rc_m="$(run_st "$WORK/mut/$TOOL_REL" "$WORK/mut.out")"
  n_m="$(passed_of "$WORK/mut.out")"

  if [ "$rc_m" = 0 ]; then
    bad "mutant selftest PASSED (rc=0) — the containment arms do not catch the regression"
  else
    ok "mutant selftest RED (rc=$rc_m)"
  fi

  for tok in 11-non-target-not-counted 12-never-delivered-not-counted; do
    grep -qF "FAIL oc-poll - $tok" "$WORK/mut.out" \
      && ok "[named] $tok is on a FAIL line under the mutant" \
      || bad "[named] $tok did NOT redden under the mutant — that leg is decoration"
  done

  # ...and the legs INDEPENDENT of the mutation must survive it, or the guard
  # would be satisfied by a mutant that simply broke the verb.
  for tok in 10-counts 11-answer-non-target-rc 12-open 4-orphan-file-not-counted; do
    grep -qF "FAIL oc-poll - $tok" "$WORK/mut.out" \
      && bad "[control] $tok reddened under the mutant — it is not mutation-independent" \
      || ok "[control] $tok survived the mutant (mutation-independent)"
  done

  if [ -n "$n_b" ] && [ -n "$n_m" ]; then
    drop=$(( n_b - n_m ))
    if [ "$drop" -eq "$EXPECTED_DROP" ]; then
      ok "CAUGHT — pass-count dropped by exactly $drop ($n_b -> $n_m): the $EXPECTED_DROP containment arms are LIVE"
    else
      bad "pass-count dropped by $drop ($n_b -> $n_m), expected $EXPECTED_DROP — either a containment arm is decoration or another leg is coupled to the count"
    fi
  else
    bad "could not measure the drop (baseline='$n_b' mutant='$n_m')"
  fi
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #163 containment arms fail under the restored-unconstrained-count mutant and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
