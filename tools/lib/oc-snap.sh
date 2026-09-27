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

  mkdir -p "$_os_mir" 2>/dev/null || {
    printf 'oc-snap: cannot create %s — running direct (EXPOSED)\n' "$_os_mir" >&2
    return 0
  }

  # FULL COPY, deliberately not symlinks. oc-ship-chain and oc-deploy invoke
  # siblings through $TOOLS_DIR (oc-prchecks, oc-deploy, oc-ledger,
  # oc-issue-log, oc-order-validate, oc-artifact-verify, oc-seal-state,
  # oc-attrib). A symlinked sibling resolves to the MUTABLE original, which
  # re-opens the very hole this guard closes. tools/ is 824K / 46 files, so the
  # copy is cheap; a new inode for every entry is the whole point.
  # Hard links would NOT work either: they share the inode, so an in-place
  # truncate would still reach the linked copy.
  cp -a "$_os_sd/." "$_os_mir/" 2>/dev/null || {
    rm -rf "$_os_mir"
    printf 'oc-snap: copy failed — running direct (EXPOSED)\n' >&2
    return 0
  }

  [ -f "$_os_mir/$_os_rel" ] || {
    rm -rf "$_os_mir"
    printf 'oc-snap: mirror lacks %s (looked for %s) -- running direct (EXPOSED)\n' \
      "$_os_rel" "$_os_mir/$_os_rel" >&2
    return 0
  }
  chmod +x "$_os_mir/$_os_rel" 2>/dev/null

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
  _osr_root="${1:-${OC_SNAP_ROOT:-/tmp}}"
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
  rm -f "$_osr_ps" 2>/dev/null
  printf '%s' "$_osr_n"
}
