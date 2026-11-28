"""cgroup isolation (#720) — the re-exec must actually happen, and fail OPEN.

The block under test is ``lib/cgroup.py::pytest_cmdline_main``. It cannot be
exercised through a fixture: by fixture time xdist workers already exist, which
is exactly why the re-exec lives in ``pytest_cmdline_main`` (plan §3.3).

What CAN be asserted from inside a running session:

* the run is NOT in a ``*.service`` leaf — the daemon's unit
  (``opencrabs-ops.service``) is the cgroup whose OOMPolicy=kill takes the
  daemon down with a single over-limit test allocation. If the run IS in a
  service leaf, isolation is inert and the whole point is lost;
* the cap set scales with ``-n N`` — a fixed ``TasksMax=128`` under ``-n 8``
  reproduces the #74 ``EAGAIN`` rows as test failures instead of a stated cap;
* fail-open: a refused scope warns and continues rather than replacing the run
  with systemd-run's exit code.

The branch LOGIC (service vs scope vs opt-out vs refusal) is driven with
synthetic paths through ``is_service_leaf``/``caps_for``, because a test that
can only exercise the branch its own environment happens to take asserts
nothing — the reason the shell harness's section 85 stubbed ``systemd-run`` in
the first place.
"""

from __future__ import annotations

import os

import pytest

from lib import cgroup


# ---------------------------------------------------------------------------
# THE required assertion: the live run is not inside the daemon's unit
# ---------------------------------------------------------------------------
def test_run_is_not_in_a_service_leaf():
    """Isolation is a CLAIM until it is read back from /proc/self/cgroup.

    A ``*.service`` leaf means the run inherited the daemon's unit, where
    MemoryMax == MemoryHigh == 1536 MiB and OOMPolicy=kill: one over-limit
    allocation tears down the daemon.
    """
    cg = cgroup.read_cgroup_path()
    assert cg, "cannot read /proc/self/cgroup — the cgroup claim is unfalsifiable"

    warning = cgroup.cgroup_warning()
    if cgroup.is_service_leaf(cg):
        # Fail-open is legitimate (no systemd-run, no user manager, refused
        # scope) — but only if it SAID SO. Silence would make a broken
        # isolation indistinguishable from a working one.
        assert warning, (
            "run is inside the daemon's unit (%s) and no fail-open warning was "
            "emitted — isolation is inert and undisclosed (#720)" % cg)
        pytest.skip("cgroup isolation failed OPEN (disclosed): %s" % warning)

    # Not a service leaf: either we re-exec'd, or we were already outside.
    assert cg.rstrip("/").rsplit("/", 1)[-1].endswith(".scope") or "/" in cg


def test_isolation_state_is_recorded():
    """The session states WHICH branch it took, so a receipt reader can tell."""
    state = cgroup.cgroup_state()
    assert state in {
        "re-exec", "already-isolated", "already-outside-service",
        "opted-out", "no-systemd-run", "no-systemctl", "no-user-manager",
        "unreadable-cgroup", "scope-refused",
    }, "unexpected cgroup state %r" % state
    # And the receipt carries the same claim durably.
    # (written by the cgroup session-finish hook; see test_receipt.py for shape)


# ---------------------------------------------------------------------------
# branch logic — synthetic paths, both directions
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path,expected", [
    ("/user.slice/user-0.slice/user@0.service/app.slice/opencrabs-ops.service", True),
    ("/user.slice/user-0.slice/user@0.service/app.slice/run-r1234.scope", False),
    # THE trap: every user-manager cgroup sits under user@0.service, so a
    # substring test on the FULL path calls any user cgroup a service — a
    # transient .scope leaf included, which made the "already isolated" branch
    # unreachable in the shell harness.
    ("/user.slice/user-0.slice/user@0.service/app.slice/x.scope", False),
    ("", False),
])
def test_is_service_leaf_reads_the_leaf_only(path, expected):
    assert cgroup.is_service_leaf(path) is expected


def test_the_one_worker_cap_set_is_the_measured_baseline():
    """``-n 1`` caps are the numbers the box was profiled at.

    These were pinned against the shell harness's single cap array while the
    shell existed. The shell is retired, so they are pinned HERE — as absolute
    values, because they are the budget every past measurement was taken in.
    Changing one silently invalidates the comparison between an old receipt and
    a new run.
    """
    caps = cgroup.caps_for(1)
    joined = " ".join(caps)
    for prop in ("MemoryMax=1024M", "MemorySwapMax=512M",
                 "CPUQuota=300%", "TasksMax=128"):
        assert prop in joined, "the -n 1 baseline lost %s: %r" % (prop, joined)


@pytest.mark.parametrize("n", [1, 2, 4, 8])
def test_caps_scale_with_worker_count(n):
    """Tree-wide caps multiply with ``-n`` — or #74 comes back as test failures.

    ``TasksMax`` and ``CPUQuota`` bound the controller AND every worker at once.
    A fixed ``TasksMax=128`` under ``-n 8`` yields "fork rejected by pids
    controller" rows, which read as EIGHT broken tools rather than one stated
    cap (the exact defect the shell harness spent section 88 diagnosing).
    """
    joined = " ".join(cgroup.caps_for(n))
    assert "TasksMax=%d" % (128 * n) in joined
    assert "CPUQuota=%d%%" % (300 * n) in joined
    # Memory scales too, but is CEILINGED at 75 % of physical RAM: a tree-wide
    # MemoryMax larger than the box is not a cap — it stops protecting the
    # daemon while still claiming to. So assert the ceiling, not the product.
    mem, swap = cgroup._mem_caps(n)
    assert "MemoryMax=%dM" % mem in joined
    assert "MemorySwapMax=%dM" % swap in joined
    assert mem <= 1024 * n
    ram = cgroup.physical_ram_mb()
    if ram:
        assert mem <= int(ram * 0.75)


def test_memory_cap_is_disclosed_when_it_is_ceilinged():
    """A silently reduced cap is indistinguishable from a slower box (#74's lesson)."""
    ram = cgroup.physical_ram_mb()
    if not ram:
        pytest.skip("no /proc/meminfo on this box")
    n = max(1, (int(ram * 0.75) // 1024) + 1)     # forces the ceiling
    desc = cgroup.caps_description(n)
    assert "ceilinged at 75%" in desc, (
        "the memory ceiling fired but the run did not say so: %r" % desc)


def test_caps_never_go_below_one_worker():
    """``-n 0`` is a supported mode, not a zero budget: caps floor at one."""
    zero = cgroup.caps_for(0)
    assert zero == cgroup.caps_for(1)


def test_worker_count_resolution():
    assert cgroup.worker_count(0) == 1
    assert cgroup.worker_count(None) == 1
    assert cgroup.worker_count("auto") >= 1
    assert cgroup.worker_count("logical") >= 1
    assert cgroup.worker_count(4) == 4
    assert cgroup.worker_count("3") == 3
    assert cgroup.worker_count("garbage") == 1


def test_probe_and_exec_share_one_cap_array():
    """The probe and the real exec must never diverge (the shell's one array).

    A divergence means the probe validates a DIFFERENT cap set than the one the
    run gets — the failure mode the shell harness avoided by building the array
    once. Asserted structurally: ``caps_for`` is the only producer, and the
    module has no second literal property list.
    """
    src = open(cgroup.__file__, encoding="utf-8").read()
    body = src[src.index("def caps_for"):src.index("def caps_description")]
    for prop in ("MemoryMax=", "CPUQuota=", "TasksMax="):
        assert prop in body, "%s is not built in caps_for — a second list exists" % prop
    # The hook must call caps_for, not build its own -p list.
    hook = src[src.index("def pytest_cmdline_main"):]
    assert "caps_for(n)" in hook, "the hook builds its own cap list instead of caps_for()"
