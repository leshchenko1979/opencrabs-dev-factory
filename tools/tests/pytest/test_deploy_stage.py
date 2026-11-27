"""Ported: the deploy stage tools — run.sh §23 (oc-build / oc-status), FAST legs.

Each leg here is a REAL process that dies on its own argument validation in a
couple of seconds — no carrier read, no fanout sweep, no network:

* usage rc 1 (no args)
* unknown arg rc 1
* the kill-file brake at 9 (it sits at the TOP of every real-mode arm, and must
  precede carrier resolution — a brake that needs the network is not a brake)
* ``--wait`` validated BEFORE any RED-scan side effect — a bad ``--wait`` must
  die rc 1 having written nothing but the shadow log

The legs that carry real weight are in ``test_e2e_deploy_stage.py``: the
log-hermetic ``oc-build --selftest`` (561 assertions, measured 898 s standalone
on 2026-11-27), the dispatched-sha SWAP-PENDING probe (3.2 s measured) and the
stale-pinned-ref round-trip (11.7 s measured). Only the selftest is genuinely
slow; all three are excluded together because they drive REAL subprocesses and
build real git repos, so their cost tracks machine load rather than the code
under test — under load 16 on 4 cores the same two legs blew past 200 s. Same
reason ``test_e2e_cache.py`` is excluded: a gate that waits 15 minutes for one
assertion is a gate nobody runs.
"""

from __future__ import annotations

import conftest as cf

STATUS = cf.tool_path("oc-status")

# --- oc-status boundary ------------------------------------------------------

def test_status_no_args_is_usage_rc1(run_tool, state_dir):
    res = run_tool([str(STATUS)], timeout=120)
    assert res.rc == 1, "no args: rc=%s, want 1 (usage)" % res.rc

def test_status_unknown_arg_is_rc1(run_tool, state_dir):
    res = run_tool([str(STATUS), "--bogus"], timeout=120)
    assert res.rc == 1, "unknown arg: rc=%s, want 1" % res.rc

def test_status_kill_file_brake_is_rc9(run_tool, state_dir):
    """The brake sits at the top of every real-mode arm.

    It must precede carrier resolution: a brake that needs the network to
    engage is not a brake (see oc-status's own note, #143-bis)."""
    (state_dir / "oc-deploy.kill").write_text("x")
    res = run_tool([str(STATUS), "poll"], timeout=180)
    assert res.rc == 9, "kill file: rc=%s, want 9 (real-mode brake)" % res.rc

def test_status_bad_wait_dies_before_side_effects(run_tool, scratch):
    """Duty-6 lens F task 5: ``--wait`` is validated FIRST, so a bad value must
    not burn a fanout sweep or write state."""
    sd = scratch.path / "wait-state"
    sd.mkdir()
    res = run_tool([str(STATUS), "poll", "--wait", "abc"], timeout=180,
                   env={"OC_DEPLOY_STATE_DIR": str(sd),
                        "OC_DEPLOY_GH": "/bin/false"})
    assert res.rc == 1, "bad --wait: rc=%s, want 1" % res.rc
    left = sorted(p.name for p in sd.iterdir())
    assert left in ([], ["oc-deploy-shadow.log"]), (
        "bad --wait wrote state before validating: %s" % left)
