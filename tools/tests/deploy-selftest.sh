#!/usr/bin/env bash
# =============================================================================
# deploy-selftest.sh — the BODY of the deploy suite, moved VERBATIM.
#
# SOURCED, never executed: `selftest()` (tools/lib/oc-deploy-lib.sh) is a thin
# wrapper that `.`-sources this file. It must stay SOURCED because the body
# declares `local T pass=0 fail=0` and defines check_rc/check_has as NESTED
# functions that close over those locals — an exec or a subprocess breaks both.
#
# T5-bis (four-way split): the suite is ONE suite and it still covers all four
# stages, so `selftest()` first loads the four tools' functions into this shell
# (oc_deploy_load_funcs) and every child below invokes the tool that OWNS its
# verb — `oc-build` (ship/features), `oc-swap` (swap-execute), `oc-fanout`
# (fanout), `oc-status` (poll/status/watch). Until factory #168 cut 5 those
# children went through the `oc-deploy` dispatcher; it is deleted, so the suite
# names the owner directly. Entry point: `oc-build --selftest` (any stage tool
# answers it, since `selftest()` lives in the shared library).
#
# Nothing about the CHECKS changed — only the paths that pin SOURCE SHAPE
# (SRC_*) and the sandbox tree in 10f-ter.
#
# WHY IT LIVES HERE: the tool was 5,011 lines, 2,186 of them selftest fixture.
# Extraction is verifiable by PASS COUNT: the battery's deploy-selftest section
# must report the same number of passing arms before and after.
# =============================================================================
  # M2-21 (2026-09-12): hermetic by construction, NOT by argv shape. The fixture
  # children below (`ship --sha <temp-repo HEAD> --execute`) inherit this and stay
  # out of the production tools.log even if the shared predicate regresses.
  export OC_TOOLS_NOLOG=1
  local T pass=0 fail=0 rc out
  T="$(mktemp -d)" || return 1
  export OC_DEPLOY_NO_WATCH=1  # piggyback OFF in selftest (explicit watch tests below run it for real)
  export OC_SWAP_IN_UNIT_CGROUP=0 # selftest sandboxes everything — do not systemd-run re-exec
  # (#623) hermetic: the fan-out's bounded re-send must never SLEEP inside a
  # selftest. The legs below set their own budget explicitly to exercise it.
  export OC_DEPLOY_NOTIFY_RETRY_BUDGET=0
  # #766: the fork-release publish tail is OFF for every selftest fixture —
  # publish-leg cases below opt back in with OC_DEPLOY_NOPUBLISH=0. This is
  # a SAFETY floor, not convenience: a fixture that forgot OC_DEPLOY_GH would
  # otherwise reach REAL GitHub (the same class the notify stub closes).
  export OC_DEPLOY_NOPUBLISH=1
  # v0.4.153: hermetic cgroup. The battery itself runs INSIDE opencrabs-ops.service,
  # so auto-detection would make every nested swap-execute re-exec via systemd-run.
  # Forced OFF here; section 22 sets it per-invocation to exercise the detach path.
  export OC_SWAP_IN_UNIT_CGROUP=0
  local SD="$T/state"
  mkdir -p "$SD/tools" "$SD/backups" "$T/bin"
  # #168 cut 5: the DISPATCHER is gone, so the children below name the tool that
  # OWNS each verb. This is deliberately NOT a router function: a leg that called
  # a shim could pass while the file that owns the behaviour was broken, which is
  # the defect the earlier cuts removed from the 21a-21e and recover-receipt legs.
  # `selftest()` therefore receives NO argv (the `--selftest` arm calls it bare),
  # so nothing here may read `$1` — the old `${1:-...}` default silently took the
  # FLAG as the binary path and reddened 378 legs the moment a stage tool ran the
  # suite (measured: oc-build --selftest -> 142 pass / 378 fail before this fix).
  # Absolute, so a re-exec after cd into tmp can still resolve them.
  local BUILD_BIN="$OC_TOOLS_DIR/ship/oc-build" SWAP_BIN="$OC_TOOLS_DIR/ship/oc-swap" \
        FANOUT_BIN="$OC_TOOLS_DIR/ship/oc-fanout" STATUS_BIN="$OC_TOOLS_DIR/ship/oc-status"
  # #168 cut 5: `lineage-check` left the library for its own tool, so the 21a-21e
  # legs go to it DIRECTLY. They used to run through the dispatcher, which made
  # them pass on a shim while the tool they claimed to cover could be broken —
  # the leg must name the file that owns the verdict.
  local LV_BIN="$OC_TOOLS_DIR/harvest/oc-verify-lineage"
  # #168 cut 5: `recover-receipt` left the library for a MODE of oc-status, so
  # its legs name that tool directly. Reached through the dispatcher they would
  # pass on the shim and prove nothing about the file that owns the repair.
  local RR_BIN="$OC_TOOLS_DIR/ship/oc-status"
  # T5-bis: the split moved code out of the one file the source-shape guards
  # below used to grep. Each such guard reads the file that OWNS what it pins.
  local SRC_LIB="$OC_TOOLS_DIR/lib/oc-deploy-lib.sh" SRC_BUILD="$OC_TOOLS_DIR/ship/oc-build"
  local SRC_SWAP="$OC_TOOLS_DIR/ship/oc-swap" SRC_FANOUT="$OC_TOOLS_DIR/ship/oc-fanout"
  local SRC_STATUS="$OC_TOOLS_DIR/ship/oc-status"
  check_rc() { if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: $1 rc=$2 want=$3"; fi; }
  check_has() { case "$2" in *"$3"*) pass=$((pass+1)) ;; *) fail=$((fail+1)); echo "SELFTEST FAIL: $1 missing: $3" ;; esac; }
  # stubs
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD/tools/val-ok";       chmod +x "$SD/tools/val-ok"
  printf '#!/usr/bin/env bash\nexit 2\n' > "$SD/tools/val-fail";     chmod +x "$SD/tools/val-fail"
  # KERNEL D2: carrier features stubs (resolution aborts on read failure)
  printf '#!/usr/bin/env bash\necho telegram\n' > "$SD/tools/carrier";      chmod +x "$SD/tools/carrier"
  printf '#!/usr/bin/env bash\nexit 3\n'        > "$SD/tools/carrier-fail"; chmod +x "$SD/tools/carrier-fail"
  # consent stubs retired 2026-08-28 (consent process eliminated)
  printf '#!/usr/bin/env bash\necho "launch $*" >> "%s"; exit 0\n' "$T/launch.log" > "$SD/launch"; chmod +x "$SD/launch"
  # notify shim (verb stub): logs every call; dead uuid bbbb -> rc 2. Created
  # early so the swap-execute DRILL case (11) can assert zero verb calls.
  cat > "$SD/notify" <<'NSTUB'
#!/usr/bin/env bash
echo "$*" >> "${NOTIFY_LOG:?}"
for last; do :; done
[ "$last" = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" ] && exit 2
exit 0
NSTUB
  chmod +x "$SD/notify"
  export NOTIFY_LOG="$T/notify.log"; : > "$NOTIFY_LOG"
  cat > "$SD/gh" <<'STUB'
#!/usr/bin/env bash
[ -n "${GH_LOG:-}" ] && echo "$*" >> "$GH_LOG"
# 6b-6e (F-1 fusion v0.4.97): ship-wait stub arm PREEMPTS the main case when
# OC_TEST_SHIPWAIT_HEAD is set — run 555's head_sha tracks the shipped sha.
if [ -n "${OC_TEST_SHIPWAIT_HEAD:-}" ]; then
  case "$*" in
    *actions/runs/555/jobs*)
      echo "{\"jobs\":[{\"name\":\"ORDER gates\"},{\"name\":\"Linux amd64 ($OC_TEST_SHIPWAIT_HEAD, telegram)\"}]}" ;;
    *actions/runs/555*)
      case "${OC_TEST_SHIPWAIT_CONCL:-}" in
        completed-success) echo "{\"status\":\"completed\",\"conclusion\":\"success\",\"head_sha\":\"$OC_TEST_SHIPWAIT_HEAD\"}" ;;
        completed-failure) echo "{\"status\":\"completed\",\"conclusion\":\"failure\",\"head_sha\":\"$OC_TEST_SHIPWAIT_HEAD\"}" ;;
        *)                 echo "{\"status\":\"in_progress\",\"conclusion\":null,\"head_sha\":\"$OC_TEST_SHIPWAIT_HEAD\"}" ;;
      esac ;;
    *workflows/quick-build-linux.yml/runs*) echo '{"workflow_runs":[{"id":555}]}' ;;
    *) echo '{}' ;;
  esac
  exit 0
fi
case "$*" in
  # #766 publish-leg controls: release view/create/upload + the tag-move PATCH.
  #   OC_TEST_REL_EXISTS : space-list of tags that already exist (view -> rc 0)
  #   OC_TEST_REL_FAIL   : non-empty => create/upload/PATCH fail (tolerance case)
  #   OC_TEST_REL_CAPTURE: dir to copy the passed asset files into (content proof)
  "release view"*)
    _tag=""; for _w in $*; do case "$_w" in fork-*) _tag="$_w"; break;; esac; done
    case " ${OC_TEST_REL_EXISTS:-} " in *" $_tag "*) exit 0;; esac
    exit 1 ;;
  "release create"*|"release upload"*)
    [ -n "${OC_TEST_REL_FAIL:-}" ] && exit 1
    if [ -n "${OC_TEST_REL_CAPTURE:-}" ]; then
      for _a in "$@"; do case "$_a" in *.tar.gz|*SHA256SUMS|*build-flags.txt) cp -f "$_a" "$OC_TEST_REL_CAPTURE/" 2>/dev/null || true;; esac; done
    fi
    exit 0 ;;
  "release edit"*) exit 0 ;;
  "api -X PATCH"*refs/tags*)
    [ -n "${OC_TEST_REL_FAIL:-}" ] && exit 1
    exit 0 ;;
  *runs?status=failure*) echo '{"workflow_runs":[{"id":888,"status":"completed","conclusion":"failure"}]}' ;;
  *actions/runs/777/jobs*) echo '{"jobs":[{"name":"ORDER gates"},{"name":"Linux amd64 (bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, telegram)","conclusion":"success"}]}' ;;
  *actions/runs/777*) echo '{"status":"completed","conclusion":"success"}' ;;
  *actions/runs/888/jobs*) echo '{"jobs":[{"name":"ORDER gates","conclusion":"success"},{"name":"Linux amd64 (eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee, telegram)","conclusion":"failure","check_run_url":"https://api.github.com/repos/leshchenko1979/opencrabs/check-runs/9001"}]}' ;;
  *runs?status=success*)
    if [ -n "${OC_TEST_GATES_FIRST:-}" ]; then echo '{"workflow_runs":[{"id":334}]}'
    elif [ -n "${OC_TEST_STALE_FIRST:-}" ]; then echo '{"workflow_runs":[{"id":999},{"id":111}]}'; else echo '{"workflow_runs":[{"id":111}]}'; fi ;;
  *actions/runs/334/jobs*) echo '{"jobs":[{"name":"ORDER gates (dddddddddddddddddddddddddddddddddddddddd)","conclusion":"success"},{"name":"Linux amd64 (dddddddddddddddddddddddddddddddddddddddd, telegram)","conclusion":"success"}]}' ;;
  *actions/runs/999/jobs*) echo '{"jobs":[{"name":"ORDER gates (2f604e56...)"}]}' ;;
  *actions/runs/998/jobs*) echo '{"jobs":[{"name":"ORDER gates (2f604e56...)"}]}' ;;
  # #68 TASK 2: run 995 DOES carry a decodable sha, so the only thing that can
  # stop it decoding is the decoder library being absent. It is a separate id from
  # 998 because 10f has already marked 998 done, and the idempotence guard would
  # answer before the decode path ran.
  *actions/runs/995/jobs*) echo '{"jobs":[{"name":"Linux amd64 (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, telegram)"}]}' ;;
  *actions/runs/995*) echo '{"status":"completed","conclusion":"success"}' ;;
  *actions/runs/998*) echo '{"status":"completed","conclusion":"success"}' ;;
  # #84: run 997's JOB-LIST read FAILS (HTTP 500) while its metadata read
  # succeeds — the exact shape measured on run 44420005606 (run fetch OK, jobs
  # fetch dead in the same gh blip). Paired with 998, which was READ fine and
  # carries no decodable sha, so the two arms differ ONLY in whether the read
  # succeeded. That difference is the whole fix.
  *actions/runs/997/jobs*) echo "HTTP 500: Server Error" >&2; exit 1 ;;
  *actions/runs/997*) echo '{"status":"completed","conclusion":"success"}' ;;
  *workflows/quick-build-linux.yml/runs*) echo '{"workflow_runs":[{"id":111}]}' ;;
  *actions/runs/222/jobs*|*actions/runs/555/jobs*|*actions/runs/789/jobs*|*actions/runs/790/jobs*|*actions/runs/791/jobs*|*actions/runs/774/jobs*) echo '{"jobs":[{"name":"ORDER gates"},{"name":"Linux amd64 (cccccccccccccccccccccccccccccccccccccccc, telegram)"}]}' ;;
  *actions/runs/333/jobs*) echo '{"jobs":[{"name":"ORDER gates"},{"name":"Linux amd64 (dddddddddddddddddddddddddddddddddddddddd, telegram)"}]}' ;;
  *actions/runs/668/jobs*) echo '{"jobs":[{"name":"Linux amd64 (ffffffffffffffffffffffffffffffffffffffff, telegram)","conclusion":"failure","check_run_url":"https://api.github.com/repos/leshchenko1979/opencrabs/check-runs/9002"}]}' ;;
  *check-runs/9002/annotations*) echo '[]' ;;
  *actions/runs/666/jobs*|*actions/runs/667/jobs*|*actions/runs/669/jobs*|*actions/runs/670/jobs*|*actions/runs/676/jobs*) echo '{"jobs":[{"name":"ORDER gates","conclusion":"success"},{"name":"Linux amd64 (eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee, telegram)","conclusion":"failure","check_run_url":"https://api.github.com/repos/leshchenko1979/opencrabs/check-runs/9001"}]}' ;;
  *check-runs/9001/annotations*) echo '[{"path":"bad.txt","start_line":3}]' ;;
  *actions/runs/444*) echo '{"status":"in_progress","conclusion":null}' ;;
  *actions/runs/222*|*actions/runs/333*|*actions/runs/555*|*actions/runs/789*|*actions/runs/790*|*actions/runs/791*|*actions/runs/774*) echo '{"status":"completed","conclusion":"success"}' ;;
  *actions/runs/66*|*actions/runs/67*|*actions/runs/77*|*actions/runs/88*)
    RED=""
    case "$*" in *actions/runs/66*|*actions/runs/67*|*actions/runs/77*|*actions/runs/88*) RED=1 ;; esac
    if [ -n "$RED" ] && [ -f "${OC_DEPLOY_STATE_DIR:-}/red-head" ]; then
      echo "{\"status\":\"completed\",\"conclusion\":\"failure\",\"head_sha\":\"$(cat "${OC_DEPLOY_STATE_DIR}/red-head")\"}"
    else
      echo '{"status":"completed","conclusion":"failure"}'
    fi ;;
  *runs/111/jobs*) echo '{"jobs":[{"name":"ORDER gates"},{"name":"Linux amd64 (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, telegram)"}]}' ;;
  # #72: the carrier's OWN declaration — the dispatch leg probes this before
  # passing -f fork_version, because an undeclared dispatch input is a hard 422
  # from the API (it would break EVERY ship, not just this one).
  #   OC_TEST_CARRIER_FORK_VERSION=1 => the input IS declared (post-transition)
  #   unset                          => transition carrier, input absent
  *contents/.github/workflows/*)
    # OC_TEST_CARRIER_YML_FAIL=1 => the read itself FAILS (rc 1). This is NOT the
    # same state as "declared nothing": an unreadable contract must refuse, not
    # be read as a negative answer (#72).
    if [ -n "${OC_TEST_CARRIER_YML_FAIL:-}" ]; then exit 1; fi
    if [ -n "${OC_TEST_CARRIER_FORK_VERSION:-}" ]; then
      printf 'on:\n  workflow_dispatch:\n    inputs:\n      source_repository:\n        required: false\n      fork_version:\n        required: false\n'
    else
      printf 'on:\n  workflow_dispatch:\n    inputs:\n      source_repository:\n        required: false\n'
    fi ;;
  *) echo '{}' ;;
esac
STUB
  chmod +x "$SD/gh"
  # #85: a SEPARATE gh stub whose API read can be made to fail, so the main
  # stub's semantics stay untouched. OC_TEST_API_FAIL_N = number of leading
  # failures on `runs?status=success`; UNSET = every call fails (the genuine-RED
  # control). The counter file is per-leg so legs cannot leak state into each
  # other — the failure that would hide is "leg 2 passes because leg 1 already
  # consumed the failures".
  cat > "$SD/gh-api-flaky" <<'FSTUB'
#!/usr/bin/env bash
[ -n "${GH_LOG:-}" ] && echo "$*" >> "$GH_LOG"
case "$*" in
  *runs?status=success*)
    _cf="${OC_TEST_API_COUNTER:?OC_TEST_API_COUNTER unset}"
    _n=0; [ -f "$_cf" ] && _n="$(cat "$_cf" 2>/dev/null || echo 0)"
    _n=$((_n + 1)); echo "$_n" > "$_cf"
    if [ -z "${OC_TEST_API_FAIL_N:-}" ] || [ "$_n" -le "$OC_TEST_API_FAIL_N" ]; then
      echo "HTTP 502: Bad Gateway (https://api.github.com/repos/x/actions/workflows/y/runs)" >&2
      exit 1
    fi
    echo '{"workflow_runs":[{"id":111}]}' ;;
  *actions/runs/111/jobs*) echo '{"jobs":[{"name":"ORDER gates"},{"name":"Linux amd64 (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, telegram)","conclusion":"success"}]}' ;;
  *actions/runs/111*) echo '{"status":"completed","conclusion":"success"}' ;;
  *runs?status=failure*) echo '{"workflow_runs":[]}' ;;
  *) echo '{}' ;;
esac
exit 0
FSTUB
  chmod +x "$SD/gh-api-flaky"
  # sandbox git: bare remote at c1, repo ahead at c2 (FF-able)
  git init -q --bare -b main "$T/remote.git"
  git init -q -b main "$T/repo"
  git -C "$T/repo" config user.email t@t; git -C "$T/repo" config user.name t
  echo one > "$T/repo/f1"; git -C "$T/repo" add f1; git -C "$T/repo" commit -qm one
  echo two > "$T/repo/f2"; git -C "$T/repo" add f2; git -C "$T/repo" commit -qm two
  local SHA2; SHA2="$(git -C "$T/repo" rev-parse HEAD)"
  git -C "$T/repo" push -q "$T/remote.git" HEAD~1:refs/heads/main   # remote main = c1
  export GH_LOG="$T/gh.log"; : > "$GH_LOG"
  # #73: a FOREIGN repo (own history, does NOT contain SHA2) and a plain
  # non-repo dir — the two wrong-directory shapes the ship guard must name.
  git init -q -b main "$T/foreign"
  git -C "$T/foreign" config user.email t@t; git -C "$T/foreign" config user.name t
  echo x > "$T/foreign/g1"; git -C "$T/foreign" add g1; git -C "$T/foreign" commit -qm foreign-one
  mkdir -p "$T/plain"
  # #166 hermetic carrier: the redscan/renice arms resolve deployed features
  # through the REAL oc-features, whose default REPO is $HOME/opencrabs — a
  # LIVE `git fetch` to GitHub per arm (~7 s each here, the #105 stall class on
  # a network hiccup, non-hermetic by construction). The fixture below carries
  # the live yml's features default, and oc-features' env-pinned defaults
  # (OC_CARRIER_REPO) point resolution at it. Production callers pass nothing
  # and keep $HOME/opencrabs; --repo/--ref still override everything.
  #
  # #168 cut 2: the read is REMOTE now, so a local bare remote cannot serve it
  # any more — the fixture's origin is a GITHUB-SHAPED slug and the read itself
  # is served by a `gh` stub through oc-features' OC_CARRIER_GH seam. That is
  # strictly more hermetic than the local fetch it replaces: no network, no
  # git object store to keep in sync, and the same yml bytes.
  local _carrier_src="$T/carrier"
  git init -q -b main "$_carrier_src" || return 1
  git -C "$_carrier_src" config user.email t@t; git -C "$_carrier_src" config user.name t
  mkdir -p "$_carrier_src/.github/workflows"
  cat > "$_carrier_src/.github/workflows/quick-build-linux.yml" <<'CYML'
name: quick-build-linux
on:
  workflow_dispatch:
    inputs:
      source_ref:
        description: full 40-char sha
        required: true
      features:
        description: 'Cargo feature set passed to --features (comma-separated)'
        required: false
        default: 'telegram,code-graph,browser,eval'
      fork_version:
        description: fork version
        required: false
        default: 'main'
jobs:
  build:
    runs-on: ubuntu-latest
CYML
  git -C "$_carrier_src" add -A; git -C "$_carrier_src" commit -qm carrier
  git -C "$_carrier_src" remote add origin git@github.com:fixture/carrier.git
  printf '#!/usr/bin/env bash\ncat "%s/.github/workflows/quick-build-linux.yml"\n' "$_carrier_src" > "$T/bin/gh-carrier"
  chmod +x "$T/bin/gh-carrier"
  export OC_CARRIER_REPO="$_carrier_src" OC_CARRIER_GH="$T/bin/gh-carrier"

  # 1. usage (no verb) -> exit 1. This was the dispatcher's contract; with the
  #    dispatcher gone the rc-1 usage shape is asserted on the tool that carries
  #    it (oc-status), NOT on a router that no longer exists. oc-build answers
  #    rc 2 here by design (a bare `oc-build` is a ship attempt missing --sha),
  #    so naming it would assert the wrong contract.
  "$STATUS_BIN" >/dev/null 2>&1; check_rc "usage-no-mode" $? 1
  # 2. unknown arg -> exit 1
  "$BUILD_BIN" ship --bogus >/dev/null 2>&1; check_rc "unknown-arg" $? 1
  # 3. kill file -> exit 9 even for valid mode
  mkdir -p "$T/kills"; printf x > "$T/kills/oc-deploy.kill"
  OC_DEPLOY_STATE_DIR="$T/kills" "$STATUS_BIN" poll >/dev/null 2>&1; check_rc "kill-file" $? 9
  # 3b. the `contributors` verb is DELETED, not retired (#168 cut 5). The three
  #     legs that used to live here asserted the deprecation NOTICE — a test that
  #     keeps a verb alive to print a message about itself. `oc-attrib
  #     --contributors` is the one shape and has its own legs. The last survivor
  #     of the old arm was this rc-1 leg, which passed only because an unknown
  #     verb is usage — i.e. it asserted the ABSENCE of a verb it named, on a
  #     router. Nothing left to name.
  # 4. ship PLAN mode: no mutation, PLAN lines, shadow entry, carrier-default features
  # 4-no-sha (Duty-6 lens F task 3): ship WITHOUT --sha must refuse rc2 —
  # no implicit CWD-HEAD adoption (wrong-directory ship pushes unintended sha).
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship 2>&1)"; check_rc "ship-no-sha-refused" $? 2
  check_has "ship-no-sha-msg" "$out" "ship requires --sha"
  check_has "ship-no-sha-gate-token" "$out" "OC_DEPLOY_GATE=missing-sha"   # C-A2
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; rc=$?
  check_rc "ship-plan-rc" $rc 0
  local SHIP_PLAN_OUT="$out"   # keep for 4b's plan-complete check (phantom cases clobber $out)
  check_has "ship-plan-lines" "$out" "would: git push"
  check_has "ship-plan-ff" "$out" "FF ok"
  check_has "ship-plan-carrier-features" "$out" "features=telegram"
  # 4a-phantom (n=1878): format-valid sha that does not EXIST -> refuse rc1,
  # before any plan/rebase output (fabricated-sha incident guard).
  local PHANTOM="4c0115ba9aa052f5cfeda01383c0d20be9e2392e"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$PHANTOM" 2>&1)"; check_rc "ship-phantom-sha" $? 1
  check_has "ship-phantom-msg" "$out" "sha not found in this repo"
  grep -q "PLAN: ship" <<<"$out" && { fail=$((fail+1)); echo "SELFTEST FAIL: phantom sha produced plan lines"; } || pass=$((pass+1))
  # 4a-wrong-cwd (#73): a REAL sha absent from the CWD repo is a DIRECTORY
  # mistake, not a phantom — the old message sent the operator hunting a
  # fabricated sha that had existed in the fork checkout all along. Refused rc 2
  # (a gate, not a data verdict) naming both directories. The probe stays
  # CWD-scoped on purpose: the push sends objects out of the CWD repo, so
  # accepting the sha here would ship from a foreign checkout and write
  # refs/oc-deploy/main into it.
  out="$(cd "$T/foreign" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_REPO="$T/repo" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; rc=$?
  check_rc "ship-wrong-cwd-rc" $rc 2
  check_has "ship-wrong-cwd-gate" "$out" "OC_DEPLOY_GATE=wrong-checkout"
  check_has "ship-wrong-cwd-names-cwd" "$out" "$T/foreign"
  check_has "ship-wrong-cwd-names-fork" "$out" "$T/repo"
  case "$out" in *"phantom?"*) fail=$((fail+1)); echo "SELFTEST FAIL: ship-wrong-cwd calls a real sha phantom";; *) pass=$((pass+1));; esac
  grep -q "PLAN: ship" <<<"$out" && { fail=$((fail+1)); echo "SELFTEST FAIL: wrong-cwd produced plan lines"; } || pass=$((pass+1))
  # 4a-wrong-cwd-CONTROL (#73): the SAME sha and the SAME OC_DEPLOY_REPO, run
  # from the repo that actually holds it, must be ADMITTED. Without this control
  # the arm above passes on a tool that refuses every ship from anywhere.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_REPO="$T/repo" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; rc=$?
  check_rc "ship-wrong-cwd-control-rc" $rc 0
  check_has "ship-wrong-cwd-control-plan" "$out" "would: git push"
  # 4a-no-repo (#73): a cwd with no git at all gets its own refusal — "not found
  # in this repo" is a lie when there is no repo.
  out="$(cd "$T/plain" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_REPO="$T/repo" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; rc=$?
  check_rc "ship-no-repo-rc" $rc 2
  check_has "ship-no-repo-gate" "$out" "not inside a git repository"
  # F-1 fusion (v0.4.97): plan-mode ship with --wait refuses (nothing to poll);
  # non-integer --wait dies 1 at validation.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git"     OC_DEPLOY_CARRIER="$SD/tools/carrier"     "$BUILD_BIN" ship --sha "$SHA2" --wait 30 2>&1)"; check_rc "ship-wait-refused" $? 2
  check_has "ship-wait-msg" "$out" "--wait on ship requires --execute"
  # C-A2 (lens C2 A2): rc-2 gate deaths carry machine-readable OC_DEPLOY_GATE
  # tokens — the retry loop branches on the token, not prose (>=10 manual
  # ship->validate->ship cycles in tools.log motivated this).
  check_has "ship-wait-gate-token" "$out" "OC_DEPLOY_GATE=wait-plan-mode"
  # ---- #176: the wait default is EXECUTE-ONLY -------------------------------
  # The regression this leg exists to catch: applying the 2700s default to EVERY
  # ship would make a bare `ship --sha S` (PLAN mode — the way every lane
  # rehearses a landing) die 2 wait-plan-mode on a flag nobody passed. Plan mode
  # must stay silent: rc 0, a plan, no default note, no poll. The refusal above
  # is what makes this leg FAST rather than hanging: a leaked default would die
  # at the gate instead of polling 2700s inside the suite.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_REPO="$T/repo" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; rc=$?
  check_rc "shipwait-plan-bare-rc" $rc 0
  check_has "shipwait-plan-bare-plan" "$out" "would: git push"
  case "$out" in
    *"defaulting to"*|*SHIP-WAIT*) fail=$((fail+1)); echo "SELFTEST FAIL: #176 wait default LEAKED into plan mode (a bare plan ship must never wait): $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-160)" ;;
    *) pass=$((pass+1)) ;;
  esac
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git"     OC_DEPLOY_CARRIER="$SD/tools/carrier"     "$BUILD_BIN" ship --sha "$SHA2" --notify-session aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa 2>&1)"; check_rc "ship-notify-refused" $? 2
  check_has "ship-notify-msg" "$out" "--notify-session is poll-mode only"
  check_has "ship-notify-gate-token" "$out" "OC_DEPLOY_GATE=notify-poll-only"
  # 4b. carrier read FAIL -> ship aborts (KERNEL D2: no silent fallback set)
  (cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier-fail" \
    "$BUILD_BIN" ship --sha "$SHA2" >/dev/null 2>&1); check_rc "carrier-fail-aborts" $? 2
  check_has "ship-plan-complete" "$SHIP_PLAN_OUT" "plan complete"
  if [ "$(git -C "$T/remote.git" rev-parse main)" != "$SHA2" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: plan mode mutated remote"; fi
  grep -q "ship-plan" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no ship-plan shadow row"; }
  # 4c. FEATURE-DEFAULT (HQ 2026-09-07, incident #125/d5863180): ship without
  # --features adopts deployed.meta.json features when the carrier default
  # disagrees; explicit mismatching --features refuses pre-dispatch rc 2.
  printf '{"prev_sha":"0000000000000000000000000000000000000000","features":"telegram,code-graph"}' > "$SD/deployed.meta.json"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; check_rc "featdef-adopt-rc" $? 0
  check_has "featdef-adopt-line" "$out" "adopting deployed set (FEATURE-DEFAULT)"
  check_has "featdef-adopt-features" "$out" "features=telegram,code-graph"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --features telegram 2>&1)"; check_rc "featdef-mismatch-rc" $? 2
  check_has "featdef-mismatch-msg" "$out" "refusing pre-dispatch"
  grep -q "features-mismatch-refused" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no features-mismatch-refused shadow row"; }
  grep -q "PLAN: ship" <<<"$out" && { fail=$((fail+1)); echo "SELFTEST FAIL: mismatch reached plan lines"; } || pass=$((pass+1))
  # matching explicit set passes the gate (order-insensitive compare)
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --features code-graph,telegram 2>&1)"; check_rc "featdef-match-reorder-rc" $? 0
  # 4d. #108 (2026-11-20, toolsmith): the pre-dispatch gate is DROP-ONLY,
  # mirroring the features-compat gate in swap_execute() that it precedes.
  # A carrier default or an explicit --features that ADDS a feature over the
  # deployed set must proceed; only a DROP is the failure class. The three 4c
  # arms above stay DROP cases (carrier stub 'telegram' vs deployed
  # 'telegram,code-graph') and must keep failing — this block adds the
  # ADDITION direction, which the old symmetric compare refused outright.
  printf '#!/usr/bin/env bash\necho telegram,code-graph,eval\n' > "$SD/tools/carrier-superset"; chmod +x "$SD/tools/carrier-superset"
  # (a) POSITIVE CONTROL: an explicit superset proceeds and reaches the plan
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier-superset" \
    "$BUILD_BIN" ship --sha "$SHA2" --features telegram,code-graph,eval 2>&1)"; check_rc "featadd-explicit-rc" $? 0
  check_has "featadd-explicit-line" "$out" "adding feature(s) eval"
  check_has "featadd-explicit-features" "$out" "features=telegram,code-graph,eval"
  grep -q "features-add-adopted:eval" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no features-add-adopted shadow row"; }
  # (b) an explicit SUBSET still refuses pre-dispatch (the drop direction is not
  # weakened by the addition fix)
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier-superset" \
    "$BUILD_BIN" ship --sha "$SHA2" --features telegram 2>&1)"; check_rc "featadd-subset-rc" $? 2
  check_has "featadd-subset-msg" "$out" "DROPS deployed feature(s): code-graph"
  # (c) --allow-features-drop is honoured PRE-DISPATCH, not only at the swap gate
  # — a deliberate drop must not be refused one stage before the stage permitting it
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier-superset" \
    "$BUILD_BIN" ship --sha "$SHA2" --features telegram --allow-features-drop 2>&1)"; check_rc "featdrop-allowed-rc" $? 0
  check_has "featdrop-allowed-line" "$out" "dropping deployed feature(s) code-graph deliberately"
  # (d) OMITTED --features adopts the carrier SUPERSET — NOT rewritten back to
  # the deployed set. That rewrite was the defect: it made the carrier default
  # structurally unable to add a feature, so `eval` could never reach the binary.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier-superset" \
    "$BUILD_BIN" ship --sha "$SHA2" 2>&1)"; check_rc "featadd-default-rc" $? 0
  check_has "featadd-default-features" "$out" "features=telegram,code-graph,eval"
  rm -f "$SD/tools/carrier-superset"   # restore pre-case state for later sections
  rm -f "$SD/deployed.meta.json"   # restore pre-case state for later sections

  # 5a. ship plan non-FF -> exit 2 (plan mode does not auto-rebase)
  git -C "$T/repo" checkout -qb div5a HEAD~1
  echo div > "$T/repo/f3"; git -C "$T/repo" add f3; git -C "$T/repo" commit -qm div
  git -C "$T/repo" push -q -f "$T/remote.git" HEAD:refs/heads/main
  (cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" >/dev/null 2>&1); check_rc "ship-plan-nonff" $? 2

  # 5b. ship execute non-FF with conflict -> exit 5 (rebase-conflict)
  git -C "$T/repo" checkout -qb div5b HEAD~1
  echo "conflict-f2" > "$T/repo/f2"; git -C "$T/repo" add f2; git -C "$T/repo" commit -qm conflict5b
  git -C "$T/repo" push -q -f "$T/remote.git" HEAD:refs/heads/main
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 2>&1)"; rc=$?
  check_rc "ship-nonff-conflict-rc" $rc 5
  check_has "ship-nonff-conflict-token" "$out" "OC_DEPLOY_GATE=rebase-conflict"

  # 5c. ship execute non-FF clean -> auto-rebase + audit + push
  git -C "$T/repo" checkout -qb div5c HEAD~1
  echo "clean-side" > "$T/repo/f_clean"; git -C "$T/repo" add f_clean; git -C "$T/repo" commit -qm clean5c
  git -C "$T/repo" push -q -f "$T/remote.git" HEAD:refs/heads/main
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 2>&1)"; rc=$?
  check_rc "ship-nonff-autorebase-rc" $rc 0
  check_has "ship-nonff-autorebase-msg" "$out" "auto-rebased"

  # 5d-f. #704: the fork-main tip is read from refs/oc-deploy/main — the DEDICATED
  #   ref this tool's own fetch writes — NEVER from FETCH_HEAD, which is ONE shared
  #   mutable file per repo that ANY concurrent fetch rewrites (oc-gate fetches
  #   ci/quick-build-linux, harvest lanes fetch upstream). Measured 2026-09-29
  #   08:33Z, chain oc-ship-702-082945: FETCH_HEAD held ci/quick-build-linux, the
  #   tip read was upstream main, and a clean FF was auto-rebased onto the wrong
  #   base (four files the commit never touched conflicted; rc 5 was the GOOD
  #   outcome — a completed replay would have pushed upstream history to fork main).
  git init -q --bare -b main "$T/r704.git"
  git init -q -b main "$T/r704"
  git -C "$T/r704" config user.email t@t; git -C "$T/r704" config user.name t
  echo a > "$T/r704/a"; git -C "$T/r704" add a; git -C "$T/r704" commit -qm a
  echo b > "$T/r704/b"; git -C "$T/r704" add b; git -C "$T/r704" commit -qm b
  echo c > "$T/r704/c"; git -C "$T/r704" add c; git -C "$T/r704" commit -qm c
  TIP_C="$(git -C "$T/r704" rev-parse HEAD)"; TIP_B="$(git -C "$T/r704" rev-parse HEAD~1)"
  git -C "$T/r704" push -q "$T/r704.git" HEAD:refs/heads/main          # remote main = TIP_C
  # a divergent, NON-ancestor tip (criterion b's foreign tip)
  git -C "$T/r704" checkout -q -b diverged "$TIP_B"
  echo d > "$T/r704/d"; git -C "$T/r704" add d; git -C "$T/r704" commit -qm d
  TIP_D="$(git -C "$T/r704" rev-parse HEAD)"
  git -C "$T/r704" checkout -q main
  git -C "$T/r704" fetch -q "$T/r704.git" "+$TIP_D:refs/heads/diverged" 2>/dev/null || true
  # (c) the resolved tip is the dedicated ref, NOT the clobbered FETCH_HEAD
  git -C "$T/r704" update-ref refs/oc-deploy/main "$TIP_C"
  git -C "$T/r704" fetch -q "$T/r704.git" "+$TIP_B:refs/heads/clobber1" 2>/dev/null || true   # FETCH_HEAD = TIP_B
  RESOLVED="$(cd "$T/r704" && resolve_main_tip)"
  [ "$RESOLVED" = "$TIP_C" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #704 resolve_main_tip read FETCH_HEAD ($RESOLVED), not refs/oc-deploy/main ($TIP_C)"; }
  # positive control: the fixture really did clobber FETCH_HEAD (else the leg is vacuous)
  [ "$(git -C "$T/r704" rev-parse FETCH_HEAD)" = "$TIP_B" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #704 fixture did not clobber FETCH_HEAD"; }
  # fallback: with the dedicated ref absent, FETCH_HEAD is still used
  git -C "$T/r704" update-ref -d refs/oc-deploy/main
  [ "$(cd "$T/r704" && resolve_main_tip)" = "$TIP_B" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #704 resolve_main_tip did not fall back to FETCH_HEAD"; }
  # containment predicate — the REMOTE's own declaration is the authority
  ( cd "$T/r704" && tip_is_fork_main "$TIP_C" "$T/r704.git" ) && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #704 tip_is_fork_main rejected the remote's own main"; }
  ( cd "$T/r704" && tip_is_fork_main "$TIP_D" "$T/r704.git" ) && { fail=$((fail+1)); echo "SELFTEST FAIL: #704 tip_is_fork_main accepted a foreign tip"; } || pass=$((pass+1))
  # (a) with FETCH_HEAD clobbered by a foreign fetch, a clean-FF ship reports FF ok
  #     and does NOT rebase. The fetch is FROZEN (OC_DEPLOY_FETCH stub) to reproduce
  #     the post-fetch/pre-read race deterministically: a live fetch would rewrite
  #     FETCH_HEAD and the window cannot be won on purpose from a test.
  git -C "$T/r704" update-ref refs/oc-deploy/main "$TIP_C"
  git -C "$T/r704" fetch -q "$T/r704.git" "+$TIP_B:refs/heads/clobber2" 2>/dev/null || true   # FETCH_HEAD = TIP_B
  out="$(cd "$T/r704" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/r704.git" \
    OC_DEPLOY_FETCH=/bin/true OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$TIP_C" 2>&1)"; rc=$?
  check_rc "704-ffok-under-clobber-rc" $rc 0
  check_has "704-tip-from-ref" "$out" "fork main tip = $TIP_C"
  check_has "704-ffok-under-clobber-msg" "$out" "FF ok"
  grep -q "auto-rebase" <<<"$out" && { fail=$((fail+1)); echo "SELFTEST FAIL: #704 rebased under a clobbered FETCH_HEAD"; } || pass=$((pass+1))
  # (b) refs/oc-deploy/main AND FETCH_HEAD both at a NON-ancestor -> resolution-class
  #     refusal BEFORE git rebase (without the containment leg this reached
  #     rebase-needed, i.e. the tool would have started a rebase onto a foreign tip)
  git -C "$T/r704" update-ref refs/oc-deploy/main "$TIP_D"
  out="$(cd "$T/r704" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/r704.git" \
    OC_DEPLOY_FETCH=/bin/true OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$TIP_C" 2>&1)"; rc=$?
  check_rc "704-foreign-tip-refused-rc" $rc 2
  check_has "704-foreign-tip-gate-token" "$out" "OC_DEPLOY_GATE=tip-not-fork-main"
  grep -q "auto-rebase\|rebase-needed" <<<"$out" && { fail=$((fail+1)); echo "SELFTEST FAIL: #704 reached the rebase path with a foreign tip"; } || pass=$((pass+1))

  # 6. ship execute end-to-end: restore FF remote, fake gh + stub validate
  git -C "$T/repo" checkout -q -B main "$SHA2"
  git -C "$T/repo" push -q -f "$T/remote.git" HEAD~1:refs/heads/main   # back to c1
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 2>&1)"; rc=$?
  check_rc "ship-exec-rc" $rc 0
  check_has "ship-exec-gates" "$out" "4/4 PASS"
  check_has "ship-exec-dispatch" "$out" "dispatched carrier run"
  if [ "$(git -C "$T/remote.git" rev-parse main)" = "$SHA2" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: main not pushed"; fi
  grep -q "workflow run" "$GH_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: gh dispatch not called"; }
  grep -q "dispatched" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no dispatched shadow row"; }
  # 6b. F-1 fusion (v0.4.97): ship --execute --wait N bounded-polls the run we
  #     just dispatched. Stub env: OC_TEST_SHIPWAIT_HEAD=the shipped sha (run
  #     555 head matches), OC_TEST_SHIPWAIT_CONCL=completed/success -> GREEN
  #     rc 0. Interval override keeps the loop tight.
  printf 'zzz\n' > "$T/shipwait-flag"   # marker: flag file present = fusion active
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="$SHA2" OC_TEST_SHIPWAIT_CONCL=completed-success \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 5 2>&1)"; rc=$?
  check_rc "shipwait-green-rc" $rc 0
  check_has "shipwait-green-line" "$out" "SHIP-WAIT: run 555 GREEN"
  grep -q "ship-wait-green:555" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no ship-wait-green shadow row"; }
  # 6c. RED within the window: terminal failure -> rc 6, no swap leg.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="$SHA2" OC_TEST_SHIPWAIT_CONCL=completed-failure \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 5 2>&1)"; rc=$?
  check_rc "shipwait-red-rc" $rc 6
  check_has "shipwait-red-line" "$out" "terminal-failure"
  grep -q "ship-wait-red:555:failure" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no ship-wait-red shadow row"; }
  # 6d. timeout: run never terminal within --wait 2 -> rc 5.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="$SHA2" OC_TEST_SHIPWAIT_CONCL=in_progress \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 2 2>&1)"; rc=$?
  check_rc "shipwait-timeout-rc" $rc 5
  check_has "shipwait-timeout-line" "$out" "never reached a terminal state"
  grep -q "ship-wait-timeout" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no ship-wait-timeout shadow row"; }
  # 6e. wrong-sha run ignored: run head is a DIFFERENT sha -> our run never
  #     "exists" -> rc 5 timeout even though a completed run is visible.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="9999999999999999999999999999999999999999" OC_TEST_SHIPWAIT_CONCL=completed-success \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 2 2>&1)"; check_rc "shipwait-wrongsha-rc" $? 5
  rm -f "$T/shipwait-flag"
  # ---- #176: THE EXECUTE-ONLY WAIT DEFAULT (HQ ruling 2026-11-25) ----------
  # The role files restated `--wait 2700` on every ship because the parser had
  # no default: an --execute ship returned the instant it dispatched, so a lane
  # that forgot the flag left the run unwatched. The default now lives in
  # oc-build, under --execute ONLY.
  # 6f is the DISCRIMINATOR: no --wait, no env escape -> the ship must POLL.
  # Pre-#176 this leg sees no SHIP-WAIT line and reddens.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="$SHA2" OC_TEST_SHIPWAIT_CONCL=completed-success \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute 2>&1)"; rc=$?
  check_rc "shipwait-default-rc" $rc 0
  check_has "shipwait-default-line" "$out" "SHIP-WAIT: run 555 GREEN"
  check_has "shipwait-default-note" "$out" "defaulting to 2700s"
  check_has "shipwait-default-names-escape" "$out" "OC_BUILD_WAIT=0"
  # 6g. THE ESCAPE: OC_BUILD_WAIT=0 on the same bare --execute ship dispatches
  #     and RETURNS. Without this leg the default could be made UNESCAPABLE and
  #     every other leg here would still pass.
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_BUILD_WAIT=0 OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="$SHA2" OC_TEST_SHIPWAIT_CONCL=completed-success \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute 2>&1)"; rc=$?
  check_rc "shipwait-env0-rc" $rc 0
  check_has "shipwait-env0-note" "$out" "OC_BUILD_WAIT=0 applies"
  check_has "shipwait-env0-dispatched" "$out" "dispatched carrier run"
  case "$out" in
    *SHIP-WAIT*) fail=$((fail+1)); echo "SELFTEST FAIL: OC_BUILD_WAIT=0 did NOT restore fire-and-forget (ship still polled)" ;;
    *) pass=$((pass+1)) ;;
  esac
  # 6h. EXPLICIT --wait BEATS the env escape: --wait 5 with OC_BUILD_WAIT=0 must
  #     still poll (the escape names the DEFAULT, never the operator's flag).
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_BUILD_WAIT=0 OC_DEPLOY_POLL_INTERVAL=1 OC_TEST_SHIPWAIT_HEAD="$SHA2" OC_TEST_SHIPWAIT_CONCL=completed-success \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 5 2>&1)"; rc=$?
  check_rc "shipwait-explicit-beats-env-rc" $rc 0
  check_has "shipwait-explicit-beats-env-line" "$out" "SHIP-WAIT: run 555 GREEN"
  # 6i. a non-integer OC_BUILD_WAIT dies 1 AT THE BOUNDARY, before any dispatch
  #     (a typo must not reach the wait loop as an arithmetic error).
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_BUILD_WAIT=abc "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute 2>&1)"; rc=$?
  check_rc "shipwait-env-bad-rc" $rc 1
  check_has "shipwait-env-bad-msg" "$out" "OC_BUILD_WAIT needs an integer"
  case "$out" in
    *"dispatched carrier run"*) fail=$((fail+1)); echo "SELFTEST FAIL: a bad OC_BUILD_WAIT still DISPATCHED (validation must precede the push/dispatch)" ;;
    *) pass=$((pass+1)) ;;
  esac
  # 7. ship execute gate-fail -> exit 2 (validator stub exits 2; push is no-op)
  (cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-fail" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 >/dev/null 2>&1); check_rc "ship-gate-fail" $? 2
  grep -q "gate-fail" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no gate-fail shadow row"; }

  # 7b. #355 GATE-BEFORE-LAND: the push leg refuses an ungated landing.
  #     The remote is first moved BEHIND the sha, so "did not push" can
  #     actually FAIL — a guard arm whose negative cannot redden is vacuous.
  R_TIP_ORIG="$(git -C "$T/remote.git" rev-parse refs/heads/main 2>/dev/null || echo none)"
  git -C "$T/repo" push -q -f "$T/remote.git" "$SHA2~1:refs/heads/main"
  R_TIP_BEFORE="$(git -C "$T/remote.git" rev-parse refs/heads/main 2>/dev/null)"
  rm -f "$SD/oc-deploy-shadow.log"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --execute --wait 0 2>&1)"; rc=$?
  check_rc "gate-missing-refused-rc" $rc 2
  check_has "gate-missing-refused-token" "$out" "OC_DEPLOY_GATE=gate-missing"
  [ "$(git -C "$T/remote.git" rev-parse refs/heads/main 2>/dev/null)" = "$R_TIP_BEFORE"  ]\
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: gate-missing-did-not-push: remote main MOVED on a refused landing"; }

  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --execute --wait 0 --gated-run 444 2>&1)"; rc=$?
  check_rc "gate-inflight-refused-rc" $rc 2
  check_has "gate-inflight-refused-token" "$out" "OC_DEPLOY_GATE=gate-inflight"
  [ "$(git -C "$T/remote.git" rev-parse refs/heads/main 2>/dev/null)" = "$R_TIP_BEFORE"  ]\
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: gate-inflight-did-not-push: remote main MOVED on an in-flight gate"; }

  (cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --execute --wait 0 --gated-run 888 >/dev/null 2>&1); check_rc "gate-red-refused-rc" $? 2

  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --execute --wait 0 --gated-run 777 2>&1)"; rc=$?
  check_rc "gate-green-allowed-rc" $rc 0
  [ "$(git -C "$T/remote.git" rev-parse refs/heads/main 2>/dev/null)" = "$SHA2"  ]\
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: gate-green-did-push: a GREEN-gated landing did NOT reach remote main"; }

  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --execute --wait 0 --allow-ungated-push "selftest: exercising the audited escape hatch" 2>&1)"; rc=$?
  check_rc "gate-override-allowed-rc" $rc 0
  check_has "gate-override-is-loud" "$out" "UNGATED PUSH OVERRIDE"
  (cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val-ok" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --execute --wait 0 --allow-ungated-push "" >/dev/null 2>&1); check_rc "gate-override-needs-justification-rc" $? 2

  if [ "$R_TIP_ORIG" != "none" ]; then
    git -C "$T/repo" push -q -f "$T/remote.git" "$R_TIP_ORIG:refs/heads/main" 2>/dev/null || true
  fi
  rm -f "$SD/oc-deploy-shadow.log"
  # 8. poll plan mode at S0: swap LOCKED, sha decoded from the build job name
  #    (jobs[0] here is an ORDER gates job with NO sha at all — nothing decodes)
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" "$STATUS_BIN" poll 2>&1)"; rc=$?
  check_rc "poll-plan-rc" $rc 0
  check_has "poll-decodes-sha" "$out" "built sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  check_has "poll-swap-locked" "$out" "swap LOCKED"
  # 8b. #85: inside the poll WINDOW an unreadable API is "not yet", not a
  #     verdict. The defect: ONE `gh api` blip on poll #1 killed a chain whose
  #     swap had already completed (measured run 44420005606 — rc=2 while
  #     deployed.sha AND the installed binary were both the verified sha), so
  #     LEG5's 12 polls of tolerance bought nothing. Fixture fails twice then
  #     answers; with TRIES=3 the SAME iteration must recover.
  : > "$T/api-counter-a"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh-api-flaky" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_TEST_API_COUNTER="$T/api-counter-a" OC_TEST_API_FAIL_N=2 \
    OC_DEPLOY_POLL_API_TRIES=3 OC_DEPLOY_POLL_API_BACKOFF=0 \
    "$STATUS_BIN" poll --wait 60 2>&1)"; rc=$?
  check_rc "poll-api-blip-tolerated-rc" $rc 0
  check_has "poll-api-blip-recovers" "$out" "built sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  # 8c. NEGATIVE CONTROL — and the reason this fix is not a silent green. An
  #     API that NEVER answers must still be RED: rc 0 here would mean the
  #     tolerance had converted a genuine failure into a pass.
  : > "$T/api-counter-b"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh-api-flaky" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_TEST_API_COUNTER="$T/api-counter-b" \
    OC_DEPLOY_POLL_API_TRIES=3 OC_DEPLOY_POLL_API_BACKOFF=0 \
    "$STATUS_BIN" poll --wait 0 2>&1)"; rc=$?
  check_rc "poll-api-dead-still-red-rc" $rc 2
  # 8d. gh's own words survive. The old `2>/dev/null` discarded them, so the
  #     message named a cause nobody had measured.
  check_has "poll-api-dead-keeps-stderr" "$out" "HTTP 502"
  check_has "poll-api-dead-counts-tries" "$out" "after 3 tries"
  # 8e. and LOCAL host state rides along, so a reader can tell "the swap never
  #     happened" from "the swap happened and the poll could not see it".
  check_has "poll-api-dead-carries-host-state" "$out" "host: deployed.sha="
  # 9. poll at S2: stage fixture (consent gate retired 2026-08-28 — GREEN run
  #    + artifact verify is the authorization now)
  printf '{"meta":{"oc_deploy_stage":"S2"}}' > "$SD/workers-ledger.json"
  # 10. poll at S2, --execute -> HANDOFF to launch stub (Phase A
  #     exits pre-bounce); backup listed explicitly in the plan line
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_SWAP_INFLIGHT_LISTER=/bin/true OC_SWAP_LAUNCH="$SD/launch" "$STATUS_BIN" poll --execute 2>&1)"; rc=$?
  check_rc "poll-handoff-rc" $rc 0
  check_has "poll-handoff" "$out" "HANDOFF"
  check_has "poll-plan-backup" "$out" "backup"
  grep -q "swap-execute --sha aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "$T/launch.log" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: launch stub not called with swap-execute"; }
  grep -q -- "--features telegram" "$T/launch.log" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: carrier-resolved features not handed to swap"; }
  # 10-bin. factory#145: the handoff must launch the RECEIVER, not $SELF. The stub
  #     records its whole argv (`launch $*`), so the collected path was always
  #     right there in the log -- and until this arm existed NOTHING asserted it.
  #     `oc-deploy` execs into oc-status, the lib's SELF resolves to oc-status, so
  #     12 units were launched as `oc-status swap-execute` (dying on oc-status's own
  #     `unknown arg` arm) and this selftest stayed green because it grepped the
  #     ARGS and never the binary.
  grep -qE -- '--collect [^ ]*/oc-swap swap-execute' "$T/launch.log" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: handoff launched the WRONG binary (want .../ship/oc-swap, got: $(grep -o -- '--collect [^ ]*' "$T/launch.log" 2>/dev/null | head -1))"; }
  grep -q "handed-off" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no handed-off shadow row"; }
  # 10a. #729: in-flight guard — a LIVE oc-swap unit for THIS sha must stop a
  #      duplicate handoff (LEG5 loops faster than deployed.sha flips; the
  #      measured defect armed 3 units for ONE run). Control below: a live unit
  #      for a DIFFERENT sha must NOT block — the guard keys on the sha.
  printf '#!/usr/bin/env bash\necho oc-swap-aaaaaaaa-1790817190.service\n' > "$SD/inflight-live"; chmod +x "$SD/inflight-live"
  L_BEFORE="$(grep -c 'swap-execute' "$T/launch.log" 2>/dev/null || true)"; L_BEFORE="${L_BEFORE:-0}"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_SWAP_INFLIGHT_LISTER="$SD/inflight-live" OC_SWAP_LAUNCH="$SD/launch" \
    "$STATUS_BIN" poll --execute 2>&1)"; rc=$?
  check_rc "poll-inflight-rc" $rc 0
  check_has "poll-inflight-msg" "$out" "already in flight"
  L_AFTER="$(grep -c 'swap-execute' "$T/launch.log" 2>/dev/null || true)"; L_AFTER="${L_AFTER:-0}"
  [ "$L_AFTER" = "$L_BEFORE" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #729 in-flight guard still armed a duplicate (launch swap-execute calls $L_BEFORE -> $L_AFTER)"; }
  grep -q "inflight" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #729 no inflight shadow row"; }
  # 10a-neg: a live unit for ANOTHER sha must NOT block this handoff (control)
  printf '#!/usr/bin/env bash\necho oc-swap-bbbbbbbb-1790817190.service\n' > "$SD/inflight-other"; chmod +x "$SD/inflight-other"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_SWAP_INFLIGHT_LISTER="$SD/inflight-other" OC_SWAP_LAUNCH="$SD/launch" \
    "$STATUS_BIN" poll --execute 2>&1)"; rc=$?
  check_rc "poll-inflight-other-rc" $rc 0
  check_has "poll-inflight-other-handoff" "$out" "HANDOFF"
  # 10a-bus. #48 defect 3: the handoff PROBES the user bus BEFORE arming.
  #      The discriminating pair differs in ONE variable -- the launcher's exit
  #      code -- so a leg that passes on a broken probe cannot hide behind a
  #      different fixture. The probe is the launcher's own bus path, and the
  #      fake records argv so "nothing was armed" is a receipt, not a claim.
  mkdir -p "$T/busbin"; : > "$T/bus.log"
  printf '#!/usr/bin/env bash\necho "$*" >> "%s"\nexit 1\n' "$T/bus.log" > "$T/busbin/systemd-run"; chmod +x "$T/busbin/systemd-run"
  out="$(PATH="$T/busbin:$PATH" OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_SWAP_INFLIGHT_LISTER=/bin/true "$STATUS_BIN" poll --execute 2>&1)"; rc=$?
  check_rc "poll-bus-unreachable-rc" $rc 4
  check_has "poll-bus-unreachable-names-bus" "$out" "user bus unreachable"
  check_has "poll-bus-unreachable-says-nothing-touched" "$out" "nothing was touched"
  grep -q -- "--unit=" "$T/bus.log" && { fail=$((fail+1)); echo "SELFTEST FAIL: #48 bus refusal still ARMED a unit"; } || pass=$((pass+1))
  grep -q -- "--scope --collect /bin/true" "$T/bus.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #48 no probe invocation recorded"; }
  grep -q "launch-preflight-no-user-bus" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #48 no bus-preflight shadow row"; }
  # 10a-bus-ok. POSITIVE CONTROL: same fixture, launcher exits 0 -> the handoff
  #      must proceed and arm a unit. Without this the refusal leg above would
  #      pass against a tool that refused EVERY handoff.
  : > "$T/bus.log"
  printf '#!/usr/bin/env bash\necho "$*" >> "%s"\nexit 0\n' "$T/bus.log" > "$T/busbin/systemd-run"; chmod +x "$T/busbin/systemd-run"
  out="$(PATH="$T/busbin:$PATH" OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_SWAP_INFLIGHT_LISTER=/bin/true "$STATUS_BIN" poll --execute 2>&1)"; rc=$?
  check_rc "poll-bus-reachable-rc" $rc 0
  check_has "poll-bus-reachable-handoff" "$out" "HANDOFF"
  grep -q -- "--unit=" "$T/bus.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #48 probe passed but no handoff unit was armed"; }
  # 10a-bus-override. An EXPLICIT OC_SWAP_LAUNCH is the operator's own choice and
  #      is NOT probed -- the fake systemd-run below is dead, and the handoff
  #      must still proceed through the named stub.
  printf '#!/usr/bin/env bash\nexit 1\n' > "$T/busbin/systemd-run"; chmod +x "$T/busbin/systemd-run"
  out="$(PATH="$T/busbin:$PATH" OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_SWAP_INFLIGHT_LISTER=/bin/true OC_SWAP_LAUNCH="$SD/launch" "$STATUS_BIN" poll --execute 2>&1)"; rc=$?
  check_rc "poll-bus-probe-skipped-on-override-rc" $rc 0
  check_has "poll-bus-probe-skipped-on-override-handoff" "$out" "HANDOFF"

  # 10b. C-#2: poll --wait with nothing new -> timeout rc 5 + notify wake
  printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' > "$SD/deployed.sha"
  : > "$T/notify.log"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_NOFANOUT=1 OC_DEPLOY_POLL_INTERVAL=0 OC_DEPLOY_NOTIFY="$SD/notify" \
    "$STATUS_BIN" poll --wait 1 --notify-session aaaaaaaa-1111-2222-3333-444444444444 2>&1)"; rc=$?
  check_rc "poll-wait-timeout-rc" $rc 5
  check_has "poll-wait-timeout-msg" "$out" "timed out"
  grep -q "timed out" "$T/notify.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: poll --wait timeout did not notify session"; }
  # 10b-bis (#74 FM-2): deferred wake refused (rc 2, mid-turn target) -> retry
  # ONCE with --interrupt inside notify_session; wake must land, no "wake
  # FAILED" stderr, exactly 2 verb calls with --interrupt on the second.
  cat > "$SD/notify-flaky" <<'NSTUB2'
#!/usr/bin/env bash
echo "$*" >> "${FLAKY_LOG:?}"
if [ -f "${FLAKY_LOG}.count" ]; then N="$(cat "${FLAKY_LOG}.count")"; else N=0; fi
N=$((N+1)); printf '%s' "$N" > "${FLAKY_LOG}.count"
[ "$N" -le 1 ] && exit 3
exit 0
NSTUB2
  chmod +x "$SD/notify-flaky"
  export FLAKY_LOG="$T/notify-flaky.log"; : > "$FLAKY_LOG"; rm -f "$FLAKY_LOG.count"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_NOFANOUT=1 OC_DEPLOY_POLL_INTERVAL=0 OC_DEPLOY_NOTIFY="$SD/notify-flaky" \
    "$STATUS_BIN" poll --wait 1 --notify-session aaaaaaaa-1111-2222-3333-444444444444 2>&1)"; rc=$?
  check_rc "poll-flaky-wake-rc" $rc 5
  case "$out" in *"wake FAILED"*) fail=$((fail+1)); echo "SELFTEST FAIL: refused wake not recovered by --interrupt retry";; *) pass=$((pass+1));; esac
  [ "$(wc -l < "$FLAKY_LOG")" -eq 2 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: expected exactly 2 verb calls (refusal + interrupt retry), got $(wc -l < "$FLAKY_LOG")"; }
  [ "$(sed -n 2p "$FLAKY_LOG" | grep -c -- '--interrupt')" -eq 1 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: second verb call lacks --interrupt"; }
  # 10c. C-#2: --wait 0 keeps the classic single-pass "nothing to do" rc 0
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_NOFANOUT=1 "$STATUS_BIN" poll --wait 0 2>&1)"; rc=$?
  check_rc "poll-wait0-rc" $rc 0
  check_has "poll-wait0-noop" "$out" "nothing to do"
  # 10e. #63 (v0.4.79): stale FIRST run skipped, older decodable run wins
  out="$(OC_TEST_STALE_FIRST=1 OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_NOFANOUT=1 "$STATUS_BIN" poll --wait 0 2>&1)"; rc=$?
  check_rc "poll-stale-first-rc" $rc 0
  check_has "poll-stale-skip-note" "$out" "skip run 999"
  check_has "poll-stale-picks-111" "$out" "nothing to do: aaaaaaaa"
  # 10f. #63 family (v0.4.79): fanout decode-fail -> rc 3, marked, idempotent on retry
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_NOTIFY="$SD/notify" \
    "$FANOUT_BIN" fanout --run 998 2>&1)"; rc=$?
  check_rc "fanout-decode-fail-rc" $rc 3
  # (#932 criterion 2, half A) The GENUINELY-undecodable run must read as a fact
  # about the RUN: rc 3, marked, and the text must NOT mention the decoder library
  # (10f-ter is the other half — a missing library is rc 2 and says so). Asserting
  # the absence of the library token here is what makes the pair discriminate: if
  # a future edit let the rc-3 arm mention oc-embed.sh again, an operator could no
  # longer tell "restore your checkout" from "this run carries no sha".
  check_has "fanout-decode-fail-says-run" "$out" "no job name decodes"
  case "$out" in *oc-embed.sh*) fail=$((fail+1)); echo "SELFTEST FAIL: #932 criterion 2 -- the undecodable-RUN arm names the decoder library, so its text no longer differs from the missing-library arm";; *) pass=$((pass+1));; esac
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_NOTIFY="$SD/notify" \
    "$FANOUT_BIN" fanout --run 998 2>&1)"; rc=$?
  check_rc "fanout-998-retry-rc" $rc 0
  check_has "fanout-998-retry-idempotent" "$out" "reason=done"
  # 10f-bis. #84: an UNREADABLE jobs list is TRANSIENT — rc 3 unchanged (the
  # contract's fan-out-infrastructure code) but NOT marked, so the next scan
  # retries instead of the range's attribution being buried forever.
  # The pair with 10f IS the assertion: 998 was READ and carries no sha
  # (permanent -> marked); 997 could not be READ (transient -> unmarked).
  # Without 10f still passing, "never marks" would pass vacuously.
  : > "$T/gh84.log"
  out="$(GH_LOG="$T/gh84.log" OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_NOTIFY="$SD/notify" \
    "$FANOUT_BIN" fanout --run 997 2>&1)"; rc=$?
  check_rc "fanout-unreadable-rc" $rc 3
  check_has "fanout-unreadable-note" "$out" "cannot READ the jobs list"
  if jq -e '.runs["997"]' "$SD/fanout.state" >/dev/null 2>&1; then
    fail=$((fail+1)); echo "SELFTEST FAIL: #84 an unreadable jobs list was MARKED done — a gh blip became a permanent, silent loss of attribution"
  else
    pass=$((pass+1))
  fi
  n1="$(grep -c 'actions/runs/997/jobs' "$T/gh84.log" 2>/dev/null || true)"
  out="$(GH_LOG="$T/gh84.log" OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_NOTIFY="$SD/notify" \
    "$FANOUT_BIN" fanout --run 997 2>&1)"; rc=$?
  check_rc "fanout-unreadable-retry-rc" $rc 3
  n2="$(grep -c 'actions/runs/997/jobs' "$T/gh84.log" 2>/dev/null || true)"
  [ "${n2:-0}" -gt "${n1:-0}" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #84 the retry did not re-read the jobs list (n1=${n1:-0} n2=${n2:-0}) — it was answered idempotent"; }
  # 10f-ter. (#932 criterion 1 + criterion 2 half B) A MISSING lib/oc-embed.sh is
  # a fault of THIS BOX, not a statement about the run. Before the guard, the bare
  # `[ -f ] && source` left oc_decode_job_sha_any UNDEFINED, the `|| continue` at
  # the decode loop ate the rc 127, and run_built_sha returned 3 — PERMANENT "the
  # jobs list was READ and carries no sha" — so fanout MARKED the run and its
  # attribution was lost with no diagnostic naming the library.
  # The pair with 10f IS the assertion (criterion 2): 998 was READ and carries no
  # sha -> rc 3, marked, text about the RUN; a missing decoder -> rc 2, NOT marked,
  # text naming the CHECKOUT. Different rc AND different text, asserted from both
  # sides. Run 995 is used, not 998, because 10f already marked 998 and the
  # idempotence guard would answer first.
  local ND="$T/noembed"
  mkdir -p "$ND/tools/lib" "$ND/tools/ship"
  # #168 cut 5: the sandbox needs the stage tools and the shared body, not a
  # dispatcher — the child below IS oc-fanout, the tool that owns the decoder
  # call. oc-embed.sh is the ONE library deliberately left out of this tree, so
  # a missing decoder stays the only difference between it and the real tree.
  cp "$OC_TOOLS_DIR"/ship/oc-build "$OC_TOOLS_DIR"/ship/oc-swap \
     "$OC_TOOLS_DIR"/ship/oc-fanout "$OC_TOOLS_DIR"/ship/oc-status "$ND/tools/ship/"
  cp "$OC_TOOLS_DIR/lib/oc-deploy-lib.sh" "$ND/tools/lib/" 2>/dev/null || true
  cp "$OC_TOOLS_DIR/lib/oc-log.sh" "$ND/tools/lib/" 2>/dev/null || true
  cp "$OC_TOOLS_DIR/lib/oc-notify.sh" "$ND/tools/lib/" 2>/dev/null || true
  # The GH_LOG assertion below is what pins the ORDERING: the guard must answer
  # BEFORE any DECODER-NEEDING call, so a network blip cannot be reported as the
  # cause while the broken checkout goes unnamed. The run-metadata fetch is allowed
  # (it is what tells us success-vs-red, and red needs no decoder); the /jobs fetch
  # is not, because that is the first call oc_decode_job_sha_any is needed for.
  : > "$T/gh995.log"
  out="$(GH_LOG="$T/gh995.log" OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_NOTIFY="$SD/notify" \
    "$ND/tools/ship/oc-fanout" fanout --run 995 2>&1)"; rc=$?
  check_rc "fanout-noembed-rc" $rc 2
  check_has "fanout-noembed-names-lib" "$out" "oc-embed.sh"
  check_has "fanout-noembed-not-an-absent-sha" "$out" "NOT marked done"
  check_has "fanout-noembed-names-checkout" "$out" "broken LOCAL TOOL TREE"
  check_has "fanout-noembed-escape-hatch" "$out" "OC_DEPLOY_ENV=missing-embed-lib"
  if grep -q '/jobs' "$T/gh995.log" 2>/dev/null; then
    fail=$((fail+1)); echo "SELFTEST FAIL: #932 the missing-library guard ran AFTER the jobs fetch — a network blip would be reported as the cause and the broken checkout would go unnamed"
  else
    pass=$((pass+1))
  fi
  case "$out" in *"no job name decodes"*) fail=$((fail+1)); echo "SELFTEST FAIL: #932 criterion 2 -- the missing-library arm uses the undecodable-RUN phrasing, so rc 2 and rc 3 no longer differ in text";; *) pass=$((pass+1));; esac
  if jq -e '.runs["995"]' "$SD/fanout.state" >/dev/null 2>&1; then
    fail=$((fail+1)); echo "SELFTEST FAIL: #932 a missing decoder MARKED the run done — a box fault became a permanent loss of attribution"
  else
    pass=$((pass+1))
  fi
  # 10f-quater. (#932 criterion 3) A MISSING oc-notify.sh is the SAME defect one
  # line below the embed lib, and the worse half: notify_session returned the
  # shell's rc 127 for an undefined command, `_notify_reason` had no arm for 127 so
  # the journal carried `reason:"unknown", verb_rc:127` -- an UNDECLARED code in a
  # durable record -- and `_notify_retryable 127` answered RETRYABLE, so the fan-out
  # spent its ENTIRE NOTIFY_RETRY_BUDGET (180 s default) re-sending through a library
  # that cannot appear mid-run. The guard is asserted IN-PROCESS because that is
  # where it lives; the child-process sourcing path is covered by 10f-ter above.
  # Control: assert the library IS resolvable in this environment, so rc 4 can only
  # have come from the _OC_NOTIFY_MISSING flag and not from a genuinely absent lib
  # (a call with the flag clear is NOT the control -- NOTIFY_CMD defaults to the real
  # `opencrabs` CLI, so that call would fire an actual notify).
  local _saved_nm="${_OC_NOTIFY_MISSING:-0}" _saved_dry="${DRYRUN:-0}"
  DRYRUN=0; _OC_NOTIFY_MISSING=1
  out="$(notify_session aaaaaaaa-1111-2222-3333-444444444444 "selftest title" "selftest body" 2>&1)"; rc=$?
  _OC_NOTIFY_MISSING="$_saved_nm"; DRYRUN="$_saved_dry"
  check_rc "notify-nolib-rc" $rc 4
  check_has "notify-nolib-names-lib" "$out" "oc-notify.sh"
  # VACUITY CONTROL for the line above (the prose promised one; without it the arm
  # passes for the WRONG reason when the library is genuinely absent, since rc 4
  # would then come from the `! command -v` clause rather than the flag).
  command -v oc_notify_session >/dev/null 2>&1 && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #932 vacuity control -- oc_notify_session ABSENT here, so notify-nolib-rc cannot discriminate a missing library from a missing flag"; }
  # The glob must be ANCHORED to a token. A bare `*127*` matched a digit run inside
  # a mktemp path ($OC_TOOLS_DIR is e.g. /tmp/criterion-tree-65j127zo, and
  # _OC_NOTIFY_LIB embeds it), so the arm failed for a reason that has nothing to
  # do with the defect it names -- a test that lies in the SAFE direction still lies.
  case "$out" in
    *"rc 127"*|*"rc=127"*|*"verb_rc:127"*) fail=$((fail+1)); echo "SELFTEST FAIL: #932 the missing-notify diagnostic leaked rc 127 -- an undeclared code in a durable record";;
    *) pass=$((pass+1));;
  esac
  # the retry loop must not run for this cause: assert the budget gate names it
  grep -q '_OC_NOTIFY_MISSING:-0}" != 1' "$SRC_FANOUT" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #932 notify_one can still burn the retry budget on a missing library"; }
  # 10g. #72: gates-FIRST job ordering with the bare-sha gates name
  #      (`ORDER gates (<40-hex>)`, no comma) at jobs[0] and the build job at
  #      jobs[1] — the GREEN run is FOUND (built sha decoded), never skipped
  out="$(OC_TEST_GATES_FIRST=1 OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_NOFANOUT=1 "$STATUS_BIN" poll --wait 0 2>&1)"; rc=$?
  check_rc "poll-gates-first-rc" $rc 0
  check_has "poll-gates-first-found" "$out" "built sha=dddddddddddddddddddddddddddddddddddddddd"
  check_has "poll-gates-first-run-id" "$out" "run=334"
  case "$out" in *"skip run 334"*) fail=$((fail+1)); echo "SELFTEST FAIL: poll-gates-first wrongly skipped run 334";; *) pass=$((pass+1));; esac
  # 10d. C-#2: handoff wakes --notify-session
  rm -f "$SD/deployed.sha"
  : > "$T/notify.log"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_DEPLOY_NOFANOUT=1 OC_SWAP_INFLIGHT_LISTER=/bin/true OC_SWAP_LAUNCH="$SD/launch" OC_DEPLOY_NOTIFY="$SD/notify" \
    "$STATUS_BIN" poll --execute --notify-session aaaaaaaa-1111-2222-3333-444444444444 2>&1)"; rc=$?
  check_rc "poll-wait-handoff-rc" $rc 0
  grep -q "HANDOFF" "$T/notify.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: handoff did not notify session"; }
  : > "$T/notify.log"   # drill case 11 asserts a CLEAN notify log — restore it
  # 11. swap-execute DRILL in sandbox: full auto-swap->backup->install->marker->
  #     restart->post-verify-FAIL->rollback->re-verify->stamp chain, no bounce
  printf 'v1-fake-binary' > "$T/bin/oc-fake"; chmod +x "$T/bin/oc-fake"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD/workers-ledger.json"
  echo prev > "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_TARGET="$T/bin/oc-fake" \
    OC_SWAP_BACKUP_DIR="$SD/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_A2A_URL="" \
    OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_DEPLOY_NOTIFY="$SD/notify" \
    "$SWAP_BIN" swap-execute --sha aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    --run 111 --features telegram --drill 2>&1)"; rc=$?
  check_rc "drill-rc" $rc 0
  check_has "drill-verdict" "$out" "DRILL COMPLETE"
  [ ! -s "$NOTIFY_LOG" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: drill performed verb calls"; }
  local JFILES; JFILES="$(ls "$SD/oc-deploy/journal/" 2>/dev/null | grep -c '^swap-')"
  [ "$JFILES" -ge 1 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no drill journal file"; }
  local JL; JL="$(ls "$SD/oc-deploy/journal/"swap-* | head -1)"
  local st; for st in auto-swap backup verify install seal marker-write restart post-verify rollback receipt; do
    grep -q "\"step\":\"$st\"" "$JL" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: journal missing step $st"; }
  done
  [ "$(cat "$SD/deployed.sha")" = "prev" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: deployed.sha not restored after rollback"; }
  jq -e '[.events[] | select(.kind=="swap-result")] | length == 1' "$SD/workers-ledger.json" >/dev/null \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no swap-result ledger stamp"; }
  grep -lq "v1-fake-binary" "$SD/backups/"* 2>/dev/null && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: backup file missing/wrong content"; }
  # 11b. F-H1: forced failed-restore branch — journal records rollback rc=1
  #      with restore_failed:true, ledger stamps ROLLBACK-FAILED (never a
  #      false ROLLED_BACK). OC_SWAP_ROLLBACK_FAIL=1 is a test-only hook.
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD/workers-ledger.json"
  echo prev > "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_TARGET="$T/bin/oc-fake" \
    OC_SWAP_BACKUP_DIR="$SD/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_A2A_URL="" \
    OC_SWAP_ROLLBACK_FAIL=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_DEPLOY_NOTIFY="$SD/notify" \
    "$SWAP_BIN" swap-execute --sha aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    --run 113 --features telegram --drill 2>&1)"; rc=$?
  check_rc "drill-rollbackfail-rc" $rc 0
  check_has "drill-rollbackfail-echo" "$out" "MANUAL RECOVERY REQUIRED"
  local JLB; JLB="$(ls -t "$SD/oc-deploy/journal/"swap-* | head -1)"
  grep -q '"step":"rollback","exit":1' "$JLB" && grep -q 'restore_failed' "$JLB" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: failed restore not journaled truthfully (rc=1 + restore_failed)"; }
  grep -q 'ROLLBACK-FAILED' "$SD/workers-ledger.json" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: ledger did not stamp ROLLBACK-FAILED"; }
  # 11c. BACKUP RETENTION (#497) — asserted at the FUNCTION level here and by a
  #      real drill below. The RULES live with prune_binary_backups(); what is
  #      test-specific: the fixture gives the NEWEST name the OLDEST mtime,
  #      which is the live shape `cp -p` produces.
  #      MUTATION KILL: swap `sort -r` for `ls -1t` (mtime order) and the
  #      "fresh backup survived" assertion fails; drop the grep and the foreign
  #      file is deleted.
  local SD7="$T/state7"; mkdir -p "$SD7/backups"
  local _n
  for _n in 01 02 03 04; do
    echo "old$_n" > "$SD7/backups/opencrabs-2026090${_n:1}-1200${_n}-pre-aaaaaa$_n"
  done
  # newest NAME, oldest mtime -> the trap
  touch -t 202001010000 "$SD7/backups/opencrabs-20260904-120004-pre-aaaaaa04"
  touch -t 202601010000 "$SD7/backups/opencrabs-20260901-120001-pre-aaaaaa01"
  echo keep > "$SD7/backups/hand-made-copy"
  local _JF7="$T/state7/journal.jsonl"; : > "$_JF7"
  (
    BACKUP_DIR="$SD7/backups" BAK_KEEP=2 JF="$_JF7" SEQ=0
    prune_binary_backups "$SD7/backups/opencrabs-20260904-120004-pre-aaaaaa04"
  ) >/dev/null 2>&1
  local _survivors; _survivors="$(ls -1 "$SD7/backups" | sort | tr '\n' ' ')"
  case "$_survivors" in
    *"pre-aaaaaa01"*) fail=$((fail+1)); echo "SELFTEST FAIL: prune kept the OLDEST name (mtime ordering?): $_survivors" ;;
    *) pass=$((pass+1)) ;;
  esac
  case "$_survivors" in
    *"pre-aaaaaa04"*) pass=$((pass+1)) ;;   # the live rollback point (oldest mtime!)
    *) fail=$((fail+1)); echo "SELFTEST FAIL: prune deleted the NEWEST-NAME backup: $_survivors" ;;
  esac
  case "$_survivors" in
    *"hand-made-copy"*) pass=$((pass+1)) ;;
    *) fail=$((fail+1)); echo "SELFTEST FAIL: prune deleted a FOREIGN file: $_survivors" ;;
  esac
  [ "$(ls -1 "$SD7/backups" | grep -cE '^opencrabs-[0-9]{8}-[0-9]{6}-pre-')" = "2" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: prune did not land on exactly 2 kept: $_survivors"; }
  grep -q '"step":"backup-prune"' "$_JF7" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: prune not journaled"; }
  # A no-op must stay SILENT: at or below the keep count nothing is removed and
  # nothing is journalled (a prune that reports on every healthy swap is noise).
  local _JF7b="$T/state7/journal2.jsonl"; : > "$_JF7b"
  ( BACKUP_DIR="$SD7/backups" BAK_KEEP=9 JF="$_JF7b" SEQ=0 prune_binary_backups "" ) >/dev/null 2>&1
  [ -s "$_JF7b" ] && { fail=$((fail+1)); echo "SELFTEST FAIL: prune journalled a no-op"; } || pass=$((pass+1))
  # A BAD KEEP VALUE must not read as "prune everything".
  local _JF7c="$T/state7/journal3.jsonl"; : > "$_JF7c"
  ( BACKUP_DIR="$SD7/backups" BAK_KEEP="abc" JF="$_JF7c" SEQ=0 prune_binary_backups "" ) >/dev/null 2>&1
  [ "$(ls -1 "$SD7/backups" | grep -cE '^opencrabs-[0-9]{8}-[0-9]{6}-pre-')" = "2" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: a non-numeric BAK_KEEP pruned anyway"; }

  # 13. swap-execute below S2 -> exit 4 (stage gate)
  printf '{"meta":{"oc_deploy_stage":"S1"}}' > "$SD/workers-ledger.json"
  OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_TARGET="$T/bin/oc-fake" \
    "$SWAP_BIN" swap-execute --sha bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
    --run 111 --drill >/dev/null 2>&1; check_rc "swap-stage-gate" $? 4
  # 13b. double-execution guard: deployed.sha == --sha -> exit 2, no install
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD/workers-ledger.json"
  printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' > "$SD/deployed.sha"
  printf 'v1-fake-binary' > "$T/bin/oc-fake"
  OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_TARGET="$T/bin/oc-fake" \
    OC_SWAP_BACKUP_DIR="$SD/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_A2A_URL="" \
    "$SWAP_BIN" swap-execute --sha aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    --run 112 --features telegram --drill >/dev/null 2>&1
  check_rc "swap-double-guard" $? 2
  [ "$(cat "$SD/deployed.sha")" = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: guard ran past marker read"; }
  [ "$(cat "$T/bin/oc-fake")" = "v1-fake-binary" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: guard did not prevent install"; }
  # 14. watchdog: CLEAN when fork main tip == deployed.sha
  local WTIP; WTIP="$(git -C "$T/remote.git" rev-parse main)"
  printf '%s\n' "$WTIP" > "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" "$STATUS_BIN" watch 2>&1)"; rc=$?
  check_rc "watch-clean-rc" $rc 0
  check_has "watch-clean-line" "$out" "WATCH-CLEAN"
  # 15. watchdog: ALERT on a stray commit pushed outside the pipeline
  git -C "$T/repo" fetch -q "$T/remote.git" main
  git -C "$T/repo" checkout -qB watchtest FETCH_HEAD
  echo stray > "$T/repo/f-stray"; git -C "$T/repo" add f-stray; git -C "$T/repo" commit -qm stray
  git -C "$T/repo" push -q "$T/remote.git" HEAD:refs/heads/main
  # 20. status subcommand: read-only deployment / daemon summary
  printf '{"sha":"1111111111111111111111111111111111111111","ts":"2026-09-11T12:00:00Z","stage":"S3","features":"telegram,code-graph","run_id":999,"target_host":"local"}\n' > "$SD/deployed.meta.json"
  printf '1111111111111111111111111111111111111111\n' > "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-text-rc" $rc 0
  check_has "status-text-sha" "$out" "Deployed SHA:    1111111111111111111111111111111111111111"

  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status --json 2>&1)"; rc=$?
  check_rc "status-json-rc" $rc 0
  check_has "status-json-sha" "$out" '"sha": "1111111111111111111111111111111111111111"'
  check_has "status-json-features" "$out" '"features": "telegram,code-graph"'
  # #470: the status daemon PID must come from the ops unit, never from
  # `pgrep | head -1` — three daemons share this box and head -1 picks by PID
  # order, so the tool reported another profile's daemon and its uptime.
  # A stub PID_CMD makes the assertion deterministic on any host: whatever the
  # stub prints is what `status` must report, regardless of what is running.
  # The stub PID must be ALIVE (this shell) — the emitter only prints the PID
  # line when the process exists, and a dead stub would read as "stopped".
  _st_live_pid=$$
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_PID_CMD="echo $_st_live_pid" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-pid-source-rc" $rc 0
  check_has "status-pid-from-unit" "$out" "  PID:             $_st_live_pid"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_PID_CMD="echo $_st_live_pid" "$STATUS_BIN" status --json 2>&1)"; rc=$?
  check_rc "status-json-pid-source-rc" $rc 0
  check_has "status-json-pid-from-unit" "$out" "\"pid\": $_st_live_pid"
  # An inactive unit reports MainPID=0, and `kill -0 0` SUCCEEDS (it targets
  # the caller's own process group) — so an unguarded PID 0 would render as
  # "running" with a garbage uptime. This must read as stopped/null.
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_PID_CMD="echo 0" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-pid-zero-rc" $rc 0
  check_has "status-pid-zero-stopped" "$out" "  Status:          stopped"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_SWAP_PID_CMD="echo 0" "$STATUS_BIN" status --json 2>&1)"; rc=$?
  check_has "status-json-pid-zero-null" "$out" '"pid": null'

  # 20b. #746: the documented rc 1 was UNREACHABLE — status_run() ended in an
  # unconditional `return 0`, so `oc-deploy status || handle-mismatch` could
  # never fire. Four discriminating legs: a marker/meta sha DISAGREEMENT (a
  # half-written swap), a record that exists ALONE in either direction (a
  # deployment no swap ever completed), NEITHER (nothing deployed -> nothing
  # to contradict -> rc 0), and the usage error (rc 2). The rc-0 MATCHING pair
  # is the section-20 control above, so a leg that always returned 1 would
  # redden there.
  printf '{"sha":"2222222222222222222222222222222222222222","stage":"S3"}\n' > "$SD/deployed.meta.json"
  printf '3333333333333333333333333333333333333333\n' > "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-mismatch-rc" $rc 1
  rm -f "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-unswapped-meta-only-rc" $rc 1
  rm -f "$SD/deployed.meta.json"
  printf '3333333333333333333333333333333333333333\n' > "$SD/deployed.sha"
  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-unswapped-marker-only-rc" $rc 1
  rm -f "$SD/deployed.sha" "$SD/deployed.meta.json"
  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status 2>&1)"; rc=$?
  check_rc "status-nothing-deployed-rc" $rc 0
  out="$(OC_DEPLOY_STATE_DIR="$SD" "$STATUS_BIN" status --bogus 2>&1)"; rc=$?
  check_rc "status-unknown-arg-rc" $rc 2
  # restore the matching pair the later watch legs read
  printf '{"sha":"1111111111111111111111111111111111111111","ts":"2026-09-11T12:00:00Z","stage":"S3","features":"telegram,code-graph","run_id":999,"target_host":"local"}\n' > "$SD/deployed.meta.json"
  printf '1111111111111111111111111111111111111111\n' > "$SD/deployed.sha"

  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_GH="$SD/gh" "$STATUS_BIN" watch 2>&1)"; rc=$?
  check_rc "watch-alert-rc" $rc 2
  check_has "watch-alert-line" "$out" "WATCH-ALERT"
  grep -q "ALERT:stray" "$SD/oc-deploy-shadow.log" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no watch alert shadow row"; }
  # 16. watchdog: a sha this tool dispatched IS covered (shadow log)
  printf '2026-01-01T00:00:00Z\tship\t%s\ttelegram\tdispatched\tstage=S3\n' "$(git -C "$T/remote.git" rev-parse main)" >> "$SD/oc-deploy-shadow.log"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" "$STATUS_BIN" watch 2>&1)"; rc=$?
  check_rc "watch-covered-rc" $rc 0
  check_has "watch-covered-line" "$out" "WATCH-CLEAN"

  # 16b. watch --with-delta (v0.4.48 merge B) — stub delta tool, no real
  # upstream fixture: rc 0 = clean, rc 1 = present (advisory).
  printf '#!/usr/bin/env bash\necho "BASE abc1234"\nexit 0\n' > "$SD/delta-stub-clean"; chmod +x "$SD/delta-stub-clean"
  printf '#!/usr/bin/env bash\necho "BASE abc1234"\necho "AHEAD 2"\nexit 1\n' > "$SD/delta-stub-ahead"; chmod +x "$SD/delta-stub-ahead"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_DELTA_TOOL="$SD/delta-stub-clean" "$STATUS_BIN" watch --with-delta 2>&1)"; rc=$?
  check_rc "watch-delta-clean-rc" $rc 0
  check_has "watch-delta-prefix" "$out" "DELTA: BASE abc1234"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_DELTA_TOOL="$SD/delta-stub-ahead" "$STATUS_BIN" watch --with-delta 2>&1)"; rc=$?
  check_rc "watch-delta-ahead-rc-stays-0" $rc 0
  check_has "watch-delta-ahead-line" "$out" "DELTA: AHEAD 2"

  # 19. tripwire severity wins: a SECOND stray commit on top of the covered
  # tip + delta present → rc 2; the advisory delta runs but never masks the
  # alarm.
  git -C "$T/repo" fetch -q "$T/remote.git" main
  git -C "$T/repo" checkout -qB watchtest2 FETCH_HEAD
  git -C "$T/repo" commit -q --allow-empty -m "stray again"
  git -C "$T/repo" push -q "$T/remote.git" HEAD:refs/heads/main
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_DELTA_TOOL="$SD/delta-stub-ahead" "$STATUS_BIN" watch --with-delta 2>&1)"; rc=$?
  check_rc "watch-delta-trip-wins-rc" $rc 2
  check_has "watch-delta-trip-alert" "$out" "WATCH-ALERT"
  check_has "watch-delta-trip-delta-ran" "$out" "DELTA: AHEAD 2"
  # 17. fanout GREEN leg (issue #24): deployed run -> one notify per session,
  #     dead uuid -> skip journal line; idempotent re-run is a no-op
  printf 'cccccccccccccccccccccccccccccccccccccccc\n' > "$SD/deployed.sha"
  printf '{"prev_sha":"0000000000000000000000000000000000000000","features":"telegram"}' > "$SD/deployed.meta.json"
  printf '#!/usr/bin/env bash\nprintf "aaaaaaaa-1111-2222-3333-444444444444\\t#99\\tabc1234\\nbbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb\\t-\\tdef5678\\n(unsigned)\\t-\\t9999999\\n"\n' > "$SD/tools/attrib-stub"
  chmod +x "$SD/tools/attrib-stub"
  : > "$NOTIFY_LOG"  # shim created in stubs section; cleared per-case
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 222 2>&1)"; rc=$?
  check_rc "fanout-green-rc" $rc 0
  check_has "fanout-green-counts" "$out" "notified=1 skipped=1"
  grep -q "aaaaaaaa-1111" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: live uuid not notified"; }
  grep -q "bbbbbbbb-bbbb" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: dead uuid attempt missing"; }
  grep -q "(unsigned)" "$NOTIFY_LOG" && { fail=$((fail+1)); echo "SELFTEST FAIL: unsigned row notified"; } || pass=$((pass+1))
  local FJ; FJ="$(ls "$SD/oc-deploy/journal/"fanout-222-*.jsonl 2>/dev/null | head -1)"
  [ -n "$FJ" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no fanout journal file"; }
  if [ -n "$FJ" ]; then
    for st in fanout-start contributors notified skip fanout-end; do
      grep -q "\"step\":\"$st\"" "$FJ" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: fanout journal missing step $st"; }
    done
    grep -q '"reason":"dead"' "$FJ" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no skip reason=dead line"; }
  fi
  jq -e '.runs["222"].notified == 1' "$SD/fanout.state" >/dev/null \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: fanout.state not marked"; }
  # 17b. idempotent re-run: no new notify calls
  local NL1; NL1="$(wc -l < "$NOTIFY_LOG")"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 222 2>&1)"; rc=$?
  check_rc "fanout-idempotent-rc" $rc 0
  check_has "fanout-idempotent-line" "$out" "reason=done"
  [ "$(wc -l < "$NOTIFY_LOG")" = "$NL1" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: re-run sent new notifies"; }
  # 17c. GREEN run not yet deployed -> noop, NOT marked done
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 333 2>&1)"; rc=$?
  check_rc "fanout-notdeployed-rc" $rc 0
  check_has "fanout-notdeployed-line" "$out" "not deployed yet"
  jq -e '.runs["333"]' "$SD/fanout.state" >/dev/null 2>&1 && { fail=$((fail+1)); echo "SELFTEST FAIL: not-deployed run marked done"; } || pass=$((pass+1))
  # 17d. non-terminal run -> rc 4
  OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" \
    "$FANOUT_BIN" fanout --run 444 >/dev/null 2>&1; check_rc "fanout-noterminal" $? 4
  # 17e. dry-run: counts but never calls the verb, never marks done
  local NL2; NL2="$(wc -l < "$NOTIFY_LOG")"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 555 --dry-run 2>&1)"; rc=$?
  check_rc "fanout-dry-rc" $rc 0
  check_has "fanout-dry-counts" "$out" "notified=2 skipped=0"   # verb never consulted in dry-run: dead uuids count as notified
  [ "$(wc -l < "$NOTIFY_LOG")" = "$NL2" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: dry-run called the verb"; }
  jq -e '.runs["555"]' "$SD/fanout.state" >/dev/null 2>&1 && { fail=$((fail+1)); echo "SELFTEST FAIL: dry-run marked done"; } || pass=$((pass+1))
  # 17e2. #407: an oc-attrib FAILURE (rc != 0) still dies rc 3 and names the real
  #       rc — the new empty-result tolerance must not swallow a broken backend.
  printf '#!/usr/bin/env bash\necho "oc-attrib: bad range" >&2\nexit 5\n' > "$SD/tools/attrib-stub-fail"
  chmod +x "$SD/tools/attrib-stub-fail"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub-fail" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 790 2>&1)"; rc=$?
  check_rc "fanout-attrib-fail-rc" $rc 3
  check_has "fanout-attrib-fail-names-rc" "$out" "rc=5"
  FJAF="$(ls -t "$SD/oc-deploy/journal/"fanout-790-*.jsonl 2>/dev/null | head -1)"
  grep -q '"step":"contributors"' "$FJAF" 2>/dev/null && grep -q '"rc":5' "$FJAF" 2>/dev/null \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: attrib-fail journal lacks rc=5 contributors row"; }
  jq -e '.runs["790"]' "$SD/fanout.state" >/dev/null 2>&1 && { fail=$((fail+1)); echo "SELFTEST FAIL: attrib-fail marked done"; } || pass=$((pass+1))
  # 17e3. #407: rc 0 with ZERO rows is GREEN (all-replayed / all-empty range after
  #       the novelty filter), never rc 3. The filter summary must land in the
  #       journal so "no rows" is legible as "nothing novel".
  printf '#!/usr/bin/env bash\necho "oc-attrib: novelty filter 0000000..ccccccc: 310 raw, 276 replayed, 34 empty, 0 contributing" >&2\nexit 0\n' > "$SD/tools/attrib-stub-empty"
  chmod +x "$SD/tools/attrib-stub-empty"
  local NL3; NL3="$(wc -l < "$NOTIFY_LOG")"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub-empty" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 791 2>&1)"; rc=$?
  check_rc "fanout-empty-attrib-rc" $rc 0
  check_has "fanout-empty-attrib-line" "$out" "no novel commits in range"
  check_has "fanout-empty-attrib-end" "$out" "notified=0 skipped=0"
  [ "$(wc -l < "$NOTIFY_LOG")" = "$NL3" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: empty-attrib case still notified"; }
  FJE="$(ls -t "$SD/oc-deploy/journal/"fanout-791-*.jsonl 2>/dev/null | head -1)"
  grep -q '"novel":0' "$FJE" 2>/dev/null && grep -q '276 replayed' "$FJE" 2>/dev/null \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: empty-attrib journal lacks the filter summary"; }
  jq -e '.runs["791"].notified == 0' "$SD/fanout.state" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: legitimately-empty fan-out not marked done"; }
  # 17f. RED leg fixture 1 — culprit blamed, innocent run owner untouched, suspect cc
  git init -q --bare -b main "$T/red1.git"
  git init -q -b main "$T/redc1"; git -C "$T/redc1" remote add origin "$T/red1.git"; git -C "$T/redc1" config user.email t@t; git -C "$T/redc1" config user.name t
  printf 'l1\nl2\nv1\nl4\nl5\nl6\nl7\n' > "$T/redc1/bad.txt"
  git -C "$T/redc1" add bad.txt; git -C "$T/redc1" commit -qm base
  git -C "$T/redc1" push -q "$T/red1.git" HEAD
  git clone -q "$T/red1.git" "$T/redw1"; git -C "$T/redw1" config user.email t@t; git -C "$T/redw1" config user.name t
  sed -i 's/^v1$/v2/' "$T/redw1/bad.txt"
  git -C "$T/redw1" add bad.txt
  git -C "$T/redw1" commit -qm "feat: culprit change

Session-Id: cccccccc-1111-2222-3333-444444444444
Issue-Ref: #101"
  git -C "$T/redw1" push -q origin HEAD
  local RHEAD1; RHEAD1="$(git -C "$T/redw1" rev-parse HEAD)"
  printf '%s\n' "$RHEAD1" > "$SD/red-head"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc1" OC_DEPLOY_REMOTE="$T/red1.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 666 2>&1)"; rc=$?
  check_rc "fanout-red-rc" $rc 0
  check_has "fanout-red-counts" "$out" "notified=1 skipped=0 unowned=0"
  grep -q "cccccccc-1111" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: culprit not notified"; }
  grep -q "bbbbbbbb-bbbb" "$NOTIFY_LOG" && { fail=$((fail+1)); echo "SELFTEST FAIL: innocent owner notified"; } || pass=$((pass+1))
  local FJ2; FJ2="$(ls "$SD/oc-deploy/journal/"fanout-666-*.jsonl 2>/dev/null | head -1)"
  grep -q '"step":"attributed"' "$FJ2" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no attributed line"; }
  grep '"step":"attributed"' "$FJ2" | grep -q "cccccccc-1111" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: attributed missing blamed uuid"; }
  grep '"step":"attributed"' "$FJ2" | grep -q '"suspect":\[\]' && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: suspect set not empty in fixture 1"; }
  grep '"step":"notified"' "$FJ2" | grep -q '"role":"blamed"' && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no blamed-role notify line"; }
  jq -e '.runs["666"].notified == 1' "$SD/fanout.state" >/dev/null && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: red run not marked done"; }
  # 17g. RED fixture 2 — suspect cc: innocent earlier toucher of the blamed file
  git init -q --bare -b main "$T/red2.git"
  git init -q -b main "$T/redc2"; git -C "$T/redc2" remote add origin "$T/red2.git"; git -C "$T/redc2" config user.email t@t; git -C "$T/redc2" config user.name t
  printf 'l1\nl2\nv1\nl4\nl5\nl6\nl7\n' > "$T/redc2/bad.txt"
  git -C "$T/redc2" add bad.txt; git -C "$T/redc2" commit -qm base
  git -C "$T/redc2" push -q "$T/red2.git" HEAD
  git clone -q "$T/red2.git" "$T/redw2"; git -C "$T/redw2" config user.email t@t; git -C "$T/redw2" config user.name t
  sed -i 's/^v1$/v1a/' "$T/redw2/bad.txt"; git -C "$T/redw2" add bad.txt
  git -C "$T/redw2" commit -qm "chore: suspect touches file

Session-Id: dddddddd-1111-2222-3333-444444444444"
  sed -i 's/^v1a$/v2/' "$T/redw2/bad.txt"; git -C "$T/redw2" add bad.txt
  git -C "$T/redw2" commit -qm "feat: culprit change

Session-Id: cccccccc-1111-2222-3333-444444444444"
  git -C "$T/redw2" push -q origin HEAD
  printf '%s\n' "$(git -C "$T/redw2" rev-parse HEAD)" > "$SD/red-head"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc2" OC_DEPLOY_REMOTE="$T/red2.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 670 2>&1)"; rc=$?
  check_rc "fanout-suspect-rc" $rc 0
  check_has "fanout-suspect-counts" "$out" "notified=2 skipped=0 unowned=0"
  grep -q "suspect cc" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no suspect-role notify"; }
  grep '"step":"attributed"' "$(ls "$SD/oc-deploy/journal/"fanout-670-*.jsonl | head -1)" | grep -q "dddddddd-1111" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: suspect uuid missing from attributed line"; }
  # 17h. RED fixture 3 — blamed commit has NO trailer: unowned, nothing notified
  git init -q --bare -b main "$T/red3.git"
  git init -q -b main "$T/redc3"; git -C "$T/redc3" remote add origin "$T/red3.git"; git -C "$T/redc3" config user.email t@t; git -C "$T/redc3" config user.name t
  printf 'l1\nl2\nv1\nl4\nl5\nl6\nl7\n' > "$T/redc3/bad.txt"
  git -C "$T/redc3" add bad.txt; git -C "$T/redc3" commit -qm base
  git -C "$T/redc3" push -q "$T/red3.git" HEAD
  git clone -q "$T/red3.git" "$T/redw3"; git -C "$T/redw3" config user.email t@t; git -C "$T/redw3" config user.name t
  sed -i 's/^v1$/v2/' "$T/redw3/bad.txt"; git -C "$T/redw3" add bad.txt
  git -C "$T/redw3" commit -qm "chore: change without trailer"
  git -C "$T/redw3" push -q origin HEAD
  printf '%s\n' "$(git -C "$T/redw3" rev-parse HEAD)" > "$SD/red-head"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc3" OC_DEPLOY_REMOTE="$T/red3.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 667 2>&1)"; rc=$?
  check_rc "fanout-unowned-rc" $rc 0
  check_has "fanout-unowned-counts" "$out" "notified=0 skipped=0 unowned=1"
  [ ! -s "$NOTIFY_LOG" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: unowned commit notified someone"; }
  grep '"step":"unowned"' "$(ls "$SD/oc-deploy/journal/"fanout-667-*.jsonl | head -1)" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: no unowned journal line"; }
  # 17i. RED fixture 4 — zero annotations: range fallback + HUMAN-FLAG
  git init -q --bare -b main "$T/red4.git"
  git init -q -b main "$T/redc4"; git -C "$T/redc4" remote add origin "$T/red4.git"; git -C "$T/redc4" config user.email t@t; git -C "$T/redc4" config user.name t
  echo x > "$T/redc4/f.txt"; git -C "$T/redc4" add f.txt; git -C "$T/redc4" commit -qm base
  git -C "$T/redc4" commit -q --allow-empty -m "feat: trailer commit

Session-Id: 99999999-8888-7777-6666-555555555555"
  git -C "$T/redc4" push -q "$T/red4.git" HEAD
  printf '%s\n' "$(git -C "$T/redc4" rev-parse HEAD)" > "$SD/red-head"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc4" OC_DEPLOY_REMOTE="$T/red4.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 668 2>&1)"; rc=$?
  check_rc "fanout-nosite-rc" $rc 0
  grep -q "99999999-8888" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: fallback did not notify range session"; }
  grep -q "HUMAN-FLAG" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: fallback text missing HUMAN-FLAG"; }
  # 17j. RED fixture 5 — culprit session DEAD: skip journal, run still completes
  git init -q --bare -b main "$T/red5.git"
  git init -q -b main "$T/redc5"; git -C "$T/redc5" remote add origin "$T/red5.git"; git -C "$T/redc5" config user.email t@t; git -C "$T/redc5" config user.name t
  printf 'l1\nl2\nv1\nl4\nl5\nl6\nl7\n' > "$T/redc5/bad.txt"
  git -C "$T/redc5" add bad.txt; git -C "$T/redc5" commit -qm base
  git -C "$T/redc5" push -q "$T/red5.git" HEAD
  git clone -q "$T/red5.git" "$T/redw5"; git -C "$T/redw5" config user.email t@t; git -C "$T/redw5" config user.name t
  sed -i 's/^v1$/v2/' "$T/redw5/bad.txt"; git -C "$T/redw5" add bad.txt
  git -C "$T/redw5" commit -qm "feat: dead-session change

Session-Id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
  git -C "$T/redw5" push -q origin HEAD
  printf '%s\n' "$(git -C "$T/redw5" rev-parse HEAD)" > "$SD/red-head"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc5" OC_DEPLOY_REMOTE="$T/red5.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$FANOUT_BIN" fanout --run 669 2>&1)"; rc=$?
  check_rc "fanout-deadculprit-rc" $rc 0
  check_has "fanout-deadculprit-counts" "$out" "notified=0 skipped=1 unowned=0"
  grep '"step":"skip"' "$(ls "$SD/oc-deploy/journal/"fanout-669-*.jsonl | head -1)" | grep -q '"reason":"dead"' \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: dead culprit not skip-journaled"; }
  # ---- (#623) the reason must NAME the contract code, and rc 2 must NOT retry.
  # The `$SD/notify` stub exits 2 for bbbb... (= no_route, PERMANENT), so this is
  # the exact case where a re-send cannot help: the journal must read `dead` and
  # the stub must have been called EXACTLY ONCE. Asserting the attempt COUNT is
  # what discriminates -- a reason-only assertion passes even if it retried.
  _n623_rc="$(grep -o '"verb_rc":[0-9]*' "$(ls "$SD/oc-deploy/journal/"fanout-669-*.jsonl | head -1)" | head -1)"
  [ "$_n623_rc" = '"verb_rc":2' ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: skip row does not carry verb_rc:2 (got '$_n623_rc')"; }
  grep -q '"retries":0' "$(ls "$SD/oc-deploy/journal/"fanout-669-*.jsonl | head -1)" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: rc 2 (no_route) RETRIED -- it is permanent, a re-send cannot help"; }
  # 17e2. (#623) a TRANSIENT code RETRIES and the recovery is journaled. The stub
  #      exits 4 (transport) once, then 0 -- so this leg proves the re-send both
  #      FIRES and is VISIBLE, which is the whole point (a silent recovery would
  #      leave an auditor unable to tell it from a first-attempt success).
  # rc 3, deliberately. rc 4 is re-routed to the A2A fallback inside
  # oc_notify_session, which reads its port from config.toml and so reaches the
  # LIVE daemon gateway -- answering no_route (rc 2) for this fixture's fake
  # uuid and masking the stub entirely (measured 2026-09-27: stub-calls=2 against
  # a journal reading verb_rc:2). rc 3 is EXCLUDED from that fallback by
  # construction, so it passes through and the retry loop is what gets tested.
  cat > "$SD/notify-transient" <<'NSTUB3'
#!/usr/bin/env bash
echo "$*" >> "${TRANSIENT_LOG:?}"
if [ -f "${TRANSIENT_LOG}.count" ]; then N="$(cat "${TRANSIENT_LOG}.count")"; else N=0; fi
N=$((N+1)); printf '%s' "$N" > "${TRANSIENT_LOG}.count"
[ "$N" -le 3 ] && exit 3
exit 0
NSTUB3
  chmod +x "$SD/notify-transient"
  export TRANSIENT_LOG="$T/notify-transient.log"; : > "$TRANSIENT_LOG"; rm -f "$TRANSIENT_LOG.count"
  # HERMETIC: OC_A2A_URL="" is load-bearing, not decoration. Without it
  # oc_notify_session's A2A fallback reaches the LIVE daemon gateway, which
  # answers `no_route` (rc 2) for the fixture's fake uuids -- so rc 2, not the
  # stub's rc 4, was what reached notify_one, and the leg measured the live
  # gateway instead of the retry logic (diagnosed 2026-09-27 from a stub-call
  # count of 2 against a journal reading rc 2). Other legs pass it for the same
  # reason (see the 17k wiring leg).
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify-transient" OC_DEPLOY_NOTIFY_RETRY_BUDGET=20 OC_DEPLOY_NOTIFY_RETRY_INTERVAL=0 \
    "$FANOUT_BIN" fanout --run 774 2>&1)"; rc=$?
  check_rc "fanout-transient-retry-rc" $rc 0
  _tjl="$(ls "$SD/oc-deploy/journal/"fanout-774-*.jsonl 2>/dev/null | head -1)"
  if grep -qE '"retried":[12]' "$_tjl"; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); echo "SELFTEST FAIL: a recovered wake was not journaled as retried (auditor cannot tell it from a first-attempt success)"
    echo "  diagnostic: journal=$_tjl stub-calls=$(wc -l < "$TRANSIENT_LOG" 2>/dev/null || echo 0)"
    sed -n '1,8p' "$_tjl" 2>/dev/null | sed 's/^/  | /'
  fi
  # The recovery must be journaled as NOTIFIED, not merely absent from skips.
  grep -q '"step":"notified"' "$_tjl" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: retried wake not journaled as notified"; }
  # (#623) The rc -> reason MAPPING, asserted DIRECTLY. This is the load-bearing
  # half of the contract: before the fix every non-zero rc journalled as `dead`,
  # so a transport failure asserted an ABSENT LANE. Asserting the mapping rather
  # than grepping a journal avoids the vacuous-leg trap -- a recovered wake emits
  # no skip row at all, so a journal grep here would pass on the mutant too.
  # `dead` is reserved for rc 2 (no_route, the ONLY permanent outcome).
  _map_ok=1
  for _pair in "2:dead" "3:refused_in_flight" "4:transport" "124:timeout"; do
    _rc="${_pair%%:*}"; _want="${_pair##*:}"
    _got="$(_notify_reason "$_rc")"
    [ "$_got" = "$_want" ] || { _map_ok=0; echo "SELFTEST FAIL: rc $_rc -> '$_got', want '$_want'"; }
  done
  [ "$_map_ok" = 1 ] && pass=$((pass+1)) || fail=$((fail+1))
  # ...and rc 2 must NOT be retryable while the transient codes must be. A retry
  # to a dead uuid cannot help; a retry to a booting daemon is the whole fix.
  _rt_ok=1
  if _notify_retryable 2; then _rt_ok=0; echo "SELFTEST FAIL: rc 2 (no_route) is PERMANENT but reads retryable"; fi
  for _rc in 3 4 124; do
    _notify_retryable "$_rc" || { _rt_ok=0; echo "SELFTEST FAIL: rc $_rc is transient but reads non-retryable"; }
  done
  [ "$_rt_ok" = 1 ] && pass=$((pass+1)) || fail=$((fail+1))
  # 17k. wiring GREEN tail (issue #24): non-drill swap driven to GREEN
  #      completion in sandbox -> fanout fired EXACTLY ONCE, fanout-end
  #      journaled BEFORE the swap-result ledger stamp.
  local SD2="$T/state2" FJ2 N_FJ2 FETS LETS
  mkdir -p "$SD2/tools/ship" "$SD2/backups" "$T/art"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD2/tools/ship/oc-verify-artifact"; chmod +x "$SD2/tools/ship/oc-verify-artifact"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD2/tools/ship/oc-seal";     chmod +x "$SD2/tools/ship/oc-seal"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD2/workers-ledger.json"
  echo prev > "$SD2/deployed.sha"
  printf 'v1-artifact' > "$T/art/opencrabs"; chmod +x "$T/art/opencrabs"
  printf 'v0-current' > "$T/bin/oc-fake2"; chmod +x "$T/bin/oc-fake2"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD2" OC_SWAP_TARGET="$T/bin/oc-fake2" \
    OC_SWAP_BACKUP_DIR="$SD2/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_REPO="$T/crepo" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_SEAL="$SD2/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD2/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
    --run 777 --features telegram --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "wire-green-rc" $rc 0
  check_has "wire-green-complete" "$out" "SWAP COMPLETE"
  N_FJ2="$(ls "$SD2/oc-deploy/journal/"fanout-777-*.jsonl 2>/dev/null | wc -l)"
  [ "$N_FJ2" = "1" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: fanout not invoked exactly once (journals=$N_FJ2)"; }
  FJ2="$(ls "$SD2/oc-deploy/journal/"fanout-777-*.jsonl 2>/dev/null | head -1)"
  grep -q '"step":"fanout-end"' "$FJ2" 2>/dev/null \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: wiring fanout no fanout-end"; }
  FETS="$(grep '"step":"fanout-end"' "$FJ2" 2>/dev/null | tail -1 | jq -r '.ts' 2>/dev/null)"
  LETS="$(jq -r '[.events[] | select(.kind=="swap-result")][-1].t' "$SD2/workers-ledger.json" 2>/dev/null)"
  if [ -n "$FETS" ] && [ -n "$LETS" ] && { [ "$FETS" \< "$LETS" ] || [ "$FETS" = "$LETS" ]; }; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); echo "SELFTEST FAIL: fanout-end not before ledger stamp (FETS=$FETS LETS=$LETS)"
  fi
  grep -q "aaaaaaaa-1111" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: wiring fanout did not notify live uuid"; }
  jq -e '.runs["777"]' "$SD2/fanout.state" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: wiring fanout.state unmarked"; }
  # 17l. NOFANOUT guard: swap completes, fan-out suppressed entirely.
  local SD3="$T/state3"
  mkdir -p "$SD3/tools/ship" "$SD3/backups"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD3/tools/ship/oc-verify-artifact"; chmod +x "$SD3/tools/ship/oc-verify-artifact"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD3/tools/ship/oc-seal";     chmod +x "$SD3/tools/ship/oc-seal"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD3/workers-ledger.json"
  echo prev > "$SD3/deployed.sha"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD3" OC_SWAP_TARGET="$T/bin/oc-fake2" \
    OC_SWAP_BACKUP_DIR="$SD3/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
    OC_DEPLOY_SEAL="$SD3/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD3/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
    --run 777 --features telegram --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "wire-nofanout-rc" $rc 0
  check_has "wire-nofanout-complete" "$out" "SWAP COMPLETE"
  [ -z "$(ls "$SD3/oc-deploy/journal/"fanout-777-*.jsonl 2>/dev/null)" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: NOFANOUT still ran fanout"; }
  [ ! -f "$SD3/fanout.state" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: NOFANOUT marked state"; }
  [ ! -s "$NOTIFY_LOG" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: NOFANOUT notified"; }
  # 17p. features-compat gate (HQ law 2026-09-04): swap whose features DROP a
  #      deployed feature is refused rc 4 with markers untouched; the same call
  #      with --allow-features-drop proceeds to SWAP COMPLETE.
  local SD5="$T/state5"
  mkdir -p "$SD5/tools/ship" "$SD5/backups"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD5/tools/ship/oc-verify-artifact"; chmod +x "$SD5/tools/ship/oc-verify-artifact"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD5/tools/ship/oc-seal";     chmod +x "$SD5/tools/ship/oc-seal"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD5/workers-ledger.json"
  echo prev > "$SD5/deployed.sha"
  printf '{"sha":"prevprevprevprevprevprevprevprevprevprevprevprevprevprev","run_id":42,"artifact_sha256":"aa","features":"telegram,code-graph","swapped_at":"2026-09-04T06:36:06Z","auth":"auto-swap","prev_sha":"old"}' > "$SD5/deployed.meta.json"
  printf 'v1-artifact' > "$T/art/opencrabs"; chmod +x "$T/art/opencrabs"
  printf 'v0-current' > "$T/bin/oc-fake5"; chmod +x "$T/bin/oc-fake5"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD5" OC_SWAP_TARGET="$T/bin/oc-fake5" \
    OC_SWAP_BACKUP_DIR="$SD5/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
    OC_DEPLOY_SEAL="$SD5/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD5/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha cccccccccccccccccccccccccccccccccccccccc \
    --run 881 --features telegram --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "featdrop-refused-rc" $rc 4
  check_has "featdrop-refused-msg" "$out" "features-compat gate"
  check_has "featdrop-names-lost" "$out" "code-graph"
  grep -q 'code-graph' "$SD5/deployed.meta.json" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: featdrop refusal mutated meta"; }
  [ ! -f "$SD5/oc-deploy/journal/swap-cccccccc-*.jsonl" ] && [ -z "$(ls "$SD5/oc-deploy/journal/" 2>/dev/null)" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: featdrop refusal wrote a swap journal"; }
  out="$(OC_DEPLOY_STATE_DIR="$SD5" OC_SWAP_TARGET="$T/bin/oc-fake5" \
    OC_SWAP_BACKUP_DIR="$SD5/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
    OC_DEPLOY_SEAL="$SD5/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD5/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha cccccccccccccccccccccccccccccccccccccccc \
    --run 882 --features telegram --allow-features-drop --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "featdrop-allowed-rc" $rc 0
  check_has "featdrop-allowed-complete" "$out" "SWAP COMPLETE"
  grep -q '"features":"telegram"' "$SD5/deployed.meta.json" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: featdrop allowed did not write meta"; }
  # 17q. additions are NOT drops: same deployed set, wider request passes the gate.
  printf '{"sha":"prevprevprevprevprevprevprevprevprevprevprevprevprevprev","run_id":42,"artifact_sha256":"aa","features":"telegram,code-graph","swapped_at":"2026-09-04T06:36:06Z","auth":"auto-swap","prev_sha":"old"}' > "$SD5/deployed.meta.json"
  out="$(OC_DEPLOY_STATE_DIR="$SD5" OC_SWAP_TARGET="$T/bin/oc-fake5" \
    OC_SWAP_BACKUP_DIR="$SD5/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
    OC_DEPLOY_SEAL="$SD5/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD5/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha dddddddddddddddddddddddddddddddddddddddd \
    --run 883 --features telegram,code-graph,voice --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "featadd-passes-rc" $rc 0
  # 17r-17u. #766 fork-release publish tail (design fork#766, owner-approved
  #      2026-10-04T21:14:29Z). The swap path publishes the ALREADY-VERIFIED
  #      binary as fork release assets and is NON-FATAL by contract.
  #        17r create path (both tags new)
  #        17s idempotent republish (immutable SKIPPED, rolling clobbered)
  #        17t publish FAILURE tolerated — ship still GREEN, rc 0
  #        17u negative control — guard ON => zero gh release calls
  local SD7="$T/state7" RELCAP="$T/relcap"
  mkdir -p "$SD7/tools/ship" "$SD7/backups" "$RELCAP/in" "$RELCAP/x" "$T/crepo"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD7/tools/ship/oc-verify-artifact"; chmod +x "$SD7/tools/ship/oc-verify-artifact"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD7/tools/ship/oc-seal";     chmod +x "$SD7/tools/ship/oc-seal"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD7/workers-ledger.json"
  echo prev > "$SD7/deployed.sha"
  printf '{"sha":"prevprevprevprevprevprevprevprevprevprevprevprevprevprev","run_id":42,"artifact_sha256":"aa","features":"telegram","swapped_at":"2026-09-04T06:36:06Z","auth":"auto-swap","prev_sha":"old"}' > "$SD7/deployed.meta.json"
  printf '{"cycle":352,"deployed_sha":"prevprevprevprevprevprevprevprevprevprevprevprevprevprev"}' > "$SD7/baseline.json"
  printf 'version = "0.5.4"\n' > "$T/crepo/Cargo.toml"   # release name source
  printf 'v1-artifact' > "$T/art/opencrabs"; chmod +x "$T/art/opencrabs"
  printf 'v0-current'  > "$T/bin/oc-fake7";  chmod +x "$T/bin/oc-fake7"
  _oc766_pub() { # $1=sha $2=run $3=rel-exists $4=rel-fail $5=nopublish
    OC_DEPLOY_STATE_DIR="$SD7" OC_SWAP_TARGET="$T/bin/oc-fake7" \
    OC_SWAP_BACKUP_DIR="$SD7/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
    OC_DEPLOY_SEAL="$SD7/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD7/tools/ship/oc-verify-artifact" \
    OC_DEPLOY_REPO="$T/crepo" OC_DEPLOY_NOPUBLISH="${5:-0}" \
    OC_TEST_REL_EXISTS="${3:-}" OC_TEST_REL_FAIL="${4:-}" OC_TEST_REL_CAPTURE="$RELCAP/in" \
    "$SWAP_BIN" swap-execute --sha "$1" --run "$2" --features telegram --artifact-dir "$T/art" 2>&1
  }
  # 17r. create path: neither tag exists -> BOTH releases created; name carries
  #      <upstream-version>+fork.<cycle> (0.5.4 from Cargo.toml, 352 from baseline).
  : > "$GH_LOG"; : > "$NOTIFY_LOG"; rm -f "$RELCAP/in"/*
  out="$(_oc766_pub e111111111111111111111111111111111111111 901 "" "")"; rc=$?
  check_rc "publish-create-rc" $rc 0
  check_has "publish-create-complete" "$out" "SWAP COMPLETE"
  grep -q "release create fork-e111111" "$GH_LOG" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: publish did not create the immutable tag"; }
  grep -q "release create fork-latest" "$GH_LOG" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: publish did not create the rolling tag"; }
  grep -q "0.5.4+fork.352" "$GH_LOG" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: release name is not <version>+fork.<cycle>"; }
  grep -q "publish=rc=0" "$SD7/workers-ledger.json" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: swap-result stamp does not carry publish=rc=0"; }
  # 17r-bis. the published tarball IS the verified binary (D1: build nothing).
  if tar -xzf "$RELCAP/in/opencrabs-fork-linux-amd64.tar.gz" -C "$RELCAP/x" 2>/dev/null; then
    [ "$(sha256sum "$RELCAP/x/opencrabs" | cut -d' ' -f1)" = "$(sha256sum "$T/art/opencrabs" | cut -d' ' -f1)" ] \
      && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: published tarball != verified binary"; }
  else fail=$((fail+1)); echo "SELFTEST FAIL: published asset is not a readable tar.gz"; fi
  grep -q "$(sha256sum "$RELCAP/in/opencrabs-fork-linux-amd64.tar.gz" | cut -d' ' -f1)" "$RELCAP/in/SHA256SUMS" 2>/dev/null \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: SHA256SUMS does not cover the tarball"; }
  [ -s "$RELCAP/in/build-flags.txt" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: build-flags.txt asset missing/empty"; }
  # 17s. idempotent republish: both tags exist -> immutable SKIPPED, rolling clobbered.
  : > "$GH_LOG"
  out="$(_oc766_pub e222222222222222222222222222222222222222 902 "fork-latest fork-e222222" "")"; rc=$?
  check_rc "publish-idem-rc" $rc 0
  grep -q "release create fork-e222222" "$GH_LOG" \
    && { fail=$((fail+1)); echo "SELFTEST FAIL: immutable tag re-created on republish"; } || pass=$((pass+1))
  grep -q "release upload fork-latest" "$GH_LOG" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: rolling tag not re-uploaded"; }
  # 17t. FAILURE TOLERATED (operative rule): gh release fails -> ship STILL rc 0,
  #      the failure is RECORDED, and the swap is NOT rolled back.
  : > "$GH_LOG"
  out="$(_oc766_pub e333333333333333333333333333333333333333 903 "" 1)"; rc=$?
  check_rc "publish-fail-tolerated-rc" $rc 0
  check_has "publish-fail-complete" "$out" "SWAP COMPLETE"
  grep -q "publish=rc=1" "$SD7/workers-ledger.json" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: tolerated publish failure not recorded"; }
  [ "$(cat "$SD7/deployed.sha")" = "e333333333333333333333333333333333333333" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: publish failure rolled back the swap"; }
  # 17u. NEGATIVE CONTROL: guard ON -> ZERO gh release calls (proves 17r's hits
  #      are the publish leg's, not ambient). publish=skipped in the stamp.
  : > "$GH_LOG"
  out="$(_oc766_pub e444444444444444444444444444444444444444 904 "" "" 1)"; rc=$?
  check_rc "publish-guard-rc" $rc 0
  check_has "publish-guard-complete" "$out" "SWAP COMPLETE"
  if grep -qE 'release (create|upload)' "$GH_LOG"; then
    fail=$((fail+1)); echo "SELFTEST FAIL: NOPUBLISH=1 still called gh release"
  else pass=$((pass+1)); fi
  grep -q "publish=skipped" "$SD7/workers-ledger.json" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: guard run did not record publish=skipped"; }
  # 17v. #72 — the carrier dispatch carries the fork release identity, and it is
  #      the SAME string the publish leg names the release with. Both legs are
  #      driven from ONE fixture ($SD7: version 0.5.4, cycle 352), so "same by
  #      construction" is MEASURED rather than agreed. The stub seal never bumps
  #      the counter, so the test simulates it between the legs (jq .cycle += 1):
  #      dispatch injects 353 (cycle+1), publish reads 353 after the seal. The
  #      flag is gated on the
  #      carrier's own declaration: an undeclared input is a hard 422 that would
  #      break EVERY ship, so a transition carrier must get the OLD form + a NOTE.
  local FV72="" PN72=""
  # Positive control: the fixture's pre-seal counter is 352. Without this the
  # dispatch expectation below could pass against a fixture that never read it.
  local CYC72
  CYC72="$(jq -r .cycle "$SD7/baseline.json")"
  [ "$CYC72" = "352" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #72 fixture baseline cycle is '$CYC72', expected 352 (positive control)"; }
  : > "$GH_LOG"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD7" OC_DEPLOY_REPO="$T/crepo" \
    OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_VALIDATE="$SD/tools/val-ok" \
    OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_TEST_CARRIER_FORK_VERSION=1 \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 2>&1)"; rc=$?
  check_rc "72-dispatch-rc" $rc 0
  # Dispatch runs BEFORE the seal, so it must inject the cycle the seal WILL write (352+1).
  check_has "72-dispatch-echo" "$out" "carrier fork_version=0.5.4+fork.353"
  FV72="$(grep -o 'fork_version=[^ ]*' "$GH_LOG" | head -1 | sed 's/^fork_version=//')"
  [ "$FV72" = "0.5.4+fork.353" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #72 dispatch did not carry -f fork_version=0.5.4+fork.353 (got '${FV72:-<none>}')"; }
  # Simulate the seal between the legs (oc-swap:452 writes --cycle CYC+1; the
  # stub seal is exit 0 and never bumps). Without this the publish leg reads the
  # pre-seal counter and the equality below is vacuous.
  jq '.cycle += 1' "$SD7/baseline.json" > "$SD7/baseline.json.tmp" && mv "$SD7/baseline.json.tmp" "$SD7/baseline.json"
  # publish leg, SAME fixture, post-seal: the release title must be the identical string
  out="$(_oc766_pub e555555555555555555555555555555555555555 905 "" "")"; rc=$?
  check_rc "72-publish-rc" $rc 0
  PN72="$(grep 'release create fork-latest' "$GH_LOG" | sed -n 's/.*--title \([^ ]*\) .*/\1/p' | head -1)"
  [ -n "$PN72" ] && [ "$PN72" = "$FV72" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #72 release name '$PN72' != dispatched fork_version '$FV72' (ONE derivation, two consumers)"; }
  # transition carrier (input NOT declared): ship still succeeds, passes NO flag,
  # and says why — this is the state the carrier is in right now.
  : > "$GH_LOG"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD7" OC_DEPLOY_REPO="$T/crepo" \
    OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_VALIDATE="$SD/tools/val-ok" \
    OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 2>&1)"; rc=$?
  check_rc "72-transition-rc" $rc 0
  grep -q 'fork_version=' "$GH_LOG" \
    && { fail=$((fail+1)); echo "SELFTEST FAIL: #72 passed fork_version to a carrier that does not declare it (422 on every ship)"; } || pass=$((pass+1))
  check_has "72-transition-note" "$out" "declares no fork_version input"
  # undecidable contract: the carrier yml read FAILS. Refusing is the only
  # honest answer — passing blind is a 422 on every ship, omitting blind ships a
  # binary whose version never matches its release name. Must NOT dispatch.
  : > "$GH_LOG"
  out="$(cd "$T/repo" && OC_DEPLOY_STATE_DIR="$SD7" OC_DEPLOY_REPO="$T/crepo" \
    OC_DEPLOY_REMOTE="$T/remote.git" OC_DEPLOY_VALIDATE="$SD/tools/val-ok" \
    OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_CARRIER="$SD/tools/carrier" \
    OC_TEST_CARRIER_YML_FAIL=1 \
    "$BUILD_BIN" ship --sha "$SHA2" --allow-ungated-push "selftest fixture: local temp repo, no live gate exists" --execute --wait 0 2>&1)"; rc=$?
  check_rc "72-undecidable-rc" $rc 2
  check_has "72-undecidable-msg" "$out" "refusing to dispatch blind"
  grep -q 'workflow run' "$GH_LOG" \
    && { fail=$((fail+1)); echo "SELFTEST FAIL: #72 dispatched despite an UNREADABLE carrier contract (blind guess either way)"; } || pass=$((pass+1))
  # 17n. sidecar sync (#47): GREEN swap restarts STALE non-ops units, leaves
  #      in-sync units untouched; sandbox systemctl shims + OC_SWAP_SIDECARS=2.
  local SD4="$T/state4" SCJ
  mkdir -p "$SD4/tools/ship" "$SD4/backups" "$SD4/proc/111" "$SD4/proc/222" "$SD4/bin"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD4/tools/ship/oc-verify-artifact"; chmod +x "$SD4/tools/ship/oc-verify-artifact"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD4/tools/ship/oc-seal";     chmod +x "$SD4/tools/ship/oc-seal"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD4/workers-ledger.json"
  echo prev > "$SD4/deployed.sha"
  printf 'v1-artifact' > "$T/art/opencrabs"          # restamp: 17l consumed prior artifact
  printf 'v0-current'  > "$T/bin/oc-fake2"; chmod +x "$T/bin/oc-fake2"
  printf 'v1-artifact' > "$SD4/bin/fresh"            # sidecar binary after its restart == deployed content
  printf 'v0-stale'    > "$SD4/bin/stale"
  ln -sf "$SD4/bin/stale"  "$SD4/proc/111/exe"       # opencrabs.service        -> STALE
  ln -sf "$T/bin/oc-fake2" "$SD4/proc/222/exe"       # opencrabs-family.service -> in-sync AFTER install
  printf '#!/usr/bin/env bash\ncase "$1" in opencrabs.service) echo 111;; opencrabs-family.service) echo 222;; *) echo 0;; esac\n' > "$SD4/sc-show";   chmod +x "$SD4/sc-show"
  printf '#!/usr/bin/env bash\necho opencrabs.service\necho opencrabs-family.service\necho opencrabs-ops.service\n' > "$SD4/sc-lister"; chmod +x "$SD4/sc-lister"
  printf '#!/usr/bin/env bash\necho active\n' > "$SD4/sc-active"; chmod +x "$SD4/sc-active"
  printf '#!/usr/bin/env bash\necho "$@" >> %s/sc-restarts.log\n[ "$1" = opencrabs.service ] && ln -sf %s/bin/fresh %s/proc/111/exe\nexit 0\n' "$SD4" "$SD4" "$SD4" > "$SD4/sc-restart"; chmod +x "$SD4/sc-restart"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD4" OC_SWAP_TARGET="$T/bin/oc-fake2" \
    OC_SWAP_BACKUP_DIR="$SD4/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_PID_CMD="echo 222" OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_SWAP_SIDECARS=2 OC_SWAP_PRIMARY_UNIT=opencrabs-ops.service \
    OC_SWAP_SIDECAR_LISTER="$SD4/sc-lister" OC_SWAP_SIDECAR_SHOW="$SD4/sc-show" \
    OC_SWAP_SIDECAR_ACTIVE="$SD4/sc-active" OC_SWAP_SIDECAR_RESTART="$SD4/sc-restart" \
    OC_SWAP_PROC_PREFIX="$SD4/proc" \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_REPO="$T/crepo" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_SEAL="$SD4/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD4/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha cccccccccccccccccccccccccccccccccccccccc \
    --run 778 --features telegram --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "sidecar-green-rc" $rc 0
  check_has "sidecar-complete" "$out" "SWAP COMPLETE"
  check_has "sidecar-summary" "$out" "SIDECAR SYNC: restarted=1 in_sync=1 failed=0"
  grep -q "opencrabs.service" "$SD4/sc-restarts.log" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: stale sidecar not restarted"; }
  grep -q "opencrabs-family.service" "$SD4/sc-restarts.log" \
    && { fail=$((fail+1)); echo "SELFTEST FAIL: in-sync sidecar was restarted"; } || pass=$((pass+1))
  SCJ="$(grep -l '"step":"sidecar-sync"' "$SD4"/oc-deploy/journal/*.jsonl 2>/dev/null | head -1)"
  [ -n "$SCJ" ] && grep -q '"action":"restarted"' "$SCJ" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: sidecar-sync journal line missing"; }
  # 17o. sidecar guard: sandbox default (SIDECARS unset) => sidecars SKIPPED,
  #      zero restarts even though units would look stale.
  printf 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n' > "$SD4/deployed.sha"  # reset: guard (13b) rejects same-sha re-swap
  out="$(OC_DEPLOY_STATE_DIR="$SD4" OC_SWAP_TARGET="$T/bin/oc-fake2" \
    OC_SWAP_BACKUP_DIR="$SD4/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_REPO="$T/crepo" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_SEAL="$SD4/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD4/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha cccccccccccccccccccccccccccccccccccccccc \
    --run 779 --features telegram --artifact-dir "$T/art" 2>&1)"; rc=$?
  check_rc "sidecar-guard-rc" $rc 0
  N_SC="$(grep -h '"step":"sidecar-sync"' "$SD4"/oc-deploy/journal/*.jsonl 2>/dev/null | grep -c 'drill-or-sandbox-or-disabled')"
  [ "$N_SC" -ge 1 ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: sandbox sidecar guard did not skip"; }
  [ "$(wc -l < "$SD4/sc-restarts.log")" = "1" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: guard run performed sidecar restarts"; }
  # 17o-bis. ruling-1273 default: PROD target + SIDECARS unset => sidecars
  #      SKIPPED too (the f3c03269 auto-swap restarted family here — defect).
  printf 'cccccccccccccccccccccccccccccccccccccccc\n' > "$SD4/deployed.sha"  # reset same-sha guard
  OC_SWAP_TARGET="$T/bin/oc-fake2" \
    OC_DEPLOY_STATE_DIR="$SD4" OC_SWAP_BACKUP_DIR="$SD4/backups" OC_SWAP_RESTART_CMD=true \
    OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
    OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
    OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_REPO="$T/crepo" OC_DEPLOY_REMOTE="$T/remote.git" \
    OC_DEPLOY_SEAL="$SD4/tools/ship/oc-seal" OC_DEPLOY_ARTVERIFY="$SD4/tools/ship/oc-verify-artifact" \
    "$SWAP_BIN" swap-execute --sha dddddddddddddddddddddddddddddddddddddddd \
    --run 780 --features telegram --artifact-dir "$T/art" >/dev/null 2>&1
  N_SC2="$(grep -h '"step":"sidecar-sync"' "$SD4"/oc-deploy/journal/*.jsonl 2>/dev/null | grep -c 'drill-or-sandbox-or-disabled')"
  [ "$N_SC2" -ge 2 ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: prod default restarted sidecars (ruling 1273)"; }
  [ "$(wc -l < "$SD4/sc-restarts.log")" = "1" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 1273-default run restarted a sidecar"; }
  # 17m. poll RED scan (issue #24 wiring): latest failed carrier run fans out
  #      (blame path via 9001 annotations); second poll is idempotent no-op.
  rm -f "$SD/oc-deploy/journal/"fanout-888-*.jsonl   # clear piggyback noise from earlier poll cases
  printf '%s\n' "$(git -C "$T/redw1" rev-parse HEAD)" > "$SD/red-head"
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc1" OC_DEPLOY_REMOTE="$T/red1.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" "$STATUS_BIN" poll 2>&1)"; rc=$?
  check_rc "poll-redscan-rc" $rc 0
  check_has "poll-redscan-line" "$out" "RED scan: run=888"
  check_has "poll-redscan-notified" "$out" "notified=1"
  grep -q "cccccccc-1111" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: RED scan did not notify culprit"; }
  jq -e '.runs["888"]' "$SD/fanout.state" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: RED scan state unmarked"; }
  # 17m-bis. (#932 REGRESSION CONTROL) A MISSING decoder must NOT refuse a RED run.
  # red_leg needs no decoder at all (it reads the jobs list and runs git blame), so
  # the entry guard is deliberately loud-but-not-fatal: refusing at entry would take
  # away a path that works. 10f-ter alone cannot see that regression -- it passes
  # whether the guard fires at entry or on the success arm -- so this arm is the one
  # that discriminates, and it uses the SAME noembed tree 10f-ter built ($ND).
  : > "$NOTIFY_LOG"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc1" OC_DEPLOY_REMOTE="$T/red1.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    "$ND/tools/ship/oc-fanout" fanout --run 676 2>&1)"; rc=$?
  check_rc "noembed-red-attrs-rc" $rc 0
  check_has "noembed-red-warns" "$out" "oc-embed.sh"
  case "$out" in
    *"broken LOCAL TOOL TREE"*) fail=$((fail+1)); echo "SELFTEST FAIL: #932 a missing decoder REFUSED a red run — red_leg needs no decoder, so the guard narrowed a path that works";;
    *) pass=$((pass+1));;
  esac
  grep -q "cccccccc-1111" "$NOTIFY_LOG" && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #932 a missing decoder suppressed RED blame attribution (no culprit notified)"; }
  jq -e '.runs["676"]' "$SD/fanout.state" >/dev/null 2>&1 && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: #932 a missing decoder left the red run UNMARKED — attribution would repeat forever"; }
  local NJ1 NJ2 NEWJ
  NJ1="$(ls "$SD/oc-deploy/journal/"fanout-888-*.jsonl 2>/dev/null | wc -l)"
  out="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$T/redc1" OC_DEPLOY_REMOTE="$T/red1.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" "$STATUS_BIN" poll 2>&1)"; rc=$?
  check_rc "poll-redscan-idem-rc" $rc 0
  check_has "poll-redscan-idem" "$out" "reason=done"
  # issue #42: every invocation journals its outcome — the no-op re-run writes
  # exactly ONE new journal (the skip line), never a duplicate sweep
  NJ2="$(ls "$SD/oc-deploy/journal/"fanout-888-*.jsonl 2>/dev/null | wc -l)"
  NEWJ="$(ls -t "$SD/oc-deploy/journal/"fanout-888-*.jsonl 2>/dev/null | head -1)"
  { [ "$NJ2" = "$((NJ1+1))" ] && grep -q '"reason":"done"' "$NEWJ"; } \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: idempotent RED scan journal wrong (before=$NJ1 after=$NJ2 skipline=$(grep -c '"reason":"done"' "$NEWJ" 2>/dev/null || echo na))"; }
  # 17g. concurrent fanouts (issue #42 flock): two sweeps on the same run
  #      -> exactly one delivery set; the loser exits 0 reason=inflight.
  #      notify-slow sleeps 1s per call so the winner's lock hold (~2s)
  #      overlaps the loser's flock attempt.
  : > "$NOTIFY_LOG"
  cat > "$SD/notify-slow" <<'NSTUB'
#!/usr/bin/env bash
echo "$*" >> "${NOTIFY_LOG:?}"
sleep 1
for last; do :; done
[ "$last" = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" ] && exit 2
exit 0
NSTUB
  chmod +x "$SD/notify-slow"
  local FOUTA FOUTB PA PB RCA RCB
  OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify-slow" "$FANOUT_BIN" fanout --run 789 >"$T/fanout-a.out" 2>&1 & PA=$!
  OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify-slow" "$FANOUT_BIN" fanout --run 789 >"$T/fanout-b.out" 2>&1 & PB=$!
  wait "$PA"; RCA=$?
  wait "$PB"; RCB=$?
  FOUTA="$T/fanout-a.out"; FOUTB="$T/fanout-b.out"
  if [ "$RCA" = 0 ] && [ "$RCB" = 0 ] \
     && [ "$(grep -l 'reason=inflight' "$FOUTA" "$FOUTB" | wc -l)" = 1 ] \
     && [ "$(wc -l < "$NOTIFY_LOG")" = 2 ] \
     && jq -e '.runs["789"].notified == 1' "$SD/fanout.state" >/dev/null 2>&1 \
     && [ "$(ls "$SD/oc-deploy/journal/"fanout-789-*.jsonl 2>/dev/null | wc -l)" = 2 ] \
     && grep -lq '"step":"lock-busy"' "$SD/oc-deploy/journal/"fanout-789-*.jsonl; then
    pass=$((pass+1))
  else
    fail=$((fail+1)) \
      ; echo "SELFTEST FAIL: concurrent fanouts not single-flight (rcA=$RCA rcB=$RCB inflight=$(grep -l 'reason=inflight' "$FOUTA" "$FOUTB" | wc -l) notifylines=$(wc -l < "$NOTIFY_LOG"))"
  fi
  # =========================================================================
  # 21. lineage guard (v0.4.148; rebase-aware v0.4.151) — REAL fixture repo.
  #     The pre-v0.4.151 guard tested ancestry ONLY, so a fork-main rebase —
  #     which rewrites shas and orphans the currently deployed commit — made it
  #     refuse EVERY legitimate forward swap: fleet-blocking, reported
  #     2026-09-12 by lane 2fbfb2f8 (10 refusals; a second lane stamped the
  #     same blocker at n=3508). Patch-id equivalence over merge-base..SHA is
  #     the fix; the negative control below is what keeps it honest.
  #     NOTE: the guard no-ops when the shas are not real objects (cat-file -e
  #     fails -> verdict "unknown"), so these cases MUST use real commits. The
  #     aaaa…/bbbb… fixtures elsewhere exercise the SKIP path, not the guard.
  local LREPO="$T/lrepo" LC0 LDEP LREW LNEW LSTALE LNEG
  git init -q -b main "$LREPO"
  git -C "$LREPO" config user.email t@t; git -C "$LREPO" config user.name t
  echo a > "$LREPO/fa"; git -C "$LREPO" add fa; git -C "$LREPO" commit -qm base
  LC0="$(git -C "$LREPO" rev-parse HEAD)"
  # pre-rewrite deployed lineage: c0 -> "deployed change" (this was LIVE)
  git -C "$LREPO" checkout -q -b old "$LC0"
  echo b > "$LREPO/fb"; git -C "$LREPO" add fb; git -C "$LREPO" commit -qm "deployed change"
  LDEP="$(git -C "$LREPO" rev-parse HEAD)"
  # rewritten fork main: upstream moved, the deployed change was REPLAYED on it
  # -> different parent, different sha, IDENTICAL patch = the rebase twin
  git -C "$LREPO" checkout -q -b rwmain "$LC0"
  echo z > "$LREPO/fz"; git -C "$LREPO" add fz; git -C "$LREPO" commit -qm "upstream change"
  git -C "$LREPO" cherry-pick "$LDEP" >/dev/null 2>&1
  LREW="$(git -C "$LREPO" rev-parse HEAD)"
  echo c > "$LREPO/fc"; git -C "$LREPO" add fc; git -C "$LREPO" commit -qm "incoming change"
  LNEW="$(git -C "$LREPO" rev-parse HEAD)"
  # a genuinely stale/delayed build off the OLD base, unrelated content
  git -C "$LREPO" checkout -q -b stale "$LC0"
  echo s > "$LREPO/fs"; git -C "$LREPO" add fs; git -C "$LREPO" commit -qm "stale build"
  LSTALE="$(git -C "$LREPO" rev-parse HEAD)"
  # negative control: looks like the twin but its CONTENT changed -> patch-id differs
  git -C "$LREPO" checkout -q -b neg "$LC0"
  echo z > "$LREPO/fz"; git -C "$LREPO" add fz; git -C "$LREPO" commit -qm "upstream change"
  git -C "$LREPO" cherry-pick "$LDEP" >/dev/null 2>&1
  echo tampered >> "$LREPO/fb"; git -C "$LREPO" add fb; git -C "$LREPO" commit -q --amend --no-edit
  LNEG="$(git -C "$LREPO" rev-parse HEAD)"
  git -C "$LREPO" checkout -q main
  # 21-pre. the fixture itself must hold: LDEP orphaned AND LREW a true twin
  git -C "$LREPO" merge-base --is-ancestor "$LDEP" "$LNEW" 2>/dev/null \
    && { fail=$((fail+1)); echo "SELFTEST FAIL: lineage fixture broken — LDEP still an ancestor of LNEW"; } \
    || pass=$((pass+1))
  [ "$(git -C "$LREPO" show "$LDEP" | git patch-id --stable | awk '{print $1}')" \
    = "$(git -C "$LREPO" show "$LREW" | git patch-id --stable | awk '{print $1}')" ] \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: lineage fixture broken — twin patch-ids differ"; }
  # 21a. oc-verify-lineage: monotonic accept (fast path)
  out="$("$LV_BIN" --repo "$LREPO" --prev "$LREW" --sha "$LNEW" 2>&1)"; rc=$?
  check_rc "lineage-check-monotonic-rc" $rc 0
  grep -qE '^verdict: +monotonic$' <<< "$out" && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: lineage-check monotonic verdict wrong: $out"; }
  # 21b. oc-verify-lineage: rewritten accept, twin named
  out="$("$LV_BIN" --repo "$LREPO" --prev "$LDEP" --sha "$LNEW" 2>&1)"; rc=$?
  check_rc "lineage-check-rewritten-rc" $rc 0
  grep -qE '^verdict: +rewritten$' <<< "$out" && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: lineage-check rewritten verdict wrong: $out"; }
  check_has "lineage-check-rewritten-twin" "$out" "rewritten_twin:    $LREW"
  # 21b-json. machine-readable shape (reporters/lanes key on this)
  out="$("$LV_BIN" --repo "$LREPO" --prev "$LDEP" --sha "$LNEW" --json 2>&1)"; rc=$?
  check_rc "lineage-check-json-rc" $rc 0
  printf '%s' "$out" | jq -e --arg t "$LREW" '.verdict=="rewritten" and .rewritten_twin==$t' >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: lineage-check --json wrong: $out"; }
  # 21c. oc-verify-lineage: genuinely absent change -> rc 2
  out="$("$LV_BIN" --repo "$LREPO" --prev "$LSTALE" --sha "$LNEW" 2>&1)"; rc=$?
  check_rc "lineage-check-absent-rc" $rc 2
  grep -qE '^verdict: +absent$' <<< "$out" && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: lineage-check absent verdict wrong: $out"; }
  # 21d. NEGATIVE CONTROL: a rewrite whose content CHANGED is still refused —
  #      this is what proves acceptance keys on patch CONTENT, not on "some
  #      commit exists in the range"
  out="$("$LV_BIN" --repo "$LREPO" --prev "$LDEP" --sha "$LNEG" 2>&1)"; rc=$?
  check_rc "lineage-check-negctrl-rc" $rc 2
  grep -qE '^verdict: +absent$' <<< "$out" && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: tampered rewrite NOT refused (patch-id not content-sensitive): $out"; }
  # 21e. unknown (object not in this repo) is SKIPPED, not refused — preserves
  #      the pre-v0.4.151 "if both exist" behaviour
  out="$("$LV_BIN" --repo "$LREPO" --prev deadbeefdeadbeefdeadbeefdeadbeefdeadbeef --sha "$LNEW" 2>&1)"; rc=$?
  check_rc "lineage-check-unknown-rc" $rc 2
  grep -qE '^verdict: +unknown$' <<< "$out" && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: lineage-check unknown verdict wrong: $out"; }
  # 21f-21j. swap-execute E2E on the real fixture. NON-drill on purpose: the
  #          guard is skipped under --drill, so a drill case would assert nothing.
  local SD6="$T/state6" LOUT LERR LRC LJF
  mkdir -p "$SD6/tools/ship" "$SD6/backups"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD6/tools/ship/oc-verify-artifact"; chmod +x "$SD6/tools/ship/oc-verify-artifact"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD6/tools/ship/oc-seal";     chmod +x "$SD6/tools/ship/oc-seal"
  printf 'v1-artifact' > "$T/art/opencrabs"; chmod +x "$T/art/opencrabs"
  printf 'v0-current' > "$T/bin/oc-lin-target"; chmod +x "$T/bin/oc-lin-target"
  : > "$NOTIFY_LOG"
  lin_swap() { # <prev> <sha> [extra...] -> LOUT/LERR/LRC/LJF
    local prev="$1" sha="$2"; shift 2
    printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD6/workers-ledger.json"
    printf '%s\n' "$prev" > "$SD6/deployed.sha"
    printf 'v0-current' > "$T/bin/oc-lin-target"
    LOUT="$(OC_DEPLOY_STATE_DIR="$SD6" OC_SWAP_TARGET="$T/bin/oc-lin-target" \
      OC_SWAP_BACKUP_DIR="$SD6/backups" OC_SWAP_RESTART_CMD=true \
      OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
      OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
      OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
      OC_DEPLOY_REPO="$LREPO" OC_DEPLOY_SEAL="$SD6/tools/ship/oc-seal" \
      OC_DEPLOY_ARTVERIFY="$SD6/tools/ship/oc-verify-artifact" \
      "$SWAP_BIN" swap-execute --sha "$sha" --run 777 --features telegram \
      --artifact-dir "$T/art" "$@" 2>"$T/lin.err")"
    LRC=$?
    LERR="$(cat "$T/lin.err")"
    LJF="$(ls -t "$SD6/oc-deploy/journal/"swap-"${sha:0:8}"-*.jsonl 2>/dev/null | head -1)"
  }
  # 21f. monotonic fast path UNCHANGED: swap proceeds and writes NO guard row
  #      (the common case still costs exactly one --is-ancestor)
  lin_swap "$LREW" "$LNEW"
  check_rc "swap-lineage-monotonic-rc" $LRC 0
  check_has "swap-lineage-monotonic-complete" "$LOUT" "SWAP COMPLETE"
  [ -z "$(grep '"step":"guard"' "$LJF" 2>/dev/null)" ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: monotonic fast path wrote a guard journal row"; }
  # 21g. post-rewrite ACCEPT: deployed sha orphaned, its change preserved under
  #      a new sha in the incoming lineage -> swap proceeds, equivalence journaled
  lin_swap "$LDEP" "$LNEW"
  check_rc "swap-lineage-rewritten-rc" $LRC 0
  check_has "swap-lineage-rewritten-complete" "$LOUT" "SWAP COMPLETE"
  grep -q '"reason":"rewrite-equivalent-swap"' "$LJF" 2>/dev/null \
    && grep -q "\"rewritten_twin\":\"$LREW\"" "$LJF" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: rewrite-equivalent-swap not journaled with the twin"; }
  check_has "swap-lineage-rewritten-note" "$LERR" "preserved as $LREW"
  # 21h. genuine STALE build refused: rc 2 + distinct gate token, and neither
  #      the target binary nor the deployed marker moved
  lin_swap "$LSTALE" "$LNEW"
  check_rc "swap-lineage-stale-rc" $LRC 2
  check_has "swap-lineage-stale-token" "$LERR" "OC_DEPLOY_SWAP_GUARD=stale-build"
  grep -q '"reason":"non-monotonic-swap"' "$LJF" 2>/dev/null && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: stale refusal not journaled as non-monotonic-swap"; }
  [ "$(cat "$T/bin/oc-lin-target")" = "v0-current" ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: stale refusal still installed the binary"; }
  [ "$(cat "$SD6/deployed.sha")" = "$LSTALE" ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: stale refusal moved the deployed marker"; }
  # 21i. audited override: the same refusal with --allow-rewritten-lineage
  #      proceeds and journals justification + actor (never a silent bypass)
  lin_swap "$LSTALE" "$LNEW" --allow-rewritten-lineage "selftest: audited override" --actor selftest
  check_rc "swap-lineage-override-rc" $LRC 0
  check_has "swap-lineage-override-complete" "$LOUT" "SWAP COMPLETE"
  grep -q '"reason":"rewritten-lineage-override"' "$LJF" 2>/dev/null \
    && grep -q '"justification":"selftest: audited override"' "$LJF" \
    && grep -q '"actor":"selftest"' "$LJF" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: override not journaled with justification+actor"; }
  check_has "swap-lineage-override-warning" "$LERR" "OVERRIDDEN"
  # 21j. the override flag cannot be used bare — a missing justification dies rc 2
  OC_DEPLOY_STATE_DIR="$SD6" "$SWAP_BIN" swap-execute --sha "$LNEW" --run 778 \
    --allow-rewritten-lineage >/dev/null 2>"$T/lin.err"; rc=$?
  check_rc "swap-lineage-override-nojust-rc" $rc 2
  check_has "swap-lineage-override-nojust-token" "$(cat "$T/lin.err")" "OC_DEPLOY_GATE=override-needs-justification"
  # ---------------------------------------------------------------------
  # 22. cgroup-kill survival + receipt recovery (v0.4.153)
  #     DEFECT: a DIRECT swap-execute launched from a session hosted by
  #     opencrabs-ops.service lives in that unit's cgroup, so its OWN step-8
  #     restart tears the cgroup down and SIGKILLs it at the restart line.
  #     Steps 9-12 (post-verify, sidecar-sync, receipt, fanout) never run, so
  #     NO swap-result row is written: the host is swapped, the ledger is
  #     silent (journal swap-acb8e205-… stops at seq 7 marker-write, 2026-09-12).
  #     Every other case in this file shims the restart with `true`, so none of
  #     them can observe it — that is the testing gap this section closes.
  #
  #     The restart shim here KILLS the swap's own process group, which is what
  #     a cgroup teardown does. The swap is launched under its own `setsid`, so
  #     that kill cannot reach this selftest.
  #       (a) DETACHED: swap_ensure_detached re-execs via setsid into a NEW
  #           session; the kill lands on the abandoned original group and the
  #           swap runs to completion (receipt step + ledger row + rc 0).
  #       (b) NEGATIVE CONTROL: OC_SWAP_DETACHED=1 suppresses the detach, so the
  #           swap IS the original group; the kill truncates it at marker-write
  #           and NO row is written. Proves the test can SEE the defect.
  #       (c) recover-receipt repairs (b): exactly one row, then a no-op re-run.
  #       (d) recover-receipt REFUSES (rc 2) a journal whose marker-write sha
  #           does not match the current deployed.sha; --historical records it.
  #     NOTE: fanout is suppressed (OC_DEPLOY_NOFANOUT=1 — no network in the
  #     battery). The proof rests on receipt + the ledger stamp, both of which
  #     land strictly AFTER the kill point, so they cannot run unless the swap
  #     survived it.
  # ---------------------------------------------------------------------
  local SD7="$T/state7" SD8="$T/state8" KPG="$T/cgpgid" COUT CERR CRC CJF NEG_JF DET_JF
  mkdir -p "$SD7/tools/ship" "$SD7/backups" "$SD8/tools/ship" "$SD8/backups"
  local d
  for d in "$SD7" "$SD8"; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$d/tools/ship/oc-verify-artifact"; chmod +x "$d/tools/ship/oc-verify-artifact"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$d/tools/ship/oc-seal";     chmod +x "$d/tools/ship/oc-seal"
  done
  # restart shim: kill the ORIGINAL process group (what a unit teardown does)
  cat > "$T/cgkill.sh" <<'EOS'
#!/bin/sh
pg="$(cat "$OC_SWAP_KILL_PGID_FILE" 2>/dev/null)"
[ -n "$pg" ] && kill -TERM -"$pg" 2>/dev/null
exit 0
EOS
  chmod +x "$T/cgkill.sh"
  # launcher wrapper: records its own pgid — under setsid it IS the session leader
  cat > "$T/cgwrap.sh" <<'EOS'
#!/bin/sh
echo "$$" > "$OC_SWAP_KILL_PGID_FILE"
exec "$@"
EOS
  chmod +x "$T/cgwrap.sh"
  cg_swap() { # <sdir> <prev> <sha> <detached 0|1> [extra...] -> COUT/CERR/CRC/CJF
    local sdir="$1" prev="$2" sha="$3" det="$4"; shift 4
    printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$sdir/workers-ledger.json"
    printf '%s\n' "$prev" > "$sdir/deployed.sha"
    printf 'v0-current' > "$T/bin/oc-cg-target"
    : > "$KPG"
    COUT="$(OC_DEPLOY_STATE_DIR="$sdir" OC_SWAP_TARGET="$T/bin/oc-cg-target" \
      OC_SWAP_BACKUP_DIR="$sdir/backups" \
      OC_SWAP_RESTART_CMD="$T/cgkill.sh" OC_SWAP_KILL_PGID_FILE="$KPG" \
      OC_SWAP_ACTIVE_CMD="echo active" OC_SWAP_SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
      OC_A2A_URL="" OC_DEPLOY_NOTIFY="$SD/notify" OC_DEPLOY_GH="$SD/gh" \
      OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" OC_DEPLOY_NOFANOUT=1 \
      OC_DEPLOY_REPO="$LREPO" OC_DEPLOY_SEAL="$sdir/tools/ship/oc-seal" \
      OC_DEPLOY_ARTVERIFY="$sdir/tools/ship/oc-verify-artifact" \
      OC_SWAP_IN_UNIT_CGROUP=1 OC_SWAP_DETACH_CMD="setsid -w" OC_SWAP_DETACHED="$det" \
      setsid "$T/cgwrap.sh" "$SWAP_BIN" swap-execute --sha "$sha" --run 790 \
      --features telegram --artifact-dir "$T/art" "$@" 2>"$T/cg.err" )"
    CRC=$?
    CERR="$(cat "$T/cg.err" 2>/dev/null)"
    CJF="$(ls -t "$sdir/oc-deploy/journal/"swap-"${sha:0:8}"-*.jsonl 2>/dev/null | head -1)"
  }
  # 22a. DETACHED: the swap survives the group kill that a unit teardown performs
  cg_swap "$SD7" "$LREW" "$LNEW" 0
  DET_JF="$CJF"
  # The WAITER (the setsid/systemd-run client) still lives in the doomed cgroup,
  # so it dies with it and reports 143 — NOT the swap's exit code. That is
  # expected, and is exactly why the swap's bookkeeping must never depend on its
  # caller. So assert (i) the kill WAS delivered (waiter rc != 0 — else the test
  # is not exercising the kill path at all) and (ii) the swap SURVIVED it, via
  # the journal + ledger assertions below, which only land after the kill point.
  [ "$CRC" != 0 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg detached waiter exited 0 — the group kill was never delivered"; }
  check_has "cg-detached-complete" "$COUT" "SWAP COMPLETE"
  grep -q '"step":"receipt"' "$DET_JF" 2>/dev/null && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg detached run lost the receipt step"; }
  grep -q '"step":"post-verify"' "$DET_JF" 2>/dev/null && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg detached run lost post-verify (killed at the bounce)"; }
  [ "$(jq '[.events[]|select(.kind=="swap-result")]|length' "$SD7/workers-ledger.json" 2>/dev/null)" = 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg detached run wrote no swap-result ledger row"; }
  # 22b. NEGATIVE CONTROL: no detach -> the kill lands -> truncated, ledger silent
  cg_swap "$SD7" "$LREW" "$LNEW" 1
  NEG_JF="$CJF"
  [ -z "$(grep '"step":"receipt"' "$NEG_JF" 2>/dev/null)" ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg negative control was NOT truncated (receipt present)"; }
  [ "$(jq -rs '.[-1].step' "$NEG_JF" 2>/dev/null)" = "marker-write" ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg negative control did not stop at marker-write"; }
  [ "$(jq '[.events[]|select(.kind=="swap-result")]|length' "$SD7/workers-ledger.json" 2>/dev/null)" = 0 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: cg negative control stamped a row despite truncation"; }
  # 22c. recover-receipt repairs the truncated swap: exactly one row, idempotent
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD7/workers-ledger.json"
  printf '%s\n' "$LNEW" > "$SD7/deployed.sha"
  COUT="$(OC_DEPLOY_STATE_DIR="$SD7" "$RR_BIN" recover-receipt --journal "$NEG_JF" 2>&1)"; CRC=$?
  check_rc "recover-rc" $CRC 0
  check_has "recover-verdict" "$COUT" "row stamped"
  [ "$(jq '[.events[]|select(.kind=="swap-result")]|length' "$SD7/workers-ledger.json" 2>/dev/null)" = 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: recover-receipt did not stamp exactly one row"; }
  COUT="$(OC_DEPLOY_STATE_DIR="$SD7" "$RR_BIN" recover-receipt --journal "$NEG_JF" 2>&1)"; CRC=$?
  check_rc "recover-idempotent-rc" $CRC 0
  check_has "recover-idempotent-msg" "$COUT" "idempotent no-op"
  [ "$(jq '[.events[]|select(.kind=="swap-result")]|length' "$SD7/workers-ledger.json" 2>/dev/null)" = 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: recover-receipt double-stamped on re-run"; }
  # 22d. REFUSAL: journal sha != current deployed.sha -> rc 2, nothing written
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD8/workers-ledger.json"
  printf 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n' > "$SD8/deployed.sha"
  COUT="$(OC_DEPLOY_STATE_DIR="$SD8" "$RR_BIN" recover-receipt --journal "$NEG_JF" 2>&1)"; CRC=$?
  check_rc "recover-refuse-rc" $CRC 2
  check_has "recover-refuse-msg" "$COUT" "superseded"
  [ "$(jq '[.events[]|select(.kind=="swap-result")]|length' "$SD8/workers-ledger.json" 2>/dev/null)" = 0 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: recover-receipt stamped despite the sha mismatch"; }
  # 22e. --historical records the superseded swap rather than refusing outright
  COUT="$(OC_DEPLOY_STATE_DIR="$SD8" "$RR_BIN" recover-receipt --journal "$NEG_JF" --historical 2>&1)"; CRC=$?
  check_rc "recover-historical-rc" $CRC 0
  check_has "recover-historical-kw" "$COUT" "SUPERSEDED"
  [ "$(jq '[.events[]|select(.kind=="swap-result")]|length' "$SD8/workers-ledger.json" 2>/dev/null)" = 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: --historical did not stamp the superseded row"; }
  # 22f. rc PROPAGATION through the detach. A non-blocking launcher (bare
  #      `setsid`) returns 0 the moment it forks, so the swap's own exit code
  #      is lost — a guard refusal (rc 2) would read as success to every caller,
  #      including oc-ship, which branches on it. The detach command must
  #      BLOCK and pass the child's rc through (`systemd-run --scope`, `setsid -w`).
  cg_swap "$SD7" "$LSTALE" "$LNEW" 0
  check_rc "cg-detached-rc-propagation" $CRC 2
  check_has "cg-detached-rc-token" "$CERR" "OC_DEPLOY_SWAP_GUARD=stale-build"
  # 22g. SELECTOR SEMANTICS (v0.4.157). Pre-v0.4.157 --run/--sha were parsed and
  #      then silently DROPPED whenever --journal was absent: the code fell
  #      through to the default branch, took the NEWEST truncated journal, and
  #      echoed the caller's --run beside a journal belonging to a different run.
  #      Live repro 2026-09-12 (lane 2fbfb2f8): `--run 34685906807` resolved to a
  #      4-seq journal of run 34683445854 and answered rc 0 "the swap never
  #      installed" for a swap that had COMPLETED and was deployed - a false
  #      negative whose only sane reader reaction is to re-run a live swap.
  #      (i)  a selector matching NOTHING refuses (rc 2) and never falls back
  #      (ii) a selector matching several journals prefers one carrying a receipt
  #           step, because that PROVES the run completed - the honest verdict is
  #           "nothing to recover", not "never installed"
  COUT="$(OC_DEPLOY_STATE_DIR="$SD7" "$RR_BIN" recover-receipt --run 999999999 --dry-run 2>&1)"; CRC=$?
  check_rc "recover-selector-nomatch-rc" $CRC 2
  check_has "recover-selector-nomatch-msg" "$COUT" "NO journal"
  case "$COUT" in *".jsonl"*) fail=$((fail+1)); echo "SELFTEST FAIL: recover-selector-nomatch fell back to a journal" ;; *) pass=$((pass+1)) ;; esac
  COUT="$(OC_DEPLOY_STATE_DIR="$SD7" "$RR_BIN" recover-receipt --sha deadbeefdeadbeefdeadbeefdeadbeefdeadbeef --dry-run 2>&1)"; CRC=$?
  check_rc "recover-selector-nomatch-sha-rc" $CRC 2
  # several journals share run 790 here (one complete, two truncated): the complete
  # one must win, so the verdict is the honest "swap completed" - the exact
  # inversion of the reported false negative.
  COUT="$(OC_DEPLOY_STATE_DIR="$SD7" "$RR_BIN" recover-receipt --run 790 --dry-run 2>&1)"; CRC=$?
  check_rc "recover-selector-prefers-complete-rc" $CRC 0
  check_has "recover-selector-prefers-complete-msg" "$COUT" "already carries a receipt step"
  # 18. structural guard: the fanout lock NAME must be ignorable by the repo.
  #     Defect class (HQ dispatch 2026-09-13): `fanout.lock.<runid>` ENDS in the
  #     run id, so the state repo's only rule (`*.lock`) CANNOT match it and 12
  #     such locks ended up TRACKED. Every other lock here ends in .lock
  #     (LEDGER.lock, host-swap.lock, run/wave-*.lock) - this one was the outlier.
  LOCKLINE="$(grep -m1 '^  local lockfile=' "$SRC_FANOUT" 2>/dev/null)"
  case "$LOCKLINE" in
    *'"$STATE_DIR/fanout.'*'.lock"'*) pass=$((pass+1)) ;;
    *) fail=$((fail+1)); echo "SELFTEST FAIL: fanout lockfile does not END in .lock (ignorable-name invariant): ${LOCKLINE:-<line not found>}" ;;
  esac
  # 18b. the state repo's own ignore rule must actually match the new name.
  if [ -f "${OC_DEV_STATE:-/nonexistent}/.gitignore" ]; then
    if python3 - "${OC_DEV_STATE:-/nonexistent}" <<'OCPY' 2>/dev/null; then pass=$((pass+1))

import fnmatch, sys
pats = [l.strip() for l in open(sys.argv[1] + '/.gitignore') if l.strip() and not l.startswith('#')]
sys.exit(0 if any(fnmatch.fnmatch('fanout.4242.lock', p) for p in pats) else 1)
OCPY
    else fail=$((fail+1)); echo "SELFTEST FAIL: state repo .gitignore does not ignore fanout.<run>.lock"; fi
  else
    pass=$((pass+1))   # state repo absent in this environment; the suffix arm above stands
  fi
  # ---- #77: scheduling class. Deploys are BACKGROUND work: `low` is the
  # default, and the class is read back off the kernel rather than echoed from
  # the flag just parsed.
  #
  # Each probe forces niceness 0 inside its own subshell first. The battery
  # renices itself to 19 (#76), so without that baseline a child which lowers
  # NOTHING inherits 19 -- a `nice=0` assertion then fails for the wrong reason
  # and, worse, a `nice=19` assertion passes for the wrong reason. #76 measured
  # exactly that failure: a mutant that never renices read 19 and the control
  # called it success.
  rc=0; out="$(bash -c 'renice -n 0 -p $$ >/dev/null 2>&1 || :; exec "$0" ship --resolve-priority' "$BUILD_BIN" 2>&1)" || rc=$?
  check_rc "priority-default-rc0" "$rc" 0
  check_has "priority-default-class-low" "$out" "priority=low"
  check_has "priority-default-nice-19" "$out" "nice=19"
  # #77 req 2: the BUILD CHILD, not just this process. The probe forks a real
  # child after the renice; if the apply moved below the child spawn this leg
  # reads child_nice=0 while the parent still reads 19, so it discriminates
  # ORDERING rather than merely restating the parent arm.
  check_has "priority-default-child-nice-19" "$out" "child_nice=19"
  check_has "priority-default-applied-names-renice" "$out" "renice"

  # `normal` must really leave the process alone, asserted from a 0 baseline so
  # "did nothing" is distinguishable from "inherited 0".
  rc=0; out="$(bash -c 'renice -n 0 -p $$ >/dev/null 2>&1 || :; exec "$0" ship --priority normal --resolve-priority' "$BUILD_BIN" 2>&1)" || rc=$?
  check_rc "priority-normal-rc0" "$rc" 0
  check_has "priority-normal-class" "$out" "priority=normal"
  check_has "priority-normal-nice-0" "$out" "nice=0"
  check_has "priority-normal-child-nice-0" "$out" "child_nice=0"
  check_has "priority-normal-applied-none" "$out" "applied=none"

  # A typo is refused, never silently treated as `normal`: an accepted-but-inert
  # flag is indistinguishable from an honoured one.
  rc=0; out="$("$BUILD_BIN" ship --priority hig --resolve-priority 2>&1)" || rc=$?
  check_rc "priority-bad-value-rc2" "$rc" 2
  # The rc alone is NOT sufficient here: an unvalidated `--priority` also exits 2,
  # downstream, on the missing-`--sha` usage die. Measured: the neutered mutant
  # returns rc 2 for that unrelated reason, so an rc-only leg passes on a tool
  # with no validation at all. The diagnostic is the discriminator.
  rc=0; out="$("$BUILD_BIN" ship --priority 2>&1)" || rc=$?
  check_rc "priority-missing-value-rc2" "$rc" 2
  check_has "priority-missing-value-names-the-flag" "$out" "--priority needs"

  # The class must reach the OPERATOR: the stderr line prints on every non-probe
  # invocation, so a lane reading a deploy log can classify the run without
  # re-deriving it from argv.
  rc=0; out="$(renice -n 0 -p $$ >/dev/null 2>&1 || :; "$BUILD_BIN" ship 2>&1)" || rc=$?
  check_has "priority-stderr-names-class" "$out" "priority=low (nice=19"

  # T-5: `oc-deploy features` is the DOCUMENTED entry; the standalone helper is
  #     internal. The leg that matters is the ONE VALUE: the verb and the
  #     helper must print the SAME set — that is the whole defect (two
  #     commands, one value, and a lane asking the helper directly could get a
  #     value the ship path disagreed with).
  printf '#!/usr/bin/env bash\necho telegram,browser\n' > "$SD/tools/carrier-multi"; chmod +x "$SD/tools/carrier-multi"
  out="$(OC_DEPLOY_CARRIER="$SD/tools/carrier-multi" "$BUILD_BIN" features 2>&1)"; rc=$?
  check_rc "features-rc0" "$rc" 0
  check_has "features-prints-the-set" "$out" "telegram,browser"
  # same value as the helper itself, read in the same run with the SAME argv
  # (empty: the helper takes no fetch flag since #168 cut 2)
  helper_out="$("$SD/tools/carrier-multi" 2>/dev/null)"
  if [ "$out" = "$helper_out" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: features value != helper value"; fi

  # an arg-echoing stub: it REPORTS what the verb forwarded, so the
  # transparency of the wrapper is asserted, not assumed
  printf '#!/usr/bin/env bash\nprintf "args:[%%s]\\n" "$*"\necho telegram\n' > "$SD/tools/carrier-args"; chmod +x "$SD/tools/carrier-args"

  # #168 cut 2: there is NO fetch flag any more — the carrier yml is read
  # REMOTELY, one code path, so there is no freshness choice left to forward.
  # The verb must add NOTHING it was not given: an EMPTY argv is asserted
  # EXACTLY, so a reintroduced implicit flag reddens here rather than shipping.
  out="$(OC_DEPLOY_CARRIER="$SD/tools/carrier-args" "$BUILD_BIN" features 2>&1)"
  check_has "features-forwards-no-implicit-flag" "$out" "args:[]"

  # --repo is forwarded (the verb is a transparent wrapper, not a second reader)
  out="$(OC_DEPLOY_CARRIER="$SD/tools/carrier-args" "$BUILD_BIN" features --repo /tmp/somewhere 2>&1)"
  check_has "features-forwards-repo" "$out" "--repo /tmp/somewhere"

  # The DELETED flags are refused, never silently accepted: a caller still
  # passing --fetch/--no-fetch gets a loud rc 1 naming the flag, so a stale
  # invocation fails visibly instead of quietly doing nothing.
  for _dead in --fetch --no-fetch; do
    out="$(OC_DEPLOY_CARRIER="$SD/tools/carrier-args" "$BUILD_BIN" features "$_dead" 2>&1)"; rc=$?
    check_rc "features-refuses${_dead//-/}" "$rc" 1
    check_has "features-refuses${_dead//-}-names-flag" "$out" "unknown arg"
  done

  # A carrier read FAILURE aborts loudly — never a silent fallback set.
  out="$(OC_DEPLOY_CARRIER="$SD/tools/carrier-fail" "$BUILD_BIN" features 2>&1)"; rc=$?
  check_rc "features-carrier-fail-rc" "$rc" 3
  check_has "features-carrier-fail-names-tool" "$out" "carrier features read FAILED"

  # An unknown flag is refused (rc 1), never ignored.
  out="$("$BUILD_BIN" features --zzz-bogus 2>&1)"; rc=$?
  check_rc "features-unknown-arg-rc1" "$rc" 1
  check_has "features-unknown-arg-names-flag" "$out" "unknown arg"

  # The usage line lists the verb (a verb nobody can discover is not a verb).
  out="$("$BUILD_BIN" --help 2>&1)"
  check_has "features-in-usage" "$out" "features [--repo P]"

  # T-5 ONE-READER guard. The behavioural legs above prove the VERB works; they
  #     cannot prove the SHIP PATH reads through the SAME reader, because the
  #     direct-call mutant produces byte-identical output (measured: MUT B
  #     reddens NOTHING). So the invariant is asserted STRUCTURALLY: the
  #     carrier tool is invoked from EXACTLY ONE place in this file — the
  #     shared reader — and the ship path calls THAT reader. A second call
  #     site is a second reader, and two readers are the defect this verb
  #     exists to remove.
  # the [c] bracket keeps the guard's OWN pattern from matching itself
  # T5-bis: "this file" is now the SPLIT (lib + four tools), so the guard counts
  # over all five — a second reader anywhere in the split is still a second reader.
  # #168 cut 2: the guard counted a FLAG SPELLING (`--fetch`), so deleting the
  # flag would have made it vacuous — it now counts INVOCATIONS, which survive
  # any flag change: the helper is EXECUTED on exactly one line (the reader's)
  # and `carrier_features` is CALLED from exactly two (the features_run wrapper
  # and the ship path's default resolution). Both are structural, not textual.
  _SPLIT_FILES="$SRC_LIB $SRC_BUILD $SRC_SWAP $SRC_FANOUT $SRC_STATUS"
  _cf_calls() { grep -h 'carrier_features' "$@" 2>/dev/null | grep -v '^[[:space:]]*#' | grep -v 'carrier_features() {' | wc -l | tr -d ' '; }
  _cf_exec()  { grep -h -- '"\$tool" "\${args' "$@" 2>/dev/null | wc -l | tr -d ' '; }
  n_reader="$(_cf_calls $_SPLIT_FILES)"
  n_exec="$(_cf_exec $_SPLIT_FILES)"
  if [ "$n_reader" -eq 2 ] && [ "$n_exec" -eq 1 ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); echo "SELFTEST FAIL: one-reader guard broken (carrier_features calls=$n_reader want 2, helper exec sites=$n_exec want 1)"
  fi
  # POSITIVE CONTROL (AGENTS rule 7): a guard that reads 0 because its pattern
  # matches nothing is indistinguishable from a clean tree. A synthetic second
  # reader appended to a COPY must move BOTH counts, else the guard is dead.
  printf 'x="$(carrier_features)"\n' > "$T/extra-reader.sh"
  if [ "$(_cf_calls $_SPLIT_FILES "$T/extra-reader.sh")" -eq 3 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: one-reader guard control did not move (a second reader would pass unnoticed)"; fi
  rm -f "$T/extra-reader.sh"

  # ---------------------------------------------------------------- #124 --
  # 23. THE RECEIPT LEG'S FALSE POSITIVE (#124). The pre-fix leg posted
  #     `message/send` with `role:"ROLE_USER"`. The gateway answers HTTP 200
  #     with a JSON-RPC ERROR body (-32602 unknown variant ROLE_USER), so
  #     curl's rc was 0, the journal recorded `a2a_accepted:true`, and nothing
  #     was ever delivered. 242 of 473 receipt rows in the live journal carry
  #     that false `true`. A `message/send` ALSO mints a real task server-side,
  #     so fixing only the role would have re-armed the same false positive one
  #     layer down: the leg must speak `session/notify` and gate on the parsed
  #     outcome. These arms are a SET — the error body must FAIL and a real
  #     delivery must still PASS, because an arm that only proves "errors fail"
  #     also passes on a leg that delivers nothing at all.
  local A2A_URL_SAVE="$A2A_URL" A2A_CURL_SAVE="$A2A_CURL" SESS_SAVE="${OC_DEPLOY_RECEIPT_SESSION:-}"
  local stub="$T/stub-a2a" stublog="$T/stub-a2a.calls"
  cat > "$stub" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$STUB_LOG"
printf '%s\n' "$STUB_BODY"
exit "${STUB_RC:-0}"
STUB
  chmod +x "$stub"
  export STUB_LOG="$stublog"
  A2A_CURL="$stub"; A2A_URL="http://stub.invalid/a2a/v1"
  OC_DEPLOY_RECEIPT_SESSION="11111111-2222-3333-4444-555555555555"

  # 23a. POSITIVE CONTROL — a delivered outcome still passes, and the request
  #      is a session/notify carrying the resolved uuid. Without this arm every
  #      "error fails" assertion below would pass on a leg that never sends.
  : > "$stublog"
  export STUB_RC=0 STUB_BODY='{"jsonrpc":"2.0","id":1,"result":{"outcome":"delivered"}}'
  if a2a_notify "selftest #124 control"; then rc=0; else rc=$?; fi
  check_rc "a2a124-delivered-rc" "$rc" 0
  if [ "${A2A_OUTCOME:-}" = "delivered" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: a2a124 delivered outcome not parsed (got '${A2A_OUTCOME:-}')"; fi
  check_has "a2a124-method" "$(cat "$stublog")" "session/notify"
  check_has "a2a124-uuid" "$(cat "$stublog")" "11111111-2222-3333-4444-555555555555"
  case "$(cat "$stublog")" in
    *"message/send"*) fail=$((fail+1)); echo "SELFTEST FAIL: a2a124 leg still posts message/send (it MINTS a task)" ;;
    *) pass=$((pass+1)) ;;
  esac

  # 23b. THE INCIDENT — HTTP 200 carrying a JSON-RPC error. curl rc is 0, so
  #      only body parsing can catch it. This is the exact shape the gateway
  #      answered while the journal recorded `true`.
  : > "$stublog"
  export STUB_RC=0
  export STUB_BODY='{"jsonrpc":"2.0","id":1,"error":{"code":-32602,"message":"Invalid params: unknown variant `ROLE_USER`, expected `user` or `agent`"}}'
  if a2a_notify "selftest #124 incident"; then rc=0; else rc=$?; fi
  check_rc "a2a124-jsonrpc-error-rc" "$rc" 1
  check_has "a2a124-jsonrpc-error-why" "${A2A_WHY:-}" "jsonrpc error"
  check_has "a2a124-jsonrpc-error-code" "${A2A_WHY:-}" "-32602"

  # 23c. A 200 with no result.outcome is not a delivery either (silent success).
  export STUB_BODY='{"jsonrpc":"2.0","id":1,"result":{}}'
  if a2a_notify "selftest #124 no outcome"; then rc=0; else rc=$?; fi
  check_rc "a2a124-no-outcome-rc" "$rc" 1
  check_has "a2a124-no-outcome-why" "${A2A_WHY:-}" "no result.outcome"

  # 23d. No addressee -> refuse BEFORE any transport call. OC_RECEIPT_DB points
  #      at a path that cannot exist so the real daemon DB is never read.
  : > "$stublog"
  unset OC_DEPLOY_RECEIPT_SESSION
  OC_RECEIPT_DB="$T/no-such.db" RECEIPT_TOPIC=99999
  if a2a_notify "selftest #124 no addressee"; then rc=0; else rc=$?; fi
  check_rc "a2a124-no-addressee-rc" "$rc" 1
  check_has "a2a124-no-addressee-why" "${A2A_WHY:-}" "no addressee"
  if [ ! -s "$stublog" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: a2a124 called the transport with no addressee resolved"; fi

  # 23e. no_route is PERMANENT — the retry must not burn its budget on it.
  : > "$stublog"
  OC_DEPLOY_RECEIPT_SESSION="11111111-2222-3333-4444-555555555555"
  export STUB_BODY='{"jsonrpc":"2.0","id":1,"result":{"outcome":"no_route"}}'
  OC_A2A_TRIES=3 OC_A2A_RETRY_SLEEP=0
  if a2a_notify_retry "selftest #124 no_route"; then rc=0; else rc=$?; fi
  check_rc "a2a124-no-route-rc" "$rc" 1
  if [ "$(wc -l < "$stublog")" -eq 1 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: a2a124 retried a permanent no_route ($(wc -l < "$stublog") calls, want 1)"; fi

  # 23f. A transport failure IS retried (the post-swap gateway gap this loop
  #      exists for).
  : > "$stublog"
  export STUB_RC=7 STUB_BODY="curl: (7) Failed to connect"
  OC_A2A_TRIES=2 OC_A2A_RETRY_SLEEP=0
  if a2a_notify_retry "selftest #124 transport"; then rc=0; else rc=$?; fi
  check_rc "a2a124-transport-rc" "$rc" 1
  if [ "$(wc -l < "$stublog")" -eq 2 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "SELFTEST FAIL: a2a124 transport failure not retried ($(wc -l < "$stublog") calls, want 2)"; fi
  check_has "a2a124-transport-why" "${A2A_WHY:-}" "transport rc=7"

  A2A_URL="$A2A_URL_SAVE"; A2A_CURL="$A2A_CURL_SAVE"
  if [ -n "$SESS_SAVE" ]; then OC_DEPLOY_RECEIPT_SESSION="$SESS_SAVE"; else unset OC_DEPLOY_RECEIPT_SESSION; fi
  unset OC_RECEIPT_DB STUB_LOG STUB_BODY STUB_RC

  # --- #142: post_verify has NO coverage, and the harness could not give it any.
  # The `return 0` at oc-swap:503 fires BEFORE `set -uo pipefail`, so every arm
  # above this one runs with nounset OFF. These arms re-enable `set -u` locally
  # and are the only place in this suite where an unset-variable read in a
  # sourced deploy function can actually abort. post_verify was never called by
  # ANY arm before this block (grep 'post_verify' over this file was empty),
  # which is how a fabricated "PV_MAT" defect survived three weeks of green runs.
  local _ns_was _ns_ctl _pv_sha _pv_abort
  case $- in *u*) _ns_was=1 ;; *) _ns_was=0 ;; esac
  set -u
  # CONTROL FIRST: prove nounset is live in this block. Without this, an arm
  # that "passes under set -u" passes identically when set -u silently failed.
  if ( unset _ns_probe142; : "$_ns_probe142" ) 2>/dev/null; then _ns_ctl=0; else _ns_ctl=1; fi
  check_rc "142-nounset-is-live-in-this-block" "$_ns_ctl" 1
  # Fixture: a real file to hash, a marker holding that hash, an `active` stub,
  # and a meta path that must stay absent (expect_meta=0).
  printf 'binary-payload\n' > "$T/pv-target"
  _pv_sha="$(sha256sum "$T/pv-target" | cut -d' ' -f1)"
  printf '%s' "$_pv_sha" > "$T/pv-marker"
  printf '#!/usr/bin/env bash\necho active\n' > "$T/pv-active"; chmod +x "$T/pv-active"
  # (a) MATCH: every precondition satisfied -> PV_MATCH=1, and it survives nounset.
  ACTIVE_CMD="$T/pv-active" SWAP_TARGET="$T/pv-target" DEPLOYED="$T/pv-marker" \
  DEPLOYED_META="$T/pv-meta-absent" SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
  post_verify "$_pv_sha" "$_pv_sha" 0
  check_rc "142-post_verify-match-nounset" "$PV_MATCH" 1
  check_has "142-post_verify-detail-nounset" "$PV_DETAIL" '"match":true'
  # (b) NO MATCH: marker differs -> PV_MATCH=0, still no unset read.
  ACTIVE_CMD="$T/pv-active" SWAP_TARGET="$T/pv-target" DEPLOYED="$T/pv-marker" \
  DEPLOYED_META="$T/pv-meta-absent" SKIP_PROC=1 OC_SWAP_SETTLE=0 OC_SWAP_TRIES=1 \
  post_verify "$_pv_sha" "0000000000000000000000000000000000000000000000000000000000000000" 0
  check_rc "142-post_verify-nomatch-nounset" "$PV_MATCH" 0
  # (c) The MEASURED contract, not an assumed one. ACTIVE_CMD is read inside a
  # command substitution (oc-swap:173); under nounset that aborts only the
  # SUBSHELL, so post_verify continues, ACTIVE stays empty and PV_MATCH stays 0.
  # That is fail-closed: an unset dependency can never yield a false PASS. The
  # first version of this arm asserted an ABORT and went red on green code —
  # assert the behaviour that exists, and that the bare read is disclosed.
  # SETTLE=0 TRIES=2: this arm asserts ONE disclosed subshell abort and a
  # fail-closed PV_MATCH=0 — the 30-try cadence is not what it measures (#166).
  { unset ACTIVE_CMD; OC_SWAP_SETTLE=0 OC_SWAP_TRIES=2 post_verify "$_pv_sha" "$_pv_sha" 0; } 2>"$T/pv-unset.err" >/dev/null
  check_rc "142-post_verify-unset-dep-no-false-pass" "$PV_MATCH" 0
  check_has "142-post_verify-unset-dep-disclosed" "$(cat "$T/pv-unset.err")" "unbound variable"
  [ "$_ns_was" = 1 ] || set +u

  # ---------------------------------------------------------------------
  # (156) the swap-result write is DELEGATED to tools/state/oc-ledger
  # ---------------------------------------------------------------------
  # The pre-#156 body jq-appended to $LEDGER (the legacy view name) under a
  # deploy-lib-held flock. In JSONL mode that name is neither the record
  # (events.jsonl) nor the view (workers.json): a row could land on a file
  # the ledger no longer tracks, with an ordinal derived from a stale view.
  # Arms run ledger_stamp in a CHILD that sources the lib with its own
  # OC_DEPLOY_STATE_DIR — never in this shell, whose $LEDGER still resolves
  # the ambient (production) path.
  local _u156="$T/u156-child.sh"
  cat > "$_u156" <<'U156EOF'
set -u
export OC_TOOLS_NOLOG=1
. "$OC_TOOLS_DIR/lib/oc-deploy-lib.sh"
case "$1" in
  stamp) ledger_stamp "$2" "$3" "$4" ;;
  stage) stage ;;
esac
U156EOF
  # 156a — JSONL mode: the row lands on the RECORD, ordinal from the record,
  #        and the stage read off the view SURVIVES the stamp.
  local SD156="$T/state156"; mkdir -p "$SD156/tools" "$SD156/backups"
  printf '{"n":7,"t":"2026-11-01T00:00:00Z","by":"seed","what":"seed row","kind":"note"}\n' > "$SD156/events.jsonl"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SD156/workers.json"
  out="$(OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SD156" bash "$_u156" stamp toolsmith-156 "swap-result probe row" swap-result 2>&1)"; rc=$?
  check_rc "156a-stamp-rc" "$rc" 0
  jq -e 'select(.kind=="swap-result" and .n==8)' "$SD156/events.jsonl" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156a row not on the RECORD (events.jsonl) at n=8"; }
  check_has "156a-stage-survives" "$(OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SD156" bash "$_u156" stage 2>/dev/null)" "S2"
  # 156b — ordinal from the RECORD, never from a stale view: record carries
  #        n=1..3, the legacy-name file (what the old body read) lies at n=99.
  local SDB="$T/state156b"; mkdir -p "$SDB/tools" "$SDB/backups"
  printf '{"n":1,"t":"t","by":"s","what":"a","kind":"note"}\n{"n":2,"t":"t","by":"s","what":"b","kind":"note"}\n{"n":3,"t":"t","by":"s","what":"c","kind":"note"}\n' > "$SDB/events.jsonl"
  printf '{"meta":{},"events":[{"n":97,"t":"t","by":"s","what":"x","kind":"note"},{"n":98,"t":"t","by":"s","what":"y","kind":"note"},{"n":99,"t":"t","by":"s","what":"z","kind":"note"}]}' > "$SDB/workers-ledger.json"
  OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SDB" bash "$_u156" stamp toolsmith-156 "swap-result ordinal probe" swap-result >/dev/null 2>&1
  jq -e 'select(.n==4 and .kind=="swap-result")' "$SDB/events.jsonl" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156b ordinal not derived from the RECORD (expected n=4)"; }
  # 156c — stage reads the JSONL VIEW: workers.json says S2, the legacy-name
  #        file (what the pre-#156 reader consulted) says S0.
  local SDC="$T/state156c"; mkdir -p "$SDC/tools" "$SDC/backups"
  printf '{"n":1,"t":"t","by":"s","what":"a","kind":"note"}\n' > "$SDC/events.jsonl"
  printf '{"meta":{"oc_deploy_stage":"S0"},"events":[]}' > "$SDC/workers-ledger.json"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}' > "$SDC/workers.json"
  check_has "156c-stage-reads-jsonl-view" "$(OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SDC" bash "$_u156" stage 2>/dev/null)" "S2"
  # 156d — LEGACY mode unchanged: record==view==workers-ledger.json, no
  #        events.jsonl is created, the row still lands (positive control for
  #        the delegation serving the mode it must not break).
  local SDD="$T/state156d"; mkdir -p "$SDD/tools" "$SDD/backups"
  printf '{"meta":{"oc_deploy_stage":"S1"},"events":[]}' > "$SDD/workers-ledger.json"
  OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SDD" bash "$_u156" stamp toolsmith-156 "swap-result legacy probe" swap-result >/dev/null 2>&1
  jq -e '[.events[] | select(.kind=="swap-result")] | length == 1' "$SDD/workers-ledger.json" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156d legacy-mode row missing from workers-ledger.json"; }
  [ ! -f "$SDD/events.jsonl" ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156d created events.jsonl in legacy mode"; }
  # 156e — the enum guard and the empty-what guard hold on THIS side; the
  #        empty-actor branch stamps an EXPLICIT unattributed row (rc 0), not
  #        a silent by:"" — positive control is 156a itself.
  OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SD156" bash "$_u156" stamp toolsmith-156 "x probe" note >/dev/null 2>&1
  check_rc "156e-foreign-kind-rc2" "$?" 2
  OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SD156" bash "$_u156" stamp toolsmith-156 "" swap-result >/dev/null 2>&1
  check_rc "156e-empty-what-rc2" "$?" 2
  OC_TOOLS_DIR="$OC_TOOLS_DIR" OC_DEPLOY_STATE_DIR="$SD156" bash "$_u156" stamp "" "swap-result empty-actor probe" swap-result >/dev/null 2>&1
  check_rc "156e-empty-actor-rc0" "$?" 0
  grep -q '(unattributed)' "$SD156/events.jsonl" \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156e empty actor did not stamp an explicit unattributed row"; }
  # 156f — the row is visible to the LEDGER's own reader (the acceptance
  #        shape: `oc-ledger events` sees what deploy stamped).
  local EV156; EV156="$(OC_LEDGER="$SD156/workers-ledger.json" "$OC_TOOLS_DIR/state/oc-ledger" events --json 2>/dev/null \
    | jq '[.[] | select(.kind=="swap-result")] | length' 2>/dev/null)"
  [ "${EV156:-0}" -ge 1 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156f oc-ledger events does not see the deploy-stamped row"; }

  # 156g — the FULL SEQUENCE on a state dir that HAS the record and NO legacy
  #        blob (plan task-2 Done-when). Every pre-existing fixture in this file
  #        writes a workers-ledger.json blob, so none of them could exercise the
  #        shape a cut-over state dir actually has: events.jsonl + workers.json
  #        with the legacy name ABSENT until a write regenerates it as a view.
  #        The sequence proves the three surfaces agree about which file the
  #        ledger IS — the MODE verb's projection, recover-receipt's existence
  #        read, and a later stamp — because each one used to raw-read $LEDGER
  #        and would answer "missing"/"no row" against the absent legacy name.
  #        It also pins that the swap-result row SURVIVES the later stamp: a row
  #        written to the view is erased by the next view rebuild, which is the
  #        original #156 defect seen from the reader side.
  local SDG="$T/state156g" GEV GOUT GRC
  mkdir -p "$SDG/tools" "$SDG/backups"
  printf '{"n":1,"t":"2026-11-01T00:00:00Z","by":"seed","kind":"note","what":"seed row"}\n' > "$SDG/events.jsonl"
  printf '{"meta":{"oc_deploy_stage":"S2"},"workers":[]}\n' > "$SDG/workers.json"
  [ ! -f "$SDG/workers-ledger.json" ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: 156g fixture is not record-only (legacy blob present)"; }
  # (1) mode: a record-only dir with NO declaration is the fail-closed VERDICT
  #     (rc 1), never "ledger unreadable" (rc 3). Pre-fix this died rc 3
  #     "projection failed on .../workers-ledger.json" — the file that is absent.
  GOUT="$(OC_LEDGER="$SDG/workers-ledger.json" "$OC_TOOLS_DIR/state/oc-ledger" mode 2>&1)"; GRC=$?
  check_rc "156g-mode-record-only-rc1-not-rc3" "$GRC" 1
  check_has "156g-mode-resolves-the-record" "$GOUT" "events.jsonl"
  case "$GOUT" in *"projection failed"*|*"workers-ledger.json"*) fail=$((fail+1)); echo "SELFTEST FAIL: 156g mode still resolves the absent legacy view" ;; *) pass=$((pass+1)) ;; esac
  # (2) with a declaration ON THE RECORD, mode answers it (rc 0).
  OC_LEDGER="$SDG/workers-ledger.json" "$OC_TOOLS_DIR/state/oc-ledger" fixture \
    --n 2 --t 2026-11-02T00:00:00Z --kind note --by hq \
    --what "MODE: FORK-STANDING — 156g fixture" >/dev/null 2>&1
  GOUT="$(OC_LEDGER="$SDG/workers-ledger.json" "$OC_TOOLS_DIR/state/oc-ledger" mode 2>&1)"; GRC=$?
  check_rc "156g-mode-declaration-from-record" "$GRC" 0
  check_has "156g-mode-declaration-value" "$GOUT" "FORK-STANDING"
  # (3) recover-receipt into that dir. The truncated journal is the one the
  #     cgroup negative control produced ($NEG_JF, stops at marker-write with
  #     deployed_sha=$LNEW), so the row is a REAL reconstruction.
  printf '%s\n' "$LNEW" > "$SDG/deployed.sha"
  GOUT="$(OC_DEPLOY_STATE_DIR="$SDG" "$RR_BIN" recover-receipt --journal "$NEG_JF" 2>&1)"; GRC=$?
  check_rc "156g-recover-rc" "$GRC" 0
  check_has "156g-recover-verdict" "$GOUT" "row stamped"
  jq -e --arg s "sha=$LNEW" 'select(.kind=="swap-result" and (.what|contains($s)))' "$SDG/events.jsonl" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156g swap-result row is not on the RECORD (events.jsonl)"; }
  # (4) idempotence is read off the RECORD too: a re-run must be a no-op, and
  #     pre-fix the raw-jq read against the absent legacy view answered 0 rows,
  #     so the second run stamped a DUPLICATE.
  GOUT="$(OC_DEPLOY_STATE_DIR="$SDG" "$RR_BIN" recover-receipt --journal "$NEG_JF" 2>&1)"; GRC=$?
  check_rc "156g-recover-idempotent-rc" "$GRC" 0
  check_has "156g-recover-idempotent-msg" "$GOUT" "idempotent no-op"
  [ "$(jq -s '[.[]|select(.kind=="swap-result")]|length' "$SDG/events.jsonl" 2>/dev/null)" = 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: 156g recover-receipt double-stamped on the record"; }
  # (5) a LATER unrelated stamp still exits 0 and does not disturb the row.
  GOUT="$(OC_LEDGER="$SDG/workers-ledger.json" "$OC_TOOLS_DIR/state/oc-ledger" stamp note "156g later note" --by hq 2>&1)"; GRC=$?
  check_rc "156g-later-stamp-rc" "$GRC" 0
  GEV="$(OC_LEDGER="$SDG/workers-ledger.json" "$OC_TOOLS_DIR/state/oc-ledger" events --kind swap-result --json 2>/dev/null)"; GRC=$?
  check_rc "156g-events-after-stamp-rc" "$GRC" 0
  [ "$(printf '%s' "$GEV" | jq 'length' 2>/dev/null)" = 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: 156g the swap-result row did not survive the later stamp"; }
  jq -e --arg s "sha=$LNEW" 'select(.kind=="swap-result" and (.what|contains($s)))' "$SDG/events.jsonl" >/dev/null 2>&1 \
    && pass=$((pass+1)) || { fail=$((fail+1)); echo "SELFTEST FAIL: 156g swap-result row vanished from the RECORD after the later stamp"; }

  # 156h — NO DEPLOY PATH APPENDS TO THE RETIRED BLOB DIRECTLY (#152 acceptance,
  #        second half). 156g proves the row LANDS on the record; this proves the
  #        blob is not a SECOND write target. The invariant is a SUBSET relation:
  #        every swap-result row in the legacy blob must also exist on the record.
  #        A direct append puts a row in the blob the record never saw, and the
  #        next view rebuild erases it — the #152 defect, stated as a measurement.
  local SDH="$T/state156h" HBLB HREC _orph=0 _row
  mkdir -p "$SDH/tools" "$SDH/backups"
  printf '{"n":1,"t":"2026-11-01T00:00:00Z","by":"seed","kind":"note","what":"seed row"}\n' > "$SDH/events.jsonl"
  printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}\n' > "$SDH/workers-ledger.json"
  printf '%s\n' "$LNEW" > "$SDH/deployed.sha"
  GOUT="$(OC_DEPLOY_STATE_DIR="$SDH" "$RR_BIN" recover-receipt --journal "$NEG_JF" 2>&1)"; GRC=$?
  check_rc "156h-recover-rc" "$GRC" 0
  # POSITIVE CONTROL: the row must exist SOMEWHERE. Without it the subset test
  # below passes vacuously on a path that wrote nothing anywhere at all.
  HREC="$(jq -s '[.[]|select(.kind=="swap-result")]|length' "$SDH/events.jsonl" 2>/dev/null)"
  [ "${HREC:-0}" -ge 1 ] && pass=$((pass+1)) \
    || { fail=$((fail+1)); echo "SELFTEST FAIL: 156h positive control — no swap-result row reached the RECORD"; }
  # THE INVARIANT: count swap-result rows in the blob that the record does not
  # carry. Any non-zero answer is a direct append to the retired artifact.
  HBLB="$(jq -r '[.events[]? | select(.kind=="swap-result") | .t + "|" + (.what // "")] | .[]' "$SDH/workers-ledger.json" 2>/dev/null)"
  if [ -n "$HBLB" ]; then
    while IFS= read -r _row; do
      [ -n "$_row" ] || continue
      jq -s -e --arg r "$_row" '[.[]|select(.kind=="swap-result")|.t + "|" + (.what // "")] | index($r)' "$SDH/events.jsonl" >/dev/null 2>&1 \
        || _orph=$((_orph+1))
    done <<< "$HBLB"
    [ "$_orph" = 0 ] && pass=$((pass+1)) \
      || { fail=$((fail+1)); echo "SELFTEST FAIL: 156h $_orph swap-result row(s) in the legacy blob that the RECORD never saw (direct append)"; }
  else
    pass=$((pass+1))
  fi

  echo "deploy selftest: $pass pass, $fail fail"
  rm -rf "$T"
  [ "$fail" = 0 ]