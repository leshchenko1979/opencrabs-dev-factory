"""Ported: RC-contract table integrity (§44) + coverage (§45).

Both sections are scanners over ``tools/docs/RC-CONTRACT.md``, and both carry
their own positive AND negative controls, because a scanner that cannot fire
reports a perfect score. The controls are the load-bearing half: §44's escaped-
pipe row must still read as a six-pipe row while a bare pipe must be flagged,
and §45's dropped-row / invented-row fixtures must be seen.

The canary rows are built by INTERPOLATION, never written literally — a
literal well-formed ``| oc-…`` row in this file would be found by the live scan
as a real site (the same move run.sh's shell-quoting canary makes).
"""

from __future__ import annotations

import os
import re

import pytest

import conftest as cf

CONTRACT = cf.TOOLS_DIR / "docs" / "RC-CONTRACT.md"
PIPE = "|"
BS = "\\"

# --- §44: a 5-column row is exactly SIX unescaped pipes ----------------------


def _scan_rows(text):
    """(rows, bad) — bad is [(lineno, tool, unescaped_pipe_count)]."""
    rows = 0
    bad = []
    for i, ln in enumerate(text.split("\n"), 1):
        if not ln.startswith("| oc-"):
            continue
        rows += 1
        n = len(re.findall(r"(?<!\\)\|", ln))
        if n != 6:
            bad.append((i, ln.split("|")[1].strip(), n))
    return rows, bad


def test_escaped_pipe_stays_a_six_pipe_row():
    """POSITIVE control: an escaped pipe in the verdict cell must not count."""
    row = "%s oc-good %s 0 %s 1 %s a %s%s b %s 2700 %s" % (
        PIPE, PIPE, PIPE, PIPE, BS, PIPE, PIPE, PIPE)
    rows, bad = _scan_rows(row + "\n")
    assert rows == 1, "the canary row did not enumerate (rows=%d)" % rows
    assert not bad, "the scanner flagged an ESCAPED pipe — control broken: %r" % bad


def test_bare_pipe_is_flagged():
    """NEGATIVE control: a bare pipe in a cell splits the GFM column."""
    row = "%s oc-bad %s 0 %s 1 %s a %s b %s 2700 %s" % (
        PIPE, PIPE, PIPE, PIPE, PIPE, PIPE, PIPE)
    rows, bad = _scan_rows(row + "\n")
    assert rows == 1
    assert bad == [(1, "oc-bad", 7)], "the scanner cannot fire: %r" % (bad,)


def test_live_contract_table_is_clean():
    """FLOOR + the real assertion: the population is enumerated and no oc-* row
    carries an unescaped pipe. GFM DROPS the text after a stray pipe, so this is
    contract text a reader silently loses."""
    rows, bad = _scan_rows(CONTRACT.read_text(encoding="utf-8"))
    assert rows >= 40, \
        "only %d oc-* row(s) enumerated (floor 40) — the scan stopped covering " \
        "the table" % rows
    assert not bad, (
        "%d oc-* row(s) carry an unescaped pipe — GFM drops the text after it "
        "(#4): %r" % (len(bad), bad[:5]))


# --- §45: every executable has a row, every row has an executable -----------

SKIP_DIR = {"lib", "tests", "archive", "__pycache__", "docs", "instruments"}
# Library-resident rows: they document a shared library, not an executable of
# their own. Named explicitly so a THIRD one cannot join silently.
LIB_RESIDENT = {"oc-base-red", "oc-mutate"}


def _enumerate_exes():
    exes = set()
    for root, dirs, files in os.walk(cf.TOOLS_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR and not d.startswith(".")]
        for f in files:
            if not f.startswith("oc-") or ".bak" in f or ".pre-" in f:
                continue
            p = os.path.join(root, f)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                exes.add(f)
    return exes


def _enumerate_rows(text):
    return {ln.split("|")[1].strip()
            for ln in text.split("\n") if ln.startswith("| oc-")}


@pytest.fixture(scope="module")
def live_table():
    text = CONTRACT.read_text(encoding="utf-8")
    return text, _enumerate_exes(), _enumerate_rows(text)


def test_coverage_floors(live_table):
    """A scanner that enumerated nothing reports a perfect score."""
    _text, exes, rows = live_table
    assert len(exes) >= 45, "only %d executable(s) enumerated (floor 45)" % len(exes)
    assert len(rows) >= 45, "only %d register row(s) parsed (floor 45)" % len(rows)


def test_every_executable_has_a_row(live_table):
    """#139: an unregistered tool ships with undocumented exit codes and nothing
    reddens."""
    _text, exes, rows = live_table
    residue = sorted(exes - rows)
    assert not residue, (
        "%d executable(s) have NO register row — undocumented exit codes "
        "(#139): %s" % (len(residue), residue))


def test_no_phantom_rows(live_table):
    """A row naming a tool that does not exist is a contract claiming something
    false. Two rows are legitimately library-resident."""
    _text, exes, rows = live_table
    phantom = sorted(rows - exes - LIB_RESIDENT)
    assert not phantom, (
        "%d row(s) name a tool that does not exist (#139): %s"
        % (len(phantom), phantom))


def test_dropped_row_is_seen_as_residue(live_table):
    """POSITIVE control: remove a real row from a COPY and the same scanner must
    report it — otherwise the leg passes on a scanner that cannot fire."""
    text, exes, _rows = live_table
    assert "| oc-poll " in text, "oc-poll row is absent — pick another canary"
    dropped = "\n".join(ln for ln in text.split("\n")
                        if not ln.startswith("| oc-poll "))
    residue = sorted(exes - _enumerate_rows(dropped))
    assert "oc-poll" in residue, \
        "the coverage scanner cannot fire: a dropped oc-poll row went unseen"


def test_invented_row_is_seen_as_phantom(live_table):
    """POSITIVE control: a row for a nonexistent tool must be flagged."""
    text, exes, _rows = live_table
    ghost = text + "\n| oc-ghost-tool | 0 | 2 | 0 |\n"
    phantom = sorted(_enumerate_rows(ghost) - exes - LIB_RESIDENT)
    assert "oc-ghost-tool" in phantom, \
        "the phantom scanner cannot fire: an invented row went unseen"
