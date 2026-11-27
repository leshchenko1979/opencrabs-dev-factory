"""cgroup isolation for the pytest battery — ``pytest_cmdline_main`` re-exec.

WHY THIS IS NOT A FIXTURE
    By fixture time xdist workers already exist: they are forked during
    ``pytest_sessionstart``, which runs long after ``pytest_cmdline_main``. A
    fixture would isolate the controller only, and every worker — the processes
    that actually run the tools — would stay inside the daemon's unit.
    ``pytest_cmdline_main`` is the EARLIEST hook pytest offers, so the re-exec
    happens before a single worker exists.

WHY IT MUST RE-EXEC AT ALL
    Every command a lane runs inherits the daemon's cgroup
    (``.../app.slice/opencrabs-ops.service``), whose wall is MemoryHigh ==
    MemoryMax == 1536 MiB with swap exhausted and whose OOMPolicy=kill tears the
    WHOLE unit down on an over-limit allocation — so a test allocation does not
    merely die, it takes the daemon with it. Measured 2026-09-30: four daemon OOM
    kills in one day, each during a battery run (run.sh:367-440, #720).

CAPS SCALE WITH ``-n N``
    ``TasksMax``, ``CPUQuota`` and ``MemoryMax`` are TREE-WIDE: they bound the
    controller AND every worker at once. A fixed ``TasksMax=128`` under ``-n 8``
    reproduces the #74 ``EAGAIN`` rows ("fork rejected by pids controller") as
    test failures instead of as a stated cap — the exact defect the shell
    harness spent a section diagnosing. So every cap is multiplied by the worker
    count, and the numbers are printed once so the run STATES its budget.

FAIL OPEN
    No ``systemd-run``, no user manager, an unreadable cgroup, or a refused scope
    all leave the run on its current path with ONE warning. A harness that
    refuses to run is worse than one running in the wrong cgroup, and a bare
    ``exec`` cannot fail open by itself: it never returns, so a refused re-exec
    would replace the run with systemd-run's own exit code and a harness error
    would be read as a RED verdict. Hence probe-then-exec: one throwaway scope
    creation settles whether the caps are accepted BEFORE the real one replaces
    us, and the probe and the exec share ONE array so they can never diverge.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# The single source of truth for the cap set. One array, two consumers.
BASE_CAPS = {
    "MemoryMax": "1024M",
    "MemorySwapMax": "512M",
    "CPUQuota": "300%",
    "TasksMax": "128",
}
# Per-worker multiplier applied to every cap (see CAPS SCALE above).
PER_WORKER = {
    "MemoryMax": 1024,        # MiB
    "MemorySwapMax": 512,     # MiB
    "CPUQuota": 300,          # percent
    "TasksMax": 128,          # pids
}
# Warning text recorded for the session, so the leaf-unit test can explain a
# deliberate fail-open instead of accusing a healthy run.
WARNING_ENV = "OC_PYTEST_CGROUP_WARNING"
STATE_ENV = "OC_PYTEST_CGROUP_STATE"


def _cpu_count() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, os.cpu_count() or 1)


def worker_count(option_numprocesses) -> int:
    """Resolve ``-n`` to a number: ``auto``/``logical`` -> cpu count, 0/None -> 1."""
    n = option_numprocesses
    if n in (None, 0, "0"):
        return 1
    if isinstance(n, str):
        if n in ("auto", "logical"):
            return _cpu_count()
        try:
            return max(1, int(n))
        except ValueError:
            return 1
    try:
        return max(1, int(n))
    except (TypeError, ValueError):
        return 1


def physical_ram_mb() -> int:
    """Total RAM in MiB, or 0 when /proc/meminfo is unreadable."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _mem_caps(n: int) -> tuple[int, int]:
    """(MemoryMax, MemorySwapMax) in MiB for ``n`` workers.

    Scaled per worker, but CEILINGED at 75 % of physical RAM: a tree-wide
    ``MemoryMax`` larger than the box is not a cap at all — it stops protecting
    the daemon (which is the entire reason the scope exists) while still
    claiming to. Measured on this host: 4015132 kB total, so ``-n auto`` (4
    workers) would otherwise ask for 4096M, more than the box has.
    """
    mem = PER_WORKER["MemoryMax"] * n
    swap = PER_WORKER["MemorySwapMax"] * n
    ram = physical_ram_mb()
    if ram > 0:
        ceiling = int(ram * 0.75)
        if mem > ceiling:
            mem = ceiling
        # Swap is capped to half the memory cap, keeping run.sh's 2:1 ratio.
        swap = min(swap, max(1, mem // 2))
    return mem, swap


def caps_for(n_workers: int) -> list[str]:
    """The cap set for a run with ``n_workers``, as systemd-run ``-p`` args.

    At ``n == 1`` this is byte-identical to run.sh:423
    (``MemoryMax=1024M MemorySwapMax=512M CPUQuota=300% TasksMax=128``) on any
    box with >=1366 MiB of RAM, so a serial pytest run and the shell harness are
    compared on the same budget. Above that, memory is ceilinged at 75 % of
    physical RAM (see ``_mem_caps``) and ``caps_description`` says so.
    """
    n = max(1, int(n_workers))
    mem, swap = _mem_caps(n)
    cpu = PER_WORKER["CPUQuota"] * n
    tasks = PER_WORKER["TasksMax"] * n
    args: list[str] = []
    for key, val in (("MemoryMax", "%dM" % mem),
                     ("MemorySwapMax", "%dM" % swap),
                     ("CPUQuota", "%d%%" % cpu),
                     ("TasksMax", "%d" % tasks)):
        args += ["-p", "%s=%s" % (key, val)]
    return args


def caps_description(n_workers: int) -> str:
    n = max(1, int(n_workers))
    mem, swap = _mem_caps(n)
    note = ""
    if mem != PER_WORKER["MemoryMax"] * n:
        note = " [memory ceilinged at 75%% of %dM physical]" % physical_ram_mb()
    return ("MemoryMax=%dM MemorySwapMax=%dM CPUQuota=%d%% TasksMax=%d "
            "(tree-wide, scaled for -n %d)%s" % (
                mem, swap, PER_WORKER["CPUQuota"] * n,
                PER_WORKER["TasksMax"] * n, n, note))


def read_cgroup_path() -> str:
    """A FUNCTION so a test can drive the branch logic with a synthetic path."""
    try:
        for line in Path("/proc/self/cgroup").read_text().splitlines():
            if line.startswith("0::"):
                return line[3:]
    except OSError:
        return ""
    return ""


def is_service_leaf(cg_path: str) -> bool:
    """Is the LEAF unit a ``*.service``?

    Read the leaf, never the whole path: every user-manager cgroup sits under
    ``user@0.service``, so a substring test on the full path calls ANY user
    cgroup a service — a transient ``.scope`` leaf included. That made the
    "already isolated" branch unreachable in the shell harness and re-exec'd a
    scope's own children (run.sh:397-408).
    """
    return bool(cg_path) and cg_path.rstrip("/").rsplit("/", 1)[-1].endswith(".service")


def _warn(msg: str) -> None:
    print("pytest-cgroup: WARNING: %s" % msg, file=sys.stderr)
    os.environ[WARNING_ENV] = msg


def _state(value: str) -> None:
    os.environ[STATE_ENV] = value


# =============================================================================
# the hook
# =============================================================================
def pytest_cmdline_main(config):
    """Re-exec into a transient scope, before any xdist worker is forked.

    Returns ``None`` in every path that continues the run (a non-None return is
    a firstresult answer and would END the session with that exit code).
    """
    # xdist workers call this hook too (xdist/remote.py). A worker must never
    # re-exec: it would fork a scope per worker and detach from its controller.
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return None

    # Guard the re-exec to ONE level: the transient child carries the flag.
    # BATTERY_CGROUP_PARENT_CG is set only by OUR exec, so its presence is what
    # distinguishes "we re-exec'd ourselves" from "an outer runner isolated us".
    if os.environ.get("BATTERY_CGROUP_ISOLATED") == "1":
        _state("re-exec" if os.environ.get("BATTERY_CGROUP_PARENT_CG")
               else "already-isolated")
        return None
    if os.environ.get("OC_PYTEST_NO_CGROUP") or os.environ.get("OC_BATTERY_NO_CGROUP"):
        _state("opted-out")
        _warn("cgroup isolation opted out (OC_PYTEST_NO_CGROUP/OC_BATTERY_NO_CGROUP) — "
              "running in %s (#720)" % (read_cgroup_path() or "?"))
        return None

    sr = shutil.which("systemd-run")
    mgr = shutil.which("systemctl")
    cg = read_cgroup_path()
    if not sr:
        _state("no-systemd-run")
        _warn("no systemd-run — running in %s (NOT isolated from the daemon "
              "cgroup, #720)" % (cg or "?"))
        return None
    if not mgr:
        _state("no-systemctl")
        _warn("no systemctl — running in %s unisolated (#720)" % (cg or "?"))
        return None
    try:
        up = subprocess.run([mgr, "--user", "is-system-running"],
                            capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        up = None
    # `is-system-running` exits 1 for "degraded", which still has a working
    # user manager — accept any answer that produced output on stdout/stderr
    # rather than only rc 0, else a degraded box silently loses isolation.
    if up is None or (up.returncode != 0 and not (up.stdout or up.stderr)):
        _state("no-user-manager")
        _warn("no user systemd manager — running in %s unisolated (#720)" % (cg or "?"))
        return None
    if not cg:
        _state("unreadable-cgroup")
        _warn("cgroup path unreadable — running unisolated (#720)")
        return None
    if not is_service_leaf(cg):
        _state("already-outside-service")
        print("pytest-cgroup: already outside a service cgroup (%s) — "
              "no isolation needed" % cg, file=sys.stderr)
        return None

    n = worker_count(getattr(config.option, "numprocesses", None))
    caps = ["--user", "--scope", "--quiet", *caps_for(n)]

    # PROBE, then EXEC — the same array both times.
    try:
        probe = subprocess.run([sr, *caps, "true"], capture_output=True, timeout=60)
        ok = probe.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        _state("scope-refused")
        _warn("could not create a transient scope — running in %s unisolated "
              "(#720)" % cg)
        return None

    os.environ["BATTERY_CGROUP_ISOLATED"] = "1"
    os.environ["BATTERY_CGROUP_PARENT_CG"] = cg
    _state("re-exec")
    print("pytest-cgroup: re-exec into a transient scope to isolate from the "
          "daemon cgroup (#720); caps: %s" % caps_description(n), file=sys.stderr)
    argv = [sys.executable, "-m", "pytest", *sys.argv[1:]]
    os.execv(sr, [sr, *caps, *argv])
    return None            # unreachable; keeps a linter honest


# =============================================================================
# session-finish hook — record the cgroup into the receipt
# =============================================================================
def pytest_sessionfinish(session, exitstatus):
    config = session.config
    run = getattr(config, "_oc_run", None)
    if run is None or hasattr(config, "workerinput"):
        return             # controller only, same rule as the receipt itself
    cg = read_cgroup_path()
    isolated = (
        os.environ.get("BATTERY_CGROUP_ISOLATED") == "1"
        and bool(cg)
        and cg != os.environ.get("BATTERY_CGROUP_PARENT_CG", "")
    )
    overrides = run.extra.setdefault("receipt_overrides", {})
    overrides["cgroup"] = cg
    overrides["cgroup_isolated"] = bool(isolated)
    # Keep the module's own view in step for the leaf-unit test.
    run.extra["cgroup_state"] = os.environ.get(STATE_ENV, "")
    run.extra["cgroup_warning"] = os.environ.get(WARNING_ENV, "")


def cgroup_state() -> str:
    return os.environ.get(STATE_ENV, "")


def cgroup_warning() -> str:
    return os.environ.get(WARNING_ENV, "")
