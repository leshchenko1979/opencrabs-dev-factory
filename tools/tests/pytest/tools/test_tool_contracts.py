"""The usage/`--help` contract cluster.

Six sections, one shape: ``run_selftest <tool>`` plus a ``--bogus`` → rc 2 and a
``--help`` → rc 0. They are folded into one module because the claim is the same
one six times, and six one-line files would be six places to drift.

Two things here are NOT boilerplate:

* **``--help`` must exit 0 AND write to STDOUT.** The rc leg alone cannot see the
  defect #748a recorded: twelve tools printed usage to STDERR while rc stayed 0,
  so ``tool --help | grep flag`` found nothing and every rc-only check passed.
  ``test_help_goes_to_stdout`` is the leg that catches that, and §43 owns the
  fleet-wide version of it.
* **``oc-census`` and ``oc-claims-single-source`` are PYTHON, not bash.** Running
  them through ``bash <tool>`` dies at the first ``import`` line with rc 2 — which
  is the SAME rc as "unknown argument", so a bash-invoked leg passes the usage
  assertion for the wrong reason while the tool never ran. The selftest legs
  below therefore invoke them directly, and the fixture asserts the shebang so a
  future bash-ification is caught rather than silently mis-run.
"""

from __future__ import annotations

import pytest

import conftest as cf

# (section, tool-path relative to tools/, selftest bound)
CONTRACTS = [
    ("48", "audit/oc-watcher-audit", 400),
    ("49", "git/oc-start", 400),
    ("50", "smoke/oc-smoke", 400),
    ("52", "audit/oc-lint-laws", 400),
    ("55", "issue/oc-census", 400),
    ("56", "audit/oc-claims-single-source", 400),
    ("29", "state/oc-drift-check", 400),
]

IDS = ["s%s-%s" % (s, p.split("/")[1]) for s, p, _ in CONTRACTS]


@pytest.mark.parametrize("section,rel,bound", CONTRACTS, ids=IDS)
def test_unknown_arg_is_rc2(section, rel, bound, run_tool):
    """§<section>: an unknown flag is a usage error, rc 2, on every one of the six.

    Invoked through the tool's own interpreter, which is what makes this leg
    meaningful for the two Python tools (see the module docstring)."""
    res = run_tool([str(cf.TOOLS_DIR / rel), "--bogus"], timeout=120)
    assert res.rc == 2, "§%s %s --bogus rc=%s, want 2 (usage)\n%s" % (
        section, rel, res.rc, res.combined[-600:])


@pytest.mark.parametrize("section,rel,bound", CONTRACTS, ids=IDS)
def test_help_is_rc0(section, rel, bound, run_tool):
    res = run_tool([str(cf.TOOLS_DIR / rel), "--help"], timeout=120)
    assert res.rc == 0, "§%s %s --help rc=%s, want 0\n%s" % (
        section, rel, res.rc, res.combined[-600:])


@pytest.mark.parametrize("section,rel,bound", CONTRACTS, ids=IDS)
def test_help_goes_to_stdout(section, rel, bound, run_tool):
    """#748a: ``--help`` is an explicitly requested READ, so the text is STDOUT.

    A tool that prints usage to stderr passes the rc leg and breaks
    ``tool --help | grep``, which is how a lane concludes a flag does not exist.
    """
    res = run_tool([str(cf.TOOLS_DIR / rel), "--help"], timeout=120)
    assert res.out.strip(), (
        "§%s %s wrote --help to STDERR (rc 0), so `%s --help | grep` finds "
        "nothing:\nstderr=%s" % (section, rel, rel, res.err[-500:]))


@pytest.mark.slow
@pytest.mark.parametrize("section,rel,bound", CONTRACTS, ids=IDS)
def test_selftest_passes(section, rel, bound, run_selftest):
    """§<section> ``run_selftest`` leg. ``run_selftest`` resolves the tool by
    NAME, so the group prefix is stripped — the tool must be findable by name
    alone or the shell battery's own ``tool_path`` would miss it too."""
    name = rel.split("/")[1]
    res = run_selftest(name, timeout=bound)
    assert res.rc == 0, "§%s %s --selftest rc=%s\n%s" % (
        section, name, res.rc, res.combined[-1200:])


@pytest.mark.parametrize("rel", ["issue/oc-census", "audit/oc-claims-single-source"])
def test_python_tools_are_not_run_through_bash(rel):
    """The interpreter guard behind the legs above.

    ``bash tools/issue/oc-census --selftest`` exits 2 at the first ``import`` —
    the same rc as a usage error — so a bash-invoked usage leg would PASS while
    the tool never ran. This asserts the shebang, which is the fact that makes
    direct invocation correct."""
    head = (cf.TOOLS_DIR / rel).open(encoding="utf-8", errors="replace").readline()
    assert "python" in head, (
        "%s starts with %r, not a python shebang — the usage legs above assume "
        "direct invocation is right" % (rel, head.strip()))
