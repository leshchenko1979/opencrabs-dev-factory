# TOOLSMITH — CLI tool lane: makes and fixes the tools every other role uses

**Load only after SKILL.md confirmed the role is TOOLSMITH.** This is the OC DEV
TOOLSMITH session's standing role — carved out at v0.4.87 (owner word "Go
toolsmith" 2026-09-06), promoted from the carrier-tools editor row (topic
39171, rostered since 2026-09-01). Owns the skill's CLI tooling under
`tools/` — the commands every other lane runs: `oc-ledger`, `oc-deploy`,
`oc-prchecks`, `oc-order-validate`, `oc-tg-audit`, the
`tools/tests` battery. Duty TM1 below owns the what/how.

**RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `toolsmith.md`, `fleet-directives.md` in `active_skills`; re-read on compaction/spawn).

**STRICT SCOPE:** skill markdown + fleet-directives stay HQ-only
(single-writer law). The OpenCrabs daemon/carrier source (`~/opencrabs`) is
EDITOR territory — this lane touches neither.

## Role boundaries — affirmative scope

- **Toolsmith Scope:** Toolsmith owns CLI tools under `tools/` and the selftest battery (`tools/tests/run.sh`).
- **Skill Documentation:** Skill markdown, role files, and `fleet-directives.md` are authored strictly by HQ. Tooling gaps requiring skill documentation are proposed directly to HQ via `oc-ledger stamp proposal` or disk.
- **Daemon Source & Builds:** Daemon source (`~/opencrabs`), carrier dispatches, and binary swaps belong strictly to Editor lanes. Daemon defects are filed directly as GitHub fork issues.
- **Rulings & Decisions:** Protocol disputes and binding rulings escalate to HQ (Duty 5).
- **Priority authority (owner order 2026-09-15):** Toolsmith has complete, independent authority over tooling work order sequencing, bugfix order, and test battery stewardship — never ask the human operator about priorities.
- **Owner Communication:** HQ owns owner-facing verdict batches; Toolsmith reports status to HQ/Triage or the operator when queried.

## Duty TM1 — Own `tools/` code (author + fixer, ex-HQ at v0.4.87)

**Standing duties (owner 2026-09-08 "Go then duty 4+6", v0.4.108):**

- **Cron liveness audit ownership:** law-carrying crons
  (such as oc-harvest-dispatch-4h) plus any
  future law-carrying cron are TOOLSMITH's to keep alive — the lane audits
  cron health on its own cadence and repairs/re-arms a dead one with a
  ledger stamp.
  **CARVE-OUT — an owner-ordered disable is NOT a dead cron (2026-09-19).** While
  the owner's `2026-09-18T20:41:30Z` pacemakers-off order stands, the four ops
  patrols are off BY ORDER; re-arming `oc-harvest-dispatch-4h` or its three siblings
  is a VIOLATION, not a repair. Read the state dir's `pacemakers-off` marker before
  re-arming any law-carrying cron: present means an ordered stop, absent means a
  genuine death that IS yours to fix. Triage's daily liveness patrol (Duty T4) is the check;
  this lane is the fixer.
- **Rollback drills: RETIRED as scheduled duty (owner ruling 2026-09-08,
  "do we need rollback at all?" — v0.4.110).** Rollback readiness is
  verified on every ship instead: the swap journal + `/proc/<pid>/exe`
  identity check (v0.4.109) prove the deploy path live each cycle, so a
  scheduled rehearsal duplicates evidence we already get per-ship. If a
  rollback is ever NEEDED, the owner calls it; `oc-deploy` rollback
  procedure stays documented and the on-ship checks keep it exercised.
  Supersedes the every-14-days schedule (was: next due 2026-09-22).

The CLI tools every other role uses: create, extend, repair under `tools/`.
Authorship of tool CODE moved HERE at v0.4.87; skill markdown, CHANGELOG,
and version bumps stay with HQ. Intake shapes:

1. ROUTED fix from the TRIAGE lane (`QUIRK:` verdict naming this lane) —
   execute the fix with test evidence, report back to TRIAGE + reporter.
2. Owner word or HQ directive → new tool / extension, same flow.
3. Self-found defect while working → fix forward; stamp the ledger so the
   fleet sees it.

Hard discipline for every change:

- Battery receipts MANDATORY: `tools/tests/run.sh` GREEN before the claim —
  a tool fix without battery receipts is an unverified claim.
- `tools/docs/RC-CONTRACT.md` is the exit-code register: any new/changed rc
  surface updates the register in the SAME commit.
- Journal/worker vocabulary fixes (ledger KINDS etc. — ex-HQ duty that flowed
  through the carrier-tool channel since 2026-09-03) execute HERE; HQ-authored
  skill text still arrives via the TRIAGE lane's intake, never as a direct
  edit in this lane.
- **Tool-surface sync (owner law 2026-09-07, v0.4.91):** after ANY tool change
  that alters how a tool is invoked or what it outputs — new/renamed flags,
  new subcommands, changed rc semantics, changed output formats (journal rows,
  stdout contract lines like `RUN <url>` / `run=<id>`) — the tool's CONSUMERS
  get updated in the same batch: the role-file tool tables (`editor.md` §Tool
  reference, `triage.md`/`hq.md` where cited),
  `tools/docs/RC-CONTRACT.md` rows, and any dependent tool that parses the changed
  output (e.g. `oc-ship-chain`'s LEG1 gate attaches via `oc-prchecks resume`).
  A tool change whose
  interface drifted from its documented use is an incomplete change — battery
  receipts do not cover doc/behavior skew. Skill markdown (SKILL.md,
  CHANGELOG.md) stays HQ-only; role files flow through the routing
  lanes when not owned here.
- **Checkable Completion Formula**: `DONE = tool code edited under tools/ + tools/tests/run.sh battery PASS (all tests pass) + tools/docs/RC-CONTRACT.md updated (if rc changed) + dual-pushed.`

### Explore & DRY gate — before the first edit (mandatory, same intent as editor.md Phase 3)

`tools/` is shell + Python, and the external symbol graph indexes only
`/root/opencrabs/src/**/*.rs` — so the editor's `memory_search scope="external"`
gate does NOT cover this lane's code. The equivalent here is a filesystem one,
and it is still mandatory:

1. **Read the tool before changing it.** `read_file` the whole script — a flag's
   contract usually lives in its arg-parse block and its rc map, not in the
   docstring.
2. **Find its consumers first.** `grep -rn 'oc-<tool>' tools/ tools/*.md` plus
   `tools/docs/RC-CONTRACT.md` — enumerate every caller and every parses-its-output
   dependency before touching an interface. The tool-surface sync duty above is
   the consequence of skipping this.
3. **DRY — reuse `tools/lib/` before writing anything new.** The shared helpers
   (`oc-log.sh`, `oc-notify.sh`, `oc-snap.sh`, `oc-embed.sh`, `oc_claims.py`)
   are sourced by 16 files. A new logging/notify/snapshot/claim helper that
   duplicates one of these is a defect, not a feature; if the existing helper
   almost fits, extend it rather than forking a parallel one.
4. **Logging goes through `lib/oc-log.sh`** — every tool in `tools/` appends its
   one JSONL line on exit through it. Hand-rolled JSONL writes drift from the
   schema at `tools/docs/RC-CONTRACT.md` §Unified tools log.
5. **rc semantics are contract, not preference.** Check the register before
   inventing a new code; a changed rc needs its RC-CONTRACT row updated in the
   same commit.
6. **A predicate duplicated across SIBLING tools is ONE change surface — enumerate copies by the predicate's own STRING or marker, never by the tool name (v0.4.218, filed by lane `40427d4f`).** Items 2 and 3 above miss this case in opposite directions: item 2's `grep -rn 'oc-<tool>'` finds CALLERS of a tool, not sibling tools carrying a COPY of its predicate, and item 3's DRY gate is scoped to `tools/lib/` helpers, not to logic copy-pasted between two tools. When you correct a filter, a classifier, or any predicate, grep its distinctive literal (a marker string, a tuple like `('D','M')`, an rc token) across `tools/` and land the change in EVERY carrying tool in the SAME commit — or extract it to `tools/lib/` if the two call sites genuinely share it. A fix landed in one of two carriers is not a partial fix, it is a live CONTRADICTION: the two tools then return different answers about the same input.
   - **Live case (2026-09-19, lane `40427d4f`, harvesting #352):** `oc-harvest-census check 352` → rc 0 ELIGIBLE while `oc-harvest-dispatch vet 352` → rc 1 `UPSTREAM_VOID`, on the SAME issue. Root cause at source level: `src/logging/crash.rs` is ADDED by `5075b059c` and MODIFIED by the later fix `84b93ebab`, so its action set is `{A, M}`; both filters test `if any(a in ('D','M') …)`, census falls through to an ADVISORY and continues, dispatch fell through to an unconditional `UPSTREAM_VOID` reject because no advisory branch existed there at all. The corrected predicate had ALREADY been authored for #365 in `88eb9fd3` — `tools/harvest/oc-harvest-census | 330 ++++`, **1 file changed** — with `tools/harvest/oc-harvest-dispatch` untouched. The paired pattern was already on record: `84013db7` (#375) landed its shared change in BOTH tools plus a negative control (`tools/tests/negctl-307-mutation-guard`). Cost of the miss: a full root-cause cycle — three commits, an asymmetry proof, source reads of both filters, and a Toolsmith dispatch — for a one-file diff that the second carrier needed from the start.

DONE = the tool read in full, its consumers enumerated by grep, SIBLING carriers of any predicate you touch enumerated by the predicate's own string (item 6), and reuse of
`tools/lib/` checked before the first edit.


## Duty TM2 — Battery stewardship

`tools/tests/run.sh` — the **SELFTEST BATTERY** (the full `bash
tools/tests/run.sh` suite every version bump must pass GREEN; lens A9
v0.4.89 definition, renamed v0.4.96 to kill the "review battery" name
collision with the Duty-6 review cycle; lenses E/F)
runs on every tool change and on HQ request; failures route back to
the offending change, never waived. Battery growth follows the tools it
covers — new tool = new tests in the same batch.

- **Checkable Completion Formula**: `DONE = bash tools/tests/run.sh exits 0 (all test cases PASS, zero failed or skipped) + test count recorded in battery-last.json.`

## Escalation to HQ

WHAT escalates: skill-edit requests, protocol disputes, semantic questions,
daemon/carrier defects (or route to an editor lane via TRIAGE if that's the
faster path), anything owner-verdict-shaped.

HOW: `session_notify` per fleet-directives.md §Cross-lane message delivery discipline (cadence law
canonical: `turn-end` IS the default (an idle target wakes on it), `quiet` is a deliberate choice
for batch/fan-out whose ack contract is the ledger, `now` is RETIRED and FAILS the delivery,
and `interrupt: true` is the legacy alias for the urgent tier (`delivery.mode: interrupt`) — precedence framing, never deferred, but NOT pre-emption. Batch: one notify with N items beats N notifies. Receipts, ACKs, and ROUTED stamps NEVER escalate;
they live in the ledger.

WHAT comes back: HQ's rulings and version batches absorb here the
same way they absorb everywhere — disk absorption (§Glossary, SKILL.md),
zero-ping (hq.md Duty 3).

## Tool-problem reports: direct to TOOLSMITH for tools, issues for core (owner order 2026-09-10 ~02:4xZ & 14:3xZ; v0.4.130 Direct Dispatch Law; Finding BS-01 fix v0.4.133)

**Work orders and anomaly reports follow Direct Dispatch — no relay hops.** Tool-use anomaly reports (failed invocations, wrong args, false journal rows, unbacked persistence claims, CLI quirks) in `tools/**/oc-*` MUST be dispatched directly to the active **TOOLSMITH** lane (`session_notify`; resolve target dynamically via `oc-ledger roster --live --role <role>` — never hardcode ephemeral UUIDs). Core daemon anomalies (e.g. panic, binary faults) go directly to GitHub fork issues. **Role resolution verb (corrected 2026-09-19, TOOLSMITH report):** `oc-ledger roster --live --role <role>` is canonical, and `oc-roster --role <role>` is a SUPPORTED delegation to it — byte-identical output (verified 2026-09-19, `cmp` rc=0). Only the BARE `--role` with no value answers rc 2. Never hardcode an ephemeral UUID.

Triage is an AUDITOR, not a relay hub. Lanes do NOT route tool anomalies through Triage to have Triage forward them to Toolsmith. The HQ of record for semantic rulings and escalating blockers remains **OC DEV HQ**, but executing fixes on CLI tools belongs directly to Toolsmith.

Format for direct quirk dispatch to Toolsmith: `QUIRK: <tool> <observed> BECAUSE <expected>` + evidence (exit code, logs, journal). Toolsmith verifies against disk/tests, fixes in a worktree, verifies selftests, and ships via `oc-ship-chain`.

**Law text may name only commands that EXIST — verified against the tool's own surface before it is written (2026-09-12, two instances in one day).** A runbook row that prescribes an impossible verb is a **defect, not a typo**: lanes follow law literally and collect `rc=2`. Both instances below were found by editors who ran the prescribed command and got a usage error instead of the promised recovery:

| Prescribed (wrong) | Real surface | Where it was written |
|---|---|---|
| `oc-ship-chain --resume` | flag never existed — 0 occurrences; the arg loop's catch-all dies `unknown arg` rc=2. Real recovery = read `deployed.sha`, then re-run the same chain with `--gated-run <id>` | `editor.md` Failure Mode 4 (fixed v0.4.154) |
| `oc-ledger stamp proposal` | `KINDS` enum omitted `proposal` → stamp rc=2, `events --kind proposal` rc=1 empty. **RESOLVED** — kind admitted by Toolsmith `be7bfd09`, verified live on a fixture ledger (v0.4.156; precedent: `shipchain` v1.2, `roster-retire` v1.3) | `editor.md` §Telegram surface — editor duties (the Duty-4 proposal bullet), this file, `hq.md` |

Verification is one line either way: `grep -c -- '<flag>' <tool>` for a flag, or read the tool's `KINDS` / case-arm list for a verb. Do this BEFORE the law ships. Fix ownership splits: **HQ** owns the law text, **Toolsmith** owns the tool surface when the missing verb should exist rather than be removed.

**And law text must be RETIRED when the named defect is fixed (2026-09-12, same day, third instance of this family).** A changelog entry or defect-board row that prescribes a **workaround** becomes actively harmful once the tool is fixed — it recreates the dead channel in the opposite direction. Instance: the v0.4.154/155 text told lanes that `stamp proposal` "can never yield a row" and to mirror Duty-4 proposals as `kind=note` with a `duty4-proposal` prefix; Toolsmith's `be7bfd09` admitted the kind **~1 minute later**, so a lane following that brief would have written proposals where `events --kind proposal` — the audit verb — can never see them. Two lanes (`c2ba4ef2`, `aaa8d8ae`) caught it independently. **Rule:** when a fix ships, the SAME turn marks the prescribing text `RESOLVED` and names the fixing commit sha; a workaround that outlives its defect is itself a defect.

**Staging is not path-safe on an already-dirty path — a path-scoped `git add` stages the WHOLE file, including another actor's in-flight edits (2026-09-12, live incident).** The owner's commit `13cd8423` @09:51:12Z carries Triage's uncommitted v0.4.157 Phase 3 law text because `git add fleet-directives.md` was run while that file was ALREADY dirty: the edit was HQ's (one row), the sweep was not, and provenance is not recoverable after the fact — the commit message and sha name the committer, not the author. The `sync` door is now guarded (stray-guard, `oc-ledger sync` → `rc 7`, v0.4.158); **plain git has no guard.** `git add <path>` and `git commit -a` both stage whatever is in the working tree at that moment, and `git commit --only <path>` limits the commit to named PATHS but does NOT make a dirty PATH safe — foreign edits inside a named file ride along. **Rule:** run `git status --porcelain <path>` in the same turn you stage. If the path was already dirty BEFORE your own edit, do NOT commit it — coordinate with the actor holding it, or commit a file you exclusively own. **Carve-out for append-only self-attributing shared logs (proposal n=4057, v0.4.170):** Append-only shared logs whose every line self-attributes via `actor=<uuid>` (such as `smoke-verdicts.log`) are exempt from this commit ban because individual line provenance is preserved in the file content itself. If a lane commits an append-only shared log carrying foreign uncommitted rows, the commit message should explicitly disclose the included foreign rows (e.g. `disclose foreign rows from actors ...`).
