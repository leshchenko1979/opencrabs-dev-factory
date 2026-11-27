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

import resource

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

# A fixpoint spin burns seconds of CPU; a starved process is killed having
# burned almost none. 5 s is the shell's threshold and sits two orders of
# magnitude above a healthy sample's 0.015-0.125 s.
SPIN_CPU_S = 5.0

# Wall backstop. The shell uses 200 s; a real fixpoint is caught by the CPU arm
# long before this, so this only bounds a true runaway.
WALL_BOUND_S = 120


def _children_cpu_s() -> float:
    """User+sys CPU of every child this process has reaped so far.

    RUSAGE_CHILDREN is per-PROCESS, so under xdist each worker measures only its
    own children and a before/after delta is attributable to the one call in
    between. That is the same quantity bash's ``TIMEFORMAT='%U'`` reports.
    """
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return ru.ru_utime + ru.ru_stime


def _carriers():
    """Every fleet file that still walks up, as run.sh §65 enumerates them."""
    out = []
    skip_dirs = ("archive",)
    for path in sorted(cf.TOOLS_DIR.glob("oc-*")) + sorted(
            cf.TOOLS_DIR.glob("*/oc-*")) + [cf.TOOLS_DIR / "tests" / "run.sh"]:
        if not path.is_file():
            continue
        name = path.name
        if name.endswith((".bak",)) or ".bak-" in name or ".pre-" in name:
            continue
        if any(part in skip_dirs for part in path.relative_to(cf.TOOLS_DIR).parts):
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

    The exact invocation that hung. Verdicts, in the shell's order:

      rc == 0                      -> RETURNED
      rc == 124 and CPU >= 5 s     -> HUNG (the dirname('.') fixpoint is back)
      rc == 124 and CPU <  5 s     -> STARVED, INCONCLUSIVE (not a hang, #83)
      any other rc                 -> a real tool failure

    A starved sample is neither green nor red on its own; but if EVERY sample
    starves there are zero observations, and a blind instrument must not pass.
    """
    returned, hung, starved, failed = [], [], [], []
    for rel, arg in SAMPLES:
        tool = cf.TOOLS_DIR / rel
        d, b = tool.parent, tool.name
        cpu0 = _children_cpu_s()
        res = run_tool(["./" + b, *arg.split()],
                       timeout=WALL_BOUND_S, cwd=d,
                       # BATTERY_IN_CHUNK is inherited when pytest is launched
                       # from inside a chunk; run.sh's own --chunk branch is
                       # guarded on it being empty, so a set value would make the
                       # run.sh sample fall through and execute the whole battery.
                       env={"BATTERY_IN_CHUNK": ""})
        cpu = _children_cpu_s() - cpu0

        if res.rc == 0:
            returned.append(rel)
        elif res.rc == 124 and cpu >= SPIN_CPU_S:
            hung.append("%s (%.1fs CPU)" % (rel, cpu))
        elif res.rc == 124:
            starved.append("%s (%.2fs CPU, bound %ds)" % (rel, cpu, WALL_BOUND_S))
        else:
            failed.append("%s rc=%s%s" % (rel, res.rc,
                                          (" :: " + res.combined.strip()[-200:])
                                          if res.combined.strip() else ""))

    assert not failed, "relative invocation FAILED for %d sample(s): %s" % (
        len(failed), "; ".join(failed))
    assert not hung, (
        "%d sample(s) HUNG by RELATIVE invocation — the dirname('.') fixpoint is "
        "back (#708): %s" % (len(hung), "; ".join(hung)))
    assert len(starved) < len(SAMPLES), (
        "relative invocation could NOT be verified: all %d sampled tool(s) killed "
        "on wall starvation (<%.0fs CPU) — the instrument was blind, not the "
        "tools (#83). %s" % (len(SAMPLES), SPIN_CPU_S, "; ".join(starved)))

    # Never claim a starved sample RETURNED: it was killed before it could.
    assert len(returned) + len(starved) == len(SAMPLES)
    if starved:
        pytest.skip("relative invocation returns for %d of %d sampled tool(s); "
                    "%d INCONCLUSIVE on wall starvation (<%.0fs CPU) — not a "
                    "fixpoint, not a verified return (#83): %s"
                    % (len(returned), len(SAMPLES), len(starved), SPIN_CPU_S,
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


def test_the_broken_preamble_times_out(tmp_path, run_tool):
    """NEGATIVE CONTROL: the instrument SEES the class it is aimed at.

    Without this half, a dynamic arm that never fires would read identical to
    one that works. The broken fixture must be KILLED AT THE BOUND *and* be
    shown to have SPUN (CPU >= the discriminator), which is exactly the signal
    the dynamic arm above uses to distinguish a hang from starvation.
    """
    _fixture(tmp_path, "broken", _BROKEN)
    cpu0 = _children_cpu_s()
    res = run_tool(["./broken"], timeout=5, cwd=tmp_path)
    cpu = _children_cpu_s() - cpu0
    assert res.rc == 124 and res.timed_out, (
        "broken preamble returned rc=%s — it must not terminate, or this leg "
        "cannot detect a hang: %s" % (res.rc, res.combined[-300:]))
    assert cpu >= 2.0, (
        "broken preamble was killed having burned only %.2fs CPU — that is the "
        "STARVATION signature, not a spin, so the control proved nothing" % cpu)


def test_the_fixed_preamble_returns(tmp_path, run_tool):
    """CONTROL, other side: the same fixture WITH the break must return rc=0.

    A 3 s wall on this leg measures MACHINE LOAD, not the fixture (factory#109):
    the fixed form returns in 43-101 ms, so 3 s is ~60x headroom and still fired
    rc=124 under the IO starvation this box reaches mid-battery, reporting the
    CONTROL as broken and denying the fleet a version for a green tree.

    So the retry inherits #83's discriminator instead of a wider wall: a starved
    sample burned almost no CPU, which is a MEASURED observation that this is not
    a hang — a pass, not a blind one.
    """
    _fixture(tmp_path, "fixed", _FIXED)
    cpu0 = _children_cpu_s()
    res = run_tool(["./fixed"], timeout=3, cwd=tmp_path)
    cpu = _children_cpu_s() - cpu0
    if res.rc == 0:
        return
    assert res.rc == 124 and cpu < 2.0, (
        "fixed preamble rc=%s after %.2fs CPU (expected 0) — a real failure, not "
        "starvation: %s" % (res.rc, cpu, res.combined[-300:]))

    # Starved: retry at a wide bound.
    cpu0 = _children_cpu_s()
    res2 = run_tool(["./fixed"], timeout=30, cwd=tmp_path)
    cpu2 = _children_cpu_s() - cpu0
    if res2.rc == 0:
        return
    assert res2.rc == 124 and cpu2 < 2.0, (
        "fixed preamble rc=%s after %.2fs CPU on retry (expected 0) — a real "
        "failure, not starvation: %s" % (res2.rc, cpu2, res2.combined[-300:]))
    # Both samples starved at <2 s CPU: no hang signal was ever observed, and
    # that ABSENCE of a spin is the observation this leg rests on.
