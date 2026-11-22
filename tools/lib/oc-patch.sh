# =============================================================================
# lib/oc-patch.sh — content identity for a rebased commit (Duty-4 n=2520)
# =============================================================================
# WHY THIS EXISTS
#   A lane's branch goes non-FF when fork main advances (the merge race). The
#   lane rebases, the content is byte-identical, but the COMMIT SHA CHANGES. The
#   CI gate is pinned to a sha, so a GREEN gate is voided by construction and
#   the lane pays a second full gate (~30 min) over bytes that never moved.
#   Measured 2026-09-25: ONE patch, THREE shas, THREE full gates —
#     47e615d9e -> run 36141969856, 9377c6a06 -> run 36144454832,
#     7f83ba97d -> run 36149339727
#   and all three carry the SAME patch-id b34db1c21bcd6fe1b537be2423324fd8822bceb7.
#   So "same patch, different sha" is a decidable question, and this is the
#   predicate that decides it.
#
# WHY patch-id AND NOT `cmp`
#   `git patch-id --stable` hashes a commit's own patch with line numbers and
#   whitespace normalised, so it is invariant to where the commit lands and to
#   the surrounding context a rebase rewrites. It is ALSO already the fleet's
#   content predicate: oc-rebase-safety compares per-file patch-ids
#   (tools/git/oc-rebase-safety, the SAME/CHANGED arms) to decide whether a
#   rebase lost a hunk. This lib gives that same predicate ONE home rather than
#   a second copy — the oc-claims-single-source rule.
#
# FAIL CLOSED
#   An uncomputable patch-id (root commit, merge commit, sha absent from the
#   local object store) is NEVER a match. A predicate that cannot observe its
#   own subject must not return "same" — that would carry a gate forward over
#   content nobody verified, which is the exact silent-clean class this fleet
#   keeps closing.
# =============================================================================

# oc_job_sha <job-name> -> first 40-hex commit sha embedded in the name, else empty.
# Covers both fleet job-name shapes: "PR-lane gates (<sha>)" and
# "ship / Linux amd64 (<sha>, <features>)".
oc_job_sha() {
  # `|| true` is the CONTRACT, not a patch: the docstring says "else empty", and
  # under a caller's `set -o pipefail` a no-match grep (or head's SIGPIPE, rc 141)
  # would otherwise return non-zero and `set -e` would abort the CALLER. Measured
  # 2026-11-20: oc-ship's LEG1 carry-forward died rc=1 with no message on a
  # content-identical rebase, purely because gh listed a sha-less job FIRST.
  printf '%s\n' "${1:-}" | grep -oE '[0-9a-f]{40}' | head -1 || true
}

# oc_patch_id <repo> <sha> -> patch-id of that commit's OWN patch, else empty.
oc_patch_id() {
  # Same contract, same hazard: "else empty" must mean rc 0 with empty output, or
  # oc_same_patch's `pa="$(oc_patch_id ...)"` aborts under set -e before its own
  # `[ -n "$pa" ] || return 1` can refuse. Refusing "unknown as same" is the whole
  # point of oc_same_patch, and it cannot refuse what it never reached.
  git -C "${1:?repo}" show --no-color --pretty=format: "${2:?sha}" 2>/dev/null \
    | git patch-id --stable 2>/dev/null | cut -d' ' -f1 || true
}

# oc_same_patch <repo> <sha-a> <sha-b> -> rc 0 when BOTH resolve locally and
# their patch-ids are equal and non-empty (content-identical rebase).
# Any other outcome — unresolvable sha, uncomputable patch-id, differing
# patches — returns non-zero. Never treat "unknown" as "same".
oc_same_patch() {
  local pa pb
  [ -n "${2:-}" ] && [ -n "${3:-}" ] || return 1
  pa="$(oc_patch_id "$1" "$2")"
  [ -n "$pa" ] || return 1
  pb="$(oc_patch_id "$1" "$3")"
  [ -n "$pb" ] || return 1
  [ "$pa" = "$pb" ]
}
