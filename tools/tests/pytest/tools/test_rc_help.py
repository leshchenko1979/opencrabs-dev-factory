"""Ported: the fleet-wide ``--help`` sweep — run.sh §43.

``tools/`` is grouped by KIND, so the executables live one level down. A flat
``tools/oc-*`` glob matches NOTHING under that layout and the section then
passes by counting zero legs — a fleet-wide check that cannot fail. So the
enumeration is recursive and a FLOOR is asserted.

Three defects this leg exists to catch, each a different way ``rc 0`` lies:

* **rc=124** — a tool killed by the bound. Named as a TIMEOUT, not a contract
  violation: the two are different defects and run.sh's original could not tell
  them apart (#115).
* **empty stdout** — ``--help`` is an explicitly requested READ, so the text
  belongs on STDOUT. Twelve tools printed it to STDERR while rc stayed 0, so
  ``tool --help | grep flag`` found nothing (#748a).
* **shell diagnostics on stderr** — the rc leg discards stderr, so a ``--help``
  whose body executes phantom commands still reads rc 0. That is how
  oc-smoke shipped ``absent`` and ``na`` running as commands (#618).

One invocation per tool yields all three: the rc, the stdout text and the stderr
text come from the same run.
"""

from __future__ import annotations

import os

import pytest

import conftest as cf

HELP_BOUND = 60.0
FLOOR = 30
SKIP_PARTS = {"/lib/", "/tests/", "/archive/", "/docs/", "/instruments/"}
SKIP_SUFFIX = (".bak", ".bak-", ".pre-")

# Shell diagnostics only. A bare "not found" is NOT one: oc-pr-atomicity's own
# usage line documents "4 PR not found" as an exit code, and the loose arm
# flagged that legitimate text.
DIAGNOSTICS = (
    "command not found",
    "syntax error",
    "unbound variable",
    "No such file or directory",
    "Bad substitution",
)


def _fleet():
    """Every shipped executable, recursively — the same skip pattern run.sh
    applies, so generated .bak pre-images are not enumerated as tools (#691)."""
    found = []
    for root, dirs, files in os.walk(cf.TOOLS_DIR):
        dirs[:] = [d for d in dirs if d not in
                   {"lib", "tests", "archive", "docs", "instruments", "__pycache__"}]
        for f in files:
            if not f.startswith("oc-") or f.endswith(SKIP_SUFFIX) or ".bak-" in f \
                    or ".pre-" in f:
                continue
            p = os.path.join(root, f)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                found.append(p)
    return sorted(found)


@pytest.fixture(scope="module")
def help_runs():
    """ONE invocation per tool, reused by all three legs: the rc, the stdout and
    the stderr all come from the same run, so the sweep costs one pass, not
    three. Module-scoped on purpose — ``run_tool`` is function-scoped, so this
    calls the conftest runner directly."""
    tools = _fleet()
    assert len(tools) >= FLOOR, (
        "fleet --help floor: only %d tool(s) enumerated (want >= %d) — the "
        "enumeration stopped matching" % (len(tools), FLOOR))
    out = []
    for p in tools:
        res = cf._run([p, "--help"], timeout=HELP_BOUND,
                      env={"OC_TOOLS_NOLOG": "1"})
        out.append((os.path.basename(p), res))
    return out


def test_help_exits_zero(help_runs):
    """rc 0 for every tool; a bound kill is called what it is."""
    bad = []
    for name, res in help_runs:
        if res.rc == 0:
            continue
        if res.rc == 124 or res.timed_out:
            bad.append("%s --help KILLED by the %gs bound — a TIMEOUT, not an RC "
                       "contract violation (factory #115)" % (name, HELP_BOUND))
        else:
            bad.append("%s --help rc=%s (tools/docs/RC-CONTRACT.md violated)"
                       % (name, res.rc))
    assert not bad, "%d tool(s) failed the --help rc leg:\n  %s" % (
        len(bad), "\n  ".join(bad))


def test_help_writes_usage_to_stdout(help_runs):
    """#748a: stdout must be NON-EMPTY — never a byte count, the text may grow."""
    empty = [name for name, r in help_runs
             if r.rc != 124 and not r.timed_out and not r.out.strip()]
    assert not empty, (
        "%d tool(s) wrote NOTHING to stdout — usage belongs on STDOUT, not "
        "STDERR (#748a, tools/docs/RC-CONTRACT.md): %s" % (len(empty), empty))


def test_help_writes_no_shell_diagnostics(help_runs):
    """#618: an unquoted heredoc body executes phantom commands while --help
    still prints and rc stays 0."""
    hits = []
    for name, res in help_runs:
        if res.rc == 124 or res.timed_out:
            continue        # a bound kill writes no diagnostics: a stated skip
        for pat in DIAGNOSTICS:
            if pat in res.err:
                line = next((ln for ln in res.err.splitlines() if pat in ln), "")
                hits.append("%s: %s" % (name, line[:70]))
                break
    assert not hits, (
        "%d tool(s) wrote a SHELL DIAGNOSTIC to stderr on --help (#618):\n  %s"
        % (len(hits), "\n  ".join(hits)))


def test_generated_sidecars_are_not_enumerated(help_runs):
    """#691: the edit tool's ``.bak`` pre-image is an EXECUTABLE copy of the
    tool, so a naive glob ran their --help as 7 phantom PASS legs.

    When there are no sidecars the guard is VACUOUS, and that is disclosed
    rather than passed silently."""
    sidecars = []
    for root, dirs, files in os.walk(cf.TOOLS_DIR):
        depth = root[len(str(cf.TOOLS_DIR)):].count(os.sep)
        if depth > 2:
            dirs[:] = []
            continue
        for f in files:
            if f.startswith("oc-") and (f.endswith(".bak") or ".bak-" in f
                                        or ".pre-" in f):
                sidecars.append(os.path.join(root, f))
    # match by BASENAME too: the enumeration records basenames, the walk records
    # full paths, so comparing the two sets directly would compare nothing.
    enumerated_names = {n for n, _r in help_runs}
    enumerated = {os.path.join(str(cf.TOOLS_DIR), name) for name, _r in help_runs}
    leaked = [s for s in sidecars
              if s in enumerated or os.path.basename(s) in enumerated_names]
    assert not leaked, (
        "%d of %d generated sidecar(s) STILL enumerated as tools (#691): %s"
        % (len(leaked), len(sidecars), leaked))
