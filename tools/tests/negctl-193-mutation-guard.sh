#!/usr/bin/env bash
# Mutation guard for factory #193 — prove the FAST-PATH arms are LIVE.
#
# #193: atomic_jq's TRUE-APPEND predicate tested ONLY the .events delta:
#   if ($new|length) == (($old|length)+1) and ($new[0:($old|length)] == $old)
# When that matched it appended one line to events.jsonl and SKIPPED the whole
# record rewrite — including the `del(.events) > workers.json` block in the else
# arm, the ONLY place non-event state is ever written. Any verb that appended
# exactly one event AND mutated non-event state therefore reported success while
# discarding the mutation. Measured on a copy of the live record: enroll lost its
# roster row, promote its role/feature, ack its last_acked, confirm its
# .confirmed, sync its three version fields, and retire printed "row removed,
# signing revoked" while the uuid kept a .role and went on signing.
#
# This guard mutates the predicate back to the event-count-only form — exactly
# the pre-#193 world — on a COPY of the tools tree, and requires:
#
#   REDDEN  (the defect): j193-enroll-*, j193-promote-*, j193-retire-*,
#           j193-ack-last-acked-persists, j193-confirm-flag-persists,
#           j193-sync-version-fields-persist, and the ORPHAN-REPAIR legs
#           (j193-orphan-row-created / -now-resolvable / -second-enroll-refused)
#           — under the mutant an orphan enroll is still admitted rc 0 but its
#           row is dropped, so the uuid never becomes resolvable and a SECOND
#           enroll is no longer refused (there is no row to collide with).
#   SURVIVE (the throughput half): j193-stamp-fast-path-* — a stamp must STILL
#           take the append path under the mutant. That is what stops this guard
#           being satisfied by "rewrite everything always", which would cure the
#           defect by throwing away #149/#177 (one ~200-byte line per stamp
#           instead of a fresh 2.8MB blob).
#   SURVIVE (the zero-event controls): j193-ack-dup-*, j193-resync-* — those
#           paths append no event, so the OLD predicate already failed for them
#           and they reached the full rewrite. They are mutation-INDEPENDENT and
#           must stay green, which is what proves the guard is aimed at the
#           predicate and not merely breaking every write verb.
#
# ASSERTION SHAPE — oc-ledger's selftest defines
#   bad() { F=$((F+1)); echo "  FAIL selftest - $*" >&2; }
# so FAIL lines go to STDERR and every failing leg NAMES ITSELF. Every capture
# below is `2>&1`, and the assertion is the TOKEN on a FAIL line, not merely
# "rc != 0" — the guard NAMES the regression instead of counting it. It ALSO
# asserts the pass-count drop, because a token test alone cannot tell a leg that
# failed from a leg that never ran.
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
#: SRC DEFAULTS TO THIS GUARD'S OWN TOOLS TREE, resolved from the script's real
#: location — never the live skill dir. A guard that copies the LIVE tree tests
#: whatever is installed there, so run from a worktree it mutated code that did
#: not carry the fix, found no #193 clause to rewrite, and reported itself inert
#: ("0 #193 predicate clauses, need exactly 1") while the pristine baseline it
#: printed came from a DIFFERENT tree than the one under review — 741 passed,
#: against the worktree's own 772. That is the fail-loud-and-vacuous shape: it
#: did not pass wrongly, but the only way to get a verdict was to remember the
#: override by hand, which is the same trap one step later.
#: SRC stays overridable so the guard can be pointed at a DELIBERATELY REVERTED
#: tree (OC_NEGCTL_SRC=...) and shown to exit non-zero — i.e. shown to detect a
#: real regression, not only to convict its own internal mutant.
_HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC="${OC_NEGCTL_SRC:-$(cd -- "$_HERE/.." && pwd)}"
TOOL_REL="state/oc-ledger"
export OC_TOOLS_NOLOG=1
#: The copied tree has no SKILL.md, so $SKILL_DIR would resolve into the temp dir
#: and the state-tracked-audit legs (which read $SKILL_DIR/SKILL.md) would redden
#: for a reason UNRELATED to the mutation, leaving a red baseline and a
#: meaningless drop. Pin it at the REAL skill dir: the mutation lands in the
#: copied CODE while data reads still see the law (same fix as negctl-38).
export OC_SKILL_DIR="$SKILL_DIR"

#: 13 of the j193 arms are the predicate's own; the rest (the stamp fast path
#: and the two zero-event paths) are SURVIVE controls and must NOT drop. The
#: exact number is asserted below, so a leg that silently stopped running (no
#: FAIL line) is caught by the count rather than by silence.
EXPECTED_DROP=13

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #193 mutation guard (fast path must prove non-event state unchanged) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc. stderr FOLDED IN: bad() writes there.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 bash "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "oc-ledger selftest: PASS=N FAIL=M"
  grep -Eo 'selftest: PASS=[0-9]+' "$1" | tail -1 | cut -d= -f2
}

# --- mutation: restore the event-count-only predicate -----------------------
mutate() {  # mutate <tools-tree> -> rc 0 on success
  python3 - "$1/$TOOL_REL" <<'PYEOF'
import sys
path = sys.argv[1]
lines = open(path, encoding="utf-8").read().split("\n")
# The #193 clause: the non-event projection comparison, plus the two lines above
# it that open the `and (...)` continuation. Matched on STRIPPED text so the
# mutation survives an indentation change, and required to be UNIQUE — two
# matches would mean the guard cannot say which it mutated.
needle = ("and (($n|del(.events)|del(.updated_at)) == ($o[0]|del(.events)|del(.updated_at)))")
hits = [i for i, l in enumerate(lines) if l.strip() == needle]
if len(hits) != 1:
    sys.stderr.write("mutation: %d #193 predicate clauses, need exactly 1\n" % len(hits))
    sys.exit(2)
i = hits[0]
indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
# The mutant must DELETE the continuation, not replace it with something false:
# `and false` would also work, but leaving `and` dangling would not parse and a
# non-parsing mutant fails EVERY leg (reading as a bogus drop of the whole
# suite) instead of the named regression this guard measures.
lines[i] = indent + "and true  # MUTANT (factory #193): pre-#193 event-count-only predicate"
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

# The guard is vacuous unless the pristine tree carries the predicate it mutates
# AND the legs it later requires to redden.
grep -qF 'del(.events)|del(.updated_at)) == ($o[0]|del(.events)|del(.updated_at))' "$SRC/$TOOL_REL" \
  && ok "baseline carries the #193 non-event projection guard" \
  || bad "the #193 predicate clause is MISSING from oc-ledger — the guard would be vacuous"
for leg in j193-stamp-fast-path-workers-byte-identical j193-enroll-row-persists \
           j193-promote-feature-persists j193-retire-row-removed \
           j193-ack-last-acked-persists j193-confirm-flag-persists \
           j193-sync-version-fields-persist j193-ack-dup-refreshes-last-acked \
           j193-resync-repairs-fields j193-orphan-row-created \
           j193-orphan-now-resolvable j193-orphan-second-enroll-refused; do
  grep -qF "$leg" "$SRC/$TOOL_REL" \
    && ok "baseline carries leg $leg" \
    || bad "leg $leg is MISSING from oc-ledger — the guard would be vacuous"
done

# --- mutant ------------------------------------------------------------------
cp -a "$SRC" "$WORK/mut" || { bad "could not copy the tools tree"; echo "MUTATION GUARD FAILED (failures=$fails)"; exit 1; }
if ! mutate "$WORK/mut" 2>"$WORK/mutate.err"; then
  bad "could not apply the mutation — guard is inert ($(cat "$WORK/mutate.err"))"
else
  if cmp -s "$SRC/$TOOL_REL" "$WORK/mut/$TOOL_REL"; then
    bad "mutant tool is byte-identical to the pristine one — no-op mutation"
  else
    ok "mutant applied ($(cmp -l "$SRC/$TOOL_REL" "$WORK/mut/$TOOL_REL" 2>/dev/null | wc -l) differing bytes in $TOOL_REL)"
  fi
  bash -n "$WORK/mut/$TOOL_REL" 2>"$WORK/syntax.err" \
    && ok "mutant parses (bash -n)" \
    || bad "mutant does not parse — $(head -1 "$WORK/syntax.err")"

  rc_m="$(run_st "$WORK/mut/$TOOL_REL" "$WORK/mut.out")"
  n_m="$(passed_of "$WORK/mut.out")"

  [ "$rc_m" = 0 ] && bad "mutant selftest PASSED (rc=0) — the j193 legs do not catch the defect" \
                  || ok "mutant selftest RED (rc=$rc_m)"

  # REDDEN — every mutation the predicate used to discard.
  REDDEN=( j193-enroll-row-persists j193-enroll-worker-resolvable j193-enroll-role-nonempty
           j193-promote-role-persists j193-promote-feature-persists
           j193-retire-row-removed
           j193-ack-last-acked-persists
           j193-confirm-flag-persists j193-confirm-worker-event-persists
           j193-sync-version-fields-persist
           j193-orphan-row-created j193-orphan-now-resolvable
           j193-orphan-second-enroll-refused )
  for tok in "${REDDEN[@]}"; do
    grep -qF "FAIL selftest - $tok" "$WORK/mut.out" \
      && ok "[named] $tok is on a FAIL line under the mutant" \
      || bad "[named] $tok did NOT redden under the mutant — that leg is decoration"
  done

  # SURVIVE — the throughput half (#149/#177) and the zero-event controls.
  SURVIVE=( j193-stamp-fast-path-events-plus-one j193-stamp-fast-path-workers-byte-identical
            j193-ack-dup-appends-no-event j193-ack-dup-refreshes-last-acked
            j193-resync-appends-no-event j193-resync-repairs-fields )
  for tok in "${SURVIVE[@]}"; do
    grep -qF "FAIL selftest - $tok" "$WORK/mut.out" \
      && bad "[control] $tok reddened under the mutant — it is not mutation-independent" \
      || ok "[control] $tok survived the mutant (mutation-independent)"
  done

  if [ -n "$n_b" ] && [ -n "$n_m" ]; then
    drop=$(( n_b - n_m ))
    if [ "$drop" -eq "$EXPECTED_DROP" ]; then
      ok "CAUGHT — pass-count dropped by exactly $drop ($n_b -> $n_m): the $EXPECTED_DROP predicate arms are LIVE"
    else
      bad "pass-count dropped by $drop ($n_b -> $n_m), expected $EXPECTED_DROP — either a guarded leg is decoration or another leg is coupled to the predicate"
    fi
  else
    bad "could not measure the drop (baseline='$n_b' mutant='$n_m')"
  fi
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #193 fast-path legs fail under the restored event-count-only predicate and stay green on the pristine tree, while the stamp fast path never moves"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
