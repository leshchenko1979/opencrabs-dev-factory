"""`oc-ledger`'s JSONL write path: the TRUE-APPEND predicate must not eat
non-event state (factory #193).

THE DEFECT
    ``atomic_jq`` splits its result back into ``events.jsonl`` + ``workers.json``.
    It has a fast path (#149) that appends ONE line to the record instead of
    re-serializing a 2.8 MB blob, and a slow path that rebuilds both files. The
    fast path was selected by a predicate that tested ONLY the event list:

        ($new|length) == (($old|length) + 1) and ($new[0:($old|length)] == $old)

    So any mutation that appends exactly one event AND changes non-event state
    was indistinguishable from a pure stamp: ``cat >> events.jsonl`` ran, the
    ``del(.events)`` rewrite of ``workers.json`` was skipped, and the non-event
    change was DROPPED with rc 0 and no diagnostic. ``enroll`` (one event + one
    ``.workers[]`` row) lost the row outright; ``promote``, ``retire``, ``ack``
    and ``confirm`` lost their field changes the same way.

WHY THE SHELL SELFTEST DID NOT CATCH IT
    ``oc-ledger --selftest`` seeds ``workers-ledger.json`` and never creates an
    ``events.jsonl``, so every one of its 418 cases runs the LEGACY single-file
    path. The JSONL branch — the live one — had no coverage of its own branch
    predicate. These legs are that coverage.

HOW "THE FAST PATH WAS TAKEN" IS PROVEN
    Not by the absence of a symptom. ``cat >>`` keeps the inode of
    ``events.jsonl``; the slow path installs a ``mv`` of a temp, which replaces
    it. So the inode is a direct observation of WHICH BRANCH RAN, and every leg
    below asserts it in the direction its branch requires. The pure-stamp leg
    additionally proves its own workers.json assertion is DISCRIMINATING (that
    the slow path would have rewritten the file) so a green there cannot mean
    "the assertion was vacuous".

FIXTURE
    A scratch ``events.jsonl`` + ``workers.json`` per leg, with ``OC_LEDGER``
    and ``OC_DEV_STATE`` pointed into ``scratch``. Nothing here can reach the
    live record: ``env_guard`` already redirects those vars and ``run_tool``
    refuses a production path at launch.
"""

from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-ledger")
ACTOR = cf.LEDGER_ACTOR
_SEQ = itertools.count()

# A roster uuid distinct from ACTOR, so "the actor is enrolled" and "the
# subject of the mutation is enrolled" can never be confused by a leg.
WORKER = "11111111-2222-3333-4444-555555555555"
WORKER2 = "22222222-3333-4444-5555-666666666666"

SEED_EVENT = '{"n":1,"t":"2026-01-01T00:00:00Z","by":"seed","kind":"note","what":"seed"}'

SEED_WORKER = {
    "uuid": WORKER,
    "role": "tester",
    "topic_id": 7,
    "feature": "-",
    "confirmed": False,
    "last_acked": None,
    "notes": [],
    "events": [],
}


def _seed_workers(*extra):
    return {
        "workers": [dict(SEED_WORKER), *extra],
        "current_skill_version": "0.4.1",
        "meta": {"skill_version": "0.4.1"},
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.fixture
def jsonl(scratch, monkeypatch):
    """A scratch JSONL ledger: ``events.jsonl`` + ``workers.json``.

    Returns a ``Node`` carrying the two paths plus ``run(*args)``, so a leg
    reads as the verb it drives. ``OC_LEDGER`` points at ``events.jsonl`` — that
    is what puts oc-ledger in JSONL mode (``_jsonl_mode``), which is the only
    mode this module is about.
    """
    root = scratch.path / "jsonl193" / ("j%d" % next(_SEQ))
    state = root / "state"
    skill = root / "skill"
    state.mkdir(parents=True, exist_ok=True)
    (skill / "tools" / "tests").mkdir(parents=True, exist_ok=True)
    (skill / "tools" / "tests" / ".keep").write_text("")

    ev = state / "events.jsonl"
    wf = state / "workers.json"
    ev.write_text(SEED_EVENT + "\n", encoding="utf-8")
    wf.write_text(json.dumps(_seed_workers()) + "\n", encoding="utf-8")

    monkeypatch.setenv("OC_LEDGER", str(ev))
    monkeypatch.setenv("OC_DEV_STATE", str(state))
    monkeypatch.setenv("OC_SKILL_DIR", str(skill))
    # ledger_sandbox's fast-contention set, for the same reason: a failure in
    # the lock/git tail must cost ~1 s here, not the production budget.
    monkeypatch.setenv("OC_SHIP_AUDIT_CHAIN", "0")
    monkeypatch.setenv("OC_LEDGER_LOCK_WAIT", "2")
    monkeypatch.setenv("OC_LEDGER_PUSH_TIMEOUT", "1")
    monkeypatch.setenv("OC_LEDGER_PUSH_MIN", "1")
    monkeypatch.setenv("OC_LEDGER_GIT_TAIL_WAIT", "5")

    return cf.Node(root, state=state, skill=skill, ev=ev, wf=wf)


def _rows(path) -> list:
    return json.loads(Path(path).read_text(encoding="utf-8")).get("workers") or []


def _event_lines(path) -> list:
    return [
        ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()
    ]


def _extract_predicate(tool: Path) -> str:
    """Pull the true-append jq program out of the SHIPPED tool, verbatim.

    Anchored on ``--slurpfile o "$base"`` — that argument pair appears exactly
    once in oc-ledger (the predicate under test), and the program is the single
    quoted argument that follows it. Reading it from the tool rather than
    restating it here is the difference between a guard and a copy of the code
    it is supposed to guard: a copied program stays green when the tool reverts.
    """
    import re

    text = Path(tool).read_text(encoding="utf-8")
    m = re.search(
        r"jq -c --slurpfile o \"\$base\" '\n(?P<prog>.*?)' \"\$next\" > \"\$app\"",
        text, re.S)
    assert m, (
        "could not find the true-append predicate in %s (anchored on "
        "`jq -c --slurpfile o \"$base\"` … `\"$next\" > \"$app\"`). If the "
        "invocation was reformatted, update the extractor — do NOT inline the "
        "program here." % tool)
    return m.group("prog")


# =============================================================================
# (b) A PURE stamp still takes the append path — and it is OBSERVED, not assumed
# =============================================================================
def test_a_pure_stamp_still_appends_in_place(jsonl, run_tool):
    """`fixture` is the pure-stamp shape that goes through ``atomic_jq``.

    ``cmd_stamp`` writes its own line in JSONL mode, so it never reaches the
    predicate under test; ``fixture`` does (one event + ``.updated_at``), and
    that is the shape #149 exists to keep cheap. If this leg goes red, the fix
    has turned every stamp into a whole-record rewrite — the regression #149
    removed — which is the failure mode the fast path must survive.

    The inode is the proof of branch: ``cat >>`` preserves it, the slow path's
    ``mv`` does not.
    """
    ev_before = jsonl.ev.read_bytes()
    inode_before = jsonl.ev.stat().st_ino
    wf_before = jsonl.wf.read_bytes()
    wf_mtime_before = jsonl.wf.stat().st_mtime_ns

    res = run_tool(
        [str(TOOL), "fixture", "--n", "500", "--t", "2026-02-02T00:00:00Z",
         "--kind", "note", "--by", "fixture-planter", "--what", "pure stamp probe"],
        timeout=120)
    assert res.rc == 0, "fixture rc=%s\n%s" % (res.rc, res.combined[-800:])

    # 1. the record GREW IN PLACE — the fast path, observed rather than inferred
    assert jsonl.ev.stat().st_ino == inode_before, (
        "events.jsonl was REPLACED (inode %s -> %s): the slow path ran for a "
        "pure stamp, which is the #149 whole-record-rewrite regression this "
        "fast path exists to prevent"
        % (inode_before, jsonl.ev.stat().st_ino))

    # 2. the old bytes are an untouched prefix, and exactly one line arrived
    ev_after = jsonl.ev.read_bytes()
    assert ev_after.startswith(ev_before), (
        "the append did not preserve the existing record byte-for-byte:\n"
        "before=%r\nafter =%r" % (ev_before[-200:], ev_after[:200]))
    assert len(_event_lines(jsonl.ev)) == 2, (
        "expected exactly one new line, got %d"
        % len(_event_lines(jsonl.ev)))

    # 3. workers.json is untouched — content AND mtime
    assert jsonl.wf.read_bytes() == wf_before, (
        "a pure stamp REWROTE workers.json; it must be left alone")
    assert jsonl.wf.stat().st_mtime_ns == wf_mtime_before, (
        "workers.json's mtime moved during a pure stamp")

    # 4. A SECOND, independent branch signal: the fast path drops `.updated_at`
    #    by design, so workers.json still carries the SEED stamp while the record
    #    already holds the newer one. The slow path writes `del(.events)` of the
    #    post-program document, which INCLUDES the bumped `.updated_at` — so it
    #    would have moved this value to 2026-02-02. That makes the assertion
    #    discriminating in the direction that matters: it cannot be satisfied by
    #    the slow path, and it is not satisfied by "nothing happened" either,
    #    because the record below demonstrably grew.
    wf_doc = json.loads(jsonl.wf.read_text(encoding="utf-8"))
    assert wf_doc.get("updated_at") == "2026-01-01T00:00:00Z", (
        "workers.json .updated_at is %r: the slow path ran and rewrote the "
        "non-event state for a pure stamp" % (wf_doc.get("updated_at"),))
    newest = json.loads(_event_lines(jsonl.ev)[-1])
    assert newest["t"] == "2026-02-02T00:00:00Z", (
        "the appended line is not the fixture row: %r" % (newest,))
    assert newest["n"] == 500, "appended n=%r, want 500" % (newest.get("n"),)


# =============================================================================
# (a) one event + non-event change -> the non-event change MUST land
# =============================================================================
def test_enroll_lands_its_roster_row(jsonl, run_tool):
    """#193's headline case: ``enroll`` = 1 event + 1 ``.workers[]`` row.

    Pre-fix this returned rc 0, appended the ``roster-enroll`` event, and left
    workers.json exactly as it was — the row was gone with no diagnostic. The
    live ledger carries five uuids in that state (see the module docstring of
    the fix commit).
    """
    before = len(_rows(jsonl.wf))

    res = run_tool([str(TOOL), "enroll", WORKER2, "editor", "--topic", "11"],
                   timeout=120)
    assert res.rc == 0, "enroll rc=%s\n%s" % (res.rc, res.combined[-800:])

    rows = _rows(jsonl.wf)
    assert len(rows) == before + 1, (
        "enroll appended its event but DROPPED the roster row (#193): "
        "%d rows before, %d after" % (before, len(rows)))
    row = [r for r in rows if r.get("uuid") == WORKER2]
    assert row, "the enrolled uuid is absent from workers.json: %r" % (rows,)
    assert row[0]["role"] == "editor", "row role=%r, want editor" % row[0].get("role")
    assert row[0]["topic_id"] == 11, "row topic_id=%r, want 11" % row[0].get("topic_id")

    # the event landed too — this is an append + a row, not one or the other
    kinds = [json.loads(ln).get("kind") for ln in _event_lines(jsonl.ev)]
    assert kinds.count("roster-enroll") == 1, (
        "expected exactly one roster-enroll event, kinds=%r" % (kinds,))


def test_promote_writes_its_field_changes(jsonl, run_tool):
    """``promote`` = 1 event + in-place ``.workers[]`` edits.

    It looked correct in the field only because the *other* verbs were worse:
    the row it mutates already existed, so the drop left a stale row rather than
    a missing one — the same defect with a quieter symptom.
    """
    res = run_tool([str(TOOL), "promote", WORKER, "editor", "--topic", "9"],
                   timeout=120)
    assert res.rc == 0, "promote rc=%s\n%s" % (res.rc, res.combined[-800:])

    row = _rows(jsonl.wf)[0]
    assert row["role"] == "editor", (
        "promote dropped its role change (#193): role=%r, want editor"
        % row.get("role"))
    assert row["topic_id"] == 9, (
        "promote dropped its topic change (#193): topic_id=%r, want 9"
        % row.get("topic_id"))
    # and it went down the SLOW path — an in-place edit is not an append
    assert len(_event_lines(jsonl.ev)) == 2, "promote must still append its event"


def test_ack_writes_last_acked(jsonl, run_tool):
    """``ack`` = 1 event + ``.last_acked``; a dropped field makes the roster
    report a worker as un-acked forever while the audit row says otherwise."""
    res = run_tool([str(TOOL), "ack", WORKER, "0.4.99"], timeout=120)
    assert res.rc == 0, "ack rc=%s\n%s" % (res.rc, res.combined[-800:])

    row = _rows(jsonl.wf)[0]
    assert row.get("last_acked"), (
        "ack dropped .last_acked (#193): the audit event exists but the roster "
        "field it mirrors is still %r" % (row.get("last_acked"),))
    assert row["last_acked"]["version"] == "0.4.99", (
        "last_acked.version=%r, want 0.4.99" % row["last_acked"].get("version"))


def test_retire_removes_the_row(jsonl, run_tool):
    """``retire`` = 1 event + row REMOVAL — the inverse of enroll's failure.

    A dropped removal is the worst direction of this defect: the retired uuid
    keeps signing, which is precisely what ``retire`` exists to stop.
    """
    before = len(_rows(jsonl.wf))
    res = run_tool([str(TOOL), "retire", WORKER, "--topic", "7"], timeout=120)
    assert res.rc == 0, "retire rc=%s\n%s" % (res.rc, res.combined[-800:])

    rows = _rows(jsonl.wf)
    assert len(rows) == before - 1, (
        "retire appended its event but left the row in place (#193): %d rows "
        "before, %d after — the uuid keeps signing" % (before, len(rows)))
    assert all(r.get("uuid") != WORKER for r in rows), (
        "the retired uuid is still rostered: %r" % (rows,))


def test_confirm_flips_confirmed_and_its_worker_note(jsonl, run_tool, scratch):
    """``confirm`` = 1 event + ``.confirmed`` + a ``workers[].events`` note.

    It touches non-event state in TWO places, which is why a fix that only
    compared ``.workers`` (say) would still pass three of the legs above and
    fail this one.
    """
    # confirm needs a claim by the worker and a gh that answers; both are shims
    gh = scratch.path / "fakegh193"
    gh.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    gh.chmod(0o755)

    claim = run_tool([str(TOOL), "stamp", "claim", "CLAIM #193 — probe"],
                     timeout=120, env={"OC_ACTOR": WORKER})
    assert claim.rc == 0, "seed claim rc=%s\n%s" % (claim.rc, claim.combined[-600:])

    res = run_tool([str(TOOL), "confirm", WORKER, "--gh", str(gh)], timeout=120)
    assert res.rc == 0, "confirm rc=%s\n%s" % (res.rc, res.combined[-800:])

    row = _rows(jsonl.wf)[0]
    assert row.get("confirmed") is True, (
        "confirm dropped .confirmed (#193): %r" % (row.get("confirmed"),))
    assert row.get("events"), (
        "confirm dropped its per-worker note (#193): workers[].events=%r"
        % (row.get("events"),))


# =============================================================================
# the predicate itself, at the boundary: a NON-event change is never an append
# =============================================================================
def test_a_non_event_change_forces_the_slow_path(jsonl, run_tool):
    """The mirror of the pure-stamp leg: the branch decision must FLIP.

    Asserted on the same observable (the inode), so the two legs together pin
    the predicate in both directions instead of only one. Without this leg a
    "fix" that hard-coded the slow path would pass every other test here and
    silently cost the #149 rewrite on every stamp.
    """
    inode_before = jsonl.ev.stat().st_ino
    res = run_tool([str(TOOL), "promote", WORKER, "editor", "--topic", "9"],
                   timeout=120)
    assert res.rc == 0, "promote rc=%s\n%s" % (res.rc, res.combined[-800:])

    assert jsonl.ev.stat().st_ino != inode_before, (
        "a mutation that changed .workers[] took the APPEND path (events.jsonl "
        "inode unchanged): the predicate is not comparing non-event state, "
        "which is exactly #193")


def test_the_fast_path_predicate_rejects_a_one_event_doc_that_moves_a_row(
        jsonl, run_tool):
    """A direct unit probe of the PREDICATE AS SHIPPED, independent of any verb.

    The verb-level legs depend on each verb's jq program; this one pins the
    DECISION RULE. The program is EXTRACTED FROM THE TOOL at test time, not
    copied into this file — a copy would be a guard over a string in a test
    file and would stay green while the tool reverted (the self-matching-grep
    trap the lock-budget module's docstring names). Extraction is what makes
    this leg neuterable: revert the predicate in ``tools/state/oc-ledger`` and
    this fails with it.

    It runs that program against a hand-built pair (old doc, new doc) differing
    by one event AND one ``.workers[]`` field, and requires it to emit nothing —
    then against a pure stamp, and requires it to emit the row.
    """
    program = _extract_predicate(TOOL)
    assert "del(.events)" in program, (
        "the extracted predicate does not compare non-event state at all:\n%s"
        % program)
    assert "del(.updated_at)" in program, (
        "the predicate is not excluding .updated_at — every append-shaped jq "
        "program bumps it, so this would force the slow path on every stamp "
        "(the #149 regression):\n%s" % program)

    old = {"workers": [dict(SEED_WORKER)], "updated_at": "2026-01-01T00:00:00Z",
           "events": [{"n": 1, "kind": "note", "what": "seed"}]}
    moved = json.loads(json.dumps(old))
    moved["workers"][0]["role"] = "editor"
    moved["updated_at"] = "2026-02-02T00:00:00Z"
    moved["events"].append({"n": 2, "kind": "roster-enroll", "what": "enrolled"})

    pure = json.loads(json.dumps(old))
    pure["updated_at"] = "2026-02-02T00:00:00Z"
    pure["events"].append({"n": 2, "kind": "note", "what": "stamp"})

    base = jsonl.state / "pred.base.json"
    base.write_text(json.dumps(old), encoding="utf-8")

    def decide(doc):
        nxt = jsonl.state / "pred.next.json"
        nxt.write_text(json.dumps(doc), encoding="utf-8")
        return subprocess.run(
            ["jq", "-c", "--slurpfile", "o", str(base), program, str(nxt)],
            capture_output=True, text=True).stdout

    assert decide(moved).strip() == "", (
        "the predicate ACCEPTED a document that moved a .workers[] row: it "
        "would take the append path and drop the row (#193)")
    out = decide(pure).strip()
    assert out, "the predicate REJECTED a pure stamp: the #149 fast path is dead"
    assert json.loads(out)["kind"] == "note", (
        "the predicate returned the wrong event: %r" % (out,))

# =============================================================================
# the OTHER silent success in the same arm: a failed non-event write must not
# report rc 0
# =============================================================================
def test_a_failed_non_event_write_is_rc4_not_a_silent_rc0(
        jsonl, run_tool, scratch, monkeypatch):
    """The slow arm used to be ``jq ... && { cmp || mv; }`` — UNGUARDED.

    When the ``del(.events)`` write failed, the ``&&`` short-circuited, the temp
    was removed and the function fell through to ``return 0``: SUCCESS reported
    over non-event state that was never installed. Same defect class as the
    predicate above it, three lines below it — which is why it is pinned here
    rather than left to the exit-code path's reputation.

    The instrument is a ``jq`` shim PREPENDED to PATH that fails on exactly one
    argument, ``del(.events)``. That argument is the slow arm's non-event write
    and is NOT the predicate's program (which is passed as a single multi-line
    argument to ``--slurpfile``), so the branch DECISION is unaffected and only
    the write under test is broken. A shim that failed every ``jq`` call would
    redden on rc 3 and prove nothing about this arm.

    The assertion is rc 4 **and** both live files byte-identical: the arm builds
    both temps before installing either, so a build failure must leave the
    record and the roster exactly as they were.
    """
    real_jq = shutil.which("jq")
    assert real_jq, "jq is required for this leg"

    bindir = scratch.path / ("jqshim193-%d" % next(_SEQ))
    bindir.mkdir(parents=True, exist_ok=True)
    shim = bindir / "jq"
    shim.write_text(
        "#!/bin/sh\n"
        'for a in "$@"; do\n'
        '  if [ "$a" = "del(.events)" ]; then\n'
        '    echo "jq: simulated non-event write failure" >&2\n'
        "    exit 5\n"
        "  fi\n"
        "done\n"
        'exec %s "$@"\n' % real_jq,
        encoding="utf-8")
    shim.chmod(0o755)
    # PREPEND to the inherited PATH (env_guard restores it per test), never to a
    # previous shim, so this leg cannot inherit a broken jq from another.
    monkeypatch.setenv("PATH", "%s:%s" % (
        bindir, os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")))

    ev_before = jsonl.ev.read_bytes()
    wf_before = jsonl.wf.read_bytes()

    res = run_tool([str(TOOL), "ack", WORKER, "0.4.99"], timeout=120)

    assert res.rc == 4, (
        "a failed non-event write reported rc=%s, want 4 — rc 0 here is a "
        "silent success over non-event state that was never installed (#193)\n%s"
        % (res.rc, res.combined[-800:]))
    assert jsonl.wf.read_bytes() == wf_before, (
        "workers.json was modified by a mutation whose non-event write FAILED")
    assert jsonl.ev.read_bytes() == ev_before, (
        "events.jsonl was modified even though the slow arm failed — both temps "
        "must be built before either file is installed")
