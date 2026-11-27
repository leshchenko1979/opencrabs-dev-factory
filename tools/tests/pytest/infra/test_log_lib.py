"""Ported: `lib/oc-log.sh (unified tools log)`, `oc_log.py consumers stay
retired (#760)`, `one availability definition in oc-issue-dispatch (#310)`.

These are run.sh sections 1-3. Every leg is a direct port of an `ok`/`bad`
assertion; the comment above each test names the original claim so a reader can
diff it against run.sh without guessing.
"""

from __future__ import annotations

import json
import re

import pytest

import conftest as cf

DEMO = """#!/usr/bin/env bash
set -u
source "$(dirname "$0")/lib/oc-log.sh"
oc_log_init "oc-demo" "$@"
trap 'oc_log_finish $?' EXIT
rc="${1:-0}"
case "$rc" in --selftest|selftest) rc=0 ;; esac
exit "$rc"
"""


@pytest.fixture
def demo(scratch):
    """The oc-demo fixture from run.sh:1112-1122 — a tool that only logs."""
    d = scratch.path / "loglib"
    (d / "lib").mkdir(parents=True, exist_ok=True)
    (d / "lib" / "oc-log.sh").write_text(
        (cf.TOOLS_DIR / "lib" / "oc-log.sh").read_text())
    exe = d / "oc-demo"
    exe.write_text(DEMO)
    exe.chmod(0o755)
    return d


def _log_env(log, **extra):
    env = {"OC_TOOLS_NOLOG": "0", "OC_TOOLS_LOG": str(log)}
    env.update(extra)
    return env


# =============================================================================
# section 1 — lib/oc-log.sh
# =============================================================================
def test_oc_log_sh_syntax(run_tool):
    """`lib syntax (bash -n)`."""
    res = run_tool(["bash", "-n", str(cf.TOOLS_DIR / "lib" / "oc-log.sh")],
                   timeout=60)
    assert res.rc == 0, res.combined


def test_oc_log_sh_row_shape_and_suppression(demo, run_tool):
    """`exactly 2 lines: exit0 + exit7 (--selftest suppressed)` + the three
    JSONL legs + `OC_TOOLS_NOLOG=1 suppresses`."""
    log = demo / "tools.log"
    env = _log_env(log)
    assert run_tool([str(demo / "oc-demo"), "0"], timeout=60, env=env).rc == 0
    assert run_tool([str(demo / "oc-demo"), "7", "--some-arg"],
                    timeout=60, env=env).rc == 7
    # --selftest must write no row
    assert run_tool([str(demo / "oc-demo"), "--selftest"],
                    timeout=60, env=env).rc == 0

    lines = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    assert len(lines) == 2, "expected 2 lines, got %d" % len(lines)

    assert any(r["tool"] == "oc-demo" and r["exit"] == 0 for r in lines)
    seven = [r for r in lines if r["exit"] == 7]
    assert seven and "--some-arg" in seven[0]["args"]
    for r in lines:
        assert {"ts", "secs", "extra"} <= set(r), "schema fields missing"

    # OC_TOOLS_NOLOG=1 suppresses even without --selftest
    run_tool([str(demo / "oc-demo"), "3"], timeout=60,
             env=_log_env(log, OC_TOOLS_NOLOG="1"))
    assert len(log.read_text().splitlines()) == 2, "env suppression failed"


def test_oc_log_sh_bare_selftest_is_tool_scoped(demo, run_tool):
    """M2-21: a bare `selftest` subcommand suppresses ONLY for a declared tool,
    and a `selftest` VALUE elsewhere does not suppress a real invocation."""
    l2 = demo / "tools2.log"
    run_tool([str(demo / "oc-demo"), "selftest"], timeout=60,
             env=_log_env(l2, OC_LOG_BARE_SELFTEST_TOOLS=" oc-demo "))
    assert not (l2.exists() and l2.stat().st_size), \
        "bare 'selftest' subcommand logged a row (M2-21)"

    l3 = demo / "tools3.log"
    run_tool([str(demo / "oc-demo"), "0", "selftest"], timeout=60,
             env=_log_env(l3, OC_LOG_BARE_SELFTEST_TOOLS=" oc-demo "))
    assert len(l3.read_text().splitlines()) == 1, \
        "a non-first 'selftest' silenced a real invocation (M2-21)"


def test_oc_log_sh_oc_has(scratch, run_tool):
    """#537: `oc_has` is a SIGPIPE-free literal substring test — 7 cases plus
    the 2 MB payload and the single-definition leg."""
    out = scratch.path / "oc_has.out"
    script = r'''
set -u; set -o pipefail
. "$1/lib/oc-log.sh"
r() { if oc_has "$2" "$3"; then g=0; else g=1; fi
      if [ "$g" = "$4" ]; then printf "ok %s\n" "$1"
      else printf "FAIL %s (want=%s got=%s)\n" "$1" "$4" "$g"; fi; }
r present       "the fix is in origin/main"    "origin/main"            0
r absent        "the fix is in origin/main"    "nowhere"                1
r parens        "Draft: true (--draft) here"   "Draft: true (--draft)"  0
r space         "state backlog=11 (>= 10) now" "backlog=11 (>= 10)"     0
r empty         "anything at all"              ""                       0
r metachar      "a*b?c[d] literal"             "*b?c[d]"                0
r glob-literal  "plain text"                   "*"                      1
'''
    res = run_tool(["bash", "-c", script, "_", str(cf.TOOLS_DIR)], timeout=60)
    fails = [ln for ln in res.out.splitlines() if ln.startswith("FAIL")]
    assert not fails, "oc_has: " + "; ".join(fails)
    assert len([ln for ln in res.out.splitlines() if ln.startswith("ok")]) == 7

    big = r'''
set -u; set -o pipefail
. "$1/lib/oc-log.sh"
big="$(printf "HIT\n"; head -c 2000000 /dev/zero | tr "\0" "x")"
oc_has "$big" HIT && echo MATCH || echo MISS
'''
    res = run_tool(["bash", "-c", big, "_", str(cf.TOOLS_DIR)], timeout=120)
    assert res.out.strip() == "MATCH", \
        "2 MB payload with newline after match -> %r" % res.out.strip()

    src = (cf.TOOLS_DIR / "lib" / "oc-log.sh").read_text()
    assert len(re.findall(r"(?m)^oc_has\(\)", src)) == 1, \
        "oc_has: definition count is not 1"


def test_oc_log_sh_rotation_is_bounded(demo, run_tool):
    """#80: under the cap NOT rotated; over it rotated to one generation; and
    the rotation runs INSIDE the append's flock."""
    rot = demo / "rot"
    rot.mkdir()
    log = rot / "t.log"

    def rotate():
        return run_tool(
            ["bash", "-c", '. "$1"; oc_log_rotate "$2"', "_",
             str(cf.TOOLS_DIR / "lib" / "oc-log.sh"), str(log)],
            timeout=60, env={"OC_TOOLS_LOG_MAX_BYTES": "100"})

    log.write_text("aaaa\n")
    assert rotate().rc == 0
    assert log.exists() and not (rot / "t.log.1").exists(), \
        "#80: an under-cap log was rotated -- the bound truncates live history"

    log.write_bytes(b"x" * 400)
    assert rotate().rc == 0
    assert (rot / "t.log.1").exists() and log.stat().st_size == 0, \
        "#80: over-cap log did not rotate"

    src = (cf.TOOLS_DIR / "lib" / "oc-log.sh").read_text()
    assert len(re.findall(r"(?m)^oc_log_rotate\(\)", src)) == 1, \
        "#80: oc_log_rotate definition count is not 1"
    assert 'oc_log_rotate "$logf"; printf' in src, \
        "#80: rotation is not inside the locked append"


# =============================================================================
# section 2 — oc_log.py consumers stay retired (#760)
# =============================================================================
_PRIVATE_RE = re.compile(r"^def (oc_log_init|_oc_log_flood_guard|_is_selftest)\(", re.M)
_CONSUMES_RE = re.compile(r"(^|\s)(from oc_log import|import oc_log)", re.M)


@pytest.mark.parametrize("rel", ["issue/oc-census", "issue/oc-issue-dispatch"])
def test_oc_log_py_consumers_stay_retired(rel):
    """#760: each consumer IMPORTS the shared module and defines no private copy."""
    f = cf.TOOLS_DIR / rel
    assert f.is_file(), "%s missing" % rel
    text = f.read_text()
    assert _CONSUMES_RE.search(text), "%s no longer imports tools/lib/oc_log.py" % rel
    m = _PRIVATE_RE.search(text)
    assert not m, "%s re-defines a private log copy: %s" % (rel, m.group(0))


def test_oc_log_py_private_copy_detector_fires(scratch):
    """CONTROL: the detector flags a re-introduced private copy."""
    c = scratch.path / "private-copy.py"
    c.write_text("def oc_log_init(tool):\n    pass\n")
    assert _PRIVATE_RE.search(c.read_text()), \
        "control: detector is blind to a private copy"


# =============================================================================
# section 3 — one availability definition in oc-issue-dispatch (#310)
# =============================================================================
_310_FALLBACK_RE = re.compile(r'class"\] in \("ACTIVE",\s*"IDLE"\).*is_busy')


def test_issue_dispatch_has_one_availability_definition():
    """#310: no class-filtered availability path survives in the shipped tool."""
    f = cf.TOOLS_DIR / "issue" / "oc-issue-dispatch"
    assert f.is_file(), "issue/oc-issue-dispatch missing"
    m = _310_FALLBACK_RE.search(f.read_text())
    assert not m, ("oc-issue-dispatch re-introduced a class-filtered "
                   "availability path: %s" % m.group(0))


def test_issue_dispatch_availability_detector_fires(scratch):
    """CONTROL: the detector flags a re-introduced class-filtered fallback."""
    c = scratch.path / "fallback.py"
    c.write_text('        available = [lane for lane in candidate_lanes if '
                 'lane["class"] in ("ACTIVE", "IDLE") and not lane["is_busy"]]\n')
    assert _310_FALLBACK_RE.search(c.read_text()), \
        "control: detector is blind to a class-filtered fallback"
