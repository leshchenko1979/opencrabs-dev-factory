#!/usr/bin/env bash
# Mutation guard for #428 — prove the close-keyword scan's legs are LIVE, not
# vacuous.
#
# #428: `oc-commit` handed the caller's `-m` bodies to `git commit` verbatim and
# inspected none of them. GitHub's default-branch parser closes an issue when a
# body carries a close keyword followed by #N, and it CANNOT read negation — so
# the honest-limit prose the process itself requires ("Part B alone does NOT fix
# #321") closed fork issue #321 ELEVEN SECONDS after the ff-merge, with no
# upstream PR at all. The fix adds a scoped, NON-BLOCKING scan that warns on
# stderr, naming the matched shape and classifying it.
#
# A leg that cannot fail is decoration. Each section reverts ONE shipped
# property on a COPY of the tools tree and requires `oc-commit --selftest` to
# fail on that copy while the unmutated copy stays green.
#
# ASSERTION SHAPE — oc-commit's selftest ABORTS at the first failing leg
# (`exit 1`), unlike oc-health which counts and continues. So exactly ONE
# `selftest: <label>` line can exist per mutant, and the strongest available
# assertion is: the mutant fails, and the FIRST (hence only) failing leg is the
# leg aimed at. The cost of that shape is shadowing, stated rather than hidden:
# a mutation that reddens leg 8a's first assertion also hides 8a's later ones
# and all of 8b/8c behind it. Every aimed leg below is therefore reachable as a
# FIRST failure under its own mutant — that is the property this guard asserts,
# and it is why `#428-clean-silent` (8b) is deliberately NOT claimed: with 8a
# ahead of it, no faithful mutation can reach it first.
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

echo "=== #428 mutation guard (oc-commit close-keyword hazard scan) ==="

# --- run a copy's selftest; echoes its rc ------------------------------------
# oc-commit writes gate + warning lines to STDERR, so the capture merges 2>&1.
run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 600 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

# --- baseline: the pristine tree must be GREEN -------------------------------
cp -a "$SRC" "$WORK/baseline" || { echo "copy failed"; exit 2; }
base_out="$WORK/baseline.out"
rc_base="$(run_st "$WORK/baseline/$COMMIT_REL" "$base_out")"
if [ "$rc_base" = "0" ]; then
  ok "baseline oc-commit --selftest GREEN (rc=0)"
else
  bad "baseline oc-commit rc=$rc_base (expected 0)"
fi
grep -q '^selftest OK$' "$base_out" \
  && ok "baseline prints the OK marker" \
  || bad "baseline did not print 'selftest OK'"

# The guard is vacuous unless the pristine tree carries the legs it later
# requires to redden. Assert the leg labels are present in the tool source — a
# mutant can only redden a leg that exists, and a renamed leg would otherwise
# silently disable this whole guard.
for leg in '#428-negated-rc0' '#428-negated-class' '#428-negated-names-shape' '#428-genuine-class' '#29-crossline-class'; do
  if grep -q "$leg " "$SRC/$COMMIT_REL"; then
    ok "baseline carries leg '$leg'"
  else
    bad "leg '$leg' is MISSING from oc-commit — the guard would be vacuous"
  fi
done

# --- mutations ---------------------------------------------------------------
# label|anchor|replacement  (ASCII anchors only: this heredoc is fed to python3
# on stdin, so a non-ASCII anchor — every warning string in oc-commit carries an
# em-dash — is one encoding surprise from a silent no-op)
mutate() {  # mutate <tree> <label> -> rc 0 on success
  python3 - "$1/$COMMIT_REL" "$2" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
MUTATIONS = {
    # Drop the negation scoping: EVERY shape is then classified as a genuine
    # close. This is the mutation AC3 names — the honest-limit fixture must stop
    # reporting class=negated.
    "negation_dropped": [
        ("if printf '%s' \"$win\" | grep -Eqi \"$NEG_RE\"; then",
         "if false; then"),
    ],
    # Report BOTH classes as negated: the distinction itself is gone, so a body
    # that really does close the issue is waved through as harmless.
    "genuine_reported_as_negated": [
        ("warn: close-keyword(#428) class=genuine line=%s shape=%s",
         "warn: close-keyword(#428) class=negated line=%s shape=%s"),
    ],
    # Keep the warning, drop the shape: a warning that does not NAME what it
    # matched cannot be acted on.
    "shape_not_named": [
        ("      printf 'warn: close-keyword(#428) class=negated line=%s shape=%s\\n' \"$ln\" \"'$shape'\" >&2\n",
         "      printf 'warn: close-keyword(#428) class=negated line=%s\\n' \"$ln\" >&2\n"),
    ],
    # Make the advisory BLOCKING: the commit dies instead of landing, which is
    # shape 2 of the #428 disposition — rejected precisely because it stops
    # correct commits. Guards the non-blocking half of the contract.
    "warning_made_blocking": [
        ("if printf '%s' \"$win\" | grep -Eqi \"$NEG_RE\"; then",
         "if printf '%s' \"$win\" | grep -Eqi \"$NEG_RE\"; then\n        exit 3  # MUTANT"),
    ],
    # #29: revert the WHOLE-BODY scan to a LINE-BOUND one — the whitespace run
    # before #N is narrowed to [[:blank:]] (space/tab only), so a keyword that
    # ends a line can no longer reach a reference on a LATER line, while every
    # one-line shape still matches. Leg 8d must redden; 8a/8c are one-line and
    # stay green, which is what makes 8d discriminating rather than a re-test.
    # The anchor is ASCII-only on purpose: this heredoc is fed to python3 on
    # stdin, so a non-ASCII anchor is one encoding surprise from a silent no-op.
    "crossline_scan_reverted": [
        ("CLOSE_RE='(^|[^A-Za-z])((close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]*:?[[:space:]]*#[0-9]+)'",
         "CLOSE_RE='(^|[^A-Za-z])((close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]*:?[[:blank:]]*#[0-9]+)'"),
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

# AC3's mutation, verbatim: dropping the negation scoping must make the
# honest-limit fixture warn as a GENUINE close. Under the mutant the fixture
# still commits (rc 0), so the class assertion is the only thing standing
# between an honest-limit sentence and a silent tracker close.
guard_one negation_dropped            "#428-negated-class"
guard_one genuine_reported_as_negated "#428-genuine-class"
guard_one shape_not_named             "#428-negated-names-shape"
guard_one warning_made_blocking       "#428-negated-rc0"
guard_one crossline_scan_reverted      "#29-crossline-class"

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — every #428 leg fails under its mutant and stays green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
