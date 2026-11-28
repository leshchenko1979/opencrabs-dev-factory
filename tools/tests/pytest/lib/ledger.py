"""Read-back helpers for the ported ``oc-ledger`` selftest (factory #204).

WHY THIS MODULE EXISTS
    ``cmd_selftest`` (``tools/state/oc-ledger:2771-5733``, 475 ``chk`` calls)
    asserts overwhelmingly by reading the ledger back and comparing one field.
    In shell that is ``jq -r '<filter>' "$OC_LEDGER"`` repeated ~400 times. Here
    it is ``events(ledger)`` plus ordinary Python, so a leg states WHAT it
    asserts instead of burying it in a jq filter string.

WHAT IS DELIBERATELY NOT HERE
    * No ledger payload constant. ``conftest._LEDGER_JSON`` is the canonical
      fixture and ``test_fixtures.py::test_ledger_sandbox_recipe_still_matches_the_tool``
      already pins it to the tool's own heredoc. A second copy here would be a
      third thing to keep in sync, and the drift would be silent.
    * No ``ledger_sandbox`` equivalent. That fixture is the fixture; these are
      the readers.

CONVENTIONS THE PORTED TESTS FOLLOW
    * Every assertion message carries the shell ``chk`` name it replaces, e.g.
      ``"[stamp#1] want rc 0 ..."``. That is what makes the 475-row mapping
      table mechanical rather than a claim.
    * A leg that drives several ``chk`` calls in sequence keeps them in ONE test
      function when the sequence IS the fixture: ``n-continuity`` is only
      meaningful after the three stamps above it, and splitting it would
      recreate shared mutable state across tests — the thing xdist punishes.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

# =============================================================================
# ledger read-back
# =============================================================================
def read_json(path):
    """Parse a ledger; raises on a corrupt file (a leg that wants a bool uses
    ``try_read_json``)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def try_read_json(path, default=None):
    try:
        return read_json(path)
    except (OSError, ValueError):
        return default


def events(path) -> list:
    """``.events`` of a ledger, or [] — the shell's ``jq '.events[]'``."""
    doc = try_read_json(path) or {}
    return doc.get("events") or []


def workers(path) -> list:
    doc = try_read_json(path) or {}
    return doc.get("workers") or []


def ns(path) -> list:
    """Every event ordinal, in file order — ``jq '[.events[].n]'``."""
    return [e.get("n") for e in events(path)]


def max_n(path) -> int:
    """``jq '([.events[].n] | max)'``; -1 for an empty log so a leg can say so."""
    vals = [n for n in ns(path) if isinstance(n, int)]
    return max(vals) if vals else -1


def where(path, **kw) -> list:
    """Events whose named fields all equal the given values."""
    return [e for e in events(path) if all(e.get(k) == v for k, v in kw.items())]


def last_where(path, **kw):
    """The LAST matching event, or None — ``... | last``."""
    rows = where(path, **kw)
    return rows[-1] if rows else None


def last_event(path):
    rows = events(path)
    return rows[-1] if rows else None


def field(path, name, **kw):
    """One field of the last event matching ``kw`` (or of the last event)."""
    row = last_where(path, **kw) if kw else last_event(path)
    return None if row is None else row.get(name)


def has_fields(row, names) -> bool:
    """``has("n") and has("t") and ...`` — present, even when null."""
    return bool(row) and all(n in row for n in names)


# =============================================================================
# text
# =============================================================================
def sha256_8(text: str) -> str:
    """First 8 hex of sha256 — the ``hash8=`` the stamp success line surfaces."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def byte_len(text: str) -> int:
    """``printf '%s' "$TEXT" | wc -c`` — BYTES, not characters.

    The distinction is the point of the leg: a multibyte payload whose character
    count is reported as its byte count would make the surfaced ``len=`` a
    constant that agrees with itself.
    """
    return len(text.encode("utf-8"))


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write(path, body: str, newline: bool = True) -> Path:
    """Write text, creating parents. ``newline=False`` reproduces the shell's
    ``printf '%s'`` (no trailing newline) — which is what makes a byte-length
    assertion discriminating."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body + ("\n" if newline else ""), encoding="utf-8")
    return p


# =============================================================================
# git — the fixture repos the shell builds inline
# =============================================================================
def git(repo, *args, check: bool = False, env: dict | None = None):
    full = dict(os.environ)
    if env:
        full.update({k: str(v) for k, v in env.items()})
    return subprocess.run(["git", "-C", str(repo)] + [str(a) for a in args],
                          capture_output=True, text=True, check=check, env=full)


def init_repo(path, files: dict | None = None, branch: str = "main") -> Path:
    """``git init`` + a PINNED identity + one base commit.

    The identity goes into the repo-local config rather than onto each command,
    because the TOOL commits on its own and must inherit it. A box without a
    global git identity would otherwise fail with "Author identity unknown",
    which reads as a broken tool rather than as a fixture defect.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    git(p, "init", "-q", "-b", branch)
    git(p, "config", "user.email", "t@t")
    git(p, "config", "user.name", "t")
    git(p, "config", "commit.gpgsign", "false")
    for fn, body in (files or {}).items():
        fp = p / fn
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(body, encoding="utf-8")
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "base")
    return p


def head(repo, ref: str = "HEAD") -> str:
    return git(repo, "rev-parse", ref).stdout.strip()


def short(repo, ref: str = "HEAD") -> str:
    return git(repo, "rev-parse", "--short", ref).stdout.strip()


def commit(repo, subject: str, body=(), date: str | None = None,
           allow_empty: bool = True):
    """A commit with an optional fixed author/committer date.

    ``date`` exists for the age-bound arms: backdating a commit is how the
    shell makes "the newest unpushed commit is N seconds old" true without
    sleeping a wall bound.
    """
    args = ["commit", "-q"]
    if allow_empty:
        args.append("--allow-empty")
    args += ["-m", subject]
    for line in body:
        args += ["-m", line]
    env = None
    if date:
        env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    return git(repo, *args, env=env)


def porcelain(repo, *paths) -> str:
    return git(repo, "status", "--porcelain", *paths).stdout


def log_subject(repo, n: int = 1) -> str:
    return git(repo, "log", "-%d" % n, "--format=%s").stdout.strip()


def rev_count(repo, rng: str) -> int:
    out = git(repo, "rev-list", "--count", rng).stdout.strip()
    try:
        return int(out)
    except ValueError:
        return -1


# =============================================================================
# the skill dir the shell's fixture builds inline
# =============================================================================
def make_skill(path, version: str = "0.4.2",
               changelog: str = "# fixture changelog\n") -> Path:
    """A skill dir with a TRACKED ``tools/tests/``.

    ``tools/tests/.keep`` is load-bearing (v0.4.157): an entirely untracked
    ``tools/`` collapses to ``?? tools/`` in porcelain, and the stray-guard reads
    that as another lane's dirty work.
    """
    p = Path(path)
    (p / "tools" / "tests").mkdir(parents=True, exist_ok=True)
    (p / "SKILL.md").write_text(
        "name: fixture\nversion: %s\n---\n# fixture\n" % version, encoding="utf-8")
    (p / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (p / "tools" / "tests" / ".keep").write_text("", encoding="utf-8")
    return p


def set_skill_version(skill, version: str, changelog_entry: bool = True):
    """``sed -i 's/^version: .*/version: X/' SKILL.md`` + the CHANGELOG row.

    Both halves, because ``sync`` refuses a bump whose CHANGELOG entry is
    missing (C8, v0.4.65) — a fixture that moves only SKILL.md asserts the
    changelog gate by accident, on every leg.
    """
    skill = Path(skill)
    md = skill / "SKILL.md"
    lines = md.read_text(encoding="utf-8").splitlines(True)
    md.write_text("".join(
        ("version: %s\n" % version) if ln.startswith("version:") else ln
        for ln in lines), encoding="utf-8")
    if changelog_entry:
        with open(skill / "CHANGELOG.md", "a", encoding="utf-8") as fh:
            fh.write("\n## v%s\nfixture receipt\n" % version)


def make_battery(path, verdict: str = "PASS", fail: int = 0, extra: str = ""):
    """``tools/tests/battery-last.json`` — the receipt ``sync`` gates on."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"verdict":"%s","fail":%d,"ts":"%s"%s}\n'
                 % (verdict, fail, now_iso(), extra), encoding="utf-8")
    return p


def rmtree(path):
    shutil.rmtree(str(path), ignore_errors=True)
