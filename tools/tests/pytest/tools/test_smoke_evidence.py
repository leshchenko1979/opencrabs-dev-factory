"""`oc-smoke-evidence` decoy-path guard (M2-2).

The section pins one property and it is the only one worth pinning: **a log
target that is not the canonical one must ANNOUNCE itself.** ``--append-log``
takes a path, and three spellings resolve three different ways:

* a bare ``--append-log`` (no value) is the canonical log — silent;
* a RELATIVE ``--append-log smoke-verdicts.log`` resolves against the STATE DIR,
  not the caller's CWD, so a battery run from anywhere still writes one place;
* a FOREIGN ABSOLUTE path is a genuine divergence, and it must say so on stderr.

The last leg is the one that carries the defect: a divergent target that stayed
silent is a verdict written where nobody looks, which reads downstream as "no
evidence" rather than "evidence elsewhere".

The divergent path is deliberately OUTSIDE the state dir — including outside
TMPDIR is what makes it a divergence at all — but it is inside ``scratch`` so it
is reaped with everything else. Pointing it into the state dir would make the
leg stop testing divergence; pointing it at a literal ``/tmp`` path would leak
one file per run into a directory this suite does not own.
"""

from __future__ import annotations

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-smoke-evidence")

# A unit that does not exist: the tool fails rc 3 AFTER the append-log resolution
# has already run, which is exactly the ordering these legs need.
MISSING_UNIT = "oc-no-such-unit"

def _run(run_tool, *args, env=None):
    return run_tool([str(TOOL), *args], timeout=120, env=env)

def test_unknown_arg_is_usage_rc2(run_tool):
    res = _run(run_tool, "--bogus")
    assert res.rc == 2, "unknown arg: rc=%s, want 2 (usage)\n%s" % (
        res.rc, res.combined[-400:])

def test_strings_deprecated_alias_parses(run_tool, state_dir):
    """E2 #6: ``--strings`` is a deprecated alias for ``--markers``, and it must
    still PARSE — the unit failure below is rc 3, which is the proof it was
    accepted rather than rejected as an unknown flag (that would be rc 2)."""
    res = _run(run_tool, "--unit", MISSING_UNIT, "--strings", "m1")
    assert res.rc == 3, \
        "--strings alias: rc=%s, want 3 (unit-fail; rc 2 would mean it did not "\
        "parse)\n%s" % (res.rc, res.combined[-400:])

def test_bare_append_log_is_the_canonical_log(run_tool, state_dir):
    """``--append-log`` with no value must NOT diverge.

    A bare flag that silently picked up the NEXT argv token as its value would
    redirect the verdict into a file named after a flag — the decoy class.
    """
    res = _run(run_tool, "--append-log", "--unit", MISSING_UNIT)
    assert "NOT the canonical" not in res.combined, \
        ("bare --append-log diverged from the canonical log (M2-2):\n%s"
         % res.combined[-600:])

def test_relative_append_log_resolves_to_the_state_dir(run_tool, state_dir):
    """A RELATIVE target is the state dir's, never the caller's CWD.

    The shell harness made the same point: a battery invoked from any directory
    must still write one place, so a relative path is resolved against STATE_DIR rather
    than ``$PWD``.
    """
    res = _run(run_tool, "--append-log", "smoke-verdicts.log",
               "--unit", MISSING_UNIT)
    assert "NOT the canonical" not in res.combined, \
        ("relative --append-log escaped STATE_DIR (M2-2):\n%s"
         % res.combined[-600:])
    assert not (cf.REPO_ROOT / "smoke-verdicts.log").exists(), \
        "a relative --append-log landed in the CWD"

def test_divergent_absolute_append_log_announces_itself(run_tool, state_dir, scratch):
    """THE leg: a foreign absolute target must name the canonical one.

    Silence here is the defect — the verdict lands somewhere no reader looks and
    the run reports "no evidence" rather than "evidence elsewhere". The note is
    on STDERR on purpose (it is a diagnostic, not the tool's output), so this
    asserts against the merged stream rather than stdout alone.
    """
    elsewhere = scratch.path / "elsewhere" / "oc-elsewhere.log"
    elsewhere.parent.mkdir(parents=True, exist_ok=True)
    res = _run(run_tool, "--append-log", str(elsewhere), "--unit", MISSING_UNIT)
    assert "NOT the canonical" in res.combined, \
        ("a divergent absolute --append-log was SILENT (M2-2):\n%s"
         % res.combined[-600:])
    # and it names WHERE it went, not just that it diverged
    assert str(elsewhere) in res.combined, \
        "the divergence note did not name the foreign path it used"
