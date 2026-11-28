"""The cgroup re-exec, tested where it now lives: ``lib/cgroup.py``.

These legs used to drive the shell block extracted out of ``run.sh`` by
``test_harness_cgroup.py``. The block is gone; ``pytest_cmdline_main`` is the
implementation, and it is testable directly because every external fact it reads
goes through one of four seams: ``shutil.which``, ``subprocess.run``,
``read_cgroup_path`` and ``os.execv``. Stub those and the whole branch tree is
observable — including the failure paths, which are the ones that matter: an
isolation that silently does nothing is worse than none, because the receipt
then claims a scope that does not exist.

WHY ``None`` IS THE CONTRACT
``pytest_cmdline_main`` is a ``firstresult`` hook. A non-``None`` return ENDS the
run with that exit code. So "keep going" and "return None" are the same
statement, and every leg below that expects the run to continue asserts
``is None`` — a leg that merely avoided an exception would pass on a hook that
returned an error code and killed the session.
"""

from __future__ import annotations

import os
import subprocess

import pytest

import conftest as cf
from lib import cgroup

SERVICE_LEAF = ("/user.slice/user-0.slice/user@0.service/app.slice/"
                "opencrabs-ops.service")


class Seams:
    """The four externals, stubbed. Every leg builds one of these."""

    def __init__(self, monkeypatch, *, cg=SERVICE_LEAF, systemd_run=True,
                 systemctl=True, probe_rc=0, manager_out=b"running\n"):
        self.execs: list[list[str]] = []
        self.runs: list[list[str]] = []

        monkeypatch.setattr(
            cgroup.shutil, "which",
            lambda name: ("/usr/bin/%s" % name) if (
                (name == "systemd-run" and systemd_run)
                or (name == "systemctl" and systemctl)) else None)
        monkeypatch.setattr(cgroup, "read_cgroup_path", lambda: cg)
        monkeypatch.setattr(cgroup.os, "execv",
                            lambda path, argv: self.execs.append(list(argv)))

        def fake_run(cmd, **kw):
            self.runs.append(list(cmd))
            if cmd[0].endswith("systemctl"):
                return subprocess.CompletedProcess(cmd, 0, manager_out, b"")
            return subprocess.CompletedProcess(cmd, probe_rc, b"", b"")
        monkeypatch.setattr(cgroup.subprocess, "run", fake_run)

        # Every env fact the hook branches on, pinned per leg.
        for k in ("PYTEST_XDIST_WORKER", "BATTERY_CGROUP_ISOLATED",
                  "BATTERY_CGROUP_PARENT_CG", "OC_PYTEST_NO_CGROUP",
                  "OC_BATTERY_NO_CGROUP"):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.delenv(cgroup.STATE_ENV, raising=False)
        monkeypatch.delenv(cgroup.WARNING_ENV, raising=False)

    @property
    def state(self) -> str:
        return os.environ.get(cgroup.STATE_ENV, "")

    @property
    def warned(self) -> str:
        return os.environ.get(cgroup.WARNING_ENV, "")


class Cfg:
    """Just enough of pytest's ``config`` for ``worker_count``."""

    class option:
        numprocesses = None


# ---------------------------------------------------------------------------
# the isolation path
# ---------------------------------------------------------------------------
def test_inside_a_service_unit_the_run_reexecs(monkeypatch):
    """A service leaf is the cgroup the daemon shares — it must re-exec away."""
    s = Seams(monkeypatch)
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert len(s.execs) == 1, "expected exactly one exec, got %r" % (s.execs,)
    assert s.execs[0][0].endswith("systemd-run")
    assert "--scope" in s.execs[0]
    assert s.state == "re-exec"


def test_reexec_carries_the_isolation_flag(monkeypatch):
    """The child must be able to tell it was isolated BY US, not by an outer run."""
    s = Seams(monkeypatch)
    cgroup.pytest_cmdline_main(Cfg())
    assert os.environ.get("BATTERY_CGROUP_ISOLATED") == "1"
    assert os.environ.get("BATTERY_CGROUP_PARENT_CG") == SERVICE_LEAF
    assert s.state == "re-exec"


def test_probe_and_exec_share_one_cap_array(monkeypatch):
    """The probe asks for the caps the run will actually get.

    If the two arrays diverge, a green probe proves a scope the run never
    entered — the probe would be certifying someone else's budget.
    """
    s = Seams(monkeypatch)
    cgroup.pytest_cmdline_main(Cfg())
    probe_caps = [a for a in s.runs[-1] if "=" in a]
    exec_caps = [a for a in s.execs[0] if "=" in a]
    assert probe_caps == exec_caps, (
        "probe caps %r != exec caps %r — the probe certified a different scope"
        % (probe_caps, exec_caps))
    assert "MemoryMax=1024M" in exec_caps


def test_the_reexec_is_guarded_to_one_level(monkeypatch):
    """The transient child carries the flag; a second entry must not re-exec.

    Without this the isolated child would isolate again, forking a scope per
    generation until the budget runs out.
    """
    s = Seams(monkeypatch)
    monkeypatch.setenv("BATTERY_CGROUP_ISOLATED", "1")
    monkeypatch.setenv("BATTERY_CGROUP_PARENT_CG", SERVICE_LEAF)
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.execs == [], "the child re-exec'd a second time — unbounded nesting"
    assert s.state == "re-exec"


def test_an_xdist_worker_never_reexecs(monkeypatch):
    """A worker that re-exec'd would fork a scope per worker and detach."""
    s = Seams(monkeypatch)
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.execs == []
    assert s.runs == [], "a worker probed the scope before deciding"


# ---------------------------------------------------------------------------
# fail-open paths — each must state WHY it is unisolated
# ---------------------------------------------------------------------------
def test_refused_scope_fails_open(monkeypatch):
    """A scope the box will not grant must not fail the gate.

    Isolation is an optimisation of the measurement environment, not a
    precondition of correctness: refusing to run because the box is busy would
    turn a resource problem into a red gate.
    """
    s = Seams(monkeypatch, probe_rc=1)
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.execs == []
    assert s.state == "scope-refused"
    assert s.warned, "failing open without saying so is silent unisolation"


def test_refusal_makes_exactly_one_attempt(monkeypatch):
    """One probe, then stop. A retry loop against a refusing box burns the run."""
    s = Seams(monkeypatch, probe_rc=1)
    cgroup.pytest_cmdline_main(Cfg())
    probes = [c for c in s.runs if not c[0].endswith("systemctl")]
    assert len(probes) == 1, "the refused probe was retried: %r" % (probes,)


def test_a_scope_cgroup_is_left_alone(monkeypatch):
    """A transient .scope leaf is already isolated — the trap is substring tests.

    Every user-manager cgroup sits under ``user@0.service``, so a substring test
    on the FULL path calls any user cgroup a service and re-execs forever.
    """
    s = Seams(monkeypatch, cg="/user.slice/user-0.slice/user@0.service/"
                             "app.slice/run-r1234.scope")
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.execs == []
    assert s.state == "already-outside-service"


def test_opt_out_skips_isolation_entirely(monkeypatch):
    """The opt-out is read BEFORE any probing — it must cost nothing."""
    s = Seams(monkeypatch)
    monkeypatch.setenv("OC_PYTEST_NO_CGROUP", "1")
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.runs == [], "the opt-out still probed the box"
    assert s.execs == []
    assert s.state == "opted-out"
    assert s.warned


@pytest.mark.parametrize("absent,needle", [
    ("systemd_run", "systemd-run"),
    ("systemctl", "systemctl"),
])
def test_missing_systemd_warns_and_survives(monkeypatch, absent, needle):
    """No user manager is a reason to SAY so, never a reason to die."""
    s = Seams(monkeypatch, **{absent: False})
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.execs == []
    assert needle in s.warned
    assert s.state in {"no-systemd-run", "no-systemctl"}


def test_an_unreadable_cgroup_fails_open(monkeypatch):
    """An empty cgroup path means /proc/self/cgroup told us nothing."""
    s = Seams(monkeypatch, cg="")
    assert cgroup.pytest_cmdline_main(Cfg()) is None
    assert s.execs == []
    assert s.state == "unreadable-cgroup"
    assert s.warned
