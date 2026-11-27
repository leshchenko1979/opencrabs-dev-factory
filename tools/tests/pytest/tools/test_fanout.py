"""Ported: `oc-fanout` + attribution — run.sh §22 (issue #24).

Two legs, and they answer different questions. GREEN asks *who contributed to
this build*, RED asks *who broke it* — and the failure that makes the pair worth
testing is that a GREEN run must never wake a lane twice, while a RED run must
never blame a lane that did not touch the broken file.

Four claims the shell section makes and this port keeps:

1. ``notified`` / ``skipped`` are SEPARATE counters. A dead uuid is a fact about
   the LANE (the transport refused it), so it must be skipped and journaled —
   never retried, never resurrected (#17 class).
2. Re-running the same ``--run`` is a NO-OP. ``fanout.state`` is the memory: a
   run that re-notifies on every sweep double-cards every lane, which is the
   measured 13:21Z TOCTOU the ``.lock`` file exists to prevent.
3. A RED run blames the CULPRIT — the session named in the commit that touched
   the annotated path — not every contributor in the range.
4. ``fanout`` with no ``--run`` is usage rc 2.

HERMETICITY is the whole difficulty here, and it is why this port passes a
session store instead of inheriting one. The fan-out resolves a commit trailer
to a LANE through ``OC_SESSIONS_DB``; with that unset it reads the LIVE ops
store, and the section then fails BOTH ways — it reddens on a box whose profile
differs, and it PASSES on a box whose DB happens to hold these fixture uuids.
The store is written per test into ``state_dir`` and passed INLINE on every
invocation, never exported: the fixture that wrote it is the only thing that
may delete it.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-fanout")

# The lane uuids the shell section uses. aaaa contributes to the GREEN build,
# bbbb is dead (the notify shim refuses it), cccc authors the RED culprit.
LANE_A = "aaaaaaaa-1111-2222-3333-444444444444"
LANE_B = "bbbbbbbb-1111-2222-3333-444444444444"
LANE_C = "cccccccc-1111-2222-3333-444444444444"
LANE_9 = "99999999-8888-7777-6666-555555555555"

GREEN_SHA = "c" * 40

@pytest.fixture
def fanout(scratch, state_dir):
    """A fan-out sandbox: session store, gh stub rules, attrib + notify shims.

    Returns a Node carrying every path a leg needs. Nothing here is exported —
    the legs pass each path inline, so the sandbox's lifetime is exactly the
    legs that use it (run.sh:§22 makes the same point about its own store).
    """
    sd = state_dir
    (sd / "tools").mkdir(parents=True, exist_ok=True)

    # -- the session store the child->lane resolver reads (#192) --------------
    # Built with python's own sqlite3 module, the same reader `lib/oc_sqlite`
    # falls back to: the box has the CLI today, but the fixture must not depend
    # on a host binary a lane may not have.
    sdb = sd / "sessions.db"
    con = sqlite3.connect(str(sdb))
    con.executescript("""
CREATE TABLE sessions (id TEXT PRIMARY KEY NOT NULL, title TEXT, model TEXT,
                       created_at INTEGER NOT NULL, parent_session_id TEXT);
INSERT INTO sessions VALUES ('%s','lane fixture A','m',0,NULL);
INSERT INTO sessions VALUES ('%s','lane fixture B','m',0,NULL);
INSERT INTO sessions VALUES ('%s','lane fixture C','m',0,NULL);
INSERT INTO sessions VALUES ('%s','lane fixture 9','m',0,NULL);
""" % (LANE_A, LANE_B, LANE_C, LANE_9))
    con.commit()
    con.close()

    # -- the deploy markers a fan-out reads ----------------------------------
    (sd / "deployed.sha").write_text(GREEN_SHA + "\n")
    (sd / "deployed.meta.json").write_text(json.dumps(
        {"prev_sha": "0" * 40, "features": "telegram"}))

    # -- oc-attrib shim: the contributors of the deployed range ---------------
    # Two sessions, one of them dead. Passed as OC_DEPLOY_ATTRIB, so the
    # fan-out's own call shape (`--repo ... --contributors --first-parent`) is
    # NOT asserted here — test_attrib.py owns that contract.
    attrib = sd / "tools" / "attrib-stub"
    attrib.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\t#77\\tabc1234\\n'\n"
        "printf '%s\\t#78\\tdef5678\\n'\n" % (LANE_A, LANE_B))
    attrib.chmod(0o755)

    # -- notify shim: records the call, refuses the dead lane (rc 2) ----------
    notify = sd / "notify"
    notify_log = sd / "notify.log"
    notify.write_text(
        "#!/usr/bin/env bash\n"
        "case \"$*\" in *%s*) exit 2 ;; esac\n"
        "printf '%%s\\n' \"$*\" >> '%s'\n"
        "exit 0\n" % (LANE_B, notify_log))
    notify.chmod(0o755)
    notify_log.write_text("")

    return cf.Node(sd, sdb=sdb, attrib=attrib, notify=notify,
                   notify_log=notify_log,
                   state=sd / "fanout.state",
                   journal_dir=sd / "oc-deploy" / "journal")

def _env(fanout, **extra):
    """The fan-out's env: every path inline, nothing inherited from the fleet."""
    env = {
        "OC_DEPLOY_ATTRIB": str(fanout.attrib),
        "OC_DEPLOY_NOTIFY": str(fanout.notify),
        "OC_SESSIONS_DB": str(fanout.sdb),
        # The RED leg's blame path walks a fixture repo; the GREEN leg never
        # touches the network because the gh stub answers both run reads.
        "OC_DEPLOY_NOFANOUT": "1",
        # A transient failure must not SLEEP inside a test (#623's budget).
        "OC_DEPLOY_NOTIFY_RETRY_BUDGET": "0",
    }
    env.update(extra)
    return env

def _gh(gh_stub, run_status, jobs, conclusion):
    """One stub serving both reads: the run, then its jobs list."""
    return gh_stub(rules=[
        ("actions/runs/%s/jobs" % run_status, json.dumps({"jobs": jobs}), 0),
        ("actions/runs/%s" % run_status,
         json.dumps({"status": "completed", "conclusion": conclusion}), 0),
    ])

def test_green_notifies_contributors_and_skips_the_dead_lane(fanout, gh_stub, run_tool):
    """GREEN: one notify per contributing session, the dead one SKIPPED.

    The counter split is the assertion: ``skipped=1`` must be a transport
    verdict, not a silent drop folded into ``notified``.
    """
    _gh(gh_stub, 222,
        [{"name": "ORDER gates (%s)" % GREEN_SHA, "conclusion": "success"},
         {"name": "Linux amd64 (%s, telegram)" % GREEN_SHA,
          "conclusion": "success"}],
        "success")
    res = run_tool([str(TOOL), "fanout", "--run", "222"],
                   timeout=180, env=_env(fanout))
    assert res.rc == 0, "GREEN fan-out rc=%s\n%s" % (res.rc, res.combined[-900:])
    assert "notified=1 skipped=1" in res.combined, \
        "GREEN counters wrong (want notified=1 skipped=1):\n%s" % res.combined[-900:]

    log = fanout.notify_log.read_text()
    assert LANE_A in log, "the live contributor was never woken:\n%s" % log
    assert LANE_B not in log, \
        "the dead uuid reached the shim — a refusal must not be logged as a send"

    state = json.loads(fanout.state.read_text())
    assert state["runs"]["222"], "fan-out state did not mark run 222"

    journalled = "".join(p.read_text() for p in fanout.journal_dir.glob("fanout-222-*.jsonl"))
    assert '"reason":"dead"' in journalled, \
        "the dead-lane skip was not journaled — the refusal left no evidence"

def test_rerun_is_a_noop(fanout, gh_stub, run_tool):
    """Idempotence: the SAME --run twice must not re-notify.

    ``fanout.state`` is the memory. Without it every sweep double-cards every
    lane — the failure the per-run lock exists to prevent, one layer down.
    """
    _gh(gh_stub, 222,
        [{"name": "Linux amd64 (%s, telegram)" % GREEN_SHA,
          "conclusion": "success"}],
        "success")
    first = run_tool([str(TOOL), "fanout", "--run", "222"],
                     timeout=180, env=_env(fanout))
    assert first.rc == 0, "first run rc=%s\n%s" % (first.rc, first.combined[-600:])
    sent_once = fanout.notify_log.read_text()

    second = run_tool([str(TOOL), "fanout", "--run", "222"],
                      timeout=180, env=_env(fanout))
    assert second.rc == 0, "rerun rc=%s\n%s" % (second.rc, second.combined[-600:])
    assert "reason=done" in second.combined, \
        "rerun did not report reason=done:\n%s" % second.combined[-600:]
    assert fanout.notify_log.read_text() == sent_once, \
        "the rerun SENT AGAIN — idempotence broken (state=%s)" % fanout.state

def test_fanout_without_run_is_usage_rc2(fanout, run_tool):
    res = run_tool([str(TOOL), "fanout"], timeout=120, env=_env(fanout))
    assert res.rc == 2, "fanout without --run: rc=%s, want 2 (usage)\n%s" % (
        res.rc, res.combined[-400:])

# =============================================================================
# RED leg — blame attribution
# =============================================================================
@pytest.fixture
def red_repo(scratch, git_repo):
    """A repo whose culprit commit carries LANE_C's trailer, plus the bare
    remote the fan-out fetches the run head from.

    Built on ``git_repo()`` with NO name, per the fixture's own warning: the
    scratch root is session-scoped, so a named repo is reused across tests and
    the second ``git init`` lands in an existing tree.
    """
    bare = git_repo(bare=True)
    work = git_repo(files={"bad.txt": "l1\nl2\nv1\nl4\n"})
    work.git("push", "-q", str(bare), "HEAD")
    head = work.git("rev-parse", "HEAD").stdout.strip()

    # the culprit change: v1 -> v2 on the annotated line
    (work / "bad.txt").write_text("l1\nl2\nv2\nl4\n")
    work.git("add", "bad.txt")
    work.git("commit", "-q", "-m",
             "feat: culprit change\n\nSession-Id: %s" % LANE_C)
    work.git("push", "-q", str(bare), "HEAD")
    culprit = work.git("rev-parse", "HEAD").stdout.strip()
    assert culprit != head
    return cf.Node(work, bare=bare, head=culprit, base=head)

def test_red_blames_the_culprit(fanout, red_repo, gh_stub, run_tool):
    """RED: the annotated path is blamed on the commit that touched it.

    The run's jobs carry NO decodable sha (a RED build never builds one), so the
    only way to attribute is the annotation -> blame walk. ``cccccccc`` must be
    the notified lane, and the attribution must be journaled — a RED fan-out
    that notifies without recording WHY is unauditable.
    """
    (fanout / "red-head").write_text(red_repo.head + "\n")
    gh_stub(rules=[
        ("actions/runs/666/jobs",
         json.dumps({"jobs": [{"name": "Linux amd64 (build)",
                               "conclusion": "failure",
                               "check_run_url":
                                   "https://api.github.com/repos/x/y/check-runs/9001"}]}), 0),
        ("check-runs/9001/annotations",
         json.dumps([{"path": "bad.txt", "start_line": 3}]), 0),
        ("actions/runs/666",
         json.dumps({"status": "completed", "conclusion": "failure",
                     "head_sha": red_repo.head}), 0),
    ])
    res = run_tool([str(TOOL), "fanout", "--run", "666"], timeout=180,
                   cwd=red_repo, env=_env(
                       fanout,
                       OC_DEPLOY_REPO=str(red_repo),
                       OC_DEPLOY_REMOTE=str(red_repo.bare)))
    assert res.rc == 0, "RED fan-out rc=%s\n%s" % (res.rc, res.combined[-1200:])
    assert "notified=1 skipped=0 unowned=0" in res.combined, \
        "RED counters wrong:\n%s" % res.combined[-1200:]

    assert LANE_C in fanout.notify_log.read_text(), \
        "the culprit lane was never notified:\n%s" % fanout.notify_log.read_text()

    lines = [json.loads(l) for l in
             "".join(p.read_text() for p in
                     fanout.journal_dir.glob("fanout-666-*.jsonl")).splitlines()
             if l.strip()]
    attributed = [l for l in lines if l.get("step") == "attributed"]
    assert attributed, "no attributed line in the journal — the blame is unauditable"
    assert any(LANE_C in json.dumps(l) for l in attributed), \
        "the attributed line does not name the culprit: %r" % attributed

    state = json.loads(fanout.state.read_text())
    assert state["runs"]["666"]["notified"] == 1, \
        "RED fan-out state did not mark the notification: %r" % state["runs"]["666"]
