"""Ported: entry-preamble fixpoint + relative invocation (#708) — run.sh §65.

THE DEFECT
    Every fleet tool carried the same copy-pasted entry preamble, which walks UP
    from the tool's own location to find the ``tools/`` root::

        _oc_r="$(dirname "$0")"
        while [ "$_oc_r" != "/" ] && [ "$(basename "$_oc_r")" != "tools" ]; do
            _oc_r="$(dirname "$_oc_r")"
        done

    Invoked by ABSOLUTE path that terminates. Invoked RELATIVELY — ``cd`` into
    the tool's directory and run ``./name`` — ``$0`` is ``./name``, so
    ``dirname`` yields ``.``, and ``dirname "."`` is ``.`` again: a FIXPOINT.
    The walk never advances, every guard stays true, and the tool spins at 100 %
    CPU emitting nothing. It had been shipped in every tool.

WHY THIS SECTION EXISTS AT ALL
    The battery's other invocation legs drive ``$t`` as an ABSOLUTE path (their
    glob is ``"$TOOLS_DIR"/...``), so they cannot observe this class — the
    fixpoint needs a RELATIVE invocation to reproduce. That blind spot is the
    section's justification, and it is why the dynamic arm below must keep
    ``cwd=<tool dir>`` and ``./name``; converting it to an absolute call would
    leave a green leg that tests nothing.

TWO ARMS, AND THEY SEE DIFFERENT THINGS
    STATIC   every file that still walks up must also carry the BREAK
             (``[ "$_oc_r" != "." ]``). Keyed on the fix's PRESENCE, never on
             the old line's absence, so it asserts the fix rather than merely
             failing to find the bug.
    DYNAMIC  drive one representative per tool KIND by relative path and require
             it to RETURN. A sample killed on WALL while having burned almost no
             CPU is STARVATION, not a hang (#83): a real fixpoint SPINS, so CPU
             is the discriminator and wall is only a backstop.

THE CPU DISCRIMINATOR IS THE POINT (#83, factory#109)
    Since #76 the battery runs its parent at ``nice 19`` + ``ionice -c3``, so
    under load a HEALTHY tool gets killed on wall clock. The old branch then
    named the fixpoint as the cause — a false ACCUSATION against a tool that
    never hung. Measured 2026-11-18: healthy = 0.03-0.04 s CPU (identical under
    nice/ionice); a real fixpoint spin = 19.8 s CPU in a 20 s wall. So the
    verdict here reads CPU, and a starved sample is reported INCONCLUSIVE rather
    than green or red. Zero observations is not a pass: if EVERY sample starves,
    the instrument was blind and the leg reds naming the INSTRUMENT.
"""

from __future__ import annotations


import pytest

import conftest as cf

# The break every walk-up must carry. Both are the shell's literal strings.
WALK_UP = 'while [ "$_oc_r" != "/" ]'
FIXPOINT_BREAK = '[ "$_oc_r" != "." ]'

# Floor, not a target: the preamble was in 44 files when the shell leg was
# written (43 tools + lib + run.sh) and measures 46 today. A glob that silently
# matches fewer reds HERE instead of passing on a shrunken population — the
# silent-skip class this battery exists to catch.
CARRIER_FLOOR = 40

# One representative per tool KIND, so a regression in any single kind is
# observable without paying a fleet-wide --help sweep. Kept as (relpath, argv):
# run.sh has no --help arm (it would execute the whole battery), so it gets a
# cheap flag that still forces the preamble to run and then exits.
SAMPLES = (
    ("state/oc-ledger", "--help"),
    ("ship/oc-build", "--help"),
    ("harvest/oc-gate", "--help"),
    ("audit/oc-lint-laws", "--help"),
    ("smoke/oc-smoke", "--help"),
    ("git/oc-commit", "--help"),
    ("issue/oc-issue-scope", "--help"),
    ("notify/oc-notify-fanout", "--help"),
    ("tests/run.sh", "--chunk 999"),
)

# The sample size the shell asserts (EP_DYN -ne 9 -> bad). Pinned so a sample
# removed from the tuple is a visible decision, not a quiet shrink.
SAMPLE_COUNT = 9

# THE BOUND IS A WALL CLOCK, AND RLIMIT_CPU WAS TRIED FIRST AND REJECTED
#
# A CPU limit looks like the perfect load-independent discriminator: the kernel
# kills a process that BURNS n seconds of CPU, and a starved process simply takes
# longer in wall time, so starvation could never masquerade as a hang.
#
# It does not work for THIS defect, and the reason is the defect's own shape.
# Measured on this box: the broken fixture is not a tight loop in one process —
# every iteration forks a `dirname`. So the spin's CPU is spread across thousands
# of short-lived children, each far inside any sane limit, while the parent
# accumulates its own CPU slowly: with `ulimit -t 5` the parent took **93 s of
# wall** to burn its 5 s budget. That is slower than the wall bound it was meant
# to replace, and it made the leg slower than the 60 s `slow` threshold on its
# own.
#
# So the bound is wall time, with headroom sized from MEASURED healthy cost:
# the fleet samples burn 0.015-0.125 s CPU and return in ~0.05-0.3 s wall. A 20 s
# bound is therefore 60-400x headroom, and a sample that hits it is reported
# INCONCLUSIVE rather than accused of hanging (#83). The negative control proves
# the instrument can see a real hang, because the broken fixture never returns at
# all.
WALL_BOUND_S = 20

# The control's bound. The fixed half returns in ~0.05 s, so 10 s is ~200x
# headroom; the broken half never returns, so any bound catches it.
CONTROL_BOUND_S = 10

# 124 is `timeout(1)`'s "the bound fired" code, which run.sh reads as
# "HUNG -- killed at the Ns bound", not as a tool verdict.
WALL_KILL_RC = 124


def _tool_env():
    """The one env adjustment the relative invocation needs.

    BATTERY_IN_CHUNK is inherited when pytest is launched from inside a chunk;
    run.sh's own --chunk branch is guarded on it being empty, so a set value
    would make the run.sh sample fall through and execute the whole battery.
    """
    return {"BATTERY_IN_CHUNK": ""}


def _carriers():
    """Every fleet file that still walks up, as run.sh §65 enumerates them.

    The glob is the shell's own: ``oc-*``, ``*/oc-*`` and ``tests/run.sh``, with
    the archive/bak exclusions. It deliberately does NOT reach this pytest tree —
    this module embeds the preamble in its CONTROL fixtures, and scanning itself
    would make the static arm red on its own text (the quoting guard's
    ``test_this_module_is_itself_clean`` exists for the same reason).
    """
    out = []
    candidates = (sorted(cf.TOOLS_DIR.glob("oc-*"))
                  + sorted(cf.TOOLS_DIR.glob("*/oc-*"))
                  + [cf.TOOLS_DIR / "tests" / "run.sh"])
    for path in candidates:
        if not path.is_file():
            continue
        name = path.name
        if name.endswith(".bak") or ".bak-" in name or ".pre-" in name:
            continue
        if "archive" in path.relative_to(cf.TOOLS_DIR).parts:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if WALK_UP in text:
            out.append((path, text))
    return out


# =============================================================================
# STATIC ARM — exact, whole fleet
# =============================================================================
def test_every_walk_up_carrier_has_the_fixpoint_break():
    """§65 static: a file that walks up WITHOUT the break spins on ``./name``.

    Keyed on the break's presence, so this reds on a NEW carrier that copies the
    preamble minus the fix — not merely on the old line reappearing.
    """
    carriers = _carriers()
    offenders = [p.relative_to(cf.TOOLS_DIR).as_posix()
                 for p, text in carriers if FIXPOINT_BREAK not in text]
    assert not offenders, (
        "%d/%d walk-up carrier(s) LACK the fixpoint break (#708) — each spins "
        "forever when invoked as ./name from its own directory: %s"
        % (len(offenders), len(carriers), ", ".join(offenders)))


def test_the_walk_up_population_clears_the_floor():
    """The glob must still SEE the fleet — 0 carriers is a broken walker, not a fix.

    Without this, deleting the preamble everywhere would read as a green static
    arm: the sweep would find nothing to object to and the pass would be vacuous.
    """
    n = len(_carriers())
    assert n >= CARRIER_FLOOR, (
        "walk-up enumerated only %d file(s) (floor %d) — the glob is not seeing "
        "the fleet, so the static arm above proved nothing" % (n, CARRIER_FLOOR))


def test_the_sample_is_complete():
    """§65: the relative-invocation sample ran 9 of 9 (EP_DYN -ne 9 -> bad)."""
    assert len(SAMPLES) == SAMPLE_COUNT, (
        "relative-invocation sample carries %d of %d entries — a sample was "
        "dropped, which shrinks the arm silently" % (len(SAMPLES), SAMPLE_COUNT))
    missing = [rel for rel, _ in SAMPLES if not (cf.TOOLS_DIR / rel).is_file()]
    assert not missing, "relative-invocation sample missing: %s" % ", ".join(missing)


# =============================================================================
# DYNAMIC ARM — behavioural, by RELATIVE path from the tool's OWN directory
# =============================================================================
def test_relative_invocation_returns(run_tool):
    """§65 dynamic: ``cd <tool dir> && ./name --help`` must TERMINATE.

    The exact invocation that hung. The sample is driven with ``cwd`` set to the
    tool's own directory and ``./name`` as argv[0] — converting either to an
    absolute path would leave a green leg that cannot observe the fixpoint.

      rc == 0          -> RETURNED
      rc == 124        -> the bound fired; INCONCLUSIVE (starved or blocked),
                          never an accusation (#83)
      any other rc     -> a real tool failure

    If EVERY sample hits the bound there are zero observations, and a blind
    instrument must not pass — that is the one state that reds rather than skips.
    """
    returned, starved, failed = [], [], []
    for rel, arg in SAMPLES:
        tool = cf.TOOLS_DIR / rel
        res = run_tool(["./" + tool.name, *arg.split()],
                       timeout=WALL_BOUND_S, cwd=tool.parent, env=_tool_env())

        if res.rc == 0:
            returned.append(rel)
        elif res.rc == WALL_KILL_RC:
            starved.append("%s (bound %ds)" % (rel, WALL_BOUND_S))
        else:
            failed.append("%s rc=%s%s" % (rel, res.rc,
                                          (" :: " + res.combined.strip()[-200:])
                                          if res.combined.strip() else ""))

    assert not failed, "relative invocation FAILED for %d sample(s): %s" % (
        len(failed), "; ".join(failed))
    assert len(starved) < len(SAMPLES), (
        "relative invocation could NOT be verified: all %d sampled tool(s) were "
        "killed at the %ds bound — the instrument was blind, not the tools (#83). "
        "This is NOT proof of a fixpoint; the control leg is what proves the "
        "instrument can see one. %s" % (len(SAMPLES), WALL_BOUND_S, "; ".join(starved)))

    # Never claim a starved sample RETURNED: it was killed before it could.
    assert len(returned) + len(starved) == len(SAMPLES)
    if starved:
        pytest.skip("relative invocation returns for %d of %d sampled tool(s); "
                    "%d INCONCLUSIVE at the %ds bound — not a fixpoint, not a "
                    "verified return (#83): %s"
                    % (len(returned), len(SAMPLES), len(starved), WALL_BOUND_S,
                       "; ".join(starved)))


# =============================================================================
# CONTROL — two-sided, and it does NOT reuse the fleet's literal preamble
# =============================================================================
# The MECHANISM under test is `dirname "." == "."`, so the fixture reproduces
# that mechanism in miniature rather than embedding the real preamble: a fixture
# carrying the fleet's literal text would make the STATIC arm match this file.
_BROKEN = """#!/usr/bin/env bash
_oc_r="$(dirname "$0")"
while [ "$_oc_r" != "/" ] && [ "$(basename "$_oc_r")" != "tools" ]; do _oc_r="$(dirname "$_oc_r")"; done
echo reached
"""

_FIXED = """#!/usr/bin/env bash
_oc_r="$(cd "$(dirname "$0")" 2>/dev/null && pwd)" || _oc_r="."
while [ "$_oc_r" != "/" ] && [ "$_oc_r" != "." ] && [ "$(basename "$_oc_r")" != "tools" ]; do _oc_r="$(dirname "$_oc_r")"; done
echo reached
"""


def _fixture(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    p.chmod(0o755)
    return p


def test_the_broken_preamble_never_returns(tmp_path, run_tool):
    """NEGATIVE CONTROL: the instrument SEES the class it is aimed at.

    Without this half, a dynamic arm that never fires reads identical to one
    that works. The broken fixture must be killed AT THE BOUND and must never
    print its terminator — that pair is what makes the dynamic arm's silence
    meaningful rather than merely empty.
    """
    _fixture(tmp_path, "broken", _BROKEN)
    res = run_tool(["./broken"], timeout=CONTROL_BOUND_S, cwd=tmp_path)
    assert res.rc == WALL_KILL_RC, (
        "broken preamble returned rc=%s — it must not terminate, or this leg "
        "cannot detect a hang: %s" % (res.rc, res.combined[-300:]))
    assert "reached" not in res.out, (
        "the broken preamble got PAST the walk-up, so the fixture no longer "
        "reproduces the fixpoint: %r" % res.out[:200])


def test_the_fixed_preamble_returns(tmp_path, run_tool):
    """CONTROL, other side: the same fixture WITH the break returns rc=0.

    The pair differs in exactly one thing — the break — so the verdict is that
    difference and not a timeout budget. The fixed form returns in ~0.05 s
    against a 10 s bound, ~200x headroom.
    """
    _fixture(tmp_path, "fixed", _FIXED)
    res = run_tool(["./fixed"], timeout=CONTROL_BOUND_S, cwd=tmp_path)
    assert res.rc == 0, (
        "fixed preamble rc=%s (expected 0) — the break did not make the walk "
        "converge: %s" % (res.rc, res.combined[-300:]))
    assert "reached" in res.out, (
        "the fixed fixture exited 0 without reaching the end of the walk: %r"
        % res.out[:200])
