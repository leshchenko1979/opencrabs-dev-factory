"""Pure ``run_selftest <tool>`` wrapper sections, ported from run.sh.

SCOPE (factory #197, worker A). These are the battery sections whose ENTIRE
body is "run this tool's ``--selftest``, assert rc 0". Everything else stays in
run.sh until its owning worker ports it:

  * bespoke shell sections with real logic ................... worker B
  * harness self-tests (lock/chunk/cgroup/scratch/receipt) ... worker D
  * cache .................................................... worker E

One function, one parameter per tool, so ``-k`` and ``-m`` select individual
tools::

    pytest tools/tests/pytest/test_tool_wrappers.py -k oc-seal
    pytest tools/tests/pytest/test_tool_wrappers.py -m "not slow"

THE CONTRACT, MEASURED NOT ASSUMED
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
  3. Timeouts are per-tool and measured, so a slow-but-legitimate selftest
     cannot red spuriously -- the defect run.sh:294-300 documents.

TIMEOUTS ARE PER-TOOL AND MEASURED (probe: 2026-11-27, this worktree)
---------------------------------------------------------------------
A blanket short bound would red a slow-but-legitimate selftest: run.sh's own
1800 s default exists because the longest measured section is 296.5 s.

Two measurements, because they differ by up to 5x: a quiet-box probe and the
same tools under the load of a real pytest run on a shared box (several sibling
worktrees were running their own suites). ``oc-wt`` is 21 s quiet and 118 s
loaded; ``oc-upstream-delta`` 12 s quiet and 60 s loaded. Bounds are sized
against the LOADED figure, with >= 2x headroom on it, because the loaded figure
is the regime this module actually runs in. A bound sized on the quiet number
would have red `oc-wt` at 118 s against 180 s -- a spurious failure, which is
the exact defect run.sh:294-300 documents.

The tools that take minutes carry ``@pytest.mark.slow`` so ``-m "not slow"``
deselects them rather than stalling a quick gate.

EVERY LEG IS `serial` IN ONE `xdist_group` -- see the measured note beside
``WRAPPER_GROUP``. A ``--selftest`` is a process TREE, this box's cgroup caps
``pids`` at 64, and two concurrent legs already peak at 41, so overlapping legs
fork-fail rather than run faster. ``-n N`` therefore runs them in order on one
worker; ``-n 0`` is unchanged. The bound is a property of the box, not of the
tools, so the marker is the honest statement of it.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# (tool, timeout_seconds) -- timeout is a hard per-call bound, REQUIRED by the
# fixture (an omittable bound is a bound that gets omitted; #753 is that hang).
# Measured wall time is in the comment so the next reader can audit the
# headroom instead of trusting the number.
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
    # oc-notify-fanout belongs HERE, not with the fast tools: measured 266 s
    # standalone and 223 s under load, i.e. SLOWER than oc-gate. It first
    # carried a 300 s bound, which is 1.13x headroom -- one loaded box away
    # from a spurious red, the exact defect run.sh:294-300 documents. 600 s is
    # 2.3x and the slow marker keeps it out of a quick gate.
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
# WHY EVERY LEG IS `serial` + ONE xdist_group: the pids cap, measured
# ---------------------------------------------------------------------------
# A `--selftest` is not one process. Every tool here forks git, mktemp, grep,
# jq and often its own sub-selftests, so ONE leg is a process TREE, and the
# trees of two legs overlap the instant they run concurrently.
#
# This box runs under a cgroup with `pids.max = 64` (`ulimit -u` is 15532, so
# the LIMIT THAT BITES is the cgroup, not the login limit -- read the former,
# never the latter). Measured 2026-11-27 in this worktree, sampling
# pids.current once a second while running JUST TWO legs (`oc-ledger` and
# `oc-wt`, `-n 2`): PEAK 41 of 64. Two legs already sit at 64% of the cap, so
# any third concurrent leg is over it and `fork()` starts returning EAGAIN.
#
# That is not a theory, it is what a `-n 4` run of this module did: 17 of 33
# legs reddened, and 17 of them carried
#     error: cannot fork() for maintenance: Resource temporarily unavailable
# (git's own message; `rev-list`, `gc`, `pack-objects`, `symbolic-ref` the
# same). The tools were healthy -- `oc-ledger` reported PASS=737 and failed 4
# legs on fork errors alone; `oc-wt`, `oc-upstream-delta` and `oc-branch-sweep`
# failed the same way. It reads as seventeen broken tools and is ONE stated cap,
# which is the defect test_cgroup.py::test_caps_scale_with_worker_count already
# names for the shell harness ("read as EIGHT broken tools rather than one
# stated cap").
#
# The remedy is the repo's OWN documented convention for exactly this case
# (pytest.ini § xdist_group USAGE): a `serial` marker states "must not overlap"
# and a shared `xdist_group` is the mechanism that makes the claim true under
# `-n N`, by pinning every member onto the SAME worker, in order. Under `-n 0`
# both are inert, so the serial fallback needs no changes -- the acceptance bar
# pytest.ini sets.
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
# stream. Measured 2026-11-27:
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

@pytest.mark.parametrize("tool", PARAMS)
def test_tool_selftest(run_selftest, fanout_ledger, tool):
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
