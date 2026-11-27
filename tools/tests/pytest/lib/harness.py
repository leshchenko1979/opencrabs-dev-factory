"""Readers and launchers for the HARNESS itself (``tools/tests/run.sh``).

The modules that test the harness need three things the fixture layer does not
give them: the exact text of a block inside ``run.sh`` (so a ported leg drives
the REAL block, never a re-typed copy), a ``--resolve-jobs`` probe that reports
what the driver DECIDED, and a ``flock``-based witness that makes a
serial-marked leg's claim ("these two never overlap") checkable.

WHY EXTRACT, NEVER RETYPE
    Every defect in this file's orbit was a copy that drifted: #720's extraction
    range swallowed #74 and then #107, #111's two receipt writers disagreed,
    #130's helpers lived inside a section and vanished under ``--jobs N``. A
    port that re-typed the block would keep passing after the real block
    regressed, which is the one thing the legs exist to catch.

WHY ``--resolve-jobs``
    The pids cap and the default ``--jobs`` are DECIDED before any section runs
    and then printed by the probe branch (``run.sh:846-852``). Driving the probe
    is the only way to assert the decision without paying a 20-minute battery —
    and it exercises the real arithmetic rather than a second copy of it.

WHY A ``flock`` WITNESS
    ``@pytest.mark.serial`` + ``@pytest.mark.xdist_group(...)`` is a CLAIM about
    scheduling. This module turns the claim into an observation: each serial leg
    holds an exclusive flock on a per-group witness file for its whole body, and
    a second leg that somehow started concurrently FAILS instead of quietly
    interleaving. See ``SerialWitness``.
"""

from __future__ import annotations

import fcntl
import os
import re
import time
from pathlib import Path

from lib import receipt as R

TOOLS_DIR = R.TOOLS_DIR
RUN_SH = TOOLS_DIR / "tests" / "run.sh"

# The numbered-section boundary. MUST match the extractor's own awk
# (``/^# ---- [0-9]/``), which is what ``--chunk K`` actually counts — NOT a
# tidier ``\d+[a-z]?\.`` pattern. The labels in run.sh are not a single shape:
# ``00``, ``00a2``, ``9b2``, and the retired ``9g/9h`` / ``66b/66c`` all open a
# chunk, so a dot-suffixed regex undercounts by 10 and every ordinal after the
# first irregular label silently shifts. Measured: ``\d+[a-z]?\.`` finds 63 of
# the extractor's 73.
SECTION_MARKER = re.compile(r"^# ---- (\d[^.\s]*)\.?\s*(.*)$", re.M)

# The extraction fences around the single-flight lock block. The section-91 legs
# in the shell harness slice exactly these two lines; so do we.
LOCK_FENCE_OPEN = "# >>> BATTERY LOCK BLOCK"
LOCK_FENCE_CLOSE = "# <<< BATTERY LOCK BLOCK"

# The cgroup isolation block's own header (a ``# ---- `` line, i.e. it is ALSO a
# chunk boundary).
CGROUP_HEADER = "# ---- cgroup isolation (#720)"


# =============================================================================
# reading run.sh
# =============================================================================
def run_sh_text() -> str:
    return RUN_SH.read_text(encoding="utf-8", errors="replace")


def extract_lock_block(text: str | None = None) -> str:
    """The single-flight lock block, fences included — verbatim.

    Same slice as ``run.sh:5256`` (``sed -n '/^# >>> BATTERY LOCK BLOCK/,...'``).
    """
    src = (text if text is not None else run_sh_text()).splitlines()
    try:
        start = next(i for i, l in enumerate(src) if l.startswith(LOCK_FENCE_OPEN))
        end = next(i for i, l in enumerate(src) if l.startswith(LOCK_FENCE_CLOSE))
    except StopIteration:                                # pragma: no cover
        raise AssertionError("the battery lock fences are gone from run.sh — the "
                             "#107 legs would drive nothing")
    return "\n".join(src[start:end + 1]) + "\n"


def extract_cgroup_block(text: str | None = None) -> str:
    """The #720 isolation block, ending at the NEXT section boundary.

    The range end is STRUCTURAL — the first line that opens a section by any
    form (``# ---- `` or ``# >>> ``) — never a list of the successors known at
    the time. That distinction is the whole #74/#107 lesson: a name list is a
    proxy, and the next insertion re-arms it (run.sh:4699-4718).
    """
    src = (text if text is not None else run_sh_text()).splitlines()
    try:
        start = next(i for i, l in enumerate(src) if l.startswith(CGROUP_HEADER))
    except StopIteration:                                # pragma: no cover
        raise AssertionError("the #720 header is gone from run.sh")
    out = [src[start]]
    for line in src[start + 1:]:
        if line.startswith("# ---- ") or line.startswith("# >>> "):
            break
        out.append(line)
    return "\n".join(out) + "\n"


def numbered_sections(text: str | None = None) -> list[tuple[int, int, str]]:
    """``[(line_no, ordinal, title)]`` for every chunk boundary in ``run.sh``.

    The boundary rule is the EXTRACTOR's (``^# ---- [0-9]``), not a tidier one:
    see ``SECTION_MARKER``. A leg that wants the human-readable index can use
    the ordinal; a leg that wants the chunk a ``--chunk K`` selects must use
    this list's POSITION, which is why the two must be the same length.
    """
    src = (text if text is not None else run_sh_text()).splitlines()
    out = []
    for i, line in enumerate(src):
        m = re.match(r"^# ---- (\d[^.\s]*)\.?\s*(.*)$", line)
        if m:
            out.append((i + 1, m.group(1), m.group(2).strip()))
    return out


def section_calls(text: str | None = None) -> list[tuple[int, str]]:
    """``[(line_no, title)]`` for every real ``section "..."`` CALL.

    Deliberately distinct from ``numbered_sections``: the gap between the two
    is the #66 defect (five numbered blocks executed under ONE ``section``
    call), and ``test_harness_pool`` asserts the gap stays closed.
    """
    src = (text if text is not None else run_sh_text()).splitlines()
    out = []
    for i, line in enumerate(src):
        m = re.match(r'^section "(.*)"\s*$', line)
        if m:
            out.append((i + 1, m.group(1)))
    return out


def extract_chunk(want: int | str, text: str | None = None) -> str:
    """A faithful re-implementation of ``run.sh:extract_chunk``.

    Kept in Python so a leg can assert the extractor's CONTRACT (the prelude is
    emitted, exactly one section is selected, the last section is reachable)
    without shelling out for every question. ``run.sh``'s own awk is asserted
    against this by ``test_harness_structure`` — if they ever disagree, that
    test says so rather than the port drifting quietly.

    POSITIONAL, like the awk it mirrors (``/^# ---- [0-9]/ { n++; insec = (n ==
    want) }``): ``want`` is the 1-based ORDINAL of the section among markers, NOT
    the printed label. The labels (``00``, ``00a2``, ``66b``) are not a 1..N
    sequence, so comparing them — which the first draft of this function did —
    silently selects nothing for most values and made ``--chunk N`` look broken.
    ``test_python_extractor_matches_run_sh_awk`` caught exactly that.
    """
    src = (text if text is not None else run_sh_text()).splitlines()
    try:
        want_n = int(want)
    except (TypeError, ValueError):
        raise AssertionError("extract_chunk wants an int ordinal, got %r" % (want,))
    n = 0
    insec = False
    out = []
    for line in src:
        if re.match(r"^# ---- [0-9]", line):
            n += 1
            insec = (n == want_n)
            continue
        if line.startswith("verdict=PASS"):
            break
        if n == 0 or insec:
            out.append(line)
    return "\n".join(out) + "\n"


# =============================================================================
# the --resolve-jobs probe
# =============================================================================
def resolve_jobs(*, pids_max: str, jobs: str | None, tmp: Path,
                 env_extra: dict | None = None,
                 script: Path | None = None,
                 baseline_nice0: bool = False,
                 root_override: str | None = "default") -> dict:
    """Run ``run.sh --resolve-jobs`` and parse the five reported fields.

    ``tmp`` must be a throwaway directory: the probe creates a scratch root and
    a lock file, and both must land somewhere the caller owns.

    ``root_override`` selects how ``OC_BATTERY_TEST_TMPDIR`` is set:
      * ``"default"`` — pin it to ``<tmp>/root``, so the probe writes only inside
        ``tmp``. This SHORT-CIRCUITS run.sh's tmpfs branch, so a caller that
        wants to exercise the ``OC_BATTERY_SHM_DIR`` legs must not use it.
      * ``None`` — do not set it at all (and clear ``TMPDIR`` too, because inside
        a chunk child it names the parent's root and would mask the choice).
        The run then picks its OWN root, which is what the tmpfs-branch and
        default-on-disk legs need. The caller is responsible for the root it
        creates: pass ``tmp`` and reap ``tmp``'s children, or accept that
        ``--resolve-jobs`` removes its own root on exit (it does).
      * any other string — an explicit inherited root path (the ownership legs).
    """
    import subprocess

    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    pm = tmp / "pids.max"
    pm.write_text(pids_max + "\n")

    env = dict(os.environ)
    # Neutralise everything the caller's own battery may have exported: the
    # probe must be driven by THIS test's inputs only.
    for k in ("BATTERY_IN_CHUNK", "BATTERY_CGROUP_ISOLATED",
              "BATTERY_CGROUP_PARENT_CG", "OC_BATTERY_JOBS",
              "OC_BATTERY_NO_PIDS_CAP", "OC_BATTERY_PIDS_MAX_FILE",
              "OC_BATTERY_TEST_TMPDIR", "OC_BATTERY_SHM_DIR"):
        env.pop(k, None)
    env.update({
        "OC_BATTERY_LOCK": str(tmp / "lock"),
        "OC_BATTERY_NO_CGROUP": "1",
        "OC_BATTERY_PIDS_MAX_FILE": str(pm),
    })
    if root_override == "default":
        env["OC_BATTERY_TEST_TMPDIR"] = str(tmp / "root")
        env["TMPDIR"] = str(tmp)
    elif root_override is None:
        # Let run.sh choose its own root. TMPDIR is cleared because inside a
        # chunk child it names the PARENT's root and would mask the choice under
        # test; the probe is launched with cwd under tmp so a relative root can
        # never escape.
        env.pop("TMPDIR", None)
        env["TMPDIR"] = str(tmp)
    else:
        env["OC_BATTERY_TEST_TMPDIR"] = str(root_override)
        env["TMPDIR"] = str(tmp)
    if env_extra:
        env.update({k: str(v) for k, v in env_extra.items()})

    # ORDER MATTERS: run.sh shifts --jobs off the front and only then tests
    # `[ "$1" = "--resolve-jobs" ]` (run.sh:846), so the flag goes LAST.
    cmd = ["bash", str(script or RUN_SH)]
    if jobs is not None:
        cmd += ["--jobs", str(jobs)]
    cmd += ["--resolve-jobs"]

    # WHY A NICE-0 BASELINE (#76, measured 2026-11-17): run.sh re-nices ITSELF
    # to 19, so every child inherits 19. A negative control that removes the
    # renice is then indistinguishable from a working one when the caller is
    # ALREADY at 19 (inside the battery it always is) -- the control is defeated
    # by inheritance, which is exactly the class it exists to catch. renice is
    # ABSOLUTE, so from an explicit 0 baseline the real block reads 19 and the
    # neutered copy reads 0.
    preexec = None
    if baseline_nice0:
        def preexec():                                   # pragma: no cover - fork
            try:
                os.setpriority(os.PRIO_PROCESS, 0, 0)
            except OSError:
                pass

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env,
                       preexec_fn=preexec)
    fields = {}
    for line in p.stdout.splitlines():
        m = re.match(r"^(jobs|pids_max|capped|nice|ioprio)=(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    if "jobs" not in fields:
        raise AssertionError(
            "the --resolve-jobs probe produced no verdict (rc=%s)\n"
            "stdout=%r\nstderr=%r" % (p.returncode, p.stdout[-2000:], p.stderr[-2000:]))
    fields["_rc"] = p.returncode
    fields["_stdout"] = p.stdout
    return fields


# =============================================================================
# the serial witness — makes "these never overlap" an observation
# =============================================================================
class Overlap(RuntimeError):
    """Two legs that claimed to be mutually exclusive ran at the same time."""


class SerialWitness:
    """An exclusive flock a serial leg holds for its whole body.

    ``@pytest.mark.serial`` + ``@pytest.mark.xdist_group(g)`` says two legs must
    not overlap. Under ``-n N`` that is enforced by xdist scheduling — a claim
    about the SCHEDULER, not about the legs. This witness observes the legs:

    * each leg opens ``<dir>/witness.<group>`` and takes ``LOCK_EX|LOCK_NB``;
    * a second holder that appears at the same time raises ``Overlap``, so a
      broken group pin FAILS instead of interleaving silently;
    * ``enter``/``exit`` timestamps are appended to ``<dir>/intervals.<group>``
      so ``overlaps()`` can check the whole session after the fact — the
      receipt-side half of the same claim.
    """

    def __init__(self, directory, group: str, hold_s: float = 0.25):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.group = group
        self.hold_s = hold_s
        self.path = self.dir / ("witness.%s" % group)
        self._fh = None
        self._t0 = 0.0

    def __enter__(self):
        self._fh = open(self.path, "a+")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._fh.close()
            self._fh = None
            raise Overlap(
                "two legs marked serial/xdist_group(%r) overlapped — the group "
                "pin is not holding, so this leg's assertions are unsound"
                % self.group)
        self._t0 = time.monotonic()
        with open(self.dir / ("intervals.%s" % self.group), "a") as log:
            log.write("enter %r %f %d\n" % (self.group, self._t0, os.getpid()))
        # Widen the window: if the scheduler DID let a sibling in, it will land
        # here rather than in the microseconds between two syscalls.
        time.sleep(self.hold_s)
        return self

    def __exit__(self, *exc):
        t1 = time.monotonic()
        with open(self.dir / ("intervals.%s" % self.group), "a") as log:
            log.write("exit %r %f %d\n" % (self.group, t1, os.getpid()))
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
        return False

    @staticmethod
    def overlaps(directory, group: str) -> list[tuple[float, float, float, float]]:
        """``[(a_enter, a_exit, b_enter, b_exit)]`` for every overlapping pair."""
        log = Path(directory) / ("intervals.%s" % group)
        if not log.is_file():
            return []
        spans = []
        stack = []
        for line in log.read_text().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            kind, _grp, ts = parts[0], parts[1], float(parts[2])
            if kind == "enter":
                stack.append(ts)
            elif kind == "exit" and stack:
                spans.append((stack.pop(), ts))
        bad = []
        for i in range(len(spans)):
            for j in range(i + 1, len(spans)):
                a, b = spans[i], spans[j]
                if a[0] < b[1] and b[0] < a[1]:
                    bad.append((a[0], a[1], b[0], b[1]))
        return bad


# =============================================================================
# misc
# =============================================================================
def pids_max_of_this_cgroup() -> str:
    """``pids.max`` as the battery would read it (empty when unbounded)."""
    return R.read_pids_max()


def tools_root() -> Path:
    """The skill root (``tools/..``) — run.sh's ``$TOOLS_DIR/..``."""
    return TOOLS_DIR.parent
