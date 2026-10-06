#!/usr/bin/env bash
# Mutation guard for #301 — prove the squash-identity controls are LIVE, not
# vacuous.
#
# A negative control that cannot fail is decoration. Every section reverts ONE
# shipped #301 behaviour on a COPY of the tools tree and requires the owning
# selftest to FAIL on that copy, with the AIMED leg as the FIRST failure, while
# the unmutated copy stays green.
#
# #301 — harvest tooling is blind to upstream squash. GitHub records `mergedAt`
# only for a merge-button landing, so a hand-applied PR (squash / rebase /
# cherry-pick) reads CLOSED with mergedAt null. Before #301 that shape read as
# a REJECTION and the unit was offered for rework — the rework IS the duplicate
# upstream PR. TWO consumers, one predicate each:
#
#   [1] oc-harvest-census --selftest — the RESIDUAL classifier
#       (tools/lib/oc_claims.py `classify_closed_pr_landing`) for a CLOSED PR
#       the squash signature did not account for. Three arms, one mutant each:
#         unreadable_defaults_absent   -> leg 4a (the #301 defect itself)
#         absent_treated_unclassifiable-> leg 4b (the positive control)
#         ancestor_inverted            -> leg 4c (the 'present' arm)
#   [2] oc-harvest-census --selftest — the SIGNATURE promotion (a CLOSED PR
#       whose number `squash_signature` yields is promoted to MERGED before any
#       verdict). Mutant drops the promotion -> leg 12.
#   [3] oc-harvest-dispatch --selftest — `oc_claims.squash_signature` is the ONE
#       home for the commit-shape arms, and the dispatcher reads a hand-applied
#       landing through it (leg 1b). Mutant empties the function -> leg 8s.
#   [4] oc-harvest-dispatch --selftest — the widened `states=` that lets a
#       CLOSED PR reach leg 1b at all (check_upstream_pr skips CLOSED by
#       default). Mutant restores the default -> leg 8s.
#   [5] oc-harvest-dispatch --selftest — the BODY arm inside squash_signature
#       (`Squashed from PR #N` / `Closes #N`), the #288 mechanism: a landing
#       whose subject names the ISSUE and whose PR number lives ONLY in the
#       body (PR #1556 -> issue #133). Dropping it re-opens the false allow
#       #288 closed (`census check 133` -> ELIGIBLE rc=0). Mutant drops ONLY
#       that arm -> leg 8u, while the subject-shaped 8s stays green.
#
# The two dispatch mutants share leg 8s on purpose: one proves the signature
# decides, the other proves the widening is what lets it be consulted. Neither
# is reachable without the other, so a leg that survives either mutant would be
# testing half the path.
#
# Harness guards (AGENTS.md §Repro harnesses): explicit tool path, recursion
# guard, process budget cap.
set -u
[ "${OC_REPRO_DEPTH:-0}" -ge 1 ] && exit 99
export OC_REPRO_DEPTH=1
ulimit -u $(( $(ps -e --no-headers | wc -l) + 200 )) 2>/dev/null || true

# The tools tree under test is the one THIS GUARD SHIPS IN — resolved from the
# guard's own location, not from the deployed skill dir. SKILL_DIR lags the
# working tree until the post-merge skill sync, so a guard pinned to it would
# test stale bytes at exactly the moment it is written (measured 2026-10-06:
# the #301 legs and `classify_closed_pr_landing` exist only in the worktree
# while SKILL_DIR still carries the pre-#301 tool, and every anchor missed).
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$SRC/lib/oc-root.sh" ] || { echo "cannot resolve the tools dir from $0"; exit 2; }
#: The v0.4.255 regroup moved the fleet into kind subdirs; a flat
#: "$SRC/$CENSUS_REL" no longer resolves. One home for each location.
CENSUS_REL="harvest/oc-harvest-census"
DISPATCH_REL="harvest/oc-harvest-dispatch"
CLAIMS_REL="lib/oc_claims.py"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #301 mutation guard ==="

# --- baseline: one pristine copy, run once per tool, reused by every section --
if ! cp -a "$SRC" "$WORK/baseline"; then echo "copy failed"; exit 2; fi

run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s' "$out" > "$outfile"
  echo "$rc"
}

echo
echo "[baseline] pristine tools tree"
rc_base="$(run_st "$WORK/baseline/$CENSUS_REL" "$WORK/base-census.out")"
if [ "$rc_base" = "0" ]; then ok "baseline census GREEN (rc=0)"; else bad "baseline census rc=$rc_base (expected 0)"; fi
rc_base="$(run_st "$WORK/baseline/$DISPATCH_REL" "$WORK/base-dispatch.out")"
if [ "$rc_base" = "0" ]; then ok "baseline dispatch GREEN (rc=0)"; else bad "baseline dispatch rc=$rc_base (expected 0)"; fi

# --- a leg that is not GREEN on the pristine tree has nothing to redden ------
# Without this pre-check a mutant could "pass" because its aimed leg was already
# red, which proves nothing about the control.
require_green() {  # require_green <base-out> <grep-fixed-string> <label>
  if grep -qF -- "$2" "$1"; then
    ok "$3: aimed leg is GREEN on the pristine tree"
  else
    bad "$3: no green '$2' leg on the pristine tree — mutant would be vacuous"
    return 1
  fi
}
require_green "$WORK/base-census.out" "  ok   - #301: a CLOSED PR whose head ref is not local REFUSES as unclassifiable" "census 4a" || true
require_green "$WORK/base-census.out" "  ok   - #301: a CLOSED PR whose head commit is LOCAL and NOT an ancestor stays ELIGIBLE_REWORK" "census 4b" || true
require_green "$WORK/base-census.out" "  ok   - #301: a CLOSED PR whose head commit IS an ancestor of the upstream ref REFUSES" "census 4c" || true
require_green "$WORK/base-census.out" "  ok   - closed PR squash-merged upstream -> REFUSED MERGED exit 1" "census leg 12" || true
require_green "$WORK/base-dispatch.out" "  ok 8s - #301: a CLOSED PR whose squash commit IS local reads HARVESTED" "dispatch 8s" || true
require_green "$WORK/base-dispatch.out" "  ok 8u - #301 BODY arm: a PR keyed ONLY by the commit body reads HARVESTED" "dispatch 8u" || true

# --- apply a python mutation to a fresh copy of the tree --------------------
# apply_mutation <label> <rel-path-in-tree> <helper-file> ; helper is a python
# script taking (path, label) that must exit non-zero if the anchor is not
# exactly-once (a no-op mutation would make the whole guard vacuous while still
# reporting PASS on every leg below).
apply_mutation() {
  local label="$1" rel="$2" helper="$3" mut="$WORK/m_$1"
  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then bad "[$label] could not copy the tools tree"; return 1; fi
  if ! python3 "$helper" "$mut/$rel" "$label"; then
    bad "[$label] could not apply the mutation — guard is inert"
    return 1
  fi
  return 0
}

# --- first-bad-leg assertion ------------------------------------------------
# The census and dispatch selftests abort at the FIRST failing leg, so exactly
# one `bad` line is ever emitted. "The first bad leg is the leg aimed at" is
# therefore the strongest assertion available without splitting the suite: a
# mutant that reddened an UNRELATED leg is caught, and a mutant that reddened
# nothing at all is caught by the rc check.
assert_caught() {  # assert_caught <label> <tool> <want_bad_substr> <bad-prefix-re>
  local label="$1" tool="$2" want="$3" prefix="$4" mut="$WORK/m_$1" outf="$WORK/m_$1.out" rc_m=""
  rc_m="$(run_st "$mut/$tool" "$outf")"
  if [ "$rc_m" = "0" ]; then
    bad "[$label] mutant selftest PASSED — the control does not catch it"
    return
  fi
  if [ "$rc_m" = "126" ] || [ "$rc_m" = "127" ]; then
    bad "[$label] mutant never RAN (rc=$rc_m) — 126/127 is a harness fault, never a catch"
    return
  fi
  local first_bad
  first_bad="$(grep -m1 -E "$prefix" "$outf" | sed -E 's/^  bad[^ -]* *- //')"
  if [ -z "$first_bad" ]; then
    bad "[$label] mutant rc=$rc_m but emitted no 'bad' leg — failure is not a leg"
  elif grep -qF -- "$want" <<< "$first_bad"; then
    ok "[$label] CAUGHT (rc=$rc_m) — first failure is the aimed leg"
    printf '%s\n' "         $first_bad" | cut -c1-140
  else
    bad "[$label] mutant reddened the WRONG leg: $first_bad"
  fi
}

# --- [1] census residual classifier (3 arms) --------------------------------
echo
echo "[1] census residual classifier — tools/lib/oc_claims.py classify_closed_pr_landing"
cat > "$WORK/mut_classifier.py" <<'PYEOF'
import re, sys
path, label = sys.argv[1], sys.argv[2]
MUTATIONS = {
    # the #301 DEFECT itself: an unreadable head ref falls through to the allow
    "unreadable_defaults_absent": (
        "    if not commits_readable:\n        return None\n    return 'absent'\n",
        "    return 'absent'\n",
    ),
    # the readable-but-not-ancestor arm stops being distinguishable from the
    # unreadable one, so rework is refused even when it is legitimate
    "absent_treated_unclassifiable": (
        "    if not commits_readable:\n        return None\n    return 'absent'\n",
        "    if not commits_readable:\n        return None\n    return None\n",
    ),
    # the 'present' arm inverted: an ancestor head commit reads as absent
    "ancestor_inverted": (
        "    if ancestor_hit:\n        return 'present'\n",
        "    if ancestor_hit:\n        return 'absent'\n",
    ),
}
if label not in MUTATIONS:
    sys.stderr.write("unknown mutation %r\n" % label)
    sys.exit(2)
anchor, repl = MUTATIONS[label]
src = open(path).read()
n = src.count(anchor)
if n != 1:
    sys.stderr.write("mutation %s: anchor occurs %d times, need exactly 1\n" % (label, n))
    sys.exit(2)
open(path, "w").write(src.replace(anchor, repl))
print("  mutated: %s (anchor occurrences=%d)" % (label, n))
PYEOF

for spec in \
  "unreadable_defaults_absent|unclassifiable CLOSED PR expected" \
  "absent_treated_unclassifiable|absent-landing CLOSED PR expected" \
  "ancestor_inverted|present-landing CLOSED PR expected" ; do
  label="${spec%%|*}"; want="${spec#*|}"
  if apply_mutation "$label" "$CLAIMS_REL" "$WORK/mut_classifier.py"; then
    assert_caught "$label" "$CENSUS_REL" "$want" '^  bad  - '
  fi
done

# --- [2] census signature promotion -----------------------------------------
echo
echo "[2] census signature promotion — CLOSED -> MERGED before any verdict"
cat > "$WORK/mut_promotion.py" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
anchor = "    if p.get('state') == 'CLOSED' and num in squashed_prs:\n"
repl = "    if False and p.get('state') == 'CLOSED' and num in squashed_prs:\n"
src = open(path).read()
n = src.count(anchor)
if n != 1:
    sys.stderr.write("mutation %s: anchor occurs %d times, need exactly 1\n" % (label, n))
    sys.exit(2)
open(path, "w").write(src.replace(anchor, repl))
print("  mutated: %s (anchor occurrences=%d)" % (label, n))
PYEOF
if apply_mutation "promotion_dropped" "$CENSUS_REL" "$WORK/mut_promotion.py"; then
  assert_caught "promotion_dropped" "$CENSUS_REL" "squash-merged upstream expected" '^  bad  - '
fi

# --- [3] the ONE home for the commit-shape arms ------------------------------
echo
echo "[3] dispatcher signature read — oc_claims.squash_signature emptied"
cat > "$WORK/mut_signature.py" <<'PYEOF'
import re, sys
path, label = sys.argv[1], sys.argv[2]
src = open(path).read()
# ASCII-only replacement, and the docstring is dropped with the body: a stub
# that returns {} is the pre-#301 state this mutant exists to restore.
STUB = ("def squash_signature(log_lines):\n"
        "    return {}\n\n")
pat = re.compile(r'^def squash_signature\(.*?(?=^def )', re.S | re.M)
new, n = pat.subn(STUB, src)
if n != 1:
    sys.stderr.write("mutation %s: expected exactly 1 substitution, got %d\n" % (label, n))
    sys.exit(2)
open(path, "w").write(new)
print("  mutated: squash_signature -> {} (substitutions=%d)" % n)
PYEOF
if apply_mutation "signature_empty" "$CLAIMS_REL" "$WORK/mut_signature.py"; then
  assert_caught "signature_empty" "$DISPATCH_REL" "hand-applied CLOSED PR #1441 expected HARVESTED" '^  bad '
fi

# --- [4] the widened states= that reaches leg 1b -----------------------------
echo
echo "[4] dispatcher CLOSED widening — check_upstream_pr back to its default states"
cat > "$WORK/mut_states.py" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
anchor = ("    _pr_closed = check_upstream_pr(issue_num, upstream_repo, mock_prs=mock_prs,\n"
          "                                   states=('MERGED', 'OPEN', 'CLOSED'))\n")
repl = "    _pr_closed = check_upstream_pr(issue_num, upstream_repo, mock_prs=mock_prs)\n"
src = open(path).read()
n = src.count(anchor)
if n != 1:
    sys.stderr.write("mutation %s: anchor occurs %d times, need exactly 1\n" % (label, n))
    sys.exit(2)
open(path, "w").write(src.replace(anchor, repl))
print("  mutated: %s (anchor occurrences=%d)" % (label, n))
PYEOF
if apply_mutation "states_not_widened" "$DISPATCH_REL" "$WORK/mut_states.py"; then
  assert_caught "states_not_widened" "$DISPATCH_REL" "hand-applied CLOSED PR #1441 expected HARVESTED" '^  bad '
fi

# --- [5] the BODY arm inside squash_signature (the #288 mechanism) -----------
# A landing whose SUBJECT names the ISSUE and whose PR number exists ONLY in the
# commit body (PR #1556 -> issue #133) is keyed by no shape arm. Dropping the
# BODY arm re-opens the false allow #288 closed, while leg 8s -- a landing whose
# subject DOES carry `(#1441)` -- stays green, so the FIRST failure is 8u.
echo
echo "[5] dispatcher body arm — squash_signature loses its BODY arm"
cat > "$WORK/mut_body_arm.py" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
# Drop ONLY the body arm; the SUBJECT/MERGE arms stay, so the subject-shaped
# leg 8s stays green and the first reddened leg is 8u (keyed only by the body).
anchor = ("        body = parts[3] if len(parts) > 3 else ''\n"
          "        for bm in _BODY_SQUASH_RE.finditer(body):\n"
          "            out.setdefault(int(bm.group(1)), sha)\n")
src = open(path).read()
n = src.count(anchor)
if n != 1:
    sys.stderr.write("mutation %s: anchor occurs %d times, need exactly 1\n" % (label, n))
    sys.exit(2)
open(path, "w").write(src.replace(anchor, ""))
print("  mutated: %s (anchor occurrences=%d)" % (label, n))
PYEOF
if apply_mutation "body_arm_dropped" "$CLAIMS_REL" "$WORK/mut_body_arm.py"; then
  assert_caught "body_arm_dropped" "$DISPATCH_REL" "body-only landing for PR #1441 expected HARVESTED" '^  bad '
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — every #301 control fails under its mutant"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
