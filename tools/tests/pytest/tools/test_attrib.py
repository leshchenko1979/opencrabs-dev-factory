"""`oc-attrib` and `oc-attrib #407 novelty filter`.

Both sections build a real git fixture and drive the SHIPPED tool. The #407
fixture is the discriminating one: a twin commit absorbed into the baseline, a
cherry-picked REPLAY of it on the tip (same patch, new sha — what a rebase
produces), a genuinely NOVEL commit, and an EMPTY commit. Without all four the
filter cannot be distinguished from "drop everything" or "drop nothing".
"""

from __future__ import annotations

import pytest

import conftest as cf


@pytest.fixture
def attrib_repo(git_repo):
    """§16 fixture: one trailer'd commit + one trailer-less commit on main."""
    repo = git_repo()  # unnamed: scratch is session-scoped, so a name collides
    sa = "dddddddd-0000-0000-0000-00000000000a"

    def ca(body, msg):
        (repo.path / "f.txt").write_text(body)
        repo.git("add", "f.txt")
        msgf = repo.path / ".msg"
        msgf.write_text(msg)
        repo.git("commit", "-q", "-F", str(msgf))

    ca("x1", "#1221 fix\n\nSession-Id: %s\nIssue-Ref: #11" % sa)
    ca("x2", "no trailer drop")
    (repo.path / "wl.json").write_text(
        '{"workers":[{"uuid":"%s","role":"editor","topic_id":30090,'
        '"feature":"echo-lane"}]}\n' % sa)
    return repo, sa


def test_attrib_joins_topic_feature_issue(attrib_repo, run_tool):
    """§16: mapped row joins topic+feature+issue; (unsigned) stays visible;
    --json carries the lane object."""
    repo, sa = attrib_repo
    tool = str(cf.tool_path("oc-attrib"))
    ledger = str(repo.path / "wl.json")

    res = run_tool([tool, "--repo", str(repo.path), "--range", "main",
                    "--ledger", ledger], timeout=120)
    assert res.rc == 0, "attrib exit=%s\n%s" % (res.rc, res.combined[-600:])

    rows = [ln.split("\t") for ln in res.out.splitlines() if ln.strip()]
    mapped = [r for r in rows if r[0] == sa]
    assert mapped, "no row for the mapped session\n%s" % res.out
    assert mapped[0][1:4] == ["30090", "echo-lane", "#11"], \
        "mapped row wrong: %r" % (mapped[0],)
    assert "(unsigned)" in res.out, "(unsigned) dropped from rows"

    js = run_tool([tool, "--repo", str(repo.path), "--range", "main",
                   "--ledger", ledger, "--json"], timeout=120)
    assert js.rc == 0, js.combined[-400:]
    lane = run_tool(["jq", "-e", "--arg", "s", sa,
                     'map(select(.session==$s))[0].lane.topic_id == 30090'],
                    timeout=60, stdin_data=js.out)
    assert lane.rc == 0, "--json lane object wrong: %s" % js.out[:400]


def test_attrib_usage_and_empty_range(attrib_repo, run_tool):
    """§16: no args -> 2; an empty range -> 4 (tool-correct degenerate state)."""
    repo, _ = attrib_repo
    tool = str(cf.tool_path("oc-attrib"))
    assert run_tool([tool], timeout=120).rc == 2, "no args -> expected 2"
    res = run_tool([tool, "--repo", str(repo.path), "--range", "main..main"],
                   timeout=120)
    assert res.rc == 4, "empty range -> %s (want 4)" % res.rc


@pytest.fixture
def novelty_repo(git_repo):
    """§17 fixture: B0 base, a twin absorbed into main, then a tip branch off B0
    carrying NOVEL, a REPLAY of the twin (new sha, same patch), and an EMPTY."""
    repo = git_repo()  # unnamed: scratch is session-scoped, so a name collides
    repo.git("commit", "-q", "--allow-empty", "-m", "base")
    b0 = repo.git("rev-parse", "HEAD").stdout.strip()

    repo.git("checkout", "-q", "-b", "src")
    (repo.path / "twin.txt").write_text("twin\n")
    repo.git("add", "twin.txt")
    repo.git("commit", "-q", "-m", "twin\n\nSession-Id: 11111111-1111-1111-1111-111111111111")
    twin = repo.git("rev-parse", "HEAD").stdout.strip()

    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--ff-only", "src")
    base = repo.git("rev-parse", "HEAD").stdout.strip()

    repo.git("checkout", "-q", "-b", "tip", b0)
    (repo.path / "pre.txt").write_text("pre\n")
    repo.git("add", "pre.txt")
    repo.git("commit", "-q", "-m", "pre\n\nSession-Id: 22222222-2222-2222-2222-222222222222")
    novel = repo.git("rev-parse", "HEAD").stdout.strip()

    repo.git("cherry-pick", twin)
    replay = repo.git("rev-parse", "HEAD").stdout.strip()
    repo.git("commit", "-q", "--allow-empty", "-m", "empty")
    empty = repo.git("rev-parse", "HEAD").stdout.strip()
    return repo, base, twin, replay, novel, empty


def test_novelty_filter(novelty_repo, run_tool):
    """§17: RAW untouched (3 rows), --novel keeps exactly the 1 novel commit,
    drops the replayed twin and the empty commit, and --no-novel == RAW."""
    repo, base, twin, replay, novel, empty = novelty_repo
    tool = str(cf.tool_path("oc-attrib"))
    rng = "%s..tip" % base
    assert replay != twin, "#407 fixture: replay reproduced the twin sha"

    raw = run_tool([tool, "--repo", str(repo.path), "--range", rng], timeout=120)
    assert raw.rc == 0, raw.combined[-400:]
    raw_rows = [ln for ln in raw.out.splitlines() if ln.strip()]
    assert len(raw_rows) == 3, "#407 RAW rows=%d want 3" % len(raw_rows)

    nov = run_tool([tool, "--repo", str(repo.path), "--range", rng, "--novel"],
                   timeout=120)
    assert nov.rc == 0, "#407 --novel rc=%s want 0" % nov.rc
    nov_rows = [ln for ln in nov.out.splitlines() if ln.strip()]
    assert len(nov_rows) == 1, "#407 --novel rows=%d want 1 (raw=3)" % len(nov_rows)
    assert novel[:7] in nov.out, "#407 --novel dropped the novel commit"
    assert replay[:7] not in nov.out, \
        "#407 --novel KEPT the replayed twin (patch-id equivalence missed)"
    assert empty[:7] not in nov.out, "#407 --novel KEPT the empty commit"

    # the filter is opt-in: RAW still shows the replay
    assert replay[:7] in raw.out, "#407 RAW lost the replayed twin"

    assert "3 raw, 1 replayed, 1 empty, 1 contributing" in nov.err, \
        "#407 stderr accounting missing: %r" % nov.err.strip()[:200]

    nn = run_tool([tool, "--repo", str(repo.path), "--range", rng, "--no-novel"],
                  timeout=120)
    assert nn.out == raw.out, "#407 --no-novel != RAW"


def test_novelty_all_replayed_is_empty_rc0(novelty_repo, run_tool):
    """§17: a tip whose every commit is a replay/empty is a legitimate EMPTY
    result at rc 0 — what oc-fanout must read as 'nothing to notify'."""
    repo, base, twin, _replay, _novel, _empty = novelty_repo
    tool = str(cf.tool_path("oc-attrib"))
    b0 = repo.git("rev-parse", "main~1").stdout.strip()

    repo.git("checkout", "-q", "-b", "tip2", b0)
    repo.git("cherry-pick", twin)
    repo.git("commit", "-q", "--allow-empty", "-m", "chore: sign tip2")

    res = run_tool([tool, "--repo", str(repo.path), "--range", "%s..tip2" % base,
                    "--novel"], timeout=120)
    assert res.rc == 0, "#407 all-replayed range rc=%s want 0" % res.rc
    assert not res.out.strip(), \
        "#407 all-replayed range returned rows: %r" % res.out[:200]
    assert "0 contributing" in res.err, \
        "#407 all-replayed accounting missing: %r" % res.err.strip()[:200]
