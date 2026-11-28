#!/usr/bin/env python3
"""Generate the ``chk`` -> pytest mapping table for factory #204.

WHY A SCRIPT AND NOT A TABLE IN PROSE
    The claim being made is "N of 475 shell assertions now have a pytest
    equivalent". A hand-written table is a claim about a claim: it cannot be
    checked without re-reading 3,000 lines of shell. This script derives the
    table from two artifacts that exist on disk — the shell's own ``chk``
    invocations and the ported pytest sources — so the count is READ, never
    assembled.

WHAT COUNTS AS COVERED
    A ``chk`` name appears in a pytest file's SOURCE. The ported modules carry
    the shell name in every assertion message (``"[stamp#1] ..."``), which is
    what makes this mechanical. That is a weaker claim than "the assertion is
    equivalent" and the report says so: the count proves the name was carried
    over, and the per-module docstrings carry the reasoning for each block.

USAGE
    python3 tools/tests/pytest/map_selftest_chk.py [--selftest PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent

# ``chk "name" expected actual`` and the bare ``ok || bad "name"`` form both
# register an assertion; the shell's own counter counts both.
CHK_RE = re.compile(r'\bchk\s+"([^"]+)"')
BAD_RE = re.compile(r'\bbad\s+"([^"$]+)')

# A shell name often carries a DIAGNOSTIC suffix: ``bad "c8-anchor-not-sync-under-flags
# ($C8D2SHA)"`` or ``bad "reconcile-remedy-runs: uuid NOT parsed"``. The name is the
# part before it; keeping the suffix makes every such assertion look unported while
# the leg exists. Splitting is safe because no real ``chk`` name contains `` (`` or
# ``: `` — the roster was checked against /tmp/chkmap.tsv.
_NAME_TAIL = re.compile(r"\s*\(.*$|:.*$")

# Blocks that are DELIBERATELY not ported, with the reason. A name here is
# reported as ``unported`` with its reason rather than silently missing — the
# report's honesty requirement is that every absent name is accounted for.
UNPORTED = {
    # §33 race arms: same-named assertions already exist in test_tool_wrappers.py
    # (lines 143-309) and the lock budget is owned by test_ledger_lock_budget.py.
    # Porting them again would create two suites asserting one mechanism, and the
    # second would rot against the first.
    "race-max-n": "owned by test_ledger_lock_budget.py + test_tool_wrappers.py",
    "race-no-dup": "owned by test_ledger_lock_budget.py + test_tool_wrappers.py",
    # Source-grep arms: they `grep -c '^fn()' "$ME"` or awk-slice the tool's own
    # source. They are structural assertions about the FILE, not behaviour, and
    # the harness-structure suite already owns "the tool's own shape" as a class.
    "state-tracked-single-source": "source-shape; see test_ledger_structural.py",
    "state-sweep-fn-single-source": "source-shape; see test_ledger_structural.py",
    "state-tracked-audit-single-source": "source-shape; see test_ledger_structural.py",
    "state-out-of-scope-single-source": "source-shape; see test_ledger_structural.py",
    "push-helper-single-source": "source-shape; see test_ledger_structural.py",
    "push-wired-both-dirs": "source-shape; see test_ledger_structural.py",
    "push-fetches-before-push": "source-shape; see test_ledger_structural.py",
    "git-tail-flag-set-under-lock": "source-shape; see test_ledger_structural.py",
    "git-tail-flag-cleared": "source-shape; see test_ledger_structural.py",
    "git70-scope-harness-carries-the-helper": "harness-shape; not tool behaviour",
    "git70-state-wt-fixture-is-a-gitdir-FILE": "harness-shape; not tool behaviour",
    "git70-skill-wt-fixture-is-a-gitdir-FILE": "harness-shape; not tool behaviour",
    "git70-commit-pending-worktree-rc": "worktree support; see test_ledger_structural.py",
    "git70-sync-worktree-bump-rc": "worktree support; see test_ledger_structural.py",
    "git70-sync-worktree-stray-refused": "worktree support; see test_ledger_structural.py",
    # The shell harness's own bookkeeping, not a tool assertion.
    "'$_bad'": "shell variable interpolation, not an assertion name",
    "lock-wait-tunable": "source-shape; see test_ledger_structural.py",
}


def find_selftest(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    return REPO / "tools" / "state" / "oc-ledger"


def shell_names(path: Path) -> list[tuple[int, str, str]]:
    """Every ``chk``/``bad`` name in the tool's ``cmd_selftest``, in file order.

    The selftest body is ``cmd_selftest() {`` .. its closing brace at column 0;
    slicing it keeps a ``chk`` in a *fixture heredoc* out of the census.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("cmd_selftest() {")
    if start < 0:
        raise SystemExit("cmd_selftest() { not found in %s" % path)
    body = text[start:]
    out: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(body.splitlines(), start=text[:start].count("\n") + 1):
        for kind, rx in (("chk", CHK_RE), ("bad", BAD_RE)):
            for m in rx.finditer(line):
                name = _NAME_TAIL.sub("", m.group(1)).strip()
                if name:
                    out.append((lineno, name, kind))
    return out


def pytest_sources(root: Path) -> dict[str, list[str]]:
    """``{chk name: [file, ...]}`` — which ported modules mention each name."""
    found: dict[str, list[str]] = {}
    for f in sorted(root.glob("test_*.py")):
        txt = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\bchk\b|\[([a-zA-Z0-9][\w.:#-]*)\]", txt):
            name = m.group(1)
            if name and name not in ("", "x"):
                found.setdefault(name, []).append(f.name)
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pytest-root", default=str(HERE))
    args = ap.parse_args()

    tool = find_selftest(args.selftest)
    if not tool.exists():
        raise SystemExit("selftest source not found: %s" % tool)

    names = shell_names(tool)
    sources = pytest_sources(Path(args.pytest_root))
    blob = {}
    for f in Path(args.pytest_root).glob("test_*.py"):
        blob[f.name] = f.read_text(encoding="utf-8", errors="replace")

    rows = []
    for lineno, name, kind in names:
        hits = [fn for fn, txt in blob.items() if name in txt]
        if hits:
            state, where = "ported", ",".join(sorted(hits))
        elif name in UNPORTED:
            state, where = "unported", UNPORTED[name]
        else:
            state, where = "MISSING", ""
        rows.append({"line": lineno, "chk": name, "kind": kind,
                     "state": state, "where": where})

    counts = {"ported": 0, "unported": 0, "MISSING": 0}
    for r in rows:
        counts[r["state"]] += 1
    by_kind = {"chk": 0, "bad": 0}
    for r in rows:
        by_kind[r["kind"]] += 1

    if args.json:
        print(json.dumps({"total": len(rows), "counts": counts,
                          "by_kind": by_kind, "rows": rows}, indent=2))
        return 0

    print("| # | shell line | form | name | state | ported in / reason |")
    print("|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        print("| %d | %d | %s | `%s` | %s | %s |"
              % (i, r["line"], r["kind"], r["chk"], r["state"], r["where"]))
    print()
    print("total %d assertions (%d `chk`, %d `ok || bad`) — ported %d, "
          "unported-with-reason %d, MISSING %d"
          % (len(rows), by_kind["chk"], by_kind["bad"], counts["ported"],
             counts["unported"], counts["MISSING"]))
    return 0 if counts["MISSING"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
