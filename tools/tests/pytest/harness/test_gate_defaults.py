"""The gate's own definition: concurrency, selection, and the receipt path.

The shell harness used to hold these as four terms inside one ``section`` call,
each chosen against a measured failure. With the shell retired they live in
``pytest.ini``'s ``addopts``, which means the bare command IS the gate — and that
makes ``pytest.ini`` load-bearing code that nothing was testing.

WHAT EACH TERM PREVENTS (the receipts, kept because they are why the numbers are
what they are, not provenance)

* ``-n 2`` — at ``-n 4`` on this 3.9 GB box, seventeen unrelated tests reddened
  with identical jemalloc ``EAGAIN`` (errno 11) thread-creation noise: overlapping
  ``--selftest`` process trees against the scope's ``TasksMax``. Zero real
  defects; the box, not the code. A gate that reddens for reasons unrelated to
  the change is a gate people learn to ignore.
* ``-m "not slow"`` — ``slow`` means "on request". Those legs drive full tool
  selftests and take minutes each; in the gate they would make every run a
  half-hour.
* The receipt path — ``oc-ledger sync`` reads ``tools/tests/battery-last.json``
  and dies rc 5 on a missing, stale or RED verdict, so the writer must not move
  it (``test_receipt.py`` pins that; this module pins that the gate can write it
  at all).

WHY A GUARD AND NOT JUST THE VALUES
Each of these can be "simplified" back into its failure by a later editor who
sees a bare number and no reason. The guard sits in `pytest.ini`, where the
values now live, so it cannot drift from them.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

import pytest

import conftest as cf

INI = cf.PYTEST_DIR / "pytest.ini"


def addopts() -> list[str]:
    """The ``addopts`` value, split on whitespace.

    Read from the ini's TEXT rather than from the live config object: the live
    object includes whatever the command line added, so a test asserting on it
    would pass or fail depending on how the suite was invoked — and a guard whose
    verdict depends on the invocation is not a guard.
    """
    text = INI.read_text(encoding="utf-8")
    m = re.search(r"^addopts\s*=\s*(.+)$", text, re.MULTILINE)
    assert m, "pytest.ini has no addopts line — the gate lost its defaults"
    # shlex, not str.split(): ``-m "not slow"`` is ONE argument, and a plain
    # split yields ``"not`` + ``slow"`` — which silently reads as no -m at all.
    return shlex.split(m.group(1))


def test_gate_runs_at_two_workers_never_four():
    """``-n 2`` is the box's measured capacity; ``-n 4`` is the EAGAIN trap."""
    opts = addopts()
    assert "-n" in opts, (
        "addopts lost -n: the gate now runs at pytest's default (one worker per "
        "CPU via xdist auto, or serial) — neither is the measured-safe value")
    n = opts[opts.index("-n") + 1]
    assert n == "2", (
        "the gate runs at -n %s. -n 4 is the documented EAGAIN trap on this box "
        "(17 unrelated reds, jemalloc errno 11, zero real defects)" % n)


def test_gate_deselects_the_slow_legs():
    """``slow`` legs are minutes each; a gate that includes them is unusable."""
    opts = addopts()
    assert "-m" in opts, "addopts lost -m: the slow legs are back in the gate"
    expr = opts[opts.index("-m") + 1].strip("\"'")
    assert "not slow" in expr, (
        "the gate's -m expression is %r — the slow legs drive full tool "
        "selftests and would make every gate run a half-hour" % expr)


def test_gate_keeps_loadgroup_scheduling():
    """``--dist loadgroup`` is what makes ``xdist_group`` mean anything.

    xdist's default scheduler is ``load``, which IGNORES ``xdist_group``
    entirely: every ``serial`` marker in this suite would be inert, and two
    same-group legs could hold at once. A marker that schedules nothing is worse
    than no marker — it reads as a guarantee.
    """
    opts = addopts()
    assert "--dist" in opts, "addopts lost --dist: xdist_group is now inert"
    assert opts[opts.index("--dist") + 1] == "loadgroup", (
        "--dist is %r, not loadgroup — every serial/xdist_group leg can now "
        "overlap" % opts[opts.index("--dist") + 1])


def test_gate_can_write_the_version_bump_receipt():
    """The gate must be able to produce the file ``oc-ledger sync`` reads.

    Asserted as a path relationship rather than by running the gate: the receipt
    path comes from ``lib.receipt.DEFAULT_RECEIPT``, and a scoped run must
    override it, so the check is that the default lands where sync looks.
    """
    from lib import receipt as R

    assert R.DEFAULT_RECEIPT == cf.REPO_ROOT / "tools" / "tests" / "battery-last.json", (
        "the receipt default is %s — oc-ledger sync reads battery-last.json and "
        "would die rc 5 or read a stale verdict" % R.DEFAULT_RECEIPT)


# ---------------------------------------------------------------------------
# the receipt is actually WRITTEN by the gate as the gate runs
# ---------------------------------------------------------------------------
def test_the_gate_writes_its_receipt_under_xdist(tmp_path):
    """A ``-n 2`` run must produce the receipt file.

    This is the leg that would have caught the defect found on 2026-11-28: the
    run was armed from ``pytest_collection_modifyitems``, a hook xdist executes
    ONLY IN WORKERS. The controller's run object stayed ``None``, so a full
    492-test gate reported success and wrote NOTHING — while ``oc-ledger sync``
    read whatever stale PASS sat at the canonical path and let a version bump
    through on numbers from an earlier run.

    Driven as a REAL subprocess run of one cheap module, because the property is
    about pytest's hook dispatch under xdist and no in-process assertion can
    observe that. ``OC_PYTEST_RECEIPT`` keeps it off the tracked receipt.
    """
    import json
    import subprocess
    import sys

    out = tmp_path / "receipt.json"
    env = dict(os.environ, OC_PYTEST_RECEIPT=str(out))
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "harness/test_gate_defaults.py",
         "-q", "-n", "2", "-p", "no:randomly",
         "--no-header", "-k", "test_gate_runs_at_two_workers"],
        capture_output=True, text=True, timeout=300, env=env,
        cwd=str(cf.PYTEST_DIR))
    assert r.returncode == 0, (r.stdout[-2000:] + r.stderr[-2000:])
    assert out.is_file(), (
        "a -n 2 run wrote no receipt — the controller never got a run object, "
        "so the gate's numbers never reach oc-ledger sync")
    data = json.loads(out.read_text())
    assert data.get("verdict") == "PASS"
    assert data.get("pass", 0) >= 1, "the receipt records no passing test"
