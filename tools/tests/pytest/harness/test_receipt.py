"""Receipt shape, path contract, and write-path guards.

The canonical path is ``tools/tests/battery-last.json`` because ``oc-ledger sync``
hard-reads that file and nothing else. This module pins that contract, the 18-field
schema, and the controller-only write path.

The field list is asserted against ``lib.receipt.FIELDS`` itself, which is the
single declaration now that the shell harness is retired. Re-listing the names here
would be a second copy that drifts — the ``#111`` defect one layer out.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conftest as cf
from lib import receipt as R


def test_receipt_has_eighteen_fields():
    """The schema is 18 fields, and the list is the one the writer validates."""
    assert len(R.FIELDS) == 18, (
        "the receipt schema is %d fields (%s) — consumers read it by name"
        % (len(R.FIELDS), list(R.FIELDS)))


def test_canonical_path_is_the_version_bump_gate():
    """The receipt lands where ``oc-ledger sync`` looks, or the gate reads stale.

    ``sync`` dies rc 5 on a missing/stale/RED receipt and names the file in its
    message. If the writer moved the path, every bump would either fail or — worse,
    if the old file were left behind — succeed on a verdict nothing refreshed.
    """
    expected = cf.REPO_ROOT / "tools" / "tests" / "battery-last.json"
    assert R.DEFAULT_RECEIPT == expected, (
        "receipt path moved to %s — oc-ledger sync reads %s"
        % (R.DEFAULT_RECEIPT, expected))


def test_receipt_has_the_timing_object_shape(tmp_path):
    """``timing`` = {max_concurrency, section_count, sum_ms, slowest[<=10]}.

    Each slowest entry is ``{n, title, ms, start_ms, end_ms}`` — the shell
    harness's battery_timing_json emitted exactly these keys, and the receipt is
    the only place a reader can learn WHICH section cost the wall (58 of 68
    sections have no measured seconds in any other artifact).
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
    assert len(timing["slowest"]) == 10, "slowest is capped at 10"
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

    The shell harness's single $FAIL_LOG was truncated by whoever started a run
    and removed on green; under N workers that would let one green worker destroy
    another's rows. Here: two per-worker files, concatenated by the controller.
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
