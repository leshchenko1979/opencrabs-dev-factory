"""`unified-log wire (real tool -> tmp log)`.

Three claims, each with a control:

* a REAL tool invocation writes exactly one JSONL row whose tool/exit/args agree
  with the run;
* the two tools #739 found UNLOGGED (oc-vendor-drift, oc-claims-single-source)
  now write a row — asserted as the ROW, never the source line;
* the bare-`selftest` arm is TOOL-SCOPED (#749b): oc-drift-check's first
  positional is a session uuid and `selftest` is legal there, so a real check
  must LOG; re-adding the tool to the declaration must make the row VANISH.

The control in the second block is the whole point: a leg that only checks "the
log is non-empty" passes for a tool that logs even when told not to.
"""

from __future__ import annotations

import json

import pytest

import conftest as cf

# The #739 pair and the argv each needs to reach its logging path.
WIRE_739 = [
    ("oc-vendor-drift", []),
    ("oc-claims-single-source", ["--scan", str(cf.TOOLS_DIR / "audit")]),
]


def _rows(log):
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text().splitlines() if x.strip()]


def test_attrib_writes_one_wire_row(scratch, run_tool, state_dir, git_repo):
    """§7 first block: one JSONL line, with tool/exit/args agreeing."""
    repo = git_repo()
    wd = scratch.path / "wire"
    wd.mkdir()
    log = wd / "tools.log"

    res = run_tool([str(cf.tool_path("oc-attrib")),
                    "--repo", str(repo.path), "--range", "main"], timeout=180,
                   env={"OC_TOOLS_NOLOG": "0", "OC_TOOLS_LOG": str(log)})
    # rc 0 = normal; rc 4 = empty range, which is tool-correct on a degenerate
    # range (a single-commit fixture has no range to walk).
    assert res.rc in (0, 4), "wire leg: rc=%s\n%s" % (res.rc, res.combined[-500:])

    rows = _rows(log)
    assert len(rows) == 1, "wire: %d JSONL line(s), want 1" % len(rows)
    r = rows[0]
    assert r["tool"] == "oc-attrib", "wire tool=%r" % r.get("tool")
    assert r["exit"] == res.rc, "wire exit=%r, actual rc=%s" % (r.get("exit"), res.rc)
    assert "--range" in r["args"], "wire args=%r" % r.get("args")


@pytest.mark.parametrize("tool,argv", WIRE_739, ids=[c[0] for c in WIRE_739])
def test_previously_unlogged_tools_write_a_row(tool, argv, scratch, run_tool):
    """#739: the ROW is written, and OC_TOOLS_NOLOG=1 suppresses it."""
    d = scratch.path / ("wire-" + tool)
    d.mkdir()
    log = d / "tools.log"

    run_tool([str(cf.tool_path(tool)), *argv], timeout=300,
             env={"OC_TOOLS_NOLOG": "0", "OC_TOOLS_LOG": str(log),
                  "OC_ACTOR": "battery-wire-739"})
    rows = [r for r in _rows(log)
            if r.get("tool") == tool and r.get("actor") == "battery-wire-739"]
    assert rows, "%s wrote NO unified-log row (#739)" % tool

    ctl = d / "ctl.log"
    run_tool([str(cf.tool_path(tool)), *argv], timeout=300,
             env={"OC_TOOLS_NOLOG": "1", "OC_TOOLS_LOG": str(ctl)})
    assert not (ctl.exists() and ctl.stat().st_size), \
        "CONTROL DEAD (#739): OC_TOOLS_NOLOG=1 still wrote a row for %s" % tool


@pytest.mark.skipif(not (cf.TOOLS_DIR / "lib" / "oc-log.sh").is_file(),
                    reason="lib/oc-log.sh absent")
def test_bare_selftest_arm_is_tool_scoped(scratch, run_tool):
    """#749b: the declared bare-arm list EQUALS the real set of arms, and a real
    check whose uuid reads 'selftest' still logs."""
    declared = run_tool(
        ["bash", "-c",
         '. "$1/lib/oc-log.sh"; printf "%s" "$OC_LOG_BARE_SELFTEST_TOOLS_DEFAULT"',
         "_", str(cf.TOOLS_DIR)], timeout=60)
    assert declared.rc == 0, declared.combined
    decl = sorted(declared.out.split())

    # the real set: every oc-* carrying a `selftest)` / `--selftest)` case arm
    actual = run_tool(
        ["bash", "-c",
         r"""grep -rlE '^[[:space:]]*(--selftest\|)?selftest(\|--selftest)?\)' "$1" --include='oc-*' 2>/dev/null \
             | grep -vE '/(lib|tests|archive)/|\.bak' | xargs -r -n1 basename | sort -u""",
         "_", str(cf.TOOLS_DIR)], timeout=120)
    act = sorted(actual.out.split())

    assert decl == act, \
        "bare-selftest list != the real arms (#749b): declared=%s actual=%s" % (
            decl, act)

    d = scratch.path / "selftest-arm"
    d.mkdir()
    real = d / "real.log"
    run_tool([str(cf.TOOLS_DIR / "state" / "oc-drift-check"), "selftest"],
             timeout=300,
             env={"OC_TOOLS_NOLOG": "0", "OC_TOOLS_LOG": str(real)})
    assert real.exists() and real.stat().st_size, \
        "a real check whose uuid reads 'selftest' wrote NO row (#749b)"

    ctl = d / "ctl.log"
    run_tool([str(cf.TOOLS_DIR / "state" / "oc-drift-check"), "selftest"],
             timeout=300,
             env={"OC_TOOLS_NOLOG": "0", "OC_TOOLS_LOG": str(ctl),
                  "OC_LOG_BARE_SELFTEST_TOOLS": " oc-drift-check "})
    assert not (ctl.exists() and ctl.stat().st_size), \
        ("CONTROL DEAD (#749b): re-adding the tool to the list did NOT suppress "
         "the row -- the leg above is vacuous")
