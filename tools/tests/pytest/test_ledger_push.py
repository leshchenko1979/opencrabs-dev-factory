"""Ported: ``oc-ledger`` selftest §push / §lock — the durability tail, its two
arms, and the two structural claims that keep them honest.

Source: ``tools/state/oc-ledger:3899-4004`` (selftest lines 1129-1234): 23
``chk`` calls plus 3 ``ok || bad`` legs in the same block. Every assertion
message carries the shell leg name it replaces.

WHAT THIS BLOCK PROTECTS

    * **#619 — the waiter budget is DERIVED, not flat.** The holder's worst case
      was two bounded network pushes while the waiter's flock budget was a flat
      30 s, so a ship storm starved concurrent appends and DROPPED JOURNAL ROWS.
      Four source claims carry the fix: the budget is computed from the I/O
      bound, it stays tunable, the refusal NAMES the worst case it derived, and
      the stale ``2 * _OC_PUSH_TIMEOUT`` form is GONE (that arm asserts ZERO,
      which is what makes it discriminating — a future edit that reintroduces
      the doubled form reddens).

    * **#95 — the ``_OC_IN_LOCK`` flag brackets ONLY the work.** ``git`` used to
      run inside the fleet ledger flock, so one saturated disk froze the ledger
      for every lane (measured 2026-11-19: 25 minutes held, 18 lanes queued,
      every stamp rc 4). The flag is what DEFERS the commit into
      ``_OC_GIT_PENDING``; it must go up after the lock is held and down before
      the release, or the deferral either leaks outside the lock or never
      happens at all. The bracket ordering is asserted here, not just the count.

    * **#524 — the push has TWO arms, and each must be silent when it should
      not fire.** A COMMIT arm (backlog crosses a threshold) cannot bound the
      SLOW regime: a quiet box sits under any threshold indefinitely, so an AGE
      arm fires on the newest unpushed commit. Both are asserted against a real
      bare origin, together with the two no-ops that must stay silent (no
      origin, no upstream) — a push tail that fires on an unconfigured remote,
      or that announces itself when it declines, trains operators to ignore it.

    * **#655 — ``push_mirror`` acts on the remote's REAL state.** With a stale
      ``@{u}`` the tool reads "ahead N" while the truth is "ahead N, behind M",
      so it measures and pushes against a stale view and WARNs identically on
      every later mutation. The fetch is asserted structurally AND the
      disclosure is asserted behaviourally, because a disclosure leg that reads
      the source would pass on a message that is never printed.

    * **The concurrent-append probe.** Ten simultaneous stamps must advance
      ``max(n)`` by exactly ten with no duplicate ordinals. A lost append is a
      journal row that silently never existed; a duplicate ``n`` is two rows
      every consumer reads as one.

WHY THE PUSH LEGS ARE BEHAVIOURAL

    ``test_ledger_lock_budget.py`` already owns the BUDGET side of #619/#95/#171
    behaviourally (it holds the lock and reads the tool's own refusal), and it
    says explicitly that the shell's grep legs are what a grep CAN do. What it
    does not do — and what this module adds — is drive the push TAIL: every leg
    below stamps a real ledger whose state repo has a real bare ``origin``, and
    reads the origin's refs afterwards. ``L.git`` / ``L.init_repo`` /
    ``L.commit`` are reused; no reader is reimplemented.

OVERLAP WITH THE EXISTING SUITE (nothing below is a second copy)

    | shell leg                          | status |
    |------------------------------------|--------|
    | ``lock-wait-derived-not-flat``     | NOT PORTED — **already covered** by ``test_ledger_lock_budget.py::test_the_disclosed_worst_case_tracks_the_push_bound``, which reads the derivation out of the tool's refusal (a stronger observation than a grep). The structural count is asserted here anyway ONLY as the anti-regression grep the shell carries; see the docstring on that leg. |
    | ``lock-wait-tunable``              | NOT PORTED — covered by ``test_a_1s_waiter_budget_times_out_with_rc_4_and_names_the_budget`` (the knob is honoured, observed). |
    | ``lock-die-names-worst-case``      | NOT PORTED — covered by the same two legs (``worst case %ds`` is asserted there). |
    | ``lock-budget-not-push-shaped``    | **ported** (asserts ZERO) — a grep for an ABSENCE has no behavioural equivalent; the budget module asserts the new form, this asserts the old one is gone. |
    | ``git-tail-flag-set-under-lock``   | **ported** + bracket ordering (the shell only counts). |
    | ``git-tail-flag-cleared``          | **ported** + bracket ordering. |
    | ``push-below-threshold-*`` (3)     | **ported** (fresh fixture per leg). |
    | ``push-commit-arm-*`` (2) + ``push-carries-this-mutation`` | **ported**. |
    | ``push-age-arm-announced`` / ``push-age-arm-mirror-caught-up`` | **ported**. |
    | ``push-fetches-before-push``       | **ported** + the block's ``push-rejection-*`` disclosure legs, which are the behavioural half of the same claim. |
    | ``push-no-origin-*`` (2)           | **ported**. |
    | ``push-no-upstream-silent``        | **ported**. |
    | ``race-max-n`` / ``race-no-dup``   | **ported** — ``test_tool_wrappers.py`` mentions these names only in COMMENTS about the tool's own selftest flaking under load; it does not port the leg. This module's version is the standalone probe, with a per-stamp rc assertion the shell does not make. |

    ``test_ledger_lock_budget.py``'s #171 legs push the SKILL repo through the
    same tail. They are not duplicated: every leg here reads the STATE repo's
    origin, and the fixture keeps the skill dir remote-free so the only ``mirror``
    lines that can appear are about the state repo (the sandbox property is
    pinned by ``test_the_sandbox_ledger_is_push_inert``).

DELIBERATELY NOT PORTED

    * The shell's ``#619``/``#95`` **behavioural** commentary legs are in
      ``test_ledger_lock_budget.py`` (holding the lock, the 3 s tail hook). Not
      repeated here.
    * ``push-rejection-discloses-the-relationship`` and
      ``push-rejection-is-never-silent`` are ported but marked ADDED: they are
      ``ok || bad`` legs in this range rather than ``chk`` rows, and they exist
      to make ``push-fetches-before-push`` non-vacuous.

TIMING / MARKS

    * The push legs use a LOCAL BARE REPO as the "origin" — never a network
      remote — so no leg depends on elapsed time or on a peer lane. Nothing
      sleeps.
    * The concurrent-append probe is marked ``slow``: it launches ten tool
      processes at once, and the repository's own note (test_tool_wrappers.py)
      measures this probe losing appends under box load ~21. That is a
      contention bound, not an elapsed-time one, and it is disclosed rather than
      silently muted. It still runs (and must pass) under ``-m slow``.
    * The module is ``serial`` + ``xdist_group("battery-ledger-lock")`` — the
      SAME group ``test_ledger_lock_budget.py`` uses, deliberately. No new group
      is introduced: both modules fork ``oc-ledger`` trees that drive git against
      real repos, so the unit of mutual exclusion is the same box process
      budget, and a second name would let the two sets overlap while each looks
      correctly pinned. ``CANONICAL_GROUPS`` is unchanged.
"""

from __future__ import annotations

import itertools
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

pytestmark = [
    pytest.mark.serial,
    pytest.mark.xdist_group("battery-ledger-lock"),
]

TOOL = cf.tool_path("oc-ledger")
_SEQ = itertools.count()

# The push bound for a LOCAL bare-repo push. The sandbox's 1 s exists to make
# contention paths fail fast; here it would be a flake generator on a load-29
# box (a `git push` to a local bare repo is milliseconds, but process start-up
# under load is not). 10 s is a bound, not a widening: nothing here asserts a
# duration, and a push that needs more than 10 s to a local bare repo has hung.
PUSH_TIMEOUT = "10"


# =============================================================================
# source reads — read-only, never a rewrite of the tool
# =============================================================================
def _lines() -> list[str]:
    return TOOL.read_text(encoding="utf-8").splitlines()


def _count(needle: str) -> int:
    """Lines CONTAINING ``needle``.

    The shell builds these patterns by CONCATENATION because a literal grep
    self-matches the leg that contains it. That hazard does not exist here (this
    file is never scanned — only ``tools/state/oc-ledger`` is), so the needles
    are spelled out in full, which is the point: a reader can see what is
    counted.
    """
    return sum(1 for ln in _lines() if needle in ln)


def _extract(*names: str) -> str:
    """``awk '/^name()/,/^}$/'`` — the shell's own extraction rule.

    ONE deviation, and it is a strict improvement: a ONE-LINE function
    (``_is_git_repo() { ...; }``) is taken as that single line. Plain awk runs
    its range on to the NEXT standalone ``}`` and drags the following function
    along with it, which is harmless for bash but leaves a helper in the snippet
    that the leg never asked for and cannot see.
    """
    src = _lines()
    out = []
    for name in names:
        start = next((i for i, ln in enumerate(src) if ln.startswith(name + "()")), None)
        assert start is not None, (
            "extraction found no %r in %s — the awk range would produce an "
            "EMPTY snippet and every leg sourced from it would measure a "
            "fixture that never ran (#70)" % (name, TOOL))
        first = src[start]
        if first.rstrip().endswith("}"):
            out.append(first)
            continue
        end = next((j for j in range(start + 1, len(src)) if src[j] == "}"), None)
        assert end is not None, "unterminated function %r" % (name,)
        out.extend(src[start:end + 1])
    return "\n".join(out) + "\n"


# =============================================================================
# fixture — the sandbox pair plus a real bare origin on the STATE repo
# =============================================================================
@pytest.fixture
def mirror(ledger_sandbox, scratch):
    """``ledger_sandbox`` with a bare ``origin`` on the STATE repo, upstream set.

    The skill dir is left WITHOUT a remote on purpose: the subject is the state
    repo's tail, and a skill push would add lines (and time) with nothing to
    assert. ``ledger_sandbox`` guarantees that shape, and
    ``test_the_sandbox_ledger_is_push_inert`` pins it.
    """
    state = Path(ledger_sandbox.state)
    # A UNIQUE bare origin per leg: a shared path would make the second
    # fixture push into the first one's history and be rejected
    # non-fast-forward, so `mirror_head` would read a STRANGER's ref.
    origin = Path(scratch) / "push" / ("origin-%d.git" % next(_SEQ))
    origin.mkdir(parents=True, exist_ok=True)
    L.git(origin, "init", "-q", "--bare", "-b", "main")
    L.git(state, "remote", "add", "origin", str(origin))
    L.git(state, "push", "-q", "--set-upstream", "origin", "HEAD")
    br = L.git(state, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert br, "the sandbox state repo has no branch — the fixture is wrong"

    def mirror_head() -> str:
        return L.git(origin, "rev-parse", "refs/heads/%s" % br,
                     check=False).stdout.strip()

    def local_head() -> str:
        return L.head(state)

    # Facts hung on a Node that wraps the sandbox's path and carries the SAME
    # `.state` / `.skill` / `.ledger` attributes, so this fixture is a drop-in
    # for ``ledger_sandbox`` in every leg below.
    return cf.Node(ledger_sandbox.path, state=state, skill=ledger_sandbox.skill,
                   ledger=ledger_sandbox.ledger, origin=origin, branch=br,
                   mirror_head=mirror_head, local_head=local_head)


def _env(**over) -> dict:
    """Per-leg knobs layered over the sandbox's env.

    ``OC_LEDGER_LOCK_WAIT`` is raised from the sandbox's 1 s: that value is the
    contention-stress default for the BUDGET legs, and ten concurrent stamps
    (or one under load 29) would die rc 4 for a reason this module is not
    asserting. 30 s is the tool's own scale, not a widened test bound.
    """
    base = {
        "OC_LEDGER_PUSH_TIMEOUT": PUSH_TIMEOUT,
        "OC_LEDGER_LOCK_WAIT": "30",
        "OC_LEDGER_GIT_TAIL_WAIT": "20",
    }
    base.update({k: str(v) for k, v in over.items()})
    return base


def _stamp(mirror, run_tool, what, **knobs):
    return run_tool([str(TOOL), "stamp", "note", what], timeout=180,
                    env=_env(**knobs))


def _mirror_lines(res) -> list[str]:
    """The tail's own disclosures: the decision line and the push result line."""
    return [ln for ln in res.combined.splitlines()
            if ln.startswith("mirror-due") or ln.startswith("mirror: state")]


# =============================================================================
# #619 / #95 — the structural claims
# =============================================================================
# lock-wait-derived-not-flat / lock-wait-tunable / lock-die-names-worst-case are
# NOT re-ported: test_ledger_lock_budget.py asserts all three by HOLDING the lock
# and reading the tool's own refusal, which is strictly more than a grep can
# observe. What is left is the one claim with no behavioural form — the ABSENCE
# of the stale doubled budget — plus the flag bracket, which the shell only
# counts.
STRUCTURE = [
    ("$(( 2 * _OC_PUSH_TIMEOUT", 0, "lock-budget-not-push-shaped",
     "the 2x-push derivation is a STALE premise since #95 took git out of the "
     "lock; ZERO is the discriminating count — one hit means the doubled form "
     "is back and every waiter sleeps 90 s for half-second work (#81 from the "
     "other side)"),
    ("_OC_IN_LOCK=1", 1, "git-tail-flag-set-under-lock",
     "the flag goes UP in exactly one place, inside with_lock, after the flock "
     "is held"),
    ("_OC_IN_LOCK=0", 2, "git-tail-flag-cleared",
     "exactly two: the module-level initialisation and the one clear inside "
     "with_lock, before the release"),
]


@pytest.mark.parametrize("needle, want, name, why", STRUCTURE,
                         ids=[row[2] for row in STRUCTURE])
def test_the_lock_budget_and_the_in_lock_flag_have_one_shape(needle, want, name,
                                                             why):
    """Shell legs 3909/3911/3913: counts that must not drift.

    A count is a weak assertion on its own, which is why the two flag legs are
    followed by an ORDERING leg below — the count says "one set, two clears",
    the ordering says they bracket the right statement.
    """
    got = _count(needle)
    assert got == want, (
        "[%s] want %d line(s) containing %r in %s, got %d — %s"
        % (name, want, needle, TOOL.name, got, why))


def test_the_in_lock_flag_brackets_only_the_work_under_the_flock():
    """ADDED (the shell counts; this reads the ORDER).

    ``with_lock`` holds ``flock`` on fd 9, sets ``_OC_IN_LOCK=1``, runs the work
    with ``9>&-`` (the #641 close — a child would otherwise inherit the lock),
    clears the flag, releases, and only THEN runs the deferred git tail. Each
    edge matters:

    * flag set BEFORE the work, or a helper's ``git_state_commit`` commits
      inside the fleet flock — the #95 defect;
    * ``9>&-`` ON the work invocation, or a spawned child keeps the lock alive
      after the parent exits (#641: 19+ minutes measured);
    * flag cleared AFTER the work and BEFORE ``exec 9>&-``, so nothing the tail
      does is mistaken for in-lock work and nothing in-lock escapes the queue;
    * the tail call AFTER the release, or git is back under the lock.
    """
    body = _extract("with_lock")

    def find(pred, label):
        for i, ln in enumerate(body.splitlines()):
            if pred(ln):
                return i
        raise AssertionError(
            "with_lock no longer contains %s — the #95/#641 ordering this leg "
            "asserts cannot be observed:\n%s" % (label, body))

    flock_i = find(lambda ln: ln.strip().startswith("flock -w"),
                   "the flock acquisition")
    on_i = find(lambda ln: ln.strip() == "_OC_IN_LOCK=1", "_OC_IN_LOCK=1")
    work_i = find(lambda ln: ln.strip() == '"$@" 9>&-; rc=$?',
                  'the work invocation "$@" 9>&-')
    off_i = find(lambda ln: ln.strip() == "_OC_IN_LOCK=0", "_OC_IN_LOCK=0")
    close_i = find(lambda ln: ln.strip() == "exec 9>&-", "the fd release")
    tail_i = find(lambda ln: ln.strip() == "_oc_flush_git_tail",
                  "the deferred git-tail call")

    assert flock_i < on_i, (
        "[git-tail-flag-set-under-lock] the flag goes up BEFORE the lock is "
        "held — a commit made while waiting would be queued as if deferred")
    assert on_i < work_i, (
        "[git-tail-flag-set-under-lock] the flag must precede the work, or "
        "git_state_commit commits INSIDE the fleet flock (#95)")
    assert work_i < off_i, (
        "[git-tail-flag-cleared] the flag is cleared before the work finishes "
        "— work that runs with the flag down commits under the lock")
    assert off_i < close_i, (
        "[git-tail-flag-cleared] the flag must be cleared before the fd is "
        "released, so the bracket and the lock end together")
    assert close_i < tail_i, (
        "#95 REGRESSED: _oc_flush_git_tail runs before the ledger lock is "
        "released — git is back under the fleet flock:\n%s" % body)


# =============================================================================
# the push tail against a real bare origin
# =============================================================================
def test_below_threshold_and_young_is_silent_and_the_mirror_does_not_move(
        mirror, run_tool):
    """Shell legs (a): three ``chk`` calls, and the third is the CONTROL.

    ``really-behind`` is what makes the other two mean anything: if local were
    not ahead of the mirror there would be nothing to push, and "the mirror did
    not move" would be true of a tail that never ran. The stamp must still land
    its row — a silent arm is a DECISION, not a failure.
    """
    state = Path(mirror.state)
    for i in (1, 2, 3):
        L.commit(state, "bl-%d" % i)
    before = mirror.mirror_head()
    assert before, "the fixture's origin carries no branch — upstream push failed"

    res = _stamp(mirror, run_tool, "push-under",
                 OC_LEDGER_PUSH_MIN="99", OC_LEDGER_PUSH_MAX_AGE="99999")
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-1200:])

    assert _mirror_lines(res) == [], (
        "[push-below-threshold-silent] backlog 4 < min 99 and the newest commit "
        "is seconds old < 99999 s, so NEITHER arm fires; the tail must say "
        "nothing at all:\n%s" % res.combined[-1200:])
    assert mirror.mirror_head() == before, (
        "[push-below-threshold-mirror-unmoved] the origin moved "
        "(%s -> %s) although no arm fired"
        % (before, mirror.mirror_head()))
    assert mirror.mirror_head() != mirror.local_head(), (
        "[push-below-threshold-really-behind] local HEAD == the mirror, so the "
        "'did not move' assertion above is VACUOUS — the fixture never had "
        "anything to push")
    # the row landed: a declining arm must still write
    assert L.field(mirror.ledger, "what") == "push-under", (
        "the stamp reported rc 0 but wrote no row — a green verdict over an "
        "empty ledger is the from-zero defect")


def test_the_commit_arm_announces_catches_up_and_carries_this_mutation(
        mirror, run_tool):
    """Shell legs (b): threshold set AT the pre-stamp backlog, so the stamp's own
    commit is what crosses it.

    ``push-carries-this-mutation`` is the sharp one: the pushed blob must contain
    the text THIS stamp wrote. A push that shipped a stale tree would satisfy
    "the refs match" and lose the row it was supposed to publish.
    """
    state = Path(mirror.state)
    for i in (1, 2, 3):
        L.commit(state, "bl-%d" % i)
    backlog = L.rev_count(state, "@{u}..HEAD")
    assert backlog > 0, "the fixture has no backlog — the commit arm cannot fire"
    before = mirror.mirror_head()

    res = _stamp(mirror, run_tool, "push-threshold",
                 OC_LEDGER_PUSH_MIN=str(backlog), OC_LEDGER_PUSH_MAX_AGE="99999")
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-1200:])

    due = [ln for ln in res.combined.splitlines()
           if ln.startswith("mirror-due: state backlog=")]
    assert due, (
        "[push-commit-arm-announced] the stamp's commit should have crossed the "
        "threshold %d (backlog was %d before it); the tail said nothing:\n%s"
        % (backlog, backlog, res.combined[-1200:]))
    assert "commit(s)" in due[0] and ">= %d" % backlog in due[0], (
        "[push-commit-arm-announced] the decision line must name the backlog and "
        "the threshold it crossed, or an operator cannot tell which arm fired: "
        "%r" % due[0])

    assert mirror.mirror_head() == mirror.local_head(), (
        "[push-commit-arm-mirror-caught-up] origin %s != local %s — the arm "
        "announced a push that did not land:\n%s"
        % (mirror.mirror_head(), mirror.local_head(), res.combined[-1200:]))
    assert mirror.mirror_head() != before, (
        "control: the origin was already at local HEAD, so the assertion above "
        "is vacuous — nothing was pushed")

    blob = L.git(mirror.origin, "show",
                 "refs/heads/%s:workers-ledger.json" % mirror.branch,
                 check=False).stdout
    assert "push-threshold" in blob, (
        "[push-carries-this-mutation] the pushed workers-ledger.json does not "
        "contain the row this stamp wrote — the tail shipped a STALE tree")


def test_the_age_arm_announces_the_age_it_measured_and_catches_up(mirror,
                                                                 run_tool):
    """Shell leg (c): below threshold, but the newest unpushed commit is older
    than the bound. ``MAX_AGE=0`` makes any backlog qualify, so no sleep.

    The decision line must carry the MEASURED age (``newest Ns old``), not a
    constant: the age arm's whole job is to bound the slow regime, and an
    announcement that does not say how old the backlog is cannot be audited.
    """
    state = Path(mirror.state)
    L.commit(state, "bl-age")

    res = _stamp(mirror, run_tool, "push-age",
                 OC_LEDGER_PUSH_MIN="99", OC_LEDGER_PUSH_MAX_AGE="0")
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-1200:])

    m = re.search(r"mirror-due: state backlog=(\d+) commit\(s\), newest (\d+)s "
                  r"old \(>= 0s\)", res.combined)
    assert m, (
        "[push-age-arm-announced] want 'mirror-due: state backlog=N commit(s), "
        "newest Ns old (>= 0s)', got:\n%s" % res.combined[-1200:])
    assert int(m.group(1)) > 0, (
        "[push-age-arm-announced] the reported backlog is %s — an age arm that "
        "fires on an empty backlog is measuring nothing" % m.group(1))

    assert mirror.mirror_head() == mirror.local_head(), (
        "[push-age-arm-mirror-caught-up] origin %s != local %s — the age arm "
        "announced a push that did not land:\n%s"
        % (mirror.mirror_head(), mirror.local_head(), res.combined[-1200:]))


def test_no_origin_is_silent_and_the_stamp_still_succeeds(mirror, run_tool):
    """Shell leg (d): no origin -> a silent no-op, never a line, never a failure.

    Both halves, and the row: an unconfigured remote is the state repo's DEFAULT
    shape, so this path runs on every lane that has not wired a mirror. A line
    here would be noise on every stamp; a failure here would make durability
    configuration a precondition for writing the journal.
    """
    state = Path(mirror.state)
    L.git(state, "remote", "remove", "origin")
    L.commit(state, "bl-noorigin")

    res = _stamp(mirror, run_tool, "push-noorigin",
                 OC_LEDGER_PUSH_MIN="1", OC_LEDGER_PUSH_MAX_AGE="0")
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-1200:])
    assert _mirror_lines(res) == [], (
        "[push-no-origin-silent] with no origin the tail must say NOTHING "
        "(backlog min/age were both forced to fire, so silence here is the "
        "no-origin guard, not an unmet threshold):\n%s" % res.combined[-1200:])

    again = run_tool([str(TOOL), "stamp", "note", "push-noorigin2"], timeout=180,
                     env=_env())
    assert again.rc == 0, (
        "[push-no-origin-stamp-still-ok] a second stamp without an origin must "
        "still succeed, rc=%s\n%s" % (again.rc, again.combined[-1200:]))
    assert L.field(mirror.ledger, "what") == "push-noorigin2", (
        "[push-no-origin-stamp-still-ok] rc 0 but the row is missing — the "
        "durability tail failed the write it exists to protect")


def test_an_origin_without_upstream_is_silent(mirror, run_tool):
    """Shell leg (e): an origin but NO upstream tracking -> silent no-op.

    Nothing to measure against: ``@{u}`` does not resolve, so the backlog is
    unknown. The tail must decline SILENTLY rather than guess — an
    ``origin``-only configuration is what a hand-wired mirror looks like before
    the first ``push -u``.
    """
    state = Path(mirror.state)
    L.git(state, "remote", "remove", "origin")
    L.git(state, "remote", "add", "origin", str(mirror.origin))
    L.commit(state, "bl-noupstream")
    # vacuity guard: there IS a backlog and an origin, so only the missing
    # upstream can explain the silence.
    assert L.rev_count(state, "@{u}..HEAD") == -1, (
        "the fixture still resolves @{u} — this leg would then assert the "
        "threshold arms, not the no-upstream guard")
    assert L.git(state, "remote", "get-url", "origin",
                 check=False).returncode == 0, "the fixture has no origin"

    res = _stamp(mirror, run_tool, "push-noupstream",
                 OC_LEDGER_PUSH_MIN="1", OC_LEDGER_PUSH_MAX_AGE="0")
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-1200:])
    assert _mirror_lines(res) == [], (
        "[push-no-upstream-silent] with no @{u} the tail must say NOTHING:\n%s"
        % res.combined[-1200:])


# =============================================================================
# #655 — push_mirror acts on the remote's REAL state
# =============================================================================
def test_push_mirror_fetches_before_it_pushes():
    """Shell leg 3954: the fetch is INSIDE ``push_mirror``, and it is there ONCE.

    Structural because the defect is a MISSING call: without the fetch the tool
    measures and pushes against a stale ``@{u}``, so it reads "ahead 1" when the
    truth is "ahead 1, behind 1", the push is rejected non-fast-forward, and it
    WARNs identically on every later mutation. The behavioural half is the next
    leg — this one only proves the call has not been dropped from the source.
    """
    body = _extract("push_mirror")
    fetches = [ln for ln in body.splitlines() if "fetch -q origin" in ln]
    assert len(fetches) == 1, (
        "[push-fetches-before-push] want exactly 1 'fetch -q origin' inside "
        "push_mirror, got %d — without it the tool measures and pushes against "
        "a stale @{u} (#655):\n%s" % (len(fetches), body))
    # and it must precede the push, or it is decoration.
    idx_fetch = next(i for i, ln in enumerate(body.splitlines())
                     if "fetch -q origin" in ln)
    idx_push = next((i for i, ln in enumerate(body.splitlines())
                     if "git -C \"$dir\" push" in ln), None)
    assert idx_push is not None, (
        "push_mirror no longer contains its push invocation:\n%s" % body)
    assert idx_fetch < idx_push, (
        "[push-fetches-before-push] the fetch runs AFTER the push — the tool "
        "would still be acting on a stale view:\n%s" % body)


def _diverged_pair(root: Path):
    """Two clones of one bare origin, diverged, with ``d``'s tracking ref STALE.

    Reproduces the #655 measurement exactly: ``w`` advances the remote, ``d``
    commits locally and then has its ``refs/remotes/origin/main`` wound BACK, so
    ``d`` believes it is strictly ahead while it is actually behind as well.
    """
    root.mkdir(parents=True, exist_ok=True)
    origin = root / "origin.git"
    origin.mkdir(parents=True, exist_ok=True)
    L.git(origin, "init", "-q", "--bare", "-b", "main")
    L.git(origin, "symbolic-ref", "HEAD", "refs/heads/main")

    w = L.init_repo(root / "w", files={"f": "base\n"})
    L.git(w, "remote", "add", "origin", str(origin))
    pushed = L.git(w, "push", "-q", "origin", "main")
    assert pushed.returncode == 0, (
        "the fixture could not seed its origin: %s" % pushed.stderr)

    d = root / "d"
    cloned = L.git(root, "clone", "-q", str(origin), str(d))
    assert cloned.returncode == 0, (
        "the fixture could not clone its origin: %s" % cloned.stderr)
    for r in (w, d):
        L.git(r, "config", "user.email", "sa@sb")
        L.git(r, "config", "user.name", "sa")
        L.git(r, "config", "commit.gpgsign", "false")

    # the remote advances under d's feet
    L.write(w / "r", "remote")
    L.git(w, "add", "r")
    L.git(w, "commit", "-q", "-m", "remote")
    L.git(w, "push", "-q", "origin", "main")
    # d commits locally, without fetching
    L.write(d / "l", "local")
    L.git(d, "add", "l")
    L.git(d, "commit", "-q", "-m", "local")
    # STALE tracking ref: d believes it is strictly ahead
    L.git(d, "update-ref", "refs/remotes/origin/main",
          L.head(d, "HEAD~1"))
    return origin, d


@pytest.fixture
def pm_snippet(scratch):
    """``push_mirror`` + its ``_is_git_repo`` helper, sourced in a subprocess.

    The helper is extracted WITH it: a snippet missing ``_is_git_repo`` makes
    ``push_mirror`` return immediately and the disclosure legs would then pass on
    output that was never produced (#70).
    """
    d = Path(scratch) / "pm"
    d.mkdir(parents=True, exist_ok=True)
    snip = d / "pm_fn.sh"
    snip.write_text(_extract("_is_git_repo", "push_mirror"), encoding="utf-8")
    return snip


def test_a_rejected_push_discloses_the_ahead_behind_relationship(
        scratch, run_tool, pm_snippet):
    """Shell legs ``push-rejection-discloses-the-relationship`` /
    ``push-rejection-is-never-silent``: ADDED legs (``ok || bad``, not ``chk``).

    These are what make ``push-fetches-before-push`` non-vacuous. The fetch is
    best-effort, so the push can still be REJECTED — and a rejection must (1)
    say the relationship (``[ahead N behind M]``), which is what distinguishes a
    moved remote from a real divergence, and (2) never be silent.

    The silence leg deliberately does NOT key on git's wording: measured, the
    same divergence prints "non-fast-forward" on one path and "fetch first" on
    the other, so a wording assertion would redden on a git-version change
    rather than on a defect. It keys on the tool's own ``rc=`` line instead.
    """
    origin, d = _diverged_pair(Path(scratch) / "div")
    script = (
        '_OC_PUSH_TIMEOUT=20\n'
        'oc_log_extra() { :; }\n'
        '. "$SNIPPET"\n'
        'push_mirror "$DIR" probe\n')
    res = run_tool(["bash", "-c", script], timeout=120,
                   env={"SNIPPET": str(pm_snippet), "DIR": str(d)})
    assert "command not found" not in res.combined, (
        "the extracted snippet is incomplete — push_mirror's helper is missing, "
        "so this leg measured a function that returned immediately (#70):\n%s"
        % res.combined[-1200:])

    assert re.search(r"\[ahead \d+ behind \d+\]", res.combined), (
        "[push-rejection-discloses-the-relationship] a diverged remote must be "
        "reported with the ahead/behind counts — that is what tells an operator "
        "'moved remote, retries' from 'real divergence, owes a human merge':\n%s"
        % res.combined[-1200:])
    assert "mirror push failed for probe rc=1" in res.combined, (
        "[push-rejection-is-never-silent] the rejection must carry the tool's "
        "own rc line (not git's wording, which moves between git versions):\n%s"
        % res.combined[-1200:])


# =============================================================================
# the concurrent-append probe
# =============================================================================
@pytest.mark.slow
def test_ten_concurrent_stamps_advance_max_n_by_ten_with_no_duplicates(
        ledger_sandbox, run_tool):
    """Shell legs ``race-max-n`` / ``race-no-dup`` — the concurrency contract.

    Ten simultaneous stamps: ``max(n)`` must advance by EXACTLY ten and no
    ordinal may repeat. The two failure modes are different defects:

    * a LOST append is a journal row that silently never existed — the row a
      lane's claim or landing record was riding on;
    * a DUPLICATE ``n`` is two rows every consumer reads as one, so a closure
      scan sees a single claim where there were two.

    WHY ``slow``. This launches ten tool processes at once. ``test_tool_wrappers.py``
    records the measurement: this probe loses appends at box load ~21 and is
    clean at load 8, i.e. the bound is CONTENTION, not elapsed time. Marking it
    ``slow`` keeps it out of the fast gate while leaving it runnable — the honest
    option, versus widening the lock budget until a lost append stops showing.

    What this port ADDS over the shell: the shell backgrounds the stamps and
    ``wait``s, ignoring each rc. Here every rc is checked, so a stamp that died
    on a lock timeout is reported as ITSELF rather than surfacing later as a
    mysteriously short max.
    """
    # The base is 0 for an EMPTY log, not ``L.max_n``'s -1 sentinel: the shell
    # computes ``$((before + 10))`` from jq's ``max``, which is null on an empty
    # array and coerces to 0 in shell arithmetic. Using -1 here would demand 9.
    ns_before = [n for n in L.ns(ledger_sandbox.ledger) if isinstance(n, int)]
    before = max(ns_before) if ns_before else 0

    def one(i: int):
        return run_tool([str(TOOL), "stamp", "note", "race-%d" % i],
                        timeout=180, env=_env())

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(one, range(10)))

    bad = [(i, r.rc, r.combined[-400:]) for i, r in enumerate(results) if r.rc != 0]
    assert bad == [], (
        "concurrent stamps failed before the invariant could be measured: %r"
        % (bad,))

    after = L.max_n(ledger_sandbox.ledger)
    assert after == before + 10, (
        "[race-max-n] want max(n) == %d (before %d + 10), got %d — %d append(s) "
        "were LOST, i.e. journal rows that silently never existed"
        % (before + 10, before, after, (before + 10) - after))

    ns = L.ns(ledger_sandbox.ledger)
    assert len(ns) == len(set(ns)), (
        "[race-no-dup] duplicate ordinal(s) in the log: %r — two rows every "
        "consumer reads as one"
        % ([n for n in set(ns) if ns.count(n) > 1],))
