"""Ported: ``oc-ledger`` selftest §structural — the single-source guards and the
two declared-vs-mechanism audits.

Source: ``tools/state/oc-ledger:3665-4002`` (selftest lines 895-1232): 24
``chk`` calls plus 21 ``ok || bad`` legs in the same block. Every assertion
message carries the shell leg name it replaces, so the mapping is mechanical.

WHAT THIS MODULE PROTECTS

    Three invariants, none of them about syntax:

    * **ONE HOME PER LIST.** ``STATE_TRACKED_PATHS`` is the only thing that
      makes a TRACKED artifact durable, so a second copy of it (or of the sweep
      function, or of the push helper) is a second mechanism that drifts
      silently while one caller keeps staging the stale one — the #441
      claim-closure shape. ``push-wired-both-dirs`` is the same claim from the
      other side: the helper must be REACHED from both repos (state and skill),
      or half the fleet's work never leaves the box.

    * **declaration -> mechanism (``state_tracked_audit``).** The glossary is
      HQ's law surface and the list is this tool's; they have drifted five
      times. The guard parses the glossary's own ``**TRACKED**`` bullet and
      names every entry the mechanism does not carry. Four properties are
      load-bearing, and each is a leg below:

        1. an underivable bullet is a SKIP that SAYS it is "NOT a clean result"
           — "I could not compare" must never read as "I compared and found
           nothing";
        2. a declared-but-uncarried name WARNS exactly ONCE and names the gap
           (a duplicated WARN per token is noise an operator learns to skip);
        3. the declaration may live in ANY law file. The 2026-11-17 regression
           (#71): v0.4.310 moved the bullet into ``reference-glossary.md`` and a
           reader pinned to ``SKILL.md`` reported SKIP while the audit it exists
           to perform had silently stopped;
        4. the success line must NAME the file it read, or a moved declaration
           is invisible in the log even while the audit works.

    * **mechanism -> its blind spot (``state_out_of_scope_audit``, #540).** The
      inverse audit: tracked files in the state repo that NEITHER the sweep list
      NOR the glossary names. Such a file is unreachable by every commit path,
      so it can be DELETED and the sanctioned verb still reports success
      (measured live on ``runs/in-flight/<uuid>.json``). A DIRTY one is a
      finding; the untouched remainder is a COUNT, and a leg that cried wolf on
      historical mass would be muted. The ledger record is deliberately absent
      from ``STATE_TRACKED_PATHS`` and carried by ``_ledger_tracked_names``, so
      a list-only leg would falsely flag the most-committed file in the repo.

HOW THIS IS PORTED (and why it is not a rewrite of the tool)

    The shell does not exercise the audits through the CLI — it EXTRACTS the
    functions out of the tool's own source with ``awk '/^fn()/,/^}$/'`` and
    sources them against a hand-declared corpus. That is ported here as a
    READ-ONLY source assertion: the same awk range rule (``_extract``), the
    snippet written to a tmp file, and a ``bash -c`` wrapper that sources it
    with a fixture ``SKILL_DIR``, a fixture ``STATE_DIR`` and a fixture
    ``LAW_FILES`` corpus. ``tools/state/oc-ledger`` is never modified.

    The wrapper takes ``STATE_TRACKED_PATHS`` / ``STATE_TRACKED_GLOB`` by
    ``eval``-ing them OUT OF THE TOOL, exactly as the shell does — a copy of the
    list here would let the guard and its fixture drift together and agree.

    The helper trio for the inverse audit (``_is_git_repo`` +
    ``_ledger_tracked_names`` + ``state_out_of_scope_audit``) is extracted
    TOGETHER, because a snippet sourced without its helper makes every arm
    report SKIPPED and the assertions then measure a fixture that never ran
    (measured #70: four arms). Every arm below therefore also asserts that no
    ``command not found`` reached the output — the same vacuity guard, one layer
    down.

DELIBERATELY NOT PORTED

    * **(d) NO ARM — the ``[ -f "$SKILL_DIR/$src" ] || continue`` guard.** The
      shell declares this one UNPORTABLE and this module keeps the disclosure
      rather than inventing a leg: awk is silent on a missing path AND on a
      directory, so the guard changes no output and no rc. A leg asserting it
      would pass with the guard deleted — decoration, which is the defect class
      #71 exists to remove. Disclosed, not shipped as a green row that tests
      nothing.
    * ``state-tracked-carries-harvest-registry`` and the two sweep-selectivity
      legs (``state-sweep-commits-harvest-registry`` /
      ``state-sweep-still-selective``) sit in this line range but exercise
      ``state_sweep_tracked`` through ``_commit_with_retry`` — the SWEEP, not
      the structural single-source block. They need a fourth extraction
      (``_CW_ERR=`` .. ``}``) and belong with the sweep/commit-pending concern;
      left unported here rather than half-fixtured.
    * The ``#508/#80`` auto-commit-tail legs and ``commit-pending-mirror-push``
      are also in range and also out of scope: they drive the stamp/commit-
      pending verbs, not the single-source guards.
    * The two ``ok || bad`` legs inside the moved-declaration arm that merely
      re-read the fixture file (``state-tracked-audit-fixture-injected``) are
      folded into the leg that builds the fixture — same assertion, one read.

NO LEG IS ``slow``: nothing here drives ``--selftest``, sleeps, or touches the
network. Each leg is one ``bash -c`` over an extracted snippet against files in
this worker's ``scratch``.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path

import pytest

import conftest as cf
from lib import ledger as L

TOOL = cf.tool_path("oc-ledger")

# The awk range rule the shell uses, kept in one place: start at the first line
# matching ``^fn()`` and end at the first following line that is exactly ``}``.
# Faithful to awk, INCLUDING its surprise: ``_is_git_repo()`` is a ONE-LINER, so
# its range runs on to the next standalone ``}`` and carries whatever function
# follows (``ledger_ok``). Harmless, and reproducing it keeps this extraction
# identical to the shell's rather than merely equivalent for today's source.
_START = r"^%s\(\)"
_END = r"^\}$"

_SEQ = itertools.count()

# The wrapper. Mirrors the shell's ``bash -c "$_corpus"'; . fn.sh; audit'``:
# the corpus is declared BEFORE the source, the two lists are eval'd out of the
# tool, and STATE_DIR (a function in the tool) is supplied by the harness.
_SCRIPT = r"""
set -u
eval "$(grep -m1 '^STATE_TRACKED_PATHS=' "$TOOL_SRC")"
eval "$(grep -m1 '^STATE_TRACKED_GLOB=' "$TOOL_SRC")"
export STATE_TRACKED_PATHS STATE_TRACKED_GLOB
STATE_DIR() { printf '%s\n' "$SD"; }
LAW_FILES=(__CORPUS__)
. "$SNIPPET"
__CALL__
"""


def _tool_text() -> str:
    return TOOL.read_text(encoding="utf-8")


def _grep_count(pattern: str) -> int:
    """``grep -c '^<pattern>'`` over the tool — one count per matching LINE."""
    rx = re.compile("^" + re.escape(pattern), re.MULTILINE)
    return len(rx.findall(_tool_text()))


def _extract(*names: str) -> str:
    """``awk '/^name()/,/^}$/'`` for each name, in order — the shell's own rule."""
    lines = _tool_text().splitlines(True)
    out = []
    for name in names:
        start = next((i for i, ln in enumerate(lines)
                      if re.match(_START % re.escape(name), ln)), None)
        assert start is not None, (
            "extraction found no %r in %s — the awk range would have produced an "
            "EMPTY snippet, and every arm sourced from it would then report "
            "SKIPPED and measure a fixture that never ran (#70)" % (name, TOOL))
        end = next((j for j in range(start, len(lines))
                    if re.match(_END, lines[j].rstrip("\n"))), None)
        assert end is not None, (
            "extraction of %r never found its closing '}' — the awk range is "
            "unterminated and the snippet would swallow the rest of the file"
            % (name,))
        out.extend(lines[start:end + 1])
    return "".join(out)


@pytest.fixture
def snippet(scratch, run_tool):
    """Callable: ``snippet(functions, skill_dir=..., corpus=..., call=...)``.

    Writes the awk-extracted snippet to a tmp file and runs it through
    ``bash -c`` with a fixture ``SKILL_DIR`` / ``SD`` and the tool's OWN list
    variables. Returns a ``conftest.Result``.
    """
    root = Path(scratch) / "structural"

    def _run(functions, *, skill_dir, call, corpus=("SKILL.md",), sd=None,
             timeout=60):
        d = root / ("s%d" % next(_SEQ))
        d.mkdir(parents=True, exist_ok=True)
        snip = d / "fn.sh"
        snip.write_text(_extract(*functions), encoding="utf-8")
        script = (_SCRIPT
                  .replace("__CORPUS__", " ".join(corpus))
                  .replace("__CALL__", call))
        return run_tool(
            ["bash", "-c", script], timeout=timeout,
            env={"TOOL_SRC": str(TOOL), "SNIPPET": str(snip),
                 "SKILL_DIR": str(skill_dir), "SD": str(sd or d / "state")})

    return _run


def _audit_lines(res, prefix):
    return [ln for ln in res.combined.splitlines() if ln.startswith(prefix)]


def _warns(res, kind="state-tracked"):
    return _audit_lines(res, "%s: WARN" % kind)


def _assert_no_broken_snippet(res):
    """#70: a snippet missing a helper still "runs" — and measures nothing."""
    assert "command not found" not in res.combined, (
        "the extracted snippet is INCOMPLETE: a helper it calls is not in it, so "
        "the audit ran on a partial mechanism and every arm below would be "
        "measuring a fixture that never ran (#70):\n%s" % res.combined[-1200:])
    assert res.timed_out is False, "the audit leg timed out:\n%s" % res.combined


# =============================================================================
# the single-source greps — 6 of the block's 24 ``chk`` calls
# =============================================================================
SINGLE_SOURCE = [
    ("state_tracked_audit()", 1, "state-tracked-audit-single-source",
     "one declared-vs-mechanism audit; a second copy would be a guard nobody "
     "runs"),
    ("state_out_of_scope_audit()", 1, "state-out-of-scope-single-source",
     "one inverse audit (#540)"),
    ("STATE_TRACKED_PATHS=", 1, "state-tracked-single-source",
     "the whitelist has ONE home; a re-inlined copy is the #441 drift shape"),
    ("state_sweep_tracked()", 1, "state-sweep-fn-single-source",
     "one sweep implementation, reached by both callers"),
    ("push_backlog_if_due()", 1, "push-helper-single-source",
     "one push-dispatch helper (#524)"),
    ("  push_backlog_if_due ", 2, "push-wired-both-dirs",
     "the helper is CALLED from both the state and the skill tail; one call "
     "site means half the fleet's work never leaves the box"),
]


@pytest.mark.parametrize("pattern, want, name, why", SINGLE_SOURCE,
                         ids=[row[2] for row in SINGLE_SOURCE])
def test_the_list_the_sweep_and_the_push_helper_each_have_one_home(
        pattern, want, name, why):
    """Shell legs 1062-1063 / 1111-1114: the DRY counts.

    ``push-wired-both-dirs`` is anchored on the CALL-SITE indent on purpose: the
    bare pattern also matches the ``push_backlog_if_due()`` DEFINITION line, so
    an unanchored count reads 3 and the leg would assert its own source rather
    than the tool.
    """
    got = _grep_count(pattern)
    assert got == want, (
        "[%s] want %d line(s) starting %r in %s, got %d — %s"
        % (name, want, pattern, TOOL.name, got, why))


# =============================================================================
# declared-vs-mechanism: state_tracked_audit
# =============================================================================
def test_the_extracted_audit_carries_the_ledger_helper_it_calls(snippet,
                                                               scratch):
    """The #70 vacuity guard for THIS module's own fixture.

    ``state_tracked_audit`` builds its mechanism from ``_ledger_tracked_names``.
    The shell extracts the audit ALONE, so that call expands to "command not
    found" and the ledger silently drops out of the mechanism — the tool's own
    source comment records the measurement (2026-11-22: two arms reddened while
    the live tool was correct). The helper is therefore extracted WITH the audit
    and the completeness is asserted here rather than assumed.
    """
    body = _extract("state_tracked_audit", "_ledger_tracked_names")
    assert "state_tracked_audit() {" in body, (
        "[state-tracked-audit-single-source] the extraction produced no audit "
        "body — every arm below would pass on an empty fixture")
    assert "_ledger_tracked_names() {" in body, (
        "the extracted snippet omits _ledger_tracked_names, so the audit's "
        "mechanism would be missing the ledger record (#70)")

    skill = Path(scratch) / "helpercheck"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        "  - **TRACKED** — `baseline.json` ·\n", encoding="utf-8")
    res = snippet(("state_tracked_audit", "_ledger_tracked_names"),
                  skill_dir=skill, call="state_tracked_audit",
                  sd=Path(scratch) / "helpercheck" / "state")
    _assert_no_broken_snippet(res)


def test_the_skip_path_says_it_is_not_a_clean_result(snippet, scratch):
    """Shell arm (a): no ``**TRACKED**`` bullet derivable -> a SKIP that says so.

    All three halves are the point. "SKIPPED" alone is a word; "NOT a clean
    result" is the verdict an operator must not misread as a pass; and ZERO WARN
    lines is what separates a skip from a finding (a skip that also warned would
    make the two verdicts indistinguishable downstream).
    """
    skill = Path(scratch) / "skip"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text("# fixture with no TRACKED bullet\n",
                                    encoding="utf-8")
    res = snippet(("state_tracked_audit", "_ledger_tracked_names"),
                  skill_dir=skill, call="state_tracked_audit")
    _assert_no_broken_snippet(res)

    assert "SKIPPED" in res.combined, (
        "[state-tracked-audit-skip-note] an underivable bullet must report a "
        "SKIP, not silence:\n%s" % res.combined[-1200:])
    assert "NOT a clean result" in res.combined, (
        "[state-tracked-audit-skip-not-silent] the SKIP must SAY it is not a "
        "clean result — 'I could not compare' and 'I compared and found "
        "nothing' are different verdicts and only one is a reason to stop "
        "reading:\n%s" % res.combined[-1200:])
    assert _warns(res) == [], (
        "[state-tracked-audit-skip-no-warn] a SKIP is not a finding; want 0 "
        "WARN lines, got %r" % (_warns(res),))


def test_a_declared_but_uncarried_name_warns_exactly_once_and_names_the_gap(
        snippet, scratch):
    """Shell arm (b): the DISCRIMINATING half — a name the mechanism lacks.

    The bullet is WRITTEN here, never sliced out of live law text. The shell's
    old ``sed -n`` derivation coupled these legs to HQ's prose: the day the
    bullet moved, the slice came back empty and three legs went red for a law
    edit that was entirely correct. A fixture must not depend on the thing it
    is testing.

    ``bogus-new-record.json`` is carried by nothing, so exactly one WARN must
    name it. Exactly one: a per-token duplicate is noise, and a leg that only
    counted ">= 1" would stay green while the guard sprayed.
    """
    skill = Path(scratch) / "gap"
    skill.mkdir(parents=True, exist_ok=True)
    bullet = (
        "  - **TRACKED** — state-dir files under `journal/` · `baseline.json` "
        "· `bogus-new-record.json` ·\n"
        "  - **GENERATED-IGNORED** — not audited\n")
    (skill / "SKILL.md").write_text(bullet, encoding="utf-8")
    # vacuity guard: the probe must actually be in the fixture, or the WARN
    # assertion below could pass on a file this leg never wrote.
    assert "bogus-new-record.json" in (skill / "SKILL.md").read_text(), (
        "[state-tracked-audit-fixture-injected] the fixture lost its probe")

    res = snippet(("state_tracked_audit", "_ledger_tracked_names"),
                  skill_dir=skill, call="state_tracked_audit")
    _assert_no_broken_snippet(res)

    warns = _warns(res)
    assert len(warns) == 1, (
        "[state-tracked-audit-warns-once] want exactly 1 'state-tracked: WARN' "
        "line for one uncarried name, got %d: %r\n%s"
        % (len(warns), warns, res.combined[-1200:]))
    assert "bogus-new-record.json" in warns[0], (
        "[state-tracked-audit-names-the-gap] the WARN must NAME the uncarried "
        "token, or an operator has a verdict with no subject: %r" % warns[0])
    # the two CARRIED names in the same bullet must stay silent — the negative
    # control that makes "one WARN" mean the guard discriminates, not that it
    # fires once per bullet.
    assert "baseline.json" not in warns[0], (
        "[state-tracked-audit-warns-once] baseline.json IS in "
        "STATE_TRACKED_PATHS; the single WARN must be about the gap only: %r"
        % warns[0])


def test_a_declaration_in_another_law_file_is_still_found_and_named(snippet,
                                                                   scratch):
    """Shell arm (c): THE 2026-11-17 REGRESSION (#71).

    The declaration lives in a law file that is NOT ``SKILL.md``. A reader
    pinned to one filename reports SKIP here while the audit it exists to
    perform has silently stopped — the exact failure. Two assertions, and the
    second is the one that makes a moved declaration visible in the log: the
    success line must NAME the file it read.
    """
    skill = Path(scratch) / "moved"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text("# no bullet here\n", encoding="utf-8")
    (skill / "reference-glossary.md").write_text(
        "  - **TRACKED** — state-dir files under `journal/` · "
        "`baseline.json` ·\n  - **NEXT** — stop\n", encoding="utf-8")

    res = snippet(("state_tracked_audit", "_ledger_tracked_names"),
                  skill_dir=skill, call="state_tracked_audit",
                  corpus=("SKILL.md", "reference-glossary.md"))
    _assert_no_broken_snippet(res)

    assert "SKIPPED" not in res.combined, (
        "[state-tracked-audit-moved-declaration-found] the audit went blind "
        "when the declaration moved into reference-glossary.md — a reader "
        "pinned to SKILL.md reports SKIP while the audit has silently "
        "stopped:\n%s" % res.combined[-1200:])
    assert _warns(res) == [], (
        "[state-tracked-audit-moved-declaration-clean] the moved bullet's names "
        "are all carried; want 0 WARN lines, got %r" % (_warns(res),))
    assert "reference-glossary.md" in res.combined, (
        "[state-tracked-audit-names-source] the success line must NAME the law "
        "file it read, or a moved declaration is invisible in the log even "
        "while the audit works:\n%s" % res.combined[-1200:])


def test_the_ledger_record_is_carried_in_both_modes(snippet, scratch):
    """ADDED leg (not in the shell): the mechanism is MODE-AWARE.

    ``_ledger_tracked_names`` answers ``workers-ledger.json`` in legacy mode and
    ``events.jsonl workers.json`` in JSONL mode. The shell's fixtures never name
    the ledger in their bullet, so the helper's answer is never observed — and
    the tool's own comment records what that cost (2026-11-22: the audit went
    red on the LIVE tool because the helper was missing from the extraction).

    Both modes are asserted, because a helper that hardcoded one name would pass
    a legacy-only leg and flag the most-committed file in the repo after the
    #149 cutover.
    """
    root = Path(scratch) / "carried"
    root.mkdir(parents=True, exist_ok=True)
    skill = root / "skill"
    skill.mkdir(parents=True, exist_ok=True)

    for mode, declared, events in (
            ("legacy", "workers-ledger.json", False),
            ("jsonl", "events.jsonl", True)):
        sd = root / mode
        sd.mkdir(parents=True, exist_ok=True)
        if events:
            (sd / "events.jsonl").write_text("", encoding="utf-8")
        (skill / "SKILL.md").write_text(
            "  - **TRACKED** — `%s` ·\n" % declared, encoding="utf-8")
        res = snippet(("state_tracked_audit", "_ledger_tracked_names"),
                      skill_dir=skill, call="state_tracked_audit", sd=sd)
        _assert_no_broken_snippet(res)
        assert _warns(res) == [], (
            "[state-tracked-audit-names-source] %s mode: the ledger record "
            "(%s) IS carried, by _ledger_tracked_names — a WARN here means the "
            "audit cannot see its own target and reports a false gap:\n%s"
            % (mode, declared, res.combined[-1200:]))


# =============================================================================
# mechanism -> its blind spot: state_out_of_scope_audit (#540)
# =============================================================================
# The trio is extracted TOGETHER. A snippet sourced without its helper makes
# every arm report SKIPPED and the assertions then measure a fixture that never
# ran (measured #70: four arms), so each leg below also calls
# _assert_no_broken_snippet.
SCOPE_FNS = ("_is_git_repo", "_ledger_tracked_names", "state_out_of_scope_audit")


@pytest.fixture
def scope_repo(scratch):
    """A state repo in LEGACY mode with one tracked file, plus the tool's lists.

    Legacy mode (no ``events.jsonl``) is the shell's fixture too, and it is the
    mode where the ledger carrier is ``workers-ledger.json``. The base commit
    exists because the audit reads ``git ls-files``.
    """
    root = Path(scratch) / "scope" / ("r%d" % next(_SEQ))
    root.mkdir(parents=True, exist_ok=True)
    repo = L.init_repo(root / "state", files={"workers-ledger.json": "{}\n"})
    return root, repo


def _scope(snippet, repo):
    return snippet(SCOPE_FNS, skill_dir=Path(repo), call="state_out_of_scope_audit",
                   sd=repo)


def test_the_inverse_audit_skips_out_loud_when_it_cannot_compare(
        snippet, scratch, scope_repo):
    """Shell arm (a): not a git repo -> a NOTE that SAYS it is not clean.

    Same posture as the forward audit, and for the same reason: a check that
    cannot observe its failure class must not report one (#485's shape). The
    zero-WARN half is the discriminator — SKIP is not a finding.
    """
    notgit = Path(scratch) / "notgit"
    notgit.mkdir(parents=True, exist_ok=True)
    res = snippet(SCOPE_FNS, skill_dir=notgit,
                  call="state_out_of_scope_audit", sd=notgit)
    _assert_no_broken_snippet(res)

    assert "SKIPPED" in res.combined, (
        "[state-out-of-scope-skip-note] a non-repo state dir must report a "
        "SKIP:\n%s" % res.combined[-1200:])
    assert "NOT a clean result" in res.combined, (
        "[state-out-of-scope-skip-not-silent] the SKIP must say it is not a "
        "clean result:\n%s" % res.combined[-1200:])
    assert _warns(res, "state-out-of-scope") == [], (
        "[state-out-of-scope-skip-note] a SKIP is not a finding; got %r"
        % (_warns(res, "state-out-of-scope"),))


def test_a_dirty_out_of_scope_file_is_reported_as_a_finding(snippet, scope_repo):
    """Shell arm (b): THE FINDING (#540), with the vacuity guard first.

    The probe must be BOTH tracked AND dirty, or the assertion would pass
    without the fix: an out-of-scope file that was never committed is invisible
    to ``git ls-files``, and one that is clean is a count, not a finding.
    """
    _, repo = scope_repo
    probe = Path(repo) / "archive-540probe" / "thing.txt"
    L.write(probe, "probe")
    L.git(repo, "add", "archive-540probe/thing.txt")
    L.git(repo, "commit", "-q", "-m", "probe: out-of-scope tracked file (#540)")
    probe.unlink()
    # vacuity guard, mirroring the shell's: tracked and dirty.
    assert L.porcelain(repo, "archive-540probe/thing.txt").strip() != "", (
        "[state-out-of-scope-probe-not-dirty] the probe must be dirty, or the "
        "finding assertion below would pass without the fix")

    res = _scope(snippet, repo)
    _assert_no_broken_snippet(res)
    assert "archive-540probe/thing.txt" in res.combined, (
        "[state-out-of-scope-reports-dirty-out-of-scope] a tracked, DIRTY file "
        "that no commit path carries must be named — it can be deleted and the "
        "sanctioned verb still reports success (#540):\n%s"
        % res.combined[-1200:])
    assert any(ln.startswith("state-out-of-scope: WARN") for ln in
               res.combined.splitlines()), (
        "[state-out-of-scope-warns-on-dirty] the finding must be a WARN, not "
        "prose:\n%s" % res.combined[-1200:])


def test_the_ledger_record_is_not_a_false_positive(snippet, scope_repo):
    """Shell arm (c), AC3: the most-committed file must NOT be flagged.

    The ledger record is deliberately absent from ``STATE_TRACKED_PATHS`` and
    carried by ``_ledger_tracked_names`` instead, so a list-only leg would
    falsely flag the one file every mutation writes. THIS FIXTURE IS LEGACY MODE
    (no ``events.jsonl``), so the carrier is ``workers-ledger.json``; in JSONL
    mode the same arm would dirty ``events.jsonl``, because the blob is
    gitignored there and ``git ls-files`` never lists it.

    The negative control is in the same leg: the OTHER out-of-scope probe stays
    dirty, so "no mention of workers-ledger.json" cannot be bought by the audit
    printing nothing at all.
    """
    _, repo = scope_repo
    # an out-of-scope file that stays dirty — the control that the audit ran.
    probe = Path(repo) / "archive-540probe" / "thing.txt"
    L.write(probe, "probe")
    L.git(repo, "add", "archive-540probe/thing.txt")
    L.git(repo, "commit", "-q", "-m", "probe: out-of-scope tracked file (#540)")
    probe.unlink()

    ledger = Path(repo) / "workers-ledger.json"
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write("\n")
    assert L.porcelain(repo, "workers-ledger.json").strip() != "", (
        "[state-out-of-scope-ledger-probe-not-dirty] workers-ledger.json must "
        "be dirty for this leg to assert anything")

    res = _scope(snippet, repo)
    _assert_no_broken_snippet(res)
    ledger_warns = [ln for ln in res.combined.splitlines()
                    if ln.startswith("state-out-of-scope: WARN")
                    and "workers-ledger.json" in ln]
    assert ledger_warns == [], (
        "[state-out-of-scope-false-positives-on-ledger] the ledger record is "
        "carried by _ledger_tracked_names, NOT by STATE_TRACKED_PATHS; flagging "
        "it means the audit models the list instead of the union of commit "
        "paths:\n%s" % res.combined[-1200:])
    assert "archive-540probe/thing.txt" in res.combined, (
        "control: the dirty out-of-scope probe must still be reported, or the "
        "silence above is silence from a leg that never ran")


def test_clean_out_of_scope_mass_is_a_labelled_count_not_a_finding(snippet,
                                                                   scope_repo):
    """Shell arm (d): tracked-but-CLEAN out-of-scope files are historical mass.

    A leg that cried wolf on the untouched remainder would be muted — which is
    worse than no leg. The shell's first version of this arm asserted the count
    line while the fixture held NO out-of-scope file at all, so it exercised the
    all-carried arm instead and failed; the arms need separate fixtures, which
    is why this one starts from a clean repo and ADDS the mass.
    """
    _, repo = scope_repo
    keep = Path(repo) / "archive-540probe" / "keep.txt"
    L.write(keep, "kept")
    L.git(repo, "add", "archive-540probe/keep.txt")
    L.git(repo, "commit", "-q", "-m", "probe: clean out-of-scope file (#540)")

    res = _scope(snippet, repo)
    _assert_no_broken_snippet(res)
    assert _warns(res, "state-out-of-scope") == [], (
        "[state-out-of-scope-warns-when-clean] a tracked but CLEAN out-of-scope "
        "file is historical mass, not a finding; got %r"
        % (_warns(res, "state-out-of-scope"),))
    assert "not a finding" in res.combined, (
        "[state-out-of-scope-count-arm-labelled] the count must be LABELLED as "
        "a count and not a finding:\n%s" % res.combined[-1200:])


def test_the_all_carried_arm_says_what_it_checked(snippet, scope_repo):
    """Shell arm (e): nothing out of scope -> a clean line that STATES the check.

    A leg that prints nothing when clean cannot be told from one that did not
    run, which is the same silence-as-verdict defect the SKIP arms exist to
    prevent — from the other side.
    """
    _, repo = scope_repo
    res = _scope(snippet, repo)
    _assert_no_broken_snippet(res)
    assert "every one of" in res.combined, (
        "[state-out-of-scope-all-carried-arm] with no out-of-scope file the "
        "audit must still SAY what it checked:\n%s" % res.combined[-1200:])
    assert _warns(res, "state-out-of-scope") == [], (
        "the all-carried arm must not WARN; got %r"
        % (_warns(res, "state-out-of-scope"),))
