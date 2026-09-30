---
name: opencrabs-dev
description: >
  OpenCrabs source ops (~/opencrabs): roles EDITOR (fork issues, per-task
  worktrees, CI gate (pr-checks), signed commits, push + sha hand-off, oc-deploy ship,
  smoke-test-on-notify), HQ (skill set + worker ledger),
  TRIAGE (interrupt lane: fix routing, enforcement — carved out of HQ at v0.4.86),
    TOOLSMITH (CLI tool lane: owns tools/ — makes and fixes the CLI tools every other role uses — carved out at v0.4.87),
    HARVEST (upstream contribution lane: ports a READY cluster, gates it, files the upstream PR and owns its lifecycle — carved out at v0.4.250); Compiler role retired 2026-08-28).
  Use when editing/fixing OpenCrabs Rust code, debugging quick-build-linux carrier or other CI runs, fetching CI artifacts, or swapping /usr/local/bin/opencrabs.
  (/opencrabs-dev)
globs:
  - ~/opencrabs/**
  - ~/opencrabs-wt/**
  - ~/.opencrabs/profiles/*/skills/opencrabs-dev/**
  - ~/.opencrabs/profiles/*/opencrabs-dev/**
  - ~/.opencrabs/profiles/*/projects/opencrabs-dev/**
version: 0.4.274
author: leshchenko1979
metadata:
  tags: [opencrabs, rust, ci, quick-build, binary-swap, worktree, session-notify]
  references:
    - https://github.com/adolfousier/opencrabs (upstream — PRs only; new issues NEVER filed here)
    - https://github.com/leshchenko1979/opencrabs (fork — push target + ISSUES HOME)
  provenance:
    - "Release history and the current version live in CHANGELOG.md (git-tracked, newest-first). The v0.4.43 B6 rationale is in war-stories.md."
---

# opencrabs-dev — OpenCrabs source procedure

**Owns:** everything touching `~/opencrabs` source, its GitHub Actions runs, or the
installed `opencrabs` binary. This file = shared facts + role router only. Actual
procedures live in FIVE role files (`editor.md` / `hq.md` / `triage.md` / `toolsmith.md` / `harvest.md`);
load ONLY the one matching the session's role.

**Binding owner directives** (sync policy, upstream PR law, carriers/builds, cargo
prohibition, telegram surface law, gates, editor creation, tool-problem triage (Triage lane),
cadence) live in `fleet-directives.md` — re-homed from ops AGENTS.md/MEMORY.md per
owner order 2026-09-02. Load it before ANY opencrabs-dev work. Executing procedure for the sync
policy's rebase procedure: `upstream-merge-runbook.md` (freeze gate, roles, conflict
classes, migration-union rule, semantic-triage defaults).

## STEP ZERO — establish the role (mandatory on every load)

Ask the operator which role this session employs before doing anything:

> **Editor / HQ / Triage / Toolsmith / Harvest?**

| Role | Owns | Procedure file |
|------|------|----------------|
| **EDITOR** | Commits + error fixes: claim issue → worktree → code → CI gate → sign → push → ff-merge into fork `main` → `oc-deploy ship` → smoke on notify. **The editor's obligation ENDS at smoke evidence** — feature COMPLETE means the evidence is posted and the feature is handed to the HARVEST lane | `editor.md` |
| **HQ** | Skill set maintenance, worker ledger, Duty 4 worker polls, Duty 6 periodic lens reviews — count derived from the catalog at gate time (details in `hq.md` and `review-lenses.md`) | `hq.md` |
| **TRIAGE** | Intake & hygiene: issue assignment, repo hygiene patrols, rebase/merge execution delegated from HQ, upstream lifecycle tracking (delta watch, PR census, dependency tracking folded from Harvester v0.4.176) | `triage.md` |
| **TOOLSMITH** | CLI tools author & maintainer: owns `tools/` code, test battery stewardship, direct recipient of tool quirks/defects (v0.4.176) | `toolsmith.md` |
| **HARVEST** | Upstream contribution: port → CI gate → file → follow. Consumes a cluster Triage surfaced and marked READY; owns the harvest branch, the gate dispatch, the upstream PR and its lifecycle (v0.4.250, owner order 2026-09-24 centralising harvest) | `harvest.md` |

Roles **DO NOT intersect**:

- The Editor NEVER installs/swaps binaries, NEVER restarts daemons, NEVER dispatches
  BUILD runs — shipping goes through `oc-deploy ship` (S3). BUILD TRIGGERS = exactly
  TWO with NO exceptions (§Hard rules, A3 ruling 2026-08-29); the Phase-7 PR-head
  gate is the step-2c pr-checks dispatch — a lint/test gate, not a build trigger.
- Hand-off point: the Editor produces (branch pushed AND fast-forwarded into fork
  `main` + reported shas); `oc-deploy ship` takes it from there (dispatch → poll
  → swap-execute, consent eliminated 2026-08-28). If the run is RED, `oc-deploy`
  reports evidence and stops — fixing code is always Editor work.
- The TRIAGE lane NEVER edits skill files (single-writer law unchanged — the
  HQ is the sole author), NEVER settles protocol disputes (rulings =
  HQ Duty 5), NEVER executes builds/swaps (strict routing, triage.md).
- The TOOLSMITH lane owns `tools/` CODE only (v0.4.87 carve-out) — skill markdown +
  fleet-directives stay HQ-only, daemon/carrier source stays Editor territory,
  NEVER settles protocol disputes (rulings = HQ Duty 5).
- The HARVEST lane owns the upstream PR lifecycle ONLY — it NEVER edits skill markdown (HQ-only), NEVER installs/swaps binaries, NEVER restarts daemons, NEVER dispatches builds, NEVER settles protocol disputes (rulings = HQ Duty 5).
- **The EDITOR's obligation ends at smoke evidence.** Harvest census, porting, upstream branch creation, PR filing and upstream lifecycle belong to the HARVEST lane — an editor lane that finds itself harvesting has taken work it does not own.
- **PRIORITY AUTHORITY (owner order 2026-09-15):** ALL lanes (Editor, HQ, Triage, Toolsmith, Harvest) have complete, independent authority over priorities, sequencing, and task ordering within their codified scopes — never ask the human operator about priorities.

If the request mixes roles (e.g. "fix X and deploy it"), split into separate
role loads — do not fuse the roles in one pass without Alexey saying so explicitly.

## Canonical tooling (v0.4.12, PROCESS-TOOL ownership)

Mechanical rituals the roles once hand-ran are now single commands in `tools/` (CLI-tool creation/fix is
the TOOLSMITH lane's scope, v0.4.87). This section is the register; archived compiler-step anchors live at
`tools/archive/compiler.md`. Fleet-wide rc conventions + the FULL per-tool rc register (the SOLE register):
`tools/docs/RC-CONTRACT.md` (lens A H1/B F1, v0.4.79; rows below carry purpose only):

**Directory layout — one level per KIND (v0.4.254):** `tools/` holds the `oc-*` fleet executables (the public interface) grouped ONE LEVEL PER FUNCTION — `audit/` `git/` `harvest/` `issue/` `notify/` `ship/` `smoke/` `state/` — beside `tools/lib/` shared helpers, `tools/tests/` the battery, `tools/archive/` retired tools, `tools/docs/` the law that documents the tools, and **`tools/instruments/` corpus-agnostic analysis tools that are NOT fleet tools** — an instrument that reviews an arbitrary corpus has no place in the `oc-*` namespace, and lands there instead.

| Tool | Slot |
|---|---|
| `./tools/ship/oc-order-validate <sha>` | ORDER gates inside `oc-deploy ship` |
| `./tools/ship/oc-job-verify <run-id> <source-ref> [--features] [--identity-only]` | standalone run-identity gate (provenance of RED runs) |
| `./tools/ship/oc-artifact-verify <artifact-path> [--source <sha>] [--run-id <id>] [--markers m1,m2] [--expect-sha <sha256>] [--expect-version <v>] [--repo R] [--json]` | EXECUTION SANITY SIGNAL + FEATURE-PRESENCE CHECK |
| `./tools/ship/oc-seal-state [--sha S] [...]` | baseline/orders seal (flag-based interface — no positional `<sha>`) |
| `./tools/state/oc-attrib --repo <path> (--range <A..B> or --deployed) [--ledger <f>] [--contributors] [--novel\|--no-novel]` | commit-range → worker-lane attribution; `--contributors` projects the 3-col TSV (SINGLE SHAPE); `--deployed` composes the range from `deployed.sha` + `prev_sha` (fan-out compute backend for [issue #24](https://github.com/leshchenko1979/opencrabs/issues/24)) and IMPLIES `--novel` (#407: drops re-sha'd + empty commits; `--no-novel` restores the raw range) |
| `./tools/ship/oc-deploy <mode>` | the ship path itself — `ship` / `poll` / `swap-execute` / `status [--json]` / `watch [--with-delta]` / `fanout` / `contributors` RETIRED (use `oc-attrib --contributors`). Editor S3 path: `editor.md` §Ship. Verdict codes + wait semantics: tools/docs/RC-CONTRACT.md |
| `./tools/ship/oc-deploy fanout --run <id> [--dry-run]` | mechanical notify fan-out for one carrier run ([#24](https://github.com/leshchenko1979/opencrabs/issues/24)); auto-fired at `swap_execute` tail + on `poll` RED-scan; `OC_DEPLOY_NOFANOUT=1` suppresses — mechanics + journal vocabulary in `s2-swap-journal-spec.md` §Fan-out legs |
| `./tools/ship/oc-carrier-features [--fetch] [--repo <path>] [--ref <branch>]` | reads the carrier-yml `features` default at `origin/<ref>`; `oc-deploy ship/poll` resolves EMPTY `--features` through this — carrier read failure aborts the ship loudly |
| `./tools/issue/oc-issue-sweep '<query>' [--fork R] [--upstream R] [--limit N]` | closed-issue hygiene sweep (HQ duty) |
| `./tools/state/oc-skew-scan [--ledger f] [--current v]` | ledger worker-version skew vs current skill version (HQ roster review) |
| `./tools/notify/oc-ping-proof <uuid> <ping-ts> [--ledger f]` | post-swap notify proof: WOKEN / SILENT / UNREACHABLE verdict |
| `./tools/harvest/oc-pr-atomicity <pr-number>` | atomicity gate (harvest Phase 7 / issue triage) |
| `./tools/state/oc-ledger <verb>` | workers-ledger: stamp/sync/check-version/cadence/ack/enroll/roster/commit-pending/claim-ref/claims/duplicates/confirm/events — `--verbs` lists registered subcommands; unrecognized verbs emit vocabulary hints; `roster --live --role <role>` is the ROLE-RESOLUTION verb; the `oc-roster --role <role>` form delegates to it and returns byte-identical output |
| `./tools/state/oc-shadow-rotate [--dry-run]` | INTERNAL tail step of `oc-ledger sync` (standalone = manual fallback) |
| `./tools/state/oc-review-persist <lens> <text\|@file\|-> [--dir DIR]` · `check-cycle <dir> [--strict-receipt]` | persist a Duty-6 review report (the index line IS the "persisted" receipt); `check-cycle` is the cycle-close gate |
| `./tools/smoke/oc-smoke-evidence [--unit opencrabs-ops] [--markers m1,m2] [--negative-control <bin>] [--append-log [<path>]]` | mechanical identity + presence evidence for a Phase 6b smoke verdict; behavioral judgment stays human; `--append-log` is the SANCTIONED writer of the **IDENTITY EVIDENCE BLOCK** in the canonical `smoke-verdicts.log` — the VERDICT ROWS are LANE-AUTHORED (see `upstream-merge-runbook.md` §Upstream-merge cadence · HARVEST LAW · NO-HOLD); bare = the canonical absolute, a wrong path is unrepresentable (M2-2) |
| `./tools/issue/oc-issue-log <issue-n> <sha> [--state <text>] [--repo <slug>] [--dry-run]` | per-commit implementation comment via gh `--body-file` ONLY |
| `./tools/git/oc-commit -m <msg> [--issue N] [--no-comment] [--state <text>] [--repo <path>]` | gated commit wrapper: derives `Issue-Ref` from the actor's latest ledger claim, adds Session-Id + Issue-Ref trailers, folds in the post-commit comment |
| `./tools/ship/oc-ship-audit [--hours N] [--log f] [--journal-dir d] [--grace min]` | dispatch-WITHOUT-swap alarm |
| `./tools/audit/oc-tg-audit <uuid> [--date D] [--days N] [--log-dir P]` | Telegram surface-law evidence scan |
| `./tools/state/oc-ledger sync` CHANGELOG gate | the sync refuses a bump whose CHANGELOG entry is missing (die 6) and WARNS on bundled commits the entry does not name. Full register: `tools/docs/RC-CONTRACT.md` |
| `./tools/harvest/oc-harvest-census <scan|check|record|sync>` | pre-flight census & lifecycle registry for upstream PR harvests; prevents duplicate/colliding PRs. `record` appends to `manual_records`, which `check` CONSULTS before declaring a unit unharvested — rc 1 `REFUSED … manually recorded as filed in PR #<n> (unit <u>)` — and the registry write MERGES into the loaded dict so foreign keys survive. Use `check`/`scan`, which derive IN_FLIGHT from the live scan |
| `./tools/harvest/oc-harvest-dispatch vet <issue-or-commits>` \| `dispatch <issue> <commits> [--dry-run]` | dispatches automated harvest-to-upstream work order for eligible features |
| `./tools/harvest/oc-harvest-sweep <pr-branch> [--base adolfousier/main] [--repo P] [--port-of sha1,sha2]` | pre-gate harvest verification (harvest Phase 7 sweep, mechanical legs); behavioral judgment stays human |
| `./tools/state/oc-health [--class <name>|--all] [--rotate] [--status] [--json] [--reap] [--quiet] [--selftest]` | 8-class rotating fleet health & cleanliness sweep (owner order 2026-09-11); spec + per-check remediation in `tools/docs/HEALTH-CLASSES.md` & `tools/docs/HEALTH-CHECKS.md`. `--reap` applies SAFE remediations only; without it the tool is a pure read |
| `./tools/state/oc-roster --selftest` | hermetic test runner for roster generation and classification |
| `./tools/audit/oc-watcher-audit [--json] [--notify-orphans]` | detached watcher compliance and sleep-loop audit across active sessions |
| `./tools/git/oc-start <issue-N> --branch <branch>` | unified entry: claim + branch + worktree initialization |
| `./tools/smoke/oc-smoke <issue-N> [--probe <cmd>] [--no-ledger]` | unified 4-leg smoke verification & verdict row logging + automatic ledger done stamp on PASS |
| `./tools/issue/oc-issue-dispatch [--auto]` · `<issue-number> [--to <uuid>] [--force] [--allow-landed] [--redispatch] [--budget-secs N]` | mechanized issue triage dispatch to idle editor lanes; the issue is POSITIONAL and `--to` names the target session — there is NO `--issue` or `--lane` flag (verified live 2026-09-25 against the tool's own `--help` and `tools/docs/RC-CONTRACT.md` row 36). `--force` overrides the claim gate, `--allow-landed` disables the landed filter, `--redispatch` disables the 7-day dedup window |
| `./tools/state/oc-questions <verb>` | the Open Questions register — the sanctioned blocked-on-you channel. Verbs, rc and the ask/answer contract: `tools/docs/RC-CONTRACT.md` row 49 · canon: `docs/instruments/open-questions.md` |
| `./tools/audit/oc-lint-laws [--strict]` | mechanical syntax & tool-existence lint of skill markdown. Read findings from the tool itself, never from this row. Register: `tools/docs/RC-CONTRACT.md` |
| `./tools/audit/oc-claims-single-source [--scan DIR] [--selftest]` | battery guard: the claim-closure predicate has exactly ONE home (`tools/lib/oc_claims.py`) — fails the battery on a re-added private copy under `tools/`. Keys on the re-implementation SHAPE, never on a name (the two copies it exists to prevent were called `claims_index` and `claim_is_closed`, so a name-keyed guard misses both). Scan units include embedded `python3 -c` / heredoc blobs, not only whole files. rc register: tools/docs/RC-CONTRACT.md |
| `./tools/harvest/oc-prchecks <branch-or-sha> [--wait N]` · `resume <run-id>` | one-command CI gate on a PR-lane branch; `resume` re-attaches to a run this lane witnessed. Register: `tools/docs/RC-CONTRACT.md` |
| `./tools/harvest/oc-upstream-delta [--repo P] [--fork-origin R] [--upstream R]` | watch-cycle arithmetic; READ-ONLY — PROPOSE/WAIT judgment stays human |
| `./tools/git/oc-wt add\|remove\|list` (`--force` is a flag on add/remove) | editor worktree manager (`--force` journals before removal) |
| `./tools/state/oc-drift-check <uuid> [--ack]` (omit-arg canonical; legacy `<uuid> <claimed-ver>` accepted) | editor §Mid-cycle skill drift step 1-2, mechanical |
| `./tools/git/oc-branch-sweep --repo <p> [--dry-run]` | branch-death proof + archive-then-delete for MERGED only |
| `./tools/issue/oc-census` | READ-ONLY pending-branch census (sync runbook Step 7 step 0): decomposes each branch's `git cherry <base> <b>` `+` set into its three arms (own-lane trailer / no trailer / foreign-lane trailer) and ENFORCES the partition identity `plus_total == plus_own + plus_untrailered + plus_other` — a row that fails to add up is an internal error, never a silently-wrong number. A non-zero aggregate `+` is NOT proof of pending work, so it splits the aggregate and runs a CONTENT leg rather than trusting either. Prints counts and the base, never a cut sha. rc register: tools/docs/RC-CONTRACT.md |
| `./tools/harvest/oc-pr-fault-scope <pr#> --run <id>` | failing-files ∩ PR-files = IN-SCOPE/BASE-FAULT |
| `./tools/state/oc-ledger confirm <uuid>` | verifies the worker's latest claim then flips workers[].confirmed=true |
| `gh workflow run pr-checks.yml --ref ci/quick-build-linux -f ref=<branch-or-sha>` | **manual fallback — prefer `./tools/harvest/oc-prchecks`** (row above). PR-lane CI gates before an upstream PR; yml lives only on the carrier branch |
| `./tools/audit/oc-log-search <pattern> [--log-dir <P>] [--date YYYY-MM-DD] [--since <ts>] [--module <re>] [--tail N]` | telemetry-only daemon-log search; HARD FENCE: `brain::provider` lines never match |
| `./tools/ship/oc-ship-chain --sha S --branch B` | CI gate → issue-log → ff-merge → ship → swap in ONE invocation; no-self-ping |
| `./tools/notify/oc-notify-fanout --title T` | per-lane skill-change brief generator; DB-validated forum-scoped targets, receipts + ledger stamp |
| `./tools/git/oc-rebase-safety overlap\|audit` | re-gate split rule arithmetic |
| `./tools/state/oc-roster <live\|forum\|claims\|work\|classify>` | the DERIVED in-progress roster (claim events + worktree state + session liveness + bindings); stores nothing. `--role <role>` delegates to `oc-ledger roster`. |

Tests: `tools/tests/run.sh` — one command, exit 0 only if all pass (the SELFTEST BATTERY — tool
selftests, distinct from the CI-gate CODE TESTS cargo triad). Must stay green before any version
bump; tools are never edited without re-running it.

### Unified tools log

Every tool in `tools/` appends ONE JSONL line on exit. Path, schema, suppression
rules and verified jq recipes: **`tools/docs/RC-CONTRACT.md` §Unified tools log** (sole home).

## Session-notify loop (since v0.3.3)

Editors live in a Telegram forum group: one topic = one editor = one live session = ONE feature.

- **TOPIC NAMES stay in sync with their lane, are `<Area>: <Qualifier>`, and are
  <= 22 characters** (owner order 2026-09-25: "keep the telegram topic names in
  sync. Use short names that would fit into the UI"). A lane that REPURPOSES a
  topic renames it in the SAME turn it repurposes the lane — that pairing is the
  sync the order asks for, and its absence is what left a topic reading
  "streaming-guard-105-xfer" after the lane became the goal owner. The 22-char
  bound is where the owner's CLIENT truncates the sidebar; it was measured by the
  Triage lane on 2026-09-25 and is NOT derivable from this box, so re-derive it
  rather than assume it if the client changes. Mechanism, verified at source:
  `rename_topic` persists through `record_topic_created`
  (`src/channels/telegram/mod.rs:51`) — an append-only INSERT into
  `channel_messages`, never a read-modify-write — so parallel renames cannot
  clobber each other, and a rename keys on `thread_id`, so session bindings are
  unaffected. The live name for a thread is the NEWEST row for that `thread_id`, not any row: the table is append-only and retains every historical name.
  **THE AUTHORITATIVE NAME IS THE NEWEST `topic renamed to "<x>"` / `topic created "<x>"` EVENT ROW — NOT the `topic_name` COLUMN, which is an ECHO. `latest_topic_name()` feeds both the inbound (`handler.rs:357-363`) and outbound (`delivery.rs:621-626`) writes, so a plain message's `topic_name` is a copy of whatever was newest when it was written and can propagate a superseded name indefinitely (measured 2026-09-27, t34653: `Compaction visibility` carries **0** rename/create events — it was never a rename target — yet was the newest `topic_name` at 12:50:16Z, two days after the event stream renamed it to `Memory: Compaction`). Read the column and you can be pushed backwards off a correct answer; read the events and t49643's live name is `Core: Skills` where its column echoes `Skills`. `sessions.title` is a bind-time label that does not follow renames at all, and `session_bindings` has no name column. Never re-type a name: emit it from the event row.**

- Every Editor commit carries a git trailer: `Session-Id: <full session uuid>`
  (`git commit --trailer "Session-Id: <uuid>"`). FULL uuid — the 8-char display
  form cannot drive routing. Each session READS ITS OWN UUID straight from its
  runtime prompt/session context — no lookup tool needed (correction
  2026-08-25); the post-swap fan-out takes notification targets from these
  trailers (`oc-attrib`; `oc-contributors` RETIRED v0.4.72 — E2 #1, subset of oc-attrib, zero live callers).
- After a healthy swap the fan-out is MECHANICAL: `oc-deploy fanout`
  (auto-fired at the `swap_execute` tail since v0.4.37,
  [#24](https://github.com/leshchenko1979/opencrabs/issues/24)) attributes the
  shipped range and notifies each contributing editor — an editor's job on
  notify is the smoke test (bullets below). GREEN/RED leg internals, range
  math, blame attribution, journal vocabulary: `s2-swap-journal-spec.md`
  §Fan-out legs (re-homed v0.4.80, lens B F4).
- Editors own testing THEIR features on notification: SMOKE TESTS against the
  swapped binary running on this box (the cargo ban itself = editor.md §Box law, one
  statement). Failures funnel back through blame attribution
  (issue #24: `oc-attrib` over Session-Id trailers — mechanical via
  `oc-deploy fanout` since v0.4.37),
  which asks the guilty editors for fixes.
- Separation holds inside the loop: the fan-out notifies + attributes but NEVER
  fixes code; Editors fix + re-push but NEVER attribute others' failures.

### session_notify mechanics — see `session-notify.md`

The `session_notify` TOOL mechanics (same-process scope, delivery-vs-queue-acceptance,
sender identity, per-surface rate limits, refusal handling, the CLI form, and the
`from`-is-a-return-address rule) live in **`session-notify.md`**. The delivery LAW is
canonical at `fleet-directives.md` §Cross-lane message delivery discipline.


### Telegram surface law (v0.4.31)

Inter-role communication is **session_notify ONLY**. No lane ever uses telegram send/edit tools to talk
to another session, another role's topic, the forum General area, an unrelated chat, or the owner DM.

- An Editor's surface is ITS OWN TOPIC and nothing else; normal replies auto-route there as session
  text, the ONLY sanctioned output. Editors NEVER invoke send/edit telegram tools (`telegram_send`,
  `tg_send_message`, `tg_edit_message`, `telegram_edit`) — not even into their own topic; no
  `tg_search_global`/cross-chat reads; `tg_get_messages` limited to the own topic. Reactions are
  allowed (owner consent signal).
- Sanctioned senders (NOT editors — none of this is lane-to-lane): the task-queue skill's documented
  `/tq-approve` flow; alerting lanes reporting to the owner DM per the ops runbook; HQ's session text.
- Violation pattern for HQ: a TOOL_ACCUM row showing an editor lane calling a telegram send/edit
  tool → session_notify the rule; second offense → review toggled.

## Test ontology (v0.4.2 — three kinds + one sanity signal, NEVER conflate)

| | SMOKE TEST | CODE TESTS | FEATURE-PRESENCE CHECK |
|---|---|---|---|
| Answers | does my feature WORK for a user right now? | is the code correct by analysis standards? | is the feature actually INSIDE the artifact we are about to deploy? |
| What | behavioral drive of ONE shipped feature | compile/run verification: cargo fmt, clippy, cargo test | static markers: binary strings/symbols, sha256 identity vs artifact, source-tree grep |
| Where | live `opencrabs-ops` unit, its real surfaces (Telegram, cron, MCP) | GitHub Actions ONLY — the CI gate (`pr-checks.yml`; upstream's own checks on PRs). Carrier build COMPILES the artifact but runs NO test leg (removed 2026-08-31, `e71dba58`) | this box, against the DOWNLOADED artifact + its source tree — nothing running |
| When | after a swap notify (`editor.md` Phase 6b) | pre-flight gate before PRs/ff-merge (Phase 7 step 2c) — `pr-checks.yml` is the ONLY CODE-TESTS locus | pre-swap, every cycle (`oc-deploy` swap path) |
| Who | owning Editor | Editor dispatches the gate and reads conclusions; `oc-deploy` reads build conclusions | `oc-deploy` swap path (pre-S3: Compiler alone) |
| Toolchain | none — local cargo FORBIDDEN in any form (binaries disabled 2026-08-28; editor.md §Box law — canonical, other files reference "(box law)") | CI's own — never local | `strings`, `sha256sum`, `git grep` — none compile anything |
| Evidence | one line: drove X, observed Y (+ run id / sha) | job/step conclusions read via API | marker found/not-found + checksum line in baseline.json |
| On FAIL | issue FIRST, then evidence to the HQ lane (`session_notify`) | fix before merge / PR | NO swap — feature missing from build; regression stated plainly |

The table above carries the ontology. **The smoke-verdict rules and their incident history —
presence-is-not-behaviour, the live-verification stamp for live-testable UX, bookkeeping-legs-are-not-a-pass,
the owner-dependent leg's PARK disposition, the no-log-probe rule for tool-description changes, leg-4
probe hygiene, and the single-sided-probe sufficiency ruling — are canonical at `editor.md`
§Phase 6b (Smoke-verdict rules).** Read them there before writing or judging a verdict.

## Glossary — official terms (v0.4.62; one concept = one name)

- **FIRE** — the release window between version bump and prod swap (editor.md
  usage, lens A8 v0.4.89). In `oc-ledger` cadence output, "FIRE" = the
  Duties-4+6 threshold verdict (≥5 bumps/5 days) — same word, different
  locus; context disambiguates.
- **carrier** — the single build lane: branch `ci/quick-build-linux` + its
  `quick-build-linux.yml` + dispatches from it. workflow_dispatch runs record
  the CARRIER ref/head, never the `-f ref` input; the carrier yml is the
  single source of truth for the prod feature set.
- **fan-out** — the automatic GREEN/RED notify fired at the swap_execute tail
  (`oc-deploy fanout`, idempotent via `fanout.state`).
- **state dir vs skill dir** — the v0.4.60 split: skill repo
  (`skills/opencrabs-dev/`, versioned code+docs) vs state dir
  (`opencrabs-dev/`, runtime). The state dir has NO tools/ — tools always
  resolve next to the invoking script.
  Its content is declared in TWO classes (v0.4.238, a RECOVERABILITY rule: a
  tracked file's only durable record is git):
  - **TRACKED** — `workers-ledger.json` · `journal/` · `oc-deploy/journal/`
    (the deploy audit trail `oc-deploy recover-receipt` reads) · the lane
    `*-state.md` records · `reviews/` · `evidence/` · `tools.log` ·
    `smoke-verdicts.log` · `deployed.sha`/`.meta.json` · `baseline.json` ·
    `fanout.state` · `base-red.json` (the BASE-RED marker store, #630) ·
    markers (`pacemakers-off`).
  - **GENERATED-IGNORED** — the generated class: `.bak`/`.bak-*` sidecars ·
    `.ledger.*` temps · `__pycache__/` · `*.pyc` · `*.lock`. Never committed,
    reaped on the hygiene cadence WITH a keep-window (a sidecar taken while its
    source was still UNTRACKED is the only copy of that reading).
  A TRACKED class's additions and updates MUST be committed by the state-repo
  commit path. That path has ONE home (#508, 2026-09-22): the `STATE_TRACKED_PATHS`
  and `STATE_TRACKED_GLOB` assignments in `tools/state/oc-ledger`, consumed by
  `state_sweep_tracked`, with a selftest asserting the single source. BOTH callers
  sweep the SAME namespace — the auto-commit tail and `commit-pending --bundle`.
  Before #508 the auto-commit staged
  `workers-ledger.json` ALONE and the sweeping verb was invoked by NO enabled cron:
  measured 2026-09-22, 345 entries had piled up on that split. Consequence for
  authorship: a class named TRACKED above is only actually swept if it is in
  `STATE_TRACKED_PATHS` — naming it here without adding it there leaves it
  accumulating while the law reads as covered.
- **single-flight** — the one dispatch/adoption lock serializing concurrent
  oc-prchecks invocations; under it, the newest carrier dispatch is this
  lane's own run.
- **CI gate** — the `pr-checks.yml` dispatch on a worktree/PR head branch:
  fmt (soft-fail) + clippy + all-features test. The ONLY code-test locus.
  Legacy synonyms "CI lint gate" / "lint gate" / "UPSTREAM CI TRIAD GATE"
  all mean THIS gate ("the triad" = fmt/clippy/test); the named rule
  UPSTREAM CI GATE (SKILL.md) is this gate run before any upstream PR.
- **ORDER gates** — the 4 pure-git pre-dispatch checks inside
  `oc-deploy ship` (SHAPE / EXISTENCE / CONTAINMENT / SIGNATURE); no cargo.
- **S2 / S3** — deploy pipeline stages: S2 = sha-bound poll + auto-swap on
  GREEN; S3 = live cutover 2026-08-28 (swap chain mechanical, consent
  eliminated). Rules saying "below S2"/"S3" mean the stage gate.
- **Lane** — one editor session (worker) owning one fork issue + its topic.
  (v0.4.89, lens A7: extended to any role session — Triage/TOOLSMITH/HQ
  lanes exist too; "lane" ≠ editor-only.)
- **disk absorption** — the v0.4.19 worker-update model: skill files are plain
  disk; workers absorb re-reads at their own boundaries (turn start, role-file
  load), no reload pings are owed or sent (defined here lens A16 v0.4.89;
  used in editor.md/triage.md/toolsmith.md).
- **Triage lane** — the interrupt lane carved out of HQ at v0.4.86 (fix routing,
  enforcement patrols — `triage.md`); never edits skill files.
- **Toolsmith lane** — the CLI tool lane carved out at v0.4.87 (owner "Go toolsmith" 2026-09-06): owns
  `tools/` code — makes + fixes the CLI tools every other role uses (`toolsmith.md`); never edits skill
  markdown. (Discover EITHER session via `session_search`, never uuid-from-memory.)
- **Roster** — the worker registry in `workers-ledger.json` (enroll / claim /
  ack rows); `oc-attrib` joins Session-Id trailers against it.
- **Lens (Reviewer A–J)** — one Duty-6 read-only review perspective
  (hq.md §Duty 6; full briefs: `review-lenses.md`).
- **HQ** — the skill-owning lane. The former name *Supervisor* is RETIRED
  (owner order 2026-09-11 folded the term into HQ — one role, one term);
  unofficial variants ("Author lane", "Carrier") seen in lane files are also
  retired — lens A-L3 v0.4.116.
- **Selftest** — a tool's built-in test mode (`oc-deploy --selftest` etc.);
  **battery** — `tools/tests/run.sh` across all tools. Both green before
  ANY version bump.
- **GREEN / RED** — a GitHub Actions run conclusion read by terminal truth
  (`gh run view --json conclusion`), never exit-code inference.
- **TOOL_ACCUM** — the per-session tool-usage rows accumulated in the unified
  tools log; evidence base for Telegram surface-law audits (triage.md Duty T4
  — ex hq.md Duty 7).
- **PARKED-OWNER-EYE** — non-blocking smoke row state (v0.4.152) stamped when
  the sole remaining behavioral evidence requires the human owner (visual pass,
  tap, UI inspection); frees the lane to continue or complete without blocking.
- **4-Leg Smoke Rubric** — the mandatory verification standard (v0.4.104) for
  shipping candidates: (1) Lineage (`git merge-base --is-ancestor`), (2) Identity
  (`oc-smoke-evidence` artifact checksum), (3) CI Gate (GREEN run on head sha),
  (4) Behavioral Probe (executing live binary path or structural N/A). All four
  must pass before an upstream PR leaves a lane.
- **issue cluster** — the harvest unit: fork-only commits grouped by their
  canonical issue ref, filtered on the ISSUE TITLE for fix-type. The dependency
  leg is the **UNION of TWO graphs** (owner ruling 2026-09-25) — the COMMIT/FILE
  graph AND the gh relationship graph — and they do NOT behave alike: only
  **1-HOP** file overlap is usable as a leg, because transitive closure collapses
  the whole delta; the gh graph is sparse and semantic but structurally weak while
  parent-linking is unenforced (13 of 55 open fix-titled clusters carry a parent).
  A set is **READY** iff (a) the most recent swap among its ready members is >24h
  ago AND (b) it has **no unready members**, where ready = swapped + smoked +
  **closed**. **THE TARGET IS EXCLUDED FROM ITS OWN READINESS SET** (HQ ruling
  2026-09-26, `n=11674`): the issue BEING harvested never gates itself; its **gh
  relatives** do. Including it was **circular** — closure is the harvest's OUTPUT
  (`triage.md:236`), never its precondition. Residual (mutually-linked pair): `upstream-merge-runbook.md §Cluster readiness`.
  Defined by `tools/harvest/oc-harvest-census clusters`, which derives it and emits
  every cluster (never pages silently); the soak gate keys on it and Triage surfaces
  by it. NOT "convergence cluster" (a Duty-4/6 group of rule proposals merged
  into one law change) and NOT a retired freeze T-group (the register was
  removed 2026-09-24); the bare word "cluster" in harvest law always means
  this one.

- **upstream-rooted** — a fix whose surface upstream shipped and we inherited; its ROOT is an upstream object
  (`--root upstream:<sha|PR|path>`, which must resolve), not a fork feature issue. Declared, never "an orphan".

## Red-run triage heuristics (shared core)

ONE location: `editor.md §Red-run triage heuristics`. Read by the editor in its fix round and by
HQ in RED triage. The heuristics themselves live there — no second copy here.

## Shared environment facts (all roles)

**Full text: `environment.md`.** One fact inlined, because no §Hard rules bullet carries it:

- **`gh` in `~/opencrabs` defaults to UPSTREAM.** `-R`/`--repo` is MANDATORY for any
  fork-targeted read or write; an unscoped call returns a real but WRONG issue or 404s.

The cargo ban, the `origin`/`adolfousier` split and actor attribution live in `environment.md` and in
§Hard rules — deliberately not restated here (Duty-6 c25 B-9: three cargo-ban homes inside SKILL.md alone).

Everything else — the skill glob gate's exact matching semantics, branch namespaces, the
carrier/feature-set/dispatch rules, and the daemon facts — is in `environment.md`.


## Upstream relations (v0.4.0, owner-approved 2026-08-26)

Upstream movement is WATCHED and ABSORBED on a schedule per the matrix below:

| Lifecycle Area | Owning Role | Key Tool / Procedure | Canonical Home |
|---|---|---|---|
| **1. Upstream Delta Watch** | Triage | `./tools/harvest/oc-upstream-delta` | `triage.md §Duty T4` |
| **2. Sync Model (REBASE)** | Triage | `upstream-merge-runbook.md` | `upstream-merge-runbook.md §Remotes & sync` |
| **3. Absorption & Dropping** | Triage / HQ | Auto-classify DROPPABLE patch-ids | `upstream-merge-runbook.md` |
| **4. Upstream PR Lifecycle** | HARVEST | Phase 7b / Phase 7c (`oc-harvest-dispatch`) | `harvest.md` |
| **5. Maintainer Interaction** | HQ / Alexey | Track PR comments via gh API & OC Dev chat heads-up | `harvest.md §Deep Core Advance Heads-Up Gate` |
| **6. Fork-local CI (`ci/*`)** | HQ | Carrier namespace `ci/quick-build-linux` | `hq.md §Upstream sync — watch & governance` |
| **7. Fork Branch Lifecycle** | Triage | `./tools/git/oc-branch-sweep` (archive before delete) | `triage.md §Duty T4` |

## Hard rules (all roles)

- Reports to Alexey: every issue/PR reference
  carries the LINK behind the number (issues: `https://github.com/leshchenko1979/opencrabs/issues/N`
  — the fork is the issues home; PRs: `https://github.com/adolfousier/opencrabs/pull/N`) — a bare `#N` is never enough.
- Refer to workers by TOPIC/CHAT NAME only (owner 2026-08-31) — NEVER by session uuid, on EVERY
  surface (owner reports, inter-lane advisories, session_notify text, verdict tables, ledger
  commentary). Uuids are for ROUTING fields only (`target_session`, `OC_ACTOR`, `Session-Id`
  trailers, tool arguments). Test: the owner must know WHICH chat to open without a lookup.
- Stick to the OFFICIAL ONTOLOGY (owner 2026-08-31): all roles use the vocabulary this SKILL
  defines — test ontology (§Test ontology), infra terms (§Glossary: selftest/battery/CI gate),
  roles (Editor/HQ/Triage/Toolsmith/Harvest/Reviewer lenses), gate colors (GREEN/RED with run
  receipt), phases, tool names. No ad-hoc synonyms; a NEW concept is proposed via the poll format
  and named on owner word. Reviewer A (REDUNDANCY + ONTOLOGY) enforces this lens-side.
- **Context Manifest Curation (Compaction Section 10, owner order 2026-09-17):** when context compaction occurs, the compactor MUST explicitly retain `opencrabs-dev`, `opencrabs-dev/fleet-directives.md`, and the active role file (`opencrabs-dev/editor.md`, `opencrabs-dev/hq.md`, `opencrabs-dev/triage.md`, `opencrabs-dev/toolsmith.md`, or `opencrabs-dev/harvest.md`) in `active_skills`. Only non-active role files are placed in `discard_skills`. Essential tools (`session_notify`, `session_search`, `bash`, `read_file`, `telegram_send`) must stay pre-activated. Canonical: `fleet-directives.md §Post-compaction skill reload & context manifest curation`.
- ONLY HQ edits skill files: `SKILL.md` · `editor.md` · `harvest.md` · `hq.md` · `triage.md` · `toolsmith.md` ·
  `review-lenses.md` · `fleet-directives.md` · `upstream-merge-runbook.md` · `war-stories.md` ·
  `s2-swap-journal-spec.md` · `README.md` · `CHANGELOG.md` · `session-notify.md` · `environment.md` · `tools/docs/*.md` — including all worker lanes AND
  the TRIAGE and TOOLSMITH lanes (2026-08-26; Compiler retired 2026-08-28). Workers propose via poll format or
  direct notify; they never write. ONE exception: `tools/**` CODE is the TOOLSMITH lane's (v0.4.87 carve-out),
  shipped with battery receipts — README's tool-fleet section and `tools/docs/*.md` count as that surface; the
  rest of README and all skill markdown stay HQ-only.
- Relay only PREDICATED claims (v0.4.6, from fabrication deviation #3): any
  build/deploy/artifact claim you pass onward must carry evidence YOU verified
  same-turn — run id against the API, sha against `ls-remote`/job-name embed,
  binary against sha256. A claim verified by someone else's message is
  unverified.
- ISSUE ROUTING (owner directives 2026-08-25 → 2026-08-27; consolidated as a
  table 2026-08-29):

| Rule | Applies to | Gate |
|---|---|---|
| NEW issues NEVER upstream — every new issue (upstream-code bugs and fork-only infra alike) is filed on the FORK | `leshchenko1979/opencrabs` | owner 2026-08-27 14:08Z |
| Upstream receives PRs ONLY — body = detailed description ending `Original issue: <full fork URL>`; NEVER `Closes #N` (wrong issue space) | `adolfousier/opencrabs` PR bodies | owner 2026-08-27 |
| Fork issue closed by US right after the PR is filed | fork issue tracker | — |
| Fork issues NEVER claimed on GitHub: no tackling comments, assignment, labels/reactions by any lane — claiming = `Issue-Ref` trailer + workers-ledger `claim` row (kind `claim`, v1.1 vocabulary since v0.4.48); uniqueness sweeps stay read-only search. **CARVE-OUT:** the item-7 approved-design comment and `oc-issue-log`'s per-commit implementation note (owner 2026-08-28) are sanctioned — the prohibition governs CLAIMING, not the design/implementation record | ledger | owner 2026-08-27 17:07Z |
| PR SHIPMENT — **PR SHIPMENT LAW (single home): feature COMPLETE + smoke PASS (v0.4.104 four-leg rubric) → the EDITOR posts smoke evidence to its forum topic and its obligation ENDS there; the HARVEST lane ports, gates and files the upstream PR. All other references to this law are pointers to THIS row — procedure: `harvest.md` Phase 7; upstream-merge-runbook.md §Upstream-merge cadence (harvest census); triage.md T4.** | mechanical gates | standing process |
| APPROVAL = Alexey's reply or a positive Telegram reaction to the explicit request in the forum topic; silence is NOT consent; spontaneous / ad-hoc PRs remain forbidden | owner word | v0.4.1 |

*Pre-2026-08-27 upstream issues stay readable for uniqueness sweeps and legacy
links; development-time upstream contact is PR-comments only (supersedes the
2026-08-22 issues/comment rule).*
- CONSENT REGISTER — **Never rule from codified memory — grep the live record
  (chat / ledger) before denying any permission** (v0.4.17 lesson, 2026-08-26).
  Deploy consent RETIRED 2026-08-28 (owner 18:50Z): GREEN carrier run + artifact
  verify IS the authorization. Upstream-PR filing follows the PR SHIPMENT law (PR SHIPMENT row, the ISSUE ROUTING bullet above), GATED BY THE MODE REGISTER below. APPROVAL
  definition above governs everything that is owner-gated (silence is NOT consent).
  - **MODE REGISTER — the upstream-PR filing gate is a MODE SWITCH (owner ruling 2026-09-20).** Two modes, ONE declared current, and the switch is the OWNER's alone. Owner's words: *"we basically have two modes: 1. High-trust mode, when I'm sure that the factory is working so that the quality allows autonomous harvesting. 2. Degraded, like now, when I want to gate every PR group."*

    | Dimension | HIGH-TRUST MODE | DEGRADED MODE |
    |---|---|---|
    | Condition (owner's words) | "the factory is working ... quality allows autonomous harvesting" | "I want to gate every PR group" |
    | Upstream PR filing | lane files on the 4-leg smoke PASS; filing NOTICE to its own topic | **the PR GROUP is HELD for explicit owner approval before the PR leaves the lane** |
    | Approval form | not required — SMOKE PASS is the gate | owner reply, or a positive Telegram reaction to the explicit request; **silence is NOT consent** |
    | Filing unit | one feature PR, per lane | **PR GROUP** — related PRs approved together |
    | Smoke rubric / CI gate / rollback | 4 legs / unchanged / owner's call | 4 legs / unchanged / owner's call |

    **CURRENT MODE: DEGRADED.** Resolution is LIVE, never remembered: read the newest `MODE:` row via `oc-ledger events --n 2000 --kind note` — **`--n` is MANDATORY, because `events` is a TAIL whose default window is ~21 rows, so a bare `events --kind note` returns an EMPTY result that is INDISTINGUISHABLE from "no `MODE:` row exists"** (the sole MODE row sat ~590 rows back and was invisible to the bare form; measured 2026-09-22T20:1xZ, and it had already produced two "no MODE row, therefore DEGRADED" findings in durable records that were RIGHT only because the law fails closed). **If NO `MODE:` row exists the default is DEGRADED** (fail closed — holding a filing costs nothing, an unapproved filing is a public act). **Under DEGRADED the harvest hold is GLOBAL**: it supersedes the retired per-group Owner Push Freeze register (removed by owner order 2026-09-24 21:04Z — see `fleet-directives.md` §Owner Push Freeze — RETIRED), so no PR group of ANY feature is filed without explicit owner approval. A feature's soak maturing, a green census, or an idle editor is never a release. The owner switches by word, receipted by `oc-ledger stamp note "MODE: <HIGH-TRUST|DEGRADED> — <provenance>" --by "hq <uuid>"`. Procedure: `harvest.md` §Phase 7 step 0a.
  (Deleted-tool history: CHANGELOG.md.)
- ROLE-SCOPED BROADCASTS: messages reach non-owning roles ONLY when tagged
  [ALL]; otherwise send strictly to the owning role. CC-everyone is noise.
- ONE formal SMOKE verdict per editor-feature lane: exactly one PASS/FAIL;
  duplicate confirmations are noise (#1227 lane double-report, 2026-08-26).
- SMOKE-EVIDENCE PRECEDENCE (v0.4.18): prefer
  smoke tests verifiable from LOGS over those requiring human verification.
  A machine-checkable verdict — CI run conclusion via API, parsed build/test
  logs, captured runtime or endpoint output — outranks "a human said it
  passed"; request human confirmation ONLY where logs genuinely cannot cover
  the claim (visual rendering, interactive UX), and then name EXACTLY what to
  observe. Design smoke captures to be self-sufficient: every claim cites run
  id + sha + step evidence, so any verdict is re-derivable from logs alone. Source-precedence ranks EVIDENCE quality only - it never conflates kinds: a green CI/build log stays CODE-TEST/build evidence and substitutes nothing for a behavioral SMOKE pass.
- UPSTREAM CI GATE (v0.4.22; encodes
  adolfousier/opencrabs CONTRIBUTING.md): NO upstream PR leaves a lane until
  the owning worktree passed the CI gate — and since v0.4.28 CI is the only
  executor, never local (Box law; local cargo in ANY form is a violation;
  Compiler role RETIRED 2026-08-28). The
  evidence is the GREEN `pr-checks.yml` run on the PR head branch (fmt/clippy/
  `cargo test --locked --profile ci --all-features` — flags VERBATIM from
  pr-checks.yml) — canonical procedure:
  harvest.md §Phase 7 step 2c. One red = fix cycle, not a filed
  PR ("PRs that fail CI will not be reviewed" — their words). Receipts ride
  the PR prep beside smoke evidence. Gate covers shipworthiness only;
  the SMOKE pass remains a required condition in BOTH modes, and owner approval
  is required under **DEGRADED MODE** and waived under **HIGH-TRUST MODE**
  (§Hard rules — CONSENT REGISTER / MODE REGISTER).
- Issue-first, no exceptions (2026-08-25): a DISCOVERED problem gets its issue
  FILED before any fix work starts — on the FORK `leshchenko1979/opencrabs`
  (ALL new issues — upstream-code bugs and fork-only infra alike; upstream
  receives PRs only). Discoverer
  files it (symptom + evidence); fixer claims via an `oc-ledger claim` row +
  an `Issue-Ref` trailer on the commit — NO CLAIMING `gh` comment, assignment
  or label on the fork issue (2026-08-27); CARVE-OUT: the item-7 approved-design
  comment and `oc-issue-log`'s per-commit note (owner 2026-08-28) are sanctioned. Covers
  task starts (`editor.md` Phase 1) AND mid-loop finds: red-build bugs, failed
  smoke tests, defects in another editor's feature.
- Continuous Issue Relationship Linking (owner order 2026-09-16; creation gate 2026-09-25; `--root` 2026-09-26): whenever
  a parent subsystem relationship, blocker dependency, or child sub-issue is established or discovered at ANY point in
  the lifecycle, the lane identifying it MUST establish native links in the same turn via
  `gh issue edit <issue> --parent <parent-issue>` and/or `--add-blocked-by <blocker-issue>`.
  **CREATION-TIME PARENT GATE — a `fix(`/`bug(`-titled issue MUST declare its origin ON the creating command
  (`tools/issue/oc-issue-create`): `--parent <N>` for a fork feature issue, `--root upstream:<sha|PR|path>` where the
  surface is upstream-inherited (`upstream-rooted`), or `--no-parent "<reason>"` as the last resort. A DECLARED root
  or orphan is legal; a SILENT one is the violation. The `--root` object must RESOLVE, or the flag is `--no-parent`
  in better clothes. Full clause + Duty T5 backstop: `upstream-merge-runbook.md`, `triage.md`.**
  **READ a relation with `gh issue view <N> --json parent,subIssues,blockedBy,blocking` — NEVER the issue object's
  `.parent` projection.** `gh api ... --jq '.parent.number'` returns a confident **null for every issue**, since the
  REST issue object omits the field; the same call returns a real title, so the null reads as "no parent". One
  recorded false negative (n=11340), and it defeated a GUARD that skipped on "already parented" — a guard and a
  verifier need the same authority.
- Restart scope: **`opencrabs-ops` ONLY.** The `family` and default-profile daemons
  require Alexey's explicit approval EVERY time. Exception (v0.4.71, lens B2 #3;
  sanctioned v0.4.59 #47): HQ may mechanically restart the
  `opencrabs-family.service` SIDECAR (journal-sequence verified) — never the
  default-profile daemon.
- Never trust watcher exit codes alone — read the run's own `conclusion` via API.
- BUILD TRIGGERS = exactly TWO, NO exceptions (v0.4.3, S3-rewired 2026-08-28; A3 owner ruling 2026-08-29): an editor's `oc-deploy ship --sha <full-sha>` background task, or Alexey's word. No other dispatch — the direct PR-head dispatch is retired (superseded by `oc-prchecks`; ORDER gate 3 containment rejects any sha outside fork `main` anyway). All builds serialize under single-flight.

## Shared war stories (why these rules exist)

Incident histories behind the hard rules live in `war-stories.md` (history is reference, not
procedure; the version-level record is `CHANGELOG.md`).