"""Section 66, part 6 of 6 — the serial legs GENUINELY do not overlap.

THE CLAIM THIS FILE EXISTS TO TEST
    ``@pytest.mark.serial`` + ``@pytest.mark.xdist_group(g)`` is a statement
    about the SCHEDULER: xdist promises same-group legs never run at once. That
    promise is not evidence about the legs. Three ways it silently stops holding
    while every mark stays in place:

      * a mistyped group string — ``"battery-pool"`` vs ``"battery_pool"`` is two
        groups, and xdist happily runs both at once;
      * ``-p no:xdist`` / ``-n 0`` on a box where the group assumption was
        carried by the scheduler alone;
      * a worker crash-restart, which reschedules without the group's state.

    Every assertion in a serial leg rests on that premise, so the premise gets
    its own test. This module is the premise.

HOW IT IS OBSERVED, NOT RE-ASSERTED
    ``H.SerialWitness`` takes an exclusive ``flock`` on ``<dir>/witness.<group>``
    for the body of a leg and logs ``enter``/``exit`` timestamps. A second
    same-group holder that appears at the same moment raises ``Overlap`` — the
    leg FAILS instead of interleaving quietly — and the log lets the whole
    session be censused afterwards. Both halves of the claim are therefore
    measured by the legs themselves, never inferred from the markers.

WHY THE CENSUS NEEDS A CONTROL
    "No overlap was recorded" is worth only what the recorder can see. A census
    that would report clean on a run where two legs DID overlap is decoration,
    so ``test_the_census_can_see_an_overlap`` hands the SAME parser a synthetic
    overlapping pair and requires it to find it. Without that leg the other two
    pass on any instrument, including a broken one (rule 7: a green verdict is
    worth what the instrument can see).

WALL-CLOCK IS NEVER ASSERTED
    The witness holds for ``hold_s`` on purpose: if the pin is broken the
    sibling lands inside that window rather than in the microseconds between two
    syscalls. That sleep is the instrument's own resolution, never a performance
    claim — nothing here asserts how long anything took.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import conftest as cf
from lib import harness as H

# The groups the harness pins. This is a DECLARATION, not a census: the census
# reads the groups collection actually found (a hand-kept list silently stops
# covering a group someone adds — this file first named four while the suite
# carried seven, so battery-nested, battery-scratch and path-restore were
# unwitnessed). What this list is FOR is the other direction: a typo like
# "battery_pool" is a real second group that serialises against nothing, and
# only a canonical set can notice it.
CANONICAL_GROUPS = (
    "battery-cgroup",
    "battery-ledger-lock",
    "battery-lock",
    "battery-nested",
    "battery-pool",
    "battery-scratch",
    "battery-sigkill",
    "cache",
    "path-restore",
)

# =============================================================================
# the negative control — a leg that FAILS when two same-group bodies overlap
# =============================================================================
@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_a_second_same_group_holder_raises_overlap(tmp_path):
    """The witness FAILS on a real overlap — proven by making one happen.

    A nested ``enter`` inside a held witness is exactly the state a broken
    group pin produces, so it is the state the witness must refuse. If this leg
    ever passes with no exception the witness is inert and every "no overlap"
    verdict in the suite is unsupported.
    """
    # A private group: the autouse witness already holds "battery-pool" for this
    # test (it carries that marker), and re-entering THAT would raise Overlap
    # before the leg could prove anything — a control that fails for the wrong
    # reason proves nothing about the witness.
    group = "witness-control"
    outer = H.SerialWitness(tmp_path, group, hold_s=0.0)
    with outer:
        with pytest.raises(H.Overlap):
            H.SerialWitness(tmp_path, group, hold_s=0.0).__enter__()


@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_witness_can_see_an_overlap(tmp_path):
    """NEGATIVE CONTROL for the CENSUS — the parser, not the lock.

    ``test_a_second_same_group_holder_raises_overlap`` proves the LOCK refuses a
    second holder. This proves the LOG PARSER can report one: two synthetic
    intervals are written by hand, straddling each other, and the same
    ``spans``/``overlaps``/``peak`` the session census uses must find them. A
    census built on a parser that cannot see a planted overlap reports clean on
    a broken run, which is the one failure mode that looks like success.
    """
    log = tmp_path / "intervals.probe"
    log.write_text(
        "enter 'probe' 100.000000 1\n"
        "enter 'probe' 100.500000 2\n"
        "exit 'probe' 101.000000 2\n"
        "exit 'probe' 101.500000 1\n",
        encoding="utf-8")

    spans = H.SerialWitness.spans(tmp_path, "probe")
    assert len(spans) == 2, "the parser lost an interval: %r" % (spans,)
    assert H.SerialWitness.overlaps(tmp_path, "probe"), (
        "the census parser reported NO overlap for two intervals that plainly "
        "straddle each other — every 'serial legs did not overlap' verdict "
        "built on it is unsupported")
    assert H.SerialWitness.peak(tmp_path, "probe") == 2, (
        "peak concurrency of the planted overlap was not 2")

    # And the disjoint inverse: touching-but-not-straddling must NOT be an
    # overlap, or the census reds on a correct run and gets muted.
    log.write_text(
        "enter 'probe' 200.000000 1\n"
        "exit 'probe' 201.000000 1\n"
        "enter 'probe' 201.000000 2\n"
        "exit 'probe' 202.000000 2\n",
        encoding="utf-8")
    assert H.SerialWitness.overlaps(tmp_path, "probe") == [], (
        "back-to-back intervals were reported as overlapping")
    assert H.SerialWitness.peak(tmp_path, "probe") == 1


# =============================================================================
# the session census — what the legs actually observed
# =============================================================================
def test_no_two_same_group_legs_overlapped_this_session(serial_witness_dir, request):
    """Every group's witness log carries ZERO overlapping pairs.

    The GROUP SET comes from collection (``conftest.pytest_collection_modify
    _items``), never from a tuple kept by hand. A hand-kept list is a census
    with a blind spot that grows: this file originally named four groups while
    the suite carried SEVEN, so ``battery-nested``, ``battery-scratch`` and
    ``path-restore`` were unwitnessed and would have censused clean forever.

    Order-independent by construction: the assertion is MONOTONIC. A leg that
    has not run yet contributes no interval, so reading early can only make the
    log shorter — it can never manufacture an overlap that is not there. What it
    CAN miss is a late overlap, which is why the witness also FAILS at the
    moment it happens (``test_a_second_same_group_holder_raises_overlap``) and
    why every grouped leg holds the witness for its whole body via the autouse
    fixture rather than for a few instructions.
    """
    groups = sorted(request.config._oc_witness_groups)
    assert groups, (
        "no xdist_group marker was collected at all — the census would report "
        "clean over an empty set")

    report = {g: cf.witness_session_report(serial_witness_dir, g) for g in groups}

    bad = {g: r["overlaps"] for g, r in report.items() if r["overlaps"]}
    assert not bad, (
        "serial legs OVERLAPPED — their xdist_group pin is not holding, so "
        "every assertion in them rests on an untested premise:\n%s"
        % "\n".join("%s: %r" % (g, pairs) for g, pairs in bad.items()))

    # A group that held more than one leg at a peak proves the same thing the
    # overlap pairs do, from the other side: peak > 1 IS an overlap.
    peaks = {g: r["peak"] for g, r in report.items() if r["peak"] > 1}
    assert not peaks, "witness peak concurrency > 1: %r" % (peaks,)


def test_every_collected_group_is_a_known_group(request):
    """Collected groups are a SUBSET of the canonical set — the typo detector.

    The census above iterates whatever collection found, which is right (no
    blind spot) but cannot notice a group that SHOULD have been one of these and
    is not: ``"battery_pool"`` instead of ``"battery-pool"`` is a real second
    group, both sides agree on it, and the leg silently stops serialising
    against the pool it meant to join. Pinning the canonical names makes adding
    a group a deliberate edit here rather than a typo that reads as a design.
    """
    collected = set(request.config._oc_witness_groups)
    unknown = collected - set(CANONICAL_GROUPS)
    assert not unknown, (
        "xdist_group value(s) not in the canonical set — a typo creates a "
        "SECOND group that serialises against nothing: %s\ncanonical: %s"
        % (sorted(unknown), sorted(CANONICAL_GROUPS)))


def test_every_serial_leg_carries_an_xdist_group(request):
    """No serial-marked leg is missing its group — read from the NODES.

    ``serial`` alone is half a pin: xdist may still schedule a same-group
    sibling beside it, because there is no group to schedule on. This is the
    check that caught ``test_harness_cgroup.py`` marking eleven legs serial with
    no group at all — a source-grep for the string ``xdist_group`` elsewhere in
    the file would have passed it.
    """
    offenders = getattr(request.config, "_oc_serial_without_group", None)
    assert offenders is not None, "collection hook did not run"
    assert not offenders, (
        "serial-marked leg(s) with NO xdist_group — the marker claims "
        "exclusivity and names nothing to enforce it:\n%s"
        % "\n".join(offenders))



@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_session_witness_dir_records_a_real_hold(serial_witness_dir):
    """The census is not vacuous — proven on the SESSION dir, in order-independent form.

    A "no overlap" verdict over a log nothing ever wrote is the from-zero
    defect: a re-armed counter reading clean. Rather than depend on some other
    module having run first (which ``-k`` selection or a different collection
    order would break), this leg takes a hold through the SAME session-scoped
    fixture the other modules use, then requires the census to see it.
    """
    # A group of its own: the autouse witness already holds "battery-pool" for
    # this very test (it carries that marker), so re-entering it would raise
    # Overlap — correctly. This leg is about the CENSUS, not the pin.
    group = "witness-selftest"
    before = cf.witness_session_report(serial_witness_dir, group)["legs"]
    with H.SerialWitness(serial_witness_dir, group, hold_s=0.0):
        pass
    after = cf.witness_session_report(serial_witness_dir, group)
    assert after["legs"] == before + 1, (
        "a hold taken through the session witness dir was not censused "
        "(legs %d -> %d) — the census in this file is measuring an empty log, "
        "so it proves nothing" % (before, after["legs"]))
    assert after["peak"] >= 1
