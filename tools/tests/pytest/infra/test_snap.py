"""Ported: `lib/oc-snap.sh` — run.sh §59 (mirror age) and §60 (reap).

Both sections exist because an instrument reported a **confident zero** or a
**confident age** that was a lie, and nothing downstream could tell.

§59 — THE MIRROR'S AGE IS ITS OWN BIRTH. ``cp -a "$src/." "$mir/"`` applies the
SOURCE DIRECTORY's attributes to the destination root, so every mirror is born
carrying ``tools/``'s mtime — all mirrors share ONE mtime to the nanosecond,
predating their own births. The only reader of that mtime is an age instrument,
so each mirror reads stale the instant it exists. The discriminating input is a
tools tree with a DELIBERATELY OLD mtime: a mirror that inherits it reads 22
days old, one that carries its own birth reads seconds old.

THE MUTANT IS THE REAL HALF. It re-stamps the mirror root to INHERIT the source
age — the identical fixture, the identical run, and the only difference is
whether the root carries its own birth. That reproduces #51 rather than merely
deleting a line, and it ASSERTs its mutation target is present: matching a stale
name silently disabled this control for a whole battery cycle, after which a
regressed tool still satisfied the comparison and the leg called itself
load-bearing.

§60 — A FALSE ZERO IS NOT A VERDICT. ``oc_snap_reap --dry-run -v`` read ``-v``
as the ROOT, scanned a directory that did not exist, and printed a confident
``0`` with rc 0 — the exact reading a lane auditing disk space takes at face
value. Four legs, and the negative control is what stops a
reject-everything mutant from scoring green.

The ``EXIT``-trap leg is a SOURCE assertion and is labelled as one: a run cannot
observe its own cleanup from inside itself, so the WIRING is what is checkable.
"""

from __future__ import annotations

import os
import time

import pytest

import conftest as cf

LIB = cf.TOOLS_DIR / "lib" / "oc-snap.sh"

OLD = "2026-09-28 09:13:41"

DEMO_TOOL = """#!/usr/bin/env bash
. "$(dirname "$0")/../lib/oc-snap.sh"
oc_snap_guard "$0" "$@"
echo "ran-from=$0"
"""

def _source(lib_dir, snippet, *, env, run_tool, timeout=120, args=()):
    """Run ``snippet`` in a bash that has sourced a COPY of the library.

    ``$1`` is the lib dir; anything in ``args`` follows as ``$2``, ``$3``…
    """
    return run_tool(["bash", "-c", snippet, "_", str(lib_dir), *args],
                    timeout=timeout, env=env)

# =============================================================================
# §59 — the mirror's age is its own birth
# =============================================================================
@pytest.fixture
def snap_tree(scratch):
    """A tools tree with a DELIBERATELY OLD mtime, plus a demo tool that guards.

    The age is the input, not decoration: a tree born now cannot discriminate an
    inherited mtime from an owned one.
    """
    root = scratch.path / "snap59"
    (root / "tools" / "lib").mkdir(parents=True, exist_ok=True)
    (root / "tools" / "demo").mkdir(parents=True, exist_ok=True)
    (root / "mir").mkdir(parents=True, exist_ok=True)
    (root / "tools" / "lib" / "oc-snap.sh").write_text(LIB.read_text())
    demo = root / "tools" / "demo" / "oc-demo59"
    demo.write_text(DEMO_TOOL)
    demo.chmod(0o755)
    old = time.mktime(time.strptime(OLD, "%Y-%m-%d %H:%M:%S"))
    os.utime(root / "tools", (old, old))
    return cf.Node(root, tools=root / "tools", mir=root / "mir",
                   demo=demo, src_mtime=int(old))

def test_mirror_does_not_inherit_the_source_mtime(snap_tree, run_tool):
    """The defect itself: a mirror born 22 days old.

    A mirror that inherits the tree's mtime makes the age instrument read a lie,
    and nothing else in the fleet reads that mtime — so this is the only place
    the lie is catchable.
    """
    now = int(time.time())
    res = run_tool(["bash", str(snap_tree.demo)], timeout=120,
                   env={"OC_TOOLS_DIR": str(snap_tree.tools),
                        "OC_SNAP_ROOT": str(snap_tree.mir),
                        "OC_SNAP_VERBOSE": "1"})
    mirrors = sorted(snap_tree.mir.glob("oc-snap-*"))
    assert mirrors, ("the guard created NO mirror (rc=%s) — the #59 legs cannot "
                     "judge anything\n%s" % (res.rc, res.combined[-600:]))
    assert "ran-from=" in res.out and "oc-snap-" in res.out, \
        "the guard did not EXEC from the mirror: %r" % res.out[-300:]

    mir_mtime = int(mirrors[0].stat().st_mtime)
    assert mir_mtime != snap_tree.src_mtime, \
        ("the mirror INHERITED the source tree's mtime (%d) — the age instrument "
         "reads a lie (#51)" % mir_mtime)
    assert abs(now - mir_mtime) <= 120, \
        ("the mirror's mtime is %d day(s) off its birth, not within 120 s — #51 "
         "regressed" % ((now - mir_mtime) // 86400))

def test_mutant_that_inherits_the_age_reproduces_the_defect(snap_tree, scratch, run_tool):
    """THE CONTROL: the leg above must be able to go red.

    The identical fixture with the re-stamp made to INHERIT the source age. If
    this does not reproduce #51, the leg above proves nothing — it is asserting
    the fixture, not the fix (CODE.md item 3).

    The mutation asserts its own target is present. A silently-missed target
    leaves the file unmutated, and a broken tool then satisfies the comparison
    and reports a FALSE ok that calls itself load-bearing.
    """
    mut = scratch.path / "snap59m"
    (mut / "mir").mkdir(parents=True, exist_ok=True)
    (mut / "tools").mkdir(parents=True, exist_ok=True)
    # cp -a so the OLD mtime travels with the tree
    # `cp -a SRC DST` where DST exists puts SRC INSIDE it, so copy into the
    # parent and keep the ``tools/`` name the guard resolves from.
    sub = run_tool(["cp", "-a", str(snap_tree.tools), str(mut)], timeout=60)
    assert sub.rc == 0, "could not stage the mutant tree: %s" % sub.err

    lib = mut / "tools" / "lib" / "oc-snap.sh"
    assert lib.is_file(), "the mutant tree has no lib copy at %s" % lib
    src = lib.read_text()
    stamp = 'touch "$_os_stage" 2>/dev/null'
    inherit = 'touch -r "$_os_sd" "$_os_stage" 2>/dev/null'
    assert stamp in src, (
        "mutant target %r not found in oc-snap.sh — the publish path moved; "
        "re-arm this control before trusting the #59 leg" % stamp)
    lib.write_text(src.replace(stamp, inherit))
    # cp -a may have refreshed the parent; pin the age again on the mutant tree.
    old = time.mktime(time.strptime(OLD, "%Y-%m-%d %H:%M:%S"))
    os.utime(mut / "tools", (old, old))

    res = run_tool(["bash", str(mut / "tools" / "demo" / "oc-demo59")],
                   timeout=120,
                   env={"OC_TOOLS_DIR": str(mut / "tools"),
                        "OC_SNAP_ROOT": str(mut / "mir")})
    mirrors = sorted((mut / "mir").glob("oc-snap-*"))
    assert mirrors, ("the mutant created no mirror (rc=%s) — the control cannot "
                     "judge\n%s" % (res.rc, res.combined[-600:]))
    mut_mtime = int(mirrors[0].stat().st_mtime)
    src_mtime = int((mut / "tools").stat().st_mtime)
    assert mut_mtime == src_mtime, (
        "the mutant did NOT reproduce #51 (mirror mtime %d, source %d) — the leg "
        "above proves nothing" % (mut_mtime, src_mtime))

# =============================================================================
# §60 — a false zero is not a verdict
# =============================================================================
@pytest.fixture
def reap_lib(scratch):
    """A private lib copy + a mirror population the reaper can count."""
    d = scratch.path / "snap60"
    (d / "lib").mkdir(parents=True, exist_ok=True)
    (d / "mir" / "oc-snap-999999999").mkdir(parents=True, exist_ok=True)
    (d / "lib" / "oc-snap.sh").write_text(LIB.read_text())
    return cf.Node(d, lib=d / "lib" / "oc-snap.sh", mir=d / "mir")

def test_unknown_option_is_refused_not_read_as_the_root(reap_lib, run_tool):
    """#53: an unrecognised flag must not BECOME the root.

    Pre-fix, ``--dry-run -v`` scanned a directory named ``-v``, found nothing,
    and printed a confident ``0`` with rc 0 — indistinguishable from a clean box,
    which is the reading a lane auditing disk space takes at face value.
    """
    res = _source(reap_lib, '. "$1/lib/oc-snap.sh"; oc_snap_reap --dry-run -v',
                  env={}, run_tool=run_tool)
    assert res.rc != 0, \
        ("oc-snap reap accepted an unknown option (rc=%s) — a bad invocation "
         "still reports a confident zero\n%s" % (res.rc, res.combined[-400:]))
    assert "unknown option" in res.err, \
        "reap rejected the option WITHOUT naming it on stderr: %r" % res.err[-300:]

def test_dry_run_still_counts_the_population(reap_lib, run_tool):
    """The legitimate path must survive the guard.

    Without this leg a reject-everything mutant would score green.
    """
    res = _source(reap_lib, '. "$1/lib/oc-snap.sh"; oc_snap_reap --dry-run',
                  env={"OC_SNAP_ROOT": str(reap_lib.mir)}, run_tool=run_tool)
    assert res.out.strip() == "1", \
        ("reap --dry-run counted %r instead of 1 — the flag guard broke the real "
         "path\n%s" % (res.out.strip(), res.combined[-400:]))

def test_nonexistent_root_is_refused(reap_lib, run_tool):
    """A root that is not a directory cannot hold a population, so it must not
    report one — the same false-zero class, one step out."""
    res = _source(reap_lib,
                  '. "$1/lib/oc-snap.sh"; oc_snap_reap /nonexistent-root-60',
                  env={}, run_tool=run_tool)
    assert res.rc != 0, \
        ("reap reported success on a nonexistent root — a false zero\n%s"
         % res.combined[-400:])

def test_the_gate_wires_the_reap_onto_its_scratch_fixture():
    """SOURCE assertion, labelled as one.

    A run cannot observe its own cleanup from inside itself — the reap runs
    after the last test — so the WIRING is what is checkable.

    Retargeted from ``run.sh``'s EXIT trap, which died with the shell harness.
    The gate's equivalent is ``conftest.scratch``: the controller sweeps roots
    whose owner pid is dead, then claims a fresh one. Mutant: delete the
    ``_reap_dead_roots`` calls — this reddens while every other #60 leg stays
    green, because those legs drive ``oc_snap_reap`` directly.
    """
    text = (cf.PYTEST_DIR / "conftest.py").read_text(encoding="utf-8")
    assert "_reap_dead_roots(tmp_path_factory.getbasetemp().parent)" in text, (
        "the scratch fixture no longer sweeps dead roots under the pytest "
        "basetemp — every kill -9'd run leaves its mirrors behind (#53)")
    assert '_reap_dead_roots(Path(os.environ.get("TMPDIR") or "/tmp"))' in text, (
        "the scratch fixture no longer sweeps the shared TMPDIR — the roots a "
        "SIGKILLed run left there are never reclaimed (#53)")
    assert "def _reap_dead_roots(" in text, (
        "the scratch fixture calls a reaper the gate does not define")

def test_stage_dir_arm_fires_and_spares_a_live_pid(reap_lib, run_tool):
    """#131: THE STAGE-DIR ARM MUST BE ABLE TO FIRE, and must spare a live pid.

    It shipped reading ``_osr_pid="${_osr_tail%%.*}"``, which left the tool name
    attached (``oc-deploy-999999``), so the numeric guard rejected EVERY stage
    dir and the arm reaped nothing while reporting a confident 0. The mirror legs
    cover a different population, which is exactly why the dead arm survived.

    The negative control is half the test: without it, a reaper that deletes
    every stage dir it sees would score green.
    """
    stage = reap_lib / "stage"
    dead = stage / ".oc-snap-stage-oc-deploy-999999.4242"
    dead.mkdir(parents=True)
    (dead / "f").write_text("x")

    dry = _source(reap_lib,
                  '. "$1/lib/oc-snap.sh"; oc_snap_reap --dry-run "$2"',
                  env={}, run_tool=run_tool, args=(str(stage),))
    assert dry.out.strip() == "1", \
        ("reap counted %r leaked stage dirs instead of 1 — the stage arm cannot "
         "fire (#131)" % dry.out.strip())

    real = _source(reap_lib, '. "$1/lib/oc-snap.sh"; oc_snap_reap "$2"',
                   env={}, run_tool=run_tool, args=(str(stage),))
    assert real.out.strip() == "1" and not dead.exists(), \
        ("reap reported %r and left the stage dir in place — a false zero "
         "(#131)" % real.out.strip())

    live = stage / (".oc-snap-stage-oc-deploy-%d.777" % os.getpid())
    live.mkdir()
    spared = _source(reap_lib, '. "$1/lib/oc-snap.sh"; oc_snap_reap "$2"',
                     env={}, run_tool=run_tool, args=(str(stage),))
    assert spared.out.strip() == "0" and live.exists(), \
        ("reap reported %r on a LIVE stage dir and/or removed it — the arm reaps "
         "what it must protect (#131)" % spared.out.strip())
