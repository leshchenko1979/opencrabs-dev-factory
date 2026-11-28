"""oc-health — hourly health / cleanliness sweep.

The section's centre of gravity is the WATCHER-WINDOW leg, and it is here
because the leg it replaced could not go red: the shell leg ran against the
LIVE detached corpus (~19,651 files, 76 s wall, growing ~2,800 files/day with
nothing reaping it) and asserted only ``rc in (0,1)`` plus "the JSON parses" —
both of which pass whether or not the override does anything at all.

The replacement runs on a two-task fixture and DISCRIMINATES: one nohup
violation is inside the window, one is three days old. 24 h must report exactly
ONE, all-history exactly TWO. Swapping the two window values reddens it, which
is what makes it a test of the knob rather than of the tool's exit code.

The assertion count for ``--selftest`` is read from the tool's own ``PASS=``
line, never hardcoded — a hardcoded count goes stale every time a case is added.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-health")

_NOHUP_TASK = "nohup /tmp/x.sh >/tmp/o.log 2>&1 &"


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _nohup_count(result):
    """The NOHUP_SPAWN violation count out of an ``oc-health --json`` run."""
    try:
        doc = json.loads(result.out)
    except ValueError:
        pytest.fail("oc-health --json is not parseable:\n%s" % result.combined[-600:])
    joined = " ".join(f.get("message", "") for f in doc.get("findings", []))
    m = re.search(r"NOHUP_SPAWNx(\d+)", joined)
    return int(m.group(1)) if m else 0


@pytest.fixture
def detached_dir(scratch):
    """Two nohup-violating detached tasks: one inside the 24 h window, one three
    days old. The AGE difference is the whole discriminator."""
    d = scratch.path / "detached"
    d.mkdir()
    now = datetime.now(timezone.utc)
    for name, when in (("wh-old", now - timedelta(days=3)), ("wh-new", now)):
        (d / (name + ".json")).write_text(json.dumps({
            "id": name, "session_id": "s", "task": _NOHUP_TASK,
            "spawned_at": _iso(when)}) + "\n")
    return d


def test_selftest_passes(run_selftest):
    """Hermetic: the tool builds its own fixture state dir, tmp glob, sqlite DB
    and git repos for the reaping cases."""
    res = run_selftest("oc-health", timeout=900)
    assert res.rc == 0, "oc-health --selftest rc=%s\n%s" % (res.rc, res.combined[-1200:])
    m = re.search(r"PASS=(\d+)", res.combined)
    assert m, "selftest printed no PASS= line:\n%s" % res.combined[-400:]
    # The count is READ, never hardcoded: a pinned number goes stale the moment a
    # case is added, and a stale number reads as a regression.
    assert int(m.group(1)) > 0, "selftest reported PASS=0 assertions"


def test_read_only_run_is_rc0_or_rc1(run_tool, state_dir):
    """Read-only: rc 0 (clean) or 1 (findings), never 2/3 on a healthy box."""
    res = run_tool([str(TOOL), "--json"], timeout=600)
    assert res.rc in (0, 1), "read-only: rc=%s (want 0|1)\n%s" % (
        res.rc, res.combined[-600:])
    json.loads(res.out)  # stdout is the whole contract


def test_help_is_rc0(run_tool, state_dir):
    res = run_tool([str(TOOL), "--help"], timeout=120)
    assert res.rc == 0, "--help: rc=%s, want 0" % res.rc
    assert res.out.strip(), "--help wrote nothing to stdout"


def test_watcher_window_discriminates(run_tool, state_dir, detached_dir):
    """24 h audits ONLY in-window tasks; 0 means ALL history.

    One violation is inside the window, one is three days old, so the correct
    answers are 1 and 2 — not "both" and "both", which is what a leg that
    cannot go red reports."""
    def run(window):
        return run_tool(
            [str(TOOL), "--class", "runtime_procs", "--json"], timeout=600,
            env={"OC_HEALTH_DETACHED_DIR": str(detached_dir),
                 "OC_HEALTH_WATCHER_WINDOW_H": str(window)})

    r24 = run(24)
    assert r24.rc in (0, 1), "24h window: rc=%s (want 0|1)" % r24.rc
    assert _nohup_count(r24) == 1, (
        "watcher window 24h counted %d NOHUP_SPAWN, want 1 — the 3-day-old "
        "task must be excluded" % _nohup_count(r24))

    r_all = run(0)
    assert r_all.rc in (0, 1), "all-history: rc=%s (want 0|1)" % r_all.rc
    assert _nohup_count(r_all) == 2, (
        "watcher window 0 counted %d NOHUP_SPAWN, want 2 — 0 must mean all "
        "history" % _nohup_count(r_all))
