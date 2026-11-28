"""Ported: ``oc-ledger`` selftest §22b-C8 — the C8 naming check on ``sync``.

Source: ``tools/state/oc-ledger:3053-3364`` (selftest lines 283-594) — 3 ``chk``
calls plus 12 ``ok || bad`` legs in the same block. Every assertion message
carries the shell name it replaces.

WHAT THIS MODULE PROTECTS
    ``sync`` must record a version, and the CHANGELOG entry for that version is
    supposed to NAME the commits it publishes. Two different gates sit here and
    they are NOT the same severity:

    * The EXISTENCE gate is HARD (``die 6``): an entry with no ``## vX.Y.Z``
      section is a refusal. That arm lives in ``test_ledger_sync.py``.
    * The NAMING check only LISTS the commits the entry does not name, and it
      must never refuse. The range is other lanes' work and carries untrailered
      law commits by design — a hard gate here would let one lane's landing
      block the fleet's version record at HQ's boundary.

    Both directions of the naming check are asserted, because a one-way test
    cannot tell a working check from one that never fires: an unnamed commit
    must be listed, and the same commit NAMED in the entry must be silent.

    The four legs that carry the real risk:

    * AN UNDERIVABLE ANCHOR must be SKIPPED OUT LOUD and must not read as clean.
      "I could not compare" and "I compared and found nothing" are different
      verdicts, and only one of them is a reason to stop reading.
    * THE ANCHOR MUST BE A SYNC, not merely a commit whose subject starts
      ``skill v``. A bump-only commit is created NEWER than the last sync; a
      prefix-only pattern anchors on it, truncating the range to empty and
      reading CLEAN. That is the UNDER-flag direction — the dangerous one,
      because a silent pass is indistinguishable from a healthy tree.
    * A MULTI-WINDOW range must SAY so rather than presenting a two-window span
      as one, with the CONTROL asserted first: with no such rows the note must
      be ABSENT, or it fires always and carries no information.
    * THE SWEEPER'S OWN BOOKKEEPING is skipped by a marker the tool WRITES (not
      a hand-maintained list) and the skip is DISCLOSED. An unreported exclusion
      is an exclusion list nobody can audit, which is how this class of gate
      dies quietly.

FIXTURE NOTE
    The shell builds ``$T/c8skill`` and ``$T/c8state`` as two git repos and
    threads them through nine sub-cases with a ``c8sync`` helper. Here each test
    builds its own pair from ``L.make_skill`` + ``L.init_repo``, so the legs are
    independent and xdist-safe. The C8 block's ledger is its OWN file, never the
    sandbox ledger — the shell measured both and only this one is read by the
    check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")


@pytest.fixture
def c8(scratch, run_tool):
    """The ``c8skill`` / ``c8state`` repo pair, plus a ``sync`` helper.

    Mirrors ``tools/state/oc-ledger:3286-3300``: a skill dir whose version is
    0.4.2 with a green battery receipt, and a ledger at 0.4.1 with no workers.
    Both are git repos with a base commit, because the naming check walks the
    skill repo's log.
    """
    root = Path(scratch) / "c8"
    skill = L.make_skill(root / "skill", version="0.4.2")
    L.make_battery(skill / "tools" / "tests" / "battery-last.json")
    L.init_repo(skill, branch="main")

    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "workers-ledger.json").write_text(json.dumps({
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
            env={
                "OC_LEDGER": str(state / "workers-ledger.json"),
                "OC_SKILL_DIR": str(skill),
                "OC_DEPLOY_STATE_DIR": str(state),
            })

    sync.skill = skill
    sync.state = state
    sync.ledger = state / "workers-ledger.json"
    return sync


def test_an_underivable_anchor_is_skipped_out_loud_and_never_reads_clean(c8):
    """``c8-naming-skip-rc`` + the two ``case`` legs beside it.

    No ``skill v...`` commit exists yet, so there is nothing to compare against.
    The check must SKIP (rc 0, it is not a refusal) but say so twice: that the
    check was skipped, and that the result is NOT a clean one. A silent skip is
    the failure mode — the tree reads healthy while nothing was compared.
    """
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.2\nc8 receipt\n")

    res = c8("0.4.2")
    assert res.rc == 0, (
        "[c8-naming-skip-rc] rc=%s, want 0 — an underivable anchor SKIPS, it "
        "does not refuse\n%s" % (res.rc, res.combined[-900:]))
    assert "C8 naming check SKIPPED" in res.combined, (
        "[c8-naming-skip-note-missing] the output does not announce the skip, "
        "so a reader cannot tell the check never ran:\n%s"
        % (res.combined[-900:],))
    assert "NOT a clean result" in res.combined, (
        "[c8-naming-skip-must-not-read-clean] the skip is presented as a clean "
        "result — 'could not compare' and 'compared, found nothing' are "
        "different verdicts:\n%s" % (res.combined[-900:],))


def test_an_unnamed_commit_is_listed_and_the_warn_never_blocks(c8):
    """``c8-naming-unnamed-not-listed`` + ``c8-naming-warn-never-blocks``.

    Both halves in one leg because they are one claim: the check FIRES on an
    unnamed commit AND the sync still completes. Asserting only the listing
    would pass on a hard gate, which is the behaviour the law forbids — the
    range carries other lanes' untrailered work by design.
    """
    L.commit(c8.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")
    (c8.skill / "unnamed.txt").write_text("x\n", encoding="utf-8")
    L.git(c8.skill, "add", "-A")
    L.commit(c8.skill, "fix(tools): #778 a commit the entry does not name")
    sha = L.short(c8.skill)
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.2\nc8 receipt\n")

    res = c8("0.4.2")
    assert "unnamed: %s" % sha in res.combined, (
        "[c8-naming-unnamed-not-listed] the unnamed commit %s is not listed — "
        "the entry published a range it does not name:\n%s"
        % (sha, res.combined[-1200:]))
    assert "WARN — C8 naming" in res.combined, (
        "[c8-naming-warn-missing] the finding is not presented as a WARN:\n%s"
        % (res.combined[-900:],))
    assert res.rc == 0, (
        "[c8-naming-warn-never-blocks] rc=%s, want 0 — the WARN is not a "
        "refusal; a hard gate here lets one lane's landing block the fleet's "
        "version record at HQ's boundary\n%s" % (res.rc, res.combined[-900:]))


def test_the_same_commit_named_in_the_entry_is_silent(c8):
    """``c8-naming-named-rc`` + ``c8-naming-not-silent-when-named``.

    The OTHER direction. Without it, a check that never fires at all passes the
    listing leg above only if the listing leg is also broken — so this pair is
    what makes either one mean anything.
    """
    L.commit(c8.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")
    (c8.skill / "unnamed.txt").write_text("x\n", encoding="utf-8")
    L.git(c8.skill, "add", "-A")
    L.commit(c8.skill, "fix(tools): #778 a commit the entry does not name")
    sha = L.short(c8.skill)

    L.set_skill_version(c8.skill, "0.4.2", changelog_entry=False)
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.2\nc8 receipt naming %s and #778\n" % sha)

    res = c8("0.4.2")
    assert res.rc == 0, (
        "[c8-naming-named-rc] rc=%s, want 0\n%s"
        % (res.rc, res.combined[-900:]))
    assert "unnamed:" not in res.combined, (
        "[c8-naming-not-silent-when-named] the entry NAMES %s and the check "
        "still reports it as unnamed — a one-way check cannot tell a working "
        "gate from one that always fires:\n%s" % (sha, res.combined[-1200:]))


def test_the_anchor_must_be_a_sync_not_a_bump_commit(c8):
    """``c8-anchor-not-sync-under-flags`` — the UNDER-flag direction.

    A bump-only commit whose subject starts ``skill v`` is created NEWER than
    the last real sync. A prefix-only anchor picks it up, truncates the range to
    empty, and reads CLEAN — so the bundled commit below it is never examined.
    The pinned pattern anchors on the SYNC commit and still sees the bundle.

    Pre-fix this emitted no ``unnamed:`` line at all, which is why the assertion
    is on the LINE and not on the rc: rc 0 either way.
    """
    L.commit(c8.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")
    L.set_skill_version(c8.skill, "0.4.2", changelog_entry=False)
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.2\nc8 receipt\n")

    (c8.skill / "unnamed2.txt").write_text("y\n", encoding="utf-8")
    L.git(c8.skill, "add", "-A")
    L.commit(c8.skill, "fix(tools): #779 a second commit the entry does not name")
    bundle_sha = L.short(c8.skill)

    L.commit(c8.skill, "skill v0.4.4: bump only (no sync commit here)")
    L.set_skill_version(c8.skill, "0.4.4", changelog_entry=False)
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.4\nc8 receipt\n")

    res = c8("0.4.4")
    assert "unnamed: %s" % bundle_sha in res.combined, (
        "[c8-anchor-not-sync-under-flags] the bundled commit %s is NOT listed "
        "— the anchor resolved to the newer bump-only commit, truncating the "
        "range to empty and reading CLEAN. That is an UNDER-flag, the direction "
        "where a silent pass is indistinguishable from a healthy tree:\n%s"
        % (bundle_sha, res.combined[-1500:]))


def test_a_multi_window_range_is_announced_with_a_negative_control(c8):
    """The MULTI-WINDOW NOTE and its control.

    The ledger is authoritative for what published — it carries versions that
    minted no commit at all — so skill-bump rows newer than the anchor mean the
    range straddles windows. The check must SAY so.

    The CONTROL comes first: with no such rows the note must be ABSENT. A note
    that fires always carries no information, and it would make the positive leg
    pass for the wrong reason.
    """
    L.commit(c8.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")

    L.set_skill_version(c8.skill, "0.4.5", changelog_entry=False)
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.5\nc8 receipt\n")
    control = c8("0.4.5")
    assert "MORE THAN ONE version window" not in control.combined, (
        "[c8-multi-window-note-false-positive] the note fired on a single-window "
        "range — a note that always fires carries no information:\n%s"
        % (control.combined[-1200:],))

    # the C8 block's OWN ledger, never the sandbox's: the shell measured both
    # paths and only this one is read by the check.
    doc = L.read_json(c8.ledger)
    doc.setdefault("events", []).extend([
        {"n": 90001, "t": "2099-01-01T00:00:00Z", "by": "oc-ledger sync",
         "kind": "skill-bump", "what": "v0.4.9 — fixture row"},
        {"n": 90002, "t": "2099-01-02T00:00:00Z", "by": "oc-ledger sync",
         "kind": "skill-bump", "what": "v0.4.10 — fixture row"},
    ])
    c8.ledger.write_text(json.dumps(doc), encoding="utf-8")

    res = c8("0.4.5")
    assert "MORE THAN ONE version window" in res.combined, (
        "[c8-multi-window-note-missing] two skill-bump rows newer than the "
        "anchor and the note is absent — the check presents a two-window span "
        "as one:\n%s" % (res.combined[-1200:],))
    assert "v0.4.9" in res.combined, (
        "[c8-multi-window-note-names-no-window] the note does not NAME the "
        "window it found, so a reader cannot tell which rows straddle it:\n%s"
        % (res.combined[-1200:],))


def test_the_sweepers_own_bookkeeping_is_skipped_by_a_marker_and_the_skip_is_disclosed(c8):
    """``c8-sweeper-listed-as-unnamed`` + ``c8-sweeper-skip-undisclosed``.

    The runtime-artifacts sweep writes a commit of its own. It is excluded by a
    MARKER the tool writes into the commit, never by a hand-maintained list —
    a list drifts, a marker cannot.

    Both halves: the commit must be ABSENT from the unnamed set, and the
    exclusion must be VISIBLE as a count. An unreported exclusion is an
    exclusion list nobody can audit, which is how this class of gate dies.
    """
    L.commit(c8.skill, "skill v0.4.1: oc-ledger sync — fixture anchor")

    (c8.skill / "sweep.txt").write_text("z\n", encoding="utf-8")
    L.git(c8.skill, "add", "-A")
    L.commit(c8.skill,
             "runtime-artifacts sweep (B3): tools/tests/battery-last.json "
             "(oc-ledger commit-pending --bundle)")
    sweep_sha = L.short(c8.skill)

    L.set_skill_version(c8.skill, "0.4.6", changelog_entry=False)
    with open(c8.skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("\n## v0.4.6\nc8 receipt\n")

    res = c8("0.4.6")
    assert "unnamed: %s" % sweep_sha not in res.combined, (
        "[c8-sweeper-listed-as-unnamed] the sweeper's own commit %s is listed "
        "as unnamed — it is this tool's bookkeeping, not a published change:\n%s"
        % (sweep_sha, res.combined[-1500:]))
    assert "skipped as this tool's own sweeper bookkeeping" in res.combined, (
        "[c8-sweeper-skip-undisclosed] the exclusion happened but is not "
        "disclosed — an unreported exclusion cannot be audited:\n%s"
        % (res.combined[-1500:],))
