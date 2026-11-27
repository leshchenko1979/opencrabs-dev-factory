"""Ported: run.sh §33 — ``oc-ledger`` lock budget (#619), plus the two #95 and
#171 hazards that share its fixture.

WHAT §33 IS FOR
    Three defects, all measured, all inside the same 131 shell lines:

    * **#619** — the waiter's flock budget was a flat 30 s while the HOLDER's
      worst case was two bounded network pushes. A ship storm starved
      concurrent appends and DROPPED JOURNAL ROWS. The fix DERIVES the waiter
      budget from the holder worst case and DISCLOSES both in the refusal, so
      an operator can widen one without silently outrunning the other.
    * **#95** — git ran INSIDE the fleet ledger lock, so one saturated disk froze
      the ledger for every lane (measured 2026-11-19: the lock held 25 minutes
      while ``git status`` sat in D-state, 18 lanes queued behind it, every
      stamp dying rc 4). Git now runs AFTER the release, under its own
      ``$LEDGER.git-tail.lock``.
    * **#171** — the push tail (``_git_state_commit_now`` → ``push_backlog_if_due``
      → ``push_mirror``) resolves ``SKILL_DIR`` from ``OC_SKILL_DIR``, defaulting
      to the tree the tool lives in (``cd "$_OC_DIR/.."``). Measured 2026-11-24:
      a battery run whose clone had a local bare ``origin`` standing in for
      GitHub PUSHED a lane's unpublished commit onto it. A test run must never
      publish a lane's work.

WHY THESE ARE BEHAVIOURAL AND NOT GREPS
    ``oc-ledger --selftest`` already asserts the DERIVATION structurally
    (``lock-wait-derived-not-flat``, ``lock-die-names-worst-case``,
    ``lock-budget-not-push-shaped`` …), and those legs are built by
    CONCATENATION precisely because a literal grep self-matches the leg that
    contains it (measured 2026-09-26: ``OC_LEDGER_LOCK_WAIT`` counted 3 hits —
    two production lines plus the assertion itself). What a grep cannot do, and
    the selftest therefore cannot either, is HOLD the lock, vary the push bound
    and read the budget the tool itself reports. That is this module.

    This is also the answer to the README's deferral note for §33 ("a pytest
    port would need the same wall-clock budget to assert anything the selftest
    does not"). It would not, and does not: the shell spent its wall clock on
    ``sleep 4`` subshells because it had no way to hold a lock synchronously.
    A Python ``flock`` holds it with zero latency, so the same contention costs
    milliseconds here and these legs finish in seconds.

TIMING HONESTY
    Nothing here asserts how long anything took. Every leg asserts ORDERING or a
    TOOL-REPORTED VALUE:

    * the budget legs read the number out of the tool's own refusal text;
    * the #95 leg POLLS ``$LEDGER.git-tail.lock`` until the holder is verifiably
      inside the tail, then asserts the ledger lock is FREE at that instant —
      the ordering claim, which neither a fast nor a saturated box can fake;
    * the #171 legs read two git refs.

    The only sleeps are (a) the 3 s ``pre-commit`` hook, which is the
    INSTRUMENT (it makes the tail observably slow) and (b) a 20 ms poll
    interval. Neither is a measurement.

SERIALISATION
    These legs hold flocks, fork a concurrent holder and stamp the same ledger
    twice. They use per-test paths under ``scratch``, but they are marked
    ``serial`` + ``xdist_group("battery-ledger-lock")`` anyway: a fork-and-poll
    against a shared box is exactly what must not race a sibling lane, and the
    shell harness runs §33 in the serial lane for the same reason.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

import conftest as cf

pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-ledger-lock"),
]

TOOL = cf.tool_path("oc-ledger")
EMPTY_LEDGER = '{"workers":[],"events":[]}'
# The fixture actor: `stamp` REFUSES an anonymous row (#19), so a leg without
# one asserts rc 2 and reports green for it.
ACTOR = cf.LEDGER_ACTOR


# =============================================================================
# helpers — local to this module; conftest is not touched
# =============================================================================
def _ledger(state) -> Path:
    """Write the empty-events ledger the shell's §33 fixture uses."""
    led = Path(state) / "l.json"
    led.write_text(EMPTY_LEDGER, encoding="utf-8")
    return led


def _base_env(ledger: Path, skill_dir) -> dict:
    """The shell's env shape for a §33 invocation, minus the per-leg knobs.

    ``OC_SHIP_AUDIT_CHAIN=0`` mirrors ``ledger_sandbox`` (oc-ledger:6198) — the
    ship audit chain is not the subject here and would add work to every stamp.
    """
    env = {
        "OC_LEDGER": str(ledger),
        "OC_ACTOR": ACTOR,
        "OC_TOOLS_NOLOG": "1",
        "OC_SHIP_AUDIT_CHAIN": "0",
    }
    if skill_dir is not None:
        env["OC_SKILL_DIR"] = str(skill_dir)
    return env


@contextmanager
def _hold_ledger_lock(ledger: Path):
    """Hold ``$LEDGER.lock`` exclusively, the way a slow holder does.

    A Python ``flock`` rather than the shell's ``( flock -x 9; sleep 4 ) &``
    plus ``sleep 0.5``: the lock is held BEFORE the tool is launched, so there
    is no window in which the waiter could win a race and the leg could pass
    for the wrong reason. Released on the way out even if the body raises.
    """
    fh = open(str(ledger) + ".lock", "a+")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        yield
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


def _lock_is_free(path: Path) -> bool:
    """True when NOBODY holds an exclusive flock on ``path`` right now.

    Non-blocking probe: if we can take it, nobody else has it. The file is
    opened ``a+`` because the tool creates its lock files lazily and a missing
    file is trivially free.
    """
    fh = open(str(path), "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return True
    finally:
        fh.close()


def _rev(repo, ref: str = "refs/heads/main") -> str:
    """``rev-parse`` a ref that may not exist yet (an empty bare repo) -> ''."""
    return cf._git(repo, "rev-parse", ref, check=False).stdout.strip()


# =============================================================================
# #619 — the waiter budget: control, tunability, disclosure, derivation
# =============================================================================
def test_control_a_free_lock_lets_the_stamp_through(ledger_sandbox, run_tool):
    """CONTROL (shell leg (c)): the same invocation that times out below SUCCEEDS.

    Without this, every other leg in this module would pass on a tool that is
    simply broken — a stamp that never acquires the lock also never reports a
    budget, and a stamp that dies on startup never reaches the refusal text.
    """
    res = run_tool([str(TOOL), "stamp", "note", "c", "--by", "hq probe"],
                   timeout=120,
                   env={"OC_LEDGER_LOCK_WAIT": "1"})
    assert res.rc == 0, (
        "control: a stamp with the lock FREE must succeed, got rc=%s\n%s"
        % (res.rc, res.combined[-800:]))

    ledger = json.loads(ledger_sandbox.ledger.read_text())
    assert [e.get("what") for e in ledger.get("events") or []] == ["c"], (
        "control: the stamp reported rc 0 but wrote no row — a green verdict "
        "over an empty ledger is the from-zero defect")


def test_a_1s_waiter_budget_times_out_with_rc_4_and_names_the_budget(
        scratch, run_tool):
    """Shell leg (a): a HELD lock + ``OC_LEDGER_LOCK_WAIT=1`` -> rc 4, and the
    refusal must name the budget it actually used.

    Both halves are load-bearing. rc 4 alone says "it gave up"; ``after 1s`` is
    what tells an operator the tunable was HONOURED rather than ignored, which
    is the whole of #619's complaint (a waiter asleep for a number it never
    chose). rc 4 under the default budget would mean the knob did nothing.
    """
    led = _ledger(scratch.path)
    with _hold_ledger_lock(led):
        res = run_tool(
            [str(TOOL), "--ledger", str(led), "stamp", "note", "a",
             "--by", "hq probe"],
            timeout=120,
            env=_base_env(led, None) | {
                "OC_LEDGER_LOCK_WAIT": "1",
                "OC_LEDGER_PUSH_TIMEOUT": "1",
            })

    assert res.rc == 4, (
        "want rc 4 (lock timeout), got rc=%s\n%s"
        % (res.rc, res.combined[-800:]))
    assert "after 1s" in res.combined, (
        "the refusal does not name the budget it used — an operator cannot "
        "tell a 1 s tunable from a 90 s default:\n%s" % res.combined[-800:])


@pytest.mark.parametrize("push_bound, worst_case", [
    (1, 31),     # the shell's own pair: 1 s bounded I/O + 30 s
    (10, 40),    # shell leg (b): the reported number must MOVE with the bound
    (7, 37),     # not in the shell: makes this a DERIVATION, not two constants
])
def test_the_disclosed_worst_case_tracks_the_push_bound(
        scratch, run_tool, push_bound, worst_case):
    """Shell legs (a)+(b): the disclosed worst case is ``push_bound + 30``.

    #619's invariant, which the shell states as two literals (31 s and 40 s).
    Two literals are satisfied by a table of constants; the third parameter,
    chosen to be neither, is what makes this a derivation. The refusal prints
    its own arithmetic — ``one bounded I/O Ns + 30s`` — so this reads the
    tool's answer rather than recomputing it here.

    This is the invariant the defect broke: before the fix an operator could
    widen the holder (``OC_LEDGER_PUSH_TIMEOUT``) without touching the waiter,
    driving the two arbitrarily far apart and starving every concurrent append.
    """
    led = _ledger(scratch.path)
    with _hold_ledger_lock(led):
        res = run_tool(
            [str(TOOL), "--ledger", str(led), "stamp", "note", "b",
             "--by", "hq probe"],
            timeout=120,
            env=_base_env(led, None) | {
                "OC_LEDGER_LOCK_WAIT": "1",
                "OC_LEDGER_PUSH_TIMEOUT": str(push_bound),
            })

    assert res.rc == 4, (
        "push_bound=%ss: want rc 4, got rc=%s\n%s"
        % (push_bound, res.rc, res.combined[-800:]))
    assert "worst case %ds" % worst_case in res.combined, (
        "push_bound=%ss must disclose a worst case of %ds (one bounded I/O "
        "%ss + 30s). The budget did not track the I/O bound — which is exactly "
        "the #619 defect (widen the holder and the waiter stays put):\n%s"
        % (push_bound, worst_case, push_bound, res.combined[-800:]))
    # And it must name the bound it derived FROM, or the arithmetic is
    # unfalsifiable for a reader who was not here when it was chosen.
    assert "bounded I/O %ss" % push_bound in res.combined, (
        "push_bound=%ss: the refusal does not name the bound it derived "
        "from:\n%s" % (push_bound, res.combined[-800:]))


# =============================================================================
# #95 — git must not run under the ledger lock
# =============================================================================
def test_a_slow_git_tail_does_not_hold_the_ledger_lock(scratch, git_repo,
                                                       run_tool):
    """The discriminating #95 leg: a 3 s git tail must not delay an appender.

    THE SHELL'S SHAPE. A ``sleep 3`` ``pre-commit`` hook makes
    ``_git_state_commit_now`` slow. A holder stamps (so its tail sits inside the
    hook); a second stamp then runs with a **1 s** ledger-lock budget. If git
    still ran under the fleet flock the second stamp would die rc 4 — the
    measured 2026-11-19 stall. rc 0 proves the lock was released before the tail.

    WHAT THE PORT ADDS. The shell waits ``sleep 1`` and HOPES the holder is in
    the tail by then. This POLLS ``$LEDGER.git-tail.lock`` until the holder
    verifiably holds it, then asserts the ledger lock is FREE **at that
    instant** — the ordering claim itself rather than a duration, so neither a
    fast nor a loaded box can fake it. If the tail lock is never observed the
    leg FAILS rather than passing vacuously (a leg that only asserted "rc 0"
    would also pass if the hook never ran at all).

    Durability is read the same way, and more sharply than the shell's: the
    holder's row must be IN the ledger while its commit is still sleeping in the
    hook. Durability is the append, not the commit.
    """
    # No origin on the state repo, and a SKILL_DIR that is not a git repo, so
    # both push arms are silent no-ops: the subject here is the LOCK, and a push
    # would add network time to every leg for no assertion.
    state = git_repo(files={"l.json": EMPTY_LEDGER})
    hook = state / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nsleep 3\n", encoding="utf-8")
    hook.chmod(0o755)
    led = state / "l.json"

    env = _base_env(led, scratch.path / "not-a-git-repo") | {
        "OC_LEDGER_GIT_TAIL_WAIT": "20",
        "OC_LEDGER_PUSH_MIN": "1",
        "OC_LEDGER_PUSH_TIMEOUT": "1",
    }

    holder = None
    try:
        # Launched with Popen rather than through run_tool: this is a CONCURRENT
        # holder whose whole purpose is to still be running when the second
        # stamp is launched, and run_tool is synchronous by design. This is the
        # same shape test_harness_lock.py uses for its lock probes; the bound
        # run_tool would have given is reproduced in `communicate` below.
        holder = subprocess.Popen(
            [str(TOOL), "--ledger", str(led), "stamp", "note",
             "slow-tail holder", "--by", "hq probe"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            env=dict(os.environ) | env, start_new_session=True)

        tail_lock = Path(str(led) + ".git-tail.lock")
        deadline = time.monotonic() + 30
        tail_held = False
        while time.monotonic() < deadline:
            if holder.poll() is not None:
                break
            if not _lock_is_free(tail_lock):
                tail_held = True
                break
            time.sleep(0.02)

        if not tail_held:
            out = holder.stdout.read() if holder.poll() is not None else ""
            pytest.fail(
                "the holder never entered its git tail — the tail lock was not "
                "observed within 30 s (holder rc=%r). Without that observation "
                "the #95 assertions below would be vacuous:\n%s"
                % (holder.poll(), out))

        # THE ORDERING CLAIM: the tail is running AND the fleet lock is FREE.
        assert _lock_is_free(Path(str(led) + ".lock")), (
            "#95 REGRESSED: the git tail holds the LEDGER lock. One saturated "
            "disk then freezes the ledger for every lane (measured 2026-11-19: "
            "25 min held, 18 lanes queued, every stamp rc 4)")

        # Durability, observed while the commit is still inside the hook.
        events = json.loads(led.read_text()).get("events") or []
        assert [e.get("what") for e in events].count("slow-tail holder") == 1, (
            "the holder's row is NOT durable while its git tail is still "
            "pending — durability is the append, not the commit: %r"
            % ([e.get("what") for e in events],))

        # THE DISCRIMINATOR: a 1 s waiter budget, while the tail is still ~3 s
        # from finishing. rc 4 here is the #95 defect; rc 0 is the fix.
        res = run_tool(
            [str(TOOL), "--ledger", str(led), "stamp", "note",
             "concurrent appender", "--by", "hq probe"],
            timeout=180,
            env=env | {"OC_LEDGER_LOCK_WAIT": "1"})
        assert res.rc == 0, (
            "#95 REGRESSED: a 3 s git tail BLOCKED a concurrent appender "
            "(rc=%s under a 1 s ledger-lock budget). The fleet lock was still "
            "held by the tail:\n%s" % (res.rc, res.combined[-800:]))
        assert "lock timeout" not in res.combined, (
            "the appender saw a lock timeout even though rc=0:\n%s"
            % res.combined[-800:])
    finally:
        if holder is not None:
            try:
                holder.communicate(timeout=60)
            except subprocess.TimeoutExpired:      # pragma: no cover
                holder.kill()
                holder.communicate()

    # Both rows survive the tail, and both are numbered — the shell's final
    # durability assertion, read from the ledger rather than from stdout.
    events = json.loads(led.read_text()).get("events") or []
    whats = [e.get("what") for e in events]
    assert whats.count("slow-tail holder") == 1, (
        "the slow-tail holder's row is MISSING after the run: %r" % (whats,))
    assert whats.count("concurrent appender") == 1, (
        "the concurrent appender's row is MISSING after the run: %r" % (whats,))
    assert sorted(e.get("n") for e in events) == [1, 2], (
        "two appends must number n=1,2 — a duplicate or a gap means the second "
        "appender numbered from a stale read: %r"
        % ([e.get("n") for e in events],))


# =============================================================================
# #171 — the hermetic skill-dir seam
# =============================================================================
@pytest.fixture
def copied_tool_tree(scratch, git_repo):
    """A COPY of ``tools/lib`` + ``tools/state/oc-ledger``, in its own repo.

    The #171 hazard is that ``SKILL_DIR`` DEFAULTS to the tree the tool runs in
    (``cd "$_OC_DIR/.."``). Asserting that against the REAL tree would mean
    asserting that a shared multi-lane repo's refs did not move during this
    test — a property of every OTHER lane on the box, not of this tool, and one
    that flips the moment a sibling lane pushes (which is why the shell's md5
    legs are wrapped in ``timeout 10`` and print their rc pair).

    So the tree is copied and its own ``origin`` is a POISON bare repo under
    scratch. That is strictly stronger than the shell's md5: the poison origin
    is read directly, and the negative control below proves a push WOULD land
    there if the seam were dropped.
    """
    repo = git_repo()
    shutil.copytree(cf.TOOLS_DIR / "lib", repo / "tools" / "lib")
    (repo / "tools" / "state").mkdir(parents=True, exist_ok=True)
    shutil.copy2(TOOL, repo / "tools" / "state" / TOOL.name)
    (repo / "tools" / "state" / TOOL.name).chmod(0o755)
    # tools/ must stay TRACKED: an entirely untracked directory collapses to
    # ``?? tools/`` in porcelain (the trap ``ledger_sandbox`` documents).
    (repo / "tools" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "tools" / "tests" / ".keep").write_text("", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "tree with tool")
    return repo


def test_a_test_run_cannot_publish_into_the_tree_it_runs_from(
        scratch, git_repo, copied_tool_tree, run_tool):
    """#171 positive leg: with the seam set, the push lands in the SENTINEL.

    The push tail must be EXERCISED, not skipped — the shell says so explicitly,
    and it is the half a "nothing moved" assertion cannot prove on its own. So
    this requires the sentinel origin's ref to MOVE (the tail really ran) AND
    the poison origin standing in for the real remote to be untouched.
    """
    origin = git_repo(bare=True)
    skill = git_repo()
    skill.git("remote", "add", "origin", str(origin))
    skill.git("push", "-q", "-u", "origin", "HEAD")
    # One unpushed commit: the backlog arm needs something to push, or the tail
    # returns before push_mirror and the leg proves nothing.
    (skill / "probe.txt").write_text("probe\n", encoding="utf-8")
    skill.git("add", "probe.txt")
    skill.git("commit", "-q", "-m", "sentinel probe")

    poison = git_repo(bare=True)
    copied_tool_tree.git("remote", "add", "origin", str(poison))
    copied_tool_tree.git("push", "-q", "-u", "origin", "HEAD")

    state = git_repo(files={"l.json": EMPTY_LEDGER})
    led = state / "l.json"
    sentinel_before = _rev(origin)
    poison_before = _rev(poison)

    res = run_tool(
        [str(copied_tool_tree / "tools" / "state" / TOOL.name),
         "stamp", "note", "push-hazard probe", "--by", "hq probe"],
        timeout=180,
        env=_base_env(led, skill) | {"OC_LEDGER_PUSH_MIN": "1",
                                     "OC_LEDGER_PUSH_TIMEOUT": "10"})
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-800:])

    sentinel_after = _rev(origin)
    assert sentinel_after == _rev(skill, "HEAD"), (
        "the sentinel origin does not carry the skill's HEAD — the push tail "
        "was SKIPPED, so this leg proves nothing:\n%s" % res.combined[-800:])
    assert sentinel_after != sentinel_before, (
        "#171: the sentinel origin's ref did not MOVE, so the assertion above "
        "is vacuous (the tail never ran):\n%s" % res.combined[-800:])

    assert _rev(poison) == poison_before, (
        "#171 REGRESSED: a test stamp PUSHED into the tree the tool runs from. "
        "On a real lane that tree's origin is GitHub and the run publishes "
        "unpublished work (measured 2026-11-24):\n%s" % res.combined[-800:])
    assert "mirror: skill pushed" in res.combined, (
        "the tail's own disclosure is missing — a leg that reads only refs "
        "would not notice the tail going silent:\n%s" % res.combined[-800:])


def test_the_poison_origin_moves_when_the_seam_is_removed(
        scratch, git_repo, copied_tool_tree, run_tool):
    """#171 NEGATIVE CONTROL: drop ``OC_SKILL_DIR`` and the tree's origin MOVES.

    Without this, the positive leg above passes on any instrument that never
    pushes at all — including a broken seam. Here the seam is removed
    (``OC_SKILL_DIR=""``; the tool spells it ``${OC_SKILL_DIR:-…}``, so empty is
    unset) and the SAME invocation must publish into the poison origin. That is
    the defect reproduced on purpose, in a place where it can only ever land on
    scratch.
    """
    poison = git_repo(bare=True)
    copied_tool_tree.git("remote", "add", "origin", str(poison))
    copied_tool_tree.git("push", "-q", "-u", "origin", "HEAD")
    # An unpushed commit on the tree: this is the "lane's work" the shell
    # measured being published by a battery run.
    (copied_tool_tree / "unpushed.txt").write_text("x\n", encoding="utf-8")
    copied_tool_tree.git("add", "-A")
    copied_tool_tree.git("commit", "-q", "-m", "one unpushed lane commit")

    state = git_repo(files={"l.json": EMPTY_LEDGER})
    led = state / "l.json"
    before = _rev(poison)

    res = run_tool(
        [str(copied_tool_tree / "tools" / "state" / TOOL.name),
         "stamp", "note", "default skill dir probe", "--by", "hq probe"],
        timeout=180,
        env=_base_env(led, "") | {"OC_LEDGER_PUSH_MIN": "1",
                                  "OC_LEDGER_PUSH_TIMEOUT": "10"})
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-800:])

    after = _rev(poison)
    assert after != before, (
        "the negative control did NOT reproduce #171: with OC_SKILL_DIR unset "
        "the tool falls back to its own tree, whose origin is the poison repo, "
        "so the push should have landed there. If this fails, the positive leg "
        "proves nothing (nothing in this fixture pushes at all):\n%s"
        % res.combined[-800:])
    assert after == _rev(copied_tool_tree, "HEAD"), (
        "the poison origin moved but not onto the tree's HEAD — read the refs "
        "before trusting the positive leg")


def test_the_sandbox_ledger_is_push_inert(ledger_sandbox, run_tool):
    """THE PYTEST-SIDE ANSWER to the shell's two real-origin md5 legs.

    The shell reads the REAL origin twice (remote-tracking refs, and
    ``ls-remote``) because its ``$SKILL_DIR`` default is the checkout it runs
    in. The pytest suite has no such exposure to assert, and asserting one
    would be asserting a property of every other lane on the box. Instead this
    pins the reason the exposure cannot arise: ``ledger_sandbox`` points
    ``OC_SKILL_DIR`` at a scratch skill dir with NO ``origin``, so
    ``push_backlog_if_due`` returns before ``push_mirror`` ever runs.

    That is a load-bearing fixture property, not decoration: if the sandbox
    ever gained an origin, every ported oc-ledger leg in the suite would start
    pushing to it.
    """
    skill = Path(ledger_sandbox.skill)
    remotes = cf._git(skill, "remote").stdout.split()
    assert remotes == [], (
        "ledger_sandbox's skill dir carries a remote %r — a push tail in ANY "
        "ported oc-ledger leg can now leave this box" % (remotes,))

    res = run_tool([str(TOOL), "stamp", "note", "inert", "--by", "hq probe"],
                   timeout=120)
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-800:])
    assert "mirror-due" not in res.combined and "mirror: " not in res.combined, (
        "the sandbox ledger reached the push arms — it must be inert:\n%s"
        % res.combined[-800:])
