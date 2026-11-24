#!/usr/bin/env bash
# =============================================================================
# oc-deploy-lib.sh — the SHARED body of the four deploy stage tools.
#
# Each of these four tools owns ONE stage of the deploy pipeline and sources
# this lib directly; there is no dispatcher in front of them (#168 cut 5):
#
#   oc-build    ship + features      dispatch a carrier build (build/land leg)
#   oc-swap     swap-execute         install a verified artifact on the host
#   oc-fanout   fanout               post-CI mechanical notifications (#24)
#   oc-status   status + poll + watch   read-only state + the handoff leg
#
# WHAT LIVES HERE, AND WHY: the four tools share a config surface (state dir,
# ledger, markers, kill files, swap targets) and a set of helpers used by more
# than one stage — the ledger stamp, the journal, the A2A receipt, the carrier
# feature reader, the fork-release identity, the stage reader, the #704 tip
# read. Splitting those into four copies would let them DRIFT, which is the
# defect class this whole tool has spent its life closing (one reader, one
# value). So there is ONE copy, here, and every tool sources it.
#
# VERBATIM RULE (owner order, plan task T5-bis): every function below is a
# BYTE-SLICE of tools/ship/oc-deploy as it stood at 5f81c599. No body was
# rewritten, no signature changed, no rc was re-mapped. The only edits are
# structural: (a) three top-level BLOCKS that were not functions in the source
# (the argv loop, the priority probe, the features resolution) are wrapped in a
# function so that four tools can share them instead of each keeping a copy;
# (b) selftest() gained ONE line, oc_deploy_load_funcs, because the suite it
# sources now exercises four tools instead of one. Both are marked NEW below.
#
# RC CONTRACT: tools/docs/RC-CONTRACT.md. The rc values raised here are the
# ones the register documents; nothing was renumbered by the split.
#
# SOURCING CONTRACT: source this AFTER lib/oc-log.sh has been initialised
# (oc_log_init "<tool>" "$@") and before the trap on EXIT. It runs at source
# time only the two conditional library probes at the bottom — those ARE the
# #932 guard and must run once per process.
# =============================================================================

# ----------------------------------------------------------------------------
# config surface (moved verbatim from tools/ship/oc-deploy:153-221)
# ----------------------------------------------------------------------------
# v0.4.60 (owner order 2026-08-31 06:03Z "move all accounting files and markers
# out of the skill dir"): deploy artifacts (deployed.sha/meta, fanout.state,
# oc-deploy/journal, shadow log) default to the STATE dir — the skill repo
# holds code only. Migration shipped same bump; OC_DEPLOY_STATE_DIR override
# unchanged (selftest fixtures + test isolation rely on it).
STATE_DIR="${OC_DEPLOY_STATE_DIR:-${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}}"
# Ledger resolution (v0.4.38, owner-approved 2026-08-29 "Go"): live runs MUST
# hit the CANONICAL ledger. The old $STATE_DIR default kept a second ledger in
# the skill dir — live swap stamps + fanout reads used it while HQ
# stamps went to the canonical file: two-file drift, baseline/orders backup
# paths pointing at an empty dir, cycle counter reset 25->1 (incident
# 2026-08-29). OC_LEDGER overrides everything; an explicit OC_DEPLOY_STATE_DIR
# keeps selftest/battery fixtures isolated on their own ledger file.
CANONICAL_LEDGER="${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}/workers-ledger.json"
if [ -n "${OC_LEDGER:-}" ]; then
  LEDGER="$OC_LEDGER"
elif [ -n "${OC_DEPLOY_STATE_DIR:-}" ]; then
  LEDGER="$OC_DEPLOY_STATE_DIR/workers-ledger.json"
else
  LEDGER="$CANONICAL_LEDGER"
fi
[ -f "$LEDGER" ] && LEDGER="$(readlink -f "$LEDGER")"  # canonical path: never write through a symlink (mv replaces links -> split-brain; drill incident 2026-08-28)
KILL_FILE="$STATE_DIR/oc-deploy.kill"
KILL_FILE2="${OC_DEPLOY_KILL_FILE:-${HOME:-/root}/oc-work/oc-deploy.disabled}"
SHADOW="$STATE_DIR/oc-deploy-shadow.log"
DEPLOYED="$STATE_DIR/deployed.sha"
DEPLOYED_META="$STATE_DIR/deployed.meta.json"
JOURNAL_DIR="$STATE_DIR/oc-deploy/journal"
TOOLS_DIR="$OC_TOOLS_DIR"   # script-relative (Duty-6 P0 fix 2026-08-31: $STATE_DIR/tools/ never existed post-split — latent ship breaker, lenses B+E)
LEDGER_TOOL="$TOOLS_DIR/state/oc-ledger"   # (156) the ONE ledger writer: stamp delegations go through it, never around it
VALIDATE="${OC_DEPLOY_VALIDATE:-$TOOLS_DIR/ship/oc-verify-order}"
# CONSENT tool var retired 2026-08-28 (consent process eliminated by owner order)
ARTVERIFY="${OC_DEPLOY_ARTVERIFY:-$TOOLS_DIR/ship/oc-verify-artifact}"
SEAL="${OC_DEPLOY_SEAL:-$TOOLS_DIR/ship/oc-seal}"
ATTRIB="${OC_DEPLOY_ATTRIB:-$TOOLS_DIR/state/oc-attrib}"   # issue #24 D1: contributors/fanout backend
REMOTE="${OC_DEPLOY_REMOTE:-https://github.com/leshchenko1979/opencrabs.git}"
FORK="${OC_DEPLOY_FORK:-leshchenko1979/opencrabs}"
CARRIER_REF="ci/quick-build-linux"
WF="quick-build-linux.yml"
GH="${OC_DEPLOY_GH:-gh}"
SELF="$(readlink -f "$0" 2>/dev/null || echo "$0")"

# Phase B swap-target overrides (sandbox/selftest point these elsewhere)
SWAP_TARGET="${OC_SWAP_TARGET:-/usr/local/bin/opencrabs}"
BACKUP_DIR="${OC_SWAP_BACKUP_DIR:-${HOME:-/root}/opencrabs-binary-backups}"
# Retention for BACKUP_DIR (#497, HQ toolshed item 2). The swap path took a
# backup on EVERY swap target and never removed one, so the directory reached 38
# files / 3.3 GB, was purged by hand to 3 / 261 MB, and regrew to 6 / 522 MB
# within ~5 h — ~260 MB per swap cycle on a 58 GB root with ~11 GB free.
# Keyed on the FILENAME STAMP, never on mtime: the backup is taken with `cp -p`,
# which preserves the SOURCE's timestamps, so a backup's mtime is the mtime of
# the binary it copied (several share one mtime — a 4-way tie was measured) and
# an mtime-ordered "newest N" is ambiguous. The name is
# `opencrabs-YYYYMMDD-HHMMSS-pre-<short>` — fixed width, so it sorts
# lexicographically into true creation order.
BAK_KEEP="${OC_SWAP_BACKUP_KEEP:-5}"
RESTART_CMD="${OC_SWAP_RESTART_CMD:-systemctl --user restart opencrabs-ops.service}"
ACTIVE_CMD="${OC_SWAP_ACTIVE_CMD:-systemctl --user is-active opencrabs-ops.service}"
PID_CMD="${OC_SWAP_PID_CMD:-systemctl --user show -p MainPID --value opencrabs-ops.service}"
SKIP_PROC="${OC_SWAP_SKIP_PROC:-0}"
A2A_URL="${OC_A2A_URL-http://127.0.0.1:18791/a2a/v1}"
# #124: the receipt leg's addressee. The PHASE B receipt announces a landed swap
# to the OC DEV HQ topic, so its target is the session BOUND to that topic —
# resolved at send time (a uuid is not durable across session replacement).
RECEIPT_TOPIC="${OC_DEPLOY_RECEIPT_TOPIC:-30220}"
A2A_CURL="${OC_A2A_CURL:-curl}"   # test seam: stub the transport
LAUNCH="${OC_SWAP_LAUNCH:-systemd-run --user}"

# Cut 4 (factory #168): every message below names the tool that ACTUALLY ran,
# never the retired `oc-deploy` dispatcher. The name is captured ONCE, at source
# time, from $0 — which is the stage tool that sourced this file (oc-build,
# oc-swap, oc-status, oc-fanout, oc-seal). A peer loaded by oc_deploy_load_funcs
# returns above its own prologue and never re-sources the lib, so the first
# capture wins and the prefix cannot drift mid-process. Before this, a consumer
# agent running `oc-build ship` was told `oc-deploy: ...` about a tool that no
# longer exists — the confusion the cut exists to remove.
OC_DEPLOY_PROG="${OC_DEPLOY_PROG:-$(basename "${0:-oc-deploy}")}"

die() { echo "$OC_DEPLOY_PROG: $2" >&2; exit "$1"; }
plan() { echo "PLAN: $*"; }

# ----------------------------------------------------------------------------
# lineage verdict (moved verbatim: 223-268)
# ----------------------------------------------------------------------------
# ------------------------------------------------- lineage verdict (v0.4.151) --
# Rebase-aware swap-guard decision. A fork-main rebase REWRITES shas: the
# currently deployed sha is left orphaned (it is no longer an ancestor of the
# incoming build) even though its CHANGE is fully present under a new sha. The
# pre-v0.4.151 guard tested ancestry only, so after every rewrite it refused
# EVERY legitimate forward swap — fleet-blocking (reported 2026-09-12).
#
#   monotonic  PREV is an ancestor of SHA                    -> accept
#   rewritten  PREV is orphaned, but a commit in BASE..SHA carries the SAME
#              patch-id (identical change, new sha)           -> accept (twin sha printed)
#   absent     both objects exist and PREV's change is genuinely NOT in SHA's
#              lineage (a real stale/delayed build)           -> refuse
#   unknown    one of the objects is not in this repo — cannot judge -> skip
#              (preserves the pre-v0.4.151 "if both exist" behaviour)
#
# Prints "<verdict> <twin-sha-or-empty>" on stdout. Always rc 0.
lineage_verdict() { # <repo> <prev_sha> <sha>
  local repo="$1" prev="$2" sha="$3" base pid twin
  git -C "$repo" cat-file -e "$prev^{commit}" 2>/dev/null || { echo "unknown "; return 0; }
  git -C "$repo" cat-file -e "$sha^{commit}"  2>/dev/null || { echo "unknown "; return 0; }
  if git -C "$repo" merge-base --is-ancestor "$prev" "$sha" 2>/dev/null; then
    echo "monotonic "; return 0
  fi
  # Fast path failed. Compare CONTENT: the deployed commit's patch-id vs every
  # commit in the incoming lineage since the fork point (single pass).
  pid="$(git -C "$repo" show "$prev" 2>/dev/null | git patch-id --stable 2>/dev/null | awk '{print $1}')"
  [ -n "$pid" ] || { echo "absent "; return 0; }
  base="$(git -C "$repo" merge-base "$prev" "$sha" 2>/dev/null || true)"
  [ -n "$base" ] || { echo "absent "; return 0; }
  twin="$(git -C "$repo" log -p --no-merges --format='commit %H' "$base..$sha" 2>/dev/null \
    | git patch-id --stable 2>/dev/null | awk -v p="$pid" '$1==p {print $2; exit}')"
  [ -n "$twin" ] && { echo "rewritten $twin"; return 0; }
  echo "absent "
  return 0
}

# Post-rewrite runbook line, shared by the swap's inline guard and
# tools/harvest/oc-verify-lineage (the read-only verb, #168 cut 5).
lineage_next_step() { # <verdict> <prev> <sha> <twin>
  case "$1" in
    monotonic) echo "next: proceed — the incoming build is a descendant of the deployed sha." ;;
    rewritten) echo "next: proceed — the deployed change is preserved as $4 in the incoming lineage (accepted automatically; no action needed)." ;;
    absent)    echo "next: DO NOT swap. The incoming build does not carry the deployed change. Re-dispatch a fresh build from fork main (oc-ship), or, if the regression is intentional and audited, re-run with --allow-rewritten-lineage \"<justification>\"." ;;
    unknown)   echo "next: cannot judge — $2 or $3 is not an object in this repo. Check OC_DEPLOY_REPO and that both shas were fetched." ;;
  esac
}

# ----------------------------------------------------------------------------
# carrier features — ONE reader, ONE value (T-5) (moved verbatim: 313-369)
# ----------------------------------------------------------------------------
# T-5 (2026-11-20): ONE value, ONE entry. `oc-build features` is the
# DOCUMENTED way to ask "what feature set does the carrier define"; the
# standalone oc-features is an INTERNAL helper behind it. Before this,
# the live journal carried 660 direct oc-features invocations against
# 2734 oc-deploy ones — two commands, one value, and a lane that asked the
# helper directly got a value the ship path could disagree with.
#
# The helper stays the ONE reader (it owns the carrier-yml parse and its rc
# contract); this verb is a THIN, argument-transparent wrapper. "Same value"
# is therefore structural, not a coincidence of two implementations: there is
# only one implementation.
CARRIER_TOOL_PATH() { echo "${OC_DEPLOY_CARRIER:-$(cd "$(dirname "$0")" && pwd)/oc-features}"; }

# carrier_features [--repo P] [--ref B] -> prints the set
carrier_features() {
  local repo="" ref="" tool out hrc errf
  while [ $# -gt 0 ]; do
    case "$1" in
      --repo) repo="${2:-}"; shift ;;
      --ref)  ref="${2:-}";  shift ;;
      *) die 1 "features: unknown arg: $1" ;;
    esac
    shift || true
  done
  tool="$(CARRIER_TOOL_PATH)"
  local args=()
  [ -n "$repo" ] && args+=(--repo "$repo")
  [ -n "$ref" ]  && args+=(--ref "$ref")
  # The helper's OWN rc is preserved (3 = carrier yml unreadable, 4 = no
  # features input): collapsing both into a generic 2 would destroy the
  # distinction a caller scripts on — "unreadable" is retryable, "no features
  # input" is not.
  errf="$(mktemp "${TMPDIR:-/tmp}/.oc-deploy-carrier-err.XXXXXX")" || errf=""
  out="$("$tool" "${args[@]}" 2>"$errf")"; hrc=$?
  if [ -n "$errf" ]; then [ -s "$errf" ] && cat "$errf" >&2; rm -f "$errf"; fi
  # The helper's OWN rc is PRESERVED (3 = carrier yml unreadable, 4 = no
  # features input): collapsing both into a generic 2 would destroy the
  # distinction a caller scripts on — "unreadable" is retryable, "no features
  # input" is not. The CALLER decides its own rc family: the ship path keeps
  # its documented rc 2, the `features` verb passes the helper's rc through.
  if [ "$hrc" -ne 0 ]; then
    echo "carrier features read FAILED (tool: $tool, rc=$hrc) — aborting, no silent fallback set" >&2
    return "$hrc"
  fi
  if [ -z "$out" ]; then
    echo "carrier features read FAILED (tool: $tool) — empty set, aborting, no silent fallback set" >&2
    return 4
  fi
  printf '%s\n' "$out"
}

features_run() { # [--repo P] [--ref B]
  carrier_features "$@" || exit $?
}

# ----------------------------------------------------------------------------
# lineage-check — MOVED OUT of the library (factory #168 cut 5).
# ----------------------------------------------------------------------------
# The verb body now lives in its own tool, tools/harvest/oc-verify-lineage,
# because it was never shared: the dispatcher was its ONLY caller, and the
# SWAP does not call it — oc-swap runs `lineage_verdict` inline (see the guard
# at its step 6). A library function with one caller, in a file every stage
# sources, is the drift surface the cut exists to remove: two spellings of
# one question, and a lane that grepped the lib could not tell which one the
# ship path actually used. The PREDICATE stays here (lineage_verdict /
# lineage_next_step above), so the tool and the inline guard still cannot
# disagree about a sha — only the ARGUMENT PARSING and the OUTPUT moved.
# ----------------------------------------------------------------------------
# recover-receipt — MOVED OUT of the library (factory #168 cut 5).
# ----------------------------------------------------------------------------
# The body now lives in tools/ship/oc-status, the tool that OWNS the read/handoff
# half of the split, and is reached as `oc-status recover-receipt`. It was never
# shared: the retired dispatcher was its only caller, so keeping it here put 195
# lines of journal-archaeology in a file every stage sources and no stage used.
# What stays here is what a SWAP writes and this verb READS: the journal dir, the
# deployed marker, `ledger_stamp` and the ledger reader. The repair and the write
# it repairs therefore still share one definition of where the evidence lives.

# ----------------------------------------------------------------------------
# stage reader + shadow log (moved verbatim: 585-590)
# ----------------------------------------------------------------------------
stage() { jq -r '.meta.oc_deploy_stage // "S0"' "$(ledger_view)" 2>/dev/null || echo S0; }
shadow_log() { # <op> <sha> <features> <result>
  printf '%s\t%s\t%s\t%s\t%s\tstage=%s\n' \
    "$(date -u +%FT%TZ)" "$1" "${2:--}" "${3:--}" "${4:--}" "$(stage)" \
    >> "$SHADOW" 2>/dev/null || true
}

# ----------------------------------------------------------------------------
# #704 fork-main tip read (moved verbatim: 647-676)
# ----------------------------------------------------------------------------
# ------------------------------------------------- #704 fork-main tip read ---
# Resolve the fork-main tip from the DEDICATED ref this tool's own fetch writes
# (`+refs/heads/main:refs/oc-deploy/main`), and only fall back to FETCH_HEAD.
# FETCH_HEAD is ONE shared, mutable file per repository, rewritten by EVERY
# `git fetch` in that repo — oc-gate fetches ci/quick-build-linux, harvest
# lanes fetch adolfousier/upstream — so a concurrent fetch landing in the ~2 s
# window between our fetch and this read silently substituted another remote's
# tip. Measured 2026-09-29 08:33Z (chain oc-ship-702-082945, sha 2a39b676): the
# tip read was upstream main, the auto-rebase replayed `upstream..sha` onto the
# wrong base, and four files the commit never touched conflicted. Exit 5 was the
# GOOD outcome — had the replay completed, upstream-derived history would have
# been pushed to fork main. `refs/oc-deploy/main` is written ONLY by this tool.
resolve_main_tip() {
  # `--verify -q`: a bare `rev-parse <unknown>` ECHOES the argument to stdout
  # (and the `||` fallback then appends its own line), so the old form could
  # return a TWO-LINE tip. Verify-quiet prints nothing on failure.
  git rev-parse --verify -q refs/oc-deploy/main 2>/dev/null \
    || git rev-parse --verify -q FETCH_HEAD 2>/dev/null
}

remote_main_tip() { # $1=remote ; the remote's OWN declaration of fork main
  git ls-remote "$1" refs/heads/main 2>/dev/null | awk 'NR==1{print $1}'
}

tip_is_fork_main() { # $1=tip $2=remote ; 0 iff tip == the remote's declared fork main
  local RM
  RM="$(remote_main_tip "$2")"
  [ -n "$RM" ] && [ "$1" = "$RM" ]
}

# ----------------------------------------------------------------------------
# journal (S2 spec) (moved verbatim: 677-691)
# ----------------------------------------------------------------------------
# ------------------------------------------------------- journal (S2 spec) --
JF=""; SEQ=0
journal_init() { # $1 = short label
  mkdir -p "$JOURNAL_DIR"
  JF="$JOURNAL_DIR/swap-$1-$(date +%s)-$$.jsonl"   # Duty-6 lens F task 4: $$ suffix — same-second collision truncated the first run's crash journal (fanout already had $$)
  : > "$JF"; SEQ=0
}
jline() { # $1=step  $2=exit(int|null)  $3=extra-json-object (optional)
  SEQ=$((SEQ+1))
  jq -cn --arg ts "$(date -u +%FT%TZ)" --argjson seq "$SEQ" --arg step "$1" \
     --argjson exit "${2:-null}" --argjson extra "${3:-\{\}}" \
     '{ts:$ts, seq:$seq, step:$step, exit:$exit} + $extra' >> "$JF"
  sync -f "$JF" 2>/dev/null || sync 2>/dev/null || true
}

# ----------------------------------------------------------------------------
# backup retention #497 (moved verbatim: 692-743)
# ----------------------------------------------------------------------------
# --------------------------------------------------- backup retention (#497) --
prune_binary_backups() { # $1 = the backup JUST TAKEN (never a prune candidate)
  # Keep the newest $BAK_KEEP backups, delete older ones (#497, HQ toolshed
  # item 2). Rules, each answering a way this could destroy a rollback point:
  #
  #  * ONLY files matching the chain's own naming convention are ever touched —
  #    `opencrabs-YYYYMMDD-HHMMSS-pre-<hex>`. Anything else in the directory
  #    (a hand-made copy, a differently-named artefact) is left alone, so this
  #    cannot eat a file it did not create.
  #  * ORDER IS THE FILENAME STAMP, never mtime: `cp -p` preserves the source's
  #    timestamps, so mtimes tie and mislead (measured 4-way). The stamp is
  #    fixed-width, so a lexicographic sort IS chronological.
  #  * THE JUST-TAKEN BACKUP IS EXEMPT by construction — it is the newest name —
  #    but it is also passed in explicitly and skipped by path, so a clock skew
  #    (a machine whose clock stepped back between swaps) cannot make the fresh
  #    backup look oldest.
  #  * NOTHING IS PRUNED BELOW THE KEEP COUNT, so an in-flight swap's journaled
  #    `backup_path` is inside the window: rollback reads that exact path and
  #    never scans the directory.
  #  * A NO-OP IS SILENT. A prune that reports on every healthy swap is noise.
  local fresh="${1:-}" keep="${BAK_KEEP:-5}" f
  [ -d "$BACKUP_DIR" ] || return 0
  case "$keep" in ''|*[!0-9]*) return 0 ;; esac   # a bad value must not mean "prune everything"
  [ "$keep" -ge 1 ] || return 0

  local pruned=0 freed=0 size
  # Newest-first by NAME; skip the first $keep, prune the remainder.
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ -n "$fresh" ] && [ "$f" = "$fresh" ] && continue
    size="$(stat -c %s "$f" 2>/dev/null || echo 0)"
    if rm -f "$f"; then
      pruned=$((pruned + 1))
      freed=$((freed + size))
    fi
  done <<EOF
$(ls -1 "$BACKUP_DIR" 2>/dev/null \
    | grep -E '^opencrabs-[0-9]{8}-[0-9]{6}-pre-[0-9a-f]+$' \
    | sort -r \
    | tail -n +"$((keep + 1))" \
    | sed "s|^|$BACKUP_DIR/|")
EOF

  if [ "$pruned" -gt 0 ]; then
    printf '%s: backup retention: pruned %d old backup(s), %d MB freed, kept newest %d\n' \
      "$OC_DEPLOY_PROG" \
      "$pruned" "$((freed / 1048576))" "$keep" >&2
    jline backup-prune 0 "$(jq -cn --argjson n "$pruned" --argjson b "$freed" \
      --argjson keep "$keep" '{pruned:$n, bytes_freed:$b, keep:$keep}')"
  fi
  return 0
}

# ----------------------------------------------------------------------------
# ledger stamp — DELEGATED to tools/state/oc-ledger (#156)
# ----------------------------------------------------------------------------
# ledger_stamp (by, what, kind) — the swap-result write.
#
# The pre-#156 body appended the row with bare jq under a deploy-lib-held
# flock. Three defects lived in those ten lines:
#   a. it poked the VIEW name (workers-ledger.json) blindly. In JSONL mode
#      (STATE_DIR carries events.jsonl) the RECORD is events.jsonl and the
#      view is workers.json — the row landed on a file the ledger no longer
#      tracks: invisible to every `oc-ledger events` consumer, never staged
#      by the git state-commit.
#   b. the ordinal was `max(events in the file it happened to hold)` — in
#      JSONL mode that is the STALE view, so n could collide with rows the
#      record already carries.
#   c. the deploy-lib flock and oc-ledger's with_lock lock the SAME
#      "$LEDGER.lock": a delegation made under a parent-held flock deadlocks
#      (the child inherits the open file description), so the flock must go.
#
# The write is therefore DELEGATED, never reimplemented: mode decision,
# locking, ordinal, append, read-back and the git tail are oc-ledger's.
# OC_LEDGER carries the resolved path (oc-ledger's own first precedence —
# `--ledger` exists only as a PRE-verb global, so appending it to the stamp
# argv is rc 2 `unknown flag`; RC-CONTRACT used to print that fiction). Kind
# stays enum-guarded on this side; rc is oc-ledger's, passed through verbatim.
#
# The text travels as a FILE, never as an argument. Callers compose it with
# command substitution (`"swap-result … sha=$(…) …"`), and text assembled that
# way is already shell-expanded BEFORE any callee sees it: a substitution
# yielding EMPTY output leaves no trace, and the ledger's read-back cannot see
# it (it compares two already-expanded copies — the #341 class). --what-file
# gives the bytes a path that never enters a shell. The temp is removed right
# after the call returns, so a killed deploy leaves at most one tiny file in
# TMPDIR rather than a half-written ledger row.
#
# One resolution, BY OVERRIDE: deploy-lib's LEDGER resolver (:53-59) stays
# and oc-ledger's own resolver is overridden via OC_LEDGER="$LEDGER" on
# every stamp call, so deploy-lib's path is the single authority for the
# writer AND the readers in this file (stage/shadow_log/recover-receipt).
# Deleting this fallback instead was considered and rejected: the readers
# and the fixture harness resolve through it, and the override already
# removes the second live opinion — do NOT "fix" either side back to a
# bare-default call.
#
# The ledger's own stdout (stamped n=... read-back ok) is NOT discarded:
# it flows into the ship journal as the write receipt and is the only place
# the row's n is visible to the swap tail.
ledger_stamp() { # $1=by  $2=what  $3=kind
  local _ls_kind="${3:-swap-result}"
  [ "$_ls_kind" = "swap-result" ] || { echo "$OC_DEPLOY_PROG: ledger_stamp kind must be swap-result (enum write-side guard, v0.4.77)" >&2; return 2; }
  [ -n "$2" ] || { echo "$OC_DEPLOY_PROG: ledger_stamp what must be non-empty" >&2; return 2; }
  if [ ! -x "$LEDGER_TOOL" ]; then
    echo "$OC_DEPLOY_PROG: ledger_stamp: ledger tool missing or not executable: $LEDGER_TOOL" >&2
    return 4
  fi
  # The old body wrote by:"" silently when the actor was empty; the ledger's
  # own law calls an anonymous row a defect, so an empty actor becomes an
  # EXPLICIT declared one via the escape hatch cmd_stamp itself documents.
  # The what-text goes through a file: see the header block above (#341).
  local _ls_tmp _ls_rc
  _ls_tmp="$(mktemp "${TMPDIR:-/tmp}/oc-deploy-what.XXXXXX")" || {
    echo "$OC_DEPLOY_PROG: ledger_stamp: cannot create a temp file for --what-file" >&2
    return 4
  }
  if ! printf '%s' "$2" > "$_ls_tmp"; then
    rm -f "$_ls_tmp"
    echo "$OC_DEPLOY_PROG: ledger_stamp: cannot write the --what-file temp $_ls_tmp" >&2
    return 4
  fi
  if [ -n "$1" ]; then
    OC_LEDGER="$LEDGER" "$LEDGER_TOOL" stamp "$_ls_kind" --what-file "$_ls_tmp" --by "$1"
  else
    OC_LEDGER="$LEDGER" "$LEDGER_TOOL" stamp "$_ls_kind" --what-file "$_ls_tmp" \
      --by "(unattributed)" --allow-unattributed
  fi
  _ls_rc=$?
  rm -f "$_ls_tmp"
  return $_ls_rc
}

# ----------------------------------------------------------------------------
# ledger_view — the path a READER consults (#156 companion to the stamp fix)
# ----------------------------------------------------------------------------
# The pre-#156 stage() read `.meta.oc_deploy_stage` off $LEDGER verbatim. In
# JSONL mode $LEDGER names the legacy file the record abandoned, so the stage
# reader would answer S0 forever (a swap LOCKED at S2 reads unlocked). The
# mode test mirrors oc-ledger's `_ledger_tracked_names` — events.jsonl in the
# ledger's dir means the view is workers.json — so the two tools cannot drift
# apart silently; the selftest's stage arms pin BOTH modes.
ledger_view() {
  if [ -f "$(dirname -- "$LEDGER")/events.jsonl" ]; then
    printf '%s/workers.json' "$(dirname -- "$LEDGER")"
  else
    printf '%s' "$LEDGER"
  fi
}

# ----------------------------------------------------------------------------
# A2A receipts (moved verbatim: 759-858)
# ----------------------------------------------------------------------------
# ------------------------------------------------------------ A2A receipts --
# #124 (2026-11-20): this leg has NEVER delivered a single receipt.
#
# TWO defects, each fatal on its own:
#   1. it sent `message/send` with `role:"ROLE_USER"`, a variant the gateway
#      rejects — `{"error":{"code":-32602,"message":"Invalid params: unknown
#      variant \`ROLE_USER\`, expected \`user\` or \`agent\`"}}`;
#   2. `>/dev/null 2>&1` threw the body away, and `curl -f` only fails on
#      HTTP >= 400 — so a JSON-RPC error carried on HTTP **200** read as
#      success. Census over the swap journals: 473 receipt rows, 242 of them
#      `a2a_accepted:true`, and not one was ever delivered.
#
# CORRECTING THE ROLE ALONE WOULD NOT HAVE FIXED IT. `message/send` CREATES A
# TASK (src/a2a/handler/send.rs) — measured 2026-11-20, the corrected-role probe
# spawned a real throwaway session (`A2A: probe-roast-test`) and still notified
# nobody. So a valid role would have re-armed the SAME false positive one layer
# down: `a2a_accepted:true` would have meant "a task was created", not "the
# owner was told".
#
# A receipt is a NOTIFICATION, so it uses `session/notify` — the method (and the
# `{outcome}` contract) the fan-out leg gets right via lib/oc-notify.sh — and it
# PARSES `result.outcome`. The transport status can never settle this: a JSON-RPC
# error rides on HTTP 200.

receipt_target_session() { # -> echoes a session uuid, rc 1 if none resolvable
  # An explicit override wins (tests, and any caller that knows its target).
  if [ -n "${OC_DEPLOY_RECEIPT_SESSION:-}" ]; then
    printf '%s\n' "$OC_DEPLOY_RECEIPT_SESSION"; return 0
  fi
  local db="${OC_RECEIPT_DB:-$HOME/.opencrabs/profiles/$NOTIFY_PROFILE/opencrabs.db}"
  [ -f "$db" ] || return 1
  command -v sqlite3 >/dev/null 2>&1 || return 1
  local id
  # A session_bindings row is authoritative; the title's `topic:<id>` tag is an
  # echo. Try the binding, then the tag. Archived sessions are NOT dead (owner
  # directive 2026-08-28) so they are not excluded — the route redirects.
  id="$(sqlite3 -readonly "$db" \
        "SELECT session_id FROM session_bindings WHERE thread_id=${RECEIPT_TOPIC} LIMIT 1;" \
        2>/dev/null | head -1)"
  if [ -z "$id" ]; then
    id="$(sqlite3 -readonly "$db" \
          "SELECT id FROM sessions WHERE title LIKE '%topic:${RECEIPT_TOPIC}%' ORDER BY updated_at DESC LIMIT 1;" \
          2>/dev/null | head -1)"
  fi
  [ -n "$id" ] || return 1
  printf '%s\n' "$id"
}

a2a_notify() { # $1=text ; exit 0 ONLY on a parsed delivered/queued outcome
  # On failure sets A2A_WHY (one line) so the journal row can say WHY without
  # anyone having to reproduce the send.
  A2A_OUTCOME="none"; A2A_WHY=""
  [ -n "$A2A_URL" ] || { A2A_WHY="no A2A_URL"; return 1; }
  local uuid
  if ! uuid="$(receipt_target_session)"; then
    A2A_WHY="no addressee for topic $RECEIPT_TOPIC"; return 1
  fi
  local body rc payload
  payload="$(jq -cn --arg sid "$uuid" --arg t "$1" \
    '{jsonrpc:"2.0", id:1, method:"session/notify",
      params:{session_id:$sid, message:$t, title:"oc-swap PHASE B RECEIPT",
              sender:"oc-swap"}}')" || { A2A_WHY="payload build failed"; return 1; }
  # Body CAPTURED, never discarded — that discard is defect 2.
  body="$("$A2A_CURL" -sS --max-time 15 -X POST "$A2A_URL" \
          -H 'Content-Type: application/json' -d "$payload" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    A2A_WHY="transport rc=$rc: $(printf '%s' "$body" | head -c 200)"; return 1
  fi
  # A JSON-RPC error on HTTP 200 is a REJECTION, not a delivery.
  if printf '%s' "$body" | jq -e '.error' >/dev/null 2>&1; then
    A2A_WHY="jsonrpc error: $(printf '%s' "$body" | jq -c '.error' 2>/dev/null | head -c 200)"
    return 1
  fi
  A2A_OUTCOME="$(printf '%s' "$body" | jq -r '.result.outcome // ""' 2>/dev/null)"
  case "$A2A_OUTCOME" in
    delivered|injected|redirected|queued) return 0 ;;
    no_route) A2A_WHY="no_route (target $uuid not live)"; return 1 ;;
    "")       A2A_WHY="no result.outcome in response: $(printf '%s' "$body" | head -c 200)"; return 1 ;;
    *)        A2A_WHY="outcome=$A2A_OUTCOME"; return 1 ;;
  esac
}

a2a_notify_retry() { # $1=text — retry up to OC_A2A_TRIES (default 6), sleeping
  # OC_A2A_RETRY_SLEEP (default 10s) between tries; returns a2a_notify's rc.
  # WHY (2026-08-28, journal swap-87d3bcb8-1787916830 seq9 exit=1): the receipt
  # races the daemon restart the swap itself just triggered — the gateway is
  # down for several seconds, the single-shot POST died, and the owner never
  # heard about a successful swap. Retrying makes the receipt survive the gap.
  # (#124) A no_route is NOT retried: a dead uuid is permanent, and 6 x 10s of
  # sleeping on it delays the swap's tail for nothing.
  [ -n "$A2A_URL" ] || return 1
  local n=0 max=${OC_A2A_TRIES:-6} s=${OC_A2A_RETRY_SLEEP:-10}
  while :; do
    a2a_notify "$1" && return 0
    case "${A2A_WHY:-}" in no_route*) return 1 ;; esac
    n=$((n+1)); [ "$n" -ge "$max" ] && return 1
    if [ "$s" -gt 0 ]; then sleep "$s"; fi
  done
}

# ----------------------------------------------------------------------------
# #766 fork release publish + #72 release identity (moved verbatim: 1366-1496)
# ----------------------------------------------------------------------------
# =============================================================================
# --- #766 FORK RELEASE PUBLISH — tail step of the swap path ------------------
# Owner-approved design 2026-10-04T21:14:29Z (fork#766, comment 5985138814);
# HQ work order 0117dd29. Publishes the SAME binary the swap path just
# downloaded and checksum-verified — builds NOTHING. Reuses the daemon's
# existing `gh` auth: no new secret and no Actions-secret dependency (an
# Actions-secret dependency is exactly what leaves upstream's release.yml dead
# on the fork).
#
# --- fork release identity: ONE derivation, TWO consumers (#72) --------------
# The release NAME (publish leg) and the version injected into the carrier build
# (dispatch leg) MUST be the same string, BY CONSTRUCTION and not by agreement.
# Why it is load-bearing rather than cosmetic: `evolve` compares the running
# binary's version against the release name, so a binary at fork.429 beside a
# release named fork.430 reports an update forever and re-downloads in a loop.
# Therefore VER/CYC are derived HERE, once, and both legs call this. Never
# compute them a second time inline — that is exactly how the two diverge.
# The legs differ ONLY by the offset, because the seal bumps the counter between
# them: dispatch runs BEFORE the seal, so it injects cycle+1 (offset 1), the
# value the seal is about to write; publish runs AFTER it, so the counter already
# holds that value and it reads cycle as-is (offset 0). Dispatch injecting the
# pre-seal cycle (offset 0) is the #72 off-by-one: the binary says fork.N while
# the release is named fork.N+1, and evolve re-downloads forever.
_fork_release_name() { # $1=sha $2=offset (default 0) -> "<upstream-version>+fork.<cycle+offset>"
  # offset 0 = read AFTER the seal (publish leg: the counter already names this deploy).
  # offset 1 = read BEFORE the seal (dispatch leg: the seal will write cycle+1).
  local sha="${1:-}" offset="${2:-0}" repo base_dir baseline ver cyc
  repo="${OC_DEPLOY_REPO:-${HOME:-/root}/opencrabs}"
  base_dir="$(dirname "$(readlink -f "$LEDGER" 2>/dev/null || echo "$LEDGER")")"
  baseline="$base_dir/baseline.json"
  # VER is the version AT $SHA (git show), never the working tree's.
  ver="$(git -C "$repo" show "$sha:Cargo.toml" 2>/dev/null | sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  [ -n "$ver" ] || ver="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$repo/Cargo.toml" 2>/dev/null | head -1)"
  [ -n "$ver" ] || ver="0.0.0"
  cyc="$(jq -r '.cycle // 0' "$baseline" 2>/dev/null || true)"
  [ -n "$cyc" ] || cyc=0
  printf '%s+fork.%s\n' "$ver" "$((cyc + offset))"
}

# Does the carrier workflow on the carrier ref DECLARE this dispatch input?
# An undeclared input is a hard 422 from the API — passing one against a carrier
# that has not shipped it yet would break EVERY ship, so the dispatch leg asks
# the carrier's own declaration instead of assuming (transition safety, #72).
_carrier_declares_input() { # $1=input name -> 0 declared, 1 not declared, 2 read FAILED
  local want="${1:-}" yml
  [ -n "$want" ] || return 2
  yml="$("$GH" api "repos/$FORK/contents/.github/workflows/$WF?ref=$CARRIER_REF" \
    -H "Accept: application/vnd.github.raw" 2>/dev/null)" || return 2
  [ -n "$yml" ] || return 2
  # `<<<` not `printf | grep -q`: under pipefail an early-exiting grep SIGPIPEs
  # printf, so the pipeline reports failure even when the match was found. It
  # only ever passed on short inputs that fit the pipe buffer (#691 lint leg).
  if grep -qE "^[[:space:]]+${want}:" <<< "$yml"; then return 0; fi
  return 1
}

# Contract (D1=P2 / D2=I2 / D3=A1 / D4=amd64-only):
#   assets : opencrabs-fork-linux-amd64.tar.gz · SHA256SUMS · build-flags.txt
#   tags   : rolling `fork-latest` (force-moved each publish)
#            immutable `fork-<sha7>` (created once, never moved)
#   name   : <upstream-version>+fork.<cycle>   (Cargo.toml · baseline.json)
#   url    : https://github.com/leshchenko1979/opencrabs/releases/download/fork-latest/opencrabs-fork-linux-amd64.tar.gz
# Idempotence: republishing the same sha clobbers fork-latest's assets and
#   SKIPS the immutable tag when it already exists.
#
# FAILURE IS TOLERATED BY CONTRACT. The caller runs this in a SUBSHELL and
# records a non-zero rc as a journal line only: a publish failure never rolls
# back a swap, never blocks a ship, never changes the ship's rc. The subshell
# also means an internal `die` or a `set -u` unbound reference exits only the
# subshell. Suppress the whole leg with OC_DEPLOY_NOPUBLISH=1 (selftest sets it).
#
# NOTE: this function sets its own EXIT trap to reap its staging dir, so it MUST
# be invoked in a subshell (its only caller is) — a bare call would replace the
# caller's EXIT trap.
publish_fork_release() { # $1=sha $2=run_id $3=features $4=binary-path $5=artifact-dir
  local SHA="${1:-}" RUN_ID="${2:-}" FEATURES="${3:-}" BIN="${4:-}" ARTDIR="${5:-}"
  [ -n "$SHA" ] && [ -n "$BIN" ] && [ -f "$BIN" ] || { echo "publish: missing sha or binary" >&2; return 1; }

  local SHA7="${SHA:0:7}" ASSET="opencrabs-fork-linux-amd64.tar.gz"
  local REPO="${OC_DEPLOY_REPO:-${HOME:-/root}/opencrabs}"
  local BASE_DIR BASELINE CYC VER NAME NOTES
  BASE_DIR="$(dirname "$(readlink -f "$LEDGER" 2>/dev/null || echo "$LEDGER")")"
  BASELINE="$BASE_DIR/baseline.json"

  # release name: <upstream-version>+fork.<cycle> — ONE derivation (#72), shared
  # with the carrier dispatch leg so the injected binary version and the release
  # name are the same string by construction. VER/CYC are recovered FROM the name
  # rather than computed again: a second computation is the divergence itself.
  NAME="$(_fork_release_name "$SHA")"
  VER="${NAME%%+fork.*}"
  CYC="${NAME##*+fork.}"

  # stage: the verified binary as `opencrabs`, plus its tarball, SHA256SUMS and
  # the carrier's own build-flags.txt (falling back to a synthesized one).
  local STAGE; STAGE="$(mktemp -d)" || return 1
  # shellcheck disable=SC2064
  trap "rm -rf '$STAGE'" EXIT
  cp "$BIN" "$STAGE/opencrabs" || { echo "publish: stage copy failed" >&2; return 1; }
  tar -czf "$STAGE/$ASSET" -C "$STAGE" opencrabs || { echo "publish: tar failed" >&2; return 1; }
  ( cd "$STAGE" && sha256sum "$ASSET" > SHA256SUMS ) || { echo "publish: sha256sum failed" >&2; return 1; }
  if [ -n "$ARTDIR" ] && [ -f "$ARTDIR/build-flags.txt" ]; then
    cp "$ARTDIR/build-flags.txt" "$STAGE/build-flags.txt"
  else
    printf 'source_ref=%s\nfeatures=%s\nsha256=%s\n' "$SHA" "$FEATURES" "$(sha256sum "$BIN" | cut -d' ' -f1)" > "$STAGE/build-flags.txt"
  fi

  NOTES="$(printf 'Fork build of opencrabs.\n\n- upstream version: %s\n- fork cycle: %s\n- sha: %s\n- run: %s\n- features: %s\n\nRolling consumer URL (no token):\nhttps://github.com/%s/releases/download/fork-latest/%s\n' \
    "$VER" "$CYC" "$SHA" "$RUN_ID" "$FEATURES" "$FORK" "$ASSET")"

  # --- immutable tag fork-<sha7>: create once, never moved (idempotent) ------
  if "$GH" release view "fork-$SHA7" --repo "$FORK" >/dev/null 2>&1; then
    echo "publish: fork-$SHA7 already exists — immutable tag left untouched"
  else
    "$GH" release create "fork-$SHA7" --repo "$FORK" --target "$SHA" \
      --title "$NAME" --notes "$NOTES" \
      "$STAGE/$ASSET" "$STAGE/SHA256SUMS" "$STAGE/build-flags.txt" >/dev/null 2>&1 \
      || { echo "publish: fork-$SHA7 create FAILED" >&2; return 1; }
  fi

  # --- rolling tag fork-latest: assets clobbered, tag force-moved ------------
  if "$GH" release view "fork-latest" --repo "$FORK" >/dev/null 2>&1; then
    "$GH" release upload "fork-latest" "$STAGE/$ASSET" "$STAGE/SHA256SUMS" "$STAGE/build-flags.txt" \
      --repo "$FORK" --clobber >/dev/null 2>&1 \
      || { echo "publish: fork-latest upload FAILED" >&2; return 1; }
    # Force-move the tag so fork-latest traces to the deployed sha. Best-effort:
    # the download URL resolves by tag NAME, so the release survives a ref move.
    "$GH" api -X PATCH "repos/$FORK/git/refs/tags/fork-latest" -f sha="$SHA" -F force=true >/dev/null 2>&1 \
      || echo "publish: fork-latest tag move skipped (assets still current)" >&2
    "$GH" release edit "fork-latest" --repo "$FORK" --title "$NAME" --notes "$NOTES" >/dev/null 2>&1 || true
  else
    "$GH" release create "fork-latest" --repo "$FORK" --target "$SHA" \
      --title "$NAME" --notes "$NOTES" \
      "$STAGE/$ASSET" "$STAGE/SHA256SUMS" "$STAGE/build-flags.txt" >/dev/null 2>&1 \
      || { echo "publish: fork-latest create FAILED" >&2; return 1; }
  fi

  echo "publish: fork release '$NAME' published (fork-latest + fork-$SHA7, sha=$SHA)"
  return 0
}

# ----------------------------------------------------------------------------
# KILL FILE brake (moved verbatim: 2071-2084)
# ----------------------------------------------------------------------------
# KILL FILE brake — invoked at the top of every REAL-mode arm of the dispatch
# case below, never from arg parsing (contract fix 2026-09-11, owner word via
# HQ d72bd52d). It used to run as "the first line of EVERY invocation", which
# also swallowed the surfaces the RC contract keeps ungated: with a kill file
# present `--help` reported 9 instead of 0, and the no-args / unknown-arg usage
# diags reported 9 instead of 1, because the brake sat above the -h|--help case
# and above the whole arg loop. Real ship / poll / swap-execute / watch / fanout
# work is still blocked, with the documented rc 9. `return 0` keeps the
# `[ -f ] && die` idiom from tripping `set -e` on the clean path.
kill_brake() {
  [ -f "$KILL_FILE" ] && die 9 "KILL FILE present ($KILL_FILE) — all deploy invocations abort"
  [ -f "$KILL_FILE2" ] && die 9 "KILL FILE present ($KILL_FILE2) — all deploy invocations abort"
  return 0
}

# ----------------------------------------------------------------------------
# argv loop — NEW WRAPPER around a verbatim block (2107-2156).
#
# In the source this was a top-level `while` loop in the main body. It is
# wrapped, NOT rewritten: the union of every verb's flags is kept exactly as it
# was, including `-h|--help` (the full oc-deploy usage) and `*) die 1 "unknown
# arg"`. Each tool calls it with its OWN remaining argv, so a flag the tool
# does not use still parses and still dies rc 1 on a typo — the same surface the
# single tool had.
# ----------------------------------------------------------------------------
oc_deploy_parse_args() { # $@ = flags for THIS invocation (the verb already shifted off)
SHA=""; FEATURES=""; FEATURES_EXPLICIT=0; EXECUTE=0; RUN_ID=""; DRILL=0; ARTDIR=""; DRYRUN=0; WITH_DELTA=0; ALLOW_DROP=0   # FEATURES="" = resolve from carrier (KERNEL D2, 2026-08-28)
WAIT_SECS=0; NOTIFY_SESSION=""   # C-#2: poll --wait / --notify-session
ALLOW_REWRITTEN_LINEAGE=0; RW_JUSTIFY=""; RW_ACTOR="${OC_DEPLOY_ACTOR:-$(id -un 2>/dev/null || echo unknown)}"   # v0.4.151: audited swap-guard override
GATED_RUN=""; GATED_SHA=""; ALLOW_UNGATED=0; UNGATED_JUSTIFY=""   # #355: gate-before-land (reuses oc-ship's --gated-run/--gated-sha contract)
# #77: scheduling class. `low` (nice 19 + ionice class idle) is the default
# because ship/poll sit in remote-CI waits for minutes and must not compete with
# the daemon. `normal` is the opt-out.
PRIORITY="low"; PRIORITY_PROBE=0; PRIORITY_NICE=""; PRIORITY_IOPRIO=""; PRIORITY_APPLIED="none"
# #675-safe: the KERNEL's per-process guard must not change.
while [ $# -gt 0 ]; do
  case "$1" in
    --sha)      SHA="${2:-}"; shift ;;
    --features) FEATURES="${2:-}"; shift; FEATURES_EXPLICIT=1 ;;
    --execute)  EXECUTE=1 ;;
    --run)      RUN_ID="${2:-}"; shift ;;
    --drill)    DRILL=1 ;;
    --allow-features-drop) ALLOW_DROP=1 ;;  # HQ law 2026-09-04: explicit escape hatch for the features-compat gate
    --allow-rewritten-lineage)   # v0.4.151: audited override for a genuinely-absent deployed change (justification MANDATORY)
      [ -n "${2:-}" ] || die 2 "OC_DEPLOY_GATE=override-needs-justification: --allow-rewritten-lineage requires a non-empty justification string (it is journaled with the actor)"
      ALLOW_REWRITTEN_LINEAGE=1; RW_JUSTIFY="${2:-}"; shift ;;
    --actor)    [ -n "${2:-}" ] || die 2 "--actor needs a value (lane uuid or name)"; RW_ACTOR="${2:-}"; shift ;;
    --gated-run) [ -n "${2:-}" ] || die 2 "OC_DEPLOY_GATE=gate-arg-empty: --gated-run needs a run id"; GATED_RUN="${2:-}"; shift ;;   # #355: the PR-lane gate run that gated this sha
    --gated-sha) [ -n "${2:-}" ] || die 2 "OC_DEPLOY_GATE=gate-arg-empty: --gated-sha needs a sha"; GATED_SHA="${2:-}"; shift ;;   # #355: the sha that WAS gated (this sha, or a content-identical rebase of it)
    --allow-ungated-push)   # #355: audited escape hatch, mirrors --allow-rewritten-lineage (justification MANDATORY)
      [ -n "${2:-}" ] || die 2 "OC_DEPLOY_GATE=override-needs-justification: --allow-ungated-push requires a non-empty justification string (it is journaled with the actor)"
      ALLOW_UNGATED=1; UNGATED_JUSTIFY="${2:-}"; shift ;;
    --dry-run)  DRYRUN=1 ;;   # issue #24: fanout rehearsal — never marks done
    --with-delta) WITH_DELTA=1 ;;   # merge B (v0.4.48): watch rides oc-upstream-delta too
    --wait)     WAIT_SECS="${2:-}"; shift ;;   # C-#2: poll blocks until a NEW green run (or timeout, rc 5)
    --notify-session) [ -n "${2:-}" ] || die 2 "--notify-session needs a session uuid"; NOTIFY_SESSION="${2:-}"; shift ;;   # C-#2: session uuid woken on handoff/timeout; guard lens C MED-3 (v0.4.79)
    --artifact-dir) ARTDIR="${2:-}"; shift ;;
    # #77: scheduling class. Validated HERE so a typo dies at the caller's own
    # arg boundary (rc 2) instead of reaching the apply step as a bad input.
    --priority)
      PRIORITY="${2:-}"
      case "$PRIORITY" in
        low|normal) : ;;
        '') die 2 "--priority needs 'low' or 'normal' (got nothing)" ;;
        *)  die 2 "--priority needs 'low' or 'normal' (got '$PRIORITY')" ;;
      esac
      shift ;;
    # #77: read-only probe — applies the REAL block, prints the resolved class,
    # exits 0 before the carrier read or any network call. The selftest drives
    # THIS; a re-implementation in the test would prove nothing.
    --resolve-priority) PRIORITY_PROBE=1 ;;
    -h|--help)  echo "usage: oc-deploy ship [--sha S] [--features F] [--execute] [--gated-run ID] [--gated-sha SHA] [--allow-ungated-push \"<justification>\"] [--allow-features-drop] [--priority low|normal] [--resolve-priority] | poll [--execute] [--wait N] [--notify-session UUID] | swap-execute --sha S --run R [--features F] [--artifact-dir D] [--drill] [--allow-features-drop] [--allow-rewritten-lineage \"<justification>\" [--actor A]] | recover-receipt [--journal J] [--run R] [--sha S] [--dry-run] [--historical] [--json] | features [--repo P] [--ref B] | watch [--with-delta] | status [--json] | fanout --run R [--dry-run] | --selftest  (contributors RETIRED — use oc-attrib --contributors)"; exit 0 ;;
    *)          die 1 "unknown arg: $1" ;;
  esac
  shift || true
done
}

# ----------------------------------------------------------------------------
# scheduling priority #77 (moved verbatim: 2158-2196)
# ----------------------------------------------------------------------------
# ---- scheduling priority (#77) ----------------------------------------------
# Applied to THIS process so every child (gh, git, oc-gate) inherits it at
# fork. `renice` rather than a `nice -n 19` wrapper: swap-execute may already
# have re-exec'd us out of the unit cgroup, and a second exec layer would make
# "which PID is the deploy" depend on which branches fired.
# A failed renice/ionice is a WARNING and never a die — refusing to ship because
# we could not lower our own priority would trade a scheduling nicety for an
# outage. What the class actually APPLIED is re-read from the kernel and carried
# in the journal row, so a run can be classified afterwards rather than inferred
# from the flag someone typed.
oc_priority_apply() {  # $1 = low|normal ; sets PRIORITY_NICE/PRIORITY_IOPRIO/PRIORITY_APPLIED
  local want="$1" a=""
  PRIORITY_APPLIED="none"
  PRIORITY_NICE="$(ps -o nice= -p $$ 2>/dev/null | tr -d ' ')"
  PRIORITY_IOPRIO="$(ionice -p $$ 2>/dev/null || true)"
  if [ "$want" = "low" ]; then
    if command -v renice >/dev/null 2>&1; then
      if renice -n 19 -p $$ >/dev/null 2>&1; then
        a="renice"
      else
        printf '%s\n' "$OC_DEPLOY_PROG: WARNING: renice -n 19 failed -- running at nice ${PRIORITY_NICE:-?} (#77)" >&2
      fi
    else
      printf '%s\n' "$OC_DEPLOY_PROG: WARNING: no renice -- running at nice ${PRIORITY_NICE:-?} (#77)" >&2
    fi
    if command -v ionice >/dev/null 2>&1; then
      if ionice -c3 -p $$ >/dev/null 2>&1; then
        a="${a:+$a+}ionice"
      else
        printf '%s\n' "$OC_DEPLOY_PROG: WARNING: ionice -c3 failed -- I/O priority unchanged (#77)" >&2
      fi
    else
      printf '%s\n' "$OC_DEPLOY_PROG: WARNING: no ionice -- I/O priority unchanged (#77)" >&2
    fi
    PRIORITY_APPLIED="${a:-none}"
    PRIORITY_NICE="$(ps -o nice= -p $$ 2>/dev/null | tr -d ' ')"
    PRIORITY_IOPRIO="$(ionice -p $$ 2>/dev/null || true)"
  fi
}

# ----------------------------------------------------------------------------
# priority REPORT — NEW WRAPPER around a verbatim block (2198-2210).
# Same reason as oc_deploy_parse_args: a top-level block, shared by four tools.
# `--resolve-priority` prints the resolved class and exits 0 (the selftest
# drives THIS, so a re-implementation in a test would prove nothing).
# ----------------------------------------------------------------------------
oc_priority_report() {
if [ "$PRIORITY_PROBE" = "1" ]; then
  # #77 req 2: a child spawned AFTER the renice must inherit it. Asserting only
  # the parent's nice cannot distinguish "applied before the children" from
  # "applied after" -- and a nice 19 parent does NOT yield a child that forked
  # at 0 (the issue's own warning). This forks a REAL child ($BASHPID inside
  # `bash -c` is the new process) and reports what it actually reads.
  PRIORITY_CHILD_NICE="$(bash -c 'ps -o nice= -p $$' 2>/dev/null | tr -d ' ')"
  printf 'priority=%s\nnice=%s\nioprio=%s\napplied=%s\nchild_nice=%s\n' \
    "$PRIORITY" "${PRIORITY_NICE:-}" "${PRIORITY_IOPRIO:-}" "${PRIORITY_APPLIED:-none}" "${PRIORITY_CHILD_NICE:-}"
  exit 0
fi
printf '%s %s: priority=%s (nice=%s ioprio=%s applied=%s)\n' \
  "$OC_DEPLOY_PROG" \
  "$MODE" "$PRIORITY" "${PRIORITY_NICE:-}" "${PRIORITY_IOPRIO:-}" "${PRIORITY_APPLIED:-none}" >&2
}

# ----------------------------------------------------------------------------
# features resolution — NEW WRAPPER around a verbatim block (2212-2284).
# Reads $MODE, $FEATURES, $FEATURES_EXPLICIT, $ALLOW_DROP and may die rc 2
# (KERNEL D2 / #108 DROP-ONLY / FEATURE-DEFAULT). Body untouched.
# ----------------------------------------------------------------------------
oc_features_resolve() {
# KERNEL D2 (2026-08-28): --features omitted -> resolve the carrier's
# features default via oc-features. A carrier read FAILURE ABORTS —
# the hardcoded fallback set was deleted, never silently ship a wrong set.
# FEATURE-DEFAULT law (HQ 2026-09-07, incident #125 lane d5863180 / carrier
# run 34143410835): the carrier default (telegram) DESYNCED from the live
# deployment (deployed.meta.json: telegram,code-graph) — artifact name embeds
# features verbatim, so the Phase-B swap units died 'artifact download
# failed'.
# #108 (2026-11-20, toolsmith): the remedy is DROP-ONLY, not a symmetric
# compare. A symmetric compare made the deployed feature set IMMUTABLE: an
# addition was refused pre-dispatch AND an omitted --features was rewritten
# back to the deployed set, so no carrier default could ever ADD a feature
# and `eval` could never reach the live binary. The old justification does
# not hold for an addition — within one ship->poll->swap chain the same
# $FEATURES feeds the dispatch (-f features=), swap-execute --features and
# oc-seal --features, so build and swap cannot disagree. So: an
# explicit --features that DROPS a deployed feature fails fast here (unless
# --allow-features-drop), an addition proceeds and is shadow-logged, and an
# omitted --features still defers to deployed.meta.json WHEN THE CARRIER
# WOULD DROP — but adopts the carrier set when it ADDS. Same predicate as the
# features-compat gate in swap_execute() this one precedes.
if [ -z "$FEATURES" ]; then
  CARRIER_TOOL="$(CARRIER_TOOL_PATH)"
  case "$MODE" in
    ship|poll)
      # T-5: the SAME helper the `features` verb uses — one reader, one value.
      # The ship path keeps its OWN rc family (2 — the usage/validation family
      # its callers script on); only the READER is shared, not the rc.
      FEATURES="$(carrier_features)" \
        || die 2 "carrier features read FAILED — aborting, no silent fallback set"
      shadow_log features-resolve "-" "$FEATURES" "carrier-default"
      ;;
    swap-execute) : ;;  # stage-gate in swap_execute decides first; empty FEATURES fails loudly downstream, never silently
  esac
fi
# ship-only reconciliation against the live deployment (runs AFTER carrier
# resolution so both default and explicit paths are covered; poll keeps the
# pre-incident behavior — the incident window was ship dispatch).
# #108 (2026-11-20): DROP-ONLY, and the rationale is stated ONCE — see the #108
# block above the omitted-features path. An addition proceeds; a DROP of a deployed
# feature is the failure class (HQ LAW 2026-09-04) and --allow-features-drop is
# honoured HERE as well as at the swap gate, so a deliberate drop is not refused one
# stage before the stage that permits it.
if [ "$MODE" = ship ] && [ -n "$FEATURES" ] && [ -f "$DEPLOYED_META" ]; then
  DEP_FEATS="$(jq -r '.features // ""' "$DEPLOYED_META" 2>/dev/null || true)"
  if [ -n "$DEP_FEATS" ] && [ "$DEP_FEATS" != "null" ]; then
    # order-insensitive set compare (comma lists), same normalization the
    # features-compat swap gate uses — 'a,b' == 'b,a' is not a mismatch
    SHIP_DROP_LIST="$(comm -23 \
      <(printf '%s\n' "$DEP_FEATS" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' | sort -u) \
      <(printf '%s\n' "$FEATURES"  | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' | sort -u) | tr '\n' ',' | sed 's/,$//')"
    SHIP_ADD_LIST="$(comm -13 \
      <(printf '%s\n' "$DEP_FEATS" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' | sort -u) \
      <(printf '%s\n' "$FEATURES"  | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' | sort -u) | tr '\n' ',' | sed 's/,$//')"
    if [ -n "$SHIP_DROP_LIST" ]; then
      if [ "$FEATURES_EXPLICIT" = 1 ]; then
        if [ "$ALLOW_DROP" != 1 ]; then
          shadow_log ship "-" "$FEATURES" "features-mismatch-refused"
          die 2 "OC_DEPLOY_GATE=feature-mismatch: explicit --features '$FEATURES' DROPS deployed feature(s): ${SHIP_DROP_LIST} — live binary has '$DEP_FEATS' (deployed.meta.json) — refusing pre-dispatch. Additions are fine; drops are the failure class. Pass the deployed set, or --allow-features-drop to override deliberately."
        fi
        shadow_log ship "-" "$FEATURES" "features-drop-allowed:$SHIP_DROP_LIST"
        echo "$OC_DEPLOY_PROG: --allow-features-drop — dropping deployed feature(s) ${SHIP_DROP_LIST} deliberately (pre-dispatch gate, #108)"
      else
        shadow_log ship "-" "$FEATURES" "features-default-corrected:$DEP_FEATS"
        echo "$OC_DEPLOY_PROG: carrier default '$FEATURES' drops deployed '$DEP_FEATS' — adopting deployed set (FEATURE-DEFAULT)"
        FEATURES="$DEP_FEATS"
      fi
    elif [ -n "$SHIP_ADD_LIST" ]; then
      shadow_log ship "-" "$FEATURES" "features-add-adopted:$SHIP_ADD_LIST"
      echo "$OC_DEPLOY_PROG: adding feature(s) ${SHIP_ADD_LIST} over deployed '$DEP_FEATS' (drop-only gate, #108)"
    fi
  fi
fi
}

# ----------------------------------------------------------------------------
# selftest (moved from 862-869; ONE line added: oc_deploy_load_funcs)
# ----------------------------------------------------------------------------
selftest() { # body lives in tests/deploy-selftest.sh (sourced: nested check_* close over local pass/fail)
  local _sf="$OC_TOOLS_DIR/tests/deploy-selftest.sh"
  if [ ! -f "$_sf" ]; then
    printf 'deploy selftest: %s missing (broken LOCAL TOOL TREE, not a test result)\n' "$_sf" >&2
    return 2   # (#932 discipline) a box fault, never a silent 0 or a bare 127
  fi
  oc_deploy_load_funcs   # NEW (the split): the suite exercises all four tools, so every arm's functions must be in THIS shell
  . "$_sf"
}

# ----------------------------------------------------------------------------
# oc_deploy_load_funcs — NEW, and the only genuinely new code in this file.
#
# The suite in tests/deploy-selftest.sh calls functions from every stage
# (stage, plan, swap_execute, status_run, fanout_run, notify_one, ...), because
# it was written when all of them lived in one file. Each split tool carries a
# documented `OC_DEPLOY_FUNCS_ONLY=1` hook that defines its functions and
# RETURNS before its prologue and main body — so sourcing it here is inert: no
# second log row, no second mirror copy, no second trap, no verb run.
# ----------------------------------------------------------------------------
oc_deploy_load_funcs() {
  local t list
  # NO argument = every stage, which is what selftest() needs (its arms call
  # functions from all four). NAMED arguments = exactly those stages, which is
  # what a RUNTIME consumer needs: the split moved bodies out of one file, so a
  # call that used to be intra-file is now cross-tool and the shell answers
  # rc 127 "command not found". Three consumers have such calls (measured by
  # whole-file scan, #68-plan T5-bis):
  #   oc-build  -> oc-fanout (run_built_sha, decode_job_sha_any) + oc-status (watch_precheck, watch_covered)
  #   oc-swap   -> oc-fanout (fanout_run and its closure)
  #   oc-status -> oc-fanout (fanout_run, notify_session, run_built_sha, ...)
  # Loading is acyclic by construction: every tool's FUNCS_ONLY guard sits ABOVE
  # its prologue, so a loaded peer defines its functions and returns without
  # sourcing this lib again or executing a verb.
  if [ "$#" -gt 0 ]; then list="$*"; else list="oc-build oc-swap oc-fanout oc-status"; fi
  for t in $list; do
    [ -f "$OC_TOOLS_DIR/ship/$t" ] || die 2 "oc_deploy_load_funcs: $OC_TOOLS_DIR/ship/$t missing (broken LOCAL TOOL TREE, not a test result)"
    OC_DEPLOY_FUNCS_ONLY=1 . "$OC_TOOLS_DIR/ship/$t"
    OC_DEPLOY_FUNCS_ONLY=0
  done
}

# ----------------------------------------------------------------------------
# OPTIONAL libraries (#932): a MISSING one is a fault of THIS BOX, never a
# statement about a run. Detection is recorded ONCE, here, so every tool that
# sources this file inherits the same answer.
# ----------------------------------------------------------------------------
_OC_EMBED="$OC_TOOLS_DIR/lib/oc-embed.sh"
# (#68-plan TASK 2) This library is CONDITIONAL and its absence used to be INVISIBLE.
# The bare `[ -f ] && source` fell through, so `oc_decode_job_sha_any` was an
# UNDEFINED COMMAND; the shell reported rc 127 for it and every call site read that
# as a NEGATIVE ANSWER. run_built_sha's `|| continue` then skipped every job name
# and returned 3 -- "the jobs list was READ and no job name decodes: a statement
# about the RUN, permanent" -- so a missing library was filed as a run that carries
# no build sha, FOREVER (fanout marks it done), with no diagnostic naming the cause.
# Record the fact here; decode_job_sha_any turns it into the TRANSIENT rc 5 that the
# fan-out's unreadable branch already handles (never marked, next scan retries #84).
_OC_EMBED_MISSING=0
if [ -f "$_OC_EMBED" ]; then source "$_OC_EMBED"; else _OC_EMBED_MISSING=1; fi
_OC_NOTIFY_LIB="$OC_TOOLS_DIR/lib/oc-notify.sh"
# (#932 criterion 3) SAME DEFECT as the embed lib one line above, and the worse half:
# an absent oc-notify.sh left `oc_notify_session` UNDEFINED, so notify_session
# returned the shell's rc 127, `_notify_reason` had no arm for it and journalled
# `reason:"unknown", verb_rc:127` -- an UNDECLARED code in a durable record -- while
# `_notify_retryable 127` said RETRYABLE, so the fan-out burned its whole
# NOTIFY_RETRY_BUDGET (180 s) re-sending through a library that cannot appear.
_OC_NOTIFY_MISSING=0
if [ -f "$_OC_NOTIFY_LIB" ]; then source "$_OC_NOTIFY_LIB"; else _OC_NOTIFY_MISSING=1; fi   # E-F4 (v0.4.97): shared wake contract
