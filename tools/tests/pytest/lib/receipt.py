"""The battery receipt — the SAME 18 fields the shell harness wrote.

**The canonical path is ``tools/tests/battery-last.json``, and it is deliberate.**
That file is the fleet's version-bump gate: ``oc-ledger sync`` reads it, refuses
with rc 5 unless ``verdict == "PASS"``, ``fail == 0`` and the stamp is under six
hours old, and names it in its own die message. Every law file that says "battery
green" (``hq.md``, ``toolsmith.md``, ``triage.md``, ``README.md``) means this file.
So the receipt path is a CONTRACT with consumers that do not know pytest exists,
and it does not move when the writer changes. A run that wrote anywhere else
would leave the bump gate reading a stale verdict forever, and reading green
while the suite is red is the
one failure mode this file exists to prevent.

Three rules this module enforces:

* **Full-selection only (#214).** pytest is designed to be run SCOPED, so once
  the canonical path became a tracked file, ANY invocation became the gate's
  writer: a one-file run stamped ``{"pass": 9, "fail": 0, "verdict": "PASS"}``
  and every predicate ``oc-ledger sync`` checks passed on 9 tests. So a run whose
  selection is not the full gate REFUSES the canonical path: it writes its
  receipt to a scratch path and says so. ``sync`` then keeps reading the last
  full verdict — the honest answer — and no consumer changes. See
  ``selection_problem()`` for the boundary and why ``-m "not slow"`` is FULL.
* **Controller-only.** No xdist worker may write the canonical path. Guarded with
  ``if not hasattr(config, "workerinput")`` — that attribute is set by xdist on
  worker processes only, so it is the cheapest and most reliable test for
  "am I the controller".
* **Fail rows are per-worker files, concatenated by the controller.** The shell
  harness's single ``$FAIL_LOG`` was truncated by whoever started a run and
  removed on green; with N workers, one green worker removing the shared file
  would erase a sibling's evidence (the #517/#614 class, one layer out). A worker
  appends only to its OWN file; the controller concatenates them into
  ``fail_rows``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

# The 18 fields, in emit_summary's order. Asserted by test_receipt_parity.
FIELDS = (
    "path",
    "ts",
    "pass",
    "fail",
    "verdict",
    "mode",
    "pids_max",
    "pids_cap",
    "fail_log",
    "fail_rows",
    "fail_rows_truncated",
    "tree_changed",
    "cgroup",
    "cgroup_isolated",
    "nice",
    "ioprio",
    "wall_ms",
    "timing",
)

FAIL_ROWS_CAP = int(os.environ.get("OC_BATTERY_FAIL_ROWS_CAP", "200"))
SLOWEST_N = 10          # ten rows is the whole receipt needs to show a trend

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS_DIR = REPO_ROOT / "tools"
DEFAULT_RECEIPT = TOOLS_DIR / "tests" / "battery-last.json"

# The battery's own directory and ini — the tree the gate means by "everything".
PYTEST_DIR = Path(__file__).resolve().parents[1]
PYTEST_INI = PYTEST_DIR / "pytest.ini"

def _norm_expr(expr) -> str:
    """Whitespace-normalised ``-m`` expression (``"not  slow "`` -> ``"not slow"``)."""
    return " ".join(str(expr or "").split())

# The gate's own -m expression. Read from ``pytest.ini``'s ``addopts`` — the
# file that DEFINES the gate — rather than kept here as a second copy that
# drifts the moment someone edits the gate. ``slow`` means "on request" (minutes
# per leg), so DESELECTING the slow legs is the gate, not a narrowing of it: a
# run carrying exactly this expression executes every test a version bump may
# rely on. Anything else — ``-m slow``, ``-m serial``, ``-m "not slow and not
# e2e"`` — is a subset. The literal is the fallback for an unreadable ini.
GATE_MARKEXPR_FALLBACK = "not slow"

def gate_markexpr() -> str:
    """The ``-m`` value ``addopts`` supplies, whitespace-normalised.

    ``shlex``, not ``str.split()``: ``-m "not slow"`` is ONE argument and a
    plain split yields ``"not`` + ``slow"``, which reads as no ``-m`` at all —
    the same trap ``test_gate_defaults.addopts()`` documents.
    """
    import shlex

    try:
        text = PYTEST_INI.read_text(encoding="utf-8")
    except OSError:
        return GATE_MARKEXPR_FALLBACK
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("addopts"):
            continue
        try:
            argv = shlex.split(stripped.split("=", 1)[1])
        except (IndexError, ValueError):
            return GATE_MARKEXPR_FALLBACK
        # ``-m`` is the only flag that sets ``option.markexpr``; ``--markers``
        # LISTS markers and sets nothing, so matching it would be a false read.
        if "-m" in argv:
            i = argv.index("-m")
            return _norm_expr(argv[i + 1]) if i + 1 < len(argv) else GATE_MARKEXPR_FALLBACK
        return ""            # addopts carries no -m: the gate is the whole tree
    return GATE_MARKEXPR_FALLBACK

# =============================================================================
# environment probes (one per receipt field)
# =============================================================================
def read_cgroup() -> str:
    """The cgroup this process is ACTUALLY in, read from /proc, never assumed."""
    try:
        for line in Path("/proc/self/cgroup").read_text().splitlines():
            if line.startswith("0::"):
                return line[3:]
    except OSError:
        pass
    return ""


def read_pids_max() -> str:
    """``pids.max`` of our own cgroup, or ``""`` when unreadable.

    Reported, never enforced here: the #74 cap decision belongs to the pids
    preflight, and the receipt's job is to say what the budget WAS.
    """
    cg = read_cgroup()
    if not cg:
        return ""
    try:
        return Path("/sys/fs/cgroup" + cg + "/pids.max").read_text().strip()
    except OSError:
        return ""


def read_nice() -> str:
    try:
        return str(os.getpriority(os.PRIO_PROCESS, 0))
    except OSError:
        return ""


def read_ioprio() -> str:
    exe = shutil.which("ionice")
    if not exe:
        return ""
    try:
        out = subprocess.run([exe, "-p", str(os.getpid())],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip()


def tree_fingerprint() -> str:
    """md5 over the tools tree: the fingerprint a bump receipt pins.

    The battery executes tools FROM THE WORKTREE, so a tool rewritten mid-run
    yields a MIXED generation whose legs fail for reasons that describe the
    EDIT, not the tool. A concurrent writer cannot be prevented from here, so
    the receipt STATES whether the tree moved instead of implying it did not.
    """
    import hashlib

    h = hashlib.md5()
    suffixes = {".sh", ".py", ".mjs"}
    paths = []
    try:
        for sub in sorted(TOOLS_DIR.iterdir()):
            if not sub.is_file():
                continue
            if sub.name.startswith("oc-") or sub.suffix in suffixes:
                if ".pre-" in sub.name or sub.name.endswith(".bak"):
                    continue
                paths.append(sub)
        for sub in sorted(TOOLS_DIR.iterdir()):
            if not sub.is_dir():
                continue
            for f in sorted(sub.iterdir()):
                if not f.is_file():
                    continue
                if f.name.startswith("oc-") or f.suffix in suffixes:
                    if ".pre-" in f.name or f.name.endswith(".bak"):
                        continue
                    paths.append(f)
    except OSError:
        return ""
    for p in sorted(set(paths)):
        try:
            h.update(p.read_bytes())
        except OSError:
            continue
    return h.hexdigest()

# =============================================================================
# selection provenance (#214) — who is allowed to stamp the bump gate
# =============================================================================
# The canonical receipt is the fleet's version-bump gate, and pytest is built to
# be run SCOPED. The two facts together mean a one-file run would otherwise hand
# ``oc-ledger sync`` a green verdict backed by the nine tests it happened to
# select — the same false-green the receipt exists to prevent, one layer out.
#
# The question this section answers is NOT "was the run big?" (a pass count is a
# number a run can be short of for honest reasons) but "was the SELECTION the
# gate's own?" — which the controller knows exactly, before a single test runs.
# Every attribute below was READ from a real pytest 9 config at
# ``pytest_configure`` time, not guessed: ``option.file_or_dir``,
# ``option.keyword``, ``option.markexpr``, ``option.deselect``,
# ``option.ignore``, ``option.ignore_glob``, ``option.lf``, ``option.newfirst``,
# ``option.failedfirst``, ``option.stepwise``, ``option.pyargs``,
# ``invocation_params.dir`` and ``inipath``.
def _is_the_tree(arg, base) -> bool:
    """True when one path argument names the battery tree itself, not a part of it.

    ``arg`` may be a nodeid (``dir/test_x.py::test_one``), a file, or a directory.
    Only the directory case can be FULL, and only when it resolves to
    ``PYTEST_DIR`` exactly: ``tools/tests/pytest/`` from the repo root and ``.``
    from inside the battery are the SAME selection, and both are the gate.
    """
    path_part = str(arg).split("::", 1)[0]
    if not path_part.strip():
        return False
    try:
        return (Path(base) / path_part).resolve() == PYTEST_DIR
    except OSError:
        return False

def selection_problem(config) -> str:
    """``""`` when this run's selection IS the gate, else WHY it is scoped.

    FULL means: every test the version bump may rely on, and nothing selected
    away. Concretely, in the order the reasons are reported:

    * no ``-k`` expression;
    * ``-m`` exactly the gate's own expression, read from ``pytest.ini`` by
      ``gate_markexpr()`` — the slow legs are deselected BY the gate, so
      requiring their absence is not a narrowing;
    * no re-run narrowing (``--lf`` / ``--nf`` / ``--ff`` / ``--sw``) and no
      ``--deselect`` / ``--ignore`` / ``--ignore-glob`` / ``--pyargs``;
    * every path argument names the battery tree itself — or there are none, in
      which case ``testpaths`` supplies it and the ini in force must be the
      battery's own.

    DELIBERATELY NOT part of the test: ``-n`` (concurrency is not selection),
    ``-q``/``--durations``/``-ra`` (reporting), ``-x``/``--maxfail`` (they can
    only stop a run that has ALREADY failed, and a stopped run's verdict is FAIL,
    never a green backed by a subset), ``-p``/``-o`` (plugin/ini plumbing) and
    ``--collect-only`` (writes no receipt at all). Refusing any of those would
    red-flag the fleet's own ship path, which is the worse failure.
    """
    opt = config.option

    keyword = str(getattr(opt, "keyword", "") or "").strip()
    if keyword:
        return "-k %r selects by name" % keyword

    expr = _norm_expr(getattr(opt, "markexpr", ""))
    gate_expr = gate_markexpr()
    if expr != gate_expr:
        if not expr:
            return ('no -m expression at all (the gate carries -m %r, so this '
                    'run describes a different selection)' % gate_expr)
        return '-m %r is not the gate\'s -m %r' % (expr, gate_expr)

    for attr, flag in (("lf", "--lf"), ("newfirst", "--nf"),
                       ("failedfirst", "--ff"), ("stepwise", "--sw")):
        if getattr(opt, attr, False):
            return "%s re-runs only part of the tree" % flag

    for attr, flag in (("deselect", "--deselect"), ("ignore", "--ignore"),
                       ("ignore_glob", "--ignore-glob")):
        values = getattr(opt, attr, None)
        if values:
            shown = ", ".join(map(str, values)) if isinstance(values, (list, tuple)) else str(values)
            return "%s %s deselects tests" % (flag, shown)

    if getattr(opt, "pyargs", False):
        return "--pyargs resolves a module name, not the tree"

    args = [a for a in (getattr(opt, "file_or_dir", None) or []) if str(a).strip()]
    if not args:
        # No path arguments: ``testpaths`` decides. That is only the battery tree
        # when the ini in force is the battery's own.
        ini = getattr(config, "inipath", None)
        try:
            ini_is_ours = ini is not None and Path(ini).resolve() == PYTEST_INI
        except OSError:
            ini_is_ours = False
        if not ini_is_ours:
            return ("no path arguments and no battery pytest.ini (inipath=%s), "
                    "so testpaths is not the battery tree" % ini)
        return ""

    base = getattr(getattr(config, "invocation_params", None), "dir", None) or Path.cwd()
    outside = [a for a in args if not _is_the_tree(a, base)]
    if outside:
        return "path selection %s is a part of the tree, not the tree" % (
            ", ".join(map(str, outside)))
    return ""

def refusal_target(config) -> tuple[Path, str]:
    """``(receipt path this run may write, why it was refused or "")``.

    The refusal keys off the CANONICAL PATH, not off how the path was chosen: if
    a scoped run would land on ``DEFAULT_RECEIPT`` — whether by default or by an
    explicit ``OC_PYTEST_RECEIPT`` aimed there — it is redirected to a scratch
    file inside this session's run dir. An override aimed anywhere else is
    honoured untouched, which is what every scoped leg in the suite uses.
    """
    requested = Path(os.environ.get("OC_PYTEST_RECEIPT") or DEFAULT_RECEIPT)
    reason = selection_problem(config)
    if not reason:
        return requested, ""
    try:
        aimed_at_gate = requested.resolve() == DEFAULT_RECEIPT.resolve()
    except OSError:
        aimed_at_gate = requested == DEFAULT_RECEIPT
    if not aimed_at_gate:
        return requested, ""
    scratch = Path(os.environ.get("OC_PYTEST_RUN_DIR") or "/tmp") / "receipt-scoped.json"
    return scratch, reason

# =============================================================================
# the run state
# =============================================================================
class Run:
    """Per-session receipt state. Lives on ``config._oc_run``."""

    def __init__(self, config, receipt_path: Path, refused: str = ""):
        self.config = config
        self.receipt_path = Path(receipt_path)
        # "" unless this run's selection was scoped and its receipt was therefore
        # refused the canonical path (#214). Named in the terminal summary.
        self.refused = refused
        self.t0_mono = time.monotonic()
        self.t0_epoch_ms = int(time.time() * 1000)
        self.rows: list[tuple[int, int, int, str]] = []   # (ordinal, start_ms, end_ms, nodeid)
        self.seen: set[str] = set()
        self.n_pass = 0
        self.n_fail = 0
        self.fp_start = tree_fingerprint()
        self.cgroup = read_cgroup()
        self.cgroup_isolated = (
            os.environ.get("BATTERY_CGROUP_ISOLATED", "") == "1"
            and bool(self.cgroup)
            and self.cgroup != os.environ.get("BATTERY_CGROUP_PARENT_CG", "")
        )
        self.extra: dict = {}
        # Per-worker fail evidence lives here; only the controller reads it back.
        self.run_dir = Path(os.environ.get("OC_PYTEST_RUN_DIR") or "/tmp/oc-pytest-run")
        self.run_dir.mkdir(parents=True, exist_ok=True)

    # -- fail evidence -------------------------------------------------------
    @property
    def worker_id(self) -> str:
        return os.environ.get("PYTEST_XDIST_WORKER", "controller")

    @property
    def fail_file(self) -> Path:
        return self.run_dir / ("fails.%s.jsonl" % self.worker_id)

    def append_fail(self, line: str) -> None:
        """Append one row to THIS worker's file. Never a shared path."""
        try:
            with open(self.fail_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(line) + "\n")
        except OSError:
            pass

    def collected_fails(self) -> tuple[list[str], bool]:
        rows: list[str] = []
        for f in sorted(self.run_dir.glob("fails.*.jsonl")):
            try:
                rows.extend(f.read_text(encoding="utf-8").splitlines())
            except OSError:
                continue
        rows = [r for r in rows if r.strip()]
        truncated = len(rows) > FAIL_ROWS_CAP
        out = []
        for r in rows[:FAIL_ROWS_CAP]:
            try:
                out.append(json.loads(r))
            except json.JSONDecodeError:
                out.append(r)
        return out, truncated

    # -- timing --------------------------------------------------------------
    def add_row(self, start: float, stop: float, nodeid: str) -> None:
        start_ms = int(start * 1000)
        end_ms = int(stop * 1000)
        self.rows.append((len(self.rows) + 1, start_ms, end_ms, nodeid))

    def timing(self) -> dict:
        """``{max_concurrency, section_count, sum_ms, slowest[<=10]}``.

        max_concurrency is the peak overlap of the intervals — the direct answer
        to "did the pool ever actually hold N tests?", which a duration sum
        cannot answer.
        """
        events = []
        for _, s, e, _nid in self.rows:
            events.append((s, 1))
            events.append((e, -1))
        events.sort()
        depth = peak = 0
        for _, delta in events:
            depth += delta
            peak = max(peak, depth)
        slowest = [
            {"n": n, "title": nid, "ms": e - s, "start_ms": s, "end_ms": e}
            for n, s, e, nid in sorted(self.rows, key=lambda r: -(r[2] - r[1]))[:SLOWEST_N]
        ]
        return {
            "max_concurrency": peak,
            "section_count": len(self.rows),
            "sum_ms": sum(e - s for _n, s, e, _nid in self.rows),
            "slowest": slowest,
        }

    def wall_ms(self) -> int:
        return int((time.monotonic() - self.t0_mono) * 1000)

    def mode(self) -> str:
        n = getattr(self.config.option, "numprocesses", None)
        if n in (None, 0):
            return "pytest sequential"
        return "pytest parallel jobs=%s" % n

    # -- the receipt ---------------------------------------------------------
    def build(self) -> dict:
        fails, trunc = self.collected_fails()
        fp_end = tree_fingerprint()
        verdict = "PASS" if self.n_fail == 0 else "FAIL"
        receipt = {
            "path": str(self.receipt_path),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pass": self.n_pass,
            "fail": self.n_fail,
            "verdict": verdict,
            "mode": self.mode(),
            "pids_max": read_pids_max(),
            "pids_cap": self.extra.get("pids_cap", ""),
            "fail_log": "",                       # no shared log: fail_rows is durable
            "fail_rows": fails,
            "fail_rows_truncated": trunc,
            "tree_changed": bool(fp_end and self.fp_start and fp_end != self.fp_start),
            "cgroup": self.cgroup,
            "cgroup_isolated": bool(self.cgroup_isolated),
            "nice": read_nice(),
            "ioprio": read_ioprio(),
            "wall_ms": self.wall_ms(),
            "timing": self.timing(),
        }
        # The cgroup session-finish hook may have improved on the configure-time
        # reading (e.g. the re-exec happened before we got here, so it is equal;
        # but a hook that re-reads gets the truth).
        receipt.update(self.extra.get("receipt_overrides", {}))
        return receipt

    def write(self) -> Path:
        receipt = self.build()
        missing = [f for f in FIELDS if f not in receipt]
        extra = [k for k in receipt if k not in FIELDS]
        if missing or extra:
            raise AssertionError(
                "receipt field drift: missing=%s extra=%s (emit_summary has 18)"
                % (missing, extra))
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(receipt, indent=2) + "\n",
                                     encoding="utf-8")
        return self.receipt_path


# =============================================================================
# hooks — called from conftest.py (a hook must be defined where pytest sees it)
# =============================================================================
# The run object for THIS process. ``pytest_runtest_logreport``'s hookspec takes
# only ``report`` (no config), so the object is published here at configure time.
_CURRENT = None
def pytest_configure(config) -> None:
    global _CURRENT
    is_controller = not hasattr(config, "workerinput")
    if is_controller:
        # One run dir per session, created BEFORE workers fork: xdist workers
        # inherit the controller's os.environ, so this is how a worker learns
        # where to put its fail file without a shared mutable path.
        run_dir = Path(os.environ.get("TMPDIR") or "/tmp") / (
            "oc-pytest-run.%d.%d" % (os.getpid(), int(time.time())))
        run_dir.mkdir(parents=True, exist_ok=True)
        os.environ["OC_PYTEST_RUN_DIR"] = str(run_dir)
        for stale in run_dir.glob("fails.*.jsonl"):
            stale.unlink(missing_ok=True)
        # #214: a scoped run must not stamp the version-bump gate. Decided HERE,
        # at configure time, from the controller's own parsed selection — before
        # a single test runs, and on the one process that writes the receipt.
        receipt_path, refused = refusal_target(config)
        config._oc_run = Run(config, receipt_path, refused=refused)  # type: ignore[attr-defined]
    else:
        # Worker: same dir (inherited), own file.
        config._oc_run = Run(config, Path("/dev/null"))     # type: ignore[attr-defined]
    _CURRENT = config._oc_run


def pytest_runtest_logreport(report) -> None:
    run = _CURRENT
    if run is None:
        return
    nodeid = report.nodeid
    if report.failed:
        # Per-worker file. A worker writes only its own rows, so a green
        # sibling can never remove this evidence.
        detail = ""
        if report.longrepr is not None:
            detail = str(report.longrepr)
        run.append_fail("%s [%s] %s" % (nodeid, report.when, detail.splitlines()[-1] if detail else ""))
    if report.when != "call":
        # A setup/teardown failure is a failed item, but its interval is not
        # the test's cost; count the item, skip the row.
        if report.failed and nodeid not in run.seen:
            run.seen.add(nodeid)
            run.n_fail += 1
        return
    if nodeid in run.seen:
        return
    run.seen.add(nodeid)
    if report.passed:
        run.n_pass += 1
    elif report.failed:
        run.n_fail += 1
    elif getattr(report, "skipped", False):
        pass
    run.add_row(report.start, report.stop, nodeid)


def pytest_sessionfinish(session, exitstatus) -> None:
    config = session.config
    run = getattr(config, "_oc_run", None)
    if run is None or hasattr(config, "workerinput"):
        return                       # CONTROLLER ONLY: workers never write
    if getattr(config.option, "collectonly", False):
        return                       # a collect-only run is not a verdict
    try:
        run.write()
    except AssertionError:
        raise
    except OSError as exc:           # a read-only tree must not turn green->red
        print("pytest-receipt: WARNING: could not write %s: %s"
              % (run.receipt_path, exc))


def receipt_path_for(config) -> Path:
    run = getattr(config, "_oc_run", None)
    return run.receipt_path if run is not None else DEFAULT_RECEIPT

def refusal_reason(config) -> str:
    """Why this run was refused the canonical path, or ``""`` if it was not."""
    run = getattr(config, "_oc_run", None)
    return getattr(run, "refused", "") if run is not None else ""
