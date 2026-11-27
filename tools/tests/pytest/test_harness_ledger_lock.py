"""The ledger's LOCK BUDGET and its push hazard (#619, #95, #171).

WHAT THIS PORTS
    ``run.sh`` section ``oc-ledger lock budget (#619)`` — the block that holds
    ``$LEDGER.lock``, varies ``OC_LEDGER_PUSH_TIMEOUT``, and reads the budget the
    tool REPORTS. Also its #95 leg (a slow git tail must not delay a second
    appender) and its #171 guard (the battery's push path must never reach the
    real remote).

WHY THIS IS BEHAVIOURAL AND NOT A GREP
    ``run.sh`` says it in as many words: "a grep for OC_LEDGER_LOCK_WAIT
    self-matches the leg that contains it". The budget is therefore read from
    what ``oc-ledger`` PRINTS on refusal, and the derivation is proven by MOVING
    the input it derives from — ``OC_LEDGER_PUSH_TIMEOUT`` — and requiring the
    reported worst case to move with it. A grep would pass on a tool that hard-
    coded the number and a behavioural leg cannot.

THE THREE THINGS THAT CAN GO WRONG, AND THE LEG FOR EACH
    (1) the waiter budget does not exceed the holder's worst case, so a normal
        storm starves concurrent appends and DROPS JOURNAL ROWS SILENTLY;
    (2) the budget is a constant, so an operator can widen the holder without
        touching the waiter and drive the two arbitrarily far apart;
    (3) THE PUSH PATH ESCAPES THE TEST — ``_git_state_commit_now``'s tail calls
        ``push_backlog_if_due "$SKILL_DIR"``, and ``SKILL_DIR`` defaults to the
        tree the battery runs in. Measured 2026-11-24: a test run PUSHED a
        lane's unpublished work onto its real remote. Every stamp below is
        therefore handed ``OC_SKILL_DIR`` pointing at a SENTINEL repo whose
        origin is a bare repo under ``tmp_path``, so the push tail stays
        EXERCISED (asserted, never skipped) and can only land there.

WHAT IS DELIBERATELY NOT ASSERTED
    How LONG the tool waited. ``flock -w`` is a wall-clock bound and this box
    runs peer lanes at load 10; the discriminating fact is the rc and the
    numbers the tool prints, both of which are independent of how loaded the
    host was when they were produced.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

import conftest as cf
from lib import harness as H

pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-lock"),
]

# A ledger with no workers and no events: valid to the tool, empty enough that a
# stamp's own row is the only thing in it.
EMPTY_LEDGER = '{"workers":[],"events":[]}'

def _git(*args, cwd=None, check=True):
    # Through H.run: git forks unpack-objects/pack-objects, and a refused fork
    # surfaces as rc 1/128 with "cannot fork()" on stderr. The FORK is retried;
    # a git that ran and failed is returned untouched (see H.run's contract).
    return H.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=check)

@pytest.fixture
def sentinel_skill(tmp_path):
    """A SKILL repo whose origin is a BARE repo under tmp_path.

    The #171 seam: ``OC_SKILL_DIR`` already exists in production
    (``oc-ledger:194``), so nothing new is switched on — the push tail runs
    exactly as it would in the field, and can only ever move THIS origin.
    """
    origin = tmp_path / "origin.git"
    skill = tmp_path / "skill"
    H.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    _git("symbolic-ref", "HEAD", "refs/heads/main", cwd=origin)
    H.run(["git", "init", "-q", str(skill)], check=True)
    # git init's default here is `master`; the assertions below read `main`, and
    # a push to a branch that does not exist would read as "nothing moved".
    _git("symbolic-ref", "HEAD", "refs/heads/main", cwd=skill)
    _git("config", "user.email", "sa@sb", cwd=skill)
    _git("config", "user.name", "sa", cwd=skill)
    _git("config", "commit.gpgsign", "false", cwd=skill)
    (skill / "f").write_text("sentinel\n", encoding="utf-8")
    _git("add", "f", cwd=skill)
    _git("commit", "-q", "-m", "sentinel base", cwd=skill)
    _git("remote", "add", "origin", str(origin), cwd=skill)
    _git("push", "-q", "-u", "origin", "HEAD", cwd=skill)
    return skill, origin

@pytest.fixture
def ledger_dir(tmp_path):
    d = tmp_path / "lb"
    d.mkdir()
    (d / "l.json").write_text(EMPTY_LEDGER, encoding="utf-8")
    return d

def _stamp(ledger_dir: Path, note: str, *, env_extra: dict,
           timeout: float = 120.0) -> tuple[int, str]:
    """Run a stamp and return ``(rc, combined output)``."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("OC_LEDGER_")}
    env.update({"OC_TOOLS_NOLOG": "1"})
    env.update({k: str(v) for k, v in env_extra.items()})
    r = H.run(
        [cf.tool_path("oc-ledger"), "--ledger", str(ledger_dir / "l.json"),
         "stamp", "note", note, "--by", "pytest probe"],
        capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout + r.stderr

def _hold_lock_for(ledger_dir: Path, seconds: float) -> subprocess.Popen:
    """Hold ``<ledger>.lock`` in a child for ``seconds``.

    A separate process on purpose: ``flock`` is per open file description, so a
    holder in THIS process would conflict with the tool only by accident of fd
    churn, making the contention a race instead of a fact.

    The child opens the lock ITSELF (``exec 9>>"$1"``) rather than inheriting an
    fd: inheritance is what #641 was about, and a shell redirection ordering
    mistake would silently hand it a different inode than the one the tool
    flocks — the leg would then read "lock free" and the timeout leg would fail
    for the wrong reason.
    """
    lock = ledger_dir / "l.json.lock"
    lock.touch()
    p = H.spawn(
        ["bash", "-c", 'exec 9>>"$1"; flock -x 9; sleep "$2"', "_",
         str(lock), str(seconds)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait until the child really holds it, rather than guessing with a sleep:
    # a probe that cannot acquire proves the holder is in place.
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        r = H.run(["flock", "-n", str(lock), "true"], capture_output=True)
        if r.returncode != 0:
            return p
        time.sleep(0.05)
    p.kill()
    raise AssertionError("the lock holder never acquired %s" % lock)

# =============================================================================
# (c) CONTROL — with the lock free the same invocation must SUCCEED
# =============================================================================
def test_a_stamp_succeeds_when_the_lock_is_free(ledger_dir, sentinel_skill):
    """CONTROL for every refusal leg below.

    Without it, "rc 4 while the lock is held" is satisfied by a tool that is
    simply broken and returns 4 for every invocation.
    """
    skill, _ = sentinel_skill
    rc, out = _stamp(ledger_dir, "control", env_extra={"OC_SKILL_DIR": skill})
    assert rc == 0, (
        "a stamp with the lock free failed (rc %d) — every contention leg "
        "below would then be measuring a broken tool:\n%s" % (rc, out))

# =============================================================================
# (a) the waiter budget is TUNABLE — the fix's load-bearing capability
# =============================================================================
def test_a_one_second_budget_times_out_with_rc_4(ledger_dir, sentinel_skill):
    """``OC_LEDGER_LOCK_WAIT=1`` against a held lock must give rc 4.

    rc 4 is the tool's own "lock timeout" code, distinct from a usage error (2)
    and from success (0), so a leg that only checked "not 0" would also pass on
    a typo in the invocation.
    """
    skill, _ = sentinel_skill
    holder = _hold_lock_for(ledger_dir, 6)
    try:
        time.sleep(0.5)
        rc, out = _stamp(ledger_dir, "a", env_extra={
            "OC_SKILL_DIR": skill,
            "OC_LEDGER_LOCK_WAIT": 1,
            "OC_LEDGER_PUSH_TIMEOUT": 1,
        })
    finally:
        holder.kill()
        holder.wait(timeout=10)
    assert rc == 4, "want rc 4 (lock timeout), got %d:\n%s" % (rc, out)

def test_the_refusal_names_the_budget_it_used(ledger_dir, sentinel_skill):
    """The message must disclose the budget, not just fail.

    An operator paged at 03:00 cannot raise a bound the tool never names.
    """
    skill, _ = sentinel_skill
    holder = _hold_lock_for(ledger_dir, 6)
    try:
        time.sleep(0.5)
        rc, out = _stamp(ledger_dir, "b", env_extra={
            "OC_SKILL_DIR": skill,
            "OC_LEDGER_LOCK_WAIT": 1,
            "OC_LEDGER_PUSH_TIMEOUT": 1,
        })
    finally:
        holder.kill()
        holder.wait(timeout=10)
    assert rc == 4, "precondition: want rc 4, got %d:\n%s" % (rc, out)
    assert "after 1s" in out, (
        "the refusal does not name the budget it used (want 'after 1s'):\n%s"
        % out)

def test_the_disclosed_worst_case_is_one_bounded_io_plus_thirty(ledger_dir, sentinel_skill):
    """``worst case`` must be ``OC_LEDGER_PUSH_TIMEOUT + 30``, disclosed.

    #95 moved git OUT of the lock, so the holder is no longer bounded by two
    network pushes; the budget was re-derived DOWN to one bounded I/O plus 30 s
    of slack. The exact number matters: keeping the inflated pre-#95 form would
    leave every waiter asleep ~90 s for work that takes half a second.
    """
    skill, _ = sentinel_skill
    holder = _hold_lock_for(ledger_dir, 6)
    try:
        time.sleep(0.5)
        rc, out = _stamp(ledger_dir, "c", env_extra={
            "OC_SKILL_DIR": skill,
            "OC_LEDGER_LOCK_WAIT": 1,
            "OC_LEDGER_PUSH_TIMEOUT": 1,
        })
    finally:
        holder.kill()
        holder.wait(timeout=10)
    assert rc == 4, "precondition: want rc 4, got %d:\n%s" % (rc, out)
    assert "worst case 31s" in out, (
        "want 'worst case 31s' (1s bounded I/O + 30s), got:\n%s" % out)

# =============================================================================
# (b) DERIVATION — raise the I/O bound and the reported worst case must move
# =============================================================================
def test_the_budget_tracks_the_io_bound(ledger_dir, sentinel_skill):
    """``OC_LEDGER_PUSH_TIMEOUT=10`` must yield ``worst case 40s``.

    This is the invariant the defect broke: an operator could widen the holder
    without touching the waiter, driving the two arbitrarily far apart, and the
    waiter would then time out on a HEALTHY holder. A hardcoded 31 passes the
    leg above and fails this one — which is why both exist.
    """
    skill, _ = sentinel_skill
    holder = _hold_lock_for(ledger_dir, 8)
    try:
        time.sleep(0.5)
        rc, out = _stamp(ledger_dir, "d", env_extra={
            "OC_SKILL_DIR": skill,
            "OC_LEDGER_LOCK_WAIT": 1,
            "OC_LEDGER_PUSH_TIMEOUT": 10,
        })
    finally:
        holder.kill()
        holder.wait(timeout=10)
    assert rc == 4, "precondition: want rc 4, got %d:\n%s" % (rc, out)
    assert "worst case 40s" in out, (
        "the budget did NOT track the bounded I/O (want 10s -> 40s); it is "
        "hardcoded rather than derived:\n%s" % out)

# =============================================================================
# #95 — git must not run under the ledger lock
# =============================================================================
def test_a_slow_git_tail_does_not_block_a_concurrent_appender(tmp_path, sentinel_skill):
    """A 3 s git tail must not delay a second appender holding a 1 s budget.

    THE DISCRIMINATING LEG. A 3 s pre-commit hook makes ``_git_state_commit_now``
    slow. If git still ran inside the fleet flock, stamp #2 would die rc 4
    ("lock timeout after 1s"). rc 0 proves the lock was released BEFORE the
    tail. The control is ``test_a_stamp_succeeds_when_the_lock_is_free``.
    """
    skill, _ = sentinel_skill
    state = tmp_path / "gb"
    state.mkdir()
    H.run(["git", "init", "-q", str(state)], check=True)
    (state / "l.json").write_text(EMPTY_LEDGER, encoding="utf-8")
    hook = state / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nsleep 3\n", encoding="utf-8")
    hook.chmod(0o755)
    _git("add", "l.json", cwd=state)
    _git("-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init", cwd=state)

    env_common = {"OC_SKILL_DIR": skill, "OC_TOOLS_NOLOG": "1"}
    holder = H.spawn(
        [cf.tool_path("oc-ledger"), "--ledger", str(state / "l.json"),
         "stamp", "note", "slow-tail holder", "--by", "pytest probe"],
        env={**os.environ, **env_common, "OC_LEDGER_GIT_TAIL_WAIT": "20"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        rc, out = _stamp(state, "concurrent appender", env_extra={
            **env_common, "OC_LEDGER_LOCK_WAIT": 1})
    finally:
        holder.wait(timeout=120)

    assert rc == 0, (
        "a concurrent appender was BLOCKED by the git tail (rc %d) — git is "
        "running under the fleet lock again:\n%s" % (rc, out))

    # Durability is the APPEND, not the commit: the holder's row must have
    # landed despite its slow tail. The field is `what` (stamp note writes
    # {n,t,by,kind,what}), null-guarded, because a bare test() on a missing key
    # dies and would make this leg pass on an EMPTY ledger.
    data = json.loads((state / "l.json").read_text(encoding="utf-8"))
    landed = [e for e in data.get("events", [])
              if "slow-tail holder" in (e.get("what") or "")]
    assert landed, "the slow-tail holder's row is MISSING from the ledger"

# =============================================================================
# #171 — the push tail must never reach the real remote
# =============================================================================
def test_a_test_repo_push_lands_in_the_sentinel_origin(tmp_path, sentinel_skill):
    """The push tail is EXERCISED, and it can only land in the sentinel.

    A leg that merely asserted "nothing reached the real origin" would also pass
    if the push tail were never reached at all — an absence proving an absence.
    This forces one push through the same invocation shape the legs above use
    and reads BOTH ends: the sentinel origin's ref must MOVE.
    """
    skill, origin = sentinel_skill
    before = _git("rev-parse", "refs/heads/main", cwd=origin).stdout.strip()

    # A new commit in the SKILL repo, so there is something to push.
    (skill / "g").write_text("probe\n", encoding="utf-8")
    _git("add", "g", cwd=skill)
    _git("commit", "-q", "-m", "sentinel probe", cwd=skill)

    state = tmp_path / "sk-state"
    state.mkdir()
    H.run(["git", "init", "-q", str(state)], check=True)
    (state / "l.json").write_text(EMPTY_LEDGER, encoding="utf-8")
    _git("add", "l.json", cwd=state)
    _git("-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "base", cwd=state)

    rc, out = _stamp(state, "push-hazard probe", env_extra={
        "OC_SKILL_DIR": skill,
        "OC_LEDGER": str(state / "l.json"),
        "OC_LEDGER_PUSH_MIN": 1,
    })
    assert rc == 0, "the push-hazard probe failed (rc %d):\n%s" % (rc, out)

    after = _git("rev-parse", "refs/heads/main", cwd=origin).stdout.strip()
    head = _git("rev-parse", "HEAD", cwd=skill).stdout.strip()
    assert after == head, (
        "the sentinel origin did not receive the skill repo's head — the push "
        "tail was SKIPPED, so 'nothing reached the real remote' proves nothing\n"
        "origin main: %s\nskill HEAD:  %s" % (after, head))
    # CONTROL: the ref really moved, so the assertion above is not comparing two
    # copies of an unmoved value.
    assert after != before, (
        "the sentinel origin's ref did not MOVE — the leg above is vacuous")
