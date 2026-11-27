"""Ported: the deploy stage tools — run.sh §23 (oc-build / oc-status).

The two legs that carry real weight are the ones where a GREEN run is NOT a
completed deploy:

* **ship-pending (n=2003 family)**: ``poll --sha S`` with S already dispatched
  must never report "nothing new" — a dispatched-sha GREEN means SWAP PENDING,
  and rc 5 ("already deployed") is the wrong answer that reads as a no-op.
* **stale pinned ref**: after a diverge/restore round-trip the plan must report
  ``FF ok`` again. The old code resurrected its own stale ref and refused rc 2.

The cheap legs around them pin the boundary: usage rc 1, the kill-file brake at
9 (it sits at the TOP of every real-mode arm), and ``--wait`` validated BEFORE
any RED-scan side effects — a bad ``--wait`` must die rc 1 having written
nothing but the shadow log.
"""

from __future__ import annotations

import os

import pytest

import conftest as cf

BUILD = cf.tool_path("oc-build")
STATUS = cf.tool_path("oc-status")

PEN_SHA = "0123456789abcdef0123456789abcdef01234567"


# --- log hermeticity ---------------------------------------------------------


@pytest.mark.slow
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


# --- oc-status boundary ------------------------------------------------------


def test_status_no_args_is_usage_rc1(run_tool, state_dir):
    res = run_tool([str(STATUS)], timeout=120)
    assert res.rc == 1, "no args: rc=%s, want 1 (usage)" % res.rc


def test_status_unknown_arg_is_rc1(run_tool, state_dir):
    res = run_tool([str(STATUS), "--bogus"], timeout=120)
    assert res.rc == 1, "unknown arg: rc=%s, want 1" % res.rc


def test_status_kill_file_brake_is_rc9(run_tool, state_dir):
    """The brake sits at the top of every real-mode arm."""
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
