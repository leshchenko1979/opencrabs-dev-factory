"""The pytest suite INSIDE the shell gate — run.sh §63.

WHAT THIS PORTS
    ``run.sh`` section 63 (``section "pytest suite"``). The section itself is
    three shell sites; what actually needs guarding is the INVOCATION, because
    each of its four terms was chosen against a measured failure and every one
    of them can be "simplified" back into that failure by a later editor.

WHY EACH TERM IS LOAD-BEARING (the receipts)
    * ``-n 2`` — at ``-n 4`` on this 3.9 GB box, seventeen unrelated tests
      reddened with identical jemalloc ``EAGAIN`` (errno 11) thread-creation
      noise: overlapping ``--selftest`` process trees against the scope's
      ``TasksMax``. Zero real defects; the box, not the code.
    * ``-m "not slow"`` — the ``slow`` marker means "on request" (README), and
      those legs drive ``run.sh --chunk N``. In a gate they would run a nested
      battery inside the battery.
    * ``OC_BATTERY_LOCK`` redirect — ``conftest.py`` resolves the lock path from
      that variable AT IMPORT. The shell process already holds the canonical
      flock, so an un-redirected nested run makes every ``serial`` leg wait its
      full 900 s budget and then SKIP. A skipped leg reads as green.
    * placed BEFORE the receipt write — the parallel driver extracts a chunk as
      everything up to ``verdict=PASS``, so a section placed after it runs zero
      legs in parallel mode while the summary still prints clean.

    Each assertion below names the term it protects, so a red says WHICH
    simplification was made rather than "the section changed".
"""

from __future__ import annotations

import re

import pytest

from lib import harness as H

SECTION_TITLE = "pytest suite"


def _strip_comments(block: str) -> str:
    """The block's CODE only — every full-line comment removed.

    The block's comments NAME the rejected forms on purpose ("never -n 4",
    "the lock is not derived from TMPDIR"), so a guard that greps the raw text
    fails on the very prose documenting the rule. Guarding a comment is the
    same defect as asserting nothing: it cannot distinguish the code from the
    description of the code.
    """
    return "\n".join(ln for ln in block.splitlines()
                     if not ln.lstrip().startswith("#"))


def _section_block() -> str:
    """The §63 body, bounded exactly as the shell census bounds it.

    From its ``section "..."`` call to the NEXT ``section "..."`` call (or EOF).
    Bounded by the call, never by a ``# ---- `` header: the header-then-call
    convention means header-bounding truncates the body.
    """
    text = H.RUN_SH.read_text()
    start = text.find('section "%s"' % SECTION_TITLE)
    if start < 0:
        pytest.fail("run.sh no longer has a section %r — the gate lost its "
                    "pytest leg" % SECTION_TITLE)
    nxt = re.search(r'^section "', text[start + 10:], re.MULTILINE)
    if nxt:
        return text[start:start + 10 + nxt.start()]
    # LAST section: bound at the receipt write, which is where the parallel
    # driver's extractor stops. An unbounded slice would drag the summary code
    # into every assertion below.
    tail = text[start:]
    stop = re.search(r'\nemit_summary\n', tail)
    return tail[:stop.start()] if stop else tail


def test_the_section_exists_and_is_numbered_as_a_chunk():
    """A numbered marker makes it its own chunk; without one it hides inside §92."""
    text = H.RUN_SH.read_text()
    markers = re.findall(r'^# ---- (\d+)\.', text, re.MULTILINE)
    assert markers, "no numbered section markers found in run.sh"
    idx = text.find('section "%s"' % SECTION_TITLE)
    before = text[:idx]
    assert re.search(r'^# ---- \d+\.[^\n]*\n(?:[^\n]*\n){0,3}section "pytest suite"',
                     before[-400:] + text[idx:idx + 200], re.MULTILINE), (
        "the pytest section carries no '# ---- N.' marker directly above it — "
        "the parallel driver counts those markers, so it would be swallowed by "
        "the previous section's chunk")


def test_parallelism_is_two_workers_never_four():
    block = _strip_comments(_section_block())
    assert "-n 2" in block, (
        "the gate no longer pins -n 2 — four workers exhausted the pids cap and "
        "reddened 17 healthy tests with jemalloc EAGAIN")
    for bad in ("-n 4", "-n auto", "--numprocesses=4"):
        assert bad not in block, (
            "%r is back in the gate — that is the invocation measured to fail "
            "on this box" % bad)


def test_slow_legs_are_deselected():
    block = _strip_comments(_section_block())
    assert '-m "not slow"' in block or "-m 'not slow'" in block, (
        "the gate no longer deselects `slow` — those legs drive "
        "`run.sh --chunk N`, i.e. a nested battery inside the battery")


def test_the_lock_path_is_redirected_away_from_the_parent():
    block = _strip_comments(_section_block())
    assert "OC_BATTERY_LOCK=" in block, (
        "the nested run inherits the parent's lock path — conftest resolves it "
        "at import, and this process HOLDS that flock, so every serial leg "
        "would wait 900 s and then SKIP (a hole reading as green)")
    # The redirect must land on an explicit /tmp path. TMPDIR is the per-run
    # scratch root, and a lock inside it fails the suite's own "lock is not
    # derived from TMPDIR" leg. Two shapes are legitimate: the literal inline,
    # or a variable assigned a /tmp path and then exported — so resolve the
    # variable rather than insisting on one spelling.
    targets = re.findall(r'OC_BATTERY_LOCK=(\S+)', block)
    assert targets, "no OC_BATTERY_LOCK assignment found in the section body"
    resolved = []
    for t in targets:
        t = t.strip('"\'')
        m = re.fullmatch(r'\$\{?(\w+)\}?', t)
        if m:
            var = m.group(1)
            got = re.search(r'^\s*%s=(\S+)' % re.escape(var), block, re.MULTILINE)
            t = got.group(1).strip('"\'') if got else ""
        resolved.append(t)
    assert all(r.startswith("/tmp/") for r in resolved), (
        "the redirected lock path(s) %r are not explicit /tmp paths — deriving "
        "one from the per-run TMPDIR breaks mutual exclusion (the #171 trap)"
        % (resolved,))


def test_a_nonzero_rc_reaches_the_fail_accumulator():
    block = _strip_comments(_section_block())
    assert re.search(r'\bbad\s+"pytest suite', block), (
        "a failing pytest run does not call bad() — its rc is decorative and the "
        "gate would stay green through any pytest regression")


def test_the_section_runs_before_the_receipt_write():
    """A section after `verdict=PASS` extracts to an EMPTY chunk in --jobs mode."""
    text = H.RUN_SH.read_text()
    idx = text.find('section "%s"' % SECTION_TITLE)
    receipt = text.find("\nemit_summary\n")
    assert receipt > 0, "emit_summary call not found — the receipt writer moved"
    assert idx < receipt, (
        "the pytest section sits AFTER the receipt write — in parallel mode its "
        "chunk extracts empty and the suite silently never runs")
