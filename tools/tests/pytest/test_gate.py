"""Ported: oc-gate — run.sh §26.

The selftest runs offline (a gh shim is injected by the tool itself), so it is
safe to invoke directly; the two usage legs pin the FULL-sha shape gate, which
is the one thing the tool refuses before it touches the network.

The state dir matters more here than usual: ``usage()`` writes a retry-storm
counter (``.oc-gate-rc2``) into ``$OC_DEPLOY_STATE_DIR``, which is exactly the
leak that forced run.sh to wrap this section in a throwaway dir (goal C,
2026-08-29). ``state_dir`` supplies it per test, so the counter can neither
escape into the fleet nor make the second usage leg sleep.
"""

from __future__ import annotations

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-gate")


def test_selftest_passes(run_selftest):
    """Offline, shim-injected. Generous bound: the gh-shim matrix is the slowest
    selftest in the fleet after oc-ledger."""
    res = run_selftest("oc-gate", timeout=900)
    assert res.rc == 0, "oc-gate --selftest rc=%s\n%s" % (res.rc, res.combined[-1200:])


def test_no_args_is_usage_rc2(run_tool, state_dir):
    res = run_tool([str(TOOL)], timeout=120)
    assert res.rc == 2, "no args: rc=%s, want 2 (usage)" % res.rc
    assert "Usage:" in res.combined, "usage text missing:\n%s" % res.combined[-400:]


def test_short_sha_is_refused_rc2(run_tool, state_dir):
    """The shape gate is FULL 40-hex only: a short sha must die at the boundary,
    never reach a dispatch."""
    res = run_tool([str(TOOL), "abc123"], timeout=120)
    assert res.rc == 2, "short sha: rc=%s, want 2 (FULL-sha shape gate)" % res.rc


def test_rc2_counter_stays_inside_the_state_dir(run_tool, state_dir):
    """The retry-storm counter is written to the STATE DIR, not the fleet.

    This is the leak that motivated run.sh's throwaway dir (goal C). Asserting
    the file lands inside ``state_dir`` makes the containment a claim rather
    than a side effect of the wrapper."""
    run_tool([str(TOOL)], timeout=120)
    assert (state_dir / ".oc-gate-rc2").exists(), \
        "rc-2 counter did not land in OC_DEPLOY_STATE_DIR — where did it go?"
