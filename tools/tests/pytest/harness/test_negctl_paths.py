"""The ``negctl-*`` controls must invoke their tool at a path that RESOLVES.

The ``negctl-*`` family is standalone by design — some take minutes and drive a
full selftest on a copied tree — so the battery never runs them. But a control
that cannot run is decoration: on the v0.4.255 regroup, three of five silently
began invoking their tool at a FLAT path (``$SRC/oc-health``,
``$WORK/baseline/oc-commit``) after the fleet moved into kind subdirectories, and
reported "guard is inert" instead of testing anything. Nothing noticed for hours.

The assertion is deliberately narrow: no control may invoke its tool as a DIRECT
child of a tools dir. That is the exact shape the regroup broke, and it has no
false positives on runtime-composed paths (``$WORK/mut_<label>/...``) or on prose
naming an old layout.

``#759`` — the segment alternation used to be a HAND-LISTED set of scratch-dir
spellings (``baseline/``, ``mut_*/``, ``mut/``) and ``mutant/``, the spelling the
census and dispatch arms actually used, was not on it. Those two flat paths were
therefore never flagged, and the arms reported CAUGHT for a mutant that never ran
(rc=127). A hand-maintained spelling list is exactly what drifted, so the pattern
accepts ANY single leading segment and leans on the kind-dir exclusion to stay
quiet on legitimate paths. The real backstop is the 126/127 rejection in each
guard's own assertions, which catches a path break whatever it is spelled.

WHY THIS MODULE CARRIES A CONTROL
---------------------------------
A regex that matches nothing reports every file green — the same false green the
section exists to prevent, one layer in. So ``test_the_predicate_flags_a_flat_path``
feeds the detector a path it MUST reject, and ``test_the_scan_found_the_controls``
pins that the enumeration is non-empty. A guard nobody has seen fire is a guess.
"""

from __future__ import annotations

import re

import pytest

import conftest as cf

TESTS_DIR = cf.REPO_ROOT / "tools" / "tests"

# A flat invocation: a variable path ending in a tools dir, then ``/oc-<name>``,
# with at most ONE optional segment between them.
INVOCATION = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*/([A-Za-z0-9_.-]+/)?oc-[a-z0-9-]+")

# The kind subdirectories the fleet regroup created. A path carrying one of these
# resolves; a path without one is flat.
KIND_DIR = re.compile(r"/(state|git|audit|ship|issue|harvest|smoke|notify|tests|lib|tools)/")


def flat_invocations(text: str) -> list[str]:
    """Every flat tool invocation in ``text``, in file order.

    Mirrors the shell predicate exactly: match the invocation shape, then drop
    any line that names a kind directory.
    """
    out = []
    for line in text.splitlines():
        if INVOCATION.search(line) and not KIND_DIR.search(line):
            out.append(line.strip())
    return out


def controls() -> list:
    """Every ``negctl-*`` file, excluding generated ``.bak`` sidecars.

    ``#759``: a ``negctl-*`` pre-image sidecar matches the glob and carries the
    very flat paths this guard exists to flag, so scanning one reddens on a file
    that is not a control at all (and is reaped on the hygiene cadence anyway).
    """
    return sorted(
        p for p in TESTS_DIR.glob("negctl-*")
        if p.is_file() and ".bak" not in p.name
    )


def test_the_scan_found_the_controls():
    """The enumeration is non-empty — an empty list passes every per-file leg."""
    found = controls()
    assert found, (
        "no negctl-* controls under %s — the glob or the tree moved, and every "
        "per-file leg below would pass vacuously" % TESTS_DIR)


def test_the_predicate_flags_a_flat_path():
    """The control: the detector MUST reject a flat path, or it proves nothing.

    Both spellings that the v0.4.255 regroup and ``#759`` produced, plus the
    ``mutant/`` spelling the hand-list missed.
    """
    for flat in ('"$SRC/oc-health" --selftest',
                 '"$WORK/baseline/oc-commit" --selftest',
                 '"$M/mutant/oc-commit" --selftest',
                 '"$WORK/mut_health/oc-commit" --selftest'):
        assert flat_invocations(flat), (
            "the predicate did not flag %r — a detector that matches nothing "
            "reports every control green" % flat)

    # And the direction it must stay QUIET on, or the guard cries wolf and gets
    # switched off: a path that names one of the kind subdirectories.
    #
    # A scratch segment (``mut_health/``) is NOT quiet — it is flat, and flagging
    # it is the point: the control copies the tree and then invokes the tool one
    # level down from nowhere. The guards' own 126/127 assertions are the
    # backstop that catches those regardless of how the path is spelled.
    for fine in ('"$SRC/state/oc-health" --selftest',
                 '"$SRC/issue/oc-issue-create" --create',
                 '"$SRC/harvest/oc-gate" --selftest',
                 '"$TOOLS_DIR/lib/oc-root" --resolve'):
        assert not flat_invocations(fine), (
            "the predicate flagged the resolvable path %r" % fine)


@pytest.mark.parametrize("path", controls(), ids=lambda p: p.name)
def test_control_invokes_its_tool_at_a_resolvable_path(path):
    """No control invokes its tool as a direct child of a tools dir."""
    flat = flat_invocations(path.read_text(encoding="utf-8", errors="replace"))
    assert not flat, (
        "%s invokes its tool at a FLAT path — post-regroup this cannot resolve, "
        "so the control reports 'guard is inert' instead of testing anything:\n  %s"
        % (path.name, "\n  ".join(flat[:3])))
