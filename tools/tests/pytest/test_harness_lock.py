"""The battery's single-flight lock, driven from the REAL block (#107, #449).

WHAT THIS PORTS
    ``run.sh`` section 91 (``section "battery lock: no child inherits the lock
    fd (#107)"``) — eight legs (a)-(h). Section 92's leg (a) (the lock path is a
    FIXED shared path, never TMPDIR-derived) lives in ``test_harness_scratch.py``
    with the rest of #171; it is asserted here too, in ``test_lock_path_is_fixed``,
    because it is the invariant this module's mutual exclusion rests on.

WHY THE BLOCK IS EXTRACTED, NEVER RETYPED
    #107's defect was an fd living in the battery shell so every child inherited
    it: SIGKILL the parent and the lock stayed held by a grandchild that was not
    the battery. A port that re-typed the block would keep passing after the real
    block regressed — which is the one thing these legs exist to catch. So each
    leg composes a "battery" from ``note()`` + the block sliced verbatim between
    its ``>>>``/``<<<`` fences + a probe body that reports what it observed.

TWO TRAPS, BOTH MEASURED IN THE SHELL HARNESS
    (1) Every launch must clear ``BATTERY_IN_CHUNK``: a ``--chunk`` child that
        inherited ``1`` makes the block SKIP, and every "does not hold the lock"
        leg then passes on an empty haystack. The probe prints
        ``BLOCK-ARMED``/``BLOCK-SKIPPED`` so a skipped block is a FAIL, not a
        green.
    (2) The contention leg must search STDOUT *and* STDERR: ``note`` writes to
        stdout in this harness, so a leg that greps only stderr reads empty and
        calls a working message missing.

SERIALISATION
    These legs fork probes, SIGKILL them, and scan ``/proc/PID/fd``. Each uses
    its own ``tmp_path`` lock, so they do not share the battery lock file — but
    they are marked ``serial`` + ``xdist_group("battery-lock")`` anyway: a
    process-group SIGKILL and a ``fuser`` scan are exactly the kind of thing that
    must not race a sibling lane on a shared box, and the shell harness runs this
    section in the serial lane for the same reason.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path

import pytest

from lib import harness as H

pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-lock"),
]

# The probe body appended after the extracted block. It reports, in order:
# whether the block ran at all, the battery's own PID, whether the battery's own
# fd table carries the lock, whether an ORDINARY child inherits it (the JOBS=1
# case), who holds it, and a live grandchild the SIGKILL leg can strand it on.
# ``$BASHPID`` — not ``$$`` — for the child check: inside a subshell ``$$`` is
# still the parent, so ``$$`` would test the parent twice.
PROBE_BODY = r"""
if [ -n "${BATTERY_LOCK:-}" ]; then echo BLOCK-ARMED; else echo BLOCK-SKIPPED; fi
echo "BATTERY-PID $$"
if ls -l "/proc/$$/fd" 2>/dev/null | grep -qF "$BATTERY_LOCK"; then echo SELF-HOLDS; else echo SELF-CLEAN; fi
( if ls -l "/proc/$BASHPID/fd" 2>/dev/null | grep -qF "$BATTERY_LOCK"; then echo CHILD-HOLDS; else echo CHILD-CLEAN; fi )
echo "HOLDERS $(fuser "$BATTERY_LOCK" 2>/dev/null | tr -s ' \t' ' ' | sed 's/^ //; s/ $//')"
sleep 30 &
echo "GRANDCHILD $!"
echo PROBE-READY
wait
"""


class LockProbe:
    """A synthetic "battery": ``note()`` + the extracted lock block + a probe."""

    def __init__(self, root: Path, name: str = "battery.sh"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = self.root / ("%s.lock" % name.replace(".sh", ""))
        self.script = self.root / name
        self.script.write_text(
            "#!/usr/bin/env bash\nset -u\n"
            "note() { printf '%s\\n' \"$*\"; }\n"
            + H.extract_lock_block()
            + PROBE_BODY,
            encoding="utf-8",
        )
        self.script.chmod(0o755)
        self._procs: list[subprocess.Popen] = []

    # -- launch ---------------------------------------------------------------
    def _env(self, extra: dict | None = None) -> dict:
        env = {k: v for k, v in os.environ.items()
               if k not in ("BATTERY_IN_CHUNK", "OC_BATTERY_LOCK",
                            "OC_BATTERY_LOCK_WAIT")}
        env["OC_BATTERY_LOCK"] = str(self.lock)
        if extra:
            env.update({k: str(v) for k, v in extra.items()})
        return env

    def launch(self, *, extra_env: dict | None = None,
               script: Path | None = None) -> subprocess.Popen:
        """Start the probe detached (own process group) and track it for cleanup."""
        p = H.spawn(
            ["bash", str(script or self.script)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self._env(extra_env), start_new_session=True)
        self._procs.append(p)
        return p

    @staticmethod
    def await_ready(p: subprocess.Popen, timeout: float = 15.0) -> str:
        """Read the probe's stdout until ``PROBE-READY`` (or the bound)."""
        deadline = time.monotonic() + timeout
        lines: list[str] = []
        while time.monotonic() < deadline:
            line = p.stdout.readline()
            if not line:
                break
            lines.append(line)
            if line.startswith("PROBE-READY"):
                return "".join(lines)
        return "".join(lines)

    def run_to_completion(self, *, extra_env: dict | None = None,
                          timeout: float = 30.0) -> tuple[int, str]:
        """Launch, let it finish (or be killed), return ``(rc, combined output)``."""
        p = self.launch(extra_env=extra_env)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._kill_group(p)
            out, err = p.communicate(timeout=10)
        return p.returncode, out + err

    # -- cleanup --------------------------------------------------------------
    @staticmethod
    def _kill_group(p: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                p.kill()
            except ProcessLookupError:
                pass

    def close(self) -> None:
        """SIGKILL every probe group and reap it. Never leave a sleep behind."""
        for p in self._procs:
            if p.poll() is None:
                self._kill_group(p)
            try:
                p.communicate(timeout=10)
            except (subprocess.TimeoutExpired, ValueError):
                pass
        self._procs.clear()


def field(out: str, key: str) -> str | None:
    """First ``KEY value`` line from probe output, or None."""
    m = re.search(r"^%s\s+(.*)$" % re.escape(key), out, re.M)
    return m.group(1).strip() if m else None

def verdict(out: str, name: str) -> str | None:
    """First ``NAME-x`` token for the two-valued probes (SELF-/CHILD-/BLOCK-)."""
    m = re.search(r"^%s-(HOLDS|CLEAN|ARMED|SKIPPED)$" % re.escape(name), out, re.M)
    return m.group(1) if m else None

def lock_is_free(lock: Path, tries: int = 100) -> bool:
    """True once ``flock -n`` succeeds; polls because release is asynchronous."""
    for _ in range(tries):
        r = H.run(["flock", "-n", str(lock), "true"],
                           capture_output=True)
        if r.returncode == 0:
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def probe(tmp_path):
    lp = LockProbe(tmp_path / "lk91")
    yield lp
    lp.close()

# =============================================================================
# (a) POSITIVE CONTROL — the block runs and acquires
# =============================================================================
def test_lock_block_arms_and_acquires(probe):
    """Without this every negative leg below passes on a block that never ran.

    A block that stopped locking anything at all — or that skipped because
    ``BATTERY_IN_CHUNK`` leaked in from the surrounding run — would satisfy
    "does not hold the lock" trivially. ``BLOCK-ARMED`` is the discriminator.
    """
    p = probe.launch()
    out = probe.await_ready(p)
    assert verdict(out, "BLOCK") == "ARMED", (
        "the lock block did not run (block=%r) — every leg below would assert "
        "nothing. output: %r" % (verdict(out, "BLOCK"), out[-600:]))
    assert "PROBE-READY" in out, "the probe never became ready: %r" % out[-600:]

# =============================================================================
# (b) the battery's OWN fd table carries no lock fd
# =============================================================================
def test_the_battery_holds_no_lock_fd_itself(probe):
    """The fix: fd 9 is opened INSIDE the coproc, so this shell never owns it.

    The old ``exec 9>`` shape put the fd in the battery shell and every child
    inherited it. ``SELF-HOLDS`` is that regression.
    """
    p = probe.launch()
    out = probe.await_ready(p)
    assert verdict(out, "BLOCK") == "ARMED", "precondition: the block must have run"
    assert verdict(out, "SELF") == "CLEAN", (
        "the battery still holds the lock fd itself, so children can inherit it "
        "(#107): %r" % out[-600:])

# =============================================================================
# (c) an ORDINARY child inherits nothing — the JOBS=1 case
# =============================================================================
def test_an_ordinary_child_inherits_no_lock_fd(probe):
    """With the default JOBS=1 every tool is this shell's own child.

    Closing the fd in the ``--chunk`` branch alone fixes only the fan-out case
    and leaves this one: a tool mid-run would keep the lock alive after the
    battery died.
    """
    p = probe.launch()
    out = probe.await_ready(p)
    assert verdict(out, "BLOCK") == "ARMED", (
        "precondition: CHILD-CLEAN would be vacuous on a block that never ran")
    assert verdict(out, "CHILD") == "CLEAN", (
        "a child of the battery still inherits the lock fd — with JOBS=1 every "
        "tool would hold it (#107): %r" % out[-600:])

# =============================================================================
# (d) the lock IS held, and NOT by the battery
# =============================================================================
def test_the_lock_is_held_by_a_child_not_the_battery(probe):
    """A lock nobody holds serialises nothing; a lock the battery holds leaks.

    Both halves matter: an empty ``HOLDERS`` means the block stopped locking,
    and the battery PID appearing among the holders is the #107 defect itself.
    """
    p = probe.launch()
    out = probe.await_ready(p)
    battery_pid = field(out, "BATTERY-PID")
    holders = field(out, "HOLDERS") or ""
    assert battery_pid, "the probe never reported its own PID: %r" % out[-600:]
    assert holders.strip(), (
        "nothing holds the lock while a battery is running — the block is not "
        "serialising anything: %r" % out[-600:])
    assert battery_pid not in holders.split(), (
        "the battery PID %s is among the lock holders (%r) — the fd is back in "
        "the battery shell (#107)" % (battery_pid, holders))

# =============================================================================
# (e) SIGKILL with a LIVE grandchild frees the lock
# =============================================================================
def test_sigkill_frees_the_lock_while_a_grandchild_lives(probe):
    """The #107 acceptance: the lock must not outlive a SIGKILLed battery.

    A live grandchild stands in for a tool mid-run. If the fd were inherited, the
    grandchild would keep the lock held after the battery died and the next run
    would burn ``BATTERY_LOCK_WAIT`` (900 s) on a process that never releases it.
    """
    p = probe.launch()
    out = probe.await_ready(p)
    assert verdict(out, "BLOCK") == "ARMED", (
        "the SIGKILL leg is vacuous — the block never ran, so no lock was taken")
    grand = field(out, "GRANDCHILD")
    assert grand and _alive(int(grand)), (
        "no live grandchild to strand the lock on, so this leg would pass "
        "vacuously: %r" % out[-600:])
    # SIGKILL the BATTERY only — not its process group — so the grandchild is
    # still alive when we check. Killing the group would prove nothing about
    # inheritance.
    os.kill(p.pid, signal.SIGKILL)
    try:
        assert lock_is_free(probe.lock), (
            "the lock outlived a SIGKILLed battery — a grandchild is still "
            "holding it (#107 regression)")
        assert _alive(int(grand)), (
            "the lock came free but the grandchild had already exited — the leg "
            "did not test inheritance")
    finally:
        try:
            os.kill(int(grand), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False

# =============================================================================
# (f) CONTENTION — bounded wait, rc 2 (a harness code, never a verdict)
# =============================================================================
def test_a_contended_run_gives_up_with_rc_2(probe):
    """A contended run must exit 2 — a harness condition, never a test verdict.

    The budget is asserted as a LOWER bound only: ``flock -w 2`` guarantees at
    least ~2 s of waiting, and an upper bound would red under ``-n N`` on a
    loaded box for the same reason it reddened under ``--jobs 2``.
    """
    holder = probe.launch()
    out = probe.await_ready(holder)
    assert "PROBE-READY" in out, "the first holder never started: %r" % out[-600:]
    t0 = time.monotonic()
    rc, combined = probe.run_to_completion(extra_env={"OC_BATTERY_LOCK_WAIT": "2"})
    elapsed = time.monotonic() - t0
    assert rc == 2, (
        "a contended run exited %d, not the harness code 2 (output: %r)"
        % (rc, combined[-600:]))
    assert elapsed >= 1.5, (
        "the contended run gave up in %.2fs with OC_BATTERY_LOCK_WAIT=2 — the "
        "bounded wait was not honoured" % elapsed)

def test_a_contended_run_names_the_budget_and_the_holder(probe):
    """The refusal must be diagnosable without hunting with ``ps``.

    ``note`` writes to STDOUT in this harness, so the search spans both streams;
    a leg that grepped only stderr would call a working message missing.
    """
    holder = probe.launch()
    out = probe.await_ready(holder)
    assert "PROBE-READY" in out, "the first holder never started"
    rc, combined = probe.run_to_completion(extra_env={"OC_BATTERY_LOCK_WAIT": "2"})
    assert "after 2s" in combined or "within 2s" in combined, (
        "the refusal does not name the budget it used (2s): %r" % combined[-800:])
    assert re.search(r"holder PID\(s\):\s*\d+", combined), (
        "the timeout did not name a holder PID: %r" % combined[-800:])

# =============================================================================
# (g) a --chunk child never opens the lock file
# =============================================================================
def test_a_chunk_child_never_opens_the_lock_file(probe):
    """A child that opened it would deadlock against its own parent.

    The block is guarded on ``BATTERY_IN_CHUNK``; the file must not even be
    CREATED. Driven through ``run.sh --chunk 999`` (an ordinal that selects no
    section), with a fresh lock path that nothing else touches.
    """
    fresh = probe.root / "chunk-only.lock"
    assert not fresh.exists()
    env = {k: v for k, v in os.environ.items() if k != "BATTERY_IN_CHUNK"}
    env["OC_BATTERY_LOCK"] = str(fresh)
    env["OC_BATTERY_NO_CGROUP"] = "1"
    r = H.run(["bash", str(H.RUN_SH), "--chunk", "999"],
                       capture_output=True, text=True, timeout=120, env=env)
    assert not fresh.exists(), (
        "a --chunk child opened the lock file %s — it would deadlock against "
        "its own parent (#107). rc=%d out=%r"
        % (fresh, r.returncode, (r.stdout + r.stderr)[-600:]))

# =============================================================================
# (h) the parallel driver waits on CHUNK PIDs, never on the coproc (#129)
# =============================================================================
FIXED_DRIVER = r"""#!/usr/bin/env bash
set -u
JOBS=2
LOG="$2"
coproc LOCKER { flock -n 9 && echo READY && cat >/dev/null; } 9>"$1"
read -r _st <&"${LOCKER[0]}"
_pids=()
for k in 1 2 3 4 5 6; do
  ( printf 'enter %s %s\n' "$k" "$(date +%s%N)" >> "$LOG"
    sleep 1
    printf 'exit %s %s\n' "$k" "$(date +%s%N)" >> "$LOG" ) & _pids+=("$!")
  while :; do
    _live=0
    for _cp in "${_pids[@]}"; do kill -0 "$_cp" 2>/dev/null && _live=$((_live + 1)); done
    [ "$_live" -lt "$JOBS" ] && break
    sleep 0.05
  done
done
wait "${_pids[@]}"
"""

OLD_DRIVER = r"""#!/usr/bin/env bash
set -u
JOBS=2
coproc LOCKER { flock -n 9 && echo READY && cat >/dev/null; } 9>"$1"
read -r _st <&"${LOCKER[0]}"
for k in 1 2 3 4 5 6; do
  ( sleep 1 ) &
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 0.05; done
done
wait
"""

def test_the_driver_terminates_while_the_old_shape_hangs(probe):
    """A bare ``wait`` saw the lock coproc and blocked forever once chunks ended.

    Measured in the shell harness: 73/73 chunks done, driver in ``do_wait``, zero
    output for 27m13s. The fixed driver tracks chunk PIDs; the OLD shape is kept
    as the negative control because a driver that never waited at all would also
    "terminate" — so the control MUST hang or the fixed arm proves nothing.
    """
    d = probe.root / "drv"
    d.mkdir(exist_ok=True)
    fixed = d / "fixed"
    old = d / "old"
    fixed.write_text(FIXED_DRIVER, encoding="utf-8")
    old.write_text(OLD_DRIVER, encoding="utf-8")
    fixed.chmod(0o755)
    old.chmod(0o755)
    log = d / "concurrency.log"
    log.write_text("", encoding="utf-8")

    # The old shape MUST hang. `timeout 4` gives it well over the 3 s its six
    # 1 s chunks need even at jobs=2, so rc 124 means "hung", not "slow".
    r_old = H.run(["timeout", "4", "bash", str(old), str(d / "o.lock")],
                           capture_output=True, timeout=30)
    assert r_old.returncode == 124, (
        "the OLD driver shape did NOT hang (rc=%d) — the control is broken, so "
        "the fixed arm proves nothing" % r_old.returncode)

    # The fixed shape must terminate. Bound is generous (20 s for ~3 s of work)
    # because the assertion is TERMINATION, not a wall window — a wall window
    # reds under -n N for the same reason it reddened under --jobs 2.
    r_new = H.run(["timeout", "20", "bash", str(fixed),
                            str(d / "f.lock"), str(log)],
                           capture_output=True, timeout=40)
    assert r_new.returncode == 0, (
        "the fixed driver did not terminate (rc=%d) — bare wait still sees the "
        "coproc: %r" % (r_new.returncode, (r_new.stdout + r_new.stderr)[-600:]))

def test_the_fixed_driver_respects_the_jobs_throttle(probe):
    """``--jobs 2`` must run TWO chunks at a time, not one.

    The old throttle counted the coproc as a worker, so ``jobs -rp`` saw 3 live
    jobs for 2 chunks and ran ONE. Wall time cannot discriminate that on a loaded
    box, so this asserts the OBSERVED peak concurrency from the driver's own
    enter/exit log — load-immune, and the property the throttle actually claims.
    """
    d = probe.root / "drv2"
    d.mkdir(exist_ok=True)
    fixed = d / "fixed"
    fixed.write_text(FIXED_DRIVER, encoding="utf-8")
    fixed.chmod(0o755)
    log = d / "concurrency.log"
    log.write_text("", encoding="utf-8")
    r = H.run(["timeout", "20", "bash", str(fixed),
                        str(d / "f.lock"), str(log)],
                       capture_output=True, timeout=40)
    assert r.returncode == 0, "the fixed driver did not terminate: rc=%d" % r.returncode
    assert peak_concurrency(log) == 2, (
        "observed peak concurrency was %d, not 2 — the throttle either runs one "
        "chunk at a time (coproc counted as a worker) or ignores JOBS"
        % peak_concurrency(log))

def peak_concurrency(log: Path) -> int:
    """Peak simultaneous chunk bodies, from the driver's enter/exit timestamps."""
    events: list[tuple[int, int]] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        kind, _k, ns = parts
        try:
            events.append((int(ns), 1 if kind == "enter" else -1))
        except ValueError:
            continue
    events.sort()
    depth = peak = 0
    for _ns, delta in events:
        depth += delta
        peak = max(peak, depth)
    return peak

# =============================================================================
# the invariant this module rests on: the lock path is FIXED, not TMPDIR-derived
# =============================================================================
def test_lock_path_is_fixed_and_never_derived_from_tmpdir():
    """A per-run TMPDIR that moved the lock would un-serialize concurrent lanes.

    This is section 92's leg (a), restated where the lock's mutual exclusion is
    actually relied on. The default is a fixed ``/tmp/oc-battery.lock``; deriving
    it from ``${TMPDIR:-/tmp}`` would hand every lane its own lock while they
    still share the one canonical receipt — green transcript, no mutual
    exclusion.
    """
    text = H.run_sh_text()
    assert re.search(
        r'^[ \t]*BATTERY_LOCK="\$\{OC_BATTERY_LOCK:-/tmp/oc-battery\.lock\}"',
        text, re.M), (
        "the battery lock default is not a fixed shared path — a per-run TMPDIR "
        "would un-serialize concurrent lanes (#171). Found: %r"
        % (re.search(r'^[ \t]*BATTERY_LOCK=".*$', text, re.M).group(0)
           if re.search(r'^[ \t]*BATTERY_LOCK=".*$', text, re.M) else None))
    assert "${TMPDIR" not in re.search(
        r'^[ \t]*BATTERY_LOCK="[^"]*"', text, re.M).group(0), (
        "the lock path is derived from TMPDIR — that is the #171 trap")
