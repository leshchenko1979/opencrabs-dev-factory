"""Ported: `oc-issue-dispatch` role-binding edge cases — run.sh §51.

The section exists because ``run_selftest oc-issue-dispatch`` counts ONE case
however many asserts the tool makes internally. The crash that actually cost a
probing cycle was invisible to it, so it is pinned here against the SHIPPED
module instead of the suite's opinion of itself.

Two defects are frozen:

1. **A lane dict with no ``raw`` key.** ``get_worker_roster`` builds lanes as
   ``{uuid,topic,topic_id,feature,class,claims,worktrees,is_busy,raw}`` and
   carries the ROLE at ``raw["role"]``. Code that read ``lane["role"]`` raised
   ``KeyError`` on every lane the roster produces — a dispatch that dies before
   it scores anything (fork #342, task 17).
2. **The role binding is IDENTITY, not prose.** A surface owner outranks a lane
   whose feature string merely lists every keyword. Delete ``ROLE_DOMAINS`` and
   this leg goes red, which is the point: the binding is the thing being tested,
   not the scoring formula.

The module is imported IN PROCESS with ``sys.dont_write_bytecode`` set BEFORE
the loader runs, so the shared checkout stays byte-identical — the same reason
run.sh's heredoc does it (a stray ``__pycache__`` in ``tools/issue/`` is an
untracked path that would set ``tree_changed`` on every receipt).
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-issue-dispatch")

@pytest.fixture(scope="module")
def dispatch():
    """The SHIPPED module, loaded by path without touching the checkout."""
    saved = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        loader = importlib.machinery.SourceFileLoader("oid_ported", str(TOOL))
        spec = importlib.util.spec_from_loader("oid_ported", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = saved
    return mod

# The issue the edge cases score against: a tools/ CLI bug, which is the
# toolsmith's domain.
ISSUE = {
    "number": 451,
    "title": "fix(tools): oc-issue-dispatch hangs",
    "body": "the culprit is tools/issue/oc-issue-dispatch",
}

LANE_NO_RAW = {"uuid": "e1", "feature": "general editor",
               "is_busy": False, "class": "ACTIVE"}
LANE_RAW_NONE = {"uuid": "e2", "feature": "general editor",
                 "is_busy": False, "class": "ACTIVE", "raw": None}
LANE_RAW_EMPTY = {"uuid": "e3", "feature": "general editor",
                  "is_busy": False, "class": "ACTIVE", "raw": {}}

@pytest.mark.parametrize("lane", [LANE_NO_RAW, LANE_RAW_NONE, LANE_RAW_EMPTY],
                         ids=["no-raw-key", "raw-none", "raw-empty"])
def test_score_affinity_survives_a_lane_without_raw(dispatch, lane):
    """#342 task 17: the roster's own lane shape must score, not raise.

    Every lane ``get_worker_roster`` builds carries the role at ``raw["role"]``,
    so a missing/None/empty ``raw`` is a lane the tool WILL see in production.
    A ``KeyError`` here is a dispatch that dies before it scores anything.
    """
    try:
        got = dispatch.score_affinity(ISSUE, lane)
    except Exception as exc:  # noqa: BLE001 — the assertion IS "does not raise"
        pytest.fail("score_affinity raised on a lane with %r: %r"
                    % (lane.get("raw", "<absent>"), exc))
    assert isinstance(got, int), \
        "score_affinity returned %r, want an int" % type(got)

def test_role_owner_outranks_a_verbose_editor(dispatch):
    """The binding is live in the shipped file.

    A toolsmith lane that OWNS ``tools/`` must beat an editor lane whose feature
    string happens to list every keyword in the issue. If ``ROLE_DOMAINS`` were
    deleted, prose would win and this goes red — which is what makes it a test
    of the binding rather than of the scoring formula.
    """
    owner = {"uuid": "e4", "is_busy": False, "class": "ACTIVE",
             "feature": "TOOLSMITH lane: owns tools/ CLI (oc-ledger, oc-fanout)",
             "raw": {"role": "toolsmith"}}
    verbose = {"uuid": "e5", "is_busy": False, "class": "ACTIVE",
               "feature": ("harvest upstream port census sweep notify queue "
                           "delivery router cli exec"),
               "raw": {"role": "editor"}}
    assert dispatch.score_affinity(ISSUE, owner) > dispatch.score_affinity(ISSUE, verbose), \
        ("the role-bound owner did not outrank the verbose editor on a tools/ "
         "issue — ROLE_DOMAINS is no longer reaching the score")

def test_role_owned_domains_reads_raw_not_top_level(dispatch):
    """The accessor that all of the above depends on.

    ``role_owned_domains`` must read ``raw["role"]`` and tolerate its absence.
    Asserting it directly names the fault when the scoring legs go red, instead
    of leaving a KeyError traceback to interpret.
    """
    owner = dict(LANE_RAW_EMPTY, raw={"role": "toolsmith"})
    assert dispatch.role_owned_domains(owner), \
        "role_owned_domains returned nothing for a toolsmith lane"
    assert dispatch.role_owned_domains(LANE_NO_RAW) == set(), \
        "role_owned_domains must be empty for a lane with no role, not raise"
