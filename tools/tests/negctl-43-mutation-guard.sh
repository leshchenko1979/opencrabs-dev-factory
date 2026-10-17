#!/usr/bin/env bash
# Mutation guard for #43 — prove the Leg R POPULATION legs are LIVE.
#
# #43: the fork-only ref set was built with `gh issue list`, which EXCLUDES pull
# requests, and both trackers are hundreds of PRs deep in that gap (measured
# 2026-10-17: upstream 1608 issues vs 2005 issues+PRs, fork 763 vs 783). That
# one wrong population cost BOTH directions:
#   FALSE POSITIVE — 69 of 124 `fork-only` rows existed upstream as PRs, so the
#     leg demanded qualification of refs that were already correct: a 55.6%
#     noise rate on a corpus that already carries real findings. A lint that
#     cries wolf gets switched off, which is how the original leak shipped.
#   FALSE NEGATIVE — a fork PR number is in NEITHER issue list, so it held no
#     row at all: fork #4 is a PR and upstream #4 is 404, a genuinely dead ref
#     the leg could never flag. (The reporter's "the true set is a strict
#     subset, so no real leak is missed" was therefore false, and corrected.)
#
# THREE ARMS, each reaching a different half:
#   ARM pop   — put the builder back on `gh issue list`. Must redden the two
#               legs that read the refreshed cache (population + provenance);
#               the truncation arm and the pre-existing Leg R arms must SURVIVE.
#   ARM hdr   — drop the `# counts:` header line. Must redden ONLY provenance:
#               a cache that cannot say which population produced it is the
#               defect itself, and only its own header can show that.
#   ARM trunc — neuter the search-index comparison. Must redden ONLY truncation:
#               a paginate that silently loses pages is the #343 class, and the
#               sentinel leg is the one thing standing between it and a set with
#               a gap in it.
#
# ASSERTION SHAPE — oc-harvest-sweep's selftest writes FAIL lines to STDERR
# (every capture is `2>&1`) and each names its own token, so the guard convicts
# a NAMED leg rather than counting a red run. It ALSO asserts the exact
# pass-count drop: a token test alone cannot tell a leg that FAILED from one
# that was DELETED, and deleting a leg prints no FAIL line at all.
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

echo "=== #43 mutation guard (Leg R ref-set population) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "selftest OK: N/M legs"
  sed -n 's/^selftest OK: \([0-9][0-9]*\)\/.*/\1/p' "$1" | tail -1
}

# --- non-vacuity: the pristine tree must CARRY the legs and the mechanism ---
for tok in 'leg-R population' 'leg-R truncation' 'leg-R cache-provenance'; do
  grep -qF "FAIL $tok" "$SRC/$TOOL_REL" \
    && ok "baseline carries the '$tok' leg" \
    || bad "the '$tok' leg is MISSING from oc-harvest-sweep — the guard would be vacuous"
done
# the builder must read the POPULATION (issues AND PRs), never the issue list
grep -qF 'issues?state=all&per_page=100' "$SRC/$TOOL_REL" \
  && ok "baseline reads the issues API (issues AND PRs)" \
  || bad "the issues-API read is MISSING — ARM pop would have nothing to revert"
grep -qF '_fr_api_pop' "$SRC/$TOOL_REL" \
  && ok "baseline carries the search-index population control" \
  || bad "the population control is MISSING — ARM trunc would be vacuous"
grep -qF 'could not read the WHOLE population' "$SRC/$TOOL_REL" \
  && ok "baseline carries the refusal message the truncation leg keys on" \
  || bad "the population refusal message is MISSING — the truncation leg could not fire"

# --- baseline ---------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_b="$(run_st "$WORK/base/$TOOL_REL" "$WORK/base.out")"
n_b="$(passed_of "$WORK/base.out")"

[ "$rc_b" = 0 ] && ok "baseline oc-harvest-sweep GREEN (rc=0, ${n_b:-?} passed)" \
               || bad "baseline oc-harvest-sweep rc=$rc_b (expected 0)"
[ -n "$n_b" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# --- mutators ---------------------------------------------------------------
mutate_pop() {  # put the builder back on `gh issue list` (the #43 defect)
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = '''    gh api "repos/$1/issues?state=all&per_page=100" --paginate --jq '.[].number' 2>/dev/null'''
repl = '''    gh issue list -R "$1" --state all --limit 2000 --json number --jq '.[].number' 2>/dev/null'''
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d issues-API read sites, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, repl))
PYEOF
}

mutate_hdr() {  # drop the population line from the cache header
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = """      printf '# counts: fork %s / upstream %s (search index %s / %s)\\n' "$_fr_fork_n" "$_fr_up_n" "$_fr_fork_exp" "$_fr_up_exp"\n"""
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d counts-header lines, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, ""))
PYEOF
}

mutate_trunc() {  # neuter the search-index comparison
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
needle = '''     || [ "$_fr_fork_n" -lt "$_fr_fork_exp" ] || [ "$_fr_up_n" -lt "$_fr_up_exp" ]; then'''
repl = '''     || [ "$_fr_fork_n" -lt 0 ] || [ "$_fr_up_n" -lt 0 ]; then'''
n = src.count(needle)
if n != 1:
    sys.stderr.write("mutation: %d population comparisons, need exactly 1\n" % n)
    sys.exit(2)
open(path, "w", encoding="utf-8").write(src.replace(needle, repl))
PYEOF
}

# arm <name> <mutator> <expected-drop> <red:comma,list> <green:comma,list>
arm() {
  local name="$1" mutator="$2" drop="$3" reds="$4" greens="$5"
  local mut="$WORK/mut-$name" rc_m n_m t
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
  # each expected-red leg must carry its OWN FAIL token. Split on COMMA only:
  # leg tokens CONTAIN spaces ("leg-R population"), so a ${list//,/ } expansion
  # would word-split them into "leg-R" + "population" and every assertion would
  # match the wrong thing — measured 2026-10-17, this guard's first run.
  local oldifs="$IFS" t
  IFS=','
  for t in $reds; do
    grep -qF "FAIL $t" "$WORK/$name.out" \
      && ok "[$name] '$t' reddened" \
      || bad "[$name] '$t' did NOT redden — that leg does not guard this mutation"
  done
  # ...and each control must survive it
  for t in $greens; do
    grep -qF "FAIL $t" "$WORK/$name.out" \
      && bad "[$name] '$t' reddened too — the arm is not isolated" \
      || ok "[$name] '$t' survived"
  done
  IFS="$oldifs"
  # the drop must be EXACT: a token test cannot see a DELETED leg
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

arm pop   mutate_pop   2 'leg-R population,leg-R cache-provenance' 'leg-R truncation,leg-R arms,leg-R hex-control'
arm hdr   mutate_hdr   1 'leg-R cache-provenance'                   'leg-R population,leg-R truncation'
arm trunc mutate_trunc 1 'leg-R truncation'                         'leg-R population,leg-R cache-provenance'

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the population, provenance and truncation legs all redden under their own mutant and the pristine tree stays green"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
