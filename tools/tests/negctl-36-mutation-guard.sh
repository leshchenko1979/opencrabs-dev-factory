#!/usr/bin/env bash
# Mutation guard for #36 — prove the ASSIGNEE and TRAILER-PARENT legs are LIVE.
#
# #36 (creation-gate legs (a) and (c)): `tools/issue/oc-issue-create` documented
# `--assignee` as "passed through to gh unchanged" and had NO handling for it, so
# every filing lane carried the assignment leg BY HAND. The constant in use,
# `adolfousier`, had also gone dead: he is not a collaborator on the fork, and
# `--add-assignee adolfousier` NO-OPS with rc 0 -- the failure reads as SUCCESS,
# which is why it survived a day. Separately, where the origin is a
# `--root upstream:<sha>` commit the parent is derivable from that commit's own
# `Closes #N` / `Fixes #N` trailer, and that derivation did not exist.
#
# This guard proves the legs that pin BOTH capabilities can FAIL. A leg that
# passes with the capability deleted tests nothing -- "a leg that cannot fail is
# decoration". It stages a tools/ tree in a temp dir, applies one surgical
# mutation per item, and requires the AIMED legs to redden while the pristine
# tree stays FAIL=0.
#
# ASSERTION SHAPE. This selftest DOES print a per-leg line for every leg, so the
# strong, leg-identifying form is available and is used here: a token must appear
# on an `ok` line of the pristine tree AND on a `FAIL` line under the mutation.
# Requiring BOTH halves is what makes the assertion leg-identifying -- a token
# that merely appears somewhere in the output proves nothing, and a token seen
# only under the mutation could be an artefact of the mutation rather than the
# leg it claims to name. (Contrast negctl-34, whose two selftests emit NO per-leg
# line and so must assert an exact pass-count drop plus a direct probe.)
#
# THE LABEL IS BRANCH-DEPENDENT, so the tokens below are STABLE PREFIXES matched
# as SUBSTRINGS, never whole lines. Two leg helpers shape the label differently:
#   has/hasnt  ->  `  ok   - <label>`   /  `  FAIL - <label>`          (stable)
#   chk :344   ->  `  ok   - <label> (rc=$3)`  vs  `  FAIL - <label> (want rc=$2 got $3)`
# So an exact-line assertion holds only for has/hasnt legs; for a `chk` leg the
# label's stable part is its prefix, and the `(want …)` tail exists only on the
# failing side. Matching the prefix is therefore the only form that can demand
# the token on BOTH sides -- and demanding both sides is exactly what caught this
# asymmetry rather than silently keying the guard on the fail-side text.
#
# MUTATION SURGERY. The mutation must remove EXACTLY the capability under test.
# A first cut of mutation B anchored on `^if [ "$ROOT_SET" = 1 ]`, which matches
# TWO sites -- the derivation guard AND the earlier root-validation block -- and
# reddened 12 legs, including unrelated `--root` refusal legs. A guard built on
# that would have claimed to protect the derivation while actually proving the
# root resolver was broken. The anchor used here (`_derived="$(printf`) is unique
# to the derivation.
#
# Standalone by design -- the negctl-* family is not wired into tools/tests/run.sh;
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
#: tree (OC_NEGCTL_SRC=...) and shown to exit non-zero -- i.e. shown to detect a
#: real regression, not only to convict its own internal mutant. Without that
#: affordance the only way to test the regression path is to break the live tree.
#: SRC must be a `tools/`-shaped directory (needs lib/ and issue/oc-issue-create).
SRC="${OC_NEGCTL_SRC:-$SKILL_DIR/tools}"
REL="issue/oc-issue-create"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FAILS=0
bad() { echo "  !! $*"; FAILS=$((FAILS + 1)); }

# stage <name> -- a tools/ tree holding lib/ + the tool under test, so the tool's
# own OC_TOOLS_DIR walk-up resolves against the COPY and never the live tree.
stage() {
  local d="$WORK/$1"
  mkdir -p "$d/issue"
  cp -a "$SRC/lib" "$d/lib" || { bad "cannot stage lib/ from $SRC"; return 1; }
  cp -a "$SRC/$REL" "$d/issue/oc-issue-create" || { bad "cannot stage $SRC/$REL"; return 1; }
  chmod +x "$d/issue/oc-issue-create"
  printf '%s' "$d"
}

# st <dir> -- the hermetic selftest (its own stub gh lives in its own mktemp dir,
# so no network is touched and the staging dir needs no gh).
st() { bash "$1/issue/oc-issue-create" --selftest 2>&1; }
fails() { grep -E '^  FAIL +- ' | sed -E 's/^  FAIL +- +//'; }
oks() { grep -E '^  ok +- ' | sed -E 's/^  ok +- +//'; }
failn() { printf '%s\n' "$1" | grep -oE 'FAIL=[0-9]+' | grep -oE '[0-9]+'; }

# A tiny stub gh for the DIRECT probes below: they run the tool OUTSIDE the
# selftest, where the selftest's own stub is not in scope. Answers rc 0 for the
# assignee check so a pristine run resolves without touching the network.
mkdir -p "$WORK/bin"
cat > "$WORK/bin/gh" <<'STUB'
#!/bin/sh
exit 0
STUB
chmod +x "$WORK/bin/gh"

echo "=== baseline: pristine $SRC ==="
P="$(stage pristine)" || exit 1
POUT="$(st "$P")"
PN="$(failn "$POUT")"
printf '%s\n' "$POUT" | tail -1
[ "$PN" = "0" ] || bad "baseline selftest is not FAIL=0 (FAIL=$PN) -- a guard cannot read a broken baseline"

# --- ITEM 1: the assignee leg --------------------------------------------------
# Mutation A removes the DEFAULT: the declaration then reads `assignee=none` and
# nothing is passed to gh, which is exactly the silent-unassigned filing the
# capability exists to prevent.
echo "=== mutation A: DEFAULT_ASSIGNEE emptied ==="
A="$(stage mutA)" || exit 1
sed -i 's/^DEFAULT_ASSIGNEE=.*/DEFAULT_ASSIGNEE=""/' "$A/issue/oc-issue-create"
grep -q '^DEFAULT_ASSIGNEE=""$' "$A/issue/oc-issue-create" \
  || bad "mutation A did not apply (no DEFAULT_ASSIGNEE line to empty) -- SRC looks pre-#36"
AOUT="$(st "$A")"
AN="$(failn "$AOUT")"
echo "  baseline FAIL=0 -> mutant A FAIL=$AN"
for tok in '…and is declared on stdout' '…and reaches gh'; do
  printf '%s\n' "$POUT" | oks   | grep -qF "$tok" || bad "aimed token not an ok line on the pristine tree: $tok"
  printf '%s\n' "$AOUT" | fails | grep -qF "$tok" || bad "mutation A did NOT redden: $tok"
done

# Direct probe: the declaration must INVERT. The selftest tokens above name the
# legs; this pins the user-visible behaviour they read.
export OC_ISSUE_CREATE_GH="$WORK/bin/gh"
PD="$(bash "$P/issue/oc-issue-create" --title 'feat(tools): probe' --body x --dry-run 2>&1)"
grep -q 'assignee=leshchenko1979' <<< "$PD" \
  || bad "pristine probe: declaration is not assignee=leshchenko1979"
AD="$(bash "$A/issue/oc-issue-create" --title 'feat(tools): probe' --body x --dry-run 2>&1)"
grep -q 'assignee=none' <<< "$AD" \
  || bad "mutation A probe: declaration did not invert to assignee=none"

# --- ITEM 2: the trailer-derived parent ---------------------------------------
# Mutation B neuters ONLY the derivation (`_derived` never gets a value). The
# anchor is unique to that assignment -- anchoring on the guard condition would
# also hit the root-validation block and prove the wrong thing.
echo "=== mutation B: trailer derivation neutered ==="
B="$(stage mutB)" || exit 1
sed -i 's|^    _derived="\$(printf.*|    _derived=""|' "$B/issue/oc-issue-create"
grep -q '^    _derived=""$' "$B/issue/oc-issue-create" \
  || bad "mutation B did not apply (no _derived=\$(printf line) -- SRC looks pre-#36"
BOUT="$(st "$B")"
BN="$(failn "$BOUT")"
echo "  baseline FAIL=0 -> mutant B FAIL=$BN"
for tok in '…and the parent is derived' \
           '…and the derivation is declared' \
           'a trailer naming an UNRESOLVABLE number REFUSES' \
           '…and names the cross-tracker hazard'; do
  printf '%s\n' "$POUT" | oks   | grep -qF "$tok" || bad "aimed token not an ok line on the pristine tree: $tok"
  printf '%s\n' "$BOUT" | fails | grep -qF "$tok" || bad "mutation B did NOT redden: $tok"
done

# Direct probe: with the derivation dead, the cross-tracker refusal must NOT
# fire. (The positive direction -- a derived parent being attached -- needs the
# selftest's stub, and is carried by the named legs above.)
BD="$(OC_ISSUE_CREATE_GH="$WORK/bin/gh" bash "$B/issue/oc-issue-create" \
      --title 'fix(tools): probe' --body x \
      --root upstream:cccccccccccccccccccccccccccccccccccccccc --dry-run 2>&1; echo "rc=$?")"
grep -q 'CROSS-TRACKER HAZARD' <<< "$BD" \
  && bad "mutation B probe: the cross-tracker refusal fired with the derivation dead"
grep -q '^rc=0' <<< "$BD" \
  || bad "mutation B probe: expected rc 0 with the derivation dead"

echo
if [ "$FAILS" -eq 0 ]; then
  echo "MUTATION GUARD PASSED: both mutations redden their aimed legs; pristine tree FAIL=0"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$FAILS)"
exit 1
