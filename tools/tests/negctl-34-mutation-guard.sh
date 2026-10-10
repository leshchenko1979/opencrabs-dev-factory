#!/usr/bin/env bash
# Mutation guard for #34 — prove the GATE-MODE (bare-form) legs are LIVE.
#
# #34: `oc-job-verify <run> <sha> --identity-only` returned rc 4 REF-MISMATCH on
# EVERY gate-mode run. Its identity anchor was the two-field build-job embed
# "(<sha>, <features>)", which a GATE run never produces: the build job is
# SKIPPED, so its name renders as the literal "${{ inputs.source_ref }}"
# placeholder and the ONLY 40-hex in the run is the bare "(<sha>)" on the gates
# job. oc-artifact-verify's provenance leg had the same blind spot. oc-deploy had
# already solved this in #72 with a private decode_job_sha_any.
#
# The fix: ONE any-shape decoder (oc_decode_job_sha_any) in lib/oc-embed.sh, and
# a two-pass scan in both tools — pass 1 keeps the two-field embed PREFERRED
# (it carries FEATURES), pass 2 falls back to the bare form. oc-deploy's private
# copy now delegates to the lib.
#
# This guard reverts the capability on a COPY of the tools tree — it neuters
# oc_decode_job_sha_any, which is exactly the pre-#34 world — and requires the
# gate-mode legs to redden while the pristine copy stays green.
#
# ASSERTION SHAPE — why this guard does NOT grep a token on a FAIL line.
# negctl-33 (and negctl-31) assert `grep <token> | grep FAIL` because their
# selftests COUNT failures and name each one. THESE TWO SELFTESTS DO NOT: every
# leg is the bare idiom `[ cond ] && passed=$((passed+1))`, and the only report is
# the final `selftest OK|FAIL: $passed/$total cases` line. There is no per-leg
# output to name, so a token-on-FAIL-line assertion cannot be written for them
# without rewriting both selftests — and a guard must not be keyed on an
# artefact the tool does not emit. The strongest available assertion is therefore
# a pair, and it IS leg-identifying:
#   (1) the mutant's pass-COUNT must drop by EXACTLY EXPECTED_DROP — a leg that
#       cannot fail cannot move the count, so a decoration guard cannot pass this;
#   (2) a DIRECT aimed-scenario probe must invert (pristine rc 0 -> mutant rc 4),
#       which names the scenario rather than a count.
# EXPECTED_DROP is stable across unrelated leg additions (a new leg does not
# depend on the fallback); it needs bumping only if ANOTHER fallback-dependent
# leg is added, which is exactly when this guard should be revisited.
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
#: real regression, not only to convict its own internal mutant. Without that
#: affordance the only way to test the regression path is to break the live tree.
SRC="${OC_NEGCTL_SRC:-$SKILL_DIR/tools}"
LIB_REL="lib/oc-embed.sh"
JV_REL="ship/oc-job-verify"
AV_REL="ship/oc-artifact-verify"
#: legs that depend on the fallback: jv 13 (bare form -> rc 0) + jv 14 (bare form
#: with a different sha -> rc 4 'job embed sha'), and the same pair in
#: oc-artifact-verify (15, 16). Neutering the decoder reddens BOTH legs of each
#: tool: with pass 2 dead, leg 14/16 no longer reaches its own sha gate, so it
#: reports the no-embed message instead — more than one failure is expected here.
EXPECTED_DROP=2
PROBE_REF="e7fccd88e44ad431f99d58ec55b3de2a701a6ac9"
export OC_TOOLS_NOLOG=1

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fails=0
ok()  { echo "  ok   - $1"; }
bad() { echo "  FAIL - $1"; fails=$((fails + 1)); }

echo "=== #34 mutation guard (gate-mode bare-form embed) ==="

run_st() {  # run_st <tool-path> <outfile> -> echoes rc
  # No OC_SKILL_DIR pin needed: neither tool reads a $SKILL_DIR artifact. The
  # tools resolve their lib through lib/oc-root.sh, which walks UP to the first
  # ancestor holding a REAL lib/oc-root.sh — so the copy's own lib/ is what gets
  # sourced, and the mutation below lands in the code under test.
  local tool="$1" outfile="$2" rc=0 out=""
  out="$(timeout 900 "$tool" --selftest 2>&1)" || rc=$?
  printf '%s\n' "$out" > "$outfile"
  echo "$rc"
}

passed_of() {  # passed_of <outfile> -> the N of "selftest ...: N/M", empty if none
  grep -Eo 'selftest (OK|FAIL): [0-9]+/[0-9]+' "$1" | tail -1 | grep -Eo '[0-9]+' | head -1
}

# --- aimed-scenario probe ----------------------------------------------------
# Drives the tool against a GATE-MODE fixture: a single bare-form job. Returns
# the tool's rc. On the pristine tree this must be 0; on the mutant it must be 4.
probe() {  # probe <tree> <jv|av> -> rc
  local tree="$1" which="$2" d="$WORK/probe_$2" rc=0
  rm -rf "$d"; mkdir -p "$d/bin"
  cat > "$d/bin/gh" <<'SH'
#!/bin/sh
case "$*" in
  *"--json jobs"*) printf '%s\n' "$STUB_JOBS" ;;
  *) printf '%s\n' '{"status":"completed","conclusion":"success","displayTitle":"pr-checks","headSha":"deadbeef","name":"pr-checks"}' ;;
esac
SH
  chmod +x "$d/bin/gh"
  if [ "$which" = jv ]; then
    PATH="$d/bin:$PATH" STUB_JOBS="{\"jobs\":[{\"name\":\"gate / PR-lane gates ($PROBE_REF)\"}]}" \
      "$tree/$JV_REL" 38015253063 "$PROBE_REF" --identity-only >/dev/null 2>&1 || rc=$?
  else
    printf '\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x3e\x00\x01\x00\x00\x00' > "$d/fake-bin-x64"
    printf 'SOME_MARKER_ABC123\n' >> "$d/fake-bin-x64"
    PATH="$d/bin:$PATH" STUB_JOBS="{\"jobs\":[{\"name\":\"gate / PR-lane gates ($PROBE_REF)\"}]}" \
      "$tree/$AV_REL" "$d/fake-bin-x64" --source "$PROBE_REF" --run-id 38015253063 >/dev/null 2>&1 || rc=$?
  fi
  echo "$rc"
}

# --- mutation: neuter the any-shape decoder ----------------------------------
mutate() {  # mutate <tree> -> rc 0 on success
  python3 - "$1/$LIB_REL" <<'PYEOF'
import sys
path = sys.argv[1]
lines = open(path, encoding="utf-8").read().split("\n")
hits = [i for i, l in enumerate(lines) if l.startswith("oc_decode_job_sha_any() {")]
if len(hits) != 1:
    sys.stderr.write("mutation: %d definitions of oc_decode_job_sha_any, need exactly 1\n" % len(hits))
    sys.exit(2)
i = hits[0]
j = None
for k in range(i + 1, len(lines)):
    if lines[k] == "}":
        j = k
        break
if j is None:
    sys.stderr.write("mutation: no closing brace at column 0 after the definition\n")
    sys.exit(3)
lines[i:j + 1] = [
    "oc_decode_job_sha_any() {",
    "  return 0  # MUTANT (factory #34): pre-#34 behaviour - the any-shape decoder is gone",
    "}",
]
open(path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
}

# --- baseline ----------------------------------------------------------------
cp -a "$SRC" "$WORK/base" || { echo "copy failed"; exit 2; }
rc_jv="$(run_st "$WORK/base/$JV_REL" "$WORK/base.jv.out")"
rc_av="$(run_st "$WORK/base/$AV_REL" "$WORK/base.av.out")"
n_jv="$(passed_of "$WORK/base.jv.out")"
n_av="$(passed_of "$WORK/base.av.out")"

[ "$rc_jv" = 0 ] && ok "baseline oc-job-verify GREEN (rc=0, ${n_jv:-?} passed)" \
                 || bad "baseline oc-job-verify rc=$rc_jv (expected 0)"
[ "$rc_av" = 0 ] && ok "baseline oc-artifact-verify GREEN (rc=0, ${n_av:-?} passed)" \
                 || bad "baseline oc-artifact-verify rc=$rc_av (expected 0)"
[ -n "$n_jv" ] && [ -n "$n_av" ] || bad "baseline did not print a pass-count marker (cannot measure the drop)"

# The guard is vacuous unless the pristine tree carries the fixtures it later
# requires to redden: a renamed or deleted gate-mode leg would silently disable it.
grep -qF 'gate / PR-lane gates' "$SRC/$JV_REL" \
  && ok "baseline carries the gate-mode fixture (oc-job-verify)" \
  || bad "the gate-mode fixture is MISSING from oc-job-verify — the guard would be vacuous"
grep -qF 'gate / PR-lane gates' "$SRC/$AV_REL" \
  && ok "baseline carries the gate-mode fixture (oc-artifact-verify)" \
  || bad "the gate-mode fixture is MISSING from oc-artifact-verify — the guard would be vacuous"

# Baseline probes: the aimed scenario must PASS before the mutation means anything.
p_jv="$(probe "$WORK/base" jv)"
p_av="$(probe "$WORK/base" av)"
[ "$p_jv" = 0 ] && ok "baseline probe: gate-mode bare form -> rc 0 (oc-job-verify)" \
                || bad "baseline probe oc-job-verify rc=$p_jv (expected 0 — the probe itself is broken)"
[ "$p_av" = 0 ] && ok "baseline probe: gate-mode bare form -> rc 0 (oc-artifact-verify)" \
                || bad "baseline probe oc-artifact-verify rc=$p_av (expected 0 — the probe itself is broken)"

# --- mutant ------------------------------------------------------------------
cp -a "$SRC" "$WORK/mut" || { bad "could not copy the tools tree"; echo "MUTATION GUARD FAILED (failures=$fails)"; exit 1; }
if ! mutate "$WORK/mut" 2>"$WORK/mutate.err"; then
  bad "could not apply the mutation — guard is inert ($(cat "$WORK/mutate.err"))"
else
  # A no-op mutation would make every assertion below vacuous while still passing.
  if cmp -s "$SRC/$LIB_REL" "$WORK/mut/$LIB_REL"; then
    bad "mutant lib is byte-identical to the pristine one — no-op mutation"
  else
    ok "mutant applied ($(cmp -l "$SRC/$LIB_REL" "$WORK/mut/$LIB_REL" 2>/dev/null | wc -l) differing bytes in $LIB_REL)"
  fi
  # The mutant must really have lost the capability, not merely changed bytes.
  if grep -q 'MUTANT (factory #34)' "$WORK/mut/$LIB_REL"; then
    ok "mutant carries the marker and no longer decodes the bare form"
  else
    bad "mutant marker absent — the mutation did not land where expected"
  fi

  rc_mjv="$(run_st "$WORK/mut/$JV_REL" "$WORK/mut.jv.out")"
  rc_mav="$(run_st "$WORK/mut/$AV_REL" "$WORK/mut.av.out")"
  m_jv="$(passed_of "$WORK/mut.jv.out")"
  m_av="$(passed_of "$WORK/mut.av.out")"

  for pair in "oc-job-verify|$rc_mjv|$n_jv|$m_jv" "oc-artifact-verify|$rc_mav|$n_av|$m_av"; do
    name="${pair%%|*}"; rest="${pair#*|}"; rc_m="${rest%%|*}"; rest="${rest#*|}"; b="${rest%%|*}"; m="${rest#*|}"
    if [ "$rc_m" = 0 ]; then
      bad "[$name] mutant selftest PASSED (rc=0) — the gate-mode legs do not catch the regression"
      continue
    fi
    ok "[$name] mutant selftest RED (rc=$rc_m)"
    if [ -n "$b" ] && [ -n "$m" ]; then
      drop=$(( b - m ))
      if [ "$drop" -eq "$EXPECTED_DROP" ]; then
        ok "[$name] CAUGHT — pass-count dropped by exactly $drop ($b -> $m): the $EXPECTED_DROP gate-mode legs are LIVE"
      else
        bad "[$name] pass-count dropped by $drop ($b -> $m), expected $EXPECTED_DROP — either a gate-mode leg is decoration or another leg is coupled to the fallback"
      fi
    else
      bad "[$name] could not measure the drop (baseline='$b' mutant='$m')"
    fi
  done

  # Aimed scenario, named: the fixture that reproduced #34 must invert.
  q_jv="$(probe "$WORK/mut" jv)"
  q_av="$(probe "$WORK/mut" av)"
  [ "$q_jv" = 4 ] && ok "[aimed leg] oc-job-verify gate-mode bare form: rc 0 -> rc $q_jv under the mutant (this is the #34 repro)" \
                  || bad "[aimed leg] oc-job-verify gate-mode bare form rc=$q_jv under the mutant, expected 4"
  [ "$q_av" = 4 ] && ok "[aimed leg] oc-artifact-verify gate-mode bare form: rc 0 -> rc $q_av under the mutant" \
                  || bad "[aimed leg] oc-artifact-verify gate-mode bare form rc=$q_av under the mutant, expected 4"
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "MUTATION GUARD PASSED — the #34 gate-mode legs fail under their mutant and stay green on the pristine tree"
  exit 0
fi
echo "MUTATION GUARD FAILED (failures=$fails)"
exit 1
