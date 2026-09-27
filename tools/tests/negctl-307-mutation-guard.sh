#!/usr/bin/env bash
# Mutation guards for #307, #365 and #375 — prove the negative controls are
# LIVE, not vacuous.
#
# A negative control that cannot fail is decoration. Each section reverts one
# shipped behaviour on a COPY of the tools tree and requires the selftests to
# FAIL on that copy while the unmutated copy stays green. If a control passes
# under the mutant, it is not testing what it claims to.
#
# #307 — anchored Issue-Ref fencing. Reverts the matcher to the pre-#307
# unanchored `git log --grep=#N`. Covers all three control sites:
#   (1) tools/harvest/oc-harvest-census --selftest
#   (2) tools/harvest/oc-harvest-dispatch --selftest   (legs 11e/11f)
#   (3) tools/tests/run.sh §00c lib/oc_claims unit cases
#
# #365 — the gate-4 SUBJECT predicate (symbol derivation + the declared-subject
# fallback). §4 reverts that predicate four ways, one per gate-4 shape, and
# requires the shape's own leg to be the FIRST failure on its mutant. The legs
# abort the suite on first failure, so "first bad leg == the leg aimed at" is
# the strongest assertion available without splitting the suite.
#
# #375 — the shared-declaration-registry exemption in the HELD_IN_FLIGHT_LANE
# fence. A fifth mutation (same §4 machinery) drops the filter call and requires
# the registry-only leg to be the FIRST failure, proving that leg is
# load-bearing rather than decoration.
#
# Harness guards (AGENTS.md §Repro harnesses): explicit tool path, recursion
# guard, process budget cap.
set -u
[ "${OC_REPRO_DEPTH:-0}" -ge 1 ] && exit 99
export OC_REPRO_DEPTH=1
ulimit -u $(( $(ps -e --no-headers | wc -l) + 200 )) 2>/dev/null || true

SKILL_DIR="/root/.opencrabs/profiles/ops/skills/opencrabs-dev"
SRC="$SKILL_DIR/tools"
#: The v0.4.255 regroup moved the fleet into kind subdirs; a flat
#: "$SRC/$CENSUS_REL" no longer resolves. One home for each location.
CENSUS_REL="harvest/oc-harvest-census"
DISPATCH_REL="harvest/oc-harvest-dispatch"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #307 mutation guard ==="

# --- two independent copies of the tools tree -------------------------------
cp -a "$SRC" "$WORK/baseline" || { echo "copy failed"; exit 2; }
cp -a "$SRC" "$WORK/mutant"   || { echo "copy failed"; exit 2; }

# --- mutate the matcher back to the pre-#307 unanchored form ----------------
if ! python3 - "$WORK/mutant/lib/oc_claims.py" <<'PYEOF'
import re, sys
path = sys.argv[1]
src = open(path).read()
MUTANT = '''def resolve_issue_commits(repo_path, iss, ref="--all", index=None):
    """MUTANT (mutation guard): the pre-#307 unanchored grep."""
    out = _git(repo_path, "log", "-n", "10", "--grep=#%d" % int(iss), "--format=%H")
    if not out:
        return []
    return [s.strip() for s in out.split() if s.strip()]


'''
pat = re.compile(r'^def resolve_issue_commits\(.*?(?=^def )', re.S | re.M)
new, n = pat.subn(MUTANT, src)
if n != 1:
    sys.stderr.write("mutation guard: expected exactly 1 substitution, got %d\n" % n)
    sys.exit(2)
open(path, "w").write(new)
print("  mutated: resolve_issue_commits -> unanchored `git log --grep=#N`")
PYEOF
then
  bad "could not apply the mutation — guard is inert"
  echo
  echo "MUTATION GUARD FAILED (failures=$fails)"
  exit 1
fi

# Confirm the mutant really is the unanchored form (a no-op mutation would make
# this whole guard vacuous while still reporting PASS on every leg below).
if grep -q 'MUTANT (mutation guard)' "$WORK/mutant/lib/oc_claims.py" \
   && grep -q -- '--grep=#%d' "$WORK/mutant/lib/oc_claims.py"; then
  ok "mutant carries the unanchored grep"
else
  bad "mutant does not carry the unanchored grep — guard is inert"
fi

# --- extract the §00c lib unit cases from run.sh ----------------------------
sed -n '/cat > "\$OCT\/unit.py" << .PYEOF./,/^PYEOF$/p' "$SRC/tests/run.sh" \
  | sed '1d;$d' > "$WORK/unit.py"
if [ -s "$WORK/unit.py" ]; then
  ok "extracted lib unit cases ($(wc -l < "$WORK/unit.py" | tr -d '[:space:]') lines)"
else
  bad "could not extract lib unit cases from run.sh"
fi

# --- run a selftest, report its rc -----------------------------------------
run_st() {  # run_st <label> <tool-path> [outfile] -> echoes rc
  local label="$1" tool="$2" outfile="${3:-}" rc=0 out=""
  out="$(timeout 600 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s' "$out" > "$WORK/last.out"
  if [ -n "$outfile" ]; then printf '%s' "$out" > "$outfile"; fi
  echo "$rc"
}

# --- (1) census -------------------------------------------------------------
echo
echo "[1] oc-harvest-census --selftest"
rc_base="$(run_st census "$WORK/baseline/$CENSUS_REL")"
if [ "$rc_base" = "0" ]; then ok "baseline census GREEN (rc=0)"; else bad "baseline census rc=$rc_base (expected 0)"; fi
rc_mut="$(run_st census-mut "$WORK/mutant/oc-harvest-census")"
if [ "$rc_mut" != "0" ]; then
  ok "mutant census CAUGHT (rc=$rc_mut)"
  grep -m1 -iE 'prose|fence|#307' "$WORK/last.out" | sed 's/^/         /' || true
else
  bad "mutant census PASSED — the prose-only control does not catch the regression"
fi

# --- (2) dispatch -----------------------------------------------------------
echo
echo "[2] oc-harvest-dispatch --selftest"
rc_base="$(run_st dispatch "$WORK/baseline/$DISPATCH_REL")"
if [ "$rc_base" = "0" ]; then ok "baseline dispatch GREEN (rc=0)"; else bad "baseline dispatch rc=$rc_base (expected 0)"; fi
rc_mut="$(run_st dispatch-mut "$WORK/mutant/oc-harvest-dispatch")"
if [ "$rc_mut" != "0" ]; then
  ok "mutant dispatch CAUGHT (rc=$rc_mut)"
  grep -m1 -E 'bad 11e|bad 11f|#307' "$WORK/last.out" | sed 's/^/         /' || true
else
  bad "mutant dispatch PASSED — legs 11e/11f do not catch the regression"
fi

# --- (3) lib unit cases -----------------------------------------------------
echo
echo "[3] lib/oc_claims unit cases (run.sh 00c)"
if python3 "$WORK/unit.py" "$WORK/baseline/lib" >"$WORK/unit_base.out" 2>&1; then
  ok "baseline lib unit cases GREEN"
else
  bad "baseline lib unit cases failed (expected green)"
  sed 's/^/         /' "$WORK/unit_base.out" | head -5
fi
if python3 "$WORK/unit.py" "$WORK/mutant/lib" >"$WORK/unit_mut.out" 2>&1; then
  bad "mutant lib unit cases PASSED — the #307 cases do not catch the regression"
else
  ok "mutant lib unit cases CAUGHT"
  grep -m1 -E '#307' "$WORK/unit_mut.out" | sed 's/^/         /' || true
fi

# --- (4) #365 gate-4 subject predicate --------------------------------------
# The #365 predicate is what decides whether a fork-only fix's SUBJECT exists
# upstream. §4 reverts it four ways -- one per gate-4 shape -- and requires each
# shape's OWN leg to be the FIRST failure on its mutant.
#
# Why "first failure" and not "all four legs": the census selftest returns 1 at
# the first failing leg, so exactly one `bad` line is ever emitted. That makes
# "the first bad leg is the leg aimed at" the strongest available assertion
# without splitting the suite, and it is sufficient -- a mutant that reddened
# some UNRELATED leg would be caught, and a mutant that reddened nothing at all
# is caught by the rc check.
echo
echo "[4] #365 gate-4 subject predicate + #375 in-flight registry exemption (oc-harvest-census --selftest)"

base365="$WORK/base365.out"
rc_base="$(run_st base365 "$SRC/$CENSUS_REL" "$base365")"
if [ "$rc_base" = "0" ]; then
  ok "baseline census GREEN (rc=0, $(grep -c '^  ok   - ' "$base365") legs)"
else
  bad "baseline census rc=$rc_base (expected 0)"
fi

for label in case_a_dropped refuse_all_absent parent_number_dropped empty_derivation_unnamed registry_filter_dropped; do
  case "$label" in
    case_a_dropped)           want_ok="#253 shape:"            want_bad="subject-absent fixture" ;;
    refuse_all_absent)        want_ok="#341 shape:"            want_bad="orphan-subject fixture" ;;
    parent_number_dropped)    want_ok="parent-harvested shape:" want_bad="harvested-parent fixture" ;;
    empty_derivation_unnamed) want_ok="inconclusive shape:"    want_bad="inconclusive fixture" ;;
    registry_filter_dropped)  want_ok="check registry-only in-flight overlap -> ELIGIBLE exit 0 (shared-registry exemption)" want_bad="registry-only overlap" ;;
  esac

  # The aimed leg must be GREEN on the pristine tree, or there is nothing to
  # redden and this mutant proves nothing.
  if ! grep -q -- "^  ok   - $want_ok" "$base365"; then
    bad "[$label] baseline has no green '$want_ok' leg — mutant would be vacuous"
    continue
  fi

  mut="$WORK/m365_$label"
  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then
    bad "[$label] could not copy the tools tree"
    continue
  fi

  if ! python3 - "$mut/$CENSUS_REL" "$label" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
# ASCII-only anchors, deliberately: the census source carries em-dashes and this
# heredoc is fed to python3 on stdin, so a non-ASCII anchor is one encoding
# surprise away from a silent no-op.
MUTATIONS = {
    # revert the derivation's POSITIVE-EVIDENCE branch: an all-absent
    # derivation stops refusing and falls through to ELIGIBLE (case (a) gone).
    "case_a_dropped": (
        "        if not present_syms:",
        "        if not present_syms and not absent_syms:",
    ),
    # revert class 2 to a bare file-existence test: every absent path refuses,
    # so the orphan ADVISORY shape can no longer pass.
    "refuse_all_absent": (
        "port decision required' % f_path)",
        "port decision required' % f_path)\n                    sys.exit(1)",
    ),
    # revert the harvested-parent sub-rule's EVIDENCE: it still falls through,
    # but the advisory stops naming the parent it consulted.
    "parent_number_dropped": (
        "parent #%s already harvested; port decision required' % (f_path, intro_iss))",
        "port decision required' % f_path)",
    ),
    # revert the INCONCLUSIVE branch's report: the derivation is still empty,
    # but the refusal stops saying so, so the branch is no longer identifiable.
    "empty_derivation_unnamed": (
        "tested = ', '.join(absent_syms[:6]) or 'none derived'",
        "tested = ', '.join(absent_syms[:6]) or 'symbols omitted'",
    ),
    # #375: drop the shared-declaration-registry filter from the IN-FLIGHT
    # fence, so a registry-only overlap fences again. The anchor is FOUR lines
    # because the soak gate carries the SAME first line -- only the in-flight
    # block follows `substantive_overlap` with `c_uuid`, which is what makes
    # this anchor unique (verified: short form occurs 2x, this form 1x).
    "registry_filter_dropped": (
        "            substantive_overlap = filter_substantive_overlap(overlap)\n"
        "            if substantive_overlap:\n"
        "                overlap_sample = ', '.join(sorted(list(substantive_overlap))[:3])\n"
        "                c_uuid = claim.get('uuid', '')[:8]",
        "            substantive_overlap = overlap\n"
        "            if substantive_overlap:\n"
        "                overlap_sample = ', '.join(sorted(list(substantive_overlap))[:3])\n"
        "                c_uuid = claim.get('uuid', '')[:8]",
    ),
}
if label not in MUTATIONS:
    sys.stderr.write("unknown mutation %r\n" % label)
    sys.exit(2)
anchor, repl = MUTATIONS[label]
src = open(path).read()
n = src.count(anchor)
if n != 1:
    sys.stderr.write("mutation %s: anchor occurs %d times, need exactly 1\n"
                     % (label, n))
    sys.exit(2)
open(path, "w").write(src.replace(anchor, repl))
print("  mutated: %s (anchor occurrences=%d)" % (label, n))
PYEOF
  then
    bad "[$label] could not apply the mutation — guard is inert"
    continue
  fi

  outf="$WORK/m365_$label.out"
  rc_m="$(run_st "m365-$label" "$mut/$CENSUS_REL" "$outf")"
  if [ "$rc_m" = "0" ]; then
    bad "[$label] mutant census PASSED — the '$want_ok' leg does not catch it"
    continue
  fi
  first_bad="$(grep -m1 '^  bad  - ' "$outf" | sed 's/^  bad  - //')"
  if [ -z "$first_bad" ]; then
    bad "[$label] mutant rc=$rc_m but emitted no 'bad' leg — failure is not a leg"
  elif grep -qF -- "$want_bad" <<< "$first_bad" ; then
    ok "[$label] CAUGHT — first failure is the $want_ok leg"
    printf '%s\n' "         $first_bad" | cut -c1-150
  else
    bad "[$label] mutant reddened the WRONG leg: $first_bad"
  fi
done

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — every #307, #365 and #375 control fails under its mutant"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
