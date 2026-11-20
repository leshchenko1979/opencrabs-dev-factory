#!/usr/bin/env bash
# =============================================================================
# oc-snap.sh — run a long-running tool from an immutable MIRROR of tools/.
#
# WHY: bash does not hold a script in memory. It reads from the file by byte
# offset as it goes, so an in-place rewrite (truncate + write, inode preserved
# — what both write_file and edit_file do, and what git checkout/pull do too)
# makes the interpreter's saved offset land in the NEW content. It resumes
# mid-line and executes whatever is there: silent death, and a false-success rc
# when the caller reads a pipe's status instead.
#
# Incident + evidence: leshchenko1979/opencrabs#167
# Design + probe receipts:
#   ~/.opencrabs/profiles/ops/projects/toolsmith-167/files/design-inplace-rewrite-guard.md
#
# USAGE — as the first executable lines of a long-running tool, directly under
# the shebang and BEFORE `set -e`/`set -u` and before any lib is sourced:
#
#   _OC_SNAP="$OC_TOOLS_DIR/lib/oc-snap.sh"   # after the oc-root bootstrap
#   if [ -f "$_OC_SNAP" ]; then . "$_OC_SNAP"; oc_snap_guard "$0" "$@"; fi
#
# oc_snap_guard either EXECs (it never returns in that case) or returns 0 with
# the tool running from an immutable copy. It never aborts a run: any failure
# falls back to running directly, with a warning on stderr.
#
# Env: OC_SNAP_ROOT (mirror root, default /tmp), OC_SNAP_DEPTH (internal).
# =============================================================================

oc_snap_guard() {
  _os_tool="$1"; shift
  _os_root="${OC_SNAP_ROOT:-/tmp}"

  # Already running from a mirror? Then THIS file is the private copy — run it.
  # This is what makes nesting safe: a mirror's own oc-prchecks is invoked via
  # the mirror's $TOOLS_DIR and must run as-is, not raise a mirror of a mirror.
  case "$_os_tool" in
    "$_os_root"/oc-snap-*) return 0 ;;
  esac

  # Safety net only: with the check above, real nesting stays at depth 1.
  if [ "${OC_SNAP_DEPTH:-0}" -ge 3 ]; then
    printf 'oc-snap: recursion limit reached — running direct\n' >&2
    return 0
  fi

  _os_sd="${OC_TOOLS_DIR:-$(cd "$(dirname "$_os_tool")" && pwd)}" || return 0
  _os_sn="$(basename "$_os_tool")"
  # The tool's path RELATIVE to the tools root. Since v0.4.254 the fleet is
  # grouped into kind-based subdirs (tools/state/oc-ledger, tools/ship/oc-ship-chain),
  # so the BASENAME alone names a path that does not exist in the mirror: the
  # copy lands at $_os_mir/state/oc-ledger while a basename test looks for
  # $_os_mir/oc-ledger, misses, and returns 0 with NO diagnostic -- the guard
  # silently degrades to running direct, the exact exposure it exists to
  # prevent (#664). Resolve the absolute path and strip the tools root.
  _os_abs="$(cd "$(dirname "$_os_tool")" 2>/dev/null && pwd)/$(basename "$_os_tool")"
  _os_rel="${_os_abs#"$_os_sd"/}"
  _os_mir="$_os_root/oc-snap-${_os_sn}-$$"
  # (#117) THE PUBLISHED PATH IS NEVER PARTIAL. The mirror used to be built with
  # `mkdir -p` straight onto its LIVE path, so it was readable -- and
  # executable -- while tar was still filling it. Measured 2026-11-20 (HQ
  # receipt, chain CHAIN-3f75b276): a mirror was observed holding 3 of its 14
  # directories, still filling, while its name-pid was already gone; and
  # tools/ship/oc-ship-chain exec'd from a mirror that lacked state/oc-ledger,
  # dying rc=127 at line 1153 mid-run -- first lost journal line `pre-flight
  # ok`. Every guard below tests ONE path (the tool itself), so a mirror that
  # has the entry point but not its SIBLINGS passes every check and then breaks
  # the caller. Build in a private stage dir, mark it complete as the LAST
  # write, and rename(2) it into place: within one filesystem that is atomic, so
  # a reader now sees either no mirror or a whole one, never a half-filled tree.
  _os_stage="$_os_root/.oc-snap-stage-${_os_sn}-$$.${RANDOM:-0}"

  rm -rf "$_os_stage" 2>/dev/null
  mkdir -p "$_os_stage" 2>/dev/null || {
    printf 'oc-snap: cannot create %s — running direct (EXPOSED)\n' "$_os_stage" >&2
    return 0
  }

  # FULL COPY, deliberately not symlinks. oc-ship-chain and oc-deploy invoke
  # siblings through $TOOLS_DIR (oc-prchecks, oc-deploy, oc-ledger,
  # oc-issue-log, oc-order-validate, oc-artifact-verify, oc-seal-state,
  # oc-attrib). A symlinked sibling resolves to the MUTABLE original, which
  # re-opens the very hole this guard closes. A new inode for every entry is the
  # whole point.
  # Hard links would NOT work either: they share the inode, so an in-place
  # truncate would still reach the linked copy.
  #
  # (#115) EXCLUDE-AWARE, because the tree outgrew the blanket copy and the
  # blanket copy is on EVERY oc-* invocation's critical path. This comment used
  # to assert "tools/ is 824K / 46 files, so the copy is cheap" -- true when
  # written, and the reason nobody re-derived it. Measured 2026-11-20:
  #     tools/ on disk   16 MB        tools/ tracked   4.6 MB
  #     *.bak            65 files  9.5 MB   (edit_file pre-images, never exec'd)
  #     *.pyc            20 files  1.3 MB   (regenerated by the interpreter)
  #     __pycache__       6 dirs            (same)
  #     *.pre-*           1 file   0.3 MB   (edit pre-image)
  # So ~11 MB of the 16 MB had ZERO protective value: none of it is ever
  # executed, so excluding it removes no inode from the in-place-rewrite
  # protection above. What it did do was cost time: a COLD copy of the full tree
  # measured 10.01 s on an otherwise idle box (three runs: 10.01 / 0.17 / 0.45 s
  # -- the first pays the page cache). The fleet `--help` leg runs 48 tools under
  # a wall-clock bound, so that cost landed on innocent tools and reddened
  # whichever one hit the loaded moment (factory #115: oc-t5-sweep FAILED in the
  # fleet loop and PASSED in its own section of the SAME run). With the excludes
  # the copy is 4.7 MB and 0.078 s. tar is used rather than `cp -a` because tar
  # can exclude; -p preserves the mode/mtime that `cp -a` gave us.
  _os_excl=(--exclude='*.bak' --exclude='*.bak-*' --exclude='*.pre-*'
            --exclude='*.pyc' --exclude='*__pycache__*' --exclude='.reap.*')
  tar -C "$_os_sd" "${_os_excl[@]}" -cf - . 2>/dev/null | tar -C "$_os_stage" -xpf - 2>/dev/null
  # Both ends are checked: a pipeline reports only the LAST command's status, so
  # a failed read side would otherwise look like a clean copy of nothing.
  _os_pst=("${PIPESTATUS[@]}")
  if [ "${_os_pst[0]:-0}" -ne 0 ] || [ "${_os_pst[1]:-0}" -ne 0 ]; then
    rm -rf "$_os_stage"
    printf 'oc-snap: copy failed (tar rc=%s/%s) — running direct (EXPOSED)\n' \
      "${_os_pst[0]:-?}" "${_os_pst[1]:-?}" >&2
    return 0
  fi
  # The mirror ROOT's mtime is reset to NOW, because `cp -a` gives it the SOURCE
  # tree's mtime instead (#51). Copying `src/.` onto `dest/` applies the source
  # DIRECTORY's own attributes to the destination root, so every mirror was born
  # carrying tools/'s mtime — measured 2026-10-20: 42 mirrors, one single mtime
  # to the nanosecond (2026-09-28 09:13:41.661447704) shared by all of them,
  # predating their births by 21.9 days. The ONLY reader of that mtime is an AGE
  # instrument (vds-servers/tools/hygiene.py pass 1, `os.path.getmtime` against
  # a 14 h gate line), so each mirror was ~525 h stale the instant it existed and
  # any burst of oc-* invocations reddened the daily audit on a healthy box.
  # Root only: the inner files keep their source mtimes (nothing ages by them)
  # and -a's mode/ownership preservation, which the copy actually needs, is
  # untouched. The consumer is vendored and sha-pinned in registry/kit.json, so
  # the producer is the only place this can be fixed.
  # Validation runs on the STAGE, before anything is published: the entry point
  # must exist and be executable in the tree we are about to swap in.
  [ -f "$_os_stage/$_os_rel" ] || {
    rm -rf "$_os_stage"
    printf 'oc-snap: mirror lacks %s (looked for %s) -- running direct (EXPOSED)\n' \
      "$_os_rel" "$_os_stage/$_os_rel" >&2
    return 0
  }
  chmod +x "$_os_stage/$_os_rel" 2>/dev/null

  # COMPLETION MARKER, written as the LAST content write. Its absence is the one
  # thing a reader can test that separates "a finished copy" from "a copy still
  # being filled" -- the state that broke HQ's chain. The touch comes after it
  # because creating a file inside a directory bumps that directory's mtime, and
  # #51 needs the mirror ROOT's mtime to be NOW (see above).
  : > "$_os_stage/.oc-snap-complete" 2>/dev/null || {
    rm -rf "$_os_stage"
    printf 'oc-snap: cannot write completion marker in %s -- running direct (EXPOSED)\n' \
      "$_os_stage" >&2
    return 0
  }
  touch "$_os_stage" 2>/dev/null

  # PUBLISH ATOMICALLY. The target is our OWN pid-suffixed path, so nothing else
  # can be using it and clearing it cannot pull a tree out from under a live run.
  # rename(2) is atomic within one filesystem: the path appears whole or not at
  # all, which is what makes a partially-filled mirror unobservable.
  rm -rf "$_os_mir" 2>/dev/null
  mv -T "$_os_stage" "$_os_mir" 2>/dev/null || {
    rm -rf "$_os_stage"
    printf 'oc-snap: cannot publish %s -- running direct (EXPOSED)\n' "$_os_mir" >&2
    return 0
  }
  # Re-checked on the PUBLISHED path, so a mirror from an older oc-snap that
  # predates this marker is refused rather than exec'd into.
  [ -f "$_os_mir/.oc-snap-complete" ] || {
    rm -rf "$_os_mir"
    printf 'oc-snap: published mirror lacks its completion marker (%s) -- running direct (EXPOSED)\n' \
      "$_os_mir/.oc-snap-complete" >&2
    return 0
  }

  # Universal verification hook: OC_SNAP_VERBOSE=1 proves, for ANY tool, that
  # this run came off an immutable copy — without adding selftest code to each.
  #   OC_SNAP_VERBOSE=1 bash tools/harvest/oc-prchecks --selftest 2>&1 | grep 'oc-snap:'
  [ -n "${OC_SNAP_VERBOSE:-}" ] && \
    printf 'oc-snap: running from %s (pid %s, tool %s)\n' \
      "$_os_mir/$_os_rel" "$$" "$_os_sn" >&2

  OC_SNAP_ROOT="$_os_root" OC_SNAP_DEPTH=$(( ${OC_SNAP_DEPTH:-0} + 1 )) \
    exec bash "$_os_mir/$_os_rel" "$@"
}

# Reap mirrors whose owning process is gone. Trap-based cleanup cannot be used:
# the tools install their own EXIT trap (trap 'oc_log_finish $?' EXIT), which
# would overwrite ours. The health sweep calls this too; it is idempotent.
#
# A mirror is named oc-snap-<tool>-<pid>, where <pid> is the TOP-LEVEL guard
# process. That process forks children (e.g. oc-deploy poll,
# oc-carrier-features --fetch) which inherit the mirror path in their argv but
# carry their OWN pids -- so a dead name-pid does NOT prove the mirror is
# unused. Both conditions must hold before removal:
#   (1) the name pid is gone, AND
#   (2) no live process references the mirror path in its argv.
# Age is deliberately NOT a criterion: a chain legitimately holds its mirror for
# 30+ minutes, and an age-based sweep would pull it out from under a live run --
# the exact failure class this guard exists to prevent (fork #167).
# Prints the number of mirrors removed on stdout.
#   --dry-run : count what WOULD be removed, remove nothing.
oc_snap_reap() {
  _osr_dry=0
  case "${1:-}" in --dry-run) _osr_dry=1; shift ;; esac
  # #53: after the --dry-run shift, $1 IS the root. An unrecognised flag used to
  # be taken as that root, so `oc_snap_reap --dry-run -v` scanned a directory
  # named "-v", found nothing there and printed a confident 0 with rc 0 -- a
  # false "nothing to reap" that is indistinguishable from a clean box, which is
  # exactly the reading a lane auditing disk space takes at face value
  # (measured 2026-10-20, this box: 126 dead mirrors / 2.0 GB reported as 0).
  case "${1:-}" in
    -*) printf 'oc_snap_reap: unknown option %s\nusage: oc_snap_reap [--dry-run] [root]\n' "$1" >&2; return 2 ;;
  esac
  _osr_root="${1:-${OC_SNAP_ROOT:-/tmp}}"
  # The same false-zero class one step further out: a root that is not a
  # directory cannot hold a population, so it must not report one.
  if [ ! -d "$_osr_root" ]; then
    printf 'oc_snap_reap: root is not a directory: %s\n' "$_osr_root" >&2
    return 2
  fi
  _osr_n=0
  _osr_ps="$(mktemp 2>/dev/null)" || _osr_ps=""
  [ -n "$_osr_ps" ] || _osr_ps="/tmp/.oc-snap-reap-$$"
  ps -eo args > "$_osr_ps" 2>/dev/null || :
  for _osr_d in "$_osr_root"/oc-snap-*; do
    [ -d "$_osr_d" ] || continue
    _osr_pid="${_osr_d##*-}"
    # Only pid-suffixed dirs are mirrors; anything else (e.g. an apply backup)
    # is not this function's to remove.
    case "$_osr_pid" in
      ''|*[!0-9]*) continue ;;
    esac
    if kill -0 "$_osr_pid" 2>/dev/null; then continue; fi
    if grep -qF "$_osr_d" "$_osr_ps" 2>/dev/null; then continue; fi
    if [ "$_osr_dry" = "1" ]; then _osr_n=$((_osr_n + 1)); continue; fi
    if rm -rf "$_osr_d" 2>/dev/null; then _osr_n=$((_osr_n + 1)); fi
  done
  # (#117) STAGE DIRS are a second population with a DIFFERENT name shape, so the
  # oc-snap-* glob above cannot see them: they are dot-prefixed and their last
  # field is "<pid>.<rand>", which fails the numeric-pid test and `continue`s.
  # A run KILLed between mkdir and rename leaks one, and nothing else would ever
  # collect it. Same two conditions as a mirror: name-pid gone AND no live
  # process naming the path in its argv.
  for _osr_d in "$_osr_root"/.oc-snap-stage-*; do
    [ -d "$_osr_d" ] || continue
    _osr_tail="${_osr_d##*/.oc-snap-stage-}"
    _osr_pid="${_osr_tail%%.*}"
    case "$_osr_pid" in
      ''|*[!0-9]*) continue ;;
    esac
    if kill -0 "$_osr_pid" 2>/dev/null; then continue; fi
    if grep -qF "$_osr_d" "$_osr_ps" 2>/dev/null; then continue; fi
    if [ "$_osr_dry" = "1" ]; then _osr_n=$((_osr_n + 1)); continue; fi
    if rm -rf "$_osr_d" 2>/dev/null; then _osr_n=$((_osr_n + 1)); fi
  done
  rm -f "$_osr_ps" 2>/dev/null
  printf '%s' "$_osr_n"
}
