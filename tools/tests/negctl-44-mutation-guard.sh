#!/usr/bin/env bash
# Mutation guard for #44 — prove the BLOCK-DELTA legs of oc-vendor-drift are LIVE.
#
# #44: the vendored `oc-questions` carries a legitimate local patch (#497, the
# closed-vocabulary widening) whose lines are NOT UNIQUE — a bare '#', blank
# lines and a duplicated assertion all recur in that file. The guard's only
# delta shape was a per-line REGEX, so there were two ways to make it green and
# BOTH were wrong:
#   * declare a pattern broad enough to match the patch -> it also strips
#     unrelated lines and the guard stops discriminating (the #41 trap: a
#     force-match makes real drift read clean, and the commit that does it is
#     read as a ratified decision);
#   * declare nothing -> the gate stays RED forever and gets switched off.
# The fix is a BLOCK delta: an EXACT contiguous run, stripped from its OWN side
# only, that must occur EXACTLY ONCE.
#
# THREE ARMS, each reaching a different half of that contract:
#   ARM nostrip  — blocks are never stripped. Must redden the IN_SYNC leg (the
#                  feature does not work) and the ambiguity leg (its message can
#                  only come from the strip path). The exactness leg SURVIVES it
#                  ("not stripped" also reads DRIFTED). The SIDE leg survives it
#                  TOO, but for an unrelated reason worth naming: with the
#                  dispatch disabled a block entry falls through to the per-line
#                  path, has no matcher, and hits the fail-closed refusal -- which
#                  is also DRIFTED. Its own discrimination is proved by ARM side,
#                  not here. That is why a token test alone would be too weak, and
#                  why the pass-count drop is asserted too.
#   ARM first    — strip the FIRST match and ignore ambiguity. Must redden ONLY
#                  the ambiguity leg: silently stripping one of two occurrences
#                  is how a block stops naming a unique region.
#   ARM side     — ignore `side` and strip from BOTH sides. Must redden the
#                  side-scoping leg, whose fixture carries a marker block
#                  VERBATIM on both sides precisely so that ignoring `side`
#                  reads IN_SYNC and hides a real upstream divergence.
#
#   ARM nomatch  — restore the old "$^" default for a delta with no matcher.
#                  "$^" is a VALID regex matching the EMPTY string, so under
#                  fullmatch it strips every blank line from BOTH sides and the
#                  pair reads IN_SYNC: a silent over-strip. Must redden ONLY the
#                  fail-closed leg.
#
# ASSERTION SHAPE — oc-vendor-drift's selftest prints `FAIL - <message>` on
# STDOUT and a `selftest: N passed, M failed` summary, so the guard convicts a
# NAMED leg and asserts the exact pass-count drop (a token test cannot tell a
# FAILED leg from a DELETED one).
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
TOOL_REL="audit/oc-vendor-drift"
export OC_TOOLS_NOLOG=1 OC_NO_FLOODGUARD=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #44 mutation guard (oc-vendor-drift BLOCK deltas) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "selftest: N passed, M failed"
  sed -n 's/^selftest: \([0-9][0-9]*\) passed.*/\1/p' "$1" | tail -1
}

# --- non-vacuity: the pristine tree must CARRY the mechanism and the legs ---
for tok in 'block delta carrying non-unique lines' \
           'one byte inside a declared block' \
           'ambiguous block (2 occurrences)' \
           'a block declared for one side is not stripped from the other' \
           'a delta with no matcher'; do
  grep -qF "$tok" "$SRC/$TOOL_REL" \
    && ok "baseline carries the '$tok' leg" \
    || bad "the '$tok' leg is MISSING from oc-vendor-drift — the guard would be vacuous"
done
grep -qF 'if "block" in d:' "$SRC/$TOOL_REL" \
  && ok "baseline dispatches block deltas" \
  || bad "the block dispatch is MISSING — ARM nostrip would have nothing to revert"
grep -qF 'if len(spans) != 1:' "$SRC/$TOOL_REL" \
  && ok "baseline requires EXACTLY ONE occurrence" \
  || bad "the uniqueness requirement is MISSING — ARM first would be vacuous"
grep -qF '(d.get("side") or "local") == side:' "$SRC/$TOOL_REL" \
  && ok "baseline scopes each block to its own side" \
  || bad "the side scoping is MISSING — ARM side would be vacuous"
grep -qF "has neither 'match' nor 'match_upstream'" "$SRC/$TOOL_REL" \
  && ok "baseline REFUSES a delta with no matcher" \
  || bad "the missing-matcher refusal is MISSING — ARM nomatch would be vacuous"

# --- baseline ---------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_b="$(run_st "$WORK/base/$TOOL_REL" "$WORK/base.out")"
n_b="$(passed_of "$WORK/base.out")"

[ "$rc_b" = 0 ] && ok "baseline oc-vendor-drift GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-vendor-drift rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# --- mutators ---------------------------------------------------------------
mutate_nostrip() {  # blocks are never stripped: the feature does not work
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = '        if "block" in d:\n'
repl = '        if False and "block" in d:\n'
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d block-dispatch sites, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, repl))
PYEOF
}

mutate_first() {  # strip the first match, ignore ambiguity
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = '        if len(spans) != 1:\n'
repl = '        if not spans:\n'
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d uniqueness tests, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, repl))
PYEOF
}

mutate_side() {  # ignore `side`: strip from BOTH sides
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = '            if (d.get("side") or "local") == side:\n'
repl = '            if True:\n'
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d side-scoping sites, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, repl))
PYEOF
}

mutate_nomatch() {  # restore the "$^" default: silent over-strip, reads green
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = ("            raise ValueError(\n"
          "                \"delta entry #%d has neither 'match' nor 'match_upstream'\"\n"
          "                % (i + 1))\n")
repl = '            m = "$^"\n'
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d fail-closed sites, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, repl))
PYEOF
}

# arm <name> <mutator> <expected-drop> <red:comma,list> <green:comma,list>
arm() {
  local name="$1" mutator="$2" drop="$3" reds="$4" greens="$5"
  local mut="$WORK/mut-$name" rc_m n_m
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
  rc_m="$(run_st "$mut/$TOOL_REL" "$WORK/$name.out")"
  n_m="$(passed_of "$WORK/$name.out")"
  [ "$rc_m" = 1 ] && ok "[$name] mutant selftest rc=1 (a red run, not a crash)" \
                  || bad "[$name] mutant rc=$rc_m (expected 1 — a crash is not a catch)"
  # Each expected-red leg must carry its OWN FAIL token. Split on COMMA only:
  # leg messages CONTAIN spaces, so a ${list//,/ } expansion would word-split
  # them and every assertion would match the wrong thing (measured 2026-10-17
  # in the sibling negctl-43 guard).
  local oldifs="$IFS" t
  IFS=','
  for t in $reds; do
    grep -qF "FAIL - $t" "$WORK/$name.out" \
      && ok "[$name] '$t' reddened" \
      || bad "[$name] '$t' did NOT redden — that leg does not guard this mutation"
  done
  for t in $greens; do
    grep -qF "FAIL - $t" "$WORK/$name.out" \
      && bad "[$name] '$t' reddened too — the arm is not isolated" \
      || ok "[$name] '$t' survived"
  done
  IFS="$oldifs"
  if [ -n "$n_b" ] && [ -n "$n_m" ]; then
    local want=$((n_b - drop))
    if [ "$n_m" = "$want" ]; then
      ok "[$name] pass-count drop exactly $drop ($n_b -> $n_m)"
    else
      bad "[$name] pass-count $n_b -> $n_m, expected exactly $drop fewer ($want)"
    fi
  else
    bad "[$name] could not measure the drop (baseline='${n_b:-}' mutant='${n_m:-}')"
  fi
}

arm nostrip mutate_nostrip 2 \
    'block delta carrying non-unique lines,ambiguous block (2 occurrences)' \
    'one byte inside a declared block,a block declared for one side is not stripped from the other,a delta with no matcher,declared delta only'
arm first   mutate_first   1 \
    'ambiguous block (2 occurrences)' \
    'block delta carrying non-unique lines,one byte inside a declared block,a block declared for one side is not stripped from the other'
arm side    mutate_side    3 \
    'block delta carrying non-unique lines,ambiguous block (2 occurrences),a block declared for one side is not stripped from the other' \
    'one byte inside a declared block,declared delta only'
arm nomatch mutate_nomatch 1 \
    'a delta with no matcher' \
    'block delta carrying non-unique lines,one byte inside a declared block,ambiguous block (2 occurrences),a block declared for one side is not stripped from the other,declared delta only'

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the block-strip, uniqueness and side-scoping legs each redden under their own mutant and the pristine tree stays green"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
