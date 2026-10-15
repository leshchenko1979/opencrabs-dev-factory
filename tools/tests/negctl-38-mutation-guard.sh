#!/usr/bin/env bash
# Mutation guard for #38 — prove the OVERLAP legs are LIVE.
#
# #38: `sweep-closed-claims` probes THREE home trackers (HOME_REPOS: fork,
# factory, upstream) whose NUMBER SPACES OVERLAP. probe() recorded the title of
# the FIRST repo that carried a number, and the emit printed it, so a FACTORY
# claim on #33 was reported as "Comatose sessions after restart" — the FORK's
# #33. The release verdict was never wrong (OPEN-wins, fail-safe), but the title
# was a specificity the claim does not carry: the token it is matched against is
# a BARE INTEGER, because parse_issue_ref_value (tools/lib/oc_claims.py) keeps
# the number and DISCARDS the slug. The tool therefore cannot know which repo a
# token means, and must not assert a title when the number was seen on more than
# one home tracker.
#
# This guard mutates the emit back to "always print the first-probed title" —
# exactly the pre-#38 world — on a COPY of the tools tree, and requires the
# overlap legs to redden while the pristine copy stays green.
#
# ASSERTION SHAPE — the token-on-FAIL-line idiom IS available here (unlike
# negctl-34, whose tools print no per-leg line): oc-ledger's selftest defines
#   bad() { F=$((F+1)); echo "  FAIL selftest - $*" >&2; }
# so every failing leg NAMES ITSELF. Two consequences this guard honours:
#   (1) FAIL lines go to STDERR — every capture below is `2>&1`, or the guard
#       would read a silent green off a red run;
#   (2) the assertion is the TOKEN on a FAIL line, not merely "rc != 0", so the
#       guard names the regression instead of counting it.
# It ALSO asserts the pass-count drop, because a token test alone cannot tell a
# leg that failed from a leg that never ran (a deleted leg produces no FAIL line).
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
TOOL_REL="state/oc-ledger"
#: legs that depend on the withhold-when-ambiguous emit: the two title-absence
#: assertions and the ambiguity-name assertion. The positive control (#29,
#: single-tracker) and the release-verdict legs are INDEPENDENT of the mutation
#: and must keep passing — that is what stops a "withhold every title" mutant
#: from being mistaken for a fix.
EXPECTED_DROP=3
export OC_TOOLS_NOLOG=1
#: The copied tree has no SKILL.md, so `SKILL_DIR` would resolve to the temp dir
#: and the three `state-tracked-audit-*` legs (which read $SKILL_DIR/SKILL.md —
#: the state-dir TRACKED/GENERATED-IGNORED declaration) would redden for a
#: REASON UNRELATED TO THE MUTATION, leaving the guard with a red baseline and a
#: meaningless drop measurement. Pin it at the REAL skill dir: the mutation lands
#: in the copied CODE, while data reads still see the law. Measured: without this
#: the baseline reads 593/rc 1 instead of 596/rc 0 (the three legs named above).
export OC_SKILL_DIR="$SKILL_DIR"

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #38 mutation guard (overlapping tracker number spaces) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN: bad() writes there.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "oc-ledger selftest: PASS=N FAIL=M"
  grep -Eo 'selftest: PASS=[0-9]+' "$1" | tail -1 | cut -d= -f2
}

# --- aimed scenario probe ----------------------------------------------------
# The #38 reproducer, hand-built and hermetic: ONE number, CLOSED on the fork AND
# on the factory, with a DIFFERENT title on each. Prints the sweep's output.
# On the pristine tree it must name the ambiguity and print NEITHER title; on the
# mutant it must print the fork's (first-probed) title.
probe() {  # probe <tools-tree> -> stdout+stderr of the sweep
  local tree="$1" d="$WORK/probe"
  rm -rf "$d"; mkdir -p "$d/bin"
  cat > "$d/bin/gh" <<'SH'
#!/bin/sh
if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
  case "$*" in
    *"opencrabs/opencrabs"*) echo '[]' ;;
    *"opencrabs-dev-factory"*)
      case "$*" in
        *"--state closed"*) echo '[{"number":64,"title":"factory-sixtyfour"}]' ;;
        *"--state open"*)   echo '[]' ;;
      esac ;;
    *)
      case "$*" in
        *"--state closed"*) echo '[{"number":64,"title":"fork-sixtyfour"}]' ;;
        *"--state open"*)   echo '[]' ;;
      esac ;;
  esac
  exit 0
fi
exit 1
SH
  chmod +x "$d/bin/gh"
  jq -n '{workers:[],events:[{n:1,t:"2026-10-14T00:00:00Z",
      by:"editor 11111111-1111-1111-1111-111111111111",kind:"claim",what:"CLAIM #64"}]}' \
    > "$d/ledger.json"
  # --dry-run: a pure read, so the probe can never write a ledger row.
  PATH="$d/bin:$PATH" OC_LEDGER="$d/ledger.json" \
    bash "$tree/$TOOL_REL" sweep-closed-claims --dry-run 2>&1
}

# --- mutation: always print the first-probed title ---------------------------
mutate() {  # mutate <tools-tree> -> rc 0 on success
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
lines = open(path, encoding="utf-8").read().split("\n")
needle = "            if len(repos) == 1:"
hits = [i for i, l in enumerate(lines) if l == needle]
if len(hits) != 1:
    sys.stderr.write("mutation: %d emit guards, need exactly 1\n" % len(hits))
    sys.exit(2)
lines[hits[0]] = ("            if True:  # MUTANT (factory #38): pre-#38 behaviour"
                  " - always assert the first-probed tracker title")
open(path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
}

# --- baseline ----------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_b="$(run_st "$WORK/base/$TOOL_REL" "$WORK/base.out")"
n_b="$(passed_of "$WORK/base.out")"

[ "$rc_b" = 0 ] && ok "baseline oc-ledger GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-ledger rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# The guard is vacuous unless the pristine tree carries the fixtures it later
# requires to redden: a renamed or deleted overlap leg would silently disarm it.
grep -qF 'no single title' "$SRC/$TOOL_REL" \
  && ok "baseline carries the withhold emit" \
  || bad "the withhold emit is MISSING from oc-ledger — the guard would be vacuous"
grep -qF 'sweep-overlap-prints-fork-title' "$SRC/$TOOL_REL" \
  && ok "baseline carries the overlap legs" \
  || bad "the overlap legs are MISSING from oc-ledger — the guard would be vacuous"

# Baseline probe: the aimed scenario must PASS before the mutation means anything.
p_out="$(probe "$WORK/base")"
grep -q 'no single title' <<< "$p_out" \
  && ok "baseline probe: overlap names the ambiguity" \
  || bad "baseline probe: 'no single title' absent — the probe itself is broken"
grep -q 'fork-sixtyfour' <<< "$p_out" \
  && bad "baseline probe: the fork title is STILL printed (the defect is live)" \
  || ok "baseline probe: neither title printed"

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
  grep -qF 'MUTANT (factory #38)' "$WORK/mut/$TOOL_REL" \
    && ok "mutant carries the marker and no longer withholds an ambiguous title" \
    || bad "mutant marker absent — the mutation did not land where expected"

  # The named regression, on a FAIL line the tool itself emits.
  q_out="$(probe "$WORK/mut")"
  grep -q 'fork-sixtyfour' <<< "$q_out" \
    && ok "[aimed leg] mutant prints the fork title (this IS the #38 repro)" \
    || bad "[aimed leg] mutant did not print the fork title — the probe is not aimed at the mutation"

  rc_m="$(run_st "$WORK/mut/$TOOL_REL" "$WORK/mut.out")"
  n_m="$(passed_of "$WORK/mut.out")"

  if [ "$rc_m" = 0 ]; then
    bad "mutant selftest PASSED (rc=0) — the overlap legs do not catch the regression"
  else
    ok "mutant selftest RED (rc=$rc_m)"
  fi

  for tok in sweep-overlap-prints-fork-title sweep-overlap-ambiguity-named \
             sweep-overlap-names-the-count; do
    grep -qF "FAIL selftest - $tok" "$WORK/mut.out" \
      && ok "[named] $tok is on a FAIL line under the mutant" \
      || bad "[named] $tok did NOT redden under the mutant — that leg is decoration"
  done

  # ...and the legs INDEPENDENT of the mutation must survive it, or the guard
  # would be satisfied by a mutant that simply broke the verb.
  for tok in sweep-overlap-single-tracker-title-kept sweep-overlap-released-64; do
    grep -qF "FAIL selftest - $tok" "$WORK/mut.out" \
      && bad "[control] $tok reddened under the mutant — it is not mutation-independent" \
      || ok "[control] $tok survived the mutant (mutation-independent)"
  done

  if [ -n "$n_b" ] && [ -n "$n_m" ]; then
    drop=$(( n_b - n_m ))
    if [ "$drop" -eq "$EXPECTED_DROP" ]; then
      ok "CAUGHT — pass-count dropped by exactly $drop ($n_b -> $n_m): the $EXPECTED_DROP overlap legs are LIVE"
    else
      bad "pass-count dropped by $drop ($n_b -> $n_m), expected $EXPECTED_DROP — either an overlap leg is decoration or another leg is coupled to the emit"
    fi
  else
    bad "could not measure the drop (baseline='$n_b' mutant='$n_m')"
  fi
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #38 overlap legs fail under their mutant and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
