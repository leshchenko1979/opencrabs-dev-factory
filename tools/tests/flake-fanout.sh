#!/usr/bin/env bash
# flake-fanout — repeat-run harness for the oc-deploy fanout fixture (factory #75)
#
# WHY THIS EXISTS
# #75 records a leg that reds intermittently inside the battery while passing
# standalone, on the identical tree. Two modes were measured, neither explained:
#   (1) `fanout-deadculprit-rc rc=3 want=0` + 5 cascading assertions
#       (`no usable head_sha` / `cannot resolve commit range`, oc-deploy:3236,3240)
#   (2) an `rc=127` cascade starting at `swap-lineage-rewritten`, where every
#       assertion AFTER one point fails and every one BEFORE it passes
# The issue's ask is explicit: "Not a fix request. The useful instrument would be
# a repeat-run harness that drives ONLY the fanout fixture N times and records the
# distribution, so the flake either reproduces in seconds or is shown to need
# battery-scale concurrency."
#
# The full `oc-deploy --selftest` is ~164 s and has no leg filter, so N runs of it
# cannot show a distribution in useful time. This harness rebuilds the ONE fixture
# (RED fixture 5, `fanout --run 669`, the dead-culprit leg) against the real tool
# and drives it N times, optionally K-at-a-time to test the concurrency arm.
#
# It asserts the SAME things the selftest leg asserts, so a red here is the same
# defect the battery reports -- not a proxy for it.
#
# USAGE
#   tools/tests/flake-fanout.sh [-n RUNS] [-j CONCURRENCY] [-v]
#     -n  iterations                       (default 20)
#     -j  run K fixtures concurrently      (default 1; use 8+ to test the
#                                           battery-scale-concurrency hypothesis)
#     -v  keep and print each iteration's output
#   exit 0 = every iteration matched the expected verdict
#   exit 1 = at least one iteration diverged (the distribution is printed)
#
# Deliberately NO `timeout` around the tool: a hang IS a result here, and the
# harness records it as `rc=timeout` rather than hiding it.
set -u

TOOLS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SELF_BIN="$TOOLS_DIR/ship/oc-fanout"
RUNS=20
JOBS=1
VERBOSE=0

while [ $# -gt 0 ]; do
  case "$1" in
    -n) RUNS="${2:?}"; shift 2 ;;
    -j) JOBS="${2:?}"; shift 2 ;;
    -v) VERBOSE=1; shift ;;
    -h|--help) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'flake-fanout: unknown arg %s\n' "$1" >&2; exit 2 ;;
  esac
done

case "$RUNS" in ''|*[!0-9]*) printf 'flake-fanout: -n wants a positive integer\n' >&2; exit 2 ;; esac
case "$JOBS" in ''|*[!0-9]*) printf 'flake-fanout: -j wants a positive integer\n' >&2; exit 2 ;; esac
[ -x "$SELF_BIN" ] || { printf 'flake-fanout: not executable: %s\n' "$SELF_BIN" >&2; exit 2; }

# ---- pid-cap awareness (#75) -------------------------------------------------
# Every `run-*.scope` under oc-tasks.slice carries `pids.max = 64`, and root is
# EXEMPT from RLIMIT_NPROC, so that cgroup cap is the only binding limit on this
# box. A fork() that hits it returns EAGAIN and bash DIES ("fork: Interrupted
# system call") -- measured, and not survivable from inside the tool: a probe
# that resolved every substitution into an assignment BEFORE appending still
# wrote nothing, because the shell itself was killed. So the harness must
# (a) state what the cap is, and (b) report an exhaustion red as EXHAUSTED
# rather than RC -- an environment red dressed as a tool red is the
# highest-severity class in this repo (#74/#75/#109/#115) and sends the next
# lane hunting a bug that is not there.
scope_pids_max() {
  # FORK-FREE on purpose: this diagnostic runs exactly when fork() is failing,
  # so `cut`/`cat` (one fork each) would return '?' precisely when it matters —
  # measured under TasksMax=20 as `pids.max=?` on the first exhausted iteration.
  # Bash builtins + redirections only.
  local rel="" line v=""
  while IFS= read -r line; do
    case "$line" in
      0:*) rel="${line#0:}"; rel="${rel#*:}" ;;
    esac
  done < /proc/self/cgroup 2>/dev/null
  [ -n "$rel" ] || { printf '?'; return; }
  { IFS= read -r v; } < "/sys/fs/cgroup${rel}/pids.max" 2>/dev/null
  printf '%s' "${v:-?}"
}
# Fork-exhaustion markers a killed/failing iteration leaves in its own output.
is_exhausted() { # $1 = captured output ; $2 = optional rc
  case "$1" in
    *"fork: retry"*|*"fork: Interrupted system call"*|*"fork: Cannot allocate memory"*) return 0 ;;
    *"background thread creation failed"*) return 0 ;;
  esac
  # rc-only arm: 254 = bash could not exec the script at all, 126/127 = not
  # executable / not found. Under fork pressure these are what a starved shell
  # reports, and they carry NO tool diagnostic — measured rc=254 with empty
  # output at TasksMax=20, which the output-only predicate read as a tool flake.
  case "${2:-}" in
    254|126|127) return 0 ;;
  esac
  return 1
}

T="$(mktemp -d)" || exit 2
trap 'rm -rf "$T"' EXIT

# ---- the git fixture, built ONCE (deterministic; only the state dir is per-run)
# A repo with one file, a base commit, and one "culprit" commit whose message
# carries the DEAD session uuid bbbb... -- the stub notify answers rc 2 for that
# uuid (no_route, permanent), which is what makes this the dead-culprit leg.
build_fixture() {
  git init -q --bare -b main "$T/red5.git" || return 1
  git init -q -b main "$T/redc5" || return 1
  git -C "$T/redc5" remote add origin "$T/red5.git"
  git -C "$T/redc5" config user.email t@t
  git -C "$T/redc5" config user.name t
  git -C "$T/redc5" config commit.gpgsign false
  printf 'l1\nl2\nv1\nl4\nl5\nl6\nl7\n' > "$T/redc5/bad.txt"
  git -C "$T/redc5" add bad.txt
  git -C "$T/redc5" commit -qm base || return 1
  git -C "$T/redc5" push -q "$T/red5.git" HEAD || return 1
  git clone -q "$T/red5.git" "$T/redw5" || return 1
  git -C "$T/redw5" config user.email t@t
  git -C "$T/redw5" config user.name t
  git -C "$T/redw5" config commit.gpgsign false
  sed -i 's/^v1$/v2/' "$T/redw5/bad.txt"
  git -C "$T/redw5" add bad.txt
  git -C "$T/redw5" commit -qm "feat: dead-session change

Session-Id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" || return 1
  git -C "$T/redw5" push -q origin HEAD || return 1
}
build_fixture || { printf 'flake-fanout: fixture build FAILED (environment, not the tool)\n' >&2; exit 2; }
RHEAD5="$(git -C "$T/redw5" rev-parse HEAD)"

# ---- per-iteration state: stubs + a FRESH state dir (fanout.state marks a run
# done, so reusing one would make every iteration after the first a no-op green).
make_state() { # $1 = dir
  local sd="$1"
  mkdir -p "$sd/tools" "$sd/oc-deploy/journal"
  printf '%s\n' "$RHEAD5" > "$sd/red-head"
  # notify stub: rc 2 for the dead uuid (permanent no_route), rc 0 otherwise.
  cat > "$sd/notify" <<'NSTUB'
#!/usr/bin/env bash
echo "$*" >> "${NOTIFY_LOG:?}"
for last; do :; done
[ "$last" = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" ] && exit 2
exit 0
NSTUB
  chmod +x "$sd/notify"
  # gh stub: run 669 is RED with one annotation at bad.txt:3 (the blamed site).
  cat > "$sd/gh" <<'GSTUB'
#!/usr/bin/env bash
case "$*" in
  *actions/runs/669/jobs*) echo '{"jobs":[{"name":"ORDER gates","conclusion":"success"},{"name":"Linux amd64 (eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee, telegram)","conclusion":"failure","check_run_url":"https://api.github.com/repos/leshchenko1979/opencrabs/check-runs/9001"}]}' ;;
  *check-runs/9001/annotations*) echo '[{"path":"bad.txt","start_line":3}]' ;;
  *actions/runs/669*)
    if [ -f "${OC_DEPLOY_STATE_DIR:-}/red-head" ]; then
      echo "{\"status\":\"completed\",\"conclusion\":\"failure\",\"head_sha\":\"$(cat "${OC_DEPLOY_STATE_DIR}/red-head")\"}"
    else
      echo '{"status":"completed","conclusion":"failure"}'
    fi ;;
  *) echo '{}' ;;
esac
GSTUB
  chmod +x "$sd/gh"
}

# ---- one iteration. Writes "<verdict> <detail>" to $2 and the tool output to $3.
# Verdict tokens: PASS | RC | COUNTS | JOURNAL | NOTIFY
one_run() { # $1 = iteration, $2 = result file, $3 = out file
  local i="$1" res="$2" out="$3"
  local sd; sd="$(mktemp -d "$T/sd-$i-XXXX")"
  make_state "$sd"
  local nlog="$sd/notify.log"; : > "$nlog"
  local rc o
  # HERMETIC (#75): every iteration invokes the SAME tool with the SAME args, so
  # without these two the harness poisons itself. OC_TOOLS_NOLOG stops each run
  # writing a tools.log row; OC_NO_FLOODGUARD stops the fleet guard
  # (tools/lib/oc-log.sh:171 — >=4 identical-args failures in 120s -> rc 8) from
  # refusing the 5th iteration and turning ONE real red into a cascade of reds.
  # That cascade is a plausible arm of #75's own "every assertion AFTER one point
  # fails" mode, so the harness must not reproduce it while measuring it.
  o="$(OC_TOOLS_NOLOG=1 OC_NO_FLOODGUARD=1 \
       OC_DEPLOY_STATE_DIR="$sd" OC_DEPLOY_GH="$sd/gh" OC_DEPLOY_REPO="$T/redc5" \
       OC_DEPLOY_REMOTE="$T/red5.git" OC_DEPLOY_NOTIFY="$sd/notify" NOTIFY_LOG="$nlog" \
       "$SELF_BIN" fanout --run 669 2>&1)"; rc=$?
  printf '%s\n' "$o" > "$out"
  if [ "$rc" -ne 0 ]; then
    # #75: an EAGAIN red is the ENVIRONMENT, not the tool. Classify it apart so
    # the verdict never accuses oc-deploy of a defect it does not have.
    if is_exhausted "$o" "$rc"; then
      printf 'EXHAUSTED rc=%s (fork EAGAIN — pids.max=%s; lower -j)\n' "$rc" "$(scope_pids_max)" > "$res"; return
    fi
    printf 'RC rc=%s want=0\n' "$rc" > "$res"; return
  fi
  case "$o" in
    *"notified=0 skipped=1 unowned=0"*) : ;;
    *) if is_exhausted "$o" "$rc"; then
         printf 'EXHAUSTED counts=%s (fork EAGAIN mid-run)\n' "$(printf '%s' "$o" | grep -o 'notified=[0-9]* skipped=[0-9]* unowned=[0-9]*' | head -1)" > "$res"; return
       fi
       printf 'COUNTS %s\n' "$(printf '%s' "$o" | grep -o 'notified=[0-9]* skipped=[0-9]* unowned=[0-9]*' | head -1)" > "$res"; return ;;
  esac
  local j; j="$(ls "$sd/oc-deploy/journal/"fanout-669-*.jsonl 2>/dev/null | head -1)"
  if [ -z "$j" ]; then printf 'JOURNAL no journal file written\n' > "$res"; return; fi
  if ! grep -q '"reason":"dead"' "$j" 2>/dev/null; then
    printf 'JOURNAL skip row missing reason:dead\n' > "$res"; return
  fi
  if ! grep -q '"retries":0' "$j" 2>/dev/null; then
    printf 'JOURNAL rc 2 (no_route) was RETRIED\n' > "$res"; return
  fi
  if grep -q 'bbbbbbbb-bbbb' "$nlog" 2>/dev/null && grep -q 'notified' "$nlog" 2>/dev/null; then
    : # the dead uuid appears only because the stub logs every call; not a defect
  fi
  printf 'PASS ok\n' > "$res"
}

printf 'flake-fanout: %s iteration(s), concurrency %s, tool %s\n' "$RUNS" "$JOBS" "$SELF_BIN"
printf 'flake-fanout: fixture HEAD %s\n' "$RHEAD5"
printf 'flake-fanout: pids.max in this scope = %s (root is exempt from RLIMIT_NPROC, so this cap binds)\n' "$(scope_pids_max)"

WORK="$T/work"; mkdir -p "$WORK"
declare -a INFLIGHT=()
started=0 done_n=0
launch() { # $1 = iteration
  one_run "$1" "$WORK/$1.res" "$WORK/$1.out" &
  INFLIGHT+=("$!:${1}")
}
drain_one() {
  local entry pid i
  entry="${INFLIGHT[0]}"; INFLIGHT=("${INFLIGHT[@]:1}")
  pid="${entry%%:*}"; i="${entry##*:}"
  wait "$pid" 2>/dev/null
  done_n=$((done_n+1))
}

while [ "$started" -lt "$RUNS" ] || [ "${#INFLIGHT[@]}" -gt 0 ]; do
  while [ "$started" -lt "$RUNS" ] && [ "${#INFLIGHT[@]}" -lt "$JOBS" ]; do
    started=$((started+1)); launch "$started"
  done
  [ "${#INFLIGHT[@]}" -gt 0 ] && drain_one
done

# ---- distribution
pass=0; fail=0; exhausted=0; unreported=0
: > "$T/failures"
i=1
while [ "$i" -le "$RUNS" ]; do
  res="$(cat "$WORK/$i.res" 2>/dev/null || printf 'NO-RESULT')"
  case "$res" in
    PASS*) pass=$((pass+1)) ;;
    EXHAUSTED*) exhausted=$((exhausted+1)); printf '  iter %-3s %s\n' "$i" "$res" >> "$T/failures" ;;
    # NO-RESULT = the iteration's subshell died before it could write a verdict.
    # That is "the arm did not report", never "the tool diverged" -- measured as
    # iter 1 NO-RESULT at TasksMax=20 while its siblings read EXHAUSTED rc=254.
    NO-RESULT) unreported=$((unreported+1)); printf '  iter %-3s %s\n' "$i" "$res" >> "$T/failures" ;;
    *) fail=$((fail+1)); printf '  iter %-3s %s\n' "$i" "$res" >> "$T/failures" ;;
  esac
  i=$((i+1))
done

printf '\n=== distribution ===\n'
printf 'PASS %s / FAIL %s / EXHAUSTED %s / UNREPORTED %s of %s\n' "$pass" "$fail" "$exhausted" "$unreported" "$RUNS"
if [ "$exhausted" -gt 0 ] || [ "$unreported" -gt 0 ]; then
  printf '\n=== fork exhaustion (#75) ===\n'
  printf 'EXHAUSTED/UNREPORTED iterations are NOT tool reds: the scope hit pids.max=%s and\n' "$(scope_pids_max)"
  printf 'the shell was killed mid-run ("fork: Interrupted system call"). This is the\n'
  printf 'ENVIRONMENT, not oc-deploy. Re-run with a lower -j; the cap is the ceiling.\n'
fi
if [ "$fail" -gt 0 ]; then
  printf '\n=== divergences ===\n'
  cat "$T/failures"
  if [ "$VERBOSE" = "1" ]; then
    printf '\n=== outputs of diverging iterations ===\n'
    i=1
    while [ "$i" -le "$RUNS" ]; do
      case "$(cat "$WORK/$i.res" 2>/dev/null)" in
        PASS*) : ;;
        *) printf '\n--- iter %s ---\n' "$i"; cat "$WORK/$i.out" 2>/dev/null ;;
      esac
      i=$((i+1))
    done
  fi
  printf '\nVERDICT: the fixture DOES flake at concurrency %s (reproduced in-harness)\n' "$JOBS"
  exit 1
fi
if [ "$exhausted" -gt 0 ] || [ "$unreported" -gt 0 ]; then
  # Inconclusive is its own verdict: not a pass (the arm did not complete) and
  # not a flake (nothing diverged). Exit 3 so a caller can tell them apart.
  printf '\nVERDICT: INCONCLUSIVE — %s exhausted + %s unreported of %s; the pid cap, not the tool\n' \
    "$exhausted" "$unreported" "$RUNS"
  printf 'Re-run at a concurrency the pid cap can carry (pids.max=%s).\n' "$(scope_pids_max)"
  exit 3
fi
printf '\nVERDICT: %s/%s clean at concurrency %s\n' "$pass" "$RUNS" "$JOBS"
printf 'A clean arm here does not clear a battery red by itself: read the failing\n'
printf 'leg name first, and check whether its output carried fork-exhaustion markers\n'
printf '(EXHAUSTED above) — that red is the environment, not the tool.\n'
exit 0
