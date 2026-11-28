"""Ported: ``oc-ledger`` selftest §56-66b — ``roster``, ``--live``,
``--reconcile``, ``duplicates``.

Source: ``tools/state/oc-ledger:4768-4905`` (selftest lines 1998-2135) — 36 of
the 475 ``chk`` calls plus the ``ok || bad`` legs in the same block. Every
assertion message carries the shell name it replaces.

WHAT THIS MODULE PROTECTS
    ``roster`` is the verb every lane uses to turn a ROLE into a session uuid.
    The skill cites it as THE dynamic resolution path in three role files, so a
    wrong answer here does not fail loudly — it sends a lane to hand-assemble a
    uuid, which is the phantom-id class the full-uuid-from-a-receipt law exists
    to prevent. The invariants are therefore:

    * rc 1 is a VERDICT, not an empty list. "no row matches" must be
      distinguishable from "the ledger was unreadable" (rc 3) and from "your
      argument was wrong" (rc 2), because a caller branches on it: rc 1 means
      fall back to session_search, never assemble an id.
    * A RETIRED row is never a dispatch target. It is excluded by default,
      ``--include-retired`` is the ONLY way to see it, and the rc-1 NO-MATCH
      must SAY that retirement is the reason — otherwise a lane reads the
      exclusion as "HQ is unrostered" and stops looking.
    * ``--live`` prefers the BINDING over the ledger's stored ``topic_id``. The
      ledger field is a copy stamped at enroll time and goes stale the moment a
      topic is reassigned; measured over the 32 live-bound workers, 4 had
      drifted and all 4 were lanes that MOVED. The fixture pins the two sources
      to DIFFERENT values (ledger 42 vs binding 55555) so a regression to the
      stored field reddens here rather than in production.
    * ``--reconcile`` exists because that preference makes the drift INVISIBLE.
      So the legs assert the DETECTION (a named mismatch, a count, an explicit
      zero) and then RUN the emitted remedy: #686 measured a remedy line that
      named ``promote --uuid <u>`` while the verb takes the uuid POSITIONALLY,
      so the string was unrunnable and a lane following it had no next step.
      Naming a remedy and executing it are different assertions.
    * ``duplicates`` groups by the FACT ``(kind, what)``, never by the actor —
      the two specimens it exists for carry DIFFERENT ``by`` strings for one
      act, so an actor-keyed grouping finds nothing on exactly those rows.

FIXTURE NOTE
    The shell drives one shared ``$T`` through the whole selftest, so the roster
    block inherits state from everything above it. Here the ``roster_fixture``
    factory rebuilds the exact state that block depends on — aaaa promoted to
    tester2, 2222 toolsmith/topic 39171, W2 tester/topic 42, and one RETIRED
    row — so each test is independent and xdist-safe.

DELIBERATELY NOT PORTED
    * ``enroll-dead-topic-*`` / ``enroll-live-topic-*`` (tool 4906-4920) sit
      just past this block and are owned by ``test_ledger_events.py``.
    * The ``roster: N rows match role~... — add --live`` dispatch nudge is
      asserted as part of ``roster-role-substring`` rather than as its own leg:
      in the shell it is an ``echo`` with no ``chk``, and the count assertion
      already pins the number it announces.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

# The four identities the shell's roster block depends on. Kept as constants so
# a leg that names one of them reads as the fixture fact it is.
W2 = "11111111-2222-3333-4444-555555555555"     # tester, ledger topic 42
WR = "99999999-9999-9999-9999-999999999999"     # retired_compiler, RETIRED
TOOLSMITH = "22222222-2222-2222-2222-222222222222"
AAAA = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"   # the sandbox's own row
WS = "77777777-7777-7777-7777-777777777777"     # enrolled, NO binding
WFALLBACK = "66666666-6666-6666-6666-666666666666"  # enrolled, no binding row
# topic 55555 is the ONLY binding the fixture DB carries; 478 is the dead one.
LIVE_TOPIC = 55555
DEAD_TOPIC = 478


def _run(run_tool, *args, env=None, timeout=120):
    return run_tool([str(TOOL), *args], timeout=timeout, env=env)


@pytest.fixture
def roster_fixture(ledger_sandbox, run_tool):
    """The roster block's starting state, rebuilt from scratch.

    Mirrors ``tools/state/oc-ledger:4789-4797``: the sandbox row is promoted to
    tester2, a toolsmith row is enrolled with a topic and a feature, W2 is the
    tester row at topic 42, and WR is enrolled and then marked RETIRED with a
    direct ledger edit (the shell does the same with ``jq``, because ``retire``
    REMOVES the row and the legs below need a row that still EXISTS and is
    still excluded).
    """
    sb = ledger_sandbox
    for args in (
        ["promote", AAAA, "tester2"],
        ["enroll", TOOLSMITH, "toolsmith", "--topic", "39171", "--feature", "tools"],
        ["enroll", W2, "tester", "--topic", "42"],
        ["enroll", WR, "retired_compiler"],
    ):
        res = _run(run_tool, *args)
        assert res.rc == 0, (
            "roster fixture: %s failed rc=%s\n%s"
            % (" ".join(args), res.rc, res.combined[-600:]))

    doc = L.read_json(sb.ledger)
    for w in doc.get("workers", []):
        if w.get("uuid") == WR:
            w["state"] = "RETIRED"
    sb.ledger.write_text(json.dumps(doc), encoding="utf-8")
    return sb


def _tsv(res) -> list:
    return [ln for ln in res.out.splitlines() if ln.strip()]


def _col(line: str, idx: int) -> str:
    parts = line.split("\t")
    return parts[idx] if len(parts) > idx else ""


def _sqlite(path, script: str):
    """Build the fixture session DB with the tool's OWN reader (#371).

    The shell does this with ``"$_OC_DIR/lib/oc_sqlite"``, not the ``sqlite3``
    CLI, because the CLI was absent from this box and every ``roster --live``
    leg skipped silently behind a ``command -v`` guard while the production verb
    was dead. Using the same helper keeps that property.
    """
    return subprocess.run(
        [str(cf.TOOLS_DIR / "lib" / "oc_sqlite"), str(path), script],
        capture_output=True, text=True)


def _session_db(tmp_path, *, with_binding=True) -> Path:
    """The shell's ``sessions``/``session_bindings`` fixture (tool 4810-4816).

    W2 is a live session WITH a binding at 55555; WS is a live SUBAGENT (title
    ``subagent:``), which the liveness query must exclude; WFALLBACK is live
    with no binding at all, so its topic can only come from the ledger field.
    """
    db = Path(tmp_path) / "sessions.db"
    script = (
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, archived_at TEXT, title TEXT);\n"
        "CREATE TABLE session_bindings (session_id TEXT PRIMARY KEY, channel TEXT,"
        " chat_id TEXT, thread_id INTEGER);\n"
        "INSERT INTO sessions VALUES ('%s', NULL, NULL);\n"
        "INSERT INTO sessions VALUES ('%s', NULL, 'subagent: probe');\n"
        "INSERT INTO sessions VALUES ('%s', NULL, NULL);\n"
        % (W2, WS, WFALLBACK))
    if with_binding:
        script += ("INSERT INTO session_bindings VALUES ('%s', 'telegram', '-100', %d);\n"
                   % (W2, LIVE_TOPIC))
    res = _sqlite(db, script)
    assert res.returncode == 0, (
        "[roster-live-fixture-db-rc] the fixture session DB could not be built "
        "rc=%s\n%s" % (res.returncode, res.stderr[-600:]))
    return db


# =============================================================================
# plain roster — role resolution, retired exclusion, JSON, usage arms
# =============================================================================
def test_roster_resolves_a_role_to_full_uuids(roster_fixture, run_tool):
    """``roster-all-*`` + ``roster-role-*`` + ``roster-prints-full-uuid``.

    The FULL uuid matters: a prefix resolves against nothing downstream, and
    the shell's own history is a lane that hand-assembled a partial id. So the
    assertion is not "a row exists" but "the row carries the 36-char uuid".
    """
    all_rows = _run(run_tool, "roster")
    assert all_rows.rc == 0, (
        "[roster-all-rc] rc=%s, want 0\n%s"
        % (all_rows.rc, all_rows.combined[-600:]))
    rows = _tsv(all_rows)
    assert len(rows) == 3, (
        "[roster-all-count] %d rows, want 3 — the RETIRED row is excluded by "
        "default (law 9)\n%s" % (len(rows), all_rows.out))

    uuids = [_col(r, 0) for r in rows]
    assert W2 in uuids, (
        "[roster-prints-full-uuid] %r not in %r — a caller gets a uuid it can "
        "use, never a prefix it has to complete" % (W2, uuids))
    assert all(len(u) == 36 for u in uuids), (
        "[roster-prints-full-uuid] a row carries a non-uuid first column: %r"
        % (uuids,))

    one = _run(run_tool, "roster", "--role", "tester2")
    assert one.rc == 0, (
        "[roster-role-rc] rc=%s, want 0\n%s" % (one.rc, one.combined[-600:]))
    r_rows = _tsv(one)
    assert len(r_rows) == 1, (
        "[roster-role-count] %d rows for role tester2, want 1\n%s"
        % (len(r_rows), one.out))
    assert _col(r_rows[0], 1) == "tester2", (
        "[roster-role-label] role column is %r, want 'tester2' — the filter "
        "must not fall back to a neighbouring role"
        % (_col(r_rows[0], 1),))


def test_the_role_filter_is_a_case_insensitive_substring(roster_fixture, run_tool):
    """``roster-role-ci-rc`` + ``roster-role-substring``.

    ``TESTER`` must hit BOTH ``tester`` and ``tester2``. A case-sensitive or
    exact compare returns 1 row here, which is the defect the leg pins: the
    callers pass role words from prose, in whatever case the doc used.
    """
    res = _run(run_tool, "roster", "--role", "TESTER")
    assert res.rc == 0, (
        "[roster-role-ci-rc] rc=%s, want 0 — the match is case-insensitive\n%s"
        % (res.rc, res.combined[-600:]))
    rows = _tsv(res)
    assert len(rows) == 2, (
        "[roster-role-substring] %d rows for 'TESTER', want 2 (tester + "
        "tester2) — the filter is a SUBSTRING match\n%s" % (len(rows), res.out))
    roles = sorted(_col(r, 1) for r in rows)
    assert roles == ["tester", "tester2"], (
        "[roster-role-substring] roles %r, want tester + tester2" % (roles,))


def test_a_retired_row_is_excluded_by_default_and_says_why(roster_fixture, run_tool):
    """``roster-retired-excluded-*`` + ``roster-include-retired-*`` (law 9).

    Both halves, because each alone is satisfiable by a broken implementation:
    excluding the row but not SAYING so leaves a lane reading rc 1 as "no such
    lane ever existed", and including it by default puts a retired lane in a
    dispatch target set. ``e756b84b`` (retired_compiler) was FIRST in two HQ
    fanout waves because the resolver ignored ``.state``.
    """
    excluded = _run(run_tool, "roster", "--role", "retired_compiler")
    assert excluded.rc == 1, (
        "[roster-retired-excluded-rc1] rc=%s, want 1 — a retired-only role is "
        "a NO-MATCH VERDICT\n%s" % (excluded.rc, excluded.combined[-600:]))
    assert not excluded.out.strip(), (
        "[roster-retired-excluded-empty] stdout is %r, want empty — the row is "
        "excluded from the listing, not merely from the count"
        % (excluded.out,))
    assert "RETIRED row" in excluded.err, (
        "[roster-retired-stderr-reason] stderr does not name retirement as the "
        "reason:\n%s" % (excluded.err[-600:],))

    included = _run(run_tool, "roster", "--role", "retired_compiler",
                    "--include-retired")
    assert included.rc == 0, (
        "[roster-include-retired-rc] rc=%s, want 0 — --include-retired is the "
        "ONLY way to see the row\n%s" % (included.rc, included.combined[-600:]))
    rows = _tsv(included)
    assert len(rows) == 1, (
        "[roster-include-retired-count] %d rows, want 1\n%s"
        % (len(rows), included.out))
    assert _col(rows[0], 0) == WR, (
        "[roster-include-retired-row] uuid %r, want %s — the row that comes "
        "back must be the retired one" % (_col(rows[0], 0), WR))

    every = _run(run_tool, "roster", "--include-retired")
    assert every.rc == 0, (
        "[roster-include-retired-all-rc] rc=%s, want 0\n%s"
        % (every.rc, every.combined[-600:]))
    assert len(_tsv(every)) == 4, (
        "[roster-include-retired-all-count] %d rows, want 4 (the 3 live plus "
        "the retired one)\n%s" % (len(_tsv(every)), every.out))


def test_a_nomatch_is_a_verdict_not_an_empty_list(roster_fixture, run_tool):
    """``roster-nomatch-rc1`` + ``roster-nomatch-empty``.

    rc 1 with EMPTY stdout: a caller branches on the code. Printing a row while
    returning 1 would let a script use the row and a human trust the code.
    """
    res = _run(run_tool, "roster", "--role", "zzznope")
    assert res.rc == 1, (
        "[roster-nomatch-rc1] rc=%s, want 1 — NO-MATCH is a verdict\n%s"
        % (res.rc, res.combined[-600:]))
    assert not res.out.strip(), (
        "[roster-nomatch-empty] stdout is %r, want empty" % (res.out,))


def test_roster_json_is_an_array_of_objects_with_every_field(roster_fixture,
                                                             run_tool):
    """``roster-json-*``.

    ``--json`` is the machine surface, so it is asserted by PARSING it: a
    ``length == 3`` check on a string would pass on a document with the wrong
    shape, and ``has()`` rather than truthiness because ``last_acked`` is
    legitimately null on a row that has never acked.
    """
    res = _run(run_tool, "roster", "--json")
    assert res.rc == 0, (
        "[roster-json-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    doc = json.loads(res.out)
    assert isinstance(doc, list) and len(doc) == 3, (
        "[roster-json-array] %r is not a 3-element array"
        % (doc if not isinstance(doc, list) else "len=%d" % len(doc),))

    row = next((r for r in doc if r.get("uuid") == W2), None)
    assert row is not None, "[roster-json-fields] %s absent from %r" % (W2, doc)
    missing = {"role", "topic_id", "feature", "last_acked"} - set(row)
    assert not missing, (
        "[roster-json-fields] %s missing %r — the JSON surface is the machine "
        "contract, so every field must be PRESENT (null is fine)"
        % (W2, sorted(missing)))


@pytest.mark.parametrize("argv, want_rc, name", [
    (["roster", "--bogus"], 2, "roster-unknown-flag-rc2"),
    (["roster", "--role"], 2, "roster-role-novalue-rc2"),
])
def test_roster_usage_errors_are_rc2(roster_fixture, run_tool, argv, want_rc,
                                     name):
    """An unrecognised flag is REFUSED, never silently ignored into a positional."""
    res = _run(run_tool, *argv)
    assert res.rc == want_rc, (
        "[%s] rc=%s, want %s\n%s" % (name, res.rc, want_rc,
                                     res.combined[-600:]))


def test_roster_help_and_an_unreadable_ledger(roster_fixture, run_tool,
                                              tmp_path):
    """``roster-help-rc0`` + ``roster-bad-ledger-rc3``.

    The two rcs that bracket the usage arms: help is 0 (so ``--help`` is never
    a failure a caller has to special-case) and an unreadable ledger is 3 (so
    "the ledger is broken" is never confused with "your role matched nothing").
    """
    helped = _run(run_tool, "roster", "-h")
    assert helped.rc == 0, (
        "[roster-help-rc0] rc=%s, want 0\n%s"
        % (helped.rc, helped.combined[-600:]))

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    res = _run(run_tool, "roster", env={"OC_LEDGER": str(bad)})
    assert res.rc == 3, (
        "[roster-bad-ledger-rc3] rc=%s, want 3 — an unparseable ledger is a "
        "HARD failure, not an empty roster\n%s" % (res.rc, res.combined[-600:]))


# =============================================================================
# --live: the binding is the route, the ledger field is only a fallback
# =============================================================================
def test_live_prefers_the_binding_over_the_stored_topic(roster_fixture, run_tool,
                                                        tmp_path):
    """``roster-live-*`` + ``roster-live-derives-topic-from-binding``.

    THE discriminating leg of the block. The fixture pins ledger ``topic_id``
    42 and binding ``thread_id`` 55555 to DIFFERENT values, so a regression to
    the stored field cannot pass: measured over the 32 live-bound workers, 4
    had drifted and every one of them was a lane that had MOVED. A wrong topic
    does the most damage exactly there — a dispatch to a stale topic reaches
    nobody, or the wrong lane.
    """
    db = _session_db(tmp_path)
    env = {"OC_LEDGER_DB": str(db)}

    res = _run(run_tool, "roster", "--role", "TESTER", "--live", env=env)
    assert res.rc == 0, (
        "[roster-live-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    rows = _tsv(res)
    assert len(rows) == 1, (
        "[roster-live-count] %d rows, want 1 — only W2 is a live session that "
        "matches TESTER\n%s" % (len(rows), res.out))
    assert _col(rows[0], 0) == W2, (
        "[roster-live-keeps-live-row] uuid %r, want %s"
        % (_col(rows[0], 0), W2))
    assert _col(rows[0], 2) == str(LIVE_TOPIC), (
        "[roster-live-derives-topic-from-binding] topic column is %r, want "
        "'%d' — the BINDING is the delivery route; the ledger's stored 42 is a "
        "copy that goes stale when a topic is reassigned"
        % (_col(rows[0], 2), LIVE_TOPIC))


def test_a_live_row_with_no_binding_falls_back_to_the_stored_topic(
        roster_fixture, run_tool, tmp_path):
    """``roster-live-fallback-*`` + ``roster-nonlive-keeps-stored-topic``.

    The fallback and its NEGATIVE CONTROL. WFALLBACK is a live session with no
    ``session_bindings`` row, so 777 can only come from the ledger. Without
    ``--live`` the stored field must be untouched (42 for W2), because every
    caller that never asked for a live read gets byte-identical output to
    before the feature existed.
    """
    db = _session_db(tmp_path)
    env = {"OC_LEDGER_DB": str(db)}
    enrolled = _run(run_tool, "enroll", WFALLBACK, "fallbackprobe", "--topic", "777")
    assert enrolled.rc == 0, (
        "fixture: enrolling the fallback probe failed rc=%s\n%s"
        % (enrolled.rc, enrolled.combined[-600:]))

    fb = _run(run_tool, "roster", "--role", "fallbackprobe", "--live", env=env)
    assert fb.rc == 0, (
        "[roster-live-fallback-rc] rc=%s, want 0 — a live row with no binding "
        "is still a row\n%s" % (fb.rc, fb.combined[-600:]))
    topics = [_col(r, 2) for r in _tsv(fb) if _col(r, 2) != "-"]
    assert topics == ["777"], (
        "[roster-live-fallback-uses-stored-topic] topics %r, want ['777'] — "
        "with no binding the ledger's stored topic is the only source, and 777 "
        "is deliberately unlike every binding in the fixture" % (topics,))

    nonlive = _run(run_tool, "roster", "--role", "TESTER")
    w2_rows = [r for r in _tsv(nonlive) if _col(r, 0) == W2]
    assert w2_rows and _col(w2_rows[0], 2) == "42", (
        "[roster-nonlive-keeps-stored-topic] topic column is %r, want '42' — "
        "WITHOUT --live the stored field is untouched, so the historical output "
        "stays byte-compatible"
        % ([_col(r, 2) for r in w2_rows],))


def test_a_subagent_is_not_live_and_a_missing_db_is_a_hard_failure(
        roster_fixture, run_tool, tmp_path):
    """``roster-live-subagent-excluded`` + ``roster-live-json-nomatch-rc1`` +
    ``roster-live-db-missing-rc3``.

    Three rcs that must stay distinct. A subagent row is NOT a live lane (its
    title marks it), so selecting one is a rc-1 NO-MATCH rather than a row — a
    lane dispatching to a subagent's id reaches nothing. And a missing session
    DB is rc 3, never an empty roster that reads as "no such lane".
    """
    db = _session_db(tmp_path)
    env = {"OC_LEDGER_DB": str(db)}
    enrolled = _run(run_tool, "enroll", WS, "subprobe")
    assert enrolled.rc == 0, (
        "fixture: enrolling the subagent probe failed rc=%s\n%s"
        % (enrolled.rc, enrolled.combined[-600:]))

    sub = _run(run_tool, "roster", "--role", "subprobe", "--live", env=env)
    assert sub.rc == 1, (
        "[roster-live-subagent-excluded] rc=%s, want 1 — an archived/subagent "
        "row is not live\n%s" % (sub.rc, sub.combined[-600:]))

    sub_json = _run(run_tool, "roster", "--role", "subprobe", "--live", "--json",
                    env=env)
    assert sub_json.rc == 1, (
        "[roster-live-json-nomatch-rc1] rc=%s, want 1 — the JSON surface keeps "
        "the same verdict as the text one\n%s"
        % (sub_json.rc, sub_json.combined[-600:]))

    missing = _run(run_tool, "roster", "--live",
                   env={"OC_LEDGER_DB": str(tmp_path / "nope.db")})
    assert missing.rc == 3, (
        "[roster-live-db-missing-rc3] rc=%s, want 3 — an unreadable session DB "
        "is a HARD fail, never an empty roster\n%s"
        % (missing.rc, missing.combined[-600:]))


# =============================================================================
# --reconcile: the drift the table silently PREFERS away
# =============================================================================
def test_reconcile_names_the_drift_counts_it_and_emits_a_RUNNABLE_remedy(
        roster_fixture, run_tool, tmp_path):
    """``reconcile-*`` — the whole J-3 detection contract (#686).

    The fixture is the drifted case by construction (ledger 42, binding 55555),
    which is why the table above cannot show it: ``--live`` already prefers the
    binding. ``--reconcile`` is the only surface where the mismatch is visible.

    ``reconcile-remedy-runs`` / ``-applied`` are the #686 fix. The leg used to
    assert the string ``promote --uuid <u> --topic <t>`` — pinning the DEFECT as
    spec — while ``promote`` takes the uuid POSITIONALLY, so that exact form
    died rc 2 "uuid shape invalid: '--uuid'" and a lane reading it, trusting it
    and running it had no next step. So this leg EXECUTES the emitted remedy
    against a COPY of the ledger and asserts the topic actually moved.
    """
    db = _session_db(tmp_path)
    env = {"OC_LEDGER_DB": str(db)}

    res = _run(run_tool, "roster", "--role", "TESTER", "--live", "--reconcile",
               env=env)
    assert res.rc == 0, (
        "[reconcile-rc] rc=%s, want 0 — --reconcile REPORTS, it never refuses\n%s"
        % (res.rc, res.combined[-800:]))
    err = res.err
    assert "BINDING-MISMATCH" in err and "stored=42 live=55555" in err, (
        "[reconcile-names-the-drift] stderr does not name both values — the "
        "detection is the whole point, and 'stored=42 live=55555' is what makes "
        "it actionable:\n%s" % (err[-800:],))

    remedy_lines = [ln for ln in err.splitlines()
                    if "reconcile with: oc-ledger " in ln]
    assert remedy_lines, (
        "[reconcile-names-the-remedy] no remedy line emitted:\n%s" % (err[-800:],))
    remedy = remedy_lines[0].split("reconcile with: oc-ledger ", 1)[1].strip()
    assert remedy.startswith("promote %s " % W2), (
        "[reconcile-names-the-remedy] remedy is %r, want it to start "
        "'promote %s ...' — the uuid is POSITIONAL (#686)" % (remedy, W2))
    assert "--topic %d" % LIVE_TOPIC in remedy, (
        "[reconcile-names-the-remedy] remedy %r does not carry --topic %d"
        % (remedy, LIVE_TOPIC))

    copy = Path(tmp_path) / "ledger-remedy.json"
    copy.write_text(roster_fixture.ledger.read_text(encoding="utf-8"),
                    encoding="utf-8")
    ran = run_tool([str(TOOL), *remedy.split()], timeout=120,
                   env={"OC_LEDGER": str(copy)})
    assert ran.rc == 0, (
        "[reconcile-remedy-runs] the EMITTED remedy exited rc=%s — a remedy "
        "nobody can run is a dead end with a plausible shape\nremedy: %s\n%s"
        % (ran.rc, remedy, ran.combined[-600:]))
    assert "uuid shape invalid" not in ran.combined, (
        "[reconcile-remedy-runs] the uuid was not parsed as a uuid — the "
        "emitted form is unrunnable: %s\n%s"
        % (remedy, ran.combined[-600:]))

    doc = L.read_json(copy)
    topic = next((w.get("topic_id") for w in doc.get("workers", [])
                  if w.get("uuid") == W2), None)
    assert str(topic) == str(LIVE_TOPIC), (
        "[reconcile-remedy-applied] the copy's topic_id is %r, want %d — the "
        "remedy ran but did not reconcile the row"
        % (topic, LIVE_TOPIC))

    assert "1 BINDING-MISMATCH row(s)" in err, (
        "[reconcile-counts-the-drift] stderr does not carry the count:\n%s"
        % (err[-800:],))

    clean = _run(run_tool, "roster", "--role", "fallbackprobe", "--live",
                 "--reconcile", env=env)
    assert "0 BINDING-MISMATCH" in clean.err, (
        "[reconcile-clean-is-explicit] a clean run must SAY zero — an empty "
        "result that reads as 'no such data' is the class this cycle closes:"
        "\n%s" % (clean.err[-600:],))

    bare = _run(run_tool, "roster", "--reconcile")
    assert bare.rc == 2, (
        "[reconcile-requires-live] rc=%s, want 2 — with no --live there is no "
        "binding to reconcile against\n%s"
        % (bare.rc, bare.combined[-600:]))


# =============================================================================
# duplicates — grouped by the FACT, never by the actor
# =============================================================================
def test_duplicates_finds_both_classes_and_names_them_apart(roster_fixture,
                                                            run_tool):
    """``duplicates-*`` (c23 H-3).

    Two classes, and the fixture plants the specimen each one exists for:

    * DUPLICATE — the same fact stamped twice by the SAME actor.
    * IDENTITY-SPLIT — the same fact stamped twice by DIFFERENT actors, which
      is one act recorded under two identities.

    Grouping by ``(kind, by, what)`` finds NOTHING on the identity-split
    specimen, which is exactly the bug the leg pins: the specimens carry
    different ``by`` strings by construction.
    """
    for what, by in (
        ("h3 dup specimen one", "editor aaa11111"),
        ("h3 dup specimen one", "editor aaa11111"),
        ("h3 split specimen two", "editor bbb22222"),
        ("h3 split specimen two", "editor ccc33333"),
    ):
        res = _run(run_tool, "stamp", "note", what, "--by", by)
        assert res.rc == 0, (
            "fixture: stamp %r by %r failed rc=%s\n%s"
            % (what, by, res.rc, res.combined[-600:]))

    res = _run(run_tool, "duplicates")
    assert res.rc == 0, (
        "[duplicates-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    out = res.combined
    assert "DUPLICATE kind=note count=2 by=editor aaa11111" in out, (
        "[duplicates-finds-same-actor-pair] the same-actor pair is not "
        "reported:\n%s" % (out[-900:],))
    assert "IDENTITY-SPLIT kind=note count=2" in out, (
        "[duplicates-finds-identity-split] the split identity is not reported "
        "— an actor-keyed grouping finds nothing on exactly the specimens this "
        "verb exists for:\n%s" % (out[-900:],))

    assert re.search(r"[0-9]+ DUPLICATE \(one fact", out), (
        "[duplicates-splits-the-two-classes] no DUPLICATE total line:\n%s"
        % (out[-900:],))
    assert re.search(r"[0-9]+ IDENTITY-SPLIT \(one act", out), (
        "[duplicates-splits-the-two-classes] no IDENTITY-SPLIT total line — "
        "the two classes must be counted apart, because one is a bookkeeping "
        "slip and the other is an attribution failure:\n%s" % (out[-900:],))

    none = _run(run_tool, "duplicates", "--kind", "no-such-kind")
    assert "duplicates: none" in none.combined, (
        "[duplicates-clean-is-explicit] a filter matching nothing must SAY "
        "'none', not print a blank that reads as a broken command:\n%s"
        % (none.combined[-600:],))

    js = _run(run_tool, "duplicates", "--json")
    try:
        parsed = json.loads(js.out)
    except ValueError as exc:
        raise AssertionError(
            "[duplicates-json-parseable] --json output does not parse: %s\n%s"
            % (exc, js.out[-600:]))
    assert isinstance(parsed, list) and len(parsed) >= 2, (
        "[duplicates-json-parseable] %r is not an array of >= 2 entries — the "
        "two planted classes must both appear"
        % (parsed if not isinstance(parsed, list) else "len=%d" % len(parsed),))
