"""The three verify tools — oc-verify-order/job/artifact.

The shell sections are thin: a ``run_selftest`` each, plus one argv leg for
``oc-verify-order``. That thinness is the reason this port ADDS a black-box exit
code table for ``oc-verify-artifact``: the tool's own selftest asserts 16 cases
about itself, and a suite grading its own homework is exactly the §51 lesson
(``oc-issue-dispatch`` counted ONE case however many asserts it made internally,
and the crash that cost a probing cycle was invisible to it).

The three ``run_selftest`` legs are NOT repeated here (factory #203):
``tools/test_tool_wrappers.py`` drives ``oc-verify-order``, ``oc-verify-job`` and
``oc-verify-artifact`` as parametrised cases already. What this module keeps is
what the blanket cannot see — the two ``oc-verify-order`` argv legs and the
artifact refusal table below.

What the table pins is the SWAP GATE's refusal vocabulary, and each code is a
different consequence:

* **rc 1** — invocation. Nothing was inspected, so nothing may be concluded.
* **rc 2** — NOT-ELF or missing. The gate refuses a non-binary outright; this is
  the code that stops a text file from replacing the live binary.
* **rc 3** — MARKER-MISSING. The artifact IS a valid ELF and is still refused,
  which is the whole point of the presence gate: a build without its markers is
  not the build that was ordered.
* **rc 4** — SHA / provenance mismatch.

The last two are the pair that matters. A gate that only distinguished
"ELF or not" would pass a marker-less build, and the fixture here is a REAL ELF
(``/bin/true`` copied) precisely so rc 3 cannot be confused with rc 2 — a
synthetic non-ELF fixture would make the marker leg pass for the wrong reason.

``--markers`` is the spelling, not ``--marker``: the singular form is not
recognised and falls through to usage (rc 1), which is itself worth knowing
because a typo there reads as "the gate refused my artifact".
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

import conftest as cf

ORDER = cf.tool_path("oc-verify-order")
ARTIFACT = cf.tool_path("oc-verify-artifact")
# ``oc-verify-job`` is covered by the selftest blanket in test_tool_wrappers.py
# (factory #203) — it had no argv leg of its own here, so nothing referenced it.

def test_verify_order_unknown_arg_is_rc1(run_tool):
    """§01: this tool's usage error is LEGACY rc 1, not the fleet's 2 — its own
    usage() comment says so, and the RC-CONTRACT keeps the row."""
    res = run_tool([str(ORDER), "--no-such-arg"], timeout=120)
    assert res.rc == 1, "oc-verify-order --no-such-arg rc=%s, want 1\n%s" % (
        res.rc, res.combined[-600:])


def test_verify_order_short_sha_is_rc1_not_a_remote_read(run_tool):
    """ARG SHAPE is gate 1: a non-40-hex argument dies rc 1 BEFORE any network
    call. Asserted as a cost property as well — the leg must not reach gh."""
    res = run_tool([str(ORDER), "notasha"], timeout=120)
    assert res.rc == 1, "oc-verify-order notasha rc=%s, want 1 (arg shape)\n%s" % (
        res.rc, res.combined[-600:])


# =============================================================================
# oc-verify-artifact — the swap gate's refusal vocabulary, black box
# =============================================================================
@pytest.fixture
def artifact_bin(tmp_path):
    """A REAL ELF: a copy of ``/bin/true``.

    Real, not synthetic, so the marker leg (rc 3) cannot be satisfied by the
    same condition as the not-ELF leg (rc 2)."""
    src = shutil.which("true") or "/bin/true"
    dst = tmp_path / "artifact-bin"
    shutil.copy2(src, dst)
    dst.chmod(0o755)
    return dst


def _artifact_rc(*argv):
    p = subprocess.run(["bash", str(ARTIFACT), *[str(a) for a in argv]],
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def test_artifact_no_args_is_rc1():
    rc, out = _artifact_rc()
    assert rc == 1, "no args rc=%s, want 1 (invocation)\n%s" % (rc, out[-600:])


def test_artifact_unknown_flag_is_rc1(artifact_bin):
    rc, out = _artifact_rc(artifact_bin, "--bogus")
    assert rc == 1, "unknown flag rc=%s, want 1\n%s" % (rc, out[-600:])


def test_artifact_missing_file_is_rc2(tmp_path):
    rc, out = _artifact_rc(tmp_path / "nope")
    assert rc == 2, "missing artifact rc=%s, want 2\n%s" % (rc, out[-600:])


def test_artifact_non_elf_is_rc2(tmp_path):
    """The gate that stops a text file replacing the live binary."""
    txt = tmp_path / "not-an-elf"
    txt.write_text("notelf\n")
    rc, out = _artifact_rc(txt)
    assert rc == 2, "non-ELF rc=%s, want 2\n%s" % (rc, out[-600:])
    assert "ELF" in out, "rc 2 without naming the ELF gate:\n%s" % out[-600:]


def test_artifact_absent_marker_is_rc3_on_a_valid_elf(artifact_bin):
    """A valid ELF refused for a missing marker — rc 3, never rc 2.

    This is the pair that matters: conflating the two would make "the artifact
    is not a binary" and "the artifact is the wrong build" the same verdict.
    """
    rc, out = _artifact_rc(artifact_bin, "--markers", "NOSUCHMARKER_ZZZ")
    assert rc == 3, (
        "absent marker on a valid ELF rc=%s, want 3 (MARKER-MISSING)\n%s"
        % (rc, out[-600:]))


def test_artifact_present_marker_passes(artifact_bin):
    """The positive control: a marker the binary really contains must PASS.

    Without this leg the rc 3 assertion above is satisfied by a gate that
    refuses every marker."""
    listing = subprocess.run(["strings", "-a", str(artifact_bin)],
                             capture_output=True, text=True, timeout=120)
    markers = [ln.strip() for ln in listing.stdout.splitlines() if ln.strip()]
    assert markers, "could not read any string out of the fixture ELF"
    rc, out = _artifact_rc(artifact_bin, "--markers", markers[0])
    assert rc == 0, (
        "a marker the ELF CONTAINS was refused (rc=%s) — the presence gate "
        "rejects everything, so the rc 3 leg proves nothing:\n%s"
        % (rc, out[-600:]))


def test_artifact_sha_mismatch_is_rc4(artifact_bin):
    rc, out = _artifact_rc(artifact_bin, "--expect-sha", "deadbeef")
    assert rc == 4, "sha mismatch rc=%s, want 4\n%s" % (rc, out[-600:])
    assert "SHA-MISMATCH" in out, "rc 4 without naming the sha gate:\n%s" % out[-600:]


def test_artifact_json_records_the_sha256_it_computed(artifact_bin):
    """The recorded-identity model: the JSON carries the sha256 of THIS artifact.

    Recomputed here with sha256sum rather than taken from the tool's own output,
    so the leg fails if the tool ever echoes a stale or inherited digest."""
    rc, out = _artifact_rc(artifact_bin, "--json")
    assert rc == 0, "clean --json rc=%s\n%s" % (rc, out[-600:])
    doc = json.loads(out[out.index("{"):])
    real = subprocess.run(["sha256sum", str(artifact_bin)],
                          capture_output=True, text=True, timeout=120
                          ).stdout.split()[0]
    assert doc.get("sha256") == real, (
        "--json sha256=%r but the artifact hashes to %r" % (doc.get("sha256"), real))

# =============================================================================
# oc-ship — the STALE-TOOLS pre-flight (factory #217)
# =============================================================================
# WHY THIS LIVES HERE. #217 was measured as an ``oc-verify-order`` failure
# ("ledger not found: …/workers-ledger.json") that is NOT an oc-verify-order
# defect: the chain runs the tools VENDORED IN ITS OWN TREE, and a tree
# branched before daf36dcb3 (#177) still resolves the workers ledger to the
# RETIRED compact view. The ORDER gate is where it SURFACES, ~25 minutes and one
# push later, with the sha already on fork main and ungated. So the regression
# has to be pinned at the gate's real seam — the chain's own pre-flight — and
# that is why a module that owns ``oc-verify-order`` also owns this leg.
#
# The fixture is a COPY of the real ``oc-ship`` plus ``lib/{oc-root.sh,oc-log.sh}``
# in a throwaway tree, with a pre-#177 ``oc_ledger_path`` APPENDED to the copied
# lib (shell function definitions are last-wins, so the append IS the old
# resolver). Nothing in this checkout is touched, and the fresh-tree leg runs the
# same copy without the append — the pair differs ONLY in the resolver, so a
# failure cannot be blamed on the fixture scaffolding.
#
# The two legs are a matched pair on purpose. The refusal leg alone would pass
# for a guard that refuses EVERY tree (the §51 lesson: a gate that always says no
# proves nothing), so the negative leg pins that a #177+ resolver stays silent.
# Neither leg asserts on rc: a fixture tree has no fork checkout, so both exit
# 3 there, and the DISTINGUISHING evidence is the STALE-TOOLS line itself.

SHA40 = "a" * 40

def _stale_tools_tree(tmp_path, stale: bool):
    """A throwaway tools tree whose ``oc-ship`` resolves the ledger like ``stale``.

    Returns the path to the copied ``oc-ship``."""
    tree = tmp_path / ("stale" if stale else "fresh")
    (tree / "lib").mkdir(parents=True)
    ship = tree / "oc-ship"
    shutil.copy2(cf.tool_path("oc-ship"), ship)
    for lib in ("oc-root.sh", "oc-log.sh"):
        shutil.copy2(cf.TOOLS_DIR / "lib" / lib, tree / "lib" / lib)
    if stale:
        # Verbatim from `git show daf36dcb3^:tools/lib/oc-log.sh`, i.e. what a
        # pre-#177 tree really carries. Appended, not substituted, so the copy
        # stays a faithful superset of the tree it models.
        with (tree / "lib" / "oc-log.sh").open("a") as fh:
            fh.write(
                "\noc_ledger_path() {\n"
                "  printf '%s\\n' \"${OC_LEDGER:-${OC_DEV_STATE:-"
                "$HOME/.opencrabs/profiles/ops/opencrabs-dev}"
                "/workers-ledger.json}\"\n"
                "}\n")
    ship.chmod(0o755)
    return ship

def _run_ship_preflight(run_tool, ship, state, **extra):
    """Run ``oc-ship`` far enough to reach the pre-flight guard and no further.

    ``OC_SHIPCHAIN_DETACHED=1`` is REQUIRED, not cosmetic: without it the chain
    re-execs itself under ``systemd-run`` and the guard's stderr never reaches
    this process — the leg would then assert on an empty string and pass or fail
    for reasons unrelated to the guard.
    ``OC_FORK_REPO`` is a path that is not a git checkout, so the run stops at
    ``require_fork_checkout`` (rc 3) immediately after the guard.
    """
    env = {
        "OC_SHIPCHAIN_DETACHED": "1",
        "OC_DEV_STATE": str(state),
        "OC_DEPLOY_STATE_DIR": str(state),
        # Empty == "not pinned": the guard treats a non-empty OC_LEDGER as the
        # caller having chosen the gate's ledger path, which disables the
        # refusal. Ambient OC_LEDGER from the lane must not leak into this leg.
        "OC_LEDGER": "",
        "OC_FORK_REPO": str(state / "no-fork-here"),
        "OC_SHIPCHAIN_FREEZE_OVERRIDE": "1",
    }
    env.update(extra)
    return run_tool(
        ["bash", str(ship), "--sha", SHA40, "--branch", "feat", "--dry-run"],
        timeout=120, env=env)

def test_oc_ship_refuses_a_stale_ledger_resolver(run_tool, tmp_path):
    """#217: a pre-#177 tree is refused BEFORE dispatch, naming the defect.

    The state dir holds ONLY ``events.jsonl`` — which is what #177 leaves behind,
    since it retired the compact view's write path. That is the measured fatal
    shape: the old resolver names ``workers-ledger.json``, the file is absent, and
    ``oc-verify-order`` dies "ledger not found" after the push."""
    state = tmp_path / "state"
    state.mkdir()
    (state / "events.jsonl").touch()
    ship = _stale_tools_tree(tmp_path, stale=True)

    res = _run_ship_preflight(run_tool, ship, state)

    assert res.rc == 3, (
        "a pre-#177 tree was not refused at the pre-flight (rc=%s, want 3). "
        "#217's whole cost is that this is discovered AFTER the push.\n%s"
        % (res.rc, res.combined[-1500:]))
    assert "STALE-TOOLS" in res.combined, (
        "rc 3 without the STALE-TOOLS verdict — the lane cannot tell this from "
        "any other pre-flight refusal:\n%s" % res.combined[-1500:])
    assert "daf36dcb3" in res.combined, (
        "the refusal must name the commit that migrated the resolver, or the "
        "lane has no idea what to merge:\n%s" % res.combined[-1500:])
    assert str(state / "workers-ledger.json") in res.combined, (
        "the refusal must name the path it resolved, so the reader can see it is "
        "the retired view and not the record:\n%s" % res.combined[-1500:])

def test_oc_ship_is_silent_on_a_current_ledger_resolver(run_tool, tmp_path):
    """The negative control: a #177+ tree must NOT be refused or warned.

    Same fixture, same state dir, same argv — the only difference is the absent
    ``oc_ledger_path`` override. Without this leg the assertion above is
    satisfied by a guard that refuses every tree, which would block the fleet."""
    state = tmp_path / "state"
    state.mkdir()
    (state / "events.jsonl").touch()
    ship = _stale_tools_tree(tmp_path, stale=False)

    res = _run_ship_preflight(run_tool, ship, state)

    assert "STALE-TOOLS" not in res.combined, (
        "a tree with the CURRENT resolver was flagged STALE-TOOLS:\n%s"
        % res.combined[-1500:])
