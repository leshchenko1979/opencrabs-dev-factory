"""Ported: oc-branch-sweep — run.sh §30, including the #525 journal leg.

#525 is a SILENT LOSS bug: ``oc_log_extra`` writes a FIXED key, so the
per-branch call that used to sit inside the delete loop overwrote the previous
entry — a two-branch sweep journaled ONE tip and read as complete. The leg
therefore reads the journal back and requires BOTH tips.

Two controls keep it honest:

* the tool is invoked with ``OC_TOOLS_NOLOG`` UNSET (the battery exports it as
  ``1`` globally, which would suppress the journal and let the assertion pass on
  an empty string);
* a control asserts both branches are really GONE, so the two legs above test
  the journal rather than a sweep that deleted nothing.
"""

from __future__ import annotations

import json

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-branch-sweep")


def test_no_repo_is_usage_rc2(run_tool, state_dir):
    res = run_tool([str(TOOL)], timeout=120)
    assert res.rc == 2, "no --repo: rc=%s, want 2 (usage)" % res.rc


@pytest.fixture
def merged_repo(git_repo):
    """A repo with TWO merged, deletable branches whose full heads we capture
    BEFORE the sweep removes them."""
    repo = git_repo()
    g = repo.git
    base = g("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    heads = {}
    for name in ("bs-one", "bs-two"):
        g("checkout", "-qb", name)
        (repo / name).write_text(name + "\n")
        g("add", name)
        g("commit", "-q", "-m", name)
        heads[name] = g("rev-parse", name).stdout.strip()
        g("checkout", "-q", base)
        g("merge", "-q", "--no-ff", "-m", "merge " + name, name)
    return repo, heads


def test_journal_names_every_deleted_tip(run_tool, scratch, merged_repo):
    """#525: both tips present, in order, as PREFIXES of the real heads."""
    repo, heads = merged_repo
    log = scratch.path / "bs-tools.log"

    # OC_TOOLS_NOLOG must be UNSET: run.sh exports it as 1 globally, and with it
    # set the journal is empty and this leg passes vacuously.
    res = run_tool([str(TOOL), "--repo", str(repo)], timeout=180,
                   env={"OC_TOOLS_NOLOG": "", "OC_TOOLS_LOG": str(log),
                        "OC_ACTOR": "test-runner"})
    # rc 1 = "deletions happened" (0 nothing-deleted / 1 deletions / 2 usage /
    # 3 git-fail). run.sh asserted nothing here; pinning 1 also proves the sweep
    # actually took the delete path.
    assert res.rc == 1, "sweep: rc=%s, want 1 (deletions)\n%s" % (
        res.rc, res.combined[-600:])

    assert log.exists(), "no tools log written — the journal is EMPTY (#525)"
    rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    entries = [r["extra"]["branch-delete"] for r in rows
               if r.get("tool") == "oc-branch-sweep"
               and "branch-delete" in (r.get("extra") or {})]
    assert entries, "no branch-delete extra journaled (#525)"

    # A single overwritten entry is the regression: the tool used to write ONE
    # key, so a two-branch sweep left one tip and read as complete.
    extra = entries[-1]
    parts = extra.split(",")
    assert len(parts) == 2, \
        "journaled ONE tip for a two-branch sweep (#525): %r" % extra

    first, last = parts[0], parts[1]
    assert first.split("@")[0] == "bs-one", "first journal entry: %r" % first
    assert last.split("@")[0] == "bs-two", "last journal entry: %r" % last
    # The journal records %(objectname:short), so assert a PREFIX rather than
    # pinning an abbreviation length that git may change.
    assert heads["bs-one"].startswith(first.split("@")[1]), \
        "first tip %r is not bs-one's head %s" % (first, heads["bs-one"])
    assert heads["bs-two"].startswith(last.split("@")[1]), \
        "last tip %r is not bs-two's head %s" % (last, heads["bs-two"])

    # CONTROL: the branches are really gone, so the legs above test the journal
    # and not a sweep that deleted nothing.
    still = repo.git("branch", "--list", "bs-one", "bs-two").stdout.strip()
    assert not still, "CONTROL DEAD (#525): sweep deleted nothing (%r)" % still
