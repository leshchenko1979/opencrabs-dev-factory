"""Ported: ``oc-ledger`` selftest §30-32 — ``commit-pending``.

Source: ``tools/state/oc-ledger:3583-3664`` (selftest lines 813-894) — the
``commit-pending`` block: 6 ``chk`` calls plus 20 ``ok || bad`` legs. Every
assertion message carries the shell name it replaces.

WHAT THIS MODULE PROTECTS
    ``commit-pending`` persists the state ledger and sweeps the runtime
    artifacts a lane leaves behind. It is also the one verb that PUSHES, so
    every leg here is about not lying about what happened:

    * (#116) A REFUSED COMMIT IS NOT A CLEAN TREE. ``did`` counts only SUCCESS,
      so a git refusal — a held ``.git/index.lock`` — used to fall through to
      ``sweep: clean — nothing pending`` at rc 0, with the row demonstrably
      staged and HEAD unmoved. Three outcomes must stay separable: COMMITTED /
      NOTHING-PENDING / FAILED (rc 4). The POSITIVE control is the dirty-ledger
      leg, so a probe that simply could not write reddens THAT instead of
      passing this one.
    * (#722) ``commit-pending --help`` USED TO RUN THE SWEEP. The dispatcher
      passed the flag straight into ``cmd_commit_pending``, which had no help
      arm, so ``--help`` fell through as an ignored positional and the sweep ran
      anyway — committing the state ledger and PUSHING both mirrors. Help must
      be a READ. The leg is two-sided with the SAME probe: NEGATIVE (help leaves
      HEAD alone) and POSITIVE (a dirtied ledger does advance HEAD), because a
      probe that cannot see a write would otherwise pass the negative as calm.
    * The sweeps are asserted by the FILENAME each one carries AND by the file
      being clean afterwards. "It printed something" is not the claim; the file
      being in the commit is.
    * The append-only carve-out's disclosure sentence is CONDITIONAL. It must
      appear when the sweep stages the multi-actor shared log and must NOT
      appear on a plain sweep — an unconditional sentence is noise on every
      commit, which is how a disclosure stops being read.

    * (#508/#80) THE AUTO-COMMIT TAIL COVERS THE TRACKED NAMESPACE, NOT THE
      LEDGER ALONE. Before #508 ``git_state_commit`` staged
      ``workers-ledger.json`` ONLY, while the whitelist sat inside
      ``commit-pending --bundle`` — a verb NO cron invokes — so ``tools.log`` sat
      modified-uncommitted in the live state dir for days. Then #177 removed the
      per-stamp sweep again, so a stamp must now leave tracked files DIRTY and
      only an explicit ``--bundle`` sweeps them. Both halves are asserted, and
      ``baseline.json`` is the POSITIVE CONTROL throughout: it is still in
      ``STATE_TRACKED_PATHS``, so a green result cannot be vacuous.
    * (#80) ``tools.log`` is NOT swept any more — the real state repo untracked
      and ``.gitignore``d it, so the mechanism must not claim it. The fixture
      carries the same ``.gitignore`` and the leg asserts the NEW contract
      (ignored, never staged, and STILL ON DISK — rotation, never deletion).
    * (32c) A configured origin receives the skill branch. The bare fixture
      remote stands in for GitHub, per the offline-selftest rule; the leg
      asserts the remote RECEIVED a commit, not merely that the tool said so.

DELIBERATELY NOT PORTED
    * ``commit-pending-clean`` (the first leg) is folded into the help test's
      negative half and into ``test_a_dirty_ledger_is_committed``'s pre-state:
      it asserts the same fixture reports clean, and a separate leg would need
      its own repo to avoid depending on sweep order.
    * ``selftest --help`` (#722) IS ported, but it lives here rather than in an
      e2e module because it is BOUNDED (``timeout 10``) and guarded by
      ``OC_LEDGER_SELFTEST=1``: on a regression the guard makes it FAIL instead
      of recursing into a nested battery. Marked slow — it shells out to the
      tool's own entry point.
"""

from __future__ import annotations

import json

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")


@pytest.fixture
def pending(ledger_sandbox, run_tool):
    """``commit-pending`` bound to the sandbox ledger/state/skill triple.

    ``ledger_sandbox`` already hands us a git-backed state dir, a skill dir with
    ``tools/tests/`` tracked, and the fast-contention env (``OC_LEDGER_LOCK_WAIT``
    / ``OC_LEDGER_PUSH_TIMEOUT`` = 1 s), so no per-call env is needed here.
    """
    def call(*args):
        return run_tool([str(TOOL), "commit-pending", *args], timeout=180)

    call.sandbox = ledger_sandbox
    return call


def _append_event(ledger, n, what):
    doc = L.read_json(ledger)
    doc.setdefault("events", []).append(
        {"n": n, "t": "x", "by": "tool", "kind": "note", "what": what})
    ledger.write_text(json.dumps(doc), encoding="utf-8")


def test_a_dirty_ledger_is_committed_and_the_file_is_left_clean(pending):
    """``commit-pending-sweep`` + ``commit-pending-left-dirty``.

    The POSITIVE control for the refused-commit leg below: a dirty ledger DOES
    commit. Without it, a probe that could not write at all would make the
    refusal leg pass by accident.
    """
    sb = pending.sandbox
    clean = pending()
    assert "clean — nothing pending" in clean.combined, (
        "[commit-pending-clean] a fresh sandbox did not report clean:\n%s"
        % (clean.combined[-900:]))

    _append_event(sb.ledger, 900, "stray")
    res = pending()
    assert "state ledger committed" in res.combined, (
        "[commit-pending-sweep] a dirty ledger did not commit:\n%s"
        % (res.combined[-900:],))
    assert res.rc == 0, (
        "[commit-pending-sweep] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-900:]))
    assert not L.porcelain(sb.state, "workers-ledger.json").strip(), (
        "[commit-pending-left-dirty] workers-ledger.json is still dirty after "
        "a reported commit — the row was staged and never written")


def test_a_refused_commit_is_rc4_and_never_reads_as_clean(pending):
    """``commit-pending-refused-*`` (#116).

    A held ``.git/index.lock`` makes git refuse, and the old code counted only
    SUCCESS — so it fell through to ``sweep: clean — nothing pending`` at rc 0
    while the row sat staged and HEAD had not moved. Three outcomes must stay
    separable: COMMITTED / NOTHING-PENDING / FAILED, and rc 4 is FAILED.

    Runs through the DISPATCHER (``oc-ledger commit-pending``), so the rc-4 arm
    doubles as the propagation arm for the ship-audit chain swallowing it.
    """
    sb = pending.sandbox
    _append_event(sb.ledger, 902, "refused-probe")
    head_before = L.head(sb.state)

    lock = sb.state / ".git" / "index.lock"
    lock.write_text("", encoding="utf-8")
    try:
        res = pending()
    finally:
        lock.unlink(missing_ok=True)

    assert res.rc == 4, (
        "[commit-pending-refused-rc4] rc=%s, want 4 — a refused commit is its "
        "own outcome, not a success and not a clean tree:\n%s"
        % (res.rc, res.combined[-1200:]))
    assert "sweep: FAILED" in res.combined, (
        "[commit-pending-refused-says-FAILED] the failure is not announced:\n%s"
        % (res.combined[-1200:],))
    assert "clean — nothing pending" not in res.combined, (
        "[commit-pending-refused-must-not-say-clean] the run reports a clean "
        "tree while the row is demonstrably staged:\n%s"
        % (res.combined[-1200:],))
    assert L.head(sb.state) == head_before, (
        "[commit-pending-refused-head-unmoved] HEAD moved during a refused "
        "commit: %s -> %s" % (head_before, L.head(sb.state)))
    assert L.porcelain(sb.state, "workers-ledger.json").strip(), (
        "[commit-pending-refused-row-still-pending] the row is no longer dirty "
        "— either it was committed after all, or the probe never staged it")


def test_a_retry_after_the_lock_is_gone_does_commit(pending):
    """``commit-pending-after-lock-released-rc0``.

    The other half of #116: the failure must not be silently RETRIED into a
    false clean. Once the lock is gone the SAME row commits, which proves it was
    genuinely pending and the refusal was about the lock, not the content.
    """
    sb = pending.sandbox
    _append_event(sb.ledger, 903, "retry-probe")
    lock = sb.state / ".git" / "index.lock"
    lock.write_text("", encoding="utf-8")
    try:
        refused = pending()
    finally:
        lock.unlink(missing_ok=True)
    assert refused.rc == 4, (
        "fixture: the held lock did not produce a refusal (rc=%s)\n%s"
        % (refused.rc, refused.combined[-900:]))

    retry = pending()
    assert retry.rc == 0, (
        "[commit-pending-after-lock-released-rc0] rc=%s, want 0 — with the "
        "lock gone the row commits, proving it was pending all along\n%s"
        % (retry.rc, retry.combined[-900:]))
    assert not L.porcelain(sb.state, "workers-ledger.json").strip(), (
        "[commit-pending-after-lock-released-rc0] the retry reported success "
        "and left the row dirty")


def test_help_is_a_read_not_a_sweep(pending):
    """``commit-pending-help-*`` (#722) — two-sided, same probe.

    ``--help`` used to run the sweep: it committed the state ledger and pushed
    both mirrors. The negative half asserts HEAD is untouched; the positive half
    dirties the ledger and asserts HEAD DOES move, so a probe that cannot see a
    write reddens the positive instead of passing the negative as calm.
    """
    sb = pending.sandbox
    head_before = L.head(sb.state)

    helped = pending("--help")
    assert helped.rc == 0, (
        "[commit-pending-help-rc] rc=%s, want 0\n%s"
        % (helped.rc, helped.combined[-900:]))
    assert "usage: oc-ledger commit-pending" in helped.combined, (
        "[commit-pending-help-text] the usage line is missing:\n%s"
        % (helped.combined[-900:],))
    assert L.head(sb.state) == head_before, (
        "[commit-pending-help-is-read] HEAD moved on --help — the flag ran the "
        "sweep instead of answering usage: %s -> %s"
        % (head_before, L.head(sb.state)))

    # the POSITIVE control: the probe CAN see a write
    _append_event(sb.ledger, 904, "help-probe")
    pending()
    assert L.head(sb.state) != head_before, (
        "[commit-pending-help-probe-cannot-see-writes] a dirtied ledger did "
        "not advance HEAD, so the negative assertion above proves nothing")


@pytest.mark.slow
def test_selftest_help_is_bounded_and_guarded(ledger_sandbox, run_tool):
    """``selftest-help-rc`` + ``selftest-help-text`` (#722).

    ``parse_global`` consumes the bare ``selftest`` token as a GLOBAL flag, which
    makes the dispatcher's own arm UNREACHABLE and leaves the arm before the
    SELFTEST branch as the only live one. On a regression this invocation would
    start a NESTED battery, so it is bounded by a timeout and guarded by
    ``OC_LEDGER_SELFTEST=1`` — the guard makes a regression FAIL the leg instead
    of recursing into one.

    Marked slow: it shells out to the tool's own entry point.
    """
    res = run_tool([str(TOOL), "selftest", "--help"], timeout=20,
                   env={"OC_LEDGER_SELFTEST": "1"})
    assert res.rc == 0, (
        "[selftest-help-rc] rc=%s, want 0 — a bounded help call must not "
        "launch a battery\n%s" % (res.rc, res.combined[-900:]))
    assert "usage: oc-ledger selftest" in res.combined, (
        "[selftest-help-text] the usage line is missing; first line was %r"
        % (res.combined.splitlines()[:1],))


def test_the_bundle_sweeps_each_runtime_artifact_class_and_leaves_it_clean(pending):
    """The ``commit-pending-*-sweep`` family (v0.4.63 through #514).

    Each sweep exists because a class of file was MISSING from the bundle
    whitelist while something else kept reading it — a parked harvest's only
    resume record sat untracked, a glossary-declared ``*-state.md`` class was
    carried by a hand-run commit rather than the mechanism. So each leg asserts
    the FILENAME in the output AND that the file is clean afterwards: printing a
    name is not carrying the file.

    ``baseline.json`` / ``journal/`` / ``reviews/`` are the ``state runtime
    files`` class; ``*-harvest-state.md`` and ``*-ship-state.md`` are the lane
    state records class (#514 widened ``*-harvest-state.md`` to the glossary's
    ``*-state.md``).
    """
    sb = pending.sandbox
    probes = [
        # (relative path, body, needle, clean-path, sweep-name, left-dirty-name)
        ("baseline.json", '{"sha":"fixture"}', "baseline.json", "baseline.json",
         "commit-pending-baseline-sweep", "commit-pending-baseline-left-dirty"),
        ("journal/sweep-probe.json", '{"probe":true}', "journal",
         "journal", "commit-pending-journal-sweep", None),
        ("341-harvest-state.md", "# probe", "lane state records committed",
         "341-harvest-state.md", "commit-pending-harvest-state-sweep",
         "commit-pending-harvest-state-left-dirty"),
        ("444-ship-state.md", "# probe", "lane state records committed",
         "444-ship-state.md", "commit-pending-ship-state-sweep",
         "commit-pending-ship-state-left-dirty"),
        ("reviews/2026probe/p.md", "probe", "reviews", "reviews",
         "commit-pending-reviews-sweep", "commit-pending-reviews-left-dirty"),
    ]
    for rel, body, needle, clean_path, name, dirty_name in probes:
        target = sb.state / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

        res = pending("--bundle")
        assert needle in res.combined, (
            "[%s] the sweep did not report %r for %s:\n%s"
            % (name, needle, rel, res.combined[-1200:]))
        # The shell splits each sweep into two chk names: the sweep reports the
        # file, and the file is clean afterwards. Printing a name is not carrying
        # the file, so the second leg is the one with teeth.
        assert not L.porcelain(sb.state, clean_path).strip(), (
            "[%s] [%s] %s is still dirty — the sweep named it and did not carry "
            "it" % (dirty_name or name, name, clean_path))


def test_the_skill_runtime_artifacts_are_swept(pending):
    """``commit-pending-bundle``.

    The skill-side bundle (``tools/tests/battery-last.json`` and friends) is a
    SEPARATE class from the state dir: pre-root-fix the shell leg leaked the
    battery receipt's untracked dirt from an earlier block, so the fixture here
    writes a fresh one.
    """
    sb = pending.sandbox
    receipt = sb.skill / "tools" / "tests" / "battery-last.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text('{"verdict":"PASS","fail":0,"probe":"bundle"}',
                       encoding="utf-8")

    res = pending("--bundle")
    assert "runtime artifacts" in res.combined, (
        "[commit-pending-bundle] the skill runtime artifact was not swept:\n%s"
        % (res.combined[-1200:],))
    assert not L.porcelain(sb.skill, "tools/tests/battery-last.json").strip(), (
        "[commit-pending-bundle] tools/tests/battery-last.json is still dirty")


def test_the_append_only_disclosure_is_conditional(pending):
    """``commit-pending-smoke-verdicts-*`` + ``commit-pending-plain-sweep`` +
    ``commit-pending-disclosure-unconditional``.

    ``smoke-verdicts.log`` is TRACKED, was in no list, and is MULTI-ACTOR (33
    distinct ``actor=`` values over 333 rows measured), so staging it owes the
    append-only carve-out's disclosure sentence.

    The control is the other half: a sweep that does NOT stage the shared log
    must not carry the sentence. An unconditional sentence is noise on every
    commit, which is exactly how a disclosure stops being read.
    """
    sb = pending.sandbox
    log = sb.state / "smoke-verdicts.log"
    log.write_text("verdict=PASS actor=deadbeef-dead-4dead-8dead-deaddeadbeef\n",
                   encoding="utf-8")

    shared = pending("--bundle")
    assert "smoke-verdicts.log" in shared.combined, (
        "[commit-pending-smoke-verdicts-sweep] the shared log was not "
        "reported:\n%s" % (shared.combined[-1200:],))
    assert not L.porcelain(sb.state, "smoke-verdicts.log").strip(), (
        "[commit-pending-smoke-verdicts-left-dirty] the shared log is still "
        "dirty after a reported sweep")
    assert "disclose foreign rows" in L.log_subject(sb.state, 1), (
        "[commit-pending-smoke-verdicts-disclosed] the commit staged a "
        "multi-actor append-only log with no disclosure of foreign rows: %r"
        % (L.log_subject(sb.state, 1),))

    # the CONTROL: a plain sweep of a lane-state record must NOT carry it
    (sb.state / "555-ship-state.md").write_text("# probe", encoding="utf-8")
    plain = pending("--bundle")
    assert "lane state records committed" in plain.combined, (
        "[commit-pending-plain-sweep] the plain sweep did not report its own "
        "record:\n%s" % (plain.combined[-1200:],))
    assert "disclose foreign rows" not in L.log_subject(sb.state, 1), (
        "[commit-pending-disclosure-unconditional] the disclosure sentence "
        "rode a commit that staged no shared log — an unconditional sentence "
        "is noise on every commit: %r" % (L.log_subject(sb.state, 1),))


# =============================================================================
# 32c — the mirror push, and #508/#80 — the tracked-namespace tail
# =============================================================================
def test_a_configured_origin_receives_the_skill_branch(pending, run_tool):
    """``commit-pending-mirror-push`` + ``commit-pending-mirror-received``.

    v0.4.50: a configured origin receives the skill branch. The second leg is
    the one that matters — "the tool said it pushed" is a claim, and a bare
    fixture remote's own HEAD is the receipt. Without it, a push that no-ops on
    a missing ref would read as success forever.

    The bare remote stands in for GitHub: the offline-selftest rule forbids
    reaching the network from the battery.
    """
    sb = pending.sandbox
    mirror = sb.path / "mirror.git"

    res = run_tool(["git", "init", "-q", "--bare", str(mirror)], timeout=60)
    assert res.rc == 0, "fixture: bare remote init failed\n%s" % res.combined[-600:]

    res = run_tool(["git", "-C", str(sb.skill), "remote", "add", "origin",
                    str(mirror)], timeout=60)
    assert res.rc == 0, "fixture: remote add failed\n%s" % res.combined[-600:]

    receipt = sb.skill / "tools" / "tests" / "battery-last.json"
    receipt.write_text('{"verdict":"PASS","fail":0,"mirror":"probe"}',
                       encoding="utf-8")

    res = pending("--bundle")
    assert "mirror: skill pushed" in res.combined, (
        "[commit-pending-mirror-push] the tool did not report pushing to the "
        "configured origin:\n%s" % (res.combined[-1500:],))

    res = run_tool(["git", "-C", str(mirror), "rev-parse", "--verify", "HEAD"],
                   timeout=60)
    assert res.rc == 0, (
        "[commit-pending-mirror-received] the bare remote has no HEAD — the "
        "tool reported a push and the remote received nothing:\n%s"
        % (res.combined[-900:]))


def test_a_stamp_leaves_tracked_files_dirty_and_only_bundle_sweeps_them(
        pending, run_tool):
    """``auto-commit-probe-still-dirty`` + ``auto-commit-control-not-dirty`` +
    ``auto-commit-tail-still-sweeps`` + ``commit-pending-bundle-inert``.

    #508 made the auto-commit tail cover the TRACKED namespace instead of the
    ledger alone; #177 then took the per-stamp sweep OUT again, so a stamp must
    leave tracked files dirty and only an explicit ``--bundle`` carries them.
    Both halves are asserted because either alone is satisfiable by the other
    defect: a tail that never sweeps passes the first, a tail that sweeps on
    every stamp passes the second.

    ``baseline.json`` is the POSITIVE CONTROL. It is still in
    ``STATE_TRACKED_PATHS``, so if the sweep stopped running entirely the
    ``bundle-inert`` leg reddens — a green result here cannot be vacuous.
    """
    sb = pending.sandbox

    # The fixture carries the REAL repo's .gitignore: tools.log is ignored there
    # since #80, and a fixture that tracked it would assert a contract the live
    # tree no longer has.
    (sb.state / ".gitignore").write_text("tools.log\ntools.log.*\n",
                                         encoding="utf-8")
    res = run_tool(["git", "-C", str(sb.state), "add", ".gitignore"], timeout=60)
    assert res.rc == 0, "fixture: git add .gitignore failed\n%s" % res.combined[-600:]
    res = run_tool(["git", "-C", str(sb.state), "-c", "user.email=t@t",
                    "-c", "user.name=t", "commit", "-q", "-m",
                    "probe: gitignore tools.log (#80)"], timeout=60)
    assert res.rc == 0, "fixture: gitignore commit failed\n%s" % res.combined[-600:]

    with (sb.state / "tools.log").open("a", encoding="utf-8") as fh:
        fh.write("probe\n")
    assert not L.porcelain(sb.state, "tools.log").strip(), (
        "[auto-commit-probe-still-dirty] tools.log is NOT ignored in the "
        "fixture, so the vacuity guard would pass for the wrong reason (#80)")

    (sb.state / "baseline.json").write_text('{"probe":"#80 control"}\n',
                                            encoding="utf-8")
    assert L.porcelain(sb.state, "baseline.json").strip(), (
        "[auto-commit-control-not-dirty] the control was not dirty to begin "
        "with, so a green sweep result below would prove nothing")

    stamp = run_tool([str(TOOL), "stamp", "note", "#508/#80 auto-commit probe"],
                     timeout=180)
    assert stamp.rc == 0, "fixture: the probe stamp failed\n%s" % stamp.combined[-900:]

    assert L.porcelain(sb.state, "baseline.json").strip(), (
        "[auto-commit-tail-still-sweeps] the STAMP committed baseline.json — "
        "#177 removed the per-stamp sweep, so the tail is back")

    pending("--bundle")
    assert not L.porcelain(sb.state, "baseline.json").strip(), (
        "[commit-pending-bundle-inert] baseline.json is still dirty after "
        "--bundle — the sweep stopped running, and it is a listed path, so this "
        "is not a whitelist question")

    res = run_tool(["git", "-C", str(sb.state), "ls-files", "--error-unmatch",
                    "tools.log"], timeout=60)
    assert res.rc != 0, (
        "[auto-commit-tools-log-tracked] the ignored log was COMMITTED — the "
        "#80 regression, where the mechanism claims a file the repo untracked")
    assert "probe" in (sb.state / "tools.log").read_text(encoding="utf-8"), (
        "[auto-commit-tools-log-lost] the log was DELETED, not rotated — an "
        "ignored file must survive on disk")
