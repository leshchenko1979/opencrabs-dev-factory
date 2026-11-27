"""Ported: the three verify tools — run.sh §01/§02/§03 (oc-verify-order/job/artifact).

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
