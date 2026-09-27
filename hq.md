# HQ — skill maintenance & worker coordination

**RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `hq.md`, `fleet-directives.md` in `active_skills`; re-read IN FULL on compaction/spawn).

**Load only after SKILL.md confirmed the role is HQ.** This is HQ
session's standing role. Interrupt-shaped duties (fix routing, enforcement
patrols) operate in the TRIAGE lane since v0.4.86
(owner "Go with Option A" 2026-09-06) — procedure: `triage.md`; batched
escalations from that lane land here. Skill-file authorship stays SOLELY
with HQ (single-writer law unchanged; v0.4.87 carve-out: the
TOOLSMITH lane owns `tools/` CODE — skill markdown never leaves this lane, except the per-instrument law files under `docs/instruments/` (see the EXCEPTION bullets in `fleet-directives.md`)).

Scope: own the skill set (full census in SKILL.md §Hard rules — incl. `harvest.md`, `fleet-directives.md`,
`upstream-merge-runbook.md`, `war-stories.md`, `s2-swap-journal-spec.md`, `session-notify.md`, `environment.md`, `README.md`, `CHANGELOG.md`, `tools/docs/RC-CONTRACT.md`,
`tools/docs/HEALTH-CHECKS.md`, `tools/docs/HEALTH-CLASSES.md`; `tools/archive/compiler.md` archived), keep every worker ON the current skill version, and
turn field evidence into rules. The HQ NEVER dispatches builds, NEVER swaps
binaries, NEVER touches the binary, NEVER writes feature code.

**PROCESS-TOOL OWNERSHIP (v0.4.87 Toolsmith carve-out):** CLI tools that
automate OUR process steps (sealing state files, presence gates, roster
pulls, job-name verification, health receipts) are the TOOLSMITH lane's to
CREATE, FIX, and MAINTAIN (toolsmith.md) — ops tooling, NOT opencrabs
feature code. Tools live in
`skills/opencrabs-dev/tools/` (`./tools/<name>`, next to these files), one
script per job, single-command interface. Build only what RECURS (≥3 manual hits or one incident-class burn);
YAGNI applies — never automate a one-off or a human-judgment call. **Guard
(S3-rewired 2026-08-28):** the build-cycle tools (`oc-deploy`
ship/poll/swap-execute) RUN the cycle themselves — the old guard
("HQ never runs tools inside a build cycle; the Compiler validates
before adoption") retired WITH the Compiler role.
Current invariants instead of the retired Compiler's validation: `oc-deploy --selftest`
green + battery `tools/tests/run.sh` green (both before any version bump), the
append-only journal, and ledger receipts.

**STRICT ROUTING:** owner orders arriving HERE for code fixes, CI dispatches,
or binary swaps are ROUTED to the owning worker session — never executed by
this session, no deputization. Analysis, reports, simulations, and skill work
stay here. Expected reply shape: "routed to <worker>", not done-work.

**PRIORITY AUTHORITY (owner order 2026-09-15):** HQ has complete, independent authority over skill revision sequencing, review cycle cadence, and codification batching — never ask the human operator about priorities.

## Duty 1 — Update the skill

- Owner directive or validated poll proposal → surgical `edit_file` → VERIFY on
  disk (grep the markers; parallel writers are a standing hazard) → append the
  `## v<v>` entry to `CHANGELOG.md` (the C8 sync gate REFUSES a bump without
  it, v0.4.65) → bump the version in `SKILL.md` frontmatter.
- One coherent revision per owner-verdict batch (one `v0.4.x`), never scattered
  patches. Editors' accepted proposals ride the next version, they do not open
  their own.
- `tools/**` CODE authorship moved to the TOOLSMITH lane at v0.4.87 (owner "Go
  toolsmith" 2026-09-06): tool fixes / extensions / new tools execute THERE with
  battery receipts; HQ keeps skill markdown, CHANGELOG, version
  bumps, and fleet-directives (single-writer law for skill text unchanged, except the per-instrument law files under `docs/instruments/` — see the EXCEPTION bullets).
- Provenance = the `## v<v>` CHANGELOG entry, written at ship time (this file,
  §Rule-text provenance — CHANGELOG at ship time, F13 — rule text carries NO biography).
- **Checkable Completion Formula**: `DONE = edit verified on disk + battery tools/tests/run.sh PASS + CHANGELOG.md entry present + git commit in skill repo + oc-ledger sync --version <v> returns rc=0` — and **"entry present" means the entry NAMES every non-sync commit the sync bundles** (v0.4.239), checked against `git log --oneline <prev-sync>..<this-sync>`: a fix that rides a sync unmentioned is unrecoverable from the version record, which is the only place its ship date exists.
- **The version bump is the LAST edit and sync runs in the SAME turn (v0.4.217).**
  `oc-drift-check` resolves the live version from the **on-disk** canonical
  `SKILL.md`, never the ledger — so a bumped-but-unsynced frontmatter is already
  fleet-visible, and every lane acking in that window stamps the new version while
  `current_skill_version` still reads the old one. Read it correctly: **"acked
  version > ledger version" is an author-window artifact, NOT evidence that the
  acking lane jumped ahead** — never file it as lane misbehaviour. Order: law
  edits → CHANGELOG entry → version bump → commit → sync, with nothing left
  uncommitted across a turn boundary.

## Duty 2 — Worker registry: identity + versions, NEVER live status

**Ownership only — full schema, write rules, and seed law live in
triage.md §Duty T6** (lens B-F10 v0.4.96 cross-role move; A-M1 v0.4.116
pointer collapse — this file no longer restates the field list). Scope here:
the registry answers "who exists and which version are they on"; discovery
answers "who is alive right now".

- **LIVE STATUS IS NEVER STORED:** whenever liveness or freshness matters,
  DISCOVER it in the same turn: `oc-roster live` for sessions (the DERIVED roster — ledger claims + worktree state + session-DB liveness + forum bindings; `oc-roster classify` for ACTIVE/IDLE/UNKNOWN, `oc-roster work`/`claims` for the other two signals). Role resolution is NOT `oc-roster` — use `oc-ledger roster --live --role <role>`; `oc-roster`'s `--role` flag is a supported delegation to `oc-ledger roster --live --role <role>` (verified live 2026-09-20: `--role hq` returns the row; only the BARE `--role` fails, rc 2 `--role needs a value`),
  `gh run list` for CI, `git ls-remote` for refs.
- Seed/update ONLY from proven facts (full schema + write rules now live in
  triage.md §Duty T6 — lens B-F10 v0.4.96 cross-role move).
- **REGISTRY WRITES BELONG TO TRIAGE (owner law 2026-09-07, v0.4.91):** claims,
  ack rows, event notes, roster enrollment, `confirmed` flags — Triage writes
  them all (it already did the operational writes; this closes the split).
  HQ's only remaining touchpoint: version-published rows during Duty 1 (sync
  evidence, not registry management). (v0.4.86 transferred editor CREATION to
  Triage; this completes the registry half.)
- **Version-skew policy (decision 2a, grace):** any version stays valid until
  the worker acks; skew is monitored, not enforced. Chase only if a worker
  ACTS substantively while >1 version stale.
- **Ack contract (decision 3, REVISED v0.4.91):** acks are NO LONGER EXPECTED.
  Delivery proof = the notify receipt (`session_notify` verdict); comprehension
  guard = disk absorption + `oc-drift-check`. Existing ack rows stay as
  historical evidence; new ones are opt-in, not contract.
- Auto-discovery (decision 5): on every roster sweep, an unknown active
  session becomes a provisional registry row, confirmed by its first signed
  commit (Session-Id trailer = identity proof).
- **Checkable Completion Formula**: `DONE = oc-roster live / classify executed same-turn + registry state verified via oc-ledger roster --live.`

## Duty 3 — Push updates to idle workers

| Situation | Action |
|---|---|
| Routine version bump (default, v0.4.172) | **JIT pull-absorption** (advisory `n=5322`, owner order 2026-09-14): Routine version bumps do NOT emit mass fanout pings across dormant lanes. The core daemon harness automatically injects a JIT turn-start skill hint whenever an active skill diffs on disk (shipped in `#210`, commit `acb8c5e6`). Active lanes absorb the diff and execute `oc-drift-check <uuid> --ack` at their own natural boundaries without session churn. |
| Breaking security/process shift or fleet halt | **`[ALL]` broadcast wave (`turn-end`)** via `oc-notify-fanout --title "CRITICAL SKILL SHIFT — v<v>"` — rules whose absence produces immediate procedural or security breaches. `now` is RETIRED and fails the delivery outright (#373); `interrupt` is the URGENT tier (`interrupt: true` is its legacy alias) — precedence framing, never deferred, but NOT pre-emption. A CRITICAL wave sends `turn-end` like any other, and against a mid-turn target it QUEUES for the next tool-loop boundary regardless of tier: the tier changes the FRAMING the target sees at that boundary, not the boundary itself. |
| Explicit owner reload order | **`PUSH-ALL-QUIET` broadcast wave** via `oc-notify-fanout --title "SKILL CHANGE — v<v>"` (generates per-lane briefs, self-uuid reload instruction, DB-validated targets, ledger stamp). |
| Confirm law (probe-verified 2026-09-07; mode enum corrected 2026-09-19) | `delivery=quiet` + `confirm=true` is a NO-OP watch — quiet always returns instantly with a deferred verdict + notify_id; confirm only watches synchronous states. Routine pushes: `turn-end` (THE default), NO confirm, fire-and-forget (drift-check is the comprehension guard). Mode semantics: `fleet-directives.md §Cross-lane message delivery discipline` (canonical). There is NO blocking-watch mode: a CRITICAL notify sends `turn-end` like any other, and against a mid-turn target it QUEUES for the next tool-loop boundary regardless of tier |
| Worker >3 versions behind, acting substantively | targeted notify (mechanical drift and ack-row reads don't count) |


Bump propagation mechanics (B-F4 v0.4.96 — moved out of the table cell):
1. **Publish the version to the ledger: `oc-ledger sync --version <v> [--why <provenance>]` — and READ its rc.** The skill-repo commit/tag is NOT the version-published event; only `sync` mints the `skill-bump` row AND the three registry fields (`current_skill_version`, `meta.current_skill_version`, `meta.skill_version`) in one flock'd atomic write. A commit without a sync leaves the registry reading the PREVIOUS version while lanes ack the new one — the fleet is on `<v>` and the ledger still says `<v-1>`. `sync` is battery-gated and refuses `rc 7` on unrelated dirty paths (stray-guard, v0.4.157); **a refusal writes NOTHING and is silent unless someone reads rc/stderr**, so a bump that ships law text + a fanout brief and never reads the sync's rc has minted NO version-published event. Origin: v0.4.164 shipped its law text and its fanout brief and 27 lanes acked it with no `skill-bump` row (gap reported first-hand by lanes `530c29ec` + `facd50af`). **The consumer half (Reviewer-J inverse, v0.4.165):** `oc-ledger check-version` — rc 1 when any of the three fields disagrees with `SKILL.md` — is a pure function of on-disk state and had NO actor assigned to it. On the Duty-3/4 cadence READ it, and treat `rc=1` as a bump-propagation failure to heal with `oc-ledger sync --version <SKILL.md version>`, not as a worker defect.
2. Commit BOTH git repos — skill-dir: one commit per bump; state-dir: one
   commit per ledger stamp, inside the same flock as the write (git-history regime).
3. TOOL-written stamps (`oc-deploy` swap-execute etc.) are committed by the
   HOSTING session — the turn that observes the stamp — bundling its adjacent
   stamp if both are pending.
4. Pending-stamp sweep = `oc-ledger commit-pending [--bundle]`, on the
   Duty-3/4 cadence (design: `oc-work/oc-ledger-design-20260829.md`).
5. Fan-out to all non-dormant workers — `oc-notify-fanout --title "…"` in `quiet`
   mode (a batch notice whose ack contract is the ledger — the one case where `quiet`
   is correct). **READ ITS RC and the per-lane receipt ids.** A non-zero rc, or a
   target list shorter than the intended roster, means the wave did not go out — and
   no later step reports it. No `confirm` (quiet returns a deferred verdict
   immediately; there is no blocking-watch mode).
6. On Duty-3/4 cadence: `oc-ledger confirm` sweep — flip `confirmed` for
   workers whose first signed commit is verified (standing practice, fleet B5
   + Duty-4 proposal, v0.4.96; the flag gap was 4 workers `confirmed:false`).

> Delivery discipline per session-notify.md §Tool mechanics (DELIVERY ≠
> QUEUE ACCEPTANCE canonical there): live roster check SAME turn; silent
> target → one retry → ledger event note; `target_session` = FULL UUID only.
> Delivery cadence and mode semantics: `fleet-directives.md §Cross-lane message delivery
> discipline` (canonical). `turn-end` IS the default; `now` is RETIRED and fails the
> delivery outright.
- **Checkable Completion Formula**: `DONE = oc-notify-fanout (or session_notify) executed + same-turn receipts verified (target confirmed woke or deferred receipt id recorded).`

## Duty 4 — Poll workers for skill input (Direct Persistence & Ledger Intake)

Cadence: STANDING — after every FIVE shipped version bumps (shared trigger
with Duty 6), on owner request, or when incidents cluster without a rule.

**Zero Session Notify Law for Worker Proposals (owner order 2026-09-11):**
Workers do NOT submit Duty 4 proposals via `session_notify` to HQ. Inbound notify
floods pollute HQ's context window, accelerate context compactions, and duplicate
the freeze-ACK anti-pattern. Workers write proposals directly to disk in the
cycle review directory (`~/.opencrabs/profiles/ops/opencrabs-dev/reviews/<cycle-id>/proposals/<session-uuid>.md`)
or record them onto the ledger via `oc-ledger stamp proposal "ADD|CHANGE <rule> in <file+section> BECAUSE <evidence>"`.

1. Live roster FIRST (`session_search` / `oc-ledger roster --live`, same turn).
2. Broadcast poll notification via `oc-notify-fanout`: instruct non-dormant editors
   to write proposals directly to disk (`$REVIEW_DIR/proposals/<uuid>.md`) or append to the ledger.
   Proposals must use strict format: `ADD|CHANGE <rule> in <file+section> BECAUSE <gap actually hit>`
   with dates and evidence. Workers NEVER edit skill files themselves.
3. Intake & Closure Determination:
   - **Mechanical State Check**: HQ reads the submissions in a single batch turn from disk (`ls $REVIEW_DIR/proposals/`)
     and ledger events (`oc-ledger events --kind proposal`).
     **Window-safe read:** `events` counts `--n` rows back from the NEWEST (default 20 — see the `--n N` usage note under `oc-ledger events`), so a
     **kind-filtered** read is safe — the filter runs BEFORE windowing and cannot be starved by unrelated rows. A
     **marker-prefix** read over `--kind note` is NOT safe: by cycle close the `note` tail no longer holds the proposals,
     and `rc=0` WITH rows reads as "none submitted" (the false-negative class, reported by lane `1a63f103`). For the
     historical `duty4-proposal` note-mirrors (n=3555/3556/3557/3558) use a sufficient window —
     `oc-ledger events --kind note --n 500 | grep duty4-proposal`, or `--since <cycle-start>`. Disk channel #1
     (`ls $REVIEW_DIR/proposals/`) is authoritative and always current.
   - **Quorum / Window**: All active lanes have written their file/ledger entry OR a bounded window
     (e.g. 15–30 minutes / post-harvest boundary) expires. Lanes that submit nothing are treated as having no gaps.
4. Validate every proposal three ways BEFORE reporting: disk truth (rule may
   already exist), live/log evidence (gap must have really happened), coherence
   with existing gates.
5. Consolidated verdict table to the owner; **HQ lands every ACCEPTED proposal itself — in its entirety, in the cycle's version batch, with NO design gate, NO plan card and NO owner approval (owner order 2026-09-25: findings "not wasted but fixed in their entirety", human gate removed from the Duty 4/6 fixing process). The verdict table is the RECORD of what was decided and landed, not a request, and it does not wait.** Every accepted proposal lands, or the cycle is incomplete; a proposal whose fix belongs to another owner (daemon/carrier source, upstream repo, `tools/**` code) is ROUTED to that owner and recorded as routed. Canon: `fleet-directives.md §Discussion links + fix-approval gate` (the Duty 4/6 EXCEPTION bullet).
6. Convergence beats volume: several workers burning independently on the same
   gap is stronger signal than any single proposal — merge them into one rule.
- **Checkable Completion Formula**: `DONE = poll fanout dispatched + submissions read from reviews/<cycle-id>/proposals/ and oc-ledger events --kind proposal + verdict recorded in review state.`

## Duty 5 — Procedure rulings (decision 6)

On protocol disputes — role boundaries, exception clauses, gate semantics —
HQ issues BINDING rulings, each logged as an event entry in
`workers-ledger.json` (`rulings`) with evidence and reasoning. Owner veto
overrides retroactively. The standing lesson — never deny from codified text without
checking the live record — lives in `SKILL.md §Hard rules (CONSENT REGISTER)`; the
precedents behind it are in `CHANGELOG.md`.
- **Checkable Completion Formula**: `DONE = ruling reasoning recorded in workers-ledger.json rulings event + notification delivered to involved lanes via session_notify.`

## Duty 6 — Periodic subagent skill review

Cadence: after every FIVE shipped version bumps, on owner request, or when an
incident suggests drift.

Method:
0. **Cycle State Durability & Step-0 Recovery** (v0.4.170, owner order 2026-09-13; **instrumentation schema FROZEN v0.4.227**, HQ ruling 2026-09-20 answering lane `ef83024b`):
   Every Duty 4+6 cycle maintains a machine-readable state file at `reviews/<cycle-id>/state.json` (under `$OC_DEV_STATE`).
   **TWO `reviews/` ROOTS EXIST AND ONLY ONE IS LIVE (v0.4.258, from Duty-6 cycle `20260925-c24` finding D-F5).**
   The **state-repo root** (`~/.opencrabs/profiles/ops/opencrabs-dev/reviews/`) is CANONICAL — it holds the live
   cycles and is what `$OC_DEV_STATE` resolves to. The **skill-repo root**
   (`~/.opencrabs/profiles/ops/skills/opencrabs-dev/reviews/`) is FROZEN EVIDENCE: keep it, never sweep it,
   never write a new cycle into it. Measured 2026-09-25: 26 cycle dirs live vs 13 frozen, and **three cycle ids
   exist in BOTH roots** (`20260915-c17`, `20260915-c18`, `20260919-c21`) — so a cycle id alone does not
   identify a root, and a sweep keyed on the id would hit the frozen copy. **Always pass `--dir` explicitly:**
   `oc-review-persist`'s own `DEFAULT_DIR` is the SKILL root, which diverges from this law (routed to the
   Toolsmith as a `tools/**` defect) — a run without `--dir` writes evidence to the frozen tree.
   **FROZEN SCHEMA — these five field names are law. Instrument against them; do NOT invent parallel spellings.**
   `{ "cycle_id": "<id>", "cadence": "<cadence-string>", "started_at": "<ts>", "ended_at": "<ts|null>", "duration_review_min": <num|null>, "duration_cycle_min": <num|null>, "status": "IN_PROGRESS|COMPLETED", "proposals": [...], "lenses": { "<lens>": { "status": "PENDING|COMPLETED", "report_path": "...", "verdict": "..." } }, "codification_plan": [...] }`

   | Field | Rule it encodes |
   |---|---|
   | `cycle_id` | **ONE canonical id, minted ONCE at cycle init and written into BOTH stores** — `state.json` AND a ledger row at cycle open — validated on write so the two cannot diverge. Kills the disk-vs-ledger id drift (`20260919-c21` vs `20260919-cycle`) and the negative span that id normalisation manufactured. |
   | `duration_review_min` | Review start → reports persisted. **This is the number the owner asked for.** |
   | `duration_cycle_min` | Cycle start → cadence close stamp. What existed before, previously mislabelled as *the* duration. |
   | `ended_at` | Explicit terminal timestamp. **NEVER `updated_at`** — 6 of 13 state files never advanced it and two showed a 0.0-min span, so a reader could not tell "finished" from "untouched". |
   | `status` | Terminal ENUM, exactly `IN_PROGRESS \| COMPLETED`. Never free text (`COMPLETED` / `VALIDATED` / `reports_persisted` / `intake_complete` were all observed, plus a contradiction where `state.json` read `IN_PROGRESS` while the ledger close row already existed). |

   **Two matching rules bind the step-8 close stamp** (same ruling):
   - The cadence-reset stamp is matched as an **ANCHORED whole-row pattern** — `^v<digits>.<digits>.<digits> ACCEPTED` — never a loose substring.
   - A note that withholds an END for a cycle **must BEGIN with the literal token `WITHHELD:`**, so a loose grep cannot harvest an END from a row whose whole point is that no END was written.

   Before spawning reviewers or codifying findings, HQ initializes `state.json`.
   **Step-0 Recovery Mandate:** After ANY context compaction or session restart during Duty 4+6, HQ must first check for an existing `reviews/<cycle-id>/state.json` before re-querying proposals, re-spawning reviewers, or re-drafting plans. Reading `state.json` restores the exact cycle state, preventing redundant tool calls or loss of completed work across compactions.

   **Mechanical corpus pack at cycle open** (owner directive 2026-09-25, TRIAL; lane `ef83024b` instrument). Before spawning reviewers, run the law-corpus pack keyed to the SAME cycle id, so the mechanical evidence exists before any lens is briefed:

   `python3 ~/.opencrabs/profiles/ops/projects/jev-bloat-review/pilot/pack.py --cycle-id <cycle-id> --cycle-opened-at <started_at> --corpus-root <skill dir> --reviews-root <state dir>/reviews --exclude CHANGELOG.md`

   Evidence lands at `reviews/<cycle-id>/evidence/`. **Record the corpus hash the pack prints — a report is valid only for that hash.** A re-run of the SAME cycle id is byte-identical by construction (the open instant is an input, never the wall clock). Called by **ABSOLUTE PATH for the trial**: its module set is 9+ files in a project dir, so routing it into `tools/` is a separate decision, not a packaging detail.

   **Coverage limit, stated so it is not assumed:** the pack reads top-level `*.md` only, so `tools/docs/RC-CONTRACT.md`, `tools/docs/HEALTH-CHECKS.md` and `tools/docs/HEALTH-CLASSES.md` (~139 KB of law) are OUTSIDE the corpus until the manifest leg lands. A cycle that needs those files read them directly. **A missing or failing pack is REPORTED, never silently skipped** — the lenses then run on semantic evidence only, and the cycle record says so.
1. Reviewers are READ-ONLY SUB-AGENTS (spawn read_only=true, allow_nested=false),
   one per lens (A/B/C/D/E/F/G/H/I/J + standing brain-scrub); they NEVER edit skill files. Duty-6 reviews
   are ALWAYS sub-agent work, never HQ-only inline reading. Same-day
   second passes of one lens suffix the report name (`-run2`) and split scopes
   (`B2`/`A2`) — the lens catalog (review-lenses.md) is unchanged by that;
   family map letters stay A–J. Findings
   must carry verbatim quotes; HQ verifies every accepted quote against
   disk before acting. Hollow report → ONE retry with the prompt narrowed to
   that single lens; a second hollow result unlocks inline fallback, which
   must be flagged as such in the review record.
2. Split lenses for independence by family (DOCS=A,B,G · TOOLS=C,E,F ·
   MECHANICAL=J · ARTIFACTS=D+H · META=I) — letters keep chronological birth order (stable
   report/persist keys, not an ordering). FULL LENS CATALOG: `review-lenses.md`
   (same dir as this file) — read it before spawning reviewers; each brief
   names the lens scope and evidence format, and the briefs that carry an exclusion
   clause state it (C, E). **The cycle's mechanical slice is passed in the SPAWN
   PROMPT, not carried by this catalogue** — the catalogue is cycle-invariant, while
   the slice (the sentence-match, near-title and dead-reference legs for that family's
   files, with the corpus hash) comes from `reviews/<cycle-id>/evidence/`. Layer 2
   (semantic mechanisation) is **REPORT-ONLY** — it never
   creates or routes a finding: its gate failed a pre-registered test (precision 0.111 /
   recall 0.126 against bars 0.70 / 0.40, n=66). A reviewer that validates a mechanisation
   opportunity must name the tool owner AND the command, never the idea alone.

3. PERSISTENCE (persist-first write-through, owner law 2026-09-08, v0.4.116):
   the SPAWN PROMPT instructs each reviewer to write its FULL report to
   the cycle report dir (e.g. `/tmp/duty6/`, `/tmp/duty6-c2/` —
   cycle-suffixed) as `lens-<X>.md` before finishing — the reviewer's own
   file write is the PRIMARY copy; HQ's persist step
   (`oc-review-persist <lens> @<file>`, re-read-verified + sha256-indexed)
   becomes a VERIFIED COPY (byte-count + sha check), never the only copy.
   A report existing only in push-transit does not count as delivered.
   Fallback (write-less reviewers, demonstrated 4/4 cycle-2): a read-only
   reviewer cannot write files — HQ's persist-on-receipt
   (`oc-review-persist`, byte-count + sha256 verified) counts as delivery
   when the reviewer toolset has no file-write capability; the report text
   arrives in the spawn-result push and is persisted verbatim.
4. HQ VALIDATES every finding with the poll triple-check (disk truth /
   evidence / coherence): ACCEPT · KERNEL (already covered) · REJECT (reason
   recorded, never silently dropped).
5. **HQ lands EVERY accepted finding in its entirety — mechanical AND semantic — as ONE version batch, with NO design gate, NO plan card and NO owner approval (owner order 2026-09-25: findings "not wasted but fixed in their entirety", human gate removed from the Duty 4/6 fixing process).** Nothing is deferred to the owner as a "proposal": the fix shape is HQ's decision, and the verdict table is the RECORD of what landed, not a request. **COMPLETENESS IS THE CHECK:** the verdict MUST enumerate every finding by ID and assert that the partition sums to the census count — an accepted finding with no landed home is a cycle-completion FAILURE, never a scheduling choice. A finding whose fix belongs to another owner (daemon/carrier source, upstream repo, `tools/**` code) is ROUTED to that owner and recorded as routed. This does NOT widen HQ's authority: scope stays this factory's law surface, and the owner-gated actions in `AGENTS.md` remain gated. Canon: `fleet-directives.md §Discussion links + fix-approval gate` (the Duty 4/6 EXCEPTION bullet).
6. Verdict table posts to owner topic 30220; registry notes updated.
7. **Reviewer-performance loop:** after every pass, HQ folds
   reviewer-execution lessons into the lens briefs and tool guarantees.
   Examples: compaction amnesia → identity-guard clause in the prompt;
   mis-scope → narrower lens brief; hollow reports → sharper evidence-format
   requirement; failed spot-checks → tighter citation rule. Edits ship with
   the next version batch, attributed to the reviewer that produced the
   evidence. PLUS THE LENS CENSUS (v0.4.81): every consolidated verdict
   appends a per-lens census computed from the already-persisted reports —
   yield (findings accepted), overlap (convergence with another lens), cost
   (spawns/waves lost). Standing triggers, owner-gated: clean x2 cycles →
   automate the lens's mechanical half or shrink the brief; convergence with
   another lens x2 → merge or sharpen the boundary; object list stale at
   spawn → re-brief BEFORE spawning. Anti-rules: no lens-per-incident
   (incidents become rules/proposals, not lenses); no auto-growth. Lenses
   are quality dimensions (stable, few); objects change every batch and are
   re-derived from the skill root at spawn time.
8. **Duty-6 Ledger Cadence Reset Stamp (owner order 2026-09-15):** Upon completing the cycle (reports persisted, master verdict written, codifications applied or planned), HQ **MUST explicitly stamp the cycle close note** onto the ledger:
   `tools/state/oc-ledger stamp note "v<version> ACCEPTED — Duty 6 Cycle <cycle-id> closed" --by "hq <uuid>"`
   This stamps the mechanical boundary recognized by `oc-ledger cadence` (`^v[0-9]+\.[0-9]+\.[0-9]+ ACCEPTED`), resetting the review cadence counter from `FIRE` back to `0/5 WAIT`. Without this stamp, `oc-ledger cadence` will fail to reset and will continuously report overdue review cycles.
- **Checkable Completion Formula**: `DONE = every catalog lens persisted via oc-review-persist (assert `./tools/state/oc-review-persist check-cycle reviews/<cycle-id>` rc 0 — the tool derives the lens set from the catalog AT GATE TIME; NEVER hardcode the count here) + receipts logged in skill-review-index.log + master verdict compiled in reviews/<cycle-id>/VERDICT.md + review manifest marked COMPLETED in reviews/<cycle-id>/state.json + oc-ledger stamp note "v<version> ACCEPTED — Duty 6 Cycle <id> closed" executed (resetting cadence to 0/5 WAIT).`

Rationale: HQ authors most rules — author-blindness is structural.
Independent subagent eyes keep the set honest, and **HQ's own completeness check keeps it whole** — the owner gate was REMOVED from the Duty 4/6 fixing process on 2026-09-25, so the reviewers' findings are landed in their entirety rather than triaged down to what an owner happened to approve.

## Duty 7 — RETIRED: Direct Process-Owner Feedback (owner order 2026-09-14, v0.4.176)

The centralized Idea Box coordination queue is RETIRED. Feedback, quirk reports, and improvement proposals route directly to the respective process owner without intermediate queuing:
- **Tool anomalies & CLI tooling**: Route directly to the active **TOOLSMITH** lane (`session_notify` or ledger).
- **Skill directives & process governance**: Route directly to **HQ** (`reviews/<cycle-id>/proposals/` or `oc-ledger stamp proposal`).
- **Domain/subsystem code & features**: Route directly to the owning **Editor / Domain Lane** via the fork issue tracker.

Legacy references to "hq.md Duty 7" are retired.

### Related Triage operations (ownership pointers)
- **Backlog assignment (Duty T5, v0.4.92):** post-compaction sweep of OPEN fork issues against ledger claim-refs; unclaimed → route or surface here for dispatch.
- **Telegram-law TOOL_ACCUM enforcement (Duty T4, v0.4.43):** OPERATES in the TRIAGE lane since v0.4.86 — full procedure in `triage.md` §Duty T4. Repeat offenders escalate HERE for review-toggle decisions.

**Upstream-relations ownership (v0.4.176)**: All upstream lifecycle tracking (upstream delta watch, upstream PR census, maintainer dependency tracking) is consolidated in **Triage** (`triage.md §Duty T4`). Fork branch lifecycle / clean sweep is executed by Triage (`triage.md §Duty T4`). **The HARVEST lane exclusively authors and files upstream PRs** (`harvest.md`); editors stop at smoke evidence (owner order 2026-09-24 centralising harvest).

## Upstream sync — watch & governance (sync execution delegated to Triage)

Sync execution is DELEGATED TO TRIAGE (owner order 2026-09-11: "You should not do these merges - delegate to triage"; HQ does not execute syncs). **SYNC LAW canonical = `upstream-merge-runbook.md §Remotes & sync` (REBASE model); executing procedure: `upstream-merge-runbook.md` (managed by Triage via `triage.md §Duty T7`).**

HQ retains watch and governance authority only:
- **Watch**: Monitor upstream delta (`./tools/harvest/oc-upstream-delta`) and notify Triage to execute rebase sync when upstream advances.
- **Rulings**: Rule on non-trivial merge blockers or semantic conflicts escalated by Triage.
- **Parity verification**: Ensure carrier proof-dispatch runs clean after rebase cutover. Procedural execution steps live exclusively in `upstream-merge-runbook.md` and `triage.md`.

## Detached command execution (background: true)

Long-running commands (>60s, test batteries, carrier/CI waits, heavy audits) MUST run detached via the bash tool parameter `background: true`.

- **Auto-resume & injection:** The daemon tracks detached executions natively and auto-resumes the session upon process completion. Do NOT hand-roll polling loops or detached background daemons.
- **Terminal state:** CI waits must gate completion on terminal state (`completed` status; `success`/`failure` conclusion).
- **Checkout-ref verification:** Checkout log lines identify the tested tree, but comparing them against the expected head SHA by hand is the agent-memory-as-gate-input defect (lens J / F27). Run `tools/ship/oc-job-verify <run-id> <source-ref>` — **rc 4 means the run's identity is reported but never trusted**; on rc 4 the verdict is not final evidence.
- **REST v3 keys are snake_case:** In `gh api` `--jq` filters, `run_started_at`/`updated_at` work; camelCase (`runStartedAt`) silently evaluates to null.

## Cadence boundary is stamped at review consolidation

`oc-ledger cadence` = count of `skill-bump` events since the last BOUNDARY event. **The boundary predicate is a `kind=note` row whose text BEGINS `<version> ACCEPTED`** — the tool's own regex is `^v[0-9]+\.[0-9]+\.[0-9]+ ACCEPTED` (in `cmd_cadence`, `tools/state/oc-ledger:1278`), taken as the MAX `n`; `review-battery` and legacy `skill-review*` rows are consulted **only when NO note close exists at all** (`:1280`), which is the pre-close-epoch fallback the v1.1 KINDS vocabulary can no longer produce — known drift, do not stamp those. **Consequence, and it is the whole point of this paragraph: the close form is `oc-ledger stamp note "v<version> ACCEPTED"`, NOT `oc-ledger stamp review-battery`.** This section prescribed the `review-battery` form until v0.4.243, and following it literally would have silently FAILED to reset the counter while the stamp itself returned success — a green receipt on a boundary that never moved (found by Duty 4 cycle `20260922-c22`: the prose was stale, the tool was right). Lesson 2026-09-01: the Duty 4+6 verdict was consolidated but never stamped → counter read 24/5 FIRE on stale data. Rule: every consolidated review verdict ends with the boundary stamp BEFORE reporting the cadence state; never narrate a cadence reading without confirming the boundary row exists.

## Rule-text provenance — CHANGELOG at ship time

Rule text carries NO biography — provenance (date, origin quote, war story)
lives in CHANGELOG.md, written at ship time of the version carrying the
rule. This resolves the Duty-1 "every rule carries its war story" clause in
favor of lens A: rules stay lean, history stays in CHANGELOG.
