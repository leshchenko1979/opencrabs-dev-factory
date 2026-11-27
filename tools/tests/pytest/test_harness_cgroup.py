"""Section 66, part 1 of 6 — the ``#720`` cgroup-isolation block.

WHAT THIS SPLITS
    In ``run.sh`` the call ``section "cgroup isolation (#720)"`` (line 4682)
    opens a span of **569 lines** carrying SIX numbered blocks: ``#85`` (this
    one) plus five that have a header but no call of their own — ``#86`` (#750),
    ``#87`` (#47), ``#88`` (#74), ``#89`` (#76) and ``#90`` (#114). One
    ``section`` line names the whole 569 lines, so the transcript and the
    per-section receipt timing attribute six blocks' work to "cgroup isolation".

    The five swallowed blocks are ported in ``test_harness_pool.py``. This module
    owns ``#85`` only: the re-exec contract.

WHY THE BLOCK IS DRIVEN, NOT RETYPED
    ``#720`` is a function of WHERE the run sits (a ``.service`` unit, a
    ``.scope``, no systemd at all), so a test that only exercises the branch its
    own environment happens to take asserts nothing. Every leg here extracts the
    block VERBATIM from ``run.sh`` and feeds it a SYNTHETIC cgroup path, stubbing
    ``systemd-run``/``systemctl`` so the re-exec contract is observable without a
    real transient scope. The one rewrite — the cgroup INPUT — is itself
    asserted to touch exactly one line, so a sed that mangles the logic reddens.

    A re-exec REPLACES the process, so "SURVIVED" is the FAILURE signal in the
    arm that wants isolation, and the PASS signal in the arms that must not.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from lib import harness as H


# BOTH markers: ``serial`` keeps it off the parallel pool, ``xdist_group`` keeps
# it off every OTHER serial leg that rewrites the same stub dir. ``serial``
# alone is half a pin — xdist may still run a same-group sibling beside it.
pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-cgroup"),
]  # the cgroup block's own stubs live in one dir

# The synthetic cgroup paths the legs drive. They are literal, not derived: the
# block's branch is decided by the LEAF unit name (``${cg##*/}``), so the test
# must state the leaf it wants.
SVC_CG = "/user.slice/user-0.slice/user@0.service/app.slice/opencrabs-ops.service"
SCOPE_CG = "/user.slice/user-0.slice/user@0.service/app.slice/oc-battery.scope"

# The block's ONLY test rewrite: the cgroup INPUT, so the branch is a function
# of the test's input rather than of where the suite runs.
REWRITE_FROM = "$(battery_cgroup_path)"
REWRITE_TO = "${CI_SYNTH_CG}"

SYSTEMD_RUN_STUB = """#!/usr/bin/bash
printf '%s\\n' "$*" >> "${CI_SR_LOG:?}"
case " $* " in *" true "*) exit "${CI_PROBE_RC:-0}" ;; esac
exit 0
"""

SYSTEMCTL_STUB = """#!/usr/bin/bash
if [ "${1:-}" = "--user" ] && [ "${2:-}" = "is-system-running" ]; then exit "${CI_MGR_RC:-0}"; fi
exit 0
"""

# Mirrors run.sh:4795-4808. ``set -u`` is load-bearing: it is what makes an
# extracted block that runs PAST its own end die at a later block's unbound
# variable (the #74/#107 overrun symptom) instead of passing silently.
HARNESS = """#!/usr/bin/env bash
set -u
note() { printf '%s\\n' "$*"; }
PATH="${CI_SB:?}:${CI_UTIL:?}"; export PATH
# ``battery_cgroup_path`` is DEFINED INSIDE the block (the reader is a function
# so this block can be driven with a synthetic path). Only that DEFINITION is
# loaded first — never the whole block, because sourcing it would run the block
# against the REAL host cgroup, and on a box whose suite sits in a .service that
# first pass would attempt a real re-exec. The definition is self-contained (a
# one-line function), so it is lifted verbatim; a `{}`-body form would need a
# terminator and this one carries its own on the same line.
grep -E '^battery_cgroup_path\\(\\) \\{' "$CI_BLOCK" > "$CI_BLOCK.fn"
grep -q '}' "$CI_BLOCK.fn" || printf '}\\n' >> "$CI_BLOCK.fn"
. "$CI_BLOCK.fn"
# The rewrite is asserted to touch exactly one line by its own leg; ``\\$`` is
# load-bearing here — unescaped, the harness would COMMAND-SUBSTITUTE the
# function and the sed pattern would become the real host path, matching nothing.
sed "s|\\$(battery_cgroup_path)|${CI_SYNTH_CG}|" "$CI_BLOCK" > "$CI_BLOCK.synth" || exit 9
. "$CI_BLOCK.synth"
printf 'SURVIVED cg=%s iso=%s\\n' "${BATTERY_SELF_CGROUP:-}" "${BATTERY_SELF_CGROUP_ISO:-}"
"""


class CgroupSandbox:
    """One extraction of the ``#720`` block plus its stub bin and runner."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.block = root / "iso.sh"
        self.block.write_text(H.extract_cgroup_block(), encoding="utf-8")
        self.sb = root / "bin"
        self.sb.mkdir(parents=True, exist_ok=True)
        for name, body in (("systemd-run", SYSTEMD_RUN_STUB),
                           ("systemctl", SYSTEMCTL_STUB)):
            p = self.sb / name
            p.write_text(body, encoding="utf-8")
            p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.sr_log = root / "sr.log"
        # A HERMETIC PATH: the stub bin plus ONLY the coreutils the block needs.
        # Removing a stub from a PATH that still carries /usr/bin proves nothing —
        # the real binary answers and the "missing systemd" arm is unreachable.
        self.util = root / "util"
        self.util.mkdir(parents=True, exist_ok=True)
        for name in ("sed", "grep", "head", "cat", "awk", "tr", "printf", "wc"):
            found = shutil.which(name)
            if found:
                link = self.util / name
                if not link.exists():
                    link.symlink_to(found)
        self.harness = root / "harness.sh"
        self.harness.write_text(HARNESS, encoding="utf-8")
        self.harness.chmod(self.harness.stat().st_mode | stat.S_IXUSR)

    def run(self, synth_cg: str, *, probe_rc: int = 0, mgr_rc: int = 0,
            extra_env: dict | None = None, block: Path | None = None):
        """Run the harness once; returns ``(rc, combined_output)``."""
        self.sr_log.write_text("", encoding="utf-8")
        env = {k: v for k, v in os.environ.items()
               if k not in ("BATTERY_IN_CHUNK", "BATTERY_CGROUP_ISOLATED",
                            "OC_BATTERY_NO_CGROUP")}
        env.update({
            "CI_SB": str(self.sb),
            "CI_UTIL": str(self.util),
            "CI_BLOCK": str(block or self.block),
            "CI_SYNTH_CG": synth_cg,
            "CI_SR_LOG": str(self.sr_log),
            "CI_PROBE_RC": str(probe_rc),
            "CI_MGR_RC": str(mgr_rc),
        })
        if extra_env:
            env.update({k: str(v) for k, v in extra_env.items()})
        p = subprocess.run(["bash", str(self.harness)], capture_output=True,
                           text=True, timeout=60, env=env)
        return p.returncode, (p.stdout + p.stderr)

    def invocations(self) -> list[str]:
        return [l for l in self.sr_log.read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture
def cgroup_box(tmp_path):
    box = CgroupSandbox(tmp_path / "cg")
    yield box
    shutil.rmtree(box.root, ignore_errors=True)

# =============================================================================
# the extracted block IS the block (not a copy)
# =============================================================================
def test_extraction_is_exactly_one_section():
    """The extraction carries one header and none of its neighbours' code.

    Both #74 (pids preflight) and #107 (battery lock) were inserted between the
    #720 block and the marker the old range ended on, and were swept into the
    fixture — the synth then ran code it was never meant to, blocking on the
    very lock the live run held (900 s, then a false ``#720: refused scope``).
    """
    block = H.extract_cgroup_block()
    headers = [l for l in block.splitlines() if l.startswith("# ---- ")]
    assert len(headers) == 1, (
        "extraction carries %d section headers (expected 1) — the range end is a "
        "name list again" % len(headers))
    assert "pids budget preflight" not in block, "#74 swept into the #720 extraction"
    assert "BATTERY LOCK BLOCK" not in block, "#107 swept into the #720 extraction"

def test_input_rewrite_touches_exactly_one_line(cgroup_box):
    """The cgroup-input sed changes ONE line (two diff sides), no more.

    The fixture is the block; if the rewrite also touched the logic, the legs
    below would be asserting a mutant rather than the code under test.
    """
    src = cgroup_box.block.read_text(encoding="utf-8")
    rewritten = src.replace(REWRITE_FROM, REWRITE_TO)
    assert rewritten != src, "the cgroup-input marker was not found — the rewrite is a no-op"
    a = src.splitlines()
    b = rewritten.splitlines()
    assert len(a) == len(b), "the rewrite changed the line count"
    diff_sides = sum(1 for x, y in zip(a, b) if x != y) * 2
    assert diff_sides == 2, (
        "the input rewrite changed %d diff sides (expected 2) — the fixture is "
        "not the block" % diff_sides)

# =============================================================================
# LEG 1 — inside a .service unit the block MUST re-exec, with #720's caps
# =============================================================================
def test_inside_a_service_unit_the_run_reexecs(cgroup_box):
    rc, out = cgroup_box.run(SVC_CG, probe_rc=0)
    assert "SURVIVED" not in out, (
        "inside a .service cgroup the block did NOT re-exec (isolation inert): %r" % out[-400:])
    assert "re-exec into a transient scope" in out, (
        "no re-exec diagnostic for a .service cgroup: %r" % out[-400:])

def test_reexec_makes_two_invocations_and_they_share_the_caps(cgroup_box):
    """Probe-then-exec: 2 invocations, identical cap set, ``--user --scope``.

    The probe is what makes the re-exec FAIL OPEN — one throwaway scope
    creation settles whether the caps are accepted BEFORE the real exec replaces
    the process. The property list lives once, so probe and exec can never
    diverge; this leg is the one that proves they do not.
    """
    cgroup_box.run(SVC_CG, probe_rc=0)
    inv = cgroup_box.invocations()
    assert len(inv) == 2, (
        "expected 2 stub invocations (probe + exec), got %d: %r" % (len(inv), inv))
    for cap in ("MemoryMax=1024M", "MemorySwapMax=512M", "CPUQuota=300%", "TasksMax=128"):
        n = sum(1 for line in inv if cap in line)
        assert n == 2, (
            "%s appears in %d of 2 invocations — the cap set diverged between "
            "probe and exec: %r" % (cap, n, inv))
    assert all("--user --scope" in line for line in inv), (
        "an invocation lacks ``--user --scope``: %r" % inv)

# =============================================================================
# LEG 2 — a REFUSED scope must fail OPEN, never swallow the run
# =============================================================================
def test_refused_scope_fails_open(cgroup_box):
    """A refused scope does NOT replace the run, and is reported as a WARNING.

    A bare ``exec`` never returns, so a refused re-exec would REPLACE the
    battery with systemd-run's exit code — a harness error read as a RED
    verdict. Fail-open is the whole reason the probe exists.
    """
    rc, out = cgroup_box.run(SVC_CG, probe_rc=1)
    assert "SURVIVED" in out, (
        "a refused scope swallowed the run — a harness error would read as a RED "
        "verdict: %r" % out[-400:])
    assert "could not create a transient scope" in out, (
        "the refusal path emitted no diagnostic: %r" % out[-400:])

def test_refusal_makes_exactly_one_attempt(cgroup_box):
    cgroup_box.run(SVC_CG, probe_rc=1)
    inv = cgroup_box.invocations()
    assert len(inv) == 1, (
        "a refusal made %d invocations (expected 1 — no second exec after a "
        "refusal): %r" % (len(inv), inv))

# =============================================================================
# LEG 3 — already outside a service cgroup: no isolation, no re-exec
# =============================================================================
def test_a_scope_cgroup_is_left_alone(cgroup_box):
    """A ``.scope`` leaf is NOT a service — the block must not re-exec.

    The branch is decided on the LEAF unit (``${cg##*/}``), not a substring of
    the full path: every user-manager cgroup sits under ``user@0.service``, so a
    substring test called ANY user cgroup a service and re-exec'd a scope's own
    children. Section 85 LEG 3 caught that; this leg keeps it caught.
    """
    rc, out = cgroup_box.run(SCOPE_CG)
    assert "already outside a service cgroup" in out and "SURVIVED" in out, (
        "an already-isolated .scope cgroup was mis-handled: %r" % out[-400:])

# =============================================================================
# LEG 4 — the documented opt-out
# =============================================================================
def test_opt_out_skips_isolation_entirely(cgroup_box):
    rc, out = cgroup_box.run(SVC_CG, extra_env={"OC_BATTERY_NO_CGROUP": "1"})
    assert "SURVIVED" in out, "OC_BATTERY_NO_CGROUP=1 still re-exec'd: %r" % out[-400:]
    assert cgroup_box.invocations() == [], (
        "the opt-out still invoked systemd-run: %r" % cgroup_box.invocations())

# =============================================================================
# NEGATIVE CONTROL — with the exec neutered, LEG 1's signal must INVERT
# =============================================================================
def test_negative_control_neutered_exec_is_detected(cgroup_box):
    """Without this, LEG 1 could be green because the harness never reaches the
    block, not because isolation works. The mutant removes the ``exec`` line and
    the run must then SURVIVE — proving the leg can fail.
    """
    neutered = cgroup_box.root / "neutered.sh"
    src = cgroup_box.block.read_text(encoding="utf-8")
    mutated = src.replace('      exec "$_oc_sr"', '      : "$_oc_sr"')
    assert mutated != src, (
        "the neuter target ``exec \"$_oc_sr\"`` was not found — this control is "
        "inert until re-armed against the current re-exec line")
    neutered.write_text(mutated, encoding="utf-8")
    rc, out = cgroup_box.run(SVC_CG, probe_rc=0, block=neutered)
    assert "SURVIVED" in out, (
        "a neutered re-exec was NOT detected — LEG 1 is inert (it would pass on a "
        "block that cannot isolate): %r" % out[-400:])

# =============================================================================
# the fail-open WARNINGS for a missing systemd (no scope ever attempted)
# =============================================================================
@pytest.mark.parametrize("absent,needle", [
    ("systemd-run", "no systemd-run"),
    ("systemctl", "no user systemd manager"),
])
def test_missing_systemd_warns_and_survives(cgroup_box, absent, needle):
    """No systemd-run / no user manager: warn and run unisolated, never refuse.

    Driven by REMOVING the stub from the sandbox bin, which is the only way to
    reach this arm without touching the host's real systemd.
    """
    (cgroup_box.sb / absent).unlink()
    rc, out = cgroup_box.run(SVC_CG)
    assert "SURVIVED" in out, (
        "a missing %s swallowed the run instead of warning: %r" % (absent, out[-400:]))
    assert needle in out, (
        "no diagnostic naming the missing %s: %r" % (absent, out[-400:]))
