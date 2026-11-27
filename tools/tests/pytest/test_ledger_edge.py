"""Ported: `oc-ledger` edge legs — run.sh §24 (empty-events fixture, usage) and
§32 (the confirm/derive-by stub).

``run_selftest oc-ledger`` already proves the tool's own 418 cases, and it costs
296 s — the single most expensive section in the battery. These legs are the
BESPOKE ones that sit beside it, and they exist because the selftest's own
fixture is not the shape a lane's shell produces:

* The selftest's ledger already holds events; the real battery fixture starts
  from ``"events":[]``. A stamp that numbers from the wrong base writes ``n=0``
  into an empty log and every later reader that trusts ``n`` reads a row that
  cannot exist.
* ``stamp`` REFUSES an anonymous row (#19), so a fixture without an actor does
  not assert "stamp works" — it asserts rc 2 and reports green for it. The
  actor is therefore load-bearing, not decoration.

Nothing here runs the 296 s selftest: these are single-invocation legs against a
sandbox ledger, which is why the module is seconds rather than minutes.
"""

from __future__ import annotations

import json

import pytest

import conftest as cf

TOOL = cf.tool_path("oc-ledger")

def test_first_stamp_into_an_empty_ledger_is_n_1(ledger_sandbox, run_tool):
    """The bespoke fixture: an EMPTY events array, then one stamp -> n=1.

    Numbering from 0 would make the first row indistinguishable from "no row",
    which is the reading every consumer of ``n`` takes.
    """
    res = run_tool([str(TOOL), "stamp", "note", "battery edge"], timeout=180)
    assert res.rc == 0, "stamp rc=%s\n%s" % (res.rc, res.combined[-800:])

    ledger = json.loads(ledger_sandbox.ledger.read_text())
    events = ledger.get("events") or []
    assert events, "the stamp wrote no event into the ledger"
    assert events[-1]["n"] == 1, \
        ("the first stamp into an empty ledger is n=%r, want 1 (a 0 or a gap "
         "makes the row unreadable to every consumer of n)" % events[-1].get("n"))

def test_unknown_subcommand_is_usage_rc2(ledger_sandbox, run_tool):
    res = run_tool([str(TOOL), "frobnicate"], timeout=120)
    assert res.rc == 2, \
        "unknown subcommand: rc=%s, want 2 (usage)\n%s" % (
            res.rc, res.combined[-600:])

def test_stamp_refuses_an_anonymous_row(ledger_sandbox, run_tool):
    """#19: a stamp with no actor is rc 2, never a nameless row.

    This is asserted rather than assumed because it is what makes
    ``ledger_sandbox``'s fixed ``OC_ACTOR`` necessary: a fixture that dropped it
    would report green on a refusal.
    """
    # BOTH identities must be blank: the tool reads
    # `${OPENCRABS_SESSION_ID:-${OC_ACTOR:-}}`, so clearing one still leaves an
    # actor and the leg would assert a refusal it never provoked.
    res = run_tool([str(TOOL), "stamp", "note", "anonymous"],
                   timeout=120,
                   env={"OC_ACTOR": "", "OPENCRABS_SESSION_ID": ""})
    assert res.rc != 0, \
        ("an anonymous stamp was ACCEPTED (#19) — a row with no actor cannot be "
         "attributed:\n%s" % res.combined[-600:])
