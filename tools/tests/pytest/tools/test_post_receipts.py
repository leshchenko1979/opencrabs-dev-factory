"""Ported: `oc-post-receipts` (§14) and `oc-upstream-delta` (§27).

Two small sections that the RC table does NOT cover, folded here so the README's
"Not ported" row is not a false inventory.

§14 is the more interesting one: the tool maps a forum TOPIC to a
``(chat_id, message_thread_id)`` pair, and the defect it pins is that it used to
pass the bare topic as ``chat_id`` — which Telegram answers with a 400. Both
directions are asserted, because "the right mapping appears" alone would pass a
tool that emits BOTH the correct pair and the broken one.

§27 is one leg: a repo path that does not exist is rc 2, not a crash and not a
silent empty delta. A zero here would be the "confident zero" class — the same
shape §60 records for ``oc-snap reap``.
"""

from __future__ import annotations

import pytest

import conftest as cf

POST_RECEIPTS = cf.TOOLS_DIR / "archive" / "oc-post-receipts"
UPSTREAM = cf.TOOLS_DIR / "harvest" / "oc-upstream-delta"

FORUM_CHAT = "-100777000111"
TOPIC = "30129"


# =============================================================================
# §14 — oc-post-receipts
# =============================================================================
def test_topic_maps_to_chat_and_thread(run_tool):
    """The correct pair is emitted: ``chat_id=<forum> -d message_thread_id=<topic>``."""
    res = run_tool([str(POST_RECEIPTS), "--dry-run", "--topic", TOPIC,
                    "--text", "mapping"], timeout=120,
                   env={"OC_FORUM_CHAT_ID": FORUM_CHAT})
    assert res.rc == 0, "dry-run rc=%s\n%s" % (res.rc, res.combined[-600:])
    want = "chat_id=%s -d message_thread_id=%s" % (FORUM_CHAT, TOPIC)
    assert want in res.combined, (
        "topic->chat/thread mapping missing (want %r in the dry-run output):\n%s"
        % (want, res.combined[-900:]))


def test_topic_is_never_passed_as_chat_id(run_tool):
    """The regression half: the bare topic must not appear as ``chat_id``.

    Telegram answers a bare topic in ``chat_id`` with a 400, so this is the
    defect that made the mapping necessary. Asserted separately from the pair
    above because a tool that emits BOTH would pass that leg alone.
    """
    res = run_tool([str(POST_RECEIPTS), "--dry-run", "--topic", TOPIC,
                    "--text", "mapping"], timeout=120,
                   env={"OC_FORUM_CHAT_ID": FORUM_CHAT})
    assert "-d chat_id=%s" % TOPIC not in res.combined, (
        "the bare topic is STILL used as chat_id (Telegram 400 regression):\n%s"
        % res.combined[-900:])


def test_plain_dry_run_is_rc0(run_tool):
    res = run_tool([str(POST_RECEIPTS), "--dry-run", "--topic", TOPIC,
                    "--text", "suite-triggered"], timeout=120)
    assert res.rc == 0, "plain dry-run rc=%s\n%s" % (res.rc, res.combined[-600:])


def test_receipt_artifact_dry_run_is_rc0(run_tool):
    res = run_tool([str(POST_RECEIPTS), "--receipt-artifact",
                    "--unit", "oc-restart-suite", "--dry-run"], timeout=120)
    assert res.rc == 0, "receipt-artifact dry-run rc=%s\n%s" % (
        res.rc, res.combined[-600:])


def test_bad_args_are_rc3(run_tool):
    """This tool's usage error is rc 3, not the fleet's 2 — its own contract."""
    res = run_tool([str(POST_RECEIPTS), "--bogus"], timeout=120)
    assert res.rc == 3, "oc-post-receipts --bogus rc=%s, want 3\n%s" % (
        res.rc, res.combined[-600:])


# =============================================================================
# §27 — oc-upstream-delta
# =============================================================================
@pytest.mark.parametrize("repo", ["/nonexistent-repo-path", "/tmp/definitely-not-a-repo-zzz"])
def test_bad_repo_path_is_rc2(repo, run_tool):
    """A repo path that does not exist is a usage error (rc 2) — never a delta of
    zero rows, which would read as "upstream has nothing new"."""
    res = run_tool([str(UPSTREAM), "--repo", repo], timeout=180)
    assert res.rc == 2, "oc-upstream-delta --repo %s rc=%s, want 2\n%s" % (
        repo, res.rc, res.combined[-600:])
