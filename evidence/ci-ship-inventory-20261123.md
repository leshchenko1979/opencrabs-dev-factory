# CI Ship Process — Surface Inventory (plan step 1)

**Date:** 2026-11-23 · **Author:** HQ lane · **Plan:** `Fix CI Ship Process` (session plan, approved)

No behaviour changed in this step. Every line reference below was opened and read in this
session against live bytes; where the plan's own line reference is wrong, the correction is
stated in place.

## 0. Surfaces read

| Surface | Identity at read time |
|---|---|
| Skill/tool repo | `leshchenko1979/opencrabs-dev-factory` @ `9d09c9f5` (`/root/.opencrabs/profiles/ops/skills/opencrabs-dev`) — holds `tools/`, the skill law, `evidence/` |
| State dir | `leshchenko1979/opencrabs-dev-state` @ `70ae77946` (`/root/.opencrabs/profiles/ops/opencrabs-dev`) — holds `workers-ledger.json` (view), `events.jsonl` (record), `tools.log` |
| Source repo | `/root/opencrabs` |
| Carrier worktree | `/root/oc-work/carrier-1936` (branch `ci/quick-build-linux`) |

---

## A. The ledger state: writers, readers, resolvers

### A.1 The two surfaces and the one format switch

`tools/state/oc-ledger:807-813` states the switch: **`events.jsonl` is the RECORD** (one JSON
object per line, append-only); `workers.json` carries the non-event state;
**`workers-ledger.json` is a MATERIALIZED VIEW** regenerated from those two, existing only so
the legacy consumers keep working — *never authoritative*.

`_jsonl_mode()` (`oc-ledger:813`) is true when `events.jsonl` exists. When it is **absent** the
tool runs the **legacy single-file path unchanged** — so the migration is opt-in per state dir
and reversible by deleting one file. Both formats are live in the fleet today.

### A.2 Writers

| id | Site | file:line | Class |
|---|---|---|---|
| **W1** | JSONL record append — the authoritative write path | `tools/state/oc-ledger` (the `stamp` path) | **Authoritative writer** |
| **W2** | `ledger_write_view` — regenerate the view atomically (tmp + `mv` on the same filesystem) | `tools/state/oc-ledger:857-868` | **The one format-switch owner** |
| **W3** | `ledger_stamp` — `jq '.events += [{…}]' "$LEDGER" > "$tmp" && mv` | `tools/lib/oc-deploy-lib.sh:562-573` (the jq at **:571**) | **Stale blob writer** — writes the VIEW |
| **W4** | `with_modes` fixture helper | `tools/harvest/oc-harvest-dispatch:2168` | Fixture, not a writer — see §G |

**W3 is the defect step 2 targets.** Its row lands in the materialized view and is erased by
the next `ledger_write_view` rebuild from `events.jsonl` + `workers.json`. Its `n` ordinal is
computed correctly (`jq '[.events[].n] | max // 0'` over the view, `:568`) — the ordinal is
right and the row is lost, which is the worst shape for an audit: a number that looks
authoritative and a record that does not exist.

### A.3 Readers of the view — every one of them is on a surface the rebuild erases

| Reader | file:line | Reads |
|---|---|---|
| `stage()` | `tools/lib/oc-deploy-lib.sh:445` | `.meta.oc_deploy_stage` off `$LEDGER` |
| `shadow_log()` | `tools/lib/oc-deploy-lib.sh:446-452` | calls `stage()` |
| `recover-receipt` idempotence | `tools/lib/oc-deploy-lib.sh:410-413` | raw `jq` over `$LEDGER`'s `.events[]` |
| `oc-status` | `tools/ship/oc-status:524` | instructs the operator to *hand-set* `ledger meta.oc_deploy_stage to S2` |

The last row is the sharp one: in JSONL mode `.meta.oc_deploy_stage` belongs in `workers.json`,
so a stage written onto the view is erased by the same rebuild that erases W3's rows.

### A.4 Two resolvers, one filename, different precedence

| Resolver | file:line | Order |
|---|---|---|
| deploy-lib | `tools/lib/oc-deploy-lib.sh:53-59` | `OC_LEDGER` → `OC_DEPLOY_STATE_DIR/workers-ledger.json` → canonical `$OC_DEV_STATE`/`$HOME/.opencrabs/profiles/ops/opencrabs-dev`/`workers-ledger.json` |
| oc-ledger | `tools/state/oc-ledger:230-239` (`parse_global`) | `--ledger` → `OC_LEDGER` → `OC_DEPLOY_STATE_DIR/workers-ledger.json` → `STATE_DIR_DEFAULT/workers-ledger.json` |

Both land on **`workers-ledger.json`** — the *view* name. Two resolvers, one target, and
`oc-ledger` additionally accepts `--ledger`, which `deploy-lib` does not: the same state dir can
be addressed by two different paths unless `OC_LEDGER` is exported (which is what step 2 does).

`oc-ledger:241-248` carries a second, newer identity rule: `STATE_DIR()` is derived from the
ledger path itself (`dirname`, pure-bash, byte-identical to `dirname`), because the previous
guard compared two readings of the *same* variable and fired on any scratch dir.

### A.5 The grep baseline — **measured, and it differs from the plan**

Command (the plan's own):

```
grep -rn 'events *+=' tools/ --include='oc-*' --include='*.sh' | grep -v '^tools/state/oc-ledger'
```

Result: **six** lines, not one.

| # | Match | What it is |
|---|---|---|
| 1 | `tools/lib/oc-deploy-lib.sh:571` | **the production writer** (W3) |
| 2 | `tools/harvest/oc-harvest-dispatch:2168` | inside the tool's embedded selftest block; writes `$st_dir/ledger-mode.json`, a **mock** ledger |
| 3–6 | `tools/harvest/oc-harvest-dispatch.2026-11-22T*.bak` (4 files) | **untracked** leftovers, gitignored by `.gitignore:6` (`*.bak`), left on disk by the 2026-11-22 dispatch-tool edit |

**Consequence for the plan.** The countable *production* target for step 2 is **one** site
(`deploy-lib:571`), so step 2's scope is unchanged. But the plan's literal acceptance text —
"returns exactly the pre-fix inventory (today: one line, `tools/lib/oc-deploy-lib.sh:571`)" —
is **stale against today's tree**: it now returns six, and a reviewer running that exact
command gets a mismatch. The criterion's *intent* (a countable baseline) holds; its *text*
must be restated as: one production writer, one embedded fixture, four ignored backups.

---

## B. The tested-tree identity chain — where it lives, and why it is not durable

| Element | file:line | Fact |
|---|---|---|
| `oc_job_sha` | `tools/lib/oc-patch.sh:33-43` | first 40-hex in a job name; covers `PR-lane gates (<sha>)` and `ship / Linux amd64 (<sha>, <features>)`. Contract: **empty string, rc 0** on no match (the `|| true` is load-bearing — a `pipefail` caller would abort) |
| Gate pinning | `tools/harvest/oc-gate:20-27` | the adopted run is pinned by the 40-hex **in its job name** via `oc_job_sha`, refused **rc 4** on mismatch; a queued run whose jobs are not materialised journals `adoption_pin=unpinned` rather than passing silently |
| Per-step tiebreak | `tools/harvest/oc-gate:61` | per-step failure detail already parsed |
| **Ship re-derives identity independently** | `tools/ship/oc-ship:1411`, `:1443-1450`, `:1458-1459` | ship lists job names, runs `oc_job_sha "$jn"` (**:1446**), matches the sha by `contains(...)` (**:1411**, **:1450**), and carries a content-identical rebase forward via `oc_same_patch` (**:1458**) |
| The verdict's only durable trace | `tools/lib/oc-log.sh:204-205`, `:255-256` | **one `tools.log` invocation row**: `extra.verdict`, `extra.adoption_pin`, `extra.run_id`, `extra.resume` — read back by the gate selftest at `oc-gate:910-911`, `:979`, `:1023` |

**The ship chain journal is a different surface.** `$STATE_DIR/oc-deploy/journal/swap-<run>-<ts>-$$.jsonl`
(`oc-deploy-lib.sh:69`, `:491-492`) carries LEG1 lines — e.g. `GATE-SKIPPED-DOCS sha=…`
(`oc-ship:1398`) — but **not** the gate's tested sha, per-job conclusions, or step detail.

> **The gap, stated plainly.** The tested tree's identity lives in a **job name** (an external
> convention baked by the carrier workflow) and the verdict about it lives in a **log row**.
> Nothing durable binds the two in a file a later reader can check without a log parser.
> `oc-ship` re-derives the identity a second time, by a second path, with no shared artefact
> to compare against — which is why a mismatch between what was gated and what lands can only
> be discovered by re-parsing both sides at the moment of shipping.

---

## C. The doc-first ordering — **the plan's premise is falsified**

`cmd_sync`'s two doc gates (`tools/state/oc-ledger:1713-1721`), both `die 6`:

```
grep -Eq "^version: $v\$"        "$SKILL_DIR/SKILL.md"    || die 6 "…bump the doc first"
grep -Eq "^## v$v([ —(:]|$)"     "$SKILL_DIR/CHANGELOG.md" || die 6 "…write the receipt first"
```

**These read FILES. There is no commit-ordering check anywhere in `cmd_sync`** — no `git log`,
no `HEAD` comparison, no "the doc must be in an earlier commit" test. The gate is a **content**
check: *at the moment `sync` runs*, the docs must already carry the version.

And the commit leg that follows (`oc-ledger:161-184`) is already idempotent:

```sh
if ! git diff --cached --quiet; then      # #467 — nothing staged → skip
  git commit -q -m "skill v$v: oc-ledger sync — ${why:-version sync}" || echo "commit-lag: …"
fi
```

`git diff --cached --quiet` exits 0 exactly when the index matches HEAD, so on a **clean tree**
the commit leg is a benign no-op.

**Therefore the one-commit path already works today:**

1. One commit carrying the implementation **and** `SKILL.md` (`version: v0.4.x`) **and** the
   `CHANGELOG.md` `## v0.4.x` entry.
2. Run the battery on that tree (the receipt must be `PASS`, `fail==0`, **< 6 h old** — the
   real gate, `oc-ledger:1705-1712`).
3. `oc-ledger sync --version v0.4.x --why "…"`: the content gates pass, the stray-guard sees
   a clean tree and refuses nothing, the commit leg no-ops, the tag is cut, the state repo is
   stamped with the version and the law digest.

**Nothing needs relaxing.** The "separate changelog-only commit and CI cycle" is a *process
convention* (what lanes actually do), not an enforced ordering — and the plan's own risk note
called for it to ship "as a design question … never as a silent edit". The honest version of
step 5 is therefore **narrower than planned**: state the one-commit path in the law prose, and
prove it with a fixture — no gate is deleted, because no gate enforces the ordering.

---

## D. The CI surface (workflows, carrier branch, job-name shapes)

### D.1 Where the workflows live

| Repo / branch | Files |
|---|---|
| `/root/opencrabs` (fork `main`) | `.github/workflows/`: `auto-assign.yml`, **`ci.yml`**, `fork-fmt-net.yml`, `prerelease.yml`, `release.yml` |
| branch `ci/quick-build-linux` (carrier) | `ci-lane-impl.yml`, **`pr-checks.yml`**, `quick-build-linux.yml` |

**`ci.yml` does NOT exist in the skill repo** — it lives in the source repo. The carrier files
exist ONLY on `ci/quick-build-linux`; `main` carries upstream's workflows and therefore has no
post-merge net. A path-based inventory that assumes them silently inventories nothing.

### D.2 `ci.yml` (source repo, the ordinary CI)

| Job | `name:` | Cap | Notes |
|---|---|---|---|
| `lint` | `Lint` | `timeout-minutes: 25` (:64) | `cargo fmt --all -- --check` (:119), `cargo clippy --locked … -D warnings` (:122) |
| `build` | `Build (${{ matrix.target }})` | `timeout-minutes: 40` (:147) | `needs: [lint, audit]` (:133); Windows deliberately NOT built (#627) |
| — | group `ci-${{ github.ref }}`, `cancel-in-progress: true` (:43-44) | | the supersede class of §H |

### D.3 `ci-lane-impl.yml` (carrier) — the ORDER gates

- `order-gates` job, `name: ORDER gates (${{ inputs.source_ref }})` (:226-228),
  **`timeout-minutes: 45`** (:228).
- The file's own header records the current shape (:71-73): the legacy `cargo test` leg was
  **deleted**, there are **four 45-minute JOB caps**, and the test leg was re-homed into
  `pr-gates-nextest`.
- `mode` input = `build` (ORDER gates → Linux amd64 build) | `gate` (PR-lane gates) (:98).
- Job-family token pinned to a short prefix-safe form, `ship` / `gate` (:91).

### D.4 `pr-checks.yml` (carrier) — the gate lane

- `name: PR-lane gates`, and exactly **ONE job, `name: gate`** (:149).
- `diagnose` input (:98): prints the runner's resource envelope **twice** — before the test leg
  and after it — because `memory.peak` taken before compilation is the peak of whatever ran
  earlier in that cgroup, so a pre-only probe cannot show what the compile-and-test leg reached.
  Now `default: false` (carrier `86bc423a2`).
- `test-threads` input: **RETIRED 2026-11-20** (:111) — the libtest leg it configured is
  deleted, nextest is the verdict; the input is accepted and IGNORED so
  `oc-prchecks --test-threads N` keeps dispatching instead of erroring.

### D.5 The three job-name shapes (the identity convention)

From the verifiers' own fixtures (`oc-verify-job:154`, `oc-verify-artifact:143`):

```
gate / PR-lane gates (<sha>)
gate / Linux amd64 (${{ inputs.source_ref }}, ${{ inputs.features }})
gate / ORDER gates (${{ inputs.source_ref }})
```

`oc-verify-artifact:249` records the trap: when the build job is SKIPPED its name renders as the
**literal** `${{ inputs.source_ref }}` placeholder, so a decoder that requires 40-hex finds
nothing — that is #34.

---

## E. The selftest inventory

23 files in `tools/tests/`: `run.sh` (299 KB — the battery), `deploy-selftest.sh` (170 KB),
`ship-selftest.sh` (179 KB), `flake-fanout.sh`, `oc-mutate-selftest.sh`, one anchored-fence
script, and **16 `negctl-*-mutation-guard.sh` scripts** (31 · 33 · 34 · 36 · 38 · 39 · 40 · 43 ·
44 · 45 · 301 · 307 · 426 · 428 · 728).

**The mutation guard is the house pattern** and the model step 2's control must follow:
`negctl-34-mutation-guard.sh` copies the tree, neuters ONE predicate
(`oc_decode_job_sha_any()` → `return 0 # MUTANT`, :123-141), re-runs the suite, and requires
exactly the affected legs to go red. Its assertion requires **exactly one** definition of that
function in `lib/oc-embed.sh`.

**The JSONL gap is confirmed by bytes.** The three fixtures the plan names
(`deploy-selftest.sh:583`, `:838`, `:863`) are:

```sh
printf '{"meta":{"oc_deploy_stage":"S2"}}'                          > "$SD/workers-ledger.json"
printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}'               > "$SD/workers-ledger.json"
printf '{"meta":{"oc_deploy_stage":"S2"},"events":[]}'               > "$SD/workers-ledger.json"
```

**Every fixture writes the LEGACY blob.** No fixture anywhere exercises the JSONL mode, which is
why the view-erasure defect in §A.2 could survive a green battery: the production writer is
exercised only in legacy mode, where the view IS the record.

---

## F. The dispatch classification — and TWO job-name decoders, not one

**`oc-harvest-dispatch:2168` is NOT a production writer.** It sits inside the tool's embedded
selftest block (`with_modes`) and writes a **mock** `$st_dir/ledger-mode.json`. The four `.bak`
files are untracked, gitignored (`.gitignore:6`) husks left by the 2026-11-22 dispatch-tool
edit. **Production writers: exactly one** (`deploy-lib:571`).

### F.1 Two decoders — and MEASUREMENT REVERSED my first reading of them

My first pass at this section read the two headers and concluded the any-shape decoder was the
canonical one. **The measurement says the opposite**, and the note is corrected in place
(factory **#160** filed).

| Decoder | Site | Predicate |
|---|---|---|
| `oc_job_sha` | `tools/lib/oc-patch.sh:36-43` | **first 40-hex ANYWHERE** (`grep -oE '[0-9a-f]{40}' \| head -1`) |
| `oc_decode_job_sha_any` | `tools/lib/oc-embed.sh:35-41` | two-pass: `oc_decode_job_embed` (two-field), else `sed -nE 's/.*\(([0-9a-f]{40})\).*/\1/p'` — the sha must be **immediately** followed by `)` |

**The four REAL job-name shapes** (from `ci-lane-impl.yml:226,263,401` and `pr-checks.yml:149`),
measured this session:

| job name | `oc_job_sha` | `oc_decode_job_sha_any` |
|---|---|---|
| `PR-lane gates (<sha>)` | `<sha>` | `<sha>` |
| **`PR-lane gates (<sha> — FIX MODE)`** | `<sha>` | **EMPTY** |
| `ORDER gates (<sha>)` | `<sha>` | `<sha>` |
| `Linux amd64 (<sha>, feat-a)` | `<sha>` | `<sha>` |

`ci-lane-impl.yml:401` renders
`PR-lane gates (${{ inputs.ref }}${{ inputs.fix && ' — FIX MODE' || inputs.lockregen && ' — LOCK REGEN' || inputs.lockupdate && ' — LOCK UPDATE' || inputs.swap && ' — SWAP MODE' || inputs.fast && ' — FAST' || '' }})`
— **five** real shapes carry a suffix, and the any-shape decoder returns empty on all five.

**Blast radius** (read from the consumers): `oc-verify-job:256-263` and `oc-verify-artifact:261-267`
SCAN all names and take the first that decodes, so they tolerate the empty decode only while
another job still decodes — and in a **gate-mode** run the build job is SKIPPED (its name renders
as the literal placeholder, `oc-verify-artifact:249`) and `ORDER gates` belongs to build mode, so
`PR-lane gates` is the ONLY sha-carrying job. With a suffix: `oc-verify-job` → rc 4
`REF-MISMATCH`, `oc-verify-artifact` → rc 4 `PROVENANCE`, `oc-fanout:124` → empty sha →
unattributable range (the #932 symptom). **Fail-closed, not wrong-write.**

**Consequence for step 3 — the plan's instruction is VINDICATED.** "Reuse `oc_job_sha`, do NOT
write a second job-name parser" is correct: `oc_job_sha` covers every real shape today. The
correction the receipt needs is the opposite of what this section first claimed: the receipt's
`tested_sha` should come from `oc_job_sha` (or from a decoder FIXED to cover the suffix shape —
factory #160), and a gate must assert the two decoders AGREE on every real shape, because the
fleet has two predicates for one question and they disagreed on a production shape.

`oc_job_sha`'s `|| true` is load-bearing, not a patch: under a caller's `set -o pipefail` a
no-match grep (or `head`'s SIGPIPE, rc 141) would abort the CALLER — measured 2026-11-20, when
oc-ship's LEG1 carry-forward died rc=1 with no message on a content-identical rebase purely
because `gh` listed a sha-less job first.

---

## G. Who else consumes the job-name convention (step 4's scope is wider than written)

| Consumer | Site | What it does with the name |
|---|---|---|
| `oc-ship` | `tools/ship/oc-ship:1446` | `oc_job_sha "$jn"` per job name |
| **`oc-audit-ship`** | `tools/ship/oc-audit-ship:242` | selects the BUILD job by `name contains sha AND NOT contains("ORDER gates")`; :239 documents that the ORDER gates job embeds the same sha but is a different job |
| `oc-verify-job` | `tools/ship/oc-verify-job:116`, `:154` | `STUB_JOBS` fixtures carrying all three name shapes |
| `oc-verify-artifact` | `tools/ship/oc-verify-artifact:126`, `:143`, `:249` | same, plus the SKIPPED-build placeholder trap |
| `oc-build` | `tools/ship/oc-build:355-356` | `"ORDER gates 4/4 PASS ($SHA)"` |

**`oc-audit-ship` is not named in the plan at all.** It is the tool that already decides *which
job's conclusion counts* — the exact discrimination the receipt must carry. A receipt that
records `jobs[]` with name/conclusion/blocking (step 3) should be what `oc-audit-ship` reads,
not a second opinion computed from the same job names.

---

## H. The five failure classes, measured against the log's own fields

Source: `opencrabs-dev/tools.log` — **91,319 lines**, 91,317 parsed (0 unparsed), file mtime
**2026-11-23T10:24:22Z**, schema `ts · tool · actor · args · exit · secs · pid · extra`. Every
count below is an enumeration over ONE coherent snapshot of that file, not a sample — and the log
is **appended live**, so a re-read drifts by a few rows.

**The verdict field is too coarse to classify on.** `extra.verdict` carries
`NO-DRIFT · DRIFT · GREEN · RED · CANCELLED · NO-HISTORY · IN-SCOPE · CLEAN · refused ·
BASE-FAULT` — but the tool writes a FINER field for the same event: **`cancel-class=`
(`TIMEOUT` · `NOT-ESTABLISHED` · `SUPERSEDED`)**, and `verdict_reason` headlines
(`run-failure` 590 · `superseded` 121 · `cancel-class=TIMEOUT` 25 · `NOT-ESTABLISHED` 20 ·
`SUPERSEDED` 16 · `run-cancelled` 3 · `jobs-failed: …` 2).

### H.1 The census

| Class | Rows | How it is recognised today | Machine-readable? |
|---|---|---|---|
| **stale-invocation** (a resume of an existing run) | **2,151** | `extra.resume` present (2,143 `oc-prchecks`, 8 `oc-gate`) + `extra.resumed_head` | **YES** — `resume`, `resumed_head` |
| **supersede** (a newer run took over; not a failure) | **137** | `verdict=CANCELLED` with reason `superseded` (121) or `cancel-class=SUPERSEDED` (16) | **PARTLY** — both carriers are free text (`verdict_reason`), no structured key |
| **timeout** | **25** | `verdict_reason` containing `cancel-class=TIMEOUT` | **PARTLY** — free TEXT inside `verdict_reason`; there is no structured `cancel_class` key |
| **not-established** | **20** | `verdict_reason` containing `cancel-class=NOT-ESTABLISHED` | **PARTLY** — same free-text carrier |
| **refusal** | **3** | `verdict ∈ {refused, BASE-FAULT}` (2 + 1) | **PARTLY** — the marker exists, but only in the GATE's vocabulary and on 3 of 91,317 rows; **37** rows carry a refusal as free text instead, and the ship/dispatch path carries none |
| **successful-retry** | **0 instances** (schema-capable) | `dispatch_attempt1_rc` on **484** rows; `dispatch_attempt2_rc` on **1** (exit ≠ 0) | **NO** — the fields EXIST, but no row proves the second attempt is written when a retry **succeeds** (see H.2) |

Every `verdict=CANCELLED` row is accounted for: 121 + 25 + 20 + 16 = **182** = the whole class.

### H.2 The successful-retry class: the SCHEMA can express it, the CORPUS never exercises it

**CORRECTION to an earlier reading of this section — the retry counter is NOT missing.**
`extra.dispatch_attempts` together with `extra.dispatch_attempt{1,2}_rc` / `_err` / `_args` all
exist: `dispatch_attempt1_rc` is written on **484** rows, `dispatch_attempt2_rc` on **1**.

Measured: that one second-attempt row's run `exit` is **NOT 0**, so the corpus holds **zero**
instances of *"dispatched, failed, retried, and won"*. The fields can express it; **no row
proves the writer populates them when a retry succeeds** — an unexercised arm is not a working
arm, and a reader must not infer that it works from its presence in the schema.

So the two readings remain indistinguishable in today's corpus not because a field is absent, but
because the only second-attempt row is a failure. The missing receipt is therefore not a counter
— it is **a positive control** proving the attempt-2 fields are written on the success path.

### H.3 The receipt field that replaces manual reading, per class

| Class | Field that names it today | Where it must live after the fix |
|---|---|---|
| stale-invocation | `extra.resume`, `extra.resumed_head` | the gate receipt file (step 3) — a resumed run is a DIFFERENT tested tree |
| supersede | `verdict_reason=superseded`, `cancel-class=SUPERSEDED` | receipt + the ship journal, so a supersede is not read as a failure |
| timeout | `cancel-class=TIMEOUT` | receipt `verdict` + `verdict_reason` |
| not-established | `cancel-class=NOT-ESTABLISHED` | receipt — the tool's own "I could not establish why" must survive into the file |
| refusal | `verdict=refused` (2) / `verdict=BASE-FAULT` (1) — **gate-side only**; the ship/dispatch path carries none | a STRUCTURED refusal marker on the ship path (step 4's distinct codes) |
| successful-retry | `dispatch_attempts` / `dispatch_attemptN_rc` — **exist, unexercised on success** | receipt — plus the positive control proving the attempt-2 fields are written when a retry WINS |

### H.4 Exit-code vocabulary observed (for the rc register in step 6)

`0` (70,582) · `1` (6,401) · `2` (6,370) · `5` (2,955) · `3` (2,729) · `143` (729) · `4` (550) ·
`6` (408) · `141` (235) · `120` (118) · `7` (82) · `9` (81). Codes below 81 rows are omitted;
`127` (command not found) falls under that floor in this snapshot.

Two of these are **signals**, not decisions: **143** (SIGTERM, 729 rows) and **141** (SIGPIPE,
235 rows) — tools killed mid-flight, whose receipts are therefore missing rather than negative.
A receipt that records only "exit != 0" loses the difference between *refused* and *killed*,
which is the difference a reader cannot reconstruct.

---
