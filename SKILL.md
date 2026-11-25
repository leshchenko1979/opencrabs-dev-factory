---
name: opencrabs-dev
description: >
  OpenCrabs source ops (~/opencrabs): roles EDITOR (fork issues, per-task
  worktrees, CI gate (pr-checks), signed commits, push + sha hand-off, oc-build ship,
  smoke-test-on-notify), HQ (skill set + worker ledger),
  TRIAGE (interrupt lane: fix routing, enforcement),
  TOOLSMITH (CLI tool lane: owns tools/ — makes and fixes the CLI tools every other role uses),
  HARVEST (upstream contribution lane: ports a READY cluster, gates it, files the upstream PR and owns its lifecycle); Compiler role RETIRED 2026-08-28).
  Use when editing/fixing OpenCrabs Rust code, debugging quick-build-linux carrier or other CI runs, fetching CI artifacts, or swapping /usr/local/bin/opencrabs.
  (/opencrabs-dev)
globs:
  - ~/opencrabs/**
  - ~/opencrabs-wt/**
  - ~/.opencrabs/profiles/*/skills/opencrabs-dev/**
  - ~/.opencrabs/profiles/*/opencrabs-dev/**
  - ~/.opencrabs/profiles/*/projects/opencrabs-dev/**
version: 0.4.335
author: leshchenko1979
metadata:
  tags: [opencrabs, rust, ci, quick-build, binary-swap, worktree, session-notify]
  references:
    - https://github.com/opencrabs/opencrabs (upstream — PULL REQUESTS ONLY; never an issue home — owner order 2026-10-09)
    - https://github.com/leshchenko1979/opencrabs-dev-factory (dev-factory issues — tooling, CI, release automation, process)
    - https://github.com/leshchenko1979/opencrabs (fork — push target + the BINARY issue tracker; ALL opencrabs binary issues live here since 2026-10-09)
  provenance:
    - "Release history and the current version live in CHANGELOG.md (git-tracked, newest-first). The v0.4.43 B6 rationale is in war-stories.md (brain dir — `load_brain_file`)."
---

# opencrabs-dev — OpenCrabs source procedure

**Owns:** everything touching `~/opencrabs` source, its GitHub Actions runs, or the
installed `opencrabs` binary. This file = shared facts + role router only. Actual
procedures live in FIVE role files (`editor.md` / `hq.md` / `triage.md` / `toolsmith.md` / `harvest.md`),
with the editor's Phase 5 and Phase 6 appendices split out as `editor-ship.md` / `editor-smoke.md`;
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
| **EDITOR** | Commits + error fixes: claim issue → worktree → code → CI gate → sign → push → ff-merge into fork `main` → `oc-build ship` → smoke on notify | `editor.md` |
| **HQ** | Skill set maintenance, worker ledger, Duty 4 worker polls, Duty 6 periodic lens reviews — count derived from the catalog at gate time (details in `hq.md` and `review-lenses.md`) | `hq.md` |
| **TRIAGE** | Intake & hygiene: issue assignment, repo hygiene patrols, rebase/merge execution delegated from HQ, upstream lifecycle tracking (delta watch, PR census, dependency tracking folded from Harvester v0.4.176) | `triage.md` |
| **TOOLSMITH** | CLI tools author & maintainer: owns `tools/` code, test battery stewardship, direct recipient of tool quirks/defects (v0.4.176) | `toolsmith.md` |
| **HARVEST** | Upstream contribution: port → CI gate → file → follow. Consumes a cluster Triage surfaced and marked READY; owns the harvest branch, the gate dispatch, the upstream PR and its lifecycle (v0.4.250, owner order 2026-09-24 centralising harvest) | `harvest.md` |

Roles **DO NOT intersect**:

- The Editor NEVER installs/swaps binaries, NEVER restarts daemons, NEVER dispatches
  BUILD runs — shipping goes through `oc-build ship` (S3). Build triggers: §Hard rules
  (A3 ruling 2026-08-29); the Phase-7 step-2c pr-checks dispatch is a lint/test gate,
  not a build trigger.
- Hand-off point: the Editor produces (branch pushed AND fast-forwarded into fork
  `main` + reported shas); `oc-build ship` takes it from there (dispatch → poll
  → swap-execute, consent eliminated 2026-08-28). If the run is RED, `oc-build`
  reports evidence and stops — fixing code is always Editor work.
No lane settles protocol disputes — rulings are HQ Duty 5.

| Lane | NEVER |
|---|---|
| TRIAGE | edits skill files (single-writer law: HQ is the sole author) · executes builds/swaps (strict routing) |
| TOOLSMITH (`tools/` CODE only) | skill markdown + `fleet-directives` (HQ-only) · daemon/carrier source (Editor territory) |
| HARVEST (upstream PR lifecycle only) | edits skill markdown (HQ-only) · installs/swaps binaries · restarts daemons · dispatches builds |
- **The EDITOR's obligation ends at a behavioural PASS on the running binary.** Harvest census, porting, upstream branch creation, PR filing and upstream lifecycle belong to the HARVEST lane — an editor lane that finds itself harvesting has taken work it does not own.
  - **CARVE-OUT — an editor MAY execute a `[HARVEST DISPATCH]` envelope** (2026-11-19, Duty-4 1a63f103 P2): receive the unit, prepare and validate the branch, push it, and run the CI gate. What stays HARVEST-only is **port SELECTION, upstream PR filing, and PR lifecycle**. This is what the dispatch tool actually enforces — `tools/harvest/oc-harvest-dispatch:763` defaults its accepted pool to `editor,harvest` — and the tool's own comment (`:2046-2049`) records why the pool was widened. Refusing a `[HARVEST DISPATCH]` on the strength of the sentence above is a wrong answer to a legitimate dispatch; the boundary that matters is selection and filing, not execution.
- **PRIORITY AUTHORITY (owner order 2026-09-15):** every lane (Editor, HQ, Triage, Toolsmith, Harvest) owns priorities, sequencing and task ordering within its codified scope — never ask the operator about priorities (`fleet-directives.md` §Autonomous Priority Authority Law).

If the request mixes roles (e.g. "fix X and deploy it"), split into separate
role loads — do not fuse the roles in one pass without Alexey saying so explicitly.

## Canonical tooling (v0.4.12, PROCESS-TOOL ownership)

Mechanical rituals the roles once hand-ran are now single commands in `tools/` (CLI-tool creation/fix is
the TOOLSMITH lane's scope, v0.4.87). Fleet-wide rc conventions and the FULL per-tool rc register live
only in `tools/docs/RC-CONTRACT.md` (the SOLE register; lens A H1/B F1, v0.4.79). Archived compiler-step
anchors: `tools/archive/compiler.md`.

**Directory layout — one level per KIND (v0.4.254):** `tools/` holds the `oc-*` fleet executables (the public interface) grouped ONE LEVEL PER FUNCTION — `audit/` `git/` `harvest/` `issue/` `notify/` `ship/` `smoke/` `state/` `reports/` — beside `tools/lib/` shared helpers, `tools/tests/` the battery, `tools/archive/` retired tools, `tools/docs/` the law that documents the tools, and **`tools/instruments/` corpus-agnostic analysis tools that are NOT fleet tools** — an instrument that reviews an arbitrary corpus has no place in the `oc-*` namespace, and lands there instead. **This sentence is the SOLE home of the group enumeration** — `editor.md` and `README.md` point here instead of restating it, so a new group is documented in exactly one place.

**Tool register: `reference-tools.md`** — one row per `oc-*` tool: invocation shape and the slot it
fills. Load it when you need a tool's exact form, or when adding one. rc semantics are never here — the
sole register is `tools/docs/RC-CONTRACT.md`.

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
  sync the order asks for. The 22-char bound is where the owner's CLIENT truncates
  the sidebar; it was measured by the Triage lane on 2026-09-25 and is NOT derivable
  from this box, so re-derive it rather than assume it if the client changes. Mechanism,
  verified at source:
  `rename_topic` persists through `record_topic_created`
  (`src/channels/telegram/mod.rs:51`) — an append-only INSERT into
  `channel_messages`, never a read-modify-write — so parallel renames cannot
  clobber each other, and a rename keys on `thread_id`, so session bindings are
  unaffected. The table is append-only and retains every historical name; the live name for a thread is its NEWEST row.
  **THE AUTHORITATIVE NAME IS THE NEWEST `topic renamed to "<x>"` / `topic created "<x>"` EVENT ROW — NOT the `topic_name` COLUMN, which is an ECHO. `latest_topic_name()` feeds both the inbound (`handler.rs:357-363`) and outbound (`delivery.rs:621-626`) writes, so a plain message's `topic_name` is a copy of whatever was newest when it was written and can propagate a superseded name indefinitely (measured 2026-09-27, t34653: `Compaction visibility` carries **0** rename/create events — it was never a rename target — yet was the newest `topic_name` at 12:50:16Z, two days after the event stream renamed it to `Memory: Compaction`). Read the column and you can be pushed backwards off a correct answer; read the events and t49643's live name is `Core: Skills` where its column echoes `Skills`. `sessions.title` is a bind-time label that does not follow renames at all, and `session_bindings` has no name column. Never re-type a name: emit it from the event row.**

- Every Editor commit carries a git trailer: `Session-Id: <full session uuid>`
  (`git commit --trailer "Session-Id: <uuid>"`). FULL uuid — the 8-char display
  form cannot drive routing. Each session READS ITS OWN UUID straight from its
  runtime prompt/session context — no lookup tool needed (correction
  2026-08-25); the post-swap fan-out takes notification targets from these
  trailers (`oc-attrib`; `oc-contributors` RETIRED v0.4.72 — E2 #1, subset of oc-attrib, zero live callers).
- After a healthy swap the fan-out is MECHANICAL: `oc-fanout fanout`
  (auto-fired at the `swap_execute` tail since v0.4.37,
  [#24](https://github.com/leshchenko1979/opencrabs/issues/24)) attributes the
  shipped range and notifies each contributing editor — an editor's job on
  notify is the smoke test (bullets below). GREEN/RED leg internals, range
  math, blame attribution, journal vocabulary: `s2-swap-journal-spec.md`
  §Fan-out legs (re-homed v0.4.80, lens B F4).
- Editors own testing THEIR features on notification: SMOKE TESTS against the
  swapped binary running on this box (the cargo ban itself = editor.md §Box law, one
  statement). Failures funnel back through blame attribution (`oc-fanout fanout`
  above), which asks the guilty editors for fixes.
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
  text, the ONLY sanctioned output. Editors NEVER invoke a channel send/edit tool — not even into
  their own topic; no cross-chat reads; own-topic message reads only. Reactions are allowed (owner
  consent signal). **The enforced tool-name list has ONE home — `triage.md §Duty T4`, which derives
  it from the live registry, so a renamed or newly-added send tool is covered without editing this
  file.**
- Sanctioned senders (NOT editors — none of this is lane-to-lane): the task-queue skill's documented
  `/tq-approve` flow; alerting lanes reporting to the owner DM per the ops runbook; HQ's session text.
- Violation pattern (Triage patrol, `triage.md §Duty T4`): a TOOL_ACCUM row showing an editor lane
  calling a telegram send/edit tool → the patrol notifies the rule; a repeat escalates to HQ for
  the review toggle.

## Test ontology (v0.4.2 — three kinds + one sanity signal, NEVER conflate)

| | SMOKE TEST | CODE TESTS | FEATURE-PRESENCE CHECK |
|---|---|---|---|
| Answers | does my feature WORK for a user right now? | is the code correct by analysis standards? | is the feature actually INSIDE the artifact we are about to deploy? |
| What | behavioral drive of ONE shipped feature | compile/run verification: cargo fmt, clippy, cargo test | static markers: binary strings/symbols, sha256 identity vs artifact, source-tree grep |
| Where | live `opencrabs-ops` unit, its real surfaces (Telegram, cron, MCP) | GitHub Actions ONLY — the CI gate (`pr-checks.yml`; upstream's own checks on PRs). Carrier build COMPILES the artifact but runs NO test leg (removed 2026-08-31, `e71dba58`) | this box, against the DOWNLOADED artifact + its source tree — nothing running |
| When | after a swap notify (`editor-smoke.md`) | pre-flight gate before PRs/ff-merge (Phase 7 step 2c) — `pr-checks.yml` is the ONLY CODE-TESTS locus | pre-swap, every cycle (`oc-swap` swap path) |
| Who | owning Editor | Editor dispatches the gate and reads conclusions; `oc-build` reads build conclusions | `oc-swap` swap path |
| Toolchain | none — local cargo FORBIDDEN in any form (binaries disabled 2026-08-28; editor.md §Box law) | CI's own — never local | `strings`, `sha256sum`, `git grep` — none compile anything |
| Evidence | one line: drove X, observed Y (+ run id / sha) | job/step conclusions read via API | marker found/not-found + checksum line in baseline.json |
| On FAIL | issue FIRST, then evidence to the HQ lane (`session_notify`) | fix before merge / PR | NO swap — feature missing from build; regression stated plainly |

**The smoke-verdict rules and their incident history are canonical at `editor-smoke.md`
§Smoke-verdict rules — read them there before writing or judging a verdict.** The subject list
lives in that heading and nowhere else: a pointer that re-enumerates it drifts the moment the
section grows (this one did, twice — c29 lens G).

## Glossary — official terms (v0.4.62; one concept = one name)

*(Definitions moved to `reference-glossary.md`: the official vocabulary — FIRE, carrier, fan-out, state dir vs skill dir, single-flight, CI gate, ORDER gates, S2/S3, lane, disk absorption, roster, lens, HQ, selftest/battery, GREEN/RED, TOOL_ACCUM, PARKED-OWNER-EYE, 4-Leg Smoke Rubric, issue cluster, upstream-rooted. Load it when a term is unfamiliar, or before naming a NEW concept — one concept, one name.)*

## Red-run triage heuristics (shared core)

ONE location: `editor.md §Red-run triage heuristics` — read by the editor in its fix round and by
HQ in RED triage. No second copy here.

## Shared environment facts (all roles)

**Full text: `environment.md`** — the skill glob gate's exact matching semantics, branch namespaces,
the carrier/feature-set/dispatch rules, **which workflow files exist on which branch (all fork CI lives
on `ci/quick-build-linux`; `main` carries upstream's, so it has no post-merge net)**, the daemon facts,
the cargo ban, the `origin`/`adolfousier` split and actor attribution. One fact is inlined, because no
§Hard rules bullet carries it:

- **`gh` in `~/opencrabs` defaults to UPSTREAM.** `-R`/`--repo` is MANDATORY for any
  fork-targeted read or write; an unscoped call returns a real but WRONG issue or 404s.

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

**How to write one (research 2026-11-17, `receipts-worth-keeping`):** **unconditional** ("Never X", never "if Y then X" — conditional measured worst), **concrete**, **negative**. Rule inline; incident narrative to `war-stories.md` (brain dir); a date is an expiry signal for humans, not a compliance lever for the model. If a prohibition actually matters, add a VERIFIER — refusal rules scored 0% under every wording intervention tested.

- Reports to Alexey: every issue/PR reference
  carries the LINK behind the number (binary issues: `https://github.com/leshchenko1979/opencrabs/issues/N`;
  factory issues: `https://github.com/leshchenko1979/opencrabs-dev-factory/issues/N`;
  PRs: `https://github.com/opencrabs/opencrabs/pull/N`) — a bare `#N` is never enough.
- Refer to workers by TOPIC/CHAT NAME only (owner 2026-08-31) — NEVER by session uuid, on EVERY
  surface (owner reports, inter-lane advisories, session_notify text, verdict tables, ledger
  commentary). Uuids are for ROUTING fields only (`target_session`, `OC_ACTOR`, `Session-Id`
  trailers, tool arguments). Test: the owner must know WHICH chat to open without a lookup.
- Stick to the OFFICIAL ONTOLOGY (owner 2026-08-31): all roles use the vocabulary this SKILL
  defines — test ontology (§Test ontology), infra terms (`reference-glossary.md`), roles
  (Editor/HQ/Triage/Toolsmith/Harvest/Reviewer lenses), gate colors (GREEN/RED with run
  receipt), phases, tool names. No ad-hoc synonyms; a NEW concept is proposed via the poll
  format and named on owner word. Reviewer A (REDUNDANCY + ONTOLOGY) enforces this lens-side.
- **Context Manifest Curation (Compaction Section 10, owner order 2026-09-17):** on compaction the compactor MUST retain `opencrabs-dev`, `opencrabs-dev/fleet-directives.md`, and the active role file in `active_skills`; only non-active role files go in `discard_skills`. Essential tools (`session_notify`, `session_search`, `bash`, `read_file`, `telegram_send`) MUST stay pre-activated. Canonical: `fleet-directives.md §Post-compaction skill reload & context manifest curation`. **The retention above is INTENT, not a guarantee: the compactor's own prompt carries no retention list and no pipeline layer enforces one (measured 2026-10-06) — [opencrabs/opencrabs#1960](https://github.com/opencrabs/opencrabs/issues/1960).**
- ONLY HQ edits skill files. **The set is DERIVED, never enumerated:** every `*.md` in the skill
  directory, plus `war-stories.md` at the profile root. A hand-maintained list goes stale silently —
  the previous closed form omitted `editor-ship.md`, `editor-smoke.md`, `reference-glossary.md` and
  `reference-tools.md` after the 2026-11-15 split (c29: 15 named, 18 on disk) and named
  `war-stories.md` as though it lived in the skill dir (v0.4.319 c29 I-2 fixed the identical stale
  list at `fleet-directives.md` §Post-compaction skill reload & context manifest curation; this site was missed). **The enumeration below is a convenience
  INDEX, never the authority** — a file on disk is HQ-only whether or not it appears here.

  Index: `SKILL.md` · `editor.md` · `editor-ship.md` · `editor-smoke.md` · `harvest.md` · `hq.md` · `triage.md` · `toolsmith.md` ·
  `review-lenses.md` · `fleet-directives.md` · `upstream-merge-runbook.md` ·
  `s2-swap-journal-spec.md` · `README.md` · `CHANGELOG.md` · `session-notify.md` · `environment.md` · `tools/docs/*.md` — including all worker lanes AND
  the TRIAGE and TOOLSMITH lanes (2026-08-26; Compiler retired 2026-08-28). **The two editor phase appendices
  (`editor-ship.md`, `editor-smoke.md`) are skill files on this list too (c29 G-1, v0.4.320). `war-stories.md` is
  HQ-owned as well but is a BRAIN-DIR file (`~/.opencrabs/profiles/ops/`), not one of this tree's — the census above
  counts SKILL-TREE files only.** Workers propose via poll format or
  direct notify; they never write. ONE exception: `tools/**` CODE is the TOOLSMITH lane's (v0.4.87 carve-out),
  shipped with battery receipts — README's tool-fleet section and `tools/docs/*.md` count as that surface; the
  rest of README and all skill markdown stay HQ-only.
- Relay only PREDICATED claims (v0.4.6, from fabrication deviation #3): any
  build/deploy/artifact claim you pass onward must carry evidence YOU verified
  same-turn — run id against the API, sha against `ls-remote`/job-name embed,
  binary against sha256. A claim verified by someone else's message is
  unverified.
- ISSUE ROUTING (owner order 2026-10-09 — canonical; superseded rulings live in `war-stories.md` — brain dir, `load_brain_file`):

| Rule | Applies to | Gate |
|---|---|---|
| **TWO-STREAM: a BINARY issue (runtime behaviour, channels, providers, TUI, memory, tools) is filed on the FORK `leshchenko1979/opencrabs` — the single binary tracker; a FACTORY issue (tooling, CI, release automation, process) on `leshchenko1979/opencrabs-dev-factory`. UPSTREAM `opencrabs/opencrabs` takes PULL REQUESTS ONLY — no new upstream issues.** The fork takes EVERY binary issue; there is no "fork-only defect" class. Do not conflate this with the harvest boundary register ([#761](https://github.com/leshchenko1979/opencrabs/issues/761) — `harvest-registry.json` → `manual_records`, `not-upstreamable` rows) or the census `FORK_ONLY_SURFACE` predicate (`tools/harvest/oc-harvest-census`): those decide whether a COMMIT can be ported upstream, never which tracker an issue goes to, and they survive unchanged. Mandatory duplicate sweep (open+closed, issues+PRs) BEFORE filing; core-surface changes carry `fix core` / `feat core` in the title | `leshchenko1979/opencrabs` (all binary) · `leshchenko1979/opencrabs-dev-factory` (factory) | owner 2026-10-09 |
| PR body = detailed what/why. `Closes #N` is **VALID same-repo** and **FORBIDDEN across trackers** (a fork or factory issue has no upstream number space) — the upstream PR body ends `Original issue: <full URL>` naming the FORK issue, EXACTLY one | `opencrabs/opencrabs` PR bodies | owner 2026-10-09 |
| A binary issue on the FORK closes via `Closes #N` on the fork commit that fixes it; the fork is a LIVE tracker — never READ-ONLY, never a historical portfolio | trackers | owner 2026-10-09 |
| Claiming = **assignment on the tracker** (the PUBLIC claim signal, owner 2026-10-03) **plus** the internal `Issue-Ref` trailer + workers-ledger `claim` row. **THE ASSIGNMENT LEG IS ATTEMPTED AND VERIFIED, NEVER ASSUMED:** both live trackers (fork + factory) assign to `leshchenko1979`, each tracker's ONLY assignable account. Where the platform denies it, RECORD the denial and let the `claim` row + `Issue-Ref` trailer BE the claim — a SILENT skip is a violation, because it is indistinguishable from a permission limit. The upstream TRIAGE grant (2026-10-04) is HISTORICAL: upstream takes PRs only. NO tackling/status comments or labels; uniqueness sweeps stay read-only. **CARVE-OUT:** the item-7 approved-design comment and `oc-issue-log`'s per-commit note (owner 2026-08-28) are sanctioned — the prohibition governs CLAIMING chatter, not the design/implementation record | tracker assignment (attempted + verified) + ledger | owner 2026-10-03 |
| **PR SHIPMENT LAW (single home): the feature BEHAVES CORRECTLY on the live binary with a smoke PASS (v0.4.104 4-Leg Smoke Rubric) → the EDITOR records that evidence AND CLOSES THE FORK ISSUE on it (owner 2026-11-15; `triage.md §Autonomous closure` class (d)) — that IS the finish line. Upstream filing happens only for groups the owner names and is never the terminus of any lane's work. All other references point HERE** — procedure: `harvest.md` Phase 7; `upstream-merge-runbook.md §Upstream-merge cadence`; `triage.md` T4 | mechanical gates | standing process |
| APPROVAL = Alexey's reply or a positive Telegram reaction to the explicit request in the forum topic; silence is NOT consent; spontaneous / ad-hoc PRs remain forbidden | owner word | v0.4.1 |

*Pre-2026-08-27 upstream issues stay readable for uniqueness sweeps and legacy links; development-time upstream contact is PR-comments only.*
- CONSENT REGISTER — **Never rule from codified memory — grep the live record (chat / ledger) before denying any permission** (v0.4.17, 2026-08-26). Deploy consent RETIRED 2026-08-28: GREEN carrier run + artifact verify IS the authorization. APPROVAL above governs everything owner-gated.
  - **UPSTREAM FILING IS AN EXCEPTION, NEVER A GOAL (owner 2026-11-12).** The fork has diverged and will keep diverging: **keeping a change on the fork is the normal, finished state** — not "degraded", not a backlog, not debt. **The retired vocabulary (`DEGRADED` / `HIGH-TRUST`) must not be reintroduced** in a report, a ruling or a commit message.
    Two states, ONE declared current, switchable by the OWNER's word alone: **FORK-STANDING** (default — nothing is filed; not filing is normal) or **UPSTREAM-ON-REQUEST** (only the NAMED groups are filed; the owner's request names the group, reply or positive reaction; silence is NOT consent; an unnamed change is never filed). CI gate, smoke rubric, atomicity and rollback are unchanged in both.
    **CURRENT STATE: FORK-STANDING.** Resolution is LIVE, never remembered: read the newest `MODE:` row via `oc-ledger events --n 2000 --kind note` — **`--n` is MANDATORY, because `events` is a TAIL whose default window is ~21 rows, so a bare `events --kind note` returns an EMPTY result INDISTINGUISHABLE from "no `MODE:` row exists"** (a real `MODE:` row sat ~590 rows back and the bare form missed it; receipt: `war-stories.md`, brain dir). **No `MODE:` row ⇒ FORK-STANDING** — fail closed, because the closed direction is "nothing is filed" and an unapproved filing is a public act. **A legacy row reads FORWARD, never backwards:** `MODE: DEGRADED` = FORK-STANDING; `MODE: HIGH-TRUST` = UPSTREAM-ON-REQUEST with NO named groups, i.e. still nothing filed until a group is named. Switch: `oc-ledger stamp note "MODE: <FORK-STANDING|UPSTREAM-ON-REQUEST> — <provenance>" --by "hq <uuid>"`. Procedure: `harvest.md` §Phase 7 step 0a.
- ROLE-SCOPED BROADCASTS: messages reach non-owning roles ONLY when tagged
  [ALL]; otherwise send strictly to the owning role. CC-everyone is noise.
- ONE formal SMOKE verdict per editor-feature lane: exactly one PASS/FAIL;
  duplicate confirmations are noise (#1227 lane double-report, 2026-08-26).
- SMOKE-EVIDENCE PRECEDENCE (v0.4.18): prefer smoke tests verifiable from LOGS over those requiring human verification. A machine-checkable verdict — CI run conclusion via API, parsed build/test logs, captured runtime or endpoint output — outranks "a human said it passed"; request human confirmation ONLY where logs genuinely cannot cover the claim (visual rendering, interactive UX), and then name EXACTLY what to observe. Design smoke captures to be self-sufficient: every claim cites run id + sha + step evidence, so any verdict is re-derivable from logs alone. Source-precedence ranks EVIDENCE quality only — it never conflates kinds: a green CI/build log stays CODE-TEST/build evidence and substitutes nothing for a behavioral SMOKE pass.
- UPSTREAM CI GATE (v0.4.22): NO upstream PR leaves a lane until the owning worktree passed the CI gate — and since v0.4.28 CI is the only executor, never local (Box law; local cargo in ANY form is a violation; Compiler role RETIRED 2026-08-28). The evidence is the GREEN `pr-checks.yml` run on the PR head branch (fmt/clippy in `pr-gates`; the test verdict is `pr-gates-nextest` — `cargo nextest run --cargo-profile ci --features <shipped set>` plus a SEPARATE `cargo test --doc` step, because nextest never runs doctests — flags VERBATIM from `ci-lane-impl.yml`, the gate body; `pr-checks.yml` is a thin caller. **The `cargo test --locked --profile ci --all-features` leg was DELETED 2026-11-20** and nextest promoted to the blocking verdict) — canonical procedure: `harvest.md` §Phase 7 step 2c. One red = fix cycle, not a filed PR ("PRs that fail CI will not be reviewed" — their words). Receipts ride the PR prep beside smoke evidence. Gate covers shipworthiness only; the SMOKE pass remains a required condition in BOTH states, and a filing happens ONLY on the owner's explicit request naming the group (§CONSENT REGISTER / UPSTREAM FILING REGISTER).
- Issue-first, no exceptions (2026-08-25; routing revised 2026-10-09): a DISCOVERED problem gets its issue FILED before any fix work starts — tracker per ISSUE ROUTING above (upstream PRs ONLY). Discoverer files it (symptom + evidence) after the duplicate sweep above; fixer claims via the tracker ASSIGNMENT plus an `oc-ledger claim` row + an `Issue-Ref` trailer on the commit — NO CLAIMING `gh` comment or label; the item-7 approved-design comment and `oc-issue-log`'s per-commit note (owner 2026-08-28) are sanctioned. Covers task starts (`editor.md` Phase 1) AND mid-loop finds: red-build bugs, failed smoke tests, defects in another editor's feature.
- Continuous Issue Relationship Linking (owner 2026-09-16; creation gate 2026-09-25; `--root` 2026-09-26): whenever a parent subsystem relationship, blocker dependency, or child sub-issue is established or discovered at ANY point in the lifecycle, the lane identifying it MUST establish native links in the same turn via `gh issue edit <issue> --parent <parent-issue>` and/or `--add-blocked-by <blocker-issue>`.
  **CREATION-TIME PARENT GATE — a `fix(`/`bug(`-titled issue MUST declare its origin ON the creating command (`tools/issue/oc-issue-create`): `--parent <N>` for a fork feature issue, `--root upstream:<sha|PR|path>` where the surface is upstream-inherited (`upstream-rooted`), or `--no-parent "<reason>"` as the last resort. A DECLARED root or orphan is legal; a SILENT one is the violation. The `--root` object must RESOLVE, or the flag is `--no-parent` in better clothes.** Full clause + Duty T5 backstop: `upstream-merge-runbook.md`, `triage.md`.
  **THE GATE HAS THREE LEGS — ASSIGNMENT and NATIVE LINK joined ORIGIN (owner 2026-10-05, origin opencrabs/opencrabs#1932).** **(a) ASSIGNMENT:** a `fix(`/`bug(`-titled issue MUST carry an assignee ON the creating command (`--assignee <login>`): `leshchenko1979` on BOTH live trackers, each tracker's ONLY assignable account (measured 2026-10-10); the pre-2026-10-09 `adolfousier` constant does NOT resolve on the fork — `--add-assignee adolfousier` silently no-ops (rc 0, assignees unchanged). This leg exists because a tracker's `auto-assign.yml` can assign the AUTHOR rather than the intended claimer — VERIFY the assignee landed. **(b) NATIVE LINK:** where the declared origin resolves to a SAME-TRACKER issue, the native parent link is OBLIGATORY — `--parent <N>` at creation, or `gh issue edit <issue> --parent <N>` as the immediate next action. A comment-only `root:` satisfies DECLAREDNESS, never the link when a same-tracker parent exists: for `--root upstream:<sha>` the parent is derivable from that commit's own `Closes #N` / `Fixes #N` trailer. Where the origin has no same-tracker issue counterpart (an upstream PR or path), the comment declaration IS the link and no native link is possible. **TOOL STATUS — BOTH LEGS SHIPPED (v0.4.297, tool commit `9f7e90be`; the clause below read "until it lands" for three weeks after it had):** `oc-issue-create` carries `--assignee` as a FIRST-CLASS flag with a per-tracker default (`leshchenko1979` on both live trackers), an `--assignee` that does NOT resolve is REFUSED (rc 3, nothing filed) rather than passed through, and `--no-assignee "<reason>"` records an explicit declaration; `--root upstream:<sha>` derives `--parent` from that commit's own `Closes #N` / `Fixes #N` trailer. **The lane still owns the leg:** the tool automates the ARGUMENT, never the VERIFICATION — read the created issue back and confirm the assignee and the native parent actually landed (`gh issue view <N> --json assignees,parent`), because a no-op that returns rc 0 is exactly the failure this leg exists to catch.**
  **READ a relation with `gh issue view <N> --json parent,subIssues,blockedBy,blocking` — NEVER the issue object's `.parent` projection.** `gh api ... --jq '.parent.number'` returns a confident **null for every issue**, since the REST issue object omits the field; the same call returns a real title, so the null reads as "no parent". A recorded false negative defeated a GUARD that skipped on "already parented" — a guard and a verifier need the same authority (`war-stories.md`, brain dir).
- Restart scope: **`opencrabs-ops` ONLY.** The `family` and default-profile daemons require Alexey's explicit approval EVERY time. Exception (v0.4.71, lens B2 #3; sanctioned v0.4.59 #47): HQ may mechanically restart the `opencrabs-family.service` SIDECAR (journal-sequence verified) — never the default-profile daemon.
- Never trust watcher exit codes alone — read the run's own `conclusion` via API.
- BUILD TRIGGERS = exactly TWO, NO exceptions (v0.4.3, S3-rewired 2026-08-28; A3 owner ruling 2026-08-29): an editor's `oc-build ship --sha <full-sha>` background task, or Alexey's word. No other dispatch — the direct PR-head dispatch is retired (superseded by `oc-gate`; ORDER gate 3 containment rejects any sha outside fork `main` anyway). All builds serialize under single-flight.

## Shared war stories (why these rules exist)

Incident histories behind the hard rules live in `war-stories.md` — **a BRAIN-DIR file, NOT shipped
in this skill tree** (`~/.opencrabs/profiles/ops/war-stories.md`; load it with `load_brain_file`).
History is reference, not procedure; the version-level record is `CHANGELOG.md`.