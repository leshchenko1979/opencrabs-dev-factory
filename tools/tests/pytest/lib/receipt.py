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

Two rules this module enforces:

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
# the run state
# =============================================================================
class Run:
    """Per-session receipt state. Lives on ``config._oc_run``."""

    def __init__(self, config, receipt_path: Path):
        self.config = config
        self.receipt_path = Path(receipt_path)
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
        receipt_path = Path(os.environ.get("OC_PYTEST_RECEIPT") or DEFAULT_RECEIPT)
        config._oc_run = Run(config, receipt_path)          # type: ignore[attr-defined]
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
