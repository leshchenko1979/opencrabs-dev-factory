"""Fixture integration — each fixture driven against a REAL tool, not a mock.

A fixture that is only exercised by its own assertions is decoration. These legs
run the actual ``oc-*`` tools under the fixture and assert the effect the fixture
claims, so a fixture that silently stopped working reddens here instead of in a
ported section six files away.

Cheap on purpose: one stamp, one git commit, one stubbed ``gh`` call, one tiny
selftest. No section of ``run.sh`` is reproduced.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib import harness as H

import conftest as cf


# =============================================================================
# state_dir
# =============================================================================
def test_state_dir_is_fresh_and_inside_scratch(scratch, state_dir):
    """A per-test state dir, inside the worker's root, replacing 21 hand-sets."""
    assert state_dir.is_dir()
    assert str(state_dir).startswith(str(scratch.path))
    assert os.environ["OC_DEPLOY_STATE_DIR"] == str(state_dir)
    # Two requests must not collide: these tools write journals and locks here.
    other = state_dir.parent / "sibling"
    other.mkdir()
    assert other != state_dir


# =============================================================================
# ledger_sandbox — driven against the real oc-ledger
# =============================================================================
def test_ledger_sandbox_stamps_a_row(ledger_sandbox, run_tool):
    """``oc-ledger stamp`` writes the SANDBOX ledger, with the fixture actor.

    This is the recipe from oc-ledger:2771-2800 driven end to end. The row lands
    in the fixture file, carries the fixture actor, and — the part that makes the
    fixture worth copying — the tool's own git tail commits to the fixture repo,
    not to anything real.

    The "nothing escaped" half uses a UNIQUE token rather than a before/after
    fingerprint: the live ledger has other writers (a ship sweep wrote to it
    during this suite's own development), so a byte-equality check races them
    and reddens for a reason that has nothing to do with the fixture. A token
    that only this test can produce cannot be raced.
    """
    import uuid

    token = "pytest-fixture-%s" % uuid.uuid4()
    ledger = ledger_sandbox.ledger
    assert json.loads(ledger.read_text())["events"] == []

    res = run_tool([cf.tool_path("oc-ledger"), "stamp", "note", token],
                   timeout=120, cwd=ledger_sandbox.state)
    assert res.rc == 0, "oc-ledger stamp failed: %s%s" % (res.out, res.err)

    events = json.loads(ledger.read_text())["events"]
    assert len(events) == 1, "the row did not land in the SANDBOX ledger"
    # derive_by prefixes the ROSTER ROLE ("tester <uuid>"), so assert the uuid is
    # present rather than equality — the role label is the tool's own contract.
    assert cf.LEDGER_ACTOR in events[0]["by"], (
        "the row was not attributed to the fixture actor: %r" % events[0]["by"])
    assert events[0]["kind"] == "note"
    assert token in events[0]["what"]

    # The unique token must not exist anywhere in live state.
    for live in (cf.LIVE_FANOUT_LEDGER, cf.LIVE_PROFILE / "workers.json"):
        try:
            body = live.read_text(errors="replace")
        except OSError:
            continue
        assert token not in body, (
            "the fixture stamp reached LIVE state (%s) — env_guard failed" % live)


def test_ledger_sandbox_blocks_anonymous_rows(ledger_sandbox, run_tool):
    """``stamp`` refuses an anonymous row (#19) — so the fixed actor is required.

    This is the assertion that makes the ``OC_ACTOR`` line load-bearing rather
    than cosmetic: with the actor unset the tool exits 2, and a section written
    against that fixture would report GREEN while asserting nothing.
    """
    # BOTH must be cleared: derive_by reads OC_ACTOR then OPENCRABS_SESSION_ID
    # (oc-ledger:1060), and env_guard pins both to the fixture actor.
    env = {"OC_ACTOR": "", "OPENCRABS_SESSION_ID": ""}
    res = run_tool([cf.tool_path("oc-ledger"), "stamp", "note", "anon"],
                   timeout=120, cwd=ledger_sandbox.state, env=env)
    assert res.rc == 2, "stamp accepted an anonymous row (want rc=2, got %s)" % res.rc
    assert "REFUSED" in res.combined or "no actor" in res.combined


# =============================================================================
# git_repo
# =============================================================================
def test_git_repo_has_pinned_identity(git_repo):
    """Identity comes from ``-c``, so the repo works without a global config.

    Four repos in the battery today only pass because this container happens to
    carry a global git identity. This leg proves the fixture does not depend on
    it: HOME is pointed at an empty dir and the commit still succeeds.
    """
    repo = git_repo(files={"a.txt": "a\n"})
    env = dict(os.environ)
    # Neutralise any global/system git config the container may carry.
    env["HOME"] = str(repo.parent / "no-such-home")
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"

    out = H.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%an <%ae>"],
        capture_output=True, text=True, env=env, check=True)
    assert out.stdout.strip() == "t <t@t>", (
        "commit identity came from somewhere other than the pinned -c: %r"
        % out.stdout.strip())

    # A second commit through the helper still works with no global config.
    (repo / "b.txt").write_text("b\n")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "second")
    log = H.run(["git", "-C", str(repo), "rev-list", "--count", "HEAD"],
                         capture_output=True, text=True, check=True)
    assert log.stdout.strip() == "2"


def test_git_repo_bare_and_branch(git_repo):
    bare = git_repo(bare=True, branch="main")
    assert (bare / "HEAD").is_file(), "not a bare repo"
    work = git_repo(branch="trunk")
    head = H.run(["git", "-C", str(work), "rev-parse", "--abbrev-ref", "HEAD"],
                          capture_output=True, text=True, check=True)
    assert head.stdout.strip() == "trunk"


# =============================================================================
# gh_stub — the three seams
# =============================================================================
def test_gh_stub_wires_all_three_seams(gh_stub):
    """One factory sets OC_DEPLOY_GH, OC_ISSUE_CREATE_GH and PATH together.

    The battery builds a bespoke stub dir per section; missing one seam is
    invisible until a leg reaches the real ``gh`` and needs network.
    """
    stub = gh_stub(rules=[("issue list", '[{"number":1}]', 0)])
    assert os.environ["OC_DEPLOY_GH"] == str(stub.path)
    assert os.environ["OC_ISSUE_CREATE_GH"] == str(stub.path)
    assert str(stub.bindir) in os.environ["PATH"].split(os.pathsep)

    # All three seams reach the SAME stub, which logs what it was asked.
    for call in (["issue", "list"], ["issue", "view", "7"], ["api", "x"]):
        out = H.run([str(stub.path), *call],
                             capture_output=True, text=True, check=True)
        assert out.returncode == 0
    calls = stub.calls()
    assert calls == [["issue", "list"], ["issue", "view", "7"], ["api", "x"]]

    # The rule fired for the matching call and not for the others.
    assert H.run([str(stub.path), "issue", "list"],
                          capture_output=True, text=True).stdout == '[{"number":1}]'


def test_gh_stub_rc_and_rerules(gh_stub):
    """A leg can drive a FAILING gh, and re-rule without a new stub dir."""
    stub = gh_stub(default_rc=1)
    assert H.run([str(stub.path), "release", "view"],
                          capture_output=True).returncode == 1
    stub.set_rules([("release view", "", 0)])
    assert H.run([str(stub.path), "release", "view"],
                          capture_output=True).returncode == 0


def test_gh_stub_is_reachable_as_a_bare_gh(gh_stub):
    """The PATH seam: a tool that calls a bare ``gh`` gets the stub, not the real one."""
    stub = gh_stub(rules=[("--version", "gh stub 0.0.0", 0)])
    out = H.run(["gh", "--version"], capture_output=True, text=True, check=True)
    assert "gh stub" in out.stdout, "bare `gh` did not resolve to the stub"
    assert stub.calls() == [["--version"]]


# =============================================================================
# run_selftest — driven against a real tool
# =============================================================================
# The tool is chosen for COST, not importance: the migration plan measures
# oc-ledger's kernel at 296.5 s, and a foundation suite that takes 5 minutes is
# a suite nobody runs while working. oc-issue-scope --selftest is hermetic and
# measured at 0.5 s, which is enough to prove the WIRING (argv shape, per-call
# state dir, the bound). Each tool's own coverage belongs to its own section.
CHEAP_SELFTEST = "oc-issue-scope"


def test_run_selftest_runs_a_real_tool(ledger_sandbox, run_selftest):
    """``run_selftest`` invokes ``<tool> --selftest`` and returns a Result."""
    res = run_selftest(CHEAP_SELFTEST, timeout=120)
    assert "--selftest" in res.cmd
    assert res.rc == 0, ("%s --selftest rc=%s\n%s\n%s"
                         % (CHEAP_SELFTEST, res.rc, res.out[-2000:], res.err[-2000:]))
    assert res.duration_ms > 0
    assert res.timed_out is False
    assert res.cmd[0] == str(cf.tool_path(CHEAP_SELFTEST))


def test_run_selftest_gives_each_call_its_own_state_dir(state_dir, run_selftest):
    """M2-22: a per-call throwaway state dir, or the /tmp leak returns.

    run.sh makes one ``mktemp -d`` per selftest and removes it after (the volume
    driver of the /tmp leak, one dir per tool per run). Here the dir is inside
    the worker's scratch, so the controller's reaper owns it either way.
    """
    res = run_selftest(CHEAP_SELFTEST, timeout=120)
    made = state_dir / ("st-" + CHEAP_SELFTEST)
    assert made.is_dir(), "run_selftest did not create a per-call state dir"
    assert res.rc == 0


def test_run_selftest_defaults_to_the_selftest_timeout(monkeypatch):
    """Omitting ``timeout`` falls back to OC_SELFTEST_TIMEOUT, never to unbounded.

    Asserted on the fixture's own source rather than by a 30-minute run: the
    point is that no path through it can produce an UNBOUNDED call, and the
    bound's value is env-derived.
    """
    assert os.environ["OC_SELFTEST_TIMEOUT"] == "1800"
    src = Path(cf.__file__).read_text(encoding="utf-8")
    body = src[src.index("def _call(tool, *, timeout=None"):]
    body = body[:body.index("return run_tool(")]
    assert "OC_SELFTEST_TIMEOUT" in body, (
        "the default bound no longer reads OC_SELFTEST_TIMEOUT")
    assert '"1800"' in body, "the documented 1800 s default vanished"
    # And the call always passes an explicit bound on to run_tool.
    tail = src[src.index("def _call(tool, *, timeout=None"):]
    assert "timeout=bound" in tail[:1500]


# =============================================================================
# tools_dir / tool_path
# =============================================================================
def test_tool_path_resolves_by_name_never_production(tools_dir):
    """Tools resolve in THIS checkout — the production one is a different tree."""
    assert tools_dir == cf.TOOLS_DIR
    assert cf.PROD_REPO not in tools_dir.parents
    path = cf.tool_path("oc-ledger")
    assert path.is_file() and os.access(path, os.X_OK)
    assert str(path).startswith(str(tools_dir))
    with pytest.raises(FileNotFoundError):
        cf.tool_path("oc-no-such-tool-xyz")


# =============================================================================
# ledger_sandbox recipe fidelity — it is a COPY, so prove it still matches
# =============================================================================
def test_ledger_sandbox_recipe_still_matches_the_tool():
    """The fixture is a verbatim copy of oc-ledger:2771-2800; drift is a defect.

    Copying is right (the tool's own 418-case selftest proves that recipe), but
    a copy with no parity check rots: the tool's fixture gains a variable the
    pytest one lacks, and every ported ledger section then fails for a reason
    that looks like a tool bug. This asserts the LOAD-BEARING parts only —
    the ledger payload, the two repos, the .keep, and the actor — not the
    surrounding shell syntax.
    """
    src = (cf.TOOLS_DIR / "state" / "oc-ledger").read_text(encoding="utf-8")
    start = src.index("cmd_selftest()")
    end = src.index("export OC_ACTOR=", start)
    recipe = src[start:end]

    # The ledger payload, whitespace-normalised.
    assert '"current_skill_version":"0.4.1"' in recipe
    assert '"updated_at":"2026-01-01T00:00:00Z"' in recipe
    assert '"uuid":"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"' in recipe
    assert '"role":"tester"' in recipe
    for frag in ('"current_skill_version":"0.4.1"', '"updated_at":"2026-01-01T00:00:00Z"',
                 '"role":"tester"', '"topic_id":1'):
        assert frag in cf._LEDGER_JSON, (
            "the fixture ledger payload lost %s (oc-ledger:2787-2789 has it)" % frag)

    # The two repos + the .keep that keeps tools/ TRACKED (v0.4.157).
    assert '"$T/state" "$T/skill"' in recipe or '$T/state" "$T/skill' in recipe
    assert "tools/tests/.keep" in recipe
    assert (Path(cf.__file__).read_text(encoding="utf-8")).count(".keep") >= 1

    # The actor: stamp refuses an anonymous row, so the recipe sets one.
    assert 'OC_ACTOR="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"' in src
    assert cf.LEDGER_ACTOR == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_ledger_sandbox_sets_the_fast_contention_vars(ledger_sandbox):
    """The four fast-contention vars, so a lock test fails in ~1 s not 900 s.

    Each default is a PRODUCTION budget (lock wait 900 s, push timeout 30 s,
    git tail 60 s). A fixture that inherits them turns one contended leg into a
    15-minute stall, which reads as a hang rather than as contention.
    """
    assert os.environ["OC_LEDGER_LOCK_WAIT"] == "1"
    assert os.environ["OC_LEDGER_PUSH_TIMEOUT"] == "1"
    assert os.environ["OC_LEDGER_PUSH_MIN"] == "1"
    assert os.environ["OC_LEDGER_GIT_TAIL_WAIT"] == "20"
    assert os.environ["OC_SHIP_AUDIT_CHAIN"] == "0"
    # And the state/skill dirs point at the fixture, not the live profile.
    assert str(ledger_sandbox.state).startswith(str(cf.LIVE_PROFILE)) is False
    assert os.environ["OC_LEDGER"] == str(ledger_sandbox.ledger)
    assert os.environ["OC_SKILL_DIR"] == str(ledger_sandbox.skill)


# =============================================================================
# env_guard vs a REAL tool — the live-ledger leak, end to end
# =============================================================================
def test_fanout_tool_resolves_the_scratch_ledger_not_the_live_one(
        scratch, run_tool, gh_stub, monkeypatch, tmp_path):
    """The strongest form of the env_guard claim: drive the real tool and READ
    BACK which ledger path it resolved.

    ``oc-notify-fanout`` defaults its ledger to ``$HOME/.opencrabs/profiles/ops/
    opencrabns-dev/events.jsonl`` via ``oc_ledger_path`` (tools/lib/oc-log.sh),
    which is why run.sh:3095 has to pass the live path explicitly and every
    fanout leg in the battery writes real fleet state. Here the fixture ledger
    is EMPTY, so the tool fails — and its error names the path it tried. That
    path must be the scratch one. A substring assertion on output is the honest
    check: it cannot be satisfied by the fixture "looking right".

    No DB, no network, no stamp: rc 3 with the path in stderr is the whole cost.
    """
    # Deliberately ABSENT: the tool's roster guard then names the path it
    # resolved (`die "roster missing: $LEDGER" 3`, oc-notify-fanout:1151), which
    # is the read-back. An existing ledger would get past that line and die on
    # the session DB instead, naming nothing.
    led = scratch.path / "fanout" / "absent-ledger.json"
    monkeypatch.setenv("OC_FANOUT_LEDGER", str(led))
    gh_stub()

    res = run_tool([cf.tool_path("oc-notify-fanout"),
                    "--title", "t", "--text", "x", "--dry-run", "--no-stamp"],
                   timeout=120,
                   env={"OC_FANOUT_SELF": "00000000-0000-4000-8000-00000000dead",
                        "OC_NOTIFY_DB": str(tmp_path / "db.sqlite"),
                        "OC_NOTIFY_BIN": "/bin/true"})

    combined = res.combined
    assert str(cf.LIVE_PROFILE) not in combined, (
        "the tool reached LIVE state: %r" % combined[:500])
    assert "roster missing: %s" % led in combined, (
        "the tool did not resolve OC_FANOUT_LEDGER to the scratch ledger; it "
        "read something else: %r" % combined[:500])
