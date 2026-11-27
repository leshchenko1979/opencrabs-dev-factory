"""Ported: the RED-RECEIPT transcript — run.sh §75 (census ordinal §62).

WHY THIS WAS DEFERRED, AND WHY THE DEFERRAL WAS WRONG
    The register said this section "asserts ``run.sh``'s own ``bad()``
    accumulator by running a synthetic failing section in a subshell. There is
    no ``run.sh`` accumulator inside pytest to assert." That is a claim about
    WHERE THE FUNCTIONS LIVE, not about whether their behaviour can be driven.
    The functions are TEXT in ``tools/tests/run.sh``, and text can be extracted
    and sourced — ``lib/harness.extract_shell_function`` does exactly that, so
    every leg here drives the REAL ``bad()``, ``record()``,
    ``finalize_fail_log()``, ``battery_capture_fail_rows()`` and
    ``emit_summary()`` out of the file on disk. Nothing is re-typed, so this port
    cannot keep passing after the block it describes regresses (the #720/#111
    lesson). §33's deferral in this same migration was withdrawn for the same
    reason: a limitation of the MEASURING INSTRUMENT misread as a property of
    the subject.

THE CONTRACT (HQ item 5, 2026-09-22; widened by #614)
    A red run must leave its FAIL rows somewhere a LATER reader can still read:

    * ``bad()`` appends ``  FAIL - <desc>`` to ``$FAIL_LOG`` **and** prints it,
      so the transcript and stdout agree about what failed — the parallel driver
      re-counts rows by that prefix, so the two halves must move together;
    * ``record()`` is a TEE: a continuation line reaches BOTH sinks, which is
      what makes a multi-line diagnosis legible in the log;
    * ``finalize_fail_log`` REMOVES the log on green and NAMES it on red, so the
      log's PRESENCE is itself the red signal — asserted in both directions,
      because a one-way leg cannot tell a working finalize from a constant;
    * the receipt carries ``fail_rows`` (#614), so the next run's truncate of
      the log cannot destroy the diagnosis, and an over-cap capture SAYS it
      truncated instead of silently dropping rows.

WHAT THIS PORT ADDS OVER THE SHELL
    The shell discards each leg's stdout (``>/dev/null``) so a synthetic failure
    cannot corrupt its own receipt — which means "reaches stdout" was never
    actually asserted, only assumed. Here the same functions are driven with
    their stdout CAPTURED, so that half of the contract is a real assertion.
"""

from __future__ import annotations

import json
import re
import shlex

import pytest

import conftest as cf
from lib import harness as H

RUN_SH = cf.REPO_ROOT / "tools" / "tests" / "run.sh"

# The prelude functions a leg needs, in dependency order. Extracted VERBATIM by
# name (``lib/harness.extract_shell_function``) — never retyped.
FUNCS = (
    "note",                     # the stdout half of every transcript row
    "_battery_check_stamp",     # ok()/bad() call it; a no-op unless timing is on
    "ok",
    "bad",
    "record",
    "finalize_fail_log",
    "battery_capture_fail_rows",
    "_battery_tree_fp",         # emit_summary fingerprints the tree
    "emit_summary",             # the ONE receipt writer
)


def _probe(tmp_path, body, *, run_tool, env=None):
    """Source the real prelude apparatus, then run ``body`` under ``set -u``.

    ``set -u`` is kept deliberately: run.sh runs under it, so a function that
    only works with an unset variable is not a function that runs in production.

    ``TOOLS_DIR`` points at a THROWAWAY tree, so ``emit_summary`` writes its
    receipt to ``<tmp>/tree/tests/battery-last.json`` and never near the
    canonical path. The prelude's own state assignments (PASS/FAIL, the
    ``$FAIL_LOG`` trio, the #614 fields) are read out of run.sh rather than
    re-listed here — a second copy of that state would drift from the one the
    real run uses.
    """
    tree = tmp_path / "tree"
    (tree / "tests").mkdir(parents=True, exist_ok=True)
    script = tmp_path / "probe.sh"
    script.write_text("\n".join([
        "set -u",
        *[H.extract_shell_function(f) for f in FUNCS],
        "TOOLS_DIR=%s" % shlex.quote(str(tree)),
        H.prelude_state(),
        body,
    ]) + "\n")
    call_env = {"TOOLS_DIR": str(tree)}
    if env:
        call_env.update(env)
    res = run_tool(["/bin/bash", str(script)], timeout=120, env=call_env)
    assert res.rc == 0, "the probe itself failed (rc=%d):\n%s" % (res.rc, res.combined[-1200:])
    return res, tree


# =============================================================================
# (a) bad() — the row reaches the transcript AND stdout, and FAIL moves
# =============================================================================
def test_bad_writes_the_fail_row_to_both_sinks(tmp_path, run_tool):
    """§62 leg (a): ``bad()`` records the row and prints it, and counts it."""
    log = tmp_path / "a.log"
    res, _tree = _probe(tmp_path, "\n".join([
        "FAIL_LOG=%s" % shlex.quote(str(log)),
        ': > "$FAIL_LOG"',
        'bad "synthetic-leg"',
        'printf "ACC=%s\\n" "$FAIL"',
    ]), run_tool=run_tool)

    assert "  FAIL - synthetic-leg" in log.read_text(), (
        "bad() did not record the FAIL row in the transcript (log=%r)"
        % log.read_text())
    assert "  FAIL - synthetic-leg" in res.out, (
        "bad() printed no FAIL row on stdout. The parallel driver re-counts rows "
        "by the '^  FAIL ' prefix, so a row that only reaches the file makes the "
        "transcript and the verdict disagree.\nstdout=%r" % res.out[-800:])
    assert "ACC=1" in res.out, (
        "bad() did not increment FAIL — the row is written but the run would "
        "still report green\nstdout=%r" % res.out[-800:])


# =============================================================================
# (b) record() — a continuation line reaches BOTH sinks
# =============================================================================
def test_record_is_a_tee(tmp_path, run_tool):
    """§62 leg (b): the detail reaches the transcript AND passes stdout through."""
    log = tmp_path / "b.log"
    res, _tree = _probe(tmp_path, "\n".join([
        "FAIL_LOG=%s" % shlex.quote(str(log)),
        ': > "$FAIL_LOG"',
        "printf 'detail-line\\n' | record",
    ]), run_tool=run_tool)

    assert "detail-line" in log.read_text(), (
        "record() did not append the detail to the transcript (log=%r) — the "
        "FAIL row would survive with nothing under it" % log.read_text())
    assert "detail-line" in res.out, (
        "record() swallowed the detail on stdout: a green run would stop being "
        "byte-identical and a red one would lose the line from its transcript\n"
        "stdout=%r" % res.out[-800:])


# =============================================================================
# (c) finalize_fail_log — BOTH directions
# =============================================================================
@pytest.mark.parametrize("fails,log_kept,field", [
    (0, False, ""),
    (1, True, "tools/tests/battery-last-fail.log"),
], ids=["green-removes-and-empties", "red-keeps-and-names"])
def test_finalize_fail_log_in_both_directions(tmp_path, run_tool, fails,
                                              log_kept, field):
    """§62 legs (c): the log's PRESENCE is the red signal — proven both ways."""
    log = tmp_path / ("c%d.log" % fails)
    res, _tree = _probe(tmp_path, "\n".join([
        "FAIL_LOG=%s" % shlex.quote(str(log)),
        ': > "$FAIL_LOG"',
        "FAIL=%d" % fails,
        "finalize_fail_log",
        'printf "EXISTS=%s\\nFIELD=<%s>\\n" '
        '"$([ -f "$FAIL_LOG" ] && echo yes || echo no)" "${FAIL_LOG_FIELD:-}"',
    ]), run_tool=run_tool)

    assert ("EXISTS=yes" in res.out) is log_kept, (
        "with FAIL=%d the transcript %s\nstdout=%r"
        % (fails, "should have been KEPT" if log_kept else "should have been REMOVED",
           res.out[-600:]))
    assert "FIELD=<%s>" % field in res.out, (
        "with FAIL=%d the receipt's fail_log field should be %r\nstdout=%r"
        % (fails, field, res.out[-600:]))


# =============================================================================
# (d)/(g) wiring — exactly ONE receipt writer declares each field
# =============================================================================
def _printf_field_count(pattern: str) -> int:
    return len(re.findall(pattern, RUN_SH.read_text(encoding="utf-8", errors="replace"),
                          re.M))


def test_exactly_one_writer_declares_the_fail_log_field():
    """§62 leg (d): ``-eq 1``, never ``>= 1`` — a second writer is the drift.

    #111 collapsed the hand-copied sequential tail into ``emit_summary``, so 1
    is the DESIGNED count; ``>= 1`` would stay green through the regression this
    leg exists to catch.
    """
    n = _printf_field_count(r"^ *printf .*fail_log")
    assert n == 1, (
        "the fail_log receipt field is declared by %d printf line(s), expected "
        "exactly 1 (emit_summary) — a second receipt writer has appeared" % n)


def test_exactly_one_writer_embeds_fail_rows():
    """§62 leg (g): the same ratchet for the #614 field, counted on the FIELD.

    Counting the format-string field (not the bare word) keeps a stray comment
    from satisfying the leg.
    """
    n = _printf_field_count(r'^ *printf .*"fail_rows": %s')
    assert n == 1, (
        'fail_rows is embedded by %d printf line(s), expected exactly 1 '
        "(emit_summary)" % n)


# =============================================================================
# (e) #614 — the red receipt is SELF-CONTAINED
# =============================================================================
def test_red_receipt_is_self_contained(tmp_path, run_tool):
    """§62 leg (e), THE DISCRIMINATING ONE: the row outlives the log.

    Drives the real ``emit_summary``, then TRUNCATES the log exactly as the next
    run's ``: > "$FAIL_LOG"`` does, and only then reads the receipt. On the
    pre-#614 artifact ``fail_rows`` is absent and the diagnosis is gone.
    """
    log = tmp_path / "e.log"
    res, tree = _probe(tmp_path, "\n".join([
        "FAIL_LOG=%s" % shlex.quote(str(log)),
        "FAIL_LOG_FIELD=tools/tests/battery-last-fail.log",
        "BATTERY_MODE=r614",
        "PASS=1; FAIL=1",
        "printf '  FAIL - r614-probe-leg\\n    probe context line\\n' > \"$FAIL_LOG\"",
        "emit_summary >/dev/null 2>&1 || true",
        ': > "$FAIL_LOG"',                      # the NEXT run starts here
    ]), run_tool=run_tool)
    assert res.rc == 0, res.combined[-800:]

    receipt = json.loads((tree / "tests" / "battery-last.json").read_text())
    assert receipt["verdict"] == "FAIL", (
        "emit_summary wrote verdict %r with FAIL=1 — a red run would commit a "
        "green receipt" % (receipt["verdict"],))
    assert receipt["fail_log"] == "tools/tests/battery-last-fail.log", (
        "the red receipt does not name the sidecar by its RELATIVE path "
        "(fail_log=%r), so a reader cannot tail it" % (receipt["fail_log"],))
    rows = receipt["fail_rows"]
    assert any("r614-probe-leg" in r for r in rows), (
        "the red receipt is NOT self-contained: fail_rows=%r carries no trace of "
        "the failing leg, and the log it names has already been truncated by the "
        "next run (#614)" % (rows,))
    assert any("probe context line" in r for r in rows), (
        "the CONTINUATION line did not ride into the receipt, so a multi-line "
        "diagnosis is still lost: %r" % (rows,))


def test_over_cap_capture_declares_its_truncation(tmp_path, run_tool):
    """§62 leg (f): a bounded capture SAYS it truncated — never a silent drop."""
    log = tmp_path / "f.log"
    res, _tree = _probe(tmp_path, "\n".join([
        "FAIL_LOG=%s" % shlex.quote(str(log)),
        "FAIL_ROWS_CAP=1",
        "FAIL_ROWS_JSON='[]'; FAIL_ROWS_TRUNC='false'",
        "printf '  FAIL - one\\n  FAIL - two\\n  FAIL - three\\n' > \"$FAIL_LOG\"",
        "battery_capture_fail_rows",
        'printf "TRUNC=%s\\nROWS=%s\\n" "$FAIL_ROWS_TRUNC" "$FAIL_ROWS_JSON"',
    ]), run_tool=run_tool)

    m_trunc = re.search(r"^TRUNC=(.*)$", res.out, re.M)
    m_rows = re.search(r"^ROWS=(.*)$", res.out, re.M)
    assert m_trunc and m_rows, "the probe printed no verdict: %r" % res.out[-600:]
    rows = json.loads(m_rows.group(1))
    assert m_trunc.group(1) == "true", (
        "3 rows against a cap of 1 were captured WITHOUT declaring the "
        "truncation (flag=%r) — the receipt would imply it holds everything"
        % m_trunc.group(1))
    assert len(rows) == 1, (
        "the cap did not bound the capture: %d row(s) from a cap of 1 — %r"
        % (len(rows), rows))
