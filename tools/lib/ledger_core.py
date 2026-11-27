#!/usr/bin/env python3
"""ledger_core.py — the STORE + LOCK layer of oc-ledger, in Python (factory #204).

This module is the sharp end of the oc-ledger port: the four semantics that the
bash tool carries comments for precisely because each one has a measured
incident behind it. Nothing here is a redesign. Every branch below exists
because the shell branch it mirrors was bought with a live fleet failure, and
the failure is quoted next to it.

WHAT IT IS
    ``load_ledger()``   the ONE reader  (bash ``ledger_load``, oc-ledger:846)
    ``atomic_write()``  the ONE writer  (bash ``atomic_jq``,   oc-ledger:924)
    ``with_lock()``     the fleet flock (bash ``with_lock``,   oc-ledger:1033)
    ``flush_git_tail()`` the deferred commit tail (bash ``_oc_flush_git_tail``,
                        oc-ledger:679)

STORE LAYOUT (unchanged; the record is the fleet's durability)

    <state dir>/events.jsonl          append-only, one JSON object per line
    <state dir>/workers.json          non-event state (roster, meta)
    <state dir>/workers-ledger.json   LEGACY compact view. When events.jsonl is
                                      ABSENT the tool runs the legacy path
                                      unchanged, so every pre-#149 fixture and
                                      every un-migrated state dir keeps working.
                                      The migration is opt-in per state dir and
                                      reversible by deleting one file.

RC VOCABULARY (tools/docs/RC-CONTRACT.md; identical to the bash tool)
    0 ok · 2 usage · 3 parse-or-load refused · 4 write-fail or lock timeout.
    :class:`LedgerError` carries the code, so a caller never guesses.

THE FOUR TRAPS, AND WHY EACH IS A TRAP
    1. A malformed JSONL line RAISES and is NEVER skipped. A skipped line turns
       a corrupt row into a MISSING row, and every closure and dispatch
       predicate then reads "no claim" — a false green on exactly the surface
       this ledger exists to make honest. The error names the line.
    2. ``atomic_write`` splits back into a TRUE APPEND only when the transform
       pushed exactly one event onto the END (prefix equality). That is the
       whole point of #149/#177: one ~200-byte line per stamp instead of a
       fresh multi-MB blob rewrite. Anything else rewrites the record
       wholesale, and ``workers.json`` is rewritten ONLY when it changed.
    3. ``with_lock`` NEVER spawns a child while holding the lock. bash's ``9>&-``
       at oc-ledger:1043 is load-bearing (#641): bash does not set
       close-on-exec on fds > 2, so a child inherits fd 9, flock is released
       only when the LAST fd on the open file description closes, and
       ``git gc --auto`` children held the fleet lock 19+ minutes on a 2.7 GB
       repo while three lanes timed out at 90/180/240 s. Here the discipline is
       structural: pure-Python work inside, and the git tail runs strictly
       after the release.
    4. ``flush_git_tail`` is DEFERRED and NEVER FATAL (#95). A failed commit
       must not fail an append that already landed and fsynced, and network
       time must never sit under the fleet lock (measured 2026-11-19: the lock
       held 25 minutes while ``git status`` sat in D-state, 18 lanes queued,
       every stamp dying rc 4).

STDLIB ONLY. No jq, no third-party packages — the same precedent
``tools/state/oc-questions`` sets. The jq renderers in here exist because the
read verbs must stay output-identical to the bash tool; see :mod:`jqfmt` below.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# rc vocabulary — the SAME numbers as the bash tool (never renumbered: every
# lane in the fleet keys on them).
# ---------------------------------------------------------------------------
RC_OK = 0
RC_VERDICT = 1        # a read verb's NO-MATCH / DRIFT verdict, never an error
RC_USAGE = 2
RC_REFUSED = 3        # parse-or-load refused
RC_IO = 4             # write-fail, or lock timeout

EVENTS_NAME = "events.jsonl"
WORKERS_NAME = "workers.json"
LEGACY_NAME = "workers-ledger.json"

PROG = "oc-ledger"


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------
class LedgerError(Exception):
    """A refusal carrying its rc. ``message`` is printed verbatim on stderr.

    The bash tool's ``die`` prints ``oc-ledger: <message>`` and exits; keeping
    the same shape here means a caller migrating from ``$(...)``-and-rc to
    Python sees the same diagnostics.
    """

    def __init__(self, rc: int, message: str):
        super().__init__(message)
        self.rc = rc
        self.message = message


class LockTimeout(LedgerError):
    """``flock`` gave up. rc 4, and the message names the budget and its knob."""

    def __init__(self, message: str):
        super().__init__(RC_IO, message)


class JqError(Exception):
    """A jq-semantics failure inside a read verb (indexing a non-object, …).

    The read verbs call it a refusal (rc 3) exactly as the bash does when jq
    exits non-zero, but it is a distinct type so a caller can tell "the ledger
    is fine, my projection was wrong" from "the ledger is unreadable".
    """


# ---------------------------------------------------------------------------
# small helpers (bash oc-ledger:190-340)
# ---------------------------------------------------------------------------
def now_iso() -> str:
    """UTC ``%Y-%m-%dT%H:%M:%SZ`` — byte-identical to the bash builtin.

    bash uses ``printf '%(%Y-%m-%dT%H:%M:%SZ)T' -1`` under ``TZ=UTC0`` (#149
    spawn reduction); this is the same instant, same shape, no subprocess.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                      r"[0-9a-f]{4}-[0-9a-f]{12}$")


def is_uuid(value) -> bool:
    """rc-0-iff-a-canonical-8-4-4-4-12-LOWERCASE-hex-uuid (bash ``_is_uuid``).

    Lowercase only, deliberately (#441): the shape a session id actually
    carries. ``derive_by`` lowercases its input for the same reason, so an
    UPPERCASE actor could never match a roster row and must not be accepted as
    one here either.
    """
    return bool(_UUID_RE.match(value or ""))


def state_dir(ledger: str) -> str:
    """The directory the record lives in (bash ``STATE_DIR``)."""
    return os.path.dirname(ledger) or "."


def events_path(ledger: str) -> str:
    return os.path.join(state_dir(ledger), EVENTS_NAME)


def workers_path(ledger: str) -> str:
    return os.path.join(state_dir(ledger), WORKERS_NAME)


def jsonl_mode(ledger: str) -> bool:
    """True when the RECORD is ``events.jsonl`` (bash ``_jsonl_mode``).

    Decided by the file being PRESENT, never by the path the caller passed: a
    fixture that only carries the compact file stays in legacy mode, which is
    what keeps every pre-#149 fixture and the whole legacy battery working.
    """
    return (os.path.isfile(events_path(ledger))
            or os.path.basename(ledger) == EVENTS_NAME)


def live_state_dir() -> str:
    """The LIVE state dir, spelled from ``$HOME`` and NOTHING ELSE (#149).

    The migrate guard used to compare ``STATE_DIR()`` against a default that
    read the same ``$OC_DEV_STATE``, so with that variable set they were equal
    BY CONSTRUCTION and the guard fired on any scratch dir — training operators
    to reach for the ``--live`` bypass to do a safe thing. ``$HOME`` stays in
    the expression deliberately: a test relocates it and exercises the guard
    without ever pointing it at the real record.
    """
    return os.path.join(os.path.expanduser("~"), ".opencrabs", "profiles",
                        "ops", "opencrabs-dev")


def is_live_state_dir(candidate: str) -> bool:
    try:
        d = os.path.realpath(candidate)
        live = os.path.realpath(live_state_dir())
    except OSError:
        return False
    return bool(d) and d == live


def skill_dir() -> str:
    """``$OC_SKILL_DIR`` or the tree this module lives in (bash ``SKILL_DIR``)."""
    env = os.environ.get("OC_SKILL_DIR")
    if env:
        return env
    tools = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(tools)


def is_git_repo(path: str) -> bool:
    """``git rev-parse --git-dir`` — answers TRUE for a LINKED WORKTREE (factory #70).

    ``[ -d "$sd/.git" ]`` answered FALSE there, because in a worktree ``.git``
    is a small ASCII FILE holding ``gitdir: …``. Every site that read it that
    way silently no-opped: commits deferred, pushes dropped, the stray-guard
    went INERT.
    """
    try:
        # child_process, not subprocess.run: this probe is the sort of thing a
        # caller reaches for from inside a locked helper, and #641 must be a
        # refusal there rather than an inherited fd.
        return child_process(["git", "-C", path, "rev-parse", "--git-dir"],
                             capture_output=True).returncode == 0
    except (OSError, RuntimeError):
        return False


# ---------------------------------------------------------------------------
# jq-compatible rendering
#
# The read verbs must stay BYTE-identical to the bash tool, and the bash tool
# renders through jq. So the handful of jq output forms those verbs use are
# reimplemented here rather than approximated with ``json.dumps`` defaults:
#
#   ``jq -c``      compact, no spaces, keys in insertion order, UTF-8 raw
#   ``jq``         two-space indent, ``": "`` separator, trailing newline
#   ``@tsv``       tab-joined with \\t \\n \\r \\\\ escaped
#   ``tostring``   strings as-is; everything else as its compact JSON
#
# NUMBERS: ints are exact. Floats use the shortest round-trip form with jq's
# exponent spelling (``1E+300``, ``1E-7``). jq 1.7 additionally PRESERVES the
# source literal's digits (``3.0e5`` prints as ``3.0E+5``), which is not
# reproducible without literal tracking; no ledger field is a float, so this
# cannot change a read verb's output today. Recorded rather than hidden.
# ---------------------------------------------------------------------------
def _fmt_number(value) -> str:
    if isinstance(value, bool):                      # bool is an int subclass
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        # jq has no JSON spelling for these and prints null.
        return "null"
    if f == 0.0:
        # jq prints -0 for a negative zero literal; a computed 0.0 is 0.
        return "-0" if str(f)[0] == "-" else "0"
    text = repr(f)
    if "e" in text or "E" in text:
        mantissa, _, exponent = text.partition("e")
        if mantissa.endswith(".0"):
            mantissa = mantissa[:-2]
        sign = "-" if exponent.startswith("-") else "+"
        digits = exponent.lstrip("+-").lstrip("0") or "0"
        return "%sE%s%s" % (mantissa, sign, digits)
    return text


def _fmt_string(value: str) -> str:
    # json.dumps already matches jq for the escapes jq emits (\b \f \n \r \t
    # \" \\ and \u00XX for the remaining control characters) and leaves
    # non-ASCII raw with ensure_ascii=False. jq escapes DEL? No — it emits it
    # raw, as Python does.
    return json.dumps(value, ensure_ascii=False)


def dumps_compact(value) -> str:
    """``jq -c``."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _fmt_number(value)
    if isinstance(value, str):
        return _fmt_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(dumps_compact(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            "%s:%s" % (_fmt_string(str(k)), dumps_compact(v))
            for k, v in value.items()) + "}"
    raise JqError("cannot serialise %r" % (type(value).__name__,))


def dumps_pretty(value, indent: int = 0) -> str:
    """``jq`` default output (two spaces, ``": "``, one value per line)."""
    pad = "  " * indent
    inner = "  " * (indent + 1)
    if isinstance(value, list):
        if not value:
            return "[]"
        body = ",\n".join(inner + dumps_pretty(v, indent + 1) for v in value)
        return "[\n" + body + "\n" + pad + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        body = ",\n".join(
            inner + _fmt_string(str(k)) + ": " + dumps_pretty(v, indent + 1)
            for k, v in value.items())
        return "{\n" + body + "\n" + pad + "}"
    return dumps_compact(value)


def to_string(value) -> str:
    """jq ``tostring``: a string stays itself, everything else is compact JSON."""
    if isinstance(value, str):
        return value
    return dumps_compact(value)


_TSV_ESCAPES = (("\\", "\\\\"), ("\t", "\\t"), ("\n", "\\n"), ("\r", "\\r"))


def tsv_field(value) -> str:
    text = to_string(value)
    for raw, escaped in _TSV_ESCAPES:
        text = text.replace(raw, escaped)
    return text


def tsv_row(values) -> str:
    """jq ``@tsv`` on a list."""
    return "\t".join(tsv_field(v) for v in values)


def alt(obj, *keys):
    """jq's ``//`` chain: the first key whose value is neither null nor false.

    Returns ``None`` when every key is absent/null/false. Note the distinction
    jq makes and Python's ``or`` does not: ``0`` and ``""`` are KEPT by ``//``
    (only ``null`` and ``false`` fall through), which is why this cannot be
    written as ``obj.get(a) or obj.get(b)``.
    """
    for key in keys:
        if not isinstance(obj, dict):
            raise JqError('Cannot index %s with string "%s"'
                          % (_jq_type(obj), key))
        if key in obj:
            value = obj[key]
            if value is not None and value is not False:
                return value
    return None


def _jq_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    return "object"


def index(obj, key):
    """jq ``.key`` — raises on a non-object, exactly as jq does."""
    if not isinstance(obj, dict):
        raise JqError('Cannot index %s with string "%s"'
                      % (_jq_type(obj), key))
    return obj.get(key)


# ---------------------------------------------------------------------------
# the ONE reader
# ---------------------------------------------------------------------------
_JSON_DECODER = json.JSONDecoder()


def _parse_stream(text: str, path: str):
    """Parse a JSON *stream* the way ``jq`` does, and report a bad token's line.

    Line-based reading is NOT equivalent: jq parses a stream of values, so a
    pretty-printed record still loads and a whitespace-only line is skipped.
    ``raw_decode`` over the whole text reproduces both, and lets the error name
    the line the way jq's own "at line N" does.
    """
    values = []
    pos = 0
    end = len(text)
    while pos < end:
        # skip inter-value whitespace (jq skips blank lines silently)
        while pos < end and text[pos] in " \t\r\n":
            pos += 1
        if pos >= end:
            break
        try:
            value, pos = _JSON_DECODER.raw_decode(text, pos)
        except ValueError as exc:
            line = text.count("\n", 0, pos) + 1
            col = pos - (text.rfind("\n", 0, pos) + 1) + 1
            raise LedgerError(
                RC_REFUSED,
                "ledger_load REFUSED — malformed JSONL in %s. A partial read "
                "would make a corrupt row look like a missing event (a false "
                "'no claim'): jq: parse error: %s at line %d, column %d"
                % (path, exc.msg if hasattr(exc, "msg") else str(exc),
                   line, col))
        values.append(value)
    return values


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()


def _load_json_file(path: str, what: str):
    try:
        text = _read_text(path)
    except OSError as exc:
        raise LedgerError(RC_REFUSED, "%s: cannot read %s: %s"
                          % (what, path, exc.strerror or exc))
    try:
        return json.loads(text)
    except ValueError as exc:
        raise LedgerError(RC_REFUSED,
                          "%s: %s is not valid JSON: %s" % (what, path, exc))


def load_ledger(ledger: str) -> dict:
    """Emit the UNIFIED dict ``{…workers, events: [...]}`` — the ONE reader.

    Two modes, one contract:

    * JSONL (``events.jsonl`` present): events from the record, everything
      else from ``workers.json``. A MALFORMED LINE RAISES rc 3 with its line
      number and is NEVER SKIPPED — "a skipped line turns a corrupt row into a
      MISSING row, and every closure and dispatch predicate then reads 'no
      claim': a false green on exactly the surface this ledger exists to make
      honest" (spec trap 5).
    * LEGACY (no ``events.jsonl``): the compact file IS the ledger, returned
      as-is. Byte-identical to the pre-#149 path, which is what keeps every
      legacy fixture working.

    ``-e`` semantics are reproduced too: the bash validates with
    ``jq -e -c .``, whose exit status follows the LAST value, so an EMPTY
    record (rc 4 from jq) and a record whose last value is ``null``/``false``
    (rc 1) are both REFUSALS, not clean reads.
    """
    ev = events_path(ledger)
    if not os.path.isfile(ev):
        return _load_json_file(ledger, "ledger_load")

    values = _parse_stream(_read_text(ev), ev)
    if not values:
        raise LedgerError(
            RC_REFUSED,
            "ledger_load REFUSED — malformed JSONL in %s. A partial read would "
            "make a corrupt row look like a missing event (a false 'no claim'): "
            "the record holds no JSON value" % ev)
    if values[-1] is None or values[-1] is False:
        raise LedgerError(
            RC_REFUSED,
            "ledger_load REFUSED — malformed JSONL in %s. A partial read would "
            "make a corrupt row look like a missing event (a false 'no claim'): "
            "the record's last value is %s, which jq -e treats as a refusal"
            % (ev, to_string(values[-1])))

    unified = {}
    wf = workers_path(ledger)
    if os.path.isfile(wf):
        workers = _load_json_file(wf, "ledger_load")
        if workers is None or workers is False:
            workers = {}
        if not isinstance(workers, dict):
            # jq: "array and object cannot be added"
            raise LedgerError(
                RC_REFUSED,
                "ledger_load REFUSED — %s holds a %s, and the unified ledger "
                "is an object (jq: %s and object cannot be added)"
                % (wf, _jq_type(workers), _jq_type(workers)))
        unified.update(workers)
    unified["events"] = values
    return unified


def max_n(ledger: str) -> int:
    """``max(events[].n)+1`` is computed from THIS — never from a derived view.

    #149: in JSONL mode ``n`` is allocated from the RECORD. The view is
    gitignored once cut over, so a fresh clone has none, and a ``max_n`` that
    read a missing view would answer 0 and hand the next writer ``n=1``,
    colliding with every live row.

    Nulls stay null (spec trap 1): ``.n // 0`` ignores them for the MAX but
    never rewrites them. A record that will not parse answers 0 here — that is
    the bash's own ``2>/dev/null || echo 0`` arm, kept because ``max_n`` runs
    INSIDE the lock after ``ledger_ok`` has already refused a corrupt record;
    the swallow cannot turn a corrupt row into a missing one.
    """
    if jsonl_mode(ledger):
        ev = events_path(ledger)
        try:
            values = _parse_stream(_read_text(ev), ev)
        except (LedgerError, OSError):
            return 0
        numbers = []
        for row in values:
            value = row.get("n") if isinstance(row, dict) else None
            numbers.append(0 if value is None or value is False else value)
        numbers = [v for v in numbers if isinstance(v, (int, float))
                   and not isinstance(v, bool)]
        return int(max(numbers)) if numbers else 0

    ledger_obj = _load_json_file(ledger, "max_n")
    events = ledger_obj.get("events") if isinstance(ledger_obj, dict) else None
    numbers = []
    for row in (events or []):
        value = row.get("n") if isinstance(row, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numbers.append(value)
    return int(max(numbers)) if numbers else 0


def ledger_ok(ledger: str) -> bool:
    """The cheap "is the ledger readable" predicate every verb gates on.

    Mode-aware (#149): in JSONL mode it validates the RECORD, never the
    derived view — a verb that validated the view died rc 3 for a ledger that
    was perfectly readable.
    """
    if jsonl_mode(ledger):
        try:
            load_ledger(ledger)
            return True
        except (LedgerError, OSError, JqError):
            return False
    if not os.path.isfile(ledger):
        return False
    try:
        _load_json_file(ledger, "ledger_ok")
        return True
    except LedgerError:
        return False


# ---------------------------------------------------------------------------
# temp hygiene (D2, #507)
# ---------------------------------------------------------------------------
TMP_PREFIX = ".ledger."
_TMP_MAX_AGE_MIN = lambda: int(os.environ.get("OC_LEDGER_TMP_MAX_AGE", "60"))


def sweep_stale_temps(directory: str, keep: str = "") -> int:
    """Reap ``.ledger.*`` corpses from a SIGKILL, and NEVER a live temp.

    Measured (#507): a 3.0 MB ``.ledger.IW5b9i`` sat for 3 days, because the
    daemon SIGKILLs in-flight children on every restart (9 starts / 9 stops on
    2026-09-21) and no trap can catch SIGKILL. Every atomic-write caller runs
    under the lock, so no live temp can be in flight when this runs; the AGE
    gate is belt-and-braces for a future caller that is not under the lock, and
    it is what stops this from becoming a blanket ``rm .ledger.*`` that could
    reap a temp mid-write.

    Best-effort by construction: never raises, never fails the caller.
    """
    swept = 0
    try:
        names = os.listdir(directory)
    except OSError:
        return 0
    now = time.time()
    max_age = _TMP_MAX_AGE_MIN() * 60
    for name in names:
        if not name.startswith(TMP_PREFIX):
            continue
        path = os.path.join(directory, name)
        if keep and path == keep:
            continue
        try:
            if now - os.stat(path).st_mtime < max_age:
                continue
            os.unlink(path)
            swept += 1
        except OSError:
            continue
    return swept


def _fsync_path(path: str) -> None:
    """fsync a FILE (bash ``sync -f``), falling back to a full sync.

    Never fatal: the row is already written, and a box that cannot fsync has
    bigger problems than this call's rc.
    """
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _atomic_replace(path: str, data: bytes, tmp_dir: str) -> None:
    """temp + rename in the SAME directory, so a reader never sees a truncation."""
    fd, tmp = tempfile.mkstemp(prefix=TMP_PREFIX, dir=tmp_dir)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# the ONE writer
# ---------------------------------------------------------------------------
def atomic_write(ledger: str, transform, *, fsync: bool = True) -> dict:
    """Load unified -> apply ``transform`` -> split back. The ONE writer.

    ``transform`` receives a private deep copy of the unified dict and returns
    either a replacement dict or ``None`` (meaning "I mutated the copy"). This
    is the Python shape of the bash's ``atomic_jq`` jq program: six call sites
    append events and several mutate ``.workers``, and none of them learns a
    second closure/dispatch predicate.

    SPLIT RULES (each is a measured requirement, not a preference):

    * **TRUE APPEND** when the transform pushed exactly ONE event onto the END
      — prefix equality: ``len(new) == len(old) + 1`` and ``new[:len(old)] ==
      old``. One ~200-byte line is appended and fsynced; ``events.jsonl`` is
      never rewritten and ``workers.json`` is never touched (an event-only
      mutation does not change non-event state; a transform that also bumped
      ``.updated_at`` has that dropped, as #177 does).
    * **WHOLESALE REWRITE** otherwise: the record is re-emitted to a temp and
      renamed, so no reader ever sees truncated JSON (spec trap 6).
    * ``workers.json`` is rewritten ONLY when it actually changed (``cmp`` in
      the bash; byte comparison here).

    rc 3 on a load or transform error, rc 4 on a write failure, and the LIVE
    LEDGER IS UNTOUCHED on every failure path — the temp is removed and the
    original files are never opened for writing until a complete new value
    exists.
    """
    sd = state_dir(ledger)
    sweep_stale_temps(sd)

    if not jsonl_mode(ledger):
        return _atomic_write_legacy(ledger, transform, fsync=fsync)

    try:
        before = load_ledger(ledger)
    except LedgerError as exc:
        raise LedgerError(RC_REFUSED,
                          "atomic_write load failed (rc=3) — the ledger was "
                          "NOT modified: %s" % exc.message) from exc
    except OSError as exc:
        raise LedgerError(RC_REFUSED,
                          "atomic_write load failed (rc=3) — the ledger was "
                          "NOT modified: %s" % exc) from exc

    old_events = list(before.get("events") or [])
    working = _deep_copy(before)
    try:
        result = transform(working)
    except LedgerError:
        raise
    except Exception as exc:                      # noqa: BLE001 - mirrors jq rc 3
        raise LedgerError(RC_REFUSED,
                          "atomic_write failed (rc=3) — the ledger was NOT "
                          "modified: %s" % (exc or "<no message>")) from exc
    after = working if result is None else result
    if not isinstance(after, dict):
        raise LedgerError(RC_REFUSED,
                          "atomic_write failed (rc=3) — the ledger was NOT "
                          "modified: the transform produced a %s, not an "
                          "object" % _jq_type(after))

    new_events = after.get("events")
    if new_events is None:
        new_events = []
    if not isinstance(new_events, list):
        raise LedgerError(RC_REFUSED,
                          "atomic_write failed (rc=3) — the ledger was NOT "
                          "modified: .events is a %s, not an array"
                          % _jq_type(new_events))

    ev = events_path(ledger)
    appended = (len(new_events) == len(old_events) + 1
                and new_events[:len(old_events)] == old_events)

    if appended:
        try:
            line = dumps_compact(new_events[-1]) + "\n"
            with open(ev, "a", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(line)
                fh.flush()
                if fsync:
                    os.fsync(fh.fileno())
        except OSError as exc:
            raise LedgerError(RC_IO,
                              "atomic_write append failed (rc=4) — the ledger "
                              "row was NOT written: %s" % exc) from exc
        if fsync:
            _fsync_path(ev)
        return after

    # wholesale: the record first, then workers.json only if it changed
    body = "".join(dumps_compact(row) + "\n" for row in new_events)
    try:
        _atomic_replace(ev, body.encode("utf-8", "surrogateescape"), sd)
    except OSError as exc:
        raise LedgerError(RC_IO,
                          "atomic_write could not rewrite %s (rc=4) — the "
                          "ledger was NOT modified: %s" % (ev, exc)) from exc

    workers = {k: v for k, v in after.items() if k != "events"}
    wf = workers_path(ledger)
    try:
        payload = dumps_compact(workers) + "\n"
    except JqError as exc:
        raise LedgerError(RC_IO, "atomic_write could not serialise workers "
                                 "(rc=4): %s" % exc) from exc
    try:
        current = None
        if os.path.isfile(wf):
            current = _read_text(wf)
        if current != payload:
            _atomic_replace(wf, payload.encode("utf-8", "surrogateescape"), sd)
    except OSError as exc:
        # The record already landed; a workers.json write failure is still an
        # io-fail for the caller, and it names what did land so nobody
        # re-derives the row.
        raise LedgerError(RC_IO,
                          "atomic_write wrote %s but could not rewrite %s "
                          "(rc=4): %s" % (ev, wf, exc)) from exc
    return after


def _atomic_write_legacy(ledger: str, transform, *, fsync: bool = True) -> dict:
    """The pre-#149 path: one compact file, transform, validate, rename.

    #570: jq's own message must survive. ``2>/dev/null`` once turned a clear
    type error ("string and array cannot be added") into a bare rc=3 that was
    indistinguishable from a bad uuid or a missing ledger, and Triage spent
    several turns re-deriving the cause. The ledger is still UNTOUCHED on
    failure; only the SILENCE is removed.
    """
    sd = state_dir(ledger)
    try:
        before = _load_json_file(ledger, "atomic_write")
    except LedgerError as exc:
        raise LedgerError(RC_REFUSED,
                          "atomic_write load failed (rc=3) — the ledger was "
                          "NOT modified: %s" % exc.message) from exc

    working = _deep_copy(before)
    try:
        result = transform(working)
    except LedgerError:
        raise
    except Exception as exc:                      # noqa: BLE001
        raise LedgerError(RC_REFUSED,
                          "atomic_write failed (rc=3) — the ledger was NOT "
                          "modified: %s" % (exc or "<no message>")) from exc
    after = working if result is None else result

    try:
        payload = dumps_compact(after) + "\n"
    except JqError as exc:
        raise LedgerError(RC_REFUSED,
                          "atomic_write failed (rc=3) — the ledger was NOT "
                          "modified: %s" % exc) from exc
    try:
        _atomic_replace(ledger, payload.encode("utf-8", "surrogateescape"), sd)
    except OSError as exc:
        raise LedgerError(RC_IO,
                          "atomic_write could not replace %s (rc=4) — the "
                          "ledger was NOT modified: %s" % (ledger, exc)) from exc
    return after


def _deep_copy(value):
    """A transform gets a PRIVATE copy, so a failure cannot half-mutate the live dict."""
    if isinstance(value, dict):
        return {k: _deep_copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deep_copy(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# the fleet lock
# ---------------------------------------------------------------------------
# #619/#95: the waiter budget must EXCEED the holder's worst case, or a normal
# ship storm starves concurrent appends and DROPS JOURNAL ROWS SILENTLY. Since
# #95 the pushes no longer run under this lock, so the holder is no longer
# bounded by the network: what remains inside is ONE read+write over a
# multi-MB ledger. Measured 2026-11-19 on the live 6,381,816-byte ledger:
# 0.45 s / 0.51 s / 0.57 s over three passes. The budget is therefore one
# bounded I/O (_OC_PUSH_TIMEOUT stays the fleet's unit) plus 30 s of slack.
# Keeping the old inflated 2x-push form would leave every waiter asleep 90 s
# for work that now takes half a second — #81's complaint from the other side.
PUSH_TIMEOUT_DEFAULT = 30
LOCK_SLACK_S = 30


def push_timeout() -> int:
    raw = os.environ.get("OC_LEDGER_PUSH_TIMEOUT", "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return PUSH_TIMEOUT_DEFAULT


def lock_worst_case() -> int:
    """The holder's own worst case, DISCLOSED in every timeout refusal."""
    return push_timeout() + LOCK_SLACK_S


def lock_budget() -> int:
    """``$OC_LEDGER_LOCK_WAIT``, defaulting to the derived worst case."""
    raw = os.environ.get("OC_LEDGER_LOCK_WAIT", "")
    if raw == "":
        return lock_worst_case()
    try:
        return int(raw)
    except ValueError:
        return lock_worst_case()


# --- the #641 guard, made structural ---------------------------------------
# bash's `9>&-` exists because bash does not set close-on-exec on fds > 2, so a
# child spawned under the lock INHERITS the locked fd and flock is released
# only when the LAST fd on the open file description closes. Python's
# subprocess defaults to close_fds=True, which would hide the hazard instead of
# removing it: a caller that passes close_fds=False, or a fork() that outlives
# us, re-opens it. So this module does BOTH:
#   * opens the lock fd non-inheritable (O_CLOEXEC) and
#   * REFUSES a child spawn while the lock is held (child_process below), which
#     turns the #641 class into a loud programming error instead of a 19-minute
#     fleet stall.
_IN_LOCK = 0
_GIT_PENDING: list[str] = []


def in_lock() -> bool:
    return _IN_LOCK > 0


def child_process(cmd, **kwargs):
    """``subprocess.run`` for anything that may be called under the lock.

    Raises :class:`RuntimeError` when the lock is held. That is the Python
    equivalent of ``9>&-`` and it is deliberately a REFUSAL rather than a
    silent fd-close: a child that outlives its parent is exactly what held the
    fleet lock 19+ minutes (#641), and only the caller can decide to move the
    work outside the lock.
    """
    if in_lock():
        raise RuntimeError(
            "#641: refusing to spawn %r while holding the fleet ledger lock — a "
            "child that inherits the lock fd keeps flock held until the LAST fd "
            "closes (measured: `git gc --auto` children held it 19+ minutes). "
            "Do the pure-Python work under the lock, release, then run the "
            "child (see flush_git_tail)." % (cmd,))
    return subprocess.run(cmd, **kwargs)


class _LedgerLock:
    """``flock(LOCK_EX)`` on ``$LEDGER.lock``, with the derived budget."""

    def __init__(self, ledger: str, budget: int | None = None,
                 poll_s: float = 0.02):
        self.path = ledger + ".lock"
        self.budget = lock_budget() if budget is None else int(budget)
        self.poll_s = poll_s
        self.fd: int | None = None

    def __enter__(self):
        global _IN_LOCK
        try:
            # O_CLOEXEC via the non-inheritable flag: belt to child_process's
            # braces, so even a fork() cannot carry the fd into a grandchild.
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        except OSError as exc:
            raise LedgerError(RC_IO,
                              "cannot open %s: %s" % (self.path, exc.strerror
                                                      or exc)) from exc
        try:
            os.set_inheritable(fd, False)
        except OSError:
            pass
        deadline = time.monotonic() + self.budget
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EACCES,
                                     errno.EWOULDBLOCK):
                    os.close(fd)
                    raise LedgerError(RC_IO, "flock failed on %s: %s"
                                      % (self.path, exc)) from exc
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise LockTimeout(self.timeout_message())
                time.sleep(self.poll_s)
        self.fd = fd
        _IN_LOCK += 1
        return self

    def timeout_message(self) -> str:
        return ("lock timeout on %s after %ds (own worst case %ds = one bounded "
                "I/O %ds + %ds; git does NOT run under this lock since #95, so "
                "a timeout means real contention, a pre-#641 inherited fd, or a "
                "holder stuck on I/O — raise with OC_LEDGER_LOCK_WAIT)"
                % (self.path, self.budget, lock_worst_case(), push_timeout(),
                   LOCK_SLACK_S))

    def __exit__(self, exc_type, exc, tb):
        global _IN_LOCK
        if _IN_LOCK > 0:
            _IN_LOCK -= 1
        fd, self.fd = self.fd, None
        if fd is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(fd)
            except OSError:
                pass
        return False


def with_lock(ledger: str, fn, *args, **kwargs):
    """Run ``fn(*args)`` with the exclusive fleet lock held, then the git tail.

    THE ORDER IS THE CONTRACT (#95): lock -> pure-Python work -> release ->
    git tail. The tail runs strictly AFTER the release, so a slow or saturated
    disk delays the commit but can never fail the append and can never hold
    the fleet lock while it waits.

    A lock timeout is rc 4 and names the budget and the knob
    (``OC_LEDGER_LOCK_WAIT``), because a caller who cannot tell "real
    contention" from "a stuck holder" reaches for the wrong remedy.
    """
    with _LedgerLock(ledger):
        result = fn(*args, **kwargs)
    flush_git_tail(ledger)
    return result


# ---------------------------------------------------------------------------
# the deferred git tail (#95)
# ---------------------------------------------------------------------------
def git_state_commit(ledger: str, message: str) -> None:
    """Commit the state repo — DEFERRED when called under the ledger lock.

    Under the lock this only QUEUES the message; the commit happens in
    :func:`flush_git_tail` after the release. Outside the lock it runs now
    (that is the path a non-mutating caller or a test uses).
    """
    if in_lock():
        _GIT_PENDING.append(message)
        return
    _git_state_commit_now(ledger, message)


def pending_git_messages() -> list[str]:
    return list(_GIT_PENDING)


def flush_git_tail(ledger: str, *, wait: int | None = None) -> None:
    """Run the queued state commits on their OWN lock file. NEVER FATAL.

    Its own ``$LEDGER.git-tail.lock`` keeps the tail serialised (two concurrent
    appends still commit in a defined order) while nobody waits on it to keep
    their row. Every failure path here is a WARNING naming the safety of the
    already-durable row, because "the append landed" and "the commit landed"
    are different claims and only the first is this function's business.
    """
    global _GIT_PENDING
    if not _GIT_PENDING:
        return
    messages = list(_GIT_PENDING)
    count = len(messages)
    if wait is None:
        try:
            wait = int(os.environ.get("OC_LEDGER_GIT_TAIL_WAIT", "60"))
        except ValueError:
            wait = 60

    lock_path = ledger + ".git-tail.lock"
    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    except OSError:
        _warn("git-tail: cannot open %s — %d state commit(s) deferred; THE "
              "LEDGER ROW IS SAFE (already appended and fsynced)"
              % (lock_path, count))
        _GIT_PENDING = []
        return
    try:
        os.set_inheritable(fd, False)
    except OSError:
        pass
    deadline = time.monotonic() + wait
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EACCES,
                                     errno.EWOULDBLOCK):
                    raise
                if time.monotonic() >= deadline:
                    _warn("git-tail: state-repo tail busy after %ds — %d state "
                          "commit(s) deferred; THE LEDGER ROW IS SAFE (already "
                          "appended and fsynced). Raise with "
                          "OC_LEDGER_GIT_TAIL_WAIT." % (wait, count))
                    return
                time.sleep(0.02)
        try:
            for message in messages:
                _git_state_commit_now(ledger, message)
        finally:
            _GIT_PENDING = []
    except OSError:
        _warn("git-tail: tail lock failed — %d state commit(s) deferred; THE "
              "LEDGER ROW IS SAFE (already appended and fsynced)" % count)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass


def _warn(message: str) -> None:
    sys.stderr.write("%s: %s\n" % (PROG, message))
    try:
        sys.stderr.flush()
    except OSError:
        pass


def _git_state_commit_now(ledger: str, message: str) -> None:
    """The commit itself. Never fatal, and never raises on a git failure.

    #149: in JSONL mode the RECORD is what gets committed. Staging only
    ``basename $LEDGER`` would stage the gitignored view and commit NOTHING — a
    state commit that reports ok with an empty tree, the same silent-success
    class as a guard that cannot see its target.
    """
    sd = state_dir(ledger)
    if not is_git_repo(sd):
        return
    if jsonl_mode(ledger):
        stage = [EVENTS_NAME, WORKERS_NAME]
    else:
        stage = [os.path.basename(ledger)]
    try:
        staged = child_process(["git", "-C", sd, "add", "--"] + stage,
                               capture_output=True).returncode == 0
        committed = staged and child_process(
            ["git", "-C", sd, "commit", "-q", "-m", message],
            capture_output=True).returncode == 0
    except (OSError, RuntimeError):
        committed = False
    if committed:
        # n=1744 hygiene: echo the auto-commit sha — a caller claiming "state
        # commit ok" without a sha in hand has nothing to verify against.
        try:
            sha = child_process(["git", "-C", sd, "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        except (OSError, RuntimeError):
            sha = "unknown"
        sys.stdout.write("git: state commit ok (%s) sha=%s\n" % (message, sha))
        try:
            sys.stdout.flush()
        except OSError:
            pass
    else:
        _warn("commit-lag: state commit deferred — %s" % message)
    # #177: the TRACKED-namespace sweep no longer runs on every stamp (that is
    # `commit-pending --bundle`, phase 3). push_backlog_if_due stays here so a
    # stamp still has a path off-box when the backlog is due.
    push_backlog_if_due(sd, "state")
    push_backlog_if_due(skill_dir(), "skill")


# ---------------------------------------------------------------------------
# opportunistic backlog push (durability, #524)
#
# Every ledger mutation COMMITS via git_state_commit; nothing pushed, so off-box
# durability rode irregular bundle/sync runs only. Measured 2026-09-23 in the
# state repo: 121 commits vs 13 pushes, and an 11-commit / 2h53m29s unpushed
# gap. A commit that never leaves the box is not a recovery point.
#
# Both arms live in the DEFERRED tail (never under the fleet lock since #95), so
# a hung network push cannot stall a lane's stamp. Posture stays the same as
# the bash: durability, never a gate.
# ---------------------------------------------------------------------------
def _push_min() -> int:
    return int(os.environ.get("OC_LEDGER_PUSH_MIN", "10") or 10)


def _push_max_age() -> int:
    return int(os.environ.get("OC_LEDGER_PUSH_MAX_AGE", "1800") or 1800)


def _git_out(cmd, timeout=None):
    """(rc, text) for a git probe; (1, "") when git cannot be run at all."""
    try:
        proc = child_process(cmd, capture_output=True, text=True,
                             timeout=timeout)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return 1, ""
    return proc.returncode, (proc.stdout or "").strip()


def push_mirror(directory: str, name: str) -> None:
    """Off-box durability tail step. WARNs, never fails the caller (v0.4.50)."""
    if not is_git_repo(directory):
        return
    rc, origin = _git_out(["git", "-C", directory, "remote", "get-url", "origin"])
    if rc != 0 or not origin:
        return
    bound = push_timeout()
    # (#655) Act on the remote's REAL state. Without the fetch the tool both
    # measures and pushes against a stale @{u}: measured, a stale tracking ref
    # reads "ahead 1" while the truth is "ahead 1, behind 1", the push is
    # rejected non-fast-forward, and every later run WARNs the same way forever.
    _, branch = _git_out(["git", "-C", directory, "symbolic-ref", "-q",
                          "--short", "HEAD"])
    if branch:
        try:
            child_process(["git", "-C", directory, "fetch", "-q", "origin",
                           branch], capture_output=True, timeout=bound)
        except (OSError, RuntimeError, subprocess.SubprocessError):
            pass
    try:
        proc = child_process(
            ["git", "-C", directory, "push", "-q", "origin", "HEAD",
             "+refs/tags/v0.4.*:refs/tags/v0.4.*"],
            capture_output=True, text=True, timeout=bound)
        rc, out = proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        rc, out = 1, str(exc)
    if rc == 0:
        sys.stdout.write("mirror: %s pushed to %s\n" % (name, origin))
        return
    rel = ""
    if ("non-fast-forward" in out or "fetch first" in out
            or "remote contains work" in out):
        _, counts = _git_out(["git", "-C", directory, "rev-list", "--left-right",
                              "--count", "@{u}...HEAD"])
        if counts and "\t" in counts:
            behind, ahead = counts.split("\t", 1)
            rel = " [ahead %s behind %s]" % (ahead, behind)
    _warn("WARN: mirror push failed for %s rc=%d (local unaffected)%s: %s"
          % (name, rc, rel, out))


def push_backlog_if_due(directory: str, name: str) -> None:
    """Push ONLY when the local backlog says so. Never fatal.

    Two arms, because the commit arm structurally cannot bound the SLOW regime:
    a quiet box can sit under the threshold indefinitely, so the age arm fires
    on the newest unpushed commit. The measurement is local (no network), so
    the common case costs one rev-list and returns before push_mirror.
    """
    if not is_git_repo(directory):
        return
    rc, origin = _git_out(["git", "-C", directory, "remote", "get-url", "origin"])
    if rc != 0 or not origin:
        return
    rc, _ = _git_out(["git", "-C", directory, "rev-parse", "--verify", "-q",
                      "@{u}"])
    if rc != 0:
        return
    rc, count = _git_out(["git", "-C", directory, "rev-list", "--count",
                          "@{u}..HEAD"])
    if rc != 0 or not count.isdigit():
        return
    backlog = int(count)
    if backlog <= 0:
        return
    minimum = _push_min()
    if backlog >= minimum:
        sys.stdout.write("mirror-due: %s backlog=%d commit(s) (>= %d) — pushing\n"
                         % (name, backlog, minimum))
    else:
        rc, newest = _git_out(["git", "-C", directory, "log", "-1",
                               "--format=%ct", "@{u}..HEAD"])
        if rc != 0 or not newest.isdigit():
            return
        age = int(time.time()) - int(newest)
        if age < _push_max_age():
            return
        sys.stdout.write("mirror-due: %s backlog=%d commit(s), newest %ds old "
                         "(>= %ds) — pushing\n"
                         % (name, backlog, age, _push_max_age()))
    push_mirror(directory, name)
