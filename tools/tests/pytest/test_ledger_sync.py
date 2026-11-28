"""Ported: ``oc-ledger`` selftest §9-22b — ``sync``, ``check-version``,
``law-digest``, ``cadence``.

Source: ``tools/state/oc-ledger:2912-3060`` (selftest lines 142-290) — 33 of the
475 ``chk`` calls plus 15 ``ok || bad`` legs in the same block. Every assertion
message carries the shell name it replaces, so the mapping is mechanical.

WHAT THIS MODULE PROTECTS
    ``sync`` is the ONE verb allowed to move a skill version, and the only place
    a ``skill-bump`` row is minted. The invariants are therefore about the gates
    in front of that write, and about the difference between a gate and a
    formality:

    * A gate that refuses writes NOTHING. ``sync-empty-why-no-event`` exists
      because a mutant that drops the ``--why`` check writes the row AND exits
      0 — the event COUNT is the assertion that discriminates.
    * Each gate keeps its OWN rc, because the rc is what a caller branches on:
      5 = the battery receipt is absent or red (go run the battery), 6 = the
      version step / SKILL.md / CHANGELOG is wrong, 2 = a usage error, 7 = an
      unrelated dirty path. Collapsing them would make "your receipt is stale"
      and "your doc does not say that version" indistinguishable to every
      script that calls this.
    * A WARN is not a refusal. A hard gate on the deferral or on C8 naming would
      let one lane's landing block the fleet's version record at HQ's boundary.
    * Idempotence: a re-sync on an unchanged tree is rc 0 and reports NO
      deferral (#467 AC-1). ``git commit`` exits non-zero for the benign
      "nothing to commit", and the old ``||`` arm cried commit-lag on every
      idempotent re-sync — a false-alarm generator, not a guard. The negative
      control (a failing hook with work staged) is asserted beside it, because
      otherwise "suppress commit-lag" would pass by suppressing it always.
    * The law digest is the only observable for "the law moved without a bump".
      The version is a SELF-REPORT; a nine-day incident had every field saying
      0.4.295 while the law moved underneath. So these legs run while the
      version FIELDS still agree — a red there cannot be the field mismatch the
      check-version legs manufacture, which is what makes them discriminating.

FIXTURE NOTE
    The shell drives one shared ``$T`` through a long sequence, so state carries
    forward between legs. Here each leg asks the ``pair`` factory for its own
    ``(state, skill)`` pair and reaches its precondition by CALLING the verb,
    not by inheriting a ledger from the leg above. That is what lets these run
    under ``-n 2``, and it means a leg cannot pass on state it did not build.

DELIBERATELY NOT PORTED HERE
    * The C8 naming block (``c8-naming-*``, ``c8-651-*``, ``c8-94-*``) lives in
      ``test_ledger_c8.py``: ~200 shell lines with its own fixture builders
      (``c8mk``/``c8commit``) and 20 assertions.
    * The ``state-tracked-*`` / ``state-out-of-scope-*`` audits ``sync`` also
      prints are ``test_ledger_misc.py``: they slice the tool's own source and
      belong with the other structural legs.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")
_SEQ = itertools.count()

# The ledger every sync leg starts from: version 0.4.1 everywhere, one rostered
# worker, no events. ``stamp`` refuses an anonymous row, so the roster is
# load-bearing rather than decorative.
BASE_LEDGER = {
    "current_skill_version": "0.4.1",
    "meta": {"skill_version": "0.4.1", "current_skill_version": "0.4.1"},
    "updated_at": "2026-01-01T00:00:00Z",
    "workers": [{
        "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "role": "tester", "topic_id": 1, "feature": "-", "confirmed": True,
        "last_acked": None, "notes": [], "events": [],
    }],
    "events": [],
}


# =============================================================================
# the pair factory — a state repo + a skill repo, as the shell's $T builds them
# =============================================================================
@pytest.fixture
def pair(scratch):
    """Factory: ``pair(tag)`` -> a fresh ``(state_dir, skill_dir)`` pair.

    Each call builds BOTH repos with a pinned identity and a base commit, and
    writes a FRESH battery receipt — the 6h staleness gate would otherwise mask
    every other gate in this module. Nothing is shared between calls.
    """
    def _make(tag: str = "p", version: str = "0.4.2"):
        root = scratch.path / "sync" / ("%s-%d" % (tag, next(_SEQ)))
        state = root / "state"
        skill = root / "skill"
        state.mkdir(parents=True, exist_ok=True)
        L.make_skill(skill, version=version)
        L.write(state / "workers-ledger.json", json.dumps(BASE_LEDGER))
        L.make_battery(skill / "tools" / "tests" / "battery-last.json")
        for repo in (state, skill):
            L.init_repo(repo)
        return state, skill
    return _make


def _env(state, skill) -> dict:
    return {
        "OC_LEDGER": str(Path(state) / "workers-ledger.json"),
        "OC_SKILL_DIR": str(skill),
        "OC_DEPLOY_STATE_DIR": str(state),
    }


def _run(run_tool, state, skill, *args, **kw):
    return run_tool([str(TOOL)] + [str(a) for a in args], timeout=180,
                    env=_env(state, skill), **kw)


def _sync(run_tool, state, skill, *args, **kw):
    return _run(run_tool, state, skill, "sync", *args, **kw)


def _ledger(state) -> Path:
    return Path(state) / "workers-ledger.json"


def _skill_bumps(state) -> list:
    return L.where(_ledger(state), kind="skill-bump")


def _bump_to(run_tool, state, skill, version: str, why: str = "fixture"):
    """Move the skill to ``version`` the way a lane does: doc first, then sync.

    Both halves, because ``sync`` refuses a bump whose CHANGELOG entry is
    missing (C8, v0.4.65) — a helper that moved only SKILL.md would make every
    caller assert the changelog gate by accident.
    """
    L.set_skill_version(skill, version)
    return _sync(run_tool, state, skill, "--version", version, "--why", why)


# =============================================================================
# 9-13: the gates in front of the write
# =============================================================================
def test_sync_gates_refuse_in_order_with_their_own_rc(pair, run_tool):
    """``sync-no-receipt``, ``sync-red-receipt``, ``sync-bad-shape``,
    ``sync-skillmd-mismatch``, ``sync-step-gap``, ``sync-changelog-missing``.

    ONE test because the gates are ORDERED: each arm removes exactly one
    objection, so the rc that comes back names the NEXT one. Run them
    independently and every arm would report the same first gate — the sequence
    is the fixture.
    """
    state, skill = pair("gates")

    # (a) no receipt at all -> 5. The battery must have run; this is the gate
    #     that stops an unverified tree from being published.
    (skill / "tools" / "tests" / "battery-last.json").unlink()
    res = _sync(run_tool, state, skill, "--version", "0.4.2")
    assert res.rc == 5, (
        "[sync-no-receipt] rc=%s, want 5 (no battery receipt)\n%s"
        % (res.rc, res.combined[-600:]))

    # (b) a RED receipt -> 5 as well. Same code on purpose: from the caller's
    #     side "absent" and "red" are one instruction — run the battery.
    L.make_battery(skill / "tools" / "tests" / "battery-last.json",
                   verdict="FAIL", fail=2)
    res = _sync(run_tool, state, skill, "--version", "0.4.2")
    assert res.rc == 5, (
        "[sync-red-receipt] rc=%s, want 5 (receipt verdict FAIL)\n%s"
        % (res.rc, res.combined[-600:]))

    # (c) a well-shaped GREEN receipt restores the gate, and the malformed
    #     version is now the next objection -> 6.
    L.make_battery(skill / "tools" / "tests" / "battery-last.json")
    res = _sync(run_tool, state, skill, "--version", "banana")
    assert res.rc == 6, (
        "[sync-bad-shape] rc=%s, want 6 (version shape must be 0.N.N)\n%s"
        % (res.rc, res.combined[-600:]))

    # (d) SKILL.md disagrees with the requested version -> 6. The doc is the
    #     published artefact; a sync that moved the ledger past it would leave
    #     the fleet reading a version no document claims.
    L.set_skill_version(skill, "0.4.9", changelog_entry=False)
    res = _sync(run_tool, state, skill, "--version", "0.4.2")
    assert res.rc == 6, (
        "[sync-skillmd-mismatch] rc=%s, want 6 (SKILL.md says 0.4.9, sync "
        "asked for 0.4.2)\n%s" % (res.rc, res.combined[-600:]))

    # (e) the doc agrees but the STEP is too large -> 6. A multi-version jump is
    #     a different act with its own flag (--catch-up), because it silently
    #     skips the intermediate CHANGELOG entries.
    L.set_skill_version(skill, "0.4.2", changelog_entry=False)
    res = _sync(run_tool, state, skill, "--version", "0.4.9")
    assert res.rc == 6, (
        "[sync-step-gap] rc=%s, want 6 (0.4.1 -> 0.4.9 is more than +1 patch "
        "and --catch-up was not given)\n%s" % (res.rc, res.combined[-600:]))

    # (f) the step is legal but the CHANGELOG entry is missing -> 6 (C8,
    #     v0.4.65). A version published with no receipt is a bump nobody can
    #     audit; the entry IS the receipt.
    res = _sync(run_tool, state, skill, "--version", "0.4.2")
    assert res.rc == 6, (
        "[sync-changelog-missing] rc=%s, want 6 (no '## v0.4.2' entry in "
        "CHANGELOG.md)\n%s" % (res.rc, res.combined[-600:]))

    assert not _skill_bumps(state), (
        "six refused syncs wrote %d skill-bump row(s) — a gate that refuses "
        "must leave no drift behind, or the next reader sees a version that "
        "was never published" % len(_skill_bumps(state)))
    assert L.read_json(_ledger(state))["current_skill_version"] == "0.4.1", (
        "a refused sync moved current_skill_version to %r, want 0.4.1"
        % (L.read_json(_ledger(state))["current_skill_version"],))


def test_empty_why_is_refused_and_writes_no_event(pair, run_tool):
    """``sync-empty-why-refused`` + ``sync-empty-why-no-event``
    + ``sync-empty-why-names-the-flag`` (H-4, factory #31).

    Every OTHER gate is satisfied here — receipt green and fresh, SKILL.md at
    0.4.2, step equal, no skill-bump row yet — so an empty ``--why`` is the ONLY
    thing that can refuse. That is what makes the leg discriminating: a mutant
    that drops the gate writes the row AND exits 0, reddening BOTH the rc leg
    and the no-event leg.
    """
    state, skill = pair("why")
    L.set_skill_version(skill, "0.4.2")

    before = len(_skill_bumps(state))
    res = _sync(run_tool, state, skill, "--version", "0.4.2")
    assert res.rc == 2, (
        "[sync-empty-why-refused] rc=%s, want 2 — a skill-bump row must not "
        "ship without its why-text\n%s" % (res.rc, res.combined[-600:]))

    after = len(_skill_bumps(state))
    assert after == before, (
        "[sync-empty-why-no-event] skill-bump rows went %d -> %d — the "
        "refusal must not write the row it refused" % (before, after))

    assert "--why" in res.err, (
        "[sync-empty-why-names-the-flag] stderr does not name --why, so the "
        "caller is told 'refused' with no way to fix it: %r" % (res.err.strip(),))


# =============================================================================
# 14-17: the happy path, its git legs, and the re-sync
# =============================================================================
def test_sync_happy_writes_three_fields_the_event_and_both_git_legs(
        pair, run_tool):
    """``sync-happy`` + ``sync-tail-rotate-line`` + ``sync-three-fields``
    + ``sync-event`` + ``sync-state-commit`` + ``sync-skill-tag``.

    The three FIELDS matter separately from the event: ``current_skill_version``
    is what the fleet reads, and the two ``meta`` copies are what
    ``check-version`` compares. A sync that updated one and not the others
    manufactures the exact drift the next section detects.
    """
    state, skill = pair("happy")
    L.set_skill_version(skill, "0.4.2")

    res = _sync(run_tool, state, skill, "--version", "0.4.2",
                "--why", "selftest")
    assert res.rc == 0, (
        "[sync-happy] rc=%s, want 0\n%s" % (res.rc, res.combined[-1000:]))

    # The tail line proves the post-sync hooks RAN rather than being skipped
    # silently — a sync that stopped calling shadow-rotate looks identical from
    # the ledger's side.
    assert "shadow-rotate:" in res.combined, (
        "[sync-tail-rotate-line] the sync tail does not report the "
        "shadow-rotate step: %r" % (res.combined[-600:],))

    doc = L.read_json(_ledger(state))
    fields = {
        "current_skill_version": doc.get("current_skill_version"),
        "meta.current_skill_version": doc.get("meta", {}).get(
            "current_skill_version"),
        "meta.skill_version": doc.get("meta", {}).get("skill_version"),
    }
    assert set(fields.values()) == {"0.4.2"}, (
        "[sync-three-fields] the three version fields are %r, want all "
        "'0.4.2' — updating one and not the others IS the drift check-version "
        "exists to catch" % (fields,))

    assert L.field(_ledger(state), "kind", kind="skill-bump") == "skill-bump", (
        "[sync-event] the last skill-bump row's kind is %r, want 'skill-bump'"
        % (L.field(_ledger(state), "kind", kind="skill-bump"),))

    # The STATE repo commit is the durable half: the ledger is only published
    # when it is committed, and the subject is what a reader greps for.
    oneline = L.git(state, "log", "--oneline").stdout
    assert "skill-bump v0.4.2" in oneline, (
        "[sync-state-commit] no commit in the state repo mentions "
        "'skill-bump v0.4.2' (log: %r)" % (oneline[:400],))

    # The SKILL repo tag is what other lanes resolve the version against.
    tags = L.git(skill, "tag").stdout.split()
    assert "v0.4.2" in tags, (
        "[sync-skill-tag] the skill repo has tags %r, want v0.4.2 among them"
        % (tags,))


def test_a_resync_is_idempotent_and_a_clean_tree_is_not_a_deferral(
        pair, run_tool):
    """``sync-resync-equal`` + ``sync-clean-tree-no-commit-lag`` (#467 AC-1).

    ``git commit`` exits non-zero for the benign "nothing to commit" case, and
    the old ``||`` arm cried commit-lag on every idempotent re-sync. A clean tree
    is not a deferral — and a warning that fires on every correct run is worse
    than none, because it teaches the reader to ignore the one that matters.
    """
    state, skill = pair("resync")
    L.set_skill_version(skill, "0.4.2")
    first = _sync(run_tool, state, skill, "--version", "0.4.2",
                  "--why", "selftest")
    assert first.rc == 0, (
        "precondition: first sync rc=%s\n%s"
        % (first.rc, first.combined[-600:]))

    res = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "resync")
    assert res.rc == 0, (
        "[sync-resync-equal] rc=%s, want 0 — an equal-version re-sync is a "
        "legal no-op\n%s" % (res.rc, res.combined[-800:]))

    assert "commit-lag: skill commit deferred" not in res.combined, (
        "[sync-clean-tree-no-commit-lag] the re-sync reports a commit "
        "deferral on a CLEAN tree — 'nothing to commit' is not a deferral "
        "(#467 AC-1): %r" % (res.combined[-800:],))


def test_a_genuine_deferral_is_still_reported(pair, run_tool):
    """``sync-hook-fail-rc`` + ``sync-genuine-deferral-reported`` (#467 AC-2).

    The negative control for the leg above. A failing pre-commit hook with
    something staged makes ``git commit`` fail while the tree is otherwise
    sound, so the ``||`` arm is then the ONLY thing that can say so.
    """
    state, skill = pair("hookfail")
    L.set_skill_version(skill, "0.4.2")
    ok = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert ok.rc == 0, (
        "precondition: first sync rc=%s\n%s" % (ok.rc, ok.combined[-600:]))

    hook = Path(skill) / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    # A staged change is what makes the commit fail for a reason OTHER than
    # "nothing to commit" — that is the whole distinction this leg draws.
    with open(Path(skill) / "CHANGELOG.md", "a", encoding="utf-8") as fh:
        fh.write("fixture\n")

    res = _sync(run_tool, state, skill, "--version", "0.4.2",
                "--why", "hookfail")
    assert res.rc == 0, (
        "[sync-hook-fail-rc] rc=%s, want 0 — a deferred commit is a WARN, not "
        "a refusal (a hard failure here would strand the ledger unpublished "
        "AND the version unbumped)\n%s" % (res.rc, res.combined[-800:]))

    assert "commit-lag: skill commit deferred" in res.combined, (
        "[sync-genuine-deferral-reported] a failing pre-commit hook with work "
        "staged did NOT produce the deferral warning — the suppression in the "
        "leg above would then be indistinguishable from never reporting at "
        "all: %r" % (res.combined[-800:],))


def test_the_stray_guard_refuses_an_unrelated_dirty_path(pair, run_tool):
    """``sync-stray-refused`` + ``sync-stray-names-path``
    + ``sync-stray-no-event`` (v0.4.157).

    rc 7 is its own code because it is its own instruction: "something
    unrelated is dirty in the skill tree, commit or remove it". Folding it into
    6 would tell the caller to fix the version doc, which is not the problem.
    """
    state, skill = pair("stray")
    # Reach the shell's precondition: the ledger is at 0.4.2, so 0.4.3 is a
    # legal +1 step and the stray path is the ONLY objection left.
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync 0.4.2 rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    L.set_skill_version(skill, "0.4.3")
    (Path(skill) / "tools" / "stray-probe.sh").write_text("stray-leg\n",
                                                          encoding="utf-8")

    res = _sync(run_tool, state, skill, "--version", "0.4.3", "--why", "stray")
    assert res.rc == 7, (
        "[sync-stray-refused] rc=%s, want 7 — an unrelated dirty path must "
        "refuse the bump rather than ride into it\n%s"
        % (res.rc, res.combined[-800:]))

    assert "stray-probe.sh" in res.combined, (
        "[sync-stray-names-path] the refusal does not NAME the stray path, so "
        "the caller cannot tell which file to deal with: %r"
        % (res.combined[-800:],))

    strayed = [b for b in _skill_bumps(state)
               if (b.get("what") or "").startswith("v0.4.3 ")]
    assert not strayed, (
        "[sync-stray-no-event] the refused sync wrote %d skill-bump row(s) "
        "for v0.4.3 anyway — a refusal must leave no drift behind"
        % len(strayed))


def test_the_payload_sweep_requires_explicit_consent(pair, run_tool):
    """``sync-payload-sweep`` + ``sync-payload-warning``
    + ``sync-sweeps-payload`` (n=1405 root-fix, v0.4.157).

    The sweep is now EXPLICIT — ``--allow-sweep`` is the consent — so a bump can
    no longer absorb a path nobody agreed to (the 20c8df4f class: v0.4.58/61/62
    strayed payload via a hardcoded add list). Asserting the file LANDED in the
    tag is what separates "the warning printed" from "the sweep happened": a tool
    that announced a sweep and committed nothing would pass the message leg.
    """
    state, skill = pair("sweep")
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync 0.4.2 rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    L.set_skill_version(skill, "0.4.3")
    (Path(skill) / "tools" / "payload-probe.sh").write_text("payload-leg\n",
                                                            encoding="utf-8")

    res = _sync(run_tool, state, skill, "--version", "0.4.3",
                "--why", "payload-sweep", "--allow-sweep")
    assert res.rc == 0, (
        "[sync-payload-sweep] rc=%s, want 0 with --allow-sweep\n%s"
        % (res.rc, res.combined[-800:]))

    assert "PAYLOAD SWEPT" in res.combined, (
        "[sync-payload-warning] the sweep happened but was not DISCLOSED — an "
        "unreported inclusion is how this class of defect stays invisible: %r"
        % (res.combined[-800:],))

    names = L.git(skill, "show", "v0.4.3", "--name-only").stdout
    assert "payload-probe.sh" in names, (
        "[sync-sweeps-payload] payload-probe.sh is not in the v0.4.3 tag's "
        "file list, so the announced sweep did not actually carry it:\n%s"
        % (names,))


# =============================================================================
# 18-19 + factory #47: the law digest
# =============================================================================
def test_law_digest_is_stamped_in_the_bump_row_and_moves_with_the_law(
        pair, run_tool):
    """``law-digest-match-rc`` + ``law-digest-stamped-in-bump-row``
    + ``law-digest-moves-with-law``.

    The version is a SELF-REPORT. The digest is the only observable for "the law
    moved without a bump" — a nine-day incident had every field saying 0.4.295
    while the law moved underneath. The anti-vacuity leg is what makes it a
    measurement rather than a constant: a law file APPEARING where there was
    none is a law change too (ABSENT -> hash), so it covers the deletion and
    rename directions as well.
    """
    state, skill = pair("digest")
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    res = _run(run_tool, state, skill, "law-digest")
    assert res.rc == 0, (
        "[law-digest-match-rc] rc=%s, want 0 — the digest is a function of the "
        "law bytes, and nothing moved\n%s" % (res.rc, res.combined[-800:]))

    stamped = (L.last_where(_ledger(state), kind="skill-bump") or {}).get(
        "law_digest") or ""
    assert len(stamped) == 64 and all(c in "0123456789abcdef"
                                     for c in stamped), (
        "[law-digest-stamped-in-bump-row] the bump row's law_digest is %r, "
        "want 64 hex chars — a constant or an empty field fails here"
        % (stamped,))

    # ANTI-VACUITY: change the law and the digest must change with it.
    (Path(skill) / "editor.md").write_text("fixture law\n", encoding="utf-8")
    # --json reports DRIFT with rc 1 as well as the verdict, which is why the
    # shell reads `.current` and DISCARDS the rc here (it asserts the rc on the
    # plain form, one leg below). Pinning rc 0 would fail on a correct tool.
    moved = _run(run_tool, state, skill, "law-digest", "--json")
    current = (json.loads(moved.out) or {}).get("current") or ""
    assert current and current != stamped, (
        "[law-digest-moves-with-law] the digest is %r after a law file was "
        "ADDED, unchanged from %r — it is not a function of the law bytes"
        % (current, stamped))


def test_a_moved_law_is_reported_as_unbumped_and_blocks_a_resync(
        pair, run_tool):
    """``law-digest-drift-rc`` + ``check-version-unbumped-law-rc``
    + ``check-version-names-unbumped-law``
    + ``check-version-unbumped-law-is-not-a-field-mismatch``
    + ``sync-resync-law-moved-refused`` + ``sync-resync-law-moved-names-cause``.

    The fourth leg is the discriminator: this red must NOT read as the field
    mismatch the check-version legs manufacture, because the fix is different
    (bump the version, not align the fields).

    ``--allow-sweep`` is passed to the re-sync deliberately: the stray-guard's
    consent must NOT override this refusal, or the consent flag becomes the
    laundering route for exactly the drift the check exists to catch.
    """
    state, skill = pair("unbumped")
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    (Path(skill) / "editor.md").write_text("fixture law\n", encoding="utf-8")

    res = _run(run_tool, state, skill, "law-digest")
    assert res.rc == 1, (
        "[law-digest-drift-rc] rc=%s, want 1 — the law moved and no bump "
        "records it\n%s" % (res.rc, res.combined[-800:]))

    cv = _run(run_tool, state, skill, "check-version")
    assert cv.rc == 1, (
        "[check-version-unbumped-law-rc] rc=%s, want 1 — check-version must "
        "carry the drift verdict\n%s" % (cv.rc, cv.combined[-800:]))

    assert "UNBUMPED-LAW" in cv.combined, (
        "[check-version-names-unbumped-law] the verdict does not say "
        "UNBUMPED-LAW: %r" % (cv.combined[-800:],))

    assert "ok: all fields agree" not in cv.combined, (
        "[check-version-unbumped-law-is-not-a-field-mismatch] the output still "
        "says 'all fields agree' — the fields DO agree; the LAW is what moved, "
        "and a reader sent to align the fields would fix nothing: %r"
        % (cv.combined[-800:],))

    # The same version cannot be re-synced to launder the moved law. The refusal
    # lives on the IDEMPOTENT-RE-SYNC path (a skill-bump row for the version
    # already exists), so the law must move AFTER a version was published —
    # otherwise the ordinary step/SKILL.md gates fire first and this leg would
    # assert a different refusal under this name.
    law = Path(skill) / "editor.md"
    law.unlink()
    assert _bump_to(run_tool, state, skill, "0.4.3",
                    "relaw-baseline").rc == 0, "precondition: sync 0.4.3"
    law.write_text("fixture law\n", encoding="utf-8")
    relaw = _sync(run_tool, state, skill, "--version", "0.4.3",
                  "--why", "relaw", "--allow-sweep")
    assert relaw.rc == 6, (
        "[sync-resync-law-moved-refused] rc=%s, want 6 — a re-sync at a moved "
        "law must be refused, and --allow-sweep must not be the way around "
        "it\n%s" % (relaw.rc, relaw.combined[-800:]))

    assert "a re-sync is not a bump" in relaw.combined, (
        "[sync-resync-law-moved-names-cause] the refusal does not explain that "
        "a re-sync is not a bump: %r" % (relaw.combined[-800:],))


def test_restoring_the_law_restores_the_verdict(pair, run_tool):
    """``law-digest-restored-rc`` + ``check-version-restored-rc``.

    A leg stuck red after the state is repaired is a false-alarm generator, not
    a guard — and the fleet learns to ignore it. Asserted as the closing half of
    the drift pair, because "red when broken" only means something alongside
    "green when fixed".
    """
    state, skill = pair("restored")
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    law = Path(skill) / "editor.md"
    law.write_text("fixture law\n", encoding="utf-8")
    assert _run(run_tool, state, skill, "law-digest").rc == 1, (
        "precondition: a moved law is rc 1")

    law.unlink()

    res = _run(run_tool, state, skill, "law-digest")
    assert res.rc == 0, (
        "[law-digest-restored-rc] rc=%s, want 0 after the law was restored — a "
        "verdict that stays red after repair trains the reader to ignore it\n%s"
        % (res.rc, res.combined[-800:]))

    cv = _run(run_tool, state, skill, "check-version")
    assert cv.rc == 0, (
        "[check-version-restored-rc] rc=%s, want 0\n%s"
        % (cv.rc, cv.combined[-800:]))


# =============================================================================
# 18-19 + #359: check-version names its cause
# =============================================================================
def test_check_version_names_which_field_drifted(pair, run_tool):
    """``check-version-ok`` + ``check-version-names-field``
    + ``check-version-drift-rc``.

    ``grep -q "meta.skill_version"`` in the shell is the whole assertion: the
    verdict must NAME the field, because "versions disagree" without the field
    name sends the reader to diff three places by hand.
    """
    state, skill = pair("cvfield")
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    ok = _run(run_tool, state, skill, "check-version")
    assert ok.rc == 0, (
        "[check-version-ok] rc=%s, want 0 when all fields agree\n%s"
        % (ok.rc, ok.combined[-600:]))

    doc = L.read_json(_ledger(state))
    doc["meta"]["skill_version"] = "0.4.1"
    L.write(_ledger(state), json.dumps(doc))

    res = _run(run_tool, state, skill, "check-version")
    assert res.rc == 1, (
        "[check-version-drift-rc] rc=%s, want 1 (meta.skill_version is 0.4.1 "
        "while the others say 0.4.2)\n%s" % (res.rc, res.combined[-800:]))

    assert "meta.skill_version" in res.combined, (
        "[check-version-names-field] the verdict does not name "
        "meta.skill_version, so the reader is told 'drift' with no field to "
        "fix: %r" % (res.combined[-800:],))


def test_check_version_separates_fleet_level_from_lane_level_drift(
        pair, run_tool):
    """``check-version-fleet-rc`` + ``check-version-names-fleet-cause``
    + ``check-version-lane-rc`` + ``check-version-names-lane-cause`` (#359).

    Both shapes keep rc 1 — that is the contract — so the DISCRIMINATOR has to
    be the named cause. FLEET-LEVEL means the ledger's own fields disagree;
    LANE-LEVEL means a worker's ack is behind. The fixes are different people's
    work, and a verdict that says only "rc 1" makes the reader guess which.
    """
    state, skill = pair("cvlevel")
    L.set_skill_version(skill, "0.4.2")
    pre = _sync(run_tool, state, skill, "--version", "0.4.2", "--why", "selftest")
    assert pre.rc == 0, (
        "precondition: sync rc=%s\n%s" % (pre.rc, pre.combined[-600:]))

    # FLEET-LEVEL: the ledger's own fields disagree.
    doc = L.read_json(_ledger(state))
    doc["meta"]["skill_version"] = "0.4.1"
    L.write(_ledger(state), json.dumps(doc))

    fleet = _run(run_tool, state, skill, "check-version")
    assert fleet.rc == 1, (
        "[check-version-fleet-rc] rc=%s, want 1\n%s"
        % (fleet.rc, fleet.combined[-800:]))
    assert "FLEET-LEVEL" in fleet.combined, (
        "[check-version-names-fleet-cause] the verdict does not say "
        "FLEET-LEVEL, so a lane owner is sent to chase a worker's ack that is "
        "not the problem: %r" % (fleet.combined[-800:],))

    # LANE-LEVEL: the SAME field drift, but now a worker is also behind. The
    # worker ack is the refinement, not an alternative trigger — the tool reaches
    # its cause branch only after ``bad > 0``, so a lane that is behind while the
    # fields all agree still returns 0. That is the tool's contract as written
    # (oc-ledger:2138-2153) and the shell drives both arms from the same drifted
    # ledger, which is why the field drift is deliberately NOT repaired here.
    doc["workers"][0]["last_acked"] = {"version": "0.4.1",
                                       "at": "2026-01-01T00:00:00Z"}
    L.write(_ledger(state), json.dumps(doc))

    lane = _run(run_tool, state, skill, "check-version")
    assert lane.rc == 1, (
        "[check-version-lane-rc] rc=%s, want 1\n%s"
        % (lane.rc, lane.combined[-800:]))
    assert "LANE-LEVEL" in lane.combined, (
        "[check-version-names-lane-cause] the verdict does not say LANE-LEVEL: "
        "%r" % (lane.combined[-800:],))


# =============================================================================
# 20-22: cadence
# =============================================================================
def _cadence(run_tool, state, skill):
    return _run(run_tool, state, skill, "cadence")


def test_cadence_counts_bumps_fires_at_five_and_resets_on_a_review(
        pair, run_tool):
    """``cadence-count`` + ``cadence-fire-rc`` + ``cadence-reset-on-review``.

    The cadence is the only mechanism that makes "Duties 4+6 are due" a
    MEASUREMENT rather than a lane's memory, so its counter has to be a function
    of the published history. The reset is asserted in the same fixture because
    a counter that only increments is a nag, not a cadence.

    The count is over skill-bump ROWS, not sync INVOCATIONS: the pad loop below
    re-syncs an already-published version, and those are idempotent. Counting
    re-syncs would make the cadence fire on housekeeping.
    """
    state, skill = pair("cadence")
    L.set_skill_version(skill, "0.4.2")
    assert _sync(run_tool, state, skill, "--version", "0.4.2",
                 "--why", "selftest").rc == 0, "precondition: sync 0.4.2"
    assert _bump_to(run_tool, state, skill, "0.4.3",
                    "payload-sweep").rc == 0, "precondition: sync 0.4.3"

    res = _cadence(run_tool, state, skill)
    assert "2/5 WAIT" in res.combined, (
        "[cadence-count] cadence does not read '2/5 WAIT' after exactly two "
        "skill-bump rows (a re-sync must not count): %r"
        % (res.combined.strip(),))

    # Three more real bumps reach the boundary. 0.4.3 is re-synced first (an
    # idempotent no-op), then 0.4.4/0.4.5/0.4.6 step forward.
    for v in ("0.4.3", "0.4.4", "0.4.5", "0.4.6"):
        _bump_to(run_tool, state, skill, v, "pad")

    fire = _cadence(run_tool, state, skill)
    assert fire.rc == 1, (
        "[cadence-fire-rc] cadence rc=%s at the boundary, want 1 (the fire "
        "verdict)\n%s" % (fire.rc, fire.combined[-600:]))
    assert "5/5 FIRE" in fire.combined, (
        "[cadence-fire-rc] cadence reads %r, want '5/5 FIRE'"
        % (fire.combined.strip(),))

    # A review-battery row is the acknowledgement that resets the counter.
    review = _run(run_tool, state, skill, "stamp", "review-battery", "boundary")
    assert review.rc == 0, "precondition: review-battery rc=%s" % review.rc

    after = _cadence(run_tool, state, skill)
    assert "0/5 WAIT" in after.combined, (
        "[cadence-reset-on-review] cadence reads %r after a review-battery "
        "row, want '0/5 WAIT' — a counter that never resets is a nag, not a "
        "cadence" % (after.combined.strip(),))


def test_a_cycle_close_note_is_also_a_reset_point(pair, run_tool):
    """``cadence-reset-on-cycle-close`` + ``cadence-counts-after-close``
    (v0.4.129, n=2349 stale-boundary class).

    A note "<version> ACCEPTED" is the canonical reset point — the boundary
    moves to that row's ordinal, and bumps after it recount from there. Both
    halves asserted: the reset, and that the counter then climbs again from the
    new boundary. A reset that zeroed the counter permanently would pass the
    first leg and hide every later duty.
    """
    state, skill = pair("close")
    L.set_skill_version(skill, "0.4.2")
    assert _sync(run_tool, state, skill, "--version", "0.4.2",
                 "--why", "selftest").rc == 0, "precondition: sync 0.4.2"
    for v in ("0.4.3", "0.4.4", "0.4.5", "0.4.6"):
        _bump_to(run_tool, state, skill, v, "pad")

    review = _run(run_tool, state, skill, "stamp", "review-battery", "boundary")
    assert review.rc == 0, "precondition: review-battery rc=%s" % review.rc

    close = _run(run_tool, state, skill, "stamp", "note",
                 "0.4.6 ACCEPTED (fixture cycle close)")
    assert close.rc == 0, (
        "precondition: cycle-close note rc=%s\n%s"
        % (close.rc, close.combined[-600:]))

    reset = _cadence(run_tool, state, skill)
    assert "0/5 WAIT" in reset.combined, (
        "[cadence-reset-on-cycle-close] cadence reads %r after an "
        "'<version> ACCEPTED' note, want '0/5 WAIT' — the cycle-close note is "
        "the canonical boundary" % (reset.combined.strip(),))

    bump = _bump_to(run_tool, state, skill, "0.4.7", "cadence-close-probe")
    assert bump.rc == 0, (
        "precondition: sync 0.4.7 rc=%s\n%s" % (bump.rc, bump.combined[-600:]))

    counted = _cadence(run_tool, state, skill)
    assert "1/5 WAIT" in counted.combined, (
        "[cadence-counts-after-close] cadence reads %r after one bump past the "
        "close, want '1/5 WAIT' — a reset that never recounts is a permanent "
        "silence" % (counted.combined.strip(),))


# =============================================================================
# 22b: sync --catch-up
# =============================================================================
def test_catch_up_is_the_only_legal_multi_version_jump(pair, run_tool):
    """``sync-catchup-needs-flag`` + ``sync-catchup-needs-why``
    + ``sync-catchup-downgrade-rc6`` + ``sync-catchup-happy``
    + ``sync-catchup-event`` + ``sync-catchup-heal``.

    The shipped-ahead dead zone (T2 verdict n=1695, HQ-approved 2026-09-06)
    gained a legal path: a multi-step FORWARD jump with a mandatory ``--why``.
    The three refusals are what keep it from becoming a general-purpose bypass —
    without the flag it is the old rc 6, without the reason it is a usage error,
    and a DOWNGRADE is still refused, because a version that goes backwards
    makes every lane's ack meaningless.

    The precondition is current=0.4.7, reached by the same pad sequence the
    cadence section uses, so the skip set in the event text is exactly 0.4.8.
    """
    state, skill = pair("catchup")
    L.set_skill_version(skill, "0.4.2")
    assert _sync(run_tool, state, skill, "--version", "0.4.2",
                 "--why", "selftest").rc == 0, "precondition: sync 0.4.2"
    for v in ("0.4.3", "0.4.4", "0.4.5", "0.4.6"):
        _bump_to(run_tool, state, skill, v, "pad")
    assert _bump_to(run_tool, state, skill, "0.4.7",
                    "cadence-close-probe").rc == 0, "precondition: sync 0.4.7"

    L.set_skill_version(skill, "0.4.9")

    no_flag = _sync(run_tool, state, skill, "--version", "0.4.9")
    assert no_flag.rc == 6, (
        "[sync-catchup-needs-flag] rc=%s, want 6 — a multi-version jump "
        "without --catch-up is the ordinary step-gap refusal\n%s"
        % (no_flag.rc, no_flag.combined[-600:]))

    no_why = _sync(run_tool, state, skill, "--version", "0.4.9", "--catch-up")
    assert no_why.rc == 2, (
        "[sync-catchup-needs-why] rc=%s, want 2 — --catch-up without a reason "
        "is a usage error (a jump with no provenance is a bump nobody can "
        "audit)\n%s" % (no_why.rc, no_why.combined[-600:]))

    L.set_skill_version(skill, "0.4.4", changelog_entry=False)
    down = _sync(run_tool, state, skill, "--version", "0.4.4",
                 "--catch-up", "--why", "downgrade-probe")
    assert down.rc == 6, (
        "[sync-catchup-downgrade-rc6] rc=%s, want 6 — a DOWNGRADE is not a "
        "catch-up; a version that goes backwards makes every lane's ack "
        "meaningless\n%s" % (down.rc, down.combined[-600:]))

    L.set_skill_version(skill, "0.4.9")
    happy = _sync(run_tool, state, skill, "--version", "0.4.9",
                  "--catch-up", "--why", "selftest-catchup")
    assert happy.rc == 0, (
        "[sync-catchup-happy] rc=%s, want 0\n%s"
        % (happy.rc, happy.combined[-800:]))

    what = L.field(_ledger(state), "what", kind="skill-bump") or ""
    assert "catch-up from 0.4.7 (skipped 0.4.8)" in what, (
        "[sync-catchup-event] the bump row's text is %r, want it to name the "
        "version jumped FROM and the ones SKIPPED — a catch-up row that reads "
        "like an ordinary bump hides exactly the window nobody published"
        % (what,))

    doc = L.read_json(_ledger(state))
    fields = {
        "current_skill_version": doc.get("current_skill_version"),
        "meta.current_skill_version": doc.get("meta", {}).get(
            "current_skill_version"),
        "meta.skill_version": doc.get("meta", {}).get("skill_version"),
    }
    assert set(fields.values()) == {"0.4.9"}, (
        "[sync-catchup-heal] the three fields are %r, want all '0.4.9' — the "
        "catch-up must HEAL the dead zone, not leave the fields behind"
        % (fields,))
