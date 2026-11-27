#!/usr/bin/env python3
# =============================================================================
# oc-ledger (python) — the ONE sanctioned write path for the workers ledger.
#
# PHASE 2 OF THE PORT (factory #204): READ-ONLY VERBS ONLY.
#   ok · law-digest · check-version · cadence · events · tail · workers ·
#   worker · roster · claims · lessons · duplicates · mode
#
# The bash tool at tools/state/oc-ledger is UNCHANGED and remains the live
# write path until the flip. This file is additive: it shares the store + lock
# layer in tools/lib/ledger_core.py, and every read verb here is required to be
# OUTPUT-IDENTICAL to its bash counterpart on the same fixture — that identity
# is the phase-2 gate, not a nicety. Where the bash emits JSON, so does this;
# where it emits TSV or prose, the bytes match.
#
# rc vocabulary (tools/docs/RC-CONTRACT.md) — the SAME numbers, never
# renumbered, because every lane in the fleet keys on them:
#   0 ok · 1 verdict (NO-MATCH / DRIFT / FIRE) · 2 usage ·
#   3 parse-or-load refused · 4 write-fail or lock timeout
#
# STDLIB ONLY, extensionless-sibling precedent: tools/state/oc-questions.
# =============================================================================

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

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
        # The bash pipes the JSON through a SECOND jq for the TSV form, so a
        # non-object element dies there; `.[] | [...]` over the collected rows
        # is the same projection.
        for row in rows:
            if not isinstance(row, dict):
                die(L.RC_REFUSED, "workers: jq failed — ledger unreadable or "
                    "query error")
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
}

# The verbs this file does NOT implement yet (phase 3) plus the two verbs the
# bash keeps for the flip. Naming them explicitly means a caller gets the same
# rc 2 and a message that says WHY, instead of a bare "unknown verb".
_WRITE_VERBS = ("stamp", "fixture", "sync", "ack", "enroll", "promote",
                "retire", "commit-pending", "confirm", "migrate", "claim",
                "claim-ref", "sweep-closed-claims", "selftest")

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
