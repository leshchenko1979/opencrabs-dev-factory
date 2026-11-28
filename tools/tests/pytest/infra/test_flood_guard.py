"""The three flood-guard sections — `flood guard reads both ts forms (#738)`,
`flood guard counts matches, not jq lines (#770)`, `flood guard ignores verdict
rcs (#68-follow-up)`.

Battery sections 4-6. Each leg drives the REAL guard out of lib/oc-log.sh against
a seeded tools log, because the defect in each case was that the guard's own
instrument was wrong — a re-derived count would reproduce the bug instead of
catching it.
"""

from __future__ import annotations

import json
import re
import time

import pytest

import conftest as cf

LIB = str(cf.TOOLS_DIR / "lib" / "oc-log.sh")


def _guard_rc(run_tool, log, tool, args, timeout=60):
    """Run the real oc_log_flood_guard against `log`; return (rc, stderr)."""
    script = ('. "$1/lib/oc-log.sh"; OC_LOG_TOOL="$2"; OC_LOG_ARGS="$3"; '
              'oc_log_flood_guard')
    res = run_tool(["bash", "-c", script, "_", str(cf.TOOLS_DIR), tool, args],
                   timeout=timeout, env={"OC_TOOLS_LOG": str(log)})
    return res.rc, res.err


def _seed(log, rows):
    """rows: [(tool, exit, args, ts_suffix)] — one JSONL row each."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    with open(log, "w") as fh:
        for tool, code, args, suffix in rows:
            fh.write(json.dumps({
                "ts": stamp + suffix, "tool": tool, "actor": "x",
                "args": args, "exit": code, "secs": 0.1, "extra": {},
            }) + "\n")


# =============================================================================
# section 4 — the ts parser reads BOTH log forms (#738)
# =============================================================================
def test_ts_parser_maps_both_forms(scratch, run_tool):
    """#738: the shared OC_LOG_JQ_TS fragment maps `Z` and `+00:00` to the same
    epoch, and the naive read is proven blind to the offset form."""
    res = run_tool(["bash", "-c", '. "$1/lib/oc-log.sh"; printf "%s" "$OC_LOG_JQ_TS"',
                    "_", str(cf.TOOLS_DIR)], timeout=60)
    assert res.rc == 0, res.combined
    frag = res.out

    def epoch(ts):
        r = run_tool(["jq", "-n", "--arg", "t", ts, frag + "{ts:$t} | ts_epoch"],
                     timeout=60)
        return r.out.strip()

    assert epoch("2026-10-01T12:00:00Z") == "1790856000"
    assert epoch("2026-10-01T12:00:00+00:00") == "1790856000"

    naive = run_tool(["jq", "-n", "--arg", "t", "2026-10-01T12:00:00+00:00",
                      '{ts:$t} | (.ts // "" | fromdateiso8601? // 0)'], timeout=60)
    assert naive.out.strip() == "0", \
        "control: the naive read did NOT drop the +00:00 form (leg does not discriminate)"


@pytest.mark.parametrize("suffix", ["Z", "+00:00"])
def test_flood_guard_trips_on_both_ts_forms(scratch, run_tool, suffix):
    """#738 behavioural: 4 prior identical failing rows in EITHER form -> rc 8."""
    log = scratch.path / ("fg-%s.log" % suffix.replace(":", "").replace("+", "p"))
    _seed(log, [("oc-fg", 7, "--same", suffix)] * 4)
    rc, err = _guard_rc(run_tool, log, "oc-fg", "--same")
    assert rc == 8, "flood guard BLIND to the %r form: rc=%s (%s)" % (suffix, rc, err)


# =============================================================================
# section 5 — the guard counts MATCHES, not jq LINES (#770)
# =============================================================================
def test_flood_guard_boundary_and_banner(scratch, run_tool):
    """#770: 3 rows -> rc 0 (no false positive), 4 rows -> rc 8, and the banner
    reports the ROW count (4x), not the pretty-printed line count (36x)."""
    log = scratch.path / "fg-boundary.log"

    _seed(log, [("oc-fg", 7, "fg-same", "Z")] * 3)
    rc3, _ = _guard_rc(run_tool, log, "oc-fg", "fg-same")
    assert rc3 == 0, "flood guard FALSE-POSITIVE: 3 prior rows -> rc %s" % rc3

    _seed(log, [("oc-fg", 7, "fg-same", "Z")] * 4)
    rc4, _ = _guard_rc(run_tool, log, "oc-fg", "fg-same")
    assert rc4 == 8, "flood guard blind to a real storm: 4 prior rows -> rc %s" % rc4

    _, err = _guard_rc(run_tool, log, "oc-fg", "fg-same")
    assert "failed 4x" in err, (
        "flood guard banner miscounts: %r (expected 'failed 4x'; 36x = the "
        "pretty-print bug)" % err.strip()[:80])


# =============================================================================
# section 6 — the guard ignores a tool's declared VERDICT rc (#68-follow-up)
# =============================================================================
@pytest.mark.parametrize("tool,code,args,want", [
    ("oc-ledger", 1, "vf-same", 0),        # (1) declared verdict -> no arm
    ("oc-ledger", 7, "vf-same", 8),        # (2) same tool, real failure -> arm
    ("oc-verify-job", 1, "vf-same", 8),    # (3) unlisted tool's rc 1 -> arm
])
def test_flood_guard_verdict_rc_scope(scratch, run_tool, tool, code, args, want):
    """#68-follow-up: the three legs are a SET — any one alone passes on a
    broken guard."""
    log = scratch.path / ("vf-%s-%d.log" % (tool, code))
    _seed(log, [(tool, code, args, "Z")] * 4)
    rc, err = _guard_rc(run_tool, log, tool, args)
    assert rc == want, "%s rc %d x4 -> rc %s (want %s): %s" % (
        tool, code, rc, want, err.strip()[:120])


def test_verdict_rc_list_agrees_with_contract(run_tool):
    """The list must not outlive the contract it is derived from: every entry
    needs an RC-CONTRACT.md row declaring rc 1 as a benign OUTCOME."""
    res = run_tool(["bash", "-c",
                    '. "$1/lib/oc-log.sh"; printf "%s" "$OC_LOG_VERDICT_RCS_DEFAULT"',
                    "_", str(cf.TOOLS_DIR)], timeout=60)
    assert res.rc == 0, res.combined
    const = res.out.strip()

    script = r'''
import re, sys
path, const = sys.argv[1], sys.argv[2]
rows = {}
for ln in open(path):
    if not ln.startswith('| oc-'):
        continue
    c = [x.strip() for x in ln.strip().strip('|').split('|')]
    if len(c) < 4:
        continue
    rows[c[0]] = (c[2], '|'.join(c[3:]))
FAILW = re.compile(r'fail|error|refus|denied|unable|abort|crash|not\s+found', re.I)
NEG = re.compile(r'\b(?:not\s+an?|no)\s+(?:error|failure|fault)\b', re.I)
bad = []
if not FAILW.search('a close FAILED'):
    bad.append("detector INERT: does not flag the historical entry 'a close FAILED'")
else:
    if FAILW.search(NEG.sub('', 'a finding (verdict, not an error)')):
        bad.append("negation-blind: reads a DISCLAIMER as an assertion")
    if not FAILW.search(NEG.sub('', 'not an error, a close FAILED')):
        bad.append("negation strip over-reached: swallowed an asserted 'FAILED'")
for ent in const.split():
    tool = ent.split(':')[0]
    if tool not in rows:
        bad.append("%s: no RC-CONTRACT row" % tool); continue
    usage, verdict = rows[tool]
    m = re.search(r'(?:^|/)\s*1\s+([^/]*)', verdict)
    if not m:
        bad.append("%s: contract does not declare rc 1 as an outcome" % tool)
    elif usage == '1':
        bad.append("%s: contract declares rc 1 as a USAGE code" % tool)
    elif FAILW.search(NEG.sub('', m.group(1))):
        bad.append("%s: contract's rc 1 is a FAILURE (%r), not a benign verdict"
                   % (tool, m.group(1).strip()[:40]))
print('; '.join(bad))
'''
    r = run_tool(["python3", "-c", script,
                  str(cf.TOOLS_DIR / "docs" / "RC-CONTRACT.md"), const], timeout=120)
    assert r.out.strip() == "", \
        "verdict-rc list DRIFTED from the contract: %s" % r.out.strip()


_NAIVE_RE = re.compile(r'\.ts // "" \| fromdateiso8601')


@pytest.mark.parametrize("rel", ["lib/oc-log.sh", "harvest/oc-gate"])
def test_no_naive_ts_read_in_code(rel):
    """The ts read must go through the shared parser; comments may QUOTE the
    naive form, so the detector reads CODE only and is paired with the positive."""
    f = cf.TOOLS_DIR / rel
    assert f.is_file(), "%s missing" % rel
    code = "\n".join(ln for ln in f.read_text().splitlines()
                     if not ln.lstrip().startswith("#"))
    assert not _NAIVE_RE.search(code), \
        "%s keeps a naive ts read in code" % rel
    assert "OC_LOG_JQ_TS" in f.read_text(), \
        "%s does not reference OC_LOG_JQ_TS" % rel


def test_naive_ts_detector_fires(scratch):
    """CONTROL: the detector flags a re-introduced naive ts read."""
    c = scratch.path / "naive.jq"
    c.write_text('    | ((.ts // "" | fromdateiso8601? // 0)) | select(. >= $cutoff)\n')
    assert _NAIVE_RE.search(c.read_text()), \
        "control: detector is blind to a naive ts read"
