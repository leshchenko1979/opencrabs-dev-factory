"""Opt-in content-hash memo for expensive ``--selftest`` subprocesses.

THE PROBLEM THIS SOLVES, MEASURED
    The battery's wall time is dominated by a handful of tool ``--selftest``
    subprocesses (``oc-issue-dispatch`` 208 s, ``oc-ledger`` 296 s, ``oc-ship``
    156 s). A lane that changed one unrelated shell file pays all of them again.
    ``.pytest_cache`` already gives ``--lf``/``--ff``/``--sw``, but that is
    *failure* memory, not *result* memory: a green leg is green forever and
    pytest has nothing to say about it.

WHY A CONTENT HASH AND NOT mtime
    mtime lies across worktrees, checkouts and ``git checkout``: a fresh clone
    stamps every file with "now", so an mtime key says "changed" for a tree that
    is byte-identical, and a ``cp -p``/``rsync -t`` can say "unchanged" for a
    tree that is not. The key here is sha256 over the BYTES of everything that
    can change the answer:

      * the tool file itself,
      * every ``tools/lib/*`` (and ``tools/tests/*.sh``) file it references,
        TRANSITIVELY — a lib change must invalidate every tool that sources it,
        which is the whole point: ``oc-log.sh`` is sourced by 68 tools,
      * the Python interpreter version,
      * the digest of ``conftest.py`` (fixture semantics are part of the answer),
      * ``CACHE_VERSION``, bumped whenever the KEY SHAPE changes,
      * the extra argv passed to ``--selftest``.

    Env vars are deliberately NOT in the key: they are knobs (state dir,
    timeouts, actor), not result determinants, and hashing the environment would
    make every run a miss. The documented consequence is at the bottom of this
    docstring.

THE FOUR RULES
    1. OFF BY DEFAULT. ``--oc-cache`` or ``OC_PYTEST_CACHE=1``. With neither,
       ``from_config`` returns ``None`` and every call site is a passthrough: no
       read, no write, no output — byte-identical to the run without this file.
    2. NEVER CACHE A FAIL. ``Cache.put`` refuses ``rc != 0`` and returns False.
       A cached failure would make a flaky leg permanently red or, worse, hide
       the fix that made it green.
    3. NEVER UNDER THE SHIP GATE. The gate sets no ``OC_PYTEST_CACHE``, so the
       cache is inert there by rule 1 and every selftest runs for real. A gate
       that can be satisfied from a cache is not a gate.
    4. BOUNDED AND SELF-PRUNING. ``cap`` entries (default 200); past it the
       least-recently-USED go first. A cache that grows forever is a new defect,
       not a feature.

LOCATION
    ``OC_PYTEST_CACHE_DIR`` if set, else ``$XDG_CACHE_HOME/oc-pytest-cache``
    (``~/.cache/...``). NEVER inside the repo tree: an untracked path under the
    skill repo trips the sync stray-guard (die 7), which reads a plain
    ``git status --porcelain`` and refuses a version bump because of one lane's
    scratch. ``.pytest_cache/`` is gitignored and therefore invisible to that
    guard, but "ignored" is a weaker promise than "outside the tree", so the
    default is outside.

KNOWN LIMITATION (stated, not hidden)
    Because the key is content, not environment, two runs whose *environment*
    differs but whose *files* are identical share an entry. That is correct for
    a selftest (a tool's own selftest must pass under any state dir) and it is
    why the key includes argv but not ``OC_*``. If a future leg's result really
    does depend on an env var, pass it through ``extra`` — do not widen the key
    with the whole environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

# Bump when the KEY SHAPE changes (a new hashed input, a different encoding).
# Entries written under an older version are simply never matched; pruning
# reaps them by LRU, so a bump needs no migration.
CACHE_VERSION = 1

ENV_ENABLE = "OC_PYTEST_CACHE"
ENV_DIR = "OC_PYTEST_CACHE_DIR"
ENV_MAX = "OC_PYTEST_CACHE_MAX"

DEFAULT_CAP = 200
ENTRY_SUFFIX = ".json"

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS_DIR = REPO_ROOT / "tools"
CONFTEST_PATH = Path(__file__).resolve().parent.parent / "conftest.py"

# A reference to a sibling lib: `lib/oc-log.sh`, `${TOOLS_DIR}/lib/oc-notify.sh`,
# `_OC_LIB="$_OC_DIR/lib/oc-log.sh"`. The token after `lib/` is resolved against
# the tools dir and kept only if the file EXISTS, so a comment mentioning a
# retired lib cannot poison the key with a phantom input.
_LIB_REF = re.compile(r"(?:lib|tests)/([A-Za-z0-9][A-Za-z0-9_.\-]*)")
# A line that SOURCES something: `. path` or `source path`.
_SOURCE_STMT = re.compile(r"^\s*(?:\.|source)\s")
# A line that ASSIGNS a path (`_OC_LIB="$_OC_DIR/lib/oc-log.sh"`).
_ASSIGN_STMT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# A Python import that resolves inside tools/lib (`from oc_log import ...`).
_PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)",
                        re.MULTILINE)
# SOURCE files only. `tools/tests/battery-last.json` is referenced by oc-ledger
# as its own gate receipt and is REWRITTEN by every battery run, so hashing it
# would invalidate the cache on every run — the one input that is guaranteed to
# change. The key covers source; runtime artefacts are not source.
_SOURCE_SUFFIXES = (".sh", ".bash", ".py")


# =============================================================================
# hashing
# =============================================================================
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    """sha256 of a file's BYTES; ``""`` when unreadable.

    A missing file is not an error here — a tool may reference a lib that does
    not exist in this checkout, and the honest key for that is "absent", which
    is a value, not a crash.
    """
    try:
        return sha256_bytes(Path(path).read_bytes())
    except OSError:
        return ""


def interpreter_tag() -> str:
    """The interpreter's identity: version, implementation, cache tag.

    ``sys.version`` alone misses a rebuild of the same version with a different
    ABI; the magic-number tag catches that.
    """
    return " ".join((
        sys.version.replace("\n", " ").strip(),
        sys.implementation.name,
        getattr(sys.implementation, "cache_tag", "") or "",
    ))


def conftest_digest() -> str:
    """Digest of the fixture file: fixture semantics are part of the answer."""
    return sha256_file(CONFTEST_PATH)


# =============================================================================
# the transitive lib closure
# =============================================================================
def lib_dir_for(tool_path, tools_dir=None) -> Path:
    """``tools/lib`` for a tool at any depth (``tools/<kind>/oc-x``)."""
    tools = Path(tools_dir or TOOLS_DIR)
    p = Path(tool_path).resolve()
    for parent in p.parents:
        if parent.name == "lib" and parent.parent == tools:
            return parent
        if parent == tools:
            return tools / "lib"
    return tools / "lib"


def referenced_files(path, tools_dir=None) -> list[Path]:
    """Files a single tool/lib file SOURCES, resolved against the tools dir.

    Static and textual on purpose: the tools are shell, and a ``source`` can be
    spelled ``. "$_oc_r/lib/oc-root.sh"`` where ``$_oc_r`` is built three lines
    up, so executing or fully parsing the shell would be both unsafe and
    fragile. The literal ``lib/<name>`` is what every one of those indirections
    ends up spelling, which makes the set discoverable without running anything.

    LINE-SCOPED, NOT FILE-SCOPED, and that distinction is load-bearing:
    oc-ledger's ``die`` message mentions ``tools/tests/run.sh`` ("run the
    battery first"), and a whole-file scan put run.sh in oc-ledger's key — every
    edit to an unrelated harness would have invalidated a 296 s selftest. So a
    ``lib/``/``tests/`` token counts only on a line that could actually source
    something: a ``.``/``source`` statement, or an ASSIGNMENT (which is where the
    path is spelled before ``source "$VAR"``). Full-line comments never count.

    OVER-INCLUSION IS THE SAFE DIRECTION: an extra file in the closure only
    invalidates more often (a spurious miss); a missing file would serve a stale
    PASS, which is the one failure mode a result cache must never have.
    """
    tools = Path(tools_dir or TOOLS_DIR)
    p = Path(path)
    try:
        text = p.read_text(errors="replace")
    except OSError:
        return []
    out: list[Path] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not (_SOURCE_STMT.match(line) or _ASSIGN_STMT.search(line)):
            continue
        for m in _LIB_REF.finditer(line):
            name = m.group(1).rstrip(".")
            if not name:
                continue
            for cand in (tools / "lib" / name, tools / "tests" / name):
                if not cand.is_file() or cand.is_symlink():
                    continue
                # tests/ holds ARTEFACTS as well as scripts, and
                # `tests/battery-last.json` is rewritten by every battery run —
                # hashing it would make the key change on every invocation,
                # i.e. a cache that can never hit. Only scripts there count.
                # A lib may be extensionless (`oc_sqlite`, `oc-base-red`); a
                # tests/ helper must be a SCRIPT. The suffix filter is what
                # keeps `tools/tests/battery-last.json` — a receipt every
                # battery run REWRITES, so hashing it would guarantee a miss on
                # every run — out of the key while keeping
                # `tools/tests/deploy-selftest.sh` in it.
                if cand.parent == tools / "lib" or cand.suffix in _SOURCE_SUFFIXES:
                    if cand not in out:
                        out.append(cand)
                break
    # Python deps, scanned in EVERY file and not just ``*.py`` ones: half the
    # Python tools here are extensionless (`tools/audit/oc-claims-single-source`)
    # and several shell tools carry a ``python3 - <<'OCPY'`` heredoc that imports
    # from tools/lib (oc-harvest-census imports BOTH oc_claims and oc_base_red
    # that way). A module name only counts if tools/lib/<name>.py exists, so
    # `import os` costs nothing and a real dependency cannot be missed.
    for m in _PY_IMPORT.finditer(text):
        cand = tools / "lib" / (m.group(1) + ".py")
        if cand.is_file() and cand not in out:
            out.append(cand)
    return out

def sourced_libs(tool_path, *, tools_dir=None, max_depth: int = 12) -> dict[str, str]:
    """``{relpath: sha256}`` for the tool's transitive closure under tools/.

    Transitivity is the requirement, not a nicety: ``oc-ledger`` sources
    ``oc-root.sh`` and ``oc-log.sh``; ``oc-deploy-lib.sh`` sources
    ``oc-embed.sh``, ``oc-notify.sh`` and ``oc-sessions.sh``. A change two hops
    down must invalidate the tool that is three hops up.
    """
    root = Path(tool_path).resolve()
    tools = Path(tools_dir or TOOLS_DIR).resolve()
    found: dict[str, str] = {}
    queue: list[tuple[Path, int]] = [(root, 0)]
    visited = {root}
    while queue:
        cur, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for ref in referenced_files(cur, tools_dir=tools):
            r = ref.resolve()
            if r in visited:
                continue
            visited.add(r)
            # Repo-relative when possible so two checkouts of the same tree
            # produce the SAME key material (an absolute path would make the
            # cache worktree-specific, which is the mtime defect again).
            try:
                rel = str(r.relative_to(REPO_ROOT))
            except ValueError:
                try:
                    rel = str(r.relative_to(tools))
                except ValueError:        # pragma: no cover - outside both roots
                    rel = str(r)
            found[rel] = sha256_file(r)
            queue.append((r, depth + 1))
    return found


# =============================================================================
# the key
# =============================================================================
def key_material(tool_path, *, args=(), extra=None, tools_dir=None) -> dict:
    """Everything that goes into the hash, as a plain JSON-able dict.

    Returned (not just hashed) so a test — and a human reading a cache entry —
    can see WHY a key changed instead of diffing two hex strings.
    """
    path = Path(tool_path)
    material = {
        "cache_version": CACHE_VERSION,
        "tool": path.name,
        "tool_sha256": sha256_file(path),
        "libs": sorted(sourced_libs(path, tools_dir=tools_dir).items()),
        "python": interpreter_tag(),
        "conftest_sha256": conftest_digest(),
        "args": [str(a) for a in args],
    }
    if extra:
        material["extra"] = {str(k): str(v) for k, v in sorted(extra.items())}
    return material


def cache_key(tool_path, *, args=(), extra=None, tools_dir=None) -> str:
    """sha256 over a CANONICAL (sorted-key, compact) encoding of the material."""
    blob = json.dumps(key_material(tool_path, args=args, extra=extra,
                                  tools_dir=tools_dir),
                      sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(blob.encode())


# =============================================================================
# location
# =============================================================================
def default_cache_dir() -> Path:
    """``$OC_PYTEST_CACHE_DIR`` else ``$XDG_CACHE_HOME/oc-pytest-cache``."""
    env = os.environ.get(ENV_DIR)
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache")
    return Path(base) / "oc-pytest-cache"


def inside_repo(path) -> bool:
    try:
        Path(path).resolve().relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def cap_from_env() -> int:
    raw = os.environ.get(ENV_MAX)
    if not raw:
        return DEFAULT_CAP
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_CAP
    return n if n > 0 else DEFAULT_CAP


# =============================================================================
# tool resolution (mirrors conftest.tool_path — kept honest by a test)
# =============================================================================
def resolve_tool(name: str, tools_dir=None) -> Path:
    """Resolve an ``oc-*`` tool by NAME, mirroring ``conftest.tool_path``.

    ``tools/`` is grouped by KIND, so a tool can be moved without touching every
    leg; the same exclusion list (lib/tests/archive/docs/instruments) applies.
    ``harness/test_cache.py::test_resolve_tool_matches_conftest`` fails if the two
    implementations ever drift.
    """
    base = Path(tools_dir or TOOLS_DIR)
    direct = base / name
    if direct.is_file() and os.access(direct, os.X_OK):
        return direct
    skip = {"lib", "tests", "archive", "docs", "instruments"}
    for sub in sorted(base.iterdir()):
        if not sub.is_dir() or sub.name in skip:
            continue
        cand = sub / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand
    raise FileNotFoundError("tool not found: %s (under %s)" % (name, base))


# =============================================================================
# a result that may have come from the cache
# =============================================================================
class Outcome:
    """The shape ``run_cached`` returns: rc/duration plus HOW it was answered.

    ``cached`` and ``key`` are the two facts a test needs and a verbose line
    prints; ``duration_ms`` on a hit is the ORIGINAL run's duration, not ~0, so
    a receipt's ``timing`` still says what the leg really costs.
    """

    __slots__ = ("rc", "duration_ms", "cached", "key", "tool", "out", "err")

    def __init__(self, rc, duration_ms, *, cached=False, key="", tool="",
                 out="", err=""):
        self.rc = rc
        self.duration_ms = duration_ms
        self.cached = cached
        self.key = key
        self.tool = tool
        self.out = out
        self.err = err

    @property
    def combined(self) -> str:
        return (self.out or "") + (self.err or "")

    def __repr__(self):
        return "<Outcome %s rc=%s %.0fms%s key=%s>" % (
            self.tool or "?", self.rc, self.duration_ms,
            " CACHED" if self.cached else "", self.key[:12])


def run_cached(cache, *, tool: str, tool_path, runner, args=(),
               extra=None, emit=None) -> Outcome:
    """Run ``runner()`` unless ``cache`` holds a PASS for this exact content.

    ``runner`` is any callable returning an object with ``.rc`` and
    ``.duration_ms`` — the plugin passes the real ``run_selftest``; the tests
    pass a stub that counts invocations, so "did it execute" is an assertion
    about a counter, never about a stopwatch.

    ``cache is None`` (the default: no ``--oc-cache``, no ``OC_PYTEST_CACHE``)
    is a pure passthrough — this function then adds nothing to today's
    behaviour, not even a key computation.
    """
    if cache is None:
        res = runner()
        return Outcome(getattr(res, "rc", 1), getattr(res, "duration_ms", 0.0),
                       tool=tool, out=getattr(res, "out", ""),
                       err=getattr(res, "err", ""))

    path = Path(tool_path)
    key = cache_key(path, args=args, extra=extra)
    hit = cache.get(key)
    if hit is not None:
        if emit is not None:
            emit(cache.hit_message(hit))
        return Outcome(hit.get("rc", 0), float(hit.get("duration_ms") or 0.0),
                       cached=True, key=key, tool=tool)

    res = runner()
    rc = getattr(res, "rc", 1)
    duration_ms = float(getattr(res, "duration_ms", 0.0))
    stored = cache.put(key, tool=tool, tool_sha256=sha256_file(path),
                       rc=rc, duration_ms=duration_ms, args=args)
    if emit is not None and not stored:
        emit("oc-cache: MISS %s key=%s rc=%s (not cached: only a PASS is "
             "stored)" % (tool, key[:12], rc))
    return Outcome(rc, duration_ms, cached=False, key=key, tool=tool,
                   out=getattr(res, "out", ""), err=getattr(res, "err", ""))


# =============================================================================
# the cache itself
# =============================================================================
class Cache:
    """A bounded directory of one-JSON-file-per-key PASS records.

    ONE FILE PER ENTRY, no shared index. An index would need a lock for every
    read and every write, and a lock is the thing that breaks under ``-n auto``
    when eight workers finish at once. Per-entry files make a hit a single
    ``read_text`` and a store a single ``os.replace`` (atomic within a
    filesystem), so concurrent workers can only ever write the same bytes twice.

    Pruning is LRU by the ``last_used`` stamp each hit rewrites. A hit therefore
    costs one small write — accepted deliberately: without it a leg that is
    green every day for a month would be the first thing pruned, which is
    exactly backwards.
    """

    def __init__(self, root, *, cap=DEFAULT_CAP, verbose=False):
        self.root = Path(root)
        self.entries_dir = self.root / "entries"
        self.cap = int(cap) if int(cap) > 0 else DEFAULT_CAP
        self.verbose = bool(verbose)
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0
        self.stores = 0
        self.pruned = 0

    # -- paths ---------------------------------------------------------------
    def path_for(self, key: str) -> Path:
        return self.entries_dir / (key + ENTRY_SUFFIX)

    # -- read ----------------------------------------------------------------
    def get(self, key: str):
        """The stored PASS for ``key``, or ``None``.

        Three independent reasons to answer ``None``, each a defect that would
        otherwise be invisible: the file is absent, the file is unreadable or
        corrupt (a half-written entry from a killed run), or the entry's
        ``cache_version`` is not this module's (the key SHAPE changed, so a
        matching hex string is a coincidence, not a match).
        """
        p = self.path_for(key)
        try:
            entry = json.loads(p.read_text())
        except (OSError, ValueError):
            self.misses += 1
            return None
        if not isinstance(entry, dict):
            self.misses += 1
            return None
        if entry.get("cache_version") != CACHE_VERSION:
            self.misses += 1
            return None
        if entry.get("rc") != 0:
            # Belt and braces: put() already refuses, but an entry that predates
            # that rule (or was hand-edited) must never serve a FAIL as a PASS.
            self.misses += 1
            return None
        entry["last_used"] = _now()
        entry["uses"] = int(entry.get("uses") or 0) + 1
        _write_json(p, entry)          # LRU stamp; failure here is not fatal
        self.hits += 1
        return entry

    # -- write ---------------------------------------------------------------
    def put(self, key: str, *, tool: str, tool_sha256: str, rc: int,
            duration_ms: float, args=(), now=None) -> bool:
        """Store a PASS. Returns False for anything that is not rc 0.

        RULE 2 IS ENFORCED HERE, in the one place every writer passes through.
        A cached failure makes a flaky leg permanently red — and, worse, makes a
        fix invisible: the tool would stay green-in-the-cache/red-on-the-box
        forever. ``timed_out`` arrives as rc 124 and is refused by the same test.
        """
        if rc != 0:
            return False
        entry = {
            "cache_version": CACHE_VERSION,
            "key": key,
            "tool": tool,
            "rc": 0,
            "duration_ms": round(float(duration_ms), 1),
            "ts": now or _now(),
            "last_used": now or _now(),
            "uses": 1,
            "tool_sha256": tool_sha256,
            "args": [str(a) for a in args],
        }
        _write_json(self.path_for(key), entry)
        self.stores += 1
        self.prune()
        return True

    # -- prune ---------------------------------------------------------------
    def prune(self) -> int:
        """Drop least-recently-USED entries until ``cap`` remain. Returns count."""
        entries = self._load_all()
        over = len(entries) - self.cap
        if over <= 0:
            return 0
        entries.sort(key=lambda kv: (kv[1].get("last_used") or "",
                                     kv[1].get("ts") or ""))
        removed = 0
        for path, _entry in entries[:over]:
            try:
                path.unlink()
                removed += 1
            except OSError:            # pragma: no cover - raced with another worker
                pass
        self.pruned += removed
        return removed

    def _load_all(self):
        out = []
        for p in self.entries_dir.glob("*" + ENTRY_SUFFIX):
            try:
                e = json.loads(p.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(e, dict):
                out.append((p, e))
        return out

    # -- reporting -----------------------------------------------------------
    def hit_message(self, entry: dict) -> str:
        """The line a hit prints under ``-v``/``--oc-cache-verbose``.

        A hit that says nothing is indistinguishable from a leg that ran and
        passed in 0 ms, which is how a cache stops being trustworthy: the whole
        value of the message is that it names the KEY, so a reader can go look
        at what that key was made of.
        """
        return ("oc-cache: HIT %s key=%s sha256=%s age=%ss saved=%sms" % (
            entry.get("tool", "?"),
            str(entry.get("key", ""))[:12],
            str(entry.get("tool_sha256", ""))[:12],
            _age_s(entry.get("ts")),
            entry.get("duration_ms"),
        ))

    def summary(self) -> str:
        return ("oc-cache: hits=%d misses=%d stores=%d pruned=%d entries=%d/%d"
                % (self.hits, self.misses, self.stores, self.pruned,
                   len(self._load_all()), self.cap))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _age_s(ts) -> str:
    try:
        then = time.mktime(time.strptime(str(ts), "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, TypeError):
        return "?"
    # strptime/mktime read the stamp as LOCAL time; the stamp is UTC. The age is
    # only ever read as "roughly how stale is this", so a whole-hours skew is
    # tolerated rather than papered over with a timezone database dependency.
    return "%d" % max(0, int(time.time() - then))


def _write_json(path: Path, payload: dict) -> None:
    """Atomic write: tmp in the SAME dir, then ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    try:
        tmp.write_text(json.dumps(payload, sort_keys=True))
        os.replace(tmp, path)
    finally:
        if tmp.exists():               # pragma: no cover - replace succeeded
            try:
                tmp.unlink()
            except OSError:
                pass


# =============================================================================
# pytest wiring — the plugin half
# =============================================================================
OPT_CACHE = "--oc-cache"
OPT_VERBOSE = "--oc-cache-verbose"
OPT_DIR = "--oc-cache-dir"
OPT_MAX = "--oc-cache-max"


def pytest_addoption(parser) -> None:
    group = parser.getgroup("oc-cache", "opt-in content-hash selftest cache")
    group.addoption(OPT_CACHE, action="store_true", default=False,
                    dest="oc_cache",
                    help="enable the content-hash selftest result cache "
                         "(same as OC_PYTEST_CACHE=1). OFF by default; the "
                         "ship gate never sets it.")
    group.addoption(OPT_VERBOSE, action="store_true", default=False,
                    dest="oc_cache_verbose",
                    help="print every cache HIT/MISS with its key (implied "
                         "by -v)")
    group.addoption(OPT_DIR, action="store", default=None,
                    dest="oc_cache_dir", metavar="PATH",
                    help="cache directory (default: $OC_PYTEST_CACHE_DIR or "
                         "$XDG_CACHE_HOME/oc-pytest-cache). Never inside the "
                         "repo tree.")
    group.addoption(OPT_MAX, action="store", default=None, dest="oc_cache_max",
                    metavar="N",
                    help="max entries before LRU pruning (default %d)"
                         % DEFAULT_CAP)


def enabled(config) -> bool:
    """The ONE place "is the cache on" is decided.

    ``--oc-cache`` OR ``OC_PYTEST_CACHE=1``. Anything else — including the ship
    gate, which sets neither — leaves it off, and ``from_config`` then returns
    ``None`` so call sites skip even the key computation.
    """
    if getattr(config.option, "oc_cache", False):
        return True
    return os.environ.get(ENV_ENABLE, "") == "1"


def verbose(config) -> bool:
    if getattr(config.option, "oc_cache_verbose", False):
        return True
    # -v/-vv is pytest's own verbosity; a cache hit is exactly the kind of thing
    # a verbose run exists to explain.
    #
    # The comparison is `> 0`, NOT `bool(...)`: `-q` sets verbose to -1, and
    # bool(-1) is True, so the truthiness form treated a QUIET run as verbose
    # and printed cache lines where today's output had none. Verified against
    # argparse rather than assumed — -q/-qq drive verbose negative.
    return getattr(config.option, "verbose", 0) > 0


def cache_dir_for(config) -> Path:
    opt = getattr(config.option, "oc_cache_dir", None)
    if opt:
        return Path(opt).expanduser()
    return default_cache_dir()


def from_config(config):
    """A ``Cache`` when enabled, else ``None`` — the passthrough signal."""
    if not enabled(config):
        return None
    cap = getattr(config.option, "oc_cache_max", None) or cap_from_env()
    return Cache(cache_dir_for(config), cap=int(cap), verbose=verbose(config))


def pytest_configure(config) -> None:
    """Register the cache on the config; announce the path when verbose.

    The path is printed on the CONTROLLER only and only when verbose, so a
    normal run's output is unchanged (rule 1: no extra output by default).
    """
    cache = from_config(config)
    config._oc_cache = cache                        # type: ignore[attr-defined]
    if cache is not None and verbose(config) and not hasattr(config, "workerinput"):
        config.pluginmanager.getplugin("terminalreporter")  # may be None
        sys.stderr.write("oc-cache: enabled dir=%s cap=%d (opt-in)\n"
                         % (cache.root, cache.cap))


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """The run's cache tally — VERBOSE ONLY.

    Rule 1 is that default behaviour is byte-identical to no-cache, and the
    battery runs ``-q``. An unconditional summary line is exactly the kind of
    extra output that rule forbids, so the tally is gated the same way a hit
    line is: ``-v`` or ``--oc-cache-verbose``. Nothing is lost — the same
    numbers are in the entries themselves and in the hit lines.
    """
    cache = getattr(config, "_oc_cache", None)
    if cache is None or hasattr(config, "workerinput"):
        return
    if not verbose(config):
        return
    terminalreporter.write_line(cache.summary())
