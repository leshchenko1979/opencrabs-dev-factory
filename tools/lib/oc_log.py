#!/usr/bin/env python3
"""oc_log.py - the ONE Python home for the unified tools log.

PARITY WITH tools/lib/oc-log.sh. That shell lib is the contract; this module is
its Python twin, so a Python tool and a shell tool write the SAME row shape to
the same file:

    {"ts":"...Z","tool":"oc-x","actor":"<uuid>","args":"...","exit":0,
     "secs":1.2,"extra":{}}

ONE JSONL line per invocation, appended at exit, flock-serialized, to
$OC_TOOLS_LOG (default: ${OC_DEV_STATE:-~/.opencrabs/profiles/ops/opencrabs-dev}/tools.log).

WHY THIS MODULE EXISTS (#739). The fleet's Python tools each hand-rolled a copy
of this parity, and the copies had already DRIFTED apart:

    tool               _is_selftest                        flood rc  signals
    oc-questions       --selftest + bare selftest          none      none
    oc-census          --selftest ONLY                     none      yes
    oc-issue-dispatch  --selftest + bare selftest          7         yes
    oc-log.sh (canon)  --selftest + tool-scoped bare       8         yes

The census copy missed the #749b bare-subcommand form - the exact class that
silently swallowed rows for five tools - and the dispatch copy exits 7 where the
contract says 8. A fourth copy would have deepened that. So new Python
consumers import THIS module instead. (Retiring the three existing copies is a
separate change: it moves REGISTERED rc semantics, so it must not ride a
"make two tools log" fix.)

USAGE

    from oc_log import oc_log_init, oc_log_extra, oc_log_finish

    def main(argv):
        ...
        oc_log_extra("set", set_id)
        return rc

    if __name__ == "__main__":
        oc_log_init("oc-x")          # right after argv is known
        rc = main(sys.argv)
        oc_log_finish(rc)
        sys.exit(rc)

`bare_selftest=True` ONLY for a tool that dispatches a bare `selftest)`
subcommand - passing it otherwise re-opens #749b, where a free-text positional
reading `selftest` silenced a REAL invocation.

DEGRADES TO SILENCE: nothing here may change the host tool's exit code. Any
failure in this module returns quietly and the tool runs as if uninstrumented.
"""

import datetime
import json
import os
import sys
import time

_LOG_ENABLED = False
_LOG_TOOL = ""
_LOG_ARGS = ""
_LOG_EXTRA = {}
_LOG_START = 0.0
_LOG_FINISHED = False

FLOOD_GUARD_RC_DEFAULT = 8  # the bash contract's rc (oc-log.sh: "FLOOD-GUARD (rc 8)")


def _log_path():
    """The canonical tools.log path - OC_TOOLS_LOG > OC_DEV_STATE > profile default."""
    return os.environ.get(
        "OC_TOOLS_LOG",
        os.path.join(
            os.environ.get(
                "OC_DEV_STATE",
                os.path.expanduser("~/.opencrabs/profiles/ops/opencrabs-dev"),
            ),
            "tools.log",
        ),
    )


def _is_selftest(argv, bare_selftest):
    """--selftest anywhere; the bare `selftest` FIRST TOKEN only when opted in."""
    if "--selftest" in argv:
        return True
    if bare_selftest and argv and argv[0] == "selftest":
        return True
    return False


def oc_log_init(tool, argv=None, signals=True, flood_guard_rc=None, bare_selftest=False):
    """Arm the log for this invocation. Call ONCE, right after argv is known.

    tool            the `tool` field's value (e.g. "oc-claims-single-source")
    argv            args WITHOUT the program name (default: sys.argv[1:])
    signals         install TERM/INT/HUP traps that log the true kill status
    flood_guard_rc  run the flood guard, exiting with this rc on a storm
                    (None = no guard; pass 8 for the bash contract's behaviour)
    bare_selftest   treat a leading bare `selftest` as a selftest (see module doc)
    """
    global _LOG_ENABLED, _LOG_TOOL, _LOG_ARGS, _LOG_EXTRA, _LOG_START, _LOG_FINISHED
    try:
        args = list(sys.argv[1:] if argv is None else argv)
        _LOG_TOOL = str(tool)
        _LOG_ARGS = " ".join(str(a) for a in args)
        _LOG_EXTRA = {}
        _LOG_FINISHED = False

        if "--no-log" in args:
            os.environ["OC_TOOLS_NOLOG"] = "1"
        # A selftest's fixture children inherit the suppression, or every child
        # it spawns logs to the PRODUCTION log (M2-21, the six phantom shas).
        if _is_selftest(args, bare_selftest):
            os.environ["OC_TOOLS_NOLOG"] = "1"
        if os.environ.get("OC_TOOLS_NOLOG", "0") == "1":
            _LOG_ENABLED = False
            return

        _LOG_ENABLED = True
        _LOG_START = time.time()

        if flood_guard_rc is not None:
            _flood_guard(flood_guard_rc)
        if signals:
            _install_signal_traps()
    except Exception:
        _LOG_ENABLED = False


def _install_signal_traps():
    """A killed invocation must log its TRUE status, never a stale 0 (lib #74)."""
    import signal

    def _sig(signum, _frame):
        sig_map = {signal.SIGTERM: ("TERM", 143), signal.SIGINT: ("INT", 130),
                   signal.SIGHUP: ("HUP", 129)}
        name, code = sig_map.get(signum, ("SIG%d" % signum, 128 + signum))
        oc_log_extra("signal", name)
        oc_log_finish(code)
        sys.exit(code)

    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(s, _sig)
        except Exception:
            pass


def _flood_guard(rc):
    """Refuse the 5th identical-args failure in 120s (a runaway lane's storm).

    Matches IDENTICAL tool+args only (the bash lib's known limit F-L4): a storm
    that interpolates a timestamp into its args never trips this.
    """
    if os.environ.get("OC_NO_FLOODGUARD", "0") == "1":
        return
    logf = _log_path()
    if not os.path.isfile(logf):
        return
    cutoff = time.time() - 120
    prior = 0
    try:
        with open(logf, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines[-300:]:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if (row.get("tool") == _LOG_TOOL
                    and str(row.get("args", ""))[:500] == _LOG_ARGS[:500]
                    and int(row.get("exit", 0)) != 0):
                ts = str(row.get("ts", ""))
                try:
                    val = datetime.datetime.fromisoformat(
                        ts[:-1] + "+00:00" if ts.endswith("Z") else ts).timestamp()
                except Exception:
                    continue
                if val >= cutoff:
                    prior += 1
    except Exception:
        return
    if prior >= 4:
        sys.stderr.write(
            "FLOOD-GUARD (rc %d): %s with identical args already failed %dx in the "
            "last 120s - refusing to run again.\n"
            "  Fix the underlying failure, change the args, or set "
            "OC_NO_FLOODGUARD=1 to bypass (and say why in the lane journal).\n"
            % (rc, _LOG_TOOL, prior))
        sys.exit(rc)


def oc_log_extra(key, value):
    """Add a string field to this invocation's extra{}."""
    if _LOG_ENABLED:
        _LOG_EXTRA[str(key)] = str(value)


def oc_log_finish(exit_code=0):
    """Append the JSONL row. Idempotent, and never changes the tool's rc."""
    global _LOG_FINISHED
    if not _LOG_ENABLED or _LOG_FINISHED:
        return
    _LOG_FINISHED = True
    try:
        end = time.time()
        row = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool": _LOG_TOOL,
            "actor": (os.environ.get("OC_ACTOR")
                      or os.environ.get("OPENCRABS_SESSION_ID") or "unknown"),
            "args": _LOG_ARGS[:500],
            "exit": int(exit_code) if isinstance(exit_code, int) else 1,
            "secs": round(end - (_LOG_START if _LOG_START > 0 else end), 1),
            "extra": _LOG_EXTRA,
        }
        line = json.dumps(row, separators=(",", ":"))
        logf = _log_path()
        os.makedirs(os.path.dirname(logf), exist_ok=True)
        try:
            import fcntl
            with open(logf + ".lock", "a") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                with open(logf, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except ImportError:
            with open(logf, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        return


# ---------------------------------------------------------------------------
# selftest: the row's shape, and the suppression that makes it meaningful.
# ---------------------------------------------------------------------------
def selftest():
    import tempfile

    legs = 0
    failed = []

    def ck(cond, msg):
        nonlocal legs
        legs += 1
        if not cond:
            failed.append(msg)
        print("%s - %s" % ("ok  " if cond else "FAIL", msg))

    tmp = tempfile.mkdtemp(prefix="oc-log-py-selftest-")
    logf = os.path.join(tmp, "tools.log")
    saved = {k: os.environ.get(k) for k in ("OC_TOOLS_LOG", "OC_TOOLS_NOLOG", "OC_ACTOR")}

    # 1. a real invocation writes exactly one well-formed row
    os.environ["OC_TOOLS_LOG"] = logf
    os.environ["OC_TOOLS_NOLOG"] = "0"
    os.environ["OC_ACTOR"] = "selftest-actor"
    oc_log_init("oc-log-py-selftest", argv=["--scan", "/tmp"])
    oc_log_extra("k", "v")
    oc_log_finish(0)
    rows = [l for l in open(logf, encoding="utf-8").read().splitlines() if l.strip()]
    ck(len(rows) == 1, "one row per invocation (got %d)" % len(rows))
    try:
        row = json.loads(rows[0])
        ck(row.get("tool") == "oc-log-py-selftest", "tool field")
        ck(row.get("actor") == "selftest-actor", "actor comes from OC_ACTOR")
        ck(row.get("exit") == 0 and row.get("extra") == {"k": "v"}, "exit + extra")
        ck(str(row.get("ts", "")).endswith("Z"), "ts is UTC Z")
    except Exception as e:  # pragma: no cover
        ck(False, "row parses as JSON (%s)" % e)

    # 2. NEGATIVE CONTROL: suppression must make the row VANISH. Without this the
    #    leg above would only be measuring that the file can be written at all.
    os.remove(logf)
    os.environ["OC_TOOLS_NOLOG"] = "1"
    oc_log_init("oc-log-py-selftest", argv=["--scan", "/tmp"])
    oc_log_finish(0)
    ck(not os.path.exists(logf), "control: OC_TOOLS_NOLOG=1 writes NO row")

    # 3. a selftest suppresses ITSELF, and the flag is EXPORTED so fixture
    #    children inherit it (M2-21: six fixture shas reached the prod log).
    os.environ.pop("OC_TOOLS_NOLOG", None)
    oc_log_init("oc-log-py-selftest", argv=["--selftest"])
    oc_log_finish(0)
    ck(not os.path.exists(logf), "--selftest self-suppresses")
    ck(os.environ.get("OC_TOOLS_NOLOG") == "1", "the suppression is EXPORTED to children")

    # 4. the bare form is OPT-IN: #749b was a real invocation silenced because a
    #    free-text positional happened to read `selftest`.
    os.environ.pop("OC_TOOLS_NOLOG", None)
    oc_log_init("oc-log-py-selftest", argv=["selftest"], bare_selftest=False)
    oc_log_finish(0)
    ck(os.path.exists(logf), "bare `selftest` as a VALUE still logs (bare_selftest=False)")
    os.remove(logf)
    os.environ.pop("OC_TOOLS_NOLOG", None)
    oc_log_init("oc-log-py-selftest", argv=["selftest"], bare_selftest=True)
    oc_log_finish(0)
    ck(not os.path.exists(logf), "bare `selftest` as the SUBCOMMAND suppresses (opt-in)")

    # 5. oc_log_finish is idempotent (an EXIT path plus a signal must not double-write)
    os.environ.pop("OC_TOOLS_NOLOG", None)
    oc_log_init("oc-log-py-selftest", argv=[])
    oc_log_finish(0)
    oc_log_finish(0)
    n = len([l for l in open(logf, encoding="utf-8").read().splitlines() if l.strip()])
    ck(n == 1, "finish twice -> still one row (got %d)" % n)

    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("selftest: %d passed, %d failed" % (legs - len(failed), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(selftest())
