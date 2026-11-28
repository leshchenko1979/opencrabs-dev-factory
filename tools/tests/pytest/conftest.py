"""pytest foundation for the oc-* tool battery.

This is the DRY half of the battery -> pytest migration (see
``~/.opencrabs/profiles/ops/research/pytest-migration-plan.md`` §4/§5). It is
ADDITIVE: ``tools/tests/run.sh`` is untouched until parity is proven, and every
fixture here mirrors a block of that harness rather than re-inventing it.

WHY EACH FIXTURE EXISTS — every one of these replaces a defect that already
happened in ``run.sh``:

  1. ``scratch``      one root per worker (59 ``mktemp -d`` sites). The root
                      carries a ``.oc-battery-owner`` pid marker because a
                      child's EXIT trap once deleted its caller's tree mid-run
                      (run.sh:487-509, #171).
  2. ``state_dir``    ``OC_DEPLOY_STATE_DIR`` (21 hand-set sites; the default at
                      run.sh:2542 is the REAL profile).
  3. ``env_guard``    autouse; blocks the four live-state leaks that exist today
                      (see ``LIVE_ENV_VARS`` below) and restores PATH/HOME.
  4. ``ledger_sandbox`` copies the recipe at ``tools/state/oc-ledger:2771-2800``
                      verbatim — it is already correct and the tool's own
                      selftest proves it.
  5. ``git_repo``     identity pinned via ``-c user.name/-c user.email``,
                      because 4 repos today only work by accident of the
                      container's global git config.
  6. ``run_tool`` /   ``timeout`` is a REQUIRED kwarg and the kill is a
     ``run_selftest`` process-GROUP kill, because ``subprocess.run(timeout=)``
                      signals only the direct child and a selftest's
                      grandchildren survive (#753; ``timeout --kill-after``
                      killed the whole group and that must not be lost).
  7. ``gh_stub``      three seams in one factory (OC_DEPLOY_GH,
                      OC_ISSUE_CREATE_GH, PATH).

Fixture order is load-bearing: each layer may use the ones above it.
"""

from __future__ import annotations

import itertools
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# --- lib/ is a sibling package; this file's dir goes on sys.path (prepend) ----
_PYTEST_DIR = Path(__file__).resolve().parent
if str(_PYTEST_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTEST_DIR))

from lib import cache as _cache  # noqa: E402
from lib import cgroup as _cgroup  # noqa: E402
from lib import harness as H  # noqa: E402
from lib import receipt as _receipt  # noqa: E402

# --- the opt-in content-hash selftest cache (#197) ---------------------------
# ``lib/cache.py`` carries pytest hookimpls (``pytest_addoption`` and friends),
# so it has to be REGISTERED as a plugin. ``-p lib.cache`` cannot work: ``-p``
# is resolved at preparse, before this conftest has put ``lib/`` on sys.path, so
# it dies with "No module named 'lib'". ``pytest_plugins`` here is loaded after
# this module is imported, i.e. after the sys.path insert above.
#
# This is ADDITIVE and INERT: the plugin adds four options and, with none of
# them and no ``OC_PYTEST_CACHE=1``, ``from_config`` returns ``None`` — no read,
# no write, no output. Registration alone changes no existing test's behaviour.
pytest_plugins = ("lib.cache",)

# =============================================================================
# Constants
# =============================================================================
PYTEST_DIR = _PYTEST_DIR
REPO_ROOT = PYTEST_DIR.parents[2]          # <repo>/tools/tests/pytest -> <repo>
TOOLS_DIR = REPO_ROOT / "tools"

# THE LOCK PATH IS NOT DERIVED FROM TMPDIR (#171, trap documented at
# run.sh:545-549). ``scratch`` exports a per-run TMPDIR; a lock path derived
# from it would give every lane its OWN lock file while the lanes still share
# one canonical receipt — both would "acquire" and both would write, silently.
# Read ONCE at import time, i.e. before any fixture touches the environment.
BATTERY_LOCK_PATH = os.environ.get("OC_BATTERY_LOCK") or "/tmp/oc-battery.lock"

HOME = Path(os.environ.get("HOME") or "/root")
# The four live-state leaks env_guard exists to block.
LIVE_PROFILE = HOME / ".opencrabs" / "profiles" / "ops" / "opencrabs-dev"
LIVE_FANOUT_LEDGER = LIVE_PROFILE / "events.jsonl"      # run.sh:3095,3102,3111
LIVE_STATE_DIR = LIVE_PROFILE                           # run.sh:2542
PROD_REPO = Path("/root/opencrabs")                     # run.sh:1536, :1974

# Env vars whose value must never resolve inside live state.
LIVE_ENV_VARS = (
    "OC_FANOUT_LEDGER",
    "OC_LEDGER",
    "OC_DEPLOY_STATE_DIR",
    "OC_DEV_STATE",
    "OC_SESSIONS_DB",
    "OC_TOOLS_LOG",
    "OC_NOTIFY_DB",
)

OWNER_MARKER = ".oc-battery-owner"
# The fixed actor oc-ledger:2771-2800 uses. `stamp` REFUSES an anonymous row
# (#19, oc-ledger:1302), so a fixture without one asserts nothing — it gets rc 2
# and the section reports green.
LEDGER_ACTOR = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_SEQ = itertools.count()


class LiveStateLeak(RuntimeError):
    """A test tried to point a tool at real fleet state."""


class Node:
    """A filesystem path that can also carry FACTS about itself.

    ``pathlib.Path`` refuses attribute assignment (no ``__dict__`` slots), and
    every fixture here needs to hang a little context off its path (``.ledger``,
    ``.calls``, ``.owned``). This wraps a ``Path`` and delegates everything else
    to it, so it is usable anywhere a path is: ``str(n)``, ``os.fspath(n)``,
    ``Path(n)``, ``n / "child"``, ``n.is_dir()``.
    """

    __slots__ = ("_p", "__dict__")

    def __init__(self, path, **facts):
        object.__setattr__(self, "_p", Path(path))
        for k, v in facts.items():
            setattr(self, k, v)

    # -- path protocol -------------------------------------------------------
    def __fspath__(self):
        return str(self._p)

    def __str__(self):
        return str(self._p)

    def __repr__(self):
        facts = ", ".join("%s=%r" % (k, v) for k, v in sorted(self.__dict__.items())
                          if not k.startswith("_"))
        return "Node(%r%s)" % (str(self._p), (", " + facts) if facts else "")

    def __truediv__(self, other):
        return self._p / other

    def __eq__(self, other):
        if isinstance(other, Node):
            return self._p == other._p
        if isinstance(other, (str, Path)):
            return self._p == Path(other)
        return NotImplemented

    def __hash__(self):
        return hash(self._p)

    def __getattr__(self, name):
        # Path methods/attributes (is_dir, parent, name, ...) fall through.
        if name == "_p":
            raise AttributeError(name)
        return getattr(object.__getattribute__(self, "_p"), name)

    @property
    def path(self):
        return self._p


# =============================================================================
# helpers
# =============================================================================
def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _reap_dead_roots(base: Path) -> list[Path]:
    """Remove roots whose ``.oc-battery-owner`` pid is dead.

    Same shape as run.sh's ``_battery_reap_test_tmpdirs``: match the pid
    ENCODED IN THE MARKER, never ``pgrep -f oc-battery`` (a name-wide pattern
    matches unrelated command lines and this run's own children). A live owner
    pid means the root is in use and is left alone.
    """
    removed: list[Path] = []
    if not base.is_dir():
        return removed
    try:
        entries = list(base.glob("oc-battery*"))
    except OSError:
        return removed
    for d in entries:
        if not d.is_dir() or d.is_symlink():
            continue
        try:
            raw = (d / OWNER_MARKER).read_text().strip()
        except OSError:
            continue                       # no marker: not ours to judge
        try:
            pid = int(raw)
        except ValueError:
            continue
        if pid == os.getpid() or _pid_alive(pid):
            continue
        shutil.rmtree(d, ignore_errors=True)
        removed.append(d)
    return removed


def _live_hits(env: dict) -> list[str]:
    """Return ``NAME=value`` for every env var pointing into live state."""
    hits = []
    live_root = str(LIVE_PROFILE)
    prod = str(PROD_REPO)
    for name in LIVE_ENV_VARS:
        val = env.get(name)
        if not val:
            continue
        if (val == prod or val.startswith(prod + "/")
                or val == live_root or val.startswith(live_root + "/")):
            hits.append("%s=%s" % (name, val))
    return hits


def _git(cwd, *args, check=True):
    """git with the identity pinned via -c (see ``git_repo``)."""
    cmd = [
        "git",
        "-c", "user.name=t",
        "-c", "user.email=t@t",
        "-c", "commit.gpgsign=false",
        "-C", str(cwd),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


# =============================================================================
# 1. scratch — one root per worker, ownership marker, controller-side reaper
# =============================================================================
@pytest.fixture(scope="session")
def scratch(request, tmp_path_factory):
    """One scratch root per worker; TMPDIR / OC_BATTERY_TEST_TMPDIR / OC_SNAP_ROOT.

    ``tmp_path_factory`` is already per-worker under xdist (each worker gets its
    own basetemp), so ``mktemp`` here yields a per-worker root with no extra
    bookkeeping — and the same call is correct under ``-n 0``.

    OWNERSHIP, NOT POSSESSION (#171). The root is exported, so every child
    inherits it. If a child treated an INHERITED root as its own, its exit path
    would delete the tree its parent and siblings are still filling — that
    happened, and section 10's own capture file vanished mid-section. The marker
    answers the only question that matters: does this directory already belong
    to a live process? Only the process whose pid is IN the marker removes it.
    """
    config = request.config
    is_controller = not hasattr(config, "workerinput")

    # Only the CONTROLLER sweeps stale roots: N workers each walking /tmp would
    # be N concurrent rm -rf walks of the same directory.
    if is_controller:
        _reap_dead_roots(tmp_path_factory.getbasetemp().parent)
        _reap_dead_roots(Path(os.environ.get("TMPDIR") or "/tmp"))

    root = Path(tmp_path_factory.mktemp("oc-battery"))
    (root / "oc-snap").mkdir(parents=True, exist_ok=True)
    (root / "fanout").mkdir(parents=True, exist_ok=True)

    marker = root / OWNER_MARKER
    try:
        prev = marker.read_text().strip()
    except OSError:
        prev = ""
    try:
        prev_pid = int(prev)
    except ValueError:
        prev_pid = None
    # Claim only an unclaimed / stale / re-entered root; a LIVE foreign owner
    # means we inherited it and must never delete it.
    owned = (prev_pid is None or prev_pid == os.getpid()
             or not _pid_alive(prev_pid))
    if owned:
        marker.write_text("%d\n" % os.getpid())

    mp = pytest.MonkeyPatch()
    request.addfinalizer(mp.undo)
    # TMPDIR redirects every bare `mktemp` in a child; OC_SNAP_ROOT redirects
    # oc_snap_guard's mirrors (tools/lib/oc-snap.sh:31,212 read the same var).
    mp.setenv("TMPDIR", str(root))
    mp.setenv("OC_BATTERY_TEST_TMPDIR", str(root))
    mp.setenv("OC_SNAP_ROOT", str(root / "oc-snap"))
    # Stable and TMPDIR-INDEPENDENT: children must inherit the ONE shared lock.
    mp.setenv("OC_BATTERY_LOCK", BATTERY_LOCK_PATH)

    def _cleanup():
        # Never delete a tree whose marker names another live process.
        if not owned:
            return
        try:
            if marker.read_text().strip() != str(os.getpid()):
                return
        except OSError:
            return
        shutil.rmtree(root, ignore_errors=True)

    request.addfinalizer(_cleanup)
    return Node(root,
                worker=os.environ.get("PYTEST_XDIST_WORKER", "ctrl"),
                owned=owned)


# =============================================================================
# 2. state_dir — OC_DEPLOY_STATE_DIR pointing into scratch
# =============================================================================
@pytest.fixture
def state_dir(scratch, monkeypatch):
    """A fresh ``OC_DEPLOY_STATE_DIR`` per test, inside this worker's scratch.

    Replaces 21 hand-set sites. Function-scoped on purpose: these tools write
    journals, receipts and lock files into the state dir, so a shared one leaks
    verdicts between tests.
    """
    d = scratch.path / "state" / ("t%d-%d" % (next(_SEQ), os.getpid()))
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OC_DEPLOY_STATE_DIR", str(d))
    return d


# =============================================================================
# 3. env_guard — autouse; blocks the four live-state leaks, restores PATH/HOME
# =============================================================================
@pytest.fixture(autouse=True)
def env_guard(scratch, state_dir, monkeypatch):
    """Block the four live-state leaks that exist in run.sh TODAY.

    * ``OC_FANOUT_LEDGER`` defaults to the LIVE fleet ledger
      (``$HOME/.opencrabs/profiles/ops/opencrabs-dev/events.jsonl``,
      run.sh:3095,3102,3111) — every fanout leg in the battery today writes the
      real ledger.
    * ``--repo /root/opencrabs`` reads the production checkout
      (run.sh:1536, :1974). An argument cannot be blocked by an env var, so
      ``run_tool`` refuses it (see ``_assert_no_live_state``).
    * ``OC_DEPLOY_STATE_DIR`` defaults to the real profile (run.sh:2542) — pinned
      by ``state_dir``.
    * ``PATH`` is prepended 4x and never restored (run.sh:3412, 3483, 4136,
      4787), so a later test inherits an earlier test's stub dirs. PATH and HOME
      are snapshotted here and restored after every test.
    """
    base_path = os.environ.get("PATH", "")
    base_home = os.environ.get("HOME", "")

    # Live-state sinks, redirected into this worker's scratch. Both paths must
    # be MATERIALISED, not merely named: a tool that resolves its ledger to
    # ``$OC_DEV_STATE/events.jsonl`` dies rc 3 on a directory with no such file,
    # and a redirect to a path nobody created turns a green leg red for a
    # reason unrelated to the code under test.
    fanout_ledger = scratch.path / "fanout" / "events.jsonl"
    fanout_ledger.parent.mkdir(parents=True, exist_ok=True)
    fanout_ledger.touch()
    monkeypatch.setenv("OC_FANOUT_LEDGER", str(fanout_ledger))
    # Defence in depth: OC_DEV_STATE is the directory the profile-derived
    # defaults fall back to (tools/lib/oc-log.sh:oc_ledger_path).
    dev_state = scratch.path / "dev-state"
    dev_state.mkdir(parents=True, exist_ok=True)
    (dev_state / "events.jsonl").touch()
    monkeypatch.setenv("OC_DEV_STATE", str(dev_state))
    monkeypatch.setenv("OC_BATTERY_LOCK", BATTERY_LOCK_PATH)
    # The battery stays silent in the unified tools log (run.sh:48).
    monkeypatch.setenv("OC_TOOLS_NOLOG", "1")
    # OPENCRABS_SESSION_ID is inherited from the lane that launched pytest and
    # oc-ledger's derive_by reads it when OC_ACTOR is empty (oc-ledger:1060), so
    # leaving it would attribute fixture rows to the REAL lane. Pin both.
    monkeypatch.setenv("OC_ACTOR", LEDGER_ACTOR)
    monkeypatch.setenv("OPENCRABS_SESSION_ID", LEDGER_ACTOR)
    # #753: every selftest is BOUNDED. 1800 s is run.sh's default and cannot red
    # a slow-but-legitimate selftest (longest measured section: 296.5 s).
    monkeypatch.setenv("OC_SELFTEST_TIMEOUT",
                       os.environ.get("OC_SELFTEST_TIMEOUT", "1800"))

    hits = _live_hits(os.environ)
    if hits:                                  # pragma: no cover - misconfiguration
        pytest.fail("env_guard: live state reachable at setup: %s" % ", ".join(hits))

    yield

    # Restore PATH/HOME even when a test mutated os.environ directly (monkeypatch
    # only undoes ITS OWN writes). This is the fix for run.sh's 4x-prepend leak.
    #
    # OC_PYTEST_NO_ENV_RESTORE=1 disables it, and exists ONLY so the restore can
    # be proven to be doing something: a leg that cannot fail is decoration
    # (the battery's NEGATIVE CONTROL idiom). Never set it in a real run.
    if os.environ.get("OC_PYTEST_NO_ENV_RESTORE") == "1":
        return
    if os.environ.get("PATH", "") != base_path:
        os.environ["PATH"] = base_path
    if os.environ.get("HOME", "") != base_home:
        os.environ["HOME"] = base_home


# =============================================================================
# 4. ledger_sandbox — recipe copied VERBATIM from tools/state/oc-ledger:2771-2800
# =============================================================================
# The fixture ledger payload is byte-identical to the heredoc at
# oc-ledger:2786-2789 (two lines; the second starts with a single space).
_LEDGER_JSON = (
    '{"current_skill_version":"0.4.1","meta":{"skill_version":"0.4.1",'
    '"current_skill_version":"0.4.1"},\n'
    ' "updated_at":"2026-01-01T00:00:00Z","workers":[{"uuid":'
    '"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee","role":"tester","topic_id":1,'
    '"feature":"-","confirmed":true,"last_acked":null,"notes":[],"events":[]}],'
    '"events":[]}\n'
)


@pytest.fixture
def ledger_sandbox(scratch, env_guard, monkeypatch):
    """A throwaway ledger + skill dir + repos, exactly as oc-ledger's selftest does.

    Verbatim from ``tools/state/oc-ledger:2771-2800`` — it is already correct and
    the tool's own 418-case selftest proves it, so this is a copy, not a design.

    Two details are load-bearing rather than cosmetic:

    * ``OC_ACTOR`` is a FIXED uuid because ``stamp`` REFUSES an anonymous row
      (#19, oc-ledger:1302) — a fixture without an actor asserts nothing, it
      just gets rc 2 while the section reports green.
    * ``tools/tests/.keep`` keeps ``tools/`` TRACKED (v0.4.157): an entirely
      untracked directory collapses to ``?? tools/`` in porcelain and the
      stray-guard reads that as another lane's dirty work.

    The fast-contention vars make the lock/push/git-tail paths fail in ~1 s
    instead of waiting out their production budgets under a test.
    """
    t = scratch.path / "ledger" / ("L%d" % next(_SEQ))
    state = t / "state"
    skill = t / "skill"
    (skill / "tools" / "tests").mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)

    (state / "workers-ledger.json").write_text(_LEDGER_JSON)
    (skill / "SKILL.md").write_text("name: fixture\nversion: 0.4.2\n---\n# fixture\n")
    (skill / "CHANGELOG.md").write_text("# fixture changelog\n")
    (skill / "tools" / "tests" / ".keep").write_text("")

    for repo in (state, skill):
        _git(repo, "init", "-q")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "base")

    monkeypatch.setenv("OC_LEDGER", str(state / "workers-ledger.json"))
    monkeypatch.setenv("OC_SKILL_DIR", str(skill))
    monkeypatch.setenv("OC_DEPLOY_STATE_DIR", str(state))
    monkeypatch.setenv("OC_ACTOR", LEDGER_ACTOR)
    # Selftest/battery fixtures disable the ship audit chain (oc-ledger:6198).
    monkeypatch.setenv("OC_SHIP_AUDIT_CHAIN", "0")
    # Fast contention: fail in ~1 s, never wait out the production budgets.
    monkeypatch.setenv("OC_LEDGER_LOCK_WAIT", "1")
    monkeypatch.setenv("OC_LEDGER_PUSH_TIMEOUT", "1")
    monkeypatch.setenv("OC_LEDGER_PUSH_MIN", "1")
    monkeypatch.setenv("OC_LEDGER_GIT_TAIL_WAIT", "20")

    return Node(t,
                state=state,
                skill=skill,
                ledger=state / "workers-ledger.json")


# =============================================================================
# 5. git_repo — identity pinned via -c, never the container's global config
# =============================================================================
@pytest.fixture
def git_repo(scratch, monkeypatch):
    """Factory: ``git_repo()`` -> an initialised repo with a base commit.

    Identity is pinned with ``-c user.name/-c user.email`` on init and on every
    commit helper (``_git``), AND written to the repo-local config so a tool
    that commits on its own inherits it. Four repos in the battery today only
    work because this container happens to carry a global git identity — on a
    box without one they fail with "Author identity unknown", which reads as a
    broken tool rather than as a fixture defect.
    """
    def _make(name=None, bare=False, branch="main", files=None):
        path = scratch.path / "git" / (name or ("r%d" % next(_SEQ)))
        path.mkdir(parents=True, exist_ok=True)
        init = ["init", "-q", "-b", branch]
        if bare:
            init.append("--bare")
        _git(path, *init)
        _git(path, "config", "user.email", "t@t")
        _git(path, "config", "user.name", "t")
        _git(path, "config", "commit.gpgsign", "false")
        if not bare:
            for fn, body in (files or {"base.txt": "base\n"}).items():
                (path / fn).write_text(body)
            _git(path, "add", "-A")
            _git(path, "commit", "-q", "-m", "base")
        return Node(path, git=lambda *a, **k: _git(path, *a, **k))

    return _make


# =============================================================================
# 6. run_tool / run_selftest — process-GROUP kill, timeout REQUIRED
# =============================================================================
class Result:
    """Small result object: ``.rc .out .err .duration_ms`` (+ ``.timed_out``)."""

    __slots__ = ("rc", "out", "err", "duration_ms", "timed_out", "cmd",
                 "cached")

    def __init__(self, rc, out, err, duration_ms, timed_out, cmd,
                 cached=False):
        self.rc = rc
        self.out = out
        self.err = err
        self.duration_ms = duration_ms
        self.timed_out = timed_out
        self.cmd = cmd
        # True only when a cache HIT produced this Result, i.e. no subprocess
        # ran. Always False for a real run, so `assert not res.cached` is the
        # "this leg actually executed" assertion the cache tests use.
        self.cached = cached

    @property
    def combined(self):
        return self.out + self.err

    def __repr__(self):
        return "<Result rc=%s %.1fms%s>" % (
            self.rc, self.duration_ms, " TIMEOUT" if self.timed_out else "")


def _assert_no_live_state(cmd: list[str], env: dict, allow_live_state: bool):
    """Refuse a launch that would reach real fleet state.

    ``--repo /root/opencrabs`` is the leak an env var cannot block (run.sh:1536,
    :1974): the argument is spelled at the call site, so the check has to sit on
    the launch path. Everything else is caught by value, because the live
    profile path is what the tools fall back to when nothing is exported.
    """
    if allow_live_state:
        return
    prod = str(PROD_REPO)
    for arg in cmd:
        s = str(arg)
        if s == prod or s.startswith(prod + "/"):
            raise LiveStateLeak(
                "run_tool: argument reaches the PRODUCTION checkout (%s). Pass a "
                "fixture repo, or pass allow_live_state=True if the leg genuinely "
                "means to read the real store." % s)
    hits = _live_hits(env)
    if hits:
        raise LiveStateLeak(
            "run_tool: live fleet state reachable: %s. env_guard should have "
            "redirected these; if a test set them on purpose, pass "
            "allow_live_state=True." % ", ".join(hits))


def _run(cmd, *, timeout, cwd=None, env=None, allow_live_state=False,
         stdin_data=None):
    """Run ``cmd`` with a HARD bound, killing the whole PROCESS GROUP on expiry.

    ``subprocess.run(timeout=)`` signals only the direct child, so a selftest's
    grandchildren survive their parent and keep burning the box: a detached
    ``oc-harvest-sweep --selftest`` spins for hours at a third of a core each
    with nothing to reap it. ``timeout --kill-after`` does kill the group;
    ``start_new_session=True`` + ``os.killpg`` reproduces that.
    ``timeout`` has NO default on purpose: a bound that can be omitted is a
    bound that will be omitted, and the #753 hang is then unreproducible.
    """
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    cmd = [str(c) for c in cmd]

    full_env = dict(os.environ)
    if env:
        full_env.update({k: str(v) for k, v in env.items()})
    _assert_no_live_state(cmd, full_env, allow_live_state)

    t0 = time.monotonic()
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
        cwd=str(cwd) if cwd else None,
        env=full_env,
        start_new_session=True,     # own process group => killpg reaches all of it
    )
    timed_out = False
    try:
        out, err = p.communicate(
            input=stdin_data.encode() if isinstance(stdin_data, str) else stdin_data,
            timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        # SIGKILL the GROUP. SIGTERM alone is not enough: the #753 class is a
        # selftest that ignores TERM, which is exactly why run.sh used
        # --kill-after.
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            p.kill()
        except ProcessLookupError:
            pass
        # The drain must ITSELF be bounded. Measured while writing this: after a
        # direct-child-only kill, a surviving grandchild holds the pipe write
        # end and `communicate()` never returns — the caller wedges with the
        # bound already fired, which is #753 wearing a different hat. killpg
        # normally makes this instant; the timeout is for a descendant that
        # escaped the group (setsid) or a pipe held by something else.
        try:
            out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                p.kill()
            except ProcessLookupError:
                pass
            try:
                out, err = p.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                out, err = b"", b"[oc-pytest] output pipe never closed after the kill"
    duration_ms = (time.monotonic() - t0) * 1000.0
    # 124 is `timeout(1)`'s "the bound fired" code; run.sh reads it as
    # "HUNG -- killed at the Ns bound", not as a tool verdict.
    rc = 124 if timed_out else p.returncode
    return Result(
        rc=rc,
        out=(out or b"").decode("utf-8", "replace"),
        err=(err or b"").decode("utf-8", "replace"),
        duration_ms=duration_ms,
        timed_out=timed_out,
        cmd=cmd,
    )


@pytest.fixture(scope="session")
def tools_dir():
    """The ``tools/`` dir of THIS checkout (never the production one)."""
    return TOOLS_DIR


def tool_path(name: str) -> Path:
    """Resolve an ``oc-*`` tool by NAME, mirroring run.sh:tool_path.

    tools/ is grouped by KIND, so a tool can be moved without touching every
    leg; the same exclusion list (lib/tests/archive/docs/instruments) applies.
    """
    direct = TOOLS_DIR / name
    if direct.is_file() and os.access(direct, os.X_OK):
        return direct
    skip = {"lib", "tests", "archive", "docs", "instruments"}
    for sub in sorted(TOOLS_DIR.iterdir()):
        if not sub.is_dir() or sub.name in skip:
            continue
        cand = sub / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand
    raise FileNotFoundError("tool not found: %s (under %s)" % (name, TOOLS_DIR))


@pytest.fixture
def run_tool(env_guard):
    """Callable: ``run_tool(cmd, *, timeout=...)`` -> ``Result``.

    ``timeout`` is a REQUIRED keyword argument. The bound is the point: the
    battery's worst defect class is a leg that never returns (#753), and a
    default would let the next ported section reintroduce it silently.
    """
    def _call(cmd, *, timeout, cwd=None, env=None, allow_live_state=False,
              stdin_data=None):
        return _run(cmd, timeout=timeout, cwd=cwd, env=env,
                    allow_live_state=allow_live_state, stdin_data=stdin_data)
    return _call


@pytest.fixture
def run_selftest(run_tool, state_dir):
    """Callable: ``run_selftest("oc-ledger", timeout=900)`` -> ``Result``.

    Mirrors run.sh:run_selftest: a per-call throwaway ``OC_DEPLOY_STATE_DIR``
    (the /tmp-leak fix, M2-22), the ``OC_SELFTEST_TIMEOUT`` default, and the
    group kill on expiry.
    """
    def _call(tool, *, timeout=None, extra_args=(), env=None,
              allow_live_state=False):
        path = tool_path(tool)
        bound = timeout
        if bound is None:
            bound = float(os.environ.get("OC_SELFTEST_TIMEOUT", "1800"))
        sd = state_dir / ("st-" + tool)
        sd.mkdir(parents=True, exist_ok=True)
        call_env = {"OC_DEPLOY_STATE_DIR": str(sd)}
        if env:
            call_env.update(env)
        return run_tool([str(path), "--selftest", *extra_args],
                        timeout=bound, env=call_env,
                        allow_live_state=allow_live_state)
    return _call


# =============================================================================
# 7. gh_stub — one factory, three seams
# =============================================================================
@pytest.fixture
def gh_stub(scratch, env_guard, monkeypatch):
    """Factory: ``gh_stub()`` -> stub wired into all three seams at once.

    The battery builds a bespoke stub dir per section (run.sh:4099-4110 for
    oc-issue-create, run.sh:2347-2491 for the deploy/ship legs). The three seams
    are ``OC_DEPLOY_GH`` (tools/lib/oc-deploy-lib.sh:91), ``OC_ISSUE_CREATE_GH``
    (tools/issue/oc-issue-create:73) and ``PATH`` (for tools that call a bare
    ``gh``).

    Every invocation is logged as one JSON line, so a leg can assert WHAT was
    asked as well as what came back.
    """
    def _make(rules=None, name=None, default_stdout="", default_rc=0):
        """``rules``: ``[(substring, stdout, rc), ...]`` — first match wins."""
        d = scratch.path / "gh" / ("g%d" % next(_SEQ))
        bindir = d / "bin"
        bindir.mkdir(parents=True, exist_ok=True)
        log = d / "calls.jsonl"
        rules_file = d / "rules.json"
        rules_file.write_text(json.dumps(
            [{"match": m, "stdout": o, "rc": r} for m, o, r in (rules or [])]))
        stub = bindir / (name or "gh")
        stub.write_text(
            "#!/usr/bin/env python3\n"
            "# generated by tools/tests/pytest/conftest.py::gh_stub\n"
            "import json, os, sys\n"
            "log = os.environ.get('GH_STUB_LOG') or %r\n"
            "argv = sys.argv[1:]\n"
            "with open(log, 'a', encoding='utf-8') as fh:\n"
            "    fh.write(json.dumps(argv) + '\\n')\n"
            "joined = ' '.join(argv)\n"
            "for rule in json.load(open(%r, encoding='utf-8')):\n"
            "    if rule['match'] in joined:\n"
            "        sys.stdout.write(rule['stdout'])\n"
            "        raise SystemExit(rule['rc'])\n"
            "sys.stdout.write(%r)\n"
            "raise SystemExit(%r)\n"
            % (str(log), str(rules_file), default_stdout, int(default_rc))
        )
        stub.chmod(0o755)

        monkeypatch.setenv("OC_DEPLOY_GH", str(stub))
        monkeypatch.setenv("OC_ISSUE_CREATE_GH", str(stub))
        monkeypatch.setenv("GH_STUB_LOG", str(log))
        monkeypatch.setenv("PATH",
                           str(bindir) + os.pathsep + os.environ.get("PATH", ""))

        def calls():
            try:
                lines = log.read_text().splitlines()
            except OSError:
                return []
            return [json.loads(x) for x in lines if x.strip()]

        def set_rules(new_rules):
            rules_file.write_text(json.dumps(
                [{"match": m, "stdout": o, "rc": r} for m, o, r in new_rules]))

        return Node(stub, bindir=bindir, log=log,
                    calls=calls, set_rules=set_rules)

    return _make


# =============================================================================
# battery lock — the ONE shared path, TMPDIR-independent
# =============================================================================
@pytest.fixture(scope="session")
def battery_lock(request):
    """Hold the battery's single-flight flock for the whole session, on demand.

    The lock path is the module constant, NOT anything derived from ``scratch``:
    a per-run TMPDIR that moved the lock would give every lane its own lock
    while they share one receipt (the trap at run.sh:545-549). Sections that
    write the canonical receipt must be ``@pytest.mark.serial`` and take this.
    """
    import fcntl

    wait = int(os.environ.get("OC_BATTERY_LOCK_WAIT", "900"))
    fh = open(BATTERY_LOCK_PATH, "a+")
    deadline = time.monotonic() + wait
    while True:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                fh.close()
                pytest.skip("battery lock %s not released within %ss"
                            % (BATTERY_LOCK_PATH, wait))
            time.sleep(0.2)

    def _release():
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()

    request.addfinalizer(_release)
    return BATTERY_LOCK_PATH

# =============================================================================
# serial witness — makes "these legs never overlap" an OBSERVATION
# =============================================================================
# ``@pytest.mark.serial`` + ``@pytest.mark.xdist_group(g)`` is a claim about the
# SCHEDULER: xdist promises to keep same-group legs apart. A claim about the
# scheduler is not evidence about the legs — a mistyped group name, a worker
# restart or a ``-p no:xdist`` run all keep the marks and drop the guarantee,
# and every assertion in those legs then rests on a premise nobody tested.
#
# ``H.SerialWitness`` takes an exclusive flock for the body of a leg. Two
# same-group legs overlapping raise ``Overlap`` from the second one, so the pin
# FAILS rather than interleaving silently; each hold is logged, so the whole
# session can be censused after the fact (``witness_session_report``).
@pytest.fixture(scope="session")
def serial_witness_dir(tmp_path_factory):
    """ONE witness dir for the session — workers must agree on the path.

    Deliberately NOT ``scratch`` (per-worker) and not ``tmp_path`` (per-test):
    an overlap between two workers is only observable if both open the same
    inode, which is the same reason the battery lock is TMPDIR-independent
    (run.sh:545-549, and the trap at run.sh:674-677).

    Anchored on the RUN root, never on ``basetemp``'s parent — those are two
    different directories and only one of them is unique to this run:

      * ``-n 0``          basetemp is ``/tmp/pytest-of-root/pytest-NNNN``, so
        its PARENT is ``/tmp/pytest-of-root``: shared with every other pytest
        run as this user, peer lanes included. Sweeping stale logs there would
        delete a live lane's evidence.
      * ``-n N`` (worker) basetemp is ``<run>/popen-gwK``, so the run root is
        its parent — shared with the sibling workers, which is the point.
    """
    base = Path(tmp_path_factory.getbasetemp())
    run_root = base.parent if base.name.startswith("popen-gw") else base
    d = run_root / "oc-witness"
    d.mkdir(parents=True, exist_ok=True)
    # A stale interval log from an earlier session would be censused as THIS
    # session's evidence — the from-zero defect, one surface over. Safe to
    # sweep only because the directory is per-run (see above).
    for f in d.glob("intervals.*"):
        f.unlink(missing_ok=True)
    return d

@pytest.fixture(autouse=True)
def _serial_witness(request, serial_witness_dir):
    """Observe the claim a group marker makes, for the test's OWN group.

    Reads the marker off the test node rather than taking a group from the
    module: ``harness/test_harness_pool_mech.py`` carries legs in TWO groups
    (``battery-pool`` and ``battery-nested``) which are allowed to overlap each
    other by design, so a module-wide hold would report a false overlap on a
    correct run — which is why this is per-test.

    A test with no group marker is not witnessed at all: there is no claim to
    observe, and holding one would fence it against legs it is meant to run
    beside.
    """
    marker = request.node.get_closest_marker("xdist_group")
    if marker is None or not marker.args:
        yield
        return
    with H.SerialWitness(serial_witness_dir, marker.args[0], hold_s=0.0):
        yield

def witness_session_report(directory, group: str) -> dict:
    """The receipt-side half: what the witness OBSERVED for ``group``.

    ``legs``      completed holds (a killed leg logs ``enter`` and no ``exit``)
    ``peak``      most simultaneous holders — 1 means the pin held
    ``overlaps``  every pair that ran at once — [] means the pin held
    ``unclosed``  holds with no ``exit``, i.e. legs a kill cut short

    An EMPTY ``legs`` is not a pass: it means no leg of that group ran, so the
    census proves nothing. Callers assert the count they expect.
    """
    from lib import harness as _H

    legs = _H.SerialWitness.spans(directory, group)
    log = Path(directory) / ("intervals.%s" % group)
    enters = exits = 0
    if log.is_file():
        for line in log.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] in ("enter", "exit"):
                enters += parts[0] == "enter"
                exits += parts[0] == "exit"
    return {
        "legs": len(legs),
        "peak": _H.SerialWitness.peak(directory, group),
        "overlaps": _H.SerialWitness.overlaps(directory, group),
        "unclosed": max(0, enters - exits),
    }


# =============================================================================
# 8. cached_selftest — the OPT-IN content-hash cache (#197)
# =============================================================================
@pytest.fixture
def cached_selftest(request, run_selftest):
    """Callable: ``cached_selftest("oc-ledger", timeout=900)`` -> ``Result``.

    A thin wrapper over ``run_selftest`` that, WHEN the cache is enabled, skips
    the subprocess on a byte-identical PASS. With no ``--oc-cache`` and no
    ``OC_PYTEST_CACHE=1`` the cache object is ``None`` and this is a pure
    passthrough — the returned ``Result`` is the one ``run_selftest`` produced,
    with nothing added, so today's behaviour is unchanged (rule 1).

    A cache HIT returns a ``Result`` with ``rc=0`` and the STORED duration, and
    ``.cached`` set, so a caller can assert "this did not run" without a clock.
    """
    def _call(tool, *, timeout=None, extra_args=(), env=None,
              allow_live_state=False, emit=None):
        # Read the cache at CALL time, not at setup time: a test that installs
        # its own cache on the config (the cache module's own legs do) must see
        # its cache honoured, and the fixture is set up before that install.
        cache = getattr(request.config, "_oc_cache", None)

        # Rule 5: a HIT is never invisible. When the caller passes no emitter
        # and the cache is on, the default emitter writes the hit line to
        # stderr — but ONLY when the run is verbose, so a normal (non -v) run's
        # output stays byte-identical to today's (rule 1). Without this the
        # fixture's own hits would be silent, which is exactly the failure mode
        # the requirement exists to prevent.
        if emit is None and cache is not None and _cache.verbose(request.config):
            emit = lambda line: sys.stderr.write(line + "\n")  # noqa: E731

        def _runner():
            return run_selftest(tool, timeout=timeout, extra_args=extra_args,
                                env=env, allow_live_state=allow_live_state)

        outcome = _cache.run_cached(
            cache, tool=tool, tool_path=tool_path(tool), runner=_runner,
            args=extra_args, emit=emit)

        return Result(rc=outcome.rc, out=getattr(outcome, "out", ""),
                      err=getattr(outcome, "err", ""),
                      duration_ms=outcome.duration_ms, timed_out=False,
                      cmd=[str(tool_path(tool)), "--selftest", *extra_args],
                      cached=outcome.cached)

    return _call

# =============================================================================
# hooks — pytest only sees hooks defined in a conftest or a plugin, so the
# implementations live in lib/ and are DELEGATED here.
# =============================================================================
def pytest_configure(config):
    # Which xdist_group values this run actually carries. Collected from the
    # NODES, never from a list kept by hand: a hardcoded tuple in the census
    # module silently stops covering a group the moment someone adds one, and a
    # census that skips a group reports clean on it forever. (Measured: the
    # hand-kept tuple named 4 groups while the suite carried 7 — battery-nested,
    # battery-scratch and path-restore were unwitnessed and uncensused.)
    config._oc_witness_groups = set()


def pytest_collection_modifyitems(session, config, items):
    groups = getattr(config, "_oc_witness_groups", None)
    if groups is None:
        return
    offenders = []
    for item in items:
        marked = [str(m.args[0]) for m in item.iter_markers("xdist_group") if m.args]
        for g in marked:
            groups.add(g)
        if item.get_closest_marker("serial") and not marked:
            offenders.append(item.nodeid)
    config._oc_witness_groups = groups
    config._oc_serial_without_group = offenders

    _receipt.pytest_configure(config)


def pytest_cmdline_main(config):
    # The EARLIEST hook: by fixture time xdist workers already exist, so the
    # cgroup re-exec has to happen here or not at all.
    return _cgroup.pytest_cmdline_main(config)


def pytest_runtest_logreport(report):
    _receipt.pytest_runtest_logreport(report)


def pytest_sessionfinish(session, exitstatus):
    # Order matters: cgroup records its receipt overrides, then the receipt is
    # written once (controller only, enforced inside each).
    _cgroup.pytest_sessionfinish(session, exitstatus)
    _receipt.pytest_sessionfinish(session, exitstatus)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    path = _receipt.receipt_path_for(config)
    run = getattr(config, "_oc_run", None)
    if run is None or hasattr(config, "workerinput"):
        return
    if getattr(config.option, "collectonly", False):
        terminalreporter.write_line("pytest-receipt: collect-only run, no receipt written")
        return
    terminalreporter.write_line(
        "pytest-receipt: %s (pass=%d fail=%d wall=%dms)"
        % (path, run.n_pass, run.n_fail, run.wall_ms()))
