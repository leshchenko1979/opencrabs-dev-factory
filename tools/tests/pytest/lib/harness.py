"""Launchers and observers the fixture layer does not provide.

WHAT SURVIVED THE SHELL HARNESS, AND WHY
    This module used to be one long parser for ``tools/tests/run.sh``: text
    extraction of its lock block, its cgroup block and its prelude, a
    ``--resolve-jobs`` probe, and a chunk/section census. All of that is gone
    with the file it read — a reader of a retired artifact has no subject.

    What remains is what was never about ``run.sh``:

    * ``SerialWitness`` — turns "these two legs never overlap" from a claim about
      the SCHEDULER into an observation about the LEGS. This is the one piece
      whose whole purpose was to distrust the mechanism it describes, so it had
      to survive the mechanism it was distrusting.
    * ``Overlap`` — the exception the witness raises when the claim is false.
    * ``pids_max_of_this_cgroup`` / ``tools_root`` — two reads of the live box
      that several modules share.

WHY A ``flock`` WITNESS AT ALL
    ``@pytest.mark.serial`` + ``@pytest.mark.xdist_group(...)`` is a CLAIM about
    scheduling. A mistyped group name, a worker that ignores the group, or a
    ``--dist`` scheduler that does not understand groups all leave the claim
    printed and unenforced. The witness makes the same claim checkable: each
    serial leg holds an exclusive flock on a per-group witness file for its whole
    body, and a second leg that somehow started concurrently FAILS instead of
    quietly interleaving. ``conftest.py``'s ``serial_witness`` fixture drives it.
"""

from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path

from lib import receipt as R

TOOLS_DIR = R.TOOLS_DIR


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
    def spans(directory, group: str) -> list[tuple[float, float]]:
        """``[(enter, exit)]`` for every completed hold of ``group``'s witness.

        The ONE parser for the interval log — ``overlaps`` and ``peak`` both read
        through it, so the observation and the census can never disagree about
        what the legs did.
        """
        log = Path(directory) / ("intervals.%s" % group)
        if not log.is_file():
            return []
        out = []
        stack: list[float] = []
        for line in log.read_text().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            kind, ts = parts[0], float(parts[2])
            if kind == "enter":
                stack.append(ts)
            elif kind == "exit" and stack:
                out.append((stack.pop(), ts))
        return out

    @staticmethod
    def overlaps(directory, group: str) -> list[tuple[float, float, float, float]]:
        """``[(a_enter, a_exit, b_enter, b_exit)]`` for every overlapping pair."""
        spans = SerialWitness.spans(directory, group)
        bad = []
        for i in range(len(spans)):
            for j in range(i + 1, len(spans)):
                a, b = spans[i], spans[j]
                if a[0] < b[1] and b[0] < a[1]:
                    bad.append((a[0], a[1], b[0], b[1]))
        return bad

    @staticmethod
    def peak(directory, group: str) -> int:
        """Peak number of legs of ``group`` holding the witness at one instant.

        The witness-side twin of ``lib/receipt.py``'s ``max_concurrency``: the
        receipt counts what the SCHEDULER reported, this counts what the LEGS
        observed. A group pinned correctly reads 1 from both.
        """
        events = []
        for start, stop in SerialWitness.spans(directory, group):
            events.append((start, 1))
            events.append((stop, -1))
        events.sort()
        depth = peak = 0
        for _, delta in events:
            depth += delta
            peak = max(peak, depth)
        return peak


# =============================================================================
# reads of the live box
# =============================================================================
def pids_max_of_this_cgroup() -> str:
    """``pids.max`` as the gate would read it (empty when unbounded)."""
    return R.read_pids_max()


def tools_root() -> Path:
    """The skill root (``tools/..``) — the tree the tools live in."""
    return TOOLS_DIR.parent
