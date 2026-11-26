#!/usr/bin/env bash
# Mutation guard for factory #185 — prove the MODE VOCABULARY arm is LIVE.
#
# #185: `oc-ledger mode` validated the SHAPE of a MODE declaration but not its
# VALUE, and `oc-harvest-dispatch`'s reader kept its own second token scan. The
# two defects compound into one fail-OPEN read of the register that decides
# whether anything is filed upstream:
#
#   ledger rows   n=200 MODE: DEGRADED              (older, legal)
#                 n=300 MODE: UPSTREAM-ON-REQUEST   (older, legal, owner-named)
#                 n=500 MODE: FACTORY-PAUSED        (NEWEST, unknown token)
#
#   pre-fix       `oc-ledger mode` -> rc 0, value FACTORY-PAUSED (no such
#                 register value, answered as if it were one), and the dispatch
#                 reader walked PAST the unknown row to n=300 and printed
#                 `Mode: UPSTREAM-ON-REQUEST` — the filing arm OPENED on an
#                 unreadable declaration.
#   required      `oc-ledger mode` -> rc 1, stdout EMPTY, stderr naming the
#                 token + row + instant; dispatch -> FORK-STANDING + a refusal
#                 note. Nothing is filed.
#
# TWO MUTANTS, because the fix has two halves and either one alone would leave
# this guard satisfiable by a half-fix:
#   A (oc-ledger)  the `known` register whitelist replaced by `true` — the
#                  pre-fix SHAPE-ONLY predicate. Only the register's own arms can
#                  catch this: the dispatch reader delegates, so it inherits the
#                  hole and reports the unknown token as a live mode.
#   B (dispatch)   the reader's private newest-first token scan RESTORED, taken
#                  VERBATIM from git HEAD (the pre-#185 implementation, not an
#                  invented stand-in). Only the dispatch's arms can catch this.
#
# ASSERTION SHAPE: both selftests name a failing leg on a FAIL line on STDERR,
# so every capture is `2>&1`. The assertion is the TOKEN on a FAIL line, not
# merely "rc != 0", and it ALSO asserts the pass-count drop, because a token
# test alone cannot tell a leg that failed from a leg that never ran.
#
# Standalone by design — the negctl-* family is not wired into tools/tests/run.sh;
# it is run deliberately when the legs it guards change. Budget ~6 min: it runs
# both selftests on the pristine tree and again under each mutant (4 full runs).
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
#: real regression, not only to convict its own internal mutants.
SRC="${OC_NEGCTL_SRC:-$SKILL_DIR/tools}"
LEDGER_REL="state/oc-ledger"
DISPATCH_REL="harvest/oc-harvest-dispatch"
#: arms that depend on the vocabulary check. 71-ter's block contributes the
#: unknown-value refusals (5 arms + 2 --json + the walk-past arm); the harvest
#: reader contributes 6a-9 and 6a-9a. 6a-9b (control) and 6a-10 (structural) are
#: mutation-INDEPENDENT and must SURVIVE both mutants.
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #185 mutation guard (an unknown MODE value must REFUSE, never walk past) ==="

run_st() {  # run_st <cmd...> <outfile> -> echoes rc. stderr FOLDED IN: chk writes there.
  local outfile="${*: -1}" rc=0
  local cmd=("${@:1:$#-1}") out=""
  out="$(timeout 900 "${cmd[@]}" 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> <marker-regex> -> the N of the summary line
  grep -Eo "$2" "$1" | tail -1 | cut -d= -f2
}

#: The dispatch suite RETURNS at the first failing leg (every leg ends in
#: `return 1`), so a mutant that trips an early leg prints NO summary line and
#: every later leg never runs. Counting `ok` lines is then the only measure —
#: and it is a LOWER BOUND on the damage, not a precise per-leg drop. Stated
#: here so no reader mistakes 75 -> 30 for "45 legs broke".
legs_of() {  # legs_of <outfile> -> summary N when present, else the ok-line count
  local n
  # `cut -d/ -f1` alone would yield the STRING "selftest: 75": the summary line is
  # "selftest: 75/75", so the prefix has to go too, or the arithmetic below reads
  # `selftest` as a variable name and dies unbound under `set -u` (measured).
  n="$(grep -Eo 'selftest: [0-9]+/[0-9]+' "$1" | tail -1 | sed -E 's/^selftest: ([0-9]+)\/[0-9]+$/\1/')"
  [ -n "$n" ] || n="$(grep -cE '^  ok ' "$1")"
  printf '%s' "$n"
}

# --- aimed scenario probe ----------------------------------------------------
# The #185 reproducer, hand-built and hermetic: an OLDER legal owner-named
# declaration, then a NEWEST declaration carrying an unknown token. On the
# pristine tree the register must refuse (rc 1, stdout empty) and the dispatch
# envelope must read FORK-STANDING + a refusal note; on either mutant it answers
# a live mode and the filing arm opens.
probe_ledger() {  # probe_ledger <tools-tree> <ledger> -> "<rc>|<stdout>"
  local tree="$1" led="$2" rc=0 out=""
  out="$(OC_LEDGER="$led" bash "$tree/$LEDGER_REL" mode --json 2>/dev/null)" || rc=$?
  printf '%s|%s' "$rc" "$out"
}

# --- mutation A: disable the register whitelist (pre-fix shape-only) ---------
mutate_a() {  # mutate_a <tools-tree> -> rc 0 on success
  python3 - "$1/$LEDGER_REL" <<'PYEOF'
import sys
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
old = ('    def known: . == "FORK-STANDING" or . == "UPSTREAM-ON-REQUEST"\n'
       '               or . == "DEGRADED" or . == "HIGH-TRUST";\n')
if src.count(old) != 1:
    sys.stderr.write("mutation A: %d known-predicate sites, need exactly 1\n" % src.count(old))
    sys.exit(2)
new = '    def known: true;   # MUTANT (factory #185): the register whitelist DISABLED\n'
open(path, "w", encoding="utf-8").write(src.replace(old, new))
PYEOF
}

# --- mutation B: restore the pre-#185 private token scan ---------------------
# The region below is VERBATIM from `git show d80f93cc4:tools/harvest/oc-harvest-dispatch`
# (the commit this branch was cut from, i.e. the real pre-fix code) — not a
# paraphrase. It is embedded rather than fetched at run time so the guard keeps
# working after the branch is merged and the old blob is no longer an ancestor.
mutate_b() {  # mutate_b <tools-tree> -> rc 0 on success
  python3 - "$1/$DISPATCH_REL" <<'PYEOF'
import sys
path = sys.argv[1]
PRE_FIX_READER = """    def read_harvest_mode(ledger_file):
        '''Resolve the live MODE; fail closed to FORK-STANDING.

        Fail-closed direction is "nothing is filed": no MODE row, an unreadable
        ledger and a missing oc-ledger all read FORK-STANDING.
        '''
        ledger_tool = os.path.join(os.environ.get('OC_TOOLS_DIR', ''), 'state', 'oc-ledger')
        if not ledger_tool or not os.path.exists(ledger_tool):
            return 'FORK-STANDING'
        try:
            res = subprocess.run([ledger_tool, 'events', '--n', '2000', '--kind', 'note', '--full'],
                                 capture_output=True, text=True, timeout=10)
        except Exception:
            return 'FORK-STANDING'
        if res.returncode != 0:
            return 'FORK-STANDING'
        for line in reversed(res.stdout.splitlines()):
            upper = line.upper()
            if 'MODE:UPSTREAM-ON-REQUEST' in upper or 'MODE: UPSTREAM-ON-REQUEST' in upper:
                return 'UPSTREAM-ON-REQUEST'
            if 'MODE:FORK-STANDING' in upper or 'MODE: FORK-STANDING' in upper:
                return 'FORK-STANDING'
            # Legacy rows, read FORWARD only (owner ruling 2026-11-12).
            if 'MODE:HIGH-TRUST' in upper or 'MODE: HIGH-TRUST' in upper:
                return 'UPSTREAM-ON-REQUEST'
            if 'MODE:DEGRADED' in upper or 'MODE: DEGRADED' in upper:
                return 'FORK-STANDING'
        return 'FORK-STANDING'

"""
old_region = PRE_FIX_READER
src = open(path, encoding="utf-8").read()
i = src.index('    def read_harvest_mode(ledger_file):')
j = src.index('    harvest_mode, mode_note = read_harvest_mode(ledger_file)')
src = src[:i] + old_region + src[j:]
caller_old = ('    harvest_mode, mode_note = read_harvest_mode(ledger_file)\n'
              '    if mode_note:\n'
              '        print(mode_note, file=sys.stderr)')
if src.count(caller_old) != 1:
    sys.stderr.write("mutation B: caller site not found exactly once\n")
    sys.exit(2)
src = src.replace(caller_old,
                  '    harvest_mode = read_harvest_mode(ledger_file)'
                  '   # MUTANT (factory #185): pre-fix walk-past reader RESTORED\n'
                  "    mode_note = ''", 1)
open(path, "w", encoding="utf-8").write(src)
PYEOF
}

# --- fixtures ----------------------------------------------------------------
mk_unknown() {  # newest row carries an UNKNOWN token, older row is owner-named
  cat > "$1" <<'JSON'
{"current_skill_version":"0.4.1","workers":[],"events":[
 {"n":200,"t":"2026-02-01T00:00:00Z","kind":"note","by":"x","what":"MODE: DEGRADED — older declaration"},
 {"n":300,"t":"2026-03-01T00:00:00Z","kind":"note","by":"x","what":"MODE: UPSTREAM-ON-REQUEST — owner named group 3"},
 {"n":500,"t":"2026-11-20T06:54:20Z","kind":"note","by":"x","what":"MODE: FACTORY-PAUSED — owner order 2026-11-17"}]}
JSON
}
mk_clean() {  # the SAME older owner-named row, no unknown above it (control)
  cat > "$1" <<'JSON'
{"current_skill_version":"0.4.1","workers":[],"events":[
 {"n":200,"t":"2026-02-01T00:00:00Z","kind":"note","by":"x","what":"MODE: DEGRADED — older declaration"},
 {"n":300,"t":"2026-03-01T00:00:00Z","kind":"note","by":"x","what":"MODE: UPSTREAM-ON-REQUEST — owner named group 3"}]}
JSON
}

# --- baseline ----------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
mk_unknown "$WORK/unknown.json"; mk_clean "$WORK/clean.json"

cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }

rc_l="$(run_st bash "$WORK/base/$LEDGER_REL" selftest "$WORK/base-ledger.out")"
n_l="$(passed_of "$WORK/base-ledger.out" 'selftest: PASS=[0-9]+')"
[ "$rc_l" = 0 ] && ok "baseline oc-ledger GREEN (rc=0, ${n_l:-?} passed)" \
                || bad "baseline oc-ledger rc=$rc_l (expected 0)"
[ -n "$n_l" ] || bad "baseline oc-ledger printed no pass-count marker (cannot measure the drop)"

rc_d="$(run_st bash "$WORK/base/$DISPATCH_REL" --selftest "$WORK/base-dispatch.out")"
n_d="$(legs_of "$WORK/base-dispatch.out")"
[ "$rc_d" = 0 ] && ok "baseline oc-harvest-dispatch GREEN (rc=0, ${n_d:-?} legs)" \
                || bad "baseline oc-harvest-dispatch rc=$rc_d (expected 0)"
[ -n "$n_d" ] || bad "baseline dispatch produced no leg count (cannot measure the drop)"

# The guard is vacuous unless the pristine tree carries the arms it later
# requires to redden: a renamed or deleted arm would silently disarm it.
grep -qF 'or . == "DEGRADED" or . == "HIGH-TRUST";' "$SRC/$LEDGER_REL" \
  && ok "baseline carries the register whitelist" \
  || bad "the register whitelist is MISSING from oc-ledger — the guard would be vacuous"
for tok in mode-unknown-value-rc1 mode-unknown-value-stdout-empty mode-unknown-value-does-not-walk-past; do
  grep -qF "\"$tok\"" "$SRC/$LEDGER_REL" \
    && ok "baseline carries the #185 arm $tok" \
    || bad "arm $tok is MISSING from oc-ledger — the guard would be vacuous"
done
for tok in 6a-9 6a-9a 6a-9b 6a-10; do
  grep -qF "$tok - #185" "$SRC/$DISPATCH_REL" \
    && ok "baseline carries the #185 leg $tok" \
    || bad "leg $tok is MISSING from oc-harvest-dispatch — the guard would be vacuous"
done
# The CONTROL tokens below are asserted to SURVIVE each mutant. A control that
# had been renamed or deleted would survive by not existing, so its presence in
# the source is asserted first — otherwise "mutation-independent" would be
# satisfied by an empty set.
for tok in mode-legacy-degraded-reads-forward mode-legacy-high-trust-reads-forward \
           mode-unknown-older-is-superseded-rc0 mode-help-rc0 mode-unknown-flag-rc2; do
  grep -qF "\"$tok\"" "$SRC/$LEDGER_REL" \
    && ok "baseline carries the control arm $tok" \
    || bad "control arm $tok is MISSING from oc-ledger — its 'survival' would be vacuous"
done
grep -qF "ledger_tool, 'mode', '--json'" "$SRC/$DISPATCH_REL" \
  && ok "baseline reader delegates to oc-ledger mode" \
  || bad "the delegation is MISSING — the guard would be vacuous"

# Baseline probes: the aimed scenario must already read the REFUSAL before any
# mutation means anything.
b_unk="$(probe_ledger "$WORK/base" "$WORK/unknown.json")"
[ "${b_unk%%|*}" = 1 ] && ok "baseline probe: unknown newest declaration -> rc 1" \
                       || bad "baseline probe: expected rc 1, got ${b_unk%%|*}"
[ -z "${b_unk#*|}" ] && ok "baseline probe: rc 1 with EMPTY stdout (no authorisation leaks)" \
                     || bad "baseline probe: stdout not empty under refusal: ${b_unk#*|}"
b_cln="$(probe_ledger "$WORK/base" "$WORK/clean.json")"
[ "${b_cln%%|*}" = 0 ] && [ -n "${b_cln#*|}" ] \
  && ok "baseline probe: the clean control still answers rc 0 with a value" \
  || bad "baseline probe: clean control must answer rc 0 with a value, got $b_cln"

# --- mutant A: register whitelist disabled -----------------------------------
echo
echo "--- mutant A: oc-ledger \`known\` -> true (pre-fix shape-only predicate) ---"
cp -a "$SRC" "$WORK/mutA" || { bad "could not copy the tools tree"; }
if ! mutate_a "$WORK/mutA" 2>"$WORK/mutA.err"; then
  bad "could not apply mutation A — guard is inert ($(cat "$WORK/mutA.err"))"
else
  cmp -s "$SRC/$LEDGER_REL" "$WORK/mutA/$LEDGER_REL" \
    && bad "mutant A is byte-identical to the pristine tool — no-op mutation" \
    || ok "mutant A applied ($(cmp -l "$SRC/$LEDGER_REL" "$WORK/mutA/$LEDGER_REL" 2>/dev/null | wc -l) differing bytes)"
  grep -qF 'MUTANT (factory #185)' "$WORK/mutA/$LEDGER_REL" \
    && ok "mutant A carries the marker" \
    || bad "mutant A marker absent — the mutation did not land where expected"
  bash -n "$WORK/mutA/$LEDGER_REL" 2>"$WORK/mutA.syntax" \
    && ok "mutant A parses (bash -n)" \
    || bad "mutant A does not parse — $(head -1 "$WORK/mutA.syntax")"

  # The named regression, on the aimed probe.
  a_unk="$(probe_ledger "$WORK/mutA" "$WORK/unknown.json")"
  [ "${a_unk%%|*}" = 0 ] \
    && ok "[aimed probe] mutant A ANSWERS the unknown token (this IS the #185 repro)" \
    || bad "[aimed probe] mutant A still refuses (rc=${a_unk%%|*}) — the probe is not aimed at the mutation"

  rc_am="$(run_st bash "$WORK/mutA/$LEDGER_REL" selftest "$WORK/mutA-ledger.out")"
  n_am="$(passed_of "$WORK/mutA-ledger.out" 'selftest: PASS=[0-9]+')"
  [ "$rc_am" = 0 ] && bad "mutant A selftest PASSED (rc=0) — the vocabulary arms do not catch it" \
                   || ok "mutant A selftest RED (rc=$rc_am)"

  for tok in mode-unknown-value-rc1 mode-unknown-value-stdout-empty mode-unknown-value-json-rc1; do
    grep -qF "FAIL selftest - $tok" "$WORK/mutA-ledger.out" \
      && ok "[named] $tok is on a FAIL line under mutant A" \
      || bad "[named] $tok did NOT redden under mutant A — that leg is decoration"
  done
  # ...and the legs INDEPENDENT of the mutation must survive it, or the guard
  # would be satisfied by a mutant that simply broke the verb.
  for tok in mode-legacy-degraded-reads-forward mode-legacy-high-trust-reads-forward \
             mode-unknown-older-is-superseded-rc0 mode-help-rc0 mode-unknown-flag-rc2; do
    grep -qF "FAIL selftest - $tok" "$WORK/mutA-ledger.out" \
      && bad "[control] $tok reddened under mutant A — it is not mutation-independent" \
      || ok "[control] $tok survived mutant A (mutation-independent)"
  done

  if [ -n "$n_l" ] && [ -n "$n_am" ]; then
    drop=$(( n_l - n_am ))
    [ "$drop" -ge 3 ] \
      && ok "CAUGHT — mutant A pass-count dropped by $drop ($n_l -> $n_am): the vocabulary arms are LIVE" \
      || bad "mutant A pass-count dropped by only $drop ($n_l -> $n_am), expected >= 3"
  else
    bad "could not measure mutant A drop (baseline='$n_l' mutant='$n_am')"
  fi
fi

# --- mutant B: pre-fix dispatch reader restored ------------------------------
echo
echo "--- mutant B: oc-harvest-dispatch pre-#185 walk-past reader RESTORED (from git) ---"
cp -a "$SRC" "$WORK/mutB" || { bad "could not copy the tools tree"; }
if ! mutate_b "$WORK/mutB" 2>"$WORK/mutB.err"; then
  bad "could not apply mutation B — guard is inert ($(cat "$WORK/mutB.err"))"
else
  cmp -s "$SRC/$DISPATCH_REL" "$WORK/mutB/$DISPATCH_REL" \
    && bad "mutant B is byte-identical to the pristine tool — no-op mutation" \
    || ok "mutant B applied ($(cmp -l "$SRC/$DISPATCH_REL" "$WORK/mutB/$DISPATCH_REL" 2>/dev/null | wc -l) differing bytes)"
  grep -qF 'MUTANT (factory #185)' "$WORK/mutB/$DISPATCH_REL" \
    && ok "mutant B carries the marker" \
    || bad "mutant B marker absent — the mutation did not land where expected"
  # The restored reader must actually carry the walk-past scan, in the ENGINE
  # region only (the selftest's own grep of that literal would otherwise match).
  sed -n '1,/^cmd_selftest()/p' "$WORK/mutB/$DISPATCH_REL" | grep -qF 'upper = line.upper()' \
    && ok "mutant B engine carries the private token scan again (the walk-past)" \
    || bad "mutant B engine has no token scan — the mutation did not restore the defect"
  bash -n "$WORK/mutB/$DISPATCH_REL" 2>"$WORK/mutB.syntax" \
    && ok "mutant B parses (bash -n)" \
    || bad "mutant B does not parse — $(head -1 "$WORK/mutB.syntax")"

  rc_bm="$(run_st bash "$WORK/mutB/$DISPATCH_REL" --selftest "$WORK/mutB-dispatch.out")"
  [ "$rc_bm" = 0 ] && bad "mutant B selftest PASSED (rc=0) — the #185 legs do not catch the walk-past" \
                   || ok "mutant B selftest RED (rc=$rc_bm)"

  # 6a-9 is the leg that NAMES the walk-past, and it is reached. 6a-10 is NOT
  # reached under this mutant — the suite returns at the first failing leg — so
  # requiring it to redden would assert something the harness never executes.
  # Its subject (the private token scan) is instead asserted STRUCTURALLY above,
  # against the mutant's own engine bytes, which is what 6a-10 tests anyway.
  grep -qF "  bad 6a-9 - #185" "$WORK/mutB-dispatch.out" \
    && ok "[named] 6a-9 reddened under mutant B (the walk-past is named, not just counted)" \
    || bad "[named] 6a-9 did NOT redden under mutant B — that leg is decoration"
  grep -qF "token='UPSTREAM-ON-REQUEST'" "$WORK/mutB-dispatch.out" \
    && ok "[named] mutant B answers the OLDER live row — the fail-OPEN read is reproduced" \
    || bad "[named] mutant B did not answer the older live row; the probe is not aimed at the defect"
  # The control leg and the pre-existing MODE legs are mutation-independent.
  for tok in 6a 6a-1 6a-2 6a-3 6a-4 6a-7 6a-8; do
    grep -qE "^  bad $tok - " "$WORK/mutB-dispatch.out" \
      && bad "[control] $tok reddened under mutant B — it is not mutation-independent" \
      || ok "[control] $tok survived mutant B (mutation-independent)"
  done

  n_bm="$(legs_of "$WORK/mutB-dispatch.out")"
  if [ -n "$n_d" ] && [ -n "$n_bm" ]; then
    drop=$(( n_d - n_bm ))
    # A strict decrease is the assertion. The magnitude is NOT a per-leg drop:
    # the suite aborts at the failing leg, so everything after 6a-9 is unrun.
    [ "$drop" -ge 1 ] \
      && ok "CAUGHT — mutant B stopped at the failing leg ($n_d -> $n_bm legs ok, suite short-circuited): the #185 legs are LIVE" \
      || bad "mutant B ran the same leg count as the pristine tree ($n_d -> $n_bm) — the #185 legs do not fire"
  else
    bad "could not measure mutant B leg count (baseline='$n_d' mutant='$n_bm')"
  fi
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — both halves of #185 fail under their restored-pre-fix mutants and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
