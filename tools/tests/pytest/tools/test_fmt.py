"""`oc-fmt` installed/repo identity.

The fleet carries ``tools/git/oc-fmt`` and also INSTALLS it. Two copies of one
formatter is a drift generator: the installed one runs, the repo one is what the
law prescribes, and a lane that edits the wrong copy sees no effect while every
check stays green.

The comparison must cover the WHOLE file, and that is the load-bearing half of
this module. A guard built on a prefix (``cmp -n``, ``head``) passes every
divergence after its window — and a TAIL-only edit is precisely the drift that
silently changes formatting behaviour while the first N bytes still match. So the
drift control appends a line and asserts the comparison NOTICES: without it the
identity leg could shrink to a subset and stay green forever.

``sh -n`` and ``--help`` are the two independent statements that the repo copy is
a real, runnable program — identity against a broken file proves the wrong thing.
"""

from __future__ import annotations

import difflib
import pathlib
import shutil
import subprocess

import pytest

import conftest as cf

REPO_COPY = cf.TOOLS_DIR / "git" / "oc-fmt"

def _identical(a, b):
    """Byte-for-byte equality of two files.

    Deliberately the WHOLE file and never a prefix: the control below exists
    because a ``cmp -n``-style guard passes every divergence past its window.
    """
    return a.read_bytes() == b.read_bytes()

def _diff_head(a, b, lines=4):
    """The first few differing lines, for a failure message worth reading."""
    left = a.read_text(errors="replace").splitlines(keepends=True)
    right = b.read_text(errors="replace").splitlines(keepends=True)
    return "".join(list(difflib.unified_diff(left, right, str(a), str(b)))[:lines])

def test_repo_copy_exists():
    """The law prescribes oc-fmt, so the repo must carry it.

    A missing repo copy would make the identity leg vacuously pass, which is the
    silent-skip class this suite exists to catch.
    """
    assert REPO_COPY.is_file(), \
        "tools/git/oc-fmt is MISSING (the law prescribes oc-fmt; the repo must "\
        "carry it)"

def test_repo_copy_parses():
    res = subprocess.run(["sh", "-n", str(REPO_COPY)],
                         capture_output=True, text=True)
    assert res.returncode == 0, \
        "tools/git/oc-fmt does not parse (sh -n):\n%s" % res.stderr[-600:]

def test_repo_copy_help_exits_zero(run_tool):
    """C-#3: an explicitly requested READ exits 0."""
    res = run_tool([str(REPO_COPY), "--help"], timeout=120)
    assert res.rc == 0, "tools/git/oc-fmt --help rc=%s\n%s" % (
        res.rc, res.combined[-400:])

def test_installed_copy_is_byte_identical(scratch):
    """The identity leg, with an honest skip when oc-fmt is not installed.

    ``skip`` rather than ``pass``: a host without the installed copy is not
    evidence that the copies agree, and a silent pass would hide a real drift on
    the host that does have it.
    """
    found = shutil.which("oc-fmt")
    if not found:
        pytest.skip("oc-fmt is not installed on this host; the repo copy is the "
                    "source of record (run.sh notes the same)")
    installed = pathlib.Path(found)
    assert _identical(REPO_COPY, installed), \
        ("the installed copy DRIFTED from the repo copy (%s):\n%s"
         % (installed, _diff_head(REPO_COPY, installed)))

def test_tail_drift_is_detected(scratch):
    """THE CONTROL: the comparison must cover the whole file.

    A tail-only edit is the drift this section exists to catch, and a
    prefix-limited guard would pass it. The fixture appends one line and asserts
    the comparison NOTICES — so the identity leg above cannot quietly degrade to
    a subset comparison.
    """
    probe = scratch.path / "oc-fmt-tail-probe"
    probe.write_bytes(REPO_COPY.read_bytes() + b"\n# drift-probe\n")
    assert not _identical(REPO_COPY, probe), \
        ("a TAIL divergence went undetected — the guard compares a subset of the "
         "file, not the whole file")
