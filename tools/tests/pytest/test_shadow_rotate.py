"""Ported: oc-shadow-rotate — run.sh §34.

The rotation is archive-then-truncate, so the ONLY thing that can silently
destroy the shadow journal is the truncate running before the append lands.
Every leg here reads the ARCHIVE, never just the exit code: a run that returned
0 and left an empty archive has lost the journal, and rc alone cannot see it.

``state_dir`` supplies ``OC_DEPLOY_STATE_DIR``, so the live journal of the fleet
is never touched.
"""

from __future__ import annotations

import pytest

import conftest as cf

TOOL = cf.TOOLS_DIR / "state" / "oc-shadow-rotate"


@pytest.fixture
def shadow(state_dir):
    return state_dir / "oc-deploy-shadow.log", state_dir / "oc-deploy-shadow.archive.log"


def _run(run_tool, *args):
    return run_tool([str(TOOL), *args], timeout=120)


def test_no_live_log_is_a_noop(run_tool, shadow):
    """Absent live log -> rc 0, and nothing is created on either side."""
    live, archive = shadow
    res = _run(run_tool, "--dry-run")
    assert res.rc == 0, "no live log: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert not live.exists(), "the noop arm CREATED the live log"
    assert not archive.exists(), "the noop arm CREATED an archive"


def test_empty_live_log_is_a_noop(run_tool, shadow):
    """Empty-but-present live log -> rc 0 and no archive row (a `-s` guard, not
    a `-f` guard: an empty file must not produce an empty archive append)."""
    live, archive = shadow
    live.write_text("")
    res = _run(run_tool)
    assert res.rc == 0, "empty live log: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert not (archive.exists() and archive.stat().st_size), \
        "empty live log produced an archive append"


def test_dry_run_plan_names_the_line_count(run_tool, shadow):
    """--dry-run reports the count and touches NEITHER file."""
    live, archive = shadow
    live.write_text("line1\nline2\n")
    res = _run(run_tool, "--dry-run")
    assert res.rc == 0, "dry-run: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert "PLAN: append 2 lines" in res.combined, \
        "dry-run PLAN did not name 2 lines: %r" % res.combined[-300:]
    assert live.read_text() == "line1\nline2\n", "dry-run MUTATED the live log"
    assert not archive.exists(), "dry-run created the archive"


def test_rotate_archives_then_truncates(run_tool, shadow):
    """The real run: archive carries the content, live is emptied."""
    live, archive = shadow
    live.write_text("line1\nline2\n")
    res = _run(run_tool)
    assert res.rc == 0, "rotate: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert not live.stat().st_size, "live log NOT truncated"
    assert archive.exists(), "archive never created — the content is GONE"
    assert "line1" in archive.read_text(), "archive lost line1"
    assert "line2" in archive.read_text(), "archive lost line2"


def test_rotate_is_additive_across_runs(run_tool, shadow):
    """A second rotation APPENDS: an earlier archived row survives.

    This is the leg the rc-only check cannot make — `>>` vs `>` differ only on
    the second run, so a single-run assertion passes for both."""
    live, archive = shadow
    live.write_text("first\n")
    assert _run(run_tool).rc == 0
    live.write_text("second\n")
    assert _run(run_tool).rc == 0
    body = archive.read_text()
    assert "first" in body and "second" in body, \
        "second rotation did not append (archive=%r)" % body


def test_unknown_arg_is_rc2(run_tool, shadow):
    """C-#3: usage is rc 2, not 1 — the retired code must not come back."""
    res = _run(run_tool, "--bogus")
    assert res.rc == 2, "unknown arg: rc=%s, want 2 (C-#3)\n%s" % (
        res.rc, res.combined[-300:])


def test_help_is_rc0(run_tool, shadow):
    res = _run(run_tool, "--help")
    assert res.rc == 0, "--help: rc=%s, want 0 (C-#3)" % res.rc
    assert "oc-shadow-rotate" in res.combined
