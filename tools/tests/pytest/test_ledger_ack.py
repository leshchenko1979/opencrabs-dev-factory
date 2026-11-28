"""Ported: ``oc-ledger`` selftest §27-29d — ``ack``, ``enroll``, ``promote``,
``retire``.

Source: ``tools/state/oc-ledger:3365-3582`` (selftest lines 595-812) — 88 of
the 475 ``chk`` calls plus the ``ok || bad`` legs in the same block. Every
assertion message carries the shell name it replaces.

WHAT THIS MODULE PROTECTS
    These four verbs are the whole roster LIFECYCLE: ``enroll`` creates a row,
    ``promote`` mutates it in place, ``retire`` removes it, and ``ack`` records
    that a lane adopted a version. Three invariants carry most of the weight:

    * ``ack`` is IDEMPOTENT per ``(uuid, version)``, and the key is an EXACT
      equality, never a ``contains``. ``oc-drift-check --ack`` delegates here,
      so one adoption that both drift-checked and acked used to write two
      byte-identical rows seconds apart. The prefix trap is the discriminating
      leg: with ``0.4.1`` on record, ``0.4.10`` must still APPEND — a substring
      key silently swallows the minor bump, which is the direction nobody
      notices until a lane's ack is missing for a version it really adopted.
    * The ack COUNT is measured as a DELTA around each step, never as an
      absolute. An absolute count CASCADES: one wrongly appended event shifts
      every later count and turns four assertions red for one root cause, so a
      control run cannot tell the reader which step broke.
    * ``retire`` is ROW-scoped, not uuid-scoped. A uuid can legitimately hold
      two rows (an editor row on one topic plus an auditor row on another), and
      the first cut removed BOTH while naming one — latent only because every
      uuid on the roster of the day held a single row. So the fixture builds the
      two-row state by hand (``enroll`` refuses a duplicate uuid by design,
      which is exactly why that shape can only arrive through a migration or an
      incident).
    * ``--role`` on ``retire`` is an EXACT match, unlike the substring match
      ``roster --role`` uses: this verb DESTROYS a row, so a fuzzy selector is
      a foot-gun.

FIXTURE NOTE
    The shell threads one shared ``$T`` through the block, and two of its legs
    depend on state left by earlier ones (``promote-ack-carries`` needs the ack
    block to have left ``last_acked`` at ``0.4.3``). Each test here rebuilds
    what it needs from a fresh ``ledger_sandbox``, and the ack-idempotence test
    runs on its own isolated two-worker ledger so the shared fixture stays
    state-neutral for the promote legs — the same split the shell makes with
    ``$T/ack2``.

DELIBERATELY NOT PORTED
    * ``retire-rowscope-restored`` / ``retire-rowscope-fixture`` are fixture
      HYGIENE, not assertions: the shell has to put the shared ``$T`` back the
      way the later roster block expects it. Here every test owns its sandbox,
      so there is nothing to restore — the equivalent assertion (the row count
      after each retire) is already made by the legs that matter.
    * ``retire-event-n-unique`` is ported as part of the retire test, but read
      through ``L.ns``: the shell's jq compares ``length`` against
      ``unique | length``, and the same statement in Python is clearer than a
      filter string.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

AAAA = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"     # the sandbox's own row
CCCC = "cccccccc-dddd-eeee-ffff-000000000000"     # second worker, isolated ledger
EDITOR = "22222222-2222-2222-2222-222222222222"
U6 = "66666666-6666-6666-6666-666666666666"


def _run(run_tool, *args, env=None, timeout=120):
    return run_tool([str(TOOL), *args], timeout=timeout, env=env)


def _ack_count(ledger) -> int:
    """``[.events[]? | select(.kind == "ack")] | length``."""
    return len(L.where(ledger, kind="ack"))


def _last_acked(ledger, uuid=AAAA) -> dict:
    for w in L.workers(ledger):
        if w.get("uuid") == uuid:
            return w.get("last_acked") or {}
    return {}


def _rows(ledger, uuid) -> list:
    return [w for w in L.workers(ledger) if w.get("uuid") == uuid]


# =============================================================================
# ack — refusals, the happy path, and version normalization
# =============================================================================
@pytest.mark.parametrize("argv, want_rc, name", [
    (["ack", "short-uuid", "0.4.2"], 2, "ack-bad-uuid"),
    (["ack", AAAA, "0.4"], 2, "ack-bad-version"),
    (["ack", AAAA, "1.2.3"], 2, "ack-bad-major"),
    (["ack", "11111111-1111-1111-1111-111111111111", "0.4.2"], 3,
     "ack-unknown-uuid"),
])
def test_ack_refuses_a_bad_argument_with_its_own_rc(ledger_sandbox, run_tool,
                                                    argv, want_rc, name):
    """``ack-bad-uuid`` / ``ack-bad-version`` / ``ack-bad-major`` /
    ``ack-unknown-uuid``.

    Four DIFFERENT rcs for four different failures: a malformed uuid or version
    is a usage error (2), an unenrolled uuid is a lookup miss (3). Collapsing
    them would make "you typed it wrong" indistinguishable from "that lane does
    not exist".
    """
    res = _run(run_tool, *argv)
    assert res.rc == want_rc, (
        "[%s] rc=%s, want %s\n%s" % (name, res.rc, want_rc,
                                     res.combined[-600:]))


def test_ack_writes_the_version_and_normalizes_the_v_prefix(ledger_sandbox,
                                                            run_tool):
    """``ack-happy`` + ``ack-written`` + ``ack-vprefix`` + ``ack-vprefix-normalized``.

    ``v0.4.3`` is a DISPLAY spelling; the stored value must be ``0.4.3``, or
    every comparison downstream (the roster's ``last_acked`` column, the sync
    gates) sees two spellings of one version.
    """
    happy = _run(run_tool, "ack", AAAA, "0.4.2")
    assert happy.rc == 0, (
        "[ack-happy] rc=%s, want 0\n%s" % (happy.rc, happy.combined[-600:]))
    assert _last_acked(ledger_sandbox.ledger).get("version") == "0.4.2", (
        "[ack-written] last_acked.version is %r, want '0.4.2'"
        % (_last_acked(ledger_sandbox.ledger).get("version"),))

    pref = _run(run_tool, "ack", AAAA, "v0.4.3")
    assert pref.rc == 0, (
        "[ack-vprefix] rc=%s, want 0 — the v-prefix is accepted\n%s"
        % (pref.rc, pref.combined[-600:]))
    assert _last_acked(ledger_sandbox.ledger).get("version") == "0.4.3", (
        "[ack-vprefix-normalized] last_acked.version is %r, want '0.4.3' — the "
        "stored form drops the display prefix"
        % (_last_acked(ledger_sandbox.ledger).get("version"),))


@pytest.mark.parametrize("argv, name", [
    (["ack", "not-a-uuid", "0.4.2"], "is-uuid-ack-shape-rc2"),
    (["enroll", "not-a-uuid", "tester"], "is-uuid-enroll-shape-rc2"),
    (["promote", "not-a-uuid", "editor"], "is-uuid-promote-shape-rc2"),
    (["retire", "not-a-uuid"], "is-uuid-retire-shape-rc2"),
])
def test_one_uuid_predicate_guards_all_four_verbs(ledger_sandbox, run_tool,
                                                  argv, name):
    """``is-uuid-*-shape-rc2`` (#441).

    The predicate used to be four byte-identical private copies, and
    ``claim-ref`` — the verb that shipped without one — used none. These pin the
    extraction: every migrated guard still refuses a non-uuid shape with rc 2,
    so the shared function cannot be quietly loosened for one caller.
    """
    res = _run(run_tool, *argv)
    assert res.rc == 2, (
        "[%s] rc=%s, want 2 — a non-uuid shape is a usage error on every verb "
        "that takes a uuid\n%s" % (name, res.rc, res.combined[-600:]))


# =============================================================================
# ack idempotence — the shared-fixture sequence, then the delta-based isolated one
# =============================================================================
def test_a_reack_refreshes_the_timestamp_without_appending_a_row(
        ledger_sandbox, run_tool):
    """``ack-reack-*`` — the M2-4 idempotence contract on the shared fixture.

    A re-ack is rc 0 (a caller retrying must not be told it failed) but appends
    NOTHING, and it still REFRESHES ``last_acked.at``: a re-ack after a failed
    git leg must not leave a stale timestamp behind, because the roster's
    ``last_acked`` column reads it. The output must also SAY it was idempotent,
    so a lane reading the log is not left guessing whether it took effect.
    """
    for args in (["ack", AAAA, "0.4.2"], ["ack", AAAA, "v0.4.3"]):
        res = _run(run_tool, *args)
        assert res.rc == 0, "fixture: %s failed rc=%s\n%s" % (
            " ".join(args), res.rc, res.combined[-600:])
    before = _ack_count(ledger_sandbox.ledger)

    reack = _run(run_tool, "ack", AAAA, "0.4.3")
    assert reack.rc == 0, (
        "[ack-reack-rc0] rc=%s, want 0 — a re-ack is not a failure\n%s"
        % (reack.rc, reack.combined[-600:]))
    assert _ack_count(ledger_sandbox.ledger) == before, (
        "[ack-reack-no-dup-event] ack events went %d -> %d; a re-ack of the "
        "same (uuid, version) must append NOTHING"
        % (before, _ack_count(ledger_sandbox.ledger)))
    assert _last_acked(ledger_sandbox.ledger).get("version") == "0.4.3", (
        "[ack-reack-last-acked-kept] last_acked.version is %r, want '0.4.3'"
        % (_last_acked(ledger_sandbox.ledger).get("version"),))

    # the v-prefix spelling normalizes to the SAME key, so it is still a dup
    before = _ack_count(ledger_sandbox.ledger)
    vpref = _run(run_tool, "ack", AAAA, "v0.4.3")
    assert vpref.rc == 0, (
        "[ack-reack-vprefix-rc0] rc=%s, want 0\n%s"
        % (vpref.rc, vpref.combined[-600:]))
    assert _ack_count(ledger_sandbox.ledger) == before, (
        "[ack-reack-vprefix-no-dup] ack events went %d -> %d — 'v0.4.3' and "
        "'0.4.3' are one version, not two"
        % (before, _ack_count(ledger_sandbox.ledger)))

    before = _ack_count(ledger_sandbox.ledger)
    at = _run(run_tool, "ack", AAAA, "0.4.3", "--at", "2026-01-02T03:04:05Z")
    assert at.rc == 0, (
        "[ack-reack-at-rc0] rc=%s, want 0\n%s" % (at.rc, at.combined[-600:]))
    assert _last_acked(ledger_sandbox.ledger).get("at") == "2026-01-02T03:04:05Z", (
        "[ack-reack-refreshes-at] last_acked.at is %r, want the --at value — a "
        "dup path that skips the refresh leaves a stale timestamp the roster "
        "then reports" % (_last_acked(ledger_sandbox.ledger).get("at"),))
    assert _ack_count(ledger_sandbox.ledger) == before, (
        "[ack-reack-at-no-dup] ack events went %d -> %d; --at refreshes the "
        "stamp, it does not mint a second row"
        % (before, _ack_count(ledger_sandbox.ledger)))
    assert "idempotent" in at.combined.lower(), (
        "[ack-reack-says-idempotent] the output does not say the re-ack was "
        "idempotent, so a lane cannot tell a no-op from a silent failure:\n%s"
        % (at.combined[-600:],))


def test_the_dedup_key_is_an_exact_version_and_includes_the_uuid(ledger_sandbox,
                                                                 run_tool,
                                                                 tmp_path):
    """``ack2-*`` — the delta-based control (M2-4, isolated two-worker ledger).

    Every count here is measured as a DELTA around its own step, because an
    absolute count cascades: one wrongly appended event would shift every later
    assertion and a control run could not name the step that broke.

    The prefix trap is the point. With ``0.4.1`` on record, ``0.4.10`` must
    APPEND. A ``contains`` key dedups it against ``0.4.1`` and the minor bump
    silently disappears — an under-record that nobody notices, because the lane
    did ack a version that really exists.
    """
    ledger = Path(tmp_path) / "led.json"
    ledger.write_text(json.dumps({
        "current_skill_version": "0.4.1",
        "meta": {"skill_version": "0.4.1", "current_skill_version": "0.4.1"},
        "updated_at": "2026-01-01T00:00:00Z",
        "workers": [
            {"uuid": AAAA, "role": "tester", "topic_id": 1, "feature": "-",
             "confirmed": True, "last_acked": None, "notes": [], "events": []},
            {"uuid": CCCC, "role": "editor", "topic_id": 2, "feature": "-",
             "confirmed": True, "last_acked": None, "notes": [], "events": []},
        ],
        "events": [],
    }), encoding="utf-8")
    env = {"OC_LEDGER": str(ledger)}

    def step(*args):
        return _run(run_tool, *args, env=env)

    # 1. a first ack appends
    before = _ack_count(ledger)
    res = step("ack", AAAA, "0.4.5")
    assert res.rc == 0, (
        "[ack2-first-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before + 1, (
        "[ack2-first-appends] ack events %d -> %d, want +1"
        % (before, _ack_count(ledger)))

    # 2. the same (uuid, version) again appends nothing
    before = _ack_count(ledger)
    res = step("ack", AAAA, "0.4.5")
    assert res.rc == 0, (
        "[ack2-reack-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before, (
        "[ack2-reack-no-dup] ack events %d -> %d, want unchanged"
        % (before, _ack_count(ledger)))
    assert _last_acked(ledger).get("version") == "0.4.5", (
        "[ack2-reack-last-acked] last_acked.version is %r, want '0.4.5'"
        % (_last_acked(ledger).get("version"),))

    # 3. a NEW version is new information -> appends
    before = _ack_count(ledger)
    res = step("ack", AAAA, "0.4.1")
    assert res.rc == 0, (
        "[ack2-newver-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before + 1, (
        "[ack2-newver-appends] ack events %d -> %d, want +1 — a different "
        "version is a different fact" % (before, _ack_count(ledger)))

    # 4. THE PREFIX TRAP: 0.4.1 is on record, 0.4.10 must still append
    before = _ack_count(ledger)
    res = step("ack", AAAA, "0.4.10")
    assert res.rc == 0, (
        "[ack2-prefixtrap-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before + 1, (
        "[ack2-prefixtrap-appends] ack events %d -> %d, want +1 — with '0.4.1' "
        "on record, '0.4.10' must NOT be deduped by it. A contains-based key "
        "swallows the minor bump and the lane's ack for a version it really "
        "adopted never lands" % (before, _ack_count(ledger)))

    before = _ack_count(ledger)
    res = step("ack", AAAA, "0.4.10")
    assert res.rc == 0, (
        "[ack2-prefixtrap-reack-rc0] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before, (
        "[ack2-prefixtrap-reack-no-dup] ack events %d -> %d, want unchanged — "
        "the exact key still dedups the exact repeat"
        % (before, _ack_count(ledger)))

    # 5. the key includes the UUID: another worker at the same version appends
    before = _ack_count(ledger)
    res = step("ack", CCCC, "0.4.5")
    assert res.rc == 0, (
        "[ack2-otheruuid-rc0] rc=%s, want 0\n%s" % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before + 1, (
        "[ack2-otheruuid-appends] ack events %d -> %d, want +1 — two lanes "
        "adopting one version are two facts" % (before, _ack_count(ledger)))

    before = _ack_count(ledger)
    res = step("ack", CCCC, "0.4.5")
    assert res.rc == 0, (
        "[ack2-otheruuid-reack-rc0] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-600:]))
    assert _ack_count(ledger) == before, (
        "[ack2-otheruuid-reack-no-dup] ack events %d -> %d, want unchanged"
        % (before, _ack_count(ledger)))

    tracked = [w for w in L.workers(ledger) if w.get("last_acked")]
    assert len(tracked) == 2, (
        "[ack2-both-workers-tracked] %d workers carry last_acked, want 2 — each "
        "row keeps its own ack state" % (len(tracked),))


# =============================================================================
# enroll
# =============================================================================
def test_enroll_creates_one_row_and_refuses_a_duplicate(ledger_sandbox, run_tool):
    """``enroll-bad-uuid`` / ``enroll-happy`` / ``enroll-dup`` / ``enroll-row``.

    ``enroll`` is the CREATE path, so a duplicate is rc 2 rather than an upsert:
    two rows for one uuid is the shape ``promote`` exists to avoid, and the
    row-scoped retire legs below show how much damage it does when it arrives
    by another route.
    """
    bad = _run(run_tool, "enroll", "nope", "editor")
    assert bad.rc == 2, (
        "[enroll-bad-uuid] rc=%s, want 2\n%s" % (bad.rc, bad.combined[-600:]))

    happy = _run(run_tool, "enroll", EDITOR, "editor", "--topic", "42")
    assert happy.rc == 0, (
        "[enroll-happy] rc=%s, want 0\n%s" % (happy.rc, happy.combined[-600:]))
    rows = _rows(ledger_sandbox.ledger, EDITOR)
    assert len(rows) == 1 and rows[0].get("topic_id") == 42, (
        "[enroll-row] rows for the new uuid: %r, want exactly one with "
        "topic_id 42 — --topic must be stored as a NUMBER, since the roster "
        "renders it by tostring" % (rows,))

    dup = _run(run_tool, "enroll", EDITOR, "editor")
    assert dup.rc == 2, (
        "[enroll-dup] rc=%s, want 2 — a duplicate uuid is refused, not "
        "upserted\n%s" % (dup.rc, dup.combined[-600:]))


# =============================================================================
# promote
# =============================================================================
def test_promote_mutates_one_row_in_place_and_carries_the_ack(ledger_sandbox,
                                                              run_tool):
    """``promote-*`` (T2 verdict n=1695, HQ confirmed NON-KERNEL).

    ONE worker, ONE row: ``promote`` mutates and never creates, so the row
    count is the assertion that separates it from an enroll-shaped
    implementation. And ``last_acked`` CARRIES across the role change — a
    promote that reset it would erase the lane's adoption record at the moment
    it changed job.
    """
    assert _run(run_tool, "enroll", EDITOR, "editor",
                "--topic", "42").rc == 0, "fixture: enroll failed"

    not_enrolled = _run(run_tool, "promote",
                        "33333333-3333-3333-3333-333333333333", "editor")
    assert not_enrolled.rc == 2, (
        "[promote-not-enrolled] rc=%s, want 2 — promote never creates a row\n%s"
        % (not_enrolled.rc, not_enrolled.combined[-600:]))

    same = _run(run_tool, "promote", EDITOR, "editor")
    assert same.rc == 2, (
        "[promote-nothing-to-change] rc=%s, want 2 — a promote that changes "
        "nothing is refused rather than journaled\n%s"
        % (same.rc, same.combined[-600:]))

    flag_guard = _run(run_tool, "promote", EDITOR, "--topic", "99")
    assert flag_guard.rc == 2, (
        "[promote-role-flag-guard] rc=%s, want 2 — '--topic' landed in the ROLE "
        "positional, which is always a parsing error\n%s"
        % (flag_guard.rc, flag_guard.combined[-600:]))

    happy = _run(run_tool, "promote", EDITOR, "toolsmith",
                 "--topic", "39171", "--feature", "tools")
    assert happy.rc == 0, (
        "[promote-happy] rc=%s, want 0\n%s" % (happy.rc, happy.combined[-600:]))
    rows = _rows(ledger_sandbox.ledger, EDITOR)
    assert len(rows) == 1, (
        "[promote-one-row] %d rows for the uuid, want 1 — promote mutates, it "
        "never appends a second row" % (len(rows),))
    assert rows[0].get("role") == "toolsmith", (
        "[promote-role-updated] role is %r, want 'toolsmith'"
        % (rows[0].get("role"),))
    assert str(rows[0].get("topic_id")) == "39171", (
        "[promote-topic-updated] topic_id is %r, want 39171"
        % (rows[0].get("topic_id"),))
    promoted = L.last_where(ledger_sandbox.ledger, by="oc-ledger promote")
    assert promoted and promoted.get("what", "").startswith("promoted 22222222"), (
        "[promote-event] the last promote row is %r, want it to start "
        "'promoted 22222222' — an in-place mutation still owes an audit row"
        % (promoted,))

    # the ack the earlier block left at 0.4.3 must survive the role change
    acked = _run(run_tool, "ack", AAAA, "0.4.3")
    assert acked.rc == 0, "fixture: ack failed rc=%s" % (acked.rc,)
    carries = _run(run_tool, "promote", AAAA, "tester2")
    assert carries.rc == 0, (
        "[promote-ack-carries-rc] rc=%s, want 0\n%s"
        % (carries.rc, carries.combined[-600:]))
    assert _last_acked(ledger_sandbox.ledger).get("version") == "0.4.3", (
        "[promote-ack-carries] last_acked.version is %r, want '0.4.3' — a "
        "promote must CARRY the ack, never reset it"
        % (_last_acked(ledger_sandbox.ledger).get("version"),))


def test_promote_help_is_reachable_and_the_emitted_remedy_parses(
        ledger_sandbox, run_tool):
    """``promote-help-*`` + ``remedy-shape-*`` + ``remedy-control`` (#686).

    This verb's own usage was UNREACHABLE: ``promote --help`` read the single
    argument as a ROLE and died rc 2 "role looks like a flag", so promote was
    the one verb with no help arm.

    The remedy legs assert REACHABILITY, not mutation. The old emitted string
    named ``promote --uuid <u>`` while the verb takes the uuid POSITIONALLY, so
    it died rc 2 "uuid shape invalid: '--uuid'" — a lane reading it, trusting it
    and running it had no next step. The positive leg proves the positional form
    parses and reaches the "nothing to change" guard; the CONTROL proves the old
    form is still rejected, because without it any string that happens to reach
    the guard would pass.
    """
    assert _run(run_tool, "enroll", EDITOR, "toolsmith", "--topic", "39171",
                "--feature", "tools").rc == 0, "fixture: enroll failed"

    helped = _run(run_tool, "promote", "--help")
    assert helped.rc == 0, (
        "[promote-help-rc] rc=%s, want 0 — --help must not be read as a role\n%s"
        % (helped.rc, helped.combined[-600:]))
    assert "usage: oc-ledger promote <uuid> <new-role>" in helped.combined, (
        "[promote-help-text] the usage line is missing:\n%s"
        % (helped.combined[-600:],))

    helped2 = _run(run_tool, "promote", EDITOR, "--help")
    assert helped2.rc == 0, (
        "[promote-help-uuid-rc] rc=%s, want 0 — the second positional is "
        "answered BEFORE the role-shape disambiguation\n%s"
        % (helped2.rc, helped2.combined[-600:]))

    positional = _run(run_tool, "promote", EDITOR, "toolsmith",
                      "--topic", "39171")
    assert positional.rc == 2, (
        "[remedy-shape-rc] rc=%s, want 2 — an unchanged role/topic stops at the "
        "nothing-to-change guard\n%s"
        % (positional.rc, positional.combined[-600:]))
    assert "uuid shape invalid" not in positional.combined, (
        "[remedy-shape] the POSITIONAL uuid was not parsed: %s"
        % (positional.combined[-600:],))
    assert "nothing to change" in positional.combined, (
        "[remedy-shape] the call did not reach the nothing-to-change guard, so "
        "the positional form is not actually runnable:\n%s"
        % (positional.combined[-600:],))

    old = _run(run_tool, "promote", "--uuid", EDITOR, "--topic", "39171")
    assert "uuid shape invalid" in old.combined, (
        "[remedy-control] the OLD '--uuid' form was accepted — it must still be "
        "rejected, or the positive leg above passes on any string that happens "
        "to reach the guard:\n%s" % (old.combined[-600:],))

    assert _rows(ledger_sandbox.ledger, EDITOR)[0].get("role") == "toolsmith", (
        "[remedy-no-mutation] the role changed — these legs assert "
        "reachability, they must not mutate the row")


# =============================================================================
# retire — the removal half of the lifecycle
# =============================================================================
def test_retire_removes_the_row_and_records_the_reason(ledger_sandbox, run_tool):
    """``retire-*`` (HQ ASK 2026-09-11).

    ``retire`` is the only verb that revokes: the sign gate keys on uuid
    PRESENCE, so removal is what makes a lane unsignable. The event is therefore
    the ONLY surviving record of the row — which is why the leg asserts its
    content (role, topic, feature, confirmed, reason) and not merely its kind.
    """
    assert _run(run_tool, "enroll", EDITOR, "editor",
                "--topic", "42").rc == 0, "fixture: enroll failed"
    assert _run(run_tool, "promote", EDITOR, "toolsmith", "--topic", "39171",
                "--feature", "tools").rc == 0, "fixture: promote failed"

    for argv, name in (
        (["retire"], "retire-no-args"),
        (["retire", "nope"], "retire-bad-uuid"),
        (["retire", "44444444-4444-4444-4444-444444444444"], "retire-not-enrolled"),
        (["retire", EDITOR, "--bogus"], "retire-unknown-arg"),
    ):
        res = _run(run_tool, *argv)
        assert res.rc == 2, (
            "[%s] rc=%s, want 2\n%s" % (name, res.rc, res.combined[-600:]))

    happy = _run(run_tool, "retire", EDITOR, "--why", "wrong topic 49607")
    assert happy.rc == 0, (
        "[retire-happy] rc=%s, want 0\n%s" % (happy.rc, happy.combined[-600:]))
    assert not _rows(ledger_sandbox.ledger, EDITOR), (
        "[retire-row-gone] the row is still in .workers[] — retire REMOVES, "
        "it does not flag")

    roster = _run(run_tool, "roster")
    assert EDITOR not in roster.combined, (
        "[retire-roster-drops] the retired uuid still appears in roster "
        "output:\n%s" % (roster.combined[-600:],))

    # the sign gate's predicate (oc-verify-order:98): .role selected by uuid.
    # Empty after retire -> the gate's `[ -n "$ROLE" ] || fail 3 UNSIGNED`.
    role_left = [w.get("role") for w in L.workers(ledger_sandbox.ledger)
                 if w.get("uuid") == EDITOR]
    assert role_left == [], (
        "[retire-loses-signing] a role is still selectable for the retired uuid "
        "(%r), so the sign gate would still admit it" % (role_left,))

    ev = L.last_where(ledger_sandbox.ledger, by="oc-ledger retire")
    assert ev and ev.get("kind") == "roster-retire", (
        "[retire-event-kind] the last retire event is %r, want kind "
        "'roster-retire'" % (ev,))
    want = ("retired toolsmith %s (topic 39171, feature tools, confirmed "
            "false): wrong topic 49607" % EDITOR)
    assert ev.get("what", "").startswith(want), (
        "[retire-event-carries-row] the event reads %r, want it to start %r — "
        "the event is the only surviving record of the row, so it must name "
        "what was removed" % (ev.get("what"), want))

    twice = _run(run_tool, "retire", EDITOR)
    assert twice.rc == 2, (
        "[retire-twice] rc=%s, want 2 — the row is gone, so this is the "
        "not-enrolled path\n%s" % (twice.rc, twice.combined[-600:]))

    # --why is OPTIONAL by design (a correction verb must never block on
    # ceremony); the ABSENCE is recorded verbatim, never silently omitted.
    assert _run(run_tool, "enroll", "55555555-5555-5555-5555-555555555555",
                "probe", "--topic", "7").rc == 0, "fixture: enroll failed"
    no_why = _run(run_tool, "retire", "55555555-5555-5555-5555-555555555555")
    assert no_why.rc == 0, (
        "[retire-why-optional] rc=%s, want 0 — --why is optional\n%s"
        % (no_why.rc, no_why.combined[-600:]))
    ev = L.last_where(ledger_sandbox.ledger, by="oc-ledger retire")
    assert ev.get("what", "").endswith("(no reason given)"), (
        "[retire-why-recorded] the event reads %r, want it to END with "
        "'(no reason given)' — an absent reason is recorded, not omitted"
        % (ev.get("what"),))

    ns = L.ns(ledger_sandbox.ledger)
    assert len(ns) == len(set(ns)), (
        "[retire-event-n-unique] ordinals are not unique: %r — a repeat makes "
        "every consumer that trusts n read a row that cannot exist" % (ns,))


def test_retire_is_row_scoped_not_uuid_scoped(ledger_sandbox, run_tool):
    """``retire-rowscope-*`` + ``retire-selector-*`` (defect fix 2026-09-11).

    A uuid can legitimately hold TWO rows — an editor row on one topic plus an
    auditor row on another. The first cut did ``.workers |= map(select(.uuid !=
    $u))`` and snapshotted the event from ``[0]``, so BOTH rows were revoked by
    an event naming one. Latent on the roster of the day (every uuid held one
    row), which is exactly why the fixture builds the shape by hand: ``enroll``
    refuses a duplicate uuid, so it can only arrive through a migration or an
    incident.

    The ambiguity arms are the other half: with two matching rows and no
    selector the verb REFUSES and writes nothing, rather than picking one.
    """
    doc = L.read_json(ledger_sandbox.ledger)
    for role, topic, feature in (("editor", 49607, "cron-session-isolation"),
                                 ("auditor", 30220, "triage")):
        doc["workers"].append({
            "uuid": U6, "role": role, "topic_id": topic, "feature": feature,
            "confirmed": False, "last_acked": None, "notes": [], "events": []})
    ledger_sandbox.ledger.write_text(json.dumps(doc), encoding="utf-8")

    assert len(_rows(ledger_sandbox.ledger, U6)) == 2, (
        "[retire-rowscope-fixture] the two-row fixture did not take: %r"
        % (_rows(ledger_sandbox.ledger, U6),))
    rev0 = len(L.where(ledger_sandbox.ledger, by="oc-ledger retire"))

    ambiguous = _run(run_tool, "retire", U6)
    assert ambiguous.rc == 2, (
        "[retire-ambiguous-rc2] rc=%s, want 2 — two rows and no selector is a "
        "refusal, never a guess\n%s"
        % (ambiguous.rc, ambiguous.combined[-600:]))
    assert len(_rows(ledger_sandbox.ledger, U6)) == 2, (
        "[retire-ambiguous-keeps-both] %d rows left, want 2 — a refused retire "
        "removes NOTHING" % (len(_rows(ledger_sandbox.ledger, U6)),))
    assert len(L.where(ledger_sandbox.ledger, by="oc-ledger retire")) == rev0, (
        "[retire-ambiguous-no-event] a retire event was written for a call that "
        "refused")

    nomatch = _run(run_tool, "retire", U6, "--topic", "99999")
    assert nomatch.rc == 2, (
        "[retire-selector-nomatch-rc2] rc=%s, want 2 — a selector matching "
        "nothing is a refusal, never a silent no-op\n%s"
        % (nomatch.rc, nomatch.combined[-600:]))
    assert len(_rows(ledger_sandbox.ledger, U6)) == 2, (
        "[retire-selector-nomatch-keeps-both] %d rows left, want 2"
        % (len(_rows(ledger_sandbox.ledger, U6)),))

    by_topic = _run(run_tool, "retire", U6, "--topic", "30220",
                    "--why", "auditor row on 30220")
    assert by_topic.rc == 0, (
        "[retire-topic-selector-rc0] rc=%s, want 0\n%s"
        % (by_topic.rc, by_topic.combined[-600:]))
    left = _rows(ledger_sandbox.ledger, U6)
    assert len(left) == 1, (
        "[retire-topic-removed-one] %d rows left, want 1 — --topic disambiguates"
        % (len(left),))
    assert left[0].get("role") == "editor", (
        "[retire-topic-kept-sibling] the surviving row is %r, want the editor "
        "row on 49607 — the selector must remove the row it NAMED, not its "
        "sibling" % (left[0].get("role"),))
    ev = L.last_where(ledger_sandbox.ledger, by="oc-ledger retire")
    want = ("retired auditor %s (topic 30220, feature triage, confirmed false):"
            " auditor row on 30220" % U6)
    assert ev.get("what", "").startswith(want), (
        "[retire-topic-event-names-removed] the event reads %r, want it to name "
        "the AUDITOR row — an event that names one row while removing both is "
        "how the defect stayed latent" % (ev.get("what"),))

    # --role is an EXACT match here, unlike roster --role's substring match:
    # this verb DESTROYS a row, so a fuzzy selector is a foot-gun.
    fuzzy = _run(run_tool, "retire", U6, "--role", "edit")
    assert fuzzy.rc == 2, (
        "[retire-selector-exact] rc=%s, want 2 — 'edit' is a PREFIX of "
        "'editor' and must not match; a destroying verb takes an exact selector"
        "\n%s" % (fuzzy.rc, fuzzy.combined[-600:]))
    assert len(_rows(ledger_sandbox.ledger, U6)) == 1, (
        "[retire-exact-kept-row] %d rows left, want 1"
        % (len(_rows(ledger_sandbox.ledger, U6)),))

    exact = _run(run_tool, "retire", U6, "--role", "editor")
    assert exact.rc == 0, (
        "[retire-role-selector-rc0] rc=%s, want 0\n%s"
        % (exact.rc, exact.combined[-600:]))
    assert not _rows(ledger_sandbox.ledger, U6), (
        "[retire-role-removed-last] the last row survived — an exact --role "
        "selector must remove it")

    # selector ARGUMENT validation, with the uuid enrolled FIRST so each case
    # fails on the SELECTOR rather than on not-enrolled (a vacuous rc 2 would
    # pass either way, and the control would be inert).
    assert _run(run_tool, "enroll", U6, "editor", "--topic", "49607").rc == 0, (
        "fixture: enroll failed")
    for argv, name in (
        (["retire", U6, "--topic"], "retire-topic-novalue-rc2"),
        (["retire", U6, "--role"], "retire-role-novalue-rc2"),
        (["retire", U6, "--topic", "abc"], "retire-topic-nonnum-rc2"),
    ):
        res = _run(run_tool, *argv)
        assert res.rc == 2, (
            "[%s] rc=%s, want 2 — the selector is invalid, so the call is a "
            "usage error\n%s" % (name, res.rc, res.combined[-600:]))
    assert len(_rows(ledger_sandbox.ledger, U6)) == 1, (
        "[retire-badselector-removes-nothing] %d rows left, want 1 — three "
        "invalid selectors must leave the row alone"
        % (len(_rows(ledger_sandbox.ledger, U6)),))
