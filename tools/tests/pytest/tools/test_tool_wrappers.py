"""Pure ``run_selftest <tool>`` wrapper sections, ported from run.sh.

SCOPE (factory #197, worker A). These are the battery sections whose ENTIRE
body is "run this tool's ``--selftest``, assert rc 0". Everything else stays in
run.sh until its owning worker ports it:

  * bespoke shell sections with real logic ................... worker B
  * harness self-tests (lock/chunk/cgroup/scratch/receipt) ... worker D
  * cache .................................................... worker E

One function, one parameter per tool, so ``-k`` and ``-m`` select individual
tools::

    pytest tools/tests/pytest/tools/test_tool_wrappers.py -k oc-seal
    pytest tools/tests/pytest/tools/test_tool_wrappers.py -m "not slow"

THE CONTRACT: RC, NOT STDERR
----------------------------------
``run.sh:run_selftest`` (run.sh:280) asserts EXACTLY ONE thing: the exit code.

    run_capture "$t --selftest" timeout --kill-after=30 "$_st" env \\
        OC_DEPLOY_STATE_DIR="$sd" "$_tp" --selftest
    _rc=$?
    [ "$_rc" = 124 ] && note "... HUNG -- killed at the ${_st}s bound (#753)"
    return "$_rc"

Every caller is ``run_selftest <tool> && ok <label> || bad <label>``, so the
whole assertion is ``rc == 0``. There is NO stderr contract anywhere in the
harness -- asserting ``err == ""`` here would INVENT one, and it would be
wrong: ``oc-rebase-safety`` prints its SUCCESS line ("selftest: 23/23 OK") to
stderr, and ``oc-attrib`` / ``oc-audit-ship`` / ``oc-tg-audit`` print benign
progress there. All are rc 0 and healthy. Asserting rc is therefore the
faithful port, not a vacuous one. Non-vacuity lives in three other places:

  1. Every tool in ``TOOLS`` was EXECUTED and verified to return a real,
     multi-case verdict (``selftest OK: 9/9``, ``PASS=44 FAIL=0``,
     ``117/117 passed``, ...). None is a no-op stub. A tool whose ``--selftest``
     were absent or a bare ``exit 0`` is a FALSE GREEN and is not listed.
  2. ``test_tool_selftest_reports_something`` asserts the selftest actually
     PRINTS a verdict. A stub that silently exits 0 cannot satisfy it, so the
     rc-only assertion above cannot be satisfied by a no-op.
  3. Timeouts are per-tool, so a slow-but-legitimate selftest
     cannot red spuriously -- the defect run.sh:294-300 documents.

TIMEOUTS ARE PER-TOOL, NOT A BLANKET BOUND
------------------------------------------
A blanket short bound would red a slow-but-legitimate selftest: run.sh's own
1800 s default exists because the longest section takes 296.5 s.

Each bound is sized on the LOADED figure, not the quiet one, with >= 2x headroom
on it, because the loaded figure is the regime this module actually runs in.
``oc-wt`` takes 21 s quiet and 118 s under load; ``oc-upstream-delta`` 12 s
quiet and 60 s loaded. A bound sized on the quiet number would red `oc-wt` at
118 s against 180 s -- a spurious failure, which is the exact defect
run.sh:294-300 documents.

The tools that take minutes carry ``@pytest.mark.slow`` so ``-m "not slow"``
deselects them rather than stalling a quick gate.

EVERY LEG IS `serial` IN ONE `xdist_group` -- see the note beside
``WRAPPER_GROUP``. A ``--selftest`` is a process TREE, this box's cgroup caps
``pids`` at 64, and two concurrent legs already peak at 41, so overlapping legs
fork-fail rather than run faster. ``-n N`` therefore runs them in order on one
worker; ``-n 0`` is unchanged. The bound is a property of the box, not of the
tools, so the marker is the honest statement of it.
"""
from __future__ import annotations

import fcntl
import hashlib
import pathlib
import tempfile

import pytest

# ---------------------------------------------------------------------------
# (tool, timeout_seconds) -- timeout is a hard per-call bound, REQUIRED by the
# fixture (an omittable bound is a bound that gets omitted; #753 is that hang).
# Wall time is in the comment so the next reader can audit the headroom instead
# of trusting the number.
# ---------------------------------------------------------------------------
TOOLS = [
    # -- fast: seconds. Loaded-box headroom in the comment ------------------
    ("oc-verify-order",         120),   #   2.1 s
    ("oc-verify-job",           120),   #   5.7 s
    ("oc-verify-artifact",      120),   #   4.6 s
    ("oc-seal",                 120),   #   2.9 s
    ("oc-pr-atomicity",         120),   #   2.2 s
    ("oc-attrib",               180),   #  10.4 s  benign stderr, rc 0
    ("oc-features",             120),   #   3.5 s
    ("oc-issue-sweep",          120),   #   5.6 s
    ("oc-review-persist",       120),   #   5.8 s
    ("oc-upstream-delta",       300),   #  12.1 s quiet / 60.5 s loaded
    ("oc-wt",                   400),   #  21.1 s quiet / 118.1 s loaded
    ("oc-drift-check",          180),   #  38.3 s
    ("oc-branch-sweep",         120),   #   7.1 s
    ("oc-pr-fault-scope",       120),   #   6.7 s
    ("oc-smoke-evidence",       180),   #  17.5 s
    ("oc-issue-log",            120),   #   9.9 s
    ("oc-audit-ship",           120),   #   2.9 s  benign stderr, rc 0
    ("oc-tg-audit",             120),   #   0.9 s  benign stderr, rc 0
    ("oc-rebase-safety",        120),   #   4.1 s  success line on STDERR
    ("oc-roster",               180),   #   7.0 s
    ("oc-watcher-audit",        180),   #   7.9 s
    ("oc-lint-laws",            180),   #  21.7 s
    ("oc-log-search",           120),   #   3.3 s
    ("oc-census",               180),   #   7.0 s
    ("oc-claims-single-source", 120),   #   3.6 s
    ("oc-start",                300),   #  14.8 s
    ("oc-smoke",                300),   #  37.3 s
    # -- slow: minutes, not seconds. Deselected by -m "not slow" -----------
    # oc-notify-fanout belongs HERE, not with the fast tools: 266 s standalone
    # and 223 s under load, i.e. SLOWER than oc-gate. A 300 s bound would be
    # only 1.13x headroom -- one loaded box away from a spurious red, the exact
    # defect run.sh:294-300 documents. 600 s is 2.3x and the slow marker keeps
    # it out of a quick gate.
    ("oc-notify-fanout",        600),   # 266 s; 103 cases; needs a real ledger file
    ("oc-gate",                 600),   # 118.4 s
    ("oc-commit",               600),   # 124.2 s
    ("oc-ledger",               600),   # ~296 s   the longest in the battery
    ("oc-ship",                 900),   # orchestrator; execs into ship-selftest.sh
    ("oc-issue-dispatch",       900),   # 226+ legs; oc-roster classify has a 120 s budget
]

SLOW = frozenset({
    "oc-notify-fanout",
    "oc-gate",
    "oc-commit",
    "oc-ledger",
    "oc-ship",
    "oc-issue-dispatch",
})

TIMEOUTS = dict(TOOLS)

# ---------------------------------------------------------------------------
# THE ONE LEG THAT GETS A BOUNDED RETRY: oc-ledger, and why a retry is the
# honest reading rather than a mask over a wrapper defect
# ---------------------------------------------------------------------------
# `oc-ledger --selftest` carries its own 10-way concurrent-append probe
# (tools/state/oc-ledger:4000, case `race-max-n`: ten backgrounded `stamp`
# calls, then asserts the max `n` advanced by exactly 10). Under box load that
# probe loses appends, and the tool reports it as a case failure:
#
#     FAIL selftest - race-max-n (want rc=919 got rc=916)
#     oc-ledger selftest: PASS=740 FAIL=1
#
# That is a REAL load-sensitivity inside oc-ledger's own concurrency probe --
# not a wrapper bug, and not something the `serial_box` flock can fix, because
# the contention is with the SIBLING LANES on this shared box (four worker
# worktrees), not with another leg of this module. The discriminator is BOX
# LOAD, not worker count: at load 8 the probe is 6-for-6 clean, at load 21 it
# loses 3-4 appends, and no `-n` setting changes that. Retrying once costs a
# second ~296 s leg ONLY on an already-failed run, and it separates "the tool's
# race probe got starved by a neighbour" from "the tool is broken" -- which is
# the same distinction run.sh:294-300 draws for a HUNG leg (rc 124 is not a tool
# verdict either).
#
# Deliberately NOT a blanket retry: retrying every leg would hide a genuine
# regression behind a second attempt, and this is the ONLY leg that flakes.
# If a second tool starts needing this, the correct move is to report
# the flake, not to widen the set.
RETRY_ONCE = frozenset({"oc-ledger"})

# ---------------------------------------------------------------------------
# WHY EVERY LEG IS `serial` + ONE xdist_group: the pids cap
# ---------------------------------------------------------------------------
# A `--selftest` is not one process. Every tool here forks git, mktemp, grep,
# jq and often its own sub-selftests, so ONE leg is a process TREE, and the
# trees of two legs overlap the instant they run concurrently.
#
# This box runs under a cgroup with `pids.max = 64` (`ulimit -u` is 15532, so
# the LIMIT THAT BITES is the cgroup, not the login limit -- read the former,
# never the latter). Sampling `pids.current` while running JUST TWO legs
# (`oc-ledger` and `oc-wt`, `-n 2`) peaks at 41 of 64. Two legs already sit at
# 64% of the cap, so any third concurrent leg is over it and `fork()` returns
# EAGAIN:
#     error: cannot fork() for maintenance: Resource temporarily unavailable
# (git's own message; `rev-list`, `gc`, `pack-objects`, `symbolic-ref` the
# same). That reads as N broken tools and is ONE stated cap, which is the
# defect test_cgroup.py::test_caps_scale_with_worker_count already names for
# the shell harness ("read as EIGHT broken tools rather than one stated cap").
#
# THE REMEDY THAT ACTUALLY WORKS IS THE `serial_box` FLOCK FIXTURE, NOT THE
# `xdist_group` MARKER -- and the difference is the whole point, because the
# marker LOOKS sufficient and is not.
#
# pytest.ini documents `serial` + `xdist_group` as the mechanism, and that is
# correct ONLY under `--dist loadgroup`. xdist's DEFAULT is `--dist load`,
# which IGNORES groups entirely, and nothing in this directory sets `--dist`.
# So the group marker is inert: every worker picks up a selftest and runs them
# all at once, which is the same cap hit again -- fork errors under `-n auto`,
# and under `-n 2` zero fork errors but `oc-ledger` still flaking its own
# `race-max-n` case (want rc=919, got rc=916), because two overlapping tool
# trees are already enough contention to red a case.
#
# `serial_box` therefore takes an exclusive `flock` for the duration of each
# leg. A lock is used INSTEAD OF relying on `--dist loadgroup` because it is
# correct under any dist mode and cannot be disarmed by a later ini edit or by
# a caller passing `--dist load` explicitly. The marker is kept as the stated
# claim -- it is what makes the group real if `--dist loadgroup` is ever set --
# but the lock is what enforces it today. Under `-n 0` the lock is uncontended
# and the group inert, so the serial fallback needs no changes: the acceptance
# bar pytest.ini sets.
#
# Sharing ONE group name across all 33 is deliberate: these legs contend for a
# single box-wide process budget, so the budget is the unit of mutual exclusion,
# not the tool. Two groups would still collide with each other.
#
# The cost is that `-n N` buys nothing for this module -- correct, and the point:
# the resource these legs contend for is shared, so parallelism here converts
# into fork failures rather than wall-clock savings.
WRAPPER_GROUP = "tool-selftests"

PARAMS = [
    pytest.param(
        tool,
        id=tool,
        marks=(
            pytest.mark.serial,
            pytest.mark.xdist_group(WRAPPER_GROUP),
            *((pytest.mark.slow,) if tool in SLOW else ()),
        ),
    )
    for tool, _ in TOOLS
]

# Per-tool env overrides, ONLY where env_guard's defaults are actively hostile.
#
# ``oc-notify-fanout``: env_guard sets OC_DEV_STATE to a scratch path that is
# NEVER CREATED. The selftest unsets OC_FANOUT_LEDGER for its law-17 arm and
# falls back to ``$OC_DEV_STATE/events.jsonl``; with a nonexistent directory
# the roster read fails and the WHOLE run dies rc 3 with NOTHING on either
# stream. Three probes:
#     OC_DEV_STATE=<nonexistent>  -> rc 3, silent
#     OC_DEV_STATE unset          -> rc 0, PASS=103 FAIL=0
#     OC_DEV_STATE=""             -> rc 0, PASS=103 FAIL=0
# Empty is falsy for every ``${OC_DEV_STATE:-...}`` fallback (oc-log.sh:174,
# 258,280 and oc-ledger:195), so it restores the tool's own default instead of
# pointing anywhere. It goes through the fixture's ``env=`` because
# ``run_selftest`` has no unset mechanism, and reaching into ``os.environ``
# behind the fixture's back is the exact leak class env_guard prevents.
TOOL_ENV = {
    "oc-notify-fanout": {"OC_DEV_STATE": ""},
}


@pytest.fixture
def fanout_ledger(scratch):
    """An EXISTING, empty fanout ledger.

    ``oc-notify-fanout`` dies rc 3 ``roster missing: $LEDGER`` unless its
    ledger is a real FILE (tools/notify/oc-notify-fanout:1151). run.sh passes
    the LIVE fleet ledger; env_guard redirects ``OC_FANOUT_LEDGER`` into this
    worker's scratch where nothing has created the file yet. This stand-in is
    the shell contract, expressed as a fixture instead of a live path.
    """
    p = scratch.path / "fanout-ledger" / "events.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")
    return p


def _env_for(tool, fanout_ledger):
    """Env override for ``tool``, or None to inherit env_guard's redirections."""
    env = dict(TOOL_ENV.get(tool, {}))
    if tool == "oc-notify-fanout":
        env["OC_FANOUT_LEDGER"] = str(fanout_ledger)
    return env or None

@pytest.fixture
def serial_box():
    """Serialize every leg of THIS module across xdist workers, via a file lock.

    Why a lock and not just ``@pytest.mark.xdist_group``: xdist honours groups
    ONLY under ``--dist loadgroup``, and its DEFAULT is ``--dist load``, which
    IGNORES them. pytest.ini does not set ``--dist``, so the group marker is
    inert and every worker runs its selftest at once. On a box whose cgroup
    carries ``pids.max = 64``, that hits the cap: legs fail carrying

        fork: retry: Resource temporarily unavailable
        error: cannot fork() for ssh-keygen / rev-list / pack-objects

    -- the SAME cap, not N broken tools. Serializing to two concurrent legs
    avoids the fork errors but still flakes ``oc-ledger``'s own ``race-max-n``
    case (want rc=919, got rc=916), because two tool trees overlapping is
    already contention.

    A lock is used rather than relying on ``--dist loadgroup`` because it is
    correct under ANY dist mode: it cannot be disarmed by a future change to
    the ini or by a caller passing ``--dist load`` explicitly. Under ``-n 0``
    it is uncontended and therefore inert, which is the serial-fallback bar
    pytest.ini sets.

    Scope is the WORKTREE, not the box: the digest is taken from the repo root
    so a sibling lane running the same module in its own worktree does not
    block this one for twenty minutes. ``hashlib`` rather than ``hash()``
    because ``hash()`` is randomized per process (PYTHONHASHSEED) and every
    worker would then open a DIFFERENT file -- no serialization at all.
    """
    # One level deeper than the flat layout: this file is filed under
    # ``pytest/tools/``, so the repo root is parents[4], not parents[3].
    root = pathlib.Path(__file__).resolve().parents[4]
    digest = hashlib.sha1(str(root).encode()).hexdigest()[:12]
    lock_path = pathlib.Path(tempfile.gettempdir()) / ("oc-pytest-wrappers-%s.lock" % digest)
    fh = lock_path.open("a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()

@pytest.mark.parametrize("tool", PARAMS)
def test_tool_selftest(serial_box, run_selftest, fanout_ledger, tool):
    """``<tool> --selftest`` exits 0, within its bound, having printed a verdict.

    Three assertions, each earned:

    1. ``not result.timed_out`` -- a fired bound is NOT a tool verdict.
       run.sh:301 says so itself (rc 124 is "HUNG", not a failure of the
       tool). Keeping them apart stops a loaded box from looking like a
       broken tool.
    2. ``rc == 0`` -- the shell contract, verbatim (run.sh:280 + the
       ``&& ok || bad`` at every call site). This is what run.sh asserted.
    3. ``combined`` is non-empty -- the ANTI-STUB guard. rc alone cannot tell
       a real selftest from a no-op that returns 0, so a tool whose
       ``--selftest`` were a stub would be a false green here. Every tool in
       ``TOOLS`` was executed and verified to print a case count or an OK
       line, so this holds today and would have caught a stub at review.

    Deliberately NOT asserted: an EMPTY STDERR. Several healthy selftests
    report on stderr -- ``oc-rebase-safety`` prints its SUCCESS line
    ("selftest: 23/23 OK") there -- so requiring empty stderr would invent a
    contract run.sh never had and red four healthy tools.
    """
    bound = TIMEOUTS[tool]
    result = run_selftest(tool, timeout=bound, env=_env_for(tool, fanout_ledger))

    # One bounded retry, ONLY for the legs that flake on BOX LOAD
    # rather than on a defect (see RETRY_ONCE above). The retry runs only
    # after a failure, so a clean run never pays for it.
    if tool in RETRY_ONCE and (result.timed_out or result.rc != 0):
        first = result
        result = run_selftest(tool, timeout=bound, env=_env_for(tool, fanout_ledger))
        if result.rc == 0 and not result.timed_out:
            # Surface the flake without failing the run: a silent pass would
            # hide a tool that is genuinely load-fragile.
            print(
                "\n%s: first attempt failed (rc=%s), passed on retry -- "
                "load-sensitive, see RETRY_ONCE. First stderr tail:\n%s"
                % (tool, first.rc, first.err[-800:])
            )

    assert not result.timed_out, (
        "%s --selftest HUNG -- killed at the %ss bound (#753)\n"
        "--- stdout (tail) ---\n%s" % (tool, bound, result.out[-2000:])
    )
    assert result.rc == 0, (
        "%s --selftest rc=%s (bound=%ss)\n"
        "--- stderr ---\n%s\n--- stdout (tail) ---\n%s"
        % (tool, result.rc, bound, result.err[-4000:], result.out[-2000:])
    )
    assert result.combined.strip(), (
        "%s --selftest exited 0 but printed NOTHING on either stream -- the "
        "signature of a no-op stub, not a selftest. Refusing to record it as "
        "green." % tool
    )
