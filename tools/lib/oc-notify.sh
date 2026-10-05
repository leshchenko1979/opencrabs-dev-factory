#!/usr/bin/env bash
# lib/oc-notify.sh — shared session-wake contract (E-F4, v0.4.97)
#
# Single owner of the session-notify wake logic previously duplicated between
# oc-deploy (notify_session, fanout path) and oc-waiter (resolve_notify_bin +
# notify_lane; oc-waiter was RETIRED in v0.4.135 and its stub deleted in #737).
# Consumers source this file and delegate.
# Also serves as an executable CLI wrapper for cross-session task chaining:
#   cmd && tools/lib/oc-notify.sh <target-uuid> <text> [title]
#
# Exit-code contract enforced here (src/cli/session_notify.rs):
#   0 delivered / 2 no_route (dead uuid, permanent) /
#   3 refused_in_flight (target mid-turn — retry ONCE with --interrupt; a
#     mid-turn target MUST be woken or the verdict is lost) / 4 transport.
#
# Consumers may override via env BEFORE sourcing (or as documented args):
#   OC_NOTIFY_BIN      notify binary path (default: $NOTIFY_BIN, then
#                      /usr/local/bin/opencrabs, then PATH lookup)
#   OC_NOTIFY_PROFILE  --profile value (default ops)

oc_notify_resolve_bin() { # -> echoes binary path, rc 1 if unresolvable
  local b="${OC_NOTIFY_BIN:-${NOTIFY_BIN:-}}"
  if [ -n "$b" ]; then [ -x "$b" ] && { echo "$b"; return 0; }; return 1; fi
  if [ -x /usr/local/bin/opencrabs ]; then echo /usr/local/bin/opencrabs; return 0; fi
  command -v opencrabs 2>/dev/null
}

oc_notify_session() { # $1=bin $2=profile $3=sender $4=uuid $5=title $6=text
  # -> 0 delivered / rc passthrough of the session-notify contract
  local bin="$1" profile="$2" sender="$3" uuid="$4" title="$5" text="$6"
  local nrc=0 rrc=0 t_start
  t_start="$(date +%s)"
  # #466: the CLI leg needs a budget of its OWN. Without one a hung
  # `session notify` blocks this function forever, and the A2A fallback below
  # is only reached on a NON-zero rc -- so the fallback exists for exactly the
  # case that prevents it from ever running. A timeout exits 124, which is not
  # 0/2/3, so a hung CLI now falls through to the A2A leg as intended.
  local cli_timeout="${OC_NOTIFY_CLI_TIMEOUT:-90}" tmo=""
  if command -v timeout >/dev/null 2>&1; then tmo="timeout $cli_timeout"; fi
  $tmo "$bin" session notify --profile "$profile" --sender "$sender" \
    --title "$title" --text "$text" "$uuid" >/dev/null 2>&1 || nrc=$?
  if [ "$nrc" = 3 ]; then   # refused_in_flight: mid-turn target — MUST be woken
    $tmo "$bin" session notify --profile "$profile" --sender "$sender" \
      --title "$title" --text "$text" --interrupt "$uuid" >/dev/null 2>&1 || rrc=$?
    nrc=$rrc
  fi
  # Fallback to direct daemon A2A JSON-RPC if CLI resolution or CLI invocation failed
  if [ "$nrc" -ne 0 ] && [ "$nrc" -ne 2 ] && [ "$nrc" -ne 3 ]; then
    local a2a_rc=0
    python3 -c "
import sys, json, os, urllib.request
try:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    p = os.path.expanduser('~/.opencrabs/profiles/' + sys.argv[2] + '/config.toml')
    port = 18791
    if os.path.exists(p):
        with open(p, 'rb') as f:
            port = tomllib.load(f).get('a2a', {}).get('port', 18791)
    url = f'http://127.0.0.1:{port}/a2a/v1'
    data = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'session/notify',
        'params': {
            'session_id': sys.argv[4],
            'message': sys.argv[6],
            'title': sys.argv[5],
            'sender': sys.argv[3]
        }
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        result = res.get('result', {})
        outcome = result.get('outcome', '')
        if outcome in ('delivered', 'injected', 'redirected', 'queued'):
            sys.exit(0)
        elif outcome == 'no_route':
            sys.exit(2)
        elif outcome in ('refused', 'refused_in_flight'):
            sys.exit(3)
        else:
            sys.exit(4)
except Exception:
    sys.exit(4)
" "$bin" "$profile" "$sender" "$uuid" "$title" "$text" 2>/dev/null || a2a_rc=$?
    if [ "$a2a_rc" -eq 0 ] || [ "$a2a_rc" -eq 2 ] || [ "$a2a_rc" -eq 3 ]; then
      nrc=$a2a_rc
    fi
  fi

  # Final verification: if CLI or caller timed out or reported failure, check session-notify.journal
  # to see if the notify actually landed (prevents false negative rc=124 on slow CLI returns).
  if [ "$nrc" -ne 0 ] && [ "$nrc" -ne 2 ] && [ "$nrc" -ne 3 ]; then
    local j_rc=1
    python3 -c "
import sys, os, datetime
try:
    target = sys.argv[1]
    t0 = float(sys.argv[2])
    profile = sys.argv[3]
    jp = os.path.expanduser('~/.opencrabs/profiles/' + profile + '/logs/session-notify.journal')
    if not os.path.exists(jp):
        jp = os.path.expanduser('~/.opencrabs/logs/session-notify.journal')
    if os.path.exists(jp):
        with open(jp, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        for line in reversed(lines[-50:]):
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                ts_str, caller, tgt, outcome, exit_str = parts[:5]
                t_val = tgt.split('=', 1)[1] if '=' in tgt else tgt
                o_val = outcome.split('=', 1)[1] if '=' in outcome else outcome
                e_val = exit_str.split('=', 1)[1] if '=' in exit_str else exit_str
                if t_val == target and o_val in ('delivered', 'injected', 'redirected', 'queued') and e_val == '0':
                    dt = datetime.datetime.fromisoformat(ts_str)
                    if dt.timestamp() >= t0 - 5:
                        sys.exit(0)
except Exception:
    pass
sys.exit(1)
" "$uuid" "$t_start" "$profile" 2>/dev/null || j_rc=$?
    if [ "$j_rc" -eq 0 ]; then
      nrc=0
    fi
  fi
  return "$nrc"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    -h|--help)
      cat <<'EOH'
Usage: oc-notify.sh <target-uuid> <text> [title]
       oc-notify.sh -h | --help

Dispatches a session notification directly to an OpenCrabs session.
Enforces the session-notify exit contract (auto-retries with --interrupt on rc 3).

Arguments:
  target-uuid   Full session UUID to receive notification
  text          Notification message body
  title         Optional notification title (defaults to "Task Complete")

Exit:
  0 delivered / 2 no_route (dead uuid) / 3 refused / 4 transport
EOH
      exit 0
      ;;
  esac

  TARGET_UUID="${1:-}"
  TEXT="${2:-}"
  TITLE="${3:-Task Complete}"
  SENDER="${OC_ACTOR:-${OPENCRABS_SESSION_ID:-${SESSION_ID:-opencrabs-dev}}}"
  PROFILE="${OC_NOTIFY_PROFILE:-ops}"

  if [ -z "$TARGET_UUID" ] || [ -z "$TEXT" ]; then
    echo "Usage: oc-notify.sh <target-uuid> <text> [title]" >&2
    exit 2
  fi

  case "$TARGET_UUID" in
    *[!0-9a-f-]*)
      echo "oc-notify: invalid target uuid '$TARGET_UUID'" >&2
      exit 2
      ;;
  esac

  BIN="$(oc_notify_resolve_bin)" || {
    echo "oc-notify: opencrabs binary not found" >&2
    exit 4
  }

  oc_notify_session "$BIN" "$PROFILE" "$SENDER" "$TARGET_UUID" "$TITLE" "$TEXT"
  exit $?
fi
