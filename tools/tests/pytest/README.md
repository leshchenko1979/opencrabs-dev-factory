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
| `tools/` | ported `run.sh` sections that drive a SHIPPED `oc-*` tool: attrib, branch-sweep, deploy stage (fast legs), fanout, fmt, gate, health, issue-dispatch, ledger, notify-fanout, receipts, quoting guard, rc contract/help, review-persist, seal, shadow-rotate, smoke-evidence, tool contracts, the `run_selftest` blanket, usage rc, vendor-drift, verify trio |
| `infra/` | `lib/*.sh` / `lib/*.py` units — claims predicate, embed, flood guard, log lib, notify lib, root resolver, snap, unified-log wire |
| `e2e/` | legs that build a real tree and run a real subprocess end-to-end: `test_e2e_deploy_stage.py` (slow) and the entry-preamble fixpoint drive |
| `.` (root) | the three that are about the SUITE rather than a subject: `conftest.py`, `test_foundation.py` (fixture foundations), `test_parity.py` (the coverage census) |

Basenames stay unique across the suite, so `--import-mode` needs no change and
`-k`/`-m` selection is unaffected. **The census in `test_parity.py` resolves
modules by basename** (`module_path()`), so a module may be refiled without
touching the coverage map — but a module moved into a folder the resolver does
not list raises rather than reporting zero mass.

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

---

## Coverage: what is ported, and what is not

The shell battery's 68 sections are not 68 equals. Three kinds live in `run.sh`:
a bare `run_selftest` line, bespoke `ok`/`bad` assertion legs, and the
harness's own infrastructure (cgroup, battery lock, scratch root). Only the
second kind needs porting — a `run_selftest` line is one pytest case and the
harness legs are already ported as `test_cgroup.py` / `test_fixtures.py`.

### Ported

| run.sh § | Subject | Module |
|---|---|---|
| 1–6 | lib/oc-log.sh, oc_log.py retired consumers, oc-issue-dispatch availability, flood guard (both ts forms, matches-not-lines, verdict rcs) | `test_log_lib.py`, `test_flood_guard.py` |
| 7 | unified-log wire (real tool → tmp log) | `test_wire.py` |
| 8–10 | oc-verify-order / oc-verify-job / oc-verify-artifact | `test_verify_trio.py` |
| 11, 19 | oc-seal IFS multi-filter merge; orders vocabulary + purge | `test_seal.py` |
| 12 | lib/oc-embed.sh job-name decoder | `test_embed.py` |
| 13 | lib/oc_claims.py canonical predicate | `test_claims_predicate.py` |
| 16–17 | oc-attrib join; #407 novelty filter (re-sha'd + empty commits) | `test_attrib.py` |
| 22 | oc-fanout + attribution (#24) | `test_fanout.py` |
| 23 | deploy stage tools (oc-build / oc-status) — fast boundary legs | `test_deploy_stage.py` |
| 23 | deploy stage tools — real-subprocess legs (selftest, dispatched-sha, stale ref) | `test_e2e_deploy_stage.py` (`slow`) |
| 24, 32 | oc-ledger edge legs; confirm + derive_by | `test_ledger_edge.py` |
| 33 | oc-ledger lock budget (#619) + the #95 git-tail and #171 skill-dir hazards | `test_ledger_lock_budget.py` |
| 25 | oc-review-persist | `test_review_persist.py` |
| 26 | oc-gate | `test_gate.py` |
| 29, 48–50, 52, 55, 56 | usage/`--help` contract cluster | `test_tool_contracts.py` |
| 30 | oc-branch-sweep incl. the #525 journal leg | `test_branch_sweep.py` |
| 34 | oc-shadow-rotate | `test_shadow_rotate.py` |
| 35 | oc-smoke-evidence decoy guard (M2-2) | `test_smoke_evidence.py` |
| 43 | rc contract `--help=0` fleet-wide (C-#3) | `test_rc_help.py` |
| 44–45 | rc contract table integrity; coverage | `test_rc_contract.py` |
| 46 | oc-notify-fanout guards (law 1, dead targets, `--roles`) | `test_notify_fanout.py` |
| 47 | oc-health incl. the watcher-window 24 h/0 discrimination | `test_health.py` |
| 51 | oc-issue-dispatch role-binding edges | `test_issue_dispatch.py` |
| **61** | **oc-issue-dispatch SIGKILL evidence (#451)** — narrative survives a kill mid-send; derived `line_buffering` control leaves 0 B | `test_harness_sigkill.py` |
| 53 | oc-fmt installed/repo identity (#88) | `test_fmt.py` |
| 57–58 | lib/oc-notify.sh CLI budget; per-send sender | `test_notify_lib.py` |
| 59–60 | lib/oc-snap.sh mirror age; reap | `test_snap.py` |
| 63 | lib/oc-root.sh resolver coherence (F-L1/F-L2) — stated as a PROPERTY over depth × invocation shape, not transliterated | `test_oc_root_resolver.py` |
| 64 | shell-quoting guard — the four scanner arms (backtick in a `-c` body, unquoted heredoc fence, `$` in a `-c` body, `bash -n` over the fleet) plus the live fleet sweep | `test_quoting_guard.py` |
| 64 | **oc-vendor-drift** (§83 by header — the census charges its nine sites to §64, see below) — IN_SYNC / DRIFTED / LOCAL_MISSING / `UPSTREAM_UNREACHABLE` rc=3, and the selftest's `0 failed` + pass floor | `test_vendor_drift.py` |
| **62** | **red-receipt transcript (fail log)** — `bad()` writes the row to the transcript **and** stdout, `record()` tees, `finalize_fail_log` both directions, the single-writer ratchets, and the #614 self-contained receipt (the row survives the next run's truncate) | `test_receipt_transcript.py` |
| 65 | entry-preamble fixpoint + relative invocation (#708) — the 9-sample relative drive (cwd = tool dir, `./name`), the two-sided fixpoint control, and a `$0` canary proving the drive really delivers a RELATIVE argv[0]. The static break-presence census lives in `test_oc_root_resolver.py` (row 63) — one invariant, one owner | `test_entry_preamble.py` |
| per-tool argv | the `ok`/`bad` usage/rc legs beside each `run_selftest` | `test_usage_rc.py` |


### §62 — a deferral that was withdrawn (the second one)

The register said §62 "asserts `run.sh`'s own `bad()` accumulator by running a
synthetic failing section in a subshell. There is no `run.sh` accumulator inside
pytest to assert." The second sentence is true and irrelevant: it is a claim
about WHERE THE FUNCTIONS LIVE, not about whether their behaviour can be driven.
`bad()`, `record()`, `finalize_fail_log()`, `battery_capture_fail_rows()` and
`emit_summary()` are TEXT in `tools/tests/run.sh`, so `lib/harness` extracts the
definitions verbatim and `test_receipt_transcript.py` drives the real ones under
`set -u`. Nothing is retyped, so the port cannot keep passing after the block it
describes regresses.

This is the same mistake §33 made, one section over: a limitation of the
MEASURING INSTRUMENT misread as a property of the subject. Both deferrals are
gone; §18 is the only one left, and it is retired rather than deferred.

The port is also stronger in one place the shell could not reach: the shell runs
each transcript leg with its stdout sent to `/dev/null` (so a synthetic failure
cannot corrupt its own receipt), which means "the `FAIL - ` row reaches STDOUT"
was never actually asserted there — only the file half was. Here stdout is
captured, so the two-sink claim is a real assertion, and a `bad()` that wrote
only to the file reds it.

### §33 — a deferral that was withdrawn

The original note said a pytest port "would need the same wall-clock budget to
assert anything the selftest does not". Half right, and the wrong half decided
the deferral. What the selftest cannot do is real — it asserts the budget's
DERIVATION by grepping the source, and those greps are built by concatenation
precisely because a literal self-matches. What it could not do, a pytest leg
does cheaply: HOLD the lock and read the budget the tool reports.

The wall clock was never the subject. The shell spent 4 s per leg on
`( flock -x 9; sleep 4 ) &` plus `sleep 0.5` because a shell has no synchronous
flock; `fcntl.flock` holds the same lock with no latency, so §33's contention
costs milliseconds here. Ported as `test_ledger_lock_budget.py` — 9 legs, and
the whole file's wall clock is dominated by the box rather than by the legs:
**44.40 s** serial / **64.13 s** under `-n 2` at load 26.10 / 22.66, against
**16.59 s** / **28.04 s** at load 11.08 / 10.60 (both pairs measured
2026-11-27 on 4 cores). That spread is the point — no single leg asserts
elapsed time (see the module docstring's TIMING HONESTY section), and the only
sleep is the deliberate 3 s `pre-commit` hook that makes the git tail
observably slow.

The legs are also mutation-checked: making the budget flat reds the three
derivation legs, running the tail under the ledger lock reds the #95 leg, and
dropping the `OC_SKILL_DIR` seam reds the #171 positive leg (with the negative
control still green).

The port is also STRONGER than the shell in three places, each of which the
shell could not reach:

* the budget legs add a third push bound (7 s → 37 s) that the shell's two
  literals (31 s, 40 s) cannot cover, so the leg asserts a derivation rather
  than a table of constants;
* the #95 leg POLLS the git-tail lock and asserts the ledger lock is free *at
  that instant*, where the shell slept 1 s and hoped the holder was in the tail;
* the #171 legs use a copied tool tree with a POISON origin, so "nothing reached
  the real remote" is a direct read instead of an md5 of a repo every other lane
  on the box is also pushing to — and the negative control (drop the seam, the
  poison origin must move) proves the positive leg is not vacuous.

### Not ported

Each of these is a deliberate decision, with the reason — not an omission.

| run.sh § | Subject | Why not ported |
|---|---|---|
| **18** | **oc-consent-check** | **RETIRED 2026-08-28 (owner order 18:50Z).** The consent process was eliminated and the tool archived to `tools/archive/`. The shell section is a `section` header with no body — it asserts nothing, so a port would be an empty test that inflates the pass count. Deleted rather than ported. |
| 14, 15, 20, 21, 27, 28, 31, 36–42, 54 | — | Each is a `run_selftest` line plus at most one argv leg, and both halves are already covered: the selftest by the parametrized `run_selftest` legs, the argv leg by `test_usage_rc.py`'s `RC_CASES` table. A port would duplicate an existing leg verbatim. |
| 66–68 | cgroup isolation, battery lock fd, scratch root | Harness infrastructure, not tool behaviour — ported as `test_cgroup.py` and `test_fixtures.py`, which assert the pytest harness's own equivalents. |
