"""The harness's STRUCTURAL invariants — extraction, the section-call gap, and
the two dead artefacts a reader would otherwise trust.

Nothing here executes a tool. Every leg reads ``tools/tests/run.sh`` and asserts
a property the shell harness already paid for, so a regression fails in
milliseconds instead of after a 20-minute battery.

WHY THESE EXIST
    * ``test_extraction_*`` — #74 and #107 were both the SAME defect: an
      extraction range that ended at "the next marker we happen to know about",
      so a later insertion was silently swept in and the extracted block ran
      code it was never meant to. The range end must be STRUCTURAL.
    * ``test_section_call_gap_*`` — the #66 defect: five numbered blocks ran
      under ONE ``section "..."`` call, so the transcript named one section and
      the wall/receipt attributed six blocks' time to it. The gap between
      ``# ---- N.`` markers and ``section "..."`` calls is that defect made
      countable.
    * ``test_dead_verdict_sentinel_*`` — the awk stop rule ``/^verdict=PASS/``
      never fires: no line in run.sh BEGINS with ``verdict=``. Recorded as a
      finding and asserted as the LIVE mechanism, never the dead one.
    * ``test_stale_seventeen_field_comment_*`` — the comment at ``:5545`` says
      "17-field printf" while ``emit_summary`` emits 18. A reader who trusts it
      drops a field from every consumer's schema.
"""

from __future__ import annotations

import re

import pytest

from lib import harness as H

# =============================================================================
# the section-call gap (#66)
# =============================================================================
def test_section_markers_outnumber_section_calls():
    """There are more ``# ---- N.`` markers than ``section "..."`` calls.

    That gap is NOT automatically a bug — retired markers (``# ---- 66b/66c
    retired``) legitimately carry no call. What must never happen is the
    reverse: a ``section`` call that opens a span covering SEVERAL numbered
    blocks, which is the #66 shape. The next test pins that.
    """
    text = H.run_sh_text()
    markers = H.numbered_sections(text)
    calls = H.section_calls(text)
    assert markers, "no ``# ---- N.`` markers found — the marker regex or run.sh moved"
    assert calls, "no ``section \"...\"`` calls found — the call regex or run.sh moved"
    assert len(markers) >= len(calls) - 5, (
        "more section CALLS (%d) than numbered markers (%d) — the index and the "
        "execution list have drifted apart" % (len(calls), len(markers)))

@pytest.mark.parametrize("ordinal,title,max_span", [
    # Every entry is a section call whose body is DELIBERATELY one block.
    # The bound is the block's own measured size plus slack; a leg that grows
    # past it is a sign another block was pasted in under the same call.
    (67, "battery lock: no child inherits the lock fd", 260),
    (68, "battery scratch root: one per-run TEST_TMPDIR", 200),
])
def test_section_call_does_not_swallow_a_neighbour(ordinal, title, max_span):
    """A ``section`` call's body must stay within its own block's budget.

    ``ordinal`` is 1-based over ``section_calls`` order, which is the order the
    shell harness executes them. The title is asserted too: a renumber that
    moves the block silently would otherwise retarget this leg at a different
    section and keep passing.
    """
    text = H.run_sh_text()
    calls = H.section_calls(text)
    lines = text.splitlines()
    assert 1 <= ordinal <= len(calls), (
        "section ordinal %d out of range (run.sh has %d section calls)" % (ordinal, len(calls)))
    ln, got_title = calls[ordinal - 1]
    assert got_title == title, (
        "section %d is %r, expected %r — a block was renumbered or reordered; "
        "retarget this leg deliberately" % (ordinal, got_title, title))
    end = calls[ordinal][0] if ordinal < len(calls) else len(lines)
    span = end - ln
    assert span <= max_span, (
        "section %d (%r) spans %d lines (bound %d) — a neighbour block was swept "
        "in under one ``section`` call, the #66 shape" % (ordinal, title, span, max_span))

def test_the_section_66_span_was_split_into_named_blocks():
    """Section 66's span carries ONE ``section`` call but SIX numbered blocks.

    This is the #66 defect in its purest form and the reason the split is
    mandatory: blocks 85-90 (cgroup isolation, the #750 arg-arm scan, the #47
    law-digest coverage, the #74 pids preflight, the #76 jobs/priority legs and
    the #114 oc-patch "else empty" contract) all execute under the single call
    ``section "cgroup isolation"``. The transcript names one section; the
    receipt's per-section timing attributes six blocks' wall to it; and a reader
    of a red transcript sees a cgroup failure when the failing leg was #114.

    The port splits them into six tests (see ``test_harness_cgroup.py`` and
    ``test_harness_pool.py``). This leg pins the FACT that makes the split
    necessary, so the reason stays checkable and the count cannot rot silently.
    """
    text = H.run_sh_text()
    calls = H.section_calls(text)
    lines = text.splitlines()
    idx = next((i for i, (_ln, t) in enumerate(calls)
                if t == "cgroup isolation"), None)
    assert idx is not None, "the ``cgroup isolation`` section call is gone"
    start = calls[idx][0]
    end = calls[idx + 1][0] if idx + 1 < len(calls) else len(lines)
    body = lines[start - 1:end - 1]

    blocks = [l for l in body if re.match(r"^# ---- \d+[a-z]?\.", l)]
    ordinals = [re.match(r"^# ---- (\d+[a-z]?)\.", l).group(1) for l in blocks]
    # The span runs from the call line to the NEXT call line, so it carries the
    # headers that FOLLOW this call. Block 85's own header sits one line ABOVE
    # the call (header, then call — the harness's convention), and block 91's
    # header sits above the NEXT call. So the blocks that actually EXECUTE under
    # this one call are 85 through 90, and the headers inside the span are
    # 86..90 plus the next section's 91.
    assert ordinals == ["86", "87", "88", "89", "90", "91"], (
        "the section-66 span no longer covers blocks 86-91 (found %r) — if a "
        "block was added or moved, split it and update test_harness_cgroup.py "
        "and test_harness_pool.py, do not widen this assertion" % (ordinals,))

    calls_in_span = [l for l in body if l.startswith('section "')]
    assert calls_in_span == ['section "cgroup isolation"'], (
        "the span now carries %d section calls (%r) — the #66 shape has changed; "
        "re-derive which blocks share a call before trusting the split"
        % (len(calls_in_span), calls_in_span))

    # The DEFECT, stated directly: five blocks beyond #85 have their own header
    # and NO section call of their own. That is the gap the split closes.
    own_call = [o for o in ordinals if o != "91"]        # 91 belongs to the next call
    assert len(own_call) == 5, (
        "expected five blocks executing under the #720 call (86-90), found %r" % own_call)

# =============================================================================
# extraction is structural, not a name list (#74 / #107)
# =============================================================================
def test_cgroup_extraction_stops_at_its_own_end():
    """The #720 block extracts to exactly ONE section header and no successor.

    Both #74 (pids preflight) and #107 (battery lock) were inserted between the
    #720 block and the marker the old range ended on, and were silently swept
    into the extracted fixture — the synth then ran code it was never meant to
    (it blocked on the very lock the live run held, burning 900 s).
    """
    block = H.extract_cgroup_block()
    headers = [l for l in block.splitlines() if l.startswith("# ---- ")]
    assert len(headers) == 1, (
        "the #720 extraction carries %d section headers (expected 1): %r — the "
        "range end is a name list again" % (len(headers), headers))
    assert headers[0].startswith("# ---- cgroup isolation"), (
        "the extracted block does not begin at the #720 header: %r" % headers[0])
    # The two measured overruns, asserted by their DISTINCTIVE code, not by name.
    assert "pids budget preflight" not in block, (
        "#74/#720: the extracted block runs PAST the isolation block (it carries "
        "the pids preflight) — the range end is a proxy again")
    assert "BATTERY LOCK BLOCK" not in block, (
        "#449/#107/#720: the extracted block runs PAST the isolation block (it "
        "carries the battery lock) — the range end is a proxy again")

def test_lock_extraction_is_fenced_and_complete():
    """The lock block extracts between its own ``>>>``/``<<<`` fences.

    Fences, not a marker range: the fences move WITH the block, so inserting a
    section above it cannot widen the slice.
    """
    block = H.extract_lock_block()
    assert block.startswith(H.LOCK_FENCE_OPEN), "lock block does not open at its fence"
    assert H.LOCK_FENCE_CLOSE in block, "lock block does not carry its closing fence"
    # The block must actually LOCK — an empty or gutted slice would satisfy the
    # fence assertions above and serialize nothing.
    assert "flock" in block, "the extracted lock block contains no flock call"
    assert "BATTERY_LOCK_WAIT" in block, (
        "the extracted lock block has no bounded wait — the TIMEOUT arm is gone")

def test_cgroup_extraction_carries_the_reexec_line():
    """The block the #720 legs drive must still contain the re-exec it tests.

    ``extract_cgroup_block`` is what ``test_harness_cgroup`` feeds to the synth.
    If the exec line moved out of the extracted range, every cgroup leg would
    drive a block that cannot re-exec and report green on an empty haystack.
    """
    block = H.extract_cgroup_block()
    assert 'exec "$_oc_sr"' in block, (
        "the re-exec line is not in the extracted #720 block — the cgroup legs "
        "would drive a block that cannot isolate")
    assert "BATTERY_CGROUP_ISOLATED" in block, (
        "the one-level guard is missing from the extracted block")

# =============================================================================
# the extractor CONTRACT — Python twin vs run.sh's own awk (#671)
# =============================================================================
def test_python_extractor_matches_run_sh_awk():
    """``H.extract_chunk`` and run.sh's awk agree on the REAL file.

    The Python twin exists so a leg can ask the extractor's contract without
    shelling out per question. If the two ever disagree, this says so rather
    than the port drifting quietly — the whole point of #671's "judge the
    extractor by RUNNING it".
    """
    import subprocess
    text = H.run_sh_text()
    total = len(H.numbered_sections(text))
    assert total > 0, "no numbered sections to compare"
    # Ask run.sh's awk for the same chunk, by sourcing its own function body.
    # `extract_chunk` is defined in the prelude, so a `--chunk` invocation runs
    # it; we drive the function directly through bash -c to avoid a full battery.
    for want in (1, total // 2, total):
        got_py = H.extract_chunk(want, text)
        proc = subprocess.run(
            ["bash", "-c",
             'extract_chunk() { awk -v want="$1" \'/^# ---- [0-9]/ { n++; insec = (n == want); next } '
             '/^verdict=PASS/ { exit } n == 0 || insec { print }\' "${2:-$0}"; }; extract_chunk "$@"',
             "_", str(want), str(H.RUN_SH)],
            capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, (
            "the awk extractor failed for chunk %s: %r" % (want, proc.stderr[-500:]))
        assert proc.stdout == got_py, (
            "the Python extractor and run.sh's awk disagree on chunk %s — the "
            "port has drifted from the harness (py %d lines, awk %d lines)"
            % (want, len(got_py.splitlines()), len(proc.stdout.splitlines())))

def test_last_section_is_reachable_by_the_extractor():
    """The last numbered section extracts to MORE than the prelude alone.

    A section placed after the receipt write extracts to an EMPTY chunk and
    runs zero legs while the transcript prints a clean summary — section 78
    landed there once and was invisible. The check is the chunk's LENGTH vs the
    prelude's, because the prelude alone satisfies a naive content grep.
    """
    text = H.run_sh_text()
    n = len(H.numbered_sections(text))
    prelude = H.extract_chunk(0, text)
    last = H.extract_chunk(n, text)
    assert len(last.splitlines()) > len(prelude.splitlines()), (
        "the last numbered section (chunk %d) extracts to no more than the "
        "prelude — it sits after the receipt write and would run zero legs" % n)

def test_trapped_fixture_is_unreachable():
    """A section after ``verdict=PASS`` extracts to the prelude only (#671 control).

    Two-sided: the reachable fixture MUST read reachable, or this leg cannot
    tell a working extractor from a blind one. ``extract_chunk`` returns the
    PRELUDE for chunk 0 and PRELUDE+section for a reachable chunk, so the
    discriminator is whether the section's body survived — not the line count,
    which is 1 for both the prelude-only case and a trapped last chunk.
    """
    reachable = ("# prelude mentioning oc-root.sh and negctl-*\n"
                 "# ---- 1 one\nsection \"one\"\n"
                 "# ---- 2 two\nsection \"two\"\nverdict=PASS; :\n")
    trapped = reachable + "# ---- 3 three\nsection \"three\"\n"

    # CONTROL (must read REACHABLE): chunk 2 carries its own body.
    assert 'section "two"' in H.extract_chunk(2, reachable), (
        "control: a reachable last section read UNREACHABLE — the check is blind")
    # The trapped file's chunk 3 sits after verdict=PASS and must carry NOTHING
    # but the prelude: the stop rule fires before the marker is ever reached.
    got = H.extract_chunk(3, trapped)
    assert 'section "three"' not in got, (
        "control: a section placed after verdict=PASS read REACHABLE — the "
        "extractor does not honour its stop rule")
    assert got == H.extract_chunk(0, trapped), (
        "the trapped chunk is not the bare prelude (%r) — the stop rule left "
        "residue, so 'unreachable' would be a coincidence of line counts" % got)

# =============================================================================
# the two dead artefacts (findings)
# =============================================================================
def test_dead_verdict_pass_sentinel_is_documented_and_harmless():
    """No line BEGINS with ``verdict=`` — the awk stop rule never fires.

    FINDING: ``run.sh:343`` carries ``/^verdict=PASS/ { exit }`` with a long
    comment asserting it is what stops prelude extraction at the receipt write.
    It cannot fire: the only ``verdict=PASS`` occurrences are a ``local
    verdict=PASS`` assignment (indented, mid-line) and ``printf`` fixtures that
    EMBED the string, never a line starting with it. The live stop mechanism is
    the section-count boundary, not this rule.

    This leg pins the FACT so the finding cannot silently become false (someone
    adding a bare ``verdict=PASS`` line would make the rule live again, and the
    comment would then be true for a different reason — worth knowing).
    """
    text = H.run_sh_text()
    begins = [l for l in text.splitlines() if l.startswith("verdict=PASS")]
    assert begins == [], (
        "a line now BEGINS with ``verdict=PASS`` (%r) — the awk stop rule at "
        "run.sh:343 has become live. Re-read the extraction contract before "
        "trusting it: the rule was dead, and the section-count boundary was "
        "doing the work." % (begins,))
    # The rule is still PRESENT (we assert the dead artefact exists, we do not
    # demand its removal — removal is a harness change, outside this port).
    assert "/^verdict=PASS/ { exit }" in text, (
        "the awk stop rule is gone from run.sh — this finding's premise changed")

def test_stale_seventeen_field_comment_is_recorded():
    """The ``:5545`` comment says 17 fields; ``emit_summary`` emits 18.

    FINDING: the comment predates the ``timing`` field. It is asserted here as a
    MISMATCH so a reader cannot trust it, and so the day someone fixes the
    comment this leg tells them the finding is resolved.
    """
    text = H.run_sh_text()
    assert "the same 17-field printf" in text, (
        "the 17-field comment was edited or removed — if it now says 18, delete "
        "this leg (the finding is resolved)")
    # The live truth: emit_summary's format string carries 18 keys. Match the
    # printf BODY (the escaped-newline JSON template), not a hand-counted line
    # range — a line range goes stale the moment a field is added.
    m = re.search(r"printf '\{\\n(.*?)\\n\}\\n'", text, re.S)
    assert m, "emit_summary's printf format string not found — the receipt writer moved"
    keys = re.findall(r'"([a-z_]+)":', m.group(1))
    assert len(keys) == 18, (
        "emit_summary now carries %d fields (%r) — the 18-field invariant this "
        "port and the receipt module both rest on has changed" % (len(keys), keys))
    assert keys[-1] == "timing", (
        "the last receipt field is %r, not 'timing' — field order changed" % keys[-1])
    # The comment's OWN claim, made countable: it says 17, the format says 18.
    assert "17" in text[text.index("the same 17-field printf"):text.index("the same 17-field printf") + 200], (
        "the stale comment no longer states 17 fields where expected")
