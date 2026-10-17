#!/usr/bin/env bash
# Mutation guard for #45 — prove the qualified-`Issue-Ref` legs are LIVE.
#
# #45: `oc-commit` emitted a BARE `Issue-Ref: #N`, which the shipped-ref law
# forbids — a bare number reaching `adolfousier/main` autolinks to a REAL BUT
# DIFFERENT upstream issue (fork #490 notify-tail loss vs upstream #490
# narration leak). The comment leg was worse: it hardcoded the FORK
# (`--repo ${OC_ISSUE_LOG_REPO:-leshchenko1979/opencrabs}`), so factory #43/#44
# implementation comments landed on fork #43/#44. Both now resolve from ONE
# slug (`--tracker` / `--issue-repo` / env), validated, fail-closed.
#
# A leg that cannot fail is decoration. Each section reverts ONE shipped
# property on a COPY of the tools tree and requires `oc-commit --selftest` to
# fail on that copy while the unmutated copy stays green.
#
# THE COPY IS A REAL `cp -a` OF THE WHOLE TREE (never a symlink farm): oc-commit
# bootstraps its tools dir by walking up for a REAL non-symlink `lib/`, so a
# mirrored tree loses `lib/oc_claims.py` and fails every leg at the first one —
# which reads as "the mutant was caught" while proving nothing. The baseline
# control below is what catches that class.
#
# ASSERTION SHAPE — oc-commit's selftest ABORTS at the first failing leg
# (`exit 1`), unlike oc-health which counts and continues. So exactly ONE
# `selftest: <label>` line can exist per mutant, and the strongest available
# assertion is: the mutant fails, and the FIRST (hence only) failing leg is the
# leg aimed at.
#
# Standalone by design — the negctl-* family is not wired into
# tools/tests/run.sh; it is run deliberately when the legs it guards change.
#
# Harness guards (AGENTS.md §Repro harnesses): explicit tool path, recursion
# guard, process budget cap, timeout, and an OC_NEGCTL_SRC override so the same
# guard can be pointed at a REVERTED tree to prove it is not inert.
set -u
[ "${OC_REPRO_DEPTH:-0}" -ge 1 ] && exit 99
export OC_REPRO_DEPTH=1
ulimit -u $(( $(ps -e --no-headers | wc -l) + 200 )) 2>/dev/null || true

SKILL_DIR="/root/.opencrabs/profiles/ops/skills/opencrabs-dev"
SRC="${OC_NEGCTL_SRC:-$SKILL_DIR/tools}"
#: The v0.4.255 regroup moved the fleet into kind subdirs; one home for it.
COMMIT_REL="git/oc-commit"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #45 mutation guard (oc-commit qualified Issue-Ref) ==="
echo "  src: $SRC"

# --- run a copy's selftest; echoes its rc ------------------------------------
run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 600 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

# --- baseline: the pristine tree must be GREEN -------------------------------
# Also the POSITIVE CONTROL for the mirror construction: a mirror that cannot
# run the suite at all fails here rather than masquerading as a caught mutant.
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
for leg in '#45 Issue-Ref #149' '#45-tracker-binary' '#45-bad-slug' \
           '#45-comment-repo' '#45-comment-repo-override' '#45-sid-only-tracker'; do
  if grep -qF "$leg" "$SRC/$COMMIT_REL"; then
    ok "baseline carries leg '$leg'"
  else
    bad "leg '$leg' is MISSING from oc-commit — the guard would be vacuous"
  fi
done

# --- mutations ---------------------------------------------------------------
# ASCII anchors only: this heredoc is fed to python3 on stdin, and every comment
# in oc-commit carries an em-dash — one encoding surprise from a silent no-op.
mutate() {  # mutate <tree> <label> -> rc 0 on success
  python3 - "$1/$COMMIT_REL" "$2" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
MUTATIONS = {
    # The trailer reverts to the bare form this issue exists to forbid. The
    # comment leg is untouched, so ONLY the trailer legs can redden.
    "trailer_bare": [
        ('--trailer "Issue-Ref: $ISSUE_REPO#$ISSUE"',
         '--trailer "Issue-Ref: #$ISSUE"'),
    ],
    # The comment leg reverts to the hardcoded fork default — the exact defect
    # that posted factory #43/#44's notes onto fork #43/#44. The trailer stays
    # qualified, so the first failing leg must be the comment-repo receipt.
    "comment_fork_default": [
        ('--repo "${OC_ISSUE_LOG_REPO:-$ISSUE_REPO}"',
         '--repo "${OC_ISSUE_LOG_REPO:-leshchenko1979/opencrabs}"'),
    ],
    # `--tracker` is consumed and does nothing: the flag reads as honoured while
    # the factory default silently wins. This is the "plumbing is inert" mutant
    # — it proves the parse arm is wired, not merely present.
    "tracker_not_wired": [
        ('    --tracker) TRACKER="${2:-}"; [ -n "$TRACKER" ] || usage; TRACKER_EXPLICIT=1; shift 2 ;;',
         '    --tracker) [ -n "${2:-}" ] || usage; shift 2 ;;'),
    ],
    # The slug validation is dropped: a malformed `--issue-repo` is accepted and
    # interpolated into a QUALIFIED ref naming a repo that does not exist. That
    # reads as correct and is strictly worse than the bare form it replaced.
    "slug_not_validated": [
        ("""printf '%s' "$ISSUE_REPO" | grep -Eq '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$' \\
  || { echo "usage: --issue-repo must be '<owner>/<repo>' (got '$ISSUE_REPO')" >&2; exit 2; }""",
         ':'),
    ],
    # The --session-id-only contradiction check is dropped, so a caller can get
    # BOTH "no ref" and a named tracker — an accepted-but-inert flag, which is
    # indistinguishable from an honoured one at read time.
    "sid_only_allows_tracker": [
        ('if [ "$SESSION_ID_ONLY" = 1 ] && { [ "$TRACKER_EXPLICIT" = 1 ] || [ -n "$ISSUE_REPO" ]; }; then',
         'if false; then'),
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
guard_one() {  # guard_one <label> <aimed-leg>
  local label="$1" aimed="$2"
  local mut="$WORK/mut_$label" outf="$WORK/mut_$label.out" rc_m="" first="" n_unrelated=""

  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then bad "[$label] could not copy the tools tree"; return; fi
  if ! mutate "$mut" "$label" 2>"$WORK/mut_$label.mutate.err"; then
    bad "[$label] could not apply the mutation — guard is inert ($(cat "$WORK/mut_$label.mutate.err"))"
    return
  fi

  # Prove the mutant really differs: a no-op mutation would make this section
  # vacuous while every assertion below still reported PASS.
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

guard_one trailer_bare             "#45 Issue-Ref #149"
# AIMED AT THE OVERRIDE LEG, not at `#45-comment-repo` (the --tracker binary
# assertion): the fork slug IS the old hardcoded default, so that leg passes
# under this very mutant. The override leg pins the comment to a slug that is
# neither constant, and is the first failure here.
guard_one comment_fork_default     "#45-comment-repo-override"
guard_one tracker_not_wired        "#45-tracker-binary"
guard_one slug_not_validated       "#45-bad-slug"
guard_one sid_only_allows_tracker  "#45-sid-only-tracker"

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — every #45 leg fails under its mutant and stays green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
