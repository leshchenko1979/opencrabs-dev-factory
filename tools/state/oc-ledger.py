#!/usr/bin/env python3
# =============================================================================
# oc-ledger (python) — the ONE sanctioned write path for the workers ledger.
#
# PORT STATUS (factory #204).
#   PHASE 2 — read verbs (DONE): ok · law-digest · check-version · cadence ·
#     events · tail · workers · worker · roster · claims · lessons ·
#     duplicates · mode
#   PHASE 3 — write verbs (IN PROGRESS): stamp · fixture landed; sync · ack ·
#     enroll · promote · retire · commit-pending · confirm · migrate · claim ·
#     claim-ref · sweep-closed-claims still refuse rc 2 by name.
#
# The bash tool at tools/state/oc-ledger is UNCHANGED and remains the live
# write path until the flip. This file is additive: it shares the store + lock
# layer in tools/lib/ledger_core.py, and every verb here is required to be
# OUTPUT-IDENTICAL to its bash counterpart on the same fixture — that identity
# is the gate, not a nicety. Where the bash emits JSON, so does this; where it
# emits TSV or prose, the bytes match.
#
# rc vocabulary (tools/docs/RC-CONTRACT.md) — the SAME numbers, never
# renumbered, because every lane in the fleet keys on them:
#   0 ok · 1 verdict (NO-MATCH / DRIFT / FIRE) · 2 usage ·
#   3 parse-or-load refused · 4 write-fail or lock timeout
#
# STDLIB ONLY, extensionless-sibling precedent: tools/state/oc-questions.
# =============================================================================

from __future__ import annotations

import datetime
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.dirname(_HERE)
for _path in (os.path.join(_TOOLS, "lib"), _TOOLS):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# No .pyc beside the module: the shared checkout must stay byte-identical, and
# a stale __pycache__ for the file that governs claim closure is a hazard not
# worth the import speedup (same rule oc_claims' bash caller states).
sys.dont_write_bytecode = True

import ledger_core as L  # noqa: E402

PROG = "oc-ledger"

# The bash tool's two verb renderings, kept SEPARATE because they differ: the
# `--help` line pipes them in one order, the unknown-verb refusal pipes them in
# another, and `--verbs` prints a third (space-separated, sweep-closed-claims
# included). Byte-identity is the gate, so all three are reproduced verbatim
# rather than derived from one tuple that would drift from the bash.
USAGE = ("usage: oc-ledger <stamp|fixture|sync|check-version|law-digest|cadence|"
         "ack|enroll|promote|retire|commit-pending|confirm|migrate|claim|"
         "claim-ref|claims|lessons|roster|events|tail|duplicates|mode|workers|"
         "worker|ok> | [selftest|--selftest]")

USAGE_VERBS = ("stamp|fixture|sync|check-version|law-digest|cadence|ack|enroll|"
               "promote|retire|commit-pending|confirm|migrate|claim|claim-ref|"
               "claims|lessons|roster|events|tail|duplicates|mode|workers|"
               "worker|ok")

VERBS_LINE = ("stamp fixture sync check-version law-digest cadence ack enroll "
              "promote retire commit-pending confirm migrate claim claim-ref "
              "claims sweep-closed-claims lessons roster events tail workers "
              "worker ok duplicates mode")

# The law a lane must re-read on a bump. The SET and the ALGORITHM live here
# (and in the bash) so `law-digest`, `check-version` and the sync stamp cannot
# disagree about what "the law" is. Order is load-bearing: it feeds the hash.
# Excluded deliberately: CHANGELOG.md (written by the bumper in the same act),
# registry/state (sync writes them), tools/docs/** and README.md (tool surface,
# a separate ownership carve-out). An ABSENT file hashes as the constant
# "ABSENT", so a rename or a deletion is a law change too.
LAW_FILES = (
    "SKILL.md", "editor.md", "editor-ship.md", "editor-smoke.md", "hq.md",
    "triage.md", "toolsmith.md", "harvest.md",
    "fleet-directives.md", "upstream-merge-runbook.md", "review-lenses.md",
    "session-notify.md", "environment.md", "s2-swap-journal-spec.md",
    "reference-glossary.md", "reference-tools.md",
)


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------
def die(rc: int, message: str):
    sys.stderr.write("%s: %s\n" % (PROG, message))
    sys.stderr.flush()
    raise SystemExit(rc)


def _refuse(exc) -> None:
    """Print a store-layer refusal's message VERBATIM and exit with its rc."""
    sys.stderr.write("%s: %s\n" % (PROG, exc.message))
    sys.stderr.flush()
    raise SystemExit(exc.rc)


def out(text: str) -> None:
    sys.stdout.write(text)


def outln(text: str = "") -> None:
    sys.stdout.write(text + "\n")


def errln(text: str = "") -> None:
    sys.stderr.write(text + "\n")


# ---------------------------------------------------------------------------
# global argument parsing (bash parse_global, oc-ledger:186)
# ---------------------------------------------------------------------------
def _dirname(path: str) -> str:
    """bash ``_oc_dirname``: trailing slashes collapsed, no slash -> "."."""
    while len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    if "/" not in path:
        return "."
    head = path.rsplit("/", 1)[0]
    return head or "/"


def resolve_ledger(explicit: str | None) -> str:
    """The ledger path, with the #177 basename remap applied.

    Callers may still pass ``workers.json`` or the retired view path. If a
    sibling ``events.jsonl`` exists it IS the record; a fixture that only has
    the compact file stays in legacy mode (JSONL mode is decided by
    ``events.jsonl`` being PRESENT, not by this path).
    """
    ledger = explicit or ""
    if not ledger:
        ledger = os.environ.get("OC_LEDGER", "")
    if not ledger:
        deploy = os.environ.get("OC_DEPLOY_STATE_DIR", "")
        if deploy:
            ledger = os.path.join(deploy, L.EVENTS_NAME)
    if not ledger:
        default = os.environ.get("OC_DEV_STATE", "") or os.path.join(
            os.path.expanduser("~"), ".opencrabs", "profiles", "ops",
            "opencrabs-dev")
        ledger = os.path.join(default, L.EVENTS_NAME)

    base = os.path.basename(ledger)
    if base == L.WORKERS_NAME:
        ledger = os.path.join(_dirname(ledger), L.EVENTS_NAME)
    elif base == L.LEGACY_NAME:
        sd = _dirname(ledger)
        sibling = os.path.join(sd, L.EVENTS_NAME)
        if not os.path.isfile(ledger) and os.path.isfile(sibling):
            ledger = sibling
    return ledger


def parse_global(argv):
    """(ledger, selftest, rest) — global flags consumed, subcommand left."""
    ledger = ""
    selftest = False
    args = list(argv)
    while args:
        head = args[0]
        if head == "--ledger":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "--ledger needs a path")
            ledger = args[1]
            args = args[2:]
        elif head in ("selftest", "--selftest"):
            selftest = True
            args = args[1:]
        else:
            break
    return resolve_ledger(ledger), selftest, args


def require_ledger(ledger: str, prefix: str = "") -> None:
    """``ledger_ok || die 3`` — the gate every read verb opens with."""
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "%sledger missing or unparseable: %s"
            % (prefix, ledger))


# ---------------------------------------------------------------------------
# law digest (single home for the SET and the ALGORITHM)
# ---------------------------------------------------------------------------
def law_digest() -> str:
    import hashlib
    lines = []
    root = L.skill_dir()
    for name in LAW_FILES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            digest = hashlib.sha256()
            try:
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        digest.update(chunk)
                value = digest.hexdigest()
            except OSError:
                value = "ABSENT"
        else:
            value = "ABSENT"
        lines.append("%s:%s\n" % (name, value))
    total = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
    return total


def law_digest_stamped(ledger: str) -> str:
    """The newest skill-bump row's ``law_digest``; "" when absent (pre-#47)."""
    try:
        unified = L.load_ledger(ledger)
    except (L.LedgerError, OSError):
        return ""
    last = None
    for row in (unified.get("events") or []):
        if isinstance(row, dict) and row.get("kind") == "skill-bump":
            last = row
    if last is None:
        return ""
    value = last.get("law_digest")
    return "" if value is None or value is False else L.to_string(value)


# ---------------------------------------------------------------------------
# small projections
# ---------------------------------------------------------------------------
def _unified(ledger: str):
    """``ledger_load`` as a value, with the bash's stderr passthrough."""
    try:
        return L.load_ledger(ledger)
    except L.LedgerError as exc:
        _refuse(exc)
    except OSError as exc:                       # pragma: no cover - io fault
        die(L.RC_REFUSED, "ledger_load failed: %s" % exc)


def _workers_docs(ledger: str, verb: str = "workers"):
    """``[(document, source_line)]`` — what a workers read opens, jq-stream-wise.

    Three shapes, and they are NOT interchangeable (each measured against the
    bash, because each one produced a real divergence the first time this file
    was written):

    * JSONL mode WITH ``workers.json``: ONE document — that file.
    * JSONL mode WITHOUT it: ``$LEDGER`` read as a jq STREAM, so a multi-row
      ``events.jsonl`` yields one document per row and each is projected
      independently. A ``workers`` read there prints one array PER ROW, which
      is what the bash prints; collapsing it to a single array would be a
      silent divergence (and on an EMPTY record the bash prints one blank line,
      not ``[]``).
    * Legacy mode: the compact file, one document.

    A record that will not parse is rc 3 with jq's own diagnostic printed
    first, exactly as the bash does (jq writes the parse error to stderr, then
    the verb dies rc 3 with "jq failed").
    """
    if L.jsonl_mode(ledger) and os.path.isfile(L.workers_path(ledger)):
        try:
            return [(json.loads(_read(L.workers_path(ledger))), 1)]
        except (ValueError, OSError):
            die(L.RC_REFUSED, "%s: ledger missing or unparseable: %s"
                % (verb, ledger))
    if not os.path.isfile(ledger):
        die(L.RC_REFUSED, "%s: ledger missing or unparseable: %s"
            % (verb, ledger))
    try:
        return L.parse_stream_lines(_read(ledger), ledger)
    except L.JqParseError as exc:
        errln(exc.jq_line)
        die(L.RC_REFUSED, "%s: jq failed — ledger unreadable or query error"
            % verb)
    except OSError:
        die(L.RC_REFUSED, "%s: ledger missing or unparseable: %s"
            % (verb, ledger))


def _workers_eval(ledger: str, docs, verb: str, uuid: str):
    """jq's own per-document evaluation of ``(.workers // [])``.

    Returns ``(outputs, rows)``: one projection per document jq could index,
    and their flattening. A document jq cannot index contributes NO output but
    prints its own error line, and the verb's exit status follows jq's, which
    is the status of the **LAST** document only:

    * ``good, bad, good`` -> rc 0, both arrays printed, one error on stderr.
    * ``good, bad``       -> rc 5, and the good array is DISCARDED.

    That last clause is the bash's, not jq's: ``out="$(jq …)" || die 3`` keeps
    nothing from a failed run, so partial output never escapes. Reproducing
    "any failure fails the verb" instead would break ``bad, good`` (rc 0) and
    reproducing "errors abort the scan" would lose the trailing documents.

    The uuid form is a different program — ``[.workers[]? | select(…)]`` — so a
    non-array ``.workers`` yields nothing there while the plain form passes a
    non-array through unchanged (both measured).
    """
    outputs = []
    rows = []
    last_failed = False
    for doc, line in docs:
        if doc is None:
            # `null` is INDEXABLE in jq — `.workers` on it is null, so `// []`
            # answers `[]`. Only booleans/numbers/strings/arrays raise.
            outputs.append([])
            continue
        if not isinstance(doc, dict):
            errln('jq: error (at %s:%d): Cannot index %s with string "workers"'
                  % (ledger, line, L._jq_type(doc)))
            last_failed = True
            continue
        last_failed = False
        value = doc.get("workers")
        if value is None or value is False:      # `// []`
            proj = []
        elif uuid:                               # `[.workers[]? | select(…)]`
            proj = [] if not isinstance(value, list) else [
                row for row in value
                if isinstance(row, dict)
                and L.to_string(_keep(row.get("uuid"), "")) == uuid]
        else:
            proj = value                         # jq keeps a non-array as-is
        outputs.append(proj)
        if isinstance(proj, list):
            rows.extend(proj)
        else:
            rows.append(proj)
    if last_failed:
        die(L.RC_REFUSED, "%s: jq failed — ledger unreadable or query error"
            % verb)
    return outputs, rows

def _workers_source(ledger: str) -> str:
    """The path jq would have been handed (for its own error messages)."""
    if L.jsonl_mode(ledger) and os.path.isfile(L.workers_path(ledger)):
        return L.workers_path(ledger)
    return ledger


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
        return fh.read()


def _jq_str(value) -> str:
    """``// ""`` for a field that must render as a string."""
    return L.to_string(value) if value is not None and value is not False else ""


def _keep(value, default):
    """jq ``.field // default`` — 0 and "" are KEPT, only null/false fall through."""
    return default if value is None or value is False else value


# ---------------------------------------------------------------------------
# jq value ordering — needed by duplicates (group_by/unique/max) and cadence
# ---------------------------------------------------------------------------
def _jq_rank(value):
    """jq's total order: null < false < true < numbers < strings < arrays < objects."""
    if value is None:
        return 0
    if value is False:
        return 1
    if value is True:
        return 2
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 3
    if isinstance(value, str):
        return 4
    if isinstance(value, (list, tuple)):
        return 5
    return 6


def _jq_key(value):
    """A sort key reproducing jq's ordering (used for group_by / unique / max)."""
    rank = _jq_rank(value)
    if rank == 3:
        return (rank, float(value))
    if rank == 4:
        return (rank, value)
    if rank == 5:
        return (rank, tuple(_jq_key(v) for v in value))
    if rank == 6:
        return (rank, tuple((k, _jq_key(v)) for k, v in sorted(value.items())))
    return (rank, 0)


def _jq_max(values):
    """jq ``max``: null on an empty list."""
    best = None
    best_key = None
    for value in values:
        key = _jq_key(value)
        if best_key is None or key > best_key:
            best, best_key = value, key
    return best


def _jq_num(value) -> float | int:
    """``.n // 0`` in the places the bash uses it for arithmetic."""
    value = _keep(value, 0)
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return value
    return 0


# ---------------------------------------------------------------------------
# ok
# ---------------------------------------------------------------------------
def cmd_ok(ledger, args):
    for arg in args:
        if arg in ("-h", "--help"):
            outln("usage: oc-ledger ok")
            outln("Exit: 0 readable / 3 missing or unparseable")
            return L.RC_OK
        die(L.RC_USAGE, "ok: unknown arg '%s' (usage: oc-ledger ok)" % arg)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ok: ledger missing or unparseable: %s" % ledger)
    outln("ok")
    return L.RC_OK


# ---------------------------------------------------------------------------
# law-digest
# ---------------------------------------------------------------------------
def cmd_law_digest(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln("usage: oc-ledger law-digest [--json]")
        outln("Exit: 0 MATCH or NO-BASELINE / 1 DRIFT / 3 ledger unreadable")
        return L.RC_OK
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    current = law_digest()
    stamped = law_digest_stamped(ledger)
    if not stamped:
        verdict, rc = "NO-BASELINE", L.RC_OK
    elif stamped == current:
        verdict, rc = "MATCH", L.RC_OK
    else:
        verdict, rc = "DRIFT", L.RC_VERDICT
    if args and args[0] == "--json":
        # `jq -n` with no -c: jq's DEFAULT output, two-space indented. The bash
        # emits this form and the gate is byte-identity, not "valid JSON".
        outln(L.dumps_pretty({"verdict": verdict, "current": current,
                              "stamped": stamped}))
    elif verdict == "MATCH":
        outln("law-digest: MATCH %s" % current)
    elif verdict == "NO-BASELINE":
        outln("law-digest: NO-BASELINE (newest skill-bump row predates #47; "
              "stamped at the next sync) — current %s" % current)
    else:
        outln("law-digest: DRIFT — the law files moved after the newest "
              "skill-bump stamp")
        outln("  current: %s" % current)
        outln("  stamped: %s" % stamped)
        outln("  a law edit without a bump: publish the NEXT version (bump "
              "SKILL.md + CHANGELOG, then: oc-ledger sync --version <next>)")
    return rc


# ---------------------------------------------------------------------------
# check-version
# ---------------------------------------------------------------------------
def _skill_version() -> str:
    """``grep -m1 '^version:' SKILL.md | awk '{print $2}'``."""
    path = os.path.join(L.skill_dir(), "SKILL.md")
    try:
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            for line in fh:
                if line.startswith("version:"):
                    fields = line.split()
                    return fields[1] if len(fields) > 1 else ""
    except OSError:
        return ""
    return ""


def cmd_check_version(ledger, args):
    for arg in args:
        if arg in ("-h", "--help"):
            outln("usage: oc-ledger check-version")
            return L.RC_OK
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    sv = _skill_version()
    unified = _unified(ledger)
    meta = unified.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    pairs = (
        ("current_skill_version", _jq_str(unified.get("current_skill_version"))),
        ("meta.current_skill_version", _jq_str(meta.get("current_skill_version"))),
        ("meta.skill_version", _jq_str(meta.get("skill_version"))),
    )
    bad = 0
    for name, got in pairs:
        if got != sv:
            outln("MISMATCH %s=%s (SKILL.md=%s)" % (name, got, sv))
            bad = 1

    # factory #47: the version fields can ALL agree while the LAW moved — the
    # case the version string cannot see, because the missing bump IS the
    # failure. The baseline is the newest skill-bump row, never the frontmatter.
    current = law_digest()
    stamped = law_digest_stamped(ledger)
    lawbad = 0
    if not stamped:
        outln("note: law digest baseline absent (newest skill-bump row predates "
              "#47) — stamped at the next sync; un-bumped law is not yet "
              "observable")
    elif stamped != current:
        lawbad = 1
        outln("MISMATCH law_digest=%s (newest skill-bump stamp=%s)"
              % (current, stamped))

    if bad == 0 and lawbad == 0:
        outln("ok: all fields agree at %s" % sv)
        return L.RC_OK
    if bad == 0:
        outln("CAUSE UNBUMPED-LAW: the law files changed after the newest "
              "skill-bump stamp — the version fields agree because no bump was "
              "attempted; publish the NEXT version (bump SKILL.md + CHANGELOG, "
              "then: oc-ledger sync --version <next>)")
        return L.RC_VERDICT
    # #359: name the CAUSE. Both causes stay rc 1 (hq.md:109 codifies rc=1 as
    # the FLEET-LEVEL heal), so the contract is made LEGIBLE, not changed.
    behind = 0
    for worker in (unified.get("workers") or []):
        if not isinstance(worker, dict):
            continue
        acked = worker.get("last_acked")
        if not isinstance(acked, dict):
            continue
        version = acked.get("version")
        if version is not None and version != sv:
            behind += 1
    if behind == 0:
        outln("CAUSE FLEET-LEVEL: registry lags SKILL.md with 0 worker(s) "
              "behind — skipped sync, not lane drift; heal with: oc-ledger "
              "sync --version %s" % sv)
    else:
        outln("CAUSE LANE-LEVEL: %d worker(s) ack behind SKILL.md — real drift; "
              "those lanes must re-ack" % behind)
    return L.RC_VERDICT


# ---------------------------------------------------------------------------
# cadence
# ---------------------------------------------------------------------------
_ACCEPTED_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+ ACCEPTED")


def cmd_cadence(ledger, args):
    for arg in args:
        if arg in ("-h", "--help"):
            outln("usage: oc-ledger cadence")
            return L.RC_OK
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    events = _unified(ledger).get("events") or []
    # Boundary = the latest review-CYCLE-CLOSE row: kind=note whose what starts
    # "vX.Y.Z ACCEPTED" (HQ acceptance IS the close receipt, n=2349 lesson: the
    # old review-battery/skill-review boundary predated the cycle it claimed to
    # close). Falls back to review-battery/skill-review rows for pre-close
    # epochs (selftest fixtures).
    closes = [_jq_num(row.get("n")) for row in events if isinstance(row, dict)
              and _jq_str(_keep(row.get("kind"), "")) == "note"
              and _ACCEPTED_RE.match(_jq_str(_keep(row.get("what"), "")))]
    close_n = _jq_num(_jq_max(closes)) if closes else 0
    if close_n > 0:
        boundary = close_n
    else:
        marks = []
        for row in events:
            if not isinstance(row, dict):
                continue
            kind = row.get("kind")
            if kind == "review-battery" or (
                    isinstance(kind, str) and kind.startswith("skill-review")):
                marks.append(_jq_num(row.get("n")))
        boundary = _jq_num(_jq_max(marks)) if marks else 0
    count = 0
    for row in events:
        if not isinstance(row, dict):
            continue
        if row.get("kind") == "skill-bump" and _jq_num(row.get("n")) > boundary:
            count += 1
    if count >= 5:
        outln("cadence: %d/5 FIRE (boundary n=%s) — Duties 4+6 due"
              % (count, _num_str(boundary)))
        return L.RC_VERDICT
    outln("cadence: %d/5 WAIT (boundary n=%s)" % (count, _num_str(boundary)))
    return L.RC_OK


def _num_str(value) -> str:
    """jq interpolation of a number: 0 renders "0", 4.0 renders "4"."""
    return L.dumps_compact(value)


# ---------------------------------------------------------------------------
# events / tail
# ---------------------------------------------------------------------------
_TS_SPACE = re.compile(r"^(\d{4}-\d{2}-\d{2}) ")
_TS_MINUTE_Z = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z$")
_TS_FRACTION = re.compile(r"\.[0-9]+Z$")
_TS_PLUS00 = re.compile(r"\+00:00$")


def _n_kind(row) -> str:
    return L.to_string(_keep(L.alt(row, "kind", "type", "event", "ev"), ""))


def _n_by(row) -> str:
    return L.to_string(_keep(L.alt(row, "by", "actor", "role", "who"), ""))


def _n_what(row) -> str:
    return L.to_string(_keep(L.alt(row, "what", "text", "summary", "note",
                                   "detail", "event", "action", "directive",
                                   "details"), ""))


def _n_n(row):
    return _keep(L.alt(row, "n", "seq", "id"), 0)


def _ts_normalise(value: str, *, strict: bool) -> str:
    """The two LOSSLESS stamp shapes, normalised so old rows stay reachable.

    ``strict`` is the WINDOWING form (a space separator and minute precision
    only). The RENDER form additionally drops fractional seconds and a
    ``+00:00`` offset — those are valid ISO-8601 spellings that a stricter
    predicate had been counting as malformed. Windowing stays STRICT on
    purpose: a row that is still non-ISO is NOT forced into every window,
    because that would make ``--since`` unable to report an empty window at all.
    """
    text = value
    text = _TS_SPACE.sub(lambda m: m.group(1) + "T", text, count=1)
    if not strict:
        text = _TS_FRACTION.sub("Z", text, count=1)
        text = _TS_PLUS00.sub("Z", text, count=1)
    text = _TS_MINUTE_Z.sub(lambda m: m.group(1) + ":00Z", text, count=1)
    return text


def _n_t(row, *, strict: bool) -> str:
    raw = L.to_string(_keep(L.alt(row, "t", "ts", "at"), ""))
    return _ts_normalise(raw, strict=strict)


def _events_projection(rows, kind, actor, since, n):
    """The #156/H-1/H-2 normalised, filtered, tailed selection."""
    matched = []
    for row in rows:
        if not isinstance(row, dict):
            # `[ .events[]? | ... ]` — jq's `?` drops a non-object here rather
            # than failing the whole query, so a scalar row is SKIPPED by this
            # verb (unlike load_ledger, which refuses the record).
            continue
        if kind and _n_kind(row) != kind:
            continue
        if actor and actor not in _n_by(row):
            continue
        if since and not (_n_t(row, strict=True) >= since):
            continue
        matched.append(row)
    length = len(matched)
    return matched[(length - n if length > n else 0):]


def _events_tsv(rows, trunc, *, strict_render=False):
    lines = []
    for row in rows:
        stamp = _n_t(row, strict=False)
        kind = _n_kind(row)
        by = _n_by(row)
        what = _n_what(row)
        lines.append(L.tsv_row([
            _n_n(row),
            stamp if stamp != "" else "?",
            kind if kind != "" else "?",
            by if by != "" else "-",
            what[:trunc],
        ]))
    return lines


def cmd_events(ledger, args):
    n = 20
    kind = ""
    actor = ""
    since = ""
    as_json = False
    as_jsonl = False
    full = False
    dump_all = False

    args = list(args)
    if args and re.fullmatch(r"[0-9]+", args[0]):
        n = int(args[0])
        args = args[1:]
    while args:
        head = args[0]
        if head == "--n":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "events: --n needs a value")
            n = args[1]
            args = args[2:]
        elif head == "--kind":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "events: --kind needs a value")
            kind = args[1]
            args = args[2:]
        elif head == "--actor":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "events: --actor needs a value")
            actor = args[1]
            args = args[2:]
        elif head == "--since":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "events: --since needs a value")
            since = args[1]
            args = args[2:]
        elif head == "--json":
            as_json = True
            args = args[1:]
        elif head == "--jsonl":
            as_jsonl = True
            args = args[1:]
        elif head == "--all":
            dump_all = True
            args = args[1:]
        elif head == "--full":
            full = True
            args = args[1:]
        elif head in ("-h", "--help"):
            outln("usage: oc-ledger events|tail [--n N] [--kind K] [--actor U] "
                  "[--since T] [--json] [--jsonl] [--all] [--full]")
            return L.RC_OK
        else:
            die(L.RC_USAGE, "events: unknown arg '%s' (usage: oc-ledger "
                "events|tail [--n N] [--kind K] [--actor U] [--since T] "
                "[--json] [--jsonl] [--all] [--full])" % head)

    if isinstance(n, str):
        if not re.fullmatch(r"[0-9]+", n):
            die(L.RC_USAGE, "events: --n must be a positive integer (got '%s')" % n)
        n = int(n)
    if n < 1:
        die(L.RC_USAGE, "events: --n must be >= 1 (got '%d')" % n)
    if as_json and as_jsonl:
        die(L.RC_USAGE, "events: --json and --jsonl are mutually exclusive")
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)

    if dump_all or as_jsonl:
        return _events_dump(ledger, kind, actor, since, as_json, as_jsonl,
                            full, dump_all)

    rows = _unified(ledger).get("events") or []
    selection = _events_projection(rows, kind, actor, since, n)
    if not selection:
        errln("events: no event matches (kind%s actor%s since%s) — widen the "
              "filter; an empty result here is a VERDICT, not an empty ledger"
              % ("=%s" % kind if kind else "",
                 "~%s" % actor if actor else "",
                 ">=%s" % since if since else ""))
        return L.RC_VERDICT
    if as_json:
        outln(L.dumps_pretty(selection))
        return L.RC_OK

    trunc = 1000000 if full else 160
    for line in _events_tsv(selection, trunc):
        outln(line)
    if not full:
        clipped = sum(1 for row in selection if len(_n_what(row)) > trunc)
        if clipped > 0:
            errln("events: %d row(s) had 'what' truncated to %d chars — rerun "
                  "with --full for the complete text" % (clipped, trunc))
    return L.RC_OK


def _events_dump(ledger, kind, actor, since, as_json, as_jsonl, full, dump_all):
    """``--all`` / ``--jsonl``: raw fields, no normalisation, no tail window."""
    if L.jsonl_mode(ledger):
        path = L.events_path(ledger)
        try:
            rows = L._parse_stream(_read(path), path)
        except L.LedgerError as exc:
            _refuse(exc)
        except OSError:
            die(L.RC_REFUSED, "events: ledger missing or unparseable: %s" % ledger)
    else:
        if not os.path.isfile(ledger):
            die(L.RC_REFUSED, "events: ledger missing or unparseable: %s" % ledger)
        try:
            doc = json.loads(_read(ledger))
        except (ValueError, OSError):
            die(L.RC_REFUSED, "events: ledger missing or unparseable: %s" % ledger)
        rows = doc.get("events") if isinstance(doc, dict) else None
        rows = rows or []

    selection = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # _EVENTS_FILTER: raw fields (no stamp normalisation), `contains` on by.
        if kind and L.to_string(_keep(L.alt(row, "kind", "type", "event", "ev"),
                                      "")) != kind:
            continue
        if actor and actor not in L.to_string(
                _keep(L.alt(row, "by", "actor", "role", "who"), "")):
            continue
        if since and not (L.to_string(_keep(L.alt(row, "t", "ts", "at"), ""))
                          >= since):
            continue
        selection.append(row)

    if as_jsonl:
        for row in selection:
            outln(L.dumps_compact(row))
        return L.RC_OK
    if as_json:
        if not selection:
            outln("[]")
        else:
            outln(L.dumps_compact(selection))
        return L.RC_OK
    if not selection:
        return L.RC_OK
    trunc = 1000000 if full else 160
    for row in selection:
        stamp = L.to_string(_keep(L.alt(row, "t", "ts", "at"), ""))
        kind_v = L.to_string(_keep(L.alt(row, "kind", "type", "event", "ev"), ""))
        by_v = L.to_string(_keep(L.alt(row, "by", "actor", "role", "who"), ""))
        what_v = L.to_string(_keep(L.alt(
            row, "what", "text", "summary", "note", "detail", "event", "action",
            "directive", "details"), ""))
        outln(L.tsv_row([
            _keep(L.alt(row, "n", "seq", "id"), 0),
            stamp if stamp != "" else "?",
            kind_v if kind_v != "" else "?",
            by_v if by_v != "" else "-",
            what_v[:trunc],
        ]))
    return L.RC_OK


# ---------------------------------------------------------------------------
# workers / worker
# ---------------------------------------------------------------------------
def cmd_workers(ledger, args):
    as_json = True
    as_tsv = False
    uuid = ""
    args = list(args)
    while args:
        head = args[0]
        if head == "--json":
            as_json, as_tsv = True, False
            args = args[1:]
        elif head == "--tsv":
            as_tsv, as_json = True, False
            args = args[1:]
        elif head == "--uuid":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "workers: --uuid needs a value")
            uuid = args[1]
            args = args[2:]
        elif head in ("-h", "--help"):
            outln("usage: oc-ledger workers [--json|--tsv] [--uuid U]")
            return L.RC_OK
        else:
            die(L.RC_USAGE, "workers: unknown arg '%s' (usage: oc-ledger workers "
                "[--json|--tsv] [--uuid U])" % head)

    docs = _workers_docs(ledger, "workers")
    outputs, rows = _workers_eval(ledger, docs, "workers", uuid)

    if as_tsv:
        # The bash pipes the JSON through a SECOND jq for the TSV form and then
        # `exit 0`s UNCONDITIONALLY, so a projection failure prints jq's error
        # and still exits 0 — the opposite of the first stage, which dies rc 3.
        # Both halves are reproduced. The error's `<stdin>:N` counter is jq's
        # own numbering of the PIPED stream, and it counts a value only once
        # the next one has been read — so a failure in the LAST array reports
        # one less than its index (measured: `[]`+`"x"` -> :1, `[]`+`[]`+`"x"`
        # -> :2, `"x"`+`[]` -> :1, `[]`+`"x"`+`[]` -> :2).
        emitted = 0
        total = len(outputs)
        for proj in outputs:
            emitted += 1
            reported = emitted if emitted < total else emitted - 1
            if not isinstance(proj, list):
                errln('jq: error (at <stdin>:%d): Cannot iterate over %s (%s)'
                      % (reported, L._jq_type(proj), L.dumps_compact(proj)))
                continue
            for row in proj:
                if not isinstance(row, dict):
                    errln('jq: error (at <stdin>:%d): Cannot index %s with '
                          'string "uuid"'
                          % (reported, L._jq_type(row)))
                    break
                outln(L.tsv_row([
                    L.to_string(_keep(row.get("uuid"), "")),
                    L.to_string(_keep(row.get("role"), "editor")),
                    L.to_string(_keep(row.get("topic_id"), 0)),
                    L.to_string(_keep(row.get("feature"), "-")),
                    L.to_string(_keep(row.get("state"), "ACTIVE")),
                ]))
        return L.RC_OK
    # One line per DOCUMENT: jq emits one array per input value, and an EMPTY
    # record yields no value at all, which `printf '%s\n' ""` renders as one
    # blank line — reproduced rather than "tidied" into `[]`.
    if not outputs:
        outln("")
        return L.RC_OK
    for proj in outputs:
        outln(L.dumps_compact(proj))
    return L.RC_OK


def cmd_worker(ledger, args):
    uuid = ""
    as_json = False
    args = list(args)
    while args:
        head = args[0]
        if head == "--uuid":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "worker: --uuid needs a value")
            uuid = args[1]
            args = args[2:]
        elif head == "--json":
            as_json = True
            args = args[1:]
        elif head in ("-h", "--help"):
            outln("usage: oc-ledger worker --uuid U [--json]")
            return L.RC_OK
        elif not uuid and not head.startswith("-"):
            uuid = head
            args = args[1:]
        else:
            die(L.RC_USAGE, "worker: unknown arg '%s' (usage: oc-ledger worker "
                "--uuid U [--json])" % head)
    if not uuid:
        die(L.RC_USAGE, "worker: --uuid is required")

    # `[.workers[]? | select(...)][0] // empty` runs PER DOCUMENT and jq emits
    # the first match across the whole stream, so the scan is document-ordered.
    docs = _workers_docs(ledger, "worker")
    found = None
    for row in _workers_eval(ledger, docs, "worker", uuid)[1]:
        if isinstance(row, dict):
            found = row
            break
    if found is None:
        return L.RC_VERDICT
    if as_json:
        outln(L.dumps_compact(found))
        return L.RC_OK
    outln(L.tsv_row([
        L.to_string(_keep(found.get("uuid"), "")),
        L.to_string(_keep(found.get("role"), "editor")),
        L.to_string(_keep(found.get("topic_id"), 0)),
        L.to_string(_keep(found.get("state"), "ACTIVE")),
    ]))
    return L.RC_OK


# ---------------------------------------------------------------------------
# lessons
# ---------------------------------------------------------------------------
def cmd_lessons(ledger, args):
    kind = "all"
    cls = ""
    args = list(args)
    while args:
        head = args[0]
        if head in ("-h", "--help"):
            outln("usage: oc-ledger lessons [--kind <lesson|incident|all>] "
                  "[--class <text>]")
            return L.RC_OK
        if head == "--kind":
            if len(args) < 2:
                die(L.RC_USAGE, "lessons: --kind needs a value")
            kind = args[1]
            args = args[2:]
        elif head == "--class":
            if len(args) < 2:
                die(L.RC_USAGE, "lessons: --class needs a value")
            cls = args[1]
            args = args[2:]
        else:
            die(L.RC_USAGE, "lessons: unknown arg '%s' (usage: oc-ledger lessons "
                "[--kind <lesson|incident|all>] [--class <text>])" % head)
    if kind not in ("lesson", "incident", "all"):
        die(L.RC_USAGE, "lessons: --kind must be lesson|incident|all (got '%s')"
            % kind)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)

    # F-4 (v0.4.119): --class is a SUBSTRING match, never a regex. The old
    # test($cls;"i") compiled it as a regex, and an invalid regex hit jq's
    # stderr-to-/dev/null plus an unconditional exit 0 — a silent false-clean.
    # Lowercase both sides + contains.
    needle = cls.lower()
    events = _unified(ledger).get("events") or []
    # `.events | to_entries[]` — the index is the KEY in the EVENT ARRAY, not
    # the row's `n`. The header says "n=<idx>" and means it.
    for idx, row in enumerate(events):
        if not isinstance(row, dict):
            continue
        row_kind = L.to_string(_keep(row.get("kind"), ""))
        if kind != "all" and row_kind != kind:
            continue
        what = L.to_string(_keep(row.get("what"), ""))
        if needle and needle not in what.lower():
            continue
        stamp = L.to_string(_keep(row.get("t"), "?"))
        outln("\t".join([
            "n=" + str(idx),
            row_kind if row_kind != "" else "?",
            stamp if stamp != "" else "?",
            what[:160],
        ]))
    return L.RC_OK


# ---------------------------------------------------------------------------
# claims  (canonical predicate: tools/lib/oc_claims.py — never re-inlined)
# ---------------------------------------------------------------------------
def cmd_claims(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln("usage: oc-ledger claims [<issue-number|#N>]")
        return L.RC_OK
    target = ""
    if args:
        target = args[0][1:] if args[0].startswith("#") else args[0]
        if not re.fullmatch(r"[0-9]+", target):
            die(L.RC_USAGE, "claims: issue number must be numeric (got '%s')"
                % args[0])
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)

    try:
        import oc_claims as oc
    except ImportError as exc:                  # pragma: no cover - tree fault
        die(L.RC_REFUSED, "claims: cannot load the canonical predicate: %s" % exc)

    events = _unified(ledger).get("events") or []
    for claim in oc.open_claims(events, target or None):
        outln("%s\t%s\t%s" % (claim["by"], claim["t"], claim["what"]))
    return L.RC_OK


# ---------------------------------------------------------------------------
# duplicates (read-only; c23 H-3)
# ---------------------------------------------------------------------------
def _iter_values(container):
    """jq's ``[]?``: an array's items, an object's values, else nothing."""
    if isinstance(container, list):
        return list(container)
    if isinstance(container, dict):
        return list(container.values())
    return []


def _jq_join(values, sep: str) -> str:
    """jq ``join(sep)``: null renders empty, everything else via tostring."""
    return sep.join("" if v is None else L.to_string(v) for v in values)


def cmd_duplicates(ledger, args):
    as_json = False
    kind = ""
    args = list(args)
    while args:
        head = args[0]
        if head == "--json":
            as_json = True
            args = args[1:]
        elif head == "--kind":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "duplicates: --kind needs a value")
            kind = args[1]
            args = args[2:]
        elif head in ("-h", "--help"):
            outln("usage: oc-ledger duplicates [--kind <k>] [--json]")
            return L.RC_OK
        else:
            die(L.RC_USAGE, "duplicates: unknown arg '%s' (usage: oc-ledger "
                "duplicates [--kind <k>] [--json])" % head)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)

    events = _unified(ledger).get("events") or []
    projected = []
    for row in _iter_values(events):
        if not isinstance(row, dict):
            continue
        # Group by the FACT -- (kind, what) -- NOT by the actor. Grouping by
        # (kind, by, what) finds nothing on the very specimens this verb exists
        # for, because the two rows carry DIFFERENT `by` strings for one act;
        # the actor difference is the second half of the defect, not a reason
        # to exclude the row.
        row_kind = L.alt(row, "kind", "type")
        if kind and L.to_string(_keep(row_kind, "")) != kind:
            continue
        projected.append({
            "k": L.to_string(_keep(L.alt(row, "kind", "type"), "-")),
            "t": _keep(L.alt(row, "t", "ts", "at"), ""),
            "b": _keep(L.alt(row, "by", "actor", "role"), "-"),
            "w": L.to_string(_keep(L.alt(row, "what", "text", "summary", "note",
                                         "detail"), "")),
            "n": _keep(row.get("n"), 0),
        })
    projected = [row for row in projected if row["w"] != ""]
    # group_by sorts by the key (jq's total order) and then groups adjacent
    # equal keys; Python's stable sort on the same key reproduces both.
    projected.sort(key=lambda row: (_jq_key(row["k"]), _jq_key(row["w"])))
    groups = []
    for row in projected:
        if groups and (groups[-1][0]["k"], groups[-1][0]["w"]) == (row["k"], row["w"]):
            groups[-1].append(row)
        else:
            groups.append([row])

    results = []
    for group in groups:
        if len(group) <= 1:
            continue
        bys = []
        for row in group:
            if row["b"] not in bys:
                bys.append(row["b"])
        bys.sort(key=_jq_key)
        results.append({
            "kind": group[0]["k"],
            "count": len(group),
            "bys": bys,
            "rows": [row["n"] for row in group],
            "ts": [row["t"] for row in group],
            "what": group[0]["w"][:90],
            "cls": "DUPLICATE" if len(bys) == 1 else "IDENTITY-SPLIT",
        })

    if as_json:
        outln(L.dumps_pretty(results))
        return L.RC_OK
    if not results:
        outln("duplicates: none -- no two rows share (kind, what)")
        return L.RC_OK
    for item in results:
        outln("%s kind=%s count=%s by=%s rows=%s ts=%s :: %s" % (
            item["cls"], item["kind"], L.dumps_compact(item["count"]),
            _jq_join(item["bys"], " | "), _jq_join(item["rows"], ","),
            _jq_join(item["ts"], " "), item["what"]))
    n_dup = sum(1 for item in results if item["cls"] == "DUPLICATE")
    n_split = len(results) - n_dup
    outln("duplicates: %d group(s) -- %d DUPLICATE (one fact, one actor, "
          "repeated) + %d IDENTITY-SPLIT (one act, two distinct actor "
          "identities). Each doubles every count that reads the ledger; removal "
          "is a human call, because a duplicate may hold the only copy of a "
          "detail." % (len(results), n_dup, n_split))
    return L.RC_OK


# ---------------------------------------------------------------------------
# roster
# ---------------------------------------------------------------------------
def _ascii_downcase(text: str) -> str:
    """jq ``ascii_downcase`` — ASCII only, never Unicode case folding."""
    return text.translate(_ASCII_LOWER)


_ASCII_LOWER = {code: code + 32 for code in range(ord("A"), ord("Z") + 1)}

_LIVE_SQL = (
    "SELECT s.id, COALESCE(b.thread_id, '') FROM sessions s "
    "LEFT JOIN session_bindings b ON b.session_id = s.id "
    "WHERE s.archived_at IS NULL "
    "AND (s.title IS NULL OR s.title NOT LIKE 'subagent:%');")


def _live_sessions(db_path: str) -> dict:
    """uuid -> live thread_id ("" when the session has no binding).

    Read through python3's built-in sqlite3 module, never the ``sqlite3`` CLI
    (#371): gating on that binary made this verb — the one every lane uses to
    resolve a role to a session uuid — fail rc 3 against a perfectly readable
    DB. A DB that will not answer is a HARD fail, never an empty roster that
    reads as "no such lane".
    """
    uri = "file:%s?mode=ro" % db_path
    try:
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        die(L.RC_REFUSED, "roster --live: session DB unreadable: %s (%s)"
            % (db_path, exc))
    try:
        rows = con.execute(_LIVE_SQL).fetchall()
    except sqlite3.Error as exc:
        die(L.RC_REFUSED, "roster --live: session DB unreadable: %s (%s)"
            % (db_path, exc))
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass
    mapping = {}
    for row in rows:
        key = "" if row[0] is None else str(row[0])
        value = "" if len(row) < 2 or row[1] is None else str(row[1])
        mapping[key] = value
    return mapping


def cmd_roster(ledger, args):
    role = ""
    live = False
    as_json = False
    include_retired = False
    reconcile = False
    args = list(args)
    while args:
        head = args[0]
        if head == "--role":
            if len(args) < 2 or not args[1]:
                die(L.RC_USAGE, "roster: --role needs a value")
            role = args[1]
            args = args[2:]
        elif head == "--live":
            live = True
            args = args[1:]
        elif head == "--include-retired":
            include_retired = True
            args = args[1:]
        elif head == "--reconcile":
            reconcile = True
            args = args[1:]
        elif head == "--json":
            as_json = True
            args = args[1:]
        elif head in ("-h", "--help"):
            outln("usage: oc-ledger roster [--role <substr>] [--live] "
                  "[--reconcile] [--include-retired] [--json]")
            return L.RC_OK
        else:
            die(L.RC_USAGE, "roster: unknown arg '%s' (usage: oc-ledger roster "
                "[--role <substr>] [--live] [--reconcile] [--include-retired] "
                "[--json])" % head)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)

    live_map = {}
    if live:
        db = os.environ.get("OC_LEDGER_DB", "") or os.path.join(
            L.state_dir(ledger), "..", "opencrabs.db")
        db = os.path.normpath(db)
        if not os.path.isfile(db):
            die(L.RC_REFUSED, "roster --live: session DB not found: %s "
                "(override with OC_LEDGER_DB)" % db)
        live_map = _live_sessions(db)

    # Legacy role alias (ontology fold 2026-09-11, c586e61f): `hq-supervisor`
    # became `hq`, and a query for the old string must still resolve — without
    # the alias it returns rc 1 NO-MATCH, which a lane reads as "HQ is
    # unrostered": a false negative in exactly the place lanes check HQ.
    lrole = _ascii_downcase(role)
    if lrole == "hq-supervisor":
        lrole = "hq"

    # `roster` reads through `jq_ledger` — the UNIFIED dict — NOT through
    # `_workers_source`. That is not cosmetic: with a record present and no
    # `workers.json` sidecar the unified path answers "no rows" (rc 1), while a
    # sidecar read dies rc 3, and the bash does the former.
    workers = _iter_values(_unified(ledger).get("workers"))

    def matches_role(worker) -> bool:
        if not lrole:
            return True
        return lrole in _ascii_downcase(L.to_string(_keep(worker.get("role"), "")))

    def is_retired(worker) -> bool:
        return L.to_string(_keep(worker.get("state"), "")) == "RETIRED"

    selected = []
    for worker in workers:
        if not isinstance(worker, dict):
            continue
        if not include_retired and is_retired(worker):
            continue
        if not matches_role(worker):
            continue
        uuid = L.to_string(_keep(worker.get("uuid"), ""))
        live_topic = live_map.get(uuid)
        if live and live_topic is None:
            continue
        selected.append((worker, uuid, live_topic))

    retired_n = 0
    if not include_retired:
        retired_n = sum(1 for worker in workers
                        if isinstance(worker, dict) and is_retired(worker)
                        and matches_role(worker))

    lines = []
    for worker, uuid, live_topic in selected:
        if live_topic is not None and live_topic != "":
            topic = live_topic
        else:
            topic = L.to_string(_keep(worker.get("topic_id"), "-"))
        feature = L.to_string(_keep(worker.get("feature"), "-"))[:60]
        last_acked = worker.get("last_acked")
        version = last_acked.get("version") if isinstance(last_acked, dict) else None
        lines.append(L.tsv_row([
            uuid,
            L.to_string(_keep(worker.get("role"), "-")),
            topic,
            feature,
            L.to_string(_keep(version, "-")),
        ]))

    if reconcile:
        if not live:
            die(L.RC_USAGE, "roster --reconcile requires --live (there is no "
                "binding to reconcile against otherwise)")
        drift = 0
        for worker, uuid, live_topic in selected:
            if live_topic is None or live_topic == "":
                continue
            stored = L.to_string(_keep(worker.get("topic_id"), ""))
            if stored == "" or stored == live_topic:
                continue
            errln("BINDING-MISMATCH uuid=%s role=%s stored=%s live=%s -- "
                  "reconcile with: oc-ledger promote %s %s --topic %s"
                  % (uuid[:8], L.to_string(_keep(worker.get("role"), "-")),
                     stored, live_topic, uuid,
                     L.to_string(_keep(worker.get("role"), "editor")),
                     live_topic))
            drift += 1
        if drift == 0:
            errln("roster --reconcile: 0 BINDING-MISMATCH over the live-bound rows")
        else:
            errln("roster --reconcile: %d BINDING-MISMATCH row(s) -- each is a "
                  "lane that MOVED and left its roster row unreconciled" % drift)

    if not lines:
        suffix = " (live sessions only)" if live else ""
        errln("roster: no row matches%s%s — fall back to session_search; NEVER "
              "hand-assemble a uuid"
              % (" role~'%s'" % role if role else "", suffix))
        if not include_retired and retired_n > 0:
            errln("roster: %d RETIRED row(s) match this role and are excluded by "
                  "default — pass --include-retired to list them; a RETIRED row "
                  "must never be dispatched" % retired_n)
        return L.RC_VERDICT

    if as_json:
        payload = []
        for line in lines:
            fields = line.split("\t")
            payload.append({
                "uuid": fields[0],
                "role": fields[1] if len(fields) > 1 else None,
                "topic_id": fields[2] if len(fields) > 2 else None,
                "feature": fields[3] if len(fields) > 3 else None,
                "last_acked": fields[4] if len(fields) > 4 else None,
            })
        outln(L.dumps_pretty(payload))
        return L.RC_OK

    for line in lines:
        outln(line)
    # Dispatch-safety nudge: a filtered lookup returning >1 row WITHOUT --live
    # is the stale-row trap (an old lane shares the role string).
    if role and not live and len(lines) > 1:
        errln("roster: %d rows match role~'%s' — add --live to keep only live "
              "sessions before dispatching" % (len(lines), role))
    return L.RC_OK


# ---------------------------------------------------------------------------
# mode (#97)
# ---------------------------------------------------------------------------
# The MODE ruling is a DECLARATION row, not any row that mentions MODE:. The
# grammar (SKILL.md §CONSENT REGISTER) is `MODE: <VALUE> — <provenance>`. The
# live ledger carries 34 rows containing "MODE:" of which exactly ONE is a
# declaration; the other 33 are prose ("held on the MODE gate"). Reading the
# ledger by eye answers the WRONG row, and `events` cannot answer at all
# without --n because it is a TAIL whose default window is ~21 rows. This verb
# is that predicate, stated once. Newest DECLARATION wins; prose never does.
_JQ_SPACE = " \t\n\r\f\v"
_DECL_RE = re.compile(r"^MODE:[ ]+[A-Z][A-Z0-9_-]*"
                      r"([ ]+(\u2014|--|-)[ ]+.*)?$")
_DECL_VALUE_RE = re.compile(r"^MODE:[ ]+([A-Z][A-Z0-9_-]*)")

MODE_HELP = (
    "usage: oc-ledger mode [--json]",
    "",
    "Print the NEWEST row whose what IS a MODE declaration — not the oldest",
    "match, and not a row that merely talks about the MODE gate.",
    "",
    "Declaration grammar (SKILL.md §CONSENT REGISTER):",
    "    MODE: <FORK-STANDING|UPSTREAM-ON-REQUEST> — <provenance>",
    "",
    "Legacy values read forward: DEGRADED => FORK-STANDING;",
    "HIGH-TRUST => UPSTREAM-ON-REQUEST with no named groups.",
    "",
    "rc 0 declaration printed · 1 no declaration (fail closed: FORK-STANDING)",
    "   2 usage · 3 ledger unreadable",
)


def _decl_word(row) -> str:
    """jq ``dw``: the row's text, trimmed of leading/trailing whitespace."""
    value = L.alt(row, "what", "text", "note", "detail")
    return L.to_string(_keep(value, "")).strip(_JQ_SPACE)


def cmd_mode(ledger, args):
    as_json = False
    for arg in args:
        if arg == "--json":
            as_json = True
        elif arg in ("-h", "--help"):
            for line in MODE_HELP:
                outln(line)
            return L.RC_OK
        else:
            die(L.RC_USAGE, "mode: unknown arg: %s (see oc-ledger mode --help)"
                % arg)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "mode: ledger unreadable: %s" % ledger)
    source = L.events_path(ledger) if L.jsonl_mode(ledger) else ledger

    events = _unified(ledger).get("events") or []
    declarations = []
    prose = 0
    for row in _iter_values(events):
        if not isinstance(row, dict):
            continue
        word = _decl_word(row)
        is_decl = bool(_DECL_RE.match(word))
        if is_decl:
            declarations.append(row)
        elif "MODE:" in word:
            prose += 1

    decl = None
    if declarations:
        declarations.sort(key=lambda row: _jq_key(_keep(row.get("n"), 0)))
        decl = declarations[-1]

    if decl is None:
        errln("%s: mode: NO DECLARATION in %s" % (PROG, source))
        errln("%s: mode: %d row(s) mention MODE: but none IS a declaration — "
              "prose is not a ruling" % (PROG, prose))
        errln("%s: mode: fail closed — no declaration means FORK-STANDING" % PROG)
        return L.RC_VERDICT

    value = _DECL_VALUE_RE.match(_decl_word(decl))
    matched = value.group(1) if value else ""
    if as_json:
        outln(L.dumps_compact({
            "n": _keep(decl.get("n"), None),
            "ts": _keep(L.alt(decl, "t", "ts", "at"), None),
            "value": matched,
        }))
    else:
        outln(L.tsv_row([
            _keep(decl.get("n"), "?"),
            _keep(L.alt(decl, "t", "ts", "at"), "?"),
            matched,
        ]))
    return L.RC_OK


# ===========================================================================
# PHASE 3 — THE WRITE VERBS (factory #204)
#
# Every verb below is a port of the corresponding ``cmd_*`` in
# ``tools/state/oc-ledger``. The store layer is NOT reimplemented: each
# mutation goes through ``ledger_core.atomic_write`` (the ONE writer) under
# ``ledger_core.with_lock`` (the ONE lock), and the git tail is QUEUED by
# ``ledger_core.git_state_commit`` and run by ``with_lock`` AFTER the release —
# which is the #95/#641 contract, enforced structurally: ``child_process``
# REFUSES to spawn while the lock is held, so the ordering cannot silently
# regress the way the bash's ``9>&-`` could be dropped in an edit.
#
# The four semantics the port must not break, restated where they bite:
#   1. a malformed JSONL line RAISES rc 3 (load_ledger), never skipped — a
#      skipped line turns a corrupt row into a MISSING row, and every closure
#      predicate then reads "no claim" (a false green);
#   2. one event pushed on the END is a TRUE APPEND (atomic_write's prefix
#      check) — one line + fsync, never a 2.8 MB rewrite;
#   3. no child process while the lock is held;
#   4. the git tail runs after release, on its own lock, and is NEVER fatal.
# ===========================================================================

# The closed kind enum, verbatim from the bash's ``KINDS``. ``skill-bump`` is
# deliberately ABSENT: it is sync-only, and both ``stamp`` and ``fixture``
# refuse it BY NAME so a hand-written bump row can never bypass the law digest
# that ``sync`` records in the same act.
KINDS = ("ruling idea idea-verdict design-feedback design-locked review-battery "
         "incident lesson note ack roster-enroll roster-retire claim hold "
         "confirm close done unclaim reject swap-result notify-fanout "
         "shipchain proposal").split()

# KINDS that CLOSE an issue. A ref-less row of this kind closes NOTHING while
# reporting success, so ``stamp`` WARNS (never refuses: of the 22 ref-less
# closing rows in the live ledger, 16 are ``done`` while 6 are ``confirm``
# ship records that legitimately carry no issue).
LANDED_KINDS = ("done", "close")

# The three home trackers, whose number spaces OVERLAP (v0.4.284). A claim
# token is a bare integer, so it cannot say which tracker it means — which is
# why a release requires "closed on a home repo AND open on NONE".
HOME_REPOS = ("leshchenko1979/opencrabs",
              "leshchenko1979/opencrabs-dev-factory",
              "opencrabs/opencrabs")

# The TRACKED-namespace whitelist (#508/#514/#540/#80). ONE home, consumed by
# the state-sweep tail here and by ``commit-pending --bundle``.
STATE_TRACKED_PATHS = (
    "baseline.json orders.json journal deployed.sha deployed.meta.json "
    "fanout.state oc-deploy oc-deploy-shadow.log oc-deploy-shadow.archive.log "
    "health-rotation.json smoke-verdicts.log reviews evidence pacemakers-off "
    "runs reports questions base-red.json harvest-registry.json").split()

# The harvest-state class carries glob metacharacters and must reach git
# QUOTED and DIRECTLY — an unquoted expansion pathname-expands against the
# CALLER's cwd. A parked harvest's state file is its ONLY resume record.
STATE_TRACKED_GLOB = "*-state.md"

# The skill repo's whitelisted runtime artifacts (never doc edits).
RUNTIME_ARTIFACTS = ("tools/tests/battery-last.json",)

# The stray-guard's exempt list (v0.4.157): the version docs and the battery
# receipt, which IS the bump's evidence.
STRAY_EXEMPT = ("SKILL.md", "CHANGELOG.md", "tools/tests/battery-last.json",
                "tools/tests/battery-last-fail.log")


def oc_clip_chars(text: str, cap: int) -> str:
    """``oc_clip_chars`` (tools/lib/oc-log.sh) — at most ``cap`` CHARACTERS.

    The bash fixed this for #588 because ``cut -c1-80`` counts BYTES under
    C.UTF-8 and clipped a non-ASCII ``what`` mid-character, printing a dangling
    lead byte on the one line whose whole purpose is to show what landed.
    """
    if cap <= 0 or len(text) <= cap:
        return text
    return text[:cap]


def _sha256_8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()[:8]


# ---------------------------------------------------------------------------
# the canonical issue tokenizer (tools/lib/oc_claims.py — never a copy)
#
# The bash DELEGATES these rather than carrying the pattern, and agreement is
# load-bearing in BOTH directions: ``claim-ref`` derives the issue from the very
# text ``claims`` scans, so a tokenizer that drifts by one character makes the
# tool DERIVE an issue the scanner cannot see — the #106/#107 false-clean.
# ---------------------------------------------------------------------------
def _oc_claims():
    try:
        import oc_claims as oc
    except ImportError as exc:                  # pragma: no cover - tree fault
        die(L.RC_REFUSED, "cannot load the canonical claim predicate: %s" % exc)
    return oc


def _issue_ref_tokens(text) -> list:
    """Every HOME-space issue reference in ``text``, as INTEGERS, in order."""
    if not text:
        return []
    return _oc_claims().issue_ref_tokens(text)


def _primary_issue_tokens(text) -> list:
    """The issue(s) ``text`` CLAIMS — its leading reference cluster (#329)."""
    if not text:
        return []
    return _oc_claims().primary_issue_tokens(text)


# ---------------------------------------------------------------------------
# actor resolution — ``derive_by`` (attribution label) and ``_self_uuid``
# ---------------------------------------------------------------------------
def _ambient_uuid() -> str:
    """``${OPENCRABS_SESSION_ID:-${OC_ACTOR:-}}`` — the SELF-verb precedence.

    ``_self_uuid`` reads this order and ``derive_by`` reads the OPPOSITE one
    (``${OC_ACTOR:-${OPENCRABS_SESSION_ID:-}}``, bash :1060 vs :2235). That is
    not an oversight to be "unified": ``derive_by`` is the ATTRIBUTION-LABEL
    path where an explicit label must outrank the ambient, while a self verb
    acts on the SESSION and the session id is the stronger identity. Collapsing
    the two into one helper made ``stamp`` stamp the wrong actor whenever both
    variables were set — caught by the differential on the first run.
    """
    return (os.environ.get("OPENCRABS_SESSION_ID")
            or os.environ.get("OC_ACTOR") or "")


def _actor_label_uuid() -> str:
    """``${OC_ACTOR:-${OPENCRABS_SESSION_ID:-}}`` — the ``derive_by`` precedence."""
    return (os.environ.get("OC_ACTOR")
            or os.environ.get("OPENCRABS_SESSION_ID") or "")


def _ascii_lower_af(text: str) -> str:
    """``tr 'A-F' 'a-f'`` — NOT a full lowercase (only A-F, as the bash does)."""
    return text.translate(str.maketrans("ABCDEF", "abcdef"))


def _carries_non_hex(value: str) -> bool:
    """bash ``*[!0-9a-f-]*`` — true when the value is a LABEL, not a uuid."""
    return any(ch not in "0123456789abcdef-" for ch in value)


def _roster_unique(workers, prefix: str) -> str:
    """``[.workers[] | select(uuid startswith $p)] | length == 1`` -> "role uuid"."""
    hits = [row for row in workers
            if isinstance(row, dict)
            and L.to_string(_keep(row.get("uuid"), "")).startswith(prefix)]
    if len(hits) != 1:
        return ""
    return "%s %s" % (L.to_string(_keep(hits[0].get("role"), "")),
                      L.to_string(_keep(hits[0].get("uuid"), "")))


def derive_by(ledger: str) -> str:
    """The default stamp attribution: roster ``role uuid``, or a LOUD sentinel.

    ``OC_ACTOR`` wins here BY DESIGN — this is the ``--by`` ATTRIBUTION-LABEL
    path, not a self-identifying verb, so an explicit label must outrank the
    ambient.
    """
    uuid = _actor_label_uuid()
    if not uuid or not (os.path.isfile(ledger) or L.jsonl_mode(ledger)):
        return "(unattributed — pass --by or export OC_ACTOR)"
    workers = _unified(ledger).get("workers")
    if not isinstance(workers, list):
        workers = []
    # M2-3: uuids are lowercase; an UPPERCASE actor could never match a row.
    uuid = _ascii_lower_af(uuid)
    for row in workers:
        if isinstance(row, dict) and L.to_string(_keep(row.get("uuid"), "")) == uuid:
            return "%s %s" % (L.to_string(_keep(row.get("role"), "")), uuid)
    # M2-3 census: the exact compare above cannot match a FRAGMENT, and 8 live
    # rows carry a bare 8-char prefix whose full uuid IS rostered. Those are an
    # UNRESOLVABLE LOOKUP, not "unrostered lanes" — resolve the unique fragment.
    # NOT a refusal: 64 of the 86 full-uuid sentinel rows belong to uuids that
    # ARE rostered today (stamped inside the pre-`enroll` window).
    if not _carries_non_hex(uuid) and len(uuid) >= 4:
        hit = _roster_unique(workers, uuid)
        if hit:
            return hit
    # M2-23: the sentinel is IDEMPOTENT. A value that already carries it is
    # echoed VERBATIM — otherwise feeding a prior row's `by` back produced
    # 'unrostered-actor unrostered-actor 2fae1230', which is unattributable AND
    # breaks an exact-string grep for the actor.
    if uuid.startswith("unrostered-actor "):
        errln("oc-ledger: WARNING — actor '%s' already carries the "
              "'unrostered-actor' sentinel — echoed VERBATIM, never "
              "double-prefixed." % uuid)
        errln("  Pass a roster role label or a session uuid as OC_ACTOR/--by.")
        return uuid
    # M2-24: the value derive_by PRODUCES must be round-trippable. It emits the
    # composed ``<role> <uuid>`` form, and feeding it back is the natural caller
    # pattern (``roster --live`` prints exactly that TSV). Resolve the TRAILING
    # token; when it names exactly one worker, stamp the CANONICAL composed form
    # from the roster — the roster's role, never the caller's guess.
    if " " in uuid:
        tail = uuid.rsplit(" ", 1)[1]
        if not _carries_non_hex(tail) and len(tail) >= 4:
            hit = _roster_unique(workers, tail)
            if hit:
                return hit
    # An unresolvable actor is LOUD and names the remedy — never a silent label.
    errln("oc-ledger: WARNING — actor '%s' is not in the roster (%s) — row "
          "stamped 'unrostered-actor %s'." % (uuid, ledger, uuid))
    errln("  If it is a session: oc-ledger enroll %s <role> [--topic N]. A "
          "factory/lane LABEL is not an actor — stamp as your ROSTER ROLE."
          % uuid)
    return "unrostered-actor %s" % uuid


def _by_uuid_shaped_unresolvable(ledger: str, value: str) -> None:
    """WARN-ONLY guard for an explicit ``--by`` (#320). Never refuses.

    ``--by`` bypasses derive_by entirely, so a hand-assembled uuid-format value
    (a remembered PREFIX plus an invented TAIL) landed as a phantom actor
    indistinguishable from a legitimate attribution. WARN, never REFUSE: 64 of
    the 86 full-uuid sentinel rows belong to uuids that ARE rostered today, and
    ``oc-ship`` passes an explicit ``--by`` fallback whose refusal would trade
    its whole ledger trail for a warning.
    """
    if not value:
        return
    cand = value.rsplit(" ", 1)[1] if " " in value else value
    if _carries_non_hex(cand):                  # a LABEL — silent, verbatim
        return
    if len(cand) < 4:
        return
    workers = _unified(ledger).get("workers")
    if not isinstance(workers, list):
        workers = []
    if any(isinstance(row, dict)
           and L.to_string(_keep(row.get("uuid"), "")).startswith(cand)
           for row in workers):
        return
    errln("oc-ledger: WARNING — --by '%s' is UUID-SHAPED but resolves to NO "
          "roster worker; the row is stamped VERBATIM and is indistinguishable "
          "from a legitimate attribution." % value)
    errln("  A hand-assembled uuid (remembered prefix + invented tail) is the "
          "usual cause. Fix: copy the uuid from a LIVE read — oc-ledger roster "
          "--live, or $OPENCRABS_SESSION_ID. A genuine label is fine as-is (it "
          "carries a non-hex char).")


def _self_uuid(verb: str, given: str) -> str:
    """A1b: a SELF verb acts on the CALLER, so the uuid comes from the ambient.

    The second half is a WARNING, not a refusal (#657): a refusal would REMOVE A
    DOCUMENTED CAPABILITY — ``ack``/``enroll`` act on ANOTHER lane's uuid as a
    roster-admin action, and the tool's own selftest exercises that deliberately
    (60 legs redden under a hard cross-check, including ``ack2-otheruuid-rc0``).
    """
    if given:
        if not L.is_uuid(given):
            die(L.RC_USAGE, "%s: uuid shape invalid (want 8-4-4-4-12 hex): '%s'"
                % (verb, given))
        ambient = _ambient_uuid()
        if ambient and L.is_uuid(ambient) and ambient != given:
            errln("note: %s acts on '%s', which is NOT the ambient session "
                  "'%s' -- correct for a roster-admin action; a mistake if you "
                  "meant yourself (omit the uuid to default to the ambient)."
                  % (verb, given, ambient))
        return given
    env_id = _ambient_uuid()
    if not env_id:
        die(L.RC_USAGE, "%s: no uuid supplied and no ambient session id. Fix: "
            "run inside a lane turn (OPENCRABS_SESSION_ID is set), or pass the "
            "uuid explicitly." % verb)
    return env_id


# ---------------------------------------------------------------------------
# claim -> issue derivation (single owner; cmd_claim_ref and cmd_confirm)
# ---------------------------------------------------------------------------
def _latest_claim_issue(ledger: str, uuid: str):
    """(issue, None) on success, (None, diagnostic) on failure.

    The ref is extracted by the SINGLE OWNER (``_issue_ref_tokens``), never by a
    bare ``#<digits>`` grep. Both failure modes are live in the ledger: a claim
    written "issue 76" carries NO '#' at all (the old grep answered rc 3 for a
    claim that EXISTS), and the old grep took the first '#<digits>' ANYWHERE in
    the prose, so n=1585 ("...issue 94 ... reusable for the #93 options hook")
    derived 93 — the WRONG issue, which ``confirm`` would then verify and close.
    """
    claim = ""
    events = _unified(ledger).get("events")
    for row in (events if isinstance(events, list) else []):
        if not isinstance(row, dict) or row.get("kind") != "claim":
            continue
        if uuid in L.to_string(_keep(row.get("by"), "")):
            claim = L.to_string(_keep(row.get("what"), ""))
    if not claim:
        return None, "no claim event by %s" % uuid
    tokens = _issue_ref_tokens(claim)
    if not tokens:
        return None, "latest claim by %s carries no numeric issue ref: %s" % (
            uuid, claim)
    return tokens[0], None


def _age_days(ts) -> float | None:
    """Days between the row stamp and now, or None when it cannot be READ.

    None is UNDECIDABLE, never 0: a row whose age cannot be read is not
    evidence of freshness, and the fail-open direction here writes a false
    Issue-Ref trailer into git history.
    """
    text = ts.strip() if isinstance(ts, str) else ""
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
    return (datetime.datetime.now(datetime.timezone.utc)
            - stamp).total_seconds() / 86400.0


def _latest_open_claim_issue(ledger: str, uuid: str, max_age_d: float = 0.0):
    """(issue, None) or (None, diagnostic) — the NEWEST claim row STILL OPEN.

    #492: the selection is the newest claim ROW THAT IS STILL OPEN, not the
    newest claim row. The two coincide only while a lane's newest claim is also
    its newest open one; the moment a lane closes a newer claim, a
    latest-row-only scan answers rc 3 and HIDES every older claim still open.
    #631: ``max_age_d`` > 0 REFUSES rather than answering when the newest open
    claim is older — a wrong Issue-Ref outlives the commit carrying it.
    """
    oc = _oc_claims()
    events = _unified(ledger).get("events")
    rows = oc.parse_events(events if isinstance(events, list) else [])
    idxs = [i for i, row in enumerate(rows)
            if row["kind"] == "claim" and uuid in row["by"]]
    if not idxs:
        return None, "no claim event by %s" % uuid
    # Newest-first, so the FIRST open candidate is also the YOUNGEST open one:
    # if it is already over the bound, every older candidate is too.
    for idx in reversed(idxs):
        row = rows[idx]
        for tok in row["targets"]:
            if oc.claim_is_closed(rows, idx, row["by"], tok):
                continue
            if max_age_d > 0:
                age = _age_days(row["t"])
                if age is None:
                    return None, (
                        "cannot DATE the newest open claim (#%d by %s, t=%r), "
                        "so its age is UNDECIDABLE and an Issue-Ref cannot be "
                        "derived from it safely\npass --issue <N> to name the "
                        "intended issue, or --session-id-only if this commit "
                        "belongs to none" % (tok, uuid, row["t"]))
                if age > max_age_d:
                    return None, (
                        "the newest open claim is STALE — #%d was claimed "
                        "%.1f days ago (bound %.1f d, %.0f h): %s\n"
                        "refusing to derive an Issue-Ref from an abandoned "
                        "claim; pass --issue <N> to name the intended issue, "
                        "or --session-id-only if this commit belongs to none"
                        % (tok, age, max_age_d, max_age_d * 24.0, row["what"]))
            return tok, None
    row = rows[idxs[-1]]
    if not row["targets"]:
        return None, ("latest claim by %s carries no numeric issue ref: %s"
                      % (uuid, row["what"]))
    detail = ("latest claim by %s is CLOSED (#%s — a done/close row for it "
              "follows): %s"
              % (uuid, ", #".join(str(t) for t in row["targets"]), row["what"]))
    older = len(idxs) - 1
    if older:
        detail += ("\n%d older claim row(s) by %s were also scanned and none "
                   "is open" % (older, uuid))
    return None, detail


# ---------------------------------------------------------------------------
# git helpers for the tails. NONE of these may run under the fleet lock —
# ``L.child_process`` raises rather than inheriting the lock fd (#641), so the
# ordering is enforced rather than documented.
# ---------------------------------------------------------------------------
_CW_ERR = ""
STATE_SWEEP_ERR = ""


def _git_run(directory: str, *args, timeout: int | None = None):
    """(rc, stdout, stderr) for a git call. Never raises; rc 1 on spawn failure."""
    try:
        proc = L.child_process(["git", "-C", directory] + list(args),
                               capture_output=True, text=True, timeout=timeout)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return 1, "", ""
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _git_out(directory: str, *args) -> tuple:
    rc, out, _ = _git_run(directory, *args)
    return rc, out.strip()


def _commit_with_retry(directory: str, subject: str) -> bool:
    """#116: a commit that FAILS must never read as a clean tree.

    ONE bounded retry first — git's own advice for ``.git/index.lock``, which a
    live concurrent commit releases in seconds. Bounded, so a genuine failure
    reports instead of spinning. The failure text lands in ``_CW_ERR`` so each
    call site can name the path it was committing.
    """
    global _CW_ERR
    rc, _, err = _git_run(directory, "commit", "-q", "-m", subject)
    if rc == 0:
        return True
    time.sleep(2)
    rc, _, err = _git_run(directory, "commit", "-q", "-m", subject)
    if rc == 0:
        return True
    _CW_ERR = " ".join((err or "").split())[:300]
    return False


def _ledger_tracked_names(ledger: str) -> str:
    """The basenames the state commit actually stages, mode-aware (#149).

    Spec trap 4: the audit's mechanism list once hardcoded workers-ledger.json,
    so after cutover it compared a declaration against a file no longer tracked
    — a guard that cannot see its target and reports clean.
    """
    if os.path.isfile(L.events_path(ledger)):
        return "events.jsonl workers.json"
    return "workers-ledger.json"


def _porcelain_paths(directory: str, *pathspecs) -> list:
    """``git status --porcelain -- <specs> | cut -c4- | sed 's/^.* -> //'``."""
    rc, out, _ = _git_run(directory, "status", "--porcelain", "--", *pathspecs)
    if rc != 0:
        return []
    paths = []
    for line in out.split("\n"):
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        paths.append(path)
    return paths


def state_sweep_tracked(directory: str, ledger: str,
                        label: str = "state") -> bool:
    """Commit the TRACKED namespace; True iff something was committed.

    ``git add`` DIES on a pathspec that matches nothing (rc 128, staging
    NOTHING at all), so the whitelist is never handed to git wholesale — the
    dirty subset is derived from ONE porcelain read first.
    """
    global STATE_SWEEP_ERR
    STATE_SWEEP_ERR = ""
    did = False
    hits = _porcelain_paths(directory, *STATE_TRACKED_PATHS)
    if hits:
        note = ""
        if "smoke-verdicts.log" in hits:
            # The append-only carve-out (toolsmith.md) exempts a self-attributing
            # shared log ONLY on condition that foreign rows are explicitly
            # disclosed; the sweep is the one actor that stages rows it did not
            # write, so it is the one that owes the sentence.
            note = (" [disclose foreign rows: smoke-verdicts.log rows "
                    "self-attribute via actor=]")
        rc, _, _ = _git_run(directory, "add", "--", *hits)
        if rc == 0:
            if _commit_with_retry(directory, "state sweep:%s (%s)%s"
                                  % (" ".join(hits), label, note)):
                outln("sweep: state runtime files committed:%s"
                      % " ".join(hits))
                did = True
            else:
                STATE_SWEEP_ERR = "state sweep:%s — %s" % (
                    " ".join(hits), _CW_ERR)
        else:
            STATE_SWEEP_ERR = "git add refused:%s" % " ".join(hits)
    if _porcelain_paths(directory, STATE_TRACKED_GLOB):
        rc, _, _ = _git_run(directory, "add", "--", STATE_TRACKED_GLOB)
        if rc == 0:
            if _commit_with_retry(directory, "state sweep: %s (%s)"
                                  % (STATE_TRACKED_GLOB, label)):
                outln("sweep: lane state records committed")
                did = True
            else:
                STATE_SWEEP_ERR = "state sweep:%s — %s" % (STATE_TRACKED_GLOB,
                                                          _CW_ERR)
        else:
            STATE_SWEEP_ERR = "git add refused:%s" % STATE_TRACKED_GLOB
    return did


# ---------------------------------------------------------------------------
# declared-vs-mechanism audit (#514) and its inverse (#540)
# ---------------------------------------------------------------------------
_BULLET_START = re.compile(r"^  - \*\*TRACKED\*\* —")
_BULLET_STOP = re.compile(r"^  - |^  [A-Za-z]")
_BACKTICKED = re.compile(r"`([^`]*)`")


def _tracked_bullet(skill_root: str):
    """(bullet_text, source_file) from the LAW CORPUS, or ("", "").

    #71: the declaration legitimately MOVES (v0.4.310 moved this bullet into
    reference-glossary.md), and a reader pinned to one filename goes blind the
    moment the law is reorganised — then reports SKIP while the audit it exists
    to perform has silently stopped. The audit follows the DECLARATION, and
    LAW_FILES is the authority on what the corpus IS, so an unlisted new law
    file cannot hide a declaration from this scan.
    """
    for name in LAW_FILES:
        path = os.path.join(skill_root, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue
        collected = []
        inside = False
        for line in lines:
            if not inside:
                if _BULLET_START.match(line):
                    inside = True
                    collected.append(line)
                continue
            if _BULLET_STOP.match(line):
                break
            collected.append(line)
        if collected:
            return "\n".join(collected), name
    return "", ""


def state_tracked_audit(ledger: str) -> None:
    """declaration -> mechanism: a name declared TRACKED that the sweep does not
    carry. WARN-only, rc 0 always (#514): the declaration is HQ's law surface
    and the list is this tool's, so a hard failure would let one side's edit
    block the other's work at a boundary it does not own."""
    bullet, found = _tracked_bullet(L.skill_dir())
    if not bullet:
        errln("state-tracked: NOTE — declared-vs-mechanism check SKIPPED: no "
              "'  - **TRACKED** —' bullet in any of the %d LAW_FILES. This is "
              "NOT a clean result and NOT a finding." % len(LAW_FILES))
        return
    mech = (STATE_TRACKED_PATHS + STATE_TRACKED_GLOB.split()
            + _ledger_tracked_names(ledger).split())
    gap = 0
    unclass = 0
    for token in _BACKTICKED.findall(bullet):
        if not token:
            continue
        if any(not ch.isprintable() for ch in token):
            continue
        # A backticked span containing whitespace is a COMMAND documented in the
        # bullet's parenthetical, not a path.
        if any(ch.isspace() for ch in token):
            unclass += 1
            continue
        # The glossary writes directory entries with a trailing slash while the
        # mechanism stores them bare; an unnormalised compare reports both.
        if token.endswith("/"):
            token = token[:-1]
        hit = False
        for name in mech:
            if token == name or token.endswith("/" + name) \
                    or name.endswith("/" + token):
                hit = True
                break
            # a leading-dot token is the second half of a slash-pair in the
            # prose ('deployed.sha'/'.meta.json' -> deployed.meta.json)
            if token.startswith(".") and token in name:
                hit = True
                break
        if hit:
            continue
        errln("state-tracked: WARN — '%s' is declared TRACKED in %s's state-dir "
              "glossary but carried by NEITHER STATE_TRACKED_PATHS nor "
              "STATE_TRACKED_GLOB. Add it to the list, or amend the glossary "
              "(#514)." % (token, found))
        gap += 1
    if unclass > 0:
        errln("state-tracked: note — %d backticked span(s) in the TRACKED "
              "bullet are not path-shaped (commands/parentheticals) and were "
              "not classified. Disclosed so the skip is never silent." % unclass)
    if gap == 0:
        errln("state-tracked: every name declared TRACKED in %s is carried by "
              "the sweep list." % found)


def state_out_of_scope_audit(ledger: str) -> None:
    """mechanism -> its own blind spot (#540). WARN-only, rc 0 always.

    A tracked file that NEITHER the sweep list NOR the glossary names is
    unreachable by EVERY commit path (there is no ``git add -A`` on the state
    repo), so it can be DELETED while the sanctioned verb still reports
    success. DIRTY out-of-scope files are FINDINGS; the untouched remainder is a
    COUNT — the mass is historical evidence, and a leg that cried wolf on it
    would be ignored, which is worse than no leg.
    """
    sd = L.state_dir(ledger)
    if not L.is_git_repo(sd):
        errln("state-out-of-scope: NOTE — inverse check SKIPPED: %s is not a "
              "git repo. This is NOT a clean result and NOT a finding." % sd)
        return
    rc, out, _ = _git_run(sd, "ls-files")
    if rc != 0:
        errln("state-out-of-scope: NOTE — inverse check SKIPPED: 'git ls-files' "
              "failed in %s. This is NOT a clean result." % sd)
        return
    tracked = [line for line in out.split("\n") if line]
    # The basename test applies to the GLOB ONLY: `*-state.md` is a pathspec
    # whose `*` crosses directories, while the literal list entries match the
    # ROOT only — `archive/orders.json` is genuinely unswept and must not read
    # as carried (a false NEGATIVE, i.e. a clean receipt over an unswept file).
    mech = STATE_TRACKED_PATHS + _ledger_tracked_names(ledger).split()
    outside = []
    for path in tracked:
        top = path.split("/", 1)[0]
        if path in mech or top in mech:
            continue
        base = path.rsplit("/", 1)[-1]
        if fnmatch.fnmatchcase(base, STATE_TRACKED_GLOB):
            continue
        outside.append(path)
    total = len(tracked)
    if not outside:
        errln("state-out-of-scope: every one of the %d tracked file(s) is "
              "carried by a commit path." % total)
        return
    dirty = []
    for path in _porcelain_paths(sd):
        if path in outside:
            dirty.append(path)
            errln("state-out-of-scope: WARN — '%s' is tracked but carried by NO "
                  "commit path, and is DIRTY in the worktree; no commit path "
                  "can reconcile it (#540)." % path)
    if not dirty:
        errln("state-out-of-scope: %d of %d tracked file(s) sit outside every "
              "commit path, none DIRTY — historical mass, a count and not a "
              "finding (#540)." % (len(outside), total))
    else:
        errln("state-out-of-scope: %d DIRTY out-of-scope file(s) reported above; "
              "%d further file(s) sit outside every commit path untouched "
              "(historical mass, a count and not a finding)."
              % (len(dirty), len(outside) - len(dirty)))


def oc_ship_audit_chain() -> None:
    """C-F4 tail-chain: rc 1 = findings -> a loud stderr pointer.

    rc 2/other is a fixture/env condition and is ignored. Runs OUTSIDE the lock
    (the dispatcher calls it after the verb returns). ``OC_SHIP_AUDIT_CHAIN=0``
    disables it, as every fixture does.
    """
    if os.environ.get("OC_SHIP_AUDIT_CHAIN", "1") != "1":
        return
    audit = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "oc-audit-ship")
    if not os.access(audit, os.X_OK):
        return
    try:
        proc = L.child_process([audit, "--grace", "120"],
                               capture_output=True, text=True)
        rc = proc.returncode
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return
    if rc == 1:
        errln("oc-ledger: SHIP-AUDIT rc=1 - ORPHANED/failed deploy legs "
              "detected; run: tools/ship/oc-audit-ship --grace 120")


# ---------------------------------------------------------------------------
# stamp — the ONE verb that mints a normal event row
# ---------------------------------------------------------------------------
STAMP_HELP = ('usage: oc-ledger stamp <kind> "<what>" [--by <actor>] '
              '[--what <text>|--what-file <path>|--what-stdin] '
              '[--allow-unattributed] [--allow-no-ref]')

FIXTURE_HELP = (
    'usage: oc-ledger fixture --n N --t <RFC3339> --kind K --by B '
    '(--what "<text>"|--what-file <path>|--what-stdin)',
    '',
    'Append a row with a FORCED ordinal and stamp — test fixtures only.',
    '--n and --t are REQUIRED (stamp derives both; a fixture exists to pin them).',
    'rc 0 appended + read-back ok · 2 usage · 3 ledger unreadable · 4 '
    'read-back/write failure',
)


def _read_text_source(verb: str, what_file: str, what_stdin: bool,
                      what: str) -> str:
    """Resolve ``--what`` / ``--what-file`` / ``--what-stdin`` (#341).

    Text passed on a BASH COMMAND LINE is expanded by the CALLER's shell before
    this tool sees it: backticks and ``$(...)`` run command substitution, and a
    substitution yielding EMPTY output leaves NO trace in the stored row. The
    read-back cannot catch that — it compares the already-expanded value against
    the already-expanded stored copy, so it is blind to caller-side expansion BY
    CONSTRUCTION. Both alternatives are mutually exclusive with each other and
    with ``--what``; command substitution strips ALL trailing newlines, so
    ``printf 'x\\n' > f`` and ``--what x`` agree byte-for-byte.
    """
    sources = (1 if what else 0) + (1 if what_file else 0) + (1 if what_stdin else 0)
    if sources > 1:
        die(L.RC_USAGE, "%s: give the text ONE way (--what | --what-file | "
            "--what-stdin), not %d" % (verb, sources))
    if what_file:
        try:
            with open(what_file, "rb") as fh:
                raw = fh.read()
        except OSError:
            die(L.RC_USAGE, "%s: --what-file not readable: %s"
                % (verb, what_file))
        return raw.decode("utf-8", "surrogateescape").rstrip("\n")
    if what_stdin:
        raw = sys.stdin.buffer.read()
        return raw.decode("utf-8", "surrogateescape").rstrip("\n")
    return what


def _issues_json(kind: str, what: str):
    """The structured ``issues`` field a claim records at WRITE time (#329).

    The prose is what a human reads; ``issues`` is what the scanner keys on, so
    the target is a FACT recorded now rather than an inference re-made from the
    sentence on every read. ``None`` (field absent) is the correct shape for
    non-claims and for a deliberately ref-less claim.
    """
    if kind != "claim":
        return None
    tokens = _primary_issue_tokens(what)
    return tokens or None


def _row(n, t: str, by: str, kind: str, what: str, issues):
    row = {"n": n, "t": t, "by": by, "kind": kind, "what": what}
    if issues is not None:
        row["issues"] = issues
    return row


def _last_event_on_disk(ledger: str):
    """The last row the RECORD holds — read BACK OFF DISK, never from memory.

    ``tail -n 1`` in the bash: a torn write or a concurrent append (impossible
    under the lock, but this is the check that would catch a broken lock) fails
    the same way a view-file mismatch used to.
    """
    if L.jsonl_mode(ledger):
        path = L.events_path(ledger)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return None
        text = data.decode("utf-8", "surrogateescape")
        lines = [line for line in text.split("\n") if line.strip()]
        if not lines:
            return None
        try:
            return json.loads(lines[-1])
        except ValueError:
            return None
    try:
        doc = json.loads(_read(ledger))
    except (ValueError, OSError):
        return None
    events = doc.get("events")
    if isinstance(events, list) and events:
        return events[-1]
    return None


def cmd_stamp(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln(STAMP_HELP)
        return L.RC_OK
    kind = ""
    what = ""
    by = ""
    by_explicit = False
    allow_unattr = False
    allow_noref = False
    what_file = ""
    what_stdin = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--by":
            if i + 1 >= len(args):
                die(L.RC_USAGE, "--by needs a value")
            by = args[i + 1]
            by_explicit = True
            i += 2
        elif arg == "--allow-unattributed":
            allow_unattr = True
            i += 1
        elif arg == "--allow-no-ref":
            allow_noref = True
            i += 1
        elif arg == "--what":
            what = args[i + 1] if i + 1 < len(args) else ""
            if not what:
                die(L.RC_USAGE, "--what needs a value")
            i += 2
        elif arg == "--what-file":
            what_file = args[i + 1] if i + 1 < len(args) else ""
            if not what_file:
                die(L.RC_USAGE, "--what-file needs a path")
            i += 2
        elif arg == "--what-stdin":
            what_stdin = True
            i += 1
        elif arg.startswith("--"):
            die(L.RC_USAGE, "stamp: unknown flag '%s' (forms: stamp <kind> "
                "\"<what>\" | stamp <kind> --what \"<text>\" | stamp <kind> "
                "--what-file <path> | stamp <kind> --what-stdin)" % arg)
        else:
            if not kind:
                kind = arg
            elif not what:
                what = arg
            i += 1

    what = _read_text_source("stamp", what_file, what_stdin, what)
    if not kind:
        die(L.RC_USAGE, "usage: oc-ledger stamp <kind> \"<what>\" [--by "
            "<label>] [--allow-unattributed] [--allow-no-ref]")
    if not what:
        die(L.RC_USAGE, "stamp: what must be non-empty")
    if not by:
        by = derive_by(ledger)
    # C-#7 (v0.4.77): underscore input normalises to the enum hyphen form.
    kind = kind.replace("_", "-")
    if kind == "skill-bump":
        die(L.RC_USAGE, "stamp: kind skill-bump is sync-only — use: oc-ledger "
            "sync --version <v>")
    if kind not in KINDS:
        die(L.RC_USAGE, "stamp: unknown kind '%s' (v1.3 vocabulary — see "
            "header)" % kind)
    if what.startswith("--"):
        # glitched-argv class, ledger n=1361/n=1372: a lost flag landed as the
        # row's text, and the read-back could not see it.
        die(L.RC_USAGE, "stamp: what looks like a lost flag (\"%s\") — pass "
            "text with --what explicitly (glitched-argv class, ledger "
            "n=1361/n=1372)" % what)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    if by_explicit:
        _by_uuid_shaped_unresolvable(ledger, by)
    # #19: an anonymous row IS a defect — it cannot be traced to a lane or a
    # tool, which is the whole point of the `by` field. derive_by() correctly
    # refused to invent an actor, but writing the sentinel anyway made the
    # defect the DEFAULT. Placed AFTER the ledger gate so a missing/corrupt
    # ledger is still rc 3, never masked by an rc 2 actor refusal.
    if not allow_unattr and by.startswith("(unattributed"):
        die(L.RC_USAGE, "stamp: REFUSED — no actor, and an anonymous row is a "
            "defect (it cannot be traced to a lane or a tool). Fix: pass --by "
            "\"<label>\" (e.g. --by \"<role> <uuid>\"), or export "
            "OC_ACTOR=<your session uuid>. If the anonymous row is deliberate: "
            "--allow-unattributed. (kind=%s)" % kind)
    # RESIDUAL (D-2 family): every consumer of a claim keys on the issue
    # reference, so a claim carrying NONE is a DEAD LETTER — and a silent one:
    # cmd_claims cannot see the row, so the verify-unclaimed dispatch gate
    # answers "clean" for an issue that IS claimed (#106/#107).
    if kind == "claim" and not allow_noref and not _issue_ref_tokens(what):
        die(L.RC_USAGE, "stamp: REFUSED — a claim must carry a numeric issue "
            "reference the scanner can see (\"CLAIM #<N> — ...\"; also "
            "accepted: \"issue <N>\", \"issue=#N\"). Every consumer keys on "
            "the ref, so a claim without one is a DEAD LETTER: cmd_claims "
            "cannot see the row, and the verify-unclaimed gate reports the "
            "issue CLEAN. If the row is deliberately ref-less: --allow-no-ref. "
            "(kind=%s)" % kind)
    # A LANDED row is a closing row and is supposed to address the issue it
    # lands, so a ref-less one closes NOTHING while reporting success (measured
    # 2026-09-25: `stamp done "592 landed: b9ee661cc"` returned "read-back ok"
    # rc 0 and left the claim OPEN). "(read-back ok)" confirms the WRITE, never
    # the ADDRESSING. WARN, scoped to LANDED_KINDS.
    if not allow_noref and kind in LANDED_KINDS and not _issue_ref_tokens(what):
        errln("oc-ledger: WARN — a '%s' row carries NO parseable issue "
              "reference, so it closes NOTHING while reporting success. The "
              "predicate accepts \"#<N>\" or \"issue <N>\" — BARE DIGITS ARE "
              "NOT A REF (\"592 landed: ...\" does not close #592; \"#592 "
              "landed: ...\" does). If the row deliberately addresses no "
              "issue: --allow-no-ref. (what=%s)" % (kind, what[:80]))

    def _stamp_locked():
        n = L.max_n(ledger) + 1
        t = L.now_iso()
        issues = _issues_json(kind, what)
        row = _row(n, t, by, kind, what, issues)

        def transform(doc):
            events = doc.get("events")
            if events is None:
                events = doc["events"] = []
            elif not isinstance(events, list):
                raise L.LedgerError(
                    L.RC_REFUSED, "atomic_write failed (rc=3) — the ledger was "
                    "NOT modified: .events is not an array")
            events.append(dict(row))
            # In JSONL mode atomic_write's TRUE-APPEND branch drops non-event
            # state, so this assignment is discarded there and lands only on the
            # wholesale path — exactly the bash's split between the two branches.
            doc["updated_at"] = t
            return None

        L.atomic_write(ledger, transform)

        # read-back self-verify (Duty-6 lens C2): never trust the write.
        last = _last_event_on_disk(ledger)
        if not isinstance(last, dict):
            die(L.RC_IO, "stamp READ-BACK MISMATCH: the last row of the record "
                "is unreadable — ledger corruption; investigate before further "
                "stamps")
        r_n = last.get("n")
        if r_n is None or L.to_string(r_n) != L.to_string(n):
            die(L.RC_IO, "stamp READ-BACK MISMATCH: sent n=%s, last line has "
                "n=%s — ledger corruption; investigate before further stamps"
                % (n, "" if r_n is None else L.to_string(r_n)))
        r_kind = L.to_string(_keep(last.get("kind"), ""))
        # ``$(jq -r ...)`` strips trailing newlines, so a `what` ending in one
        # fails this comparison in the bash too. Reproduce, do not "fix".
        r_what = L.to_string(_keep(last.get("what"), "")).rstrip("\n")
        if r_kind != kind or r_what != what:
            die(L.RC_IO, "stamp READ-BACK MISMATCH: sent kind=%s what=%s, disk "
                "has kind=%s what=%s — ledger corruption; investigate before "
                "further stamps" % (kind, what, r_kind, r_what))
        # The structured field is verified too: it is what the scan keys on, so
        # a silently-dropped `issues` array would reintroduce the prose
        # inference this field exists to replace.
        if kind == "claim":
            r_iss = L.dumps_compact(last.get("issues"))
            if r_iss != L.dumps_compact(issues):
                die(L.RC_IO, "stamp READ-BACK MISMATCH: sent issues=%s, disk "
                    "has issues=%s — the claim's target is not what was "
                    "written; investigate before further stamps"
                    % (L.dumps_compact(issues), r_iss))
        # Surface WHAT WAS STORED, not merely that something was stored (#341):
        # the read-back above compares two values that were BOTH already expanded
        # by the caller's shell, so it cannot see caller-side expansion; this
        # line is the last place a silently-corrupted `what` is catchable by eye.
        w_show = oc_clip_chars(r_what.replace("\n", " "), 80)
        outln("stamped n=%s kind=%s (read-back ok) what=\"%s\" len=%d hash8=%s"
              % (n, kind, w_show, len(r_what), _sha256_8(r_what)))
        L.git_state_commit(ledger, "ledger n=%s: %s (oc-ledger stamp)"
                           % (n, kind))

    L.with_lock(ledger, _stamp_locked)
    return L.RC_OK


# ---------------------------------------------------------------------------
# fixture — a row whose n and t are FORCED (test fixtures only)
# ---------------------------------------------------------------------------
def cmd_fixture(ledger, args):
    if args and args[0] in ("-h", "--help"):
        for line in FIXTURE_HELP:
            outln(line)
        return L.RC_OK
    n = ""
    t = ""
    kind = ""
    by = ""
    what = ""
    what_file = ""
    what_stdin = False

    i = 0
    while i < len(args):
        arg = args[i]
        pairs = {"--n": (n, "--n needs a value"),
                 "--t": (t, "--t needs a value"),
                 "--kind": (kind, "--kind needs a value"),
                 "--by": (by, "--by needs a value"),
                 "--what": (what, "--what needs a value"),
                 "--what-file": (what_file, "--what-file needs a path")}
        if arg in pairs:
            _, message = pairs[arg]
            if i + 1 >= len(args):
                die(L.RC_USAGE, "fixture: " + message)
            value = args[i + 1]
            if arg == "--n":
                n = value
            elif arg == "--t":
                t = value
            elif arg == "--kind":
                kind = value
            elif arg == "--by":
                by = value
            elif arg == "--what":
                what = value
            else:
                what_file = value
            i += 2
        elif arg == "--what-stdin":
            what_stdin = True
            i += 1
        else:
            die(L.RC_USAGE, "fixture: unknown arg '%s' (usage: oc-ledger "
                "fixture --n N --t <RFC3339> --kind K --by B --what \"<text>\")"
                % arg)

    if not n:
        die(L.RC_USAGE, "fixture: --n N is REQUIRED — a fixture row exists to "
            "FORCE its ordinal (stamp derives one)")
    if not re.fullmatch(r"[0-9]+", n):
        die(L.RC_USAGE, "fixture: --n must be a non-negative integer (got '%s')"
            % n)
    if not t:
        die(L.RC_USAGE, "fixture: --t <RFC3339> is REQUIRED — a fixture row "
            "exists to FORCE its stamp (stamp writes now)")
    # Shape, not normalisation: the value is stored VERBATIM (the read-back pins
    # byte equality). A stamp outside the ISO-8601 UTC family would be
    # unrankable by `events --since`, which is exactly what a seeded fixture is
    # for.
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
                        t):
        die(L.RC_USAGE, "fixture: --t must be RFC3339 UTC "
            "(YYYY-MM-DDTHH:MM:SSZ), got '%s'" % t)
    if not kind:
        die(L.RC_USAGE, "fixture: --kind K is REQUIRED")
    kind = kind.replace("_", "-")
    if kind == "skill-bump":
        die(L.RC_USAGE, "fixture: kind skill-bump is sync-only — it is not a "
            "fixture row")
    if kind not in KINDS:
        die(L.RC_USAGE, "fixture: unknown kind '%s' (v1.3 vocabulary — see "
            "header)" % kind)
    if not by:
        die(L.RC_USAGE, "fixture: --by B is REQUIRED — a fixture row names its "
            "planter, it is never derived")
    what = _read_text_source("fixture", what_file, what_stdin, what)
    if not what:
        die(L.RC_USAGE, "fixture: what must be non-empty")
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "fixture: ledger missing or unparseable: %s" % ledger)

    def _fixture_locked():
        forced_n = int(n)
        issues = _issues_json(kind, what)
        row = _row(forced_n, t, by, kind, what, issues)

        def transform(doc):
            events = doc.get("events")
            if events is None:
                events = doc["events"] = []
            elif not isinstance(events, list):
                raise L.LedgerError(
                    L.RC_REFUSED, "atomic_write failed (rc=3) — the ledger was "
                    "NOT modified: .events is not an array")
            events.append(dict(row))
            doc["updated_at"] = t
            return None

        L.atomic_write(ledger, transform)

        # The read-back resolves through the RECORD and compares the LAST row
        # against all four forced values, so a verb that quietly derived n or t
        # cannot report success.
        last = _last_event_on_disk(ledger)
        ok = (isinstance(last, dict)
              and L.dumps_compact(last.get("n")) == L.dumps_compact(forced_n)
              and L.to_string(_keep(last.get("t"), "")) == t
              and L.to_string(_keep(last.get("kind"), "")) == kind
              and L.to_string(_keep(last.get("what"), "")).rstrip("\n") == what)
        if not ok:
            disk_n = last.get("n") if isinstance(last, dict) else None
            die(L.RC_IO, "fixture READ-BACK MISMATCH sent n=%s t=%s kind=%s "
                "disk n=%s t=%s kind=%s what=%s — the forced n/t did not land; "
                "investigate before further fixture rows"
                % (n, t, kind,
                   "<none>" if disk_n is None else L.to_string(disk_n),
                   L.to_string(_keep((last or {}).get("t"), "<none>")),
                   L.to_string(_keep((last or {}).get("kind"), "<none>")),
                   oc_clip_chars(L.to_string(
                       _keep((last or {}).get("what"), "<none>")), 60)))
        w_show = oc_clip_chars(what.replace("\n", " "), 80)
        outln("fixtured n=%s kind=%s t=%s (read-back ok) what=\"%s\" len=%d "
              "hash8=%s" % (n, kind, t, w_show, len(what), _sha256_8(what)))
        L.git_state_commit(ledger, "ledger n=%s: %s (oc-ledger fixture)"
                           % (n, kind))

    L.with_lock(ledger, _fixture_locked)
    return L.RC_OK


def _split_two(args):
    """``uuid=$1 role=$2; shift 2 2>/dev/null || true`` — bash shift semantics.

    ``shift N`` FAILS ATOMICALLY when fewer than N positionals remain: it shifts
    NOTHING and the argument stays put. So ``oc-ledger enroll --topic`` leaves
    ``--topic`` in the tail, where the flag parser reports "--topic needs a
    value" — the diagnostic the caller needs. A plain ``args[2:]`` slice drops
    it silently and the run instead dies on the role-shape guard, naming the
    wrong cause. Caught by the differential on the first pass.
    """
    if len(args) >= 2:
        return args[0], args[1], list(args[2:])
    if len(args) == 1:
        return args[0], "", list(args)
    return "", "", []


# ---------------------------------------------------------------------------
# ack — a lane records that it has READ a version (self verb)
# ---------------------------------------------------------------------------
ACK_HELP = "usage: oc-ledger ack [<uuid>] <0.N.N version> [--at <ts>]"

_AT_ISO = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def _normalise_at(value: str) -> str:
    """Canonicalise an ISO-8601 UTC stamp, accepting the whole family (H-2/c23).

    ``--at`` is the ONLY caller-supplied stamp on any path and it used to be
    written VERBATIM. The live ledger carried 19 stamps that cannot be true — 9
    with a literal ``x`` for a redacted digit, 2 space-separated, 8 at
    minute-precision — and because ``events --since`` compares
    BYTE-LEXICOGRAPHICALLY, each one silently MIS-RANKED instead of erroring: a
    malformed value is always-less-than, so it drops out of every window. A
    stamp that cannot be parsed is a row no window can reach.

    Accept the family and canonicalise rather than demanding one spelling: a
    stamp with fractional seconds or ``+00:00`` is WELL-FORMED, and refusing it
    would be the same defect in the direction nobody reports.
    """
    text = value
    text = re.sub(r"\.[0-9]+", "", text)
    text = re.sub(r"\+00:00$", "", text)
    text = re.sub(r"Z$", "", text)
    return text + "Z"


def cmd_ack(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln(ACK_HELP)
        return L.RC_OK
    uuid, version, rest = _split_two(args)
    at = ""
    i = 0
    while i < len(rest):
        if rest[i] == "--at":
            # DELIBERATE DIVERGENCE (the only one in this verb). The bash reads
            # ``at="${2:-}"`` then ``shift 2``, and ``shift 2`` FAILS ATOMICALLY
            # when one positional remains — so ``--at`` never leaves ``$1`` and
            # ``oc-ledger ack --at`` loops FOREVER (verified: timeout 5 →
            # rc 124). A hang is not a behaviour worth porting; this refuses
            # rc 2 with the reason. Every other flag path matches byte-for-byte.
            if i + 1 >= len(rest):
                die(L.RC_USAGE, "ack: --at needs a value (an ISO-8601 UTC "
                    "stamp); the bash tool HANGS on this input — see cmd_ack")
            at = rest[i + 1]
            i += 2
        else:
            i += 1
    # A1b: ``ack`` is SELF, so the uuid is optional. A single NON-UUID argument
    # is the VERSION (``oc-ledger ack 0.4.268``), which is the form the owner
    # asked for.
    if uuid and not version and not L.is_uuid(uuid):
        version = uuid
        uuid = ""
    uuid = _self_uuid("ack", uuid)
    if not version:
        die(L.RC_USAGE, ACK_HELP)
    # tolerate display spelling v0.N.N; store bare, matching sync
    if version.startswith("v"):
        version = version[1:]
    if not re.fullmatch(r"0\.[0-9]+\.[0-9]+", version):
        die(L.RC_USAGE, "ack: version shape invalid (want 0.N.N, v prefix "
            "tolerated): '%s'" % version)
    if not at:
        at = L.now_iso()
    at = _normalise_at(at)
    if not _AT_ISO.match(at):
        die(L.RC_USAGE, "ack: --at must be an ISO-8601 UTC stamp "
            "(YYYY-MM-DDThh:mm:ssZ, fractional seconds and +00:00 accepted); "
            "got '%s'" % at)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    doc = _unified(ledger)
    workers = doc.get("workers")
    if not any(isinstance(row, dict)
               and L.to_string(_keep(row.get("uuid"), "")) == uuid
               for row in (workers if isinstance(workers, list) else [])):
        die(L.RC_REFUSED, "ack: unknown uuid %s — roster discovery first "
            "(Duty 2), or: oc-ledger enroll" % uuid)

    def _ack_locked():
        n = L.max_n(ledger) + 1
        t = L.now_iso()
        # M2-4: idempotent re-ack, mirroring sync's dup guard. An ack of a
        # (uuid, version) already ON RECORD is not new information. It fired in
        # the wild because ``oc-drift-check --ack`` DELEGATES here, so one
        # adoption that both drift-checked and acked wrote TWO byte-identical
        # rows seconds apart (lane 1a63f103 n=3717/3718; 462181e9 x3).
        # rc stays 0: oc-drift-check does ``|| die 3`` on this call.
        # The KEY is (uuid, version) and the compare is EXACT equality on the
        # composed ``what`` — a substring test would make 0.4.1 match 0.4.10
        # and swallow a real bump.
        want = "worker %s acked %s" % (uuid, version)
        events = _unified(ledger).get("events")
        dup = sum(1 for row in (events if isinstance(events, list) else [])
                  if isinstance(row, dict)
                  and L.to_string(_keep(row.get("kind"), "")) == "ack"
                  and L.to_string(_keep(row.get("what"), "")) == want)

        if dup > 0:
            def transform(doc_):
                for row in doc_.get("workers") or []:
                    if isinstance(row, dict) \
                            and L.to_string(_keep(row.get("uuid"), "")) == uuid:
                        row["last_acked"] = {"version": version, "at": at}
                # fields STILL refreshed (--at may carry a new timestamp) — a
                # lane that re-acks after a failed git leg must not keep a
                # stale last_acked.at
                doc_["updated_at"] = t
                return None
            L.atomic_write(ledger, transform)
            outln("acked %s at %s (already on record — idempotent, no dup "
                  "event)" % (uuid, version))
            L.git_state_commit(ledger, "ledger: ack %s v%s re-ack via oc-ledger"
                               % (uuid, version))
            return

        def transform(doc_):
            for row in doc_.get("workers") or []:
                if isinstance(row, dict) \
                        and L.to_string(_keep(row.get("uuid"), "")) == uuid:
                    row["last_acked"] = {"version": version, "at": at}
            events_ = doc_.get("events")
            if events_ is None:
                events_ = doc_["events"] = []
            events_.append({"n": n, "t": t, "by": "oc-ledger ack",
                            "kind": "ack", "what": want})
            doc_["updated_at"] = t
            return None
        L.atomic_write(ledger, transform)
        outln("acked %s at %s (event n=%s)" % (uuid, version, n))
        L.git_state_commit(ledger, "ledger n=%s: ack %s v%s (oc-ledger)"
                           % (n, uuid, version))

    L.with_lock(ledger, _ack_locked)
    return L.RC_OK


# ---------------------------------------------------------------------------
# enroll — add a roster row (self verb)
# ---------------------------------------------------------------------------
ENROLL_HELP = ("usage: oc-ledger enroll [<uuid>] <role> [--topic N] "
               "[--feature X]")


def _warn_topic_not_a_binding(ledger: str, topic: str) -> None:
    """TOPIC EXISTENCE GUARD (fork #503, Toolsmith 2026-09-22).

    ``--topic`` was taken verbatim and coerced with ``tonumber``, so ANY numeric
    value enrolled rc 0 and a real forum topic was indistinguishable from an
    issue number — a live row carried ``topic_id`` 478 (an ISSUE id, never a
    topic) and only a retire could undo it.

    WARN, never refuse: ``enroll`` runs at lane bring-up and must not be
    blockable by an absent or busy session DB (a refusal here would be a worse
    defect than the one it guards), and the live roster resolves 32 of 32 today,
    so this fires on a genuinely wrong value rather than on normal traffic.
    Mirrors ``derive_by``, which warns for an unresolvable actor and still
    writes.
    """
    if not topic or topic == "-" or not topic.isdigit():
        return
    db = os.environ.get("OC_LEDGER_DB") or os.path.join(
        os.path.dirname(L.state_dir(ledger)), "opencrabs.db")
    if not os.path.isfile(db):
        return
    try:
        con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    except sqlite3.Error:
        return
    try:
        row = con.execute("SELECT count(*) FROM session_bindings WHERE "
                          "thread_id = %s;" % topic).fetchone()
    except sqlite3.Error:
        return
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass
    if row and row[0] == 0:
        errln("oc-ledger enroll: WARNING topic %s names no live binding in %s "
              "— if that is an ISSUE number rather than a forum topic the "
              "roster mapping is wrong and only a retire can undo it (fork "
              "#503); if the topic was simply created and its lane has not "
              "messaged yet, ignore this." % (topic, db))


def cmd_enroll(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln(ENROLL_HELP)
        return L.RC_OK
    uuid, role, rest = _split_two(args)
    topic = "-"
    feature = "-"
    # A1b: ``enroll`` is SELF, so a single non-uuid argument is the ROLE
    # (``oc-ledger enroll editor`` = enroll myself).
    if uuid and not role and not L.is_uuid(uuid):
        role = uuid
        uuid = ""
    uuid = _self_uuid("enroll", uuid)
    i = 0
    while i < len(rest):
        if rest[i] == "--topic":
            if i + 1 >= len(rest):
                die(L.RC_USAGE, "--topic needs a value")
            topic = rest[i + 1]
            i += 2
        elif rest[i] == "--feature":
            if i + 1 >= len(rest):
                die(L.RC_USAGE, "--feature needs a value")
            feature = rest[i + 1]
            i += 2
        else:
            i += 1
    if not uuid or not role:
        die(L.RC_USAGE, ENROLL_HELP)
    # arg-shape guard (fork quirk 2026-09-04, #95 lane): a missing role
    # positional let ``--topic`` land in ``$role`` and pass the non-empty check.
    # Roles are prose words — a leading dash is always a parsing error.
    if role.startswith("-"):
        die(L.RC_USAGE, "enroll: role looks like a flag: '%s' (role positional "
            "missing?)" % role)
    if not L.is_uuid(uuid):
        die(L.RC_USAGE, "enroll: uuid shape invalid: '%s'" % uuid)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    workers = _unified(ledger).get("workers")
    if any(isinstance(row, dict)
           and L.to_string(_keep(row.get("uuid"), "")) == uuid
           for row in (workers if isinstance(workers, list) else [])):
        die(L.RC_USAGE, "enroll: uuid already enrolled: %s" % uuid)
    _warn_topic_not_a_binding(ledger, topic)

    def _enroll_locked():
        n = L.max_n(ledger) + 1
        t = L.now_iso()
        what = ("enrolled %s %s%s" % (role, uuid,
                                      "" if topic == "-" else " (topic %s)" % topic))

        def transform(doc):
            workers_ = doc.get("workers")
            if workers_ is None:
                workers_ = doc["workers"] = []
            workers_.append({
                "uuid": uuid, "role": role,
                "topic_id": None if topic == "-" else int(topic),
                "feature": feature, "confirmed": False, "first_seen": t,
                "last_acked": None, "notes": [], "events": []})
            events_ = doc.get("events")
            if events_ is None:
                events_ = doc["events"] = []
            events_.append({"n": n, "t": t, "by": "oc-ledger enroll",
                            "kind": "roster-enroll", "what": what})
            doc["updated_at"] = t
            return None
        L.atomic_write(ledger, transform)
        outln("enrolled %s %s (event n=%s)" % (role, uuid, n))
        L.git_state_commit(ledger, "ledger n=%s: enroll %s %s (oc-ledger)"
                           % (n, role, uuid))

    L.with_lock(ledger, _enroll_locked)
    return L.RC_OK


# ---------------------------------------------------------------------------
# promote — update an enrolled row IN PLACE
# ---------------------------------------------------------------------------
PROMOTE_HELP = ("usage: oc-ledger promote <uuid> <new-role> [--topic N] "
                "[--feature X]")


def cmd_promote(ledger, args):
    # -h|--help is answered BEFORE the role-shape disambiguation below: with
    # ``promote --help`` the single argument would be read as a ROLE, so the old
    # path died rc 2 ("role looks like a flag") and this verb's own usage was
    # unreachable — the one verb without a help arm (#686).
    if args and args[0] in ("-h", "--help"):
        outln(PROMOTE_HELP)
        return L.RC_OK
    if len(args) > 1 and args[1] in ("-h", "--help"):
        outln(PROMOTE_HELP)
        return L.RC_OK
    uuid, role, rest = _split_two(args)
    topic = ""
    feature = ""
    # A1b (#659): promote is SELF when the uuid is omitted. A single non-uuid
    # argument is the new ROLE, exactly as enroll disambiguates.
    if uuid and not role and not L.is_uuid(uuid):
        role = uuid
        uuid = ""
    uuid = _self_uuid("promote", uuid)
    i = 0
    while i < len(rest):
        if rest[i] == "--topic":
            if i + 1 >= len(rest):
                die(L.RC_USAGE, "--topic needs a value")
            topic = rest[i + 1]
            i += 2
        elif rest[i] == "--feature":
            if i + 1 >= len(rest):
                die(L.RC_USAGE, "--feature needs a value")
            feature = rest[i + 1]
            i += 2
        else:
            i += 1
    if not uuid or not role:
        die(L.RC_USAGE, PROMOTE_HELP)
    if role.startswith("-"):
        die(L.RC_USAGE, "promote: role looks like a flag: '%s' (role "
            "positional missing?)" % role)
    if not L.is_uuid(uuid):
        die(L.RC_USAGE, "promote: uuid shape invalid: '%s'" % uuid)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    workers = _unified(ledger).get("workers")
    rows = [row for row in (workers if isinstance(workers, list) else [])
            if isinstance(row, dict)
            and L.to_string(_keep(row.get("uuid"), "")) == uuid]
    if not rows:
        die(L.RC_USAGE, "promote: uuid not enrolled — use enroll to create the "
            "row: %s" % uuid)
    # current values (null renders as "-" — the enroll convention)
    cur = rows[0]
    cur_role = L.to_string(_keep(cur.get("role"), "-"))
    cur_topic = L.to_string(_keep(cur.get("topic_id"), "-"))
    cur_feature = L.to_string(_keep(cur.get("feature"), "-"))
    changes = ""
    if role != cur_role:
        changes = "role: %s -> %s" % (cur_role, role)
    if topic and topic != cur_topic:
        if not (topic.isdigit() or topic == "-"):
            die(L.RC_USAGE, "promote: --topic must be a number or '-'")
        changes = ("%s; topic: %s -> %s" % (changes, cur_topic, topic)
                   if changes else "topic: %s -> %s" % (cur_topic, topic))
    if feature and feature != cur_feature:
        changes = ("%s; feature: %s -> %s" % (changes, cur_feature, feature)
                   if changes else "feature: %s -> %s" % (cur_feature, feature))
    if not changes:
        die(L.RC_USAGE, "promote: nothing to change (role/topic/feature all "
            "unchanged)")

    def _promote_locked():
        n = L.max_n(ledger) + 1
        t = L.now_iso()

        def transform(doc):
            for row in doc.get("workers") or []:
                if not (isinstance(row, dict)
                        and L.to_string(_keep(row.get("uuid"), "")) == uuid):
                    continue
                row["role"] = role
                if topic:
                    row["topic_id"] = None if topic == "-" else int(topic)
                if feature:
                    row["feature"] = feature
                notes = row.get("notes")
                if not isinstance(notes, list):
                    notes = [] if notes is None else [notes]
                row["notes"] = notes + ["promoted at %s: %s" % (t, changes)]
            events_ = doc.get("events")
            if events_ is None:
                events_ = doc["events"] = []
            events_.append({"n": n, "t": t, "by": "oc-ledger promote",
                            "kind": "note",
                            "what": "promoted %s: %s" % (uuid, changes)})
            doc["updated_at"] = t
            return None
        L.atomic_write(ledger, transform)
        outln("promoted %s (%s) — event n=%s" % (uuid, changes, n))
        L.git_state_commit(ledger, "ledger n=%s: promote %s (oc-ledger)"
                           % (n, uuid))

    L.with_lock(ledger, _promote_locked)
    return L.RC_OK


# ---------------------------------------------------------------------------
# retire — REMOVE one roster row (the correction path)
# ---------------------------------------------------------------------------
RETIRE_HELP = ("usage: oc-ledger retire <uuid> [--topic N] [--role R] "
               "[--why TEXT]")


def cmd_retire(ledger, args):
    """ROW-SCOPED, NOT UUID-SCOPED (defect fix 2026-09-11, HQ report d72bd52d).

    The first cut removed ``.workers |= map(select(.uuid != $u))`` — EVERY row
    carrying that uuid — and snapshotted the event from ``[0]``, so a uuid with
    two rows would have had both revoked by an event naming only one. That was
    LATENT on the roster of the day but the roster model plainly permits two: an
    editor row on one topic plus an auditor row on another. So the verb takes
    ``--topic``/``--role`` selectors — EXACT match, deliberately NOT the
    substring match ``roster --role`` uses, because this verb DESTROYS a row —
    and REFUSES rc 2 when the uuid matches more than one row and no selector
    disambiguates, listing them so the caller can pick. A guard with no selector
    would be a dead end: a legitimately two-row uuid could then never be
    retired at all.

    Removal is by ARRAY INDEX, never by re-matching a predicate, so the row
    removed is exactly the row shown and snapshotted.

    A1b (#659): retire is the ONE self-verb deliberately WITHOUT an env default.
    ``ack``/``enroll``/``promote`` take it, but retire DESTROYS a roster row — a
    no-argument ``oc-ledger retire`` would silently remove the AMBIENT lane's own
    enrollment, and the fixture pin ``retire-no-args`` (rc 2) exists for that
    reason. So the uuid stays REQUIRED.
    """
    uuid = args[0] if args else ""
    why = ""
    sel_topic = ""
    sel_role = ""
    rest = args[1:]
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "--why":
            if i + 1 >= len(rest) or not rest[i + 1]:
                die(L.RC_USAGE, "retire: --why needs a value")
            why = rest[i + 1]
            i += 2
        elif arg == "--topic":
            if i + 1 >= len(rest) or not rest[i + 1]:
                die(L.RC_USAGE, "retire: --topic needs a value")
            sel_topic = rest[i + 1]
            i += 2
        elif arg == "--role":
            if i + 1 >= len(rest) or not rest[i + 1]:
                die(L.RC_USAGE, "retire: --role needs a value")
            sel_role = rest[i + 1]
            i += 2
        elif arg in ("-h", "--help"):
            outln(RETIRE_HELP)
            return L.RC_OK
        else:
            die(L.RC_USAGE, "retire: unknown arg '%s' (usage: oc-ledger retire "
                "<uuid> [--topic N] [--role R] [--why TEXT])" % arg)
    if not uuid:
        die(L.RC_USAGE, RETIRE_HELP)
    if not L.is_uuid(uuid):
        die(L.RC_USAGE, "retire: uuid shape invalid: '%s'" % uuid)
    # Selector shape is validated BEFORE the match query, so a malformed
    # --topic can never be misread as "no row matches".
    if sel_topic and not sel_topic.isdigit():
        die(L.RC_USAGE, "retire: --topic must be an integer, got '%s'"
            % sel_topic)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    workers = _unified(ledger).get("workers")
    workers = workers if isinstance(workers, list) else []
    # An absent topic_id can never equal a numeric --topic ("" != "49607"), so a
    # selector never matches a null-topic row.
    matches = [(idx, row) for idx, row in enumerate(workers)
               if isinstance(row, dict)
               and L.to_string(_keep(row.get("uuid"), "")) == uuid
               and (not sel_topic
                    or L.to_string(_keep(row.get("topic_id"), "")) == sel_topic)
               and (not sel_role
                    or L.to_string(_keep(row.get("role"), "")) == sel_role)]
    if not matches:
        die(L.RC_USAGE, "retire: no row matches %s%s%s — nothing to remove"
            % (uuid,
               " (topic %s)" % sel_topic if sel_topic else "",
               " (role %s)" % sel_role if sel_role else ""))
    if len(matches) > 1:
        errln("retire: ambiguous — %d rows carry %s; add --topic N and/or "
              "--role R to pick exactly one:" % (len(matches), uuid))
        for _, row in matches:
            errln("  %s  topic %s  feature %s  confirmed %s"
                  % (L.to_string(_keep(row.get("role"), "-")),
                     L.to_string(_keep(row.get("topic_id"), "-")),
                     L.to_string(_keep(row.get("feature"), "-")),
                     L.to_string(_keep(row.get("confirmed"), False))))
        die(L.RC_USAGE, "retire: ambiguous uuid — refusing to remove more than "
            "one row")
    idx, row = matches[0]
    if not why:
        why = "(no reason given)"
    # Snapshot the row BEFORE removal — the event is its only surviving record.
    cur_role = L.to_string(_keep(row.get("role"), "-"))
    cur_topic = L.to_string(_keep(row.get("topic_id"), "-"))
    cur_feature = L.to_string(_keep(row.get("feature"), "-"))
    cur_confirmed = L.to_string(_keep(row.get("confirmed"), False))

    def _retire_locked():
        n = L.max_n(ledger) + 1
        t = L.now_iso()
        what = ("retired %s %s (topic %s, feature %s, confirmed %s): %s"
                % (cur_role, uuid, cur_topic, cur_feature, cur_confirmed, why))

        def transform(doc):
            workers_ = doc.get("workers")
            if isinstance(workers_, list) and idx < len(workers_):
                del workers_[idx]
            events_ = doc.get("events")
            if events_ is None:
                events_ = doc["events"] = []
            events_.append({"n": n, "t": t, "by": "oc-ledger retire",
                            "kind": "roster-retire", "what": what})
            doc["updated_at"] = t
            return None
        L.atomic_write(ledger, transform)
        outln("retired %s %s (event n=%s) — row removed, signing revoked"
              % (cur_role, uuid, n))
        L.git_state_commit(ledger, "ledger n=%s: retire %s %s (oc-ledger)"
                           % (n, cur_role, uuid))

    L.with_lock(ledger, _retire_locked)
    return L.RC_OK


# ---------------------------------------------------------------------------
# claim — record a CLAIM row for an issue (delegates to stamp)
# ---------------------------------------------------------------------------
CLAIM_HELP = ('usage: oc-ledger claim [<uuid>] <issue-number|#N> [text...] | '
              'oc-ledger claim --issue <N> [--what <text>]')

_UUID_LOOSE = re.compile(r"^[0-9a-fA-F-]{36}$")
_ISSUE_ARG = re.compile(r"^#?[0-9]+$")


def cmd_claim(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln(CLAIM_HELP)
        return L.RC_OK
    by = ""
    issue = ""
    what = ""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--by", "--session", "--actor"):
            # The bash does ``by="${2:-}"; shift 2`` and ``shift 2`` FAILS
            # ATOMICALLY with one positional left, so ``claim --by`` never
            # leaves ``$1`` and loops forever (same defect as ``ack --at``).
            # Refuse instead of hanging; see cmd_ack for the full note.
            if i + 1 >= len(args):
                die(L.RC_USAGE, "claim: %s needs a value" % arg)
            by = args[i + 1]
            i += 2
        elif arg in ("--issue", "--ref"):
            if i + 1 >= len(args):
                die(L.RC_USAGE, "claim: %s needs a value" % arg)
            issue = args[i + 1]
            i += 2
        elif arg in ("--what", "--note", "--task", "--title"):
            if i + 1 >= len(args):
                die(L.RC_USAGE, "claim: %s needs a value" % arg)
            what = args[i + 1]
            i += 2
        elif arg in ("-h", "--help"):
            outln(CLAIM_HELP)
            return L.RC_OK
        else:
            if not issue and _UUID_LOOSE.match(arg):
                by = arg
            elif not issue and _ISSUE_ARG.match(arg):
                issue = arg.lstrip("#")
            elif not what:
                what = arg
            else:
                what = what + " " + arg
            i += 1
    if not issue:
        die(L.RC_USAGE, "usage: oc-ledger claim [<uuid>] <issue-number|#N> "
            "[text...] (numeric issue ref required)")
    # Defect #335: the prefix test must BE the consumer's predicate, not a
    # substring search. The old ``case *"#$issue"*`` fired on a mention ANYWHERE
    # in the prose, so ``claim --issue 299 --what "fixed #294 ... (#299)"``
    # suppressed the prefix and the row's LEADING cluster (#294) became the
    # claim's target — the explicit flag lost to a passing mention, and oc-commit
    # then derived Issue-Ref #294 from that row and cross-posted onto a done
    # issue. Suppress the prefix ONLY when the prose already LEADS with a cluster
    # naming $issue, tested with the single owner every consumer reads the row
    # with. ``--issue #N`` is accepted too: a stray '#' would otherwise build
    # "CLAIM ##N" and dodge the membership test.
    issue = issue.lstrip("#")
    if what:
        if issue in [str(tok) for tok in _primary_issue_tokens(what)]:
            full_what = what
        else:
            full_what = "CLAIM #%s — %s" % (issue, what)
    else:
        full_what = "CLAIM #%s" % issue
    stamp_args = ["claim", full_what]
    if by:
        stamp_args += ["--by", by]
    return cmd_stamp(ledger, stamp_args)


# ---------------------------------------------------------------------------
# claim-ref — the #N a consumer may safely ACT on
# ---------------------------------------------------------------------------
CLAIM_REF_HELP = (
    "usage: oc-ledger claim-ref <uuid> [--open] [--max-age-d <days>]   "
    "(--open = the lane's NEWEST claim row that is STILL OPEN; --max-age-d > 0 "
    "additionally REFUSES when that claim is older than <days> (#631). rc 3 = "
    "no open claim, or one too old to act on. The composed '<role> <uuid>' is "
    "also accepted; for an ISSUE number use: oc-ledger claims <N>)")

_MAX_AGE_SHAPE = re.compile(r"^[0-9.]+$")


def cmd_claim_ref(ledger, args):
    open_only = False
    uuid = ""
    max_age_d = ""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--open":
            open_only = True
            i += 1
        elif arg == "--max-age-d":
            # #631: bound the AGE of the claim the derivation may act on.
            # 0/absent = unbounded (the plain read); positive refuses rather
            # than answering when the newest open claim is older.
            if i + 1 >= len(args) or not args[i + 1]:
                die(L.RC_USAGE, "claim-ref: --max-age-d needs a value (days; "
                    "0 = unbounded)")
            max_age_d = args[i + 1]
            i += 2
        elif arg.startswith("--max-age-d="):
            max_age_d = arg[len("--max-age-d="):]
            i += 1
        elif arg in ("-h", "--help"):
            outln(CLAIM_REF_HELP)
            return L.RC_OK
        elif arg.startswith("--"):
            die(L.RC_USAGE, "claim-ref: unknown flag '%s'" % arg)
        else:
            if uuid:
                die(L.RC_USAGE, "claim-ref: unexpected extra argument '%s'" % arg)
            uuid = arg
            i += 1
    if not uuid:
        die(L.RC_USAGE, "usage: oc-ledger claim-ref <uuid> [--open]")
    # #631: the bound must be a NUMBER. A typo (``--max-age-d 7d``) used to be
    # accepted by this parse and then read by the helper as 0 = UNBOUNDED, so a
    # caller who believed they had a bound had none — an accepted-but-inert flag
    # is indistinguishable from an honoured one, which is the exact class #631
    # fixes.
    if max_age_d and not _MAX_AGE_SHAPE.match(max_age_d) \
            or max_age_d.count(".") > 1:
        die(L.RC_USAGE, "claim-ref: --max-age-d must be a number of days (got "
            "'%s'; 0 = unbounded)" % max_age_d)
    # #441 / Design Q shape 1: enforce the DOMAIN the usage line declares. Only
    # PRESENCE was checked before, so any non-empty string was taken as the
    # actor and the free substring match did the rest — two plain issue numbers
    # failed in OPPOSITE directions, rc 0 and rc 3, so a caller could not learn
    # the failure MODE from the argument and a typo was reported as a fact about
    # the ledger:
    #   claim-ref 440  -> 402, rc 0   (440 sits inside 52058a75-e94b-4400-9e07-…)
    #   claim-ref 2fae -> 436, rc 0   (a four-character fragment)
    #   claim-ref 441  -> 393, rc 0   (this defect's OWN issue number)
    #   claim-ref 438  -> "no claim event by 438", rc 3
    # ACCEPTED: a canonical uuid, or the M2-24 composed '<role> <uuid>' form
    # derive_by EMITS (round-trip guard: the TRAILING token must be a uuid).
    if " " in uuid:
        if not L.is_uuid(uuid.rsplit(" ", 1)[1]):
            die(L.RC_USAGE, "claim-ref: '%s' is neither a session uuid nor the "
                "'<role> <uuid>' form — usage: oc-ledger claim-ref <uuid> "
                "[--open]. To resolve an ISSUE number, run: oc-ledger claims "
                "<N>" % uuid)
    elif not L.is_uuid(uuid):
        die(L.RC_USAGE, "claim-ref: '%s' is not a session uuid — the ledger is "
            "addressed by session uuid, and a bare issue number or a fragment "
            "substring-matches a FOREIGN lane and answers with ITS claim. "
            "Usage: oc-ledger claim-ref <uuid> [--open]. To resolve an ISSUE "
            "number, run: oc-ledger claims <N>" % uuid)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    if open_only:
        out, diag = _latest_open_claim_issue(
            ledger, uuid, float(max_age_d) if max_age_d else 0.0)
        if out is None:
            die(L.RC_REFUSED, "claim-ref --open: %s" % diag)
    else:
        out, diag = _latest_claim_issue(ledger, uuid)
        if out is None:
            die(L.RC_REFUSED, "claim-ref: %s" % diag)
    outln(str(out))
    return L.RC_OK


# ---------------------------------------------------------------------------
# confirm — verify the lane's claim against the live tracker, flip confirmed
# ---------------------------------------------------------------------------
CONFIRM_HELP = "usage: oc-ledger confirm <uuid> [--gh <cmd>]"


def _gh_issue_exists(gh: str, issue, repo: str) -> bool:
    try:
        proc = L.child_process([gh, "issue", "view", str(issue), "--repo", repo,
                                "--json", "number"],
                               capture_output=True, text=True)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def cmd_confirm(ledger, args):
    if args and args[0] in ("-h", "--help"):
        outln(CONFIRM_HELP)
        return L.RC_OK
    uuid = ""
    gh = os.environ.get("GH_BIN") or "gh"
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--gh":
            if i + 1 >= len(args) or not args[i + 1]:
                die(L.RC_USAGE, "confirm: --gh needs a command")
            gh = args[i + 1]
            i += 2
        elif arg.startswith("--"):
            die(L.RC_USAGE, "confirm: unknown flag '%s'" % arg)
        else:
            if not uuid:
                uuid = arg
            i += 1
    if not uuid:
        die(L.RC_USAGE, CONFIRM_HELP)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    workers = _unified(ledger).get("workers")
    rows = [row for row in (workers if isinstance(workers, list) else [])
            if isinstance(row, dict)
            and L.to_string(_keep(row.get("uuid"), "")) == uuid]
    if not rows:
        die(L.RC_REFUSED, "confirm: unknown worker uuid %s" % uuid)
    # claim->issue derivation delegated to the single owner (E4, v0.4.77)
    issue, diag = _latest_claim_issue(ledger, uuid)
    if issue is None:
        die(L.RC_REFUSED, "confirm: %s" % diag)
    # live issue existence check, against ALL home trackers (injectable gh shim
    # keeps the selftest offline). v0.4.284: a claim may name any of the three,
    # so resolvable in ANY passes. Fail-safe in the direction that matters — a
    # confirm that cannot find the issue ANYWHERE is still refused, never taken.
    if not any(_gh_issue_exists(gh, issue, repo) for repo in HOME_REPOS):
        die(L.RC_REFUSED, "confirm: issue #%s not resolvable on any home tracker"
            % issue)
    t = L.now_iso()
    # D-2 (HQ d72bd52d, 2026-09-12): ``by`` must CONTAIN the uuid, because
    # cmd_claims links a closure with ``(.value.by // "") | contains($u)``. The
    # composed "<role> <uuid>" form satisfies it and stays readable.
    role = L.to_string(_keep(rows[0].get("role"), ""))
    by = "%s %s" % (role, uuid) if role else uuid

    def _confirm_locked():
        n = L.max_n(ledger) + 1

        def transform(doc):
            for row in doc.get("workers") or []:
                if not (isinstance(row, dict)
                        and L.to_string(_keep(row.get("uuid"), "")) == uuid):
                    continue
                row["confirmed"] = True
                # D-2: the top-level .events row is the one cmd_claims SCANS —
                # without it `confirm` flips .confirmed but the claim still
                # reads OPEN forever.
                sub = row.get("events")
                if not isinstance(sub, list):
                    sub = [] if sub is None else [sub]
                row["events"] = sub + [{"t": t, "kind": "confirm",
                                        "issue": "#%s" % issue}]
            events_ = doc.get("events")
            if events_ is None:
                events_ = doc["events"] = []
            events_.append({
                "n": n, "t": t, "by": by, "kind": "confirm",
                "what": "CONFIRM #%s — claim verified live "
                        "(workers[].confirmed=true)" % issue})
            doc["updated_at"] = t
            return None
        L.atomic_write(ledger, transform)
        outln("confirmed: %s (claim #%s verified live)" % (uuid, issue))
        L.git_state_commit(ledger, "ledger confirm %s (#%s)" % (uuid, issue))

    L.with_lock(ledger, _confirm_locked)
    return L.RC_OK


# ---------------------------------------------------------------------------
# sweep-closed-claims — release claims whose issue shipped and closed
# ---------------------------------------------------------------------------
SWEEP_HELP = "usage: oc-ledger sweep-closed-claims [--dry-run]"


class _ProbeFailed(Exception):
    """The gh probe could not answer. Converted to the bash's rc 3 by the verb.

    A ``gh`` failure is LOUD, never a silent clean: an empty ``closed_map`` from
    a failed probe used to print "All open claims map to OPEN issues." —
    absence read as a verdict. The diagnostic has already been printed by the
    time this is raised (see ``_probe_issue_state``).
    """


def _probe_issue_state(state: str) -> dict:
    """number -> {"title", "repos"} across the three home trackers.

    DELIBERATE DIVERGENCE, rc preserved: the bash captures this probe's stderr
    into ``$TMPDIR/oc-sweep-closed-claims.$$.err`` and then ``rm -f``s it
    WITHOUT READING, so an operator sees only "scan failed (rc 4)" and never the
    reason — the exact silence-as-verdict class this file's own comments rail
    against. The rc and the final message are byte-identical to the bash; the
    gh diagnostic is ADDITIONALLY printed. Nothing the bash prints is lost.


    #38: the three home trackers have OVERLAPPING number spaces, so one number
    can exist on more than one of them with a DIFFERENT title on each. The claim
    token it is matched against is a bare integer — the slug is DISCARDED — so
    the token cannot say which tracker it means. The first-probed repo title is
    therefore kept for display only, and the repos a number was seen on ride
    beside it so the emit can withhold a title the token cannot support.
    """
    out = {}
    for repo in HOME_REPOS:
        try:
            proc = L.child_process(
                ["gh", "issue", "list", "--repo", repo, "--state", state,
                 "--limit", "1000", "--json", "number,title"],
                capture_output=True, text=True)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            errln("gh issue list --repo %s --state %s failed (rc 1): %s"
                  % (repo, state, exc))
            raise _ProbeFailed()
        if proc.returncode != 0:
            errln("gh issue list --repo %s --state %s failed (rc %d): %s"
                  % (repo, state, proc.returncode,
                     (proc.stderr or "").strip()[:200]))
            raise _ProbeFailed()
        try:
            for item in json.loads(proc.stdout or "[]"):
                ent = out.setdefault(item["number"],
                                     {"title": item.get("title", ""),
                                      "repos": []})
                ent["repos"].append(repo)
        except (ValueError, KeyError, TypeError) as exc:
            errln("failed to parse %s issues (%s): %s" % (repo, state, exc))
            raise _ProbeFailed()
    return out


def cmd_sweep_closed_claims(ledger, args):
    """Release OPEN claim rows whose issue is CLOSED on a home tracker and OPEN
    on none (v0.4.284 — three trackers, overlapping number spaces).

    #485: the verdict is a claim about a POPULATION, so the population is read in
    FULL. Only the CLOSED list was fetched before, which made a token absent
    from it indistinguishable from a token whose issue is genuinely OPEN — and
    also from a token naming an issue that does not exist on ANY home tracker,
    which is the shape that printed "All open claims map to OPEN issues." for 15
    days while n=1678 stayed OPEN against work that had shipped. Every token now
    lands in exactly one of three classes: CLOSED (released), OPEN (the intended
    clean case), UNRESOLVED (reported, never released, and it WITHHOLDS the
    clean verdict). The summary line carries the four counts so the verdict can
    be checked against the population it names.

    #314: this verb had NO WRITE PATH in the bash — ``--dry-run`` was parsed and
    the live branch printed the same scan and exited 0, so the flag changed
    nothing. A claim on a shipped-and-closed issue therefore stayed OPEN until
    its claimant hand-stamped a redundant closure.

    A ``gh`` failure is LOUD (rc 4), never a silent clean: an empty closed_map
    from a failed probe used to print the clean verdict — absence read as a
    verdict.
    """
    dry_run = False
    for arg in args:
        if arg == "--dry-run":
            dry_run = True
        elif arg in ("-h", "--help"):
            outln(SWEEP_HELP)
            return L.RC_OK
        else:
            die(L.RC_USAGE, "sweep-closed-claims: unknown argument '%s'" % arg)
    if not L.ledger_ok(ledger):
        die(L.RC_REFUSED, "ledger missing or unparseable: %s" % ledger)
    oc = _oc_claims()
    events = _unified(ledger).get("events")
    open_rows = oc.open_claims(events if isinstance(events, list) else [])
    if not open_rows:
        outln("All open claims map to OPEN issues (0 0 0 0 = claim rows, open "
              "tokens, closed tokens, unresolvable tokens).")
        return L.RC_OK

    try:
        closed_map = _probe_issue_state("closed")
        open_map = _probe_issue_state("open")
    except _ProbeFailed:
        # The bash's own rc here: the embedded python exits 4, the shell sees it
        # and dies 3 with this message. Same rc, same words, plus the reason.
        die(L.RC_REFUSED, "sweep-closed-claims: scan failed (rc 4) — ledger or "
            "GitHub probe")

    n_open = 0
    closed_rows = []
    unresolved = []
    for claim in open_rows:
        for tok in claim["tokens"]:
            # OPEN WINS: tested FIRST, so a token open on ANY home repo is never
            # released on the strength of a same-numbered CLOSED issue elsewhere.
            if tok in open_map:
                n_open += 1
            elif tok in closed_map:
                ent = closed_map[tok]
                repos = ent["repos"]
                # #38: print a title ONLY when the number was seen on exactly
                # one home tracker. On an overlap the bare token names no repo,
                # so the first-probed repo title is a specificity the claim does
                # not carry — the release verdict is still correct (closed
                # everywhere, open nowhere) but the title is withheld and the
                # ambiguity named.
                if len(repos) == 1:
                    label = (ent["title"] or "")[:60]
                else:
                    label = ("no single title — #%d exists on %d home trackers "
                             "(%s)" % (tok, len(repos), ", ".join(repos)))
                closed_rows.append((tok, claim["by"], label))
            else:
                unresolved.append((tok, claim["by"], claim["what"][:60]))
    counts = "%d %d %d %d" % (len(open_rows), n_open, len(closed_rows),
                              len(unresolved))

    # #485: report the UNRESOLVABLE class before any verdict. A token that names
    # no fork issue in EITHER state is neither a stale claim nor a live one: it
    # is a claim this verb cannot judge, and counting it as open is what made
    # the clean verdict a lie.
    if unresolved:
        outln("UNRESOLVED: %d claim token(s) name no issue on any home tracker "
              "(neither OPEN nor CLOSED):" % len(unresolved))
        for tok, by, what in unresolved:
            outln("  Issue #%s is on no home tracker — claimed by %s (%s)"
                  % (tok, by, what))
        outln("  These claims are NOT released and NOT clean. A common cause is "
              "a")
        outln("  reference to a repository we do not track (a third-party slug, "
              "or a")
        outln("  tracker added after this list was last updated): the number "
              "resolves")
        outln("  there, never here.")

    if not closed_rows:
        if unresolved:
            return L.RC_OK
        outln("All open claims map to OPEN issues (%s = claim rows, open "
              "tokens, closed tokens, unresolvable tokens)." % counts)
        return L.RC_OK

    issues = sorted({row[0] for row in closed_rows})
    outln("Found %d open claim(s) across %d CLOSED issue(s):"
          % (len(closed_rows), len(issues)))
    for tok, by, label in closed_rows:
        outln("  Issue #%s (CLOSED: %s) claimed by %s" % (tok, label, by))

    if dry_run:
        outln("--dry-run: no ledger rows written. Re-run without --dry-run to "
              "release these claims.")
        return L.RC_OK

    released = 0
    for iss in issues:
        rc = cmd_stamp(ledger, ["unclaim",
                                "#%s — closed-issue stale claim sweep" % iss])
        if rc != L.RC_OK:
            die(L.RC_IO, "sweep-closed-claims: unclaim stamp failed for #%s"
                % iss)
        released += 1
    outln("Released %d closed issue(s) — one unclaim row addressed to each."
          % released)
    return L.RC_OK


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
READ_VERBS = ("ok", "law-digest", "check-version", "cadence", "events", "tail",
              "workers", "worker", "roster", "claims", "lessons", "duplicates",
              "mode")

# The full declared surface, in the bash tool's own order (its `--verbs` arm).
ALL_VERBS = ("stamp", "fixture", "sync", "check-version", "law-digest",
             "cadence", "ack", "enroll", "promote", "retire", "commit-pending",
             "confirm", "migrate", "claim", "claim-ref", "claims",
             "sweep-closed-claims", "lessons", "roster", "events", "tail",
             "workers", "worker", "ok", "duplicates", "mode")

_HANDLERS = {
    "ok": cmd_ok,
    "law-digest": cmd_law_digest,
    "check-version": cmd_check_version,
    "cadence": cmd_cadence,
    "events": cmd_events,
    "tail": cmd_events,
    "workers": cmd_workers,
    "worker": cmd_worker,
    "roster": cmd_roster,
    "claims": cmd_claims,
    "lessons": cmd_lessons,
    "duplicates": cmd_duplicates,
    "mode": cmd_mode,
    # --- phase 3: the write verbs ---
    "stamp": cmd_stamp,
    "fixture": cmd_fixture,
    "ack": cmd_ack,
    "enroll": cmd_enroll,
    "promote": cmd_promote,
    "retire": cmd_retire,
    "claim": cmd_claim,
    "claim-ref": cmd_claim_ref,
    "confirm": cmd_confirm,
    "sweep-closed-claims": cmd_sweep_closed_claims,
}

# The verbs this file does NOT implement yet plus the one verb the bash keeps
# for the flip. Naming them explicitly means a caller gets the same rc 2 and a
# message that says WHY, instead of a bare "unknown verb".
_WRITE_VERBS = ("selftest",)

_HINTS = {
    "note": "unknown verb '%s' — did you mean 'events' or 'stamp note'?",
    "show": "unknown verb '%s' — did you mean 'events' or 'stamp note'?",
    "list": "unknown verb '%s' — did you mean 'events' or 'stamp note'?",
    "append": "unknown verb '%s' — did you mean 'stamp'?",
    "add": "unknown verb '%s' — did you mean 'stamp'?",
    "entry": "unknown verb '%s' — did you mean 'stamp'?",
    "record": "unknown verb '%s' — did you mean 'stamp'?",
    "roster-enroll": "unknown verb '%s' — did you mean 'enroll'?",
    "roster-amend": "unknown verb '%s' — did you mean 'promote' or 'enroll'?",
    "roster-update": "unknown verb '%s' — did you mean 'promote' or 'enroll'?",
    "roster-retire": "unknown verb '%s' — did you mean 'retire'?",
    "kinds": "unknown verb '%s' — kinds are listed in --help",
    "push-mirror": "unknown verb '%s' — did you mean 'sync' or 'commit-pending'?",
    "version-publish": "unknown verb '%s' — did you mean 'sync --version <v>'?",
}


def main(argv) -> int:
    ledger, selftest, args = parse_global(argv)

    if args and args[0] in ("-h", "--help"):
        outln(USAGE)
        return L.RC_OK
    # NOT a usage-and-exit-0: the bash's dispatcher sees an empty subcommand and
    # falls through to its unknown-verb arm, so `oc-ledger` with no args is rc 2.
    # A caller scripting `oc-ledger` bare must not read success.
    if selftest:
        # Phase 4 owns the battery; the bash selftest still gates the port.
        die(L.RC_USAGE, "selftest is not part of the read-only port yet — run "
            "the bash tool's battery: bash tools/state/oc-ledger --selftest")

    sub = args[0] if args else ""
    rest = args[1:]
    if sub == "--verbs":
        # The DECLARED surface, byte-identical to the bash tool. The write verbs
        # are listed because they exist at the live path; in THIS file each one
        # refuses rc 2 with a message naming the bash tool, so the declaration
        # is not a claim that they are ported yet.
        outln(VERBS_LINE)
        return L.RC_OK

    handler = _HANDLERS.get(sub)
    if handler is not None:
        return handler(ledger, rest)
    if sub in _WRITE_VERBS:
        die(L.RC_USAGE, "%s is a write verb and is not part of the read-only "
            "port yet — use the bash tool (tools/state/oc-ledger)" % sub)
    hint = _HINTS.get(sub)
    if hint:
        die(L.RC_USAGE, hint % sub)
    die(L.RC_USAGE, "unknown verb '%s' — usage: oc-ledger <%s> | --verbs | "
        "--selftest" % (sub, USAGE_VERBS))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except L.LedgerError as exc:
        # A store-layer refusal surfaces with the SAME diagnostic shape the
        # bash tool prints, and its rc is carried, never inferred.
        sys.stderr.write("%s: %s\n" % (PROG, exc.message))
        sys.exit(exc.rc)
    except BrokenPipeError:                      # pragma: no cover - pipe close
        try:
            sys.stdout.close()
        except OSError:
            pass
        sys.exit(L.RC_OK)
    except KeyboardInterrupt:                    # pragma: no cover
        sys.exit(130)
