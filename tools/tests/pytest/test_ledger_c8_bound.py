"""Ported: ``oc-ledger`` selftest §C8 continued — the bound, the widening,
and the self-commit skips.

Source: ``tools/state/oc-ledger:3150-3364`` (selftest lines 380-594). These are
the C8 arms that ``test_ledger_c8.py`` does NOT carry: its fixture threads one
skill/state pair through nine sub-cases, while every leg here needs its OWN
dirs — the bound arms seed a shared ledger with 2099 rows on purpose, so a bound
leg reading that ledger would measure the pollution instead of its own
condition. That is why this is a second module rather than more tests in the
first.

WHAT THIS MODULE PROTECTS — four mechanisms, each two-sided

1. THE SELF-COMMIT SKIPS (#531, legs g/h/i). A commit made by the SYNCING
   SESSION with no ``Issue-Ref`` trailer cannot be named by the entry it
   publishes — its sha does not exist when the entry is written — so it is
   excluded structurally, and the exclusion is DISCLOSED (an unreported skip is
   an exclusion list nobody can audit). But the skip must not swallow real work:
   a self-commit that DOES carry ``Issue-Ref`` stays LISTED, and one whose
   SUBJECT merely mentions an issue in prose is still skipped. A subject is
   prose; the trailer is the contract the fleet keys on.

2. THE LEDGER BOUND (#651, legs j/k/l). The subject anchor cannot see a bump
   whose version commit is LANE-authored — it carries no ``: oc-ledger sync``
   form — so the sync finds a clean tree, mints the skill-bump row and commits
   nothing. Measured at the real v0.4.268 sync: the subject predicate returned
   the v0.4.265 sync and the range spanned 51 commits where the true window was
   13. The bound fires on a STALE anchor and corrects the range; its control
   proves it does NOT fire on a FRESH one (an unconditional bound narrows a
   correct range against the wrong instant). The past-head guard is the third
   direction: a row stamped after EVERY commit would filter the range to empty,
   and an empty range reads as a clean check while verifying nothing.

3. THE ENTRY SET THE RANGE SPANS (#94, legs m/n/o). When the range is BOUNDED,
   reading only ``## v$v`` is correct — earlier windows are excluded by
   construction. When the bound does NOT fire the range is unbounded and can
   span several windows, so a commit shipped under an earlier window is dated in
   THAT window's entry and testing only ``## v$v`` flags it for lacking a ship
   date it has. Widening is CONDITIONAL and both directions are asserted: the
   widening must silence the earlier-window commit AND still list one named
   nowhere, and on a BOUNDED range it must NOT widen — widening there would hide
   a genuine miss, trading a false positive for a false negative.

4. THE DISCLOSURES THEMSELVES are asserted by their own wording, not by a
   substring that some OTHER line in the output could satisfy. The shell measured
   this: ``*"v0.4.8"*`` stayed green under the mutation that neutered the
   widening, because the older straddle note already prints the window list. So
   the widen note's own sentence and its rendered window list are matched
   together, and the guidance must be a READABLE list (``v0.4.2, v0.4.8, v0.4.9``)
   rather than the raw space-separated ``$spans``.

FIXTURE NOTE
    ``bound_fixture`` reproduces the shell's ``c8mk``/``c8commit`` pair: a
    skill+state repo pair whose ledger starts at 0.4.1 with no workers, plus a
    backdating helper. Backdating is what makes the window arithmetic true
    without sleeping. Every leg gets its own pair.

DELIBERATELY NOT PORTED
    Nothing in this range. The one arm the shell itself declares unportable is
    in the ``state_tracked_audit`` block, not here (see
    ``test_ledger_structural.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

SYNCED_BY = "oc-ledger sync"


@pytest.fixture
def bound(scratch, run_tool):
    """``c8mk`` — a fresh skill+state repo pair per call, plus a ``sync`` helper.

    The ledger starts at 0.4.1 with no workers and is its own file, never the
    sandbox ledger: the shell measured both and only this one is read by the
    check.
    """
    seq = [0]

    def make():
        seq[0] += 1
        root = Path(scratch) / ("c8b%d" % seq[0])
        skill = L.make_skill(root / "skill", version="0.4.1")
        L.make_battery(skill / "tools" / "tests" / "battery-last.json")
        L.init_repo(skill, branch="main")

        state = root / "state"
        state.mkdir(parents=True, exist_ok=True)
        ledger = state / "workers-ledger.json"
        ledger.write_text(json.dumps({
            "current_skill_version": "0.4.1",
            "meta": {"skill_version": "0.4.1", "current_skill_version": "0.4.1"},
            "updated_at": "2026-01-01T00:00:00Z",
            "workers": [],
            "events": [],
        }), encoding="utf-8")
        L.init_repo(state, branch="main")

        def sync(version: str):
            return run_tool(
                [str(TOOL), "sync", "--version", version, "--why", "selftest-c8"],
                timeout=180,
                env={"OC_LEDGER": str(ledger),
                     "OC_SKILL_DIR": str(skill),
                     "OC_DEPLOY_STATE_DIR": str(state)})

        sync.skill = skill
        sync.state = state
        sync.ledger = ledger

        def bump(rows):
            """Append ``skill-bump`` rows: ``[(n, iso_t, what), ...]``."""
            doc = json.loads(ledger.read_text(encoding="utf-8"))
            for n, t, what in rows:
                doc["events"].append({"n": n, "t": t, "by": SYNCED_BY,
                                      "kind": "skill-bump", "what": what})
            ledger.write_text(json.dumps(doc), encoding="utf-8")

        sync.bump = bump
        return sync

    return make


def _release(sync, version: str, changelog_section: str):
    """Move the skill to ``version`` with an explicit CHANGELOG section.

    ``L.set_skill_version`` writes a generic receipt; these legs assert on
    entries that NAME specific commits, so the section body is a parameter.
    """
    md = sync.skill / "SKILL.md"
    lines = md.read_text(encoding="utf-8").splitlines(True)
    md.write_text("".join(
        ("version: %s\n" % version) if ln.startswith("version:") else ln
        for ln in lines), encoding="utf-8")
    with open(sync.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v%s\n%s\n" % (version, changelog_section))


# =============================================================================
# (g)(h)(i) — the self-commit skip, three ways
# =============================================================================
def test_a_self_commit_with_no_issue_ref_is_skipped_and_the_skip_is_disclosed(bound):
    """``c8-selfcommit-no-issue-listed`` + ``c8-selfskip-undisclosed`` (#531).

    A commit by the SYNCING SESSION naming no issue cannot be named by the entry
    it publishes — its sha does not exist when the entry is written. So it is
    excluded structurally, and the exclusion is REPORTED: an unreported skip is
    an exclusion list nobody can audit.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")

    (sync.skill / "law.txt").write_text("w\n", encoding="utf-8")
    L.git(sync.skill, "add", "-A")
    L.commit(sync.skill, "law: fixture cycle commit (no issue ref)",
             body=["Session-Id: %s" % cf.LEDGER_ACTOR])
    self_sha = L.short(sync.skill)

    _release(sync, "0.4.7", "c8 receipt")
    res = sync("0.4.7")

    assert "unnamed: %s" % self_sha not in res.combined, (
        "[c8-selfcommit-no-issue-listed] this session's own no-issue commit %s "
        "is listed as unnamed — its sha did not exist when the entry was "
        "written, so it cannot be named:\n%s" % (self_sha, res.combined[-1500:]))
    assert "skipped as made by THIS syncing session" in res.combined, (
        "[c8-selfskip-undisclosed] the self-skip happened but is not disclosed "
        "— an unreported skip cannot be audited:\n%s" % (res.combined[-1500:],))


def test_a_self_commit_that_names_an_issue_stays_listed(bound):
    """``c8-selfcommit-with-issue-hidden`` — the TIGHTENING (#531).

    Without this leg the skip above trades a false positive for a false NEGATIVE
    on exactly the commits it exists to surface: a self-commit that ships real
    work carries ``Issue-Ref`` and is published, so it must stay listed.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")

    (sync.skill / "fix.txt").write_text("v\n", encoding="utf-8")
    L.git(sync.skill, "add", "-A")
    L.commit(sync.skill, "fix(tools): a self-commit that ships real work (#780)",
             body=["Session-Id: %s" % cf.LEDGER_ACTOR, "Issue-Ref: #780"])
    shipped_sha = L.short(sync.skill)

    _release(sync, "0.4.8", "c8 receipt")
    res = sync("0.4.8")

    assert "unnamed: %s" % shipped_sha in res.combined, (
        "[c8-selfcommit-with-issue-hidden] a self-commit carrying Issue-Ref is "
        "real shipped work and must stay listed; it vanished:\n%s"
        % (res.combined[-1500:],))


def test_a_subject_mentioning_an_issue_is_still_skipped(bound):
    """``c8-prose-mention-still-listed`` + ``c8-prose-mention-skip-undisclosed``.

    CORRECTED 2026-09-25 (HQ report, verified first-hand): a self-commit whose
    SUBJECT merely mentions an issue in prose carries no ``Issue-Ref`` trailer
    and IS skipped. Measured on HQ's v0.4.250 sync — ``b1307038`` "law: name the
    four #547 commits bundled in v0.4.249 (C8 leg)" was flagged although it fixes
    nothing; it NAMES that window's commits. A subject is prose, the trailer is
    the contract.

    Discriminating: pre-fix the subject test saw ``#`` and kept it listed.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")

    (sync.skill / "prose.txt").write_text("w\n", encoding="utf-8")
    L.git(sync.skill, "add", "-A")
    L.commit(sync.skill,
             "law: name the four #781 commits bundled elsewhere (C8 leg)",
             body=["Session-Id: %s" % cf.LEDGER_ACTOR])
    prose_sha = L.short(sync.skill)

    _release(sync, "0.4.9", "c8 receipt")
    res = sync("0.4.9")

    assert "unnamed: %s" % prose_sha not in res.combined, (
        "[c8-prose-mention-still-listed] a subject that merely MENTIONS an "
        "issue carries no Issue-Ref trailer and must be skipped; it was "
        "listed:\n%s" % (res.combined[-1500:],))
    assert "skipped as made by THIS syncing session" in res.combined, (
        "[c8-prose-mention-skip-undisclosed] the skip is not disclosed:\n%s"
        % (res.combined[-1500:],))


# =============================================================================
# (j)(k)(l) — the ledger bound, three directions
# =============================================================================
def test_a_stale_anchor_bounds_the_range_and_names_the_correction(bound):
    """``c8-651-bound-note-missing`` + ``-true-window-commit-lost`` +
    ``-earlier-window-still-swept`` + ``-straddle-note-should-be-suppressed-when-corrected``.

    A lane-authored bump mints a skill-bump row at 09:00 with no sync commit;
    three earlier-window commits sit behind the subject anchor. Without the bound
    all four are swept in. With it: only the true-window commit is listed, the
    earlier three are gone, the straddle note goes QUIET (the bound corrected
    it), and the correction is NAMED.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor",
             date="2026-09-27T06:00:00 +0000")
    for i in (1, 2, 3):
        L.commit(sync.skill, "fix(tools): #77%d earlier window" % i,
                 date="2026-09-27T07:0%d:00 +0000" % i)
    L.commit(sync.skill,
             "skill v0.4.4: Duty 4+6 cycle — lane authored, no sync commit",
             date="2026-09-27T09:00:00 +0000")

    (sync.skill / "true.txt").write_text("n\n", encoding="utf-8")
    L.git(sync.skill, "add", "-A")
    L.commit(sync.skill, "fix(tools): #780 the true window",
             date="2026-09-27T09:30:00 +0000")
    true_sha = L.short(sync.skill)

    sync.bump([(9101, "2026-09-27T09:00:00Z", "v0.4.4 — lane-authored bump")])
    _release(sync, "0.4.2", "c8 receipt names nothing")

    res = sync("0.4.2")

    assert "BOUNDED to commits after v0.4.4" in res.combined, (
        "[c8-651-bound-note-missing] the bound fired but is not announced, so a "
        "reader cannot tell the range was narrowed:\n%s"
        % (res.combined[-2000:],))
    assert "unnamed: %s" % true_sha in res.combined, (
        "[c8-651-true-window-commit-lost] the commit inside the true window "
        "(%s) is not listed — the bound dropped real work:\n%s"
        % (true_sha, res.combined[-2000:]))
    for i in (1, 2, 3):
        assert "#77%d earlier window" % i not in res.combined, (
            "[c8-651-earlier-window-still-swept] an earlier-window commit "
            "(#77%d) is still listed after the bound narrowed the range:\n%s"
            % (i, res.combined[-2000:]))
    assert "MORE THAN ONE version window" not in res.combined, (
        "[c8-651-straddle-note-should-be-suppressed-when-corrected] the "
        "straddle note still fires although the bound CORRECTED the range — a "
        "correction that leaves the old warning up teaches readers to ignore "
        "it:\n%s" % (res.combined[-2000:],))


def test_a_fresh_anchor_does_not_fire_the_bound(bound):
    """``c8-651-bound-fired-on-fresh-anchor`` + ``c8-651-fresh-anchor-range-broken``.

    CONTROL. The newest skill-bump row is OLDER than the anchor commit, so the
    anchor is not stale. An unconditional bound would narrow a correct range
    against the wrong instant — measured, it widened a 1-commit range to 2 and
    would double-report the previous window's work.
    """
    sync = bound()
    sync.bump([(9201, "2026-09-27T05:00:00Z", "v0.4.1 — old row")])
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor",
             date="2026-09-27T06:00:00 +0000")

    (sync.skill / "k.txt").write_text("k\n", encoding="utf-8")
    L.git(sync.skill, "add", "-A")
    L.commit(sync.skill, "fix(tools): #790 the only bundled commit")
    only_sha = L.short(sync.skill)

    _release(sync, "0.4.2", "c8 receipt names nothing")
    res = sync("0.4.2")

    assert "BOUNDED to commits after" not in res.combined, (
        "[c8-651-bound-fired-on-fresh-anchor] the bound fired although the "
        "newest skill-bump row predates the anchor — an unconditional bound "
        "narrows a correct range against the wrong instant:\n%s"
        % (res.combined[-2000:],))
    assert "unnamed: %s" % only_sha in res.combined, (
        "[c8-651-fresh-anchor-range-broken] the one commit in the fresh window "
        "(%s) is not listed:\n%s" % (only_sha, res.combined[-2000:]))


def test_a_row_stamped_past_head_is_refused_so_the_range_is_not_emptied(bound):
    """``c8-651-past-head-guard-note-missing`` +
    ``-bound-applied-past-head-would-empty-the-range`` +
    ``-past-head-guard-emptied-the-range``.

    A row stamped after EVERY commit in the repo would filter the range to
    EMPTY, and an empty range reads as a clean check while verifying nothing —
    #485's shape from the opposite direction. The bound must be REFUSED, the
    subject anchor kept, and the refusal said.

    Not hypothetical: leg (e) of the C8 block injects exactly such rows.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor",
             date="2026-09-27T06:00:00 +0000")

    (sync.skill / "l.txt").write_text("l\n", encoding="utf-8")
    L.git(sync.skill, "add", "-A")
    L.commit(sync.skill, "fix(tools): #791 the bundled commit")
    bundled_sha = L.short(sync.skill)

    sync.bump([(9301, "2099-01-01T00:00:00Z", "v0.4.9 — future row")])
    _release(sync, "0.4.2", "c8 receipt names nothing")

    res = sync("0.4.2")

    assert "AFTER every commit in the repo" in res.combined, (
        "[c8-651-past-head-guard-note-missing] the past-head guard fired but is "
        "not announced:\n%s" % (res.combined[-2000:],))
    assert "BOUNDED to commits after" not in res.combined, (
        "[c8-651-bound-applied-past-head-would-empty-the-range] the bound was "
        "applied against a row stamped past HEAD — that filters the range to "
        "EMPTY and an empty range reads clean while verifying nothing:\n%s"
        % (res.combined[-2000:],))
    assert "unnamed: %s" % bundled_sha in res.combined, (
        "[c8-651-past-head-guard-emptied-the-range] the guard emptied the range "
        "— the bundled commit (%s) is not listed:\n%s"
        % (bundled_sha, res.combined[-2000:]))


# =============================================================================
# (m)(n)(o) — #94, the entry set the range spans
# =============================================================================
def test_an_unbounded_range_reads_the_earlier_window_entries(bound):
    """``c8-94-earlier-window-entry-ignored`` + ``-unnamed-commit-lost`` +
    ``-widen-note-missing`` + ``-widen-note-names-no-window`` +
    ``-guidance-window-list-unreadable`` + ``-warn-misnames-its-scope``.

    The existence gate and the naming test both read ``## v$v``. When the range
    is UNBOUNDED it can span several windows, so a commit shipped under an
    earlier window is dated in THAT window's entry — and testing only
    ``## v$v`` flags it for lacking a ship date it actually has. The false
    positive is structural: it can only fire when the bound fails, and the bound
    failing is exactly what makes the range span more than one window.

    The shape is reachable only through the past-head guard (a bump row stamped
    after every commit leaves the range unbounded while rows newer than the
    anchor still enumerate windows) — that is the real incident shape: a lane
    publishes the bump row before the commit lands, or the clocks disagree. So
    the fixture builds it the same way.

    The POSITIVE CONTROL is in the same fixture: a commit named NOWHERE is still
    listed. Without it, the widening could have been "silence everything" and
    the earlier-window leg would pass on a check that reads no entries at all.

    The disclosures are matched by their OWN wording, together with the rendered
    window list. The shell measured why: a bare ``*"v0.4.8"*`` match stayed green
    under the mutation that neutered the widening, because the older straddle
    note already prints the window list.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor",
             date="2026-09-27T06:00:00 +0000")
    L.commit(sync.skill, "fix(tools): #781 named in the earlier window",
             date="2026-09-27T07:00:00 +0000")
    earlier_sha = L.short(sync.skill)
    L.commit(sync.skill, "fix(tools): #782 named NOWHERE at all",
             date="2026-09-27T07:30:00 +0000")
    nowhere_sha = L.short(sync.skill)

    sync.bump([(9401, "2026-09-27T07:05:00Z", "v0.4.8 — in-range row"),
               (9402, "2099-01-01T00:00:00Z", "v0.4.9 — past-head row")])

    md = sync.skill / "SKILL.md"
    lines = md.read_text(encoding="utf-8").splitlines(True)
    md.write_text("".join(
        ("version: 0.4.2\n") if ln.startswith("version:") else ln
        for ln in lines), encoding="utf-8")
    with open(sync.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("# fixture changelog\n\n## v0.4.2\nc8 receipt names nothing\n"
                 "\n## v0.4.8\nc8 earlier-window receipt names %s\n" % earlier_sha)

    res = sync("0.4.2")
    out = res.combined

    assert "unnamed: %s" % earlier_sha not in out, (
        "[c8-94-earlier-window-entry-ignored] a commit dated in an earlier "
        "window's entry (%s) is flagged for lacking a ship date it has two "
        "windows back:\n%s" % (earlier_sha, out[-2500:]))
    assert "unnamed: %s" % nowhere_sha in out, (
        "[c8-94-unnamed-commit-lost] the positive control failed — a commit "
        "named NOWHERE (%s) is not listed, so the widening silenced everything:"
        "\n%s" % (nowhere_sha, out[-2500:]))
    assert "UNBOUNDED and spans more than one version window" in out, (
        "[c8-94-widen-note-missing] the widening happened but is not disclosed "
        "— a scope change nobody can see is how a check starts reporting on "
        "something other than what its message says:\n%s" % (out[-2500:],))
    assert "more than one version window (v0.4.2 + v0.4.8 v0.4.9)" in out, (
        "[c8-94-widen-note-names-no-window] the widen note does not carry its "
        "own window list — the older straddle note already prints windows, so a "
        "bare window match proves nothing:\n%s" % (out[-2500:],))
    assert "one of v0.4.2, v0.4.8, v0.4.9" in out, (
        "[c8-94-guidance-window-list-unreadable] the guidance renders the raw "
        "space-separated list, leaving the reader unable to tell one window "
        "from two:\n%s" % (out[-2500:],))
    assert ("none of the entries for the version windows this UNBOUNDED range "
            "spans") in out, (
        "[c8-94-warn-misnames-its-scope] the WARN claims the '## v0.4.2' entry "
        "is the only place a ship date exists, sending the reader to edit a "
        "file that already names the commit:\n%s" % (out[-2500:],))


def test_a_bounded_range_does_not_widen(bound):
    """``c8-94-bounded-note-missing`` + ``-bounded-range-widened-anyway`` +
    ``-widen-note-fired-on-a-bounded-range``.

    The other direction of #94. Here the bound FIRES, so earlier windows are
    excluded from the range by construction; a commit IN the range that is named
    only in an earlier entry must STILL be flagged. Widening unconditionally
    would silence exactly the miss this leg exists to surface, trading a false
    positive for a false negative.
    """
    sync = bound()
    L.commit(sync.skill, "skill v0.4.1: oc-ledger sync — fixture anchor",
             date="2026-09-27T06:00:00 +0000")

    sync.bump([(9501, "2026-09-27T06:30:00Z", "v0.4.5 — in-range row")])
    L.commit(sync.skill,
             "fix(tools): #783 in the bounded window, named only earlier",
             date="2026-09-27T07:00:00 +0000")
    missed_sha = L.short(sync.skill)

    md = sync.skill / "SKILL.md"
    lines = md.read_text(encoding="utf-8").splitlines(True)
    md.write_text("".join(
        ("version: 0.4.2\n") if ln.startswith("version:") else ln
        for ln in lines), encoding="utf-8")
    with open(sync.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("# fixture changelog\n\n## v0.4.2\nc8 receipt names nothing\n"
                 "\n## v0.4.5\nc8 earlier receipt names %s\n" % missed_sha)

    res = sync("0.4.2")
    out = res.combined

    assert "BOUNDED to commits after" in out, (
        "[c8-94-bounded-note-missing] the bound fired but is not announced:\n%s"
        % (out[-2000:],))
    assert "unnamed: %s" % missed_sha in out, (
        "[c8-94-bounded-range-widened-anyway] a commit in the BOUNDED window "
        "(%s) is named only in an earlier entry and must still be flagged; the "
        "widening silenced it:\n%s" % (missed_sha, out[-2000:]))
    assert "UNBOUNDED and spans" not in out, (
        "[c8-94-widen-note-fired-on-a-bounded-range] the widen note fired on a "
        "bounded range, where earlier windows are excluded by construction:\n%s"
        % (out[-2000:],))
