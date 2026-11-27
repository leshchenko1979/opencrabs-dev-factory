"""Receipt parity: the pytest receipt must carry emit_summary's 18 fields.

The parity check reads the format string out of ``tools/tests/run.sh`` rather
than re-listing the fields here. A second hand-written copy would drift, and the
copy that drifts is the one nobody reads — the same defect as ``#111`` (two
receipt writers that already disagreed) one layer out.

The comment at ``run.sh:5545`` says 17 fields. It is STALE: it was written
before ``timing`` was added. The count is asserted from the format string, so
the stale comment cannot propagate into the schema.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import conftest as cf
from lib import receipt as R

RUN_SH = cf.REPO_ROOT / "tools" / "tests" / "run.sh"


def emit_summary_fields() -> list[str]:
    """The field names in emit_summary's printf, in order."""
    src = RUN_SH.read_text(encoding="utf-8", errors="replace")
    start = src.index("emit_summary() {")
    # The format string ends at the closing quote of the printf, which is the
    # first line ending in a lone "'" after the opening.
    seg = src[start:start + 4000]
    fmt_start = seg.index("printf '{")
    fmt_end = seg.index("' \\\n", fmt_start)
    fmt = seg[fmt_start:fmt_end]
    return re.findall(r'"([a-z_]+)":', fmt)


def test_emit_summary_has_eighteen_fields():
    """The measured fact: 18, not the 17 the :5545 comment claims."""
    fields = emit_summary_fields()
    assert len(fields) == 18, (
        "run.sh:emit_summary now emits %d fields (%s) — the pytest receipt and "
        "every consumer must be updated together" % (len(fields), fields))
    # The stale comment, named explicitly so nobody "fixes" the code to match it.
    src = RUN_SH.read_text(encoding="utf-8", errors="replace")
    assert "the same 17-field printf" in src or "17-field" in src, (
        "the stale 17-field comment vanished; if it was corrected, delete this "
        "assertion and update the docstring")


def test_receipt_fields_match_emit_summary_exactly():
    """Same names, same ORDER — a consumer that indexes positionally must work."""
    assert list(R.FIELDS) == emit_summary_fields()


def test_receipt_has_the_timing_object_shape(tmp_path):
    """``timing`` = {max_concurrency, section_count, sum_ms, slowest[<=10]}.

    Each slowest entry is ``{n, title, ms, start_ms, end_ms}`` — run.sh's
    battery_timing_json emits exactly these keys, and the receipt is the only
    place a reader can learn WHICH section cost the wall (58 of 68 sections have
    no measured seconds in any other artifact).
    """
    class _Cfg:
        class option:
            numprocesses = 0
    run = R.Run(_Cfg(), tmp_path / "r.json")
    for i in range(14):
        run.add_row(1000.0 + i, 1000.5 + i, "test_mod.py::t%d" % i)
    run.n_pass = 14
    receipt = run.build()

    assert set(receipt) == set(R.FIELDS)
    timing = receipt["timing"]
    assert set(timing) == {"max_concurrency", "section_count", "sum_ms", "slowest"}
    assert timing["section_count"] == 14
    assert timing["max_concurrency"] == 1, "non-overlapping rows cannot overlap"
    assert timing["sum_ms"] == 7000, "14 rows x 500ms"
    assert len(timing["slowest"]) == 10, "slowest is capped at 10, like run.sh"
    for entry in timing["slowest"]:
        assert set(entry) == {"n", "title", "ms", "start_ms", "end_ms"}
        assert entry["ms"] == entry["end_ms"] - entry["start_ms"]


def test_timing_max_concurrency_measures_overlap(tmp_path):
    """Peak overlap, not duration sum: the direct test of "did the pool hold N"."""
    class _Cfg:
        class option:
            numprocesses = 3
    run = R.Run(_Cfg(), tmp_path / "r.json")
    # three overlapping [0,1000] rows
    run.add_row(0.0, 1.0, "a")
    run.add_row(0.1, 1.1, "b")
    run.add_row(0.2, 1.2, "c")
    # one later, alone
    run.add_row(5.0, 5.5, "d")
    assert run.timing()["max_concurrency"] == 3


def test_fail_rows_come_from_per_worker_files(tmp_path, monkeypatch):
    """A green worker must never erase a sibling's evidence (#517/#614, one out).

    run.sh's single $FAIL_LOG is truncated by whoever starts a run and removed
    on green; under N workers that would let one green worker destroy another's
    rows. Here: two per-worker files, concatenated by the controller.
    """
    class _Cfg:
        class option:
            numprocesses = 2
    run_dir = tmp_path / "rundir"
    run_dir.mkdir()
    (run_dir / "fails.gw0.jsonl").write_text(json.dumps("row from worker 0") + "\n")
    (run_dir / "fails.gw1.jsonl").write_text(json.dumps("row from worker 1") + "\n")
    run = R.Run(_Cfg(), tmp_path / "r.json")
    run.run_dir = run_dir

    rows, truncated = run.collected_fails()
    assert rows == ["row from worker 0", "row from worker 1"]
    assert truncated is False

    # A worker appends only to ITS OWN file.
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw7")
    run.append_fail("row from worker 7")
    assert (run_dir / "fails.gw7.jsonl").is_file()
    assert "gw7" not in (run_dir / "fails.gw0.jsonl").read_text()


def test_fail_rows_are_capped_and_disclosed(tmp_path):
    """Bounded rows plus a truthful ``fail_rows_truncated`` flag."""
    class _Cfg:
        class option:
            numprocesses = 0
    run_dir = tmp_path / "rundir"
    run_dir.mkdir()
    many = [json.dumps("row %d" % i) for i in range(R.FAIL_ROWS_CAP + 5)]
    (run_dir / "fails.ctrl.jsonl").write_text("\n".join(many) + "\n")
    run = R.Run(_Cfg(), tmp_path / "r.json")
    run.run_dir = run_dir
    rows, truncated = run.collected_fails()
    assert len(rows) == R.FAIL_ROWS_CAP
    assert truncated is True


def test_receipt_refuses_field_drift(tmp_path):
    """Writing a receipt with a missing or extra field is an error, not a silent
    schema change that every consumer discovers later."""
    class _Cfg:
        class option:
            numprocesses = 0
    run = R.Run(_Cfg(), tmp_path / "r.json")
    run.extra["receipt_overrides"] = {"surprise": 1}
    with pytest.raises(AssertionError, match="receipt field drift"):
        run.write()


def test_receipt_is_controller_only():
    """The canonical path is guarded by ``hasattr(config, 'workerinput')``.

    Static, because the guard's WHOLE value is that it cannot be observed from a
    passing worker: an xdist worker that wrote the receipt would race the
    controller and the last writer would win, so the test has to read the code.
    """
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert 'hasattr(config, "workerinput")' in src, (
        "the controller guard vanished — workers can now write the canonical receipt")
    fin = src[src.index("def pytest_sessionfinish"):]
    assert 'hasattr(config, "workerinput")' in fin, (
        "the guard is no longer in the WRITE path (sessionfinish)")


def test_collect_only_writes_no_receipt():
    """A collect-only run is not a verdict, so it must not overwrite a real one."""
    src = Path(R.__file__).read_text(encoding="utf-8")
    fin = src[src.index("def pytest_sessionfinish"):]
    assert 'collectonly' in fin, "a collect-only run can now clobber the last verdict"
