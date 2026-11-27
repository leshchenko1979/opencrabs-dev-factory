# tools/tests/pytest — the pytest half of the battery

`tools/tests/run.sh` is still **the gate**. This tree is the additive migration
target: nothing here changes what `run.sh` does, and the shell harness is not
touched until a pytest run reproduces its verdict. Plan:
`~/.opencrabs/profiles/ops/research/pytest-migration-plan.md`.

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
python3 -m pytest tools/tests/pytest/ -m "not network and not live_state"

# collect only (proves the suite imports; writes no receipt)
python3 -m pytest tools/tests/pytest/ --collect-only -q
```

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
| `network` | reaches the network (github, the A2A endpoint, registries) | no |
| `live_state` | reads or writes a REAL store (fleet ledger, `workers.json`, the production checkout) | **never** |
| `slow` | more than a few seconds | on request |

Markers are `strict_markers = true`, so an unregistered marker is an error
rather than a silent no-op that makes `-m serial` look like it selected nothing.

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
tools/tests/pytest-receipt.json
```

Written **controller-only** (`if not hasattr(config, "workerinput")`), with the
same **18 fields** as `run.sh:emit_summary` (`tools/tests/run.sh:1001`) — the
comment at `:5545` saying 17 is stale. Override the path with
`OC_PYTEST_RECEIPT`. A `--collect-only` run writes nothing: it is not a verdict.

`timing` is `{max_concurrency, section_count, sum_ms, slowest}` where each
`slowest` entry is `{n, title, ms, start_ms, end_ms}` and holds at most 10 rows.
`max_concurrency` is the peak overlap of the test intervals — the direct answer
to "did the pool ever actually hold N tests?", which a duration sum cannot
answer.

Fail rows go to **per-worker files** (`$OC_PYTEST_RUN_DIR/fails.<worker>.jsonl`)
and are concatenated by the controller, so a green worker can never delete a
sibling's evidence. `run.sh`'s single `$FAIL_LOG` cannot do this: one green
worker would remove it.

---

## Fixtures (`conftest.py`)

In dependency order — each may use the ones above it.

| fixture | scope | what it does / what it replaces |
|---|---|---|
| `scratch` | session | One root per worker via `tmp_path_factory.mktemp("oc-battery")`; sets `TMPDIR`, `OC_BATTERY_TEST_TMPDIR`, `OC_SNAP_ROOT`; writes a `.oc-battery-owner` pid marker. Replaces 59 `mktemp -d` sites. **Only the owner removes it** — a child's exit must never delete the parent's tree (`run.sh:487-509`, #171). The controller reaps roots whose marker pid is dead. **The lock path is NOT derived from TMPDIR** (`run.sh:545-549`): a per-run TMPDIR that moved the lock would give every lane its own lock while they share one receipt. |
| `state_dir` | function | A fresh `OC_DEPLOY_STATE_DIR` inside `scratch`. Replaces 21 hand-set sites; the tool default at `run.sh:2542` is the real profile. |
| `env_guard` | function, **autouse** | Blocks the four live-state leaks (below) and restores `PATH`/`HOME` after every test. |
| `ledger_sandbox` | function | The recipe from `tools/state/oc-ledger:2771-2800`, verbatim: throwaway ledger + skill dir + two git repos + `.keep`, `OC_LEDGER`/`OC_SKILL_DIR`/`OC_ACTOR` (a fixed uuid — `stamp` refuses anonymous rows), `OC_SHIP_AUDIT_CHAIN=0`, and the fast-contention vars `OC_LEDGER_LOCK_WAIT=1`, `OC_LEDGER_PUSH_TIMEOUT=1`, `OC_LEDGER_PUSH_MIN=1`, `OC_LEDGER_GIT_TAIL_WAIT=20`. |
| `git_repo` | function | Factory. `git init` with identity pinned via `-c user.name/-c user.email` **and** written repo-local — 4 repos in the battery today only work by accident of the container's global git config. |
| `run_tool` | function | `run_tool(cmd, *, timeout=...)` → `Result(.rc, .out, .err, .duration_ms, .timed_out, .cmd)`. **`timeout` is required** — no default. |
| `run_selftest` | function | `run_selftest("oc-x", timeout=...)` → same `Result`. Per-call throwaway state dir (M2-22); falls back to `OC_SELFTEST_TIMEOUT` (1800 s). |
| `gh_stub` | function | Factory. One stub wired into **three seams** at once: `OC_DEPLOY_GH`, `OC_ISSUE_CREATE_GH`, and a `PATH` dir. Logs every call as JSON. |
| `battery_lock` | session | Holds the single-flight flock at `/tmp/oc-battery.lock` (override `OC_BATTERY_LOCK`), wait budget `OC_BATTERY_LOCK_WAIT` (default 900 s). |
| `tools_dir` | session | The `tools/` dir of **this** checkout. |

### What `env_guard` blocks

Four leaks that exist in `run.sh` today:

1. **`OC_FANOUT_LEDGER`** defaults to the live fleet ledger
   (`$HOME/.opencrabs/profiles/ops/opencrabs-dev/events.jsonl`,
   `run.sh:3095,3102,3111`). Every fanout leg in the battery writes it today.
2. **`--repo /root/opencrabs`** reads the production checkout
   (`run.sh:1536`, `:1974`). An argument cannot be blocked by an env var, so
   `run_tool` refuses it at launch (`LiveStateLeak`).
3. **`OC_DEPLOY_STATE_DIR`** defaults to the real profile (`run.sh:2542`) —
   pinned by `state_dir`.
4. **`PATH` is prepended 4× and never restored** (`run.sh:3412`, `3483`, `4136`,
   `4787`), so a later section inherits an earlier one's stub dirs. `PATH` and
   `HOME` are snapshotted and restored after every test.

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
`os.killpg(..., SIGKILL)`, then reports `rc=124` — the code `run.sh` already
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
- **At `-n 1` the caps are byte-identical to `run.sh:423`**, so a serial pytest
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

## Findings the port produced

Two defects surfaced only because the legs drive the REAL blocks instead of
grepping them. Both were in this suite's own tooling, not in `run.sh`:

1. **The section-marker regex missed 10 of 73 sections.** `\d+[a-z]?\.` matches
   `3.`, `9b.` but not `00a2.` (two digits), and it cannot match the retired
   aliases `9g`/`9h`. `lib/harness.py`'s twin extractor therefore disagreed
   with `run.sh`'s awk by ten sections while looking correct. Caught by
   `test_the_section_count_matches_the_marker_count`, which compares the twin
   against the awk it emulates — a comparison of two implementations, not a
   grep of one.

2. **The `missing-systemd` legs were creating real transient scopes.** Unlinking
   the stub did not hide `/usr/bin/systemd-run`, so the block found the host's
   real binary and registered a scope on the live user manager. Fixed with a
   restricted `CI_UTIL` PATH; verified zero leaks with
   `systemctl --user list-units 'run-*'`. A negative test that removes a stub
   must control the whole search path, or it tests the host.

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
  `subprocess.run` — the bound and the group kill are the point. Where a leg
  needs raw `Popen`/`run` (a detached probe, a scanner), use `H.spawn`/`H.run`:
  they are the same call plus a bounded retry on a REFUSED FORK.

  Why that retry exists, measured 2026-11-27: three peer lanes on four cores
  and 3 GB RAM held load at 18, and `-n auto` reds **rotated** between runs —
  a different leg each time, always at a fork, always `BlockingIOError:
  [Errno 11]`. A rotating identity is the discriminator: a logic defect fails
  the SAME leg every run. The ceiling was never the limit (cgroup pids
  343/10251, 522 threads against 31064), so the refusal is transient pressure.
  Only the fork is retried — a child that RAN and exited non-zero is a verdict
  and is never retried, because retrying it would be the suite lying to itself.

  **A generated script is not a caller.** A rewrite that adds `H.` inside a
  string literal handed to `write_text` produces a child that dies on
  `NameError` while the parent test still passes its own assertions — the
  grandchild never starts and the leg proves nothing. Generated code keeps
  plain `subprocess`.
- **Never hardcode `/root/opencrabs` or a `$HOME/.opencrabs/...` path.** Use
  `scratch`, `state_dir`, `ledger_sandbox`, `git_repo`, `gh_stub`.
- **`timeout` is a number, not a guess.** 1800 s for a real selftest; tens of
  seconds for a fixture-level tool call.
- **A leg that writes the canonical receipt must be `serial`.** The lock is the
  only thing preventing two lanes from interleaving writes.
