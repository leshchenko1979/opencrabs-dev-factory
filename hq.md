# HQ — skill maintenance & worker coordination

**Load only after SKILL.md confirmed the role is HQ.** This is HQ
session's standing role. Interrupt-shaped duties (fix routing, enforcement
patrols) operate in the TRIAGE lane since v0.4.86
(owner "Go with Option A" 2026-09-06) — procedure: `triage.md`; batched
escalations from that lane land here. Skill-file authorship stays SOLELY
with HQ (single-writer law unchanged; v0.4.87 carve-out: the
TOOLSMITH lane owns `tools/` CODE — skill markdown never leaves this lane, except the per-instrument law files under `docs/instruments/` (see the EXCEPTION bullets in `fleet-directives.md`)).

**RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `hq.md`, `fleet-directives.md` in `active_skills`; re-read IN FULL on compaction/spawn).

Scope: own the skill set (full census: `SKILL.md §Hard rules` — the one home), keep every worker ON the current skill version, and
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

**MOVED 2026-09-27.** The intake contract — the channels a proposal arrives on, the closure
determination, the validation triple-check, the per-lens census and the checkable completion
formula — now lives at `docs/instruments/review-rotation.md` **in the meta-factory repo
(`/root/agent-factories/`), NOT resolvable from this skill tree**. Authored by the Review
Rotation instrument lane (owner order 2026-09-27). Do not restate the contract here — a second
copy is the drift this carve removed.

> **⚠ NOT OPERATIVE FOR THIS FACTORY (Duty-6 c27 I-1, measured 2026-10-01).** The carve above
> names `tools/review.py` as THE executable. **That file does not exist in this skill tree**, and
> the real engine (`/root/agent-factories/tools/review.py`) hardcodes its cycle root to its own
> repo (`REPO_ROOT = Path(__file__).resolve().parent.parent`), so it answers *"Cycle … not
> found"* about cycles that are sitting on disk here. The instrument's own adoption census
> reports this factory `0/5 … ABSENT`, and its lens catalog (14 lenses / 6 families) is not ours
> (11). **The OPERATIVE carriers at this factory are `tools/state/oc-review-persist` and
> `tools/state/oc-review-persist check-cycle`, with the in-corpus catalog `review-lenses.md`.**
> The pointer above is kept because the contract is real and lives elsewhere; its claim of a
> WIRED executable does not survive measurement.

What STAYS at this factory, because it is process law about US and not about the instrument:

- **Cadence: STANDING** — after every FIVE shipped version bumps (shared trigger with Duty 6),
  on owner request, or when incidents cluster without a rule.
- **Zero Session Notify Law for Worker Proposals (owner order 2026-09-11):** workers do NOT
  submit Duty 4 proposals via `session_notify` to HQ — inbound notify floods pollute HQ's
  context window, accelerate compactions and duplicate the freeze-ACK anti-pattern. Workers
  write proposals to `$REVIEW_DIR/proposals/<session-uuid>.md` or record them on the ledger via
  `oc-ledger stamp proposal "ADD|CHANGE <rule> in <file+section> BECAUSE <evidence>"`.
  Workers NEVER edit skill files themselves.
- **The channels are DECLARED, not inferred.** The cycle declares the proposal directory and the
  ledger kind it reads; the instrument REFUSES on an undeclared or absent channel rather than
  reading nothing and reporting clean.
- **Landing discipline: see §Duty 6 — ONE version batch, no design gate, no plan card, no owner
  approval; a fix whose owner is elsewhere is ROUTED and recorded as routed.**
- **Checkable Completion Formula** (restored on-file, Duty-6 c28 G4 — the copy the 2026-09-27 carve moved to the unreachable meta-factory path left this duty with none): `DONE = every worker proposal for the cycle is read + each finding re-verified first-hand (an unreproduced finding is NOT a finding) + accepted findings landed in the Duty-6 version batch OR recorded as routed with their owner named + registry notes updated.`
## Duty 5 — Procedure rulings (decision 6)

On protocol disputes — role boundaries, exception clauses, gate semantics —
HQ issues BINDING rulings, each logged as an event entry in
`workers-ledger.json` (`rulings`) with evidence and reasoning. Owner veto
overrides retroactively. The standing lesson — never deny from codified text without
checking the live record — lives in `SKILL.md §Hard rules (CONSENT REGISTER)`; the
precedents behind it are in `CHANGELOG.md`.
- **Checkable Completion Formula**: `DONE = ruling reasoning recorded in workers-ledger.json rulings event + notification delivered to involved lanes via session_notify.`

## Duty 6 — Periodic subagent skill review

Cadence: shared trigger with Duty 4 (see §Duty 4). The cadence is COMPUTED from the ledger, never
narrated — see `docs/instruments/review-rotation.md` and the section below.

**MOVED 2026-09-27.** The review contract — step-0 recovery, the frozen state schema and its
field rules, the anchored boundary matching, the read-only sub-agent reviewers, the family
split, persist-first write-through, the validation triple-check, the reviewer-performance loop
and the lens census — now lives at `docs/instruments/review-rotation.md` **in the meta-factory
repo (`/root/agent-factories/`), NOT resolvable from this skill tree**. The instrument names
`tools/review.py` (`step0` · `brief` · `record` · `waive` · `verify` · `compile` · `cadence` ·
`close` · `migrate`) with `docs/review-cycle.schema.json` as its state schema — **but that
executable is NOT operative for this factory; see the ⚠ banner in §Duty 4 above.** The
operative carriers here are `tools/state/oc-review-persist` and its `check-cycle` gate, against
the in-corpus catalog `review-lenses.md`.

What STAYS at this factory:

- **HQ lands EVERY accepted finding in its entirety — mechanical AND semantic — as ONE version
  batch**, with NO design gate, NO plan card and NO owner approval (owner order 2026-09-25:
  findings "not wasted but fixed in their entirety"). Nothing is deferred to the owner as a
  "proposal". A finding whose fix belongs to another owner is ROUTED and recorded as routed.
  Scope stays this factory's law surface; the owner-gated actions in `AGENTS.md` remain gated.
- **The verdict table posts to owner topic 30220**; registry notes updated.
- **The ledger cadence reset stamp is ours and is mandatory** — see the section below. Without
  it the counter never resets and continuously reports overdue cycles.
- **Two `reviews/` roots exist and only one is live.** The STATE-repo root
  (`~/.opencrabs/profiles/ops/opencrabs-dev/reviews/`) is canonical and is what `$OC_DEV_STATE`
  resolves to; the skill-repo root is FROZEN EVIDENCE — keep it, never sweep it, never write a
  new cycle into it, and always pass `--dir` explicitly.
- **The corpus pack is a TRIAL, not this instrument** — it runs by absolute path from its own
  project dir, and its routing into `tools/` is a separate decision.
- **KEY-SET CLOSURE STAYS HERE.** No instrument at THIS factory carries the "every key ⊆ the
  ruled set" closure: the meta-factory engine's `review.py schema` (which would emit it) is NOT
  operative here (see the ⚠ banner in §Duty 4), and `tools/state/oc-review-persist` emits no
  cycle-state schema — so an unknown top-level key such as c25's `corpus_hash` is accepted
  silently. Until a carrier closes it, a cycle open/close must assert key-set closure by hand.
  Stated because a carve must not delete a live rule that has no mechanical carrier. (Tool half
  — a `validate` verb emitting `additionalProperties: false` on the cycle schema — ROUTED to
  Toolsmith, c27 J-1.)
- **Checkable Completion Formula** (restored on-file, Duty-6 c28 G4 — the 2026-09-27 carve moved the contract to the unreachable meta-factory path and left this duty with none): `DONE = all catalog lenses A–J + brain-scrub dispatched and every report persisted under $OC_DEV_STATE/reviews/<cycle>/reports/ + oc-review-persist check-cycle returns rc 0 (a deliberately-skipped lens carries a waivers.log row, not a hole) + every load-bearing finding re-verified first-hand + accepted findings landed as ONE version batch + verdict table posted to owner topic 30220 + cadence reset stamped (oc-ledger stamp note "v<version> ACCEPTED").`
## Duty 7 — RETIRED (owner order 2026-09-14, v0.4.176)

Duty 7 and the centralized Idea Box coordination queue are RETIRED; feedback routes directly to the
process owner. **The routing table itself is NOT retired and is canonical at
`fleet-directives.md §Unified Event Capture`** (tool anomaly → TOOLSMITH · skill/governance proposal
→ `reviews/<cycle-id>/proposals/` or `oc-ledger stamp proposal` · domain code → the owning Editor
lane via the fork tracker). Legacy references to "hq.md Duty 7" are retired.

## Related Triage operations (ownership pointers)
- **Backlog assignment (Duty T5, v0.4.92):** post-compaction sweep of OPEN fork issues against ledger claim-refs; unclaimed → route or surface here for dispatch.
- **Telegram-law TOOL_ACCUM enforcement (Duty T4, v0.4.43):** OPERATES in the TRIAGE lane since v0.4.86 — full procedure in `triage.md` §Duty T4. Repeat offenders escalate HERE for review-toggle decisions.

**Upstream-relations ownership (v0.4.176)**: All upstream lifecycle tracking (upstream delta watch, upstream PR census, maintainer dependency tracking) is consolidated in **Triage** (`triage.md §Duty T4`). Fork branch lifecycle / clean sweep is executed by Triage (`triage.md §Duty T4`). **The HARVEST lane exclusively authors and files upstream PRs** (`harvest.md`); editors stop at smoke evidence (owner order 2026-09-24 centralising harvest).

## Upstream sync — watch & governance (sync execution delegated to Triage)

Sync execution is DELEGATED TO TRIAGE (owner order 2026-09-11: "You should not do these merges - delegate to triage"; HQ does not execute syncs). **SYNC LAW canonical = `upstream-merge-runbook.md §Remotes & sync` (REBASE model); executing procedure: `upstream-merge-runbook.md` (managed by Triage via the `triage.md` prologue — "Upstream sync: delegated to Triage"; upstream patrols in `triage.md §Duty T4`).**

HQ retains watch and governance authority only:
- **Watch**: Monitor upstream delta (`./tools/harvest/oc-upstream-delta`) and notify Triage to execute rebase sync when upstream advances.
- **Rulings**: Rule on non-trivial merge blockers or semantic conflicts escalated by Triage.
- **Parity verification**: Ensure carrier proof-dispatch runs clean after rebase cutover. Procedural execution steps live exclusively in `upstream-merge-runbook.md` and `triage.md`.

## Detached command execution (background: true)

Long-running commands (>60s, test batteries, carrier/CI waits, heavy audits) MUST run detached via the bash tool parameter `background: true`.

- **Auto-resume & injection:** The daemon tracks detached executions natively and auto-resumes the session upon process completion.
- **Terminal state:** CI waits must gate completion on terminal state (`completed` status; `success`/`failure` conclusion).
- **Checkout-ref verification:** Checkout log lines identify the tested tree, but comparing them against the expected head SHA by hand is the agent-memory-as-gate-input defect (lens J / F27). Run `tools/ship/oc-job-verify <run-id> <source-ref>` — **rc 4 means the run's identity is reported but never trusted**; on rc 4 the verdict is not final evidence.
- **REST v3 keys are snake_case:** In `gh api` `--jq` filters, `run_started_at`/`updated_at` work; camelCase (`runStartedAt`) silently evaluates to null.

## Cadence boundary is stamped at review consolidation

`oc-ledger cadence` = count of `skill-bump` events since the last BOUNDARY event. **The boundary
predicate is a `kind=note` row whose text BEGINS `<version> ACCEPTED`** — the tool's regex is
`^v[0-9]+\.[0-9]+\.[0-9]+ ACCEPTED`, taken as the MAX `n`.

**The close form is `oc-ledger stamp note "v<version> ACCEPTED"`, NOT
`oc-ledger stamp review-battery`.** This section prescribed the `review-battery` form until
v0.4.243, and following it literally silently FAILED to reset the counter while the stamp itself
returned success — a green receipt on a boundary that never moved (found by Duty 4 cycle
`20260922-c22`: the prose was stale, the tool was right). Rule: every consolidated review verdict
ends with the boundary stamp BEFORE reporting the cadence state; never narrate a cadence reading
without confirming the boundary row exists.

**The predicate's mechanics are the instrument's** — `review.py cadence`, and
`docs/instruments/review-rotation.md` for the two anchored matching rules. What stays here is the
STAMP, the ledger it lands on and the close ordering above.
## Rule-text provenance — CHANGELOG at ship time

Rule text carries NO biography — provenance (date, origin quote, war story)
lives in CHANGELOG.md, written at ship time of the version carrying the
rule. This resolves the Duty-1 "every rule carries its war story" clause in
favor of lens A: rules stay lean, history stays in CHANGELOG.
