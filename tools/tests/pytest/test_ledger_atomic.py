"""Ported: ``oc-ledger`` selftest §H-2 / §D2-#507 / §570 / §A1b / §factory-70 /
§149 / §177 — the WRITE-side stamp guard, the ``atomic_jq`` temp leak,
``atomic_jq``'s silence, the self-verb uuid derivation, LINKED WORKTREES,
``migrate``, and the lock-free read verbs.

Source: ``tools/state/oc-ledger:5101-5560`` (selftest lines 2331-2790) — 62 of
the 475 ``chk`` calls plus 29 ``ok || bad`` / ``case`` legs in the same block.
Every assertion message carries the shell name it replaces.

WHAT THIS MODULE PROTECTS

    * **A stamp that cannot be parsed is a row no window can reach.** ``--at``
      is the ONLY caller-supplied stamp on any path, and it used to be written
      verbatim: the live ledger carried 19 impossible stamps (9 with a literal
      ``x`` for a redacted digit, 2 space-separated, 8 missing their seconds).
      Because ``--since`` compares BYTE-LEXICOGRAPHICALLY, each one silently
      mis-ranked instead of erroring. The refusal arms are asserted per shape
      rather than as one "garbage is refused", and the accept arm asserts the
      STORED value, because "accepts" and "canonicalises" are different
      contracts and only the second keeps the byte-compare honest.
    * **A corpse left by SIGKILL must be collected, a LIVE temp must not be.**
      No trap can catch SIGKILL, so ``sweep_stale_temps`` is the only cover —
      and a blanket ``rm .ledger.*`` would reap a temp mid-write. Both
      directions are asserted (stale reaped, fresh kept), because a sweep that
      reaps everything passes the first leg alone.
    * **A catchable signal mid-write must leave nothing behind**, and the probe
      must never report a vacuous green: if the temp window was never OBSERVED
      the leg says so instead of passing.
    * **A failing ``atomic_jq`` must not fail SILENTLY.** ``2>/dev/null`` turned
      jq's own "string and array cannot be added" into a bare rc 3 that was
      indistinguishable from a bad uuid or a missing ledger; Triage spent several
      turns re-deriving a cause jq had already stated. Leg B is the
      discriminating one — a bare rc 3 cannot distinguish the cause, which IS
      the defect — so it asserts jq's OWN message on stderr AND that the store
      is byte-identical afterwards. Leg A is the other half: the provoking row
      class (a legacy ``.notes`` STRING) is COERCED rather than fatal, so such a
      row self-heals instead of blocking every later promote.
    * **A self verb's uuid is optional and derived from the environment**, but
      the roster-admin path must SURVIVE: acking on ANOTHER lane's uuid is
      documented usage, so a supplied other-uuid must reach the roster check
      (rc 3, unknown uuid) and never a mismatch refusal (rc 2). #657 shipped the
      cross-check as a WARNING instead, and these legs assert the two properties
      that make a warning useful: it NAMES the mismatch, and it never changes
      the outcome. The gate arm keeps a non-uuid ambient SILENT, or every
      fixture and non-session shell would emit the note and it would be noise.
    * **A linked worktree IS a git checkout.** ``.git`` is a FILE there, so
      ``[ -d "$x/.git" ]`` answered FALSE and every state/skill tail silently
      no-oped — one leg per FUNCTION FAMILY (the scope audit, the state commit,
      the commit-pending sweep + its mirror push, the backlog push, the sync
      bump, the bundle half), each paired with the non-git control that must
      KEEP skipping. Without the control an arm passes vacuously on a tool whose
      predicate never runs.
    * **``migrate``'s destination guard must fire on the LIVE dir and NOT on a
      scratch one.** The old guard compared ``STATE_DIR()`` against
      ``$STATE_DIR_DEFAULT`` and both read ``$OC_DEV_STATE``, so with that
      variable set they were equal BY CONSTRUCTION and every scratch dir was
      refused as live. Worse than a false positive: the only way past it was
      ``--live``, the flag that permits the REAL dir — the guard trained
      operators to reach for its own bypass. So the refusal arm runs against a
      RELOCATED ``$HOME`` (never the real record), the positive control runs
      with the same ``$HOME`` against a scratch destination, ``--live`` is
      asserted to still work, and the refusal's PRINTED REMEDY is run VERBATIM
      (it named ``--ledger``, which the arg loop did not accept).
    * **The migration is only half the point; the write path is the other.**
      ``stamp`` on a JSONL dir appends ONE line instead of rewriting the blob,
      and a no-view dir must not have a view created or refreshed for it.

NOTES ON WHAT THE SHELL DOES THAT THIS MODULE DOES DIFFERENTLY

    * The shell's ``$T`` is shared and ``rm -rf``'d mid-block, so several of its
      fixtures are built into a directory an earlier block deleted. Every leg
      here builds its OWN root, and nothing is inherited from the leg above.
    * ``git70-audit-worktree-skipped`` / ``-nongit-still-skips`` are ``ok||bad``
      legs (a grep for ``SKIPPED``), so they carry no ``chk`` row. They are
      ported beside the two ``chk`` fixture-shape legs they depend on, and the
      worktree arm additionally asserts the POSITIVE line, because "the SKIPPED
      note is absent" would also hold for a harness that printed nothing at all.
    * The shell's ``h2 ack --at refuses '$_bad'`` is ONE ``chk`` inside a
      ``for`` loop, so the roster's single row stands for four invocations. It
      is ported as a parametrize with one id per SHAPE and the name rendered
      per arm (``[h2 ack --at refuses '<stamp>']``), which is the mechanical
      expansion of the shell's interpolation — the row is not lost, it is the
      loop's four turns.
    * The ``#507`` trap probe uses a bounded OBSERVATION window (20 s) rather
      than the shell's 5 s: under a loaded box the tool's startup can outlast
      five seconds, and a probe that never sees the window reports
      INCONCLUSIVE — a red that names the fixture, not the tool. The window is
      not a test timeout and nothing sleeps it out on the happy path.

SLOW LEGS
    ``tmp-trap-clears-on-term`` is marked ``slow``: it is the one leg whose
    timing is load-sensitive (it has to observe a temp file while a mutation is
    mid-write), so it is excluded from the ``-m "not slow"`` gate and must be
    run explicitly with ``-m slow``. Everything else here is deterministic
    single-invocation work against a throwaway ledger in this worker's scratch.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")
LEDGER_UUID = cf.LEDGER_ACTOR          # the rostered worker in ledger_sandbox

# =============================================================================
# helpers
# =============================================================================
def _run(run_tool, *args, env=None, **kw):
    return run_tool([str(TOOL)] + [str(a) for a in args], timeout=180,
                    env=env, **kw)

def _md5(path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

def _stored_at(ledger, uuid=LEDGER_UUID):
    """``.workers[]|select(.uuid==U)|.last_acked.at`` — the WRITE, not the rc."""
    for row in L.workers(ledger):
        if row.get("uuid") == uuid:
            return (row.get("last_acked") or {}).get("at")
    return None

# =============================================================================
# H-2 (c23): write-side validation of the ONLY caller-supplied stamp
# =============================================================================
# One entry per SHAPE, not one "garbage" arm: each of these three shapes was
# found in the live ledger, and a guard that refuses only the first would leave
# the other two silently mis-ranking. The ids are the shell's own names.
BAD_AT = [
    ("2026-01-02 03:04:05Z", "space-separated: parses in no ISO reader"),
    ("2026-01-02T03:04Z", "minute precision: the seconds are simply absent"),
    ("2026-01-02T03:0x:05Z", "a literal 'x' for a redacted digit (9 live rows)"),
    ("not-a-stamp", "prose"),
]

@pytest.mark.parametrize("stamp", [b[0] for b in BAD_AT],
                         ids=["space", "minute", "literal-x", "prose"])
def test_ack_at_refuses_a_stamp_no_window_can_reach(ledger_sandbox, run_tool,
                                                    stamp):
    """``h2 ack --at refuses '<stamp>'`` (x4, tool:5101).

    rc 2 and NOTHING written: the row is the thing being guarded, so a refusal
    that still appended would be the defect wearing a guard's clothes.
    """
    before = _md5(ledger_sandbox.ledger)
    res = _run(run_tool, "ack", LEDGER_UUID, "0.9.9", "--at", stamp)
    assert res.rc == 2, (
        "[h2 ack --at refuses '%s'] rc=%s, want 2 — a stamp no ISO reader can "
        "parse mis-ranks against every --since window instead of erroring\n%s"
        % (stamp, res.rc, res.combined[-600:]))
    assert _md5(ledger_sandbox.ledger) == before, (
        "[h2 ack --at refuses '%s'] the refusal MODIFIED the ledger — a refused "
        "write must leave the store byte-identical" % stamp)

def test_ack_at_accepts_the_iso_family_and_stores_the_canonical_form(
        ledger_sandbox, run_tool):
    """``h2 ack --at accepts a well-formed stamp`` (tool:5104).

    Two claims, because they are different contracts: a bare
    ``YYYY-MM-DDThh:mm:ssZ`` is accepted, AND a fractional-seconds stamp is
    accepted and NORMALISED. Accepting without canonicalising would leave the
    stored form multi-shaped, which is exactly what the byte-lexicographic
    ``--since`` compare cannot survive.
    """
    res = _run(run_tool, "ack", LEDGER_UUID, "0.9.9",
               "--at", "2026-01-02T03:04:05Z")
    assert res.rc == 0, (
        "[h2 ack --at accepts a well-formed stamp] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-600:]))
    assert _stored_at(ledger_sandbox.ledger) == "2026-01-02T03:04:05Z", (
        "[h2 ack --at accepts a well-formed stamp] stored at=%r"
        % (_stored_at(ledger_sandbox.ledger),))

    # The canonicalising half: fractional seconds are WELL-FORMED, and refusing
    # them would be a guard that blocks a legitimate write.
    res = _run(run_tool, "ack", LEDGER_UUID, "0.9.10",
               "--at", "2026-01-02T03:04:05.123Z")
    assert res.rc == 0, (
        "[h2 ack --at accepts a well-formed stamp] fractional seconds refused: "
        "rc=%s, want 0 (a fraction is well-formed)\n%s"
        % (res.rc, res.combined[-600:]))
    assert _stored_at(ledger_sandbox.ledger) == "2026-01-02T03:04:05Z", (
        "[h2 ack --at accepts a well-formed stamp] the fraction was not "
        "canonicalised away: stored at=%r, want '2026-01-02T03:04:05Z' — a "
        "multi-shaped stamp is what --since's byte compare cannot rank"
        % (_stored_at(ledger_sandbox.ledger),))

# =============================================================================
# D2 / #507: the atomic_jq temp leak
# =============================================================================
def test_stale_temp_is_swept_and_a_fresh_one_survives(ledger_sandbox, run_tool):
    """``tmp-sweep-stale-reaped`` + ``tmp-sweep-fresh-kept`` (tool:5113-5114).

    A corpse from SIGKILL must be collected by the NEXT mutation — no trap can
    catch SIGKILL, so this sweep is the only cover — while a FRESH temp must
    survive the age gate. Both directions in one leg, because a blanket
    ``rm .ledger.*`` passes the first half alone and would reap a live write.
    """
    state = ledger_sandbox.state
    stale = state / ".ledger.stale1"
    stale.write_text("")
    three_days_ago = time.time() - 3 * 86400
    os.utime(stale, (three_days_ago, three_days_ago))
    fresh = state / ".ledger.fresh1"
    fresh.write_text("")

    res = _run(run_tool, "stamp", "note", "#507 sweep probe")
    assert res.rc == 0, ("the probe stamp failed rc=%s\n%s"
                         % (res.rc, res.combined[-600:]))
    assert not stale.exists(), (
        "[tmp-sweep-stale-reaped] a 3-day-old .ledger.* temp survived the "
        "mutation that should have collected it — a SIGKILLed write's corpse "
        "now sits in the state dir forever")
    assert fresh.exists(), (
        "[tmp-sweep-fresh-kept] the sweep reaped a FRESH temp — a blanket "
        "`rm .ledger.*` would delete a write that is still in flight")

@pytest.mark.slow
def test_a_catchable_signal_mid_write_leaves_no_temp_behind(ledger_sandbox):
    """``tmp-trap-clears-on-term`` (tool:5141).

    The window is opened DETERMINISTICALLY by a ``jq`` shim that sleeps ONLY
    when its stdout is the ``.ledger.*`` temp (the mutation write), so nothing
    else in the invocation is slowed. The ``SAW`` guard matters: a probe that
    never observed the window reports INCONCLUSIVE, never a vacuous green.

    Marked ``slow`` because it is the one leg whose timing depends on the box:
    the observation window has to outlast tool startup, and under a loaded
    machine a short window turns a working trap into a red that names the
    fixture. Run it with ``-m slow``.
    """
    state = ledger_sandbox.state
    shim = ledger_sandbox.path / "shim"
    shim.mkdir(parents=True, exist_ok=True)
    real_jq = shutil.which("jq")
    assert real_jq, "fixture: jq is not on PATH"
    shim_jq = shim / "jq"
    shim_jq.write_text(
        "#!/bin/sh\n"
        "case \"$(readlink /proc/$$/fd/1 2>/dev/null)\" in */.ledger.*) sleep 5 ;; esac\n"
        "exec \"%s\" \"$@\"\n" % real_jq)
    shim_jq.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = "%s:%s" % (shim, env.get("PATH", ""))
    proc = subprocess.Popen(
        [str(TOOL), "stamp", "note", "#507 trap probe"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env, start_new_session=True)

    saw = False
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        if list(state.glob(".ledger.*")):
            saw = True
            break
        if proc.poll() is not None:
            break
        time.sleep(0.05)

    # Kill the whole GROUP, not just the tool: the sleeping jq shim is a child,
    # and the shell's single-pid `kill` leaves it running for up to 5 s. Same
    # assertion, no orphan.
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        proc.wait(timeout=10)

    assert saw, (
        "[tmp-trap-probe-window] the temp was never observed — probe "
        "inconclusive, so [tmp-trap-clears-on-term] would prove nothing. Either "
        "the shim stopped intercepting the mutation write, or the box is too "
        "loaded to open the window inside 20 s. Investigate before trusting the "
        "trap: a probe that never saw the window must never report green.")
    left = sorted(p.name for p in state.glob(".ledger.*"))
    assert not left, (
        "[tmp-trap-clears-on-term] a CATCHABLE SIGTERM mid-write left %s "
        "behind — the EXIT trap is the cover for every catchable signal" % left)

# =============================================================================
# #570: atomic_jq must never fail SILENTLY
# =============================================================================
Q5U = "cccccccc-1111-2222-3333-444444444444"
Q5ARR = [{"n": 1, "t": "2026-10-05T00:00:00Z", "by": "seed",
          "kind": "note", "what": "seed"}]
Q5STR = "legacy string | 2026-09-06 roster-amend n=1604"

def _q570_fixture(root: Path, notes, events) -> Path:
    """The hermetic shape proven in this lane: one worker, caller-chosen notes."""
    state = Path(root) / "state"
    (Path(root) / "skill").mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    doc = {"workers": [{"uuid": Q5U, "role": "editor", "topic_id": 9,
                        "feature": "q570", "notes": notes}],
           "events": events,
           "updated_at": "2026-10-05T00:00:00Z"}
    ledger = state / "workers-ledger.json"
    ledger.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    return ledger

def _q570_env(ledger: Path) -> dict:
    """``OC_ACTOR=`` in the shell, and the ambient id cleared with it.

    Both, because ``_self_uuid`` falls back from ``OPENCRABS_SESSION_ID`` to
    ``OC_ACTOR``: clearing only one leaves a uuid ambient behind, and the
    cross-check note would then land in the stderr these legs read.
    """
    return {"OC_ACTOR": "", "OPENCRABS_SESSION_ID": "",
            "OC_NO_FLOODGUARD": "1",
            "OC_SKILL_DIR": str(Path(ledger).parent.parent / "skill"),
            "OC_LEDGER": str(ledger)}

def test_promote_coerces_a_legacy_string_notes_into_an_array(tmp_path, run_tool):
    """``q570-A-*`` (tool:5170-5175).

    The provoking row class is a legacy ``.notes`` STRING. Adding an entry to a
    string is a jq type error, so before the coercion every promote on such a
    row failed — and the row could never self-heal. Four assertions because
    "rc 0" alone would pass a tool that replaced the notes outright: the legacy
    entry must SURVIVE as element 0, and the role must have been applied.
    """
    ledger = _q570_fixture(tmp_path, Q5STR, Q5ARR)
    res = _run(run_tool, "promote", Q5U, "reviewer", env=_q570_env(ledger))
    assert res.rc == 0, (
        "[q570-A-promote-coerces-a-string-notes] rc=%s, want 0 — a legacy "
        "string .notes must be coerced, not fatal\n%s"
        % (res.rc, res.combined[-800:]))

    row = L.workers(ledger)[0]
    assert isinstance(row.get("notes"), list), (
        "[q570-A-notes-became-an-array] notes is %s, want array"
        % type(row.get("notes")).__name__)
    assert row["notes"][0] == Q5STR, (
        "[q570-A-legacy-entry-survived] notes[0]=%r, want the legacy string "
        "verbatim — a coercion that drops the old entry destroys history"
        % (row["notes"][0],))
    assert row.get("role") == "reviewer", (
        "[q570-A-role-was-applied] role=%r, want 'reviewer'" % (row.get("role"),))

def test_a_genuine_jq_failure_returns_3_and_says_why(tmp_path, run_tool):
    """``q570-B-*`` (tool:5182-5187).

    The discriminating half of #570: a bare rc 3 cannot distinguish "bad uuid"
    from "the ledger is missing" from "jq refused the addition", which IS the
    defect. So the leg asserts jq's OWN message on stderr — never a paraphrase
    of it — and that the store is byte-identical afterwards.
    """
    ledger = _q570_fixture(tmp_path, Q5ARR, Q5STR)
    before = _md5(ledger)
    res = _run(run_tool, "promote", Q5U, "reviewer", env=_q570_env(ledger))

    assert res.rc == 3, (
        "[q570-B-jq-failure-still-returns-3] rc=%s, want 3 — a genuine jq "
        "failure keeps its own code\n%s" % (res.rc, res.combined[-800:]))
    assert "atomic_jq failed" in res.err, (
        "[q570-B-names-the-cause-on-stderr] stderr does not say 'atomic_jq "
        "failed'; the failure is SILENT, which is the whole of #570\nstderr=%r"
        % res.err[-800:])
    assert "cannot be added" in res.err, (
        "[q570-B-carries-jq-s-OWN-message] stderr does not carry jq's own "
        "text ('cannot be added') — a caller still has to re-derive the "
        "cause\nstderr=%r" % res.err[-800:])
    assert _md5(ledger) == before, (
        "[q570-B-store-UNTOUCHED-on-failure] the failed promote MODIFIED the "
        "ledger — a failed atomic_jq must leave the store byte-identical")

# =============================================================================
# A1b: a SELF verb's uuid is optional, derived from the environment
# =============================================================================
A1W = "bbbbbbbb-1111-2222-3333-444444444444"
A1E = "cccccccc-1111-2222-3333-444444444444"

@pytest.fixture
def a1b_ledger(tmp_path) -> Path:
    """A PRIVATE store, as the shell's A1b block builds one.

    Self-contained on purpose: an earlier version ran against the shared fixture
    ledger and enrolling a worker made four roster-count legs elsewhere read one
    extra — fixture pollution that reads as a defect.
    """
    ledger = Path(tmp_path) / "workers-ledger.json"
    ledger.write_text(json.dumps({"workers": [{
        "uuid": A1W, "role": "tester", "topic": "1", "feature": "a1b",
        "last_acked": None, "confirmed": False, "notes": []}],
        "events": []}) + "\n", encoding="utf-8")
    return ledger

def _a1b_env(ledger, session_id: str, actor: str = "") -> dict:
    return {"OC_ACTOR": actor, "OPENCRABS_SESSION_ID": session_id,
            "OC_LEDGER": str(ledger),
            "OC_SKILL_DIR": str(Path(ledger).parent / "skill")}

def _enrol_other_lane(run_tool, ledger) -> None:
    """Reach the precondition BY CALLING the verb, not by seeding the roster.

    The shell's A1b block enrolls ``$A1E`` a few lines above its warn legs, so
    the warn legs inherit a two-row roster. Seeding that row in the fixture
    instead would make ``a1b-enroll-single-arg-is-role`` — which enrolls the
    same uuid — die "already enrolled" and measure the wrong thing. Calling the
    verb here keeps each leg independent AND keeps that leg honest.
    """
    res = _run(run_tool, "enroll", "a1b-tester", env=_a1b_env(ledger, A1E))
    assert res.rc == 0, (
        "fixture precondition: enrolling the other lane failed rc=%s\n%s"
        % (res.rc, res.combined[-600:]))

def _role_of(ledger, uuid):
    for row in L.workers(ledger):
        if row.get("uuid") == uuid:
            return row.get("role")
    return ""

def _acked_version(ledger, uuid):
    for row in L.workers(ledger):
        if row.get("uuid") == uuid:
            return (row.get("last_acked") or {}).get("version") or ""
    return ""

def test_ack_derives_the_uuid_from_the_ambient_session(a1b_ledger, run_tool):
    """``a1b-ack-no-uuid-derives`` + ``a1b-ack-wrote-the-env-id`` (5205-5206).

    The owner's directive: the tools required the lane to pass its own session
    id while the environment already held it. The write is asserted, not just
    the rc — a tool that accepted the argument and acked nobody would pass an
    rc-only leg.
    """
    res = _run(run_tool, "ack", "0.9.1", env=_a1b_env(a1b_ledger, A1W))
    assert res.rc == 0, (
        "[a1b-ack-no-uuid-derives] rc=%s, want 0 — a single non-uuid argument "
        "is the VERSION and the uuid comes from the ambient session\n%s"
        % (res.rc, res.combined[-600:]))
    assert _acked_version(a1b_ledger, A1W) == "0.9.1", (
        "[a1b-ack-wrote-the-env-id] last_acked.version=%r, want '0.9.1' on the "
        "AMBIENT id" % (_acked_version(a1b_ledger, A1W),))

def test_ack_without_any_ambient_id_refuses_and_names_the_remedy(a1b_ledger,
                                                               run_tool):
    """``a1b-ack-no-env-refuses`` + ``a1b-refusal-names-the-remedy`` (5210-5211).

    rc 2 rather than a silent no-op, and the message has to name what to do:
    an operator reading "no uuid" with no remedy re-runs the same command.
    """
    res = _run(run_tool, "ack", "0.9.2", env=_a1b_env(a1b_ledger, ""))
    assert res.rc == 2, (
        "[a1b-ack-no-env-refuses] rc=%s, want 2 (usage: no uuid, no ambient)\n%s"
        % (res.rc, res.combined[-600:]))
    assert re.search(r"OPENCRABS_SESSION_ID|pass the uuid explicitly", res.err), (
        "[a1b-refusal-names-the-remedy] stderr names no remedy — it must say "
        "OPENCRABS_SESSION_ID or 'pass the uuid explicitly'\nstderr=%r"
        % res.err[-600:])

def test_enroll_treats_a_single_argument_as_the_role(a1b_ledger, run_tool):
    """``a1b-enroll-single-arg-is-role`` + ``a1b-enroll-used-the-env-id``.

    Disambiguated BY SHAPE: for ``ack`` a lone non-uuid is the VERSION, for
    ``enroll`` it is the ROLE. A fresh uuid is used because ``$A1W`` is already
    enrolled above, and enrolling it again would die "already enrolled" and
    measure the wrong thing.
    """
    res = _run(run_tool, "enroll", "a1b-tester",
               env=_a1b_env(a1b_ledger, A1E))
    assert res.rc == 0, (
        "[a1b-enroll-single-arg-is-role] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-600:]))
    assert _role_of(a1b_ledger, A1E) == "a1b-tester", (
        "[a1b-enroll-used-the-env-id] role=%r on uuid %s, want 'a1b-tester'"
        % (_role_of(a1b_ledger, A1E), A1E))

def test_a_supplied_other_uuid_reaches_the_roster_check(a1b_ledger, run_tool):
    """``a1b-other-uuid-not-cross-checked`` (5231) — THE DECISION LEG.

    Acking on ANOTHER lane's uuid is documented usage (the ack2 fixture drives
    it end to end), and A1b's cross-check half would refuse it — 60 legs redden
    under that rule. So a supplied other-uuid must reach the ROSTER check
    (rc 3, unknown uuid), never a mismatch refusal (rc 2). If someone adds the
    unconditional cross-check later, THIS leg reddens first and says why.
    """
    res = _run(run_tool, "ack", "aaaaaaaa-1111-2222-3333-444444444444", "0.9.3",
               env=_a1b_env(a1b_ledger, A1W))
    assert res.rc == 3, (
        "[a1b-other-uuid-not-cross-checked] rc=%s, want 3 (unknown uuid on the "
        "ROSTER) — a 2 here means the ambient/supplied cross-check became a "
        "refusal and the roster-admin path is gone\n%s"
        % (res.rc, res.combined[-600:]))

def test_the_cross_check_warns_and_never_changes_the_outcome(a1b_ledger,
                                                            run_tool):
    """``a1b-other-uuid-warns`` + ``a1b-warned-ack-still-succeeds`` +
    ``a1b-warned-ack-wrote-the-other-lane`` (5237-5241).

    #657 shipped the cross-check as a WARNING. Two properties make a warning
    useful rather than noise: it NAMES the mismatch, and it never changes the
    outcome. Both are asserted, plus the write on the OTHER lane's row, because
    a warning that also silently retargeted the write would be worse than none.
    """
    _enrol_other_lane(run_tool, a1b_ledger)
    res = _run(run_tool, "ack", A1E, "0.9.5", env=_a1b_env(a1b_ledger, A1W))
    assert "NOT the ambient session" in res.combined, (
        "[a1b-other-uuid-warns] no warning naming the mismatch\nout=%r"
        % res.combined[-800:])
    assert res.rc == 0, (
        "[a1b-warned-ack-still-succeeds] rc=%s, want 0 — the cross-check is a "
        "WARNING, and a warning that refuses is a gate nobody declared\n%s"
        % (res.rc, res.combined[-600:]))
    assert _acked_version(a1b_ledger, A1E) == "0.9.5", (
        "[a1b-warned-ack-wrote-the-other-lane] last_acked.version=%r on %s, "
        "want '0.9.5'" % (_acked_version(a1b_ledger, A1E), A1E))

def test_a_non_uuid_ambient_stays_silent(a1b_ledger, run_tool):
    """``a1b-label-ambient-stays-silent`` (5246) — the GATE on the warning.

    Fixtures and non-session shells carry a LABEL (``test-runner``) in the
    ambient slot. If the warning fired for those, every fixture run would emit
    it and the real mismatch would be indistinguishable from the noise.
    """
    _enrol_other_lane(run_tool, a1b_ledger)
    res = _run(run_tool, "ack", A1E, "0.9.6",
               env=_a1b_env(a1b_ledger, "test-runner", actor="test-runner"))
    assert "NOT the ambient session" not in res.combined, (
        "[a1b-label-ambient-stays-silent] a non-uuid ambient ('test-runner') "
        "produced the mismatch warning — every fixture and non-session shell "
        "would emit it and the warning becomes noise\nout=%r"
        % res.combined[-800:])
    assert res.rc == 0, ("[a1b-label-ambient-stays-silent] rc=%s, want 0\n%s"
                         % (res.rc, res.combined[-600:]))

# =============================================================================
# factory #70: a LINKED WORKTREE is a git checkout
# =============================================================================
# ``.git`` is a FILE in a worktree, so ``[ -d "$x/.git" ]`` answered FALSE and
# every state/skill tail silently no-oped — the v0.4.157 defect, reachable again
# from any worktree because the guard read "no repo" and went INERT.
#
# This block builds its OWN root: the shell's shared ``$T`` is ``rm -rf``'d by an
# earlier block, so a fixture pointed into it tests a nonexistent path and every
# arm reddens for the wrong reason (measured on the first run: 15 arms, all
# "cannot change to .../state").
W70_LEDGER = {
    "current_skill_version": "0.4.1",
    "meta": {"skill_version": "0.4.1", "current_skill_version": "0.4.1"},
    "updated_at": "2026-01-01T00:00:00Z",
    # The rostered actor is not decoration: ``stamp`` REFUSES an anonymous row
    # (#19) and WARNS on an unrostered one, and that warning on stderr is noise
    # this block's assertions would have to read past.
    "workers": [{"uuid": cf.LEDGER_ACTOR, "role": "tester", "topic_id": 1,
                 "feature": "-", "confirmed": True, "last_acked": None,
                 "notes": [], "events": []}],
    "events": [],
}

class W70:
    """The #70 fixture root: a state repo, a skill repo, and their worktrees."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.state = self.root / "state"
        self.skill = self.root / "skill"
        self.state_wt = self.root / "state-wt"
        self.skill_wt = self.root / "skill-wt"
        self.origin = self.root / "state-origin.git"

@pytest.fixture
def w70(scratch):
    """Build the state/skill pair, then add a linked worktree to each.

    The bare origin exists so the ``commit-pending`` mirror tail has somewhere
    to PUSH: without a remote the push arm silently no-ops and the assertion
    would pass on a tool that never pushed anything.
    """
    root = scratch.path / "w70" / ("w%d" % next(cf._SEQ))
    root.mkdir(parents=True, exist_ok=True)
    w = W70(root)
    (w.skill / "tools" / "tests").mkdir(parents=True, exist_ok=True)
    w.state.mkdir(parents=True, exist_ok=True)
    (w.skill / "tools" / "tests" / ".keep").write_text("", encoding="utf-8")
    L.write(w.state / "workers-ledger.json", json.dumps(W70_LEDGER))
    (w.skill / "SKILL.md").write_text(
        "name: fixture\nversion: 0.4.2\n---\n# fixture\n", encoding="utf-8")
    (w.skill / "CHANGELOG.md").write_text("# fixture changelog\n", encoding="utf-8")
    L.make_battery(w.skill / "tools" / "tests" / "battery-last.json")
    for repo in (w.state, w.skill):
        L.init_repo(repo)

    L.git(w.state, "worktree", "add", "-q", str(w.state_wt), "-b", "wt70state",
           check=True)
    L.git(w.skill, "worktree", "add", "-q", str(w.skill_wt), "-b", "wt70skill",
          check=True)
    L.git(root, "init", "-q", "--bare", str(w.origin), check=True)
    L.git(w.state_wt, "remote", "add", "origin", str(w.origin))
    L.git(w.state_wt, "push", "-q", "-u", "origin", "HEAD")
    return w

def _w70_env(w: W70, **kw) -> dict:
    env = {"OC_LEDGER": str(w.state / "workers-ledger.json"),
           "OC_SKILL_DIR": str(w.skill),
           "OC_DEPLOY_STATE_DIR": str(w.state),
           "OC_ACTOR": cf.LEDGER_ACTOR}
    env.update(kw)
    return env

def _scope_harness(tool_source: str) -> str:
    """Extract the three functions ``state_out_of_scope_audit`` calls.

    The shell builds this with three ``awk`` ranges and then asserts the helper
    came along (``git70-scope-harness-carries-the-helper``). The helper is
    load-bearing: without ``_is_git_repo`` every call returns 127, the SKIP
    branch fires on EVERY path, and the arms measure a fixture that never ran.
    """
    out = []
    for name in ("_is_git_repo", "_ledger_tracked_names", "state_out_of_scope_audit"):
        m = re.search(r"^%s\(\) \{.*?^\}$" % re.escape(name), tool_source,
                      re.MULTILINE | re.DOTALL)
        assert m, ("fixture: %s() is not in the tool source — the scope harness "
                   "cannot be extracted" % name)
        out.append(m.group(0))
    return "\n".join(out) + "\n"

def _scope_declaration(tool_source: str, name: str) -> str:
    m = re.search(r"^%s=(.*)$" % re.escape(name), tool_source, re.MULTILINE)
    assert m, "fixture: %s= is not declared in the tool source" % name
    return m.group(1).strip().strip("'").strip('"')

def _audit(harness: Path, declarations: dict, state_dir: Path):
    """``state_out_of_scope_audit`` with ``STATE_DIR()`` overridden.

    The shell sources the extracted functions under a fake ``STATE_DIR``; the
    same shape here, so the audit is exercised against a directory that is not
    this tool's own ledger dir.
    """
    script = (
        'STATE_DIR() { printf "%%s\\n" "%s"; }\n'
        '. "%s"\n'
        'state_out_of_scope_audit\n' % (state_dir, harness))
    env = dict(os.environ)
    env.update(declarations)
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env=env)

def test_the_scope_audit_runs_in_a_worktree_and_still_skips_a_plain_dir(
        w70, tools_dir, tmp_path):
    """``git70-scope-harness-carries-the-helper``, ``git70-state-wt-fixture-is-a-
    gitdir-FILE``, ``git70-audit-worktree-skipped``, ``git70-audit-nongit-still-
    skips`` (tool:5284-5297).

    One test because the four are one fixture and one mechanism: the harness
    carries the helper, the fixture is genuinely a worktree, the audit therefore
    RUNS there, and a plain directory still SKIPS. The non-git arm is the
    control — without it "the SKIPPED note is absent" would pass on a harness
    that printed nothing at all.
    """
    source = (tools_dir / "state" / "oc-ledger").read_text(encoding="utf-8")
    harness = Path(tmp_path) / "scope_fn.sh"
    harness.write_text(_scope_harness(source), encoding="utf-8")
    declarations = {
        "STATE_TRACKED_PATHS": _scope_declaration(source, "STATE_TRACKED_PATHS"),
        "STATE_TRACKED_GLOB": _scope_declaration(source, "STATE_TRACKED_GLOB"),
    }

    assert harness.read_text().count("_is_git_repo() {") == 1, (
        "[git70-scope-harness-carries-the-helper] the extracted snippet does "
        "not carry _is_git_repo — every call returns 127, the SKIP branch fires "
        "on every path, and the arms below measure a fixture that never ran")

    assert (w70.state_wt / ".git").is_file() and not (w70.state_wt / ".git").is_dir(), (
        "[git70-state-wt-fixture-is-a-gitdir-FILE] .git in the worktree is not a "
        "FILE — this is not a linked worktree, so the legs below would measure "
        "the wrong predicate")

    res = _audit(harness, declarations, w70.state_wt)
    assert "SKIPPED" not in res.stderr, (
        "[git70-audit-worktree-skipped] the audit SKIPPED a linked worktree — "
        "`[ -d .git ]` answered false there and the tail silently no-oped\n%s"
        % res.stderr[-600:])
    assert "every one of the 1 tracked file(s) is carried by a commit path." in res.stderr, (
        "[git70-audit-worktree-skipped] the audit ran but did not reach its "
        "clean verdict — 'the SKIPPED note is absent' would also hold for a "
        "harness that printed nothing at all\nstderr=%r" % res.stderr[-600:])

    plain = Path(tmp_path) / "notgit"
    plain.mkdir()
    res = _audit(harness, declarations, plain)
    assert "SKIPPED" in res.stderr, (
        "[git70-audit-nongit-still-skips] a plain directory did NOT skip — the "
        "control is what keeps the worktree arm from passing vacuously\n%s"
        % res.stderr[-600:])

def test_a_stamp_in_a_worktree_state_dir_commits(w70, run_tool):
    """``git70-state-commit-in-worktree`` + ``git70-state-commit-head-moved``.

    ``_git_state_commit_now`` is the tail that went inert: the row was written
    and never committed, so the worktree accumulated uncommitted state that the
    next lane's pull would not see. HEAD moving is the assertion; the message is
    the diagnosis.
    """
    head_before = L.head(w70.state_wt)
    res = _run(run_tool, "stamp", "note", "git70 worktree commit",
               env=_w70_env(w70, OC_LEDGER=str(w70.state_wt / "workers-ledger.json")))
    assert "git: state commit ok" in res.combined, (
        "[git70-state-commit-in-worktree] no 'git: state commit ok' — a stamp in "
        "a WORKTREE state dir did not commit\n%s" % res.combined[-900:])
    assert L.head(w70.state_wt) != head_before, (
        "[git70-state-commit-head-moved] HEAD did not move — the tool reported a "
        "commit that did not happen")

def test_commit_pending_commits_and_pushes_from_a_worktree(w70, run_tool):
    """``git70-commit-pending-worktree-rc``, ``-committed``, ``-push-mirror``,
    ``git70-push-mirror-received`` (tool:5312-5318).

    The sweep must COMMIT and its mirror tail must PUSH — ``push_mirror`` is
    guarded by the same ``_is_git_repo`` test, so one arm covers both. The
    RECEIVED arm is the one that cannot be faked by a local commit: it compares
    the BARE repo's branch tip against the worktree's HEAD, because the bare
    repo's own HEAD still names the default branch the push never created.
    """
    ledger = w70.state_wt / "workers-ledger.json"
    doc = L.read_json(ledger)
    doc["events"] = list(doc.get("events") or []) + [
        {"n": 9901, "t": "x", "by": "tool", "kind": "note", "what": "git70-wt"}]
    ledger.write_text(json.dumps(doc), encoding="utf-8")

    head_before = L.head(w70.state_wt)
    res = _run(run_tool, "commit-pending",
               env=_w70_env(w70, OC_LEDGER=str(ledger)))
    assert res.rc == 0, (
        "[git70-commit-pending-worktree-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-900:]))
    assert L.head(w70.state_wt) != head_before, (
        "[git70-commit-pending-worktree-committed] HEAD did not move — "
        "commit-pending no-oped in a linked worktree")
    assert "mirror: state pushed" in res.combined, (
        "[git70-push-mirror-worktree] no 'mirror: state pushed' — the mirror "
        "tail is guarded by the same predicate that went inert\n%s"
        % res.combined[-900:])
    pushed = L.git(w70.origin, "rev-parse", "--verify", "-q",
                   "refs/heads/wt70state").stdout.strip()
    assert pushed == L.head(w70.state_wt), (
        "[git70-push-mirror-received] the bare repo's wt70state tip (%r) is not "
        "the worktree's HEAD (%r) — the push was reported, not received"
        % (pushed, L.head(w70.state_wt)))

def test_the_backlog_push_fires_in_a_worktree(w70, run_tool):
    """``git70-push-backlog-worktree`` (tool:5332).

    Forced with ``OC_LEDGER_PUSH_MIN=1``: the default 10-commit threshold would
    return before the guard could matter, so the arm would pass on a tool whose
    backlog path never ran.
    """
    res = _run(run_tool, "stamp", "note", "git70 backlog",
               env=_w70_env(w70, OC_LEDGER=str(w70.state_wt / "workers-ledger.json"),
                            OC_LEDGER_PUSH_MIN="1"))
    assert "mirror-due: state" in res.combined, (
        "[git70-push-backlog-worktree] no 'mirror-due: state' — the backlog "
        "push no-oped in a linked worktree\n%s" % res.combined[-900:])

def test_sync_refuses_a_stray_and_then_bumps_in_a_worktree(w70, run_tool):
    """``git70-skill-wt-fixture-is-a-gitdir-FILE``, ``git70-sync-worktree-stray-
    refused``, ``-stray-names-path``, ``-bump-rc``, ``-bump-committed``,
    ``-bump-subject``, ``-bump-log-empty`` (tool:5327-5342, 5348).

    With ``OC_SKILL_DIR`` a WORKTREE the stray-guard must FIRE (it read "no repo"
    and went INERT) and a clean bump must COMMIT into the worktree. The stray
    arm's rc 7 is the same code a non-worktree repo gives, which is the point:
    the guard is not supposed to know what a worktree is, only what a repo is.
    """
    assert (w70.skill_wt / ".git").is_file() and not (w70.skill_wt / ".git").is_dir(), (
        "[git70-skill-wt-fixture-is-a-gitdir-FILE] .git in the skill worktree is "
        "not a FILE — this is not a linked worktree")

    current = L.read_json(w70.state / "workers-ledger.json").get(
        "current_skill_version") or "0.4.0"
    nxt = "%s.%s" % (current.rsplit(".", 1)[0], int(current.rsplit(".", 1)[1]) + 1)

    # The doc halves a bump needs: the CHANGELOG entry (C8) and a green receipt.
    with open(w70.skill_wt / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v%s\nworktree receipt\n" % nxt)
    L.make_battery(w70.skill_wt / "tools" / "tests" / "battery-last.json")
    stray = w70.skill_wt / "tools" / "wt-stray-probe.sh"
    stray.write_text("wt-stray\n", encoding="utf-8")

    res = _run(run_tool, "sync", "--version", nxt, "--why", "git70-stray",
               env=_w70_env(w70, OC_SKILL_DIR=str(w70.skill_wt)))
    assert res.rc == 7, (
        "[git70-sync-worktree-stray-refused] rc=%s, want 7 — the stray-guard "
        "went INERT in a linked worktree\n%s" % (res.rc, res.combined[-900:]))
    assert "wt-stray-probe.sh" in res.combined, (
        "[git70-sync-worktree-stray-names-path] the refusal does not name the "
        "offending path, so the operator cannot act on it\n%s"
        % res.combined[-900:])

    stray.unlink()
    head_before = L.head(w70.skill_wt)
    res = _run(run_tool, "sync", "--version", nxt, "--why", "git70-bump",
               env=_w70_env(w70, OC_SKILL_DIR=str(w70.skill_wt)))
    assert res.rc == 0, (
        "[git70-sync-worktree-bump-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-1200:]))
    assert L.head(w70.skill_wt) != head_before, (
        "[git70-sync-worktree-bump-committed] HEAD did not move — the bump was "
        "reported and never committed")
    assert L.log_subject(w70.skill_wt).startswith("skill v%s" % nxt), (
        "[git70-sync-worktree-bump-subject] subject=%r, want it to start with "
        "'skill v%s'" % (L.log_subject(w70.skill_wt), nxt))
    assert res.combined.strip(), (
        "[git70-sync-worktree-bump-log-empty] the sync log is empty — a failing "
        "sync would then be undiagnosable")

def test_the_bundle_commits_the_skill_half_in_a_worktree(w70, run_tool):
    """``git70-bundle-worktree-skill`` (tool:5346).

    The SKILL half of ``commit-pending --bundle`` is the same predicate in a
    second home; fixing one and not the other is the shape this leg catches.
    """
    L.make_battery(w70.skill_wt / "tools" / "tests" / "battery-last.json",
                   extra=',"probe":"bundle70"')
    res = _run(run_tool, "commit-pending", "--bundle",
               env=_w70_env(w70, OC_SKILL_DIR=str(w70.skill_wt),
                            OC_LEDGER=str(w70.state_wt / "workers-ledger.json")))
    assert "runtime artifacts committed" in res.combined, (
        "[git70-bundle-worktree-skill] no 'runtime artifacts committed' — the "
        "skill half of --bundle no-oped in a linked worktree\n%s"
        % res.combined[-900:])

# =============================================================================
# #149: migrate a legacy single-file ledger -> DELIBERATELY NOT PORTED HERE
# =============================================================================
# This block was ported by a second pass into its own module,
# ``test_ledger_migrate.py`` (10 tests, same ``mig149-*`` names). Kept as a
# pointer rather than a copy: two modules asserting the same chk names drift,
# and the one that stops being read is the one that rots. The migration is a
# verb, so it gets a verb module.

# =============================================================================
# #177: the lock-free read verbs
# =============================================================================
# ``workers`` / ``worker`` / ``events --all|--jsonl`` / ``ok`` take no lock and
# never slurp the view. The fixtures cover BOTH shapes — the compact legacy file
# and a JSONL dir (record + workers.json, view possibly absent in a fresh clone)
# — plus the ``--ledger events.jsonl`` remap.
R177_DOC = {
    "workers": [
        {"uuid": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "role": "editor",
         "topic_id": 7, "feature": "x", "state": "ACTIVE"},
        {"uuid": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "role": "toolsmith",
         "topic_id": 0, "feature": "-", "state": "RETIRED"},
    ],
    "events": [
        {"n": 1, "t": "2026-11-25T09:00:00Z", "kind": "claim",
         "by": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "what": "CLAIM #177"},
        {"n": 2, "t": "2026-11-25T09:01:00Z", "kind": "note",
         "by": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "what": "hello"},
    ],
}
R177_EDITOR = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
R177_TOOLSMITH = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

@pytest.fixture
def r177(scratch):
    """A legacy compact ledger, a JSONL dir with no view, and a malformed one."""
    root = scratch.path / "r177" / ("r%d" % next(cf._SEQ))
    root.mkdir(parents=True, exist_ok=True)
    legacy = root / "workers-ledger.json"
    legacy.write_text(json.dumps(R177_DOC), encoding="utf-8")

    jl = root / "jl"
    jl.mkdir()
    (jl / "events.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in R177_DOC["events"]), encoding="utf-8")
    (jl / "workers.json").write_text(
        json.dumps({"workers": R177_DOC["workers"][:1]}), encoding="utf-8")

    bad = root / "bad"
    bad.mkdir()
    (bad / "workers-ledger.json").write_text("not json\n", encoding="utf-8")

    noview = root / "noview"
    noview.mkdir()
    (noview / "events.jsonl").write_text(
        json.dumps({"n": 1, "t": "2026-11-25T09:00:00Z", "kind": "note",
                    "by": "hq", "what": "seed"}) + "\n", encoding="utf-8")
    (noview / "workers.json").write_text(
        json.dumps({"workers": [], "updated_at": "2026-11-25T09:00:00Z"}),
        encoding="utf-8")
    return cf.Node(root, legacy=legacy, jl=jl, bad=bad, noview=noview)

def _r177(run_tool, ledger, *args, **kw):
    return _run(run_tool, *args, env={"OC_LEDGER": str(ledger)}, **kw)

def test_the_legacy_compact_ledger_is_fully_readable(r177, run_tool):
    """``r177-ok-legacy-rc``, ``-workers-count``, ``-workers-first-role``,
    ``-worker-tsv``, ``-worker-miss-rc``, ``-events-all-count``, ``-events-kind-
    filter``, ``-events-all-empty-is-rc0``, ``-events-all-empty-array``,
    ``-events-tail-nomatch-still-rc1`` (tool:5507-5545).

    One test because the ten are one fixture read ten ways, and because the
    interesting assertion is the CONTRAST: an empty ``--all`` is rc 0 with ``[]``
    while a no-match TAIL is rc 1. Collapsing those two would make "the ledger
    holds no such event" indistinguishable from "wrong filter".
    """
    res = _r177(run_tool, r177.legacy, "ok")
    assert res.rc == 0, ("[r177-ok-legacy-rc] rc=%s, want 0\n%s"
                         % (res.rc, res.combined[-600:]))

    res = _r177(run_tool, r177.legacy, "workers", "--json")
    assert res.rc == 0, ("[r177-workers-count] rc=%s\n%s"
                         % (res.rc, res.combined[-600:]))
    rows = json.loads(res.out)
    assert len(rows) == 2, "[r177-workers-count] %d rows, want 2" % len(rows)
    assert rows[0]["role"] == "editor", (
        "[r177-workers-first-role] first role=%r, want 'editor'"
        % (rows[0].get("role"),))

    res = _r177(run_tool, r177.legacy, "worker", "--uuid", R177_TOOLSMITH)
    assert res.rc == 0, ("[r177-worker-tsv] rc=%s\n%s"
                         % (res.rc, res.combined[-600:]))
    assert res.out.rstrip("\n") == "\t".join(
        [R177_TOOLSMITH, "toolsmith", "0", "RETIRED"]), (
        "[r177-worker-tsv] rendered %r, want uuid/role/topic_id/state as TSV — "
        "oc-notify-fanout's extract reads exactly this shape"
        % (res.out.rstrip("\n"),))

    res = _r177(run_tool, r177.legacy, "worker", "--uuid",
                "00000000-0000-4000-8000-000000000000")
    assert res.rc == 1, (
        "[r177-worker-miss-rc] rc=%s, want 1 — a NO-MATCH is a verdict, not an "
        "error\n%s" % (res.rc, res.combined[-600:]))

    res = _r177(run_tool, r177.legacy, "events", "--json", "--all")
    assert len(json.loads(res.out)) == 2, (
        "[r177-events-all-count] %d events, want 2" % len(json.loads(res.out)))

    res = _r177(run_tool, r177.legacy, "events", "--kind", "note", "--json", "--all")
    assert len(json.loads(res.out)) == 1, (
        "[r177-events-kind-filter] %d notes, want 1 — the filter must actually "
        "filter" % len(json.loads(res.out)))

    res = _r177(run_tool, r177.legacy, "events", "--kind", "nosuch", "--json", "--all")
    assert res.rc == 0, (
        "[r177-events-all-empty-is-rc0] rc=%s, want 0 — an --all over an empty "
        "match is an empty RESULT, not a verdict\n%s"
        % (res.rc, res.combined[-600:]))
    assert res.out.strip() == "[]", (
        "[r177-events-all-empty-array] printed %r, want []" % res.out.strip())

    res = _r177(run_tool, r177.legacy, "events", "--kind", "nosuch")
    assert res.rc == 1, (
        "[r177-events-tail-nomatch-still-rc1] rc=%s, want 1 — the TAIL keeps "
        "its verdict code; --all must not have flattened it\n%s"
        % (res.rc, res.combined[-600:]))

def test_a_jsonl_dir_reads_without_a_view_and_with_a_record_remap(r177, run_tool):
    """``r177-ok-jsonl-without-view-rc``, ``-jsonl-workers-count``, ``-jsonl-
    events-lines``, ``-remap-events-jsonl-workers``, ``-remap-events-jsonl-
    events``, ``r177-ok-malformed-rc`` (tool:5529-5542).

    A fresh clone has the record and ``workers.json`` but no view. The REMAP
    arms are the other half: ``--ledger events.jsonl`` must be used as the
    record path, which is what lets a caller name the file it actually holds.
    """
    missing_view = r177.jl / "workers-ledger.json"
    assert not missing_view.exists(), "fixture: the view must be absent"

    res = _r177(run_tool, missing_view, "ok")
    assert res.rc == 0, (
        "[r177-ok-jsonl-without-view-rc] rc=%s, want 0 — a JSONL dir with no "
        "view is a valid store\n%s" % (res.rc, res.combined[-600:]))

    res = _r177(run_tool, missing_view, "workers", "--json")
    assert len(json.loads(res.out)) == 1, (
        "[r177-jsonl-workers-count] %d rows, want 1 (from workers.json)"
        % len(json.loads(res.out)))

    res = _r177(run_tool, missing_view, "events", "--jsonl")
    assert len(res.out.splitlines()) == 2, (
        "[r177-jsonl-events-lines] %d lines, want 2 (the record is already "
        "JSONL; this must not re-render it)" % len(res.out.splitlines()))

    # --ledger events.jsonl is used as the record path (#177; no view remap).
    res = _r177(run_tool, r177.jl / "events.jsonl", "workers", "--json")
    assert len(json.loads(res.out)) == 1, (
        "[r177-remap-events-jsonl-workers] %d rows, want 1 — naming the record "
        "must find its sibling workers.json" % len(json.loads(res.out)))

    res = _r177(run_tool, r177.jl / "events.jsonl", "events", "--json", "--all")
    assert len(json.loads(res.out)) == 2, (
        "[r177-remap-events-jsonl-events] %d events, want 2"
        % len(json.loads(res.out)))

    res = _r177(run_tool, r177.bad / "workers-ledger.json", "ok")
    assert res.rc == 3, (
        "[r177-ok-malformed-rc] rc=%s, want 3 — unreadable is its own code, "
        "never 1 (no match)\n%s" % (res.rc, res.combined[-600:]))

def test_a_jsonl_stamp_appends_the_record_and_never_creates_a_view(r177, run_tool):
    """``r177-stamp-jsonl-no-view-file`` + ``r177-stamp-jsonl-appended``
    (tool:5551-5552).

    #177's second half: a stamp in JSONL mode appends to the record and must not
    CREATE or REFRESH the view. A view written here would resurrect the O(n)
    write the whole change removed — and it would do it silently.
    """
    res = _r177(run_tool, r177.noview / "events.jsonl", "stamp", "note",
                "no-view stamp", "--by", "hq",
                "--allow-unattributed", "--allow-no-ref")
    assert res.rc == 0, ("fixture: the no-view stamp failed rc=%s\n%s"
                         % (res.rc, res.combined[-900:]))
    assert not (r177.noview / "workers-ledger.json").exists(), (
        "[r177-stamp-jsonl-no-view-file] the stamp CREATED a compact view — the "
        "O(n) write #177 removed, resurrected silently")
    lines = (r177.noview / "events.jsonl").read_text().splitlines()
    assert len(lines) == 2, (
        "[r177-stamp-jsonl-appended] the record has %d lines, want 2 (seed + "
        "the new row)" % len(lines))
