#!/usr/bin/env bash
# lib/oc-sessions.sh — the SESSION STORE as a fact source for trailer consumers
# (factory #192).
#
# WHY THIS EXISTS. A commit's `Session-Id` trailer names a session uuid, and the
# post-swap fan-out notifies that uuid. Nothing in the fleet ever asked the store
# WHAT that uuid is, so two silent outcomes shipped:
#   - the uuid is a sub-agent session (`sessions.title LIKE 'subagent:%'`) — a
#     real row, so every gate passes, but a session no human-facing lane reads.
#     The notify is accepted, journalled `notified`, and read by nobody.
#   - the uuid is in no store at all (a coding agent that invented one) — the
#     transport answers rc 2 `no_route` and the fan-out journals `skip`.
# Measured on fork main at #192: 25% of the last 60 commits named a sub-agent
# session and 1.7% named a session that exists nowhere, i.e. 45% of trailers
# were unusable for attribution while the fan-out reported success.
#
# TWO CONSUMERS, ONE ANSWER. `oc-commit` asks before it stamps (refuse a child
# whose lane is knowable); `oc-fanout` asks before it notifies (walk child ->
# lane). They must not grow private copies of the query — that is how the
# roster/trailer readers forked before (#738, #754).
#
# THE THREE-WAY ANSWER IS THE POINT. `unknown` (no row) and "the store could not
# be read" are DIFFERENT facts and must never collapse: the first is a statement
# about the uuid, the second about THIS BOX. A consumer that read an unreadable
# store as "no such session" would report a live lane as a phantom (the #932
# class, one layer down). So every function that can fail to read returns rc 3
# with a diagnostic naming the store, and no stdout.
#
# READ-ONLY BY CONSTRUCTION: every query goes through `tools/lib/oc_sqlite` on a
# `file:...?mode=ro` URI — in place, never copied, never written (AGENTS.md
# §Reading daemon state). This lib has no writer; the backfill of pre-ship rows
# is a separate tool with its own explicit `--apply`.
#
# COST: `oc_sessions_kind` is one indexed primary-key lookup. A caller with MANY
# uuids (the fan-out walks every contributing session of a ship) calls
# `oc_sessions_load` ONCE — a single full-table read into two associative arrays
# — and every later `oc_sessions_kind` is answered from memory. 1.9k rows on the
# live box; the load is ~30 ms and buys the whole run.
#
# REQUIRES bash 4+ (associative arrays) and nothing else. Safe under `set -u`
# (every parameter is defaulted) and under `set -o pipefail` (no pipelines).
# =============================================================================

# OC_SESSIONS_LIB_VER: bumped when the ANSWER SHAPE changes, so a consumer can
# refuse a lib it does not understand instead of mis-reading it.
OC_SESSIONS_LIB_VER=1

# oc_sessions_db — the store path. Precedence: OC_SESSIONS_DB (fixtures, tests,
# a second profile) > the profile default. Same shape oc-health/oc-roster use,
# so one env var moves every consumer at once.
oc_sessions_db() {
  if [ -n "${OC_SESSIONS_DB:-}" ]; then
    printf '%s\n' "$OC_SESSIONS_DB"
    return 0
  fi
  printf '%s\n' "$HOME/.opencrabs/profiles/${OC_PROFILE:-ops}/opencrabs.db"
}

# _oc_sessions_sqlite — the sanctioned reader, resolved from THIS file's own
# directory so a sourced copy (selftest fixtures, an immutable mirror) reads its
# sibling and never a path baked in at authoring time.
_oc_sessions_sqlite() {
  # OC_SESSIONS_SQLITE is the same kind of seam OC_DEPLOY_GH and OC_NOTIFY_DB
  # already are: a way for a SELFTEST to drive this library against an instrument
  # it controls. It exists because the defect this library must survive — a store
  # whose POINT lookups return zero rows with rc 0 while the FULL read fails — is
  # a property of a particular corrupt page geometry, and a hand-corrupted sqlite
  # file does not reproduce it reliably (measured 2026-11-27: three corruption
  # shapes were tried and every one failed the cheap query too, i.e. none of them
  # reproduced the ambiguous state). A stub encodes the shape exactly. Production
  # never sets it, and the sibling resolution below stays the default.
  if [ -n "${OC_SESSIONS_SQLITE:-}" ]; then
    printf '%s\n' "$OC_SESSIONS_SQLITE"
    return 0
  fi
  local here="${BASH_SOURCE[0]%/*}"
  case "$here" in
    "${BASH_SOURCE[0]}") here="." ;;   # sourced with no slash: CWD is the lib dir
  esac
  printf '%s\n' "$here/oc_sqlite"
}

# oc_sessions_available — rc 0 when the store file exists and is readable.
# Deliberately a FILE test, not a query: a caller uses this to decide whether to
# ask at all, and a query that answers "empty" cannot be told from "no table".
oc_sessions_available() {
  local db
  db="$(oc_sessions_db)"
  [ -n "$db" ] && [ -f "$db" ] && [ -r "$db" ]
}

# _oc_sessions_uuid_ok <uuid> — rc 0 for the BARE 36-char uuid shape.
# LOAD-BEARING: the uuid is interpolated into SQL below, and a trailer is
# caller-controlled text. A charset test (no pipe, so no #537 SIGPIPE race)
# plus the positional shape oc-commit already enforces (#754) makes injection
# unreachable rather than "escaped".
_oc_sessions_uuid_ok() {
  case "${1:-}" in
    ''|*[!0-9a-fA-F-]*) return 1 ;;
    ????????-????-????-????-????????????) return 0 ;;
    *) return 1 ;;
  esac
}

# oc_sessions_load — ONE full read of the store into memory.
# Sets OC_SESSION_KIND_CACHE[id] = lane|child and OC_SESSION_PARENT_CACHE[id] =
# parent uuid ('' when NULL), then OC_SESSIONS_LOADED=1.
# rc 0 loaded · rc 3 the store could not be read (diagnostic names it).
oc_sessions_load() {
  local db out id kind parent
  db="$(oc_sessions_db)"
  if ! oc_sessions_available; then
    printf 'oc_sessions: session store not readable: %s\n' "$db" >&2
    return 3
  fi
  declare -gA OC_SESSION_KIND_CACHE=()
  declare -gA OC_SESSION_PARENT_CACHE=()
  # A NULL title is not a subagent: `NULL LIKE 'subagent:%'` is NULL, which the
  # CASE sends to the ELSE arm — a lane. That is the honest reading (the title
  # was never set, so nothing claims it is a child).
  out="$("$(_oc_sessions_sqlite)" "file:$db?mode=ro" \
    "SELECT id, CASE WHEN title LIKE 'subagent:%' THEN 'child' ELSE 'lane' END, COALESCE(parent_session_id,'') FROM sessions")" \
    || { printf 'oc_sessions: cannot read sessions from %s\n' "$db" >&2; return 3; }
  while IFS='|' read -r id kind parent; do
    [ -n "$id" ] || continue
    OC_SESSION_KIND_CACHE["$id"]="$kind"
    OC_SESSION_PARENT_CACHE["$id"]="$parent"
  done <<< "$out"
  OC_SESSIONS_LOADED=1
  return 0
}

# oc_sessions_kind <uuid> — WHAT IS THIS UUID?
#   stdout: `lane`            a human-facing session
#           `child <parent>`  a sub-agent session, lane uuid known
#           `child -`         a sub-agent session with NO parent recorded
#                             (pre-ship rows: the column was added without a
#                             backfill, so a child can be unattributable)
#           `unknown`         no such row in this store
#   rc 0 answered (all four shapes above) · rc 2 usage · rc 3 store unreadable
# rc 3 is the one that must never be folded into `unknown`: it is a fact about
# the BOX, and a consumer that notified anyway would be guessing.
oc_sessions_kind() {
  local uuid="${1:-}" db out kind parent
  _oc_sessions_uuid_ok "$uuid" || {
    printf 'oc_sessions_kind: not a session uuid: %s\n' "${uuid:-<empty>}" >&2
    return 2
  }
  if [ "${OC_SESSIONS_LOADED:-0}" = 1 ]; then
    case "${OC_SESSION_KIND_CACHE[$uuid]:-}" in
      child)
        parent="${OC_SESSION_PARENT_CACHE[$uuid]:-}"
        printf 'child %s\n' "${parent:--}"
        return 0 ;;
      lane)
        printf 'lane\n'
        return 0 ;;
      *)
        printf 'unknown\n'
        return 0 ;;
    esac
  fi
  db="$(oc_sessions_db)"
  if ! oc_sessions_available; then
    printf 'oc_sessions: session store not readable: %s\n' "$db" >&2
    return 3
  fi
  out="$("$(_oc_sessions_sqlite)" "file:$db?mode=ro" \
    "SELECT CASE WHEN title LIKE 'subagent:%' THEN 'child' ELSE 'lane' END, COALESCE(parent_session_id,'') FROM sessions WHERE id='$uuid'")" \
    || { printf 'oc_sessions: cannot read sessions from %s\n' "$db" >&2; return 3; }
  # AN EMPTY POINT LOOKUP IS AMBIGUOUS, and this is where the ambiguity is
  # resolved — once, for every caller. A healthy store returns zero rows only
  # when the uuid is genuinely absent. A DAMAGED store returns zero rows too, on
  # any page it can still read: measured 2026-11-27 on this box, the ops DB
  # answers `count(*)` = 1917 and a point lookup for a REAL uuid with empty
  # output, while the full table read fails `database disk image is malformed`
  # (btreeInitPage error 11). Reporting that as `unknown` blames the ACTOR for a
  # BOX fault (#932), and it is indistinguishable from a genuine phantom at every
  # layer above. So the absent answer is only reported absent after a FULL read —
  # the one that touches every page — confirms the store is intact. The common
  # path (a row exists) never pays this: it returns above.
  if [ -z "$out" ]; then
    oc_sessions_load || return 3
    # The full read just populated the cache, and THAT is the authoritative
    # answer — the point query that returned nothing may have skipped a page the
    # full read reached. Re-ask from the cache rather than assuming absence.
    case "${OC_SESSION_KIND_CACHE[$uuid]:-}" in
      child) printf 'child %s\n' "${OC_SESSION_PARENT_CACHE[$uuid]:--}" ;;
      lane)  printf 'lane\n' ;;
      *)     printf 'unknown\n' ;;
    esac
    return 0
  fi
  kind="${out%%|*}"
  parent="${out#*|}"
  if [ "$kind" = child ]; then
    printf 'child %s\n' "${parent:--}"
  else
    printf 'lane\n'
  fi
}

# oc_sessions_lane <uuid> — walk child -> lane.
#   stdout: the uuid of the human-facing session this work belongs to (the input
#           itself when it is already a lane)
#   rc 0 resolved · 1 the uuid is in NO store row (a phantom) · 2 usage
#   rc 3 the store could not be read · 4 a child whose chain does not reach a
#   lane (no parent recorded, a parent that is not in the store, or a cycle)
# On any non-zero rc, OC_SESSIONS_LANE_WHY names the reason in the journal's
# vocabulary: `not-in-store` / `no-parent` / `broken-chain` / `cycle`.
# The depth cap is not paranoia: a self-parented row (or a two-row loop) would
# otherwise spin forever inside a fan-out that holds a flock.
oc_sessions_lane() {
  local uuid="${1:-}" cur kind_out rc parent depth=0 max="${OC_SESSIONS_MAX_DEPTH:-5}"
  OC_SESSIONS_LANE_WHY=""
  _oc_sessions_uuid_ok "$uuid" || {
    printf 'oc_sessions_lane: not a session uuid: %s\n' "${uuid:-<empty>}" >&2
    OC_SESSIONS_LANE_WHY="not-a-uuid"
    return 2
  }
  cur="$uuid"
  while : ; do
    kind_out="$(oc_sessions_kind "$cur")"; rc=$?
    [ "$rc" = 0 ] || { OC_SESSIONS_LANE_WHY="store-unreadable"; return 3; }
    case "$kind_out" in
      lane)
        printf '%s\n' "$cur"
        return 0 ;;
      'child -')
        # A child with no parent recorded. This is the pre-ship row shape, and
        # it is NOT the child's fault: report it distinctly so the caller can
        # say "unattributable" instead of "not a session".
        [ "$depth" = 0 ] && OC_SESSIONS_LANE_WHY="no-parent" || OC_SESSIONS_LANE_WHY="broken-chain"
        return 4 ;;
      'child '*)
        parent="${kind_out#child }"
        if [ "$parent" = "$cur" ]; then OC_SESSIONS_LANE_WHY="cycle"; return 4; fi
        cur="$parent" ;;
      *)
        [ "$depth" = 0 ] && OC_SESSIONS_LANE_WHY="not-in-store" || OC_SESSIONS_LANE_WHY="broken-chain"
        return 1 ;;
    esac
    depth=$((depth+1))
    if [ "$depth" -ge "$max" ]; then OC_SESSIONS_LANE_WHY="cycle"; return 4; fi
  done
}
