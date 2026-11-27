"""Ported: `oc-seal` — run.sh §11 (IFS multi-filter merge) and §19 (orders).

§11 is the regression for a real silent-data-loss bug: the multi-filter merge
joined filters with a SPACE instead of a PIPE, so `.sha` and
`.feature_presence` could not both survive one merge. §19 is the orders
vocabulary/purge contract.
"""

from __future__ import annotations

import json

import pytest

import conftest as cf

A = "a" * 40
B = "b" * 40


def test_seal_ifs_multifilter_merge_keeps_pipe_operators(state_dir, run_tool):
    """§11: a dry-run merge applies BOTH `.sha` AND `.feature_presence`."""
    b = state_dir / "b.json"
    o = state_dir / "o.json"
    b.write_text('{"sha":"%s","run_id":1,"name":"keep-me"}' % A)
    o.write_text('{"orders":[]}')
    s = B

    res = run_tool([str(cf.tool_path("oc-seal")),
                    "--baseline", str(b), "--orders", str(o),
                    "--sha", s, "--run-id", "42", "--marker", "width=1600",
                    "--found", "1", "--dry-run"], timeout=120)
    assert res.rc == 0, "seal merge exit=%s (expected 0)\n%s" % (res.rc, res.combined[-600:])

    merged = json.loads(res.out)
    assert merged.get("sha") == s, "IFS merge lost .sha: %r" % merged.get("sha")
    fp = merged.get("feature_presence", {}).get("width=1600", {})
    assert fp.get("found") == 1, \
        "IFS merge lost .feature_presence: %r" % merged.get("feature_presence")


def test_seal_orders_vocabulary_and_purge(state_dir, run_tool):
    """§19: status-only mark, uppercased vocabulary, per-row evidence, the
    legacy `order_sha` row, the default DISPATCHED status, a rejected BOGUS
    vocabulary, purge-by-sha, and purge of an unknown sha -> 1."""
    tool = str(cf.tool_path("oc-seal"))
    orders = state_dir / "orders.json"
    orders.write_text(json.dumps({"orders": [
        {"sha": A, "features": "telegram", "status": "queued"},
        {"order_sha": B, "status": "dispatched", "run_id": "7"},
    ]}) + "\n")

    res = run_tool([tool, "--orders", str(orders), "--mark-order", A,
                    "--status", "deployed", "--order-evidence", "PID 1 disk==proc"],
                   timeout=120)
    assert res.rc == 0, "status-only mark rejected\n%s" % res.combined[-400:]

    doc = json.loads(orders.read_text())
    assert doc["orders"][0]["status"] == "DEPLOYED", \
        "vocabulary not uppercased/stored: %r" % doc["orders"][0]["status"]
    assert doc["orders"][0]["evidence"] == "PID 1 disk==proc", "per-row evidence missing"

    assert run_tool([tool, "--orders", str(orders), "--mark-order", B,
                     "--with-run", "99"], timeout=120).rc == 0
    doc = json.loads(orders.read_text())
    assert doc["orders"][1]["run_id"] == "99", "legacy order_sha row not markable"
    assert doc["orders"][1]["status"] == "DISPATCHED", \
        "default status wrong: %r" % doc["orders"][1]["status"]

    assert run_tool([tool, "--orders", str(orders), "--mark-order", A,
                     "--status", "BOGUS"], timeout=120).rc == 1, \
        "BOGUS accepted by the vocabulary"

    assert run_tool([tool, "--orders", str(orders), "--purge-order", B],
                    timeout=120).rc == 0
    assert len(json.loads(orders.read_text())["orders"]) == 1, "purge did not remove the row"

    assert run_tool([tool, "--orders", str(orders), "--purge-order", B],
                    timeout=120).rc == 1, "purge of an unknown sha was not refused"
