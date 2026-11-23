# Factory test battery — step-1 baseline profile

Plan `2fae1230-de9e-4fa5-aa24-822cf7188c3e` ("Speed Up Factory Test Battery"), step 1.
Actor: toolsmith. Captured 2026-11-23 ~16:58–17:45Z.

---

## 1. What is pinned, and to which commit

The canonical receipt `tools/tests/battery-last.json` has **no commit field**. Its schema is
`path, ts, pass, fail, verdict, mode, pids_max, pids_cap, fail_log, fail_rows,
fail_rows_truncated, tree_changed, cgroup, cgroup_isolated, nice, ioprio, wall_ms, timing`.
So the measured tree must be pinned out-of-band. It is pinned here:

| Fact | Value | Evidence |
|---|---|---|
| Receipt measured at | **`95454e01e0330d491f7cedaa1ee3a21f71d4e9c3`** | receipt `ts=2026-11-23T15:52:00Z`; `git log -1 95454e01` → `2026-11-23T14:43:21+00:00`; receipt `tree_changed=false` |
| Receipt committed in | `4a58880abd5aa1e93fa6197d7a6218f9a4a5b83b` | `git log -1 4a58880a` → `2026-11-23T15:56:20Z` "battery receipt — PASS 459/0 measured at 95454e01" |
| Diff `95454e01..4a58880a` | **only** `tools/tests/battery-last.json` (+4/−4) | `git diff --stat 95454e01 4a58880a` |

**Consequence:** `4a58880a` and `95454e01` differ *only* in the receipt file, which the battery
rewrites on every run. A re-run at `4a58880a` therefore measures an equivalent tree. The tree
fingerprint helper value recorded earlier is `d2bdff32ec52e95f45335326f2f07f3c`.

## 2. Baseline numbers (verbatim receipt, `tools/tests/battery-last.json`)

```json
{
  "path": "/root/.opencrabs/profiles/ops/skills/opencrabs-dev/tools/tests/battery-last.json",
  "ts": "2026-11-23T15:52:00Z",
  "pass": 459,
  "fail": 0,
  "verdict": "PASS",
  "mode": "sequential",
  "pids_max": "64",
  "pids_cap": "",
  "fail_log": "",
  "fail_rows": [],
  "fail_rows_truncated": false,
  "tree_changed": false,
  "cgroup": "/user.slice/user-0.slice/user@0.service/oc.slice/oc-tasks.slice/run-ra89e22d2e697480b8098034ef3d7e5ac.scope",
  "cgroup_isolated": false,
  "nice": "19",
  "ioprio": "idle",
  "wall_ms": 2144957,
  "timing": {"max_concurrency": 1, "section_count": 71, "sum_ms": 2144746, "slowest": [{"n": 7, "ms": 454299, "start_ms": 1795447210201, "end_ms": 1795447664500, "title": "unified-log wire (real tool -> tmp log)"}, {"n": 55, "ms": 359917, "start_ms": 1795448678843, "end_ms": 1795449038760, "title": "oc-issue-dispatch (mechanized issue triage dispatch)"}, {"n": 25, "ms": 243700, "start_ms": 1795447820045, "end_ms": 1795448063745, "title": "oc-deploy"}, {"n": 26, "ms": 179847, "start_ms": 1795448063745, "end_ms": 1795448243592, "title": "oc-ledger"}, {"n": 44, "ms": 112123, "start_ms": 1795448410409, "end_ms": 1795448522532, "title": "oc-ship (5\u2192swapped orchestrator, owner GO 16:16Z)"}, {"n": 4, "ms": 107175, "start_ms": 1795447040519, "end_ms": 1795447147694, "title": "flood guard reads both ts forms (#738)"}, {"n": 28, "ms": 73530, "start_ms": 1795448247786, "end_ms": 1795448321316, "title": "oc-gate"}, {"n": 1, "ms": 54599, "start_ms": 1795446975753, "end_ms": 1795447030352, "title": "lib/oc-log.sh (unified tools log)"}, {"n": 17, "ms": 53426, "start_ms": 1795447732142, "end_ms": 1795447785568, "title": "oc-attrib #407 novelty filter (re-sha'd + empty commits)"}, {"n": 48, "ms": 53205, "start_ms": 1795448543024, "end_ms": 1795448596229, "title": "oc-notify-fanout guards (law1 placeholder + dead-target skip + --roles)"}]}
}
```

**Wall:** 2,144,957 ms = **35.75 min**. **459 passed / 0 failed / 71 sections**, `max_concurrency 1`,
`mode sequential`, `jobs` at the product default (`run.sh:304 JOBS="${OC_BATTERY_JOBS:-1}"`, unset).

### Where the time goes (top 10 of 71 sections)

| # | Section | ms | % of wall |
|---|---|---|---|
| 7 | unified-log wire (real tool -> tmp log) | 454,299 | 21.2% |
| 55 | oc-issue-dispatch (mechanized issue triage dispatch) | 359,917 | 16.8% |
| 25 | oc-deploy | 243,700 | 11.4% |
| 26 | oc-ledger | 179,847 | 8.4% |
| 44 | oc-ship (5→swapped orchestrator) | 112,123 | 5.2% |
| 4 | flood guard reads both ts forms (#738) | 107,175 | 5.0% |
| 28 | oc-gate | 73,530 | 3.4% |
| 1 | lib/oc-log.sh (unified tools log) | 54,599 | 2.5% |
| 17 | oc-attrib #407 novelty filter | 53,426 | 2.5% |
| 48 | oc-notify-fanout guards | 53,205 | 2.5% |

**Top 4 sections = 57.8% of the wall.** `sum_ms 2,144,746` vs `wall_ms 2,144,957` → 211 ms of
non-section overhead across 71 sections, i.e. the harness itself is not the cost.

## 3. Resource regime at baseline measurement

Captured pre-run in the isolated clone at 2026-11-23T16:58:00Z:

| Knob | Value |
|---|---|
| commit | `4a58880abd5aa1e93fa6197d7a6218f9a4a5b83b` (detached worktree `/tmp/bat-baseline`) |
| `tree_status_porcelain` | empty (clean) |
| `run.sh` sha256 | `4d3033497f06208f61664d24cff7754e8f00747e867becb3607cd6fb405d83e4` |
| `OC_BATTERY_JOBS` | unset → `JOBS=1` (product default, `run.sh:304`) |
| nproc | 4 |
| loadavg at launch | 9.93 / 9.87 / 7.99 |
| mem | 3,921 MB total, 1,302 used, 2,618 available |
| swap | 4,095 MB total, 552 used, 3,543 free |
| cgroup | `/user.slice/.../app.slice/opencrabs-ops.service` |
| `pids.max` | 192 |
| `memory.max` | 3,221,225,472 (3 GiB) |
| disk `/` | 58 G size, 55 G used, **2.5 G avail, 96%** |
| snap mirrors in `/tmp` | 56 |

The prior receipt's own regime differs and is recorded for comparison: `pids_max 64`,
cgroup `.../oc.slice/oc-tasks.slice/run-ra89e22d2e697480b8098034ef3d7e5ac.scope`,
`cgroup_isolated false`, `nice 19`, `ioprio idle`. Both runs are **unisolated** — the battery
warns `no user systemd manager -- running in .../app.slice/opencrabs-ops.service unisolated (#720)`,
so `#720` isolation did not engage in either sample.

## 4. Blocker: a clean second sample could not be taken

A re-run was launched at `4a58880a` in `/tmp/bat-baseline` under its own lock
(`OC_BATTERY_LOCK=/tmp/oc-battery-baseline.lock`) to avoid colliding with any lane. It reached
**57 ok / 0 FAIL / 9 section headers** and then stalled in section 9 (`oc-verify-job`) with no
failure — the stall is environmental, not a test defect:

| Measurement | Value | Meaning |
|---|---|---|
| `/proc/pressure/io` | `some avg10=76.18 avg60=83.29 avg300=85.27` | host **85% I/O-stalled** |
| `/proc/pressure/cpu` | `some avg10=0.62 avg300=2.88`, `full 0.00` | CPU is *not* the constraint |
| loadavg | 17.19 → 20.40 on **4** cores | load is D-state disk wait, not runnable work |
| D-state processes | 17 | most of the host blocked on I/O |
| disk `/` | 2.5 G → **1.6 G free (98%)** during the run | shrinking under the run |
| `tar -C .../tools ... -cf - .` (oc-verify-job snapshot) | **~2.8 KB/s** (28,672 B per 10 s, `read_bytes` 2,588,672 → 2,617,344) | snapshot crawl, not progress |

Concurrent live writes were present throughout and are **not mine to stop**:
three `oc-ship` lanes (`--sha 2787cf4a…`, `--sha 66ae0f31…`, `--sha 15f24fbe…`) minting
`/tmp/oc-snap-oc-ship-*` every ~2 min and cloning into `/tmp/tmp.*`; `pytest -q` at 57% CPU;
`llama-server` embedding; a PDF generation job. Per the step-1 precondition
("without concurrent battery runs or live writes"), that precondition was **not satisfiable**
at execution time.

**A timing number taken under 85% I/O stall measures contention, not the battery**, so it is not
reported as a baseline. The section also carries `timeout --kill-after=30 1800`, so letting it
continue would have produced a *timeout FAIL* — an environment artifact that would read as a
code regression in the receipt. The run was therefore not allowed to write a misleading receipt.

**Termination record:** stopped at 46:51 elapsed (`kill -TERM` then `-KILL` on the process group;
the D-state `tar` and its `oc-verify-job` parent needed direct `SIGKILL`). No `BATTERY_EXIT=` line
was ever written, so no receipt was produced in the clone. Partial state at stop: **57 ok /
0 FAIL / 9 section headers**, last section `oc-verify-job`. Worktree `/tmp/bat-baseline` and the
`oc-verify-job` stage dir were removed; canonical tree left clean at `4a58880a` + this doc.

### New finding relevant to step 2+

`oc-verify-job --selftest` snapshots the whole `tools/` tree with
`tar -C <root>/tools --exclude=... -cf - .` piped into `tar -xpf -` in a stage dir, on **every
invocation**. That is a full-tree copy per call; under I/O pressure it is the first section to
wedge. This is a concrete optimisation target independent of the `JOBS` lever.

## 5. Reproduction commands

```bash
# clone the pinned tree (no live writes, own lock)
git -C /root/.opencrabs/profiles/ops/skills/opencrabs-dev \
  worktree add --detach /tmp/bat-baseline 4a58880abd5aa1e93fa6197d7a6218f9a4a5b83b

# run detached, product-default jobs (do NOT pass --jobs)
cd /tmp/bat-baseline && setsid bash -c '
  OC_BATTERY_LOCK=/tmp/oc-battery-baseline.lock bash tools/tests/run.sh \
    > /tmp/bat-base-1.log 2>&1; echo BATTERY_EXIT=$? >> /tmp/bat-base-1.log' </dev/null &

# read the RECEIPT, never $? after a pipe
jq '{verdict,pass,fail,wall_ms,mode,timing}' /tmp/bat-baseline/tools/tests/battery-last.json

# precondition gate before trusting any wall number
cat /proc/pressure/io; df -h /; cat /proc/loadavg
```

## 6. Not done / next

- No second clean sample: blocked on host I/O saturation (§4). Re-run when
  `/proc/pressure/io` `some avg60` is low and `/` has multi-GB free.
- `JOBS` default untouched: `run.sh:304` still `JOBS="${OC_BATTERY_JOBS:-1}"`. Sections 88/89
  assert that default; a change would redden leg `#76`. That lever belongs to the
  default-change lane, not here.
- No production file changed; no default changed; battery not run in the canonical tree.
