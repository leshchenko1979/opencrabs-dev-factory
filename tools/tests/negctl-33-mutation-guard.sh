#!/usr/bin/env bash
# Mutation guard for #33 — prove the --test-threads passthrough legs are LIVE.
#
# #33: `oc-prchecks` could not pass the carrier's `test_threads` workflow input
# (the #1936 Stage 1 hang-capture mitigation). Its dispatch carried only
# `-f ref=`, `-f fast=`, `-f no_cancel=`, so a lane hitting the fleet-wide
# parallel-test deadlock could not ask the gate for a bounded libtest thread
# count — the gate burned its full 45-min job wall instead (run 37995939368,
# `Run tests` hung >44 min vs a normal 19m38s).
#
# The fix adds `--test-threads N`, GATED ON THE CARRIER YML CONTRACT: the flag is
# passed only when the yml declares the input, and a request the yml cannot
# honour dies LOUD rc 4 with NO dispatch — because unlike no_cancel (an internal
# optimisation) this input is CALLER-REQUESTED, so a silent drop would run the
# gate WITHOUT the mitigation while the caller believed it applied.
#
# A leg that cannot fail is decoration. This guard reverts the dispatch block on
# a COPY of the tools tree and requires `oc-prchecks --selftest` to fail on that
# copy, with the aimed legs among the FAIL lines, while the unmutated copy stays
# green.
#
# ASSERTION SHAPE — oc-prchecks' selftest COUNTS failures (it prints
# `selftest: $pass/$((pass+fail)) passed` and returns `[ "$fail" -eq 0 ]`); it
# does NOT abort at the first failing leg. So the strongest available assertion
# is: the mutant's rc is non-zero AND the aimed leg's TOKEN appears on a FAIL line.
# The mutation drops BOTH the send and the rc-4 gate, so two legs are expected to
# redden — more than one failure is not itself a fault here.
#
# THE TOKEN MUST SHARE ITS LINE WITH `FAIL`, AND `t_ok`/`t_bad` PRINT DIFFERENT
# TEXT. This file's legs follow the local convention of naming the leg only in the
# t_ok label ("<leg>: ... -> <claim>") while the t_bad label carries the diagnostic
# ("<leg> declared (rc=...)"), so a guard keyed on the t_ok label can NEVER match a
# reddened leg. The first run of this guard did exactly that: the mutant read
# 84/86 with both aimed legs genuinely reddening, yet the guard reported them
# uncaught — and the labels were multi-line besides (t_bad interpolated a
# multi-line $tt_out), putting the token and the FAIL marker on different lines of
# the SAME label. Both were fixed together: the #33 legs now carry a stable
# `<leg>/<claim>` token in BOTH labels (single-line via tt_brief), and this guard
# greps that token on a FAIL line. When adding a leg here, give it a token of the
# same shape and add it to AIMED. Do NOT key a guard on a t_ok label.
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
TOOL_REL="harvest/oc-prchecks"
AIMED="test_threads/dispatched"
AIMED_FAIL="test_threads/contract"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #33 mutation guard (oc-prchecks --test-threads passthrough) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  # No OC_SKILL_DIR pin here: unlike oc-ledger, oc-prchecks reads no $SKILL_DIR
  # artifact (grep: zero SKILL_DIR / SKILL.md refs), so a tools-only copy is a
  # faithful stand-in.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

# --- baseline: the pristine tree must be GREEN -------------------------------
cp -a "$SRC" "$WORK/baseline" || { echo "copy failed"; exit 2; }
base_out="$WORK/baseline.out"
rc_base="$(run_st "$WORK/baseline/$TOOL_REL" "$base_out")"
if [ "$rc_base" = "0" ]; then
  ok "baseline oc-prchecks --selftest GREEN (rc=0)"
else
  bad "baseline oc-prchecks rc=$rc_base (expected 0)"
fi
grep -Eq 'selftest: [0-9]+/[0-9]+ passed' "$base_out" \
  && ok "baseline prints the pass-count marker" \
  || bad "baseline did not print 'selftest: N/M passed'"

# The guard is vacuous unless the pristine tree carries the legs it later requires
# to redden. Assert both labels are present in the tool source — a mutant can only
# redden a leg that exists, and a renamed leg would silently disable this guard.
for label in "$AIMED" "$AIMED_FAIL"; do
  if grep -qF "$label" "$SRC/$TOOL_REL"; then
    ok "baseline carries leg '${label:0:60}…'"
  else
    bad "leg '$label' is MISSING from oc-prchecks — the guard would be vacuous"
  fi
done

# --- mutation ----------------------------------------------------------------
# Drop the WHOLE dispatch block: the send AND the fail-loud rc-4 gate. That is
# exactly the pre-#33 behaviour (the flag never reaches the carrier), so the
# aimed legs must catch it. Anchored on the ASCII assignment `TEST_THREADS_SENT=0`
# (unique in the file) and walked to the matching `fi` by depth counting — the
# block's own echo line carries an em-dash, and a non-ASCII anchor fed to python3
# is one encoding surprise from a silent no-op.
mutate() {  # mutate <tree> -> rc 0 on success
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
ANCHOR = "TEST_THREADS_SENT=0"
src = open(path, encoding="utf-8").read()
lines = src.split("\n")
hits = [i for i, l in enumerate(lines) if l.strip() == ANCHOR]
if len(hits) != 1:
    sys.stderr.write("mutation: %d lines are exactly %r, need exactly 1\n" % (len(hits), ANCHOR))
    sys.exit(2)
i = hits[0]
nxt = lines[i + 1].lstrip() if i + 1 < len(lines) else ""
if not nxt.startswith("if "):
    sys.stderr.write("mutation: line after the anchor is not an `if` (%r)\n" % nxt[:60])
    sys.exit(3)
depth = 0
j = None
for k in range(i + 1, len(lines)):
    t = lines[k].strip()
    if t.startswith("if ") or t.startswith("if["):
        depth += 1
    elif t == "fi" or t.startswith("fi "):
        depth -= 1
        if depth == 0:
            j = k
            break
if j is None:
    sys.stderr.write("mutation: no matching `fi` for the anchor's if-block\n")
    sys.exit(4)
lines[i:j + 1] = ["TEST_THREADS_SENT=0  # MUTANT: pre-#33 behaviour (flag never dispatched)"]
open(path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
}

# --- mutation matrix ---------------------------------------------------------
guard_one() {  # guard_one <label> <aimed-leg> [<extra-aimed-leg>]
  local label="$1" aimed="$2" extra="${3:-}"
  local mut="$WORK/mut_$label" outf="$WORK/mut_$label.out" rc_m=""

  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then bad "[$label] could not copy the tools tree"; return; fi
  if ! mutate "$mut" 2>"$WORK/mut_$label.mutate.err"; then
    bad "[$label] could not apply the mutation — guard is inert ($(cat "$WORK/mut_$label.mutate.err"))"
    return
  fi

  # Prove the mutant really differs (a no-op mutation would make this section
  # vacuous while every assertion below still reported PASS).
  if cmp -s "$SRC/$TOOL_REL" "$mut/$TOOL_REL"; then
    bad "[$label] mutant is byte-identical to the pristine tool — no-op mutation"
    return
  else
    ok "[$label] mutant applied ($(cmp -l "$SRC/$TOOL_REL" "$mut/$TOOL_REL" 2>/dev/null | wc -l) differing bytes)"
  fi

  rc_m="$(run_st "$mut/$TOOL_REL" "$outf")"
  if [ "$rc_m" = "0" ]; then
    bad "[$label] mutant selftest PASSED (rc=0) — the aimed leg does not catch the regression"
    return
  fi
  ok "[$label] mutant selftest RED (rc=$rc_m)"

  if grep -F "$aimed" "$outf" | grep -q 'FAIL'; then
    ok "[$label] CAUGHT — the aimed leg reddened: $(grep -F "$aimed" "$outf" | grep -m1 'FAIL' | cut -c1-140)"
  else
    bad "[$label] the aimed leg '$aimed' did NOT redden in the mutant output"
  fi

  if [ -n "$extra" ]; then
    if grep -F "$extra" "$outf" | grep -q 'FAIL'; then
      ok "[$label] CAUGHT — the fail-loud rc-4 leg reddened too"
    else
      bad "[$label] the fail-loud leg '$extra' did not redden"
    fi
  fi

  # Evidence of SCALE (informational — leg counts grow over time, so this is
  # reported, never asserted): the mutant's own pass-count marker. A mutation that
  # reddens exactly the aimed pair must read one step below the baseline's N/N.
  local pc=""
  pc="$(grep -Eo 'selftest: [0-9]+/[0-9]+ passed' "$outf" | tail -1)"
  [ -n "$pc" ] && ok "[$label] mutant pass-count: $pc" || bad "[$label] mutant printed no pass-count marker"
}

guard_one threads_block_dropped "$AIMED" "$AIMED_FAIL"

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #33 legs fail under their mutant and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
