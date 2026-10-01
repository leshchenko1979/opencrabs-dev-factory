#!/usr/bin/env bash
# =============================================================================
# tools/tests/run.sh — repeatable test suite for the oc-* CLI tools.
#
# One command to run the whole suite:
#     bash tools/tests/run.sh
#
# Each tool gets its own --selftest AND a dedicated edge-case test that proved
# fatal during the build. Exit 0 only if EVERY test passes; any failure prints
# a line and exits nonzero (1 = test failed, 2 = harness error/tool missing).
#
# The oc-seal-state IFS-join regression here is the one that silently dropped
# pipe operators between jq filters (fix 2026-08-26) — if it ever comes back,
# this suite goes red before anyone trusts a seal.
# =============================================================================
set -u
# --- oc-root bootstrap: resolve the tools dir at ANY depth (tools/lib/oc-root.sh)
_oc_r="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || _oc_r="."; _oc_d="$_oc_r"; while [ "$_oc_r" != "/" ] && [ "$_oc_r" != "." ] && ! { [ -f "$_oc_r/lib/oc-root.sh" ] && [ ! -L "$_oc_r/lib" ]; } && [ "$(basename "$_oc_r")" != "tools" ]; do _oc_r="$(dirname "$_oc_r")"; done
if [ "$(basename "$_oc_r")" = "tools" ]; then _oc_d="$_oc_r"; fi
if [ -f "$_oc_r/lib/oc-root.sh" ] && [ ! -L "$_oc_r/lib" ]; then . "$_oc_r/lib/oc-root.sh"; else OC_TOOLS_DIR="$(cd "$_oc_d" && pwd)"; fi
TOOLS_DIR="$OC_TOOLS_DIR"

# ---- tree fingerprint: battery integrity (2026-09-27) ------------------------
# The battery executes tools FROM THE WORKTREE, so a tool rewritten while the
# run is in progress can be read MID-WRITE -- bash reads scripts incrementally,
# and a tool with an embedded Python body then yields a MIXED generation whose
# legs fail with jq type errors and count drifts. That is a red describing the
# EDIT, not the tool. Measured 2026-09-27: two red receipts (16:22, 17:01) both
# fell inside one lane's edit window, while two quiet runs read PASS (17:13,
# 17:17). A concurrent writer cannot be prevented from here, so the receipt
# STATES whether the tree moved under it instead of implying it did not.
_battery_tree_fp() {
  { find "$TOOLS_DIR" -maxdepth 2 -type f \
      \( -name 'oc-*' -o -name '*.sh' -o -name '*.py' -o -name '*.mjs' \) \
      -not -name '*.pre-*' -not -name '*.bak' -print0 2>/dev/null | sort -z | xargs -0 md5sum 2>/dev/null
    md5sum "$0" 2>/dev/null
  } | md5sum | awk '{print $1}'
}
BATTERY_FP_START="$(_battery_tree_fp)"
PASS=0 FAIL=0
# Battery stays silent in the unified tools log: every suite invocation is a
# synthetic run, not fleet activity (KERNEL batch D0, 2026-08-28).
export OC_TOOLS_NOLOG=1
export OC_ACTOR="test-runner"
# ---- battery timing instrumentation (owner order 2026-09-28) ----------------
# The owner asked whether --jobs actually parallelises; the answer was readable
# NOWHERE. No per-section timing existed (the only date +%s in this file is a
# leg, not the driver), and a run's chunk transcripts are removed at the end of
# that same run -- so a 20-minute wall was unfalsifiable: "one greedy section"
# and "a throttle that never releases" predict the same wall, and neither had a
# receipt. These fields report what the driver DID: per-section wall time, its
# offset within the run (the wave structure), the aggregate wall, and the
# MAXIMUM CONCURRENCY OBSERVED -- the direct test of whether the pool ever held
# --jobs sections at once.
BATTERY_T0="$(date +%s%N)"
BATTERY_WALL_MS=0
BATTERY_SECTIONS_JSON='[]'
BATTERY_SECTIONS_TSV=""

# ---- helpers ---------------------------------------------------------------
note()  { printf '%s\n' "$*"; }
ok()    { PASS=$((PASS+1)); note "  ok   - $*"; }
bad()   { FAIL=$((FAIL+1)); note "  FAIL - $*"; if [ -n "${FAIL_LOG:-}" ]; then printf '  FAIL - %s\n' "$*" >> "$FAIL_LOG"; fi; }
# tools/ is grouped by KIND (owner order 2026-09-25): oc-* live in functional
# subdirs. Resolve by NAME so a tool can be moved without touching every leg.
tool_path() {
  [ -x "$TOOLS_DIR/$1" ] && { printf '%s\n' "$TOOLS_DIR/$1"; return 0; }
  for _d in "$TOOLS_DIR"/*/; do
    [ -d "$_d" ] || continue
    case "${_d%/}" in */lib|*/tests|*/archive|*/docs|*/instruments) continue ;; esac
    [ -x "$_d$1" ] && { printf '%s\n' "$_d$1"; return 0; }
  done
  return 1
}
tool()  { [ -x "$(tool_path "$1" 2>/dev/null)" ] || { bad "missing tool: $1"; return 1; } }
section() { note ""; note "== $1 =="; }
# record — a continuation line's detail: printed AND appended to the fail
# transcript. `tee -a` is byte-transparent on stdout, so a GREEN run stays
# byte-identical (continuations appear only under a FAIL row).
record() { if [ -n "${FAIL_LOG:-}" ]; then tee -a "$FAIL_LOG"; else cat; fi; }
# Fork #453 (2026-09-20): a failing --selftest used to be a dead end — the
# tool's own output went to /dev/null, so a flake left a bare tool name and
# nothing to diagnose. Capture it and surface a bounded window of it under the
# FAIL row. The success path prints NOTHING extra: parallel mode re-counts rows
# by prefix (grep -c '^  ok ' / '^  FAIL '), and a green transcript must stay
# byte-identical. Continuation lines are indented under a '| ' marker, which
# matches neither prefix.
#
# THE WINDOW MUST NOT GUESS WHERE THE FAILURE IS. A tail-only window was
# measured losing the failing assertion outright: oc-watcher-audit prints its
# assertions in order and its summary last, so its one FAIL sat in the first 7
# lines while tail -20 showed the 19 PASSes that followed — a live flake whose
# diagnosis was thrown away (2026-09-20, on the very run that was to be this
# fix's own receipt). So up to 40 lines are shown in FULL, and beyond that the
# head AND the tail are shown with the elided middle counted: a selftest marks
# the failure at the start (assertion order) or at the end (named on the way
# out), and which end it is cannot be known in advance.
run_capture() { # $1 = label, $2.. = command
  local label="$1"; shift
  local out rc n
  out="$(mktemp)"
  "$@" >"$out" 2>&1; rc=$?
  if [ "$rc" -eq 0 ]; then
    ok "$label"
  else
    bad "$label"
    n="$(wc -l < "$out")"
    if [ "$n" -le 40 ]; then
      sed 's/^/       | /' "$out" | record
    else
      note "       | ... $((n - 40)) line(s) omitted from the middle"
      head -n 20 "$out" | sed 's/^/       | /' | record
      note "       | ..."
      tail -n 20 "$out" | sed 's/^/       | /' | record
    fi
  fi
  rm -f "$out"
  return "$rc"
}
run_selftest() {
  local t="$1"
  _tp="$(tool_path "$t" 2>/dev/null)"
  if [ -z "$_tp" ] || [ ! -x "$_tp" ]; then bad "$t missing or not executable"; return 1; fi
  # M2-22 (2026-09-12): the state dir must be removed after the run — this was
  # the volume driver of the /tmp leak (one dir per tool per battery run).
  # A plain `rm -rf` right after the call, NOT a global trap: chunk mode
  # re-extracts and sources the prelude (everything before the first `# ---- N`
  # marker) once per section, so a prelude-level trap would be set N times.
  local sd _rc _st
  sd="$(mktemp -d)"
  # #753: every selftest is BOUNDED. run_capture() has no bound of its own, so a
  # selftest that hangs used to hang the whole battery -- silently, forever.
  # Measured 2026-10-01: six detached oc-harvest-sweep --selftest runs spun ~5 h
  # at 37-39% CPU each (load ~11 on 4 cores) and nothing reaped them.
  # 1800s default: the longest battery section measured is 296.5s (oc-ledger
  # kernel, tools/tests/battery-last.json ts=2026-10-01T13:51:50Z, PASS 310/0),
  # so this cannot red a slow-but-legitimate selftest. Override: OC_SELFTEST_TIMEOUT.
  # --kill-after reaps a child that ignores TERM; timeout signals the whole
  # process group, so a selftest's own grandchildren die with it.
  _st="${OC_SELFTEST_TIMEOUT:-1800}"
  run_capture "$t --selftest" timeout --kill-after=30 "$_st" env OC_DEPLOY_STATE_DIR="$sd" "$_tp" --selftest
  _rc=$?
  [ "$_rc" = 124 ] && note "       | $t --selftest HUNG -- killed at the ${_st}s bound (#753)"
  rm -rf "$sd"
  return "$_rc"
}

# ---- battery driver: --jobs N parallel mode + internal --chunk mode (v0.4.131)
# Sections are fully isolated (each builds its own mktemp state, no shared
# mutable state), so they run concurrently. --jobs N spawns one chunk per
# section (default 1 = sequential, unchanged). Output is re-aggregated in
# section order so the transcript matches a sequential run line-for-line.
# Chunk mode re-extracts prelude+section from this file and sources it —
# BATTERY_IN_CHUNK guards the re-entry so sourcing the extracted prelude
# (which contains this driver) cannot recurse.
BATTERY_MODE="sequential"
extract_chunk() { # $1 = 1-based section chunk; prints prelude + that section
  # POSITIONAL CONSTRAINT (measured 2026-09-25): the `/^verdict=PASS/ { exit }`
  # guard below is what stops the prelude extraction at the receipt write. A
  # numbered section placed AFTER that line therefore extracts to an EMPTY chunk
  # and runs zero legs in parallel mode -- while the run still prints a clean
  # summary and the PASS count simply does not move. Section 78 landed there and
  # was invisible. Put new sections ABOVE the receipt write, and the leg in
  # section 78 asserts the last section stays reachable.
  awk -v want="$1" '
    /^# ---- [0-9]/ { n++; insec = (n == want); next }
    /^verdict=PASS/ { exit }
    n == 0 || insec { print }
  ' "$0"
}
if [ "${1:-}" = "--chunk" ] && [ -n "${2:-}" ] && [ -z "${BATTERY_IN_CHUNK:-}" ]; then
  export BATTERY_IN_CHUNK=1
  C="$(mktemp)"; extract_chunk "$2" > "$C"
  # shellcheck disable=SC1090
  source "$C"; rm -f "$C"
  exit $(( FAIL > 0 ? 1 : 0 ))
fi

# ---- single-flight lock: ONE battery run at a time (#449) -------------------
# tools/tests/battery-last.json is ONE canonical path shared by every lane, and
# this script writes it from two sites with no lock — so two concurrent runs
# clobber each other's receipt (measured 2026-09-20: commit 284b8456 committed a
# FAIL receipt under a "pass 213, fail 0" message) and the extra load flakes the
# timing-sensitive oc-ship-chain detach-survival pair. The whole run is
# serialized here. The canonical path is KEPT because consumers read it — a
# per-lane receipt path would break them.
#
# Placement is load-bearing: this sits AFTER the --chunk branch above and is
# guarded on BATTERY_IN_CHUNK, because a --chunk child takes its branch and
# exits before reaching this line, and the prelude sourced INSIDE a child sees
# BATTERY_IN_CHUNK=1. Locking any earlier would deadlock every child against
# its own parent. rc 2 = harness condition, never a test verdict.
if [ -z "${BATTERY_IN_CHUNK:-}" ]; then
  BATTERY_LOCK="${OC_BATTERY_LOCK:-${TMPDIR:-/tmp}/oc-battery.lock}"
  BATTERY_LOCK_WAIT="${OC_BATTERY_LOCK_WAIT:-900}"
  exec 9>"$BATTERY_LOCK" || { note "battery: cannot open lock file $BATTERY_LOCK"; exit 2; }
  if ! flock -n 9; then
    note "battery: another run holds $BATTERY_LOCK — waiting up to ${BATTERY_LOCK_WAIT}s"
    if ! flock -w "$BATTERY_LOCK_WAIT" 9; then
      note "battery: lock not released within ${BATTERY_LOCK_WAIT}s — NOT a test failure and NOT a verdict."
      note "battery: re-run once the holder finishes, or raise the budget with OC_BATTERY_LOCK_WAIT=<sec>."
      exit 2
    fi
  fi
fi

JOBS="${OC_BATTERY_JOBS:-$(nproc 2>/dev/null || echo 4)}"
if [ "${1:-}" = "--jobs" ] && [ -n "${2:-}" ]; then JOBS="$2"; shift 2; fi
case "${1:-}" in --jobs=*) JOBS="${1#--jobs=}"; shift ;; esac
# ---- cgroup isolation (#720): never run the battery inside the daemon's unit -
# Every command a lane runs inherits the daemon's cgroup
# (`.../app.slice/opencrabs-ops.service`), whose wall is MemoryHigh == MemoryMax
# == 1536 MiB with swap exhausted -- measured 98.6% full WHILE IDLE -- and whose
# OOMPolicy=kill means a test allocation does not merely die itself: systemd
# tears the whole unit down and takes the daemon with it. The test processes are
# small (tens of MiB); the hazard is CO-TENANCY with a full wall, so no test
# diet can fix it -- the run must not be in that cgroup at all. It re-execs
# itself into a transient user scope (a SIBLING of the service, outside its
# accounting) with its own caps, and the receipt names the cgroup it ACTUALLY
# ran in so the isolation is a durable claim, not a story.
#
# Placement is load-bearing: this sits AFTER the --chunk branch (whose children
# take their branch and exit, never reaching here) and AFTER the single-flight
# lock (so a queued run blocks on the lock rather than re-exec'ing under it).
# BATTERY_CGROUP_ISOLATED guards the re-exec to ONE level: the transient child
# carries the flag, so it runs the suite instead of recursing.
#
# Fails OPEN. A missing systemd-run, no user manager, an unreadable cgroup, or a
# refusal by the re-exec all leave the run on its current path with one WARNING
# -- a harness that refuses to run is worse than one running in the wrong
# cgroup. Opt out with --no-cgroup or OC_BATTERY_NO_CGROUP=1.
BATTERY_NO_CGROUP="${OC_BATTERY_NO_CGROUP:-}"
[ -n "${BATTERY_NO_CGROUP:-}" ] || { for _a in "$@"; do [ "$_a" = "--no-cgroup" ] && BATTERY_NO_CGROUP=1; done; }
# The cgroup reader is a FUNCTION so section 85 can drive this block with a
# synthetic path. The branch it takes depends on where the RUN sits -- a
# .service unit on this box, no systemd at all in CI -- so a test that only ever
# exercises the branch its own environment happens to take asserts nothing.
# Production carries no test-only override; the test redefines the function.
battery_cgroup_path() { sed -n 's/^0:://p' /proc/self/cgroup 2>/dev/null | head -n1; }
if [ -z "${BATTERY_IN_CHUNK:-}" ] && [ -z "${BATTERY_CGROUP_ISOLATED:-}" ] && [ -z "${BATTERY_NO_CGROUP:-}" ]; then
  _oc_sr="$(command -v systemd-run 2>/dev/null || true)"
  _oc_cg="$(battery_cgroup_path)"
  _oc_mgr="$(command -v systemctl 2>/dev/null || true)"
  # Read the LEAF unit, not the whole path: every user-manager cgroup sits under
  # `user@0.service`, so a substring test on the full path calls ANY user cgroup
  # a service -- a transient `.scope` leaf included, which made the "already
  # isolated" branch unreachable and re-exec'd a scope's own children (section 85
  # LEG 3 caught this). The last path segment names the unit we are actually in.
  case "${_oc_cg##*/}" in *.service) _oc_svc=1 ;; *) _oc_svc=0 ;; esac
  if [ -z "$_oc_sr" ]; then
    note "battery: WARNING: no systemd-run -- running in ${_oc_cg:-?} (NOT isolated from the daemon cgroup, #720)"
  elif [ -z "$_oc_mgr" ] || ! systemctl --user is-system-running >/dev/null 2>&1; then
    note "battery: WARNING: no user systemd manager -- running in ${_oc_cg:-?} unisolated (#720)"
  elif [ -z "$_oc_cg" ]; then
    note "battery: WARNING: cgroup path unreadable -- running unisolated (#720)"
  elif [ "$_oc_svc" = "0" ]; then
    note "battery: already outside a service cgroup (${_oc_cg}) -- no isolation needed"
  else
    # Fail OPEN -- which a bare `exec` cannot do by itself: it never returns, so
    # a REFUSED re-exec would REPLACE the battery with systemd-run's own exit
    # code, and a harness error would be read as a RED verdict. One throwaway
    # scope creation settles whether the caps are accepted BEFORE the real one
    # replaces us. The property list lives HERE, once: the probe and the real
    # exec share one array, so they can never diverge.
    _oc_caps=(--user --scope --quiet \
      -p MemoryMax=1024M -p MemorySwapMax=512M -p CPUQuota=300% -p TasksMax=128)
    if "$_oc_sr" "${_oc_caps[@]}" true; then
      export BATTERY_CGROUP_ISOLATED=1 BATTERY_CGROUP_PARENT_CG="$_oc_cg"
      note "battery: re-exec into a transient scope to isolate from the daemon cgroup (#720)"
      exec "$_oc_sr" "${_oc_caps[@]}" "$0" "$@"
    fi
    note "battery: WARNING: could not create a transient scope -- running in ${_oc_cg} unisolated (#720)"
  fi
fi
# The cgroup this run is ACTUALLY in, read fresh -- and whether the re-exec
# moved it. `isolated=true` asserts only what is observable: the flag is set AND
# the path differs from the one the re-exec started in.
BATTERY_SELF_CGROUP="$(sed -n 's/^0:://p' /proc/self/cgroup 2>/dev/null | head -n1)"
BATTERY_SELF_CGROUP_ISO=false
if [ "${BATTERY_CGROUP_ISOLATED:-0}" = "1" ] && [ -n "$BATTERY_SELF_CGROUP" ] \
   && [ "$BATTERY_SELF_CGROUP" != "${BATTERY_CGROUP_PARENT_CG:-}" ]; then
  BATTERY_SELF_CGROUP_ISO=true
fi

# ---- red-receipt transcript -------------------------------------------------
# Defect (HQ item 5, 2026-09-22): emit_summary wrote battery-last.json durably
# while the transcript went only to stdout, so a committed red receipt
# (228 pass / 1 fail, commit d1f63d9f) recorded THAT a leg failed and nothing
# about WHICH — undiagnosable by the next reader, and its /tmp transcript was
# gone. The receipt is a durable artifact; its diagnosis must be one too.
#
# Contract: a RED run leaves $FAIL_LOG carrying the FAIL rows and their
# continuation lines, and the receipt JSON names that path; a GREEN run REMOVES
# any stale log, so the log's PRESENCE is itself the red signal.
FAIL_LOG="$TOOLS_DIR/tests/battery-last-fail.log"
FAIL_LOG_REL="tools/tests/battery-last-fail.log"
# Only the PARENT truncates: chunk children append to this same path, and a
# child truncating it would erase rows its siblings already wrote.
if [ -z "${BATTERY_IN_CHUNK:-}" ]; then : > "$FAIL_LOG" 2>/dev/null || true; fi
# ---- self-contained red receipt (#614) --------------------------------------
# Defect (measured 2026-09-26): the receipt NAMED $FAIL_LOG while the log's life
# was ONE RUN -- :179 truncates it the moment a queued run starts, and
# finalize_fail_log removes it on green. A reader arriving after the next run
# found a FAIL receipt pointing at 0 bytes: the #517 defect one step out. The
# receipt is the durable artifact, so the diagnosis rides IN it.
# Contract: on RED the receipt carries `fail_rows` (the FAIL rows and their
# continuation lines, bounded by FAIL_ROWS_CAP) plus `fail_rows_truncated`, so
# no later run can destroy the evidence. $FAIL_LOG is kept for immediate reading
# (tail/grep on a large dump) and is no longer the durable half.
# json.dumps, not hand-rolled: a row may carry quotes or backslashes, and a
# string-built array would emit invalid JSON exactly when it is needed.
FAIL_ROWS_CAP="${OC_BATTERY_FAIL_ROWS_CAP:-200}"
battery_capture_fail_rows() {
  FAIL_ROWS_JSON='[]'; FAIL_ROWS_TRUNC='false'
  [ -s "${FAIL_LOG:-}" ] || return 0
  local total; total="$(wc -l < "$FAIL_LOG" 2>/dev/null || echo 0)"
  case "$total" in ''|*[!0-9]*) total=0 ;; esac
  [ "$total" -gt "$FAIL_ROWS_CAP" ] && FAIL_ROWS_TRUNC='true'
  FAIL_ROWS_JSON="$(python3 -c 'import json,sys
cap=int(sys.argv[2])
try: lines=open(sys.argv[1],encoding="utf-8",errors="replace").read().splitlines()
except Exception: print("[]"); raise SystemExit
print(json.dumps(lines[:cap]))' "$FAIL_LOG" "$FAIL_ROWS_CAP" 2>/dev/null)"
  [ -n "$FAIL_ROWS_JSON" ] || FAIL_ROWS_JSON='[]'
  return 0
}
finalize_fail_log() {
  if [ "$FAIL" -eq 0 ]; then rm -f "$FAIL_LOG"; FAIL_LOG_FIELD=""; else FAIL_LOG_FIELD="$FAIL_LOG_REL"; fi
}
# ---- timing collection (see the defaults block at the top of this prelude) --
battery_collect_timing() { # $1 = section count, $2 = per-chunk dir ($PT)
  local nch="$1" pt="$2" k s e
  BATTERY_SECTIONS_TSV="$pt/timing.tsv"
  : > "$BATTERY_SECTIONS_TSV" 2>/dev/null || BATTERY_SECTIONS_TSV=""
  for k in $(seq 1 "$nch"); do
    [ -s "$pt/$k.ms" ] || continue
    read -r s e < "$pt/$k.ms" 2>/dev/null || continue
    case "${s:-}" in ''|*[!0-9]*) continue ;; esac
    case "${e:-}" in ''|*[!0-9]*) continue ;; esac
    printf '%s\t%s\t%s\t%s\n' "$k" "$s" "$e" "$(( e - s ))" >> "$BATTERY_SECTIONS_TSV"
  done
  BATTERY_SECTIONS_JSON="$(battery_timing_json "$BATTERY_SECTIONS_TSV" "$0")"
  [ -n "$BATTERY_SECTIONS_JSON" ] || BATTERY_SECTIONS_JSON='[]'
  return 0
}

# Emits the receipt's `timing` object. max_concurrency is the peak overlap of
# the section intervals -- the direct answer to "did the pool ever actually
# hold $JOBS sections?", which a duration-sum cannot answer.
battery_timing_json() {
  python3 - "$1" "$2" <<'OC_TIMING_JSON' 2>/dev/null
import json, sys
rows = []
try:
    for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 4:
            continue
        try:
            rows.append((int(p[0]), int(p[1]), int(p[2]), int(p[3])))
        except ValueError:
            continue
except OSError:
    pass
titles, n = {}, 0
try:
    for line in open(sys.argv[2], encoding="utf-8", errors="replace"):
        if line.startswith("# ---- ") and line[7:8].isdigit():
            n += 1
            titles[n] = line[7:].strip()
except OSError:
    pass
events = []
for k, s, e, d in rows:
    events.append((s, 1))
    events.append((e, -1))
events.sort()
depth = peak = 0
for _, delta in events:
    depth += delta
    if depth > peak:
        peak = depth
slow = [{"n": k, "ms": d, "start_ms": s, "end_ms": e, "title": titles.get(k, "")}
        for k, s, e, d in sorted(rows, key=lambda r: -r[3])[:10]]
print(json.dumps({"max_concurrency": peak, "section_count": len(rows),
                  "sum_ms": sum(r[3] for r in rows), "slowest": slow}))
OC_TIMING_JSON
}

# Transcript half: one summary line plus the slowest few, so the wall time is
# attributable from the run's OWN output instead of from a separate experiment.
battery_timing_lines() {
  [ "${BATTERY_WALL_MS:-0}" -gt 0 ] 2>/dev/null || return 0
  note "  timing: wall=$(( BATTERY_WALL_MS / 1000 ))s  jobs=${JOBS:-?}  mode=${BATTERY_MODE:-?}"
  [ -s "${BATTERY_SECTIONS_TSV:-}" ] || return 0
  python3 - "$BATTERY_SECTIONS_TSV" <<'OC_TIMING_SHOW' 2>/dev/null || return 0
import sys
rows = []
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 4:
        continue
    try:
        rows.append((int(p[0]), int(p[1]), int(p[2]), int(p[3])))
    except ValueError:
        continue
if not rows:
    raise SystemExit
events = []
for k, s, e, d in rows:
    events.append((s, 1))
    events.append((e, -1))
events.sort()
depth = peak = 0
for _, delta in events:
    depth += delta
    if depth > peak:
        peak = depth
longest = max(rows, key=lambda r: r[3])
print("  sections: %d  sum=%ds  max-concurrency=%d  longest=%ds (#%d)"
      % (len(rows), sum(r[3] for r in rows) // 1000, peak,
         longest[3] // 1000, longest[0]))
print("  slowest: " + "  ".join("#%d=%ds" % (k, d // 1000)
                               for k, s, e, d in sorted(rows, key=lambda r: -r[3])[:6]))
OC_TIMING_SHOW
}
emit_summary() {
  local verdict=PASS; [ "$FAIL" -eq 0 ] || verdict=FAIL
  finalize_fail_log
  battery_capture_fail_rows
  local _fpe _changed; _fpe="$(_battery_tree_fp)"
  _changed=false; [ "$_fpe" = "$BATTERY_FP_START" ] || _changed=true
  printf '{\n  "path": "%s",\n  "ts": "%s",\n  "pass": %d,\n  "fail": %d,\n  "verdict": "%s",\n  "mode": "%s",\n  "fail_log": "%s",\n  "fail_rows": %s,\n  "fail_rows_truncated": %s,\n  "tree_changed": %s,\n  "cgroup": "%s",\n  "cgroup_isolated": %s,\n  "wall_ms": %s,\n  "timing": %s\n}\n' \
    "$TOOLS_DIR/tests/battery-last.json" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$PASS" "$FAIL" "$verdict" "$BATTERY_MODE" "$FAIL_LOG_FIELD" \
    "$FAIL_ROWS_JSON" "$FAIL_ROWS_TRUNC" "$_changed" "$BATTERY_SELF_CGROUP" "$BATTERY_SELF_CGROUP_ISO" "$BATTERY_WALL_MS" "$BATTERY_SECTIONS_JSON" \
    > "$TOOLS_DIR/tests/battery-last.json"
  [ "$_changed" = false ] || note "  WARNING: the tools tree CHANGED during this run — a red here may describe the edit, not the tool; re-run on a quiet tree"
  note ""
  note "=============================="
  note "  PASS: $PASS   FAIL: $FAIL   (receipt: tools/tests/battery-last.json = $verdict, mode: $BATTERY_MODE)"
  battery_timing_lines
  note "=============================="
  [ "$FAIL" -eq 0 ] || note "tests FAILED (nonzero exit below)"
  return $(( FAIL > 0 ? 1 : 0 ))
}
if [ "${BATTERY_IN_CHUNK:-0}" = "0" ] && [ "$JOBS" -gt 1 ]; then
  BATTERY_MODE="parallel jobs=$JOBS"
  NCH="$(grep -cE '^# ---- [0-9]' "$0")"
  PT="$(mktemp -d -t oc-battery-pt.XXXXXX)"
  RUN_SCRIPT="$(readlink -f "$0" 2>/dev/null || echo "$0")"
  for k in $(seq 1 "$NCH"); do
    # Each child records its own [start,end] as ms offsets from the PARENT's
    # clock, so the receipt shows the wave structure and the critical path.
    ( _bs="$(date +%s%N)"
      bash "$RUN_SCRIPT" --chunk "$k" > "$PT/$k.log" 2>&1
      _be="$(date +%s%N)"
      printf '%s %s\n' "$(( (_bs - BATTERY_T0) / 1000000 ))" "$(( (_be - BATTERY_T0) / 1000000 ))" > "$PT/$k.ms" 2>/dev/null ) &
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 0.05; done
  done
  wait
  BATTERY_WALL_MS="$(( ($(date +%s%N) - BATTERY_T0) / 1000000 ))"
  battery_collect_timing "$NCH" "$PT"
  PASS=0; FAIL=0
  for k in $(seq 1 "$NCH"); do
    [ -f "$PT/$k.log" ] && cat "$PT/$k.log"
    o="$(grep -c '^  ok ' "$PT/$k.log" 2>/dev/null || true)"; f="$(grep -c '^  FAIL ' "$PT/$k.log" 2>/dev/null || true)"
    PASS=$((PASS + ${o:-0})); FAIL=$((FAIL + ${f:-0}))
  done
  rm -rf "$PT"
  emit_summary
  exit $?
fi

# ---- 00. lib/oc-log.sh (unified tools log, KERNEL batch D0) -----------------
section "lib/oc-log.sh (unified tools log)"
if [ -f "$TOOLS_DIR/lib/oc-log.sh" ]; then
  bash -n "$TOOLS_DIR/lib/oc-log.sh" && ok "lib syntax (bash -n)" || bad "lib syntax"
  d="$(mktemp -d)"
  mkdir -p "$d/lib"; cp "$TOOLS_DIR/lib/oc-log.sh" "$d/lib/"
  cat > "$d/oc-demo" <<'DEMO'
#!/usr/bin/env bash
set -u
source "$(dirname "$0")/lib/oc-log.sh"
oc_log_init "oc-demo" "$@"
trap 'oc_log_finish $?' EXIT
rc="${1:-0}"
case "$rc" in --selftest|selftest) rc=0 ;; esac
exit "$rc"
DEMO
  chmod +x "$d/oc-demo"
  L="$d/tools.log"
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$L" "$d/oc-demo" 0
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$L" "$d/oc-demo" 7 --some-arg
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$L" "$d/oc-demo" --selftest
  [ -f "$L" ] && [ "$(wc -l < "$L")" -eq 2 ] && ok "exactly 2 lines: exit0 + exit7 (--selftest suppressed)" \
    || bad "expected 2 lines, got $([ -f "$L" ] && wc -l < "$L" || echo none)"
  jq -e 'select(.tool=="oc-demo" and .exit==0)' "$L" >/dev/null 2>&1 && ok "JSONL valid, exit-0 line" || bad "exit-0 line malformed"
  jq -e 'select(.tool=="oc-demo" and .exit==7 and (.args|contains("--some-arg")))' "$L" >/dev/null 2>&1 \
    && ok "exit-7 line carries args" || bad "exit-7 line wrong"
  jq -e 'select(has("ts") and has("secs") and has("extra"))' "$L" >/dev/null 2>&1 \
    && ok "schema fields ts/secs/extra present" || bad "schema fields missing"
  # suppression via env alone (no --selftest)
  OC_TOOLS_NOLOG=1 OC_TOOLS_LOG="$L" "$d/oc-demo" 3
  [ "$(wc -l < "$L")" -eq 2 ] && ok "OC_TOOLS_NOLOG=1 suppresses" || bad "env suppression failed"
  # M2-21 (2026-09-12): the BARE `selftest` SUBCOMMAND must suppress too.
  # oc-deploy:2976 dispatches `--selftest|selftest) selftest "$@" ;;` as ONE
  # case arm, so a flag-only predicate let a bare-subcommand selftest log every
  # fixture child it spawned into the PRODUCTION tools.log -- 93 rows per run,
  # six phantom shas across two weeks, read back by oc-ship-audit as ORPHANED
  # dispatches (rc=1, gating `oc-ledger commit-pending`).
  L2="$d/tools2.log"
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$L2" "$d/oc-demo" selftest
  [ -s "$L2" ] && bad "bare 'selftest' subcommand logged a row (M2-21)" \
               || ok "bare 'selftest' subcommand suppressed (M2-21)"
  # separate log: a leak in the assertion above must not cascade into this one
  L3="$d/tools3.log"
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$L3" "$d/oc-demo" 0 selftest
  [ "$(wc -l < "$L3")" -eq 1 ] \
    && ok "a 'selftest' VALUE does not suppress a real invocation (M2-21)" \
    || bad "non-first 'selftest' silenced a real invocation (M2-21)"
  # ---- #537: oc_has — SIGPIPE-free literal substring test --------------------
  # The fleet's `echo "$out" | grep -q PAT` assertion is a latent FALSE NEGATIVE
  # under pipefail: `grep -q` exits at the FIRST match, the writer takes SIGPIPE,
  # and the pipeline reports 141 DESPITE the match. oc_has matches inside the
  # shell — no pipe, so the status cannot be the writer's. The needle is QUOTED
  # in the case arm: unquoted, real tokens in this corpus are PARSE-TIME syntax
  # errors (`Draft: true (--draft)`, `age: 0.3h`), not wrong matches.
  OHF="$d/oc_has.out"
  TOOLS_DIR="$TOOLS_DIR" bash -c '
    set -u; set -o pipefail
    . "$TOOLS_DIR/lib/oc-log.sh"
    r() { if oc_has "$2" "$3"; then g=0; else g=1; fi
          if [ "$g" = "$4" ]; then printf "ok %s\n" "$1"
          else printf "FAIL %s (want=%s got=%s)\n" "$1" "$4" "$g"; fi; }
    r present       "the fix is in origin/main"    "origin/main"            0
    r absent        "the fix is in origin/main"    "nowhere"                1
    r parens        "Draft: true (--draft) here"   "Draft: true (--draft)"  0
    r space         "state backlog=11 (>= 10) now" "backlog=11 (>= 10)"     0
    r empty         "anything at all"              ""                       0
    r metachar      "a*b?c[d] literal"             "*b?c[d]"                0
    r glob-literal  "plain text"                   "*"                      1
  ' > "$OHF" 2>&1
  while IFS= read -r _ohl; do
    case "$_ohl" in
      ok\ *)   ok "oc_has: ${_ohl#ok }" ;;
      FAIL\ *) bad "oc_has: ${_ohl#FAIL }" ;;
    esac
  done < "$OHF"
  # size-independence: a 2 MB payload must still read as a match (the idiom is
  # 40/40 wrong on exactly this shape; oc_has is deterministic here).
  OHL="$(TOOLS_DIR="$TOOLS_DIR" bash -c '
    set -u; set -o pipefail
    . "$TOOLS_DIR/lib/oc-log.sh"
    big="$(printf "HIT\n"; head -c 2000000 /dev/zero | tr "\0" "x")"
    oc_has "$big" HIT && echo MATCH || echo MISS
  ' 2>&1)"
  [ "$OHL" = "MATCH" ] && ok "oc_has: 2 MB payload with newline after match -> MATCH (idiom: 40/40 wrong)" \
    || bad "oc_has: 2 MB payload -> '$OHL'"
  [ "$(grep -c '^oc_has()' "$TOOLS_DIR/lib/oc-log.sh")" -eq 1 ] \
    && ok "oc_has: defined exactly once in lib/oc-log.sh" \
    || bad "oc_has: definition count is not 1"
  rm -rf "$d"

else
  bad "lib/oc-log.sh missing"
fi

# ---- 00b. unified-log WIRE test (real tool -> tmp OC_TOOLS_LOG) -------------
section "unified-log wire (real tool -> tmp log)"
if tool oc-attrib; then
  wd="$(mktemp -d)"
  WL="$wd/tools.log"
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$WL" "$TOOLS_DIR/state/oc-attrib" --repo /root/opencrabs --deployed >/dev/null 2>&1
  wrc=$?
  # rc=0 normal; rc=4 = empty range (prev_sha==deployed or no commits in range) —
  # tool-correct on degenerate live marker state (seen 2026-08-31, double swap-execute)
  case $wrc in 0|4) wrc_ok=1;; *) wrc_ok=0;; esac
  wjq='select(.tool=="oc-attrib" and .exit=='"$wrc"' and (.args|contains("--deployed")))'
  [ $wrc_ok -eq 1 ] && [ -f "$WL" ] && [ "$(wc -l < "$WL")" -eq 1 ] \
    && jq -e "$wjq" "$WL" >/dev/null 2>&1 \
    && ok "wire: 1 JSONL line, tool/exit/args correct" || bad "wire test: rc=$wrc lines=$([ -f "$WL" ] && wc -l < "$WL" || echo none)"
  rm -rf "$wd"
fi

# ---- 00c. the ACTOR contract on a VENDORED python tool (#749a) --------------
# oc-questions re-implements, in Python, the actor resolution that
# tools/lib/oc-log.sh does in shell -- and it read OPENCRABS_SESSION_ID ALONE.
# So every caller that set OC_ACTOR (which the owner rule of 2026-08-30 requires
# of every oc-* invocation) was logged as actor="unknown" and could not be
# traced to a lane. Assert the ROW, not the source line: the vendor manifest's
# declared delta keeps the BYTES honest, but says nothing about what a row
# actually carries. Control (run by hand, decisive): neutering the actor line
# back to upstream's form makes this leg FAIL -- measured 2026-10-01.
if tool oc-questions; then
  wqd="$(mktemp -d)"
  WQ="$wqd/q.log"
  OC_TOOLS_NOLOG=0 OC_TOOLS_LOG="$WQ" OC_ACTOR="battery-actor-probe" \
    "$TOOLS_DIR/state/oc-questions" list >/dev/null 2>&1
  jq -e 'select(.tool=="oc-questions" and .actor=="battery-actor-probe")' "$WQ" >/dev/null 2>&1 \
    && ok "oc-questions row carries OC_ACTOR, not the session id (#749a)" \
    || bad "oc-questions row did NOT carry OC_ACTOR (#749a): $(tail -1 "$WQ" 2>/dev/null | cut -c1-120)"
  rm -rf "$wqd"
fi

# ---- 1. oc-order-validate --------------------------------------------------
section "oc-order-validate"
run_selftest oc-order-validate
if tool oc-order-validate; then
  "$TOOLS_DIR/ship/oc-order-validate" --no-such-arg >/dev/null 2>&1; [ $? -eq 1 ] && ok "unknown arg -> 1 (usage)" || bad "unknown arg -> expected 1"
fi

# ---- 02. oc-job-verify -----------------------------------------------------
section "oc-job-verify"
run_selftest oc-job-verify

# ---- 03. oc-artifact-verify ------------------------------------------------
section "oc-artifact-verify"
run_selftest oc-artifact-verify

# ---- 04. oc-seal-state -----------------------------------------------------
# The REGRESSION test: multi-filter merges must keep the pipe operators.
# The fix was IFS='|' (was IFS=' | ' which joined with a space, dropping the
# pipes between jq filters -> silent data loss on .sha + .feature_presence).
section "oc-seal-state (incl. IFS-join regression)"
run_selftest oc-seal-state
if tool oc-seal-state; then
  d="$(mktemp -d)"
  printf '{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","run_id":1,"name":"keep-me"}' > "$d/b.json"
  printf '{"orders":[]}' > "$d/o.json"
  S="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  OUT="$("$TOOLS_DIR/ship/oc-seal-state" --baseline "$d/b.json" --orders "$d/o.json" \
    --sha "$S" --run-id 42 --marker width=1600 --found 1 --dry-run)"
  rc=$?
  [ "$rc" -eq 0 ] || { bad "seal merge exit=$rc (expected 0)"; rm -rf "$d"; }
  # multi-filter: BOTH .sha AND .feature_presence must survive the join
  sha_ok="$(printf '%s' "$OUT" | jq -r '.sha==$e' --arg e "$S")"
  fp_ok="$(printf '%s' "$OUT" | jq -r '.feature_presence["width=1600"].found == 1')"
  [ "$sha_ok" = "true" ] && [ "$fp_ok" = "true" ] && ok "IFS multi-filter merge: sha + feature_presence both applied" \
    || bad "IFS multi-filter merge regressed (sha=$sha_ok fp=$fp_ok)"
  rm -rf "$d"
fi

# ---- 00b. lib/oc-embed.sh (F-M5, v0.4.77): direct unit coverage -------------
section "lib/oc-embed.sh (job-name embed decoder)"
if [ -f "$TOOLS_DIR/lib/oc-embed.sh" ]; then
  bash -n "$TOOLS_DIR/lib/oc-embed.sh" && ok "embed-lib syntax (bash -n)" || bad "embed-lib syntax"
  # shellcheck disable=SC1091
  . "$TOOLS_DIR/lib/oc-embed.sh"
  out="$(oc_decode_job_embed "Linux amd64 (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, telegram)")"
  [ "$out" = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|telegram" ] \
    && ok "embed: well-formed job name -> sha|features" || bad "embed decode got: '$out'"
  out="$(oc_decode_job_embed "Linux amd64 (bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, local-stt,local-tts)")"
  [ "$out" = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb|local-stt,local-tts" ] \
    && ok "embed: comma feature set survives" || bad "embed comma-set got: '$out'"
  out="$(oc_decode_job_embed "ORDER gates / validate (no embed here)")"
  [ -z "$out" ] && ok "embed: ORDER job without embed -> empty" || bad "embed no-embed got: '$out'"
  out="$(oc_decode_job_embed "Linux amd64 (shortsha, x)")"
  [ -z "$out" ] && ok "embed: non-40-hex parenthetical -> empty" || bad "embed short-sha got: '$out'"
  # CALLER-PREFIXED job names (HQ request, 2026-09-21). The carrier CI refactor
  # (commit 0e81404c8 on ci/quick-build-linux) split the two lane workflows into
  # thin shells calling one shared workflow_call body, and GitHub renders every
  # called job as "<caller> / <called>": `ship / Linux amd64 (<sha>, <features>)`,
  # `gate / PR-lane gates (<sha>)`. The anchor is the parenthetical, so the prefix
  # is harmless TODAY — but every fixture above is unprefixed, so nothing GUARDED
  # that: a future name shape could break the ship lane with a green battery.
  # This case and the one below cover a slash WITH an embed; the existing
  # "ORDER gates / validate" case covers a slash WITHOUT one. Both matter.
  out="$(oc_decode_job_embed "ship / Linux amd64 (aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, telegram)")"
  [ "$out" = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|telegram" ] \
    && ok "embed: caller-prefixed job name -> sha|features" || bad "embed prefix got: '$out'"
  # A caller-prefixed job with NO comma is not an embed (the decoder requires
  # `<sha>,`), which is the same rule the real ORDER-gates name relies on.
  out="$(oc_decode_job_embed "gate / PR-lane gates (bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb)")"
  [ -z "$out" ] \
    && ok "embed: caller-prefixed, sha without a feature list -> empty (not an embed)" \
    || bad "embed prefix-nofeat got: '$out'"
  # The REAL post-refactor shapes, verbatim from run 35612234852. BOTH carry a
  # slash and a 40-hex, and only ONE is decodable — the decoder needs the COMMA
  # after the sha, because an embed is `(<sha>, <features>)`. That asymmetry is
  # load-bearing: `run_built_sha` (oc-deploy:1874-1882) takes the FIRST job name
  # that DECODES, so the ORDER-gates job must NOT decode or the ship lane would
  # read the gate as the build.
  out="$(oc_decode_job_embed "ship / Linux amd64 (5140b36a0d8b2015eeea27ecbe18a46cc7d6e0c8, telegram,code-graph,browser)")"
  [ "$out" = "5140b36a0d8b2015eeea27ecbe18a46cc7d6e0c8|telegram,code-graph,browser" ] \
    && ok "embed: real ship-lane build job name (run 35612234852)" || bad "embed real-ship got: '$out'"
  out="$(oc_decode_job_embed "ship / ORDER gates (5140b36a0d8b2015eeea27ecbe18a46cc7d6e0c8)")"
  [ -z "$out" ] \
    && ok "embed: prefixed ORDER-gates job is NOT decodable (first-match lands on the build)" \
    || bad "embed real-gates should be empty, got: '$out'"
  out="$(oc_decode_job_embed "ship / PR-lane gates (5140b36a0d8b2015eeea27ecbe18a46cc7d6e0c8)")"
  [ -z "$out" ] \
    && ok "embed: prefixed PR-lane gates job is NOT decodable" \
    || bad "embed real-prelanegates should be empty, got: '$out'"
else
  bad "lib/oc-embed.sh missing"
fi

# ---- 00c. lib/oc_claims.py (#313/#314, toolsmith 2fae1230): canonical claim
# ---- predicate — direct unit coverage. Four inlined copies of this predicate
# ---- had drifted apart (two extracted issue tokens as ints, two as strings;
# ---- only one asked WHO authored the closing row), so the module is now the
# ---- single implementation every consumer imports. These cases pin the exact
# ---- properties the drift broke, plus the token-extraction traps (#272).
section "lib/oc_claims.py (canonical claim-closure predicate)"
if [ -f "$TOOLS_DIR/lib/oc_claims.py" ]; then
  # ast.parse, NOT py_compile: py_compile writes a __pycache__ .pyc next to the
  # module, and a synthetic battery run must leave the shared checkout
  # byte-identical (same reason the suite sets OC_TOOLS_NOLOG above).
  python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$TOOLS_DIR/lib/oc_claims.py" 2>/dev/null \
    && ok "oc_claims-lib syntax (ast.parse)" || bad "oc_claims-lib syntax"
  OCT="$(mktemp -d)"
  cat > "$OCT/unit.py" << 'PYEOF'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import oc_claims as oc

fails = []
def chk(desc, got, want):
    if got != want:
        fails.append("%s (got %r want %r)" % (desc, got, want))

# --- issue_ref_tokens: TOKEN extraction, never a substring or digit run (#272)
chk("ref #129", oc.issue_ref_tokens("CLAIM #129 — x"), [129])
chk("ref date not an issue", oc.issue_ref_tokens("stamped 2026-09-15"), [])
chk("ref owner handle not an issue", oc.issue_ref_tokens("leshchenko1979/opencrabs#52"), [52])
chk("ref sha prefix not an issue", oc.issue_ref_tokens("commit 262193f67 landed"), [])
chk("ref uuid prefix not an issue", oc.issue_ref_tokens("session 6630dc9a-0eeb"), [])
chk("ref issue N form", oc.issue_ref_tokens("claims issue 94"), [94])
chk("ref issue=N form", oc.issue_ref_tokens("issue=4242 task"), [4242])
chk("ref issue#N form", oc.issue_ref_tokens("issue#77"), [77])
chk("ref multi in first-seen order", oc.issue_ref_tokens("#38, #80 — multi"), [38, 80])
chk("ref 760 is not 76", oc.references("#760", 76), False)
chk("ref 760 matches 760", oc.references("#760", 760), True)

# --- primary_issue_tokens: what a claim CLAIMS (#329). The leading reference
# --- cluster is the address; a reference in the body is a mention, not a claim.
chk("primary single", oc.primary_issue_tokens("CLAIM #129 — x"), [129])
chk("primary prose mention excluded",
    oc.primary_issue_tokens("CLAIM #327 — filed, one live break (#323)"), [327])
chk("primary live phantom n=8226 shape",
    oc.primary_issue_tokens(
        "filed fragility class issue (#327): 14 bodies, one proven live break (#323)"), [327])
chk("primary genuine dual claim survives",
    oc.primary_issue_tokens("CLAIM #193, #205 — harvest packaging"), [193, 205])
chk("primary live dual n=4802", oc.primary_issue_tokens("CLAIM #193, #205"), [193, 205])
chk("primary slash-joined list",
    oc.primary_issue_tokens("CLAIM #1414/#1418 — pair"), [1414, 1418])
chk("primary live n=8034 parenthetical excluded",
    oc.primary_issue_tokens("CLAIM #302 — backfill (supersedes #290, #297)"), [302])
# #379: this leg used to expect [1419] while its own name said "excluded" --
# the expectation pinned the phantom the issue is about. A leading reference
# qualified by a FOREIGN slug is upstream space: no fork target, so the dead
# letter ([]), never a claim on a fork issue that does not exist.
chk("primary live n=1678 upstream slug is not a fork target",
    oc.primary_issue_tokens(
        "md-plane wave lane claims n=1675 PATH-2 execution: upstream issue "
        "adolfousier/opencrabs#1419 filed FIRST"), [])
chk("ref foreign slug skipped by every-ref tokens",
    oc.issue_ref_tokens("upstream adolfousier/opencrabs#1419 filed"), [])
chk("ref fork slug still yields its number",
    oc.issue_ref_tokens("fork leshchenko1979/opencrabs#52"), [52])
chk("primary foreign slug in the body is not the address",
    oc.primary_issue_tokens("CLAIM #400 - upstream adolfousier/opencrabs#1419"), [400])
chk("primary fork-qualified ref keeps its number",
    oc.primary_issue_tokens("Issue-Ref leshchenko1979/opencrabs#1419"), [1419])
# the false-negative guard: a filesystem path before a SPACED `issue N` must
# not read as a slug and silently drop a real fork reference. This is why the
# predicate matches the immediate form only.
chk("ref filesystem path before spaced issue-N is not a slug",
    oc.issue_ref_tokens("see tools/lib/oc_claims.py issue 379"), [379])
chk("primary non-leading ref is the anchor when no earlier ref exists",
    oc.primary_issue_tokens("Claimed compaction-signal feature: Issue-Ref "
                            "leshchenko1979/opencrabs#29 (mirror of #1256)"), [29])
chk("primary of a ref-less note is empty", oc.primary_issue_tokens("no refs here"), [])
chk("primary never empties a referencing note",
    oc.primary_issue_tokens("x #5 y #6 z"), [5])
chk("primary is a subset of every-ref tokens",
    set(oc.primary_issue_tokens("CLAIM #12 — see #13 and #14"))
    <= set(oc.issue_ref_tokens("CLAIM #12 — see #13 and #14")), True)

# --- type uniformity: the drift bug (str tokens compared to int tokens)
chk("ref tokens are INTEGERS",
    all(isinstance(t, int) for t in oc.issue_ref_tokens("CLAIM #129, issue 94")), True)

# --- actor_key / actor_match
chk("actor full uuid", oc.actor_key("editor 1a63f103-1234-5678-9abc-def012345678"),
    ("uuid", "1a63f103-1234-5678-9abc-def012345678"))
chk("actor short uuid last token", oc.actor_key("toolsmith/2fae1230"), ("uuid", "2fae1230"))
chk("actor label", oc.actor_key("lamp-lane"), ("label", "lamp-lane"))
chk("actor role prefix stripped", oc.actor_key("editor-14"), ("label", "14"))
chk("actor short==full uuid", oc.actor_match("editor 2fae1230",
    "toolsmith 2fae1230-aaaa-bbbb-cccc-dddddddddddd"), True)
chk("actor uuid never matches label", oc.actor_match("editor 2fae1230", "editor-14"), False)
chk("actor different uuids", oc.actor_match("editor 11111111", "editor 22222222"), False)
chk("actor empty label", oc.actor_match("editor-", "editor-"), False)

# --- is_addressed: anchored at the START of what (the #305 fence)
chk("addressed plain", oc.is_addressed("#71 — released", 71), True)
chk("addressed STANDDOWN", oc.is_addressed("STANDDOWN #71 (11111111) — shipped", 71), True)
chk("addressed sweep form", oc.is_addressed("#2 — closed-issue stale claim sweep", 2), True)
# `UNCLAIM #N` is deliberately NOT an address: that ref is the AUTHOR's own
# claim, and the prose after it often names ANOTHER lane — so treating it as an
# address would let a lane's own standdown release a third lane's claim, which
# is exactly the #305 defect. It closes the author's claim by signal 1 instead.
chk("UNCLAIM #N is not an address (#305)", oc.is_addressed("UNCLAIM #72 — stood down in favour of editor lane X", 72), False)
chk("addressed mid-sentence is NOT", oc.is_addressed("note: see #264 for detail", 264), False)
chk("addressed 71 does not address 710", oc.is_addressed("#710 — x", 71), False)
# #690 (2026-09-28, toolsmith; reported by Triage 530c29ec): the LEADING LEAD-IN
# form is an address too, and 42 live rows use it -- including this lane's own
# `issue #675 landed a0931587`, which could not close its own claim. The arm is
# BOUNDED to the start, so the #305 fence below still holds.
chk("addressed 'issue #N' lead-in", oc.is_addressed("issue #29 close-out: upstream PR filed", 29), True)
chk("addressed 'Issue #N' case-insens", oc.is_addressed("Issue #24 mechanical notify fan-out LANDED", 24), True)
# CONTROLS: the fence is unchanged -- a NON-leading "issue #N" is still not an
# address, and neither is a bare mention whose #N is a different issue.
chk("NEG: 'issue #N' NOT at the start is not an address",
    oc.is_addressed("reopened issue #75 — still open", 75), False)
chk("NEG: leading lead-in does not address a MENTIONED issue",
    oc.is_addressed("issue #29 close-out: supersedes #75", 75), False)

# --- is_unattributed sentinels
chk("sentinel unattributed", oc.is_unattributed("(unattributed)"), True)
chk("sentinel unrostered", oc.is_unattributed("unrostered-actor 6630dc9a"), True)
chk("sentinel real actor", oc.is_unattributed("editor 11111111"), False)

# --- open_claims: the canonical rule, all three signals.
# NB the ledger `n` is the ROW number, not the issue: each case is annotated
# with the issue it claims so the survivors below are readable.
EV = [
  {"n": 1, "t": "t1", "by": "editor 11111111", "kind": "claim", "what": "CLAIM #1 — same-author closure"},
  {"n": 2, "t": "t2", "by": "editor 11111111", "kind": "done", "what": "DONE #1 — own row"},
  {"n": 3, "t": "t3", "by": "editor 22222222", "kind": "claim", "what": "CLAIM #2 — addressed closure by another lane"},
  {"n": 4, "t": "t4", "by": "triage 33333333", "kind": "unclaim", "what": "#2 — closed-issue stale claim sweep"},
  {"n": 5, "t": "t5", "by": "editor 44444444", "kind": "claim", "what": "CLAIM #3 — foreign prose must NOT release"},
  {"n": 6, "t": "t6", "by": "triage 33333333", "kind": "unclaim", "what": "UNCLAIM #99 — stood down in favour of editor lane 44444444"},
  {"n": 7, "t": "t7", "by": "(unattributed)", "kind": "claim", "what": "CLAIM #4 — unattributed"},
  {"n": 8, "t": "t8", "by": "editor 55555555", "kind": "confirm", "what": "CONFIRM #4 — any lane closes an unattributed claim"},
  {"n": 9, "t": "t9", "by": "editor 66666666", "kind": "claim", "what": "CLAIM #5 — non-closing kind must not close"},
  {"n":10, "t": "t10", "by": "editor 66666666", "kind": "note", "what": "NOTE #5 — not a closing kind"},
]
# rows 5 (#3, released only by a foreign prose mention) and 9 (#5, whose only
# later row is a non-closing kind) survive; rows 1, 3, 7 are closed by signals
# 1, 2 and 3 respectively.
open_ns = sorted(c["n"] for c in oc.open_claims(EV))
chk("open_claims survivors", open_ns, [5, 9])
chk("open_claims target filter", sorted(c["n"] for c in oc.open_claims(EV, 3)), [5])
chk("open_claims target filter closed", oc.open_claims(EV, 1), [])
chk("open_claims tokens are ints",
    all(isinstance(t, int) for c in oc.open_claims(EV) for t in c["tokens"]), True)
chk("open_claims skips ref-less claim",
    oc.open_claims([{"n": 1, "by": "editor 11111111", "kind": "claim", "what": "CLAIM without a ref"}]), [])

# --- open_claims targets the ADDRESS, not every reference (#329).
PHA = [{"n": 1, "by": "editor 11111111", "kind": "claim",
        "what": "CLAIM #327 — filed, one proven live break (#323)"}]
chk("#329: phantom claim on the mentioned issue does not exist",
    oc.open_claims(PHA, 323), [])
chk("#329: the addressed issue is still open", sorted(c["tokens"] for c in oc.open_claims(PHA)), [[327]])
chk("#329: structured issues field wins over prose",
    sorted(c["tokens"] for c in oc.open_claims(
        [{"n": 1, "by": "editor 11111111", "kind": "claim",
          "what": "CLAIM #5 — mentions #6", "issues": [5]}])), [[5]])
chk("#329: structured field may carry a genuine dual claim",
    sorted(c["tokens"] for c in oc.open_claims(
        [{"n": 1, "by": "editor 11111111", "kind": "claim",
          "what": "CLAIM #5, #6", "issues": [5, 6]}])), [[5, 6]])
chk("#329: empty structured field falls back to the address",
    sorted(c["tokens"] for c in oc.open_claims(
        [{"n": 1, "by": "editor 11111111", "kind": "claim",
          "what": "CLAIM #5 — x", "issues": []}])), [[5]])
chk("#329: non-numeric structured entries are ignored, not crashed on",
    sorted(c["tokens"] for c in oc.open_claims(
        [{"n": 1, "by": "editor 11111111", "kind": "claim",
          "what": "CLAIM #5 — x", "issues": ["5", None, "junk"]}])), [[5]])

# --- legacy schema fallback: rows carrying note/actor instead of what/by
LEG = [{"n": 1, "actor": "editor 11111111", "type": "claim", "note": "CLAIM #7 — legacy keys"}]
chk("legacy keys parsed", len(oc.open_claims(LEG)), 1)

# --- #307 anchored Issue-Ref resolution: the TRAILER, never prose.
# A commit that merely MENTIONS #N in its subject or body is not work on #N.
# The pre-#307 footprint leg was an unanchored `git log --grep=#N`, so upstream
# commit 1e34378050 (subject `(#478)`, body prose `(#300)`) read as fork work on
# #300 and fenced #291's harvest on files #291 never touched. These cases pin the
# anchored predicate AND the positive twin (a trailer DOES resolve), so a
# resolver that simply always returned [] could not pass.
import tempfile, subprocess as _sp, shutil as _sh
def _g(repo, *a):
    return _sp.run(["git", "-C", repo] + list(a), capture_output=True, text=True)
_fx = tempfile.mkdtemp(prefix="occlaims-")
_g(_fx, "init", "-q", "-b", "main")
_g(_fx, "config", "user.email", "unit@local")
_g(_fx, "config", "user.name", "unit")
with open(_fx + "/base.txt", "w") as f: f.write("b\n")
_g(_fx, "add", "-A"); _g(_fx, "commit", "-q", "-m", "base commit")
# subject prose only, no trailer
with open(_fx + "/prose.txt", "w") as f: f.write("p\n")
_g(_fx, "add", "-A"); _g(_fx, "commit", "-q", "-m", "fix(x): reword the note (#701)")
# body prose only, no trailer
with open(_fx + "/bodyprose.txt", "w") as f: f.write("bp\n")
_g(_fx, "add", "-A"); _g(_fx, "commit", "-q", "-m", "fix(w): plain subject",
                         "-m", "This mentions #704 in the body prose only.")
# the positive twin: a real fork Issue-Ref trailer
with open(_fx + "/anchored.txt", "w") as f: f.write("a\n")
_g(_fx, "add", "-A"); _g(_fx, "commit", "-q", "-m", "fix(y): real work",
                         "--trailer", "Issue-Ref: #702")
# cross-space trap: a trailer naming ANOTHER repo must not fence a fork issue
with open(_fx + "/upstream.txt", "w") as f: f.write("u\n")
_g(_fx, "add", "-A"); _g(_fx, "commit", "-q", "-m", "fix(z): upstream work",
                         "--trailer", "Issue-Ref: adolfousier/opencrabs#703")
_idx = oc.issue_ref_index(_fx)
chk("#307 subject-prose mention resolves to NO commits", oc.resolve_issue_commits(_fx, 701), [])
chk("#307 subject-prose mention resolves to NO files", oc.resolve_issue_files(_fx, 701), [])
chk("#307 body-prose mention resolves to NO commits", oc.resolve_issue_commits(_fx, 704), [])
chk("#307 body-prose mention resolves to NO files", oc.resolve_issue_files(_fx, 704), [])
chk("#307 trailer-anchored issue resolves its own file",
    oc.resolve_issue_files(_fx, 702), ["anchored.txt"])
chk("#307 foreign-slug trailer does not fence a fork issue",
    oc.resolve_issue_files(_fx, 703), [])
_order_repo = "/root/opencrabs"
_order_chain = ["5140b36a0", "f1c120f43", "e07eab828"]
chk("parents-first order: #478 chain", oc.order_commits_parents_first(_order_repo, _order_chain), ["e07eab828", "f1c120f43", "5140b36a0"])
chk("parents-first order is input-independent", oc.order_commits_parents_first(_order_repo, list(reversed(_order_chain))), ["e07eab828", "f1c120f43", "5140b36a0"])

_sh.rmtree(_fx, ignore_errors=True)

if fails:
    for f in fails:
        sys.stderr.write("  unit-fail: %s\n" % f)
    sys.exit(1)
PYEOF
  if python3 "$OCT/unit.py" "$TOOLS_DIR/lib" 2>"$OCT/err"; then
    ok "oc_claims predicate unit cases (tokens/actors/address/signals)"
  else
    bad "oc_claims predicate unit cases"; sed 's/^/    /' "$OCT/err" | head -20 | record
  fi
  rm -rf "$OCT"
else
  bad "lib/oc_claims.py missing"
fi

# ---- 5. oc-post-receipts ----------------------------------------------------
section "oc-post-receipts"
if tool archive/oc-post-receipts; then
  "$TOOLS_DIR/archive/oc-post-receipts" --dry-run --topic 30129 --text "suite-triggered" >/dev/null 2>&1; rc=$?
  map_out="$(OC_FORUM_CHAT_ID=-100777000111 "$TOOLS_DIR/archive/oc-post-receipts" --dry-run --topic 30129 --text "mapping" 2>&1)"
  case "$map_out" in
    *"chat_id=-100777000111 -d message_thread_id=30129"*)
      ok "topic->chat/message_thread mapping (defect fix: bare topic as chat_id => Telegram 400)" ;;
    *) bad "topic->chat mapping broken or absent in dry-run output" ;;
  esac
  case "$map_out" in
    *"-d chat_id=30129"*) bad "STILL maps topic into chat_id" ;;
    *) ok "no bare-topic-as-chat_id regression" ;;
  esac
  [ $rc -eq 0 ] && ok "dry-run topic exit 0" || bad "dry-run topic exit $rc (expected 0)"
  "$TOOLS_DIR/archive/oc-post-receipts" --receipt-artifact --unit oc-restart-suite --dry-run >/dev/null 2>&1; [ $? -eq 0 ] && ok "receipt-artifact dry-run exit 0" || bad "receipt-artifact dry-run failed"
  "$TOOLS_DIR/archive/oc-post-receipts" --bogus >/dev/null 2>&1; [ $? -eq 3 ] && ok "bad args -> 3" || bad "bad args -> expected 3"
fi


# ---- 7. oc-pr-atomicity ----------------------------------------------------
section "oc-pr-atomicity"
run_selftest oc-pr-atomicity
if tool oc-pr-atomicity; then
  "$TOOLS_DIR/harvest/oc-pr-atomicity" >/dev/null 2>&1; [ $? -eq 1 ] && ok "no args -> 1 (usage)" || bad "no args -> expected 1"
fi

# ---- 8. oc-ci-parity RETIRED v0.4.117 (owner "3 - ok" 21:44Z: zero live use in 12d, C-H2; three-way-diff check in merge runbook supersedes) ----

# ---- 9. oc-contributors RETIRED v0.4.72 (E2 #1: subset of oc-attrib, zero live callers) ----
# coverage lives in the oc-attrib section; oc-seal-state derives the same list.

# ---- 9b. oc-attrib -----------------------------------------------------------
section "oc-attrib"
run_selftest oc-attrib
if tool oc-attrib; then
  d="$(mktemp -d)"
  git -C "$d" init -q -b main >/dev/null 2>&1
  git -C "$d" config user.email t@t; git -C "$d" config user.name t
  ca() { printf '%s' "$1" > "$d/f.txt"; git -C "$d" add f.txt; printf '%s' "$2" > "$d/.msg"; git -C "$d" commit -q -F "$d/.msg"; }
  SA='dddddddd-0000-0000-0000-00000000000a'
  ca x1 "#1221 fix

Session-Id: $SA
Issue-Ref: #11"
  ca x2 "no trailer drop"
  printf '{"workers":[{"uuid":"%s","role":"editor","topic_id":30090,"feature":"echo-lane"}]}\n' "$SA" > "$d/wl.json"
  OUT="$("$TOOLS_DIR/state/oc-attrib" --repo "$d" --range main --ledger "$d/wl.json")"; rc=$?
  [ $rc -eq 0 ] && ok "attrib exit 0" || bad "attrib exit=$rc"
  echo "$OUT" | awk -F'\t' -v s="$SA" '$1==s && $2=="30090" && $3=="echo-lane" && $4=="#11" {f=1} END{exit !f}' \
    && ok "mapped row joins topic+feature+issue" || bad "mapped row wrong"
  echo "$OUT" | grep -q '(unsigned)' && ok "(unsigned) visible in rows" || bad "(unsigned) dropped"
  J="$("$TOOLS_DIR/state/oc-attrib" --repo "$d" --range main --ledger "$d/wl.json" --json)"
  echo "$J" | jq -e --arg s "$SA" 'map(select(.session==$s))[0].lane.topic_id == 30090' >/dev/null \
    && ok "--json lane object numeric topic_id" || bad "--json lane wrong"
  "$TOOLS_DIR/state/oc-attrib" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2" || bad "no args -> expected 2"
  "$TOOLS_DIR/state/oc-attrib" --repo "$d" --range main..main >/dev/null 2>&1; [ $? -eq 4 ] && ok "empty range -> 4" || bad "empty range -> expected 4"
  rm -rf "$d"
fi

# ---- 9b2. oc-attrib #407 — novelty filter (re-sha'd + empty commits) ---------
# After a lineage rewrite the deployed range is full of commits whose change is
# ALREADY in the baseline (a rebase re-sha's every commit) plus EMPTY commits
# (which carry no patch-id at all). Both were attributed to their original
# authors, so a post-swap fan-out woke every lane on every ship — 276 of 310
# commits in the measured live range were replays. These legs pin the black-box
# contract: RAW is untouched, --novel drops replayed + empty, --no-novel is
# byte-identical to RAW, and a range whose every commit is filtered out is a
# legitimate EMPTY result at rc 0 (not an error).
section "oc-attrib #407 novelty filter (re-sha'd + empty commits)"
run_selftest oc-attrib
if tool oc-attrib; then
  d="$(mktemp -d)"
  git -C "$d" init -q -b main >/dev/null 2>&1
  git -C "$d" config user.email t@t; git -C "$d" config user.name t
  printf 'base\n' > "$d/base.txt"; git -C "$d" add base.txt; git -C "$d" commit -qm base
  B0="$(git -C "$d" rev-parse HEAD)"
  # the ORIGINAL feature commit on its own branch, absorbed into main — the
  # baseline must CONTAIN the original, or `git cherry` cannot see its patch-id.
  git -C "$d" checkout -q -b src
  printf 'twin\n' > "$d/twin.txt"; git -C "$d" add twin.txt
  git -C "$d" commit -qm "twin

Session-Id: 11111111-1111-1111-1111-111111111111"
  TWIN="$(git -C "$d" rev-parse HEAD)"
  git -C "$d" checkout -q main
  git -C "$d" merge -q --ff-only src
  BASE="$(git -C "$d" rev-parse HEAD)"
  # the tip lineage starts at B0 (the commit BEFORE the original), never at the
  # baseline itself: cherry-picking onto the baseline would be a no-op, and
  # cherry-picking onto a tree that already contains the change commits nothing
  # at all.
  git -C "$d" checkout -q -b tip "$B0"
  # a genuinely NOVEL commit lands FIRST — it also gives the replay a different
  # parent (and tree) than the original, so the cherry-pick yields a NEW sha
  # instead of a byte-identical commit (same author, same message, same second).
  printf 'pre\n' > "$d/pre.txt"; git -C "$d" add pre.txt
  git -C "$d" commit -qm "pre

Session-Id: 22222222-2222-2222-2222-222222222222"
  NOVEL="$(git -C "$d" rev-parse HEAD)"
  # the REPLAY: same patch, new sha — exactly what a rebase produces
  git -C "$d" cherry-pick "$TWIN" >/dev/null 2>&1 || bad "#407 fixture: cherry-pick failed"
  REPLAY="$(git -C "$d" rev-parse HEAD)"
  # an EMPTY commit — no patch-id, so `git cherry` can never match it
  git -C "$d" commit -q --allow-empty -m empty
  EMPTY="$(git -C "$d" rev-parse HEAD)"
  [ "$REPLAY" != "$TWIN" ] && ok "#407 fixture: replay carries a distinct sha" \
    || bad "#407 fixture: replay reproduced the twin sha (no twin to detect)"
  S_TWIN="$(printf '%s' "$TWIN" | cut -c1-7)"
  S_REPLAY="$(printf '%s' "$REPLAY" | cut -c1-7)"
  S_NOVEL="$(printf '%s' "$NOVEL" | cut -c1-7)"
  S_EMPTY="$(printf '%s' "$EMPTY" | cut -c1-7)"
  RAW="$("$TOOLS_DIR/state/oc-attrib" --repo "$d" --range "$BASE..tip" 2>/dev/null)"
  NOV="$("$TOOLS_DIR/state/oc-attrib" --repo "$d" --range "$BASE..tip" --novel 2>"$d/nov.err")"; nrc=$?
  [ "$nrc" -eq 0 ] && ok "#407 --novel exits 0" || bad "#407 --novel rc=$nrc want 0"
  [ "$(printf '%s\n' "$RAW" | wc -l)" -eq 3 ] && ok "#407 RAW range keeps all 3 commits (replay+novel+empty)" \
    || bad "#407 RAW rows=$(printf '%s\n' "$RAW" | wc -l) want 3"
  [ "$(printf '%s\n' "$NOV" | wc -l)" -eq 1 ] && ok "#407 --novel keeps exactly the 1 novel commit" \
    || bad "#407 --novel rows=$(printf '%s\n' "$NOV" | wc -l) want 1 (raw=3)"
  grep -q "$S_NOVEL" <<< "$NOV" && ok "#407 --novel keeps the novel commit" || bad "#407 --novel dropped the novel commit"
  grep -q "$S_REPLAY" <<< "$NOV" && bad "#407 --novel KEPT the replayed twin (patch-id equivalence missed)" || ok "#407 --novel drops the replayed twin"
  grep -q "$S_EMPTY" <<< "$NOV" && bad "#407 --novel KEPT the empty commit" || ok "#407 --novel drops the empty commit"
  grep -q "$S_REPLAY" <<< "$RAW" && ok "#407 RAW still shows the replayed twin (filter is opt-in)" || bad "#407 RAW lost the replayed twin"
  grep -q "3 raw, 1 replayed, 1 empty, 1 contributing" "$d/nov.err" && ok "#407 stderr accounting names raw/replayed/empty/contributing" \
    || bad "#407 stderr accounting missing: $(cat "$d/nov.err" 2>/dev/null)"
  NN="$("$TOOLS_DIR/state/oc-attrib" --repo "$d" --range "$BASE..tip" --no-novel 2>/dev/null)"
  [ "$NN" = "$RAW" ] && ok "#407 --no-novel is byte-identical to RAW" || bad "#407 --no-novel != RAW"
  # an ALL-REPLAYED tip — nothing but a re-sha'd original plus an empty commit,
  # against a baseline that already carries both — must yield ZERO rows at rc 0.
  # This is the case oc-deploy's fan-out has to read as "nothing to notify"
  # rather than as an attrib breakdown (issue #407 instance B).
  git -C "$d" checkout -q -b tip2 "$B0"
  git -C "$d" cherry-pick "$TWIN" >/dev/null 2>&1 || bad "#407 fixture: tip2 cherry-pick failed"
  git -C "$d" commit -q --allow-empty -m "chore: sign tip2"
  ALLF="$("$TOOLS_DIR/state/oc-attrib" --repo "$d" --range "$BASE..tip2" --novel 2>"$d/allf.err")"; arc=$?
  [ "$arc" -eq 0 ] && [ -z "$ALLF" ] && ok "#407 all-replayed range -> rc 0 with no rows" \
    || bad "#407 all-replayed range rc=$arc rows=$(printf '%s\n' "$ALLF" | wc -l) want rc 0 / 0 rows"
  grep -q "0 contributing" "$d/allf.err" && ok "#407 all-replayed accounting reports 0 contributing" \
    || bad "#407 all-replayed accounting missing: $(cat "$d/allf.err" 2>/dev/null)"
  rm -rf "$d"
fi

# ---- 9c. oc-consent-check — RETIRED 2026-08-28 (owner order 18:50Z: consent
#         process eliminated; tool archived to tools/archive/). Tests removed.
section "oc-consent-check (RETIRED — skipped)"

# ---- 9d. oc-seal-state orders vocabulary/purge ---------------------------------
section "oc-seal-state orders"
run_selftest oc-seal-state
if tool oc-seal-state; then
  d="$(mktemp -d)"; O="$d/orders.json"
  printf '{"orders":[{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","features":"telegram","status":"queued"},{"order_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","status":"dispatched","run_id":"7"}]}\n' > "$O"
  "$TOOLS_DIR/ship/oc-seal-state" --orders "$O" --mark-order aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --status deployed --order-evidence "PID 1 disk==proc" >/dev/null 2>&1
  [ $? -eq 0 ] && ok "status-only mark accepted" || bad "status-only mark rejected"
  [ "$(jq -r '.orders[0].status' "$O")" = "DEPLOYED" ] && ok "vocabulary uppercased + stored" || bad "status not DEPLOYED"
  [ "$(jq -r '.orders[0].evidence' "$O")" = "PID 1 disk==proc" ] && ok "per-row evidence stored" || bad "evidence missing"
  "$TOOLS_DIR/ship/oc-seal-state" --orders "$O" --mark-order bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb --with-run 99 >/dev/null 2>&1
  [ "$(jq -r '.orders[1].run_id' "$O")" = "99" ] && ok "legacy order_sha row markable" || bad "legacy row missed"
  [ "$(jq -r '.orders[1].status' "$O")" = "DISPATCHED" ] && ok "default status DISPATCHED" || bad "default status wrong"
  "$TOOLS_DIR/ship/oc-seal-state" --orders "$O" --mark-order aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --status BOGUS >/dev/null 2>&1
  [ $? -eq 1 ] && ok "invalid vocabulary -> 1" || bad "BOGUS accepted"
  "$TOOLS_DIR/ship/oc-seal-state" --orders "$O" --purge-order bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb >/dev/null 2>&1
  [ "$(jq '.orders|length' "$O")" -eq 1 ] && ok "purge removes matching row" || bad "purge failed"
  "$TOOLS_DIR/ship/oc-seal-state" --orders "$O" --purge-order bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb >/dev/null 2>&1
  [ $? -eq 1 ] && ok "purge unknown sha -> 1" || bad "purge miss not refused"
  rm -rf "$d"
fi

# ---- 9e. oc-carrier-features (KERNEL C1) -----------------------------------
section "oc-carrier-features"
run_selftest oc-carrier-features
if tool oc-carrier-features; then
  "$TOOLS_DIR/ship/oc-carrier-features" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
fi

# ---- 9f. oc-issue-sweep (KERNEL C3) -----------------------------------------
section "oc-issue-sweep"
run_selftest oc-issue-sweep
if tool oc-issue-sweep; then
  "$TOOLS_DIR/issue/oc-issue-sweep" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
fi

# ---- 9g. oc-skew-scan (KERNEL C4) -------------------------------------------
section "oc-skew-scan"
run_selftest oc-skew-scan
if tool oc-skew-scan; then
  "$TOOLS_DIR/state/oc-skew-scan" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
fi

# ---- 9h. oc-ping-proof (B25) -------------------------------------------------
section "oc-ping-proof"
run_selftest oc-ping-proof
if tool oc-ping-proof; then
  "$TOOLS_DIR/notify/oc-ping-proof" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
fi

# ---- 9i. oc-watchdog-check — RETIRED v0.4.65 (lens E A1: pure passthrough to oc-deploy watch) ----

# ---- 9k. oc-deploy contributors + fanout (issue #24) -------------------------
# Black-box battery checks for the #24 mechanical notify fan-out, invoking the
# ABSOLUTE tool path (selftest re-invokes via $0 — a different code path):
# contributors over the REAL oc-attrib; GREEN leg with a dead-session skip;
# RED leg blame attribution over a real git fixture; idempotence; usage rc.
# Stubs are heredocs: the original printf form corrupted the JSON quotes
# (bash printf eats \" in the format string) and silently rc-3'd the GREEN
# leg. Suspect cc / unowned / zero-site fallback / dry-run / drill
# suppression are covered by the full oc-deploy --selftest in section 10.
section "oc-deploy contributors + fanout (#24)"
if tool oc-deploy; then
  d="$(mktemp -d)"; SD="$d/state"; mkdir -p "$SD/tools"
  # contributors: real oc-attrib over a trailer fixture -> uuid + issue + sha7
  git init -q -b main "$d/crepo"
  git -C "$d/crepo" config user.email t@t; git -C "$d/crepo" config user.name t
  git -C "$d/crepo" commit -q --allow-empty -m base
  CBASE="$(git -C "$d/crepo" rev-parse HEAD)"
  git -C "$d/crepo" commit -q --allow-empty -m "feat: battery trailer

Session-Id: 99999999-8888-7777-6666-555555555555
Issue-Ref: #77"
  CTIP="$(git -C "$d/crepo" rev-parse HEAD)"
  # contributors verb RETIRED (v0.4.91, lens E-2): loud deprecation rc 1, points at oc-attrib.
  # The working TSV projection is covered by oc-attrib --contributors (single shape now).
  OUTK="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_ATTRIB="$TOOLS_DIR/state/oc-attrib" \
    "$TOOLS_DIR/ship/oc-deploy" contributors "$CBASE..$CTIP" --repo "$d/crepo" 2>&1)"; rck=$?
  if [ "$rck" -eq 1 ] && case "$OUTK" in *"RETIRED"*"oc-attrib"*) true ;; *) false ;; esac; then
    ok "contributors: retired verb -> rc1 + loud oc-attrib pointer"
  else
    bad "contributors retired (rc=$rck, want 1 + RETIRED + oc-attrib pointer)"
  fi
  # gh stub: run 222 GREEN (built sha cccc...) + run 666 RED (head from red-head)
  cat > "$SD/gh" <<'GHSTUB'
#!/usr/bin/env bash
SD="$(cd "$(dirname "$0")" && pwd)"
case "$*" in
  *actions/runs/222/jobs*) echo '{"jobs":[{"name":"ORDER gates (cccccccccccccccccccccccccccccccccccccccc)","conclusion":"success"},{"name":"Linux amd64 (cccccccccccccccccccccccccccccccccccccccc, telegram)","conclusion":"success"}]}' ;;
  *actions/runs/222*) echo '{"status":"completed","conclusion":"success"}' ;;
  *actions/runs/666/jobs*) echo '{"jobs":[{"name":"Linux amd64 (build)","conclusion":"failure","check_run_url":"https://api.github.com/repos/leshchenko1979/opencrabs/check-runs/9001"}]}' ;;
  *check-runs/9001/annotations*) echo '[{"path":"bad.txt","start_line":3}]' ;;
  *actions/runs/666*) echo "{\"status\":\"completed\",\"conclusion\":\"failure\",\"head_sha\":\"$(cat "$SD/red-head" 2>/dev/null)\"}" ;;
  *) echo '{}' ;;
esac
GHSTUB
  chmod +x "$SD/gh"
  printf 'cccccccccccccccccccccccccccccccccccccccc\n' > "$SD/deployed.sha"
  printf '{"prev_sha":"0000000000000000000000000000000000000000","features":"telegram"}' > "$SD/deployed.meta.json"
  # two sessions: aaaaaaaa live, bbbbbbbb dead (notify shim exits 2) -> skipped=1
  cat > "$SD/tools/attrib-stub" <<'ATTRSTUB'
#!/usr/bin/env bash
printf 'aaaaaaaa-1111-2222-3333-444444444444\t#77\tabc1234\n'
printf 'bbbbbbbb-1111-2222-3333-444444444444\t#78\tdef5678\n'
ATTRSTUB
  chmod +x "$SD/tools/attrib-stub"
  cat > "$SD/notify" <<NOTIFYSHIM
#!/usr/bin/env bash
case "\$*" in *bbbbbbbb*) exit 2 ;; esac
echo "\$*" >> "$d/notify.log"; exit 0
NOTIFYSHIM
  chmod +x "$SD/notify"
  : > "$d/notify.log"
  OUTK="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$TOOLS_DIR/ship/oc-deploy" fanout --run 222 2>&1)"; rck=$?
  if [ "$rck" -eq 0 ] && case "$OUTK" in *"notified=1 skipped=1"*) true ;; *) false ;; esac; then
    ok "fanout GREEN: notified=1 skipped=1"
  else
    bad "fanout GREEN leg (rc=$rck, want 0 + 'notified=1 skipped=1'; got: $OUTK)"
  fi
  grep -q "aaaaaaaa-1111" "$d/notify.log" && ok "fanout GREEN: verb shim called" || bad "fanout GREEN: no verb call"
  grep -q "bbbbbbbb-1111" "$d/notify.log" && bad "dead uuid logged by shim (should be refused rc 2)" || ok "dead uuid: shim refused, not logged"
  jq -e '.runs["222"]' "$SD/fanout.state" >/dev/null 2>&1 && ok "fanout GREEN: state marked" || bad "fanout GREEN: state unmarked"
  grep -q '"reason":"dead"' "$SD"/oc-deploy/journal/fanout-222-*.jsonl 2>/dev/null && ok "dead uuid: skip journaled" || bad "dead uuid: no skip journal line"
  OUTK="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_ATTRIB="$SD/tools/attrib-stub" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$TOOLS_DIR/ship/oc-deploy" fanout --run 222 2>&1)"; rck=$?
  [ "$rck" -eq 0 ] && case "$OUTK" in *"reason=done"*) true ;; *) false ;; esac \
    && ok "fanout idempotent rerun: reason=done" || bad "fanout idempotent rerun (rc=$rck)"
  # RED leg: culprit commit (trailer cccccccc-1111) blamed at bad.txt:3
  git init -q --bare -b main "$d/red1.git"
  git init -q -b main "$d/redc1"; git -C "$d/redc1" config user.email t@t; git -C "$d/redc1" config user.name t
  printf 'l1\nl2\nv1\nl4\n' > "$d/redc1/bad.txt"
  git -C "$d/redc1" add bad.txt; git -C "$d/redc1" commit -qm base
  git -C "$d/redc1" push -q "$d/red1.git" HEAD
  git clone -q "$d/red1.git" "$d/redw1"; git -C "$d/redw1" config user.email t@t; git -C "$d/redw1" config user.name t
  sed -i 's/^v1$/v2/' "$d/redw1/bad.txt"
  git -C "$d/redw1" add bad.txt
  git -C "$d/redw1" commit -qm "feat: culprit change

Session-Id: cccccccc-1111-2222-3333-444444444444"
  git -C "$d/redw1" push -q "$d/red1.git" HEAD
  git -C "$d/redw1" rev-parse HEAD > "$SD/red-head"
  OUTK="$(OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_GH="$SD/gh" OC_DEPLOY_REPO="$d/redc1" OC_DEPLOY_REMOTE="$d/red1.git" \
    OC_DEPLOY_NOTIFY="$SD/notify" "$TOOLS_DIR/ship/oc-deploy" fanout --run 666 2>&1)"; rck=$?
  if [ "$rck" -eq 0 ] && case "$OUTK" in *"notified=1 skipped=0 unowned=0"*) true ;; *) false ;; esac; then
    ok "fanout RED: blamed culprit notified=1"
  else
    bad "fanout RED leg (rc=$rck, want 0 + 'notified=1 skipped=0 unowned=0'; got: $OUTK)"
  fi
  grep -q "cccccccc-1111" "$d/notify.log" && ok "fanout RED: culprit verb call" || bad "fanout RED: culprit not notified"
  FJR="$(ls "$SD"/oc-deploy/journal/fanout-666-*.jsonl 2>/dev/null | head -1)"
  if [ -n "$FJR" ] && grep -q '"step":"attributed"' "$FJR" && grep '"step":"attributed"' "$FJR" | grep -q "cccccccc-1111"; then
    ok "fanout RED: attributed journal blames culprit"
  else
    bad "fanout RED: attributed line missing/wrong"
  fi
  jq -e '.runs["666"].notified == 1' "$SD/fanout.state" >/dev/null 2>&1 && ok "fanout RED: state marked" || bad "fanout RED: state unmarked"
  OUTK="$(OC_DEPLOY_STATE_DIR="$SD" "$TOOLS_DIR/ship/oc-deploy" fanout 2>&1)"; rck=$?
  [ "$rck" -eq 2 ] && ok "fanout without --run -> 2 (usage)" || bad "fanout usage (rc=$rck, want 2)"
  rm -rf "$d"
fi

# ---- 10. oc-deploy -----------------------------------------------------------
# Regression pinned here (2026-08-27): after a diverged remote round-trip, the
# non-FF fetch refspec silently rejected the update and the ref-first fallback
# resurrected a STALE refs/oc-deploy/main — FF check saw a ghost "rebase needed".
section "oc-deploy"
# M2-21 (2026-09-12) e2e: the selftest must be LOG-HERMETIC BY CONSTRUCTION,
# not by argv shape. Run the BARE subcommand -- the spelling that slipped the
# flag-only predicate -- with OC_TOOLS_LOG pointed at a temp file and require
# ZERO rows. Pre-fix this wrote 93 rows of fixture dispatches; oc-ship-audit
# read six of them back as ORPHANED and rc=1'd a gate that fronts
# `oc-ledger commit-pending`. OC_TOOLS_NOLOG=0 is REQUIRED: the battery exports
# it as 1 globally (run.sh:21), which would make this assertion vacuous.
LSE="$(mktemp -d)/selftest.log"
run_capture "oc-deploy selftest (bare subcommand)" \
  env OC_TOOLS_NOLOG=0 OC_DEPLOY_STATE_DIR="$(mktemp -d)" OC_TOOLS_LOG="$LSE" \
     "$TOOLS_DIR/ship/oc-deploy" selftest
if [ -s "$LSE" ]; then
  bad "bare selftest leaked $(wc -l < "$LSE") row(s) into OC_TOOLS_LOG (M2-21)"
else
  ok "bare selftest is log-hermetic: 0 rows (M2-21)"
fi
if tool oc-deploy; then
  "$TOOLS_DIR/ship/oc-deploy" >/dev/null 2>&1; [ $? -eq 1 ] && ok "no args -> 1 (usage)" || bad "no args -> expected 1"
  "$TOOLS_DIR/ship/oc-deploy" --bogus >/dev/null 2>&1; [ $? -eq 1 ] && ok "unknown arg -> 1" || bad "unknown arg -> expected 1"
  d="$(mktemp -d)"; printf x > "$d/oc-deploy.kill"
  OC_DEPLOY_STATE_DIR="$d" "$TOOLS_DIR/ship/oc-deploy" poll >/dev/null 2>&1
  [ $? -eq 9 ] && ok "kill file -> 9 (real-mode brake)" || bad "kill file -> expected 9"
  # Duty-6 lens F task 5: --wait validated BEFORE any RED-scan side effects —
  # bad --wait dies rc1 with no fanout/state writes (the kill-file brake sits at
  # the TOP of every real-mode arm, so poll with kill file + bad --wait -> 9,
  # not 1; contract fix ec4706bd moved it there from before arg parsing).
  d2="$(mktemp -d)"
  OC_DEPLOY_STATE_DIR="$d2" OC_DEPLOY_GH=/bin/false "$TOOLS_DIR/ship/oc-deploy" poll --wait abc >/dev/null 2>&1
  [ $? -eq 1 ] && ok "poll bad --wait -> 1 before side effects" || bad "poll bad --wait -> expected 1"
  [ "$(ls -A "$d2" 2>/dev/null)" = "oc-deploy-shadow.log" ] && ok "poll bad --wait: no state writes beyond shadow log" || bad "poll bad --wait wrote state: $(ls "$d2")"
  rm -rf "$d2"
  # Ship-pending law (n=2003 family, v0.4.99): poll --sha S with S already
  # deployed must NOT say "nothing new" — dispatched-sha GREEN = SWAP PENDING.
  # Full-loop dry check: state dir with deployed.sha == the only decodable
  # green run's sha, plus --sha of that same sha -> swap-execute handoff path
  # reached, never rc5 "already deployed". (Uses --execute but stage < S2 in
  # the sandbox, so the loop breaks and lands in the LOCKED plan branch.)
  d3="$(mktemp -d)"; SD3="$d3/state"; mkdir -p "$SD3"
  PEN_SHA="0123456789abcdef0123456789abcdef01234567"
  printf '%s\n' "$PEN_SHA" > "$SD3/deployed.sha"
  printf '{"sha":"%s","features":"telegram","ts":"2026-09-08T00:00:00Z"}\n' "$PEN_SHA" > "$SD3/deployed.meta.json"
  # gh stub: one success run whose job name embeds PEN_SHA (both-shapes decode)
  cat > "$d3/gh" <<GHEOF
#!/usr/bin/env bash
case "\$*" in
  *"/runs?status=success"*) echo '{"workflow_runs":[{"id":111}]}';;
  *"/runs/111/jobs"*) echo '{"jobs":[{"name":"build (0123456789abcdef0123456789abcdef01234567, telegram)"},{"name":"gates (0123456789abcdef0123456789abcdef01234567)"}]}';;
  *) echo '{}';;
esac
GHEOF
  chmod +x "$d3/gh"
  OC_DEPLOY_STATE_DIR="$SD3" OC_DEPLOY_GH="$d3/gh" OC_DEPLOY_NOFANOUT=1 OC_DEPLOY_POLL_INTERVAL=1 \
    "$TOOLS_DIR/ship/oc-deploy" poll --wait 2 --sha "$PEN_SHA" --execute --features telegram >/dev/null 2>&1
  RC3=$?
  grep -q "nothing new" "$d3"/oc-deploy-shadow.log 2>/dev/null && MISSED=1 || MISSED=0
  [ "$RC3" != 5 ] && [ "$MISSED" = 0 ] && ok "poll --sha pending: dispatched-sha GREEN never reports 'already deployed'" || bad "poll --sha pending: rc=$RC3 missed=$MISSED"
  rm -rf "$d3"
  rm -rf "$d"
  # stale pinned ref: diverge remote -> ship --execute (pins div tip) -> restore
  # remote -> plan MUST report FF ok (old code: rc 2 via resurrected stale ref)
  d="$(mktemp -d)"; SD="$d/state"; mkdir -p "$SD/tools"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD/tools/val"; chmod +x "$SD/tools/val"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$SD/gh"; chmod +x "$SD/gh"
  git init -q --bare -b main "$d/remote.git"
  git init -q -b main "$d/repo"
  git -C "$d/repo" config user.email t@t; git -C "$d/repo" config user.name t
  echo one > "$d/repo/f1"; git -C "$d/repo" add f1; git -C "$d/repo" commit -qm one
  echo two > "$d/repo/f2"; git -C "$d/repo" add f2; git -C "$d/repo" commit -qm two
  SHA2="$(git -C "$d/repo" rev-parse HEAD)"
  git -C "$d/repo" push -q "$d/remote.git" HEAD~1:refs/heads/main
  (cd "$d/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$d/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val" OC_DEPLOY_GH="$SD/gh" \
    "$TOOLS_DIR/ship/oc-deploy" ship --sha "$SHA2" --features telegram >/dev/null 2>&1)
  git -C "$d/repo" checkout -qb div HEAD~1
  echo div > "$d/repo/f3"; git -C "$d/repo" add f3; git -C "$d/repo" commit -qm div
  git -C "$d/repo" push -q -f "$d/remote.git" HEAD:refs/heads/main
  (cd "$d/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$d/remote.git" \
    "$TOOLS_DIR/ship/oc-deploy" ship --sha "$SHA2" --features telegram >/dev/null 2>&1)
  git -C "$d/repo" checkout -q -B main "$SHA2"
  git -C "$d/repo" push -q -f "$d/remote.git" main~1:refs/heads/main
  OUT2="$(cd "$d/repo" && OC_DEPLOY_STATE_DIR="$SD" OC_DEPLOY_REMOTE="$d/remote.git" \
    OC_DEPLOY_VALIDATE="$SD/tools/val" OC_DEPLOY_GH="$SD/gh" "$TOOLS_DIR/ship/oc-deploy" ship --sha "$SHA2" --features telegram 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ] && case "$OUT2" in *"FF ok"*) true ;; *) false ;; esac; then
    ok "stale pinned ref: FF ok after diverge/restore round-trip"
  else
    bad "stale pinned ref regression (rc=$rc, want 0 + 'FF ok' line)"
  fi
  rm -rf "$d"
fi

# ---- 11. oc-ledger (KERNEL C1–C5 + item-2(b) commit-pending sweep) ---------
# RESTORED 2026-09-29 (toolsmith 2fae1230). The 2026-09-29 owner order removed
# "questions and ledger" on the premise that their code belongs to the meta
# factory and is tested there. Measured: that holds for `questions`
# (TEMPLATE/tools/questions + TEMPLATE/tests/test_questions.py) but NOT for
# oc-ledger -- the template ships `ledger.py`, a different artifact, and its own
# addon doc (TEMPLATE/docs/addons/harness/opencrabs.md:243) states the harness
# supplies `oc-ledger`. Nothing else tests it, so removing this section left it
# uncovered. Restored; remove again only with a replacement gate.
section "oc-ledger"
run_selftest oc-ledger
d="$(mktemp -d)"; mkdir -p "$d/state"
printf '{"current_skill_version":"0.0.1","meta":{"skill_version":"0.0.1","current_skill_version":"0.0.1"},"updated_at":"x","workers":[],"events":[]}' > "$d/state/workers-ledger.json"
# #19 (2026-09-12): stamp REFUSES an anonymous row, so the battery fixture
# carries an actor the way a lane's shell does.
OC_LEDGER="$d/state/workers-ledger.json" OC_ACTOR="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" "$TOOLS_DIR/state/oc-ledger" stamp note "battery edge" >/dev/null 2>&1 \
  && [ "$(jq '.events[-1].n' "$d/state/workers-ledger.json")" = "1" ] \
  && ok "empty-events fixture: first stamp -> n=1" || bad "empty-events fixture stamp"
OC_LEDGER="$d/state/workers-ledger.json" "$TOOLS_DIR/state/oc-ledger" frobnicate >/dev/null 2>&1
[ $? -eq 2 ] && ok "unknown subcommand -> 2 (usage)" || bad "unknown subcommand -> expected 2"
rm -rf "$d"

# ---- 12. oc-review-persist (ghost-incident cure: reports on disk) ----------
section "oc-review-persist"
run_selftest oc-review-persist
d="$(mktemp -d)"
"$TOOLS_DIR/state/oc-review-persist" A "battery edge report" --dir "$d" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ] && [ -s "$d/skill-review-A-$(date -u +%Y%m%d).md" ] && [ -s "$d/skill-review-index.log" ]; then
  ok "persist + index receipt on disk"
else
  bad "persist edge (rc=$rc)"
fi
rm -rf "$d"

# ---- 13. oc-prchecks (KERNEL C5 — one-command PR lint gate) ----------------
section "oc-prchecks"
run_selftest oc-prchecks
if tool oc-prchecks; then
  SD_PRC="$(mktemp -d)"   # hermetic: usage() writes .oc-prchecks-rc2 into the state dir (goal C, ts 18:34:19Z leak)
  OC_DEPLOY_STATE_DIR="$SD_PRC" "$TOOLS_DIR/harvest/oc-prchecks" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
  OC_DEPLOY_STATE_DIR="$SD_PRC" "$TOOLS_DIR/harvest/oc-prchecks" abc123 >/dev/null 2>&1; [ $? -eq 2 ] && ok "short sha -> 2 (FULL-sha shape gate)" || bad "short sha -> expected 2"
  rm -rf "$SD_PRC"
  [ ! -f "${OC_DEPLOY_STATE_DIR:-/root/.opencrabs/profiles/ops/opencrabs-dev}/.oc-prchecks-rc2" ] || true   # informational; real check: no NEW writes below
fi

# ---- 14. oc-upstream-delta (KERNEL C6 — watch-cycle arithmetic) ------------
section "oc-upstream-delta"
run_selftest oc-upstream-delta
if tool oc-upstream-delta; then
  "$TOOLS_DIR/harvest/oc-upstream-delta" --repo /nonexistent-repo-path >/dev/null 2>&1; [ $? -eq 2 ] && ok "bad repo path -> 2" || bad "bad repo path -> expected 2"
fi

# ---- 15. oc-wt (KERNEL C7 — worktree add/remove, un-skippable index chain) -
section "oc-wt"
run_selftest oc-wt
if tool oc-wt; then
  "$TOOLS_DIR/git/oc-wt" add "Bad_Slug" some-branch >/dev/null 2>&1; [ $? -eq 2 ] && ok "bad slug -> 2 (usage)" || bad "bad slug -> expected 2"
fi

# ---- 16. lens-C tool builds (v0.4.58, owner Go 2026-08-31 04:20Z) -----------
section "oc-drift-check"
run_selftest oc-drift-check
if tool oc-drift-check; then
  "$TOOLS_DIR/state/oc-drift-check" u1 0.4 >/dev/null 2>&1; [ $? -eq 2 ] && ok "bad version shape -> 2" || bad "bad shape -> expected 2"
fi

section "oc-branch-sweep"
run_selftest oc-branch-sweep
if tool oc-branch-sweep; then
  "$TOOLS_DIR/git/oc-branch-sweep" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no repo -> 2 (usage)" || bad "no repo -> expected 2"
fi

section "oc-pr-fault-scope"
run_selftest oc-pr-fault-scope
if tool oc-pr-fault-scope; then
  "$TOOLS_DIR/harvest/oc-pr-fault-scope" 1 >/dev/null 2>&1; [ $? -eq 2 ] && ok "missing --run -> 2 (usage)" || bad "missing --run -> expected 2"
fi

section "oc-ledger confirm + derive_by"
# (oc-ledger selftest executed in section 11)

section "oc-ledger lock budget (#619)"
if tool oc-ledger; then
  # (#619) The lock waiter budget must be DERIVED from the holder worst case, which
  # the two in-lock network pushes dominate. This leg is BEHAVIOURAL, not a grep: a
  # grep for OC_LEDGER_LOCK_WAIT self-matches the leg that contains it, which is the
  # trap this test was written to avoid (measured 2026-09-26). Hold the lock, vary the
  # push bound, and read the budget the tool itself reports.
  LB="$(mktemp -d)"
  printf '{"workers":[],"events":[]}' > "$LB/l.json"
  # (c) CONTROL: with the lock free the same invocation must SUCCEED, or the legs
  # below would pass on a tool that is simply broken.
  OC_LEDGER_LOCK_WAIT=1 OC_TOOLS_NOLOG=1 "$TOOLS_DIR/state/oc-ledger" --ledger "$LB/l.json" stamp note "c" --by "hq probe" >/dev/null 2>&1 \
    && ok "#619 control: lock free -> stamp succeeds (rc 0)" || bad "#619 control: lock free -> stamp failed"
  # (a) the waiter budget is TUNABLE -- the fix's load-bearing capability
  ( flock -x 9; sleep 4 ) 9>>"$LB/l.json.lock" &
  HLD=$!; sleep 0.5
  O1="$(OC_LEDGER_LOCK_WAIT=1 OC_LEDGER_PUSH_TIMEOUT=1 OC_TOOLS_NOLOG=1 "$TOOLS_DIR/state/oc-ledger" --ledger "$LB/l.json" stamp note "a" --by "hq probe" 2>&1)"; R1=$?
  wait "$HLD" 2>/dev/null
  [ "$R1" -eq 4 ] && ok "#619: a 1s waiter budget times out with rc 4" || bad "#619: want rc 4, got $R1"
  case "$O1" in *"after 1s"*) ok "#619: the refusal names the budget it used" ;; *) bad "#619: refusal does not name the budget: $(printf '%s' "$O1" | head -1)" ;; esac
  case "$O1" in *"worst case 32s"*) ok "#619: budget disclosed as 2x1s push + 30s non-push = 32s" ;; *) bad "#619: want worst case 32s, got: $(printf '%s' "$O1" | head -1)" ;; esac
  # (b) DERIVATION: raise the push bound and the reported worst case must move with
  # it. This is the invariant the defect broke -- an operator could widen the holder
  # without touching the waiter, driving the two arbitrarily far apart.
  ( flock -x 9; sleep 4 ) 9>>"$LB/l.json.lock" &
  HLD=$!; sleep 0.5
  O2="$(OC_LEDGER_LOCK_WAIT=1 OC_LEDGER_PUSH_TIMEOUT=10 OC_TOOLS_NOLOG=1 "$TOOLS_DIR/state/oc-ledger" --ledger "$LB/l.json" stamp note "b" --by "hq probe" 2>&1)"
  wait "$HLD" 2>/dev/null
  case "$O2" in *"worst case 50s"*) ok "#619: budget TRACKS the push bound (10s -> 50s)" ;; *) bad "#619: budget did not track the push bound: $(printf '%s' "$O2" | head -1)" ;; esac
  rm -rf "$LB"
fi

# ---- 17. lens-F coverage batch (v0.4.72, F8: tools the battery never ran) ---
section "oc-shadow-rotate"
if tool oc-shadow-rotate; then
  d="$(mktemp -d)"
  OC_DEPLOY_STATE_DIR="$d" "$TOOLS_DIR/state/oc-shadow-rotate" --dry-run >/dev/null 2>&1; [ $? -eq 0 ] && ok "no live log -> noop rc 0" || bad "no live log -> expected 0"
  printf 'line1\nline2\n' > "$d/oc-deploy-shadow.log"
  OUTS="$(OC_DEPLOY_STATE_DIR="$d" "$TOOLS_DIR/state/oc-shadow-rotate" --dry-run 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] && case "$OUTS" in *"PLAN: append 2 lines"*) true ;; *) false ;; esac && ok "dry-run PLAN names 2 lines" || bad "dry-run PLAN (rc=$rc, got: $OUTS)"
  OC_DEPLOY_STATE_DIR="$d" "$TOOLS_DIR/state/oc-shadow-rotate" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 0 ] && [ ! -s "$d/oc-deploy-shadow.log" ] && grep -q line1 "$d/oc-deploy-shadow.archive.log" \
    && ok "rotate: archive appended + live truncated" || bad "rotate (rc=$rc)"
  OC_DEPLOY_STATE_DIR="$d" "$TOOLS_DIR/state/oc-shadow-rotate" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage, C-#3: was 1)" || bad "unknown arg -> expected 2"
  rm -rf "$d"
fi

section "oc-smoke-evidence"
run_selftest oc-smoke-evidence
if tool oc-smoke-evidence; then
  "$TOOLS_DIR/smoke/oc-smoke-evidence" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/smoke/oc-smoke-evidence" --unit oc-no-such-unit --strings m1 >/dev/null 2>&1; [ $? -eq 3 ] && ok "--strings deprecated alias parses (unit-fail rc 3, E2 #6)" || bad "--strings alias -> expected 3"
  # M2-2: the decoy-path guard. A bare/relative --append-log must resolve to the
  # CANONICAL log (no divergence note); a foreign absolute path must announce itself.
  SED_TMP="$(mktemp -d)"
  OC_DEPLOY_STATE_DIR="$SED_TMP" "$TOOLS_DIR/smoke/oc-smoke-evidence" --append-log --unit oc-no-such-unit 2>&1 | grep -q 'NOT the canonical' && bad "bare --append-log diverged from canonical" || ok "bare --append-log -> canonical log (M2-2)"
  OC_DEPLOY_STATE_DIR="$SED_TMP" "$TOOLS_DIR/smoke/oc-smoke-evidence" --append-log smoke-verdicts.log --unit oc-no-such-unit 2>&1 | grep -q 'NOT the canonical' && bad "relative --append-log escaped STATE_DIR" || ok "relative --append-log resolves to STATE_DIR, not CWD (M2-2)"
  OC_DEPLOY_STATE_DIR="$SED_TMP" "$TOOLS_DIR/smoke/oc-smoke-evidence" --append-log /tmp/oc-elsewhere.log --unit oc-no-such-unit 2>&1 | grep -q 'NOT the canonical' && ok "divergent absolute --append-log announces itself (M2-2)" || bad "divergent --append-log was silent"
  rm -rf "$SED_TMP"
fi

section "oc-issue-log"
run_selftest oc-issue-log
if tool oc-issue-log; then
  "$TOOLS_DIR/issue/oc-issue-log" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
  OC_ISSUE_LOG_REPO=x/y "$TOOLS_DIR/issue/oc-issue-log" 1 zznotasha --dry-run >/dev/null 2>&1; [ $? -eq 3 ] && ok "bad sha -> 3 (not found)" || bad "bad sha -> expected 3"
fi

section "oc-commit"
run_selftest oc-commit
if tool oc-commit; then
  "$TOOLS_DIR/git/oc-commit" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
fi

section "oc-ship-audit"
run_selftest oc-ship-audit
if tool oc-ship-audit; then
  "$TOOLS_DIR/ship/oc-ship-audit" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
fi

section "oc-tg-audit"
run_selftest oc-tg-audit
if tool oc-tg-audit; then
  "$TOOLS_DIR/audit/oc-tg-audit" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
fi

section "oc-harvest-sweep"
run_selftest oc-harvest-sweep
if tool oc-harvest-sweep; then
  "$TOOLS_DIR/harvest/oc-harvest-sweep" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
fi

section "oc-harvest-census"
run_selftest oc-harvest-census
if tool oc-harvest-census; then
  "$TOOLS_DIR/harvest/oc-harvest-census" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
fi

section "oc-rebase-safety"
run_selftest oc-rebase-safety
if tool oc-rebase-safety; then
  "$TOOLS_DIR/git/oc-rebase-safety" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
  "$TOOLS_DIR/git/oc-rebase-safety" overlap >/dev/null 2>&1; [ $? -eq 2 ] && ok "overlap missing args -> 2" || bad "overlap missing args -> expected 2"
  "$TOOLS_DIR/git/oc-rebase-safety" audit >/dev/null 2>&1; [ $? -eq 2 ] && ok "audit missing args -> 2" || bad "audit missing args -> expected 2"
fi

section "oc-roster"
run_selftest oc-roster
if tool oc-roster; then
  "$TOOLS_DIR/state/oc-roster" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
  "$TOOLS_DIR/state/oc-roster" --no-such-arg >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2" || bad "unknown arg -> expected 2"
fi

# ---- 18. oc-ship-chain (5→swapped orchestrator, owner GO 16:16Z) -----------
section "oc-ship-chain (5→swapped orchestrator, owner GO 16:16Z)"
run_selftest oc-ship-chain
if tool oc-ship-chain; then
  "$TOOLS_DIR/ship/oc-ship-chain" >/dev/null 2>&1; [ $? -eq 2 ] && ok "no args -> 2 (usage)" || bad "no args -> expected 2"
  "$TOOLS_DIR/ship/oc-ship-chain" --no-such-arg >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2" || bad "unknown arg -> expected 2"
fi


# ---- battery receipt (oc-ledger sync gate reads this; the file itself rides --
# ---- the skill repo via commit-pending --bundle) ------------------------------
# ---- 60. rc contract: --help exits 0 fleet-wide (C-#3, tools/docs/RC-CONTRACT.md)
section "rc contract --help=0 fleet-wide (C-#3)"
# tools/ is grouped by KIND (owner order 2026-09-25), so the fleet executables
# live one level down. A flat "$TOOLS_DIR"/oc-* glob matches NOTHING after the
# regroup and this section then passes by counting zero legs -- a fleet-wide
# check that cannot fail, which is the silent-skip class this battery exists to
# catch. Enumerate recursively and assert a FLOOR, so a future layout change
# reddens here instead of quietly reducing the leg count.
HELP_N=0
for t in "$TOOLS_DIR"/oc-* "$TOOLS_DIR"/*/oc-*; do
  [ -x "$t" ] || continue
  case "$t" in */lib/*|*/tests/*|*/archive/*|*.bak|*.bak-*|*.pre-*) continue ;; esac
  tn="$(basename "$t")"
  HELP_N=$((HELP_N+1))
  OC_TOOLS_NOLOG=1 timeout 20 "$t" --help >/dev/null 2>&1     && ok "$tn --help rc=0" || bad "$tn --help rc!=0 (tools/docs/RC-CONTRACT.md violated)"
  # (#618) The rc check above discards STDERR, so a --help whose body executes
  # phantom commands still reads rc=0. That is how oc-smoke shipped `absent` and
  # `na` running as commands and vanishing from its own help text: an UNQUOTED
  # heredoc whose body carries unescaped backticks. The help still printed, so
  # nothing reddened. Read stderr and assert it is free of shell diagnostics.
  # The patterns name SHELL diagnostics specifically. A bare "not found" is NOT
  # one: oc-pr-atomicity's own usage line documents "4 PR not found" as an exit
  # code, and the loose arm flagged that legitimate text -- a false positive of
  # the guard I had just written. Anchor on the shell's own wording.
  HERR="$(OC_TOOLS_NOLOG=1 timeout 20 "$t" --help 2>&1 >/dev/null || true)"
  case "$HERR" in
    *"command not found"*|*"syntax error"*|*"unbound variable"*|*"No such file or directory"*|*"Bad substitution"*)
      bad "$tn --help wrote a SHELL DIAGNOSTIC to stderr: $(printf '%s' "$HERR" | head -1 | cut -c1-70)" ;;
  esac
done
[ "$HELP_N" -ge 30 ] && ok "fleet --help floor: $HELP_N tool(s) enumerated" \
  || bad "fleet --help floor: only $HELP_N tool(s) enumerated -- the glob stopped matching (want >= 30)"
# #691: the edit tool writes a `.bak` pre-image beside every file it edits, and
# those sidecars are EXECUTABLE copies of the tool, so the glob above enumerated
# them as fleet tools and ran their --help (7 phantom PASS legs, 2026-09-28).
# Re-evaluate the SAME skip pattern against the live sidecar population, and
# disclose vacuity rather than passing silently when there are none.
_BAKFIND="find \"$TOOLS_DIR\" -maxdepth 2 -type f \( -name 'oc-*.bak' -o -name 'oc-*.bak-*' -o -name 'oc-*.pre-*' \)"
_BAKC="$(eval "$_BAKFIND" 2>/dev/null | grep -c . || true)"
_BAKSKIP=0
while IFS= read -r _bf; do
  [ -n "$_bf" ] || continue
  case "$_bf" in */lib/*|*/tests/*|*/archive/*|*.bak|*.bak-*|*.pre-*) _BAKSKIP=$((_BAKSKIP+1)) ;; esac
done <<< "$(eval "$_BAKFIND" 2>/dev/null)"
if [ "$_BAKC" = "0" ]; then
  ok "generated-ignored sidecar class: none present (guard vacuous this run)"
elif [ "$_BAKSKIP" = "$_BAKC" ]; then
  ok "generated-ignored sidecar class: all $_BAKC skipped by the tool enumeration (#691)"
else
  bad "generated-ignored sidecar class: $((_BAKC-_BAKSKIP)) of $_BAKC STILL enumerated as tools (#691)"
fi

# ---- 61. oc-notify-fanout: placeholder guard + target validation (HQ ASSIGN 2026-09-09)
section "oc-notify-fanout guards (law1 placeholder + dead-target skip + --roles)"
NF="$TOOLS_DIR/notify/oc-notify-fanout"
# LAW 16 (defect D-1, HQ 2026-09-12): self identity is DERIVED from the
# invoking session and an unresolved self is a HARD ERROR (rc 2) — the old
# hardcoded lane default is gone. So every fixture must name its invoker.
# Resolve the live toolsmith lane; the fallback matches no real lane, which
# keeps 61a/61b about the placeholder guard rather than about exclusion.
NFSELF="$(bash "$TOOLS_DIR/state/oc-ledger" roster --live --role toolsmith 2>/dev/null | head -1 | awk '{print $1}')"
[ -n "$NFSELF" ] || NFSELF="00000000-0000-4000-8000-00000000dead"
# 61a. placeholder law: dangling token -> every send ABORTed, rc!=0
NFOUT="$(OC_TOOLS_NOLOG=1 OC_FANOUT_SELF="$NFSELF" OC_FANOUT_LEDGER="$HOME/.opencrabs/profiles/ops/opencrabs-dev/workers-ledger.json" timeout 200 bash "$NF" \
  --title "t-battery" --text "dangling {{NOSUCH}} token" --dry-run 2>&1)" \
  && bad "fanout placeholder-guard: rc=0 on token leak" \
  || { grep -q "placeholder-token-survived" <<< "$NFOUT" \
       && ok "fanout placeholder-guard: dangling token -> send ABORTed (law1)" \
       || bad "fanout placeholder-guard: aborted but no law1 receipt"; }
# 61b. substitution: valid tokens -> DRY briefs, no ABORT, dead uuids skipped
NFOUT="$(OC_TOOLS_NOLOG=1 OC_FANOUT_SELF="$NFSELF" OC_FANOUT_LEDGER="$HOME/.opencrabs/profiles/ops/opencrabs-dev/workers-ledger.json" timeout 200 bash "$NF" \
  --title "t-battery" --text "v{{VERSION}} u{{UUID}}" --dry-run 2>&1)"
grep -q "placeholder-token-survived" <<< "$NFOUT" \
  && bad "fanout substitution: valid tokens ABORTed (substitution broken)" \
  || ok "fanout substitution: {{UUID}}/{{VERSION}} resolved, 0 ABORTs"
grep -qE "sent=[0-9]+ skipped=[0-9]+ failed=0" <<< "$NFOUT" \
  && ok "fanout dry-run summary clean (dead targets skipped, none failed)" \
  || bad "fanout dry-run summary has failures"
# 61c. roles filter: --roles toolsmith (self-excluded) -> sent=0
NFOUT="$(OC_TOOLS_NOLOG=1 OC_FANOUT_SELF="$NFSELF" OC_FANOUT_LEDGER="$HOME/.opencrabs/profiles/ops/opencrabs-dev/workers-ledger.json" timeout 200 bash "$NF" \
  --title "t" --text "x" --dry-run --roles toolsmith 2>&1)"
grep -q "sent=0" <<< "$NFOUT" \
  && ok "fanout --roles filter respected" \
  || bad "fanout --roles filter leaked sends"
# 61d. oc-notify-fanout internal selftest suite
run_selftest "oc-notify-fanout" "$NF"

# ---- 62. oc-health (owner-ordered hourly health & cleanliness sweep, 2026-09-11)
section "oc-health (hourly health & cleanliness sweep)"
HZ="$TOOLS_DIR/state/oc-health"
# 62a. hermetic selftest: fixture state dir + tmp glob + sqlite DB + git repos,
#      so the reaping cases run without touching live state. The assertion count
#      is read from the selftest's own PASS= line (never hardcoded — a hardcoded
#      count silently goes stale every time a case is added).
HOUT="$(bash "$HZ" --selftest 2>&1)"; HRC=$?
HN="$(printf '%s' "$HOUT" | sed -n 's/.*PASS=\([0-9]*\).*/\1/p' | tail -1)"
[ "$HRC" -eq 0 ] && ok "oc-health --selftest PASS (${HN:-?} assertions)" \
  || bad "oc-health --selftest rc=$HRC: $(printf '%s' "$HOUT" | tail -3)"
# 62b. read-only run must NOT mutate: no --reap, no writes; rc is 0 (clean) or 1
#      (findings) — never 2/3 on a healthy box.
HOUT="$(bash "$HZ" --json 2>&1)"; HRC=$?
case "$HRC" in
  0|1) ok "oc-health read-only rc=$HRC (0 clean / 1 findings)" ;;
  *)   bad "oc-health read-only rc=$HRC (want 0|1)" ;;
esac
printf '%s' "$HOUT" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null \
  && ok "oc-health --json parses (stdout is the whole contract)" \
  || bad "oc-health --json not parseable: $(printf '%s' "$HOUT" | head -2)"
# 62c. --help exits 0 (rc-contract row)
bash "$HZ" --help >/dev/null 2>&1 && ok "oc-health --help rc=0" || bad "oc-health --help rc!=0"
# 62d. watcher-window override: 0 = all history must still be a valid measurement
#      (rc 0|1, parseable JSON) — the knob must never turn into a measurement failure.
WOUT="$(OC_HEALTH_WATCHER_WINDOW_H=0 bash "$HZ" --class runtime_procs --json 2>&1)"; WRC=$?
case "$WRC" in
  0|1) ok "oc-health watcher-window override rc=$WRC (0 clean / 1 findings)" ;;
  *)   bad "oc-health watcher-window override rc=$WRC (want 0|1)" ;;
esac
printf '%s' "$WOUT" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null \
  && ok "oc-health --class runtime_procs --json parses" \
  || bad "oc-health runtime_procs json not parseable: $(printf '%s' "$WOUT" | head -2)"

# ---- 63. oc-watcher-audit (detached watcher compliance audit, Cycle 5 Review C-2)
section "oc-watcher-audit (detached watcher compliance audit)"
run_selftest oc-watcher-audit
if tool oc-watcher-audit; then
  "$TOOLS_DIR/audit/oc-watcher-audit" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/audit/oc-watcher-audit" --help >/dev/null 2>&1 && ok "oc-watcher-audit --help rc=0" || bad "oc-watcher-audit --help rc!=0"
fi

# ---- 65. oc-start (unified claim, branch, worktree initializer, Cycle c14)
section "oc-start (unified task initializer)"
run_selftest oc-start
if tool oc-start; then
  "$TOOLS_DIR/git/oc-start" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/git/oc-start" --help >/dev/null 2>&1 && ok "oc-start --help rc=0" || bad "oc-start --help rc!=0"
fi

# ---- 66. oc-smoke (unified 4-leg smoke verification & verdict row generator, Cycle c14)
section "oc-smoke (unified 4-leg smoke verification)"
run_selftest oc-smoke
if tool oc-smoke; then
  "$TOOLS_DIR/smoke/oc-smoke" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/smoke/oc-smoke" --help >/dev/null 2>&1 && ok "oc-smoke --help rc=0" || bad "oc-smoke --help rc!=0"
fi

# ---- 64. oc-issue-dispatch (mechanized fork issue dispatch, v0.4.169 Zero-Ack)
section "oc-issue-dispatch (mechanized issue triage dispatch)"
run_selftest oc-issue-dispatch
if tool oc-issue-dispatch; then
  "$TOOLS_DIR/issue/oc-issue-dispatch" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/issue/oc-issue-dispatch" --help >/dev/null 2>&1 && ok "oc-issue-dispatch --help rc=0" || bad "oc-issue-dispatch --help rc!=0"
  # Edge cases that proved fatal during the role-binding build (fork #342, task
  # 17). run_selftest above counts ONE case however many asserts the tool makes
  # internally, so the crash that actually cost a probing cycle is pinned here
  # against the SHIPPED module: score_affinity must survive a lane dict with no
  # "raw" key. get_worker_roster builds lanes as {uuid,topic,topic_id,feature,
  # class,claims,worktrees,is_busy,raw} and carries the role at raw["role"], so
  # reading lane["role"] raised KeyError. sys.dont_write_bytecode is set BEFORE
  # the loader runs so the shared checkout stays byte-identical (same reason as
  # the oc_claims section above).
  OCT="$(mktemp -d)"
  cat > "$OCT/edge.py" << 'PYEOF'
import importlib.util, os, sys
from importlib.machinery import SourceFileLoader

sys.dont_write_bytecode = True

loader = SourceFileLoader("oid_edge", os.path.join(sys.argv[1], "issue", "oc-issue-dispatch"))
spec = importlib.util.spec_from_loader("oid_edge", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

fails = []
def chk(desc, got, want):
    if got != want:
        fails.append("%s (got %r want %r)" % (desc, got, want))

issue = {"number": 451, "title": "fix(tools): oc-issue-dispatch hangs",
         "body": "the culprit is tools/issue/oc-issue-dispatch"}

# A lane dict that omits raw (or carries raw=None/{}) must score, not crash.
for desc, lane in (
    ("no raw key", {"uuid": "e1", "feature": "general editor", "is_busy": False, "class": "ACTIVE"}),
    ("raw None", {"uuid": "e2", "feature": "general editor", "is_busy": False, "class": "ACTIVE", "raw": None}),
    ("raw empty", {"uuid": "e3", "feature": "general editor", "is_busy": False, "class": "ACTIVE", "raw": {}}),
):
    try:
        got = mod.score_affinity(issue, lane)
    except Exception as exc:
        fails.append("score_affinity raised on lane with %s: %r" % (desc, exc))
        continue
    chk("score_affinity int on lane with %s" % desc, isinstance(got, int), True)

# The binding must still be live in the shipped file: the surface owner outranks
# a verbose editor on its own issue. Delete ROLE_DOMAINS and this goes red.
lane_owner = {"uuid": "e4", "is_busy": False, "class": "ACTIVE",
              "feature": "TOOLSMITH lane: owns tools/ CLI (oc-ledger, oc-deploy)",
              "raw": {"role": "toolsmith"}}
lane_verbose = {"uuid": "e5", "is_busy": False, "class": "ACTIVE",
                "feature": "harvest upstream port census sweep notify queue delivery router cli exec",
                "raw": {"role": "editor"}}
chk("role-bound owner outranks the verbose editor on a tools/ issue",
    mod.score_affinity(issue, lane_owner) > mod.score_affinity(issue, lane_verbose), True)

if fails:
    for f in fails:
        sys.stderr.write("  edge-fail: %s\n" % f)
    sys.exit(1)
PYEOF
  if python3 "$OCT/edge.py" "$TOOLS_DIR" >/dev/null 2>"$OCT/err"; then
    ok "oc-issue-dispatch role-binding edge cases (raw-absent lanes; owner outranks prose)"
  else
    bad "oc-issue-dispatch role-binding edge cases"; sed 's/^/    /' "$OCT/err" | head -20 | record
  fi
  rm -rf "$OCT"
fi

# ---- 67. oc-lint-laws (markdown law syntax & tool reference linter)
section "oc-lint-laws (law syntax & reference linter)"
run_selftest oc-lint-laws
if tool oc-lint-laws; then
  "$TOOLS_DIR/audit/oc-lint-laws" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/audit/oc-lint-laws" --help >/dev/null 2>&1 && ok "oc-lint-laws --help rc=0" || bad "oc-lint-laws --help rc!=0"
  # c24 J-1: the LIVE corpus, actually LINTED. Every leg above and every leg in
  # the tool's own selftest points at a fixture tools/ dir, so DEFAULT_CORPUS is
  # never read and a phantom flag in the SHIPPED law stays green -- which is how
  # the dead `oc-ship-chain --resume` citation went unseen for weeks. The leg
  # below runs the real corpus and requires rc 0; the control plants a phantom
  # and requires rc 1, so the leg cannot pass by measuring nothing.
  _LLT="$(mktemp -d -t oc-battery-lint.XXXXXX)"
  _ll_rc=0
  "$TOOLS_DIR/audit/oc-lint-laws" >"$_LLT/live.out" 2>&1 || _ll_rc=$?
  if [ "$_ll_rc" -eq 0 ]; then
    ok "live corpus lint -> rc 0 (every flag/verb named by the shipped law exists)"
  else
    bad "live corpus lint -> rc=$_ll_rc: $(head -2 "$_LLT/live.out" | tr '\n' ' ')"
  fi
  printf 'Run `oc-lint-laws --qqzz-probe` to check.\n' > "$_LLT/probe.md"
  _ll_p=0
  "$TOOLS_DIR/audit/oc-lint-laws" --file "$_LLT/probe.md" >/dev/null 2>&1 || _ll_p=$?
  [ "$_ll_p" -eq 1 ] && ok "live corpus lint control: a planted phantom reddens (rc 1)" || bad "live corpus lint control -> rc=$_ll_p want 1"
  rm -rf "$_LLT"
fi

# ---- 68. oc-harvest-dispatch (automated harvest order dispatcher)
section "oc-harvest-dispatch (harvest order dispatcher)"
run_selftest oc-harvest-dispatch
if tool oc-harvest-dispatch; then
  "$TOOLS_DIR/harvest/oc-harvest-dispatch" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/harvest/oc-harvest-dispatch" --help >/dev/null 2>&1 && ok "oc-harvest-dispatch --help rc=0" || bad "oc-harvest-dispatch --help rc!=0"
fi

# ---- 69. oc-log-search (telemetry-only daemon-log search)
section "oc-log-search (telemetry-only log search)"
run_selftest oc-log-search
if tool oc-log-search; then
  "$TOOLS_DIR/audit/oc-log-search" --bogus >/dev/null 2>&1; [ $? -eq 2 ] && ok "unknown arg -> 2 (usage)" || bad "unknown arg -> expected 2"
  "$TOOLS_DIR/audit/oc-log-search" --help >/dev/null 2>&1 && ok "oc-log-search --help rc=0" || bad "oc-log-search --help rc!=0"
fi

# ---- 71. oc-census (READ-ONLY pending-branch census) ------------------------
# The selftest builds a throwaway 5-branch fixture repo and asserts the
# decomposition invariant (plus_total == plus_own + plus_untrailered +
# plus_other) plus the tip-lane resolution rule. It never touches the real
# repo, so it costs ~1s and is safe to run in the battery.
section "oc-census (pending-branch census)"
run_selftest oc-census

# ---- 72. oc-claims-single-source (claim-predicate single-source guard) ------
# The claim-closure predicate was inlined FIVE times and the copies drifted
# (#305/#309/#313/#424/#425). Tools 18/19 deleted the last two; this guard is
# what stops a sixth. It keys on the SHAPE a copy must re-implement - never on
# a function name - so a rename does not evade it.
#
# Placed BEFORE the battery-last.json receipt write on purpose: a section added
# after that line would run but its legs would never reach the receipt, so the
# battery would report a total that silently excluded this guard.
section "oc-claims-single-source (private-copy guard)"
run_selftest oc-claims-single-source

# ---- 73. lib/oc-notify.sh CLI budget (#466) --------------------------------
# Defect: the CLI leg ran `session notify` with NO timeout of its own, so a hung
# CLI blocked oc_notify_session() forever -- and the A2A fallback below it is
# reached only on a NON-zero rc, so the fallback existed for exactly the case
# that made it unreachable. The fix wraps BOTH CLI calls in `timeout`.
#
# Discriminating input: a `bin` stub that HANGS (sleep 30). Pre-fix the function
# never returns, the outer `timeout 20` kills the whole subshell, and the leg
# reports FAIL -- measured on the HEAD lib (172 lines): rc=124, empty result,
# marker `invoked`+`killed` only, NO `a2a`. Post-fix it returns in ~2s with the
# A2A leg entered. `timeout` exits 124, which is not 0/2/3, so the kill
# deliberately falls through to the fallback; that passthrough is the contract
# the rc assertion pins.
section "lib/oc-notify.sh CLI budget (#466)"
NFSTUB="$(mktemp -d)"; NFMARK="$NFSTUB/mark"
cat > "$NFSTUB/bin" <<'NFSTUBEOF'
#!/bin/sh
echo "invoked" >> "$MARK"
trap 'echo killed >> "$MARK"; exit 143' TERM
sleep 30
NFSTUBEOF
chmod +x "$NFSTUB/bin"
# The A2A fallback is an inline `python3 -c`. Intercepting python3 records ENTRY
# to that leg without opening a socket to the live gateway -- whose availability
# is a host fact, not a property of this code, so a real call would make the leg
# pass or fail for the wrong reason.
cat > "$NFSTUB/python3" <<'NFPYEOF'
#!/bin/sh
echo "a2a" >> "$MARK"
exit 4
NFPYEOF
chmod +x "$NFSTUB/python3"
NFRES="$(MARK="$NFMARK" NFSTUB="$NFSTUB" TOOLS_DIR="$TOOLS_DIR" timeout 20 bash -c '
  export MARK PATH="$NFSTUB:$PATH" OC_NOTIFY_CLI_TIMEOUT=2
  . "$TOOLS_DIR/lib/oc-notify.sh"
  t0="$(date +%s)"
  oc_notify_session "$NFSTUB/bin" ops test-runner 00000000-0000-4000-8000-000000000000 t x; rc=$?
  t1="$(date +%s)"
  printf "elapsed=%s rc=%s\n" "$((t1-t0))" "$rc"
' 2>&1)"; nfrc=$?
NFEL="$(printf '%s' "$NFRES" | sed -n 's/^elapsed=\([0-9]*\).*/\1/p')"
NFRC="$(printf '%s' "$NFRES" | sed -n 's/.*rc=\([0-9]*\).*/\1/p')"
[ "$nfrc" -eq 0 ] && [ -n "$NFEL" ] && [ "$NFEL" -le 15 ] \
  && ok "notify CLI leg bounded by its own budget (${NFEL}s vs a 30s hang, budget 2s)" \
  || bad "notify CLI leg UNBOUNDED: outer kill rc=$nfrc result='$NFRES' (#466 regression)"
grep -q '^invoked$' "$NFMARK" 2>/dev/null \
  && ok "notify CLI leg reached the bin stub" \
  || bad "notify CLI leg never reached the bin stub"
grep -q '^a2a$' "$NFMARK" 2>/dev/null \
  && ok "A2A fallback leg REACHED after the CLI timeout (unreachable by construction pre-#466)" \
  || bad "A2A fallback leg NOT reached after a hung CLI -- the fallback is still unreachable"
[ "$NFRC" = "124" ] \
  && ok "timeout passthrough keeps the ambiguous rc=124 (never read as a delivery verdict)" \
  || bad "hung CLI returned rc='$NFRC', want 124 (0/2/3 would read as a delivery outcome)"
rm -rf "$NFSTUB"

# ---- 74. oc-issue-dispatch survives SIGKILL with evidence (#451) -------------
# Defect: a dispatch killed by an outer `timeout` left a 0-BYTE stdout, so the
# run read as a silent hang "with no output and no side effect" even though it
# had reached the send. Two causes, both fixed: stdout was block-buffered on a
# redirected stream (nothing is flushed when SIGKILL lands, and SIGKILL cannot
# be caught, so there is no exit-time flush either), and the notify-budget
# announcement was printed only AFTER the blocking send returned.
#
# Discriminating input: a `lib/oc-notify.sh` stub that SLEEPS, so the run is
# still inside the send when an outer `timeout -s KILL` fires. The control is
# the SAME source with the buffering mechanism inverted
# (line_buffering=True -> False): identical content, identical kill, and the
# ONLY difference is whether the announcement survives to the file.
#
# The control is DERIVED, never read from history. Pinning a pre-fix sha would
# go stale the moment the repo is rebased or that object is gc'd, and would then
# report a FALSE failure against a healthy tool. Inverting the one mechanism
# keeps this cell a true single-variable discriminator indefinitely.
section "oc-issue-dispatch SIGKILL evidence (#451)"
D451STUB="$(mktemp -d)"
mkdir -p "$D451STUB/tools/lib" "$D451STUB/tools/issue" "$D451STUB/bin" "$D451STUB/home"
cp "$TOOLS_DIR/issue/oc-issue-dispatch" "$D451STUB/tools/issue/oc-issue-dispatch"
chmod +x "$D451STUB/tools/issue/oc-issue-dispatch"
for f in "$TOOLS_DIR"/lib/*.py; do [ -e "$f" ] && cp "$f" "$D451STUB/tools/lib/"; done
# lib/oc-root.sh is the marker the depth-agnostic bootstrap walks up to find. A
# fixture that copies only *.py leaves the tool unable to resolve the tools root,
# so TOOL_DIR collapses to the tool's own subdir and the shared lib/ disappears.
[ -f "$TOOLS_DIR/lib/oc-root.sh" ] && cp "$TOOLS_DIR/lib/oc-root.sh" "$D451STUB/tools/lib/"
# The send must BLOCK so the kill lands inside it. A real notify would either
# reach the live bus or return instantly, and neither reproduces #451. Bounded
# at 30s: the stub outlives the 10s kill by design, but never permanently.
printf '#!/bin/sh\nsleep 30\n' > "$D451STUB/tools/lib/oc-notify.sh"
chmod +x "$D451STUB/tools/lib/oc-notify.sh"
# gh is stubbed: whether the fork has an open issue #451 is a HOST fact, not a
# property of this code, so a real call would make the leg pass or fail for the
# wrong reason.
#
# The stub answers BOTH reads the targeted path makes (#483). It used to answer
# "[]" to everything, which was enough while the targeted path read the OPEN LIST
# alone and stubbed any number that list did not carry. Since #483 an
# unresolvable number is a REFUSAL, not a stub, so a stub that says "[]" to the
# single-issue lookup now models a genuinely missing issue and the run exits 1
# BEFORE the send -- the leg would fail for a reason that has nothing to do with
# #451. The LIST stays empty here on purpose: the send must be reached through
# the direct lookup, which is the path #483 added.
cat > "$D451STUB/bin/gh" <<'D451GH'
#!/bin/sh
case "$1 $2" in
  "issue view") echo '{"number":451,"title":"fix(tools): oc-issue-dispatch hangs","body":"the culprit is tools/issue/oc-issue-dispatch","labels":[{"name":"tools"}],"state":"OPEN","stateReason":null}' ;;
  *) echo "[]" ;;
esac
D451GH
chmod +x "$D451STUB/bin/gh"
printf '{"workers":[],"events":[]}\n' > "$D451STUB/ledger.json"

sed 's/line_buffering=True/line_buffering=False/' "$D451STUB/tools/issue/oc-issue-dispatch" \
  > "$D451STUB/tools/oc-issue-dispatch-nolb"
[ "$(grep -c 'line_buffering=False' "$D451STUB/tools/oc-issue-dispatch-nolb")" -eq 1 ] \
  && ok "control derived: the line-buffering mechanism inverted exactly once" \
  || bad "control derivation did not invert exactly one line_buffering site -- the discriminator is unsound"
chmod +x "$D451STUB/tools/oc-issue-dispatch-nolb"

d451_run() { # $1 = tool path, $2 = label
  D451OUT="$D451STUB/out-$2.txt"
  # OC_TOOLS_NOLOG is re-exported explicitly: env -i drops the battery's own
  # export, and without it these synthetic runs append to the unified tools log.
  # --allow-landed --redispatch: this fixture uses issue 451 purely as a VEHICLE
  # for the SIGKILL-survival question, and #451's own fix IS landed (an Issue-Ref
  # trailer on the skill repo's origin/main). Since #370 the targeted path runs
  # the same eligibility arms as --auto, so the fixture must bypass them or it
  # refuses with rc 8 before ever reaching the notify leg it exists to test.
  env -i HOME="$D451STUB/home" PATH="$D451STUB/bin:/usr/bin:/bin" \
      OC_TOOLS_NOLOG=1 OC_DISPATCH_NOTIFY_TIMEOUT=60 OC_DISPATCH_RECEIPT_GRACE=5 \
      timeout -s KILL 10 "$1" 451 \
        --to deadbeef-0000-0000-0000-000000000000 \
        --allow-landed --redispatch \
        --ledger "$D451STUB/ledger.json" --repo "$TOOLS_DIR/.." \
      > "$D451OUT" 2>"$D451STUB/err-$2.txt"
  D451RC=$?
  D451BYTES="$(wc -c < "$D451OUT" | tr -d ' ')"
  D451ANN="$(grep -c 'notify budget' "$D451OUT" 2>/dev/null || true)"
  if [ -z "$D451ANN" ]; then D451ANN=0; fi
}

d451_run "$D451STUB/tools/issue/oc-issue-dispatch" postfix
[ "$D451RC" -eq 137 ] \
  && ok "post-fix: killed mid-send (rc=137 SIGKILL -- the #451 precondition)" \
  || bad "post-fix: rc=$D451RC, want 137 -- the kill did not land mid-send"
[ "$D451BYTES" -gt 0 ] && [ "$D451ANN" -ge 1 ] \
  && ok "post-fix: the dispatch narrative SURVIVED SIGKILL (${D451BYTES}B, ${D451ANN} budget announcement)" \
  || bad "post-fix: killed run left ${D451BYTES}B / ${D451ANN} announcements -- the evidence was discarded (#451 regression)"

d451_run "$D451STUB/tools/oc-issue-dispatch-nolb" prefix
[ "$D451RC" -eq 137 ] \
  && ok "control: killed mid-send under an identical timeout (rc=137 -- the cells are comparable)" \
  || bad "control: rc=$D451RC, want 137 -- the cells are not comparable"
[ "$D451BYTES" -eq 0 ] && [ "$D451ANN" -eq 0 ] \
  && ok "control: WITHOUT line buffering the same run leaves 0B / 0 announcements (the assertion is discriminating)" \
  || bad "control: left ${D451BYTES}B / ${D451ANN} announcements -- this cell cannot fail on the pre-fix artifact, so it proves nothing"

rm -rf "$D451STUB"

# ---- 75. red-receipt transcript (fail log) ---------------------------------
# Defect (HQ item 5, 2026-09-22): emit_summary wrote battery-last.json durably
# while the transcript went only to stdout, so a committed red receipt
# (228 pass / 1 fail, commit d1f63d9f) recorded THAT a leg failed and nothing
# about WHICH -- undiagnosable by the next reader. Contract: a RED run leaves
# tools/tests/battery-last-fail.log carrying the FAIL rows and their
# continuation lines and the receipt JSON names it; a GREEN run removes it, so
# the log's PRESENCE is itself the red signal.
#
# #614 (2026-09-26) widened it: the log's life was ONE RUN (the next run
# truncates it at :179, a green one removes it) while the receipt outlives it --
# so a red receipt could name a 0-byte file and the failing leg became
# unrecoverable. The diagnosis now rides IN the receipt (`fail_rows` +
# `fail_rows_truncated`); the sidecar stays for immediate tail/grep but is no
# longer the durable half. Leg (e) is the discriminating one.
#
# Discriminating input: on the pre-fix artifact bad() has no transcript arm and
# record() does not exist, so `bad` writes nothing to $FAIL_LOG. Legs (a)-(c)
# go red on HEAD while passing here.
section "red-receipt transcript (fail log)"
FLT="$(mktemp -d)"
# (a) bad() records the FAIL row. Runs in a SUBSHELL so the synthetic failure
#     increments only the subshell's FAIL, and its stdout goes to /dev/null --
#     a leaked "  FAIL - " line would be counted by the parallel parent and
#     corrupt this run's own receipt.
( FAIL_LOG="$FLT/a.log"; : > "$FAIL_LOG"; bad "synthetic-leg" ) >/dev/null 2>&1
grep -q '  FAIL - synthetic-leg' "$FLT/a.log" \
  && ok "bad() writes the FAIL row to the transcript" \
  || bad "bad() did not record the FAIL row ($(wc -c < "$FLT/a.log" 2>/dev/null || echo 0) bytes)"
# (b) record() is a TEE: the detail must reach BOTH stdout and the transcript.
printf 'detail-line\n' | { FAIL_LOG="$FLT/b.log"; : > "$FAIL_LOG"; record; } > "$FLT/b.out" 2>/dev/null
if grep -q 'detail-line' "$FLT/b.log" 2>/dev/null && grep -q 'detail-line' "$FLT/b.out" 2>/dev/null; then
  ok "record() appends to the transcript AND passes stdout through"
else
  bad "record() tee failed: detail-line absent from the transcript or from stdout"
fi
# (c) finalize_fail_log: green clears the log and empties the field; red keeps
#     it and names it. Both directions, because a one-way test cannot tell a
#     working finalize from a constant.
( FAIL=0; FAIL_LOG="$FLT/c.log"; : > "$FAIL_LOG"; finalize_fail_log
  [ ! -f "$FAIL_LOG" ] && [ -z "$FAIL_LOG_FIELD" ] ) \
  && ok "finalize on green removes the log and empties the receipt field" \
  || bad "finalize on green left the log or a non-empty field"
( FAIL=1; FAIL_LOG="$FLT/d.log"; : > "$FAIL_LOG"; finalize_fail_log
  [ -f "$FAIL_LOG" ] && [ "$FAIL_LOG_FIELD" = "tools/tests/battery-last-fail.log" ] ) \
  && ok "finalize on red keeps the log and names it in the receipt" \
  || bad "finalize on red lost the log or the field name"
# (d) wiring: BOTH receipt writers must declare the field (emit_summary, and the
#     sequential tail). Counts the declaration, so a writer left behind is
#     caught rather than a stray comment satisfying it.
# Read the ARTIFACT UNDER TEST ($0), never the canonical path: a mutant run
# under a sibling name would otherwise inspect the fixed file and pass.
SELF_ABS="$(readlink -f "$0" 2>/dev/null || echo "$0")"
[ "$(grep -cE '^ *printf .*fail_log' "$SELF_ABS")" -ge 2 ] \
  && ok "both receipt writers declare the fail_log field" \
  || bad "a receipt writer is missing the fail_log field ($SELF_ABS)"
rm -rf "$FLT"
# (e) #614 -- THE DISCRIMINATING LEG. A red receipt must be SELF-CONTAINED: the
#     failing rows ride in the receipt, so the NEXT run's truncate of $FAIL_LOG
#     cannot destroy the diagnosis. Drives the real emit_summary in a SUBSHELL
#     (never the parent: it would reset this run's own receipt) and reads the
#     verdict OUT of the produced JSON, never a pipeline rc. On the pre-fix
#     artifact `fail_rows` is absent, so this leg reddens -- and its message
#     reproduces the defect verbatim.
R614="$(mktemp -d)"; mkdir -p "$R614/t/tests"
R614_V="$( ( TOOLS_DIR="$R614/t"; FAIL_LOG="$R614/f.log"
  FAIL_LOG_REL="tools/tests/battery-last-fail.log"; FAIL_LOG_FIELD="tools/tests/battery-last-fail.log"
  FAIL_ROWS_JSON='[]'; FAIL_ROWS_TRUNC='false'; BATTERY_MODE="r614"
  PASS=1; FAIL=1
  printf '  FAIL - r614-probe-leg\n    probe context line\n' > "$FAIL_LOG"
  emit_summary >/dev/null 2>&1 || true
  : > "$FAIL_LOG"
  python3 -c 'import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: print("NOPARSE"); raise SystemExit
rows=d.get("fail_rows")
print("SELF_CONTAINED" if isinstance(rows,list) and any("r614-probe-leg" in r for r in rows) else "LOST")' "$R614/t/tests/battery-last.json" 2>/dev/null || echo NOPARSE ) )"
[ "$R614_V" = "SELF_CONTAINED" ] \
  && ok "red receipt is self-contained: the failing row survives the next run's truncate (#614)" \
  || bad "#614: red receipt NOT self-contained (verdict=$R614_V) -- it names a log the next run destroys"

# (f) truncation must be DECLARED, never silent: over-cap rows still carry their
#     head AND say so. Asserts the flag and that rows actually arrived.
R614_T="$( FAIL_LOG="$R614/big.log"; FAIL_ROWS_CAP=1
  FAIL_ROWS_JSON='[]'; FAIL_ROWS_TRUNC='false'
  printf '  FAIL - one\n  FAIL - two\n  FAIL - three\n' > "$FAIL_LOG"
  battery_capture_fail_rows 2>/dev/null || true
  printf '%s|%s' "$FAIL_ROWS_TRUNC" "$(printf '%s' "$FAIL_ROWS_JSON" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)" )"
case "$R614_T" in
  true'|'1) ok "over-cap rows are captured up to the cap AND the truncation is declared" ;;
  *) bad "#614: truncation not declared or no rows captured (got: ${R614_T:0:40})" ;;
esac

# (g) wiring: BOTH receipt writers must embed fail_rows -- counts the printf
#     field, so a writer left behind is caught rather than a comment satisfying it.
R614_N="$(grep -cE '^ *printf .*"fail_rows": %s' "$SELF_ABS")"
[ "$R614_N" -ge 2 ] \
  && ok "both receipt writers embed fail_rows" \
  || bad "a receipt writer is missing fail_rows ($R614_N of 2 printf lines)"
rm -rf "$R614"

# ---- 77. lib/oc-root.sh resolver coherence (F-L1/F-L2) -----------------------
# Two defects HQ's lens F found in the v0.4.255 regroup's wake, both the
# "green over a surface it cannot see" class:
#   F-L1  oc_tools_dir tested only `[ -f .../lib/oc-root.sh ]`, omitting the
#         `[ ! -L .../lib ]` guard the bootstrap in the SAME FILE calls
#         load-bearing. A borrowed lib/ means that ancestor is not our root.
#   F-L2  the doc block showed a 3-line bootstrap missing BOTH `basename` arms,
#         while 40 of the 42 files carrying a bootstrap ran the 4-line form. A
#         lane copying the documented form silently drops the arms.
# The byte-equality leg is what keeps F-L2 closed: prose cannot drift from the
# callers it documents without reddening here.
section "lib/oc-root.sh resolver coherence (F-L1/F-L2)"
RT="$(mktemp -d)"
mkdir -p "$RT/tools/lib" "$RT/tools/audit"
cp "$TOOLS_DIR/lib/oc-root.sh" "$RT/tools/lib/oc-root.sh"
: > "$RT/tools/lib/oc-notify.sh"
cp "$TOOLS_DIR/lib/oc-root.sh" "$RT/tools/audit/probe.sh"

# F-L2: the documented bootstrap must equal a real caller's, byte for byte.
# Both sides are extracted BY PATTERN, never by line number, so drift in either
# file moves the comparison with it instead of silently comparing nothing.
# The 3 LOGIC lines are compared byte-identically; the trailing `TOOLS_DIR=`
# assignment is asserted by pattern, because tools legitimately annotate it with
# their own comment (oc-deploy carries a Duty-6 note there). Comparing all four
# byte-for-byte would redden on a comment, which is not the arm set F-L2 is about.
DOC="$RT/doc.txt"
sed -n '/^# USAGE/,/^#   TOOLS_DIR=/p' "$TOOLS_DIR/lib/oc-root.sh" \
  | sed 's/^#   //' | grep -E '^(_oc_r=|if \[ "\$\(basename|if \[ -f "\$_oc_r)' > "$DOC"
CALLER="$RT/caller.txt"
grep -E '^(_oc_r=|if \[ "\$\(basename|if \[ -f "\$_oc_r)' \
  "$TOOLS_DIR/ship/oc-deploy" | head -3 > "$CALLER"
if [ -s "$DOC" ] && cmp -s "$DOC" "$CALLER"; then
  ok "oc-root: documented bootstrap == a real caller's ($(wc -l < "$DOC" | tr -d ' ') logic lines, byte-identical)"
else
  bad "oc-root: doc block and caller bootstrap DIVERGE ($(wc -l < "$DOC" | tr -d ' ') doc vs $(wc -l < "$CALLER" | tr -d ' ') caller logic lines)"
fi
grep -q '^TOOLS_DIR="\$OC_TOOLS_DIR"' "$TOOLS_DIR/ship/oc-deploy" \
  && ok "oc-root: caller carries the TOOLS_DIR assignment the doc block shows" \
  || bad "oc-root: doc block shows a TOOLS_DIR assignment the caller does not carry"

# F-L1 arm A — control: a REAL lib/ must still resolve, or the guard broke the
# normal path and every sibling reach with it.
resolved="$(oc_tools_dir "$RT/tools/audit/probe.sh" 2>/dev/null)"
[ "$resolved" = "$RT/tools" ] \
  && ok "oc_tools_dir: real lib/ resolves to the tools root" \
  || bad "oc_tools_dir: real lib/ resolved to '$resolved' (want $RT/tools)"

# F-L1 arm B — the defect: a SYMLINKED lib/ is a borrowed lib/, so that ancestor
# is not our root. Pre-fix this returned the fixture root.
rm -rf "$RT/tools/lib"
ln -s "$TOOLS_DIR/lib" "$RT/tools/lib"
leaked="$(oc_tools_dir "$RT/tools/audit/probe.sh" 2>/dev/null)"
[ "$leaked" != "$RT/tools" ] \
  && ok "oc_tools_dir: symlinked lib/ is REJECTED (does not adopt the fixture)" \
  || bad "oc_tools_dir: symlinked lib/ was ACCEPTED — the F-L1 defect is back"

# The `basename != tools` arm: a marker-less tools/ must STOP the walk rather
# than let it adopt an ancestor's marker as its root. Without the arm the helper
# returns $ANC — a root ABOVE the tree the tool actually lives in.
ANC="$(mktemp -d)"
mkdir -p "$ANC/lib" "$ANC/tools/sub"
cp "$TOOLS_DIR/lib/oc-root.sh" "$ANC/lib/oc-root.sh"
: > "$ANC/lib/oc-notify.sh"
cp "$TOOLS_DIR/lib/oc-root.sh" "$ANC/tools/sub/probe.sh"
adopted="$(oc_tools_dir "$ANC/tools/sub/probe.sh" 2>/dev/null)"
[ "$adopted" != "$ANC" ] \
  && ok "oc_tools_dir: marker-less tools/ stops the walk (no ancestor adoption)" \
  || bad "oc_tools_dir: adopted the ANCESTOR root $ANC across a marker-less tools/ — basename arm missing"
rm -rf "$ANC" "$RT"

# ---- 78. negctl-* controls invoke their tool at a RESOLVABLE path ------------
# The negctl-* family is standalone by design (not run here -- some take minutes
# and run full selftests on copied trees). But a control that cannot run is
# decoration: on the v0.4.255 regroup three of five silently began invoking their
# tool at a FLAT path (`$SRC/oc-health`, `$WORK/baseline/oc-commit`) after the
# fleet moved into kind subdirs, and reported "guard is inert" instead of testing
# anything. Nothing noticed for hours.
#
# The assertion is deliberately narrow: no control may invoke its tool as a
# DIRECT child of a tools dir. That is the exact shape the regroup broke, and it
# has no false positives on runtime-composed paths (`$WORK/mut_<label>/...`) or
# on prose naming an old layout.
for _nc in "$TOOLS_DIR"/tests/negctl-*; do
  [ -e "$_nc" ] || continue
  _nb="$(basename "$_nc")"
  # A flat invocation: a variable path ending in a tools dir, then /oc-<name>.
  _flat="$(grep -nE '\$[A-Za-z_][A-Za-z0-9_]*/(baseline/|mut_[a-z_]*/|mut/)?oc-[a-z0-9-]+' "$_nc" \
            | grep -vE '/(state|git|audit|ship|issue|harvest|smoke|notify|tests|lib|tools)/' \
            | head -3)"
  [ -z "$_flat" ] \
    && ok "negctl $_nb: invokes its tool at a resolvable (non-flat) path" \
    || bad "negctl $_nb: FLAT tool invocation -- post-regroup this cannot resolve: $(printf '%s' "$_flat" | head -1 | cut -c1-90)"
done

# The extractor exits at the receipt write, so a numbered section placed AFTER
# it extracts to an empty chunk and runs ZERO legs while the run still reports a
# clean summary. Measured 2026-09-25: section 78 landed there and the battery
# count did not move (255 -> 255). Assert the extractor can reach the LAST
# numbered section, so this trap reddens instead of hiding.
_nch="$(grep -cE '^# ---- [0-9]' "$0")"
_reach="$(awk -v want="$_nch" '
    /^# ---- [0-9]/ { n++; insec = (n == want); next }
    /^verdict=PASS/ { exit }
    n == 0 || insec { print }
  ' "$0" | grep -cE '^# ---- [0-9]|oc-|negctl')"
[ "${_reach:-0}" -gt 0 ] \
  && ok "battery extractor reaches the LAST numbered section (chunk $_nch)" \
  || bad "battery extractor CANNOT reach section $_nch — it sits after the receipt write, so it runs zero legs in parallel mode"



# ---- 79. oc-issue-create (creation-time parent gate, #599) -------------------
if [ -f "$TOOLS_DIR/issue/oc-issue-create" ]; then
  bash "$TOOLS_DIR/issue/oc-issue-create" --selftest >/dev/null 2>&1 \
    && ok "oc-issue-create --selftest" || bad "oc-issue-create --selftest"
  bash "$TOOLS_DIR/issue/oc-issue-create" --help >/dev/null 2>&1 \
    && ok "oc-issue-create --help rc=0" || bad "oc-issue-create --help rc=0"
  # The gate's whole point: a fix-titled issue with no parent is REFUSED. Run it
  # with the stub gh so no real issue can be created.
  _ic_t="$(mktemp -d)"; mkdir -p "$_ic_t/bin"
  printf '#!/bin/sh\ncase "$1 $2" in "issue list") echo "[{\"number\":1,\"title\":\"fix(tools): x\"}]" ;; *) exit 0 ;; esac\n' > "$_ic_t/bin/gh"
  chmod +x "$_ic_t/bin/gh"
  OC_ISSUE_CREATE_GH="$_ic_t/bin/gh" bash "$TOOLS_DIR/issue/oc-issue-create" \
    --title "fix(tools): battery probe" --body x >/dev/null 2>&1
  [ $? -eq 3 ] && ok "oc-issue-create REFUSES a fix title with no parent (rc=3)" \
               || bad "oc-issue-create did NOT refuse a fix title with no parent"
  rm -rf "$_ic_t"
fi

# ---- 80. oc-issue-scope (body-surface classifier, #608) ----------------------
if [ -f "$TOOLS_DIR/issue/oc-issue-scope" ]; then
  bash "$TOOLS_DIR/issue/oc-issue-scope" --selftest >/dev/null 2>&1 \
    && ok "oc-issue-scope --selftest" || bad "oc-issue-scope --selftest"
  bash "$TOOLS_DIR/issue/oc-issue-scope" --help >/dev/null 2>&1 \
    && ok "oc-issue-scope --help rc=0" || bad "oc-issue-scope --help rc=0"

  # Hermetic end-to-end: gh is STUBBED (no network) and the tracked-path index
  # comes from the real repos on disk, so the verdicts are deterministic.
  # The three specimens are the failure variants hand-caught in one session.
  _sq_t="$(mktemp -d)"; mkdir -p "$_sq_t/bin"
  cat > "$_sq_t/bin/gh" <<'SQGH'
#!/bin/sh
# $1=issue $2=view ... ; emit the specimen body for the requested number.
case "$*" in
  *"view 531"*) printf '{"number":531,"title":"test(isolation): x","body":"- Surface: `src/tests/**` — Editor territory, not tools/**."}' ;;
  *"view 439"*) printf '{"number":439,"title":"fix(notify): x","body":"run_tool_loop{...}: tools/registry.rs:428: Executing tool: session_notify"}' ;;
  *"view 419"*) printf '{"number":419,"title":"fix(tools): notify schema","body":"The fix lands in src/brain/tools/subagent/notify.rs — Editor territory."}' ;;
  *) exit 1 ;;
esac
SQGH
  chmod +x "$_sq_t/bin/gh"
  _sq() { PATH="$_sq_t/bin:$PATH" bash "$TOOLS_DIR/issue/oc-issue-scope" "$@" 2>/dev/null; }

  # (a) NEGATION — a token inside a negation is not a surface claim.
  _sq 531 | grep -q "^#531  OUT" \
    && ok "oc-issue-scope: #531 negated mention buckets OUT" \
    || bad "oc-issue-scope: #531 negated mention did NOT bucket OUT"
  # (b) SUBSTRING — a truncated log path is not a surface claim (no .rs under tools/).
  _sq 439 | grep -q "^#439  UNPINNED" \
    && ok "oc-issue-scope: #439 truncated log path is not a claim" \
    || bad "oc-issue-scope: #439 truncated log path read as a claim"
  # (c) TITLE-PREFIX — the body decides, and the disagreement is FLAGGED.
  _sq 419 | grep -q "^#419  OUT" \
    && ok "oc-issue-scope: #419 fix(tools) title + src body buckets OUT" \
    || bad "oc-issue-scope: #419 title prefix decided the bucket"
  _sq 419 | grep -q "disagrees with the body surface" \
    && ok "oc-issue-scope: #419 title/body disagreement is FLAGGED" \
    || bad "oc-issue-scope: title/body disagreement was silent"

  # DISCRIMINATING CONTROL: the naive shape a lane writes by hand (substring, no
  # polarity, no tracked-path resolution) buckets ALL THREE IN. If this control
  # ever stops being IN, the legs above have stopped measuring anything.
  _sq_naive() {
    printf '%s' "$2" | python3 -c '
import re,sys
b=sys.stdin.read()
hits=re.findall(r"(?:tools|\.github)/[A-Za-z0-9_./*-]*", b)
print("IN" if hits else "UNPINNED")'
  }
  [ "$(_sq_naive x '- Surface: `src/tests/**` — Editor territory, not tools/**.')" = "IN" ] \
    && ok "oc-issue-scope control: the NAIVE substring shape reads #531 as IN (legs discriminate)" \
    || bad "oc-issue-scope control: the naive shape did NOT read #531 as IN -- legs may be vacuous"
  rm -rf "$_sq_t"
fi
# ---- 81. SIGPIPE pipeline-form carrier guard (#660) -------------------------
# The CLASS, not one instance: `printf ... | grep -q` under `set -o pipefail`
# returns 141 (SIGPIPE) DESPITE a successful match, once the payload exceeds the
# kernel's 64 KiB pipe buffer and grep exits before the writer finishes. #660
# replaced 92 sites; FOUR came back within 36 minutes, in the same file, because
# nothing carried the rule. This section IS the carrier.
#
# Measured (peer receipt, 60 trials/row, two runs): 8 KiB 0/60, 32 KiB 0-2/60,
# 56 KiB 4-7/60, 64 KiB 33-48/60, 128 KiB 60/60; here-string form 0/60 at every
# size. Every site standing today pipes a small payload and NONE can flip at its
# current size -- the reason to forbid the form is that nothing stops a payload
# from growing, not that it is failing now.
#
# The guard must be able to SEE its own class, or a clean result means nothing:
# the canary below proves the detector fires on a planted site.
# ---------------------------------------------------------------------------
echo "== SIGPIPE pipeline-form guard (#660) =="

# Two exclusions, both about what is NOT a site:
#   - the generated-ignored sidecar class (.bak / .bak-* / .pre-*), which the
#     edit tool writes beside every file it touches -- sidecars are NOT code
#     (#691: this scan reported 6 live sites, every one inside a sidecar);
#   - comments, which quote the form without being it.
# The old `printf '%s\n'` exemption was REMOVED by #693: it hid a real site
# in oc-lint-laws while its stated premise (newline-terminated, [ -n ]-guarded)
# says nothing about SIGPIPE, which is payload-size gated.
_SG_HITS="$(grep -rnP "printf[^|]*\|\s*grep\s+-q" "$TOOLS_DIR" 2>/dev/null \
  | grep -v '/tests/run.sh:' \
  | grep -vE '^[^:]+\.(bak|pre-)' \
  | grep -v ':[0-9]*: *#' \
  || true)"
_SG_N="$(printf '%s\n' "$_SG_HITS" | grep -c . || true)"

# The guard must be able to SEE its own class, or a clean result means nothing.
_SG_CANARY="$(printf '%s\n' "printf '%s' \"\$x\" | grep -q y" \
  | grep -cP "printf[^|]*\|\s*grep\s+-q" || true)"
[ "$_SG_CANARY" = "1" ] \
  && ok "SIGPIPE guard observes its own class (canary fires)" \
  || bad "SIGPIPE guard cannot see the class it forbids (canary=$_SG_CANARY)"
# #693: the revision above ALSO exempted the `printf '%s\n...'` shape by
# pattern, so this form was invisible while standing in oc-lint-laws. Run the
# SAME filter chain over a fixture carrying that shape: a guard that cannot see
# the shape it used to exempt is how the live site survived the #660 sweep.
_SGF="$(mktemp -d)"
printf "printf '%%s\\\\n%%s' \"\$a\" \"\$b\" | grep -qF x\n" > "$_SGF/oc-canary"
_SG_CAN_F="$(grep -rnP "printf[^|]*\|\s*grep\s+-q" "$_SGF" 2>/dev/null \
  | grep -v ':[0-9]*: *#' \
  | grep -c . || true)"
rm -rf "$_SGF"
[ "$_SG_CAN_F" = "1" ] \
  && ok "SIGPIPE guard sees the printf-format shape it used to exempt (#693)" \
  || bad "SIGPIPE guard CANNOT see the printf-format shape (canary=$_SG_CAN_F) — the exemption blind spot is back" 
[ "$_SG_N" = "0" ] \
  && ok "no printf-pipe-grep-q sites remain (use <<< or oc_has)" \
  || bad "printf-pipe-grep-q sites present: $_SG_N (use <<< or oc_has)"

if [ "$_SG_N" != "0" ]; then
  printf '%s\n' "$_SG_HITS" | sed 's/^/      /' | head -20
fi
# #691 controls, BOTH directions: a sidecar carrying the form must be
# EXCLUDED (it is not code), and a live source file carrying it must still be
# SEEN -- otherwise the filter has degraded to "accept nothing".
_SGF2="$(mktemp -d)"; _SGF3="$(mktemp -d)"
printf "printf '%%s' \"\$x\" | grep -q y\n" > "$_SGF2/oc-canary.bak"
printf "printf '%%s' \"\$x\" | grep -q y\n" > "$_SGF3/oc-real"
_SG_CAN_B="$(grep -rnP "printf[^|]*\|\s*grep\s+-q" "$_SGF2" 2>/dev/null \
  | grep -vE '^[^:]+\.(bak|pre-)' \
  | grep -c . || true)"
_SG_CAN_C="$(grep -rnP "printf[^|]*\|\s*grep\s+-q" "$_SGF3" 2>/dev/null \
  | grep -vE '^[^:]+\.(bak|pre-)' \
  | grep -c . || true)"
rm -rf "$_SGF2" "$_SGF3"
[ "$_SG_CAN_B" = "0" ] \
  && ok "SIGPIPE scan excludes the sidecar class (#691)" \
  || bad "SIGPIPE scan counts a .bak sidecar as code (canary=$_SG_CAN_B)"
[ "$_SG_CAN_C" = "1" ] \
  && ok "SIGPIPE scan still sees a live source file (no over-filter, #691)" \
  || bad "SIGPIPE scan OVER-filters: a live source file was skipped (canary=$_SG_CAN_C)"


# ---- 82. shell-quoting guard: python3 engine fences (#670) ------------------
# CLASS: a python body fenced so the SHELL interprets it.
#   ARM A  a -c body opened with a DOUBLE quote -- a backtick inside it runs
#          command substitution, so the body's own text becomes shell input.
#   ARM B  a heredoc that feeds python3 whose DELIMITER IS UNQUOTED -- $VAR and
#          backticks expand inside the body before python ever sees it.
# Both have cost real work here: a backtick inside a -c body ran a phantom
# "harvest: command not found", and an unquoted heredoc carrying a doubled
# triple-quote closed the enclosing shell string and destroyed 1607 lines of a
# tool (2026-09-18). The fleet measures 0 sites today, so this section is a
# CARRIER, not a sweep: the first new site reddens here instead of surfacing as
# a phantom command in production.
#
# BLIND SPOT, stated rather than implied: $VAR and $(cmd) inside a DOUBLE-quoted
# body are NOT detected. They cannot be told apart from a shell argument that
# FOLLOWS the closing quote without a full parser, and a rule that guessed
# would fire on this tree's 28 legitimate one-line -c calls. Arm A therefore
# keys on the BACKTICK, which is unambiguous inside a double-quoted body and is
# the form the incident took; arm B keys on the delimiter being unquoted.
section "shell-quoting guard (python3 -c / heredoc fences)"
SQD="$(mktemp -d)"
cat > "$SQD/scan.py" <<'SQSCANEOF'
import os, re, sys

def scan_file(p):
    try:
        text = open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        return []
    out = []
    # ARM A: a DOUBLE-quoted python3 -c body carrying a backtick.
    for m in re.finditer(r'python3\s+-c\s+"', text):
        i = m.end()
        while i < len(text):
            c = text[i]
            if c == '\\':
                i += 2
                continue
            if c == '`':
                out.append((p, 'ARM-A: backtick inside a double-quoted python3 -c body'))
                break
            if c == '"':
                break
            i += 1
    # ARM B: a heredoc feeding python3 whose delimiter is UNQUOTED. The
    # delimiter must be a bare word, so a quoted one does not match by
    # construction -- which is what separates the hazard from the safe form.
    for m in re.finditer(r'python3\b[^\n]*?<<-?\s*([A-Za-z_][A-Za-z0-9_]*)', text):
        out.append((p, 'ARM-B: unquoted heredoc (delimiter %s) feeds python3' % m.group(1)))
    return out

target = sys.argv[1]
if os.path.isdir(target):
    files = []
    for dp, dn, fn in os.walk(target):
        dn[:] = [d for d in dn if d not in ('__pycache__', '.git')]
        files.extend(os.path.join(dp, f) for f in fn)
else:
    files = [target]
for f in sorted(files):
    for p, msg in scan_file(f):
        print('%s: %s' % (p, msg))
SQSCANEOF
# CANARY, built by INTERPOLATION. This file lives under tools/, so the live
# scan reads it: a hazard written literally here would be found as a REAL site
# and the leg would false-positive against its own canary. The backtick comes
# from its octal escape and the heredoc delimiters from %s, so no literal
# hazard text exists in this file.
SQ_BT="$(printf '\140')"
printf 'python3 -c "print(%sdate%s)"\n' "$SQ_BT" "$SQ_BT" > "$SQD/hazard.sh"
printf 'python3 - "$@" <<%s\nprint(1)\nPYEOF\n' "PYEOF" >> "$SQD/hazard.sh"
printf "python3 -c 'print(1)'\n" > "$SQD/safe.sh"
printf 'python3 - "$@" <<%s\nprint(1)\nPYEOF\n' "'PYEOF'" >> "$SQD/safe.sh"
SQ_HAZ="$(python3 "$SQD/scan.py" "$SQD/hazard.sh" 2>&1)"
SQ_SAFE="$(python3 "$SQD/scan.py" "$SQD/safe.sh" 2>&1)"
case "$SQ_HAZ" in *ARM-A*) ok "shell-quoting: backtick in a double-quoted -c body is SEEN" ;;
  *) bad "shell-quoting: ARM A cannot fire (canary unseen: $SQ_HAZ)" ;; esac
case "$SQ_HAZ" in *ARM-B*) ok "shell-quoting: an unquoted heredoc feeding python3 is SEEN" ;;
  *) bad "shell-quoting: ARM B cannot fire (canary unseen: $SQ_HAZ)" ;; esac
[ -z "$SQ_SAFE" ] && ok "shell-quoting: the SAFE fence forms stay green (control)" \
  || bad "shell-quoting: the control fired on safe forms: $SQ_SAFE"
SQ_LIVE="$(python3 "$SQD/scan.py" "$TOOLS_DIR" 2>&1)"
if [ -z "$SQ_LIVE" ]; then
  ok "shell-quoting: no hazard site in the fleet"
else
  bad "shell-quoting: $(printf '%s' "$SQ_LIVE" | wc -l) hazard site(s):
$(printf '%s' "$SQ_LIVE" | head -5)"
fi
rm -rf "$SQD"

# ---- 83. oc-vendor-drift: vendored copies match their upstream (#700) --------
# The register is the meta factory's tool; this fleet carries a copy. The copy is
# allowed exactly three DECLARED delta lines (the deployment name); anything else
# is drift. Presence is not behaviour, so the leg drives the guard, not the file.
if [ -x "$TOOLS_DIR/audit/oc-vendor-drift" ]; then
  VD_OUT="$(./tools/audit/oc-vendor-drift 2>&1)"; VD_RC=$?
  if [ -d /root/agent-factories/.git ]; then
    if [ "$VD_RC" -eq 0 ]; then
      ok "oc-vendor-drift: vendored register IN_SYNC with upstream rc=0"
    else
      bad "oc-vendor-drift rc=$VD_RC on a reachable upstream:
$(printf '%s' "$VD_OUT" | head -5)"
    fi
  else
    # Disclosed skip, never a silent pass: the guard's whole contract is that an
    # unreachable upstream is NOT green, so a battery green here would be a lie.
    case "$VD_OUT" in
      *UPSTREAM_UNREACHABLE*) note "  SKIP oc-vendor-drift: upstream repo absent (disclosed by the guard)" ;;
      *) bad "oc-vendor-drift rc=$VD_RC with the upstream repo ABSENT but no UPSTREAM_UNREACHABLE verdict" ;;
    esac
  fi
  # NEGATIVE CONTROL: an unresolvable recorded ref must be rc 3, never green.
  VD_BAD="$(./tools/audit/oc-vendor-drift --ref 0000000000000000000000000000000000000000 2>&1)"; VD_BRC=$?
  if [ "$VD_BRC" -eq 3 ]; then
    ok "oc-vendor-drift: an unresolvable ref is rc=3, never green (control)"
  else
    bad "oc-vendor-drift: unresolvable ref gave rc=$VD_BRC, contract says 3"
  fi
  VD_ST="$(./tools/audit/oc-vendor-drift --selftest 2>&1)"; VD_SRC=$?
  case "$VD_ST" in
    *"selftest: 8 passed, 0 failed"*) ok "oc-vendor-drift selftest: 8 passed, 0 failed" ;;
    *) bad "oc-vendor-drift selftest: $(printf '%s' "$VD_ST" | tail -2)" ;;
  esac
  [ "$VD_SRC" -eq 0 ] || bad "oc-vendor-drift selftest rc=$VD_SRC"
else
  bad "oc-vendor-drift missing at tools/audit/oc-vendor-drift"
fi

# ---- 84. entry-preamble fixpoint: a relative invocation must not hang (#708) --
section "entry-preamble fixpoint + relative invocation (#708)"
# A lane that cds into a tool's directory and runs ./name used to SPIN FOREVER.
# The entry preamble walked up with `dirname "$0"`; with $0='./tool' that yields
# '.', and `dirname "."` is '.' -- a FIXPOINT, so the walk never advanced, all
# three guards stayed true, and the tool emitted nothing at 100% CPU. It had been
# copy-pasted into every fleet tool. Section 60 drives $t as an ABSOLUTE path
# (its glob is "$TOOLS_DIR"/...), so it cannot observe this class: the fixpoint
# needs a RELATIVE invocation to reproduce.
#
# STATIC ARM (exact, whole fleet): anything that still walks up must carry the
# fixpoint break. Keyed on the BREAK's presence, never on the old line's absence,
# so this leg asserts the fix rather than merely failing to find the bug.
EP_N=0; EP_BAD=0
for t in "$TOOLS_DIR"/oc-* "$TOOLS_DIR"/*/oc-* "$TOOLS_DIR"/tests/run.sh; do
  [ -f "$t" ] || continue
  case "$t" in */archive/*|*.bak|*.bak-*|*.pre-*) continue ;; esac
  grep -qF 'while [ "$_oc_r" != "/" ]' "$t" 2>/dev/null || continue
  EP_N=$((EP_N+1))
  if grep -qF '[ "$_oc_r" != "." ]' "$t" 2>/dev/null; then
    :
  else
    EP_BAD=$((EP_BAD+1))
    bad "$(basename "$t"): walk-up WITHOUT the fixpoint break (#708)"
  fi
done
# FLOOR: the preamble was in 44 files when this leg was written (43 tools + lib +
# run.sh). A glob that silently matches fewer reddens here instead of passing on a
# shrunken population -- the silent-skip class this battery exists to catch.
if [ "$EP_N" -ge 40 ]; then
  ok "fixpoint break present in all $EP_N file(s) carrying the walk-up"
else
  bad "walk-up enumerated only $EP_N file(s) (floor 40) -- the glob is not seeing the fleet"
fi

# DYNAMIC ARM (behavioural): drive a sample by RELATIVE path from the tool's OWN
# directory -- the exact invocation that hung. One representative per kind, so a
# regression in any single kind is observable without paying a fleet-wide --help
# sweep for the second time in this battery.
EP_DYN=0
for rel in state/oc-ledger ship/oc-deploy harvest/oc-prchecks audit/oc-lint-laws \
           smoke/oc-smoke git/oc-commit issue/oc-issue-scope notify/oc-ping-proof \
           tests/run.sh; do
  t="$TOOLS_DIR/$rel"
  [ -f "$t" ] || { bad "relative-invocation sample missing: $rel"; continue; }
  EP_DYN=$((EP_DYN+1))
  d="$(dirname "$t")"; b="$(basename "$t")"
  # run.sh has NO --help arm (it would execute the whole battery); give it a
  # cheap flag that still forces the preamble to run and then exits.
  case "$rel" in tests/run.sh) _arg="--chunk 999" ;; *) _arg="--help" ;; esac
  # shellcheck disable=SC2086
  # BATTERY_IN_CHUNK is inherited from THIS chunk and disables the nested
  # run.sh --chunk branch (its own guard is `[ -z "${BATTERY_IN_CHUNK:-}" ]`),
  # so it would fall through and execute the whole battery. Clear it.
  ( cd "$d" && OC_TOOLS_NOLOG=1 BATTERY_IN_CHUNK= timeout 20 "./$b" $_arg >/dev/null 2>&1 ); rc=$?
  if [ "$rc" -eq 0 ]; then
    :
  elif [ "$rc" -eq 124 ]; then
    bad "$rel: ./$b HUNG (rc=124) -- the dirname('.') fixpoint is back (#708)"
  else
    bad "$rel: ./$b rc=$rc (expected 0; 124 = fixpoint hang)"
  fi
done
[ "$EP_DYN" -eq 9 ] && ok "relative invocation returns for all $EP_DYN sampled tool(s)" \
  || bad "relative-invocation sample ran $EP_DYN of 9"

# CONTROL -- two-sided, and it does NOT reuse the fleet's literal line (a fixture
# embedding the real preamble would make the static arm above match run.sh's own
# text). The MECHANISM under test is `dirname "." == "."`, so the fixture
# reproduces that mechanism in miniature: the broken form must TIME OUT, and the
# same fixture with the break must RETURN. Without the broken half this leg could
# not tell a working instrument from one that never fires.
EP_FX="$(mktemp -d)"
{
  printf '%s\n' '#!/usr/bin/env bash'
  printf '%s\n' '_oc_r="$(dirname "$0")"'
  printf '%s\n' 'while [ "$_oc_r" != "/" ] && [ "$(basename "$_oc_r")" != "tools" ]; do _oc_r="$(dirname "$_oc_r")"; done'
  printf '%s\n' 'echo reached'
} > "$EP_FX/broken"
{
  printf '%s\n' '#!/usr/bin/env bash'
  printf '%s\n' '_oc_r="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || _oc_r="."'
  printf '%s\n' 'while [ "$_oc_r" != "/" ] && [ "$_oc_r" != "." ] && [ "$(basename "$_oc_r")" != "tools" ]; do _oc_r="$(dirname "$_oc_r")"; done'
  printf '%s\n' 'echo reached'
} > "$EP_FX/fixed"
chmod +x "$EP_FX/broken" "$EP_FX/fixed"
( cd "$EP_FX" && timeout 3 ./broken >/dev/null 2>&1 ); fx=$?
if [ "$fx" -eq 124 ]; then
  ok "fixpoint control: the broken preamble TIMES OUT (the instrument sees the class)"
else
  bad "fixpoint control: broken preamble returned rc=$fx, so this leg cannot detect a hang"
fi
( cd "$EP_FX" && timeout 3 ./fixed >/dev/null 2>&1 ); fx=$?
[ "$fx" -eq 0 ] && ok "fixpoint control: the same fixture WITH the break returns rc=0" \
  || bad "fixpoint control: fixed preamble rc=$fx (expected 0)"
rm -rf "$EP_FX"

# ---- 85. cgroup isolation (#720): the battery must not run in the daemon unit -
section "cgroup isolation (#720)"
# Every command a lane runs inherits the daemon's cgroup
# (`.../app.slice/opencrabs-ops.service`), whose wall is MemoryHigh == MemoryMax
# == 1536 MiB with swap exhausted and whose OOMPolicy=kill tears the WHOLE unit
# down on an allocation that exceeds it -- so a test allocation does not merely
# die, it takes the daemon with it. Measured 2026-09-30: four daemon OOM kills
# (07:46 08:34 10:08 12:05Z), each during a battery run. The test processes are
# small (tens of MiB); the hazard is CO-TENANCY with a full wall, so no test diet
# can fix it -- the run must not BE in that cgroup. The preamble re-execs into a
# transient user scope, a SIBLING of the service and outside its accounting.
#
# The block under test is EXTRACTED FROM THIS FILE, never retyped: $0 is this
# script, and a hand-copied fixture would drift from the code it claims to test.
# The single rewrite is the cgroup INPUT -- the branch taken is a function of
# where the run sits, and a test that can only exercise the branch its own
# environment happens to take asserts nothing. The rewrite's exactness is
# asserted below, so a sed that mangles more than the input reddens here.
CI_FX="$(mktemp -d)"
CI_BLOCK="$CI_FX/iso.sh"
awk '/^# ---- cgroup isolation \(#720\)/,/^# ---- red-receipt transcript/' "$0" \
  | sed '/^# ---- red-receipt transcript/d' > "$CI_BLOCK"
if [ -s "$CI_BLOCK" ] && grep -q 'BATTERY_CGROUP_ISOLATED' "$CI_BLOCK"; then
  ok "isolation block extracted from run.sh ($(wc -l < "$CI_BLOCK") lines)"
else
  bad "#720: isolation block NOT found in run.sh -- the extractor matched nothing"
fi
# INPUT rewrite exactness: exactly one source line may differ (two diff sides).
sed "s|\$(battery_cgroup_path)|\${CI_SVC_CG}|" "$CI_BLOCK" > "$CI_FX/exact.sh"
_nd="$(diff "$CI_BLOCK" "$CI_FX/exact.sh" | grep -c '^[<>]')"
[ "$_nd" -eq 2 ] \
  && ok "cgroup input rewrite touches exactly one line (the branch input, not the logic)" \
  || bad "#720: input rewrite changed $_nd diff sides (expected 2) -- the fixture is not the block"

# Stub systemd-run/systemctl: they log their argv (so the re-exec CONTRACT is
# observable) and exit with settable rc (so the probe's REFUSAL path is drivable).
CI_SB="$CI_FX/bin"; mkdir -p "$CI_SB"
cat > "$CI_SB/systemd-run" <<'CI_STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${CI_SR_LOG:?}"
case " $* " in *" true "*) exit "${CI_PROBE_RC:-0}" ;; esac
exit 0
CI_STUB
cat > "$CI_SB/systemctl" <<'CI_STUB'
#!/usr/bin/env bash
if [ "${1:-}" = "--user" ] && [ "${2:-}" = "is-system-running" ]; then exit "${CI_MGR_RC:-0}"; fi
exit 0
CI_STUB
chmod +x "$CI_SB/systemd-run" "$CI_SB/systemctl"

# Harness: source the block with a synthetic cgroup path, then report whether we
# SURVIVED. A working re-exec REPLACES this process, so "SURVIVED" is the FAILURE
# signal in the arm that wants isolation -- and the PASS signal in the arms that
# must not re-exec (already isolated, or opted out).
cat > "$CI_FX/harness.sh" <<'CI_HARNESS'
#!/usr/bin/env bash
set -u
note() { printf '%s\n' "$*"; }
PATH="${CI_SB:?}:$PATH"; export PATH
if [ -n "${CI_SYNTH_CG:-}" ]; then
  sed "s|\$(battery_cgroup_path)|\${CI_SYNTH_CG}|" "$CI_BLOCK" > "$CI_BLOCK.synth" || exit 9
  CI_BLOCK="$CI_BLOCK.synth"
fi
. "$CI_BLOCK"
printf 'SURVIVED cg=%s iso=%s\n' "${BATTERY_SELF_CGROUP:-}" "${BATTERY_SELF_CGROUP_ISO:-}"
CI_HARNESS
chmod +x "$CI_FX/harness.sh"
ci_out() { # $1 = synthetic cgroup path; remaining: env assignments
  local synth="$1"; shift
  : > "$CI_FX/sr.log"
  env -u BATTERY_IN_CHUNK -u BATTERY_CGROUP_ISOLATED -u OC_BATTERY_NO_CGROUP \
      "CI_SB=$CI_SB" "CI_BLOCK=$CI_BLOCK" "CI_SYNTH_CG=$synth" "CI_SR_LOG=$CI_FX/sr.log" \
      "$@" bash "$CI_FX/harness.sh" 2>&1
}
CI_SVC_CG='/user.slice/user-0.slice/user@0.service/app.slice/opencrabs-ops.service'
CI_SCOPE_CG='/user.slice/user-0.slice/user@0.service/app.slice/oc-battery.scope'

# LEG 1 -- inside a .service unit the block MUST re-exec, with #720's caps.
_1="$(ci_out "$CI_SVC_CG" CI_PROBE_RC=0)"
case "$_1" in
  *SURVIVED*) bad "#720: inside a .service cgroup the block did NOT re-exec (isolation inert)";;
  *"re-exec into a transient scope"*) ok "#720: inside a .service unit the run re-execs into a transient scope";;
  *) bad "#720: neither a re-exec nor a diagnostic for a .service cgroup";;
esac
_sr="$(cat "$CI_FX/sr.log" 2>/dev/null || true)"
_ln="$(printf '%s\n' "$_sr" | grep -c .)"
[ "$_ln" -eq 2 ] \
  && ok "#720: probe then real exec -- 2 invocations, and the probe is what makes it fail-open" \
  || bad "#720: expected 2 stub invocations, got $_ln"
if [ "$(printf '%s\n' "$_sr" | grep -c 'MemoryMax=1024M')" -eq 2 ] \
   && [ "$(printf '%s\n' "$_sr" | grep -c 'MemorySwapMax=512M')" -eq 2 ] \
   && [ "$(printf '%s\n' "$_sr" | grep -c 'CPUQuota=300%')" -eq 2 ] \
   && [ "$(printf '%s\n' "$_sr" | grep -c 'TasksMax=128')" -eq 2 ]; then
  ok "#720: both invocations carry the full cap set (one property list, never divergent)"
else
  bad "#720: cap set differs between probe and real exec: $_sr"
fi
case "$_sr" in
  *"--user --scope"*) ok "#720: re-exec requests a user transient scope";;
  *) bad "#720: re-exec argv lacks --user --scope";;
esac

# LEG 2 -- the scope creation is REFUSED: must fail OPEN, not exit RED.
_2="$(ci_out "$CI_SVC_CG" CI_PROBE_RC=1)"
case "$_2" in
  *SURVIVED*) ok "#720: a refused scope does NOT replace the run (fail-open holds)";;
  *) bad "#720: a refused scope swallowed the run -- a harness error would read as a RED verdict";;
esac
case "$_2" in
  *"could not create a transient scope"*) ok "#720: refusal is reported as a WARNING, and the battery still runs";;
  *) bad "#720: refusal path emitted no diagnostic";;
esac
_ln="$(printf '%s\n' "$(cat "$CI_FX/sr.log" 2>/dev/null)" | grep -c .)"
[ "$_ln" -eq 1 ] \
  && ok "#720: refusal makes exactly one attempt (no second exec after a refusal)" \
  || bad "#720: refusal path made $_ln invocations (expected 1)"

# LEG 3 -- already outside a service cgroup: no isolation, no re-exec.
_3="$(ci_out "$CI_SCOPE_CG" CI_PROBE_RC=0)"
case "$_3" in
  *"already outside a service cgroup"*SURVIVED*) ok "#720: a .scope cgroup is left alone (no needless re-exec)";;
  *) bad "#720: an already-isolated cgroup was mis-handled: $_3";;
esac

# LEG 4 -- the documented opt-out.
_4="$(ci_out "$CI_SVC_CG" CI_PROBE_RC=0 OC_BATTERY_NO_CGROUP=1)"
case "$_4" in
  *SURVIVED*) ok "#720: OC_BATTERY_NO_CGROUP=1 opts out of isolation";;
  *) bad "#720: the opt-out still re-exec'd";;
esac
[ -s "$CI_FX/sr.log" ] \
  && bad "#720: the opt-out still invoked systemd-run" \
  || ok "#720: the opt-out invoked no scope at all"

# NEGATIVE CONTROL (neuter-the-code): with the exec line removed, LEG 1's signal
# must INVERT. Without this the leg could be passing because the harness never
# reaches the block, not because isolation works.
sed 's|^      exec "\$_oc_sr"|      : "\$_oc_sr"|' "$CI_BLOCK" > "$CI_FX/neutered.sh"
_ci_orig="$CI_BLOCK"; CI_BLOCK="$CI_FX/neutered.sh"
_5="$(ci_out "$CI_SVC_CG" CI_PROBE_RC=0)"
CI_BLOCK="$_ci_orig"
case "$_5" in
  *SURVIVED*) ok "#720 NEGATIVE CONTROL: a neutered re-exec IS detected (the leg can fail)";;
  *) bad "#720 NEGATIVE CONTROL: neutered re-exec still not detected -- this leg is inert";;
esac
rm -rf "$CI_FX"
# ---- 86. fleet-wide: no arg arm may swallow a missing flag value (#750) -----
# A value-taking arm written `--flag) VAR="${2:-}"; shift 2 ;;` HANGS forever
# when the flag is the LAST argument: `shift 2` with $#=1 returns 1 and does NOT
# shift, so `while [ $# -gt 0 ]` re-reads the same $1, and `${2:-}` suppresses
# the unbound-variable error that would otherwise kill the loop. 59 arms across
# 14 tools did this; every one was reachable by a plain typo, and the tool never
# returned. The guard is `[ $# -ge 2 ] || { ...; exit 2; };` BEFORE the read.
# Two traps the guard must avoid, both measured on the fix:
#   * `usage` is NOT always defined (7 of the 14 define no usage()), so a bare
#     `usage;` bail prints `usage: command not found` -- and under `set -e`
#     (oc-notify-fanout) that exits 127 BEFORE the intended 2.
#   * the bail must sit before the assignment, or the arm still reads an empty
#     $2 first.
# This is a SHAPE property, decidable without executing the tool -- hence a
# static scan rather than 59 timed invocations. Keyed on shape, never on a tool
# name, so a new tool inherits the guard simply by existing.
_hg_scan() { # $1 = dir to scan; prints "<file>:<line>" per unguarded arm
  python3 - "$1" <<'PY'
import os,re,sys
root=sys.argv[1]
arm=re.compile(r'^\s*(--[a-z][a-z0-9-]*)\)(.*)$')
bail=re.compile(r'\b(usage|die|fail|exit|return)\b')
for dp,_,fns in os.walk(root):
    if '__pycache__' in dp: continue
    for fn in sorted(fns):
        if not fn.startswith('oc-'): continue
        if '.bak' in fn or fn.endswith(('.orig','.rej')): continue
        p=os.path.join(dp,fn)
        try: lines=open(p,encoding='utf-8',errors='replace').read().split('\n')
        except OSError: continue
        for i,l in enumerate(lines,1):
            m=arm.match(l)
            if not m: continue
            body=m.group(2)
            if '${2:-}' not in body or 'shift 2' not in body: continue
            pre=body[:body.index('shift 2')].replace('${2:-}','')
            if bail.search(pre): continue
            print("%s:%d"%(p,i))
PY
}
_hg_hits="$(_hg_scan "$TOOLS_DIR")"
if [ -z "$_hg_hits" ]; then
  ok "#750: no unguarded value-taking arg arm anywhere in the fleet"
else
  bad "#750: $(printf '%s\n' "$_hg_hits" | wc -l) unguarded value-taking arg arm(s) -- each HANGS on a missing value"
  printf '%s\n' "$_hg_hits" | sed 's/^/        /' | record
fi

# NEGATIVE CONTROL (neuter-the-code): a fixture carrying the shape MUST be
# flagged, or the leg could be green because the scanner itself is inert. The
# guarded fixture is the anti-vacuity half: a scanner that flagged everything
# would pass the first leg while reporting every healthy arm as a defect.
_hg_fx="$(mktemp -d)"
printf '%s\n' '#!/bin/sh' 'while [ $# -gt 0 ]; do case "$1" in' \
  '  --repo) REPO="${2:-}"; shift 2 ;;' 'esac; done' > "$_hg_fx/oc-fake"
printf '%s\n' '#!/bin/sh' 'while [ $# -gt 0 ]; do case "$1" in' \
  '  --repo) [ $# -ge 2 ] || { echo x; exit 2; }; REPO="$2"; shift 2 ;;' \
  '  --issue) ISSUE="${2:-}"; [ -n "$ISSUE" ] || usage; shift 2 ;;' \
  'esac; done' > "$_hg_fx/oc-good"
_hg_ctrl="$(_hg_scan "$_hg_fx")"
if [ "$_hg_ctrl" = "$_hg_fx/oc-fake:3" ]; then
  ok "#750 NEGATIVE CONTROL: the scanner flags the shape and ONLY the shape (the leg can fail)"
else
  bad "#750 NEGATIVE CONTROL: scanner did not isolate the fixture (got '$(printf '%s' "$_hg_ctrl" | tr '\n' ' ')') -- this leg is inert"
fi
rm -rf "$_hg_fx"

verdict=PASS; [ "$FAIL" -eq 0 ] || verdict=FAIL
finalize_fail_log
battery_capture_fail_rows
_tch=false
_tch=false
_tch=false
_fp_tail="$(_battery_tree_fp)"
[ "$_fp_tail" = "$BATTERY_FP_START" ] || _tch=true
BATTERY_WALL_MS="$(( ($(date +%s%N) - BATTERY_T0) / 1000000 ))"
printf '{\n  "path": "%s",\n  "ts": "%s",\n  "pass": %d,\n  "fail": %d,\n  "verdict": "%s",\n  "fail_log": "%s",\n  "fail_rows": %s,\n  "fail_rows_truncated": %s,\n  "tree_changed": %s,\n  "cgroup": "%s",\n  "cgroup_isolated": %s,\n  "wall_ms": %s,\n  "timing": %s\n}\n' \
  "$TOOLS_DIR/tests/battery-last.json" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$PASS" "$FAIL" "$verdict" "$FAIL_LOG_FIELD" \
  "$FAIL_ROWS_JSON" "$FAIL_ROWS_TRUNC" "$_tch" "$BATTERY_SELF_CGROUP" "$BATTERY_SELF_CGROUP_ISO" "$BATTERY_WALL_MS" "$BATTERY_SECTIONS_JSON" \
  > "$TOOLS_DIR/tests/battery-last.json"
[ "$_tch" = false ] || note "  WARNING: the tools tree CHANGED during this run — a red here may describe the edit, not the tool; re-run on a quiet tree"

# ---- summary ----------------------------------------------------------------
note ""
note "=============================="
note "  PASS: $PASS   FAIL: $FAIL   (receipt: tools/tests/battery-last.json = $verdict)"
battery_timing_lines
note "=============================="
[ "$FAIL" -eq 0 ] || note "tests FAILED (nonzero exit below)"
[ "$FAIL" -eq 0 ]
