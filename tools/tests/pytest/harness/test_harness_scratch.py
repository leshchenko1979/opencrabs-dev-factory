"""The battery's per-run scratch root, and the lock that must NOT move with it
(#171, plus #92 leg (a)).

WHAT THIS PORTS
    ``run.sh`` section 92 (``section "battery scratch root: one per-run
    TEST_TMPDIR, lock stays shared (#171)"``) — six legs (a)-(e), including the
    ownership/reap pair.

THE TRAP THIS MODULE EXISTS FOR
    The change moves the battery's scratch (every ``mktemp`` plus the ~33
    ``oc-snap`` mirrors) onto one per-run root, tmpfs when it fits. Its one
    correctness trap is the LOCK: ``BATTERY_LOCK`` used to default to
    ``${TMPDIR:-/tmp}/oc-battery.lock``, which was a single shared path only
    because TMPDIR was shared. With TMPDIR per-run, a TMPDIR-derived default
    hands every lane its OWN lock while the lanes still share
    ``tools/tests/battery-last.json`` — mutual exclusion would end silently,
    with a green transcript. ``test_the_lock_default_is_a_fixed_path`` is that
    trap made checkable, and it is asserted from the SOURCE rather than a live
    run because the default is what ships.

WHY EVERY LEG CLEARS ``OC_BATTERY_TEST_TMPDIR`` AND ``TMPDIR``
    This module can run inside a chunk child whose prelude EXPORTED the parent's
    root; an inherited override would make the tmpfs/floor legs assert the
    parent's choice instead of the floor's (the shell harness reddened exactly
    that way while writing it). ``root_override=None`` in ``H.resolve_jobs`` is
    that clearing.

SERIALISATION
    These legs create and remove directories under ``/dev/shm`` and ``TMPDIR``
    and drive the reaper, which walks those trees. ``serial`` +
    ``xdist_group("battery-scratch")`` keeps a sibling lane from filling or
    reaping a root while this one is reading it.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from lib import harness as H

pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-scratch"),
]


def scratch_root_line(out: str) -> str | None:
    """The probe's own ``battery scratch root: <path>`` announcement."""
    m = re.search(r"^\s*battery scratch root: (\S+)", out, re.M)
    return m.group(1) if m else None

# =============================================================================
# (a) SOURCE — the lock default is a FIXED path, never a per-run TMPDIR
# =============================================================================
def test_the_lock_default_is_a_fixed_path():
    """The invariant the whole run's mutual exclusion rests on.

    A per-run TMPDIR plus a TMPDIR-derived lock = every lane has its own lock
    while they share one receipt. That is a green transcript over lost mutual
    exclusion, which is the worst possible failure mode: nothing looks wrong.
    """
    text = H.run_sh_text()
    m = re.search(r'^[ \t]*BATTERY_LOCK="[^"]*"', text, re.M)
    assert m, "no BATTERY_LOCK assignment found in run.sh — the block moved"
    assignment = m.group(0)
    assert re.match(r'^[ \t]*BATTERY_LOCK="\$\{OC_BATTERY_LOCK:-/tmp/oc-battery\.lock\}"',
                    assignment), (
        "the lock default is not the fixed shared path /tmp/oc-battery.lock "
        "(found: %r) — a per-run TMPDIR would un-serialize concurrent lanes "
        "(#171)" % assignment)
    assert "TMPDIR" not in assignment, (
        "the lock path is derived from TMPDIR (%r) — that is the #171 trap: "
        "each lane gets its own lock while sharing one receipt" % assignment)

# =============================================================================
# (b) SOURCE — the root redirects BOTH populations, together
# =============================================================================
def test_the_root_redirects_tmpdir_and_snap_root_together():
    """A root that moved TMPDIR but left the mirrors behind would halve the win.

    The two exports must be the SAME root, and the mirrors must sit under it:
    a split population desyncs the EXIT reap, which deletes one and leaks the
    other.
    """
    text = H.run_sh_text()
    assert re.search(r'^\s*export TMPDIR="\$_oc_bt_root"', text, re.M), (
        "the scratch root is not exported as TMPDIR")
    assert re.search(r'^\s*export OC_SNAP_ROOT="\$_oc_bt_root/oc-snap"', text, re.M), (
        "the scratch root is not exported as OC_SNAP_ROOT under the same root — "
        "one population would stay on the old root")

# =============================================================================
# (c) LIVE — an explicit root is honoured, announced, and removed on exit
# =============================================================================
def test_an_explicit_root_is_honoured_announced_and_removed(tmp_path):
    """``OC_BATTERY_TEST_TMPDIR`` is used, named, and reaped on a clean exit.

    ``--resolve-jobs`` exits before any section, so this costs one preflight
    rather than a battery — and it is the same code path the A/B arms use.
    """
    root = tmp_path / "root"
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "probe",
                       root_override=str(root))
    got = scratch_root_line(r["_stdout"])
    assert got == str(root), (
        "the run did not adopt OC_BATTERY_TEST_TMPDIR=%s (announced %r)"
        % (root, got))
    assert not root.exists(), (
        "the run left its scratch root behind on a clean exit (%s) — a leaked "
        "root per run fills the disk" % root)

# =============================================================================
# (d) LIVE — the tmpfs branch and its floor are REAL, not decorative
# =============================================================================
def _tmpfs_candidate() -> str | None:
    """``/dev/shm`` when it is genuinely tmpfs here, else None."""
    if not os.path.isdir("/dev/shm"):
        return None
    r = subprocess.run(["stat", "-f", "-c", "%T", "/dev/shm"],
                       capture_output=True, text=True)
    return "/dev/shm" if r.returncode == 0 and "tmpfs" in r.stdout else None

def test_opting_in_to_tmpfs_puts_the_root_on_tmpfs(tmp_path):
    """POSITIVE CONTROL for the floor leg below.

    Without it the floor leg cannot tell a working floor from a branch that never
    runs. A satisfiable floor plus an explicit tmpfs candidate MUST choose tmpfs.
    """
    cand = _tmpfs_candidate()
    if cand is None:
        pytest.skip("/dev/shm is not tmpfs here — the tmpfs-branch legs cannot run")
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "probe",
                       root_override=None,
                       env_extra={"OC_BATTERY_SHM_DIR": cand,
                                  "OC_BATTERY_SHM_MIN_MB": "1"})
    got = scratch_root_line(r["_stdout"]) or ""
    assert got.startswith(cand + "/oc-battery-"), (
        "CONTROL FAILED: %s with a satisfiable floor did not choose tmpfs "
        "(announced %r) — the floor leg below would prove nothing" % (cand, got))

def test_an_impossible_tmpfs_floor_falls_back_to_disk(tmp_path):
    """An unsatisfiable floor must move the root OFF tmpfs.

    The floor protects a lane running ``-n N``, where N sections' fixtures
    coexist. A floor that is never consulted is a cap that is not a cap.
    """
    cand = _tmpfs_candidate()
    if cand is None:
        pytest.skip("/dev/shm is not tmpfs here — the floor leg cannot run")
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "probe",
                       root_override=None,
                       env_extra={"OC_BATTERY_SHM_DIR": cand,
                                  "OC_BATTERY_SHM_MIN_MB": "999999999"})
    got = scratch_root_line(r["_stdout"]) or ""
    assert got, "the fallback run announced no scratch root at all"
    assert not got.startswith(cand + "/"), (
        "OC_BATTERY_SHM_MIN_MB=999999999 still chose %s — the floor is not "
        "consulted (#171)" % cand)

def test_the_default_root_is_on_disk_not_tmpfs(tmp_path):
    """The SHIPPED default is disk: tmpfs is opt-in.

    This is the A/B verdict — 1.26 % median gain against a 10 % keep bar — so a
    /dev/shm default here is a regression of that trade, not a
    performance improvement.
    """
    cand = _tmpfs_candidate()
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "probe",
                       root_override=None)
    got = scratch_root_line(r["_stdout"]) or ""
    assert got, "the default run announced no scratch root"
    if cand:
        assert not got.startswith(cand + "/"), (
            "the DEFAULT scratch root is on tmpfs (%r) — step 7's A/B measured "
            "1.26%% against a 10%% bar, so tmpfs must stay opt-in via "
            "OC_BATTERY_SHM_DIR (#171)" % got)

# =============================================================================
# (e) OWNERSHIP — an inherited root is used, and NEVER deleted
# =============================================================================
def test_an_inherited_live_root_is_used_but_not_deleted(tmp_path):
    """A nested run must not delete the tree its parent and siblings are filling.

    In the shell harness, ``OC_BATTERY_TEST_TMPDIR=$R run.sh
    --resolve-jobs`` deletes $R and a canary inside it. Under ``--jobs N`` that
    is the tree N siblings are still writing, and section 10's own capture file
    vanishes mid-section — turning a real verdict into a red one whose evidence
    was unlinked.
    """
    root = tmp_path / "inherited"
    root.mkdir()
    canary = root / "canary"
    canary.write_text("alive\n", encoding="utf-8")
    # A LIVE owner marker: this test process is alive for the whole leg, so a
    # nested run must read the tree as inherited and leave it alone.
    (root / ".oc-battery-owner").write_text("%d\n" % os.getpid(), encoding="utf-8")

    H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "probe",
                   root_override=str(root))
    assert canary.exists(), (
        "a nested run deleted its parent's scratch root — chunk children and "
        "--resolve-jobs probes would wreck a live run (#171)")

def test_a_root_left_by_a_dead_owner_is_adopted_and_removed(tmp_path):
    """A ``kill -9`` leaves a marker naming a dead pid; the next run must adopt.

    Without adoption the stale marker makes that directory immortal: every
    future run reads it as "someone else's, leave it", so the leak is permanent.
    """
    root = tmp_path / "orphaned"
    root.mkdir()
    (root / ".oc-battery-owner").write_text("999999\n", encoding="utf-8")
    H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "probe",
                   root_override=str(root))
    assert not root.exists(), (
        "a root whose owner was kill -9'd was NOT adopted and removed — a stale "
        "marker makes it immortal (#171)")
