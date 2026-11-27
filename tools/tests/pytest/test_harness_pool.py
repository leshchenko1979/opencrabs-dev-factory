"""Section 66, part 2 of 6 — the FIVE blocks swallowed by ONE ``section`` call.

THE SPLIT
    ``run.sh:4682`` reads ``section "cgroup isolation (#720)"`` and opens a span
    of **569 lines**. Six numbered blocks execute under that single call:

        #85  cgroup isolation (#720)      -> test_harness_cgroup.py
        #86  no arg arm swallows a value  (#750)  <-- here
        #87  law-digest SET coverage      (#47)   <-- here
        #88  pids budget preflight        (#74)   <-- here
        #89  default jobs=1 + low priority(#76)   <-- here
        #90  oc-patch "else empty"        (#114)  <-- here
        #91  battery lock (#107)          -> test_harness_lock.py

    Blocks #86-#90 have their own ``# ---- `` header and NO ``section`` call of
    their own. So the transcript names one section, the receipt's per-section
    timing attributes six blocks' wall to it, and a reader of a red transcript
    sees a cgroup failure when the failing leg was #114. This module gives each
    of the five its own test, named for what it guards.

WHY EACH BLOCK IS DRIVEN, NEVER RETYPED
    #88 and #89 both ship a ``_pf*`` probe family that calls ``run.sh
    --resolve-jobs`` — the real arithmetic, not a second copy of it. #86 and #87
    run the block's OWN python scanner over a fixture tree. #90 sources the real
    ``lib/oc-patch.sh`` under the real caller flags. A retyped leg would stay
    green while the harness kept the bug.

WHY WALL-CLOCK IS NEVER ASSERTED
    #89's shell legs include a 3-6 s wall window for the driver, and #76's
    original defect was measured as a wall regression. Under ``-n N`` on this box
    that window reds for the same reason it reddened under ``--jobs 2``. Where a
    timing property matters the port asserts an OBSERVED concurrency or a
    CPU-time-immune structural fact instead, and says so at the leg.

MARKERS
    ``#88``/``#89`` spawn ``run.sh --resolve-jobs`` probes that create and remove
    scratch roots and take lock files; ``#90`` writes a git state repo. All three
    are ``serial`` + ``xdist_group("battery-pool")``. ``#86``/``#87`` are pure
    scans and run anywhere, but they live in this module so the split is legible
    as one file per section-66 block group.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from lib import harness as H

POOL_MARKERS = [pytest.mark.serial, pytest.mark.xdist_group("battery-pool")]


def _pf_env(tmp: Path, pids_max: str) -> dict:
    """The environment ``_pf``/``_pf_nojobs`` build, for a direct probe call."""
    pm = tmp / "pm"
    pm.write_text(pids_max + "\n", encoding="utf-8")
    return {"OC_BATTERY_PIDS_MAX_FILE": str(pm)}


# =============================================================================
# #86 — no arg arm may swallow a missing flag value (#750)
# =============================================================================
HG_SCANNER = r'''
import os,re,sys
root=sys.argv[1]
arm=re.compile(r'^\s*(--[a-z][a-z0-9-]*)\)(.*)$')
bail=re.compile(r'\b(usage|die|fail|exit|return)\b')
for dp,_,fns in os.walk(root):
    if '__pycache__' in dp: continue
    for fn in sorted(fns):
        if not fn.startswith('oc-'): continue
        if '.bak' in fn or fn.endswith(('.orig','.rej')): continue
        p=os.path.join(dp,fn)
        try: lines=open(p,encoding='utf-8',errors='replace').read().split('\n')
        except OSError: continue
        for i,l in enumerate(lines,1):
            m=arm.match(l)
            if not m: continue
            body=m.group(2)
            if '${2:-}' not in body or 'shift 2' not in body: continue
            pre=body[:body.index('shift 2')].replace('${2:-}','')
            if bail.search(pre): continue
            print("%s:%d"%(p,i))
'''


def scan_arg_arms(root: Path) -> list[str]:
    """``<file>:<line>`` for every UNGUARDED value-taking ``--flag)`` arm.

    The shape is ``--flag) VAR="${2:-}"; shift 2 ;;`` with no bail before the
    assignment: when the flag is the LAST argument, ``shift 2`` with ``$#=1``
    returns 1 and does NOT shift, so the loop re-reads the same ``$1`` forever
    and ``${2:-}`` suppresses the unbound-variable error that would have killed
    it. 59 arms across 14 tools had this; every one reachable by a typo.
    """
    r = H.run([sys.executable, "-c", HG_SCANNER, str(root)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "the arg-arm scanner failed: %r" % r.stderr[-500:]
    return [l for l in r.stdout.splitlines() if l.strip()]


def test_no_unguarded_value_taking_arg_arm_in_the_fleet():
    """No tool in the fleet can HANG on a flag whose value is missing (#750).

    Keyed on SHAPE, never on a tool name, so a new tool inherits the guard
    simply by existing — and a new defect is caught without anyone adding it to
    a list.
    """
    hits = scan_arg_arms(H.TOOLS_DIR)
    assert hits == [], (
        "%d unguarded value-taking arg arm(s) — each HANGS forever when its "
        "flag is the last argument (#750):\n  %s"
        % (len(hits), "\n  ".join(hits)))

def test_the_arg_arm_scanner_flags_the_shape_and_only_the_shape(tmp_path):
    """NEGATIVE CONTROL — two-sided, or the scan above is inert.

    A scanner that flagged everything would pass the first leg while reporting
    every healthy arm as a defect; a scanner that flagged nothing would pass it
    vacuously. The fixture carries one broken arm and one guarded arm, and only
    the broken one may be reported.
    """
    (tmp_path / "oc-fake").write_text(
        '#!/bin/sh\nwhile [ $# -gt 0 ]; do case "$1" in\n'
        '  --repo) REPO="${2:-}"; shift 2 ;;\n'
        'esac; done\n', encoding="utf-8")
    (tmp_path / "oc-good").write_text(
        '#!/bin/sh\nwhile [ $# -gt 0 ]; do case "$1" in\n'
        '  --repo) [ $# -ge 2 ] || { echo x; exit 2; }; REPO="$2"; shift 2 ;;\n'
        '  --issue) ISSUE="${2:-}"; [ -n "$ISSUE" ] || usage; shift 2 ;;\n'
        'esac; done\n', encoding="utf-8")
    hits = scan_arg_arms(tmp_path)
    assert hits == ["%s:3" % (tmp_path / "oc-fake")], (
        "the scanner did not isolate the broken fixture (got %r) — this leg is "
        "inert" % (hits,))

# =============================================================================
# #87 — the law-digest SET covers the tree (#47)
# =============================================================================
LAW_SCANNER = r'''
import re,sys,os
tool,root=sys.argv[1],sys.argv[2]
try: src=open(tool).read()
except OSError: print("NOSET"); raise SystemExit(0)
m=re.search(r'^LAW_FILES=\((.*?)^\)', src, re.S|re.M)
if not m: print("NOSET"); raise SystemExit(0)
declared=set(m.group(1).split())
excl={"CHANGELOG.md","README.md"}
present={f for f in os.listdir(root) if os.path.isfile(os.path.join(root,f))}
top={f for f in present if f.endswith(".md")}
print("MISSING:"+",".join(sorted(top-declared-excl)))
print("PHANTOM:"+",".join(sorted(declared-present)))
print("COUNT:%d"%len(declared))
'''


def law_scan(root: Path) -> dict:
    """Read ``LAW_FILES`` FROM THE TOOL and compare it with the tree.

    Read from the tool rather than re-listed: a second copy would drift, and the
    copy that drifts is the one nobody reads. Two documented exclusions —
    ``CHANGELOG.md`` (written by the bumper in the same act) and ``README.md``
    (the tool-fleet surface).
    """
    tool = H.TOOLS_DIR / "state" / "oc-ledger"
    r = H.run([sys.executable, "-c", LAW_SCANNER, str(tool), str(root)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "the law scanner failed: %r" % r.stderr[-500:]
    out = r.stdout
    if "NOSET" in out:
        pytest.fail("LAW_FILES not found in oc-ledger — the coverage leg cannot "
                    "read the set")
    def field(name):
        m = re.search(r"^%s:(.*)$" % name, out, re.M)
        return m.group(1) if m else ""
    return {"missing": [x for x in field("MISSING").split(",") if x],
            "phantom": [x for x in field("PHANTOM").split(",") if x],
            "count": int(field("COUNT") or 0)}


def test_every_top_level_law_file_is_declared_in_the_digest_set():
    """A law file in the tree but not in ``LAW_FILES`` is invisible to the digest.

    That is the same defect one layer out: a check built to make law edits
    visible, with a coverage boundary that silently excludes the new file.
    """
    got = law_scan(H.tools_root())
    assert got["count"] >= 10, (
        "LAW_FILES declares %d law files — expected the full law set (>=10; the "
        "set grows as law files split)" % got["count"])
    assert got["missing"] == [], (
        "UNDECLARED law file(s) would be invisible to the digest: %s — add them "
        "to LAW_FILES in oc-ledger (#47)" % ", ".join(got["missing"]))

def test_the_digest_set_has_no_phantom_entry():
    """The inverse direction: a declared name that does not exist hashes ABSENT.

    ABSENT is stable, so the leg never reddens and the set silently shrinks —
    the digest then claims coverage it does not have.
    """
    got = law_scan(H.tools_root())
    assert got["phantom"] == [], (
        "LAW_FILES names file(s) that do NOT exist (their hash is ABSENT "
        "forever): %s (#47)" % ", ".join(got["phantom"]))

def test_the_law_scanner_flags_an_undeclared_file(tmp_path):
    """NEGATIVE CONTROL — membership, not position (#71).

    ``MISSING:`` carries a comma-joined SORTED list, so a substring glob only
    matches while the injected name happens to sort first — i.e. while the real
    tree has no other undeclared file. The moment one exists the control
    reported "scanner missed" about a scanner that had worked, blaming the
    instrument for the tree's own state.
    """
    root = H.tools_root()
    for f in root.glob("*.md"):
        if f.is_file():
            (tmp_path / f.name).touch()
    (tmp_path / "zz-undeclared-law.md").touch()
    got = law_scan(tmp_path)
    assert "zz-undeclared-law.md" in got["missing"], (
        "the scanner did not flag the injected undeclared file (MISSING: %r) — "
        "the coverage leg is inert" % (got["missing"],))

# =============================================================================
# #88 — pids budget preflight (#74)
# =============================================================================
@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_jobs_4_under_pids_max_64_is_capped_to_2(tmp_path):
    """The MEASURED defect, driven through the real arithmetic.

    One tree, one commit: ``--jobs 4`` -> 390 PASS / 8 FAIL carrying 63
    "Resource temporarily unavailable" rows; ``--jobs 2`` -> 398/0. ``dmesg``
    named the run's own scope with ``pids.max=64``. So 64 pids and 4 chunks
    cannot both hold, and the run must cap to 2 — the shape that ran green.
    """
    r = H.resolve_jobs(pids_max="64", jobs="4", tmp=tmp_path)
    assert r["jobs"] == "2", (
        "--jobs 4 under pids.max=64 resolved to %r (want 2) — the cap is inert"
        % r["jobs"])
    assert r["capped"] == "yes", (
        "the cap fired but was not DISCLOSED (capped=%r) — a silent cap is "
        "indistinguishable from a slower box" % r["capped"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_pids_max_of_max_caps_nothing(tmp_path):
    """``max`` is an UNBOUNDED budget, never a zero one.

    Reading it as a number would cap the fleet to 1 job on any box whose pids
    controller is disabled — a silent throughput collapse that looks like a
    loaded host.
    """
    r = H.resolve_jobs(pids_max="max", jobs="4", tmp=tmp_path)
    assert r["jobs"] == "4", (
        "pids.max=max resolved to %r (want 4) — 'max' was read as a number"
        % r["jobs"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_a_pids_budget_below_one_chunk_floors_at_one(tmp_path):
    """The FLOOR: 16/32 = 0, and ``JOBS=0`` runs NOTHING while printing green.

    A silent all-green over zero tests is worse than a red — there is no signal
    at all that the suite did not run.
    """
    r = H.resolve_jobs(pids_max="16", jobs="4", tmp=tmp_path)
    assert r["jobs"] == "1", (
        "pids.max=16 resolved to %r (want 1) — a zero cap runs nothing while "
        "printing a clean sweep" % r["jobs"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_pids_cap_opt_out_is_real(tmp_path):
    """``OC_BATTERY_NO_PIDS_CAP=1`` must actually opt out, or the cap leg above
    could be passing on something other than the cap.
    """
    r = H.resolve_jobs(pids_max="64", jobs="4", tmp=tmp_path,
                       env_extra={"OC_BATTERY_NO_PIDS_CAP": "1"})
    assert r["jobs"] == "4", (
        "the opt-out still capped to %r — the knob is decorative" % r["jobs"])

# =============================================================================
# #89 — default jobs=1 and low priority for the parent (#76)
# =============================================================================
@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_default_jobs_is_one_never_nproc(tmp_path):
    """The battery is BACKGROUND work: it must lose every race to the daemon.

    Measured 2026-11-17: the default ``$(nproc)=4`` cost an hour of stall — disk
    86-95 % busy, swap 250 MB -> 1 GB, ~150 major faults/s, 16 daemon threads
    blocked on page faults. Same tree, same commit: jobs=2 -> 747 s, jobs=1 ->
    1171 s, both 398/0 — the wall is the intended trade.
    """
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path)
    assert r["jobs"] == "1", (
        "with OC_BATTERY_JOBS unset the default resolved to %r (want 1) — the "
        "battery still fans out on its own" % r["jobs"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_parent_actually_runs_at_nice_19(tmp_path):
    """Read back from ``ps``, never from the value we asked for.

    ``renice`` can be refused, and a receipt claiming nice 19 while the run sat
    at 0 is worse than no claim at all.
    """
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path)
    assert r["nice"] == "19", (
        "the parent's nice read %r (want 19) — the priority drop is inert"
        % r["nice"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_parent_actually_runs_at_io_class_idle(tmp_path):
    """I/O class idle (``ionice -c3``), where the box honours it."""
    r = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path)
    assert r["ioprio"] == "idle", (
        "the parent's ioprio read %r (want idle) — I/O priority unchanged"
        % r["ioprio"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_both_jobs_overrides_survive_the_new_default(tmp_path):
    """A lane that needs the old speed must have a way back to it.

    Both the env var and the flag, because they take different code paths and a
    default change is exactly what breaks one of them.
    """
    via_env = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "env",
                             env_extra={"OC_BATTERY_JOBS": "2"})
    assert via_env["jobs"] == "2", (
        "OC_BATTERY_JOBS=2 resolved to %r (want 2)" % via_env["jobs"])
    via_flag = H.resolve_jobs(pids_max="max", jobs="2", tmp=tmp_path / "flag")
    assert via_flag["jobs"] == "2", (
        "--jobs 2 resolved to %r (want 2)" % via_flag["jobs"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_pids_cap_still_bites_on_top_of_an_explicit_jobs(tmp_path):
    """The issue asked for the preflight to be KEPT, and "kept" is only true if
    it still bites after the default moved.
    """
    r = H.resolve_jobs(pids_max="16", jobs="2", tmp=tmp_path)
    assert r["jobs"] == "1", (
        "--jobs 2 under pids.max=16 resolved to %r (want 1) — the cap was "
        "dropped when the default changed" % r["jobs"])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_the_renice_is_not_defeated_by_inheritance(tmp_path):
    """NEGATIVE CONTROL, paired and from an explicit nice-0 baseline.

    MEASURED THE HARD WAY (battery 2026-11-17T15:21:35Z, 411 PASS / 1 FAIL):
    inside the battery this control read nice 19 from the MUTANT and reported
    the renice leg inert — because the battery has already reniced ITSELF to 19,
    so every child inherits 19 and a neutered renice is indistinguishable from a
    working one. The control was defeated by INHERITANCE, which is exactly the
    class of defect it exists to catch.

    ``renice`` is ABSOLUTE, so from an explicit 0 baseline the real block reads
    19 and the neutered copy reads 0. Both halves must be asserted, or a
    single-sided check cannot discriminate when the inherited value already
    equals the target.
    """
    # Baseline: can we get to nice 0 at all?
    r_real = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "real",
                            baseline_nice0=True)
    assert r_real["nice"] == "19", (
        "from a nice-0 baseline the REAL block read %r (want 19) — the renice "
        "did not run" % r_real["nice"])

    # The mutant: `if renice -n 19 -p $$ ...; then` -> `if false; then`
    src = H.run_sh_text()
    pat = re.compile(r"^(\s*)if renice -n 19 -p \$\$ >/dev/null 2>&1; then$", re.M)
    m = pat.search(src)
    assert m, ("the renice line was not found — this control is inert until "
               "re-armed against the current renice statement")
    mutant = pat.sub(lambda mm: "%sif false; then" % mm.group(1), src, count=1)
    mut_script = tmp_path / "run.sh-mut76"
    mut_script.write_text(mutant, encoding="utf-8")

    r_mut = H.resolve_jobs(pids_max="max", jobs=None, tmp=tmp_path / "mut",
                           script=mut_script, baseline_nice0=True)
    assert r_mut["nice"] != "19", (
        "from a nice-0 baseline the NEUTERED copy also read 19 — LEG 'parent "
        "runs at nice 19' is inert (it would pass on a block with no renice)")

# =============================================================================
# #90 — lib/oc-patch.sh: "else empty" must mean rc 0, never abort (#114)
# =============================================================================
OP_LIB = H.TOOLS_DIR / "lib" / "oc-patch.sh"


def _oc_job_sha(job_name: str) -> tuple[str, int]:
    """Mirror the caller shape ``js="$(oc_job_sha "$jn")"`` under errexit.

    The ASSIGNMENT form, not a printf argument — only the assignment trips
    ``set -e``, and that distinction is the whole defect.
    """
    r = H.run(
        ["bash", "-c",
         'set -e; set -o pipefail; . "$1" || exit 9; '
         'js="$(oc_job_sha "$2")"; printf "%s" "$js"',
         "_", str(OP_LIB), job_name],
        capture_output=True, text=True, timeout=60)
    return r.stdout, r.returncode


@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_a_sha_less_job_name_is_empty_with_rc_0():
    """The defect: a no-match pipeline returns non-zero, the ASSIGNMENT fails,
    and ``set -e`` aborts the caller BEFORE the line handling the empty case.

    ``oc-ship`` died rc=1 with no stderr on a content-identical rebase, purely
    because ``gh`` listed a sha-less job FIRST — a leg whose whole purpose is to
    avoid a second full gate, failing on job ORDER rather than content.
    """
    out, rc = _oc_job_sha("gate / PR-lane nextest timing (non-blocking)")
    assert rc == 0, (
        "oc_job_sha aborted on a sha-less name (rc=%d) — set -e killed the "
        "caller before 'else empty' (#114)" % rc)
    assert out == "", "a sha-less name yielded %r, not empty" % out

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_a_sha_carrying_job_name_still_extracts_its_sha():
    """CONTROL — the fix must not have made the extractor return empty always."""
    sha = "7378fe47aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    out, rc = _oc_job_sha("gate / PR-lane gates (%s)" % sha)
    assert rc == 0, "a sha-carrying name aborted (rc=%d)" % rc
    assert out == sha, "oc_job_sha lost the extraction: got %r" % out[:24]

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_a_sha_less_job_sorting_first_does_not_kill_the_loop():
    """THE ORDER LEG — the shape that actually failed.

    A single sha-less name does not reproduce it: the old code only died when a
    sha-less job sorted FIRST, so the loop must be driven with that order.
    """
    sha = "7378fe47aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    script = (
        'set -e; set -o pipefail; . "$1" || exit 9\n'
        'for jn in "gate / PR-lane nextest timing (non-blocking)" '
        '"gate / PR-lane gates (%s)"; do\n'
        '  js="$(oc_job_sha "$jn")"\n'
        '  [ -n "$js" ] || continue\n'
        '  printf "%%s" "$js"\n'
        'done\n' % sha)
    r = H.run(["bash", "-c", script, "_", str(OP_LIB)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (
        "the loop died when a sha-less job sorted first (rc=%d): %r"
        % (r.returncode, r.stderr[-400:]))
    assert r.stdout == sha, (
        "the loop yielded %r, not the sha — job ORDER is not content (#114)"
        % r.stdout[:24])

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_oc_patch_id_has_the_same_empty_contract():
    """``oc_patch_id`` carries the same contract, and this leg DISCRIMINATES.

    With the bug the assignment aborts (rc 1); fixed, it yields empty and rc 0.
    ``oc_same_patch``'s own refusal cannot discriminate — both paths end rc 1 —
    so the direct leg is the one that proves the abort is gone.
    """
    r = H.run(
        ["bash", "-c",
         'set -e; set -o pipefail; . "$1" || exit 9\n'
         'p="$(oc_patch_id "$2" deadbeefdeadbeefdeadbeefdeadbeefdeadbeef)"\n'
         'printf "%s|rc=%s" "$p" "$?"',
         "_", str(OP_LIB), str(H.tools_root())],
        capture_output=True, text=True, timeout=60)
    assert r.stdout == "|rc=0", (
        "oc_patch_id aborted on an unresolvable sha (%r) — same contract break "
        "as oc_job_sha (#114)" % r.stdout)

@pytest.mark.serial
@pytest.mark.xdist_group("battery-pool")
def test_oc_same_patch_still_refuses_an_unknown_sha():
    """CONTROL — unknown is never "same"."""
    head = H.run(["git", "-C", str(H.tools_root()), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=60).stdout.strip()
    r = H.run(
        ["bash", "-c",
         'set -e; set -o pipefail; . "$1" || exit 9\n'
         'if oc_same_patch "$2" deadbeefdeadbeefdeadbeefdeadbeefdeadbeef "$3"; '
         'then exit 7; fi',
         "_", str(OP_LIB), str(H.tools_root()), head],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (
        "oc_same_patch accepted an unresolvable sha as 'same', or could not "
        "reach its refusal (rc=%d)" % r.returncode)
