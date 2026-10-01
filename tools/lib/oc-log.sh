#!/usr/bin/env bash
# =============================================================================
# lib/oc-log.sh — unified tool log (KERNEL batch D0, 2026-08-28, owner order:
# "all tools save also to a single log file we will analyse in future").
#
# Every oc-* tool sources this lib and calls:
#     oc_log_init "<toolname>" "$@"      # right after set -u / arg parse
#     trap 'oc_log_finish $?' EXIT       # merge with any existing EXIT trap
#
# ONE JSONL line per invocation is appended at exit to $OC_TOOLS_LOG
# (default: /root/.opencrabs/profiles/ops/opencrabs-dev/tools.log):
#     {"ts":"…Z","tool":"oc-x","actor":"<uuid>","args":"…","exit":0,"secs":1.2,"extra":{}}
#
# actor — $OC_ACTOR (a session/role uuid) when set, else "unknown". Every
# oc-* invocation must carry OC_ACTOR=<session-uuid> (owner rule 2026-08-30)
# so floods/behavior stay attributable after the fact (ledger-beats-memory
# guard); an unset tool logs "unknown" so gaps are visible, never silent.
#
# Filterable/searchable by design — jq recipes live in SKILL.md §Unified
# tools log. Per-tool journals (the logging law) are UNTOUCHED: journals stay
# the durable step-by-step record, this file is the cross-tool analysis
# aggregate.
#
# Suppression: the invocation IS a selftest -- either the `--selftest` FLAG or
# the bare `selftest` SUBCOMMAND (oc-deploy dispatches both from one case arm),
# see oc_is_selftest() below -- or OC_TOOLS_NOLOG=1 (the battery sets this so
# suites stay silent). A bare-subcommand selftest used to slip the flag-only
# predicate and log every fixture child it spawned into the PRODUCTION log.
# Degrades to silence (never breaks the host tool): no jq, no line, no write.
# =============================================================================

OC_LOG_ENABLED=0
OC_LOG_TOOL=""
OC_LOG_ARGS=""
OC_LOG_EXTRA="{}"
OC_LOG_START=""

# oc_is_selftest -- TRUE when this invocation is the tool's own selftest.
# M2-21 (2026-09-12, toolsmith): the `--selftest` FLAG is not the only spelling --
# oc-deploy dispatches `--selftest|selftest) selftest "$@" ;;` as ONE case arm, and
# the bare SUBCOMMAND slipped the flag-only predicate. Consequence: OC_TOOLS_NOLOG
# was never exported, so every fixture child the selftest spawned was logged to the
# PRODUCTION tools.log -- six fixture shas across two weeks (08-31 -> 09-12) that
# oc-ship-audit read back as ORPHANED dispatches, reddening a gate that fronts
# `oc-ledger commit-pending`. The same predicate guards oc_log_flood_guard, which
# must never trip on a selftest replaying its own failure fixtures.
# First-token match for the bare form ONLY: a VALUE that happens to read
# "selftest" (e.g. `--dir selftest`) must never silence a real invocation.
#
# #749b (2026-10-01, toolsmith): the first-token arm still misfired when the
# VALUE IS the first token. oc-drift-check's first positional is a session uuid
# and `selftest` is legal there, so `oc-drift-check selftest` ran a REAL check
# (rc 1, NO-HISTORY) and wrote NO row at all -- and because OC_TOOLS_NOLOG is
# EXPORTED, the suppression was inherited by its children, so the oc-ledger
# grandchild went dark too. A row never written is indistinguishable from a run
# that never happened. The same hole swallowed the tools whose first positional
# is free text -- oc-log-search (pattern), oc-issue-sweep (query),
# oc-harvest-sweep (branch) -- measured at 0 rows each.
#
# The bare SUBCOMMAND spelling is therefore a property of the TOOLS that
# dispatch one -- exactly five carry a `selftest)` case arm -- and NOT of the
# fleet. oc_log_init sets OC_LOG_TOOL BEFORE this predicate runs, so the arm can
# be scoped to its owners: a free-text positional that reads `selftest` in any
# other tool now logs normally. Battery section 00d holds this list EQUAL to the
# real set of arms in both directions, and its negative control (the env hook
# below) proves the arm is what suppresses the row.
OC_LOG_BARE_SELFTEST_TOOLS_DEFAULT=" oc-commit oc-deploy oc-ledger oc-roster oc-watcher-audit "
OC_LOG_BARE_SELFTEST_TOOLS="${OC_LOG_BARE_SELFTEST_TOOLS:-$OC_LOG_BARE_SELFTEST_TOOLS_DEFAULT}"
oc_is_selftest() {
  case " $OC_LOG_ARGS " in
    *" --selftest "*) return 0 ;;
  esac
  case "$OC_LOG_BARE_SELFTEST_TOOLS" in
    *" ${OC_LOG_TOOL:-} "*) [ "${OC_LOG_ARGS%% *}" = "selftest" ] && return 0 ;;
  esac
  return 1
}

oc_log_init() {
  OC_LOG_TOOL="${1:-unknown}"
  shift 2>/dev/null || true
  OC_LOG_ARGS="$*"
  case " $OC_LOG_ARGS " in
    *" --no-log "*)   export OC_TOOLS_NOLOG=1 ;;  # lib-level suppression (E-B1, 2026-08-31): tools no longer pre-scan argv
  esac
  # recursive selftest children stay silent too (M2-21: the bare subcommand counts)
  if oc_is_selftest; then export OC_TOOLS_NOLOG=1; fi
  if [ "${OC_TOOLS_NOLOG:-0}" = "1" ]; then
    OC_LOG_ENABLED=0
    return 0
  fi
  OC_LOG_ENABLED=1
  OC_LOG_START="$(date +%s.%N)"
  oc_log_flood_guard
  # Signal honesty (#74, A3-lane report 2026-09-03): an async kill left $? at
  # the last COMPLETED command (usually 0), so the EXIT trap journaled an
  # exit-0 success row for an interrupted invocation. Trap TERM/INT/HUP and
  # exit 128+N: the EXIT trap then logs the true kill status, and extra.signal
  # names the signal — "interrupted" can never read as "success".
  trap 'oc_log_extra "signal" "TERM"; exit 143' TERM
  trap 'oc_log_extra "signal" "INT";  exit 130' INT
  trap 'oc_log_extra "signal" "HUP";  exit 129' HUP
  return 0
}

# oc_log_flood_guard — C-F1 (lens C 2026-08-31, owner "Go all"): a runaway
# lane re-invoking a failing tool in a loop (evidence: 140-row storm, one
# night) is refused at init. Counts PRIOR failed invocations with identical
# tool+args in the last 120s; >=4 prior failures -> the 5th attempt exits 8
# with a loud stderr banner. Bypass: OC_NO_FLOODGUARD=1 (selftests always
# bypass — a selftest replaying failures must not trip its own guard).
# Known limit (F-L4, v0.4.77): the guard matches IDENTICAL tool+args only —
# varying-arg storms (timestamps/run-ids interpolated into args) never trip
# rc 8; identical-args loops do.
oc_log_flood_guard() {
  [ "${OC_NO_FLOODGUARD:-0}" = "1" ] && return 0
  if oc_is_selftest; then return 0; fi   # M2-21: the bare `selftest` subcommand bypasses too
  command -v jq >/dev/null 2>&1 || return 0
  local logf="${OC_TOOLS_LOG:-${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}/tools.log}"
  [ -f "$logf" ] || return 0
  local cutoff n
  cutoff="$(($(date +%s) - 120))"
  n="$(tail -n 300 "$logf" 2>/dev/null | jq -R -r \
    --arg tool "$OC_LOG_TOOL" --arg args "${OC_LOG_ARGS:0:500}" --argjson cutoff "$cutoff" '
    fromjson? | select(.tool == $tool and .args == $args and ((.exit // 0) != 0))
    | ((.ts // "" | fromdateiso8601? // 0)) | select(. >= $cutoff)' 2>/dev/null | wc -l)"
  if [ "${n:-0}" -ge 4 ]; then
    echo "FLOOD-GUARD (rc 8): $OC_LOG_TOOL with identical args already failed ${n}x in the last 120s — refusing to run again." >&2
    echo "  Fix the underlying failure, change the args, or set OC_NO_FLOODGUARD=1 to bypass (and say why in the lane journal)." >&2
    exit 8
  fi
  return 0
}

# oc_log_extra <key> <value> — add a string field to the invocation's extra{}
oc_log_extra() {
  [ "${OC_LOG_ENABLED:-0}" = "1" ] || return 0
  command -v jq >/dev/null 2>&1 || return 0
  OC_LOG_EXTRA="$(jq -cn --argjson e "${OC_LOG_EXTRA:-{\}}" --arg k "${1:-}" --arg v "${2:-}" \
    '$e + {($k): $v}' 2>/dev/null)" || OC_LOG_EXTRA="{}"
  return 0
}

# oc_log_finish <exit-code> — append the JSONL line. Never fails, never
# changes the host tool's exit code.
oc_log_finish() {
  local rc="${1:-0}"
  [ "${OC_LOG_ENABLED:-0}" = "1" ] || return 0
  command -v jq >/dev/null 2>&1 || return 0
  local end secs line logf
  end="$(date +%s.%N)"
  secs="$(awk -v s="${OC_LOG_START:-$end}" -v e="$end" 'BEGIN { printf "%.1f", e - s }' 2>/dev/null)"
  [ -n "$secs" ] || secs="0.0"
  line="$(jq -cn \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg tool "$OC_LOG_TOOL" \
    --arg actor "${OC_ACTOR:-${OPENCRABS_SESSION_ID:-unknown}}" \
    --arg args "${OC_LOG_ARGS:0:500}" \
    --argjson exit "$rc" \
    --arg secs "$secs" \
    --argjson extra "${OC_LOG_EXTRA:-{\}}" \
    '{ts:$ts, tool:$tool, actor:$actor, args:$args, exit:$exit, secs:($secs|tonumber), extra:$extra}' 2>/dev/null)" || return 0
  [ -n "$line" ] || return 0
  logf="${OC_TOOLS_LOG:-${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}/tools.log}"
  mkdir -p "$(dirname "$logf")" 2>/dev/null
  if command -v flock >/dev/null 2>&1; then
    ( flock -x 9; printf '%s\n' "$line" >>"$logf" ) 9>>"$logf.lock" 2>/dev/null \
      || printf '%s\n' "$line" >>"$logf" 2>/dev/null
  else
    printf '%s\n' "$line" >>"$logf" 2>/dev/null
  fi
  return 0
}

# oc_ledger_path -- THE canonical workers-ledger.json path (v0.4.38 precedence:
# OC_LEDGER > OC_DEV_STATE > profile default). Every tool spelled this expression
# inline, so one literal and one precedence lived in a dozen files and could drift
# in any one of them. A caller with its own ledger source (a --ledger flag, a
# fixture) parses that itself and skips this helper.
oc_ledger_path() {
  printf '%s\n' "${OC_LEDGER:-${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}/workers-ledger.json}"
}

# oc_session_trailer <commit-message-text> — Duty-6 lens F task 2 (v0.4.91 batch)
# ONE Session-Id convention for ALL tools: git interpret-trailers semantics —
# the LAST Session-Id trailer wins (trailers are an ordered stack; the last one
# is the most recent attribution). Replaces the head -1 (oc-order-validate) vs
# tail -1 (oc-attrib) split that let one quoted-trailer message validate as
# signed but attribute as unsigned. Falls back to grep semantics when git
# interpret-trailers is unavailable (non-git context).
oc_session_trailer() { # stdin/arg: commit message text; stdout: uuid or empty
  local msg="${1:-}"
  [ -n "$msg" ] || msg="$(cat)"
  printf '%s\n' "$msg" | git interpret-trailers --parse 2>/dev/null \
    | sed -n 's/^[Ss]ession-[Ii][Dd]:[[:space:]]*//p' | tail -1
}

# oc_has <haystack> <needle> — LITERAL substring test; rc 0 present / 1 absent.
# (#537) The SIGPIPE-free replacement for the fleet's `echo "$out" | grep -q PAT`
# idiom, which under `set -o pipefail` is a latent FALSE NEGATIVE: `grep -q`
# exits at the FIRST match and closes the pipe, the writer (`echo`/`printf`, a
# shell builtin) then takes SIGPIPE, and the pipeline's status becomes 141 —
# not 0 — so the compound is false EVEN THOUGH THE PATTERN MATCHED. Whether it
# fires is a race gated by payload size and by whether a newline follows the
# match; 129 sites in the echo form and 78 in the printf form carry the class.
#
# `case` matches inside the shell itself — no pipe, no second process, so the
# status is the comparison's alone and cannot be the writer's.
#
# The needle is QUOTED inside the case arm. That is what makes it a literal
# substring rather than a pattern, and it is load-bearing: unquoted, real tokens
# from this corpus are PARSE-TIME syntax errors, not wrong matches —
#     case "$out" in *Draft: true (--draft)*)  -> syntax error near `true'
#     case "$out" in *age: 0.3h*)              -> syntax error near `0.3h*'
#
# Quoting also makes glob metacharacters in the needle literal: a needle of `*`
# matches a literal `*`, NOT "anything" — the deliberate difference from grep,
# which would read it as a pattern. An EMPTY needle matches everything (every
# string contains the empty string), mirroring `grep -q ""`.
#
# Safe under `set -u` (both params default) and `set -o pipefail` (no pipeline).
oc_has() { # <haystack> <needle> -> 0 present / 1 absent
  case "${1:-}" in *"${2:-}"*) return 0 ;; *) return 1 ;; esac
}

# J-5 (c23): the newline-safe append predicate has ONE home.
# An unterminated append poisons the NEXT writer -- the last row of the log
# glues onto the first line of the new one, and the damage is silent (a reader
# sees a longer line, never an error). Two tools each hand-rolled this check
# before this helper existed (oc-smoke's append_log_safe, oc-smoke-evidence's
# append_log); they were functionally identical, which is the shape the
# single-source guard exists to collapse. Cost already paid: proposal n=4177,
# the glued-rows incident on lane c10cd97b (2026-09-12).
oc_append_line_safe() { # <file> <line> -> appends, terminating a prior unterminated row
  local f="${1:-}" c="${2:-}"
  [ -n "$f" ] || return 2
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  if [ -s "$f" ] && [ -n "$(tail -c 1 "$f" 2>/dev/null || true)" ]; then
    printf '\n' >> "$f"   # terminate the previous writer's unterminated row
  fi
  printf '%s\n' "$c" >> "$f"
}

# #588: the CHARACTER-safe clip has ONE home.
# `cut -c1-N` counts BYTES under C.UTF-8 (this box's locale), not characters.
# A cap landing inside a multi-byte character leaves a DANGLING LEAD BYTE, and
# appending a literal ellipsis after it yields a string no UTF-8 reader can
# decode — the whole file then fails a plain text read. Measured on the live
# smoke-verdicts.log: 2 rows carry `...PASS \xe2\xe2\x80\xa6[tru`, and
# `open(path, encoding='utf-8').read()` dies on them. The damage is silent to
# grep/tail, which is why it survived a green battery.
# Bash's `${var:0:N}` is character-safe (and this lib is bash-only: it already
# uses `local`). Use it for ANY text that can hold non-ASCII.
oc_clip_chars() { # <text> <cap-chars> -> prints at most <cap> CHARACTERS
  local t="${1:-}" cap="${2:-0}"
  case "$cap" in ''|*[!0-9]*) cap=0 ;; esac
  if [ "$cap" -le 0 ] || [ "${#t}" -le "$cap" ]; then
    printf '%s' "$t"
  else
    printf '%s' "${t:0:$cap}"
  fi
}
