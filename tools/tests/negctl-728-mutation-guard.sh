#!/usr/bin/env bash
# Mutation guard for #728 — prove the `--session-id-only` legs are LIVE, not
# vacuous.
#
# #728: `oc-commit` had NO route for a commit that belongs to no issue. The
# Issue-Ref derivation was MANDATORY whenever `--issue` was absent, so the only
# way to commit a tools/** self-commit or a hygiene sweep was to borrow an
# unrelated OPEN claim's number — and the wrapper then posted an implementation
# comment onto THAT issue. Fork #465 carries a false comment of exactly this
# shape. The fix adds `--session-id-only`: Session-Id alone, no Issue-Ref, no
# post-commit comment, no #501 cross-check, and rc 2 when combined with
# `--issue` (the two are unsatisfiable together).
#
# A leg that cannot fail is decoration. Each section reverts ONE shipped
# property on a COPY of the tools tree and requires `oc-commit --selftest` to
# fail on that copy while the unmutated copy stays green.
#
# THE COPY IS A REAL `cp -a` OF THE WHOLE TREE, never a symlink farm. oc-commit
# bootstraps its tools dir by walking up for a REAL (non-symlink) `lib/`, so a
# mirror built from symlinked directories silently resolves OC_TOOLS_DIR to the
# mirror root, loses `lib/oc_claims.py` on the python path, and fails EVERY leg
# at the first one — which reads as "the mutant was caught" while proving
# nothing. Measured while writing this guard: a symlink-farm mirror failed the
# baseline itself (`OPENCRABS_SESSION_ID fallback != 0`, oc-ledger dying on
# ModuleNotFoundError). The baseline control below is what catches that class.
#
# ASSERTION SHAPE — oc-commit's selftest ABORTS at the first failing leg
# (`exit 1`), unlike oc-health which counts and continues. So exactly ONE
# `selftest: <label>` line can exist per mutant, and the strongest available
# assertion is: the mutant fails, and the FIRST (hence only) failing leg is the
# leg aimed at. Shadowing is stated rather than hidden: a mutation that reddens
# leg 10a's first assertion also hides its later ones. Every aimed leg below is
# therefore reachable as a FIRST failure under its own mutant.
#
# Standalone by design — the negctl-* family is not wired into
# tools/tests/run.sh; it is run deliberately when the legs it guards change.
#
# Harness guards (AGENTS.md §Repro harnesses): explicit tool path, recursion
# guard, process budget cap, timeout.
set -u
[ "${OC_REPRO_DEPTH:-0}" -ge 1 ] && exit 99
export OC_REPRO_DEPTH=1
ulimit -u $(( $(ps -e --no-headers | wc -l) + 200 )) 2>/dev/null || true

SKILL_DIR="/root/.opencrabs/profiles/ops/skills/opencrabs-dev"
SRC="$SKILL_DIR/tools"
#: The v0.4.255 regroup moved the fleet into kind subdirs, so a flat
#: "$SRC/$COMMIT_REL" no longer resolves. One home for the location.
COMMIT_REL="git/oc-commit"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #728 mutation guard (oc-commit --session-id-only) ==="

# --- run a copy's selftest; echoes its rc ------------------------------------
# oc-commit writes gate + warning lines to STDERR, so the capture merges 2>&1.
run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 600 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

# --- baseline: the pristine tree must be GREEN -------------------------------
# This is also the POSITIVE CONTROL for the mirror construction: a mirror that
# cannot run the suite at all fails here rather than masquerading as a caught
# mutant further down.
cp -a "$SRC" "$WORK/baseline" || { echo "copy failed"; exit 2; }
base_out="$WORK/baseline.out"
rc_base="$(run_st "$WORK/baseline/$COMMIT_REL" "$base_out")"
if [ "$rc_base" = "0" ]; then
  ok "baseline oc-commit --selftest GREEN (rc=0)"
else
  bad "baseline oc-commit rc=$rc_base (expected 0) — the guard would be inert: $(grep -m1 '^selftest: ' "$base_out")"
fi
grep -q '^selftest OK$' "$base_out" \
  && ok "baseline prints the OK marker" \
  || bad "baseline did not print 'selftest OK'"

# The guard is vacuous unless the pristine tree carries the legs it later
# requires to redden. Assert the leg labels are present in the tool source — a
# mutant can only redden a leg that exists, and a renamed leg would otherwise
# silently disable this whole guard.
for leg in '#728-sid-only-rc0' '#728-sid-only-no-ref' '#728-sid-only-announced' \
           '#728-sid-only-conflict' '#728-control-derivation' \
           '#728-sid-only-no-comment' '#728-control-comment'; do
  if grep -q "$leg" "$SRC/$COMMIT_REL"; then
    ok "baseline carries leg '$leg'"
  else
    bad "leg '$leg' is MISSING from oc-commit — the guard would be vacuous"
  fi
done

# --- mutations ---------------------------------------------------------------
# label|anchor|replacement  (ASCII anchors only: this heredoc is fed to python3
# on stdin, so a non-ASCII anchor — every comment in oc-commit carries an
# em-dash — is one encoding surprise from a silent no-op)
mutate() {  # mutate <tree> <label> -> rc 0 on success
  python3 - "$1/$COMMIT_REL" "$2" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
MUTATIONS = {
    # The flag stops suppressing the derivation: the tool still derives #149
    # from the actor's open claim and ANNOUNCES a ref it did not emit. The
    # commit's trailer stays correct, so the misleading stderr is the whole
    # defect — which is exactly why 10a asserts the announcement and not only
    # the trailer's absence.
    "derivation_ignores_flag": [
        ('if [ "$SESSION_ID_ONLY" = 0 ] && [ -z "$ISSUE" ]; then',
         'if [ -z "$ISSUE" ]; then'),
    ],
    # The post-commit comment leg loses its issue gate: with the env defaults
    # (OC_COMMIT_COMMENT=1, NO_COMMENT=0) it runs and the implementation comment
    # lands on an issue the commit never claimed.
    "comment_not_gated": [
        ('if [ "$SESSION_ID_ONLY" = 0 ] && [ "$NO_COMMENT" = 0 ] && [ "${OC_COMMIT_COMMENT:-1}" = 1 ]; then',
         'if [ "$NO_COMMENT" = 0 ] && [ "${OC_COMMIT_COMMENT:-1}" = 1 ]; then'),
    ],
    # The trailer branch always emits Issue-Ref, so the flag produces a ref it
    # promised not to produce.
    "trailer_always_ref": [
        ('  _TRAILERS=(--trailer "Session-Id: $OC_ACTOR")\n',
         '  _TRAILERS=(--trailer "Session-Id: $OC_ACTOR" --trailer "Issue-Ref: #$ISSUE")\n'),
    ],
    # The contradiction check is dropped: `--session-id-only --issue 42` is
    # accepted instead of refused, so a caller can silently get BOTH a promise
    # of no ref and a named ref.
    "no_issue_flag_check": [
        ('if [ "$SESSION_ID_ONLY" = 1 ] && [ "$ISSUE_EXPLICIT" = 1 ]; then',
         'if false; then'),
    ],
    # The flag is never SET — the parse arm consumes it and does nothing. This
    # is the "the flag is inert" mutant, and it is the one that proves the
    # plumbing itself rather than any single branch.
    "flag_not_wired": [
        ('    --session-id-only) SESSION_ID_ONLY=1; shift ;;',
         '    --session-id-only) shift ;;'),
    ],
    # `--no-comment` also suppresses the Issue-Ref trailer. This mutant exists
    # ONLY to make leg 10c (the control) provably able to fail: 10c is the one
    # #728 leg whose assertion is not otherwise reachable as a FIRST failure,
    # because oc-commit aborts at the first failing leg and every earlier
    # derivation leg runs WITHOUT --no-comment (leg 4 at :118). The anchor is
    # the two-line trailer branch, since the bare `if [ "$SESSION_ID_ONLY" = 1 ]`
    # occurs three times in the file.
    "no_comment_suppresses_ref": [
        ('if [ "$SESSION_ID_ONLY" = 1 ]; then\n  _TRAILERS=(--trailer "Session-Id: $OC_ACTOR")\n',
         'if [ "$SESSION_ID_ONLY" = 1 ] || [ "$NO_COMMENT" = 1 ]; then\n  _TRAILERS=(--trailer "Session-Id: $OC_ACTOR")\n'),
    ],
}
if label not in MUTATIONS:
    sys.stderr.write("unknown mutation %r\n" % label)
    sys.exit(2)
src = open(path).read()
for i, (anchor, repl) in enumerate(MUTATIONS[label], 1):
    n = src.count(anchor)
    if n != 1:
        sys.stderr.write("mutation %s: anchor %d occurs %d times, need exactly 1\n"
                         % (label, i, n))
        sys.exit(2)
    src = src.replace(anchor, repl)
open(path, "w").write(src)
PYEOF
}

# --- mutation matrix --------------------------------------------------------
# guard_one <label> <aimed-leg> — the leg that must be the FIRST failure.
guard_one() {
  local label="$1" aimed="$2"
  local mut="$WORK/mut_$label" outf="$WORK/mut_$label.out" rc_m="" first=""

  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then bad "[$label] could not copy the tools tree"; return; fi
  if ! mutate "$mut" "$label" 2>"$WORK/mut_$label.mutate.err"; then
    bad "[$label] could not apply the mutation — guard is inert ($(cat "$WORK/mut_$label.mutate.err"))"
    return
  fi

  # Prove the mutant really differs (a no-op mutation would make this section
  # vacuous while every assertion below still reported PASS).
  if cmp -s "$SRC/$COMMIT_REL" "$mut/$COMMIT_REL"; then
    bad "[$label] mutant is byte-identical to the pristine tool — no-op mutation"
    return
  else
    ok "[$label] mutant applied ($(cmp -l "$SRC/$COMMIT_REL" "$mut/$COMMIT_REL" 2>/dev/null | wc -l) differing bytes)"
  fi

  rc_m="$(run_st "$mut/$COMMIT_REL" "$outf")"
  if [ "$rc_m" = "0" ]; then
    bad "[$label] mutant selftest PASSED (rc=0) — the aimed leg does not catch the regression"
    return
  fi

  first="$(grep -m1 '^selftest: ' "$outf" | sed 's/^selftest: //')"
  if [ -z "$first" ]; then
    bad "[$label] mutant failed (rc=$rc_m) but printed no 'selftest:' label — cannot attribute the failure"
    return
  fi
  n_unrelated="$(printf '%s\n' "$outf" | grep -c '^selftest: ' || true)"
  case "$first" in
    "$aimed "*)
      ok "[$label] CAUGHT — first failing leg is the aimed one: $first"
      ;;
    *)
      bad "[$label] first failing leg was '$first', aimed at '$aimed *'"
      ;;
  esac
  if [ "$n_unrelated" -gt 1 ]; then
    bad "[$label] printed $n_unrelated failure labels — the suite did NOT abort at the first (assertion shape assumed one)"
  fi
}

guard_one derivation_ignores_flag "#728-sid-only-announced"
guard_one comment_not_gated       "#728-sid-only-no-comment"
guard_one trailer_always_ref      "#728-sid-only-no-ref"
guard_one no_issue_flag_check     "#728-sid-only-conflict"
guard_one flag_not_wired          "#728-sid-only-no-ref"
guard_one no_comment_suppresses_ref "#728-control-derivation"

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — every #728 leg fails under its mutant and stays green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
