"""Foundation smoke tests — the three properties the other workers depend on.

These are not "does the framework import" tests. Each one asserts a defect the
shell harness already paid for, so a regression here fails BEFORE a ported
section inherits it:

* ``test_scratch_*``    TMPDIR / OC_SNAP_ROOT / the lock path (plan §3.4, §3.5)
* ``test_env_guard_*``  the live-state leaks (plan §3.8)
* ``test_run_tool_*``   the process-GROUP kill (plan §3.1, #753)

Run them alone with ``-k foundation``; they touch no tool and no network.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import conftest as cf


# =============================================================================
# 1. scratch
# =============================================================================
def test_scratch_isolates_tmpdir_and_snap_root(scratch):
    """TMPDIR, OC_BATTERY_TEST_TMPDIR and OC_SNAP_ROOT all land in one root.

    This is what makes every bare ``mktemp`` in a ported section and every
    ``oc_snap_guard`` mirror land inside the tree the controller owns — the two
    populations that leaked 126 mirrors / 2.0 GB before #53/#171.
    """
    root = Path(scratch)
    assert root.is_dir(), "scratch root missing: %s" % root
    assert os.environ["TMPDIR"] == str(root)
    assert os.environ["OC_BATTERY_TEST_TMPDIR"] == str(root)
    assert os.environ["OC_SNAP_ROOT"] == str(root / "oc-snap")
    assert (root / "oc-snap").is_dir()

    # A real mktemp, the way a ported leg would make one.
    out = subprocess.run(["mktemp", "-d"], capture_output=True, text=True, check=True)
    made = Path(out.stdout.strip())
    assert str(made).startswith(str(root)), (
        "mktemp escaped the scratch root: %s (TMPDIR=%s)" % (made, os.environ["TMPDIR"]))
    made.rmdir()


def test_scratch_lock_path_is_not_derived_from_tmpdir(scratch):
    """The lock stays on ONE shared path while TMPDIR is per-run.

    The trap: a TMPDIR-derived lock gives every lane its OWN lock file while
    the lanes still share one canonical receipt, so two runs both "acquire"
    and both write. The assertion is the relationship, not the literal: the
    lock must not be inside the scratch root.
    """
    lock = os.environ["OC_BATTERY_LOCK"]
    assert lock == cf.BATTERY_LOCK_PATH
    assert not lock.startswith(str(scratch)), (
        "lock path moved into the per-run TMPDIR (%s) — mutual exclusion is gone" % lock)


def test_scratch_ownership_marker_names_this_process(scratch):
    """Only the process whose pid is IN the marker may remove the root (#171)."""
    marker = Path(scratch) / cf.OWNER_MARKER
    assert marker.is_file(), "no ownership marker: a child could delete its parent's tree"
    assert marker.read_text().strip() == str(os.getpid())
    assert scratch.owned is True


def test_scratch_reaper_removes_dead_roots_and_keeps_live_ones(tmp_path):
    """The controller-side reaper: dead pid -> removed, live pid -> left alone.

    A root left by a ``kill -9``'d owner is otherwise immortal (its EXIT trap
    never ran), which is the leak ``_battery_reap_test_tmpdirs`` exists for.
    """
    dead = tmp_path / "oc-battery-999999"
    live = tmp_path / ("oc-battery-%d" % os.getpid())
    unmarked = tmp_path / "oc-battery-nomarker"
    for d in (dead, live, unmarked):
        d.mkdir()
    (dead / cf.OWNER_MARKER).write_text("999999\n")     # no such pid
    (live / cf.OWNER_MARKER).write_text("%d\n" % os.getpid())
    # unmarked: no marker at all -> not ours to judge

    removed = cf._reap_dead_roots(tmp_path)
    assert dead in removed
    assert not dead.exists(), "a dead-owner root survived the reaper"
    assert live.exists(), "the reaper deleted a LIVE root"
    assert unmarked.exists(), "the reaper judged a root it could not attribute"


# =============================================================================
# 2. env_guard
# =============================================================================
def test_env_guard_blocks_the_live_fanout_ledger():
    """OC_FANOUT_LEDGER must never be the live fleet ledger.

    The leak is that the tool DEFAULTS to ``$HOME/.opencrabs/profiles/ops/
    opencrabs-dev/events.jsonl``, so a leg that simply does not export the var
    writes the real fleet ledger. env_guard redirects it for every test.
    """
    live = str(cf.LIVE_FANOUT_LEDGER)
    got = os.environ["OC_FANOUT_LEDGER"]
    assert got != live, "OC_FANOUT_LEDGER still points at the LIVE fleet ledger"
    assert not got.startswith(str(cf.LIVE_PROFILE))
    assert os.environ.get("OC_TOOLS_NOLOG") == "1"
    assert os.environ.get("OC_SELFTEST_TIMEOUT") == "1800"


# The PATH leak, proven as a PAIR rather than as one self-satisfying assertion:
# the shell harness prepended to PATH four times and never restored it, so a
# later section inherited an earlier one's stub dirs and could pass against a
# binary it did not install. The proof needs two tests that must see each
# other's environment, so both are pinned to ONE xdist worker with
# xdist_group — which is also the documented usage in pytest.ini.
STUB_DIR = "/nonexistent/oc-env-guard-stub"


@pytest.mark.serial
@pytest.mark.xdist_group("path-restore")
def test_env_guard_blocks_state_dir_and_lets_a_test_pollute_path():
    """Test 1 of the pair: assert the pin, then deliberately leak PATH."""
    assert not os.environ["OC_DEPLOY_STATE_DIR"].startswith(str(cf.LIVE_PROFILE))
    assert not os.environ["OC_DEPLOY_STATE_DIR"].startswith(str(cf.PROD_REPO))
    # Deliberate pollution, of exactly the shape the shell harness's four
    # prepends made.
    os.environ["PATH"] = STUB_DIR + os.pathsep + os.environ["PATH"]
    assert STUB_DIR in os.environ["PATH"]


@pytest.mark.serial
@pytest.mark.xdist_group("path-restore")
def test_env_guard_restored_path_for_the_next_test():
    """Test 2 of the pair: the previous test's pollution is GONE.

    Without env_guard's post-yield restore this fails, which is the whole point:
    the leak is real and a silent one poisons every later test in the worker.
    """
    assert STUB_DIR not in os.environ.get("PATH", ""), (
        "PATH pollution from the previous test survived — env_guard is not "
        "restoring it (the PATH leak)")


def test_run_tool_refuses_the_production_checkout():
    """``--repo /root/opencrabs`` is the leak an env var cannot block.

    The shell harness read the PRODUCTION checkout, so a leg that copied it
    verbatim would assert against a tree this lane does not own.
    """
    with pytest.raises(cf.LiveStateLeak) as exc:
        cf._run([sys.executable, "-c", "pass", "--repo", str(cf.PROD_REPO)],
                timeout=10)
    assert "PRODUCTION checkout" in str(exc.value)


def test_run_tool_refuses_a_live_env_value(monkeypatch):
    """A live-state env value set behind env_guard's back is caught at launch."""
    monkeypatch.setenv("OC_LEDGER", str(cf.LIVE_PROFILE / "workers.json"))
    with pytest.raises(cf.LiveStateLeak) as exc:
        cf._run([sys.executable, "-c", "pass"], timeout=10)
    assert "live fleet state reachable" in str(exc.value)


# =============================================================================
# 3. run_tool — the process-GROUP kill
# =============================================================================
def test_run_tool_kills_the_grandchild_on_timeout(run_tool, tmp_path):
    """A two-level process tree must be GONE after the bound fires (#753).

    ``subprocess.run(timeout=)`` signals only the direct child: the selftest's
    grandchildren survive, keep burning the box, and nothing reaps them. The
    fixture uses ``start_new_session=True`` + ``os.killpg``, which is what
    ``timeout --kill-after`` did.

    The tree is built so the grandchild OUTLIVES its parent if only the direct
    child is signalled: the middle process forks the grandchild and then blocks
    in ``wait``, so killing the middle one leaves the grandchild reparented and
    running. Only a group kill reaches it.
    """
    pidfile = tmp_path / "grandchild.pid"
    # middle: spawn a detached grandchild that sleeps, record its pid, then block.
    middle = tmp_path / "middle.py"
    middle.write_text(
        "import os, subprocess, sys, time\n"
        "g = subprocess.Popen([sys.executable, '-c',"
        " 'import time; time.sleep(120)'])\n"
        "open(%r, 'w').write(str(g.pid))\n"
        "time.sleep(120)\n" % str(pidfile)
    )

    started = time.monotonic()
    res = run_tool([sys.executable, str(middle)], timeout=2)
    elapsed = time.monotonic() - started

    assert res.timed_out is True, "run_tool did not time out at a 2s bound"
    assert res.rc == 124, "timeout must surface timeout(1)'s rc 124, got %r" % res.rc
    assert elapsed < 30, "the bound did not actually bound anything (%.1fs)" % elapsed

    assert pidfile.is_file(), "the grandchild never started — the fixture proves nothing"
    gpid = int(pidfile.read_text().strip())

    # Poll: SIGKILL is asynchronous, and a zombie still answers kill -0 until it
    # is reaped by init. 2s is generous for init to adopt and reap.
    deadline = time.monotonic() + 5
    alive = True
    while time.monotonic() < deadline:
        try:
            os.kill(gpid, 0)
        except ProcessLookupError:
            alive = False
            break
        time.sleep(0.05)

    if alive:
        # Last resort: distinguish "still running" from "unreaped zombie".
        try:
            state = Path("/proc/%d/stat" % gpid).read_text().split(") ", 1)[1][0]
        except (OSError, IndexError):
            state = "?"
        os.kill(gpid, 9) if state != "Z" else None
        assert state == "Z", (
            "grandchild pid %d SURVIVED the group kill (state=%s) — the #753 "
            "orphan class is back" % (gpid, state))


def test_run_tool_requires_timeout(run_tool):
    """``timeout`` has no default: omitting it is a TypeError, not a 10-min hang."""
    with pytest.raises(TypeError):
        run_tool([sys.executable, "-c", "pass"])


def test_run_tool_returns_the_result_object(run_tool):
    res = run_tool([sys.executable, "-c", "import sys; print('out'); "
                                          "print('err', file=sys.stderr); sys.exit(3)"],
                   timeout=30)
    assert res.rc == 3
    assert res.out.strip() == "out"
    assert res.err.strip() == "err"
    assert res.duration_ms >= 0
    assert res.timed_out is False


# =============================================================================
# 4. battery_lock — single-flight, one shared path
# =============================================================================
@pytest.mark.serial
@pytest.mark.xdist_group("battery-lock")
def test_battery_lock_is_the_one_shared_path(battery_lock, scratch):
    """The flock is held on the SHARED path, outside the per-run TMPDIR.

    Two properties, and both matter: the file is the module constant (so every
    lane contends on the same inode), and it is not inside this worker's scratch
    root (so a per-run TMPDIR cannot hand each lane its own lock while they share
    one receipt — the trap of a per-lane lock file).
    """
    import fcntl

    assert battery_lock == cf.BATTERY_LOCK_PATH
    assert not battery_lock.startswith(str(scratch.path))
    assert Path(battery_lock).exists()

    # The lock is really HELD: a non-blocking acquire from a second fd fails.
    fh = open(battery_lock, "a+")
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        fh.close()
