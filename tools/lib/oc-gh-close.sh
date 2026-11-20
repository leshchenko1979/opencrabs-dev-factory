#!/usr/bin/env bash
# tools/lib/oc-gh-close.sh — ONE implementation of "close an issue on a behavioural
# receipt" (triage.md §Autonomous closure, class (d) behavioural-smoke-landed).
#
# SOURCED, never executed. Provides oc_close_on_receipt().
#
# WHY THIS IS A LIB (T-10, 2026-11-20): class (d) closure now has TWO callers —
# `oc-smoke --close` (the live verdict path) and `oc-closure-sweep --apply` (the
# catch-up path for a PASS that landed before the close did). The sweep's whole
# acceptance is "closes through the same path `oc-smoke --close` uses", and two
# copies of a gh-close block is exactly how that drifts: the copy nobody is
# reading stops matching the one that is. One function, two callers, one guard set.
#
# CONTRACT
#   oc_close_on_receipt <prog> <gh> <repo> <issue> <receipt-1> <receipt-2>
#     prog       program name used in the stderr messages
#     gh         gh binary (selftests pass a stub, so never hardcode `gh`)
#     repo       owner/repo
#     issue      NUMERIC issue number; a slug is refused (rc 4) — gh cannot close
#                a slug and resolving one would be a guess about which tracker
#     receipt-1  first receipt line, pre-formatted by the caller
#     receipt-2  second receipt line, pre-formatted by the caller
#
#   rc 0  closed by THIS call
#      1  already CLOSED — idempotent no-op, nothing written (guard 4)
#      2  tracker state unreadable — nothing attempted (guard 7)
#      3  close attempted and FAILED — nothing closed (guard 7)
#      4  issue is not numeric — nothing attempted
#
# The function NEVER exits and NEVER toggles the caller's shell options: the
# caller owns rc policy (guard 7 — a gh failure must not change a verdict that is
# already on disk). Every failure path writes NOTHING to the tracker.
#
# The comment is built with printf, never a heredoc: receipt text carries PROBE
# OUTPUT, and an unquoted heredoc would expand `$(...)`/backticks out of a probe
# that merely printed them. printf takes its arguments literally.
#
# Guard 7 is about the CALLER's exit code, but the messages still name it, because
# a caller that lets a failed close change its rc is the defect this records.

oc_close_on_receipt() {
  local prog="${1:-oc-close}" gh="${2:-gh}" repo="$3" issue="$4" r1="$5" r2="$6"
  local state vrc comment out crc

  case "$issue" in
    ''|*[!0-9]*)
      printf "%s: NOTE --close skipped: '%s' is not a numeric ref, so there is no issue to close\n" \
        "$prog" "$issue" >&2
      return 4
      ;;
  esac

  # `|| { ... }` rather than set +e/set -e: a command in an OR-list is exempt from
  # `set -e` in the caller, so the caller's shell options are never touched.
  state="$("$gh" issue view "$issue" -R "$repo" --json state --jq .state 2>&1)" || {
    vrc=$?
    printf '%s: WARNING: --close skipped — cannot read state of %s#%s (gh rc=%s): %s\n' \
      "$prog" "$repo" "$issue" "$vrc" "$(printf '%s' "$state" | tr '\n' ' ')" >&2
    printf '%s:          the verdict row stands and the exit code is unchanged (guard 7);\n' "$prog" >&2
    printf '%s:          close %s#%s by hand once the tracker is reachable\n' "$prog" "$repo" "$issue" >&2
    return 2
  }
  state="$(printf '%s' "$state" | tr -d '[:space:]')"

  if [ "$state" = "CLOSED" ]; then
    # Idempotent (guard 4): a second close is noise on the tracker and a second
    # receipt on the record, so say it and stop.
    printf '%s: NOTE %s#%s is already CLOSED — no second close\n' "$prog" "$repo" "$issue" >&2
    return 1
  fi

  comment="$(printf '%s\n\n- %s\n- %s\n' \
    "Closed on behavioural receipt (class (d) behavioural-smoke-landed)." \
    "$r1" "$r2")"

  out="$("$gh" issue close "$issue" -R "$repo" --comment "$comment" 2>&1)" || {
    crc=$?
    printf '%s: WARNING: close of %s#%s failed (gh rc=%s): %s\n' \
      "$prog" "$repo" "$issue" "$crc" "$(printf '%s' "$out" | tr '\n' ' ')" >&2
    printf '%s:          the verdict row stands and the exit code is unchanged (guard 7)\n' "$prog" >&2
    return 3
  }

  printf '%s: closed %s#%s on the behavioural receipt (class (d) behavioural-smoke-landed)\n' \
    "$prog" "$repo" "$issue"
  return 0
}
