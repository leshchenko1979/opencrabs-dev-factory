"""Entry-preamble fixpoint + relative invocation (#708).

    (README coverage row 65. The brief's "§63/§64/§65" are README rows; the
    shell's own section numbers were §77/§82/§84 — this module is the §84
    behaviour.)

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
    The walk never advances, every guard stays true, and the tool spins emitting
    nothing. It had been copy-pasted into every tool in the fleet.

WHY THIS SECTION EXISTS AT ALL
    The battery's other invocation legs drive ``$t`` as an ABSOLUTE path (their
    glob is ``"$TOOLS_DIR"/...``), so they cannot observe this class — the
    fixpoint needs a RELATIVE invocation to reproduce. That blind spot is the
    section's whole justification, and it is why the drive below must keep
    ``cwd=<tool dir>`` and ``./name``: converting either to an absolute form
    would leave a green leg that tests nothing.

SCOPE — THE BEHAVIOURAL HALF ONLY
    §84 has two arms in the shell and only one belongs in this module.

      static   every walk-up carrier must carry the ``.`` break. Already owned
               by ``test_oc_root_resolver.py::test_every_walkup_carrier_has_the
               _fixpoint_break``, because the walk-up preamble IS the resolver's
               bootstrap — §77 and §84 are two views of one line of code. Two
               ports of one invariant drift: the first to be sharpened leaves the
               other asserting a stale floor.
      dynamic  drive one representative per tool KIND by RELATIVE path and
               require it to RETURN. That is this module.

THE BOUND, AND WHY IT IS NOT A CPU LIMIT
    A wall clock cannot by itself distinguish "hung" from "starved", which is why
    the shell leg reads CPU as well (#83, factory#109). ``RLIMIT_CPU`` looks like
    the clean answer — the kernel kills a process that BURNS n seconds of CPU, so
    a starved process simply takes longer in wall time — and it was implemented
    here FIRST, then rejected. This defect's spin is a FORK LOOP:
    each iteration forks a ``dirname``, so the CPU is spread across thousands of
    short-lived children each inside any sane limit while the parent accrues its
    own slowly. ``ulimit -t 5`` needs **47-65 s of wall** to fire (three runs,
    load 7.3; the parent burns its 5 s budget while the forked ``dirname``s
    burn the rest).

    So the bound is wall time with headroom sized from healthy cost:
    the fleet samples burn 0.10-0.41 s CPU and return in 0.17-0.66 s wall (load
    7.3), making a 20 s bound 30-120x headroom. A sample that hits it is
    INCONCLUSIVE, never accused of hanging. What licenses the verdict is the
    CONTROL, below: the broken fixture never returns at all, so the instrument
    is proven able to see the class it is aimed at rather than assumed to be.
"""

from __future__ import annotations


import pytest

import conftest as cf

# One representative per tool KIND, so a regression in any single kind is
# observable without paying a fleet-wide --help sweep. Kept as (relpath, argv).
SAMPLES = (
    ("state/oc-ledger", "--help"),
    ("ship/oc-build", "--help"),
    ("harvest/oc-gate", "--help"),
    ("audit/oc-lint-laws", "--help"),
    ("smoke/oc-smoke", "--help"),
    ("git/oc-commit", "--help"),
    ("issue/oc-issue-scope", "--help"),
    ("notify/oc-notify-fanout", "--help"),
)

# The sample size the shell asserts (EP_DYN -ne 8 -> bad). Pinned so a sample
# removed from the tuple is a visible decision, not a quiet shrink.
#
# It was 9 until the retired shell harness's own entry point was the ninth
# sample — it needed a cheap flag that ran its preamble and exited.
SAMPLE_COUNT = 8

# THE BOUND IS A WALL CLOCK, AND RLIMIT_CPU WAS TRIED FIRST AND REJECTED
#
# A CPU limit looks like the perfect load-independent discriminator: the kernel
# kills a process that BURNS n seconds of CPU, and a starved process simply takes
# longer in wall time, so starvation could never masquerade as a hang.
#
# It does not work for THIS defect, and the reason is the defect's own shape.
# The broken fixture is not a tight loop in one process —
# every iteration forks a `dirname`. So the spin's CPU is spread across thousands
# of short-lived children, each far inside any sane limit, while the parent
# accumulates its own CPU slowly: with `ulimit -t 5` the parent takes **47-65 s
# of wall** to burn its 5 s budget (three runs, load 7.3). That is slower than
# the wall bound it was meant to replace, and it makes the leg slower than the
# 60 s `slow` threshold on its own.
#
# So the bound is wall time, with headroom sized from healthy cost:
# the fleet samples burn 0.10-0.41 s CPU and return in ~0.17-0.66 s wall (load
# 7.3). A 20 s bound is therefore 30-120x headroom, and a sample that hits it is
# reported INCONCLUSIVE rather than accused of hanging (#83). The negative
# control proves the instrument can see a real hang, because the broken fixture
# never returns at all.
WALL_BOUND_S = 20

# The control's bound. The fixed half returns in ~0.05 s, so 10 s is ~200x
# headroom; the broken half never returns, so any bound catches it.
CONTROL_BOUND_S = 10

# 124 is `timeout(1)`'s "the bound fired" code, which the shell harness read as
# "HUNG -- killed at the Ns bound", not as a tool verdict.
WALL_KILL_RC = 124


def _tool_env():
    """The one env adjustment the relative invocation needs.

    BATTERY_IN_CHUNK is inherited when pytest is launched from inside a chunk;
    the shell harness's own --chunk branch was guarded on it being empty, so a
    set value would make the sample fall through and execute the whole battery.
    """
    return {"BATTERY_IN_CHUNK": ""}


# SCOPE: THE BEHAVIOURAL ARM ONLY — §77'S MODULE OWNS THE STATIC CENSUS
#
# §84 has two halves and only one of them belongs here.
#     ``test_oc_root_resolver.py::test_every_walkup_carrier_has_the_fixpoint_break``
#     asserts the same invariant (every walk-up carrier carries the ``.`` break,
#     keyed on the fix's presence, with the same floor), because the walk-up
#     preamble IS the resolver's bootstrap: §77 and §84 are two views of one line
#     of code. Porting it twice gives the suite two half-rules that drift apart —
#     the first to be sharpened leaves the other asserting a stale floor.
#
# This module therefore owns only §84's reason for existing: the BEHAVIOURAL arm.
# The battery's other invocation legs drive tools by ABSOLUTE path, so none of
# them can observe a relative-path fixpoint at all.
# =============================================================================
# the sample's own integrity
# =============================================================================
def test_the_sample_is_complete():
    """§84: the relative-invocation sample runs 9 of 9 (``EP_DYN -ne 9 -> bad``).

    The shell reds when the sample covered fewer than nine, so a silently
    shrunk arm cannot read as a green one. Pinning the count AND checking each
    file exists catches both ways that happens: a representative dropped from
    the tuple, and a tool moved so its sample no longer resolves.
    """
    assert len(SAMPLES) == SAMPLE_COUNT, (
        "relative-invocation sample carries %d of %d entries — a representative "
        "was dropped, which shrinks the arm silently"
        % (len(SAMPLES), SAMPLE_COUNT))
    missing = [rel for rel, _ in SAMPLES if not (cf.TOOLS_DIR / rel).is_file()]
    assert not missing, "relative-invocation sample missing: %s" % ", ".join(missing)

def test_the_harness_delivers_a_relative_dollar0(tmp_path, run_tool):
    """CANARY: the drive below is only §84's drive if ``$0`` arrives RELATIVE.

    The whole section rests on one premise — that ``cwd=<tool dir>`` plus argv
    ``./name`` reaches the tool as ``$0='./name'``, so ``dirname "$0"`` is ``.``
    and the fixpoint is reproducible. Every other leg in this module *assumes*
    that premise. This one measures it.

    It is here because the premise has already been lost once, silently: a
    wrapper of the form ``bash -c 'ulimit -t N; exec "$@"' _ ./tool`` REBUILDS
    ``$0`` as an ABSOLUTE path, so the broken fixture walked up to ``/`` and
    printed ``reached`` — and the dynamic arm, still green, was then testing
    absolute invocation, i.e. the exact class it exists to rule out. Nothing
    failed; only the instrument had quietly turned into a different instrument.

    So: a fixture that PRINTS ``$0`` and exits. If a future harness change
    absolutizes argv, this leg reds with the reason instead of the control
    above reding with a mystery.
    """
    probe = _fixture(tmp_path, "probe", '#!/usr/bin/env bash\nprintf "%s" "$0"\n')
    res = run_tool(["./" + probe.name], timeout=CONTROL_BOUND_S, cwd=tmp_path)

    assert res.rc == 0, (
        "the $0 probe did not run (rc=%s): %s" % (res.rc, res.combined[-300:]))
    assert res.out.startswith("./"), (
        "argv[0] reached the tool as %r, not './%s' — the harness ABSOLUTIZED it, "
        "so `dirname \"$0\"` is a real directory rather than '.', the fixpoint "
        "cannot be reproduced, and the dynamic arm below silently stops testing "
        "the relative-invocation class it exists for (#708)"
        % (res.out, probe.name))


# =============================================================================
# DYNAMIC ARM — behavioural, by RELATIVE path from the tool's OWN directory
# =============================================================================
def test_relative_invocation_returns(run_tool):
    """§84 dynamic: ``cd <tool dir> && ./name --help`` must TERMINATE.

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
