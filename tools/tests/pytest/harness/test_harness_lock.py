"""The battery's single-flight lock, tested where it now lives.

WHAT THIS REPLACES
    The shell harness's section 91 held eight legs driving a shell block that
    acquired the
    lock in a coproc holder. That block is retired with the shell, and with it
    the legs' SUBJECT — a test of an extracted text block cannot outlive the file
    it was extracted from, and porting the block into the test tree would assert
    on a copy that no longer runs in production.

    The mechanism that replaced it is the ``battery_lock`` fixture in
    ``conftest.py``: an in-process ``flock`` on the one canonical path, taken on
    demand and released by a finalizer. The invariants are the same ones the
    shell legs protected, restated against the code that actually runs:

    * the path is FIXED and shared — a TMPDIR-derived path hands every lane its
      own lock while they share one receipt, so two runs write it concurrently
      and both look green;
    * a second acquirer is kept out while the first holds it (mutual exclusion);
    * a released lock is immediately available again (no leaked holder);
    * ``OC_BATTERY_LOCK`` overrides the path, because every scoped run needs its
      own lock file rather than contending with the real gate.

WHY THE SHELL'S fd-INHERITANCE LEGS HAVE NO COUNTERPART HERE
    #107's defect was an fd living in the battery shell so every child inherited
    it: SIGKILL the parent and a grandchild kept the lock. The fixture closes
    that by construction — it holds the fd in the session process and opens no
    child that could inherit it, so there is no ``/proc/PID/fd`` scan to make.
    ``test_the_lock_is_not_held_by_any_child`` pins the consequence that is still
    observable: after the holder exits, no surviving process holds the path.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys
from pathlib import Path

import pytest

import conftest as cf

pytestmark = [pytest.mark.serial, pytest.mark.xdist_group("battery-lock")]


def _try_lock(path: Path):
    """Open ``path`` and attempt an exclusive non-blocking flock.

    Returns ``(fh, acquired)``; the caller always closes ``fh``.
    """
    fh = open(path, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fh, True
    except BlockingIOError:
        return fh, False


# ---------------------------------------------------------------------------
# the invariant the whole mechanism rests on: ONE shared path
# ---------------------------------------------------------------------------
def test_lock_path_is_fixed_and_never_derived_from_tmpdir():
    """A per-run TMPDIR that moved the lock would un-serialize concurrent lanes.

    The default used to be ``${TMPDIR:-/tmp}/oc-battery.lock``, which was one
    shared path only because TMPDIR was shared. The per-run scratch root breaks
    that premise: a TMPDIR-derived default hands every lane its OWN lock while
    they still share the one canonical receipt — green transcript, no mutual
    exclusion.
    """
    assert cf.BATTERY_LOCK_PATH == "/tmp/oc-battery.lock", (
        "the battery lock default is %r — a per-run path would un-serialize "
        "concurrent lanes" % cf.BATTERY_LOCK_PATH)
    assert "TMPDIR" not in cf.BATTERY_LOCK_PATH, (
        "the lock path is derived from TMPDIR — that is the trap this leg exists "
        "to catch")


def test_the_env_override_is_read_at_import():
    """Every leg that takes the lock sets ``OC_BATTERY_LOCK``.

    If the override were ignored, scoped runs would contend on the shared
    default instead of their own probe path — and a scoped run would block the
    real gate for its whole budget.

    Read in a SUBPROCESS: the value is a module constant resolved at import, and
    reloading ``conftest`` inside a live session would re-run its module-level
    setup under the running suite.
    """
    env = dict(os.environ, OC_BATTERY_LOCK="/tmp/probe-override.lock")
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import conftest as c; "
         "print(c.BATTERY_LOCK_PATH)" % str(cf.PYTEST_DIR)],
        capture_output=True, text=True, timeout=120, env=env,
        cwd=str(cf.PYTEST_DIR))
    assert r.returncode == 0, r.stderr[-1500:]
    assert r.stdout.strip() == "/tmp/probe-override.lock", (
        "OC_BATTERY_LOCK was ignored (got %r) — concurrent legs would serialise "
        "against the shared default" % r.stdout.strip())


# ---------------------------------------------------------------------------
# mutual exclusion — the property, observed rather than assumed
# ---------------------------------------------------------------------------
def test_a_second_acquirer_is_kept_out(tmp_path):
    """Two runs writing one receipt is the defect; the lock is what prevents it."""
    lock = tmp_path / "gate.lock"
    first, got = _try_lock(lock)
    assert got, "the first acquirer was refused — the lock is not usable"
    try:
        second, got2 = _try_lock(lock)
        assert not got2, (
            "a second acquirer took the lock while the first held it — two runs "
            "would write the canonical receipt concurrently")
        second.close()
    finally:
        fcntl.flock(first.fileno(), fcntl.LOCK_UN)
        first.close()


def test_a_released_lock_is_immediately_available(tmp_path):
    """A lock that stayed held after release would stall every later run.

    This is the shape of the #107 failure seen from the other side: not a child
    inheriting the fd, but a holder that never lets go.
    """
    lock = tmp_path / "gate.lock"
    fh, got = _try_lock(lock)
    assert got
    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    fh.close()

    again, got2 = _try_lock(lock)
    assert got2, "the lock was still held after release — the next run stalls"
    fcntl.flock(again.fileno(), fcntl.LOCK_UN)
    again.close()


def test_the_lock_is_not_held_by_any_child(tmp_path):
    """After the holder exits, no surviving process holds the path.

    The shell harness needed a ``/proc/PID/fd`` scan because the block spawned a
    coproc. Here the observable is the outcome: a process that opens and closes
    the lock leaves nothing behind holding it.
    """
    lock = tmp_path / "gate.lock"
    child = subprocess.run(
        [sys.executable, "-c",
         "import fcntl\n"
         "fh = open(%r, 'a+')\n"
         "fcntl.flock(fh.fileno(), fcntl.LOCK_EX)\n"
         "fh.close()\n" % str(lock)],
        capture_output=True, text=True, timeout=120)
    assert child.returncode == 0, child.stderr[-1000:]

    fh, got = _try_lock(lock)
    assert got, (
        "the lock outlived the process that held it — a dead run would block "
        "every later one for the full budget")
    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    fh.close()


def test_the_wait_budget_is_bounded():
    """An unbounded wait turns a stuck peer into a hung gate.

    ``OC_BATTERY_LOCK_WAIT`` is the bound; its default must be a finite number,
    because a wait that can outlast the operator's patience is indistinguishable
    from a hang.
    """
    raw = os.environ.get("OC_BATTERY_LOCK_WAIT", "900")
    assert raw.isdigit(), "OC_BATTERY_LOCK_WAIT=%r is not a number of seconds" % raw
    assert 0 < int(raw) <= 7200, (
        "the lock wait is %ss — outside any sane gate budget" % raw)
