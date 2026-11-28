#!/usr/bin/env bash
# Mutation guard for #426 — prove the two unset-direction legs are LIVE, not
# vacuous.
#
# #426: `oc-health` class 5 chose its verdict direction from the ABSENCE of a
# hand-made marker (`<state dir>/pacemakers-off`), so "the owner lifted the
# order" and "the marker was never written" were byte-identical to the check.
# With the marker absent in every profile it re-reported the owner's own
# 2026-09-18 pacemakers-off order back to him as `8 QUIRK cron-disabled` on
# every run. The fix routes the absent case to a NOTES channel: observed and
# surfaced, never counted as a finding, so rc stays 0.
#
# A leg that cannot fail is decoration. Each section reverts ONE shipped
# property on a COPY of the tools tree and requires `oc-health --selftest` to
# fail on that copy while the unmutated copy stays green. Unlike the census
# selftest (which aborts at the first bad leg), oc-health COUNTS failures and
# runs on, so this guard asserts the strongest available property: the mutant
# reddens EXACTLY the legs aimed at, and no unrelated leg.
#
# Standalone by design — the negctl-* family is not part of
# the pytest gate; it is run deliberately when the legs it guards change.
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
#: "$SRC/$HEALTH_REL" no longer resolves. One home for the location.
HEALTH_REL="state/oc-health"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #426 mutation guard (oc-health unset-direction notes channel) ==="

# --- run a copy's selftest; echoes its rc -----------------------------------
# oc-health prints `bad` lines to STDERR, so the capture must merge 2>&1.
run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 600 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

# --- baseline: the pristine tree must be GREEN, with the aimed legs present --
cp -a "$SRC" "$WORK/baseline" || { echo "copy failed"; exit 2; }
base_out="$WORK/baseline.out"
rc_base="$(run_st "$WORK/baseline/$HEALTH_REL" "$base_out")"
if [ "$rc_base" = "0" ]; then
  ok "baseline oc-health --selftest GREEN (rc=0, $(grep -c '^oc-health selftest' "$base_out") summary line(s))"
else
  bad "baseline oc-health rc=$rc_base (expected 0)"
fi
grep -q '^oc-health selftest: PASS=[0-9]* FAIL=0$' "$base_out" \
  && ok "baseline reports FAIL=0" \
  || bad "baseline reports failures: $(grep -m1 '^oc-health selftest' "$base_out")"

# The guard is vacuous unless the pristine tree carries the legs it later
# requires to redden. Assert the leg names are present in the tool source — a
# mutant can only redden a leg that exists, and a renamed leg would otherwise
# silently disable this whole guard.
for leg in schedulers-lawcron-rc0 schedulers-unset-direction-rc0; do
  if grep -q "chk \"$leg\"" "$SRC/$HEALTH_REL"; then
    ok "baseline carries leg '$leg'"
  else
    bad "leg '$leg' is MISSING from oc-health — the guard would be vacuous"
  fi
done

# --- mutations ---------------------------------------------------------------
# label|anchor|replacement  (ASCII anchors only: this heredoc is fed to python3
# on stdin, so a non-ASCII anchor is one encoding surprise from a silent no-op)
mutate() {  # mutate <tree> <label> -> rc 0 on success
  python3 - "$1/$HEALTH_REL" "$2" <<'PYEOF'
import sys
path, label = sys.argv[1], sys.argv[2]
MUTATIONS = {
    # Revert the fix itself: the unset direction asserts a finding again —
    # exactly the pre-fix `8 QUIRK cron-disabled` behaviour #426 is about.
    # Blast radius is WIDE and intended: every leg that asserts the new channel
    # asserts the absence of this old finding, so all of them must redden.
    "finding_restored": [
        ("add_note scheduler-direction-unset",
         "add_finding 8 QUIRK cron-disabled"),
    ],
    # Drop the notes from the machine contract: the human line survives, the
    # JSON consumer never learns the direction was unset.
    # TWO anchors: the format fields AND their arguments. Dropping only the
    # fields leaves a surplus arg, and POSIX printf then repeats the format —
    # emitting MALFORMED JSON, which reddens the schema leg for a reason that
    # has nothing to do with notes. The pre-fix artifact was well-formed JSON
    # WITHOUT the channel, so the faithful mutation removes both.
    "json_notes_dropped": [
        (',"notes":%d,"notes_detail":[%s]', ''),
        ('"$REAPED" "$FAILED" "$NOTES" "$N_JSON" "$STATE"',
         '"$REAPED" "$FAILED" "$STATE"'),
    ],
    # Drop the human line: the note exists only in JSON.
    "text_note_dropped": [
        ('  [ -n "$N_TEXT" ] && printf \'%s\' "$N_TEXT"\n', ''),
    ],
    # Break the channel separation: a note that also counts as a finding sends
    # rc to 1 and pages the owner on every run — the failure mode the whole
    # channel exists to prevent.
    "note_counts_as_finding": [
        ("  NOTES=$((NOTES + 1))\n",
         "  NOTES=$((NOTES + 1))\n  FINDINGS=$((FINDINGS + 1))\n"),
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
# aimed = the leg names the mutation MUST redden (space-separated).
guard_one() {  # guard_one <label> <aimed-legs>
  local label="$1" aimed="$2"
  local mut="$WORK/mut_$label" outf="$WORK/mut_$label.out" rc_m="" leg="" n_aimed=0 n_hit=0
  local unrelated=""

  rm -rf "$mut"
  if ! cp -a "$SRC" "$mut"; then bad "[$label] could not copy the tools tree"; return; fi
  if ! mutate "$mut" "$label" 2>"$WORK/mut_$label.mutate.err"; then
    bad "[$label] could not apply the mutation — guard is inert ($(cat "$WORK/mut_$label.mutate.err"))"
    return
  fi

  # Prove the mutant really differs (a no-op mutation would make this section
  # vacuous while every leg below still reported PASS).
  if cmp -s "$SRC/$HEALTH_REL" "$mut/$HEALTH_REL"; then
    bad "[$label] mutant is byte-identical to the pristine tool — no-op mutation"
    return
  else
    ok "[$label] mutant applied ($(cmp -l "$SRC/$HEALTH_REL" "$mut/$HEALTH_REL" 2>/dev/null | wc -l) differing bytes)"
  fi

  rc_m="$(run_st "$mut/$HEALTH_REL" "$outf")"
  if [ "$rc_m" = "0" ]; then
    bad "[$label] mutant selftest PASSED (rc=0) — the aimed legs do not catch the regression"
    return
  fi

  for leg in $aimed; do
    n_aimed=$((n_aimed + 1))
    if grep -q "^  FAIL $leg" "$outf"; then
      n_hit=$((n_hit + 1))
      printf '         caught: %s\n' "$(grep -m1 "^  FAIL $leg" "$outf" | cut -c1-140)"
    else
      bad "[$label] aimed leg '$leg' did NOT redden — it is decoration"
    fi
  done
  [ "$n_hit" -eq "$n_aimed" ] && ok "[$label] CAUGHT — all $n_aimed aimed leg(s) reddened under mutation"

  # Strongest available assertion: the mutation reddens the aimed legs and
  # nothing else. An unrelated failure means the legs are not isolating the
  # property they claim to test.
  unrelated="$(grep '^  FAIL ' "$outf" \
    | sed 's/^  FAIL //' \
    | while IFS= read -r line; do
        hit=0
        for leg in $aimed; do
          case "$line" in "$leg"*) hit=1 ;; esac
        done
        [ "$hit" = "0" ] && printf '%s\n' "$line"
      done)"
  if [ -z "$unrelated" ]; then
    ok "[$label] reddened nothing outside the aimed legs"
  else
    bad "[$label] reddened UNRELATED leg(s): $(printf '%s' "$unrelated" | tr '\n' '|' | cut -c1-180)"
  fi
}

guard_one finding_restored          "schedulers-lawcron-rc0 schedulers-lawcron-note-names-live-job schedulers-lawcron-asserts-unread-direction schedulers-unset-direction-rc0 schedulers-unset-direction-findings-empty schedulers-unset-direction-note schedulers-unset-direction-legacy-finding"
# json_notes_dropped removes the note from the JSON contract. In leg 10e findings are
# EMPTY, so notes_detail is the ONLY carrier of the note's payload: the slug, the marker
# path, and the job names all reach the --json output solely through it. Every 10e leg
# that greps for note CONTENT therefore reddens by construction — while the legs asserting
# rc and the EMPTINESS of findings stay green (the mutation touches neither).
# Derived by reading the mutation and the leg bodies, not by prediction: this list was
# wrong twice from guessing, once for marker-path and once for lists-job.
guard_one json_notes_dropped        "schedulers-unset-direction-note schedulers-unset-direction-marker-path schedulers-unset-direction-lists-job"
guard_one text_note_dropped         "schedulers-lawcron-note-names-live-job schedulers-rename-proof"
guard_one note_counts_as_finding    "schedulers-lawcron-rc0 schedulers-unset-direction-rc0"

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — every #426 leg fails under its mutant and stays green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
