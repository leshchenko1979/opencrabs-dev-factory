#!/usr/bin/env bash
# =============================================================================
# ship-selftest.sh — the BODY of `oc-ship --selftest`, moved VERBATIM
# (one assertion adapted, see below).
#
# SOURCED at top level by the SELFTEST_MODE=2 arm of tools/ship/oc-ship.
# It used to be `eval "$(sed -n '/^selftest_impl()/,/^}$/p' "$SELF")"` — a
# function text-scraped out of its own file, which CANNOT work once the body
# lives elsewhere: the scrape matches nothing and the suite silently runs ZERO
# arms while exiting 0. A source is the honest form of the same thing.
#
# Globals (T, PASS, FAIL) and ok()/bad() are top-level here exactly as they were
# top-level inside the eval'd function, so semantics are unchanged.
#
# THE ONE ADAPTED ASSERTION: arm `wt69-no-gitdir-proxy` computed a `prod_end`
# line by grepping `^selftest_impl()` in $SELF, to scan production code while
# skipping the selftest body. The body is no longer in $SELF, so $SELF is now
# entirely production code and prod_end is the whole file. The NEGATIVE CONTROL
# beside it is unchanged, so the scanner is still shown able to fire.
# =============================================================================
  set -u
  T="$(mktemp -d)"
  trap 'rm -rf "$T"' EXIT
  export OC_SHIPCHAIN_LOG="$T/detach-default.log"
  PASS=0; FAIL=0
  # The owning session the fixture commits declare via a Session-Id trailer —
  # the same trailer every editor commit carries (SKILL.md §Session-notify
  # loop). Test 12 proves oc-ship defaults OC_ACTOR from it.
  FIXTURE_SESSION="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
  # The identity the WAKE fixture lends the chain through the ENVIRONMENT. A
  # selftest must never read the CALLER's identity: tools/tests/run.sh:44
  # exports OC_ACTOR="test-runner" (label-shaped by design) and no
  # OPENCRABS_SESSION_ID, so an ambient read made the wake legs assert the
  # LAUNCHER rather than the mechanism -- and a BARE ambient expansion under
  # set -u aborted the whole selftest, dropping 84 of 194 legs behind one
  # unbound-variable line (#667). The legs lend their own uuid and assert THAT.
  LEG_UUID="11111111-2222-3333-4444-555555555555"
  ok()   { PASS=$((PASS+1)); echo "ok $1"; }
  bad()  { FAIL=$((FAIL+1)); echo "FAIL $1"; }
  check_rc() { [ "$2" = "$3" ] && ok "$1 (rc=$2)" || bad "$1 (want rc=$3 got $2)"; }

  # fixture fork repo: bare origin + clone with main
  git init -q --bare "$T/origin.git"
  git init -q "$T/clone"
  git -C "$T/clone" config user.email t@t; git -C "$T/clone" config user.name t
  echo base > "$T/clone/base.txt"
  # #20 fixtures: README.md IS include_str!'d from src/lib.rs (so a commit
  # touching it changes compiled output and MUST gate), while ONTOLOGY.md is
  # reached by nothing (so a commit touching only it may skip). The skip
  # predicate must separate these two; that separation is the whole point.
  mkdir -p "$T/clone/src/docs/reference/templates"
  printf 'pub const A: &str = include_str!("../README.md");\npub const B: &str = include_str!("docs/reference/templates/AGENTS.md");\n' > "$T/clone/src/lib.rs"
  printf '# agents\n' > "$T/clone/src/docs/reference/templates/AGENTS.md"
  printf '# readme\n' > "$T/clone/README.md"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm base
  git -C "$T/clone" branch -M main
  git -C "$T/clone" remote add origin "$T/origin.git"
  git -C "$T/clone" push -q origin main
  git -C "$T/clone" checkout -qb feat
  echo feat > "$T/clone/feat.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm feat --trailer "Session-Id: $FIXTURE_SESSION"
  FSHA="$(git -C "$T/clone" rev-parse HEAD)"
  # The remote-branch pre-flight (defect fix 2026-09-11) requires $BRANCH to
  # exist on the fork remote, because LEG1's gate needs it there. Every test
  # below chains --branch feat, so feat MUST be pushed or they all die rc 3 at
  # pre-flight. Without this push the pre-flight had no fixture and test 1's
  # unguarded `OUT="$(run_chain ...)"` made `set -e` abort the entire selftest
  # silently — rc 3, ZERO output, not one assertion printed. Fixture push and
  # the pre-flight assertions at the end of this function land together for
  # exactly that reason.
  git -C "$T/clone" push -q origin feat
  # A deliberately UNPUSHED branch: the pre-flight's own fixture.
  git -C "$T/clone" checkout -qb unpushed-fixture
  echo u > "$T/clone/u.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm u
  USHA="$(git -C "$T/clone" rev-parse HEAD)"
  # #20 fixtures (the docs-only ONTOLOGY.md branch and the compiled README.md
  # branch) are built INSIDE test 20, not here. An earlier test force-pushes
  # onto origin/main (diverge, then feat), so a branch cut from the ORIGINAL
  # main stops being a descendant of the clone's main and LEG3 dies rc 5 NON-FF
  # before a single gate assertion can run — the first run of this block failed
  # exactly that way. Building them at the point of use keeps them
  # fast-forwardable against whatever origin/main has become by then.
  # fixture "fork checkout" = clone back on main
  git -C "$T/clone" checkout -q main

  # fake binaries
  cat > "$T/fake-prchecks" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "${FAKE_PRCHECKS_LOG:-/dev/null}"
# #21: optional gate latency, so the cgroup-detach survival test has a window
# to kill inside. Unset for every other test -> byte-identical behaviour.
[ -n "${FAKE_SLOW_GATE:-}" ] && sleep "$FAKE_SLOW_GATE"
# #92: CANCELLED-superseded, emitted in prchecks' OWN line shape
# (oc-gate:2134) so the capture is exercised against the real format
# rather than a convenient one -- including the REARM_HINT appended to the
# SAME line, which is where the phrase `superseding run:` occurs a second
# time. That second occurrence is `resume superseding run: oc-gate
# resume <id>`: non-digit text sits between the colon and the number, so it
# cannot match the capture pattern. The fixture therefore reproduces the
# real shape and does NOT claim to exercise `head -1`, which is defensive
# (see the capture site's comment).
if [ "${FAKE_GATE:-green}" = "infra6" ]; then
  printf 'oc-gate: VERDICT RED (infra) -- the gate run was cancelled by a superseding run\n'
  printf '  superseding run: 222 -- https://example.invalid/runs/222 (re-arm: oc-gate abc --wait 600 — or resume superseding run: oc-gate resume 222 --wait 600)\n'
  exit 6
fi
# green unless FAKE_GATE=red
[ "${FAKE_GATE:-green}" = "red" ] && exit 3
exit 0
EOF
  cat > "$T/fake-deploy" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  ship) [ -n "${FAKE_SHIP_LOG:-}" ] && echo "$*" >> "$FAKE_SHIP_LOG"
        # Contract-faithful rc (defect #336): the real `oc-deploy ship
        # --execute --wait` exits 6 on a terminal-RED carrier build and 5 on
        # a wait-timeout / rebase-gate refusal — it NEVER exits 3 from the
        # ship verb. The old fixture returned 3, which the chain's dead
        # rc-3 arm translated into "carrier RED", so the fixture kept a
        # wrong mapping green. FAKE_SHIP_RC forces any ship rc; the
        # FAKE_SHIP_STDERR hook carries the OC_DEPLOY_GATE=<cause> token
        # the real tool writes on stderr.
        if [ -n "${FAKE_SHIP_RC:-}" ]; then
          [ -n "${FAKE_SHIP_STDERR:-}" ] && echo "$FAKE_SHIP_STDERR" >&2
          exit "$FAKE_SHIP_RC"
        fi
        [ "${FAKE_CARRIER:-green}" = "red" ] && exit 6
        # record WHAT was shipped and RESET the poll counter: the marker is
        # written by the SWAP, not by the ship call (real oc-deploy writes it
        # during the Phase B bounce, after the handoff).
        s=""; shift; while [ $# -gt 0 ]; do case "$1" in --sha) s="$2"; shift 2 ;; *) shift ;; esac; done
        d="${OC_DEPLOY_STATE_DIR:-/tmp}"; mkdir -p "$d" 2>/dev/null || true
        printf '%s\n' "$s" > "$d/pending.sha" 2>/dev/null || true
        rm -f "$d/deployed.sha" "$d/polls" 2>/dev/null || true
        echo "carrier run GREEN (fake)"; exit 0 ;;
  poll) # CONTRACT-FAITHFUL (defect fix 2026-09-12): the real `poll --execute`
        # exits 0 PRE-bounce and prints a HANDOFF line, NEVER a completion
        # token. Printing `SWAPPED (fake)` here is exactly how the rc-6 defect
        # stayed invisible — the fixture was more permissive than the tool.
        # Completion is modelled by the MARKER; FAKE_POLL_ROUNDS is now a REAL
        # counter (the old env decrement never persisted across processes), so
        # it can delay the marker to exercise the wait loop.
        d="${OC_DEPLOY_STATE_DIR:-/tmp}"; mkdir -p "$d" 2>/dev/null || true
        n=0; [ -f "$d/polls" ] && n="$(cat "$d/polls" 2>/dev/null || echo 0)"
        n=$((n+1)); printf '%s\n' "$n" > "$d/polls" 2>/dev/null || true
        if [ "$n" -lt "${FAKE_POLL_ROUNDS:-1}" ]; then
          echo "S2 pending (fake)"; exit 0
        fi
        [ -f "$d/pending.sha" ] && cp "$d/pending.sha" "$d/deployed.sha" 2>/dev/null || true
        echo "HANDOFF: Phase B transient unit owns the swap (fake) — poll exits pre-bounce by design"
        exit 0 ;;
  status) # read-only marker view — the same surface the real tool exposes
        d="${OC_DEPLOY_STATE_DIR:-/tmp}"
        printf '{\n  "deployed": {\n    "sha": "%s"\n  }\n}\n' "$(cat "$d/deployed.sha" 2>/dev/null)" ;;
esac
exit 9
EOF
  chmod +x "$T/fake-prchecks" "$T/fake-deploy"
  # #85 fixtures: two stubs that fail ONLY at the poll verb, so the chain still
  # reaches LEG5. One reports oc-deploy's rc=2 "gh api" verdict; the other the
  # rc=2 user-bus precondition. Both exist because the arm that matters is the
  # DISCRIMINATION: a case statement that always chose one branch would pass a
  # one-stub test either way.
  # A THIRD stub for the #85 residual (HQ, 2026-11-19): a run that reports a
  # WARNING first and the real cause second. `oc-deploy: ` prefixes WARNINGs
  # too (`:3889-3901`), so a first-line reader took the warning — which names
  # no cause — defaulted the hint to "user bus", and never displayed line two.
  for _v in api bus warn; do
    cat > "$T/fake-deploy-$_v" <<EOF
#!/usr/bin/env bash
if [ "\$1" = "poll" ]; then
  case "$_v" in
    api)
    echo "oc-deploy: gh api runs query failed after 3 tries within --wait 600s: HTTP 502: Bad Gateway — host: deployed.sha=\$(cat "\${OC_DEPLOY_STATE_DIR:-/tmp}/deployed.sha" 2>/dev/null || echo '<absent>') binary=/usr/local/bin/opencrabs sha256=<unreadable> (binary unreadable at /usr/local/bin/opencrabs)" >&2 ;;
    bus)
    echo "oc-deploy: user bus unreachable — 'systemd-run --user' cannot reach the systemd user manager" >&2 ;;
    warn)
    echo "oc-deploy: WARNING: renice -n 0 failed: Operation not permitted (fake)" >&2
    echo "oc-deploy: gh api runs query failed after 3 tries within --wait 600s: HTTP 502: Bad Gateway — host: deployed.sha=<absent> binary=$T/fake-swapped sha256=<unreadable>" >&2 ;;
  esac
  exit 2
fi
exec "$T/fake-deploy" "\$@"
EOF
    chmod +x "$T/fake-deploy-$_v"
  done
  printf '#!/usr/bin/env bash\nexit 0\n' > "$T/fake-issuelog"
  chmod +x "$T/fake-issuelog"

  # Fixtures are NOT real chains: they run against a temp clone with fake
  # prchecks/deploy and touch no fork state, so they carry the sanctioned
  # freeze override. Without it the guard blocks the selftest's own fixtures
  # and --selftest dies rc 3 during the fork-rebase window.
  run_chain() {
    OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
      bash "$SELF" "$@"
  }

  # 1. full GREEN chain (default --fast)
  # GUARDED (2026-09-12): `set -e` + a bare `OUT="$(...)"` aborts the WHOLE
  # selftest on the first failing chain — rc 6, zero output, no assertion
  # printed. A harness that cannot report a failure cannot be trusted green.
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  check_rc "full-chain-green" "$RC" 0
  case "$OUT" in *SWAPPED*) ok "swapped-marker" ;; *) bad "swapped-marker: $OUT" ;; esac
  # Gate-mode marker (Design E, #415 step 11). The default gate is FAST and the
  # all-features test leg does NOT run, so the mode must be STATED on the ship
  # surface, journalled, AND carried on the final line — otherwise a lane cites
  # a run as CI-gate evidence while the test leg skipped (run 35449400784:
  # step 8 fmt success, step 9 clippy success, step 11 "Run tests" SKIPPED).
  case "$OUT" in *"GATE MODE = FAST"*) ok "gate-mode-stated-fast" ;; *) bad "gate-mode-stated-fast: $OUT" ;; esac
  case "$OUT" in *"does NOT run"*) ok "gate-mode-fast-names-the-skip" ;; *) bad "gate-mode-fast-names-the-skip: $OUT" ;; esac
  grep -q "GATE MODE FAST" "$T/journal.log" && ok "gate-mode-journal-fast" || bad "gate-mode-journal-fast"
  case "$OUT" in *"SWAPPED sha=$FSHA gate=FAST"*) ok "gate-mode-on-final-line" ;; *) bad "gate-mode-on-final-line: $OUT" ;; esac
  # The chain's own final line is now the ONLY SWAPPED token in this test:
  # the stub no longer prints one, so a regression to a stdout-token
  # predicate dies here instead of passing on a fixture that lies.
  grep -q "LEG5 swap poll start" "$T/journal.log" && ok "leg5-ran" || bad "leg5-ran"
  grep -q "LEG4 ship GREEN" "$T/journal.log" && ok "journal-ship-leg" || bad "journal-ship-leg"
  grep -q "DONE SWAPPED" "$T/journal.log" && ok "journal-done" || bad "journal-done"

  grep -q -e "--fast" "$T/prchecks.log" && ok "default-gate-is-fast" || bad "default-gate-is-fast"
  grep -F "LEG1 gate start (resolved argv:" "$T/journal.log" | grep -q -- "--fast"     && ok "journal-leg1-resolved-argv-fast" || bad "journal-leg1-resolved-argv-fast"
  # 1a-#85. LEG5 MUST SURVIVE AN UNREADABLE API, and must say WHICH failure it
  #     hit. Measured 2026-11-18, run 44420005606: a single gh-api blip on poll
  #     #1 killed the chain with rc=2 while deployed.sha AND the installed
  #     binary were both the verified sha, and the message offered the "user
  #     bus" hint — a cause nobody had measured. rc 6 is PRESERVED here: the
  #     fix is a better message plus oc-deploy's own window tolerance, never a
  #     green.
  # run_chain hardcodes OC_DEPLOY_BIN, so an env prefix on it is silently
  # overridden — these two legs carry their own invocation.
  chain_with_deploy() {
    OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$1" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SWAP_TARGET="$T/fake-swapped" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5
  }
  # The host-state line must be read from THIS fixture, never from the box: an
  # arm that stats /usr/local/bin/opencrabs passes or fails on whatever the
  # host happens to be running, which is a fixture reading live state. Note
  # deployed.sha is deliberately NOT pre-written here — the fake `ship` verb
  # clears the marker and only the SWAP restores it, so at LEG5 it is legitimately
  # absent and asserting a sha there would test the fixture's bookkeeping.
  mkdir -p "$T/state"
  printf 'fixture-swapped-binary\n' > "$T/fake-swapped"
  printf '{"artifact_sha256":"%s"}\n' "$(sha256sum "$T/fake-swapped" | awk '{print $1}')" \
    > "$T/state/deployed.meta.json"
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(chain_with_deploy "$T/fake-deploy-api" 2>&1)" || RC=$?
  check_rc "leg5-api-failure-still-rc6" "$RC" 6
  case "$OUT" in *"user bus"*) bad "leg5-api-failure-no-bus-blame: message blames a user bus it did not measure" ;;
                 *) ok "leg5-api-failure-no-bus-blame" ;; esac
  case "$OUT" in *"the API was unreadable"*) ok "leg5-api-failure-names-api" ;;
                 *) bad "leg5-api-failure-names-api: $OUT" ;; esac
  # Two arms, because "carries host state" is not one fact: the line must be
  # present at all, AND it must report the CONFIGURED target — a hardcoded
  # /usr/local/bin/opencrabs would satisfy presence while reading the box.
  case "$OUT" in *"host: deployed.sha="*) ok "leg5-api-failure-carries-host-state" ;;
                 *) bad "leg5-api-failure-carries-host-state: $OUT" ;; esac
  case "$OUT" in *"binary=$T/fake-swapped"*) ok "leg5-api-failure-reads-configured-target" ;;
                 *) bad "leg5-api-failure-reads-configured-target: $OUT" ;; esac
  # POSITIVE CONTROL for the discrimination above: a NON-API rc=2 poll failure
  # must still get the bus hint. Without this arm, a `case` collapsed to the API
  # branch would satisfy all three arms above and mislabel every bus failure.
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(chain_with_deploy "$T/fake-deploy-bus" 2>&1)" || RC=$?
  check_rc "leg5-bus-failure-still-rc6" "$RC" 6
  # The hint itself, not the substring "user bus": the fixture's own cause text is
  # echoed into the message, so a loose grep passes on a `case` that never chose
  # the bus branch (measured: mutant 353/2 left this arm green until tightened).
  case "$OUT" in *"from a shell that HAS the user bus"*) ok "leg5-bus-failure-keeps-bus-hint" ;;
                 *) bad "leg5-bus-failure-keeps-bus-hint: $OUT" ;; esac
  # and it must NOT wear the API label: the discrimination has to point both ways
  case "$OUT" in *"the API was unreadable"*) bad "leg5-bus-failure-no-api-mislabel: a bus failure was labelled an API failure" ;;
                 *) ok "leg5-bus-failure-no-api-mislabel" ;; esac

  # 1a-ter. #85 RESIDUAL (HQ, 2026-11-19): the reader took only the FIRST
  #   `oc-deploy: `-prefixed line. That prefix is shared with WARNINGs, so a
  #   warning printed before the fatal line occupied the slot, matched neither
  #   API pattern, defaulted the hint to "user bus", and — worse — the real
  #   cause on line two was never displayed at all. Three arms, because the fix
  #   makes three separate promises: the cause must be VISIBLE, the hint must
  #   follow the SET rather than its first element, and the warning itself must
  #   not be swallowed either. The positive control for "single cause still
  #   reaches the API hint" is leg5-api-failure-names-api above, which runs
  #   unchanged against the one-cause fixture.
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(chain_with_deploy "$T/fake-deploy-warn" 2>&1)" || RC=$?
  check_rc "leg5-warn-before-fatal-still-rc6" "$RC" 6
  case "$OUT" in *"gh api runs query failed"*) ok "leg5-warn-before-fatal-shows-cause" ;;
                 *) bad "leg5-warn-before-fatal-shows-cause: the fatal line behind a warning was never displayed: $OUT" ;; esac
  case "$OUT" in *"the API was unreadable"*) ok "leg5-warn-before-fatal-picks-api-hint" ;;
                 *) bad "leg5-warn-before-fatal-picks-api-hint: hint chosen off the warning, not the set: $OUT" ;; esac
  case "$OUT" in *"WARNING: renice"*) ok "leg5-warn-before-fatal-keeps-warning" ;;
                 *) bad "leg5-warn-before-fatal-keeps-warning: the warning was dropped from the displayed set: $OUT" ;; esac

  # 1b. full GREEN chain with --full (opts out of --fast)
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 --full 2>&1)" || RC=$?
  check_rc "full-chain-fast" "$RC" 0
  case "$OUT" in *"GATE MODE = FULL"*) ok "gate-mode-stated-full" ;; *) bad "gate-mode-stated-full: $OUT" ;; esac
  case "$OUT" in *"satisfies the CI-gate leg"*) ok "gate-mode-full-claims-test-leg" ;; *) bad "gate-mode-full-claims-test-leg: $OUT" ;; esac
  case "$OUT" in *"does NOT run"*) bad "gate-mode-full-claims-skip" ;; *) ok "gate-mode-full-no-skip-claim" ;; esac
  grep -q "GATE MODE FULL" "$T/journal.log" && ok "gate-mode-journal-full" || bad "gate-mode-journal-full"
  case "$OUT" in *"SWAPPED sha=$FSHA gate=FULL"*) ok "gate-mode-full-on-final-line" ;; *) bad "gate-mode-full-on-final-line: $OUT" ;; esac
  grep -q -e "--fast" "$T/prchecks.log" && bad "full-opt-in-passed-fast" || ok "full-opt-in-omits-fast"
  grep "LEG1 gate start" "$T/journal.log" | grep -q -- "--fast" && bad "journal-leg1-argv-truth-full-claims-fast" || ok "journal-leg1-argv-truth-full-omits-fast"
  grep -F "LEG1 gate start (resolved argv:" "$T/journal.log" | grep -qF "$FSHA"     && ok "journal-leg1-argv-names-sha" || bad "journal-leg1-argv-names-sha"

  # 1b-tt. factory #39: --test-threads rides LEG1's FRESH dispatch. Four legs:
  # forward, ABSENCE control, env default, and shape. The absence control is
  # load-bearing -- without it a mutant that always appends --test-threads (a
  # hardcoded default, say) passes the forward leg VACUOUSLY.
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 --test-threads 2 2>&1)" || RC=$?
  check_rc "test-threads/chain-green" "$RC" 0
  grep -q -e "--test-threads 2" "$T/prchecks.log" && ok "test-threads/forwarded: --test-threads 2 reaches the LEG1 dispatch" || bad "test-threads/forwarded: $(head -2 "$T/prchecks.log" 2>/dev/null | tr '\n' ' ')"
  grep -F "LEG1 gate start (resolved argv:" "$T/journal.log" | grep -q -- "--test-threads 2" && ok "test-threads/journal-resolved-argv" || bad "test-threads/journal-resolved-argv"
  case "$OUT" in *INERT*) bad "test-threads/fresh-path-is-not-inert: $OUT" ;; *) ok "test-threads/fresh-path-is-not-inert" ;; esac

  # 1b-tt-absence. NEGATIVE CONTROL: the same chain WITHOUT the flag (and
  # without the env) must carry NO --test-threads at all.
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  check_rc "test-threads/absent-chain-green" "$RC" 0
  grep -q -e "--test-threads" "$T/prchecks.log" && bad "test-threads/absent: no flag -> dispatch carries NO --test-threads" || ok "test-threads/absent: no flag -> dispatch carries NO --test-threads (absence control)"

  # 1b-tt-env. OC_SHIPCHAIN_TEST_THREADS is the env default. Scoped to the
  # command substitution's own subshell so it cannot leak into later legs.
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_TEST_THREADS=3 FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  check_rc "test-threads/env-chain-green" "$RC" 0
  grep -q -e "--test-threads 3" "$T/prchecks.log" && ok "test-threads/env: OC_SHIPCHAIN_TEST_THREADS=3 reaches the dispatch" || bad "test-threads/env: $(head -2 "$T/prchecks.log" 2>/dev/null | tr '\n' ' ')"

  # 1b-tt-shape. A non-integer is a usage error (rc 2) and NOTHING dispatches.
  rm -f "$T/prchecks.log"
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 --test-threads abc 2>&1)" || RC=$?
  check_rc "test-threads/shape-usage" "$RC" 2
  [ -s "$T/prchecks.log" ] && bad "test-threads/shape-dispatched-nothing" || ok "test-threads/shape: rc 2 and NO dispatch"
  case "$OUT" in *"non-negative integer"*) ok "test-threads/shape-names-the-contract" ;; *) bad "test-threads/shape-names-the-contract: $OUT" ;; esac

  # 1c. LEG2 issue-log FAILURE must ABORT the chain (defect fix 2026-09-19,
  #     fork #361, lane d18ce16a report). Before the fix this leg journalled
  #     "non-fatal" and the chain carried on regardless, so the MANDATORY
  #     one-comment-per-commit step (owner 2026-08-28 22:54Z) failed OPEN on
  #     every chain — #373 reached its ff-merge with 0 comments. The stub is
  #     the ONLY failure injected here, so a chain that still reaches SWAPPED
  #     reddens this case. Invoked explicitly rather than through run_chain:
  #     run_chain pins OC_ISSUELOG_BIN internally, so a pre-set override would
  #     be silently ignored and the test would pass on the GOOD stub.
  printf '#!/usr/bin/env bash\necho "stub: issue-log refuses" >&2\nexit 3\n' > "$T/fake-issuelog-fail"
  chmod +x "$T/fake-issuelog-fail"
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog-fail" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
      bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  check_rc "leg2-fail-aborts" "$RC" 3
  case "$OUT" in *SWAPPED*) bad "leg2-fail-no-swap (chain continued past a failed mandatory leg)" ;; *) ok "leg2-fail-no-swap" ;; esac
  grep -q "LEG2 issue-log FAILED" "$T/journal.log" && ok "leg2-fail-journaled" || bad "leg2-fail-journaled"
  case "$OUT" in *"mandatory per-commit implementation comment did not post"*) ok "leg2-fail-names-the-step" ;; *) bad "leg2-fail-names-the-step: $OUT" ;; esac
  git -C "$T/clone" merge-base --is-ancestor "$FSHA" main 2>/dev/null \
    && bad "leg2-fail-no-merge" || ok "leg2-fail-no-merge"

  # 1d. #395: LEG2's journal must carry the guard's VERDICT. tools.log is
  #     suppressed on this path, so the journal line is the only durable record
  #     — and it used to read a bare "LEG2 issue-log done" whether the comment
  #     posted or the guard skipped it. Two stubs: one emitting the token, one
  #     silent (an older tool version), which must read `unknown`, not nothing.
  printf '#!/usr/bin/env bash\necho "idem=skip"\nexit 0\n' > "$T/fake-issuelog-skip"
  chmod +x "$T/fake-issuelog-skip"
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog-skip" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
      bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  grep -q "LEG2 issue-log done (idem=skip)" "$T/journal.log" && ok "leg2-idem-journaled" || bad "leg2-idem-journaled"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$T/fake-issuelog-notoken"
  chmod +x "$T/fake-issuelog-notoken"
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog-notoken" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
      bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  grep -q "LEG2 issue-log done (idem=unknown)" "$T/journal.log" && ok "leg2-idem-unknown" || bad "leg2-idem-unknown"

  # 1e. #11 LEG2 TRACKER RESOLUTION. Before this fix the leg passed
  #     oc-issue-log NO --repo at all, so the tool silently fell back to its
  #     own default -- the fork. Two measured consequences: a binary-tracker
  #     ship died rc 3 (CHAIN-725ad527, issue #1916, branch
  #     feat/telegram-local-file-links), and a number <= 766 -- which exists
  #     on BOTH trackers -- posted the note to the fork's same-numbered
  #     UNRELATED issue and exited 0. The chain now resolves the tracker and
  #     passes it EXPLICITLY. The stub LOGS ITS ARGV, so each assertion reads
  #     what the chain actually handed the tool rather than what it printed.
  printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$@" >> "$ILOG_ARGV"\nexit 0\n' > "$T/fake-issuelog-argv"
  chmod +x "$T/fake-issuelog-argv"
  # A fake gh answering `issue view <n> --repo <slug> --json state -q .state`
  # from a flat "<slug> <n> <state>" table, so the probe never reaches the
  # network (the real chain's probe is the only network touch in LEG2).
  cat > "$T/fake-gh" <<'FGHEOF'
#!/usr/bin/env bash
slug=""; n=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) slug="$2"; shift 2 ;;
    view) shift; n="${1:-}"; shift ;;
    *) shift ;;
  esac
done
line="$(awk -v s="$slug" -v n="$n" '$1==s && $2==n {print $3}' "${T_PROBE_TABLE:-/dev/null}" 2>/dev/null)"
[ -n "$line" ] || exit 1
printf '%s\n' "$line"
FGHEOF
  chmod +x "$T/fake-gh"
  # Runs the chain with the probe ON and the argv-logging stub. The probe
  # table is always $T/probe.tbl, which each case writes first.
  run_chain_probe() {
    rm -f "$T/journal.log"; : > "$T/ilog.argv"
    git -C "$T/clone" reset -q --hard origin/main
    RC=0
    OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog-argv" OC_FORK_REPO="$T/clone" ILOG_ARGV="$T/ilog.argv" \
      OC_SHIPCHAIN_PROBE_GH="$T/fake-gh" T_PROBE_TABLE="$T/probe.tbl" \
      OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
      OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
        bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 "$@" 2>&1)" || RC=$?
  }

  # The stub writes ONE ARG PER LINE, so a tracker assertion must read the
  # `--repo` line and the slug line as a PAIR -- grepping for the two joined by
  # a space can never match a newline-separated argv.
  argv_has() {
    awk -v a="$1" -v b="$2" 'prev==a && $0==b {found=1} {prev=$0} END{exit !found}' "$T/ilog.argv"
  }

  # (a) binary-tracker-only number -> resolves to the binary tracker and is
  #     passed EXPLICITLY. This is the #1916 regression: with no --repo the
  #     stub would show the tool's own default and the chain would still die
  #     on the real binary-tracker issue.
  printf 'opencrabs/opencrabs 42 OPEN\n' > "$T/probe.tbl"
  run_chain_probe
  check_rc "leg2-probe-binary-rc" "$RC" 0
  argv_has --repo opencrabs/opencrabs && ok "leg2-probe-binary-passes-slug" || bad "leg2-probe-binary-passes-slug: $(tr '\n' ' ' < "$T/ilog.argv")"
  grep -q "LEG2 tracker resolved: opencrabs/opencrabs" "$T/journal.log" && ok "leg2-probe-binary-journaled" || bad "leg2-probe-binary-journaled"

  # (b) the #11 SILENT-MIS-POST class, disambiguated by state: the same number
  #     exists on the fork (CLOSED) and on the binary tracker (OPEN). A lane
  #     ships an issue it is still working, so the uniquely-OPEN copy owns the
  #     ship and the chain must pick the binary tracker, NOT the fork.
  printf 'leshchenko1979/opencrabs 42 CLOSED\nopencrabs/opencrabs 42 OPEN\n' > "$T/probe.tbl"
  run_chain_probe
  check_rc "leg2-probe-collision-rc" "$RC" 0
  argv_has --repo opencrabs/opencrabs && ok "leg2-probe-collision-picks-open" || bad "leg2-probe-collision-picks-open: $(tr '\n' ' ' < "$T/ilog.argv")"

  # (c) BOTH copies open -- the probe CANNOT decide, and this is the one case
  #     where a wrong guess posts a comment onto an unrelated issue. The chain
  #     must FAIL OPEN to the fork (refusing would break every fork ship whose
  #     number collides with an upstream issue) AND say so LOUDLY, so the
  #     default is visible rather than silent.
  printf 'leshchenko1979/opencrabs 42 OPEN\nopencrabs/opencrabs 42 OPEN\n' > "$T/probe.tbl"
  run_chain_probe
  check_rc "leg2-probe-ambiguous-rc" "$RC" 0
  argv_has --repo leshchenko1979/opencrabs && ok "leg2-probe-ambiguous-fails-open-to-fork" || bad "leg2-probe-ambiguous-fails-open-to-fork: $(tr '\n' ' ' < "$T/ilog.argv")"
  case "$OUT" in *"WARNING — issue #42 resolves on MORE THAN ONE tracker"*) ok "leg2-probe-ambiguous-warns" ;; *) bad "leg2-probe-ambiguous-warns: $OUT" ;; esac
  grep -q "LEG2 tracker resolved: leshchenko1979/opencrabs (fork default (AMBIGUOUS:" "$T/journal.log" && ok "leg2-probe-ambiguous-journaled" || bad "leg2-probe-ambiguous-journaled"

  # (d) --issue-repo is AUTHORITATIVE: it bypasses the probe entirely, so a
  #     lane can name the tracker without depending on gh at all. The probe
  #     table here deliberately holds a DIFFERENT answer, which the chain must
  #     ignore -- a resolution that consulted gh anyway would pick it.
  printf 'opencrabs/opencrabs 42 OPEN\n' > "$T/probe.tbl"
  run_chain_probe --issue-repo leshchenko1979/opencrabs-dev-factory
  check_rc "leg2-flag-authoritative-rc" "$RC" 0
  argv_has --repo leshchenko1979/opencrabs-dev-factory && ok "leg2-flag-authoritative" || bad "leg2-flag-authoritative: $(tr '\n' ' ' < "$T/ilog.argv")"
  grep -q "LEG2 tracker resolved: leshchenko1979/opencrabs-dev-factory (--issue-repo (explicit))" "$T/journal.log" && ok "leg2-flag-journaled" || bad "leg2-flag-journaled"

  # 2. gate RED → exit 4, merge must NOT happen
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(FAKE_GATE=red run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "gate-red" "$RC" 4
  git -C "$T/clone" merge-base --is-ancestor "$FSHA" main 2>/dev/null \
    && bad "gate-red-no-merge" || ok "gate-red-no-merge"

  # 3. carrier RED -> exit 4. ship rc 6 IS the real carrier-RED signal; the
  #    fixture used to return rc 3, a code no oc-deploy ship path emits, and
  #    the chain's dead rc-3 arm translated it into "carrier RED" (#336).
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_CARRIER=red run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "carrier-red" "$RC" 4
  grep -q "LEG4 carrier RED" "$T/journal.log" && ok "journal-carrier-red" || bad "journal-carrier-red"

  # 3b. LEG4 WAIT-TIMEOUT (ship rc 5, no rebase-gate token) -> rc 8, its own
  #     journal line, and NOT the INFRA branch: "the build is slow" and "the
  #     build is broken" must not share an exit code (#336).
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_SHIP_RC=5 run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "ship-wait-timeout" "$RC" 8
  grep -q "LEG4 ship WAIT-TIMEOUT" "$T/journal.log" && ok "journal-ship-wait-timeout" || bad "journal-ship-wait-timeout"
  case "$OUT" in *SHIP-WAIT-TIMEOUT*) ok "ship-wait-timeout-msg" ;; *) bad "ship-wait-timeout-msg: $OUT" ;; esac
  grep -q "LEG4 ship INFRA" "$T/journal.log" && bad "ship-wait-timeout-not-infra" || ok "ship-wait-timeout-not-infra"

  # 3c. ship rc 5 WITH a rebase-gate token is the OTHER rc-5 cause: a lane
  #     rebase problem, not a timeout. It must keep rc 5 (NON-FF class) and
  #     must NOT be reported as WAIT-TIMEOUT — the discrimination is the
  #     OC_DEPLOY_GATE= token oc-deploy writes on stderr.
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_SHIP_RC=5 FAKE_SHIP_STDERR='OC_DEPLOY_GATE=rebase-conflict: manual conflict resolution required' run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "ship-rebase-gate" "$RC" 5
  grep -q "LEG4 ship REBASE-GATE rebase-conflict" "$T/journal.log" && ok "journal-ship-rebase-gate" || bad "journal-ship-rebase-gate"
  case "$OUT" in *SHIP-WAIT-TIMEOUT*) bad "rebase-gate-not-timeout" ;; *) ok "rebase-gate-not-timeout" ;; esac

  # 3d. an unexpected ship rc still lands in the INFRA branch (rc 6) — the
  #     catch-all must stay reachable, or a future oc-deploy rc would be
  #     silently swallowed as a success.
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_SHIP_RC=4 run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "ship-infra-other-rc" "$RC" 6
  grep -q "LEG4 ship INFRA rc=4" "$T/journal.log" && ok "journal-ship-infra" || bad "journal-ship-infra"

  # 3d-bis. #756: oc-deploy's post-push ORDER-validator death (die 2) now
  #     carries OC_DEPLOY_GATE=order-gate-failed, so the chain names it as a
  #     gate fault (rc 4) instead of the INFRA bucket (rc 6). Before the fix
  #     the producer emitted no token and the catch-all mislabelled it INFRA.
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_SHIP_RC=2 FAKE_SHIP_STDERR='OC_DEPLOY_GATE=order-gate-failed: ORDER gates failed post-push (see validator exit code)' run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "ship-order-gate-failed" "$RC" 4
  grep -q "LEG4 ship ORDER-GATE-FAILED" "$T/journal.log" && ok "journal-ship-order-gate-failed" || bad "journal-ship-order-gate-failed"
  grep -q "LEG4 ship INFRA" "$T/journal.log" && bad "order-gate-not-infra" || ok "order-gate-not-infra"

  # 3e. the LEG4 --wait DEFAULT is the other half of the fix: with no --wait
  #     flag the chain must hand ship a budget that outlasts a real carrier
  #     build. The old 900 s default expired on every one of the 10 most
  #     recent healthy builds and was reported as INFRA (#336). The fake ship
  #     records its own argv, so this asserts the DEFAULT and not a flag the
  #     test passed.
  rm -f "$T/journal.log" "$T/ship-argv.log"
  RC=0; OUT="$(FAKE_SHIP_LOG="$T/ship-argv.log" run_chain --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "default-wait-green" "$RC" 0
  grep -q -- "--wait 2700" "$T/ship-argv.log" 2>/dev/null \
    && ok "default-ship-wait-2700" || bad "default-ship-wait-2700: $(cat "$T/ship-argv.log" 2>/dev/null)"

  # 3f. (#755) SIGNATURE pre-check: a tip whose Session-Id trailer is ABSENT is
  #     refused rc 3 BEFORE the ff-merge, so main is never stranded at an
  #     unattributable tip. Before the fix the ORDER validator ran at LEG4
  #     (AFTER the merge) and main was left ungated — measured 2026-10-01,
  #     chain CHAIN-541119b2.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" checkout -qb feat-unsigned
  echo us > "$T/clone/us.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "unsigned tip"   # NO Session-Id trailer
  USHA2="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" push -q origin feat-unsigned
  git -C "$T/clone" checkout -q main
  MB="$(git -C "$T/clone" rev-parse main)"
  RC=0; OUT="$(run_chain --sha "$USHA2" --branch feat-unsigned --issue 42 2>&1)" || RC=$?
  check_rc "leg3-unsigned-pre-check" "$RC" 3
  case "$OUT" in *"UNSIGNED (rc 3, caught BEFORE the merge)"*) ok "leg3-unsigned-names-cause" ;; *) bad "leg3-unsigned-names-cause: $OUT" ;; esac
  grep -q "LEG3 PRE-SIGNATURE FAIL" "$T/journal.log" && ok "journal-leg3-pre-signature" || bad "journal-leg3-pre-signature"
  MA="$(git -C "$T/clone" rev-parse main)"
  [ "$MB" = "$MA" ] && ok "leg3-unsigned-main-not-advanced" || bad "leg3-unsigned-main-not-advanced (main moved $MB -> $MA)"

  # 4. STALE-BASE RECOVERY (T10, plan #68) -- POSITIVE CONTROL for the new arm.
  #    The leg here used to be `non-ff` and asserted ONLY rc 5, a code EIGHT
  #    causes share; worse, its fixture never reached NON-FF at all. J-1
  #    converts a non-descendant tip into STALE-BASE before the ff-merge runs,
  #    and nothing between J-1 and that merge touches the network, so ancestry
  #    cannot change in between -- NON-FF (oc-ship, residual arm) is
  #    unreachable within one run and has NO leg, deliberately: a leg for a
  #    state the fixture cannot build would be decoration (CODE.md item 3).
  #    This fixture -- divergent but NON-CONFLICTING -- is exactly the state
  #    the recovery exists for: the work is sound, only the parent is stale.
  rm -f "$T/journal.log"
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qb diverge
  echo diverge > "$T/clone/diverge.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm diverge
  git -C "$T/clone" push -q origin diverge:main   # origin main now has diverge
  DIV="$(git -C "$T/clone" rev-parse origin/main)"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -q feat
  echo more > "$T/clone/more.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm more --trailer "Session-Id: $FIXTURE_SESSION"
  FSHA2="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main   # main = diverged tip; feat diverged from it
  RC=0; OUT="$(run_chain --sha "$FSHA2" --branch feat 2>&1)" || RC=$?
  check_rc "stale-base-recovered" "$RC" 0
  case "$OUT" in *"STALE-BASE recovered"*) ok "stale-base-recovered-names-cause" ;; *) bad "stale-base-recovered-names-cause: $OUT" ;; esac
  grep -q "LEG3 STALE-BASE RECOVERED" "$T/journal.log" && ok "journal-stale-base-recovered" || bad "journal-stale-base-recovered"
  grep -q "patch-ids SAME" "$T/journal.log" && ok "journal-recovery-carried-gate" || bad "journal-recovery-carried-gate"
  LANDED="$(git -C "$T/clone" rev-parse main)"
  # the landing is a ff-merge of the REBASED tip: no merge commit, ever
  [ "$(git -C "$T/clone" rev-list --count --merges "$DIV..$LANDED")" = "0" ] && ok "stale-base-recovered-no-merge-commit" || bad "stale-base-recovered-no-merge-commit"
  # the rebased history sits ON TOP of the new main, and holds exactly the two
  # commits the branch carried -- nothing lost, nothing invented
  git -C "$T/clone" merge-base --is-ancestor "$DIV" "$LANDED" && ok "stale-base-recovered-parented-on-new-main" || bad "stale-base-recovered-parented-on-new-main"
  [ "$(git -C "$T/clone" rev-list --count "$DIV..$LANDED")" = "2" ] && ok "stale-base-recovered-commit-count" || bad "stale-base-recovered-commit-count (want 2 got $(git -C "$T/clone" rev-list --count "$DIV..$LANDED"))"
  # the work survived, and the rebase brought the new main's file with it
  for f in diverge.txt feat.txt more.txt; do
    git -C "$T/clone" cat-file -e "$LANDED:$f" 2>/dev/null && ok "stale-base-recovered-kept-$f" || bad "stale-base-recovered-kept-$f"
  done
  # the recovery pin is dropped once the landing is done (no ref litter)
  [ -z "$(git -C "$T/clone" for-each-ref --format='%(refname)' refs/oc-chain-recovery/)" ] && ok "stale-base-recovered-pin-dropped" || bad "stale-base-recovered-pin-dropped"
  # origin/main is advanced only by oc-deploy (faked here): the chain lands
  # LOCAL main and must not push
  [ "$(git -C "$T/clone" rev-parse origin/main)" = "$DIV" ] && ok "stale-base-recovered-did-not-push" || bad "stale-base-recovered-did-not-push"

  # 4b. STALE-BASE REFUSED when the gate cannot carry -- T10 NEGATIVE CONTROL.
  #     A rebase that CONFLICTS is the cleanest proof: the tip cannot be moved
  #     onto the new main, so the gate validated text that will never land.
  #     The fixture is reused by 4c, so the two messages discriminate on
  #     IDENTICAL state -- "conflicted" vs "disabled" is the whole difference.
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qb cfeat
  echo theirs > "$T/clone/diverge.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm cfeat --trailer "Session-Id: $FIXTURE_SESSION"
  CSHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" push -q origin cfeat   # the branch pre-flight needs it on the fork remote
  git -C "$T/clone" checkout -q main
  echo ours > "$T/clone/diverge.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm cmain
  git -C "$T/clone" push -q origin main
  git -C "$T/clone" reset -q --hard origin/main
  MAINBEFORE="$(git -C "$T/clone" rev-parse main)"
  RC=0; OUT="$(run_chain --sha "$CSHA" --branch cfeat 2>&1)" || RC=$?
  check_rc "stale-base-conflict-refused" "$RC" 5
  case "$OUT" in *"AUTOMATIC RECOVERY DID NOT CARRY THE GATE"*) ok "stale-base-conflict-names-void-gate" ;; *) bad "stale-base-conflict-names-void-gate: $OUT" ;; esac
  case "$OUT" in *"conflicted"*) ok "stale-base-conflict-names-cause" ;; *) bad "stale-base-conflict-names-cause: $OUT" ;; esac
  [ "$(git -C "$T/clone" rev-parse main)" = "$MAINBEFORE" ] && ok "stale-base-conflict-main-untouched" || bad "stale-base-conflict-main-untouched"
  [ -z "$(git -C "$T/clone" for-each-ref --format='%(refname)' refs/oc-chain-recovery/)" ] && ok "stale-base-conflict-no-pin-litter" || bad "stale-base-conflict-no-pin-litter"

  # 4c. the escape hatch, on the SAME conflicting state. The message must say
  #     DISABLED rather than CONFLICTED: that is what proves the knob
  #     suppressed the attempt instead of the attempt merely failing.
  export OC_CHAIN_NO_STALE_RECOVER=1
  RC=0; OUT="$(run_chain --sha "$CSHA" --branch cfeat 2>&1)" || RC=$?
  unset OC_CHAIN_NO_STALE_RECOVER
  check_rc "stale-base-killswitch" "$RC" 5
  case "$OUT" in *"disabled by OC_CHAIN_NO_STALE_RECOVER=1"*) ok "stale-base-killswitch-names-knob" ;; *) bad "stale-base-killswitch-names-knob: $OUT" ;; esac
  case "$OUT" in *"conflicted"*) bad "stale-base-killswitch-did-not-rebase" ;; *) ok "stale-base-killswitch-did-not-rebase" ;; esac

  # RESTORE: origin/main and main back to the diverge tip, feat back to FSHA.
  # 4b advanced origin/main past DIV, and FSHA is not an ancestor of it, so the
  # later legs (`--sha $FSHA --branch feat`) would read as stale otherwise.
  git -C "$T/clone" push -q -f origin "$DIV":main
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" branch -f feat "$FSHA"

  # RESTORE the fixture precondition: tests 5..19 ship `--sha $FSHA --branch
  # feat`, and LEG3 now REQUIRES the branch tip to EQUAL the gated sha (a tip
  # that moved under the chain is the defect). Test 4 left feat at FSHA2.
  git -C "$T/clone" branch -f feat "$FSHA"

  # 4b. TIP MOVED under the chain (defect fix 2026-09-12, lane c6b1a539).
  #     LEG3 merged the branch BY NAME, so a rebase + force-push while the
  #     gate ran would land a tip NO GATE VALIDATED while LEG4 shipped the
  #     ORIGINAL $SHA. The pin must refuse rc 5 AND leave main untouched —
  #     a refusal that still moved main would be the same defect with a
  #     louder message.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -q feat
  git -C "$T/clone" reset -q --hard origin/main
  echo "tip-a" > "$T/clone/tip.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm tip-a
  TSHA="$(git -C "$T/clone" rev-parse HEAD)"
  # the lane rebases + force-pushes AFTER the gate pinned TSHA
  echo "tip-b" >> "$T/clone/tip.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm tip-b
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  MAIN_BEFORE="$(git -C "$T/clone" rev-parse HEAD)"
  RC=0; OUT="$(run_chain --sha "$TSHA" --branch feat 2>&1)" || RC=$?
  check_rc "tip-moved-rc5" "$RC" 5
  case "$OUT" in *"branch tip moved under the chain"*) ok "tip-moved-message" ;; *) bad "tip-moved-message: $OUT" ;; esac
  case "$OUT" in *"oc-ship --sha "*"--branch feat"*) ok "tip-moved-resume-command" ;; *) bad "tip-moved-resume-command: $OUT" ;; esac
  grep -q "LEG3 TIP-MOVED" "$T/journal.log" && ok "tip-moved-journal" || bad "tip-moved-journal"
  [ "$(git -C "$T/clone" rev-parse HEAD)" = "$MAIN_BEFORE" ] && ok "tip-moved-main-untouched" || bad "tip-moved-main-untouched"
  git -C "$T/clone" branch -f feat "$FSHA"   # restore for the tests that follow

  # 4c. THE CHECKOUT-STATE ARMS (#55): the SAME rc 5 as NON-FF but the
  #     OPPOSITE remedy — the branch is correctly based and the LOCAL checkout
  #     is the problem, so a rebase would rewrite a good gated tip and burn the
  #     gate for nothing.
  #
  #     WHY THIS SECTION EXISTS AT ALL. Pre-#55 the arm presumed the checkout
  #     was "simply behind" and prescribed `git merge --ff-only origin/main`.
  #     This fixture then built ahead=1/behind=0 and ASSERTED that remedy —
  #     i.e. the leg encoded a command that provably cannot help in the state
  #     it was given. Measured in a scratch repo and on the live box
  #     (2026-10-25, ledger n=15480): `merge --ff-only origin/main` with main
  #     AHEAD prints "Already up to date.", exits 0, moves nothing, and the
  #     re-run reproduces the identical rc 5. A leg asserting a no-op is a leg
  #     that can never go red on "the remedy reconciles the state", which is the
  #     only property that matters. The assertions below therefore demand the
  #     no-op's ABSENCE, and each arm names the mutant that kills it.
  #
  #     SELF-CONTAINED ON PURPOSE: test 4 force-pushed `diverge` to origin/main
  #     and never restored it, so `feat` is genuinely NOT based on origin/main
  #     by the time this runs — a fixture reusing `feat` would be a TRUE NON-FF
  #     and would assert the wrong branch of the discriminator. Restore
  #     origin/main first, then base a dedicated branch on it.

  # ---- 4c-i. LOCAL-MAIN-AHEAD: the live shape that motivated #55 ----------
  #     ahead=1, behind=0. The remedy must NOT be the ff-merge (it is a no-op
  #     here), must forbid the rebase, and must say the wait is on the owning
  #     lane. MUTANT KILLED: the pre-#55 text — it carried
  #     "merge --ff-only origin/main", so the absence leg goes RED against it.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" push -q -f origin "$FSHA:main"
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qb ahead-feat origin/main
  echo ahead > "$T/clone/ahead.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "ahead-feat on current origin/main" --trailer "Session-Id: $FIXTURE_SESSION"
  git -C "$T/clone" push -q origin ahead-feat
  AHEAD_TIP="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  echo "local-only" > "$T/clone/local-only.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "local-only (unpushed peer commit)"
  AHEAD_MAIN="$(git -C "$T/clone" rev-parse HEAD)"
  # sanity: this fixture must BE the ahead=1/behind=0 state, or it tests nothing
  [ "$(git -C "$T/clone" rev-list --count origin/main..main)" = "1" ] && ok "ahead-fixture-is-ahead-1" || bad "ahead-fixture-is-ahead-1"
  [ "$(git -C "$T/clone" rev-list --count main..origin/main)" = "0" ] && ok "ahead-fixture-is-behind-0" || bad "ahead-fixture-is-behind-0"
  RC=0; OUT="$(run_chain --sha "$AHEAD_TIP" --branch ahead-feat 2>&1)" || RC=$?
  check_rc "local-main-ahead-rc5" "$RC" 5
  case "$OUT" in *"LOCAL-MAIN-AHEAD (rc 5, NOT a rebase problem"*) ok "local-main-ahead-message" ;; *) bad "local-main-ahead-message: $OUT" ;; esac
  case "$OUT" in *"Do NOT rebase"*) ok "local-main-ahead-forbids-rebase" ;; *) bad "local-main-ahead-forbids-rebase: $OUT" ;; esac
  # THE #55 LEG: the no-op remedy must be GONE. This is the assertion the old
  # fixture inverted, and the one that goes RED if the no-op ever returns.
  case "$OUT" in *"merge --ff-only origin/main"*) bad "local-main-ahead-must-not-prescribe-the-noop-ff-merge" ;; *) ok "local-main-ahead-no-noop-remedy" ;; esac
  # and it must SAY the reconcile is a no-op, so a lane is not left guessing
  # why the obvious command did nothing
  case "$OUT" in *"NO-OP"*) ok "local-main-ahead-names-the-noop" ;; *) bad "local-main-ahead-names-the-noop: $OUT" ;; esac
  case "$OUT" in *"NON-FF: rebase"*) bad "local-main-ahead-misclassified-as-non-ff" ;; *) ok "local-main-ahead-not-non-ff" ;; esac
  grep -q "LEG3 LOCAL-MAIN-AHEAD" "$T/journal.log" && ok "local-main-ahead-journal" || bad "local-main-ahead-journal"
  # the journal line must carry the COUNTS, because the counts are the evidence
  grep -q "ahead=1" "$T/journal.log" && ok "local-main-ahead-journal-carries-counts" || bad "local-main-ahead-journal-carries-counts"
  [ "$(git -C "$T/clone" rev-parse HEAD)" = "$AHEAD_MAIN" ] && ok "local-main-ahead-main-untouched" || bad "local-main-ahead-main-untouched"

  # ---- 4c-ii. LOCAL-MAIN-DIVERGED: both sides moved -----------------------
  #     ahead=1, behind=1. Neither a wait nor a no-op settles it; the text must
  #     say so and must not send the lane at a rebase of the BRANCH.
  #     MUTANT KILLED: an arm that only tests ahead>0 would call this AHEAD and
  #     claim "main already contains origin/main", which is false here.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qb div-feat origin/main
  echo div > "$T/clone/div.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "div-feat on current origin/main" --trailer "Session-Id: $FIXTURE_SESSION"
  git -C "$T/clone" push -q origin div-feat
  DIV_TIP="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  echo "div-local" > "$T/clone/div-local.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "div-local (main moves independently)"
  DIV_MAIN="$(git -C "$T/clone" rev-parse HEAD)"
  # move origin/main to the tip, so main is ahead 1 AND behind 1
  git -C "$T/clone" push -q origin div-feat:main
  [ "$(git -C "$T/clone" rev-list --count origin/main..main)" = "1" ] && ok "diverged-fixture-is-ahead-1" || bad "diverged-fixture-is-ahead-1"
  [ "$(git -C "$T/clone" rev-list --count main..origin/main)" = "1" ] && ok "diverged-fixture-is-behind-1" || bad "diverged-fixture-is-behind-1"
  RC=0; OUT="$(run_chain --sha "$DIV_TIP" --branch div-feat 2>&1)" || RC=$?
  check_rc "local-main-diverged-rc5" "$RC" 5
  case "$OUT" in *"LOCAL-MAIN-DIVERGED (rc 5, NOT a rebase problem"*) ok "local-main-diverged-message" ;; *) bad "local-main-diverged-message: $OUT" ;; esac
  case "$OUT" in *"Do NOT rebase"*) ok "local-main-diverged-forbids-rebase" ;; *) bad "local-main-diverged-forbids-rebase: $OUT" ;; esac
  case "$OUT" in *"NO-OP"*) bad "local-main-diverged-must-not-claim-a-noop-wait" ;; *) ok "local-main-diverged-not-a-noop-wait" ;; esac
  case "$OUT" in *"merge --ff-only origin/main"*) bad "local-main-diverged-must-not-prescribe-the-noop-ff-merge" ;; *) ok "local-main-diverged-no-noop-remedy" ;; esac
  grep -q "LEG3 LOCAL-MAIN-DIVERGED" "$T/journal.log" && ok "local-main-diverged-journal" || bad "local-main-diverged-journal"
  grep -q "behind=1" "$T/journal.log" && ok "local-main-diverged-journal-carries-counts" || bad "local-main-diverged-journal-carries-counts"
  [ "$(git -C "$T/clone" rev-parse HEAD)" = "$DIV_MAIN" ] && ok "local-main-diverged-main-untouched" || bad "local-main-diverged-main-untouched"
  # restore for the tests that follow
  git -C "$T/clone" push -q -f origin "$FSHA:main"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main

  # ---- J-1 (c23): PRE-LEG3 ANCESTRY RE-CHECK ------------------------------
  # The gate runs BEFORE the landing lock, so origin/main can move while the
  # chain waits in the queue and the ff-merge performs no rebase of its own.
  # This fixture makes the branch's base genuinely superseded: base a branch on
  # origin/main, then advance origin/main PAST it. The pre-check must name the
  # cause BEFORE attempting the merge, so the operator is never left reading a
  # generic NON-FF whose remedy (rebase) is one of two opposite answers.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" push -q -f origin "$FSHA:main"
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qb preanc-feat origin/main
  echo preanc > "$T/clone/preanc.txt"
  echo preanc-side > "$T/clone/base.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "preanc-feat on a base that will be superseded" --trailer "Session-Id: $FIXTURE_SESSION"
  git -C "$T/clone" push -q origin preanc-feat
  PREANC_TIP="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  echo later > "$T/clone/later.txt"
  echo main-side > "$T/clone/base.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "main advances past preanc-feat's base"
  git -C "$T/clone" push -q origin main
  RC=0; OUT="$(run_chain --sha "$PREANC_TIP" --branch preanc-feat 2>&1)" || RC=$?
  check_rc "pre-ancestry-rc5" "$RC" 5
  case "$OUT" in *"STALE-BASE (rc 5, caught BEFORE the merge attempt)"*) ok "pre-ancestry-message" ;; *) bad "pre-ancestry-message: $OUT" ;; esac
  case "$OUT" in *"oc-rebase-safety"*) ok "pre-ancestry-names-the-remedy" ;; *) bad "pre-ancestry-names-the-remedy: $OUT" ;; esac
  # the carry-forward is what makes the remedy affordable rather than a fresh
  # ~25-min gate for identical bytes (Duty-4 n=2520) -- the message must name it
  case "$OUT" in *"--gated-run"*) ok "pre-ancestry-names-the-carry-forward" ;; *) bad "pre-ancestry-names-the-carry-forward: $OUT" ;; esac
  grep -q "LEG3 PRE-ANCESTRY MISS" "$T/journal.log" && ok "pre-ancestry-journal" || bad "pre-ancestry-journal"
  # the whole point of a PRE-check: the generic NON-FF text must NOT be what
  # the operator reads, because it cannot distinguish the two opposite causes
  case "$OUT" in *"NON-FF"*) bad "pre-ancestry-must-not-read-as-non-ff" ;; *) ok "pre-ancestry-not-non-ff" ;; esac
  # the ALREADY-LANDED arm: a tip already contained in origin/main is not a
  # rebase problem either, and must say so rather than advise a rebase
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" checkout -qb landed-feat origin/main
  echo landed > "$T/clone/landed.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "landed-feat"
  git -C "$T/clone" push -q origin landed-feat
  LANDED_TIP="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" merge -q --ff-only landed-feat
  # main must advance PAST the landed tip, or TIP == origin/main and the
  # pre-check correctly falls through as a harmless no-op merge (rc 0) --
  # the ALREADY-LANDED arm is for a tip CONTAINED in a main that moved on.
  echo after > "$T/clone/after.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "main advances past the landed tip"
  git -C "$T/clone" push -q origin main
  RC=0; OUT="$(run_chain --sha "$LANDED_TIP" --branch landed-feat 2>&1)" || RC=$?
  check_rc "pre-ancestry-already-landed-rc5" "$RC" 5
  case "$OUT" in *"ALREADY-LANDED"*) ok "pre-ancestry-already-landed-message" ;; *) bad "pre-ancestry-already-landed-message: $OUT" ;; esac
  case "$OUT" in *"Do NOT re-gate"*) ok "pre-ancestry-already-landed-forbids-regate" ;; *) bad "pre-ancestry-already-landed-forbids-regate: $OUT" ;; esac
  # restore for the tests that follow
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  # NOTE (#55): the stale-feat branch cleanup that used to live here is GONE with
  # the leg that created it. The old 4c fixture built an AHEAD main on `stale-feat`
  # and then asserted the ff-merge no-op as its remedy; 4c-i/4c-ii now build
  # ahead-feat / div-feat and assert the no-op's ABSENCE. Deleting a branch that
  # no longer exists aborts the whole battery under `set -e` -- which is exactly
  # how this was found (battery died at 109 legs, not on an assertion).

  # 5. gated-sha with fake gh shim
  # #153: IDENTITY IS A TOKEN, NOT A SUBSTRING. oc-ship no longer reads the
  # gated ref off a run's name or headSha (GitHub exposes neither: dispatch
  # inputs are `inputs: null`, and headSha names the CARRIER). It reads the
  # run's event+headBranch, then extracts the 40-hex token from the JOB NAME
  # and compares it EXACTLY. This shim answers THAT contract, parameterised so
  # a leg can vary the single field under test:
  #   FAKE_GH_REF         event+branch of run 11111 (default: carrier dispatch)
  #   FAKE_GH_JOB_SHA     the 40-hex token in the job name (default $FSHA)
  #   FAKE_GH_JOB_SUFFIX  text appended AFTER the token (the substring trap)
  #   FAKE_GH_JOB_CONC    that job's conclusion (default success)
  # Run 22222 is permanently a `push` run: it must always be SKIPPED as
  # not-a-carrier-dispatch, which is what makes the positive control prove the
  # scan DISCRIMINATES rather than merely returning the first run it sees.
  cat > "$T/fake-gh" <<EOF
#!/usr/bin/env bash
case "\$*" in
  *"run list"*)
    printf '%s\n' 11111 22222
    ;;
  *"run view 11111"*"event,headBranch"*)
    printf '%s\n' "\${FAKE_GH_REF:-workflow_dispatch ci/quick-build-linux}"
    ;;
  *"run view 11111"*"--json jobs"*)
    printf 'PR-lane gates (%s)%s\t%s\n' "\${FAKE_GH_JOB_SHA:-$FSHA}" "\${FAKE_GH_JOB_SUFFIX:-}" "\${FAKE_GH_JOB_CONC:-success}"
    ;;
  *"run view 22222"*"event,headBranch"*)
    printf '%s\n' "push refs/heads/main"
    ;;
  *)
    exit 1
    ;;
esac
exit 0
EOF
  chmod +x "$T/fake-gh"

  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  # reset origin/main back to the commit before diverge so feat is fast-forwardable
  git -C "$T/clone" push -q -f origin "$FSHA:main"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh" run_chain --sha "$FSHA" --branch feat --gated-sha "$FSHA" 2>&1)" || RC=$?
  check_rc "gated-sha-green" "$RC" 0
  grep -q "LEG1 gate pre-verified GREEN (gh run 11111" "$T/journal.log" && ok "journal-gated-sha" || bad "journal-gated-sha"
  # (#672) THE BANNER MUST NOT CLAIM A MODE THAT NEVER RAN. NO gate leg runs on
  # the --gated-sha path, so the mode is CARRIED-FORWARD. Before #672 the banner
  # was computed from FAST_GATE alone and printed "GATE MODE = FAST ... the
  # all-features TEST leg does NOT run" over a gate BORROWED from an earlier
  # run whose test leg may well have run (measured 2026-09-28, lane c2ba4ef2:
  # --gated-sha printed FAST while carrying run 36401057885 forward, whose "Run
  # tests" step ran 9970 passed / 0 failed). The detached log this prints to is
  # exactly what a lane cites as its LEG3 receipt, so the false mode was a false
  # evidence claim rather than a cosmetic one.
  case "$OUT" in *"GATE MODE = CARRIED-FORWARD"*) ok "gate-mode-gated-sha-carried-forward" ;; *) bad "gate-mode-gated-sha-carried-forward: $OUT" ;; esac
  case "$OUT" in *"GATE MODE = FAST"*) bad "gate-mode-gated-sha-claims-fast (no leg ran)" ;; *) ok "gate-mode-gated-sha-does-not-claim-fast" ;; esac
  grep -q "GATE MODE CARRIED-FORWARD" "$T/journal.log" && ok "gate-mode-journal-carried-forward" || bad "gate-mode-journal-carried-forward"
  # 5b. Duty-4 n=2520: a METADATA-ONLY rebase rewrites the sha while the patch
  # is unchanged, so strict sha equality voided a GREEN gate by construction
  # (measured 2026-09-25: ONE patch, THREE shas, THREE full ~25-min gates). The
  # twin below is built by amending only the commit DATE: same tree, same
  # parent, same diff -> same patch-id, different sha.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q --detach "$FSHA"
  GIT_COMMITTER_DATE="2020-01-01T00:00:00Z" git -C "$T/clone" commit -q --amend --no-edit --date="2020-01-01T00:00:00Z"
  TWIN="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" tag -f rebasetwin "$TWIN" >/dev/null 2>&1 || true
  if [ "$TWIN" = "$FSHA" ]; then
    bad "gated-sha-rebase-twin: fixture failed to build a distinct sha"
  else
    ok "gated-sha-rebase-twin: ${FSHA:0:8} -> ${TWIN:0:8}"
    if oc_same_patch "$T/clone" "$FSHA" "$TWIN"; then
      ok "gated-sha-rebase-patchid-equal"
    else
      bad "gated-sha-rebase-patchid-equal: twin is NOT content-identical (fixture broken)"
    fi
    git -C "$T/clone" checkout -q main
    git -C "$T/clone" reset -q --hard origin/main
    # #153: a content-identical rebase is visible on the tracker ONLY as a job
    # name carrying the PRE-rebase sha, which is exactly the SECOND probe the
    # exact-token scan makes ($SHA first, $GATED_SHA second). Without this the
    # job name carries $FSHA, probe 1 matches, and the leg silently stops
    # exercising the carry-forward path at all.
    RC=0; OUT="$(FAKE_GH_JOB_SHA="$TWIN" OC_GH="$T/fake-gh" run_chain --sha "$FSHA" --branch feat --gated-sha "$TWIN" 2>&1)" || RC=$?
    check_rc "gated-sha-rebase-carried" "$RC" 0
    case "$OUT" in *"LEG1 gate carried forward"*) ok "gated-sha-rebase-loud" ;; *) bad "gated-sha-rebase-loud: $OUT" ;; esac
  fi

  # 5c. CONTROL: a gated-sha whose CONTENT genuinely differs must still die rc 2.
  # Without this arm the content leg could silently degrade into a blanket
  # acceptance of any mismatched sha, which is worse than the defect it fixes.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  # NOTE: `main` is NOT usable here — an earlier leg force-pushed it to $FSHA,
  # so rev-parse main == SHA and the equality check passes trivially (this leg
  # failed that way on first run). Build a twin with a REAL tree change instead.
  git -C "$T/clone" checkout -q --detach "$FSHA"
  printf 'control\n' >> "$T/clone/README.md"
  git -C "$T/clone" add README.md
  GIT_COMMITTER_DATE="2020-01-02T00:00:00Z" git -C "$T/clone" commit -q --amend --no-edit --date="2020-01-02T00:00:00Z"
  OTHER="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  if [ "$OTHER" = "$FSHA" ] || oc_same_patch "$T/clone" "$FSHA" "$OTHER"; then
    bad "gated-sha-different-content: fixture built a CONTENT-IDENTICAL twin (control is vacuous)"
  else
    RC=0; OUT="$(OC_GH="$T/fake-gh" run_chain --sha "$FSHA" --branch feat --gated-sha "$OTHER" 2>&1)" || RC=$?
    check_rc "gated-sha-different-content" "$RC" 2
    case "$OUT" in *"LEG1 gate carried forward"*) bad "gated-sha-different-content-no-carry: carried a gate across DIFFERENT content" ;; *) ok "gated-sha-different-content-no-carry" ;; esac
  fi

  # 5d. #153: IDENTITY IS A TOKEN, NOT A SUBSTRING.
  # The pre-#153 scan matched `select(.name | contains($SHA))` on the RUN name.
  # That is not proof of identity: it accepts an ABBREVIATED sha and it accepts
  # any name that merely CONTAINS those bytes. GitHub exposes no dispatch inputs
  # (`inputs: null`, measured 2026-11-23 on run 45183001870) and headSha names
  # the CARRIER, so the job name is the sole identity carrier -- and only TOKEN
  # EQUALITY establishes it. Leg 5 above is the POSITIVE CONTROL for this block:
  # it keeps these three from passing on a scan that never matches anything.
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main

  # (a) CONTAINS != IDENTITY. The job name carries a DIFFERENT 40-hex as its own
  # token and $FSHA only as trailing text. `contains($SHA)` adopts this; exact
  # token equality must refuse it.
  _f1="${FSHA:0:1}"
  if [ "$_f1" = "a" ]; then _nf=b; else _nf=a; fi
  SUBSHA="$_nf${FSHA:1}"
  if [ "$SUBSHA" = "$FSHA" ]; then
    bad "153-substring: fixture built an identical sha"
  else
    rm -f "$T/journal.log"
    RC=0; OUT="$(FAKE_GH_JOB_SHA="$SUBSHA" FAKE_GH_JOB_SUFFIX=" for $FSHA" OC_GH="$T/fake-gh" run_chain --sha "$FSHA" --branch feat --gated-sha "$FSHA" 2>&1)" || RC=$?
    check_rc "153-substring-is-not-identity" "$RC" 4
    # Read the JOURNAL, not $OUT: the pre-verified line is journalled, never
    # printed, so an $OUT grep here could never go red (found by mutation:
    # this check stayed green while M1 adopted the substituted run).
    if grep -q "LEG1 gate pre-verified GREEN" "$T/journal.log" 2>/dev/null; then
      bad "153-substring-was-adopted (contains() would have passed this)"
    else
      ok "153-substring-not-adopted"
    fi
  fi

  # (b) AN ABBREVIATED sha is not the sha. oc_job_sha returns EMPTY for a short
  # token, and an empty token must never compare equal to anything.
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_GH_JOB_SHA="${FSHA:0:12}" OC_GH="$T/fake-gh" run_chain --sha "$FSHA" --branch feat --gated-sha "$FSHA" 2>&1)" || RC=$?
  check_rc "153-abbreviated-sha-refused" "$RC" 4
  grep -q "1 job name(s) carried no 40-hex token" "$T/journal.log" && ok "153-abbreviated-counted-as-unpinned" || bad "153-abbreviated-counted-as-unpinned"

  # (c) A RUN OF ANOTHER EVENT is not this gate at all. Reading one as the gate
  # would verify a tree nobody asked about, so it is skipped and COUNTED.
  rm -f "$T/journal.log"
  RC=0; OUT="$(FAKE_GH_REF="push refs/heads/main" OC_GH="$T/fake-gh" run_chain --sha "$FSHA" --branch feat --gated-sha "$FSHA" 2>&1)" || RC=$?
  check_rc "153-non-carrier-event-refused" "$RC" 4
  # FAIL-CLOSED VISIBILITY (#153): an unestablished identity must never read as
  # "no run exists" when the real cause is "none of these runs were this gate".
  grep -q "LEG1 identity scan:" "$T/journal.log" && ok "153-population-journalled" || bad "153-population-journalled"
  grep -q "2 not a carrier workflow_dispatch" "$T/journal.log" && ok "153-population-counts-both-nondispatch" || bad "153-population-counts-both-nondispatch"


  # 6. gated-run with fake gh shim
  cat > "$T/fake-gh-run" <<'EOF'
#!/usr/bin/env bash
echo "completed success success"
exit 0
EOF
  chmod +x "$T/fake-gh-run"

  # 1f. #92 THE WHOLE POINT, ASSERTED END TO END. A CANCELLED-superseded gate
  # must RE-ARM AS A RESUME: the child waits on the superseder, and NO second
  # gate is dispatched. Both halves are load-bearing -- a re-arm that merely
  # avoids re-dispatching but waits on nothing is a silent no-op, and a resume
  # that also re-dispatches cancels the very run it resumed.
  cat > "$T/fake-gh-resume" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "${FAKE_GH_LOG:-/dev/null}"
echo "completed success success"
exit 0
EOF
  chmod +x "$T/fake-gh-resume"
  rm -f "$T/journal.log" "$T/prchecks.log" "$T/gh.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-resume" FAKE_GH_LOG="$T/gh.log" \
      FAKE_PRCHECKS_LOG="$T/prchecks.log" FAKE_GATE=infra6 \
      OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
      run_chain --sha "$FSHA" --branch feat --issue 42 2>&1)" || RC=$?
  check_rc "rearm-rc6-resume-ships" "$RC" 0
  grep -q "gate-resume:222" "$T/journal.log" \
    && ok "rearm-rc6-resume-journalled" \
    || bad "rearm-rc6-resume-journalled: [$(grep 'RE-ARM' "$T/journal.log" 2>/dev/null | tr '\n' ' ')]"
  grep -q "run view 222" "$T/gh.log" \
    && ok "rearm-rc6-child-waits-on-superseder" \
    || bad "rearm-rc6-child-waits-on-superseder: [$(cat "$T/gh.log" 2>/dev/null | tr '\n' ' ')]"
  _pd="$(grep -c . "$T/prchecks.log" 2>/dev/null || true)"
  [ "${_pd:-0}" = 1 ] && ok "rearm-rc6-dispatches-exactly-once" \
    || bad "rearm-rc6-dispatches-exactly-once (got ${_pd:-0}: a resume must start nothing)"

  # 1g. #92 GUARD 3 -- the operator opt-out still wins over a NAMED superseder.
  # Without this arm the resume class can be wired in a way that bypasses
  # --no-rearm, and every other arm still passes: the positive control only
  # proves the class fires, never that it can be switched off.
  rm -f "$T/journal.log" "$T/prchecks.log" "$T/gh.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-resume" FAKE_GH_LOG="$T/gh.log" \
      FAKE_PRCHECKS_LOG="$T/prchecks.log" FAKE_GATE=infra6 \
      OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
      run_chain --sha "$FSHA" --branch feat --issue 42 --no-rearm 2>&1)" || RC=$?
  check_rc "norearm-rc6-resume-flag-exit-unchanged" "$RC" 6
  grep -q "RE-ARM" "$T/journal.log" \
    && bad "norearm-rc6-resume-flag-suppresses-restart" \
    || ok "norearm-rc6-resume-flag-suppresses-restart"

  # 1h. #92 GUARD 4 -- the budget bounds a resume exactly as it bounds any other
  # re-arm. MAX=0 is the sharpest form: the class fires but no attempt is spent.
  rm -f "$T/journal.log" "$T/prchecks.log" "$T/gh.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-resume" FAKE_GH_LOG="$T/gh.log" \
      FAKE_PRCHECKS_LOG="$T/prchecks.log" FAKE_GATE=infra6 \
      OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 OC_SHIPCHAIN_REARM_MAX=0 \
      run_chain --sha "$FSHA" --branch feat --issue 42 2>&1)" || RC=$?
  check_rc "norearm-rc6-resume-max0-exit-unchanged" "$RC" 6
  grep -q "RE-ARM" "$T/journal.log" \
    && bad "norearm-rc6-resume-max0-suppresses-restart" \
    || ok "norearm-rc6-resume-max0-suppresses-restart"

  # 1i. #92 GUARD 5 -- REPLACEMENT, NOT APPEND. A pre-existing --gated-run must
  # not survive beside the new one: two flags are last-wins at best and a silent
  # misparse at worst, and a surviving --gated-sha would describe a DIFFERENT
  # gate than the run actually waited on. Asserted against the real function
  # text, extracted from this file, so the arm cannot drift from production.
  sed -n '/^_chain_rearm_argv()/,/^}/p' "$SELF" > "$T/rearm-argv.sh"
  if [ -s "$T/rearm-argv.sh" ]; then
    _av="$(bash -c 'source "$1"; CHAIN_ARGV=(--sha abc --branch feat --gated-run 111 --test-threads 2); _chain_rearm_argv 222' _ "$T/rearm-argv.sh" 2>/dev/null | tr '\n' ' ')"
    _gn="$(grep -o -- '--gated-run' <<< "$_av" | wc -l | tr -d ' ')"
    [ "$_gn" = 1 ] && ok "rearm-rc6-argv-has-one-gated-run" \
      || bad "rearm-rc6-argv-has-one-gated-run (got $_gn): [$_av]"
    case "$_av" in
      *"222"*) ok "rearm-rc6-argv-carries-superseder" ;;
      *) bad "rearm-rc6-argv-carries-superseder: [$_av]" ;;
    esac
    case "$_av" in
      *"111"*) bad "rearm-rc6-argv-drops-stale-gated-run: [$_av]" ;;
      *) ok "rearm-rc6-argv-drops-stale-gated-run" ;;
    esac
  else
    bad "rearm-rc6-argv-extract: _chain_rearm_argv not found in \$SELF"
  fi

  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-run" run_chain --sha "$FSHA" --branch feat --gated-run 11111 2>&1)" || RC=$?
  check_rc "gated-run-green" "$RC" 0
  grep -q "LEG1 gate pre-verified GREEN (gh run: 11111 completed success" "$T/journal.log" && ok "journal-gated-run" || bad "journal-gated-run"

  # 6-tt. factory #39: --test-threads on a CARRY-FORWARD path is INERT, and the
  # chain must SAY SO. A silent drop would let a lane read the carried run as
  # mitigated evidence it never received -- and NOTHING may dispatch here, so
  # the empty fake-prchecks log is the control that no second gate was fired.
  rm -f "$T/prchecks.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-run" FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --gated-run 11111 --test-threads 2 2>&1)" || RC=$?
  check_rc "test-threads/inert-carry-green" "$RC" 0
  case "$OUT" in *INERT*) ok "test-threads/inert-declared-on-stderr" ;; *) bad "test-threads/inert-declared-on-stderr: $OUT" ;; esac
  grep -q "INERT" "$T/journal.log" && ok "test-threads/inert-journalled" || bad "test-threads/inert-journalled"
  [ -s "$T/prchecks.log" ] && bad "test-threads/inert-dispatched-nothing" || ok "test-threads/inert: no dispatch on the carry-forward path"

  # 6a. Duty-4 n=2520, the arm the editor lane ACTUALLY hit: --gated-run whose
  # job name carries the PRE-rebase sha. The job match is by `contains($SHA)`,
  # so a metadata-only rebase reads "no-job" and dies rc 4 by construction —
  # exactly what voided #459's GREEN gate and forced a third full 25-min gate.
  # The shim keys on which sha the query names: the twin is content-identical
  # (leg 5b proved the patch-ids match), so the carry must fire.
  # The shim models a REAL carrier run: its job NAME carries the pre-rebase sha
  # ($TWIN), so the first job-match query (contains($SHA)) answers no-job while
  # the jobs[]? | .name query returns the twin's job line.
  cat > "$T/fake-gh-run-rebase" <<EOF
#!/usr/bin/env bash
case "\$*" in
  *"jobs[]? | .name"*) printf 'ship / Linux amd64 (%s, telegram)\n' "$TWIN" ;;
  *"$TWIN"*) echo "completed success success" ;;
  *) echo "completed success no-job" ;;
esac
exit 0
EOF
  chmod +x "$T/fake-gh-run-rebase"
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-run-rebase" run_chain --sha "$FSHA" --branch feat --gated-run 11111 2>&1)" || RC=$?
  check_rc "gated-run-rebase-carried" "$RC" 0
  case "$OUT" in *"LEG1 gate carried forward"*) ok "gated-run-rebase-loud" ;; *) bad "gated-run-rebase-loud: $OUT" ;; esac

  # 6b-CONTROL: a --gated-run whose job sha is NOT content-identical must still
  # die rc 4. Without this arm the carry could degrade into accepting any run.
  rm -f "$T/journal.log"
  cat > "$T/fake-gh-run-unrelated" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  *"jobs[]? | .name"*) echo "ship / Linux amd64 (1111111111111111111111111111111111111111, telegram)" ;;
  *) echo "completed success no-job" ;;
esac
exit 0
EOF
  chmod +x "$T/fake-gh-run-unrelated"
  RC=0; OUT="$(OC_GH="$T/fake-gh-run-unrelated" run_chain --sha "$FSHA" --branch feat --gated-run 11111 2>&1)" || RC=$?
  check_rc "gated-run-unrelated-content" "$RC" 4
  case "$OUT" in *"LEG1 gate carried forward"*) bad "gated-run-unrelated-no-carry: carried a gate across UNRELATED content" ;; *) ok "gated-run-unrelated-no-carry" ;; esac

  # 6b-repo. factory #90: --repo is a gh SLUG, never a checkout path. A path
  # used to reach `gh -R` verbatim, gh refused it, the refusal went to
  # /dev/null, and the chain died rc 4 reporting a phantom status mismatch on
  # a run that was actually green. Refuse at the arg boundary, naming the knob
  # that DOES take a path.
  RC=0; OUT="$(OC_GH="$T/fake-gh-run" run_chain --sha "$FSHA" --branch feat --gated-run 11111 --repo /root/opencrabs-wt/857-notify-transport-cause 2>&1)" || RC=$?
  check_rc "repo-path-refused" "$RC" 2
  case "$OUT" in
    *"OC_FORK_REPO"*) ok "repo-path-names-checkout-knob" ;;
    *) bad "repo-path-names-checkout-knob: $OUT" ;;
  esac
  # CONTROL: the same invocation with a real slug must NOT be refused here.
  # Without it the arm passes on a guard that rejects every --repo.
  RC=0; OUT="$(OC_GH="$T/fake-gh-run" run_chain --sha "$FSHA" --branch feat --gated-run 11111 --repo leshchenko1979/opencrabs 2>&1)" || RC=$?
  check_rc "repo-slug-accepted" "$RC" 0

  # 6b-ghfail. When gh CANNOT ANSWER, the chain must say so and must not read
  # the empty answer as a RED gate. Before #90 both cases reached the same die
  # and printed `run status '' != 'completed success success'`.
  cat > "$T/fake-gh-run-broken" <<'EOF'
#!/usr/bin/env bash
echo "failed to determine base repo: expected the \"[HOST/]OWNER/REPO\" format" >&2
exit 1
EOF
  chmod +x "$T/fake-gh-run-broken"
  RC=0; OUT="$(OC_GH="$T/fake-gh-run-broken" run_chain --sha "$FSHA" --branch feat --gated-run 11111 2>&1)" || RC=$?
  check_rc "gated-run-gh-failure-rc4" "$RC" 4
  case "$OUT" in
    *"could not be read"*) ok "gated-run-gh-failure-named" ;;
    *) bad "gated-run-gh-failure-named: $OUT" ;;
  esac
  case "$OUT" in
    *"expected the"*) ok "gated-run-gh-failure-carries-stderr" ;;
    *) bad "gated-run-gh-failure-carries-stderr: gh's own message was swallowed — $OUT" ;;
  esac
  case "$OUT" in
    *"!= 'completed success success'"*) bad "gated-run-gh-failure-no-phantom-verdict: still reported a status mismatch for a run it never read" ;;
    *) ok "gated-run-gh-failure-no-phantom-verdict" ;;
  esac

  # 6b. gated-run with in_progress status triggers oc-gate resume
  cat > "$T/fake-gh-run-inprogress" <<'EOF'
#!/usr/bin/env bash
echo "in_progress null in_progress"
exit 0
EOF
  chmod +x "$T/fake-gh-run-inprogress"
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_GH="$T/fake-gh-run-inprogress" run_chain --sha "$FSHA" --branch feat --gated-run 11111 2>&1)" || RC=$?
  check_rc "gated-run-inprogress" "$RC" 0
  grep -q "LEG1 gate GREEN (resumed run 11111)" "$T/journal.log" && ok "journal-gated-run-inprogress" || bad "journal-gated-run-inprogress"

  # 7. journaling failure is LOUD and NEVER FATAL (2026-09-11, defect fix lane
  # 4b4463d5). A journal write that could never succeed (stamping a kind absent
  # from oc-ledger's enum -> permanent rc 2) was swallowed by `|| true`, making
  # it byte-identical to success: 216/216 real stamps died and no chain ever had
  # a ledger trail. Copy the tool beside a fake oc-ledger that rejects the kind
  # (exactly what the real one did) and assert the chain still completes AND
  # says so on stderr.
  # NOTE: OC_TOOLS_NOLOG must be forced OFF here — it routes journal() to stderr
  # and would bypass the ledger path under test. The battery exports it =1
  # globally, so neutralize it explicitly and redirect the tool log instead.
  mkdir -p "$T/bin"
  cp "$SELF" "$T/bin/oc-ship"
  mkdir -p "$T/bin/state"
  cat > "$T/bin/state/oc-ledger" <<'EOF'
#!/usr/bin/env bash
echo "oc-ledger: stamp: unknown kind 'shipchain' (v1.2 vocabulary — see header)" >&2
exit 2
EOF
  chmod +x "$T/bin/state/oc-ledger"
  run_chain_plain() { # as run_chain, but the LEDGER path (no OC_SHIPCHAIN_LEDGER)
    OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$T/tools.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
      bash "$T/bin/oc-ship" "$@"
  }
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(run_chain_plain --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "journal-fail-nonfatal" "$RC" 0
  case "$OUT" in *"WARNING — ledger journaling FAILED (rc=2)"*) ok "journal-fail-loud" ;; *) bad "journal-fail-loud: $OUT" ;; esac
  case "$OUT" in *"unknown kind 'shipchain'"*) ok "journal-fail-shows-stderr" ;; *) bad "journal-fail-shows-stderr" ;; esac
  case "$OUT" in *"journal line(s) lost"*) ok "journal-fail-summary" ;; *) bad "journal-fail-summary" ;; esac
  case "$OUT" in *SWAPPED*) ok "journal-fail-chain-completed" ;; *) bad "journal-fail-chain-completed" ;; esac

  # 8. a WORKING ledger path stays quiet — no false alarm, and the summary stays
  # silent (the counter only speaks when lines were actually lost).
  printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/state/oc-ledger"; chmod +x "$T/bin/state/oc-ledger"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(run_chain_plain --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "journal-ok-rc" "$RC" 0
  case "$OUT" in *"journaling FAILED"*) bad "journal-ok-no-false-alarm" ;; *) ok "journal-ok-no-false-alarm" ;; esac
  case "$OUT" in *"line(s) lost"*) bad "journal-ok-no-false-summary" ;; *) ok "journal-ok-no-false-summary" ;; esac

  # 8b. (#664) the remedy must name the cause it can ESTABLISH, and no other.
  # The #21 fix branched 143|137 correctly but left the KINDS hypothesis as the
  # catch-all, so rc=4 — with_lock's lock timeout, where the stamp was never
  # attempted — was answered with "oc-ledger must accept kind 'shipchain'", and a
  # lane following it edits KINDS for nothing while the contention stays. Two
  # lanes reported this against the same live rows (40427d4f, 462181e9).
  cat > "$T/bin/state/oc-ledger" <<'EOF'
#!/usr/bin/env bash
printf 'oc-ledger: lock timeout on workers-ledger.json.lock after 90s\n' >&2
exit 4
EOF
  chmod +x "$T/bin/state/oc-ledger"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(run_chain_plain --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "journal-rc4-nonfatal" "$RC" 0
  case "$OUT" in *"cause: rc=4"*) ok "journal-rc4-names-lock" ;;
    *) bad "journal-rc4-names-lock: $OUT" ;; esac
  case "$OUT" in *"stamp was never attempted"*) ok "journal-rc4-says-never-attempted" ;;
    *) bad "journal-rc4-says-never-attempted" ;; esac
  # the discriminating negative: rc 4 must NOT print the KINDS remedy
  case "$OUT" in *"must accept kind 'shipchain'"*) bad "journal-rc4-no-kinds-advice" ;;
    *) ok "journal-rc4-no-kinds-advice" ;; esac

  # 8c. rc 2 KEEPS the KINDS advice — the split must not throw away the case the
  # advice is right for (oc-ledger:858 dies 2 on an unknown kind).
  cat > "$T/bin/state/oc-ledger" <<'EOF'
#!/usr/bin/env bash
printf "oc-ledger: stamp: unknown kind 'shipchain' (v1.2 vocabulary — see header)\n" >&2
exit 2
EOF
  chmod +x "$T/bin/state/oc-ledger"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(run_chain_plain --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  case "$OUT" in *"must accept kind 'shipchain'"*) ok "journal-rc2-keeps-kinds-advice" ;;
    *) bad "journal-rc2-keeps-kinds-advice: $OUT" ;; esac
  case "$OUT" in *"cause: not established"*) bad "journal-rc2-not-neutral" ;;
    *) ok "journal-rc2-not-neutral" ;; esac

  # 8d. an UNEXPECTED rc gets no asserted cause at all.
  cat > "$T/bin/state/oc-ledger" <<'EOF'
#!/usr/bin/env bash
printf 'oc-ledger: something unrecognised\n' >&2
exit 9
EOF
  chmod +x "$T/bin/state/oc-ledger"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(run_chain_plain --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  case "$OUT" in *"cause: not established for rc=9"*) ok "journal-rc9-cause-neutral" ;;
    *) bad "journal-rc9-cause-neutral: $OUT" ;; esac
  case "$OUT" in *"must accept kind 'shipchain'"*) bad "journal-rc9-no-kinds-advice" ;;
    *) ok "journal-rc9-no-kinds-advice" ;; esac
  case "$OUT" in *"cause: rc=4"*) bad "journal-rc9-not-rc4" ;;
    *) ok "journal-rc9-not-rc4" ;; esac

  # 9-11. LEG1 gate rc 5 is NON-TERMINAL, never infra (defect fix 2026-09-11,
  # lane 4b4463d5). oc-gate rc 5 = "still in flight after --wait" with the
  # live run id on stdout; the old `*)` arm made it fatal, so a FRESH chain
  # killed itself while its own gate was still building — ledger n=2595 / n=2609
  # / n=2611: three chains, three identical rc-5 deaths, ZERO SWAPPED rows ever.
  # rc 5 must RESUME-POLL; only a genuinely exhausted budget may give up, and
  # that gives up as rc 7 (in flight), distinct from rc 6 (infra).
  cat > "$T/fake-prchecks-inflight" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "resume" ]; then
  case "${GATE_MODE:-green}" in
    green)  echo "VERDICT GREEN"; exit 0 ;;
    always) echo "IN-FLIGHT run=888 https://x/runs/888 (still in_progress)"; exit 5 ;;
  esac
fi
[ "${GATE_MODE:-green}" = "norunid" ] && { echo "IN-FLIGHT (still in_progress)"; exit 5; }
echo "IN-FLIGHT run=888 https://x/runs/888 (still in_progress)"; exit 5
EOF
  chmod +x "$T/fake-prchecks-inflight"
  run_chain_inflight() {
    OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks-inflight" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
      bash "$SELF" "$@"
  }

  # 9. rc 5 then a GREEN resume → the chain completes (the whole point of the fix)
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=green run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "gate-rc5-resumes-to-green" "$RC" 0
  case "$OUT" in *SWAPPED*) ok "gate-rc5-chain-completed" ;; *) bad "gate-rc5-chain-completed: $OUT" ;; esac
  grep -q "LEG1 gate in flight (run=888) — resume-poll 1/" "$T/journal.log" && ok "gate-rc5-journaled-resume" || bad "gate-rc5-journaled-resume"
  grep -q "LEG1 gate GREEN" "$T/journal.log" && ok "gate-rc5-journaled-green" || bad "gate-rc5-journaled-green"

  # 10. an ALWAYS-timing-out gate gives up as rc 7 (in flight), never rc 6 (infra)
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=always OC_SHIPCHAIN_GATE_RESUMES=2 run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "gate-rc5-exhausted-rc7" "$RC" 7
  case "$OUT" in *"still in flight (run=888)"*) ok "gate-rc5-exhausted-names-run" ;; *) bad "gate-rc5-exhausted-names-run: $OUT" ;; esac
  case "$OUT" in *"re-run with --gated-run 888"*) ok "gate-rc5-exhausted-resume-command" ;; *) bad "gate-rc5-exhausted-resume-command: $OUT" ;; esac
  case "$OUT" in *"resume-poll 2/2"*) ok "gate-rc5-exhausted-resume-count" ;; *) bad "gate-rc5-exhausted-resume-count" ;; esac
  grep -q "LEG1 gate STILL IN FLIGHT run=888" "$T/journal.log" && ok "gate-rc5-exhausted-journaled" || bad "gate-rc5-exhausted-journaled"

  # 11. rc 5 with NO run id cannot resume → rc 6 infra (the honest dead end)
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=norunid run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "gate-rc5-no-runid-rc6" "$RC" 6

  # 11c. A structured NON-ZERO exit wakes the arming lane (#662). The header
  # promises the daemon resumes on a structured exit, but that resume is a BOOT-
  # TIME in-flight classifier: a lane that armed a chain and settled is logged
  # completed_before_kill and never woken, so landed-but-unshipped work stalls
  # until a human re-reads the chain. Measured: 21 PRE-ANCESTRY MISS rows;
  # specimen 151d06227 / chain oc-ship-626-104449, unlanded 7h20m. The wake is on
  # the TOOL side, so it holds whatever the daemon's classifier does or does not
  # do. Stub binary records the call instead of notifying anything real.
  cat > "$T/bin/opencrabs" <<'EOF'
#!/usr/bin/env bash
echo "NOTIFY-CALLED: $*" >> "${WAKELOG:-/dev/null}"
exit 0
EOF
  chmod +x "$T/bin/opencrabs"
  rm -f "$T/journal.log" "$T/wake.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=always OC_SHIPCHAIN_GATE_RESUMES=2 \
    OPENCRABS_SESSION_ID="$LEG_UUID" \
    OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "wake-rc7-exit-code" "$RC" 7
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"EXITED rc=7"*) ok "wake-rc7-fires" ;;
    *) bad "wake-rc7-fires: [$(cat "$T/wake.log" 2>/dev/null)]" ;; esac
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"--sender oc-ship"*) ok "wake-rc7-sender" ;;
    *) bad "wake-rc7-sender" ;; esac
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"$LEG_UUID"*) ok "wake-rc7-targets-env-lane" ;;
    *) bad "wake-rc7-targets-env-lane" ;; esac

  # 11d. the opt-out suppresses, and the chain's own rc is UNCHANGED either way --
  # a wake is a notification, never a verdict, and rc is the audit surface.
  rm -f "$T/wake.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=always OC_SHIPCHAIN_GATE_RESUMES=2 OC_SHIPCHAIN_NO_WAKE=1 \
    OPENCRABS_SESSION_ID="$LEG_UUID" \
    OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "wake-nowake-exit-code-unchanged" "$RC" 7
  [ -s "$T/wake.log" ] && bad "wake-nowake-suppressed" || ok "wake-nowake-suppressed"

  # 11d1. #55: the wake must carry the chain's OWN die text, not the rc legend.
  # The legend is keyed on the CODE, and rc 5 covers EIGHT causes with opposite
  # remedies, so a legend can contradict the very run that armed it. Measured
  # 2026-10-25 (ledger n=15480): the wake said "rebase onto fork main and
  # re-gate" while the same run's journal said "Do NOT rebase" -- following the
  # wake would have rewritten a correctly-based gated tip and burned a ~26-min
  # gate. MUTANT KILLED: reverting _rem to chain_remedy-only turns the first
  # leg RED, because the legend has no die text to carry.
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-55" \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" CHAIN_INTENT=1 \
    CHAIN_DIE_MSG="LOCAL-MAIN-AHEAD (rc 5): sentinel-die-text" \
    _chain_wake_arming_lane 5 ) >/dev/null 2>&1 || true
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"sentinel-die-text"*) ok "wake-carries-the-die-text" ;;
    *) bad "wake-carries-the-die-text: [$(cat "$T/wake.log" 2>/dev/null)]" ;; esac
  # #55 MUTANT: make _rem fall back to chain_remedy unconditionally -> this leg
  # must go RED. It forbids the LEGEND's own marker ("EIGHT causes"), not the
  # pre-#55 wording "rebase onto fork main": that string no longer exists in the
  # legend at all, so forbidding it could never fail and the leg would have been
  # decoration (CODE.md item 3). Caught by running the mutant, not by reading.
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"EIGHT causes"*) bad "wake-must-not-carry-the-legend-when-a-die-text-exists" ;;
    *) ok "wake-prefers-die-text-over-legend" ;; esac
  # ...and with NO die text (a signal, or a wrapped tool's own rc) the legend is
  # still the fallback: the disclosure must not become a silence.
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-55b" \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" CHAIN_INTENT=1 \
    _chain_wake_arming_lane 5 ) >/dev/null 2>&1 || true
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"EIGHT causes"*) ok "wake-falls-back-to-legend-without-a-die-text" ;;
    *) bad "wake-falls-back-to-legend-without-a-die-text: [$(cat "$T/wake.log" 2>/dev/null)]" ;; esac

  # 11d2. #695 + #137/#138: the wake's STATE CLAIM must be READ, not asserted.
  # rc is not the swap verdict, and the deployed.sha MARKER is not this run's
  # receipt either -- it is a global host marker an EARLIER chain wrote. #137
  # measured 2026-11-22: a --dry-run against an already-deployed sha, dying at a
  # pre-flight guard with ZERO journal rows for that sha, woke claiming the ship
  # had LANDED and the failure was POST-SWAP. Four arms; the POSITIVE CONTROL is
  # what stops a "fix" that simply deletes the LANDED branch.
  mkdir -p "$T/state"
  printf '%s\n' "$FSHA" > "$T/state/deployed.sha"
  # (a) POSITIVE CONTROL: THIS chain's own LEG5 poll confirmed the swap and then
  # it died (the #695 shape: swap confirmed, rc 141 after). SWAPPED=1 is the
  # run-scoped receipt, so the LANDED claim is EARNED here.
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-695" SWAPPED=1 \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    CHAIN_INTENT=1 _chain_wake_arming_lane 141 ) >/dev/null 2>&1 || true
  _W_SWAPPED="$(cat "$T/wake.log" 2>/dev/null)"
  case "$_W_SWAPPED" in *"LANDED for this sha IN THIS CHAIN"*) ok "wake-swapped-in-chain-claims-landed" ;;
    *) bad "wake-swapped-in-chain-claims-landed: [$_W_SWAPPED]" ;; esac
  case "$_W_SWAPPED" in *"UNSHIPPED"*) bad "wake-swapped-in-chain-claims-unshipped" ;;
    *) ok "wake-swapped-in-chain-claims-unshipped" ;; esac
  # (b) #137 NEGATIVE: the same marker, but THIS chain recorded no swap. The
  # pre-fix code asserted LANDED/POST-SWAP here. BOTH strings must be absent --
  # forbidding the pair is what catches a fix that renames the state but keeps
  # the claim.
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-137" \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    CHAIN_INTENT=1 _chain_wake_arming_lane 141 ) >/dev/null 2>&1 || true
  _W_PREEXIST="$(cat "$T/wake.log" 2>/dev/null)"
  case "$_W_PREEXIST" in *"POST-SWAP"*) bad "wake-preexisting-marker-must-not-claim-post-swap" ;;
    *) ok "wake-preexisting-marker-must-not-claim-post-swap" ;; esac
  case "$_W_PREEXIST" in *"ALREADY swapped"*) bad "wake-preexisting-marker-must-not-claim-already-swapped" ;;
    *) ok "wake-preexisting-marker-must-not-claim-already-swapped" ;; esac
  case "$_W_PREEXIST" in *"THIS chain recorded NO swap"*) ok "wake-preexisting-marker-names-the-real-state" ;;
    *) bad "wake-preexisting-marker-names-the-real-state: [$_W_PREEXIST]" ;; esac
  # (c) #138: rc 3 is PRE-FLIGHT (the legend's own class), so the message must
  # carry the "nothing was dispatched" half AND must not be the post-swap text.
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-138" \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    CHAIN_INTENT=1 _chain_wake_arming_lane 3 ) >/dev/null 2>&1 || true
  _W_PREFLIGHT="$(cat "$T/wake.log" 2>/dev/null)"
  case "$_W_PREFLIGHT" in *"PRE-FLIGHT refused"*"nothing was dispatched"*) ok "wake-preflight-rc3-says-nothing-dispatched" ;;
    *) bad "wake-preflight-rc3-says-nothing-dispatched: [$_W_PREFLIGHT]" ;; esac
  case "$_W_PREFLIGHT" in *"POST-SWAP"*) bad "wake-preflight-rc3-must-not-claim-post-swap" ;;
    *) ok "wake-preflight-rc3-must-not-claim-post-swap" ;; esac
  # (d) SWAPPED=1 is a receipt about the sha THIS chain swapped, so it cannot
  # license a LANDED claim when the marker carries a DIFFERENT sha. Without this
  # arm the predicate could be `SWAPPED=1` alone and every arm above would pass.
  printf '%s\n' "1111111111111111111111111111111111111111" > "$T/state/deployed.sha"
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-137c" SWAPPED=1 \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    CHAIN_INTENT=1 _chain_wake_arming_lane 141 ) >/dev/null 2>&1 || true
  _W_OTHERSHA="$(cat "$T/wake.log" 2>/dev/null)"
  case "$_W_OTHERSHA" in *"LANDED for this sha"*) bad "wake-swapped-other-sha-must-not-claim-landed" ;;
    *) ok "wake-swapped-other-sha-must-not-claim-landed" ;; esac
  case "$_W_OTHERSHA" in *"UNSHIPPED"*) ok "wake-swapped-other-sha-reads-the-marker" ;;
    *) bad "wake-swapped-other-sha-reads-the-marker: [$_W_OTHERSHA]" ;; esac
  printf '%s\n' "$FSHA" > "$T/state/deployed.sha"
  rm -f "$T/state/deployed.sha" "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-695" \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    CHAIN_INTENT=1 _chain_wake_arming_lane 141 ) >/dev/null 2>&1 || true
  case "$(cat "$T/wake.log" 2>/dev/null)" in *"deployed.sha is ABSENT"*) ok "wake-reads-marker-no-swap" ;;
    *) bad "wake-reads-marker-no-swap: [$(cat "$T/wake.log" 2>/dev/null)]" ;; esac

  # 11d3. #48 defect 1: the wake's REMEDY is derived from rc, not hardcoded.
  # Both real stops of one chain falsified the old single sentence: rc=3 was a
  # checkout precondition no gate name can satisfy, rc=6 a dead user bus on a
  # chain ALREADY armed with --gated-run. Three codes whose remedies must
  # DIFFER, each asserting the blanket line's ABSENCE -- a table that repeated
  # it everywhere would otherwise pass a "names the cause" leg on rc 7 alone.
  for _rc in 3 6 7; do
    rm -f "$T/wake.log"
    ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-48" \
      OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
      OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      CHAIN_INTENT=1 _chain_wake_arming_lane "$_rc" ) >/dev/null 2>&1 || true
    case "$_rc" in
      3) _WAKE_3="$(cat "$T/wake.log" 2>/dev/null)" ;;
      6) _WAKE_6="$(cat "$T/wake.log" 2>/dev/null)" ;;
      7) _WAKE_7="$(cat "$T/wake.log" 2>/dev/null)" ;;
    esac
  done
  case "$_WAKE_3" in *"PRECONDITION refused"*) ok "wake-remedy-rc3-is-precondition" ;;
    *) bad "wake-remedy-rc3-is-precondition: [$_WAKE_3]" ;; esac
  case "$_WAKE_6" in *"INFRASTRUCTURE, not a gate"*) ok "wake-remedy-rc6-is-infra" ;;
    *) bad "wake-remedy-rc6-is-infra: [$_WAKE_6]" ;; esac
  case "$_WAKE_7" in *"--gated-run <id>"*) ok "wake-remedy-rc7-names-gated-run" ;;
    *) bad "wake-remedy-rc7-names-gated-run: [$_WAKE_7]" ;; esac
  case "$_WAKE_3$_WAKE_6" in *"often needs only --gated-run"*) bad "wake-remedy-drops-the-blanket-line" ;;
    *) ok "wake-remedy-drops-the-blanket-line" ;; esac
  case "$_WAKE_6" in *"--gated-run"*) bad "wake-remedy-rc6-does-not-name-a-gate" ;;
    *) ok "wake-remedy-rc6-does-not-name-a-gate" ;; esac
  case "$_WAKE_3" in *"--gated-run: there is no gate"*) ok "wake-remedy-rc3-warns-against-the-gate" ;;
    *) bad "wake-remedy-rc3-warns-against-the-gate: [$_WAKE_3]" ;; esac

  # 11d4. #48 defect 2: the checkout precondition is read BEFORE the gate. The
  # cost being fixed is TIME-TO-VERDICT, so "rc 3" alone is not the assertion --
  # the prchecks stub logs every call, and an EMPTY log is the receipt that the
  # expensive leg never ran. A mutant that only moved the check after LEG1 would
  # still exit 3 and be caught here.
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" checkout -q -b feat-precondition
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  check_rc "preflight-checkout-rc3" "$RC" 3
  case "$OUT" in *"not main"*) ok "preflight-checkout-names-condition" ;;
    *) bad "preflight-checkout-names-condition: $OUT" ;; esac
  [ -s "$T/prchecks.log" ] && bad "preflight-checkout-gate-not-dispatched: [$(cat "$T/prchecks.log")]" \
    || ok "preflight-checkout-gate-not-dispatched"
  git -C "$T/clone" checkout -q main

  # 11d4-bis. #137: the run-scoped swap receipt must be DECLARED, not merely
  # absent. The arm above is the #137 shape end-to-end -- a REAL chain that dies
  # rc 3 at a precondition having dispatched nothing -- and by the point it dies
  # STATE_DIR is set (:1218) while deployed.sha carries $FSHA (an earlier chain
  # deployed it), so the LANDED branch is REACHABLE. That reachability is what
  # makes this leg non-vacuous; the freeze arm cannot serve here because it dies
  # at :1017, BEFORE STATE_DIR exists, so `_dep` is empty and LANDED is
  # unreachable however the wake is written.
  # Inherit SWAPPED=1 from the environment. The declaration must overwrite it,
  # or a chain that swapped nothing claims the ship LANDED on an inherited
  # variable -- the same defect class as reading the global marker as a receipt.
  printf '%s\n' "$FSHA" > "$T/state/deployed.sha"
  git -C "$T/clone" checkout -q -b feat-envswapped
  rm -f "$T/wake.log"
  RC=0; OUT="$(SWAPPED=1 \
      OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      OC_DEPLOY_STATE_DIR="$T/state" OC_SWAP_TARGET="$T/fake-swapped" \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 \
      OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
      OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "preflight-env-swapped-rc3" "$RC" 3
  _W_ENVSW="$(cat "$T/wake.log" 2>/dev/null)"
  # POSITIVE CONTROL: the wake must have FIRED. Without this, a chain that never
  # reached the wake would satisfy the refusal assertion below for the wrong
  # reason -- the exact vacuity this leg exists to avoid.
  [ -s "$T/wake.log" ] && ok "wake-env-swapped-fired" || bad "wake-env-swapped-fired: no wake log"
  case "$_W_ENVSW" in *"LANDED for this sha"*) bad "wake-env-inherited-swapped-must-not-claim-landed: [$_W_ENVSW]" ;;
    *) ok "wake-env-inherited-swapped-must-not-claim-landed" ;; esac
  git -C "$T/clone" checkout -q main
  rm -f "$T/state/deployed.sha"

  # 11e. SWAPPED (rc 0) must NOT wake -- the lane already sees the verdict, and a
  # wake on every success would be the noise this tool's own fan-out was filed for.
  rm -f "$T/wake.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=green \
    OPENCRABS_SESSION_ID="$LEG_UUID" \
    OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "wake-green-rc0" "$RC" 0
  [ -s "$T/wake.log" ] && bad "wake-green-no-wake" || ok "wake-green-no-wake"

  # 11f. HERMETICITY, and it is DISCRIMINATING: a selftest that forgets the
  # allow-flag must fire NOTHING. Were the guard absent, this leg would reach the
  # real /usr/local/bin/opencrabs and notify this lane for real -- which is why
  # the assertion is on the flag and not on a stub's absence.
  rm -f "$T/wake.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(GATE_MODE=always OC_SHIPCHAIN_GATE_RESUMES=2 \
    OPENCRABS_SESSION_ID="$LEG_UUID" \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    run_chain_inflight --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "wake-hermetic-exit-code" "$RC" 7
  [ -s "$T/wake.log" ] && bad "wake-hermetic-no-allow-flag" || ok "wake-hermetic-no-allow-flag"

  # 14. #14: a NON-chain invocation must never wake the arming lane. Measured
  #     2026-10-05: `oc-ship --help` piped into a short reader raised
  #     SIGPIPE (awk, rc 141) which, under set -e, aborted BEFORE `exit 0` and
  #     fired the EXIT-trap wake with SHA and STATE_DIR BOTH unset -- so
  #     "${STATE_DIR:-}/deployed.sha" resolved to the ROOT path, was absent, and
  #     the delivered message read "deployed.sha is ABSENT" with the sha rendered
  #     "?". Five occurrences, four lanes, 2026-09-30..10-05. `--eval-docs-skip`
  #     (exit 1/3) is the same class AND is a MANDATED lane invocation
  #     (editor.md:691), so the routine query path woke the querying lane too.
  #     The discriminator is CHAIN_INTENT (set only after the --sha/--branch
  #     checks). These legs are the NEGATIVE half; the wake-rc7-fires and
  #     wake-reads-marker-* legs above are the positive control (they set
  #     CHAIN_INTENT=1).
  # 14a. the pipe itself: rc 0, not 141 (usage() tolerates EPIPE).
  RC=0; ( set -o pipefail; OC_SHIPCHAIN_IMPL=0 bash "$SELF" --help 2>/dev/null | head -2 >/dev/null ) || RC=$?
  check_rc "help-short-pipe-rc0" "$RC" 0
  # 14b. --help does not wake even with the stub armed.
  rm -f "$T/wake.log"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    bash "$SELF" --help 2>&1)" || RC=$?
  check_rc "help-no-wake-rc0" "$RC" 0
  [ -s "$T/wake.log" ] && bad "help-no-wake" || ok "help-no-wake"
  # 14c. THE DISCRIMINATING LEG: rc 1 -- non-zero, so the pre-#14 predicate WOULD
  #      wake -- yet no chain was attempted. Fixture feat.txt is code, so
  #      --eval-docs-skip answers GATE-REQUIRED rc 1.
  rm -f "$T/wake.log"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" OC_FORK_REPO="$T/clone" \
    bash "$SELF" --eval-docs-skip "$FSHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-rc1" "$RC" 1
  [ -s "$T/wake.log" ] && bad "eval-docs-skip-no-wake" || ok "eval-docs-skip-no-wake"
  # 14d. the predicate directly, intent unset -> suppressed. Positive twin is the
  #      wake-reads-marker-* pair above (same call with CHAIN_INTENT=1).
  rm -f "$T/wake.log"
  ( SHA="$FSHA" STATE_DIR="$T/state" CHAIN="c-14" \
    OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
    _chain_wake_arming_lane 141 ) >/dev/null 2>&1 || true
  [ -s "$T/wake.log" ] && bad "wake-no-intent-suppressed" || ok "wake-no-intent-suppressed"


  # 11. FREEZE GUARD (contract fix 2026-09-11, owner word via HQ): a REAL chain
  #     is blocked rc 3 while the freeze file is present, and the sanctioned
  #     override lifts it. OC_SHIPCHAIN_FREEZE_FILE makes this hermetic — the
  #     case never depends on the live .fork-freeze existing.
  printf 'freeze\n' > "$T/freeze"
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_FILE="$T/freeze" \
      bash "$SELF" --sha "$FSHA" --branch feat 2>&1)" || RC=$?
  check_rc "freeze-blocks-real-chain-rc3" "$RC" 3
  case "$OUT" in *FREEZE*) ok "freeze-message" ;; *) bad "freeze-message: $OUT" ;; esac

  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_FILE="$T/freeze" \
      OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "freeze-override-lifts-block" "$RC" 0

  # Remote-branch pre-flight + the rc-2 precondition split (defect fix
  # 2026-09-11, lane facd50af report). An unpushed branch used to clear
  # pre-flight, burn a gate dispatch and come back "sha not found", which the
  # gate arm then classified INFRA rc=6 — a phantom infra hunt for a missing
  # precondition. The fixture carries a deliberately unpushed branch
  # (`unpushed-fixture`) so both halves are testable.
  rm -f "$T/journal.log"
  git -C "$T/clone" checkout -q main
  RC=0; OUT="$(run_chain --sha "$USHA" --branch unpushed-fixture --dry-run 2>&1)" || RC=$?
  check_rc "branch-preflight-unpushed-rc3" "$RC" 3
  case "$OUT" in
    *unpushed-fixture*) ok "branch-preflight-names-branch" ;;
    *) bad "branch-preflight-names-branch: $OUT" ;;
  esac
  # The pre-flight must fire BEFORE the DRY-RUN success line. Pre-fix this
  # emitted "pre-flight ok ... branch=unpushed-fixture" and exited 0, so
  # asserting the absence of that line is what makes this non-vacuous: the rc
  # assertion alone would pass on any unrelated rc-3 death.
  case "$OUT" in
    *"pre-flight ok"*) bad "branch-preflight-blocks-dispatch: emitted pre-flight ok" ;;
    *) ok "branch-preflight-blocks-dispatch" ;;
  esac
  # The pushed branch must still pass — the pre-flight is not a blanket block.
  RC=0; OUT="$(run_chain --sha "$FSHA" --branch feat --dry-run 2>&1)" || RC=$?
  check_rc "branch-preflight-pushed-passes" "$RC" 0
  # oc-gate rc 2 is its documented USAGE/PRECONDITION class ("usage /
  # sha-shape / unknown ref / repo-path-no-origin"), never infra — the rc-6
  # contract lists only prchecks 4/7/8 as infra. It must not be funnelled into
  # "gate infra" rc 6 (the reporter's second finding).
  cat > "$T/fake-prchecks-rc2" <<'EOF2'
#!/usr/bin/env bash
echo "oc-gate: sha deadbeef not found on leshchenko1979/opencrabs" >&2
exit 2
EOF2
  chmod +x "$T/fake-prchecks-rc2"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks-rc2" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "gate-precondition-rc2-not-infra" "$RC" 3
  case "$OUT" in
    *"NOT an infrastructure fault"*) ok "gate-precondition-message" ;;
    *) bad "gate-precondition-message: $OUT" ;;
  esac
  case "$OUT" in
    *"gate infra"*) bad "gate-precondition-not-labelled-infra" ;;
    *) ok "gate-precondition-not-labelled-infra" ;;
  esac

  # #495 (lane 2fbfb2f8 report): an ABBREVIATED --sha must converge. Pre-fix the
  # abbreviation reached oc-gate, which refused it as "short sha refused
  # (carrier inputs are FULL-sha-bound; got N chars)" — correctly — and the
  # chain then died rc 2 telling the lane to "push it and re-run" with the SAME
  # abbreviation. The branch and sha were on the remote and matched exactly, so
  # the message sent the lane to inspect state that was already correct, and the
  # printed command could not succeed for ANY input.
  #
  # The stub below is a faithful model of that refusal: it fails rc 2 on a
  # non-40-char hex argument, exactly as tools/harvest/oc-gate:811 does. So this
  # leg asserts the NORMALISATION (the chain must hand it 40 chars), not merely
  # that some chain ran.
  # MUTATION KILL: delete the entry normalisation block and this leg reddens —
  # the chain passes $SHORT_SHA through, the stub refuses, and the rc-2 arm
  # reports the abbreviation. Conversely the MESSAGE split is proven separately
  # below, since with normalisation in place the rc-2 arm is unreachable by this
  # route.
  cat > "$T/fake-prchecks-sha-bound" <<'EOF2'
#!/usr/bin/env bash
# Model oc-gate's OWN refusal (tools/harvest/oc-gate:811): carrier inputs are
# FULL-sha-bound. ONLY the first positional argument is the ref — the invocation
# is `<bin> <ref> [--repo R] --wait N [--fast]`, and a blanket "every all-hex
# argument" test misfires on a wait value like 2700;  `--wait` numbers and the
# branch name are not refs.
a="${1:-}"
case "$a" in
  *[!0-9a-f]*|'') exit 0 ;;          # not hex (or empty) -> not a ref
esac
if [ "${#a}" -ne 40 ]; then
  echo "oc-gate: short sha refused (carrier inputs are FULL-sha-bound; got ${#a} chars)" >&2
  exit 2
fi
echo "$*" >> "${FAKE_PRCHECKS_LOG:-/dev/null}"
exit 0
EOF2
  chmod +x "$T/fake-prchecks-sha-bound"
  SHORT_SHA="$(printf '%s' "$FSHA" | cut -c1-9)"
  [ "${#SHORT_SHA}" -eq 9 ] || bad "short-sha-fixture: abbreviation is ${#SHORT_SHA} chars, want 9"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks-sha-bound" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_DEPLOY_STATE_DIR="$T/state" \
      bash "$SELF" --sha "$SHORT_SHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "short-sha-resolved-to-full: the chain converges" "$RC" 0
  case "$OUT" in
    *"is a 9-char abbreviation; resolved to the full 40-char $FSHA"*) ok "short-sha-resolution-announced" ;;
    *) bad "short-sha-resolution-announced: $OUT" ;;
  esac
  case "$OUT" in
    *"short sha refused"*) bad "short-sha-never-reaches-prchecks" ;;
    *) ok "short-sha-never-reaches-prchecks" ;;
  esac
  # ...and the normalised sha is what the DOWNSTREAM legs saw too, not just the
  # gate: the final line names the full sha, so the whole chain works from ONE
  # canonical value (a partially-normalised chain would journal both).
  case "$OUT" in
    *"SWAPPED sha=$FSHA"*) ok "short-sha-every-leg-uses-the-full-sha" ;;
    *) bad "short-sha-every-leg-uses-the-full-sha: $OUT" ;;
  esac
  # The rc-2 MESSAGE split (#495 defect 1). Normalisation makes this arm
  # unreachable by the --sha route, so drive it directly: a stub that refuses rc
  # 2 while the chain still holds a NON-40 sha. OC_SHIPCHAIN_SHA_AS_IS=1 is the
  # documented bypass that models "the abbreviation survived" — without it the
  # assertion would be about a state the fix removed, which is not a control.
  cat > "$T/fake-prchecks-short-refuse" <<'EOF2'
#!/usr/bin/env bash
echo "oc-gate: short sha refused (carrier inputs are FULL-sha-bound; got 9 chars)" >&2
exit 2
EOF2
  chmod +x "$T/fake-prchecks-short-refuse"
  RC=0; OUT="$(OC_SHIPCHAIN_SHA_AS_IS=1 OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks-short-refuse" \
      OC_DEPLOY_BIN="$T/fake-deploy" OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
      OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_DEPLOY_STATE_DIR="$T/state" \
      bash "$SELF" --sha "$SHORT_SHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "short-sha-rc2-arm-still-rc3" "$RC" 3
  # THE DEFECT: the old text blamed the remote and told the lane to push.
  case "$OUT" in
    *"push it and re-run"*) bad "short-sha-message-does-not-blame-the-remote" ;;
    *) ok "short-sha-message-does-not-blame-the-remote" ;;
  esac
  case "$OUT" in
    *"ABBREVIATION"*"FULL-sha-bound"*) ok "short-sha-message-names-the-real-cause" ;;
    *) bad "short-sha-message-names-the-real-cause: $OUT" ;;
  esac
  # ...and the remediation CONVERGES: it prints the full sha, not the
  # abbreviation it was handed.
  case "$OUT" in
    *"oc-ship --sha $FSHA --branch feat"*) ok "short-sha-remediation-converges" ;;
    *) bad "short-sha-remediation-converges (want --sha $FSHA): $OUT" ;;
  esac
  # Control: the NON-short rc-2 shape keeps the push instruction, so the split
  # is discriminating rather than a blanket rewrite.
  case "$OUT" in
    *"NOT an infrastructure fault"*) ok "short-sha-keeps-the-not-infra-clause" ;;
    *) bad "short-sha-keeps-the-not-infra-clause: $OUT" ;;
  esac

  # Ship Lock contention selftest:
  # Hold lock in background -> chain wait -> release lock -> chain completes
  #
  # The holder releases on the chain's OWN "contended" row instead of a fixed
  # `sleep 1`. That fixed window was load-sensitive and flaked: `acquire_ship_lock`
  # is called at :1505, i.e. AFTER preflight, sha resolution and the issue probe,
  # so on a loaded box (measured 2026-11-18: load avg 19.4 with five peer chains
  # running) the chain reached the lock more than a second after launch, found it
  # already free, journalled "acquired immediately" and failed THIS arm for a
  # reason that has nothing to do with contention -- while `...-resolved` and
  # `...-released` still passed, which is the signature of a timing flake rather
  # than a lock defect.
  #
  # Waiting for the contention row does not weaken what the arm asserts (the
  # chain must still WAIT for the lock); it makes the observation deterministic.
  # The 600-iteration bound (30s) keeps a chain that dies before reaching the
  # lock from hanging the battery.
  mkdir -p "$T/state"
  # (#78) A BACKGROUNDED `flock ... sleep N` IS NOT RELEASED BY KILLING ITS
  # WRAPPER. `flock file cmd` forks, so $SUBPID is the flock and the `sleep N`
  # child INHERITS the lock fd: `kill $SUBPID` leaves the lock HELD until the
  # sleep expires. Measured 2026-11-15 — the 12s holder in the re-arm budget
  # arm was still holding two arms later, where `rearm-heals-then-ships` wants
  # rc 0 and got rc 9 (SHIP-LOCK-TIMEOUT). It passed in one run and failed in
  # the next with no code change between them, which is the definition of a
  # flaky arm. Kill the CHILD first (that closes the fd), then the wrapper,
  # then verify the lock is genuinely acquirable before the next arm starts.
  #
  # AND ONE LEVEL OF "CHILD" IS NOT ENOUGH (measured 2026-11-18, the #78 arms):
  # the marker-held holder is bash(script) -> flock -> bash -c, so the lock fd
  # lives in the GRANDCHILD. Killing the flock + the script left `bash -c`
  # running with the fd, the lock stayed held for the holder's full 300s bound,
  # and EVERY later arm contended — `rearm-heals-then-ships` read rc 9 after two
  # re-arms, which looks exactly like a supervisor defect and is not one. So the
  # whole descendant tree is killed, deepest first, and a lock that outlives the
  # drop is a RED: it makes the FOLLOWING arm contend, and a leak that reads as
  # a subject failure is worse than no fixture at all.
  _drop_ship_lock() {
    local _i=0 _pids _p
    _drop_tree() {
      local _c
      for _c in $(pgrep -P "$1" 2>/dev/null); do _drop_tree "$_c"; done
      printf '%s\n' "$1"
    }
    _pids="$(_drop_tree "$SUBPID" 2>/dev/null || true)"
    for _p in $_pids; do kill -TERM "$_p" 2>/dev/null || true; done
    kill "$SUBPID" 2>/dev/null || true
    wait "$SUBPID" 2>/dev/null || true
    while [ "$_i" -lt 200 ]; do
      flock -n "$T/state/ship.lock" true 2>/dev/null && return 0
      _i=$((_i+1)); sleep 0.05
    done
    bad "fixture-lock-not-dropped (the holder outlived _drop_ship_lock, so every later arm contends — this is a FIXTURE leak, not a chain defect)"
    return 0
  }
  cat > "$T/hold-lock.sh" <<'HOLD'
#!/usr/bin/env bash
# $1 = fixture root (state/ lives under it), $2 = chain journal,
# $3 = the journal row that RELEASES the lock (default: the contention row).
# A marker, never a stopwatch. A blind `sleep N` races the chain's startup and
# the race has two failure shapes, both measured 2026-11-15: holder too SHORT
# and attempt 1 never sees contention, so an arm asserting a re-arm gets rc 0
# with NO `RE-ARM` row (`rearm-healed-attempt-journalled` read an empty journal);
# holder too LONG and the RE-ARMED attempt times out too, so the arm that wants
# rc 0 gets rc 9 instead (`rearm-heals-then-ships`, the pre-#78 flake).
T="$1"; J="$2"; M="${3:-SHIP-LOCK contended}"
flock -x "$T/state/ship.lock" bash -c '
  # (#78) 6000 iterations x 0.05s = 300s. The bound exists only so a holder that
  # is never dropped cannot hang the battery; it must OUTLAST a full chain run,
  # because the arms that hold "for the whole run" release on no marker at all
  # and are stopped by _drop_ship_lock.
  i=0
  while [ "$i" -lt 6000 ]; do
    grep -qF "$1" "$0" 2>/dev/null && exit 0
    i=$((i+1)); sleep 0.05
  done
  exit 0
' "$J" "$M"
HOLD
  chmod +x "$T/hold-lock.sh"
  # (#78) HOLD THE LOCK ON A MARKER, NEVER ON A STOPWATCH. A fixed `sleep N`
  # cannot express "held for the whole run": the chain's startup varies with
  # fixture state, and once the holder expires the chain reaches a FREE lock,
  # acquires it and SHIPS. Measured 2026-11-18 on the #78 arms: under 12s
  # holds, `rearm-max1-exits-9` and two of the three opt-out forms shipped
  # (rc 0, no RE-ARM row) while the FIRST opt-out form passed on the very same
  # hold -- the arms were asserting the clock, not the supervisor, and the
  # failure looked like a code defect in the thing being tested.
  # The marker below never appears in the journal, so only `_drop_ship_lock`
  # releases it; and the lock is VERIFIED held before the chain starts, because
  # an arm whose fixture never armed is indistinguishable from one whose
  # subject misbehaved -- both read as a legitimate red.
  _hold_lock_until_dropped() {
    bash "$T/hold-lock.sh" "$T" "$T/journal.log" "__never_released__" &
    SUBPID=$!
    local _i=0
    while [ "$_i" -lt 200 ]; do
      flock -n "$T/state/ship.lock" true 2>/dev/null || return 0
      _i=$((_i+1)); sleep 0.05
    done
    bad "fixture-lock-never-armed (the holder did not take the lock, so this arm asserts nothing)"
    return 1
  }
  # The journal is cleared BEFORE the holder starts: it polls that file for the
  # contention row, so a leftover row from an earlier arm would release the lock
  # before this chain ever ran -- the same flake wearing a different hat.
  rm -f "$T/journal.log"
  bash "$T/hold-lock.sh" "$T" "$T/journal.log" &
  SUBPID=$!
  sleep 0.1
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  wait $SUBPID 2>/dev/null || true
  check_rc "ship-lock-contention-resolved" "$RC" 0
  grep -q "SHIP-LOCK acquired after" "$T/journal.log" && ok "journal-ship-lock-waited" || bad "journal-ship-lock-waited"
  # The contended row is the OTHER half of the same event: without it the chain
  # took the lock first-try and "acquired after" would be a lie about a queue
  # that never existed. Asserted separately so a broken contended-row is a red,
  # not a slow pass.
  grep -q "SHIP-LOCK contended" "$T/journal.log" && ok "journal-ship-lock-contended" || bad "journal-ship-lock-contended"
  grep -q "SHIP-LOCK released" "$T/journal.log" && ok "journal-ship-lock-released" || bad "journal-ship-lock-released"

  # Ship Lock TIMEOUT is rc 9, NOT rc 6 (defect fix 2026-09-19, fork #391;
  # reported independently by lanes 61161247 and c78e78e0). The old timeout died
  # rc 6 — the INFRA branch — so a lane reading the exit table went hunting a
  # broken component and re-dispatched the gate, burning a full gate cycle for a
  # queue condition. Contention is NOT infra: the same reasoning that split rc 7
  # (gate in flight) and rc 8 (ship wait) out of rc 6.
  rm -f "$T/journal.log"
  _hold_lock_until_dropped || true
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      SHIP_LOCK_TIMEOUT=1 OC_SHIPCHAIN_NO_REARM=1 \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  _drop_ship_lock
  # (#78) NO_REARM is LOAD-BEARING here, not tidiness. This arm asserts the
  # exit CONTRACT (a timeout is rc 9 and is labelled non-infra), and it holds
  # the lock for 5s against a 1s budget. Once #78 taught the chain to re-arm
  # rc 9, a re-armed attempt reaching the lock AFTER the holder released
  # legitimately ACQUIRED it and shipped -- rc 0, measured. So the arm was
  # racing the holder rather than testing the verdict, and it HUNG the suite:
  # the re-armed child carried the identical argv and ran the full chain
  # inside a fixture built only for the timeout path. The supervisor has its
  # own arms (1c/1c1/1c2); this one pins the contract with it out of the way.
  check_rc "ship-lock-timeout-is-rc9-not-infra" "$RC" 9
  case "$OUT" in
    *"SHIP-LOCK-TIMEOUT"*) ok "ship-lock-timeout-names-itself" ;;
    *) bad "ship-lock-timeout-names-itself" ;;
  esac
  case "$OUT" in
    *"gate infra"*|*"ship infra"*) bad "ship-lock-timeout-not-labelled-infra" ;;
    *) ok "ship-lock-timeout-not-labelled-infra" ;;
  esac
  grep -q "SHIP-LOCK timeout" "$T/journal.log" && ok "journal-ship-lock-timeout" || bad "journal-ship-lock-timeout"

  # The queue budget must OUTLAST the hold it serializes (LEG4's WAIT). The old
  # literal 600 was structurally shorter than the ~3300s hold, so every chain
  # that queued behind a real ship expired by construction. Assert the DERIVED
  # relation rather than a pinned number, so a future edit to WAIT carries the
  # budget with it instead of silently re-introducing the shortfall.
  _lwait="$( ( unset OC_SHIPCHAIN_SHIP_WAIT; eval "$(grep -m1 '^WAIT=' "$SELF")"; printf '%s' "$WAIT" ) 2>/dev/null)"
  _lbudg="$( ( unset OC_SHIPCHAIN_LOCK_WAIT; eval "$(grep -m1 '^WAIT=' "$SELF")"; eval "$(grep -m1 '^SHIP_LOCK_WAIT=' "$SELF")"; printf '%s' "$SHIP_LOCK_WAIT" ) 2>/dev/null)"
  if [ "${_lbudg:-0}" -ge "$(( ${_lwait:-0} + 600 ))" ]; then
    ok "ship-lock-budget-outlasts-leg4-hold"
  else
    bad "ship-lock-budget-outlasts-leg4-hold (WAIT=${_lwait:-?} budget=${_lbudg:-?})"
  fi

  # 1c. #78 RE-ARM SUPERVISOR — Class A. rc 9 (lock timeout) is the only class
  # that provably touched nothing outside this process: no gate run was
  # dispatched, no swap started, so a restart costs one queue wait and nothing
  # else. Measured over 213 real re-arms: 70 were this shape (lock timeout, plus
  # pre-dispatch gate rc 4/7/8), i.e. a human was woken to be told a queue
  # condition had already cleared itself.
  #
  # The DEFAULT budget is asserted here rather than pinned as a constant: this
  # arm runs with no OC_SHIPCHAIN_REARM_MAX in the environment, so "exactly two
  # RE-ARM rows" IS the default. An edit that raises the ceiling silently turns
  # this red, which is the point — a bound nobody can see is not a bound.
  #
  # The wake count is the arm that matters most. The supervisor `exec`s BEFORE
  # _chain_wake_arming_lane runs, so attempts 1 and 2 are suppressed by
  # construction and only the exhausted attempt notifies. A regression that
  # woke per attempt would send a lane three notifies for one chain — the exact
  # storm the pre-#78 wake was already famous for.
  cat > "$T/bin/opencrabs" <<'EOF'
#!/usr/bin/env bash
echo "NOTIFY-CALLED: $*" >> "${WAKELOG:-/dev/null}"
exit 0
EOF
  chmod +x "$T/bin/opencrabs"
  rm -f "$T/journal.log" "$T/wake.log"
  _hold_lock_until_dropped || true
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      SHIP_LOCK_TIMEOUT=1 OPENCRABS_SESSION_ID="$LEG_UUID" \
      OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
      OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "rearm-exhausted-budget-still-exits-9" "$RC" 9
  grep -q "RE-ARM attempt 1/2 after rc=9" "$T/journal.log" \
    && ok "rearm-first-attempt-journalled" \
    || bad "rearm-first-attempt-journalled: [$(grep 'RE-ARM' "$T/journal.log" 2>/dev/null | tr '\n' ' ')]"
  grep -q "RE-ARM attempt 2/2 after rc=9" "$T/journal.log" \
    && ok "rearm-second-attempt-journalled" || bad "rearm-second-attempt-journalled"
  _rn="$(grep -c 'RE-ARM attempt' "$T/journal.log" 2>/dev/null || true)"
  [ "${_rn:-0}" = 2 ] && ok "rearm-default-budget-is-two" || bad "rearm-default-budget-is-two (got ${_rn:-0})"
  _wn="$(grep -c 'NOTIFY-CALLED' "$T/wake.log" 2>/dev/null || true)"
  [ "${_wn:-0}" = 1 ] && ok "rearm-wakes-once-not-per-attempt" || bad "rearm-wakes-once-not-per-attempt (got ${_wn:-0})"
  case "$(cat "$T/wake.log" 2>/dev/null)" in
    *"rc=9"*) ok "rearm-exhausted-wake-carries-rc" ;;
    *) bad "rearm-exhausted-wake-carries-rc: [$(cat "$T/wake.log" 2>/dev/null)]" ;;
  esac
  # 1c3. #78 BUDGET CARRIED ACROSS *TWO* EXECS, asserted where it is OBSERVABLE.
  # An arm that stops at "attempt 2/2" CANNOT prove carry: a reset-to-1 mutant
  # writes 1 at the end of attempt 1 and the correct code writes 1 too, so
  # attempt 2 reads 2/2 either way. Measured 2026-11-18 -- the mutant left
  # `rearm-second-attempt-journalled` GREEN while the chain re-armed 155 times.
  # Attempt 3 is the first step where the two diverge: correct code reads 3/3
  # and then exhausts, a reset mutant re-reads 2/3 forever and never exhausts.
  # `timeout` bounds that mutant case (it would otherwise run to the fixture
  # holder's own bound); the correct case finishes in seconds.
  # The lock is re-armed for THIS arm rather than inherited from the block
  # above: under a reset mutant that block loops until the fixture holder's own
  # bound expires, so an inherited lock reads FREE here and the arm ships rc 0
  # with no RE-ARM rows -- measured 2026-11-18 (`got 0` where the honest
  # mutant answer is a non-zero count of repeated 2/3). A red for the wrong
  # reason is not a test.
  _drop_ship_lock
  _hold_lock_until_dropped || true
  rm -f "$T/journal.log" "$T/wake.log"
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      SHIP_LOCK_TIMEOUT=1 OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_REARM_MAX=3 \
      OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
      OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      timeout 150 bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "rearm-budget3-still-exits-9" "$RC" 9
  grep -q "RE-ARM attempt 3/3 after rc=9" "$T/journal.log" \
    && ok "rearm-third-attempt-proves-carry" \
    || bad "rearm-third-attempt-proves-carry: [$(grep -o 'RE-ARM attempt [0-9]*/[0-9]*' "$T/journal.log" 2>/dev/null | tr '\n' ' ')]"
  _rn3="$(grep -c 'RE-ARM attempt' "$T/journal.log" 2>/dev/null || true)"
  [ "${_rn3:-0}" = 3 ] && ok "rearm-budget3-arms-exactly-three" || bad "rearm-budget3-arms-exactly-three (got ${_rn3:-0})"
  _drop_ship_lock

  # 1d. #78 A RE-ARM THAT HEALS MUST NOT WAKE THE LANE -- and the control comes
  # FIRST, because "wake.log is empty" is the single most vacuous assertion this
  # suite could carry: it passes on a fixture that could never wake at all, on a
  # uuid-less env, on a stub binary that was never invoked. So the same fixture
  # is run twice, changing exactly ONE thing (the supervisor):
  #   control : --no-rearm  -> rc 9 and EXACTLY ONE wake (the path is live)
  #   subject : re-arm ON   -> rc 0 and ZERO wakes (the path was suppressed)
  # The holder releases on the chain's OWN `SHIP-LOCK timeout` journal row, not
  # on a stopwatch: attempt 1 must time out against the 2s budget, and only then
  # does the re-armed attempt reach a free lock and ship.
  #
  # BOTH ARMS OPT IN TO RE-ARMING, so the pair differs in EXACTLY ONE variable
  # (the opt-out) and the comparison attributes something. Until 2026-11-18 the
  # control alone carried NO_REARM while the subject alone carried
  # REARM_ALLOW_SELFTEST: two variables moved, so a control that passed proved
  # nothing about the opt-out -- it was passing because hermeticity had already
  # blocked the restart. A control that differs from its subject in two places
  # is not a control. That is the owner-order
  # shape: a queue condition that cleared itself, healed in-tool, with the lane
  # left asleep. Release-on-timeout is what makes the arm deterministic -- a
  # fixed hold made attempt 1's failure depend on how long the chain took to
  # reach the lock, which is exactly what flaked.
  rm -f "$T/wake.log"
  # Journal cleared BEFORE the holder starts: the holder polls that file for the
  # timeout row, so a leftover row from an earlier arm would release the lock
  # before this chain ever ran.
  rm -f "$T/journal.log"
  bash "$T/hold-lock.sh" "$T" "$T/journal.log" "SHIP-LOCK timeout" &
  SUBPID=$!
  sleep 0.1
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 \
      SHIP_LOCK_TIMEOUT=2 OC_SHIPCHAIN_NO_REARM=1 OPENCRABS_SESSION_ID="$LEG_UUID" \
      OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
      OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  _drop_ship_lock
  check_rc "rearm-control-without-supervisor-is-rc9" "$RC" 9
  _wn="$(grep -c 'NOTIFY-CALLED' "$T/wake.log" 2>/dev/null || true)"
  [ "${_wn:-0}" = 1 ] && ok "rearm-control-wake-path-is-live" \
    || bad "rearm-control-wake-path-is-live (got ${_wn:-0}): the suppression arm below would be vacuous"

  rm -f "$T/wake.log"
  # Journal cleared BEFORE the holder starts: the holder polls that file for the
  # timeout row, so a leftover row from an earlier arm would release the lock
  # before this chain ever ran.
  rm -f "$T/journal.log"
  bash "$T/hold-lock.sh" "$T" "$T/journal.log" "SHIP-LOCK timeout" &
  SUBPID=$!
  sleep 0.1
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 \
      SHIP_LOCK_TIMEOUT=2 OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 OPENCRABS_SESSION_ID="$LEG_UUID" \
      OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  _drop_ship_lock
  check_rc "rearm-heals-then-ships" "$RC" 0
  grep -q "RE-ARM attempt 1/" "$T/journal.log" \
    && ok "rearm-healed-attempt-journalled" \
    || bad "rearm-healed-attempt-journalled: [$(grep 'RE-ARM' "$T/journal.log" 2>/dev/null | tr '\n' ' ')]"
  _wn="$(grep -c 'NOTIFY-CALLED' "$T/wake.log" 2>/dev/null || true)"
  [ "${_wn:-0}" = 0 ] && ok "rearm-healed-does-not-wake" \
    || bad "rearm-healed-does-not-wake (got ${_wn:-0}): [$(cat "$T/wake.log" 2>/dev/null | head -2 | tr '\n' ' ')]"

  # 1e. #78 THE EXHAUSTED WAKE MUST NAME THE ATTEMPT COUNT. A wake that reads
  # identically to a first-try failure withholds the one fact the lane needs:
  # every in-tool restart was already spent, so the cause is not transient and
  # re-running by hand will not clear it. Budget 1 is asserted here so the count
  # is unambiguous (1/1), and the wake text must carry it.
  rm -f "$T/wake.log"
  rm -f "$T/journal.log"
  _hold_lock_until_dropped || true
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
      OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
      OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
      OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_SHIPCHAIN_NO_ISSUE_PROBE=1 \
      SHIP_LOCK_TIMEOUT=1 OC_SHIPCHAIN_REARM_MAX=1 OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
      OPENCRABS_SESSION_ID="$LEG_UUID" \
      OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
      bash "$SELF" --sha "$FSHA" --branch feat --issue 42 --wait 5 2>&1)" || RC=$?
  _drop_ship_lock
  check_rc "rearm-max1-exits-9" "$RC" 9
  grep -q "RE-ARM attempt 1/1" "$T/journal.log" \
    && ok "rearm-max1-journals-1-of-1" || bad "rearm-max1-journals-1-of-1"
  grep -q "RE-ARM attempt 2/" "$T/journal.log" \
    && bad "rearm-max1-budget-is-honoured (a 2nd attempt ran under a 1 budget)" \
    || ok "rearm-max1-budget-is-honoured"
  _wn="$(grep -c 'NOTIFY-CALLED' "$T/wake.log" 2>/dev/null || true)"
  [ "${_wn:-0}" = 1 ] && ok "rearm-max1-wakes-exactly-once" || bad "rearm-max1-wakes-exactly-once (got ${_wn:-0})"
  case "$(cat "$T/wake.log" 2>/dev/null)" in
    *"already RE-ARMED 1 time(s) in-tool (budget 1)"*) ok "rearm-max1-wake-names-attempt-count" ;;
    *) bad "rearm-max1-wake-names-attempt-count: [$(cat "$T/wake.log" 2>/dev/null | head -2 | tr '\n' ' ')]" ;;
  esac

  # 1c1. THE OPT-OUTS, both forms, on one lock hold. An opt-out must suppress
  # the RESTART without also suppressing the NOTIFY: turning a self-healing
  # chain into a silent stall is a strictly worse failure than the wake it
  # replaces, and the rc must be identical either way (a wake is never a
  # verdict). ONE hold across all three forms, released only by
  # _drop_ship_lock after the loop: the hold must outlast all three runs, which
  # is exactly what a fixed sleep cannot promise (see _hold_lock_until_dropped).
  #
  # THE FLAG AND ENV LEGS MUST OPT IN TO RE-ARMING (OC_SHIPCHAIN_REARM_ALLOW_SELFTEST),
  # and that is not tidiness. Without it the HERMETICITY guard blocks the restart
  # before the opt-out is ever consulted, so both legs pass on a build with no
  # opt-out code at all -- measured 2026-11-18: a mutant with the
  # `[ -z "$NO_REARM" ] || return 1` line deleted still scored 347 passed /
  # 0 failed, i.e. the two arms were decoration. With the opt-in the ONLY thing
  # suppressing the restart is the opt-out, and the same mutant reddens both.
  # The `selftest` leg deliberately does NOT opt in: it asserts hermeticity on
  # its own, which is the other guard and must stay separately proven.
  rm -f "$T/journal.log"
  _hold_lock_until_dropped || true
  for _opt in flag env selftest; do
    rm -f "$T/journal.log" "$T/wake.log"
    RC=0
    if [ "$_opt" = "flag" ]; then
      OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
        OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
        OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
        SHIP_LOCK_TIMEOUT=1 OPENCRABS_SESSION_ID="$LEG_UUID" \
        OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
        OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
        bash "$SELF" --sha "$FSHA" --branch feat --wait 5 --no-rearm 2>&1)" || RC=$?
    elif [ "$_opt" = "env" ]; then
      OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
        OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
        OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
        SHIP_LOCK_TIMEOUT=1 OPENCRABS_SESSION_ID="$LEG_UUID" OC_SHIPCHAIN_NO_REARM=1 \
        OC_SHIPCHAIN_REARM_ALLOW_SELFTEST=1 \
        OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
        bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
    else
      # 1c1-selftest. NEITHER opt-out is set, so the restart must be suppressed
      # by the HERMETICITY guard alone (OC_SHIPCHAIN_SELFTEST is inherited from
      # the suite and this leg does not pass the re-arm opt-in). Without this
      # leg the guard is only tested by the suite not hanging, and a hang is a
      # worthless detector: it reports nothing and costs a full re-run.
      OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
        OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
        OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
        SHIP_LOCK_TIMEOUT=1 OPENCRABS_SESSION_ID="$LEG_UUID" \
        OC_SHIPCHAIN_WAKE_ALLOW_SELFTEST=1 OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" \
        bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
    fi
    check_rc "no-rearm-$_opt-exit-code-unchanged" "$RC" 9
    grep -q 'RE-ARM attempt' "$T/journal.log" \
      && bad "no-rearm-$_opt-suppresses-restart" || ok "no-rearm-$_opt-suppresses-restart"
    _wn="$(grep -c 'NOTIFY-CALLED' "$T/wake.log" 2>/dev/null || true)"
    [ "${_wn:-0}" = 1 ] && ok "no-rearm-$_opt-still-wakes" || bad "no-rearm-$_opt-still-wakes (got ${_wn:-0})"
  done
  _drop_ship_lock

  # 1c2. The env twin is validated AT THE ARG BOUNDARY, so a typo is a usage
  # error and never a silently-inert knob. #63 class: an accepted-but-ignored
  # setting is indistinguishable from an honoured one, and this one guards a
  # restart loop — the failure mode is a chain that either storms or never
  # heals, with no evidence either way in the log.
  # HERMETICITY (#78): OC_SHIPCHAIN_IMPL=0 is MANDATORY on this call, for the
  # same reason the --eval-docs-skip legs state it: the suite runs INSIDE
  # `selftest_impl`, so a child that inherits OC_SHIPCHAIN_IMPL=1 takes the
  # SELFTEST_MODE=2 branch (:587) and re-enters the WHOLE suite at :692.
  # Measured 2026-11-15: without it this arm recursed instead of dying rc 2,
  # one nested suite per level at ~8 min each, and the outer run never
  # returned — 242 ok printed, then a hang with no summary line. `timeout`
  # alone would have masked that: the arm would go red without ever naming
  # the cause, and a hang is a worthless detector (it reports nothing and
  # costs a full re-run). The bound is kept as a second line of defence.
  RC=0; OUT="$(OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IMPL=0 \
    OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" OC_TOOLS_NOLOG=1 \
    OC_SHIPCHAIN_LEDGER="$T/journal.log" OC_SHIPCHAIN_FREEZE_OVERRIDE=1 \
    OC_SHIPCHAIN_NO_REARM=abc timeout 120 \
    bash "$SELF" --sha "$FSHA" --branch feat --wait 5 2>&1)" || RC=$?
  check_rc "no-rearm-env-typo-is-rc2" "$RC" 2
  case "$OUT" in
    *"OC_SHIPCHAIN_NO_REARM needs 0 or 1"*) ok "no-rearm-env-typo-names-itself" ;;
    *) bad "no-rearm-env-typo-names-itself: [$OUT]" ;;
  esac

  # 12. ACTOR DEFAULTING (v0.4.152 §Attribution & Goal Hygiene A1; defect fix
  # 2026-09-12, toolsmith). A tool that ALREADY KNOWS the owning session MUST
  # default the actor to it — an `(unattributed — pass --by or export OC_ACTOR)`
  # row is a TOOL defect, not lane sloppiness. The chain is handed the commit it
  # ships (--sha) and every editor commit carries a `Session-Id: <uuid>`
  # trailer, so the owning session is ON DISK inside a sha the chain already
  # holds. 34 unattributed rows landed in the 2026-09-12 night shift (n=3515
  # class) with that trailer sitting in the very commit shipped.
  # The probe reads ${OC_ACTOR} out of the CHILD's environment (the fake deploy
  # runs as a child of the chain), so it proves what the chain actually
  # EXPORTED — not what a later log line merely claims.
  cat > "$T/fake-deploy-actor" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  ship) printf '%s\n' "${OC_ACTOR:-<unset>}" > "${FAKE_ACTOR_FILE:-/dev/null}"
        s=""; shift; while [ $# -gt 0 ]; do case "$1" in --sha) s="$2"; shift 2 ;; *) shift ;; esac; done
        d="${OC_DEPLOY_STATE_DIR:-/tmp}"; mkdir -p "$d" 2>/dev/null || true
        printf '%s\n' "$s" > "$d/pending.sha" 2>/dev/null || true
        rm -f "$d/deployed.sha" "$d/polls" 2>/dev/null || true
        echo "carrier run GREEN (fake)"; exit 0 ;;
  poll) # no completion token — the MARKER is the completion signal
        d="${OC_DEPLOY_STATE_DIR:-/tmp}"; mkdir -p "$d" 2>/dev/null || true
        [ -f "$d/pending.sha" ] && cp "$d/pending.sha" "$d/deployed.sha" 2>/dev/null || true
        echo "HANDOFF: Phase B transient unit owns the swap (fake) — poll exits pre-bounce by design"
        exit 0 ;;
  status) d="${OC_DEPLOY_STATE_DIR:-/tmp}"
        printf '{\n  "deployed": {\n    "sha": "%s"\n  }\n}\n' "$(cat "$d/deployed.sha" 2>/dev/null)" ;;
esac
exit 9
EOF
  chmod +x "$T/fake-deploy-actor"
  actor_probe() { # $1 = file the child writes its OC_ACTOR into; rest = chain args
    OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy-actor" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    FAKE_ACTOR_FILE="$1" \
      bash "$SELF" "${@:2}"
  }
  rm -f "$T/journal.log" "$T/actor.seen"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  # (a) OC_ACTOR unset in the caller's env -> the --sha trailer supplies it
  RC=0; OUT="$( unset OC_ACTOR; actor_probe "$T/actor.seen" --sha "$FSHA" --branch feat --wait 5 2>&1 )" || RC=$?
  check_rc "actor-default-rc" "$RC" 0
  SEEN="$(cat "$T/actor.seen" 2>/dev/null || true)"
  [ "$SEEN" = "$FIXTURE_SESSION" ] && ok "actor-default-from-sha-trailer" \
    || bad "actor-default-from-sha-trailer (want $FIXTURE_SESSION got '$SEEN')"
  grep -q "actor defaulted to $FIXTURE_SESSION" "$T/journal.log" \
    && ok "actor-default-journaled" || bad "actor-default-journaled"
  # (b) an explicit OC_ACTOR WINS over the trailer (the caller knows better)
  rm -f "$T/journal.log" "$T/actor.seen"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$( export OC_ACTOR="11111111-2222-3333-4444-555555555555"; actor_probe "$T/actor.seen" --sha "$FSHA" --branch feat --wait 5 2>&1 )" || RC=$?
  check_rc "actor-env-wins-rc" "$RC" 0
  SEEN="$(cat "$T/actor.seen" 2>/dev/null || true)"
  [ "$SEEN" = "11111111-2222-3333-4444-555555555555" ] && ok "actor-env-wins-over-trailer" \
    || bad "actor-env-wins-over-trailer (got '$SEEN')"
  grep -q "actor defaulted" "$T/journal.log" && bad "actor-env-no-default-row" || ok "actor-env-no-default-row"
  # (c) NO trailer on the sha and no env -> NOTHING INVENTED. The old loud
  # unattributed path must survive: a fabricated actor is worse than none.
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  echo notrailer > "$T/clone/nt.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm notrailer
  NTSHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" branch -f feat HEAD
  git -C "$T/clone" push -q -f origin feat
  git -C "$T/clone" reset -q --hard origin/main
  rm -f "$T/journal.log" "$T/actor.seen"
  RC=0; OUT="$( unset OC_ACTOR; actor_probe "$T/actor.seen" --sha "$NTSHA" --branch feat --wait 5 2>&1 )" || RC=$?
  # (c) #755 re-aim: an untrailered tip is now refused by the LEG3 SIGNATURE
  # pre-check (rc 3) BEFORE the merge, so the deploy leg never runs. The
  # 'never invent an actor' invariant still holds, asserted two ways: the fake
  # deploy wrote no actor, and the chain journaled no 'actor defaulted' row.
  # (Before #755 the chain proceeded with the actor unset — same invariant,
  # reached one leg later; gate 4 refused the tip at LEG4 and stranded main.)
  check_rc "actor-no-trailer-rc" "$RC" 3
  SEEN="$(cat "$T/actor.seen" 2>/dev/null || true)"
  [ -z "$SEEN" ] && ok "actor-never-invented" \
    || bad "actor-never-invented (want '' got '$SEEN')"
  grep -q "actor defaulted" "$T/journal.log" && bad "actor-no-trailer-no-fabrication" \
    || ok "actor-no-trailer-no-fabrication"

  # 20. DOCS-ONLY GATE SKIP (owner ruling 2026-09-12 11:04Z). A commit whose
  #     every changed path is markdown NOT compiled into the binary must skip
  #     LEG1 — journaled + visible, never a silent absence of a gate.
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  # Built here, from the CURRENT origin/main (see the note in the fixture block
  # above). docs-fixture touches only ONTOLOGY.md, which nothing compiles;
  # compiled-md-fixture touches README.md, which src/lib.rs include_str!'s.
  git -C "$T/clone" checkout -qB docs-fixture main
  printf '# ontology\n' > "$T/clone/ONTOLOGY.md"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "docs only" --trailer "Session-Id: $FIXTURE_SESSION"
  DOCS_SHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" push -q -f origin docs-fixture
  git -C "$T/clone" checkout -qB compiled-md-fixture main
  printf '# readme v2\n' > "$T/clone/README.md"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "readme bump" --trailer "Session-Id: $FIXTURE_SESSION"
  CMDSHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" push -q -f origin compiled-md-fixture
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$DOCS_SHA" --branch docs-fixture --wait 5 2>&1)" || RC=$?
  check_rc "docs-only-chain-green" "$RC" 0
  grep -q "GATE-SKIPPED-DOCS sha=$DOCS_SHA" "$T/journal.log" && ok "docs-only-skip-journaled" || bad "docs-only-skip-journaled"
  grep -q "reason=" "$T/journal.log" && ok "docs-only-skip-names-reason" || bad "docs-only-skip-names-reason"
  grep -q "ONTOLOGY.md" "$T/journal.log" && ok "docs-only-skip-names-paths" || bad "docs-only-skip-names-paths"
  [ -s "$T/prchecks.log" ] && bad "docs-only-dispatched-no-gate" || ok "docs-only-dispatched-no-gate"
  grep -q "LEG1 gate start" "$T/journal.log" && bad "docs-only-no-gate-start" || ok "docs-only-no-gate-start"
  case "$OUT" in *SWAPPED*) ok "docs-only-chain-completed" ;; *) bad "docs-only-chain-completed: $OUT" ;; esac
  case "$OUT" in *"GATE SKIPPED"*) ok "docs-only-skip-visible-on-stderr" ;; *) bad "docs-only-skip-visible-on-stderr" ;; esac

  # 20b. NEGATIVE CASE: README.md IS include_str!'d from src/lib.rs, so a commit
  #      touching it changes compiled output and MUST still gate. If this ever
  #      skips, the skip predicate has become an extension check.
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$CMDSHA" --branch compiled-md-fixture --wait 5 2>&1)" || RC=$?
  check_rc "compiled-md-chain-green" "$RC" 0
  grep -q "GATE-SKIPPED-DOCS" "$T/journal.log" && bad "compiled-md-not-skipped" || ok "compiled-md-not-skipped"
  grep -q "$CMDSHA" "$T/prchecks.log" && ok "compiled-md-gate-dispatched" || bad "compiled-md-gate-dispatched"

  # 20c. the escape hatch: OC_SHIPCHAIN_NO_DOCS_SKIP=1 forces the gate even for a
  #      docs-only sha (a gate that can vanish needs a way to summon it back).
  rm -f "$T/journal.log" "$T/prchecks.log"
  git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_NO_DOCS_SKIP=1 FAKE_PRCHECKS_LOG="$T/prchecks.log" run_chain --sha "$DOCS_SHA" --branch docs-fixture --wait 5 2>&1)" || RC=$?
  check_rc "docs-skip-override-chain-green" "$RC" 0
  grep -q "GATE-SKIPPED-DOCS" "$T/journal.log" && bad "docs-skip-override-disables" || ok "docs-skip-override-disables"
  grep -q "$DOCS_SHA" "$T/prchecks.log" && ok "docs-skip-override-gates" || bad "docs-skip-override-gates"

  # 20d. --eval-docs-skip standalone inspection verb (Defect #20 / Reviewer J-7).
  #      rc 0 = docs-only (prints paths); rc 1 = gate-required; rc 2 = missing sha;
  #      rc 3 = bad ref or git error.
  # Note: OC_SHIPCHAIN_IMPL=0 is mandatory when calling $SELF as a standalone command
  # from inside selftest_impl to prevent inheriting SELFTEST_MODE=2 (re-entering selftest).
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip 2>&1)" || RC=$?
  check_rc "eval-docs-skip-no-sha-rc2" "$RC" 2
  case "$OUT" in *"--sha or commit argument required"*) ok "eval-docs-skip-no-sha-msg" ;; *) bad "eval-docs-skip-no-sha-msg: $OUT" ;; esac

  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip deadbeef1234 2>&1)" || RC=$?
  check_rc "eval-docs-skip-bad-sha-rc3" "$RC" 3
  case "$OUT" in *"bad commit or unknown ref"*) ok "eval-docs-skip-bad-sha-msg" ;; *) bad "eval-docs-skip-bad-sha-msg: $OUT" ;; esac

  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip "$DOCS_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-docs-rc0" "$RC" 0
  case "$OUT" in *"ONTOLOGY.md"*) ok "eval-docs-skip-docs-paths" ;; *) bad "eval-docs-skip-docs-paths: $OUT" ;; esac
  case "$OUT" in *"DOCS-ONLY gate skip permitted"*) ok "eval-docs-skip-docs-msg" ;; *) bad "eval-docs-skip-docs-msg: $OUT" ;; esac

  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip --sha "$DOCS_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-flag-docs-rc0" "$RC" 0

  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip "$CMDSHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-compiled-rc1" "$RC" 1
  case "$OUT" in *"GATE-REQUIRED"*) ok "eval-docs-skip-compiled-msg" ;; *) bad "eval-docs-skip-compiled-msg: $OUT" ;; esac

  # 20d-ter (#69). "Is this a git checkout?" must be answered by GIT's predicate,
  # not by a proxy. A LINKED WORKTREE has a `.git` FILE (a gitdir pointer), so the
  # old `[ -d "$FORK_REPO/.git" ]` pre-flight refused a valid checkout as "not
  # found" and never dispatched a gate — measured live on
  # /root/opencrabs-wt/1930-compaction-budget, 62-byte ASCII `.git`.
  # The worktree is a FIXTURE created here: a live path would make the arm pass or
  # fail with the box, and the predicate is what is under test.
  # `--detach` on purpose: a branch already checked out in $T/clone cannot be
  # added again, and a fixture that silently fails to materialise would leave the
  # arm asserting nothing.
  git -C "$T/clone" worktree add -q --detach "$T/wt-linked" main 2>/dev/null || true
  [ -f "$T/wt-linked/.git" ] && ok "wt69-fixture-is-a-gitdir-file" \
    || bad "wt69-fixture-is-a-gitdir-file (fixture did not materialise as a linked worktree — the arms below would be vacuous)"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/wt-linked" bash "$SELF" --eval-docs-skip "$DOCS_SHA" 2>&1)" || RC=$?
  case "$OUT" in
    *"fork checkout not found"*) bad "eval-docs-skip-linked-worktree-accepted: refused a valid worktree: $OUT" ;;
    *) ok "eval-docs-skip-linked-worktree-accepted" ;;
  esac
  check_rc "eval-docs-skip-linked-worktree-rc0" "$RC" 0

  # Positive control for the refusal direction: a directory that EXISTS but is not
  # a checkout must still refuse rc 3. Without this, a predicate that accepts
  # everything (e.g. `true`) would pass the worktree arm above.
  mkdir -p "$T/not-a-checkout"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/not-a-checkout" bash "$SELF" --eval-docs-skip "$DOCS_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-not-a-checkout-rc3" "$RC" 3
  case "$OUT" in *"path exists but is not a git checkout"*) ok "eval-docs-skip-not-a-checkout-msg" ;; *) bad "eval-docs-skip-not-a-checkout-msg: $OUT" ;; esac

  # An ABSENT path gets a distinct message. One message for two causes is half of
  # what #69 reports: "not found" sent the lane looking at paths when the path was
  # fine and the TEST was wrong.
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/absent-path-xyz" bash "$SELF" --eval-docs-skip "$DOCS_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-absent-path-rc3" "$RC" 3
  case "$OUT" in *"path does not exist"*) ok "eval-docs-skip-absent-path-msg" ;; *) bad "eval-docs-skip-absent-path-msg: $OUT" ;; esac

  # And the ordinary shape still passes: a plain clone. This one stayed green
  # while the worktree died, so it cannot stand in for the worktree arm — but it
  # must not go red either, or the fix would have broken the normal case.
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip "$DOCS_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-plain-clone-rc0" "$RC" 0

  # SINGLE SOURCE (#69). The comment above require_fork_checkout claims "both call
  # sites share this one implementation so they cannot drift back apart" — and a
  # claim in a comment is not a check. The original defect was the SAME wrong test
  # duplicated at two sites, and only ONE of them is reachable from the arms above
  # (the other needs a full --sha/--branch chain). So assert the shape directly:
  # exactly one definition, and no surviving `-d .../.git` proxy anywhere.
  # This arm is what makes the "cannot drift" sentence true rather than hopeful.
  [ "$(grep -c '^require_fork_checkout()' "$SELF")" = "1" ] \
    && ok "wt69-single-source-definition" \
    || bad "wt69-single-source-definition: require_fork_checkout is defined $(grep -c '^require_fork_checkout()' "$SELF") times — the two call sites can drift apart again"
  # The scanner reads PRODUCTION CODE, never prose and never the selftest body:
  # this file's own comment block quotes the old test to explain the defect, and
  # the fixture below must contain the shape to prove the scanner fires. A scanner
  # that reads all three reddens on the explanation and on its own test data.
  # Same law as #47's negative control, which went inert by asserting a POSITION
  # in a sorted list: an instrument must be shown able to fire on its target.
  _wt69_scan() { # $1 = file, $2 = last production line; prints offending lines
    sed -n "1,${2}p" "$1" | grep -vE '^[[:space:]]*#' \
      | grep -E '\[[[:space:]]+-d[[:space:]]+"?\$[A-Za-z_]*FORK[A-Za-z_]*/\.git' || true
  }
  _wt69_prod_end="$(grep -c '' "$SELF")"   # body now lives in tests/ship-selftest.sh, so $SELF is ALL production code
  if [ -n "$(_wt69_scan "$SELF" "$_wt69_prod_end")" ]; then
    bad "wt69-no-gitdir-proxy: a \`-d .../.git\` test survives in the CODE — it refuses every linked worktree: $(_wt69_scan "$SELF" "$_wt69_prod_end" | head -1)"
  else
    ok "wt69-no-gitdir-proxy"
  fi
  # NEGATIVE CONTROL: the same scanner must FLAG the shape when it is real code.
  printf '%s\n' 'x=1' '[ -d "$FORK_REPO/.git" ] || die nope 3' > "$T/wt69-proxy-fixture.sh"
  [ -n "$(_wt69_scan "$T/wt69-proxy-fixture.sh" 99)" ] \
    && ok "wt69-no-gitdir-proxy NEGATIVE CONTROL: the scanner flags the shape (the leg can fail)" \
    || bad "wt69-no-gitdir-proxy NEGATIVE CONTROL: scanner missed the injected proxy — the coverage leg is inert"

  # 20d-bis (#537). The compiled-md set is derived by cd'ing into the fork repo
  # and grepping src/ for include_str!/include_bytes! of markdown. Its failure
  # path used to print NOTHING, which is indistinguishable from a legitimate
  # "this repo compiles in no markdown" — so a failed derivation made every
  # markdown path look non-compiled and the gate was SKIPPED. The sentinel makes
  # the two cases separable, and shipchain_docs_only fails CLOSED on it.
  # The function must be EXTRACTED, not called in place: this selftest body is
  # eval'd at line 229, before the script reaches the definition, so no function
  # defined later in the file exists here.
  sed -n '/^shipchain_compiled_md_set()/,/^}$/p' "$SELF" > "$T/set_fn.sh"
  if [ -s "$T/set_fn.sh" ]; then
    _sent="$(FORK_REPO="$T/oc-537-does-not-exist" bash -c '. '"$T"'/set_fn.sh; shipchain_compiled_md_set' 2>/dev/null)"
    case "$_sent" in
      *__OC_DERIVE_FAILED__*) ok "compiled-md-set: unenterable repo -> sentinel (fail-closed signal)" ;;
      *) bad "compiled-md-set: unenterable repo gave '$_sent' (empty reads as no-compiled-md)" ;;
    esac
    mkdir -p "$T/oc-537-emptysrc/src"
    _sent2="$(FORK_REPO="$T/oc-537-emptysrc" bash -c '. '"$T"'/set_fn.sh; shipchain_compiled_md_set' 2>/dev/null)"
    case "$_sent2" in
      *__OC_DERIVE_FAILED__*) bad "compiled-md-set: sentinel on a LEGITIMATELY empty set" ;;
      *) ok "compiled-md-set: enterable repo with no compiled md -> empty, no sentinel" ;;
    esac
  else
    bad "compiled-md-set: extraction from \$SELF produced nothing (leg cannot run)"
  fi

  # 20e. RANGE vs TIP (defect #322, editor lane #286 report). The skip must
  #      judge the WHOLE range the chain fast-forwards into main, not the tip
  #      commit. Every #20 fixture above is a SINGLE commit, where tip and range
  #      are the same diff by construction — which is exactly why the tip-based
  #      predicate looked correct and the defect survived the battery. The
  #      negative fixture below is the shape that broke it: a code commit UNDER
  #      a docs-only tip. The positive control (both commits markdown) proves
  #      the range judgement still skips a genuinely docs-only branch, so the
  #      new assertion cannot be satisfied by simply gating everything.
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qB range-code-fixture main
  printf 'pub fn f() {}\n' > "$T/clone/src/code_322.rs"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "code under a docs tip" --trailer "Session-Id: $FIXTURE_SESSION"
  printf '# notes\n' > "$T/clone/NOTES_322.md"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "docs tip" --trailer "Session-Id: $FIXTURE_SESSION"
  RANGE_CODE_SHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -qB range-docs-fixture main
  printf '# one\n' > "$T/clone/ONE_322.md"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "docs one" --trailer "Session-Id: $FIXTURE_SESSION"
  printf '# two\n' > "$T/clone/TWO_322.md"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm "docs two" --trailer "Session-Id: $FIXTURE_SESSION"
  RANGE_DOCS_SHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main

  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip "$RANGE_CODE_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-range-code-rc1" "$RC" 1
  case "$OUT" in *"GATE-REQUIRED"*) ok "eval-docs-skip-range-code-msg" ;; *) bad "eval-docs-skip-range-code-msg: $OUT" ;; esac

  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_FORK_REPO="$T/clone" bash "$SELF" --eval-docs-skip "$RANGE_DOCS_SHA" 2>&1)" || RC=$?
  check_rc "eval-docs-skip-range-docs-rc0" "$RC" 0
  case "$OUT" in *"DOCS-ONLY gate skip permitted"*) ok "eval-docs-skip-range-docs-msg" ;; *) bad "eval-docs-skip-range-docs-msg: $OUT" ;; esac

  # 21. CGROUP DETACH (LAW 17, defect #21). A chain launched from a session is
  #     a child of the daemon and sits INSIDE the unit cgroup a swap's
  #     `systemctl --user restart` tears down, so it is SIGTERM'd mid-leg and
  #     simply stops. The fix re-execs outside that cgroup before the ship lock
  #     is taken. A fixture cannot build cgroups, so the proxy is a NEW SESSION
  #     (`setsid`): exactly what `systemd-run --scope` hands the payload — a
  #     process group the unit's teardown cannot reach. The assertions below
  #     therefore test the property that matters (the payload is unreachable
  #     from the launcher's group), not the systemd call itself.
  cat > "$T/fake-detach" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "${FAKE_DETACH_LOG:-/dev/null}"
# stdio-binding probe: this runs AS the child of the redirected re-exec, so the
# marker reaches a file only if the redirect exists.
echo "FAKE-DETACH-STDIO-BOUND" >&2
exec setsid -w "$@"
EOF
  chmod +x "$T/fake-detach"
  # fresh branch cut at the point of use (earlier tests move origin/main)
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  git -C "$T/clone" checkout -qb detach-fixture
  echo d > "$T/clone/d.txt"
  git -C "$T/clone" add -A && git -C "$T/clone" commit -qm detach --trailer "Session-Id: $FIXTURE_SESSION"
  DSHA="$(git -C "$T/clone" rev-parse HEAD)"
  git -C "$T/clone" push -q -f origin detach-fixture
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main

  # 21a. INSIDE the cgroup -> the detach MUST fire, and the re-exec'd chain
  #      must still carry the SAME argv (a drained "$@" would die rc 2 with
  #      "--sha required" — the failure mode ORIG_ARGS exists to prevent).
  rm -f "$T/journal.log" "$T/detach-a.log" "$T/detach-stdio.log"
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=1 OC_SHIPCHAIN_DETACH_CMD="$T/fake-detach" \
    OC_SHIPCHAIN_LOG="$T/detach-stdio.log" \
    FAKE_DETACH_LOG="$T/detach-a.log" FAKE_PRCHECKS_LOG="$T/prchecks.log" \
      bash "$SELF" --sha "$DSHA" --branch detach-fixture --wait 5 2>&1)" || RC=$?
  check_rc "detach-inside-cgroup-rc" "$RC" 0
  [ -s "$T/detach-a.log" ] && ok "detach-fired" || bad "detach-fired"
  grep -q -- "--sha $DSHA" "$T/detach-a.log" && ok "detach-preserves-argv" || bad "detach-preserves-argv"
  # LAW 17 residual: the re-exec must bind stdio to a FILE. The marker is
  # written by the fixture's own stderr, which is inherited from the redirected
  # re-exec — so it can reach a file only when the redirect exists. Without
  # this, the scope survives the cgroup teardown and then dies EPIPE on its
  # first stderr write, silently (field case: 26 minutes in, 0-byte log).
  grep -q "FAKE-DETACH-STDIO-BOUND" "$T/detach-stdio.log" \
    && ok "detach-stdio-bound-to-file" || bad "detach-stdio-bound-to-file"
  grep -q "DONE SWAPPED" "$T/journal.log" && ok "detach-chain-completed" || bad "detach-chain-completed"
  # HQ order 2026-11-21: the detach must SAY where the log went, and the path must
  # reach the ledger row. Both assertions ride this arm deliberately: 21a is the
  # only place a detach actually FIRES, so they cannot pass on a chain that never
  # detached. `detach-fired` above is their positive control.
  grep -qF "oc-ship: detached log: $T/detach-stdio.log" <<< "$OUT" \
    && ok "detach-prints-log-path" || bad "detach-prints-log-path (stderr lacked the path; got: $(head -c 300 <<< "$OUT"))"
  grep -qF "detached log: $T/detach-stdio.log" "$T/journal.log" 2>/dev/null \
    && ok "detach-journals-log-path" || bad "detach-journals-log-path (journal has no path row: $(head -c 300 "$T/journal.log" 2>/dev/null))"

  # 21b. LOOP GUARD: a re-entered chain (OC_SHIPCHAIN_DETACHED=1) must NOT
  #      re-exec — otherwise the detach recurses forever.
  rm -f "$T/journal.log" "$T/detach-b.log"
  git -C "$T/clone" checkout -q main; git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=1 OC_SHIPCHAIN_DETACHED=1 OC_SHIPCHAIN_DETACH_CMD="$T/fake-detach" \
    FAKE_DETACH_LOG="$T/detach-b.log" FAKE_PRCHECKS_LOG="$T/prchecks.log" \
      bash "$SELF" --sha "$DSHA" --branch detach-fixture --wait 5 2>&1)" || RC=$?
  check_rc "detach-loopguard-rc" "$RC" 0
  [ -s "$T/detach-b.log" ] && bad "detach-loopguard-no-reexec" || ok "detach-loopguard-no-reexec"

  # 21c. NOT in the cgroup -> no detach at all. The detach must be a response
  #      to the environment, never an unconditional re-exec (every ordinary
  #      chain would otherwise pay a scope creation it does not need).
  rm -f "$T/journal.log" "$T/detach-c.log"
  git -C "$T/clone" checkout -q main; git -C "$T/clone" reset -q --hard origin/main
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
    OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
    OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
    OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
    OC_SHIPCHAIN_IN_UNIT_CGROUP=0 OC_SHIPCHAIN_DETACH_CMD="$T/fake-detach" \
    FAKE_DETACH_LOG="$T/detach-c.log" FAKE_PRCHECKS_LOG="$T/prchecks.log" \
      bash "$SELF" --sha "$DSHA" --branch detach-fixture --wait 5 2>&1)" || RC=$?
  check_rc "detach-outside-cgroup-rc" "$RC" 0
  [ -s "$T/detach-c.log" ] && bad "detach-not-taken-outside-cgroup" || ok "detach-not-taken-outside-cgroup"

  # 21d/21e. SURVIVAL + its NEGATIVE CONTROL, both in-selftest. The driver
  #     launches the chain in its OWN session, waits for it to be inside the
  #     gate, then SIGTERMs that session's process group — the closest a
  #     fixture gets to the swap's cgroup teardown. HOOK=1 must SURVIVE;
  #     HOOK=0 (detach disabled) must TRUNCATE. Without 21e, 21d would only
  #     prove the fixture is slow — the detach, not luck, has to be what saves
  #     the run.
  cat > "$T/survive-driver.sh" <<'DRIVER'
#!/usr/bin/env bash
# $1=T  $2=SELF  $3=SHA  $4=HOOK (1 = detach on, 0 = detach off)
T="$1"; SELF="$2"; SHA="$3"; HOOK="$4"
J="$T/surv-journal.log"; D="$T/detach-surv.log"
rm -f "$J" "$D"
setsid env \
  OC_SHIPCHAIN_IMPL=0 OC_SHIPCHAIN_IN_UNIT_CGROUP="$HOOK" \
  OC_SHIPCHAIN_DETACH_CMD="$T/fake-detach" FAKE_DETACH_LOG="$D" \
  OC_SHIPCHAIN_LOG="$T/detach-surv-stdio.log" \
  FAKE_SLOW_GATE=3 \
  OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
  OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
  OC_TOOLS_NOLOG=1 OC_SHIPCHAIN_LEDGER="$J" \
  OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" \
  bash "$SELF" --sha "$SHA" --branch detach-fixture --wait 5 > "$T/surv.out" 2>&1 &
CHAIN_PID=$!
i=0
while [ "$i" -lt 300 ]; do
  grep -q "LEG1 gate start" "$J" 2>/dev/null && break
  i=$((i+1)); sleep 0.05
done
kill -TERM -"$CHAIN_PID" 2>/dev/null
wait "$CHAIN_PID" 2>/dev/null
i=0
while [ "$i" -lt 400 ]; do
  grep -q "DONE SWAPPED" "$J" 2>/dev/null && break
  i=$((i+1)); sleep 0.05
done
grep -q "DONE SWAPPED" "$J" && echo SURVIVED || echo TRUNCATED
DRIVER
  chmod +x "$T/survive-driver.sh"
  git -C "$T/clone" checkout -q main; git -C "$T/clone" reset -q --hard origin/main
  SURV="$(bash "$T/survive-driver.sh" "$T" "$SELF" "$DSHA" 1 2>/dev/null | tail -1)"
  [ "$SURV" = "SURVIVED" ] && ok "detach-survives-group-kill" || bad "detach-survives-group-kill (got '$SURV')"
  grep -q "FAKE-DETACH-STDIO-BOUND" "$T/detach-surv-stdio.log" \
    && ok "detach-surv-stdio-bound-to-fixture" || bad "detach-surv-stdio-bound-to-fixture"
  git -C "$T/clone" checkout -q main; git -C "$T/clone" reset -q --hard origin/main
  TRUNC="$(bash "$T/survive-driver.sh" "$T" "$SELF" "$DSHA" 0 2>/dev/null | tail -1)"
  [ "$TRUNC" = "TRUNCATED" ] && ok "no-detach-truncates-on-kill" || bad "no-detach-truncates-on-kill (got '$TRUNC')"

  # ---- #77: scheduling class. A chain is BACKGROUND work and must not compete
  # with the daemon, so `low` is the DEFAULT -- and the class is read back off
  # the kernel, never echoed from the flag we just parsed.
  #
  # Every probe runs inside a subshell whose niceness is first forced to 0.
  # That is not decoration: the battery renices itself to 19 (#76), so a child
  # that lowers nothing inherits 19 -- a naive `nice=0` assertion then fails for
  # the wrong reason, and a naive `nice=19` assertion PASSES for the wrong
  # reason. #76 measured exactly that: a mutant that never renices read 19 and
  # the control reported success.
  RC=0; OUT="$(bash -c 'renice -n 0 -p $$ >/dev/null 2>&1 || :; OC_SHIPCHAIN_IMPL=0 exec bash "$0" --resolve-priority' "$SELF" 2>&1)" || RC=$?
  check_rc "priority-default-rc0" "$RC" 0
  grep -qx 'priority=low' <<< "$OUT" \
    && ok "priority-default-class-low" || bad "priority-default-class-low (got: $OUT)"
  grep -qx 'nice=19' <<< "$OUT" \
    && ok "priority-default-nice-19" || bad "priority-default-nice-19 (got: $OUT)"
  # #77 req 2: the CHILD, not just this process. The probe forks a real child
  # after the renice; if the apply moved below that spawn this reads 0 while the
  # parent still reads 19, so it discriminates ORDERING.
  grep -qx 'child_nice=19' <<< "$OUT" \
    && ok "priority-default-child-nice-19" || bad "priority-default-child-nice-19 (got: $OUT)"
  grep -q '^applied=.*renice' <<< "$OUT" \
    && ok "priority-default-applied-names-renice" || bad "priority-default-applied-names-renice (got: $OUT)"

  # 15b. `normal` must really leave the process alone. Asserted from a 0
  #      baseline so "did nothing" is distinguishable from "inherited 0".
  RC=0; OUT="$(bash -c 'renice -n 0 -p $$ >/dev/null 2>&1 || :; OC_SHIPCHAIN_IMPL=0 exec bash "$0" --priority normal --resolve-priority' "$SELF" 2>&1)" || RC=$?
  check_rc "priority-normal-rc0" "$RC" 0
  grep -qx 'priority=normal' <<< "$OUT" \
    && ok "priority-normal-class" || bad "priority-normal-class (got: $OUT)"
  grep -qx 'nice=0' <<< "$OUT" \
    && ok "priority-normal-nice-0" || bad "priority-normal-nice-0 (got: $OUT)"
  grep -qx 'child_nice=0' <<< "$OUT" \
    && ok "priority-normal-child-nice-0" || bad "priority-normal-child-nice-0 (got: $OUT)"
  grep -qx 'applied=none' <<< "$OUT" \
    && ok "priority-normal-applied-none" || bad "priority-normal-applied-none (got: $OUT)"

  # 15c. a typo must be refused, not silently treated as `normal` -- an accepted
  #      but ignored flag is indistinguishable from an honoured one.
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 bash "$SELF" --priority hig --resolve-priority 2>&1)" || RC=$?
  check_rc "priority-bad-value-rc2" "$RC" 2
  RC=0; OUT="$(OC_SHIPCHAIN_IMPL=0 bash "$SELF" --priority 2>&1)" || RC=$?
  check_rc "priority-missing-value-rc2" "$RC" 2
  # rc alone is not sufficient: see the twin leg in oc-deploy -- an unvalidated
  # flag can exit 2 downstream for an unrelated reason, so the diagnostic is
  # what discriminates validation from a later usage error.
  grep -q -- '--priority needs' <<< "$OUT" \
    && ok "priority-missing-value-names-the-flag" || bad "priority-missing-value-names-the-flag (got: $OUT)"

  # 15d. the class must reach the OPERATOR, not just the probe. The stderr line
  #      prints on every non-probe invocation, so a lane reading a chain's log
  #      can tell what class it ran at without re-deriving it from argv.
  RC=0; OUT="$(renice -n 0 -p $$ >/dev/null 2>&1 || :; OC_SHIPCHAIN_IMPL=0 OPENCRABS_SESSION_ID="$LEG_UUID" \
    OC_NOTIFY_BIN="$T/bin/opencrabs" WAKELOG="$T/wake.log" OC_FORK_REPO="$T/clone" \
    bash "$SELF" --eval-docs-skip "$FSHA" 2>&1)" || RC=$?
  check_rc "priority-stderr-line-rc1" "$RC" 1
  grep -q 'oc-ship: priority=low (nice=19' <<< "$OUT" \
    && ok "priority-stderr-names-class" || bad "priority-stderr-names-class (got: $OUT)"

  # ---- #79: a SIGNAL must terminate the chain, and must be LABELLED so a
  # supervisor can refuse to re-arm it.
  #
  # Before the fix `_chain_exit_handler` was trapped on `EXIT INT TERM` and
  # never called `exit`, so SIGTERM released the landing lock, journalled, woke
  # the arming lane, finished the log row -- and then RESUMED execution,
  # unlocked, mid-leg, with a wake already sent. A kill read as a clean stop.
  #
  # The arm is built as a PAIR, because rc alone cannot discriminate: a chain
  # that exits 143 AFTER completing its work also reads 143. The signal is sent
  # while LEG1's gate child is still running, so a chain that resumes goes on to
  # print the completion marker -- and its ABSENCE is what proves termination
  # rather than a late exit.
  rm -f "$T/journal.log" "$T/prchecks-sig.log" "$T/sig.out"
  git -C "$T/clone" checkout -q main
  git -C "$T/clone" reset -q --hard origin/main
  cat > "$T/sig-driver.sh" <<'DRIVER'
#!/usr/bin/env bash
T="$1"; SELF="$2"; SHA="$3"
FAKE_SLOW_GATE=2 FAKE_PRCHECKS_LOG="$T/prchecks-sig.log" \
OC_SHIPCHAIN_IMPL=0 OC_PRCHECKS_BIN="$T/fake-prchecks" OC_DEPLOY_BIN="$T/fake-deploy" \
OC_ISSUELOG_BIN="$T/fake-issuelog" OC_FORK_REPO="$T/clone" \
OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$T/tools-sig.log" OC_SHIPCHAIN_NO_ISSUE_PROBE=1 OC_SHIPCHAIN_LEDGER="$T/journal.log" \
OC_SHIPCHAIN_FREEZE_OVERRIDE=1 OC_DEPLOY_STATE_DIR="$T/state" OC_SHIPCHAIN_IN_UNIT_CGROUP=0 \
  bash "$SELF" --sha "$SHA" --branch feat --wait 5 >"$T/sig.out" 2>&1 &
pid=$!
i=0
while [ "$i" -lt 400 ]; do [ -s "$T/prchecks-sig.log" ] && break; i=$((i+1)); sleep 0.02; done
kill -TERM "$pid" 2>/dev/null
wait "$pid"
echo "rc=$?"
DRIVER
  chmod +x "$T/sig-driver.sh"
  SIGLINE="$(bash "$T/sig-driver.sh" "$T" "$SELF" "$FSHA" 2>/dev/null | tail -1)"
  check_rc "signal-term-exit-code" "${SIGLINE#rc=}" 143
  # The completion marker is the journal's, matching the detach arms' convention:
  # a chain that RESUMED after the signal runs LEG2 to the end and writes it.
  grep -q "DONE SWAPPED" "$T/journal.log" 2>/dev/null && bad "signal-term-did-not-continue" || ok "signal-term-did-not-continue"
  # #74 preservation: the log row must still NAME the signal. Without this arm
  # the annotation can be dropped by any future trap reordering and every other
  # #79 arm still passes -- the exit code is right, the label is gone.
  grep -q '"signal":"TERM"' "$T/tools-sig.log" 2>/dev/null && ok "signal-term-labelled-in-log" || bad "signal-term-labelled-in-log: $(tail -2 "$T/tools-sig.log" 2>/dev/null | tr '\n' ' ')"

  # ---- #78: the re-arm classifier.
  #
  # The predicate under test is "did anything external happen", NOT "which leg
  # died" -- the table above chain_rearm_action() carries the reasoning. Every
  # vertex is asserted in BOTH directions, because the two failure modes are
  # opposite and both silent: an over-broad arm dispatches a fresh gate onto a
  # gated ref and CANCELS the run it was waiting for, while an over-narrow one
  # leaves a mechanical exit waking a human for nothing. A one-directional arm
  # would pass while the classifier drifted to either extreme.
  _ra() { CHAIN_DIE_MSG="${1:-}"; GATE_RUN_ID="${2:-}"; chain_rearm_action "${3:-}"; }
  _ra_ck() { # $1 = arm name, $2 = want, $3 = message, $4 = rc, $5 = gate run id
    local got; got="$(_ra "$3" "${5:-}" "$4")"
    [ "$got" = "$2" ] && ok "$1" || bad "$1: want '$2', got '$got' (msg='$3' rc=$4 run='${5:-}')"
  }
  # rc 9 = SHIP-LOCK-TIMEOUT: never got past the landing lock, nothing external.
  _ra_ck "rearm-rc9-lock-retry" "lock-retry" "ship lock timeout" 9
  # The three prchecks codes that provably dispatch NOTHING. These are the only
  # rc-6 exits that may restart.
  _ra_ck "rearm-gate-infra-4" "gate-redispatch" "gate infra rc=4" 6
  _ra_ck "rearm-gate-infra-7" "gate-redispatch" "gate infra rc=7" 6
  _ra_ck "rearm-gate-infra-8" "gate-redispatch" "gate infra rc=8" 6
  # THE GUARD: the SAME pre-dispatch codes with a witnessed run must NOT
  # re-arm. prchecks rc 4 is also reachable from the rc=5 resume loop's own
  # "run view failed" / "jobs fetch failed" sites, where a live run exists --
  # re-dispatching there cancels the verdict. Without these three arms the code
  # class alone would look correct and the cancel hazard would be unmeasured.
  _ra_ck "norearm-gate-infra-4-witnessed-run" "" "gate infra rc=4" 6 "43652761485"
  _ra_ck "norearm-gate-infra-7-witnessed-run" "" "gate infra rc=7" 6 "43652761485"
  _ra_ck "norearm-gate-infra-8-witnessed-run" "" "gate infra rc=8" 6 "43652761485"
  # rc-6 exits where a run DID exist: restarting cancels the live verdict.
  _ra_ck "norearm-gate-infra-6-cancelled" "" "gate infra rc=6" 6
  # #92: rc 6 becomes re-armable ONLY as a RESUME of the superseder prchecks
  # named. The arm directly above is the control -- an UNNAMED rc 6 must still
  # refuse -- and these pin the named cases in both directions. `none` is what
  # prchecks prints for the TIMEOUT-cancel class, and resuming nothing is not
  # an action.
  _ra_ck6() { # $1 = arm name, $2 = want, $3 = superseder, $4 = message
    local got; GATE_SUPERSEDING="$3"
    got="$(_ra "$4" "" 6)"
    [ "$got" = "$2" ] && ok "$1" || bad "$1: want '$2', got '$got' (sup='$3')"
    GATE_SUPERSEDING=""
  }
  _ra_ck6 "rearm-rc6-resumes-named-superseder" "gate-resume:222" "222" "gate infra rc=6"
  _ra_ck6 "norearm-rc6-none-found-refuses"     ""                "none" "gate infra rc=6"
  _ra_ck6 "norearm-rc6-empty-superseder"       ""                ""     "gate infra rc=6"
  _ra_ck "norearm-gate-resume-failed" "" "gate resume failed" 6
  _ra_ck "norearm-gate-rc5-no-run-id" "" "gate rc=5 but no run id on stdout" 6
  # The swap sites: LEG3/LEG4 already touched the world.
  _ra_ck "norearm-swap-poll-failed" "" "swap poll failed rc=1" 6
  _ra_ck "norearm-swap-not-confirmed" "" "swap not confirmed after 12 polls" 6
  # Class B (rc 7 / rc 8) is DROPPED by owner decision 2026-11-18: 0 of 213
  # measured re-arms. These arms pin that boundary so a later "symmetry" edit
  # cannot quietly wire them back in.
  _ra_ck "norearm-rc7-class-b" "" "carrier head unresolvable" 7
  _ra_ck "norearm-rc8-class-b" "" "gate ambiguous" 8
  # rc 5 is ONE code with eight opposite remedies -- never mechanically mapped.
  _ra_ck "norearm-rc5" "" "gate timed out in flight" 5
  # The default wake classes keep today's behaviour exactly.
  _ra_ck "norearm-rc3-frozen" "" "freeze active" 3
  _ra_ck "norearm-rc4" "" "runner killed" 4
  _ra_ck "norearm-rc0" "" "" 0
  # An rc-6 whose message names no prchecks code is NOT a dispatch failure: the
  # classifier must fall through rather than treat "infra" as sufficient.
  _ra_ck "norearm-rc6-bare-infra" "" "gate infra" 6
  _ra_ck "norearm-rc6-empty-msg" "" "" 6
  CHAIN_DIE_MSG=""

  echo "selftest: $PASS passed, $FAIL failed"
  # Contract fix 2026-09-11: was `return $?`, which returned ECHO's status (0),
  # so a broken selftest still exited 0 and the battery's run_selftest gate
  # could never see it fail. rc now reflects the failure count.
  [ "$FAIL" -eq 0 ]