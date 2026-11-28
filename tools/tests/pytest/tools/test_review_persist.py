"""`oc-review-persist`.

The section exists because of a GHOST INCIDENT: a review was produced, reported
as done, and left NOTHING on disk — so the next reader could not tell a review
that never ran from one that ran and was lost. Two artefacts are the cure, and
both are asserted here because either alone is insufficient:

* ``skill-review-<lane>-<YYYYMMDD>.md`` — the report itself, on disk;
* ``skill-review-index.log`` — the index row, which is what makes the report
  FINDABLE. A report written without an index entry is the ghost again, one
  directory deeper.

The date is in the filename, so the assertion computes it from the same UTC day
the tool does rather than globbing loosely: a filename the tool dated differently
is exactly the defect (a lane reading "today's report" would find yesterday's).
"""

from __future__ import annotations

import datetime

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-review-persist")

def test_persist_writes_the_report_and_the_index(run_tool, scratch):
    """One invocation, two artefacts, both non-empty.

    ``-s`` (non-empty) not ``-f`` (exists): a zero-byte report is the ghost with
    a filename, which is worse than no file at all because it reads as success.
    """
    out = scratch.path / "reviews"
    out.mkdir()
    res = run_tool([str(TOOL), "A", "battery edge report", "--dir", str(out)],
                   timeout=180)
    assert res.rc == 0, "persist rc=%s\n%s" % (res.rc, res.combined[-800:])

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    report = out / ("skill-review-A-%s.md" % today)
    assert report.is_file(), (
        "no report at %s — the review left nothing on disk (the ghost "
        "incident)\nwrote: %s"
        % (report.name, sorted(p.name for p in out.iterdir())))
    assert report.stat().st_size > 0, \
        "the report exists but is EMPTY — the ghost with a filename"

    index = out / "skill-review-index.log"
    assert index.is_file(), (
        "no index row — the report is on disk but unfindable (the ghost, one "
        "directory deeper)")
    assert index.stat().st_size > 0, "the index file exists but is EMPTY"

    assert report.name in index.read_text(), \
        ("the index does not name the report it was written with — an index that "
         "omits its own row cannot be used to find anything:\n%s"
         % index.read_text()[-400:])
