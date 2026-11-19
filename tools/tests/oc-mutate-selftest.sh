#!/usr/bin/env bash
# oc-mutate-selftest.sh — arms for oc-mutate. Sourced by `oc-mutate --selftest`.
#
# Every arm here exists to catch a specific way a mutation harness lies:
#   * reporting CAUGHT when the mutation never applied (no-op detector)
#   * reporting CAUGHT when the suite simply died (SUITE-DIED split)
#   * reporting CAUGHT when the PRISTINE tree was already red (baseline control)
#   * attributing the red to a leg that did not go red (--leg assertion)
#   * leaking child writes into the PRODUCTION state dir (the mut627 incident)
#
# The fixture tool is deliberately trivial so a reddened leg is unambiguous.
set -u

fails=0
ok()  { printf 'ok   - %s\n' "$1"; }
bad() { printf 'FAIL - %s\n' "$1"; fails=$((fails+1)); }

ST_WORK="$(mktemp -d "${TMPDIR:-/tmp}/oc-mutate-st.XXXXXX")" || { echo "FAIL - mktemp"; exit 1; }
trap 'rm -rf "$ST_WORK"' EXIT

# --- fixture tools trees -----------------------------------------------------
# tree A: GUARD=on makes leg-alpha pass; mutating it to `off` reddens ONLY
# leg-alpha, which is what lets the "green legs not listed" arm mean something.
mkdir -p "$ST_WORK/good/state"
cat > "$ST_WORK/good/state/fixture-tool" <<'FIX'
#!/usr/bin/env bash
set -u
GUARD=on
case "${1:-}" in
  --selftest)
    # Prove the state-seam redirect: the child's writes must land in the
    # fixture dir, never in the caller's real state dir.
    [ -n "${OC_DEV_STATE:-}" ] && : > "$OC_DEV_STATE/child-wrote" 2>/dev/null || true
    f=0
    if [ "$GUARD" = on ]; then
      printf 'selftest: leg-alpha PASS\n'
    else
      printf 'selftest: leg-alpha FAIL\n'
      f=$((f+1))
    fi
    printf 'selftest: leg-beta-guard-holds PASS\n'
    printf 'selftest: leg-gamma PASS\n'
    # THE TRAP (2026-11-19): a PASSING leg whose LABEL contains the word FAIL.
    # oc-smoke's t_ok prints exactly this shape. extract_fails matched the bare
    # token, so a green run fabricated seven red legs and a sound mutant was
    # accused of surviving. Any arm that asserts "nothing reddened" is worthless
    # unless the fixture carries this line.
    printf 'selftest: FAIL verdict never closes  OK\n'
    if [ "$f" -eq 0 ]; then printf 'selftest OK\n'; exit 0; fi
    exit 1 ;;
  *) printf 'usage\n'; exit 2 ;;
esac
FIX
chmod +x "$ST_WORK/good/state/fixture-tool"

# tree B: already red on the pristine copy — the INCONCLUSIVE path.
mkdir -p "$ST_WORK/red/state"
cat > "$ST_WORK/red/state/fixture-tool" <<'FIX'
#!/usr/bin/env bash
set -u
case "${1:-}" in
  --selftest) printf 'selftest: leg-alpha FAIL\n'; exit 1 ;;
  *) exit 2 ;;
esac
FIX
chmod +x "$ST_WORK/red/state/fixture-tool"

MUT="$SELF_DIR/oc-mutate"
run_mut() {  # run_mut <args...> ; sets OUT, RC
  OUT="$("$MUT" "$@" 2>&1)"; RC=$?
}

# --- 1. CAUGHT, and it names the aimed leg -----------------------------------
run_mut state/fixture-tool 's/^GUARD=on$/GUARD=off/' --leg leg-alpha \
        --tools-src "$ST_WORK/good" --no-stamp
if [ "$RC" = 0 ] && printf '%s' "$OUT" | grep -q 'CAUGHT' && printf '%s' "$OUT" | grep -q 'leg-alpha'; then
  ok "a mutation that reddens the aimed leg is CAUGHT (rc=0)"
else
  bad "expected CAUGHT rc=0 naming leg-alpha, got rc=$RC"; printf '%s\n' "$OUT" | sed 's/^/     /'
fi

# --- 2. POSITIVE CONTROL: green legs are NOT reported as reddened ------------
# Without this arm a harness that prints every leg name under "reddened" would
# pass arm 1 while attributing the red to legs that never failed.
# The third name is the 2026-11-19 regression: it is a GREEN leg whose label
# contains the word FAIL. Before the fix extract_fails matched the bare token
# and reported it red, so this arm is the one that would have caught the bug.
if printf '%s' "$OUT" | grep -q 'leg-beta-guard-holds' || printf '%s' "$OUT" | grep -q 'leg-gamma' || printf '%s' "$OUT" | grep -q 'FAIL verdict never closes'; then
  bad "green legs (leg-beta-guard-holds / leg-gamma / FAIL verdict never closes) appeared in the reddened set"
else
  ok "legs that stayed green are absent from the reddened set (incl. a FAIL-named green leg)"
fi

# --- 3. no-op mutation is refused, never scored ------------------------------
run_mut state/fixture-tool 's/THIS_PATTERN_IS_ABSENT/whatever/' --leg leg-alpha \
        --tools-src "$ST_WORK/good" --no-stamp
if [ "$RC" = 1 ] && printf '%s' "$OUT" | grep -q 'NO-OP MUTATION'; then
  ok "a mutation that changes no bytes is refused (rc=1, no verdict)"
else
  bad "expected NO-OP rc=1, got rc=$RC"; printf '%s\n' "$OUT" | sed 's/^/     /'
fi

# --- 4. a mutation nothing asserts is SURVIVED -------------------------------
run_mut state/fixture-tool 's/^set -u$/set -u   # mutated/' --leg leg-alpha \
        --tools-src "$ST_WORK/good" --no-stamp
if [ "$RC" = 1 ] && printf '%s' "$OUT" | grep -q 'SURVIVED'; then
  ok "a mutation no leg asserts is SURVIVED (rc=1), not CAUGHT"
else
  bad "expected SURVIVED rc=1, got rc=$RC"; printf '%s\n' "$OUT" | sed 's/^/     /'
fi

# --- 5. the wrong aimed leg is LEG-MISSED, not a pass ------------------------
run_mut state/fixture-tool 's/^GUARD=on$/GUARD=off/' --leg leg-beta-guard-holds \
        --tools-src "$ST_WORK/good" --no-stamp
if [ "$RC" = 1 ] && printf '%s' "$OUT" | grep -q 'LEG-MISSED'; then
  ok "a red that misses the aimed leg is LEG-MISSED (rc=1)"
else
  bad "expected LEG-MISSED rc=1, got rc=$RC"; printf '%s\n' "$OUT" | sed 's/^/     /'
fi

# --- 6. a RED BASELINE is INCONCLUSIVE (rc=3), never a catch ----------------
# This is the negctl-728 trap: a bad mirror fails every leg, and scoring that
# as "the mutant was caught" is a false receipt for a guard that may not exist.
run_mut state/fixture-tool 's/^set -u$/set -u   # mutated/' --leg leg-alpha \
        --tools-src "$ST_WORK/red" --no-stamp
if [ "$RC" = 3 ] && printf '%s' "$OUT" | grep -q 'BASELINE RED'; then
  ok "a red pristine baseline is INCONCLUSIVE (rc=3), not a catch"
else
  bad "expected BASELINE RED rc=3, got rc=$RC"; printf '%s\n' "$OUT" | sed 's/^/     /'
fi

# --- 7. child writes land in the FIXTURE, never the production state dir ----
# The mut627 incident in one assertion: a mutation harness that writes into the
# real ledger is indistinguishable from a real ledger event.
REAL_STATE="${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}"
probe="$REAL_STATE/oc-mutate-probe-$$"
: > "$probe" 2>/dev/null && probe_writable=1 || probe_writable=0
[ "$probe_writable" = 1 ] && rm -f "$probe"

OUT="$("$MUT" state/fixture-tool 's/^GUARD=on$/GUARD=off/' --leg leg-alpha \
        --tools-src "$ST_WORK/good" --no-stamp --keep 2>&1)"; RC=$?
kept="$(printf '%s' "$OUT" | sed -n 's/^ *work dir kept: //p' | tail -1)"
if [ -n "$kept" ] && [ -f "$kept/state/child-wrote" ]; then
  ok "the child suite's state writes land in the fixture dir"
else
  bad "child writes did not reach the fixture state dir (kept=${kept:-<none>})"
fi
if [ "$probe_writable" = 1 ] && [ -f "$REAL_STATE/child-wrote" ]; then
  bad "LEAK: the child wrote into the production state dir ($REAL_STATE/child-wrote)"
  rm -f "$REAL_STATE/child-wrote"
else
  ok "no child write leaked into the production state dir"
fi
[ -n "$kept" ] && rm -rf "$kept"

# --- 8. a missing tool is a usage error, not a verdict ----------------------
run_mut state/no-such-tool 's/a/b/' --tools-src "$ST_WORK/good" --no-stamp
if [ "$RC" = 2 ] && printf '%s' "$OUT" | grep -q 'no such tool'; then
  ok "a missing tool is a usage error (rc=2)"
else
  bad "expected rc=2 for a missing tool, got rc=$RC"; printf '%s\n' "$OUT" | sed 's/^/     /'
fi

# --- 9. --help documents the flags the arms rely on ------------------------
OUT="$("$MUT" --help 2>&1)"; RC=$?
missing=""
for f in --leg --selftest-arg --timeout --no-stamp; do
  printf '%s' "$OUT" | grep -q -- "$f" || missing="$missing $f"
done
if [ "$RC" = 0 ] && [ -z "$missing" ]; then
  ok "--help exits 0 and documents --leg/--selftest-arg/--timeout/--no-stamp"
else
  bad "--help rc=$RC missing:${missing:-<none>}"
fi

# --- 10. recursion is refused ----------------------------------------------
OUT="$(OC_MUTATE_DEPTH=1 "$MUT" state/fixture-tool 's/a/b/' --tools-src "$ST_WORK/good" --no-stamp 2>&1)"; RC=$?
if [ "$RC" = 2 ] && printf '%s' "$OUT" | grep -q 'refusing to recurse'; then
  ok "a nested run is refused (rc=2)"
else
  bad "expected recursion refusal rc=2, got rc=$RC"
fi

printf '\n%s arm(s) failed\n' "$fails"
[ "$fails" -eq 0 ] && printf 'selftest OK\n'
[ "$fails" -eq 0 ] && exit 0
exit 1
