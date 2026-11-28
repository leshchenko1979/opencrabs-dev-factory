"""Ported: ``oc-ledger`` selftest §66c-70 — ``enroll``'s topic-existence guard,
the ``hq``/``hq-supervisor`` role alias, ``events``/``tail``, ``mode``,
``--verbs`` and the did-you-mean hints.

Source: ``tools/state/oc-ledger:4906-5100`` (selftest lines 2136-2330) — 57 of
the 475 ``chk`` calls plus the ``chkeq``/``ok || bad`` legs in the same block
(the ``mode`` DECLARATION arms are ``chkeq``, so they carry no ``chk`` row of
their own; they are ported beside the ``mode`` rc arms and named after them).
Every assertion message carries the shell name it replaces.

WHAT THIS MODULE PROTECTS

    * **A warning that never refuses, and never fires on the right answer.**
      ``enroll --topic`` used to accept any number, so a live row was enrolled
      on topic 478 — an ISSUE id, never a forum topic — and only a ``retire``
      could undo it. The guard WARNS (enroll runs at lane bring-up and must not
      be blockable by a busy session DB), so the two halves of the contract are
      rc 0 on BOTH paths and the warning present on exactly one. The fixture
      binds 55555 and nothing else, so 478 is dead and 55555 is live *by
      construction*; a leg that asserted only the rc would pass on a guard that
      warns about everything or nothing.
    * **The alias is a MAPPING, not a substring.** ``hq-supervisor`` was renamed
      ``hq`` and lanes had the old spelling in active habit; a rc-1 NO-MATCH
      there reads to a lane as "HQ is unrostered". So both spellings must select
      the SAME row set — and ``cmp`` on two EMPTY outputs also passes, so the
      legs assert non-empty *and* byte-equal *and* that the row is the enrolled
      one. The bare retired term ``supervisor`` must still fail loudly, which is
      what separates an alias from a fuzzy match.
    * **``events`` is a tail whose rc 1 is a VERDICT.** rc 0 rows printed, 1 no
      match ("widen the filter"), 2 usage, 3 ledger unreadable. A caller that
      conflates 1 with 3 concludes "the ledger has no such event" instead of
      "wrong filter" or "unreadable store", so each code is asserted with the
      discriminating observation beside it.
    * **The projection is WIDER than the canonical schema.** ``.events[]``
      carries 27 key schemas in the live corpus; a row storing its content in
      ``text`` (or its stamp in ``ts``, actor in ``actor``, the legacy
      ``{at,detail,id,type}`` block) used to render a BLANK content column and
      drop out of every ``--since`` window (byte-lexicographic compare against
      ``""`` is always-less-than). The legs assert the EXACT rendered string —
      never a grep — and then assert the row is *reachable* by ``--actor``,
      ``--since`` and ``--kind``, which is the half a blank stamp broke.
    * **A silent clip is how a claim gets built on half a line.** ``events``
      truncates ``what`` at 160 chars by default and must SAY so on stderr;
      ``--full`` must print the whole thing and must not nudge. Both directions
      are asserted, because "never nudge" would also pass a tool that never
      truncates and "always nudge" would pass a tool that clips everything.
    * **``mode`` reads the newest DECLARATION, not the newest mention.** The
      fixture is the live shape that made the verb necessary: an older
      declaration (200), a newer declaration (300), and a newer still prose row
      that only talks about the gate (400). A loose predicate answers 400,
      oldest-wins answers 200, and only the declaration predicate answers 300 —
      so the arm cannot pass vacuously.

NOTES ON WHAT THE SHELL DOES THAT THIS MODULE DOES DIFFERENTLY
    * ``enroll-dead-topic-rc0`` sits on tool line 4905 — one line ABOVE this
      block's start — but is asserted here as the precondition of
      ``enroll-dead-topic-warns``: a warn-only leg would pass on a REFUSAL that
      also printed a warning, which is the one outcome the guard exists to
      avoid. The name is carried verbatim so the mapping stays mechanical.
    * ``events-since-past-20`` is asserted against a SEEDED 25-row ledger
      instead of the shell's accumulated ``$T`` state, because "the default
      ``--n`` window is 20" is only a measurement when there are more than 20
      rows to clip. ``--all`` over the same fixture is asserted to return 26, so
      the 20 cannot be a truncated file masquerading as a window.
    * ``test_enroll_topic_guard_is_inert_without_a_session_db`` is an ADDITION,
      not a ported ``chk``: it pins the edge the shell's fixture relies on
      (``OC_LEDGER_DB`` is passed explicitly *because* the derived path does not
      exist here), so a future change that made the DB mandatory would redden
      it instead of silently turning the guard into a refusal.
    * Nothing here is skipped: all 57 ``chk`` names in tool lines 4906-5100 and
      all 10 ``chkeq`` names in the same block are ported.

Nothing here drives ``--selftest`` and nothing sleeps a wall-clock bound, so no
leg is ``slow``: each is a handful of tool invocations against a throwaway
ledger in this worker's scratch.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

# The fixture session DB binds this topic and ONLY this one, so "live" and
# "dead" are properties of the fixture rather than of the number's shape.
LIVE_TOPIC = 55555
DEAD_TOPIC = 478          # the real INCIDENT's value: an ISSUE number
DEAD_UUID = "ab000000-0000-4000-8000-000000000503"
LIVE_UUID = "ab000000-0000-4000-8000-000000000504"
HQ_UUID = "88888888-8888-8888-8888-888888888888"

# =============================================================================
# helpers
# =============================================================================
def _run(run_tool, *args, env=None, **kw):
    return run_tool([str(TOOL)] + [str(a) for a in args], timeout=180,
                    env=env, **kw)

def _append(ledger, *rows):
    """``jq '.events += [...]'`` — the shell's way of planting a fixture row.

    A hand-edited ledger is exactly the shape this verb has to survive, so the
    fixture is written rather than produced by a verb: a row the writers would
    never mint (``{"at":…,"detail":…}``) is the case under test.
    """
    doc = L.read_json(ledger)
    doc["events"] = list(doc.get("events") or []) + list(rows)
    Path(ledger).write_text(json.dumps(doc), encoding="utf-8")
    return doc

def _rows(res) -> list:
    """The TSV body of an ``events`` run, one list per line."""
    return [ln.split("\t") for ln in res.out.splitlines() if ln.strip()]

def _session_db(path, script: str):
    """Build the fixture session DB with the tool's OWN reader (#371).

    The shell does this with ``"$_OC_DIR/lib/oc_sqlite"``, not the ``sqlite3``
    CLI: on a box without that binary every ``--live`` leg skipped silently
    behind a ``command -v`` guard while the production verb was dead.
    """
    return subprocess.run(
        [str(cf.TOOLS_DIR / "lib" / "oc_sqlite"), str(path), script],
        capture_output=True, text=True)

def _bindings_db(tmp_path, threads) -> Path:
    """A ``sessions``/``session_bindings`` DB binding exactly ``threads``."""
    db = Path(tmp_path) / "sessions.db"
    script = (
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, archived_at TEXT, title TEXT);\n"
        "CREATE TABLE session_bindings (session_id TEXT PRIMARY KEY, channel TEXT,"
        " chat_id TEXT, thread_id INTEGER);\n")
    for i, thread in enumerate(threads):
        sid = "1111111%d-1111-4111-8111-111111111111" % i
        script += "INSERT INTO sessions VALUES ('%s', NULL, NULL);\n" % sid
        script += ("INSERT INTO session_bindings VALUES ('%s', 'telegram', '-100', %d);\n"
                   % (sid, thread))
    res = _session_db(db, script)
    assert res.returncode == 0, (
        "fixture session DB could not be built rc=%s\n%s"
        % (res.returncode, res.stderr[-600:]))
    return db

# =============================================================================
# §66c: the topic-existence guard on enroll (fork #503)
# =============================================================================
def test_enroll_warns_on_a_dead_topic_and_only_on_a_dead_topic(
        ledger_sandbox, run_tool, tmp_path):
    """``enroll-dead-topic-warns`` + ``enroll-live-topic-rc0``
    + ``enroll-live-topic-must-not-warn`` + ``enroll-event-records-topic``.

    ONE test because the two invocations are one experiment: the guard is only
    proven by warning on the dead value AND staying silent on the live one, and
    the two share the fixture DB. Splitting them would let a leg pass on a
    fixture it did not build.
    """
    db = _bindings_db(tmp_path, [LIVE_TOPIC])
    env = {"OC_LEDGER_DB": str(db)}

    dead = _run(run_tool, "enroll", DEAD_UUID, "deadtopic",
                "--topic", DEAD_TOPIC, env=env)
    assert dead.rc == 0, (
        "[enroll-dead-topic-rc0] rc=%s, want 0 — the guard WARNS and never "
        "refuses: enroll runs at lane bring-up and must not be blockable by a "
        "session DB\n%s" % (dead.rc, dead.combined[-800:]))
    assert ("WARNING topic %d names no live binding" % DEAD_TOPIC) in dead.combined, (
        "[enroll-dead-topic-warns] topic %d has no binding in the fixture DB "
        "and the enroll did not say so; stderr was:\n%s"
        % (DEAD_TOPIC, dead.err[-800:]))
    assert str(db) in dead.combined, (
        "[enroll-dead-topic-warns] the warning does not name the DB it checked "
        "(%s) — an operator cannot tell which store answered\n%s"
        % (db, dead.err[-800:]))

    live = _run(run_tool, "enroll", LIVE_UUID, "livetopic",
                "--topic", LIVE_TOPIC, env=env)
    assert live.rc == 0, (
        "[enroll-live-topic-rc0] rc=%s, want 0\n%s"
        % (live.rc, live.combined[-800:]))
    assert ("WARNING topic %d" % LIVE_TOPIC) not in live.combined, (
        "[enroll-live-topic-must-not-warn] topic %d IS bound in the fixture DB "
        "and the enroll warned anyway — a guard that fires on the right answer "
        "is noise, and noise gets ignored on the day it is right:\n%s"
        % (LIVE_TOPIC, live.combined[-800:]))

    # The event must carry the topic the caller supplied: the phantom row's own
    # event recorded none, which is why its bad topic_id could not be traced
    # from the trail at all.
    text = Path(ledger_sandbox.ledger).read_text(encoding="utf-8")
    assert "(topic %d)" % DEAD_TOPIC in text, (
        "[enroll-event-records-topic] the enroll event does not carry "
        "'(topic %d)' — a wrong topic_id that the event omits cannot be traced "
        "after the fact, which is how the 478 row survived\nledger tail:\n%s"
        % (DEAD_TOPIC, text[-800:]))
    enrolled = L.where(ledger_sandbox.ledger, kind="roster-enroll")
    dead_rows = [e for e in enrolled if str(DEAD_TOPIC) in (e.get("what") or "")]
    assert dead_rows, (
        "[enroll-event-records-topic] no roster-enroll event records topic %d "
        "(rows: %r) — a wrong topic_id that the event omits cannot be traced "
        "after the fact, which is how the 478 row survived"
        % (DEAD_TOPIC, [e.get("what") for e in enrolled]))

def test_enroll_topic_guard_is_inert_without_a_session_db(ledger_sandbox, run_tool):
    """The guard's OTHER edge: no DB, no warning, still rc 0.

    Not a ``chk`` in the shell — it is the precondition the shell's fixture
    relies on (``OC_LEDGER_DB`` is passed explicitly *because* the derived path
    does not exist here). Asserting it keeps the guard from becoming a refusal
    the day someone makes the DB mandatory.
    """
    missing = Path(ledger_sandbox.state) / "absent.db"
    res = _run(run_tool, "enroll", DEAD_UUID, "deadtopic",
               "--topic", DEAD_TOPIC, env={"OC_LEDGER_DB": str(missing)})
    assert res.rc == 0, (
        "[enroll-dead-topic-rc0] with no session DB the enroll is rc=%s, want 0 "
        "— an absent DB must never block a lane's bring-up\n%s"
        % (res.rc, res.combined[-800:]))
    assert "names no live binding" not in res.combined, (
        "[enroll-dead-topic-warns] a warning was emitted for a DB that does not "
        "exist (%s) — the guard must be silent when it cannot check\n%s"
        % (missing, res.combined[-800:]))

# =============================================================================
# §66b: the hq / hq-supervisor role alias
# =============================================================================
def test_role_alias_maps_the_retired_spelling_onto_the_same_row_set(
        ledger_sandbox, run_tool):
    """``role-alias-new-rc`` + ``role-alias-legacy-rc`` + ``role-alias-same-set``
    + ``role-alias-finds-hq-row`` + ``role-alias-bare-term-rc1``.

    ``cmp -s`` on two EMPTY files passes, so byte-equality alone would certify a
    roster that matched nothing. The legs therefore assert non-empty first, then
    equality, then that the row IS the enrolled HQ row.
    """
    res = _run(run_tool, "enroll", HQ_UUID, "hq", "--topic", "30220")
    assert res.rc == 0, (
        "fixture enroll hq failed rc=%s\n%s" % (res.rc, res.combined[-800:]))

    new = _run(run_tool, "roster", "--role", "hq")
    assert new.rc == 0, (
        "[role-alias-new-rc] rc=%s, want 0 for the CURRENT spelling\n%s"
        % (new.rc, new.combined[-800:]))
    old = _run(run_tool, "roster", "--role", "hq-supervisor")
    assert old.rc == 0, (
        "[role-alias-legacy-rc] rc=%s, want 0 — a rc-1 NO-MATCH here reads to a "
        "lane as 'HQ is unrostered', a false negative in exactly the place "
        "lanes check HQ's existence\n%s" % (old.rc, old.combined[-800:]))

    rows = [ln for ln in new.out.splitlines() if ln.strip()]
    assert rows, (
        "[role-alias-finds-hq-row] the current spelling returned NOTHING; two "
        "empty outputs would compare equal and certify a roster that matched "
        "nothing")
    assert new.out == old.out, (
        "[role-alias-same-set] the two spellings select different row sets — "
        "current:\n%r\nlegacy:\n%r" % (new.out, old.out))
    assert any(ln.split("\t")[0] == HQ_UUID for ln in rows), (
        "[role-alias-finds-hq-row] %s is not in the matched rows %r"
        % (HQ_UUID, rows))

    bare = _run(run_tool, "roster", "--role", "supervisor")
    assert bare.rc == 1, (
        "[role-alias-bare-term-rc1] rc=%s, want 1 — the alias is an EXACT "
        "mapping, never a blanket 'supervisor' match; a stale query written with "
        "the bare retired term must still fail loudly\n%s"
        % (bare.rc, bare.combined[-800:]))

# =============================================================================
# §67-70: events | tail — the read verb
# =============================================================================
def test_events_tail_window_filters_and_usage_codes(ledger_sandbox, run_tool):
    """``events-rc`` + ``events-n-count`` + ``events-newest-last``
    + ``events-tail-alias-rc`` + ``events-tail-alias-count``
    + ``events-nomatch-rc1`` + ``events-kind-rc`` + ``events-kind-only``
    + ``events-actor-rc`` + ``events-actor-only`` + ``events-json-*``
    + the five usage arms.

    ONE test: the window assertions are relative to the fixture's own ``max n``
    (the shell compares against ``jq '.events[-1].n'`` on the same file), so the
    fixture and the assertions have to be the same object.
    """
    seeded = [{"n": i, "t": "2026-01-0%dT00:00:00Z" % (i % 9 + 1),
               "kind": "incident" if i == 3 else "note",
               "by": cf.LEDGER_ACTOR, "what": "fixture row %d" % i}
              for i in range(1, 6)]
    _append(ledger_sandbox.ledger, *seeded)
    ledger = ledger_sandbox.ledger
    newest = L.max_n(ledger)

    res = _run(run_tool, "events", "--n", 3)
    assert res.rc == 0, (
        "[events-rc] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:]))
    rows = _rows(res)
    assert len(rows) == 3, (
        "[events-n-count] %d row(s) for --n 3, want 3\n%s" % (len(rows), res.out))
    assert rows[-1][0] == str(newest), (
        "[events-newest-last] the last printed row has n=%r, want %r — the tail "
        "runs oldest -> newest, and a reversed window makes every 'the newest "
        "row says X' read the OLDEST one instead"
        % (rows[-1][0], newest))
    assert [int(r[0]) for r in rows] == [newest - 2, newest - 1, newest], (
        "[events-newest-last] the window is %r, want the LAST three ordinals "
        "ending at %d — 'n 3' counts BACK from the newest"
        % ([r[0] for r in rows], newest))

    alias = _run(run_tool, "tail", "--n", 1)
    assert alias.rc == 0, (
        "[events-tail-alias-rc] rc=%s, want 0 — `tail` is an accepted alias\n%s"
        % (alias.rc, alias.combined[-800:]))
    assert len(_rows(alias)) == 1, (
        "[events-tail-alias-count] %d row(s) for `tail --n 1`, want 1\n%s"
        % (len(_rows(alias)), alias.out))

    nomatch = _run(run_tool, "events", "--kind", "zzznope")
    assert nomatch.rc == 1, (
        "[events-nomatch-rc1] rc=%s, want 1 — NO-MATCH is a verdict, not a "
        "silent empty: a caller that gets 0 here concludes 'no such event' "
        "instead of 'wrong filter'\n%s" % (nomatch.rc, nomatch.combined[-800:]))
    assert "no event matches" in nomatch.combined, (
        "[events-nomatch-rc1] rc 1 without the 'widen the filter' verdict on "
        "stderr is indistinguishable from a crash\n%s" % nomatch.err[-800:])

    kind = _run(run_tool, "events", "--kind", "incident")
    assert kind.rc == 0, (
        "[events-kind-rc] rc=%s, want 0 for a kind the fixture carries\n%s"
        % (kind.rc, kind.combined[-800:]))
    krows = _rows(kind)
    assert krows, (
        "[events-kind-only] the incident filter returned NOTHING; 'every row is "
        "incident' is vacuously true on an empty set")
    assert all(r[2] == "incident" for r in krows), (
        "[events-kind-only] a row of another kind survived the filter: %r"
        % ([r[2] for r in krows],))

    stamp = _run(run_tool, "stamp", "note", "EVENTS-FIXTURE actor probe",
                 env={"OC_ACTOR": HQ_UUID})
    assert stamp.rc == 0, (
        "fixture stamp failed rc=%s\n%s" % (stamp.rc, stamp.combined[-800:]))
    actor = _run(run_tool, "events", "--actor", HQ_UUID)
    assert actor.rc == 0, (
        "[events-actor-rc] rc=%s, want 0 for an actor the fixture carries\n%s"
        % (actor.rc, actor.combined[-800:]))
    arows = _rows(actor)
    assert arows, (
        "[events-actor-only] the actor filter returned NOTHING — an empty set "
        "makes 'every row carries the uuid' vacuously true")
    assert all(HQ_UUID in r[3] for r in arows), (
        "[events-actor-only] a row does not carry %s in its `by` column: %r"
        % (HQ_UUID, [r[3] for r in arows]))

    js = _run(run_tool, "events", "--json")
    assert js.rc == 0, (
        "[events-json-rc] rc=%s, want 0\n%s" % (js.rc, js.combined[-800:]))
    payload = json.loads(js.out)
    assert isinstance(payload, list) and 0 < len(payload) <= 20, (
        "[events-json-array] --json emitted %r, want a non-empty ARRAY of at "
        "most the 20-row default window" % (payload,))
    last = payload[-1]
    assert L.has_fields(last, ("n", "t", "kind", "by", "what")), (
        "[events-json-fields] the last element is missing a field: has %r, want "
        "all of n/t/kind/by/what (element=%r)" % (sorted(last), last))
    assert last["what"] == "EVENTS-FIXTURE actor probe", (
        "[events-json-fields] the last element is %r, want the row just stamped "
        "— the fields must belong to the SAME row" % (last,))

    # The usage arms. Each is a distinct rc 2 because a caller branches on it.
    zero = _run(run_tool, "events", "--n", "0")
    assert zero.rc == 2, (
        "[events-n0-rc2] rc=%s, want 2 — '--n 0' is a usage error, not 'print "
        "nothing', because an empty window is indistinguishable from no match\n%s"
        % (zero.rc, zero.combined[-600:]))
    nonint = _run(run_tool, "events", "--n", "abc")
    assert nonint.rc == 2, (
        "[events-n-nonint-rc2] rc=%s, want 2\n%s"
        % (nonint.rc, nonint.combined[-600:]))
    unknown = _run(run_tool, "events", "--bogus")
    assert unknown.rc == 2, (
        "[events-unknown-flag-rc2] rc=%s, want 2 — an unknown flag must not fall "
        "through to the default window\n%s" % (unknown.rc, unknown.combined[-600:]))
    novalue = _run(run_tool, "events", "--n")
    assert novalue.rc == 2, (
        "[events-n-novalue-rc2] rc=%s, want 2\n%s"
        % (novalue.rc, novalue.combined[-600:]))

    helper = _run(run_tool, "events", "-h")
    assert helper.rc == 0, (
        "[events-help-rc0] rc=%s, want 0 — help is a READ, never a usage "
        "error\n%s" % (helper.rc, helper.combined[-600:]))
    assert "usage: oc-ledger events" in helper.out, (
        "[events-help-rc0] -h printed no usage line: %r" % (helper.out[:400],))

    broken = _run(run_tool, "events", env={"OC_LEDGER": str(Path(ledger_sandbox.state) / "bad.json")})
    assert broken.rc == 3, (
        "[events-bad-ledger-rc3] rc=%s, want 3 — an UNREADABLE ledger must be "
        "distinguishable from 'no match' (1), or a missing store reads as an "
        "empty one\n%s" % (broken.rc, broken.combined[-600:]))

def test_events_since_window_is_lexicographic_and_defaults_to_20(
        ledger_sandbox, run_tool):
    """``events-since-past-rc`` + ``events-since-past-20`` + ``events-since-none-rc1``.

    The 25-row fixture makes "20" a measurement of the default window rather
    than a coincidence. The corrupt ``t="x"`` row is load-bearing: ``--since``
    compares BYTES, so a no-match sentinel that only sorts above "2099" would
    let "x" through and answer rc 0 — the exact silent mis-ranking the verb's
    own comment describes.
    """
    rows = [{"n": i, "t": "2026-02-%02dT00:00:00Z" % i, "kind": "note",
             "by": "x", "what": "since row %d" % i} for i in range(1, 26)]
    rows.append({"n": 99, "t": "x", "kind": "note", "by": "x",
                 "what": "corrupt stamp, hand-edited"})
    _append(ledger_sandbox.ledger, *rows)

    res = _run(run_tool, "events", "--since", "2020-01-01T00:00:00Z")
    assert res.rc == 0, (
        "[events-since-past-rc] rc=%s, want 0 — a window before every row "
        "matches all of them\n%s" % (res.rc, res.combined[-800:]))
    assert len(_rows(res)) == 20, (
        "[events-since-past-20] %d row(s), want 20 — the DEFAULT --n window, "
        "which is what every caller that omits --n gets"
        % len(_rows(res)))

    everything = _run(run_tool, "events", "--since", "2020-01-01T00:00:00Z", "--all")
    assert len(_rows(everything)) == 26, (
        "[events-since-past-20] --all returned %d row(s), want 26 (25 dated + "
        "the corrupt one) — otherwise the 20 above is a truncated file, not a "
        "window" % len(_rows(everything)))

    none = _run(run_tool, "events", "--since", "zzzz")
    assert none.rc == 1, (
        "[events-since-none-rc1] rc=%s, want 1 — the sentinel has to sort above "
        "'x' too, not just above 2099: a corrupt stamp sorts ABOVE every "
        "digit-leading value, so a 2099 sentinel would admit it and answer 0\n%s"
        % (none.rc, none.combined[-800:]))

def test_events_truncates_at_160_and_nudges_unless_full(ledger_sandbox, run_tool):
    """``events-trunc-rc`` + ``events-trunc-160`` + ``events-trunc-nudge``
    + ``events-full-rc`` + ``events-full-300`` + ``events-full-no-nudge``.

    Both directions: a silent clip is how a claim gets built on half a line, and
    a nudge under ``--full`` would train callers to ignore it.
    """
    long = "x" * 300
    stamp = _run(run_tool, "stamp", "note", long)
    assert stamp.rc == 0, (
        "fixture stamp of a 300-char payload failed rc=%s\n%s"
        % (stamp.rc, stamp.combined[-800:]))

    clipped = _run(run_tool, "events", "--n", 1)
    assert clipped.rc == 0, (
        "[events-trunc-rc] rc=%s, want 0\n%s"
        % (clipped.rc, clipped.combined[-800:]))
    body = _rows(clipped)[0][4]
    assert len(body) == 160, (
        "[events-trunc-160] the content column is %d chars, want 160 — the "
        "default clip; a different number is a different contract for every "
        "caller parsing this column" % len(body))
    assert "truncated" in clipped.err, (
        "[events-trunc-nudge] the row was clipped to 160 chars and stderr said "
        "nothing — a SILENT clip is how a claim gets built on half a line\n"
        "stderr was: %r" % (clipped.err[-600:],))

    whole = _run(run_tool, "events", "--n", 1, "--full")
    assert whole.rc == 0, (
        "[events-full-rc] rc=%s, want 0\n%s"
        % (whole.rc, whole.combined[-800:]))
    full_body = _rows(whole)[0][4]
    assert len(full_body) == 300, (
        "[events-full-300] --full printed %d chars, want 300\n%r"
        % (len(full_body), full_body[:200]))
    assert full_body == long, (
        "[events-full-300] --full changed the payload, not just its length: "
        "%r" % (full_body[:200],))
    assert "truncated" not in whole.err, (
        "[events-full-no-nudge] --full still nudged about truncation: %r"
        % (whole.err[-600:],))

def test_events_renders_non_canonical_key_schemas_and_makes_them_reachable(
        ledger_sandbox, run_tool):
    """``events-nc-*`` — the ``{n,ts,actor,kind,text}`` shape.

    A row that keeps its content in ``text``, its stamp in ``ts`` and its actor
    in ``actor`` used to render with a BLANK content column AND drop out of
    ``--actor``/``--since``/``--kind``. The render is asserted as the EXACT
    string, so a traceback echoing the source line cannot satisfy it.
    """
    text = "noncanonical content must survive the projection"
    actor = "cccccccc-1111-2222-3333-444444444444"
    ts = "y2099-01-01T00:00:00Z"
    _append(ledger_sandbox.ledger,
            {"n": 99001, "ts": ts, "actor": actor, "kind": "nc-schema",
             "text": text, "claim_ref": "nc-probe"})

    res = _run(run_tool, "events", "--n", 1)
    assert res.rc == 0, (
        "[events-nc-render-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-800:]))
    row = _rows(res)[0]
    assert row[4] == text, (
        "[events-nc-content] the content column is %r, want %r — the projection "
        "reads `text`, and a blank column is what made these rows invisible"
        % (row[4], text))
    assert row[1] == ts, (
        "[events-nc-ts] the stamp column is %r, want %r (`ts`, not `t`)"
        % (row[1], ts))
    assert row[2] == "nc-schema", (
        "[events-nc-kind] the kind column is %r, want 'nc-schema'" % (row[2],))
    assert row[3] == actor, (
        "[events-nc-actor] the actor column is %r, want %r (`actor`, not `by`)"
        % (row[3], actor))

    by_actor = _run(run_tool, "events", "--actor", actor, "--json")
    assert by_actor.rc == 0, (
        "[events-nc-actor-reach] rc=%s, want 0 — the row is SELECTABLE by an "
        "actor it does not print under `by`, which is the defect this arm "
        "exists for\n%s" % (by_actor.rc, by_actor.combined[-600:]))
    assert len(json.loads(by_actor.out)) == 1, (
        "[events-nc-actor-reach] %r, want exactly the one row"
        % (json.loads(by_actor.out),))

    by_since = _run(run_tool, "events", "--since", ts, "--json")
    assert by_since.rc == 0, (
        "[events-nc-since-reach] rc=%s, want 0 — a row whose stamp lives in "
        "`ts` must still fall inside a window\n%s"
        % (by_since.rc, by_since.combined[-600:]))
    assert len(json.loads(by_since.out)) == 1, (
        "[events-nc-since-reach] %r, want exactly the one row"
        % (json.loads(by_since.out),))

    by_kind = _run(run_tool, "events", "--kind", "nc-schema", "--json")
    assert by_kind.rc == 0, (
        "[events-nc-kind-reach] rc=%s, want 0\n%s"
        % (by_kind.rc, by_kind.combined[-600:]))
    assert len(json.loads(by_kind.out)) == 1, (
        "[events-nc-kind-reach] %r, want exactly the one row"
        % (json.loads(by_kind.out),))

    # The truncation nudge must measure the NORMALISED field it prints, not the
    # raw `.what` (which is absent here).
    doc = L.read_json(ledger_sandbox.ledger)
    for ev in doc["events"]:
        if ev.get("n") == 99001:
            ev["text"] = "y" * 300
    Path(ledger_sandbox.ledger).write_text(json.dumps(doc), encoding="utf-8")

    clipped = _run(run_tool, "events", "--n", 1)
    assert clipped.rc == 0, (
        "[events-nc-trunc-rc] rc=%s, want 0\n%s"
        % (clipped.rc, clipped.combined[-800:]))
    assert len(_rows(clipped)[0][4]) == 160, (
        "[events-nc-trunc-160] the normalised content column is %d chars, want "
        "160 — a clip measured against the RAW `.what` would not clip at all "
        "here, because this row has no `what`" % len(_rows(clipped)[0][4]))
    assert "truncated" in clipped.err, (
        "[events-nc-trunc-nudge] the clipped non-canonical row produced no nudge: "
        "%r" % (clipped.err[-600:],))

def test_events_renders_the_legacy_at_detail_id_type_block(ledger_sandbox, run_tool):
    """``events-legacy-*`` — the 22-row ``{at,detail,id,type}`` block.

    The old projection read only ``{kind,type}/{by,actor,role}/{t,ts}/
    {what,text,summary,note}``, so every one of these rendered a BLANK stamp and
    a blank content column — and the blank stamp also dropped them out of every
    ``--since`` window (byte-lexicographic compare against ``""`` is
    always-less-than). Assertions are FILTER-scoped, never positional: a ``--n 1``
    tail read would be moved by any later row.
    """
    at = "2026-08-27T02:55:00Z"
    detail = "legacy at/detail row must render its stamp and its content"
    _append(ledger_sandbox.ledger,
            {"at": at, "detail": detail, "id": 99002, "type": "legacy-shape"})

    res = _run(run_tool, "events", "--kind", "legacy-shape", "--n", 1)
    assert res.rc == 0, (
        "[events-legacy-render-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-800:]))
    row = _rows(res)[0]
    assert row[1] == at, (
        "[events-legacy-stamp] the stamp column is %r, want %r (`at`)" % (row[1], at))
    assert row[4] == detail, (
        "[events-legacy-content] the content column is %r, want %r (`detail`)"
        % (row[4], detail))
    assert row[2] == "legacy-shape", (
        "[events-legacy-kind] the kind column is %r, want 'legacy-shape' (`type`)"
        % (row[2],))

    reach = _run(run_tool, "events", "--since", at, "--kind", "legacy-shape",
                 "--n", 1, "--json")
    assert reach.rc == 0, (
        "[events-legacy-since-reach] rc=%s, want 0 — a blank stamp is "
        "always-less-than every window bound, which is the half a blank stamp "
        "broke\n%s" % (reach.rc, reach.combined[-800:]))
    assert len(json.loads(reach.out)) == 1, (
        "[events-legacy-since-reach] %r, want the one row — a row that renders "
        "but is unreachable is only half fixed"
        % (json.loads(reach.out),))

# =============================================================================
# §71-bis: mode (#97)
# =============================================================================
MODE_EVENTS = [
    {"n": 100, "t": "2026-01-01T00:00:00Z", "kind": "note", "by": "x",
     "what": "held on the MODE: gate pending owner"},
    {"n": 200, "t": "2026-02-01T00:00:00Z", "kind": "note", "by": "x",
     "what": "MODE: UPSTREAM-ON-REQUEST — older declaration"},
    {"n": 300, "t": "2026-03-01T00:00:00Z", "kind": "note", "by": "x",
     "what": "MODE: FORK-STANDING — newer declaration"},
    {"n": 400, "t": "2026-04-01T00:00:00Z", "kind": "note", "by": "x",
     "what": "PHASE 7 MODE: GATE. MODE: resolved live at 12:00"},
]

MODE_PROSE = [
    {"n": 10, "t": "2026-01-01T00:00:00Z", "kind": "note", "by": "x",
     "what": "held on the MODE: gate"},
    {"n": 11, "t": "2026-01-02T00:00:00Z", "kind": "note", "by": "x",
     "what": "PHASE 7 MODE: GATE. MODE: resolved live by HQ"},
]

def _ledger_with(tmp_path, events, name="mode.json") -> Path:
    p = Path(tmp_path) / name
    p.write_text(json.dumps({"current_skill_version": "0.4.1",
                             "workers": [], "events": events}),
                 encoding="utf-8")
    return p

def test_mode_reads_the_newest_declaration_not_the_newest_mention(
        run_tool, tmp_path):
    """``mode-rc0`` + the four ``chkeq`` DECLARATION arms + ``mode-json-*``.

    The fixture answers 300 only under the declaration predicate: a loose
    "mentions MODE:" answers 400, oldest-wins answers 200. Both wrong answers are
    asserted against explicitly, so this cannot pass vacuously.
    """
    path = _ledger_with(tmp_path, MODE_EVENTS)
    env = {"OC_LEDGER": str(path)}

    res = _run(run_tool, "mode", env=env)
    assert res.rc == 0, (
        "[mode-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-800:]))
    cols = res.out.splitlines()[0].split("\t")
    assert cols[0] == "300", (
        "[mode-newest-declaration] the ruling is n=%r, want 300 — the newest "
        "row that IS a declaration. 400 is the newest row that MENTIONS MODE:, "
        "200 the oldest declaration\n%s" % (cols[0], res.out))
    assert cols[0] != "400", (
        "[mode-not-newest-mention] the verb answered the newest row that merely "
        "MENTIONS MODE: (400) — prose is not a ruling")
    assert cols[0] != "200", (
        "[mode-not-oldest-declaration] the verb answered the OLDEST declaration "
        "(200) instead of the newest")
    assert cols[2] == "FORK-STANDING", (
        "[mode-value] the value column is %r, want 'FORK-STANDING' — the value "
        "and the ordinal must come from the SAME row" % (cols[2],))

    js = _run(run_tool, "mode", "--json", env=env)
    assert js.rc == 0, (
        "[mode-json-rc0] rc=%s, want 0\n%s" % (js.rc, js.combined[-800:]))
    payload = json.loads(js.out)
    assert payload.get("n") == 300, (
        "[mode-json-n] .n is %r, want 300" % (payload.get("n"),))
    assert payload.get("value") == "FORK-STANDING", (
        "[mode-json-value] .value is %r, want 'FORK-STANDING'"
        % (payload.get("value"),))
    assert payload.get("ts") == "2026-03-01T00:00:00Z", (
        "[mode-json-ts] .ts is %r, want the DECLARATION's own stamp "
        "'2026-03-01T00:00:00Z' — the row's three fields must agree"
        % (payload.get("ts"),))

def test_mode_fails_closed_on_prose_only_and_keeps_its_rc_vocabulary(
        run_tool, tmp_path, ledger_sandbox):
    """``mode-no-declaration-rc1`` + ``mode-no-declaration-says-prose``
    + ``mode-no-declaration-names-count`` + ``mode-unknown-flag-rc2``
    + ``mode-help-rc0`` + ``mode-bad-ledger-rc3``.

    rc 1 must SAY it failed closed and name the count: a lane that reads a bare
    rc 1 will otherwise take the last thing it saw as the ruling.
    """
    prose = _ledger_with(tmp_path, MODE_PROSE, "mode-prose.json")
    res = _run(run_tool, "mode", env={"OC_LEDGER": str(prose)})
    assert res.rc == 1, (
        "[mode-no-declaration-rc1] rc=%s, want 1 — no declaration means fail "
        "closed (FORK-STANDING), never a guess\n%s"
        % (res.rc, res.combined[-800:]))
    assert "prose is not a ruling" in res.err, (
        "[mode-no-declaration-says-prose] stderr does not say why the rows were "
        "rejected: %r" % (res.err[-600:],))
    assert "2 row(s) mention MODE:" in res.err, (
        "[mode-no-declaration-names-count] stderr does not name how many rows "
        "mentioned MODE: — the count is the operator's only handle on which "
        "rows to look at. stderr: %r" % (res.err[-600:],))
    assert "FORK-STANDING" in res.err, (
        "[mode-no-declaration-rc1] the refusal does not say what it fell back "
        "to: %r" % (res.err[-600:],))

    bad_flag = _run(run_tool, "mode", "--bogus", env={"OC_LEDGER": str(prose)})
    assert bad_flag.rc == 2, (
        "[mode-unknown-flag-rc2] rc=%s, want 2\n%s"
        % (bad_flag.rc, bad_flag.combined[-600:]))
    helper = _run(run_tool, "mode", "-h", env={"OC_LEDGER": str(prose)})
    assert helper.rc == 0, (
        "[mode-help-rc0] rc=%s, want 0 — help is a read\n%s"
        % (helper.rc, helper.combined[-600:]))
    assert "newest" in helper.out.lower(), (
        "[mode-help-rc0] the help text does not state the predicate it "
        "implements: %r" % (helper.out[:400],))

    broken = _run(run_tool, "mode",
                  env={"OC_LEDGER": str(Path(ledger_sandbox.state) / "bad.json")})
    assert broken.rc == 3, (
        "[mode-bad-ledger-rc3] rc=%s, want 3 for an unreadable ledger — 3 is "
        "'cannot read', not 'no declaration' (1)\n%s"
        % (broken.rc, broken.combined[-600:]))

# =============================================================================
# §71: --verbs discovery and the did-you-mean hints
# =============================================================================
def test_verbs_lists_every_verb_and_hints_name_the_right_ones(run_tool):
    """``verbs-flag-rc0`` + ``verbs-flag-contains-stamp``
    + ``verbs-flag-contains-roster`` + ``verbs-flag-contains-mode``
    + ``suggest-roster-enroll`` + ``suggest-roster-amend``.

    ``--verbs`` is the discovery surface: a verb missing from it is a verb
    callers will not find, which is how the playbooks kept guessing ``tail``.
    The hints matter for the same reason — the wrong suggestion sends a lane to
    a verb that will refuse it.
    """
    res = _run(run_tool, "--verbs")
    assert res.rc == 0, (
        "[verbs-flag-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    words = res.out.split()
    assert "stamp" in words, (
        "[verbs-flag-contains-stamp] 'stamp' is missing from --verbs (%d words: "
        "%r) — a verb that is not advertised is a verb callers guess at"
        % (len(words), words))
    assert "roster" in words, (
        "[verbs-flag-contains-roster] 'roster' is missing from --verbs (%d "
        "words: %r)" % (len(words), words))
    assert "mode" in words, (
        "[verbs-flag-contains-mode] 'mode' is missing from --verbs (%d words: "
        "%r)" % (len(words), words))

    enroll = _run(run_tool, "roster-enroll")
    assert enroll.rc == 2, (
        "[suggest-roster-enroll] rc=%s, want 2 — an unknown verb is a usage "
        "error, never a silent no-op\n%s"
        % (enroll.rc, enroll.combined[-600:]))
    assert "did you mean 'enroll'?" in enroll.combined, (
        "[suggest-roster-enroll] the refusal does not offer 'enroll'; stderr "
        "was %r" % (enroll.err[-600:],))

    amend = _run(run_tool, "roster-amend")
    assert amend.rc == 2, (
        "[suggest-roster-amend] rc=%s, want 2\n%s"
        % (amend.rc, amend.combined[-600:]))
    assert "did you mean 'promote' or 'enroll'?" in amend.combined, (
        "[suggest-roster-amend] the refusal does not offer 'promote'/'enroll' — "
        "the retired verb has TWO successors and naming only one sends the lane "
        "to a verb that may refuse it; stderr was %r" % (amend.err[-600:],))
