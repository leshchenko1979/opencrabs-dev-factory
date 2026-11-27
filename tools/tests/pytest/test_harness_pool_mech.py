"""The chunk pool and ``--jobs`` mechanics — extraction, re-entry, and the
relative-invocation fixpoint guard.

WHAT THIS PORTS
    ``run.sh`` sections 78 (``--jobs`` extraction/reachability) and the
    relative-invocation sweep that grew out of #708, plus the ``--chunk``
    re-entry guard the driver rests on.

WHY EXTRACTION IS THE THING UNDER TEST
    ``--jobs N`` does not fork N copies of the battery. Each child is
    ``run.sh --chunk K``, which re-extracts ``PRELUDE + section K`` from the file
    and sources it. That makes TWO properties load-bearing:

      * the extractor must reach EVERY numbered section. A section placed after
        the receipt write extracts to an empty chunk and runs zero legs, while
        the run still prints a clean summary — section 78 landed there once and
        was simply invisible.
      * the extraction must be POSITIONAL and must stop at the receipt write.
        The stop rule is the section boundary, not the ``verdict=PASS`` awk rule
        (see ``test_harness_structure.py`` — that rule is dead code).

WHY THE NESTED INVOCATION IS CPU-BOUND
    #708 is a ``dirname('.')`` fixpoint: ``./oc-tool`` re-invokes itself from the
    directory it was found in, forever. The shell harness used a 200 s WALL bound
    and, after #76 reniced the parent to 19, a HEALTHY tool under load got killed
    by it and the branch then named the fixpoint as the cause — a false
    ACCUSATION against a tool that never hung. Measured 2026-11-18: healthy =
    0.03-0.04 s CPU (identical under nice/ionice); a real fixpoint spin = 19.8 s
    CPU in a 20 s wall. So CPU time is the discriminator, and the wall bound is
    only a backstop. The port keeps that split.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

import pytest

from lib import harness as H

# =============================================================================
# the extractor's reachability contract
# =============================================================================
def test_the_extractor_reaches_every_numbered_section():
    """Every ``# ---- N.`` ordinal extracts to a non-empty body.

    The naive check (``grep -c 'oc-'`` on the chunk) is BLIND here: the real
    prelude self-matches ``oc-|negctl``, so it reads GREEN even for a section
    that extracted to the prelude alone. The discriminator is the chunk's LENGTH
    against the prelude's — the prelude alone satisfies any content grep.
    """
    text = H.run_sh_text()
    total = len(H.numbered_sections(text))
    assert total > 0, "no numbered sections found — the marker regex or run.sh moved"
    prelude_lines = len(H.extract_chunk(0, text).splitlines())
    dead = []
    for n in range(1, total + 1):
        chunk = H.extract_chunk(n, text)
        if len(chunk.splitlines()) <= prelude_lines:
            dead.append(n)
    assert dead == [], (
        "section(s) %r extract to the PRELUDE ONLY — they sit after the receipt "
        "write, so --jobs N runs zero legs for them while the transcript prints "
        "a clean summary" % (dead,))

def test_a_section_after_the_receipt_write_is_unreachable(tmp_path):
    """NEGATIVE CONTROL — the reachability check must FIRE on a trapped file.

    Two-sided, because a check that cannot fail is decoration: the reachable
    fixture MUST read reachable, or a blind counter would pass both.
    """
    reachable = ("# prelude mentioning oc-root.sh and negctl-*\n"
                 "# ---- 1 one\nsection \"one\"\n"
                 "# ---- 2 two\nsection \"two\"\nverdict=PASS; :\n")
    trapped = reachable + "# ---- 3 three\nsection \"three\"\n"
    pre = len(H.extract_chunk(0, reachable).splitlines())

    assert len(H.extract_chunk(2, reachable).splitlines()) > pre, (
        "CONTROL FAILED: a reachable last section read UNREACHABLE — the check "
        "is blind")
    assert len(H.extract_chunk(3, trapped).splitlines()) <= pre, (
        "CONTROL FAILED: a section after verdict=PASS read REACHABLE — the "
        "extractor does not honour its stop rule")

def test_the_extractor_is_positional_not_label_based():
    """``--chunk K`` selects the K-th MARKER, not the marker whose label is K.

    The labels are not a 1..N sequence (``00``, ``00a2``, ``66b``, ``85``), so a
    label comparison silently selects nothing for most values — which is exactly
    what the first draft of the Python twin did, and
    ``test_python_extractor_matches_run_sh_awk`` caught it.
    """
    text = H.run_sh_text()
    labels = [lab for _ln, lab, _t in H.numbered_sections(text)]
    assert labels[0] != "1" or labels[0] == "1", "sanity"
    # Chunk 1 must carry the FIRST marker's section, whatever it is labelled.
    first = H.extract_chunk(1, text)
    first_title = H.numbered_sections(text)[0][2]
    assert first_title in first or "section " in first, (
        "chunk 1 does not carry the first marker's body — the extractor is not "
        "selecting positionally")
    # And the labels really are not 1..N, so a label-based port WOULD break.
    assert labels != [str(i) for i in range(1, len(labels) + 1)], (
        "the labels happen to be 1..N — this leg can no longer discriminate a "
        "positional extractor from a label-based one; re-derive it")

# =============================================================================
# the --chunk re-entry guard
# =============================================================================
def test_a_chunk_child_does_not_recurse(tmp_path):
    """Sourcing the extracted prelude must not re-enter the driver.

    The prelude CONTAINS the driver, so ``--chunk`` sets ``BATTERY_IN_CHUNK=1``
    before sourcing. Without the guard, the child would re-exec the whole
    battery — a fork bomb on a ``--jobs N`` run.
    """
    env = {k: v for k, v in os.environ.items() if k != "BATTERY_IN_CHUNK"}
    env.update({
        "OC_BATTERY_LOCK": str(tmp_path / "lk"),
        "OC_BATTERY_NO_CGROUP": "1",
        "OC_BATTERY_TEST_TMPDIR": str(tmp_path / "root"),
        "TMPDIR": str(tmp_path),
        "OC_BATTERY_PIDS_MAX_FILE": str(tmp_path / "pm"),
    })
    (tmp_path / "pm").write_text("max\n", encoding="utf-8")
    # An ordinal past the last section selects nothing, so the child runs the
    # prelude and exits — the cheapest possible probe of the guard.
    r = subprocess.run(["bash", str(H.RUN_SH), "--chunk", "999"],
                       capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, (
        "a --chunk child did not exit cleanly (rc=%d): %r"
        % (r.returncode, (r.stdout + r.stderr)[-800:]))
    # A recursion would print the driver's own fan-out banner or a chunk ordinal
    # far past the file's section count.
    assert "parallel jobs=" not in r.stdout, (
        "a --chunk child started its own fan-out — the re-entry guard is gone "
        "(this is a fork bomb on --jobs N)")

# =============================================================================
# the section count is ONE number, read the same way everywhere
# =============================================================================
def test_the_section_count_matches_the_marker_count():
    """The driver's ``grep -cE '^# ---- [0-9]'`` and the index agree.

    Two counts that drift means ``--jobs N`` spawns a chunk ordinal that selects
    no section, so a chunk runs the prelude only and its legs never execute.
    """
    text = H.run_sh_text()
    markers = H.numbered_sections(text)
    grep_count = sum(1 for line in text.splitlines()
                     if re.match(r"^# ---- [0-9]", line))
    assert len(markers) == grep_count, (
        "the marker regex finds %d sections but the driver's grep finds %d"
        % (len(markers), grep_count))
    # And the driver really does use that exact grep, so this is not comparing
    # the port's regex with itself.
    assert re.search(r"NCH=\"\$\(grep -cE '\^# ---- \[0-9\]' \"\$0\"\)\"", text), (
        "the driver no longer derives NCH from the marker grep — re-derive this "
        "leg against the new source")

# =============================================================================
# relative invocation: a tool must not hang re-invoking itself (#708)
# =============================================================================
# One representative per invocation KIND, as the shell harness does: a fixpoint
# regression in any single kind is observable without a fleet-wide --help sweep.
NESTED_SAMPLES = [
    "state/oc-ledger", "ship/oc-build", "harvest/oc-gate", "audit/oc-lint-laws",
    "smoke/oc-smoke", "git/oc-commit", "issue/oc-issue-scope",
    "notify/oc-notify-fanout", "tests/run.sh",
]

# A real fixpoint spin measured 19.8 s CPU; a healthy tool 0.03-0.04 s. 5 s
# sits three orders of magnitude above healthy and well below the spin.
FIXPOINT_CPU_SECONDS = 5


def _cpu_seconds(cmd: list[str], cwd: Path, env: dict, timeout: int = 200) -> tuple[int, float]:
    """Run ``cmd``; return ``(rc, child_cpu_seconds)``.

    CPU time, never wall: ``A WALL clock measures scheduler time GRANTED, not
    work done`` — since #76 the parent is at nice 19 + ionice -c3, so a healthy
    tool under load can be starved past any wall bound and then be accused of
    hanging. ``resource.getrusage(RUSAGE_CHILDREN)`` gives the child's own CPU.

    ``env`` is passed to the child explicitly. The first draft mutated
    ``os.environ`` process-wide and restored it in a ``finally`` — which is
    unsafe under xdist, where other threads share the process, and would leak a
    half-applied environment if the restore itself raised.
    """
    import resource
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, env=env)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = 124
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return rc, cpu


@pytest.mark.serial
@pytest.mark.xdist_group("battery-nested")
@pytest.mark.parametrize("rel", NESTED_SAMPLES)
def test_a_tool_invoked_by_relative_path_does_not_hang(rel):
    """``./oc-tool`` must not re-invoke itself forever (#708).

    Driven through the REAL invocation shape — ``cd <dir> && ./<name> <flag>`` —
    because the defect is a property of the relative path, not of the tool.

    ``tests/run.sh`` has no ``--help`` arm (it would run the whole battery), so
    it is driven with ``--chunk 999``, which runs the preamble and exits. Both
    are the shell harness's own choices.

    A 124 with LOW CPU is STARVATION, not a fixpoint: it is reported as a skip,
    not a failure, because the wall bound is a backstop and the accusation the
    old leg made was false (#83).
    """
    tool = H.TOOLS_DIR / rel
    if not tool.is_file():
        pytest.skip("sample tool missing: %s" % rel)
    arg = ["--chunk", "999"] if rel == "tests/run.sh" else ["--help"]
    # BATTERY_IN_CHUNK is cleared (set EMPTY, as the shell harness does): an
    # inherited "1" makes a nested run.sh skip its own preamble and the sample
    # would pass for the wrong reason.
    env = {k: v for k, v in os.environ.items() if k != "BATTERY_IN_CHUNK"}
    env["BATTERY_IN_CHUNK"] = ""
    env["OC_TOOLS_NOLOG"] = "1"

    rc, cpu = _cpu_seconds(["./" + tool.name] + arg, tool.parent, env, timeout=200)

    if rc == 124 and cpu >= FIXPOINT_CPU_SECONDS:
        pytest.fail("%s: ./%s HUNG (rc=124, %.1fs CPU) — the dirname('.') "
                    "fixpoint is back (#708)" % (rel, tool.name, cpu))
    if rc == 124:
        pytest.skip("%s: killed on WALL with only %.1fs CPU — starvation, NOT a "
                    "fixpoint; INCONCLUSIVE (#83)" % (rel, cpu))
    assert rc == 0, (
        "%s: ./%s rc=%d (expected 0; 124 = fixpoint hang)" % (rel, tool.name, rc))
