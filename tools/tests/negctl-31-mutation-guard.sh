#!/usr/bin/env bash
# Mutation guard for #31 — prove the H-4 provenance gate's legs are LIVE.
#
# #31: `oc-ledger sync --version <v>` with no `--why` exited 0 and wrote a
# provenance-free `skill-bump` row ("v0.4.294 — ; battery receipt ts ...",
# n=15059). The tool's header had always declared `--why mandatory` and
# upstream-merge-runbook.md:411 (H-4) makes it law, but the code required it
# only for --catch-up. The fix adds a fail-closed rc-2 gate after the step-check.
#
# A leg that cannot fail is decoration. This guard reverts the gate on a COPY of
# the tools tree and requires `oc-ledger --selftest` to fail on that copy, with
# `sync-empty-why-refused` among the FAIL lines, while the unmutated copy stays
# green.
#
# ASSERTION SHAPE — oc-ledger's selftest COUNTS failures (it prints
# `oc-ledger selftest: PASS=$P FAIL=$F` and returns `[ "$F" -eq 0 ]`); it does NOT
# abort at the first failing leg, unlike oc-commit. So the strongest available
# assertion is: the mutant's rc is non-zero AND the aimed leg appears among its
# FAIL lines. Shadowing is possible (a mutation that reddens an earlier leg does
# not hide this one, because the run continues), so more than one failure is
# expected and is not itself a fault here.
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
SRC="$SKILL_DIR/tools"
#: One home for the location (v0.4.255 regroup moved the fleet into kind subdirs).
LEDGER_REL="state/oc-ledger"
AIMED="sync-empty-why-refused"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #31 mutation guard (oc-ledger sync empty-why provenance gate) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  # OC_SKILL_DIR is pinned to the REAL skill dir. A `tools/`-only copy resolves
  # SKILL_DIR to its temp parent (no SKILL.md), and three `state-tracked-audit-*`
  # legs read $SKILL_DIR/SKILL.md directly — they failed on the pristine copy
  # before this pin (measured: FAIL=3, all three). Pinning OC_SKILL_DIR replicates
  # the normal run exactly: line 166 takes the override, while the selftest's own
  # `export OC_SKILL_DIR="$T/skill"` (its fixture section) still redirects every
  # sync subprocess to the fixture skill repo, so nothing writes the real tree.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(OC_SKILL_DIR="$SKILL_DIR" timeout 900 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

# --- baseline: the pristine tree must be GREEN -------------------------------
cp -a "$SRC" "$WORK/baseline" || { echo "copy failed"; exit 2; }
base_out="$WORK/baseline.out"
rc_base="$(run_st "$WORK/baseline/$LEDGER_REL" "$base_out")"
if [ "$rc_base" = "0" ]; then
  ok "baseline oc-ledger --selftest GREEN (rc=0)"
else
  bad "baseline oc-ledger rc=$rc_base (expected 0)"
fi
grep -Eq 'oc-ledger selftest: PASS=[0-9]+ FAIL=0' "$base_out" \
  && ok "baseline prints the PASS=/FAIL=0 marker" \
  || bad "baseline did not print 'FAIL=0'"

# The guard is vacuous unless the pristine tree carries the leg it later requires
# to redden. Assert the label is present in the tool source — a mutant can only
# redden a leg that exists, and a renamed leg would silently disable this guard.
if grep -q "$AIMED" "$SRC/$LEDGER_REL"; then
  ok "baseline carries leg '$AIMED'"
else
  bad "leg '$AIMED' is MISSING from oc-ledger — the guard would be vacuous"
fi

# --- mutation ----------------------------------------------------------------
# Drop the whole gate line. Anchored on the ASCII tail `must not ship without its
# why-text` PLUS the gate's own shape `[ -n "$why" ] || die 2` — the phrase alone
# occurs TWICE (the gate line AND the selftest-leg comment above it), so the shape
# filter is what makes the anchor unique (measured: the phrase-only anchor aborted
# with "anchor occurs in 2 lines"). The whole line is replaced, so no dangling
# message text survives. The tail is ASCII because a non-ASCII anchor fed to
# python3 on stdin is one encoding surprise from a silent no-op (the gate line
# carries an em-dash).
mutate() {  # mutate <tree> -> rc 0 on success
  python3 - "$1/$LEDGER_REL" <<'PYEOF'
import sys
path = sys.argv[1]
ANCHOR = "must not ship without its why-text"
GATE = '[ -n "$why" ] || die 2'
src = open(path).read()
lines = src.split("\n")
hits = [i for i, l in enumerate(lines) if ANCHOR in l and GATE in l]
if len(hits) != 1:
    sys.stderr.write("mutation: %d lines carry anchor+gate shape, need exactly 1\n" % len(hits))
    sys.exit(2)
lines[hits[0]] = "  : # MUTANT: H-4 why-gate dropped"
open(path, "w").write("\n".join(lines))
PYEOF
}

# --- mutation matrix ---------------------------------------------------------
guard_one() {  # guard_one <label> <aimed-leg>
  local label="$1" aimed="$2"
  local mut="$WORK/mut_$label" outf="$WORK/mut_$label.out" rc_m=""

  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then bad "[$label] could not copy the tools tree"; return; fi
  if ! mutate "$mut" 2>"$WORK/mut_$label.mutate.err"; then
    bad "[$label] could not apply the mutation — guard is inert ($(cat "$WORK/mut_$label.mutate.err"))"
    return
  fi

  # Prove the mutant really differs (a no-op mutation would make this section
  # vacuous while every assertion below still reported PASS).
  if cmp -s "$SRC/$LEDGER_REL" "$mut/$LEDGER_REL"; then
    bad "[$label] mutant is byte-identical to the pristine tool — no-op mutation"
    return
  else
    ok "[$label] mutant applied ($(cmp -l "$SRC/$LEDGER_REL" "$mut/$LEDGER_REL" 2>/dev/null | wc -l) differing bytes)"
  fi

  rc_m="$(run_st "$mut/$LEDGER_REL" "$outf")"
  if [ "$rc_m" = "0" ]; then
    bad "[$label] mutant selftest PASSED (rc=0) — the aimed leg does not catch the regression"
    return
  fi
  ok "[$label] mutant selftest RED (rc=$rc_m)"

  if grep -q "$aimed" "$outf"; then
    ok "[$label] CAUGHT — the aimed leg reddened: $(grep -m1 "$aimed" "$outf" | sed 's/^  //')"
  else
    bad "[$label] the aimed leg '$aimed' did NOT appear in the mutant output"
  fi
}

guard_one why_gate_dropped "$AIMED"

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #31 leg fails under its mutant and stays green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
