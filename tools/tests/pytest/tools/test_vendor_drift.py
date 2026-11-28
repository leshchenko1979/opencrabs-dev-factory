"""Ported: ``oc-vendor-drift`` — run.sh §83 (census ordinal §64).

WHY THIS MODULE IS MAPPED TO §64
    run.sh has no ``section "..."`` call for the vendor-drift block: it opens on
    a bare ``# ---- 83.`` header, and the census bounds a section's body by the
    NEXT ``section`` call. So the block's nine ok/bad sites fall inside §64's
    body and are charged to §64 — which is exactly why §64 read "28 shell sites,
    19 pytest assertions" and looked like a quoting-guard deficit. Nine of those
    twenty-eight were never about quoting at all.

    Rather than re-define the count (which would have to re-bound every section
    and would re-break §67 — see the census docstring), the sites are paid back
    with REAL coverage: this module ports them, and the mapping says so.

THE CONTRACT (issue #700)
    A vendored copy is compared against its recorded upstream revision with a
    DECLARED delta allowed. The verdict vocabulary is the claim:

      * ``IN_SYNC``              bytes equal at the ref, after the declared delta
      * ``DRIFTED``              the copy was edited outside that delta
      * ``LOCAL_MISSING``        the vendored path does not exist
      * ``UPSTREAM_UNREACHABLE`` repo/ref/path unreadable — **never green**

    Every leg below drives the shipped tool against a THROWAWAY upstream git repo
    built in the test, so nothing here depends on the live meta-factory checkout
    the shell leg reads (``/root/agent-factories``) — the port is deterministic
    where the shell was conditional.

WHY THE DRIFT LEG IS NOT DECORATION
    "IN_SYNC on a declared delta" passes trivially for a guard that compares
    nothing. ``test_a_byte_outside_the_delta_is_drifted`` is the control that
    makes it mean something: one edited byte, same fixture, must flip the verdict.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

import conftest as cf

TOOL = cf.TOOLS_DIR / "audit" / "oc-vendor-drift"

BODY = (
    "#!/usr/bin/env python3\n"
    'PROG = "upstream-name"\n'
    "def main():\n"
    "    return 0\n"
)
VENDORED = BODY.replace("upstream-name", "oc-questions")

# The pass count the tool's own selftest reports.
# A FLOOR, never an exact total: an exact number reddens on every legitimate new
# leg, and the tempting repair is to lower it — which is how a leg gets deleted
# (a hardcoded "8 passed" reddened the moment #44 took the total to 13).
SELFTEST_FLOOR = 13


@pytest.fixture
def vd(tmp_path, run_tool):
    """A throwaway upstream repo + vendored tree + manifest, plus ``check()``."""
    up = tmp_path / "upstream"
    (up / "T").mkdir(parents=True)
    for cmd in (["init", "-q"], ["config", "user.email", "t@t"],
                ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(up), *cmd], check=True,
                       capture_output=True)
    (up / "T" / "thing").write_text(BODY)
    subprocess.run(["git", "-C", str(up), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(up), "commit", "-qm", "one"], check=True,
                   capture_output=True)
    ref = subprocess.run(["git", "-C", str(up), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()

    local = tmp_path / "local"
    (local / "tools" / "state").mkdir(parents=True)
    loc = local / "tools" / "state" / "thing"
    loc.write_text(VENDORED)

    manifest = {"upstream_repo": str(up), "vendor": [{
        "local": "tools/state/thing", "upstream_path": "T/thing", "ref": ref,
        "delta": [{"match": '^PROG = "oc-questions"$',
                   "match_upstream": '^PROG = "upstream-name"$',
                   "why": "deployment name"},
                  {"match": '^RENDER = "x-render\\.mjs"$',
                   "why": "sibling name"}]}]}
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest))

    def _check(*extra, repo=None, timeout=180):
        return run_tool([str(TOOL), "--manifest", str(mpath),
                         "--repo", str(repo or up), "--root", str(local),
                         *extra], timeout=timeout)

    class VD:
        pass

    v = VD()
    v.check = _check
    v.upstream = up
    v.local = local
    v.vendored = loc
    v.manifest = mpath
    v.ref = ref
    v.dir = tmp_path
    return v


def test_tool_is_present_and_executable():
    """§83 leg: the guard lives where the fleet expects it, and can be run.

    The shell's site here is the ``else`` arm — ``bad "oc-vendor-drift missing"``.
    Asserted as the POSITIVE claim, because "the tool is absent" is only ever
    true of a broken tree; what a battery must not do is silently skip the block.
    """
    assert TOOL.is_file(), "oc-vendor-drift is missing at %s" % TOOL
    assert os.access(TOOL, os.X_OK), (
        "%s exists but is not executable — every §83 leg above would be skipped "
        "by the shell's ``[ -x ]`` guard while the section still read green" % TOOL)


def test_declared_delta_only_is_in_sync(vd):
    """§83 leg: a copy differing ONLY by the declared delta is IN_SYNC rc=0."""
    res = vd.check()
    assert res.rc == 0, (
        "a vendored copy that differs only inside the declared delta read rc=%d "
        "— the manifest's whole purpose is to make that a pass\n%s"
        % (res.rc, res.combined[-1500:]))
    assert "IN_SYNC" in res.out, "no IN_SYNC verdict:\n%s" % res.combined[-1500:]


def test_a_byte_outside_the_delta_is_drifted(vd):
    """§83 leg (NEGATIVE CONTROL): one edited byte flips the same fixture to red.

    Without this, ``test_declared_delta_only_is_in_sync`` would pass for a guard
    that never compares anything.
    """
    vd.vendored.write_text(VENDORED.replace("return 0", "return 1"))
    res = vd.check()
    assert res.rc == 1, (
        "one byte edited OUTSIDE the declared delta read rc=%d, contract says 1\n%s"
        % (res.rc, res.combined[-1500:]))
    assert "DRIFTED" in res.out, (
        "the verdict is not DRIFTED — a real edit was reported as something "
        "else:\n%s" % res.combined[-1500:])


def test_missing_vendored_copy_is_reported_not_assumed_clean(vd):
    """§83 leg: an absent vendored file is LOCAL_MISSING rc=1, never a pass."""
    vd.vendored.unlink()
    res = vd.check()
    assert res.rc == 1, (
        "an ABSENT vendored copy read rc=%d, contract says 1\n%s"
        % (res.rc, res.combined[-1500:]))
    assert "LOCAL_MISSING" in res.out, (
        "an absent copy was not named LOCAL_MISSING:\n%s" % res.combined[-1500:])


def test_unreachable_upstream_is_rc_3_and_never_green(vd):
    """§83 legs: an unreadable upstream is rc 3 + UPSTREAM_UNREACHABLE.

    This is the arm the shell drives conditionally (``if [ -d
    /root/agent-factories/.git ]``); here it is driven directly by pointing
    ``--repo`` at a directory that is not a git repo, so the disclosed-skip
    contract is asserted on every run instead of only where the meta factory
    happens to be checked out.
    """
    res = vd.check(repo=vd.dir / "no-such-repo")
    assert res.rc == 3, (
        "an unreachable upstream read rc=%d, contract says 3 — a green here is "
        "the lie the guard exists to prevent\n%s" % (res.rc, res.combined[-1500:]))
    assert "UPSTREAM_UNREACHABLE" in res.out, (
        "rc 3 without an UPSTREAM_UNREACHABLE verdict — the caller cannot tell "
        "this from a crash:\n%s" % res.combined[-1500:])


def test_unresolvable_recorded_ref_is_rc_3(vd):
    """§83 leg (NEGATIVE CONTROL): a bogus recorded ref must never read green."""
    man = json.loads(vd.manifest.read_text())
    man["vendor"][0]["ref"] = "0" * 40
    vd.manifest.write_text(json.dumps(man))
    res = vd.check()
    assert res.rc == 3, (
        "an unresolvable recorded ref read rc=%d, contract says 3\n%s"
        % (res.rc, res.combined[-1500:]))
    assert "UPSTREAM_UNREACHABLE" in res.out, res.combined[-1500:]


def test_selftest_passes_with_a_floor(vd):
    """§83 legs: the tool's own selftest is green, 0 failed, at or above a FLOOR.

    A floor rather than an exact total, for the reason stated on
    ``SELFTEST_FLOOR``. ``0 failed`` is the half that actually discriminates: a
    selftest that stopped asserting would still print a passing total of 0.
    """
    res = vd.check("--selftest", timeout=300)
    assert res.rc == 0, "oc-vendor-drift --selftest rc=%d\n%s" % (res.rc, res.combined[-1500:])
    m = None
    for line in res.out.splitlines():
        if line.startswith("selftest:"):
            m = line
    assert m, "the selftest printed no 'selftest: N passed, M failed' line:\n%s" % res.combined[-1500:]
    n_pass = int(m.split()[1])
    assert "0 failed" in m, "the selftest reports a FAILURE: %r" % m
    assert n_pass >= SELFTEST_FLOOR, (
        "the selftest is down to %d legs (floor %d) — legs were deleted, and the "
        "'0 failed' above is then vacuous" % (n_pass, SELFTEST_FLOOR))
