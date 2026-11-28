"""oc-gate — the usage / state-dir legs.

``oc-gate --selftest`` is NOT driven here: ``tools/test_tool_wrappers.py``
already runs it as one parametrised case, and it is the second-slowest selftest
in the fleet (~118 s). Two modules driving the same selftest is a
duplicated 118 s of wall for one extra rc assertion — the blanket owns that
assertion (factory #203). What this module keeps is what the blanket CANNOT
assert:

* the two usage legs, which pin the FULL-sha shape gate — the one thing the
  tool refuses before it touches the network;
* the state-dir containment, which is the leak that forced the shell harness to
  wrap this section in a throwaway dir (goal C).

The state dir matters more here than usual: ``usage()`` writes a retry-storm
counter (``.oc-gate-rc2``) into ``$OC_DEPLOY_STATE_DIR``. ``state_dir`` supplies
it per test, so the counter can neither escape into the fleet nor make the
second usage leg sleep.
"""

from __future__ import annotations

import conftest as cf

TOOL = cf.tool_path("oc-gate")



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

    This is the leak that motivated the shell harness's throwaway dir (goal C).
    Asserting
    the file lands inside ``state_dir`` makes the containment a claim rather
    than a side effect of the wrapper."""
    run_tool([str(TOOL)], timeout=120)
    assert (state_dir / ".oc-gate-rc2").exists(), \
        "rc-2 counter did not land in OC_DEPLOY_STATE_DIR — where did it go?"
