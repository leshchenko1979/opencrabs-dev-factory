"""Ported: `lib/oc_claims.py (canonical claim-closure predicate)` — run.sh §13.

The original is a 347-line heredoc driving the shipped module as a unit: the
predicate was inlined four times and the copies drifted (#313/#314), so these
cases pin the exact properties the drift broke. Ported 1:1 — the module is
imported directly and each `chk(...)` becomes one assert.

The one leg that read live state in run.sh (`order_commits_parents_first` over
`/root/opencrabs` commit shas) is rebuilt on a fixture repo: the property under
test is "output is parents-first and input-order-independent", which a local
3-commit chain demonstrates exactly, without a production checkout.
"""

from __future__ import annotations

import os
import sys

import pytest

import conftest as cf

sys.dont_write_bytecode = True


@pytest.fixture(scope="module")
def oc():
    lib = str(cf.TOOLS_DIR / "lib")
    sys.path.insert(0, lib)
    try:
        import oc_claims  # noqa: F401  (imported for the fixture)
    finally:
        sys.path.remove(lib)
    return oc_claims


def test_oc_claims_syntax():
    """`oc_claims-lib syntax (ast.parse)` — ast.parse, never py_compile: a .pyc
    beside the module would dirty the shared checkout."""
    import ast

    src = (cf.TOOLS_DIR / "lib" / "oc_claims.py").read_text()
    ast.parse(src)


# =============================================================================
# issue_ref_tokens — TOKEN extraction, never a substring or digit run (#272)
# =============================================================================
@pytest.mark.parametrize("text,want", [
    ("CLAIM #129 — x", [129]),
    ("stamped 2026-09-15", []),
    ("leshchenko1979/opencrabs#52", [52]),
    ("commit 262193f67 landed", []),
    ("session 6630dc9a-0eeb", []),
    ("claims issue 94", [94]),
    ("issue=4242 task", [4242]),
    ("issue#77", [77]),
    ("#38, #80 — multi", [38, 80]),
    ("upstream opencrabs/opencrabs#1419 filed", [1419]),
    ("upstream adolfousier/opencrabs#1419 filed", [1419]),
    ("factory leshchenko1979/opencrabs-dev-factory#344", [344]),
    ("upstream acme/widgets#1419 filed", []),
    ("fork leshchenko1979/opencrabs#52", [52]),
    ("see tools/lib/oc_claims.py issue 379", [379]),
])
def test_issue_ref_tokens(oc, text, want):
    assert oc.issue_ref_tokens(text) == want


def test_references_is_token_exact(oc):
    """`ref 760 is not 76` / `ref 760 matches 760`."""
    assert oc.references("#760", 76) is False
    assert oc.references("#760", 760) is True


def test_issue_ref_tokens_are_ints(oc):
    """type uniformity — the drift bug was str tokens compared to int tokens."""
    assert all(isinstance(t, int) for t in oc.issue_ref_tokens("CLAIM #129, issue 94"))


# =============================================================================
# primary_issue_tokens — what a claim CLAIMS (#329)
# =============================================================================
@pytest.mark.parametrize("text,want", [
    ("CLAIM #129 — x", [129]),
    ("CLAIM #327 — filed, one live break (#323)", [327]),
    ("filed fragility class issue (#327): 14 bodies, one proven live break (#323)", [327]),
    ("CLAIM #193, #205 — harvest packaging", [193, 205]),
    ("CLAIM #193, #205", [193, 205]),
    ("CLAIM #1414/#1418 — pair", [1414, 1418]),
    ("CLAIM #302 — backfill (supersedes #290, #297)", [302]),
    ("md-plane wave lane claims n=1675 PATH-2 execution: upstream issue "
     "opencrabs/opencrabs#1419 filed FIRST", [1419]),
    ("CLAIM acme/widgets#1419 only", []),
    ("Issue-Ref leshchenko1979/opencrabs#1419", [1419]),
    ("CLAIM #400 - upstream opencrabs/opencrabs#1419", [400]),
    ("Claimed compaction-signal feature: Issue-Ref "
     "leshchenko1979/opencrabs#29 (mirror of #1256)", [29]),
    ("no refs here", []),
    ("x #5 y #6 z", [5]),
])
def test_primary_issue_tokens(oc, text, want):
    assert oc.primary_issue_tokens(text) == want


def test_primary_is_subset_of_all_refs(oc):
    text = "CLAIM #12 — see #13 and #14"
    assert set(oc.primary_issue_tokens(text)) <= set(oc.issue_ref_tokens(text))


# =============================================================================
# actor_key / actor_match
# =============================================================================
@pytest.mark.parametrize("by,want", [
    ("editor 1a63f103-1234-5678-9abc-def012345678",
     ("uuid", "1a63f103-1234-5678-9abc-def012345678")),
    ("toolsmith/2fae1230", ("uuid", "2fae1230")),
    ("lamp-lane", ("label", "lamp-lane")),
    ("editor-14", ("label", "14")),
])
def test_actor_key(oc, by, want):
    assert oc.actor_key(by) == want


@pytest.mark.parametrize("a,b,want", [
    ("editor 2fae1230", "toolsmith 2fae1230-aaaa-bbbb-cccc-dddddddddddd", True),
    ("editor 2fae1230", "editor-14", False),
    ("editor 11111111", "editor 22222222", False),
    ("editor-", "editor-", False),
])
def test_actor_match(oc, a, b, want):
    assert oc.actor_match(a, b) is want


# =============================================================================
# is_addressed — anchored at the START of what (the #305 fence)
# =============================================================================
@pytest.mark.parametrize("what,iss,want", [
    ("#71 — released", 71, True),
    ("STANDDOWN #71 (11111111) — shipped", 71, True),
    ("#2 — closed-issue stale claim sweep", 2, True),
    ("UNCLAIM #72 — stood down in favour of editor lane X", 72, False),
    ("note: see #264 for detail", 264, False),
    ("#710 — x", 71, False),
    ("issue #29 close-out: upstream PR filed", 29, True),
    ("Issue #24 mechanical notify fan-out LANDED", 24, True),
    ("reopened issue #75 — still open", 75, False),
    ("issue #29 close-out: supersedes #75", 75, False),
])
def test_is_addressed(oc, what, iss, want):
    assert oc.is_addressed(what, iss) is want


# =============================================================================
# is_unattributed sentinels
# =============================================================================
@pytest.mark.parametrize("by,want", [
    ("(unattributed)", True),
    ("unrostered-actor 6630dc9a", True),
    ("editor 11111111", False),
])
def test_is_unattributed(oc, by, want):
    assert oc.is_unattributed(by) is want


# =============================================================================
# open_claims — the canonical rule, all three signals
# =============================================================================
EV = [
    {"n": 1, "t": "t1", "by": "editor 11111111", "kind": "claim",
     "what": "CLAIM #1 — same-author closure"},
    {"n": 2, "t": "t2", "by": "editor 11111111", "kind": "done", "what": "DONE #1 — own row"},
    {"n": 3, "t": "t3", "by": "editor 22222222", "kind": "claim",
     "what": "CLAIM #2 — addressed closure by another lane"},
    {"n": 4, "t": "t4", "by": "triage 33333333", "kind": "unclaim",
     "what": "#2 — closed-issue stale claim sweep"},
    {"n": 5, "t": "t5", "by": "editor 44444444", "kind": "claim",
     "what": "CLAIM #3 — foreign prose must NOT release"},
    {"n": 6, "t": "t6", "by": "triage 33333333", "kind": "unclaim",
     "what": "UNCLAIM #99 — stood down in favour of editor lane 44444444"},
    {"n": 7, "t": "t7", "by": "(unattributed)", "kind": "claim", "what": "CLAIM #4 — unattributed"},
    {"n": 8, "t": "t8", "by": "editor 55555555", "kind": "confirm",
     "what": "CONFIRM #4 — any lane closes an unattributed claim"},
    {"n": 9, "t": "t9", "by": "editor 66666666", "kind": "claim",
     "what": "CLAIM #5 — non-closing kind must not close"},
    {"n": 10, "t": "t10", "by": "editor 66666666", "kind": "note",
     "what": "NOTE #5 — not a closing kind"},
]


def test_open_claims_survivors_and_filters(oc):
    assert sorted(c["n"] for c in oc.open_claims(EV)) == [5, 9]
    assert sorted(c["n"] for c in oc.open_claims(EV, 3)) == [5]
    assert oc.open_claims(EV, 1) == []


def test_open_claims_tokens_are_ints_and_refless_skipped(oc):
    assert all(isinstance(t, int) for c in oc.open_claims(EV) for t in c["tokens"])
    assert oc.open_claims([{"n": 1, "by": "editor 11111111", "kind": "claim",
                            "what": "CLAIM without a ref"}]) == []


# --- open_claims targets the ADDRESS, not every reference (#329) -------------
PHA = [{"n": 1, "by": "editor 11111111", "kind": "claim",
        "what": "CLAIM #327 — filed, one proven live break (#323)"}]


def test_open_claims_targets_the_address(oc):
    assert oc.open_claims(PHA, 323) == []
    assert sorted(c["tokens"] for c in oc.open_claims(PHA)) == [[327]]


@pytest.mark.parametrize("what,issues,want", [
    ("CLAIM #5 — mentions #6", [5], [[5]]),
    ("CLAIM #5, #6", [5, 6], [[5, 6]]),
    ("CLAIM #5 — x", [], [[5]]),
    ("CLAIM #5 — x", ["5", None, "junk"], [[5]]),
])
def test_open_claims_structured_issues_field(oc, what, issues, want):
    row = [{"n": 1, "by": "editor 11111111", "kind": "claim",
            "what": what, "issues": issues}]
    assert sorted(c["tokens"] for c in oc.open_claims(row)) == want


def test_open_claims_legacy_keys(oc):
    """legacy schema fallback: note/actor instead of what/by."""
    leg = [{"n": 1, "actor": "editor 11111111", "type": "claim",
            "note": "CLAIM #7 — legacy keys"}]
    assert len(oc.open_claims(leg)) == 1


# =============================================================================
# #307 anchored Issue-Ref resolution: the TRAILER, never prose
# =============================================================================
@pytest.fixture
def claims_repo(git_repo):
    """The #307 fixture: prose mentions in subject AND body, a real fork
    trailer, a third-party-slug trailer, and a binary-tracker trailer."""
    repo = git_repo("claims307")

    def commit(fname, msg, *extra):
        (repo.path / fname).write_text(fname + "\n")
        repo.git("add", "-A")
        repo.git("commit", "-q", "-m", msg, *extra)

    commit("prose.txt", "fix(x): reword the note (#701)")
    commit("bodyprose.txt", "fix(w): plain subject",
           "-m", "This mentions #704 in the body prose only.")
    commit("anchored.txt", "fix(y): real work", "--trailer", "Issue-Ref: #702")
    commit("thirdparty.txt", "fix(z): third-party work",
           "--trailer", "Issue-Ref: acme/widgets#703")
    commit("binary.txt", "fix(b): binary-tracker work",
           "--trailer", "Issue-Ref: opencrabs/opencrabs#705")
    return repo


def test_issue_ref_resolution_is_trailer_anchored(oc, claims_repo):
    repo = str(claims_repo.path)
    assert oc.resolve_issue_commits(repo, 701) == []
    assert oc.resolve_issue_files(repo, 701) == []
    assert oc.resolve_issue_commits(repo, 704) == []
    assert oc.resolve_issue_files(repo, 704) == []
    assert oc.resolve_issue_files(repo, 702) == ["anchored.txt"]
    assert oc.resolve_issue_files(repo, 703) == []
    # v0.4.284 positive control: a binary-tracker trailer IS ours and anchors.
    assert oc.resolve_issue_files(repo, 705) == ["binary.txt"]


def test_order_commits_parents_first_is_input_independent(oc, git_repo):
    """run.sh read three shas out of /root/opencrabs; the property is
    parents-first + input-order-independent, which a local chain shows exactly."""
    repo = git_repo("order-chain")
    shas = []
    for i in range(3):
        (repo.path / ("f%d.txt" % i)).write_text("%d\n" % i)
        repo.git("add", "-A")
        repo.git("commit", "-q", "-m", "c%d" % i)
        shas.append(repo.git("rev-parse", "HEAD").stdout.strip())
    want = shas  # oldest first
    assert oc.order_commits_parents_first(str(repo.path), shas) == want
    assert oc.order_commits_parents_first(str(repo.path), list(reversed(shas))) == want


# =============================================================================
# soak anchor basis disclosure (#315)
# =============================================================================
def test_soak_anchor_basis(oc):
    assert oc.soak_anchor_fields("abc1234", 1759276800).split()[0] == "soak_basis=swap"
    assert oc.soak_anchor_fields("abc1234", 1759276800, "commit").split()[0] == \
        "soak_basis=commit"
    assert oc.soak_anchor_fields("abc1234", 0, "unresolved").split()[0] == \
        "soak_basis=unresolved"


def test_soak_anchor_triple_survives(oc):
    a = oc.soak_anchor_fields("abc1234", 1759276800)
    assert ("anchor_commit=abc1234" in a and "anchor_deployed_ts=" in a
            and "eligible_at=" in a)


def test_classify_soak_anchor_branches(oc, monkeypatch):
    monkeypatch.delenv("OC_HARVEST_MOCK_DEPLOYED_TS", raising=False)
    _, age, note = oc.classify_soak_anchor(
        "deadbeef", 1759276800, lambda sha, ts: 0, [], 1759363200)
    assert "soak_basis=commit" in note
    assert round(age, 1) == 24.0
    _, uage, unote = oc.classify_soak_anchor("", 0, lambda sha, ts: 0, [], 1759363200)
    assert "soak_basis=unresolved" in unote
    assert uage is None


# =============================================================================
# #356 upstream-side reader: slug-qualified only
# =============================================================================
@pytest.mark.parametrize("value,want", [
    ("leshchenko1979/opencrabs#356", [356]),
    ("#356", []),
    ("opencrabs/opencrabs#356", []),
    ("acme/widgets#356", []),
])
def test_parse_issue_ref_value_require_slug(oc, value, want):
    assert oc.parse_issue_ref_value(value, home_slugs=(oc.FORK_SLUG,),
                                    require_slug=True) == want


@pytest.mark.parametrize("value,want", [
    ("#356", [356]),
    ("leshchenko1979/opencrabs#356", [356]),
])
def test_parse_issue_ref_value_default_reader(oc, value, want):
    """Positive controls: the new parameter must not disable the old contract."""
    assert oc.parse_issue_ref_value(value) == want


# =============================================================================
# #301 squash_signature: three arms over %H%x1f%s%x1f%P%x1f%b%x1e
# =============================================================================
def _rec(sha, subj, parents, body=""):
    return "%s\x1f%s\x1f%s\x1f%s" % (sha, subj, parents, body)


@pytest.mark.parametrize("records,want", [
    ([_rec("a" * 40, "fix(x): y (#1556)", "p1")], {1556: "a" * 40}),
    ([_rec("b" * 40, "Merge PR #1557", "p1")], {1557: "b" * 40}),
    ([_rec("c" * 40, "feat(t): dedup (#133)", "p1",
           "Squashed from PR #1556.\n\nCloses #1556")],
     {133: "c" * 40, 1556: "c" * 40}),
    ([_rec("d" * 40, "Merge branch (#999)", "p1 p2")], {}),
    ([_rec("e" * 40, "fix(x): y (#1556)", "p1", "Squashed from PR #1556")],
     {1556: "e" * 40}),
    ([_rec("f" * 40, "plain commit", "p1", "no keywords")], {}),
    (["", "\x1f\x1f", "   "], {}),
])
def test_squash_signature(oc, records, want):
    assert oc.squash_signature(records) == want
