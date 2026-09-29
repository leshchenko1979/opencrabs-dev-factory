#!/usr/bin/env bash
# oc-root.sh — the ONE depth-agnostic resolution of the tools directory.
#
# WHY THIS EXISTS
#   tools/ is structured by KIND: the oc-* fleet executables at the top level,
#   with lib/ tests/ archive/ docs/ instruments/ as subdirs. A tool that derives
#   its own directory with `dirname "$0"` breaks the moment it is grouped into a
#   subdir — and so does every sibling reach built on it ($TOOLS_DIR/ship/oc-deploy,
#   $TOOLS_DIR/lib/oc-log.sh), which is why the grouping step is gated on this
#   resolver existing first.
#
# HOW IT RESOLVES
#   Walk UP from the invoking script to the first ancestor that holds
#   lib/oc-root.sh. The marker is this file itself, not a bare `lib/`, so an
#   unrelated project's lib/ can never be mistaken for ours.
#
#   The marker must be a REAL lib/ directory in the same tree — a SYMLINKED lib/
#   is rejected, because a borrowed lib/ means that ancestor is not our root.
#   This is not hypothetical: /tmp/lib was found to be a symlink to the real
#   tools/lib (2026-09-25, dated 09-19), so a marker test that followed symlinks
#   stopped the walk at /tmp for EVERY script under /tmp and resolved
#   OC_TOOLS_DIR=/tmp — which read as a broken tool (rc=127 on every sibling
#   reach) rather than a broken layout. `[ ! -L "$d/lib" ]` closes that class.
#
#   A symlink shim resolves to the same root either way: readlink -f sends the
#   walk to the real script's directory and the walk converges upward on the
#   common ancestor, while an unreadlink'd shim converges there too. So a shim
#   at tools/oc-x pointing into tools/state/oc-x yields tools/ in both cases.
#
# USAGE — the bootstrap is the same 4 lines in every tool, because the resolver
# cannot be found without first finding the tools dir:
#
#   _oc_r="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || _oc_r="."; _oc_d="$_oc_r"; while [ "$_oc_r" != "/" ] && [ "$_oc_r" != "." ] && ! { [ -f "$_oc_r/lib/oc-root.sh" ] && [ ! -L "$_oc_r/lib" ]; } && [ "$(basename "$_oc_r")" != "tools" ]; do _oc_r="$(dirname "$_oc_r")"; done
#   if [ "$(basename "$_oc_r")" = "tools" ]; then _oc_d="$_oc_r"; fi
#   if [ -f "$_oc_r/lib/oc-root.sh" ] && [ ! -L "$_oc_r/lib" ]; then . "$_oc_r/lib/oc-root.sh"; else OC_TOOLS_DIR="$(cd "$_oc_d" && pwd)"; fi
#   TOOLS_DIR="$OC_TOOLS_DIR"
#
# WHY THIS BLOCK WAS DOCUMENTED WRONG (F-L2, measured 2026-09-25). 40 of the 42
# files carrying a bootstrap ran the 4-line form above; this file described a
# 3-line form missing BOTH `basename` arms. A lane copying the documented form
# silently drops the arms, and nothing in the battery compares the two, so the
# divergence was invisible. The battery now asserts byte equality between this
# block and a real caller for exactly that reason -- on the three LOGIC lines,
# with the trailing `TOOLS_DIR=` assignment checked by pattern instead, because
# tools annotate that line with their own comments and comparing it byte-for-byte
# would redden on a comment rather than on the arm set this leg exists to protect.
#
# WHAT THE `basename != tools` ARM DOES. It stops the walk AT the nearest
# directory named `tools` even when that directory carries no marker, and then
# makes `_oc_d` that dir. Without it, a marker-less or stale tools/ keeps walking
# and can adopt an ANCESTOR's lib/oc-root.sh as its root — a root above the tree
# the tool actually lives in. The battery pins this with a fixture that plants a
# marker above a marker-less tools/: with the arm the helper refuses, without it
# the helper returns the ancestor.
#
# On return: OC_TOOLS_DIR is the absolute tools dir. Two cases, and the second
# is why the bootstrap is not a bare walk:
#
#   1. A tools root is found above the script — the normal case. OC_TOOLS_DIR is
#      that root, so a tool grouped into tools/<group>/ still resolves
#      tools/lib/ and its siblings.
#   2. NO tools root is found above it — a fixture copy, or a stray script. The
#      bootstrap then falls back to the DIRECTORY THE SCRIPT LIVES IN, which is
#      the historical `dirname "$0"` semantics. This case is load-bearing for
#      the battery: many selftests copy a tool into a temp dir beside FAKE
#      siblings and assert the tool uses THOSE, so a walk that escaped the
#      fixture to the real tools/ would silently defeat the test's isolation
#      (measured 2026-09-25: without this fallback, TOOLS_DIR walked past the
#      fixture and oc-ship-chain's journal legs read rc=127 against the real
#      tree). A fixture that copies a REAL lib/ beside the tool keeps case 1 —
#      that is oc-snap.sh's mirror, and it must still resolve to the mirror.
#
# A silently empty TOOLS_DIR is the failure this must never produce: it turns
# every sibling reach into a command not found, which reads as a broken tool
# rather than a broken layout.

# oc_tools_dir <script-path> — print the tools dir for an arbitrary script.
# Useful for resolving a SIBLING's root; the bootstrap above uses _oc_r instead.
#
# IT AGREES WITH THE BOOTSTRAP NOW, AND THAT IS THE POINT OF THIS LEG.
# Measured 2026-09-25: this helper tested only `[ -f "$_ocd/lib/oc-root.sh" ]`,
# omitting the `[ ! -L "$_ocd/lib" ]` guard the bootstrap in the SAME FILE calls
# load-bearing. A borrowed lib/ means that ancestor is not our root, and the
# symlink case is not hypothetical — /tmp/lib was found to be a symlink to the
# real tools/lib, so a marker test that follows symlinks stopped the walk at /tmp
# for every script under it and resolved OC_TOOLS_DIR=/tmp (rc=127 on every
# sibling reach, which reads as a broken tool rather than a broken layout).
#
# At the time of the fix this helper had ZERO callers outside this file (grep over
# tools/ returns the definition only), so the guard is written for its NEXT caller,
# not to repair live behaviour — and that is precisely when such a disagreement is
# cheapest to close. A helper and a bootstrap that resolve the same question by
# different rules will eventually be used side by side, and the divergence will be
# found by whoever is debugging a sibling reach at 3am.
oc_tools_dir() {
  _ocd="${1:-$0}"
  _ocd="$(readlink -f "$_ocd" 2>/dev/null || printf '%s' "$_ocd")"
  _ocd="$(dirname "$_ocd")"
  while [ -n "$_ocd" ] && [ "$_ocd" != "/" ]; do
    if [ -f "$_ocd/lib/oc-root.sh" ] && [ ! -L "$_ocd/lib" ]; then
      printf '%s\n' "$_ocd"; return 0
    fi
    if [ "$(basename "$_ocd")" = "tools" ]; then return 1; fi
    _ocp="$_ocd"
    _ocd="$(dirname "$_ocd")"
    # H-2: dirname(".") is "." and dirname("x") is ".", so a BARE relative name
    # (no slash -- readlink -f failed on it) parks here and spins forever with no
    # timeout. Break the moment the walk stops making progress.
    [ "$_ocd" = "$_ocp" ] && break
  done
  return 1
}

OC_TOOLS_DIR="$(cd "${_oc_r:-$(dirname "$0")}" 2>/dev/null && pwd)" || {
  printf 'oc-root: cannot resolve the tools dir (searched up from %s)\n' "${_oc_r:-$0}" >&2
  exit 1
}
