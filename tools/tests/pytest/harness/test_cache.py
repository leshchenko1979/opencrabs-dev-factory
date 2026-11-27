"""The content-hash selftest cache — proven by COUNTING INVOCATIONS, not timing.

Every leg here answers a question a stopwatch cannot: *did the tool actually
run?* A stub tool appends one line per execution to a counter file, so "cache
hit" is an assertion about a file with N lines in it, and a flaky 40 ms selftest
can never make the answer ambiguous.

The seven properties, in the order the design requirements state them:

  1. OFF BY DEFAULT          — two runs, two executions, nothing written.
  2. HIT on unchanged bytes  — two runs, ONE execution.
  3. MISS when the tool's bytes change.
  4. MISS when a SOURCED LIB's bytes change (the subtle one — transitive).
  5. NEVER a FAIL            — a non-zero rc is executed both times, stored never.
  6. PRUNING                 — past the cap, the least-recently-used go first.
  7. KEY STABILITY           — the same inputs hash the same in two processes.

ISOLATION: every test builds its cache in ``tmp_path``, so nothing here shares a
directory with another test and the whole module is xdist-safe by construction —
no ``serial`` marker is needed for correctness. The two legs that shell out to a
NESTED pytest session are marked serial anyway, because pytester's own temp
handling is the one thing here that is not obviously worker-local.

A note on why the stub is a shell script rather than a mock: the cache's job is
to decide whether a SUBPROCESS runs, so the thing it skips must be a real
subprocess with a real exit code. A mock would let a bug in the rc handling pass
green.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import conftest as cf
from lib import cache as oc_cache

pytest_plugins = ("pytester",)

REPO_ROOT = cf.REPO_ROOT


# =============================================================================
# helpers — a stub tool that COUNTS, and a fake tools tree
# =============================================================================
def make_stub_tool(tmp_path, *, rc=0, sources=(), name="oc-stub"):
    """A tiny ``--selftest`` tool that appends one line per execution.

    ``sources`` are relative paths under ``tmp_path/tools/`` the stub SOURCES
    before exiting — that is what lets leg 4 prove a lib change invalidates the
    tool that sources it, using a real ``.`` statement rather than a mock.
    """
    tools = tmp_path / "tools"
    (tools / "lib").mkdir(parents=True, exist_ok=True)
    counter = tmp_path / "invocations.log"

    src_lines = []
    for rel in sources:
        lib = tools / rel
        lib.parent.mkdir(parents=True, exist_ok=True)
        if not lib.exists():
            lib.write_text("# stub lib %s\nstub_lib_value() { echo v1; }\n" % rel)
        src_lines.append('. "%s"' % lib)

    body = textwrap.dedent(
        """\
        #!/bin/sh
        {sources}
        echo run >> {counter}
        exit {rc}
        """
    ).format(sources="\n".join(src_lines), counter=counter, rc=rc)

    tool = tools / name
    tool.write_text(body)
    tool.chmod(0o755)
    return tool, counter


def count(counter: Path) -> int:
    """How many times the stub actually executed."""
    try:
        return len(counter.read_text().splitlines())
    except OSError:
        return 0


class Runner:
    """A ``runner`` callable for ``run_cached`` that executes the stub for real."""

    def __init__(self, tool: Path):
        self.tool = tool
        self.calls = 0

    def __call__(self):
        self.calls += 1
        p = subprocess.run([str(self.tool), "--selftest"],
                           capture_output=True, text=True, timeout=60)

        class _R:
            rc = p.returncode
            duration_ms = 1.0
            out = p.stdout
            err = p.stderr
        return _R()


def stub_tool_for(tmp_path, monkeypatch, *, rc=0, sources=(), name="oc-stub"):
    """Point ``cf.tool_path`` at a STUB so a fixture leg is hermetic.

    The fixture legs below exercise the WIRING (does ``cached_selftest`` call
    ``run_cached`` with the right tool, does a hit reach ``Result.cached``), not
    a real tool's health. Using a real tool made them fail whenever the box was
    loaded enough for its selftest to time out — a flake about the machine, not
    about the cache. The stub counts its own executions, so "did it run" is a
    counter, never a clock.
    """
    tool, counter = make_stub_tool(tmp_path, rc=rc, sources=sources, name=name)
    real = cf.tool_path
    monkeypatch.setattr(cf, "tool_path",
                        lambda n: tool if n == name else real(n))
    return tool, counter

def new_cache(tmp_path, **kw):
    return oc_cache.Cache(tmp_path / "cache", **kw)


# =============================================================================
# 1. OFF BY DEFAULT — the default behaviour must be today's behaviour
# =============================================================================
def test_cache_is_none_without_the_option_or_the_env(monkeypatch):
    """``from_config`` answers ``None`` unless asked, and the option alone is enough.

    This is rule 1 in one assertion pair: the ship gate sets neither
    ``--oc-cache`` nor ``OC_PYTEST_CACHE``, so the gate can never be satisfied
    from a cache — it always runs every selftest for real.
    """
    class _Opt:
        oc_cache = False
        oc_cache_verbose = False
        oc_cache_dir = None
        oc_cache_max = None
        verbose = 0

    class _Cfg:
        option = _Opt()

    monkeypatch.delenv(oc_cache.ENV_ENABLE, raising=False)
    assert oc_cache.enabled(_Cfg()) is False
    assert oc_cache.from_config(_Cfg()) is None

    monkeypatch.setenv(oc_cache.ENV_ENABLE, "1")
    assert oc_cache.enabled(_Cfg()) is True
    assert isinstance(oc_cache.from_config(_Cfg()), oc_cache.Cache)

    # ...and the flag alone, with the env unset, is equally sufficient.
    monkeypatch.delenv(oc_cache.ENV_ENABLE, raising=False)

    class _Opt2(_Opt):
        oc_cache = True
    _Cfg.option = _Opt2()
    assert oc_cache.from_config(_Cfg()) is not None


def test_off_by_default_runs_the_tool_every_time(tmp_path, capsys):
    """Two runs with ``cache=None`` => two executions, zero output, zero writes.

    Byte-identical to today is the bar: not "no hits" but *no cache machinery at
    all*. The absence of the cache directory afterwards is the proof that no
    write happened, and ``capsys`` proves nothing was printed.
    """
    tool, counter = make_stub_tool(tmp_path)
    runner = Runner(tool)
    for _ in range(2):
        out = oc_cache.run_cached(None, tool="oc-stub", tool_path=tool,
                                  runner=runner, emit=lambda m: print(m))
        assert out.cached is False
        assert out.rc == 0
    assert runner.calls == 2, "the cache must not short-circuit when it is off"
    assert count(counter) == 2
    assert capsys.readouterr().out == "", "cache-off must print nothing"
    assert not (tmp_path / "cache").exists(), "cache-off must write nothing"


# =============================================================================
# 2. HIT on unchanged bytes
# =============================================================================
def test_hit_on_unchanged_bytes_executes_once(tmp_path):
    """Second run: zero executions, and the outcome says it was cached."""
    tool, counter = make_stub_tool(tmp_path)
    cache = new_cache(tmp_path)
    runner = Runner(tool)

    first = oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                                runner=runner)
    assert (first.cached, first.rc, runner.calls, count(counter)) == (False, 0, 1, 1)

    second = oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                                 runner=runner)
    assert (second.cached, second.rc) == (True, 0)
    assert runner.calls == 1, "a hit must not execute the tool"
    assert count(counter) == 1
    # The key the hit reported is the key the miss stored.
    assert second.key == first.key
    # ...and a hit still reports the ORIGINAL duration, so a receipt's timing
    # keeps saying what the leg really costs.
    assert second.duration_ms == pytest.approx(1.0)


def test_hit_records_provenance(tmp_path):
    """Rule 5: key, tool, rc, duration_ms, ts, tool_sha256 — all on the entry."""
    tool, _ = make_stub_tool(tmp_path)
    cache = new_cache(tmp_path)
    oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                        runner=Runner(tool))
    key = oc_cache.cache_key(tool)
    entry = json.loads(cache.path_for(key).read_text())
    for field in ("key", "tool", "rc", "duration_ms", "ts", "tool_sha256",
                  "cache_version"):
        assert field in entry, "cache entry is missing provenance: %s" % field
    assert entry["key"] == key
    assert entry["tool"] == "oc-stub"
    assert entry["rc"] == 0
    assert entry["tool_sha256"] == oc_cache.sha256_file(tool)
    assert entry["cache_version"] == oc_cache.CACHE_VERSION


def test_a_hit_is_never_invisible(tmp_path):
    """Rule 5: the hit line names the key, so a hit cannot read as a 0 ms pass."""
    tool, _ = make_stub_tool(tmp_path)
    cache = new_cache(tmp_path, verbose=True)
    runner = Runner(tool)
    oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool, runner=runner)

    seen = []
    oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool, runner=runner,
                        emit=seen.append)
    assert len(seen) == 1, "a cache hit must emit exactly one line"
    line = seen[0]
    assert line.startswith("oc-cache: HIT oc-stub key=")
    assert oc_cache.cache_key(tool)[:12] in line
    assert "saved=1.0ms" in line


# =============================================================================
# 3. MISS when the tool's own bytes change
# =============================================================================
def test_miss_when_tool_bytes_change(tmp_path):
    """A one-byte edit to the tool invalidates the entry — bytes, never mtime."""
    tool, counter = make_stub_tool(tmp_path)
    cache = new_cache(tmp_path)
    runner = Runner(tool)

    oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool, runner=runner)
    key_before = oc_cache.cache_key(tool)

    # Same path, same size class, different CONTENT. mtime is untouched on
    # purpose (os.utime back to the original): an mtime-keyed cache would call
    # this unchanged, which is the defect the content hash exists to avoid.
    stat = tool.stat()
    tool.write_text(tool.read_text().replace("exit 0", "exit 0  # changed"))
    os.utime(tool, (stat.st_atime, stat.st_mtime))

    key_after = oc_cache.cache_key(tool)
    assert key_after != key_before, "content change must change the key"

    out = oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                              runner=runner)
    assert out.cached is False
    assert runner.calls == 2
    assert count(counter) == 2


# =============================================================================
# 4. MISS when a SOURCED LIB changes — the subtle one
# =============================================================================
def test_miss_when_a_sourced_lib_changes(tmp_path):
    """The tool's own bytes are identical; the LIB it sources is not.

    This is the leg that makes the cache safe to use on this repo: 68 tools
    source ``lib/oc-log.sh``, so a lib fix must invalidate every one of them.
    The stub here sources a real ``. "$path"`` line, and only the lib is edited.
    """
    tool, counter = make_stub_tool(tmp_path, sources=("lib/oc-stub-lib.sh",))
    lib = tmp_path / "tools" / "lib" / "oc-stub-lib.sh"
    tools_dir = tmp_path / "tools"
    cache = new_cache(tmp_path)
    runner = Runner(tool)

    assert lib in oc_cache.referenced_files(tool, tools_dir=tools_dir), \
        "the stub's `. path` line must be discovered as a source"

    oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool, runner=runner)
    key_before = oc_cache.cache_key(tool, tools_dir=tools_dir)
    tool_bytes = oc_cache.sha256_file(tool)

    lib.write_text("# stub lib, v2 — a fix\nstub_lib_value() { echo v2; }\n")
    assert oc_cache.sha256_file(tool) == tool_bytes, "the TOOL must be unchanged"

    key_after = oc_cache.cache_key(tool, tools_dir=tools_dir)
    assert key_after != key_before, \
        "a sourced lib's bytes must invalidate the tool that sources it"

    out = oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                              runner=runner, extra={"tools_dir": str(tools_dir)})
    # `extra` is in the key too, so compare against a run WITHOUT extra by
    # re-running the same call: the second call must be a HIT on the new key.
    assert out.cached is False
    again = oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                               runner=runner, extra={"tools_dir": str(tools_dir)})
    assert again.cached is True, "the new key must be stored after the re-run"
    assert count(counter) == 2


def test_sourced_libs_are_transitive(tmp_path):
    """A lib two hops down must invalidate the tool three hops up."""
    tools = tmp_path / "tools"
    (tools / "lib").mkdir(parents=True)
    (tools / "lib" / "a.sh").write_text('. "$OC_TOOLS_DIR/lib/b.sh"\n')
    (tools / "lib" / "b.sh").write_text('. "$OC_TOOLS_DIR/lib/c.sh"\n')
    (tools / "lib" / "c.sh").write_text("c_value() { echo 1; }\n")
    tool = tools / "oc-chain"
    tool.write_text('#!/bin/sh\n. "$OC_TOOLS_DIR/lib/a.sh"\nexit 0\n')
    tool.chmod(0o755)

    closure = oc_cache.sourced_libs(tool, tools_dir=tools)
    assert set(closure) == {"lib/a.sh", "lib/b.sh", "lib/c.sh"}, closure

    key_before = oc_cache.cache_key(tool, tools_dir=tools)
    (tools / "lib" / "c.sh").write_text("c_value() { echo 2; }\n")
    assert oc_cache.cache_key(tool, tools_dir=tools) != key_before, \
        "the deepest lib in the chain must reach the key"


def test_real_oc_ledger_closure_includes_its_libs():
    """Against the REAL repo: oc-ledger's key covers the libs it actually sources.

    A closure that quietly returned nothing would make every test above pass
    while the cache served stale PASSes on the real battery — so one leg reads
    the real tool and names the libs that must be in there.
    """
    ledger = cf.tool_path("oc-ledger")
    closure = oc_cache.sourced_libs(ledger)
    names = {Path(p).name for p in closure}
    assert "oc-log.sh" in names, closure
    assert "oc-root.sh" in names, closure
    # oc-log.sh is the lib 68 tools source; if it can drop out of the closure,
    # a one-line fix there would leave every one of them cached as green.
    assert "tools/lib/oc-log.sh" in closure

    # Every entry is a hash, and the tool's own bytes are in the material.
    material = oc_cache.key_material(ledger)
    assert material["tool"] == "oc-ledger"
    assert material["tool_sha256"] == oc_cache.sha256_file(ledger)
    assert len(material["libs"]) >= 3
    assert all(len(h) == 64 for _p, h in material["libs"])


def test_runtime_receipts_are_not_in_the_key():
    """``tools/tests/battery-last.json`` is rewritten every run — never a key input.

    If it were, the key would change on every invocation and the cache could
    never hit. This asserts the exclusion on the real tool that mentions it.
    """
    ledger = cf.tool_path("oc-ledger")
    closure = oc_cache.sourced_libs(ledger)
    assert "tools/tests/battery-last.json" not in closure
    assert "tools/tests/run.sh" not in closure, \
        "a die() message naming run.sh must not pull the harness into the key"


# =============================================================================
# 5. NEVER CACHE A FAIL
# =============================================================================
def test_never_stores_a_nonzero_rc(tmp_path):
    """A failing stub is executed BOTH times and never enters the cache.

    Caching a failure would make a flaky leg permanently red — and, worse, make
    a fix invisible: the tool would stay red-in-the-cache/red-on-the-box with no
    way to see that it had been fixed.
    """
    tool, counter = make_stub_tool(tmp_path, rc=3)
    cache = new_cache(tmp_path)
    runner = Runner(tool)

    for _ in range(2):
        out = oc_cache.run_cached(cache, tool="oc-stub", tool_path=tool,
                                  runner=runner)
        assert out.rc == 3
        assert out.cached is False, "a FAIL must never be served from the cache"

    assert runner.calls == 2
    assert count(counter) == 2
    assert list(cache.entries_dir.glob("*.json")) == [], \
        "a non-zero rc must leave no entry behind"


def test_put_refuses_nonzero_rc_and_timed_out(tmp_path):
    """The refusal lives in ``put`` — the one place every writer passes through.

    ``timeout(1)``'s 124 (the process-group kill) is covered by the same test:
    a timed-out leg is not a verdict, and caching it would make a hung tool
    permanently "green" in 0 ms.
    """
    cache = new_cache(tmp_path)
    assert cache.put("k1", tool="t", tool_sha256="x", rc=1,
                     duration_ms=10.0) is False
    assert cache.put("k2", tool="t", tool_sha256="x", rc=124,
                     duration_ms=10.0) is False
    assert list(cache.entries_dir.glob("*.json")) == []
    assert cache.put("k3", tool="t", tool_sha256="x", rc=0,
                     duration_ms=10.0) is True
    assert len(list(cache.entries_dir.glob("*.json"))) == 1


def test_get_ignores_a_hand_written_fail_entry(tmp_path):
    """Defence in depth: an entry with rc!=0 on disk is never served as a PASS."""
    cache = new_cache(tmp_path)
    cache.path_for("badkey").write_text(json.dumps({
        "cache_version": oc_cache.CACHE_VERSION, "key": "badkey",
        "tool": "oc-stub", "rc": 1, "duration_ms": 5.0,
        "ts": "2026-01-01T00:00:00Z", "tool_sha256": "x"}))
    assert cache.get("badkey") is None


def test_get_ignores_a_corrupt_entry(tmp_path):
    """A killed run leaves a half-written entry; it must read as a MISS, not crash."""
    cache = new_cache(tmp_path)
    cache.path_for("trunc").write_text('{"cache_version": 1, "rc": 0')
    assert cache.get("trunc") is None


def test_get_ignores_an_older_cache_version(tmp_path):
    """A CACHE_VERSION bump must not match an old entry's hex key by accident."""
    cache = new_cache(tmp_path)
    cache.path_for("oldkey").write_text(json.dumps({
        "cache_version": oc_cache.CACHE_VERSION - 1, "key": "oldkey",
        "tool": "oc-stub", "rc": 0, "duration_ms": 5.0,
        "ts": "2026-01-01T00:00:00Z", "tool_sha256": "x"}))
    assert cache.get("oldkey") is None


# =============================================================================
# 6. PRUNING — bounded, LRU
# =============================================================================
def test_pruning_drops_the_oldest_first(tmp_path):
    """Fill past the cap: the least-recently-USED go, and the cap holds.

    ``now`` is passed explicitly so the ordering is a fact of the test rather
    than of the clock — a pruning test that depends on two ``time.gmtime`` calls
    landing in different seconds passes or fails by luck.
    """
    cache = new_cache(tmp_path, cap=3)
    for i in range(5):
        cache.put("k%d" % i, tool="oc-stub", tool_sha256="x", rc=0,
                  duration_ms=1.0, now="2026-01-0%dT00:00:00Z" % (i + 1))

    keys = sorted(json.loads(p.read_text())["key"]
                  for p in cache.entries_dir.glob("*.json"))
    assert keys == ["k2", "k3", "k4"], "the two oldest must have been pruned"
    assert cache.pruned >= 2


def test_a_hit_makes_an_entry_recent(tmp_path):
    """Use, not age, decides who is pruned — otherwise a daily-green leg dies first."""
    cache = new_cache(tmp_path, cap=2)
    cache.put("keep", tool="oc-stub", tool_sha256="x", rc=0, duration_ms=1.0,
              now="2026-01-01T00:00:00Z")
    cache.put("newer", tool="oc-stub", tool_sha256="x", rc=0, duration_ms=1.0,
              now="2026-01-02T00:00:00Z")

    # Touch `keep` so it becomes the most recently used, then overflow the cap.
    entry = cache.get("keep")
    assert entry is not None
    cache.put("newest", tool="oc-stub", tool_sha256="x", rc=0, duration_ms=1.0,
              now="2026-01-03T00:00:00Z")

    keys = {json.loads(p.read_text())["key"]
            for p in cache.entries_dir.glob("*.json")}
    assert keys == {"keep", "newest"}, "the USED entry must outlive the stale one"


def test_default_cap_is_bounded():
    """A cache that grows forever is a new defect; the default must be finite."""
    assert oc_cache.DEFAULT_CAP == 200
    assert oc_cache.Cache("/tmp/oc-cap-probe-%d" % os.getpid()).cap == 200


# =============================================================================
# 7. KEY STABILITY across processes
# =============================================================================
def test_key_is_stable_across_two_processes(tmp_path):
    """Same inputs, two separate interpreters, one key — no PYTHONHASHSEED luck.

    A key built from a ``set`` iteration order or an unsorted dict would differ
    between processes and the cache would miss forever, which looks exactly like
    a cache that works (it never serves a stale PASS) and never helps.
    """
    ledger = cf.tool_path("oc-ledger")
    code = (
        "import sys; sys.path.insert(0, %r);"
        "from lib import cache;"
        "print(cache.cache_key(%r, args=['--selftest']))"
        % (str(cf.PYTEST_DIR), str(ledger))
    )
    runs = []
    for seed in ("0", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        p = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env, timeout=120)
        assert p.returncode == 0, p.stderr
        runs.append(p.stdout.strip())

    assert runs[0] == runs[1], "the key must not depend on hash seed"
    assert runs[0] == oc_cache.cache_key(ledger, args=["--selftest"])
    assert len(runs[0]) == 64


def test_key_covers_args_and_interpreter():
    """argv and the interpreter are in the material: a different suite is a miss."""
    ledger = cf.tool_path("oc-ledger")
    a = oc_cache.cache_key(ledger)
    b = oc_cache.cache_key(ledger, args=["--verbose"])
    assert a != b, "extra argv must change the key"

    material = oc_cache.key_material(ledger)
    assert material["python"] == oc_cache.interpreter_tag()
    assert "cache_version" in material
    assert material["conftest_sha256"] == oc_cache.conftest_digest()


def test_two_checkouts_of_the_same_tree_share_a_key(tmp_path):
    """The key is repo-RELATIVE, so a second worktree is a hit, not a miss.

    This is the mtime defect restated: worktrees have different mtimes and
    different absolute paths, and neither may enter the key.
    """
    ledger = cf.tool_path("oc-ledger")
    other = tmp_path / "other-checkout" / "tools"
    other.mkdir(parents=True)
    # Same content at a different absolute path.
    copy = other / "state"
    copy.mkdir()
    (copy / "oc-ledger").write_bytes(ledger.read_bytes())

    assert oc_cache.sourced_libs(ledger) == oc_cache.sourced_libs(copy / "oc-ledger"), \
        "the closure must be spelled repo-relative, not absolute"


# =============================================================================
# location — never inside the repo tree (the stray-guard)
# =============================================================================
def test_default_dir_is_outside_the_repo(monkeypatch, tmp_path):
    """Rule 7: the cache lives in the user cache dir, never in the checkout.

    An untracked path under the skill repo trips the sync stray-guard (die 7),
    which reads a plain ``git status --porcelain`` and refuses a version bump
    because of one lane's scratch.
    """
    monkeypatch.delenv(oc_cache.ENV_DIR, raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    d = oc_cache.default_cache_dir()
    assert d == tmp_path / "xdg" / "oc-pytest-cache"
    assert oc_cache.inside_repo(d) is False

    monkeypatch.setenv(oc_cache.ENV_DIR, str(tmp_path / "explicit"))
    assert oc_cache.default_cache_dir() == tmp_path / "explicit"


def test_the_real_default_is_not_in_the_repo():
    """Without any override the answer is still outside the checkout."""
    assert oc_cache.inside_repo(oc_cache.default_cache_dir()) is False


# =============================================================================
# the plugin half — options, and the off-by-default silence
# =============================================================================
def seed_plugin(pytester):
    """Give the NESTED run the same plugin wiring the real run gets.

    ``pytester`` builds a throwaway rootdir whose conftest knows nothing about
    ``lib.cache``, and ``-p lib.cache`` cannot help: ``-p`` is resolved at
    preparse, before any conftest has put the package on ``sys.path``. So the
    nested run gets a conftest that does what the real one does — sys.path
    first, then ``pytest_plugins`` — which also proves the real wiring works
    rather than proving a second, test-only path works.
    """
    # ``lib/`` lives at the pytest ROOT, not beside this module: the nested run's
    # sys.path entry must be the root, and this file's own parent is now a
    # subject subfolder with no ``lib`` in it (hence cf.PYTEST_DIR, not __file__).
    pytester.makeconftest(textwrap.dedent(
        """\
        import sys
        sys.path.insert(0, %r)
        pytest_plugins = ("lib.cache",)
        """
    ) % str(cf.PYTEST_DIR))

@pytest.mark.serial
@pytest.mark.xdist_group("cache")
def test_plugin_is_silent_and_inert_by_default(pytester):
    """A nested pytest run without the flag prints no cache line and writes nothing.

    The bar for "off by default" is not "no hits" — it is that a reader of the
    output cannot tell this plugin exists.
    """
    pytester.makepyfile("""
        def test_ok():
            assert True
    """)
    seed_plugin(pytester)
    cache_dir = pytester.path / "cachedir"
    result = pytester.runpytest("-p", "no:cacheprovider", "-q",
                                "--oc-cache-dir", str(cache_dir))
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*oc-cache:*")
    assert not cache_dir.exists(), "an off run must not create the cache dir"


@pytest.mark.serial
@pytest.mark.xdist_group("cache")
def test_plugin_announces_the_cache_when_asked(pytester):
    """With the flag the run says where the cache is — a hit is never invisible."""
    pytester.makepyfile("""
        def test_ok():
            assert True
    """)
    seed_plugin(pytester)
    cache_dir = pytester.path / "cachedir"
    result = pytester.runpytest("-p", "no:cacheprovider", "-q", "--oc-cache",
                                "--oc-cache-verbose", "--oc-cache-dir",
                                str(cache_dir))
    result.assert_outcomes(passed=1)
    # The announcement is on stderr (it is diagnostics, not a test result), so
    # a caller redirecting pytest's report stream still sees it.
    result.stderr.fnmatch_lines(["*oc-cache: enabled dir=*cap=200*"])
    result.stdout.fnmatch_lines(["*oc-cache: hits=0 misses=0*"])


# =============================================================================
# parity with the foundation — resolve_tool must not drift
# =============================================================================
def test_resolve_tool_matches_conftest():
    """The cache's tool resolver and the foundation's must agree, tool for tool.

    Two resolvers is one too many; they exist because ``lib/cache.py`` must not
    import ``conftest`` (pytest imports conftest, conftest imports lib). This
    leg is the contract that keeps them identical.
    """
    skip = {"lib", "tests", "archive", "docs", "instruments"}
    names = []
    for sub in sorted(cf.TOOLS_DIR.iterdir()):
        if not sub.is_dir() or sub.name in skip:
            continue
        for cand in sorted(sub.iterdir()):
            if cand.is_file() and os.access(cand, os.X_OK) and \
                    cand.name.startswith("oc-"):
                names.append(cand.name)
    assert len(names) >= 30, "expected the full tool population, got %d" % len(names)
    for name in names:
        assert oc_cache.resolve_tool(name) == cf.tool_path(name), name


def test_resolve_tool_refuses_a_missing_name():
    with pytest.raises(FileNotFoundError):
        oc_cache.resolve_tool("oc-no-such-tool-exists")

# =============================================================================
# end to end — the FIXTURE, not just the library
# =============================================================================
def test_fixture_is_a_passthrough_when_the_cache_is_off(
        cached_selftest, tmp_path, monkeypatch):
    """No flag: the fixture executes, and says so via ``.cached``."""
    tool, counter = stub_tool_for(tmp_path, monkeypatch)
    res = cached_selftest("oc-stub", timeout=120)
    assert res.rc == 0
    assert res.cached is False, "a cache-off run must never report a hit"
    assert "--selftest" in res.cmd
    assert count(counter) == 1, "the cache-off path must really execute"

def test_fixture_skips_the_subprocess_on_a_second_identical_call(
        request, cached_selftest, monkeypatch, tmp_path):
    """Enabled: the same tool twice = one real run, then a HIT.

    The cache is built here rather than taken from the session so this leg owns
    its directory (``tmp_path``), which is what keeps the module xdist-safe.
    """
    cache = new_cache(tmp_path)
    monkeypatch.setattr(request.config, "_oc_cache", cache, raising=False)
    tool, counter = stub_tool_for(tmp_path, monkeypatch)

    first = cached_selftest("oc-stub", timeout=120)
    assert first.rc == 0 and first.cached is False
    assert count(counter) == 1

    second = cached_selftest("oc-stub", timeout=120)
    assert second.rc == 0
    assert second.cached is True, "an unchanged tool must hit the cache"
    # The hit replays the STORED duration (rounded on store), so a skipped 300 s
    # leg still reports what it cost — the saving is legible from the result.
    assert second.duration_ms == pytest.approx(first.duration_ms, abs=0.5)
    assert count(counter) == 1, "a HIT must not spawn the subprocess again"

def test_fixture_still_runs_when_the_previous_run_failed(
        request, cached_selftest, monkeypatch, tmp_path):
    """A failing leg is never memoised: both calls execute for real."""
    cache = new_cache(tmp_path)
    monkeypatch.setattr(request.config, "_oc_cache", cache, raising=False)
    # A stub whose selftest is RED: rc=1 with no dependency on any real tool.
    tool, counter = stub_tool_for(tmp_path, monkeypatch, rc=1)

    first = cached_selftest("oc-stub", timeout=120)
    assert first.rc != 0 and first.cached is False
    second = cached_selftest("oc-stub", timeout=120)
    assert second.cached is False, "a FAIL must never be served from cache"
    assert second.rc != 0
    assert count(counter) == 2, "a red leg must re-run every time"

def test_fixture_hit_prints_its_key_when_verbose(
        request, cached_selftest, monkeypatch, tmp_path, capsys):
    """Rule 5 through the FIXTURE: a verbose hit names the key on stderr.

    The library-level leg (``test_a_hit_is_never_invisible``) proves ``emit``
    works when a caller supplies one. This leg proves the FIXTURE supplies one
    by default — without it a real run's hits were silent, which is the exact
    "hit indistinguishable from a 0 ms pass" failure the rule exists to stop.
    """
    cache = new_cache(tmp_path, verbose=True)
    monkeypatch.setattr(request.config, "_oc_cache", cache, raising=False)
    monkeypatch.setattr(request.config.option, "oc_cache_verbose", True,
                        raising=False)
    monkeypatch.setattr(request.config.option, "verbose", 1, raising=False)
    tool, counter = stub_tool_for(tmp_path, monkeypatch)

    first = cached_selftest("oc-stub", timeout=120)
    assert first.cached is False
    capsys.readouterr()          # drop the first call's output

    second = cached_selftest("oc-stub", timeout=120)
    assert second.cached is True
    err = capsys.readouterr().err
    assert "oc-cache: HIT oc-stub" in err, err
    assert oc_cache.cache_key(tool)[:12] in err
    assert count(counter) == 1

def test_fixture_hit_is_silent_without_verbose(
        request, cached_selftest, monkeypatch, tmp_path, capsys):
    """Rule 1 + 5 together: no ``-v`` means no extra output, even on a hit."""
    cache = new_cache(tmp_path, verbose=False)
    monkeypatch.setattr(request.config, "_oc_cache", cache, raising=False)
    monkeypatch.setattr(request.config.option, "oc_cache_verbose", False,
                        raising=False)
    monkeypatch.setattr(request.config.option, "verbose", 0, raising=False)
    tool, counter = stub_tool_for(tmp_path, monkeypatch)

    cached_selftest("oc-stub", timeout=120)
    capsys.readouterr()
    second = cached_selftest("oc-stub", timeout=120)
    assert second.cached is True
    captured = capsys.readouterr()
    assert "oc-cache: HIT" not in captured.err
    assert "oc-cache" not in captured.out

def test_quiet_runs_are_not_treated_as_verbose():
    """``-q`` sets verbose to -1; ``bool(-1)`` is True, so truthiness lied.

    A quiet run must never grow cache output: that is rule 1 ("byte-identical
    by default") read strictly, and the whole battery runs with ``-q``. The
    bug this pins was live — every ``-q`` run printed the enabled/summary
    lines — so it is worth a leg rather than a comment.
    """
    class _Opt:
        oc_cache_verbose = False
        verbose = -1                       # exactly what `-q` produces
    class _Cfg:
        option = _Opt()

    assert oc_cache.verbose(_Cfg()) is False
    _Opt.verbose = 0                       # the default
    assert oc_cache.verbose(_Cfg()) is False
    _Opt.verbose = 1                       # -v
    assert oc_cache.verbose(_Cfg()) is True
    _Opt.oc_cache_verbose = True           # --oc-cache-verbose wins regardless
    _Opt.verbose = -1
    assert oc_cache.verbose(_Cfg()) is True

def test_terminal_summary_is_verbose_only(tmp_path):
    """The run tally must not appear in a quiet run either.

    Rule 1 is byte-identical default output, and the battery runs ``-q``. The
    summary hook printed unconditionally, so every quiet ``--oc-cache`` run
    grew a line today's output never had. A HIT line is not the only way the
    cache can speak; the tally is the other one.
    """
    class _Reporter:
        def __init__(self):
            self.lines = []
        def write_line(self, line):
            self.lines.append(line)
    class _Opt:
        oc_cache_verbose = False
        verbose = -1                       # -q
    class _Cfg:
        option = _Opt()

    cfg = _Cfg()
    cache = oc_cache.Cache(tmp_path / "c", cap=5, verbose=False)
    cfg._oc_cache = cache

    reporter = _Reporter()
    oc_cache.pytest_terminal_summary(reporter, 0, cfg)
    assert reporter.lines == [], "a quiet run must emit no cache tally"

    _Opt.verbose = 1                       # -v
    oc_cache.pytest_terminal_summary(reporter, 0, cfg)
    assert len(reporter.lines) == 1
    assert "oc-cache: hits=" in reporter.lines[0]
