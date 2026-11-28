"""Receipt PROVENANCE: a scoped run must not stamp the version-bump gate (#214).

THE DEFECT
    ``tools/tests/battery-last.json`` is git-tracked because ``oc-ledger sync``
    hard-reads that exact path. That made EVERY pytest invocation the gate's
    writer: a one-file run stamped ``{"pass": 9, "fail": 0, "verdict": "PASS"}``
    and every predicate ``sync`` checks passed on nine tests. Measured in the
    issue, immediately after the repoint.

THE FIX (option 1, refuse)
    The controller knows its own selection at ``pytest_configure`` — before a
    single test runs, on the one process that writes the receipt. If that
    selection is not the gate's own, the run writes its receipt to a scratch path
    and says so on one line; ``sync`` then keeps reading the last FULL verdict,
    which is the honest answer. No consumer change, and it fails closed.

WHAT THIS MODULE PINS, AND WHY BOTH DIRECTIONS MATTER
    * ``test_scoped_selection_does_not_stamp_the_canonical_receipt`` — the
      refusal. Fails if the guard is removed (under-refusal: the #214 bug).
    * ``test_gate_invocation_still_stamps_the_canonical_receipt`` — the gate.
      Fails if the guard over-refuses. Refusing the REAL gate would break the
      fleet's ship path, which is strictly worse than the bug: no bump could
      ever be backed by a fresh verdict again.
    * ``test_the_selection_boundary`` — the table itself, so a later "simplify"
      cannot quietly move the line between "gate" and "scoped".

WHY A SANDBOX AND NOT THE REAL TREE
    These legs must observe a WRITE (or its absence) at a canonical path. Doing
    that in the real checkout would stamp the fleet's gate receipt with a
    two-test verdict — i.e. commit the very defect being fixed. So each leg
    builds a throwaway repo skeleton (real ``conftest.py``, real ``lib/``, real
    ``pytest.ini``, two trivial tests) and asserts on ITS canonical path.
    The code under test is a byte copy of the shipped files, so the legs still
    drive the real implementation.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import conftest as cf
from lib import receipt as R

# ---------------------------------------------------------------------------
# sandbox: a throwaway repo skeleton with the REAL harness in it
# ---------------------------------------------------------------------------
def _sandbox(root: Path) -> Path:
    """Build ``<root>/tools/tests/pytest`` carrying the real conftest + lib + ini.

    The layout is load-bearing twice over: ``conftest.REPO_ROOT`` is
    ``parents[2]`` of the pytest dir and ``receipt.REPO_ROOT`` is ``parents[4]``
    of ``lib/receipt.py``, so this tree makes ``DEFAULT_RECEIPT`` resolve to
    ``<root>/tools/tests/battery-last.json`` — the sandbox's own gate path.
    """
    pytest_dir = root / "tools" / "tests" / "pytest"
    pytest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cf.PYTEST_DIR / "conftest.py", pytest_dir / "conftest.py")
    shutil.copy2(cf.PYTEST_DIR / "pytest.ini", pytest_dir / "pytest.ini")
    lib_dst = pytest_dir / "lib"
    lib_dst.mkdir(exist_ok=True)
    for src in (cf.PYTEST_DIR / "lib").glob("*.py"):
        shutil.copy2(src, lib_dst / src.name)
    # Two modules, and one ``slow`` leg, so every scoped shape below still
    # COLLECTS something and exits 0. Otherwise ``-m slow`` or
    # ``--ignore test_tiny.py`` would exit 5 ("no tests ran") and the leg would
    # pass or fail on pytest's empty-selection code rather than on the refusal.
    (pytest_dir / "test_tiny.py").write_text(
        "import pytest\n\n"
        "def test_tiny_one():\n    assert True\n\n"
        "def test_tiny_two():\n    assert True\n\n"
        "@pytest.mark.slow\n"
        "def test_tiny_slow():\n    assert True\n",
        encoding="utf-8")
    (pytest_dir / "test_other.py").write_text(
        "def test_other_one():\n    assert True\n", encoding="utf-8")
    return pytest_dir

def _run(pytest_dir: Path, *args: str, env_extra: dict | None = None):
    """Run pytest in the sandbox. No ``OC_PYTEST_RECEIPT`` unless a leg sets one."""
    env = {k: v for k, v in os.environ.items() if k != "OC_PYTEST_RECEIPT"}
    # The cgroup hook re-execs into a systemd scope, which would move the run's
    # argv/cwd and add nothing to what these legs observe.
    env["OC_PYTEST_NO_CGROUP"] = "1"
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([sys.executable, "-m", "pytest", *args],
                       capture_output=True, text=True, timeout=300,
                       cwd=str(pytest_dir), env=env)
    return SimpleNamespace(rc=r.returncode, out=r.stdout, err=r.stderr,
                           combined=r.stdout + r.stderr)

def _canonical(pytest_dir: Path) -> Path:
    return pytest_dir.parent / "battery-last.json"

# ---------------------------------------------------------------------------
# (a) a scoped selection must NOT stamp the canonical receipt
# ---------------------------------------------------------------------------
def test_scoped_selection_does_not_stamp_the_canonical_receipt(tmp_path):
    """The #214 repro, verbatim: one file, no override, canonical path untouched.

    Before the fix this leg reddens exactly as the issue reports — the tracked
    receipt goes from a full-battery verdict to ``pass: 9`` (here: ``pass: 2``)
    with ``verdict: PASS``, and ``oc-ledger sync`` accepts it.
    """
    pytest_dir = _sandbox(tmp_path)
    canonical = _canonical(pytest_dir)
    assert not canonical.exists(), "sandbox started with a receipt already there"

    res = _run(pytest_dir, "test_tiny.py", "-q", "-n", "0")
    assert res.rc == 0, res.combined[-2000:]

    assert not canonical.exists(), (
        "a one-file run stamped the version-bump gate — this is #214: "
        "`oc-ledger sync` reads this file and would pass the bump on a partial "
        "verdict")
    assert "REFUSED the canonical gate receipt" in res.combined, (
        "the scoped run neither wrote the gate receipt nor said it refused it — "
        "silence is indistinguishable from a successful stamp:\n%s"
        % res.combined[-2000:])

def test_the_refusal_names_where_it_wrote_and_why(tmp_path):
    """The notice is the contract with the reader: what, why, and where instead."""
    pytest_dir = _sandbox(tmp_path)
    res = _run(pytest_dir, "test_tiny.py", "-q", "-n", "0")
    assert res.rc == 0, res.combined[-2000:]

    line = [l for l in res.combined.splitlines() if "REFUSED" in l]
    assert len(line) == 1, (
        "expected exactly one refusal line, got %d:\n%s" % (len(line), res.combined[-2000:]))
    notice = line[0]
    assert str(_canonical(pytest_dir)) in notice, (
        "the notice does not name the gate path it protected: %r" % notice)
    assert "path selection" in notice or "-k" in notice or "-m" in notice, (
        "the notice does not say WHY the selection was scoped: %r" % notice)

    # ...and the receipt really did land where the notice says, still readable.
    # Parsed from the notice rather than globbed out of /tmp: every leg of this
    # module runs its own sandbox, and under -n 2 a glob would read a SIBLING's
    # scratch receipt as if it were this run's.
    m = re.search(r"Wrote (\S+) instead", notice)
    assert m, "the notice does not say where the receipt went: %r" % notice
    written = Path(m.group(1))
    assert written.is_file(), (
        "the notice named %s, which does not exist" % written)
    assert written.resolve() != _canonical(pytest_dir).resolve()
    data = json.loads(written.read_text())
    assert data["verdict"] == "PASS", "the scratch receipt is not a usable verdict"
    assert data["pass"] == 2, "the scratch receipt does not describe this run"
    assert data["path"] != str(_canonical(pytest_dir)), (
        "the scratch receipt claims to be the gate receipt")

@pytest.mark.parametrize("args,needle", [
    (("test_tiny.py",), "path selection"),
    (("test_tiny.py::test_tiny_one",), "path selection"),
    (("-k", "tiny_one"), "-k"),
    (("-m", "slow"), "-m"),
    (("-m", "not slow and not e2e"), "-m"),
    (("--deselect", "test_tiny.py::test_tiny_one"), "--deselect"),
    (("--ignore", "test_tiny.py"), "--ignore"),
    (("--lf",), "--lf"),
])
def test_every_scoped_shape_is_refused(tmp_path, args, needle):
    """One leg per way pytest lets a caller narrow a run.

    Each was READ from a real pytest 9 config, not assumed: ``--deselect`` lands
    in ``option.deselect``, ``--ignore`` in ``option.ignore``, ``--lf`` in
    ``option.lf``, and a nodeid in ``option.file_or_dir`` beside the file case.
    """
    pytest_dir = _sandbox(tmp_path)
    canonical = _canonical(pytest_dir)
    res = _run(pytest_dir, *args, "-q", "-n", "0")
    assert res.rc == 0, res.combined[-2000:]
    assert not canonical.exists(), (
        "%s stamped the gate receipt" % (args,))
    assert "REFUSED the canonical gate receipt" in res.combined
    assert needle in res.combined, (
        "the refusal for %s does not name %r:\n%s"
        % (args, needle, res.combined[-1500:]))

def test_an_explicit_override_aimed_at_the_gate_is_also_refused(tmp_path):
    """Pointing ``OC_PYTEST_RECEIPT`` AT the canonical path is not a loophole.

    The refusal keys off the PATH a scoped run would land on, not off how that
    path was chosen. Otherwise one env var would restore the whole #214 hazard.
    """
    pytest_dir = _sandbox(tmp_path)
    canonical = _canonical(pytest_dir)
    res = _run(pytest_dir, "test_tiny.py", "-q", "-n", "0",
               env_extra={"OC_PYTEST_RECEIPT": str(canonical)})
    assert res.rc == 0, res.combined[-2000:]
    assert not canonical.exists(), (
        "an explicit OC_PYTEST_RECEIPT aimed at the gate defeated the refusal")
    assert "REFUSED" in res.combined

def test_an_override_elsewhere_is_honoured(tmp_path):
    """Every scoped leg in this suite overrides the path — that must keep working."""
    pytest_dir = _sandbox(tmp_path)
    out = tmp_path / "scratch" / "receipt.json"
    res = _run(pytest_dir, "test_tiny.py", "-q", "-n", "0",
               env_extra={"OC_PYTEST_RECEIPT": str(out)})
    assert res.rc == 0, res.combined[-2000:]
    assert out.is_file(), "a scoped run with an explicit scratch override wrote nothing"
    # Two legs from test_tiny.py; its third is ``slow`` and addopts deselects it.
    assert json.loads(out.read_text())["pass"] == 2
    assert "REFUSED" not in res.combined, (
        "a run already writing to a scratch path was refused again — the notice "
        "would then be noise on every nested leg")

# ---------------------------------------------------------------------------
# (b) the gate invocation must STILL stamp the canonical receipt
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("args", [
    (),                              # bare: testpaths + addopts = THE GATE
    (".",),                          # the same tree, named explicitly
    ("-m", "not slow"),              # the gate's own marker expression, stated
])
def test_gate_invocation_still_stamps_the_canonical_receipt(tmp_path, args):
    """The gate's own selection is FULL — refusing it would break every bump.

    ``-m "not slow"`` is legal BY DESIGN: it is the gate (``addopts``), and the
    slow legs are "on request", so a run carrying it executes every test a
    version bump may rely on. A guard that refused this expression would leave
    ``oc-ledger sync`` reading a stale verdict forever — a worse failure than
    #214, because no bump could ever be backed by a fresh run.
    """
    pytest_dir = _sandbox(tmp_path)
    canonical = _canonical(pytest_dir)

    res = _run(pytest_dir, *args, "-q", "-n", "0")
    assert res.rc == 0, res.combined[-2000:]
    assert "REFUSED" not in res.combined, (
        "the GATE selection %s was refused — the ship path is now broken:\n%s"
        % (args or ("<bare>",), res.combined[-2000:]))
    assert canonical.is_file(), (
        "the gate invocation %s wrote no canonical receipt, so oc-ledger sync "
        "reads a stale verdict" % (args or ("<bare>",)))
    data = json.loads(canonical.read_text())
    assert data["verdict"] == "PASS"
    assert data["fail"] == 0
    assert data["path"] == str(canonical), (
        "the receipt records a different path than the one it landed on")

def test_the_gate_writes_the_canonical_path_under_xdist(tmp_path):
    """``-n 2`` is the real invocation, and the controller is the only writer.

    Not redundant with the leg above: under xdist the controller is a different
    process from every test, and that is precisely the arming bug of 2026-11-28
    (``pytest_collection_modifyitems`` runs only in workers). A refusal decided
    anywhere but the controller would be invisible here.
    """
    pytest_dir = _sandbox(tmp_path)
    canonical = _canonical(pytest_dir)

    res = _run(pytest_dir, "-q", "-n", "2")
    assert res.rc == 0, res.combined[-2000:]
    assert "REFUSED" not in res.combined, res.combined[-2000:]
    assert canonical.is_file(), "a -n 2 gate run wrote no canonical receipt"
    data = json.loads(canonical.read_text())
    assert data["verdict"] == "PASS"
    assert data["pass"] == 3, (
        "the gate run executed %d legs — the sandbox holds three non-slow ones "
        "(test_tiny x2, test_other x1)" % data["pass"])
    assert data["mode"] == "pytest parallel jobs=2"

# ---------------------------------------------------------------------------
# the boundary itself — the table a later editor must not move by accident
# ---------------------------------------------------------------------------
_UNSET = object()

def _cfg(*, file_or_dir=(), keyword="", markexpr=_UNSET, deselect=None,
         ignore=None, ignore_glob=None, lf=False, newfirst=False,
         failedfirst=False, stepwise=False, pyargs=False, ini=None, base=None):
    """A config shaped like the one ``pytest_configure`` receives.

    Field names are the ones pytest 9 actually sets on ``config.option`` and
    ``config.invocation_params`` — verified against a live config, not guessed.

    ``markexpr`` defaults to the gate's own expression rather than ``""``: at
    ``pytest_configure`` a real config has ALREADY merged ``addopts``, so it
    never carries an empty ``-m`` unless the caller passed ``-m ""`` explicitly.
    Defaulting to ``""`` here would model a config pytest cannot produce.
    """
    if markexpr is _UNSET:
        markexpr = R.gate_markexpr()
    opt = SimpleNamespace(
        file_or_dir=list(file_or_dir), keyword=keyword, markexpr=markexpr,
        deselect=deselect, ignore=ignore, ignore_glob=ignore_glob, lf=lf,
        newfirst=newfirst, failedfirst=failedfirst, stepwise=stepwise,
        pyargs=pyargs)
    return SimpleNamespace(
        option=opt,
        inipath=Path(ini) if ini is not None else cf.PYTEST_DIR / "pytest.ini",
        invocation_params=SimpleNamespace(dir=Path(base or cf.PYTEST_DIR)))

def test_the_selection_boundary():
    """FULL = the whole tree, nothing selected away. Scoped = anything narrower."""
    full = [
        {},                                              # bare: testpaths decides
        {"file_or_dir": ["."]},                          # inside the battery
        {"file_or_dir": [str(cf.PYTEST_DIR)]},           # absolute, the tree itself
        {"markexpr": "not slow"},                        # THE GATE's own -m
        {"markexpr": "  not   slow  "},                  # same expression, spacing
        {"file_or_dir": [".", "."]},                     # repeated, still the tree
    ]
    for kw in full:
        assert R.selection_problem(_cfg(**kw)) == "", (
            "FULL selection %r was judged scoped: %r"
            % (kw, R.selection_problem(_cfg(**kw))))

    scoped = [
        {"file_or_dir": ["harness/test_receipt.py"]},
        {"file_or_dir": ["harness/test_receipt.py::test_receipt_has_eighteen_fields"]},
        {"file_or_dir": ["harness/"]},                   # a subject folder
        {"file_or_dir": ["tools/"]},
        {"file_or_dir": [".", "harness/test_receipt.py"]},
        {"keyword": "ledger"},
        {"markexpr": "slow"},
        {"markexpr": "serial"},
        {"markexpr": "not slow and not e2e"},
        {"markexpr": "not slow or serial"},
        {"deselect": ["harness/test_receipt.py::test_x"]},
        {"ignore": ["harness"]},
        {"ignore_glob": ["*e2e*"]},
        {"lf": True},
        {"newfirst": True},
        {"failedfirst": True},
        {"stepwise": True},
        {"pyargs": True},
        {"ini": "/tmp/somewhere-else/pytest.ini"},        # testpaths is not ours
    ]
    for kw in scoped:
        assert R.selection_problem(_cfg(**kw)) != "", (
            "SCOPED selection %r was accepted as the gate — it would stamp a "
            "PASS backed by a subset" % (kw,))

def test_the_gate_marker_expression_is_read_from_the_ini_not_duplicated():
    """The boundary tracks ``pytest.ini``, so editing the gate moves the boundary.

    A second copy of ``"not slow"`` in ``receipt.py`` would go stale the moment
    someone changed the gate's ``-m`` — and a stale copy either refuses the real
    gate (no bump can ever be backed) or accepts a narrower expression as full.
    """
    import shlex

    text = (cf.PYTEST_DIR / "pytest.ini").read_text(encoding="utf-8")
    m = re.search(r"^addopts\s*=\s*(.+)$", text, re.MULTILINE)
    assert m, "pytest.ini has no addopts — the gate lost its defaults"
    argv = shlex.split(m.group(1))
    assert "-m" in argv, "the gate no longer carries -m"
    in_ini = argv[argv.index("-m") + 1]

    assert R.gate_markexpr() == in_ini, (
        "receipt.gate_markexpr() is %r but the gate's addopts says %r — the "
        "refusal boundary has drifted from the gate's own definition"
        % (R.gate_markexpr(), in_ini))
    # And the boundary accepts exactly it.
    assert R.selection_problem(_cfg(markexpr=in_ini)) == ""

def test_concurrency_and_reporting_are_not_selection():
    """``-n``/``-q``/``-x`` must not be mistaken for narrowing.

    ``-x`` can only stop a run that has ALREADY failed, and a stopped run's
    verdict is FAIL — never a green backed by a subset. Treating these as scoped
    would refuse the fleet's own ship path.
    """
    for kw in ({"markexpr": "not slow"}, {"file_or_dir": ["."]}):
        assert R.selection_problem(_cfg(**kw)) == ""
    # The same run with a fail-fast flag is still the same SELECTION.
    assert R.selection_problem(_cfg(file_or_dir=["."])) == ""
    assert R.selection_problem(_cfg(markexpr="not slow")) == ""
