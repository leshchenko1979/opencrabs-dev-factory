# tools/tests/pytest — the pytest half of the battery

**This is the gate.** `python3 -m pytest` here is the whole battery — the shell
harness was retired on 2026-11-28 and `tools/tests/run.sh` no longer exists.

---

## Run it

```sh
# serial — the default, and the reference mode
python3 -m pytest tools/tests/pytest/

# one worker per CPU (caps scale, see below)
python3 -m pytest tools/tests/pytest/ -n auto

# explicit serial. THE SAME TESTS MUST PASS, with zero changes.
python3 -m pytest tools/tests/pytest/ -n 0

# by name
python3 -m pytest tools/tests/pytest/ -k ledger

# by marker
python3 -m pytest tools/tests/pytest/ -m "not slow"
python3 -m pytest tools/tests/pytest/ -m serial

# one subject folder (harness/ tools/ infra/ e2e/ — see the layout below)
python3 -m pytest tools/tests/pytest/harness/

# collect only (proves the suite imports; writes no receipt)
python3 -m pytest tools/tests/pytest/ --collect-only -q
```

---

## Layout — one folder per subject

49 modules in one flat directory meant filtering by subject was `-k` guessing
against 49 names. They are filed by the subject their own docstring states:

| folder | what lives there |
|---|---|
| `harness/` | the pytest harness itself — `conftest` fixtures driven against real tools (`test_fixtures.py`), the battery lock/scratch/cgroup/sigkill/pool harness legs, the serial-witness census, and the receipt (`test_receipt*.py`) |
| `tools/` | legs that drive a SHIPPED `oc-*` tool: attrib, branch-sweep, deploy stage (fast legs), fanout, fmt, gate, health, issue-dispatch, ledger, notify-fanout, receipts, quoting guard, rc contract/help, review-persist, seal, shadow-rotate, smoke-evidence, tool contracts, the `run_selftest` blanket, usage rc, vendor-drift, verify trio |
| `infra/` | `lib/*.sh` / `lib/*.py` units — claims predicate, embed, flood guard, log lib, notify lib, root resolver, snap, unified-log wire |
| `e2e/` | legs that build a real tree and run a real subprocess end-to-end: `test_e2e_deploy_stage.py` (slow) and the entry-preamble fixpoint drive |
| `.` (root) | the two that are about the SUITE rather than a subject: `conftest.py` and `test_foundation.py` (fixture foundations) |

Basenames stay unique across the suite, so `--import-mode` needs no change and
`-k`/`-m` selection is unaffected.

`-n 0` is a **supported mode, not an accident**. Every fixture is
worker-agnostic — `tmp_path_factory` is per-worker under xdist and per-session
without it — so the serial fallback needs zero test changes. That is the
acceptance bar for the whole migration: *if a test needs `-n 0` to pass, the
fixture is wrong.*

---

## Markers

| marker | meaning | in the gate? |
|---|---|---|
| `serial` | mutually-exclusive legs: flock, live ports, the canonical receipt | yes |
| `slow` | more than a few seconds | on request |

Markers are `strict_markers = true`, so an unregistered marker is an error
rather than a silent no-op that makes `-m serial` look like it selected nothing.

There is deliberately **no `network` and no `live_state` marker** (deleted in
factory #203). Both were registered and selected nothing — zero uses, and no leg
qualifies: every `gh` call goes through `gh_stub`, `_assert_no_live_state`
refuses a production path at launch, `allow_live_state=True` appears in zero
tests, and nothing runs `curl`/`urllib`/`requests`/`socket`. A registered marker
that selects nothing is the same lie as `-m serial` matching nothing, one layer
up.

### `serial` needs `xdist_group`

```python
@pytest.mark.serial
@pytest.mark.xdist_group("battery-lock")
def test_canonical_receipt(...): ...
```

`serial` alone is a *claim* ("this leg must not overlap"). Under `-n N` the
mechanism that makes the claim true is `xdist_group`: xdist pins every test in a
group to the SAME worker, in order. Without it a `serial` test is scattered
across workers and overlaps freely. Under `-n 0` the group is inert, which is
why the serial fallback needs no changes.

---

## Where the receipt goes

```
tools/tests/battery-last.json
```

Written **controller-only** (`if not hasattr(config, "workerinput")`), carrying
the **18 fields** the shell harness used to emit. The path is not a preference:
`oc-ledger sync` reads that exact file and dies rc 5 on a missing, stale (>6h) or
RED verdict, so it is the fleet's version-bump gate. Override with
`OC_PYTEST_RECEIPT` for a scratch run — and do that for any scoped run, because a
filtered run otherwise stamps a PASS backed by the few tests it selected
(factory #214). A `--collect-only` run writes nothing: it is not a verdict.

`timing` is `{max_concurrency, section_count, sum_ms, slowest}` where each
`slowest` entry is `{n, title, ms, start_ms, end_ms}` and holds at most 10 rows.
`max_concurrency` is the peak overlap of the test intervals — the direct answer
to "did the pool ever actually hold N tests?", which a duration sum cannot
answer.

Fail rows go to **per-worker files** (`$OC_PYTEST_RUN_DIR/fails.<worker>.jsonl`)
and are concatenated by the controller, so a green worker can never delete a
sibling's evidence. A single shared fail log cannot do this: one green worker
would truncate the file its siblings are still writing to.

---

## Fixtures (`conftest.py`)

In dependency order — each may use the ones above it.

| fixture | scope | what it does / what it replaces |
|---|---|---|
| `scratch` | session | One root per worker via `tmp_path_factory.mktemp("oc-battery")`; sets `TMPDIR`, `OC_BATTERY_TEST_TMPDIR`, `OC_SNAP_ROOT`; writes a `.oc-battery-owner` pid marker. Replaces 59 `mktemp -d` sites. **Only the owner removes it** — a child's exit must never delete the parent's tree (#171). The controller reaps roots whose marker pid is dead. **The lock path is NOT derived from TMPDIR**: a per-run TMPDIR that moved the lock would give every lane its own lock while they share one receipt. |
| `state_dir` | function | A fresh `OC_DEPLOY_STATE_DIR` inside `scratch`, so no leg touches the real profile. |
| `env_guard` | function, **autouse** | Blocks the four live-state leaks (below) and restores `PATH`/`HOME` after every test. |
| `ledger_sandbox` | function | The recipe from `tools/state/oc-ledger:2771-2800`, verbatim: throwaway ledger + skill dir + two git repos + `.keep`, `OC_LEDGER`/`OC_SKILL_DIR`/`OC_ACTOR` (a fixed uuid — `stamp` refuses anonymous rows), `OC_SHIP_AUDIT_CHAIN=0`, and the fast-contention vars `OC_LEDGER_LOCK_WAIT=1`, `OC_LEDGER_PUSH_TIMEOUT=1`, `OC_LEDGER_PUSH_MIN=1`, `OC_LEDGER_GIT_TAIL_WAIT=20`. |
| `git_repo` | function | Factory. `git init` with identity pinned via `-c user.name/-c user.email` **and** written repo-local — 4 repos in the battery today only work by accident of the container's global git config. |
| `run_tool` | function | `run_tool(cmd, *, timeout=...)` → `Result(.rc, .out, .err, .duration_ms, .timed_out, .cmd)`. **`timeout` is required** — no default. |
| `run_selftest` | function | `run_selftest("oc-x", timeout=...)` → same `Result`. Per-call throwaway state dir (M2-22); falls back to `OC_SELFTEST_TIMEOUT` (1800 s). |
| `gh_stub` | function | Factory. One stub wired into **three seams** at once: `OC_DEPLOY_GH`, `OC_ISSUE_CREATE_GH`, and a `PATH` dir. Logs every call as JSON. |
| `battery_lock` | session | Holds the single-flight flock at `/tmp/oc-battery.lock` (override `OC_BATTERY_LOCK`), wait budget `OC_BATTERY_LOCK_WAIT` (default 900 s). |
| `tools_dir` | session | The `tools/` dir of **this** checkout. |

### What `env_guard` blocks

Four ways a leg could reach live state, and what stops each:

1. **`OC_FANOUT_LEDGER`** defaults to the live fleet ledger
   (`$HOME/.opencrabs/profiles/ops/opencrabs-dev/events.jsonl`) — redirected
   into the scratch root, so no fanout leg writes it.
2. **`--repo /root/opencrabs`** reads the production checkout. An argument
   cannot be blocked by an env var, so `run_tool` refuses it at launch
   (`LiveStateLeak`).
3. **`OC_DEPLOY_STATE_DIR`** defaults to the real profile — pinned by
   `state_dir`.
4. **`PATH` accumulation**, so a later test inherits an earlier one's stub
   dirs. `PATH` and `HOME` are snapshotted and restored after every test.

It also sets `OC_TOOLS_NOLOG=1`, `OC_SELFTEST_TIMEOUT=1800`, and pins
`OC_ACTOR` / `OPENCRABS_SESSION_ID` to the fixture actor (the latter is
inherited from the launching lane and `oc-ledger`'s `derive_by` prefers it).

`OC_PYTEST_NO_ENV_RESTORE=1` disables the PATH/HOME restore. It exists **only**
so the restore can be proven to be doing something — a leg that cannot fail is
decoration. Never set it in a real run.

---

## Why `run_tool` kills a process GROUP

`subprocess.run(timeout=)` signals only the direct child. A selftest's
grandchildren survive their parent and keep burning the box — measured
2026-10-01: six detached `oc-harvest-sweep --selftest` runs spun ~5 h at 37-39 %
CPU each and nothing reaped them. `timeout --kill-after` *did* kill the group,
and `run_tool` reproduces that with `start_new_session=True` +
`os.killpg(..., SIGKILL)`, then reports `rc=124` — the code the battery
reads as "HUNG -- killed at the Ns bound".

The post-kill drain is bounded too. Measured while writing this: after a
direct-child-only kill, a surviving grandchild holds the pipe write end and
`communicate()` never returns — the caller wedges *with the bound already
fired*, which is #753 wearing a different hat.

---

## cgroup isolation (`lib/cgroup.py`)

`pytest_cmdline_main` — the **earliest** hook — re-execs the run into a
transient `systemd-run` scope before any xdist worker is forked. A fixture is
too late: workers already exist by then.

- **Caps scale with `-n N`.** `TasksMax`, `CPUQuota` and `MemoryMax` are
  tree-wide, so a fixed `TasksMax=128` under `-n 8` reproduces the #74 `EAGAIN`
  rows as test failures instead of a stated cap. Memory is ceilinged at 75 % of
  physical RAM — a tree-wide cap larger than the box protects nothing — and the
  run says so when the ceiling fires.
- **At `-n 1` the caps are the full per-worker allowance**, so a serial pytest
  run and the shell harness are compared on the same budget.
- **Probe, then exec, one array.** A bare `exec` cannot fail open: it never
  returns, so a refused re-exec would replace the run with systemd-run's exit
  code and a harness error would be read as RED. One throwaway scope settles the
  caps first, and the probe and the exec share `caps_for()` so they cannot
  diverge.
- **Fails OPEN with a warning.** No `systemd-run`, no user manager, an
  unreadable cgroup or a refused scope all leave the run where it was and print
  one WARNING. Opt out with `OC_PYTEST_NO_CGROUP=1` (or `OC_BATTERY_NO_CGROUP`).
- The receipt records `cgroup` and `cgroup_isolated` from the session-finish
  hook, and `test_cgroup.py::test_run_is_not_in_a_service_leaf` asserts the run
  is not inside a `*.service` leaf (the daemon's unit, whose `OOMPolicy=kill`
  takes the daemon down with one over-limit allocation).

---

## Adding a ported section

```python
import conftest as cf

@pytest.mark.serial
@pytest.mark.xdist_group("battery-lock")
def test_oc_ledger_stamp(ledger_sandbox, run_tool):
    res = run_tool([cf.tool_path("oc-ledger"), "stamp", "note", "x"], timeout=120)
    assert res.rc == 0, res.combined
```

Rules that are not negotiable:

- **Every subprocess goes through `run_tool`/`run_selftest`.** No bare
  `subprocess.run` — the bound and the group kill are the point.
- **Never hardcode `/root/opencrabs` or a `$HOME/.opencrabs/...` path.** Use
  `scratch`, `state_dir`, `ledger_sandbox`, `git_repo`, `gh_stub`.
- **`timeout` is a number, not a guess.** 1800 s for a real selftest; tens of
  seconds for a fixture-level tool call.
- **A leg that writes the canonical receipt must be `serial`.** The lock is the
  only thing preventing two lanes from interleaving writes.
- **A dedicated module never repeats the selftest blanket.** `<tool> --selftest`
  exits 0 is owned by `tools/test_tool_wrappers.py`, once per tool, slow-marked.
  A section module exists to assert what the blanket CANNOT see about its
  subject — argv/rc vocabulary, a state-dir containment, a counter read as a
  field. Three modules used to drive a selftest a second time (`test_gate.py`
  ~118 s, `test_notify_fanout.py` ~266 s, `test_verify_trio.py` ~12 s × 3) and
  the duplicate legs were deleted in factory #203: the second site bought one
  extra `rc == 0` for minutes of wall.
