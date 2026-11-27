"""Ported: the per-tool usage/rc legs of run.sh.

These are the bespoke `ok`/`bad` legs that sit beside a `run_selftest <tool>`
line. The `run_selftest` wrapper itself belongs to the selftest module; what is
ported here is only the argv/rc contract each tool declares in
`tools/docs/RC-CONTRACT.md`.

Section -> test mapping is in the docstring of each test.
"""

from __future__ import annotations

import pytest

import conftest as cf


def _tool(name):
    return str(cf.tool_path(name))


# (section, tool, argv, want_rc, claim)
RC_CASES = [
    ("8",  "oc-verify-order",    ["--no-such-arg"],                 1, "unknown arg -> 1 (usage)"),
    ("15", "oc-pr-atomicity",    [],                                1, "no args -> 1 (usage)"),
    ("20", "oc-features",        ["--bogus"],                       2, "unknown arg -> 2 (usage)"),
    ("21", "oc-issue-sweep",     [],                                2, "no args -> 2 (usage)"),
    ("28", "oc-wt",              ["add", "Bad_Slug", "some-branch"], 2, "bad slug -> 2 (usage)"),
    ("29", "oc-drift-check",     ["u1", "0.4"],                     2, "bad version shape -> 2"),
    ("31", "oc-pr-fault-scope",  ["1"],                             2, "missing --run -> 2 (usage)"),
    ("36", "oc-issue-log",       [],                                2, "no args -> 2 (usage)"),
    ("37", "oc-commit",          [],                                2, "no args -> 2 (usage)"),
    ("38", "oc-audit-ship",      ["--bogus"],                       2, "unknown arg -> 2 (usage)"),
    ("39", "oc-tg-audit",        [],                                2, "no args -> 2 (usage)"),
    ("40", "oc-rebase-safety",   [],                                2, "no args -> 2 (usage)"),
    ("40", "oc-rebase-safety",   ["overlap"],                       2, "overlap missing args -> 2"),
    ("40", "oc-rebase-safety",   ["audit"],                         2, "audit missing args -> 2"),
    ("41", "oc-roster",          [],                                2, "no args -> 2 (usage)"),
    ("41", "oc-roster",          ["--no-such-arg"],                 2, "unknown arg -> 2"),
    ("42", "oc-ship",            [],                                2, "no args -> 2 (usage)"),
    ("42", "oc-ship",            ["--no-such-arg"],                 2, "unknown arg -> 2"),
    ("51", "oc-issue-dispatch",  ["--bogus"],                       2, "unknown arg -> 2 (usage)"),
    ("54", "oc-log-search",      ["--bogus"],                       2, "unknown arg -> 2 (usage)"),
]


@pytest.mark.parametrize("section,tool,argv,want,claim", RC_CASES,
                         ids=["s%s-%s-%s" % (c[0], c[1], c[4][:24].replace(" ", "_"))
                              for c in RC_CASES])
def test_usage_rc(section, tool, argv, want, claim, run_tool):
    """run.sh §<section>: `<tool> <argv>` -> rc <want> (usage contract)."""
    res = run_tool([_tool(tool), *argv], timeout=120)
    assert res.rc == want, "§%s %s: want rc %s, got %s\n%s" % (
        section, claim, want, res.rc, res.combined[-800:])


# --help legs: an explicitly requested READ must exit 0 (C-#3 / #748a)
@pytest.mark.parametrize("section,tool", [
    ("51", "oc-issue-dispatch"),
    ("54", "oc-log-search"),
])
def test_help_exits_zero(section, tool, run_tool):
    """run.sh §<section>: `<tool> --help` -> rc 0."""
    res = run_tool([_tool(tool), "--help"], timeout=120)
    assert res.rc == 0, "§%s %s --help rc=%s" % (section, tool, res.rc)


def test_issue_log_bad_sha_is_rc3(run_tool):
    """run.sh §36: a non-existent sha is rc 3 (not found), with a stubbed repo."""
    res = run_tool([_tool("oc-issue-log"), "1", "zznotasha", "--dry-run"],
                   timeout=120, env={"OC_ISSUE_LOG_REPO": "x/y"})
    assert res.rc == 3, "bad sha -> %s (want 3)\n%s" % (res.rc, res.combined[-500:])
