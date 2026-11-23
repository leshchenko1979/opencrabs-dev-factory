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

## D–G. CI surface, selftest inventory, historical log, dispatch classification

*(appended from the delegated read-only inventory — see below)*
