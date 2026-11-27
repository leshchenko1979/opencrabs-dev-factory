"""Ported: `oc-notify-fanout` guards — run.sh §46 (law 1, dead targets, --roles).

The section exists because the tool's own ``--selftest`` counts ONE case however
many assertions it makes internally: a wave that reaches nobody while reporting
success is invisible to it. Three legs, each a different way a wave LOOKS clean
and is not:

* **61a law 1 — placeholder-token guard.** A brief that still carries ``{{TOK}}``
  after substitution is a brief no lane can act on. Every send must ABORT and the
  wave must exit non-zero. The failure it prevents is the quiet one: ``sent=N``
  while every lane received a literal ``{{NOSUCH}}``.
* **61b substitution.** ``{{UUID}}`` / ``{{VERSION}}`` must resolve and no ABORT
  may fire. The twin of 61a, so "fix 61a by deleting the guard" reddens here.
* **61c ``--roles``.** With the invoker's own role as the only selector, the wave
  must reach NOBODY: the roster row matches, and self-exclusion is what keeps it
  from being sent to. A leg using ``--roles editor`` cannot tell those apart.

The tool's own ``--selftest`` is NOT driven here (factory #203) — see the SCOPE
note at the end of this file for why and where it went.

**Counters are read as FIELDS, never substrings.** ``absent=1`` CONTAINS
``sent=1``, so the shell's ``grep -q 'sent=1'`` arm is satisfied by a wave that
merely disclosed an absence — it can never go red in exactly the case it was
written for (measured 2026-11-21: mutation M3 drove ``sent`` to 2 and the
substring arm still passed). ``_field`` anchors on a key boundary.

**DEVIATION from run.sh, deliberate: this port touches NO live state.** The shell
section resolves the invoker with ``oc-ledger roster --live`` and points
``OC_FANOUT_LEDGER`` at the LIVE fleet ledger, so each of its four legs writes
real fleet state and its verdict depends on which lanes exist on the box today.
Here the invoker is a fixture uuid, the roster is a fixture JSON and the session
DB is a throwaway, so the same four claims hold on any box and no leg can flip
because a lane was retired. ``OC_FANOUT_RUN_DIR`` is redirected as well: the
tool's production default is ``<skill>/run`` and the wave id is DERIVED FROM THE
BRIEF TEXT, so two concurrent instances collide on one lock there (the 2026-11-21
``rc 7``/``rc 4`` class the tool's own selftest comment records).
"""

from __future__ import annotations

import json
import re
import sqlite3

import pytest

import conftest as cf

NF = cf.tool_path("oc-notify-fanout")

FORUM = "-1999999999"

LANE_1 = "11111111-1111-4111-8111-111111111111"   # editor
LANE_2 = "22222222-2222-4222-8222-222222222222"   # editor
LANE_T = "33333333-3333-4333-8333-333333333333"   # toolsmith — the invoker

# Matches no real lane, so a leaked self can never silently exclude someone.
SELF_ABSENT = "00000000-0000-4000-8000-00000000dead"


def _field(name, text):
    """The LAST ``name=N`` in the tool's output, or ``None``.

    Anchored on a key boundary: ``absent=1`` must not satisfy a ``sent`` check.
    """
    hits = re.findall(r"(?:^|\s)%s=(\d+)" % re.escape(name), text, re.M)
    return int(hits[-1]) if hits else None


@pytest.fixture
def wave(tmp_path):
    """A fan-out sandbox: fixture roster, throwaway session DB, isolated run dir.

    Built under ``tmp_path``, NOT ``scratch``: the scratch root is SESSION-scoped,
    so a fixed subdirectory name is reused across tests and the second
    ``CREATE TABLE sessions`` lands in an existing DB (the same trap ``git_repo``
    documents for named repos).

    Three live sessions, all bound to one forum chat, so ``--roles`` is the only
    thing that can shrink the target set — ``sent=3`` reached everyone and
    ``sent=0`` reached nobody.
    """
    root = tmp_path / "notify-fanout"
    root.mkdir(parents=True, exist_ok=True)

    db = root / "sessions.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT, archived_at INTEGER,
                       updated_at INTEGER DEFAULT 0);
CREATE TABLE session_bindings (session_id TEXT PRIMARY KEY, channel TEXT,
                               chat_id TEXT, thread_id INTEGER,
                               updated_at INTEGER DEFAULT 0);
INSERT INTO sessions VALUES ('%s','lane1',NULL,strftime('%%s','now'));
INSERT INTO sessions VALUES ('%s','lane2',NULL,strftime('%%s','now'));
INSERT INTO sessions VALUES ('%s','toolsmith',NULL,strftime('%%s','now'));
INSERT INTO session_bindings VALUES ('%s','telegram','%s',1,0);
INSERT INTO session_bindings VALUES ('%s','telegram','%s',2,0);
INSERT INTO session_bindings VALUES ('%s','telegram','%s',3,0);
""" % (LANE_1, LANE_2, LANE_T, LANE_1, FORUM, LANE_2, FORUM, LANE_T, FORUM))
    con.commit()
    con.close()

    ledger = root / "roster.json"
    ledger.write_text(json.dumps({"workers": [
        {"uuid": LANE_1, "role": "editor", "topic_id": 1},
        {"uuid": LANE_2, "role": "editor", "topic_id": 2},
        {"uuid": LANE_T, "role": "toolsmith", "topic_id": 3},
    ], "events": []}, indent=1) + "\n")

    run_dir = root / "run"
    run_dir.mkdir()

    return cf.Node(root, db=db, ledger=ledger, run_dir=run_dir)


def _env(wave, self_uuid=SELF_ABSENT, **extra):
    """Every path inline; nothing inherited from the fleet."""
    env = {
        "OC_FANOUT_LEDGER": str(wave.ledger),
        "OC_NOTIFY_DB": str(wave.db),
        "OC_FANOUT_FORUM_CHAT": FORUM,
        "OC_FANOUT_SELF": self_uuid,
        "OC_FANOUT_RUN_DIR": str(wave.run_dir),
        "OC_TOOLS_NOLOG": "1",
    }
    env.update(extra)
    return env


def _wave(run_tool, wave, *argv, self_uuid=SELF_ABSENT):
    return run_tool([str(NF), *argv], timeout=200,
                    env=_env(wave, self_uuid=self_uuid))


# =============================================================================
# 61a. law 1 — a dangling token ABORTs every send
# =============================================================================
def test_dangling_placeholder_aborts_every_send(run_tool, wave):
    """A brief carrying ``{{NOSUCH}}`` must not reach one lane, and the wave
    must not exit 0: a green rc here is the silent-delivery defect."""
    res = _wave(run_tool, wave, "--title", "t-battery",
                "--text", "dangling {{NOSUCH}} token",
                "--dry-run", "--no-stamp")

    assert res.rc != 0, (
        "law 1: rc=0 on a brief whose placeholder SURVIVED substitution — every "
        "lane would have received a literal {{NOSUCH}}:\n%s"
        % res.combined[-900:])
    assert "placeholder-token-survived" in res.combined, (
        "the wave aborted but emitted no law-1 receipt, so an operator cannot "
        "tell a guard from a crash:\n%s" % res.combined[-900:])
    assert _field("sent", res.combined) == 0, (
        "law 1 aborted on paper yet counted sent=%s:\n%s"
        % (_field("sent", res.combined), res.combined[-900:]))
    assert _field("failed", res.combined) == 3, (
        "want failed=3 (one ABORT per target), got %s:\n%s"
        % (_field("failed", res.combined), res.combined[-900:]))
    assert "DRY " not in res.combined, (
        "a target reached a DRY receipt after the law-1 abort — the guard fired "
        "per-target and the wave carried on:\n%s" % res.combined[-900:])


# =============================================================================
# 61b. substitution — valid tokens resolve, nothing aborts
# =============================================================================
def test_valid_tokens_substitute_and_nothing_aborts(run_tool, wave):
    """The twin of 61a: deleting the guard to make 61a pass reddens THIS leg."""
    res = _wave(run_tool, wave, "--title", "t-battery",
                "--text", "v{{VERSION}} u{{UUID}}",
                "--dry-run", "--no-stamp")

    assert res.rc == 0, "substitution rc=%s\n%s" % (res.rc, res.combined[-900:])
    assert "placeholder-token-survived" not in res.combined, (
        "{{UUID}}/{{VERSION}} were NOT substituted — the guard fired on legal "
        "tokens:\n%s" % res.combined[-900:])
    assert _field("sent", res.combined) == 3, (
        "want sent=3 (every forum-bound lane), got %s:\n%s"
        % (_field("sent", res.combined), res.combined[-900:]))
    assert _field("failed", res.combined) == 0, (
        "a dry wave reported failed=%s with no dead targets in the roster:\n%s"
        % (_field("failed", res.combined), res.combined[-900:]))


# =============================================================================
# 61c. --roles — self is excluded, so a toolsmith wave reaches nobody
# =============================================================================
def test_roles_filter_excludes_the_invoking_lane(run_tool, wave):
    """``--roles toolsmith`` from the toolsmith itself: the roster HAS a matching
    row and the wave must still reach nobody.

    This is what separates "the filter works" from "the filter matched and
    self-exclusion works" — with ``--roles editor`` a broken self-exclusion would
    still read sent=2, so the toolsmith is the discriminating choice.
    """
    res = _wave(run_tool, wave, "--title", "t", "--text", "x",
                "--dry-run", "--no-stamp", "--roles", "toolsmith",
                self_uuid=LANE_T)

    assert res.rc == 0, "roles rc=%s\n%s" % (res.rc, res.combined[-600:])
    assert _field("sent", res.combined) == 0, (
        "self was NOT excluded: a toolsmith-only wave sent to %s lane(s):\n%s"
        % (_field("sent", res.combined), res.combined[-900:]))
    assert _field("skipped", res.combined) == 0, (
        "the self-excluded lane was counted as SKIPPED (%s) — self-exclusion is a "
        "filter, not a per-target skip, and conflating them inflates every wave's "
        "skip count:\n%s" % (_field("skipped", res.combined), res.combined[-900:]))

# =============================================================================
# SCOPE — what this module deliberately does NOT do
# =============================================================================
# The shell section also carried ``run_selftest oc-notify-fanout``. That leg is
# deleted here (factory #203): ``tools/test_tool_wrappers.py`` drives the same
# ``--selftest`` as one parametrised case, slow-marked, at a measured 266 s.
# Driving it twice buys one extra ``rc == 0`` and costs four and a half minutes
# of every full run. The blanket owns "the selftest exits 0"; this module owns
# the three claims the selftest cannot make about itself — which is the whole
# reason it exists.
