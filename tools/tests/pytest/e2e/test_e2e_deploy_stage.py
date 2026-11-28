"""Ported: the deploy stage tools — run.sh §23 (oc-build / oc-status), E2E legs.

These are the legs where a GREEN run is NOT a completed deploy, plus the one
hermeticity assertion that costs a full selftest. All three drive REAL
subprocesses and build real git repos, so they follow the ``test_e2e_cache.py``
precedent: a ``test_e2e_`` filename AND ``@pytest.mark.slow``, so the fast gate
can drop them with either ``--ignore=tools/tests/pytest/e2e/test_e2e_deploy_stage.py``
or ``-m "not slow"``. Of the three, only the selftest is slow — 898 s against
3.2 s and 11.7 s for the other two, which are excluded for their real-subprocess
surface, not their wall time.

* **log hermeticity (M2-21)**: ``oc-build --selftest`` must write ZERO rows to
  ``OC_TOOLS_LOG``. The suite is 561 assertions, 0 fail, and takes ~7m45s wall
  under load on 4 cores. This is the leg that makes the section look hung — it
  is SLOW, not stuck.
* **ship-pending (n=2003 family)**: ``poll --sha S`` with S already dispatched
  must never report "nothing new" — a dispatched-sha GREEN means SWAP PENDING,
  and rc 5 ("already deployed") is the wrong answer that reads as a no-op.
  Costs ~2.3 s.
* **stale pinned ref**: after a diverge/restore round-trip the plan must report
  ``FF ok`` again. The old code resurrected its own stale ref and refused rc 2.
  Costs ~4.9 s.

The cheap boundary legs (usage rc 1, unknown arg, the kill-file brake at 9, bad
``--wait``) stay in ``test_deploy_stage.py``, where they finish in seconds.
"""

from __future__ import annotations

import pytest

import conftest as cf

BUILD = cf.tool_path("oc-build")
STATUS = cf.tool_path("oc-status")

PEN_SHA = "0123456789abcdef0123456789abcdef01234567"

# --- log hermeticity ---------------------------------------------------------

@pytest.mark.slow
@pytest.mark.timeout(1800)
def test_build_selftest_is_log_hermetic(run_tool, scratch):
    """M2-21: the selftest must write ZERO unified-log rows.

    Pre-fix it wrote 93 rows of fixture dispatches, and oc-audit-ship read six
    of them back as ORPHANED and rc=1'd a gate fronting ``oc-ledger
    commit-pending``. ``OC_TOOLS_NOLOG=0`` is REQUIRED: the battery exports it
    as 1 globally, which would make this assertion vacuous."""
    log = scratch.path / "selftest.log"
    sd = scratch.path / "build-state"
    sd.mkdir()
    res = run_tool([str(BUILD), "--selftest"], timeout=900,
                   env={"OC_TOOLS_NOLOG": "0", "OC_TOOLS_LOG": str(log),
                        "OC_DEPLOY_STATE_DIR": str(sd)})
    assert res.rc == 0, "oc-build --selftest rc=%s\n%s" % (res.rc, res.combined[-1200:])
    leaked = log.read_text().splitlines() if log.exists() else []
    assert not leaked, (
        "selftest leaked %d row(s) into OC_TOOLS_LOG (M2-21): %r"
        % (len(leaked), leaked[:3]))

# --- dispatched-sha GREEN is SWAP PENDING, never "nothing new" ---------------

@pytest.fixture
def pending_state(state_dir):
    """State dir where ``deployed.sha`` is BEHIND the only decodable green run:
    the dispatched sha is GREEN, the deploy has not swapped."""
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "deployed.sha").write_text(PEN_SHA + "\n")
    (state_dir / "deployed.meta.json").write_text(
        '{"sha":"%s","features":"telegram","ts":"2026-09-08T00:00:00Z"}\n' % PEN_SHA)
    return state_dir

@pytest.mark.slow
def test_dispatched_sha_green_never_reads_as_already_deployed(
        run_tool, pending_state, gh_stub):
    """n=2003 family: rc 5 + "nothing new" here would silently skip the swap."""
    gh = gh_stub(rules=[
        ("/runs?status=success", '{"workflow_runs":[{"id":111}]}', 0),
        ("/runs/111/jobs",
         '{"jobs":[{"name":"build (%s, telegram)"},'
         '{"name":"gates (%s)"}]}' % (PEN_SHA, PEN_SHA), 0),
    ])
    res = run_tool(
        [str(STATUS), "poll", "--wait", "2", "--sha", PEN_SHA, "--execute",
         "--features", "telegram"], timeout=300,
        env={"OC_DEPLOY_STATE_DIR": str(pending_state),
             "OC_DEPLOY_GH": str(gh.path),
             "OC_DEPLOY_NOFANOUT": "1", "OC_DEPLOY_POLL_INTERVAL": "1"})

    assert res.rc != 5, (
        "poll --sha on a dispatched-sha GREEN exited 5 (\"already deployed\") — "
        "that is SWAP PENDING, not a no-op:\n%s" % res.combined[-800:])
    shadow = pending_state / "oc-deploy-shadow.log"
    body = shadow.read_text() if shadow.exists() else ""
    assert "nothing new" not in body, (
        "poll --sha pending journaled 'nothing new' — the swap was silently "
        "skipped:\n%s" % body[-600:])

# --- stale pinned ref --------------------------------------------------------

@pytest.mark.slow
def test_stale_pinned_ref_reports_ff_ok(run_tool, scratch):
    """Diverge the remote, ship (pinning a now-stale tip), restore the remote,
    ship again: the plan must read FF ok, not refuse rc 2 on its own stale ref."""
    d = scratch.path / "ship"
    state = d / "state"
    state.mkdir(parents=True)
    (state / "tools").mkdir()
    val = state / "tools" / "val"
    val.write_text("#!/usr/bin/env bash\nexit 0\n")
    val.chmod(0o755)
    ghbin = d / "gh"
    ghbin.write_text("#!/usr/bin/env bash\nexit 0\n")
    ghbin.chmod(0o755)

    remote = d / "remote.git"
    repo = d / "repo"
    g = lambda *a, cwd=repo: cf._run(["git", *a], timeout=60, cwd=cwd)

    assert g("init", "-q", "--bare", "-b", "main", str(remote), cwd=d).rc == 0
    assert g("init", "-q", "-b", "main", str(repo), cwd=d).rc == 0
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    g("config", "commit.gpgsign", "false")
    for name in ("f1", "f2"):
        (repo / name).write_text(name + "\n")
        g("add", name)
        g("commit", "-q", "-m", name)
    sha2 = g("rev-parse", "HEAD").out.strip()

    assert g("push", "-q", str(remote), "HEAD~1:refs/heads/main").rc == 0

    env = {"OC_DEPLOY_STATE_DIR": str(state), "OC_DEPLOY_REMOTE": str(remote),
           "OC_DEPLOY_VALIDATE": str(val), "OC_DEPLOY_GH": str(ghbin)}

    def ship():
        return run_tool([str(BUILD), "ship", "--sha", sha2, "--features", "telegram"],
                        timeout=300, cwd=repo, env=env)

    assert ship().rc == 0, "first ship (plan mode) failed"

    # diverge the remote, ship again so the tool pins the diverged tip
    g("checkout", "-qb", "div", "HEAD~1")
    (repo / "f3").write_text("div\n")
    g("add", "f3")
    g("commit", "-q", "-m", "div")
    assert g("push", "-q", "-f", str(remote), "HEAD:refs/heads/main").rc == 0
    ship()

    # restore the remote to the ancestor the sha fast-forwards from
    g("checkout", "-q", "-B", "main", sha2)
    assert g("push", "-q", "-f", str(remote), "main~1:refs/heads/main").rc == 0

    res = ship()
    assert res.rc == 0, (
        "stale pinned ref regression: rc=%s, want 0 with 'FF ok'\n%s"
        % (res.rc, res.combined[-800:]))
    assert "FF ok" in res.combined, (
        "plan did not report 'FF ok' after the diverge/restore round-trip:\n%s"
        % res.combined[-600:])
