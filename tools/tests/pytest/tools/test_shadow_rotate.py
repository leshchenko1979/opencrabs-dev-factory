"""Ported: oc-shadow-rotate — run.sh §34.

Rotation is APPEND-to-archive then TRUNCATE-live, so the one way it can destroy
the shadow journal is truncating before the append lands — and that failure
leaves rc 0. Every assertion here therefore reads the ARCHIVE, never just the
exit code, and the second-rotation leg is the only one where ``>>`` and ``>``
differ (a single run passes for both).

``state_dir`` supplies ``OC_DEPLOY_STATE_DIR``, so the live journal is never
touched.
"""

from __future__ import annotations

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-shadow-rotate")


@pytest.fixture
def shadow(state_dir):
    """(live, archive) paths inside the per-test deploy state dir."""
    return state_dir / "oc-deploy-shadow.log", state_dir / "oc-deploy-shadow.archive.log"


def _run(run_tool, *args):
    return run_tool([str(TOOL), *args], timeout=120)


def test_absent_live_log_is_a_noop(run_tool, shadow):
    live, archive = shadow
    res = _run(run_tool, "--dry-run")
    assert res.rc == 0, "absent live log: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert not live.exists(), "the noop arm CREATED the live log"
    assert not archive.exists(), "the noop arm CREATED an archive"


def test_empty_live_log_is_a_noop(run_tool, shadow):
    """The guard is ``-s``, not ``-f``: an empty file must not yield an empty
    archive append."""
    live, archive = shadow
    live.write_text("")
    res = _run(run_tool)
    assert res.rc == 0, "empty live log: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert not (archive.exists() and archive.stat().st_size), \
        "an empty live log produced an archive write"


def test_dry_run_plan_names_the_line_count(run_tool, shadow):
    live, archive = shadow
    live.write_text("line1\nline2\n")
    res = _run(run_tool, "--dry-run")
    assert res.rc == 0, "dry-run: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert "PLAN: append 2 lines" in res.combined, \
        "dry-run did not report 'PLAN: append 2 lines': %r" % res.combined[-300:]
    assert live.read_text() == "line1\nline2\n", "dry-run MUTATED the live log"
    assert not archive.exists(), "dry-run created the archive"


def test_rotate_archives_then_truncates(run_tool, shadow):
    live, archive = shadow
    live.write_text("line1\nline2\n")
    res = _run(run_tool)
    assert res.rc == 0, "rotate: rc=%s\n%s" % (res.rc, res.combined[-400:])
    assert archive.exists(), "archive missing after rotate — the rows are LOST"
    body = archive.read_text()
    assert "line1" in body, "archive lost line1"
    assert "line2" in body, "archive lost line2"
    assert live.exists() and live.stat().st_size == 0, "live log not truncated"


def test_rotate_appends_across_runs(run_tool, shadow):
    """Second rotation must APPEND: `>>` vs `>` differ only here."""
    live, archive = shadow
    live.write_text("first\n")
    assert _run(run_tool).rc == 0
    live.write_text("second\n")
    assert _run(run_tool).rc == 0
    body = archive.read_text()
    assert "first" in body and "second" in body, \
        "rotation did not append on the second run (archive=%r)" % body


def test_unknown_arg_is_rc2(run_tool, shadow):
    """C-#3: usage is rc 2; the retired rc 1 must not return."""
    res = _run(run_tool, "--bogus")
    assert res.rc == 2, "unknown arg: rc=%s, want 2 (C-#3)\n%s" % (
        res.rc, res.combined[-300:])


def test_help_is_rc0(run_tool, shadow):
    res = _run(run_tool, "--help")
    assert res.rc == 0, "--help: rc=%s, want 0 (C-#3)" % res.rc
    assert res.out.strip(), "--help wrote nothing to stdout"
