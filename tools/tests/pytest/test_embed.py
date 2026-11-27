"""Ported: `lib/oc-embed.sh (job-name embed decoder)` — run.sh §12.

Pure unit coverage of the two decoders, sourced straight out of the library.
The asymmetry they pin is load-bearing: `oc_decode_job_embed` requires the
`(<sha>, <features>)` two-field form, `oc_decode_job_sha_any` accepts the bare
gate-mode `(<sha>)` too — because `run_built_sha` takes the FIRST job name that
decodes, so the ORDER-gates job must NOT decode as a build.
"""

from __future__ import annotations

import pytest

import conftest as cf

LIB = str(cf.TOOLS_DIR / "lib" / "oc-embed.sh")
SHA = "a" * 40
SHA2 = "b" * 40
REAL_SHA = "5140b36a0d8b2015eeea27ecbe18a46cc7d6e0c8"

EMBED_CASES = [
    # (label, job name, expected)
    ("well-formed job name -> sha|features",
     "Linux amd64 (%s, telegram)" % SHA, "%s|telegram" % SHA),
    ("comma feature set survives",
     "Linux amd64 (%s, local-stt,local-tts)" % SHA2, "%s|local-stt,local-tts" % SHA2),
    ("ORDER job without embed -> empty",
     "ORDER gates / validate (no embed here)", ""),
    ("non-40-hex parenthetical -> empty",
     "Linux amd64 (shortsha, x)", ""),
    ("caller-prefixed job name -> sha|features",
     "ship / Linux amd64 (%s, telegram)" % SHA, "%s|telegram" % SHA),
    ("caller-prefixed, sha without a feature list -> empty",
     "gate / PR-lane gates (%s)" % SHA2, ""),
    ("real ship-lane build job name (run 35612234852)",
     "ship / Linux amd64 (%s, telegram,code-graph,browser)" % REAL_SHA,
     "%s|telegram,code-graph,browser" % REAL_SHA),
    ("prefixed ORDER-gates job is NOT decodable",
     "ship / ORDER gates (%s)" % REAL_SHA, ""),
    ("prefixed PR-lane gates job is NOT decodable",
     "ship / PR-lane gates (%s)" % REAL_SHA, ""),
]

ANY_CASES = [
    ("bare gates-job form -> sha",
     "gate / PR-lane gates (%s)" % SHA, SHA),
    ("two-field build-job form -> sha (features dropped)",
     "ship / Linux amd64 (%s, telegram)" % SHA2, SHA2),
    ("no embed -> empty",
     "ORDER gates / validate (no embed here)", ""),
    ("non-40-hex parenthetical -> empty",
     "Linux amd64 (shortsha, x)", ""),
]


def test_embed_lib_syntax(run_tool):
    """`embed-lib syntax (bash -n)`."""
    res = run_tool(["bash", "-n", LIB], timeout=60)
    assert res.rc == 0, res.combined


def _decode(fn, name, run_tool):
    script = '. "$1"; %s "$2"' % fn
    res = run_tool(["bash", "-c", script, "_", LIB, name], timeout=60)
    assert res.rc == 0, "%s exited %s on %r: %s" % (fn, res.rc, name, res.combined[-300:])
    # `$(...)` in run.sh strips the trailing newline the sed arm emits.
    return res.out.rstrip("\n")


@pytest.mark.parametrize("label,name,want", EMBED_CASES,
                         ids=[c[0][:38].replace(" ", "-") for c in EMBED_CASES])
def test_oc_decode_job_embed(label, name, want, run_tool):
    assert _decode("oc_decode_job_embed", name, run_tool) == want, label


@pytest.mark.parametrize("label,name,want", ANY_CASES,
                         ids=[c[0][:38].replace(" ", "-") for c in ANY_CASES])
def test_oc_decode_job_sha_any(label, name, want, run_tool):
    assert _decode("oc_decode_job_sha_any", name, run_tool) == want, label
