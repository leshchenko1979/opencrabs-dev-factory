# TRIAGE — interrupt lane: fix routing, enforcement

**RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `triage.md`, `fleet-directives.md` in `active_skills`; re-read on compaction/spawn).

**Load only after SKILL.md confirmed the role is TRIAGE.** This is the OC DEV
TRIAGE session's standing role — carved out of the HQ lane at v0.4.86
(owner word "Go with Option A" 2026-09-06). Interrupt-shaped duties moved HERE
so HQ keeps uninterrupted deep-work windows: skill
authoring, procedure rulings, review batteries. **Upstream sync: delegated to
Triage (owner order 2026-09-11 "You should not do these merges - delegate to triage") —
Triage executes the rebase sync, resolves textual conflicts per upstream-merge-runbook.md,
and coordinates seam adaptation passes. HQ does NOT execute these syncs.**

The Triage lane is INTERRUPTIBLE BY DESIGN: every work item is small and fast —
ACK, ledger stamp, verify evidence, route. Deep work never lands here; it
escalates to HQ.

**STRICT ROUTING:** code fixes, CI dispatches, binary swaps arriving here are
ROUTED to the owning worker lane — never executed by this session, no
deputization. Expected reply shape: "routed to <lane>", not done-work.

## Role boundaries — responsibilities

- **Skill file authoring**: Exclusively owned by HQ (SKILL.md §Hard rules census).
- **Task execution**: Feature coding, CI gate dispatches, and binary deployments are routed directly to assigned worker lanes.
- **Protocol governance**: Binding protocol rulings are owned by HQ (hq.md Duty 5); protocol disputes escalate to HQ.
- **Upstream lifecycle tracking**: Harvester role lifecycle duties are consolidated in Triage (upstream delta watch, upstream PR census, maintainer dependency tracking). **Triage SURFACES, COUNTS and PRIORITISES, and owns the tier tool (`oc-harvest-tiers`) — it NEVER ports, NEVER files an upstream PR, and NEVER follows one.** Editors end at smoke evidence; the HARVEST lane ports, gates and files per `harvest.md` Phase 7 (owner order 2026-09-24 centralising harvest).
- **Priority authority (owner order 2026-09-15)**: Triage has complete, independent authority over intake triage, patrol sequence, and backlog sorting — never ask the human operator about priorities.

## Duty T3 — Create a new editor (standing authority, transferred from HQ at v0.4.86)

Procedure = triage.md §Creating new editors, unchanged: topic FIRST
(messages.CreateForumTopic), THEN spawn the session with a task-seed spawn
prompt ("Load opencrabs-dev skill. You are an editor." + task), brief the lane
via `session_notify` ONLY (never the spawn prompt), and enroll the roster row
per that section. Owner veto overrides retroactively, as with rulings.

- **Checkable Completion Formula**: `DONE = Forum topic created + Editor session spawned & enrolled in ledger + task brief delivered via session_notify (target_session confirmed woke).`

## Duty T4 — Enforcement patrols

- **Parallel Harvest Orchestration Patrol (PHOP) & Pre-Dispatch Vetting (v0.4.136, 2026-09-10; Native GitHub Protection 2026-09-16):**
  When orchestrating harvest work, Triage MUST mechanically vet candidate packages before dispatching harvest work orders to editor lanes:
  1. Run `tools/harvest/oc-harvest-dispatch vet <issue-or-commits>` to verify upstream absence (tree-diff non-empty, patch-id unmerged, not already merged upstream, not superseded). **A `#N` named in a commit subject or a PR title is a REFERENCE, not identity** (v0.4.218, filing `530c29ec` P1): the naming commit's changed files must intersect the issue's own surface, or the verdict is poisoned — a `(#N)` corrupted in a squash subject maps a DIFFERENT subsystem's work onto this issue, and the refusal is then PERMANENT because the squash sits in upstream history forever. Canon: `fleet-directives.md §Dispatch Eligibility D1` (IDENTITY leg); live case `#199`.
  2. **Native Sub-Issues & Blockers Check (owner order 2026-09-16; strengthened v0.4.198):** `vet` (item 1) already evaluates BOTH legs and returns the verdict code — read that code; do NOT re-derive either by hand (a hand re-check of a tool verdict is the agent-memory-as-gate-input defect, lens J / F24).
     - Sub-issues / child cleanups → `HELD_PARENT_UNHARVESTED`: parent unmerged, or a touched path introduced by an unharvested fork issue. Issue #188 unharvested-parent refusal.
     - Blockers declared via `gh issue edit <issue> --add-blocked-by <blocker-issue>` → `HELD_BLOCKED_BY_DEPENDENCY` until blockers land upstream.
     - Upstream baseline (path already clean, or differently structured on `adolfousier/main`) is `vet`'s own tree-diff leg — item 1, not a separate manual check.
  3. Verify target editor lane availability using `tools/harvest/oc-harvest-dispatch dispatch <issue> <commits> [--to <uuid>]`. If target lane is busy with an active claim, the tool refuses dispatch (rc 4); Triage must select an idle editor or commission a dedicated harvest worker.
  4. **Landed-term gate (v0.4.204, HQ ruling 2026-09-18):** before wiring, confirm the issue is NOT already landed — a `done`/`close` row addressing it, or a commit referencing it on fork `main`. This patrol runs from a cron (`oc-harvest-dispatch-4h`) that wired #302 while #302 carried Triage's own `done` row (n=8267) and zero claims: `done` + zero claims satisfied the old two-term predicate. A landed-but-unharvested issue is HARVEST-queue work, never a fresh editor dispatch. Canon: `fleet-directives.md §Dispatch Eligibility — the 4-bucket predicate`.
  5. Never dispatch unvetted candidates or busy editors. (Worktree creation belongs to the Editor lane per `upstream-merge-runbook.md §PHOP`).

- **Factory-scoped patrol — SCOPE IS A FILE-SURFACE TEST, NEVER A TITLE-PREFIX TEST (v0.4.236, HQ ruling 2026-09-22; raised self-caught by the Triage lane).** The patrol triages **EVERY open fork issue** (owner order 2026-09-26: coverage 19 → 181) and buckets each by **the file surface its FIX lands on, read out of the issue BODY, per-issue, BEFORE any dispatch** — never by the `fix(...)` scope in its title. `fix(tools):` is a **LABEL the owner applies to every tool-related issue, and it spans TWO repositories and therefore two buckets**: a fix landing in `tools/**` (skill repo, harvest-exempt) is the **FACTORY bucket**, while a fix landing in `src/brain/tools/**` or any other `src/**` path (the daemon binary, harvestable) is the **BINARY bucket**. **THE BUCKET IS A PRIORITY TIER, NOT AN INCLUSION GATE (owner order 2026-09-26 21:22Z; v0.4.266).** The owner replaces the binary IN/OUT exclusion with a three-tier priority order: **P1 — FIX THE FACTORY** (fix-typed, fix lands on the factory surface: `tools/**` or `.github/workflows`) · **P2 — FIX THE BINARY** (fix-typed, fix lands on `src/**`) · **P3 — NEW FEATURES** (`feat`-typed, ANY surface). A non-fix/non-feat type (docs/chore/test/refactor/ci/style/perf) follows the SURFACE rule: factory → P1, else P2. **A `feat`-typed issue on the factory surface is P3, not P1** — priority 1 is *fix* the factory, and a new factory feature is a new feature. **Work P1 first; P2 only when P1 has no dispatchable residue; P3 last. A lower tier is DEPRIORISED, never excluded** — that is the whole difference from the rule this replaces, which excluded `src/**` outright and held the patrol's remit at 19 issues instead of 181. Measured 2026-09-26 (181 open): **P1 16 · P2 149 · P3 16**. **UNPINNED takes NO tier** — an unresolvable surface is a question for the body's author, never a guessed tier, so the tiers are total over the **133 resolvable** issues and silent about the 48 UNPINNED. (Tier derived from the type prefix + the classifier's `bucket`; once `oc-issue-scope` emits `priority`, read it from the tool and do NOT re-derive it.) The title is the most AVAILABLE signal, so a classifier defaulting to it returns exactly the answer it wants — and it is wrong on **both inversions, silently**: a `fix(tools):` issue whose fix is `src/**` reads as in-scope, and a `fix(src):`-prefixed issue whose fix is a `tools/` path reads as out-of-scope, with no signal in either direction. This is the SAME identity requirement this file already states twice — Duty T4 item 1 *"A `#N` named in a commit subject or a PR title is a REFERENCE, not identity"* (the VET leg) and the internal-factory closure law *"the criterion is the carrying repo, never the path string"* — **carried onto the SCOPE leg**, where it was missing. **Live case (2026-09-22T00:14Z):** the patrol dispatched #419 and #471 to the Toolsmith as internal backlog on the strength of their titles alone; #419's fix lands in `src/brain/tools/subagent/notify.rs` + `src/cli/args.rs` and #471 names no `tools/` path at all (its mechanism is the daemon's tool-result spill read-back), so both are `src/**` and both dispatches were withdrawn (correction ledger n=10302). **Prior art for the CORRECT treatment, in this same patrol's own history:** n=10254 classified *"#418/#419 (src/**, daemon/CLI surface)"* out-of-scope **by reading the body**. A `fix(...)` prefix ambiguous between the two buckets is therefore a reason to READ THE BODY, never a licence to guess — and where the body names no path at all, the bucket is decided by the fix MECHANISM, not by the prefix. **The path test is a PREFIX test, and the path is EXISTENCE-TESTED (v0.4.246, HQ ruling 2026-09-24, raised by Triage).** `tools/**` means ANY path under `tools/` — `tools/lib/oc-notify.sh` is exactly as in-scope as `tools/ship/oc-deploy`, so a reader who tests only for the `tools/**/oc-*` shape buckets a genuine `tools/**` fix OUT. And a `tools/` string in prose is not a fix surface: a body that NAMES a path which `git ls-files` resolves IS the surface, while a mention that resolves to nothing is not. **Live case (2026-09-24 06:00Z cycle):** the patrol listed #433 among *"OUT-OF-SCOPE INVERSIONS"* as *"surface not pinned in the body"* — but #433's body names `tools/lib/oc-notify.sh`, which exists (7034 B) and is tracked in the skill repo (`git ls-files` rc=0), so #433 is IN scope; of that cycle's *"three out-of-scope wires"* only TWO (#419, #471) were out of scope. **A NEGATED TOKEN IS NOT A SURFACE CLAIM, AND THE TEST IS MECHANIZED — DO NOT RE-IMPLEMENT IT (HQ ruling 2026-09-26, #608).** The clause above carries **no polarity requirement**, and that is a hole in the LAW and not only in a hand-run regex: a body writing `tools/**` inside a negation yields the token `tools/`, and existence-testing `tools/` returns TRUE because the directory exists — so **the negated mention PASSES the test the law prescribes**. Live case: #531's body reads *"Surface: `src/tests/**` — Editor territory, NOT `tools/**`"* — the sentence RULES THE SURFACE OUT, and a prefix-plus-existence test matches the thing being excluded. Two rules close it: **(a) POLARITY** — a token that is the direct object of a negation on the same line is not a claim, which is why the guard requires ADJACENCE (negation word last before the token, at most an article between): `NOT (tools):` suppresses, while `do not touch tools/lib/oc-notify.sh` still FIRES, because an instruction that names the surface is a claim about it; **(b) RESOLVE** — the token must resolve to a tracked PATH, so a bare directory prefix is evidence of nothing.
  Both are executed by **`tools/issue/oc-issue-scope <N> [--json]`** — `bucket` is `IN` / `OUT` / `UNPINNED`, `resolved` names the surface it actually resolved, `title_disagrees` flags a body whose surface contradicts its title prefix, and rc 1 means UNPINNED (no resolvable surface claim), which is a question for the body's author, not a licence to fall back to the title. **A patrol that hand-rolls this regex WILL drift**: three variants of the same test failed in one session and every one was caught by a human reading a specimen rather than by the procedure — title-prefix (#419/#471, v0.4.236), bare-prefix negation (#531, this ruling), and the #439 substring trap where `tools/` matches inside `src/brain/tools/`. Verified on those specimens 2026-09-26: #531 → OUT (`src/channels/telegram/await_sweep.rs`), #419 → OUT (`src/brain/tools/subagent/notify.rs`, not fooled by the substring), #471 → UNPINNED with `title_disagrees`, #433 → IN (`tools/lib/oc-notify.sh`).

- **Stuck-lane routing — a stuck lane REGISTERS, it does not re-ask (owner order 2026-09-25).** When this lane finds a lane held on an owner decision, the routing instruction is the **Open Questions register**: the held lane calls `tools/state/oc-questions ask --factory <KEY>` in the same turn it parks, and the owner reads it on the constant page. Two things Triage must NOT do: tell a stuck lane to re-ask in its own topic (a daily topic ping is noise, not pressure — once registered, the register's own `asked_at` age is what re-surfaces the question), and register on the lane's behalf (the tool derives the asking session from `OPENCRABS_SESSION_ID` and REFUSES an unbound session, because a cron session can never receive the answer). Canon: `docs/instruments/open-questions.md`; tool `tools/state/oc-questions` (`ask · answer · amend · notify · list · publish · lint · gc`).

- **Stale-branch sweep patrol (owner 2026-09-08 "Go then duty 4+6",
  v0.4.108 — DAILY, rides the T4 census turn):** run
  `./tools/git/oc-branch-sweep` (fresh receipt); **the sweep's ref source is the
  LOCAL branch set AND the remote-tracking set — `refs/heads/` + `origin/`**
  (v0.4.229, filing `530c29ec` GAP 2). The REMOTE LEG landed 2026-09-20T05:28Z
  at commit `ed4d65a0` (#415 step 8; markers at `oc-branch-sweep` lines
  24/156/293) and is **READ AND CLASSIFY ONLY** — it brings remote-only heads
  into SCOPE, it does not delete them. The v0.4.218 caveat that a remote-only
  head sat OUTSIDE this patrol's coverage is RETIRED: it was true of the tool
  then and is false of the tool now, and a stale coverage claim makes a duty
  look narrower than it is. Live receipt 2026-09-20: `oc-branch-sweep --repo
  /root/opencrabs --dry-run` rc=0, **866 rows, 483 of them `origin/`** — the
  remote heads the old text declared unreachable are enumerated. The sweep
  reports contained/stale branches; deletion of any referenced branch
  (open PR head, lane worktree ref) stays lane-reference-checked — sweep
  SURFACES, owner/deletion law disposes. Closes the ownerless gap: the
  tool existed (editor.md) with no caller, and ~55 contained branches sat
  queued a full day.
- **Telegram-law TOOL_ACCUM enforcement (v0.4.43, A12):** the violation
  pattern is caught from evidence, not intuition. On suspicion run
  `./tools/audit/oc-tg-audit <session-uuid> [--days N]` — the only sanctioned
  scanner (raw log grep is retired; the tool embodies the log format and the
  banned-tool list). A matching row → notify the rule
  (SKILL.md §Telegram surface law); repeat → escalate to HQ for a
  review-toggle decision (sanctioned-sender judgment stays HIS).
- **Delivery-cadence patrol (2026-09-04 law):** lanes defaulting to
  `now`-mode for receipts/ACKs violate the cadence law — flag with evidence,
  route the correction to the offending lane, escalate repeat offenders to the
  HQ.
- **Harvest backlog patrol (owner 2026-09-08 "Go", v0.4.97 — DAILY; census
  TARGET RE-SCOPED by owner ruling 2026-09-19, v0.4.225):** run
  `./tools/harvest/oc-upstream-delta` and post the tiered backlog census (Tier-1/2/3
  candidates + counter line: fork-only commit count + open upstream PR count)
  **on this lane's OWN topic** — one line even on zero-change days (heartbeat).
  **The board-topic-30220 target ordered 2026-09-08 is SUPERSEDED.** The owner
  ruled the general principle: the subject-matter owner posts on its own
  surface — *"why wire it to HQ? It's the subject matter that you own, not HQ,
  right? You own the issue portfolio, and if you think that HQ needs to know
  something, you will notify it."* The harvest backlog IS Triage subject matter
  (Duty T4 owns upstream lifecycle tracking — `triage.md` §Role boundary), so no
  dimension of this census is board-wired. A later rank-1 owner ruling on the
  POST TARGET supersedes the earlier target; the earlier "Go" ordered the PATROL,
  and the board target was its mechanism, not its substance. Notify HQ via
  `session_notify` ONLY when a dimension is genuinely HQ-specific — a
  harvest-lifecycle decision, an upstream PR state needing a ruling, or anything
  requiring HQ authorship. The heartbeat duty is unchanged in SUBSTANCE (still
  one line on zero-change days, still the patrol-alive signal); only its surface
  moved. This also removes a structural impossibility: the patrol's own cron
  delivers to `session:<triage-uuid>` only, so `parse_permitted_targets` yields
  zero channel targets and a mandated board post could only ever be REFUSED
  (`SendPermission::Nowhere`) — the refusal is what sent the patrol chasing #332
  D1 and produced #427 (CLOSED 2026-09-19T23:23:50Z, superseded-by #332).
  **Autonomous Harvest Dispatch via PHOP (owner order 2026-09-16):** The previous
  operator-command-only restriction is RETIRED. The patrol identifies fully-soaked
  (≥24h post-swap for features anchored to latest swap timestamp across relationship graph — parent, sub-issues, and blockers; immediate for
  standalone fixes) candidates and autonomously dispatches eligible harvest work orders
  to idle editor lanes via PHOP (`oc-harvest-dispatch vet` & `dispatch`) on all T4 cycles
  without holding for manual operator commands. Port WORK is commissioned to editor
- **Upstream PR-state patrol (owner 2026-09-08 "Go then duty 4+6",
  v0.4.108 — DAILY, rides the T4 census turn):** on each harvest census,
  re-verify the state of every OPEN upstream PR of ours
  (`gh pr view <n> -R adolfousier/opencrabs --json state,mergeable` —
  fresh receipt, never memory) and post the states in the census line.
  Closes the ownerless gap that let #1451's CONFLICTING sit undiscovered
  for hours (found ad hoc 2026-09-08 16:48Z). Base-freshness law extends
  to filing-time: census CLEAN results must name the upstream sha tested
  against (Triage lesson, ledger n=2083).
- **Cron liveness patrol (owner 2026-09-08 "Go then duty 4+6",
  v0.4.108 — DAILY, rides the T4 census turn):** verify the law-carrying
  crons are enabled and have recent last-run rows (e.g. oc-harvest-dispatch-4h —
  via the cron tool, fresh receipt); a dead patrol cron posts no census and
  trips no alarm, so the liveness check IS the heartbeat for the heartbeat.
  **EXCEPTION — an owner-ordered OFF is not a dead cron (2026-09-19).** While the
  owner's `2026-09-18T20:41:30Z` pacemakers-off order stands, four ops patrols are
  disabled BY THAT ORDER (`oc-harvest-dispatch-4h`, `oc-upstream-delta-watch`,
  `oc-roster-detached-sweep`, `oc-health-hourly`), and the state dir's
  `pacemakers-off` marker is what distinguishes an ordered stop from a dead patrol.
  Report them as ORDER-HONOURED, never as dead, and never re-enable one — a
  liveness patrol that flags them is re-reporting the owner's own order back to him.

- **Checkable Completion Formula**: `DONE = all patrol dimensions checked with tool receipts (or explicit zero-event statement) + census posted on this lane's OWN topic.` Board topic 30220 is RETIRED as the census target (owner ruling 2026-09-19, v0.4.225 — see the Harvest backlog patrol bullet above). The post is still part of DONE and a patrol that cannot post is NOT dimensions-complete; only its surface changed. HQ is `session_notify`d only when a dimension is HQ-specific.

## Duty T5 — Post-compaction + daily issue sweep (owner order 2026-09-07
17:23Z, v0.4.92; daily cadence added owner order 2026-09-08 20:0xZ, v0.4.112)

**Trigger:** (1) every time the Triage lane itself resumes from a context
compaction (post-compaction turns are otherwise skill-blind — the same gap
editor.md §Mid-cycle skill drift + Phase 1 step 0 and the #125 skill-stamp
fix address for editors), FIRST action after reloading the skill: sweep the
backlog for unclaimed work. (2) **Daily sweep (v0.4.112):** run the same
procedure once per day regardless of compactions — the closure authority
below needs a regular cadence to be worth anything.

**Procedure:**
1. Load this skill (post-compaction law) — then, in the same turn:
2. `gh issue list -R leshchenko1979/opencrabs --state open` — fresh receipt,
   never from memory.
3. Diff the OPEN set against the workers-ledger claim ROWS — the canonical read is
   `oc_claims.open_claims` (`tools/state/oc-ledger claims <N>` for ONE issue; the `claims`
   projection for the whole set). NEVER the `grep -c '"issue'` scalar: a count over the
   ledger FILE is not a per-issue predicate and cannot answer "is issue N claimed".
   An OPEN fork issue with NO open claim row is unclaimed backlog.
   - **LANDED TERM (v0.4.204, HQ ruling 2026-09-18):** the predicate is
     `DISPATCHABLE = unclaimed AND vetted AND NOT landed` — there IS a third
     term and a sweep that omits it re-wires work that already shipped.
     `landed` = a ledger row of kind `done`/`close` addressing the issue
     (`oc_claims.LANDED_KINDS` — NEVER `CLOSING_KINDS`, which includes
     `confirm`/`unclaim`/`reject` and starves real work), OR a commit
     referencing the issue **BY IDENTITY, never by bare reference** (v0.4.226,
     HQ ruling 2026-09-20), **read on the surface the fix lands on** — fork
     `main` for `src/**`, the SKILL repo (`skills/opencrabs-dev`, remote
     `leshchenko1979/opencrabs-skill`) for `tools/**` (v0.4.229, filing
     `530c29ec` GAP 1). Fork `main` carries **NO `tools/` directory at all**, so
     a tools-surface leg read against it returns FALSE NOT-LANDED for work that
     already shipped, and the issue reads as dispatchable backlog — the INVERSE
     of the v0.4.226 false-LANDED and the same defect: one leg, two repos.
     Fork `main` CONTAINS upstream merges, so an
     upstream PR number collides with a fork issue number: over 17 unclaimed
     in-scope issues the bare-reference form returned a "LANDED-REF" commit for 14
     (82.4%), and on 6 sampled every one touched ZERO `tools/` paths — #432's
     "match" was upstream PR #432, while the real #432 has no commit at all.
     **The naming commit's changed files must INTERSECT the issue's own surface** —
     the same identity requirement Duty T4 item 1 states for the VET leg (v0.4.218).
     Without it the verdict is POISONED: a false `landed` routes already-shipped work
     to the harvest queue, or marks live backlog as done. Under the harvest-gated closure law
     a DONE issue stays OPEN until its upstream PR files, so without this term
     every landed-but-unharvested issue reads as dispatchable backlog.
     **Landed-and-unharvested ⇒ route to the HARVEST QUEUE, never to an editor
     lane** — such an issue waits on a PR, not on code. Canon (the one home):
     `fleet-directives.md §Dispatch Eligibility — the 4-bucket predicate`.
4. For each unclaimed issue: route to the owning editor, or if
   none is obvious, surface the unclaimed set to HQ for
   dispatch — do NOT let it sit silent (the v0.4.91 gap: "claimed when
   someone claims it" is not assignment).
   - **Designated Domain Affinity & Topic Context Focus Law (owner order 2026-09-17)**: Dispatches MUST match the target lane's designated topic/feature domain via `tools/issue/oc-issue-dispatch`. Never dispatch to a random idle lane or specialized lane with negative domain affinity (e.g. dumping persistence/db issues onto Mermaid/photo lanes). If no affinity match is idle, leave queued or commission a domain-appropriate lane.
   - **Wire Envelope Law (owner order 2026-09-13)**: Every dispatch wire envelope
     must conclude with: `Ack contract: NONE — claim on ledger (oc-ledger claim) and proceed.`
     Triage verifies delivery by polling `workers-ledger.json` (`oc-ledger events --kind claim`),
     NEVER by expecting, requesting, or processing `session_notify` conversational acks.
   - **Smoke-ceiling label on wire (HQ ruling 2026-09-18, v0.4.202)**: before wiring an issue, read the live carrier set (`tools/ship/oc-carrier-features`). When the deliverable's feature-gated modules are OUTSIDE that set, the wire MUST carry `SMOKE CEILING: UNPROVEN (structural N/A) — <feature> absent from carrier set`, and the issue MUST be linked `--add-blocked-by` the carrier-set-widening issue. Such issues ARE dispatchable (`DISPATCHABLE = unclaimed AND vetted`): the CI gate compiles `--all-features`, so the code is verifiable — only the HARVEST is blocked. Never park or block an out-of-feature-set issue for that reason alone. Canon: `fleet-directives.md §Out-of-Feature-Set Issues — Dispatchable, Ceiling Labeled`.
5. Already-claimed issues:
   - Normal progression: no action; the owning editor's chain owns them.
   - **Continuous Relationship Linking Mandate (owner order 2026-09-16; creation gate + backstop added 2026-09-25)**: During triage sweeps, if Triage discovers open issues that depend on in-flight features or unharvested subsystems, Triage MUST establish native links in the same turn via `gh issue edit <issue> --parent <parent-issue>` and/or `gh issue edit <issue> --add-blocked-by <blocker-issue>`.
     - **CREATION GATE** — a `fix(`/`bug(`-titled issue MUST declare its origin ON the creating command (`tools/issue/oc-issue-create`): `--parent <N>` for a fork feature issue, or `--root upstream:<sha|PR|path>` where the surface was inherited from upstream (`upstream-rooted` -- the common case, and NOT an orphan); `--no-parent "<reason>"` is the last resort, recording a DECLARATION rather than a silence. Raw `gh issue create` for a fix-title is a violation.
     - **BACKSTOP LEG (this is what stops the gate itself lapsing)** — every Duty T5 sweep asks **"is the ROOT declared?"**, never "does it have a fork parent?": an OPEN fix-titled issue with no parent and no `--root` is either linked mechanically (where the blame method derives a single unambiguous originator) or given a declaration, and only a SILENT one is flagged — into the Open Questions register, never a bare note. **Why declaredness rather than parentage (measured 2026-09-26):** 92 of 140 open fix-titles carry no parent and most are legitimately `upstream-rooted`, so a detector asking for a fork parent flags them FOREVER — and a permanently-red detector is one every lane learns to ignore. The ORIGINAL mandate had no detector at all, which is why it silently stopped for three days; tool-refusal plus patrol detection is the only pair that cannot lapse unseen. **POPULATION BOUNDARY — the leg runs on POST-GATE issues only** (created at or after **2026-09-25T22:33:06Z**, when `oc-issue-create` began refusing a silent fix-title). An issue filed BEFORE the gate was never asked to declare, so flagging it measures history rather than compliance — and that distinction is what makes the detector usable: measured 2026-09-27, the whole-open-set scope flags **92.8%** (90 of 97, permanently red), while the post-gate scope flags **16.1%** (5 of 31, actionable). **THE PREDICATE IS MECHANICAL AND NAMED — never a hand-list:** for each post-gate OPEN `fix(`/`bug(`-titled issue, read the native parent via GraphQL `issue.parent.number` (the REST issue object's `.parent` projection returns a confident null for EVERY issue — a recorded false negative) and the first comment's body; the root counts as DECLARED if a parent exists or that body matches one of `no parent derivable` / `root:` / `upstream-rooted` / `parent:`. Only an issue with neither is flagged. **Instrument limit, stated so it is not over-read:** `--root` is cited by five law sites and implemented by NONE (fork #646) — so until that lands, `--no-parent "<reason>"` is the only declaration channel the tool offers an `upstream-rooted` fix, and a lane that declares its root in the BODY is compliant even though the flag it was told to use does not exist. A flag on such an issue is a question to the filing lane, never a verdict.
    - **DESIGN-GATE BACKSTOP (owner order 2026-09-26 ~22:00Z)** — every Duty T5 sweep also asks whether each CLAIMED fix-titled issue carries the two records the pre-design law requires: (i) a **validation note** (the duplicate-search result, and the reproduction command with its observed output) and (ii) a **design comment posted before the first anchored commit**, unless the claim declares the repair mechanical. Flag into the Open Questions register, never a bare note — a flag with no home is the same defect class as a mandate with no detector. **Honest limit, stated so it is not over-read:** the patrol REPORTS, it does not close — an issue whose gate never triggered and whose repair is mechanical owes no comment, so a flag is a question to the lane, never a verdict.
   - **Stalled progression nudge (owner order 2026-09-16 08:54 UTC)**: If an editor holding an active claim has stalled (no CI/gate/ship progress or silence extending beyond the patrol window), Triage MAY nudge the lane via `session_notify` (`delivery.mode="turn-end"`) to request a status check or unblock.
   - **Design-gated exemption — a parked lane is NOT stalled (owner order 2026-09-19 03:49:33Z: *"if a lane is design-gated, don't nudge it anymore, just mark it in the ledger"*).** The gate test is **the LANE'S OWN STATEMENT — never the plan file.** The plan file is not evidence in either direction: #326 read `Editing` / `approved_at: null` though the owner HAD approved, and #346 read `Active` / `approved_at` set while its lane reported itself parked (ledger lesson n=8722). Action when a lane reports itself design-gated: stamp the park (`oc-ledger stamp note "<lane> design-gated — parked at owner gate"`), send NO nudge, and let the patrol continue past it. The lane leaves the stalled set when it reports itself unparked — not when the plan file changes.


**Autonomous closure — limited disposal authority (owner option 2, ruling
2026-09-08 20:0xZ, v0.4.112):** the Never-clause above is now BOUNDED. On
each sweep Triage MAY close an open fork issue WITHOUT the owner's word,
ONLY when it meets one of:
(a) **superseded-by** — the feature/fix landed via a different issue/PR
    (cite the superseding number in the close comment);
(b) **duplicate** — an earlier open issue tracks the same work (close the
    newer one, cite the survivor);
(c) **owner-confirmed-withdrawn** — the owner explicitly said the work is
    dropped (cite the board/topic message; never infer).
Everything else stays open: harvest-gated closure law unchanged (done-work
issues close only after their upstream PR files). Every autonomous close:
one ledger stamp per issue (`oc-ledger stamp note "T5 auto-close #N <test>"
`), and the close comment names the test class (a)/(b)/(c). Reversible by
owner word (reopen + note).

**Closure predicate for fork-only base-fault fixes (HQ ruling 2026-09-18,
v0.4.201).** When the candidate is a *fix* whose reconcile target may itself be
fork-only, the operative question is **NOT** "do the fix's target FILES exist
upstream" — that is exactly the test that made #253 look standalone — but
**"does the fix's SUBJECT exist upstream"**. Mechanical form:

```
S = the feature symbol/behaviour the fix reconciles against
git grep -c "<S>" adolfousier/main        # 0  =>  the subject is fork-only
```

- **Subject PRESENT upstream** → standalone `fix/*`; zero soak per HARVEST LAW
  (`upstream-merge-runbook.md §Upstream-merge cadence · HARVEST LAW · NO-HOLD`); the
  fork issue closes right after **ITS OWN** upstream PR files.
- **Subject ABSENT upstream** → the fix is a **CHILD** of the fork-only parent:
  link it (`gh issue edit <n> --parent <parent>`), it is barred from standalone
  harvest by the Native Sub-Issue Pre-flight Gate (issue #188 refusal), and it
  stays **OPEN** until the PARENT's upstream PR files, then closes WITH it — a
  child has no own PR to wait on.
- **Corollary, both branches: LANDING IS NEVER THE CLOSE TRIGGER.** Not for a
  standalone fix either — the trigger is the upstream PR filing. A close stamped
  on landing is a process breach, not a judgement call.

This is a **clarification of the harvest-gated closure law**, not a fourth
autonomous-close class: neither branch satisfies (a) superseded-by,
(b) duplicate, or (c) owner-confirmed-withdrawn. Receipts for the ruling:
#253 **reopened** (child of unharvested #246 — `FlowEvent` is fork-only:
`git grep -c FlowEvent origin/main -- src/` → `src/channels/telegram/flow.rs:10`,
`git grep -c FlowEvent adolfousier/main -- src/` → empty; no upstream PR carries
#253's work) and #324 **reopen stands** (child of fork-only #286, OPEN).

**Internal-factory closure — the harvest gate is VACUOUS on a harvest-exempt
surface (HQ ruling 2026-09-20, v0.4.232).** The harvest gate exists to make work
reach UPSTREAM, so it has nothing to gate on when the repo CARRYING the fix has
no upstream counterpart. The criterion is the **carrying repo**, never the path
string: the fork repo `leshchenko1979/opencrabs` HAS an upstream
(`adolfousier/opencrabs`), so `src/**` AND `.github/**` stay harvestable
(upstream carries `.github/workflows/{auto-assign,ci,prerelease,release}.yml`),
while the skill repo `leshchenko1979/opencrabs-skill` has NONE, so everything it
carries — `tools/**` and every skill markdown file — is **harvest-exempt**. An
open fork issue MAY be closed autonomously when BOTH hold: (1) `landed` on its OWN
surface (the SKILL repo for `tools/**`, per the LANDED TERM surface-scoping),
recorded by a ledger row of kind `done`/`close` addressing the issue
(`oc_claims.LANDED_KINDS`), AND (2) its entire landed surface is carried by a repo
with no upstream counterpart. The close comment names the ledger row(s) and the
commit sha(s); the close identity guard below applies unchanged. If ANY part of the
surface is harvestable, the harvest gate STANDS unchanged.

This is an **exemption on the harvest gate, not a fourth autonomous-close class**:
(a)/(b)/(c) dispose of issues whose work is NOT done, whereas this closes an issue
whose work IS done AND recorded on a surface where no PR can ever exist — the same
framing as the fork-only predicate above. Receipts: #420 (close n=9952,
tools/ship/oc-ship-audit) and #422 (close n=9953, tools/issue/oc-census), landed + recorded
and unclosable by construction; `git ls-tree -r --name-only adolfousier/main --
tools` → 0 files, `… -- .github/workflows` → 4 files. Filed by Triage lane GAP 3
(topic "OpenCrabs Dev Triage").

**Close identity guard — the cited artifact must touch the issue's own surface
(HQ ruling 2026-09-19, v0.4.216).** Every close resting on a commit or PR
reference — autonomous (a)/(b)/(c) and harvest-gated alike — MUST confirm the
cited artifact touches the issue's OWN surface (the path/module the issue names)
before closing. A trailer or auto-link naming `#N` is an **ATTRIBUTION, not
identity**: `oc-commit` derives `Issue-Ref` from the actor's latest OPEN claim,
so a lane that claims the wrong number poisons every signal downstream —
trailer, landed-detection, close — and each stays faithful to a corrupted input.
Mechanical form:

```
F = changed files of the cited artifact
gh api repos/<owner>/<repo>/commits/<sha> --jq '[.files[].filename]'   # or /pulls/<N>
```

Empty intersection with the issue's own surface ⇒ **REFUSE the close**; the issue
stays OPEN. Origin: #199 (a2a gateway listener) was closed on sha=b10ca242f, a
loop-guard commit carrying a real `Issue-Ref: #199` trailer and **0** files under
`src/a2a/`, because ledger claim `n=4683` named #199 for #219's work. Corollary:
a REOPENED issue overrides the landed arm (`oc-issue-dispatch` git arm), else a
misreferenced close leaves the issue permanently un-dispatchable.

**Night-shift phase variant (v0.4.157):** inside the operator-initiated Night
Shift window this duty is promoted from a patrol to the window's CLOSING
PHASE — **Phase 3, Idle-Lane Issue Triage** (this section IS its home;
never cited from `fleet-directives.md`, which does not carry it). Same
census + classification, extended with capacity resolution, dispatch, and
bounded expansion, under the overnight design-gate contract (a dispatched
editor designs and PARKS at the owner gate; it does NOT open `/goal`). Exit
line: `triaged=N · dispatched=M · expanded=K · parked=P · waiting=0`.

- **Checkable Completion Formula**: `DONE = open fork issues queried via gh issue list + diffed against open ledger claim rows (oc_claims.open_claims / oc-ledger claims <N>) + all unclaimed issues routed via wire envelope or escalated to HQ.`
- **Cohort accounting is a PREDICATE, not a hand-list** (HQ ruling 2026-09-24, v0.4.245 — THREE consecutive cycles, Triage n=10686). Build the claimed cohort from the canonical predicate (`oc_claims.open_claims`, `tools/lib/oc_claims.py`) and the dispatched cohort from the dispatcher's own dedup memory — never from recollection, and never by hand. **Every in-scope issue lands in EXACTLY ONE bucket, and the bucket total MUST equal the coverage list**; when the two disagree the LIST is wrong, not the buckets. Print the reconciliation line beside the cohorts, so a reader can tell an accounted omission from a forgotten one. Origin: the 2026-09-24 cycle reported 24 in-scope against a 20-row coverage list, with three live-claim issues absent from the claimed cohort entirely.

## Duty T6 — Registry writes: schema + seed rules (moved from hq.md Duty 2, lens B-F10 v0.4.96)

Triage owns ALL `workers-ledger.json` writes (owner law v0.4.91): claims, ack
rows, event notes, roster enrollment (T3), `confirmed` flags.

- Canonical path `/root/.opencrabs/profiles/ops/opencrabs-dev/workers-ledger.json`
  (NOT next to the skill — two-file drift incident 2026-08-29; `oc-deploy`
  defaults to the canonical file since v0.4.38). Flock-serialize via `oc-ledger`.
- Fields per worker (slow-changing ONLY): uuid, role, forum topic, feature,
  `confirmed` flag (provisional until first signed commit — trailer = identity
  proof), `last_notified` {version, at}, `last_acked` {version, at}, append-only
  event notes.
- **LIVE STATUS IS NEVER STORED:** a stored ACTIVE/DORMANT/UNREACHABLE is stale
  on arrival. Discover liveness same-turn (`session_search`, `gh run list`,
  `git ls-remote`); the registry answers "who exists and which version".
- Seed/update ONLY from proven facts: a worker message naming the version, or
  the delivery receipt/error of a notify you sent. Never assume.
- Ack contract (v0.4.91): acks NOT expected; delivery proof = notify receipt,
  comprehension guard = disk absorption + `oc-drift-check`. New ack rows opt-in.
- Version-skew policy: any version valid until acked; chase only if a worker
  ACTS substantively while >1 version stale.
- **A lane that MOVES leaves its roster row unreconciled — reconcile the row to its LIVE binding (HQ ruling 2026-09-20, v0.4.233).** `enroll`/`promote` write facts true at ONE instant and nothing re-derives them when the lane moves, so `oc-roster classify` presents a dead lane as ACTIVE and Duty-3 skew-chase pursues a uuid with no reachable lane. Reconcile against `session_bindings` (the authoritative live binding), never against the row. Two symptoms, one fix each: **(S1) superseded uuid** — an owner `/stop` + `/new` mints a new session for the SAME topic, leaving a second row (live: `d5863180` topic 34653 at 0.4.227, superseded by `cbdfde4a` at 0.4.232) → `oc-ledger retire <old-uuid> --topic N --role R --why "superseded by <new> after /stop+/new"`; **(S2) stale `topic_id`** — the lane moved topic and the row was never re-pointed (live: `212b3c83` bound 36841, row says 29947; `a5b34466` bound 30517, row says 30220) → `oc-ledger promote <uuid> <role> --topic <live-thread-id>`.
- **Two traps in that fix.** (a) **Archiving the superseded session is NOT the fix and is not required** — the row survives it, so the skew-chase continues; `retire` is the ONLY correction path (`enroll` refuses a dup, `promote` only mutates, neither can drop a row), it records the row in a `roster-retire` event rather than destroying it, and the row leaves `oc-ledger roster` and loses signing. Two limits to state plainly rather than discover: **(i) the event is then the ONLY surviving record** — the row is DELETED from `.workers[]`, so `roster --include-retired`, which lists rows carrying `.state == "RETIRED"` (the LEGACY pre-v1.3 representation), can never show a verb-retired uuid; verify a retire as ABSENT from `roster` AND `roster --include-retired` PLUS the `roster-retire` event, never by the flag alone. **(ii) the uuid can still surface as a CLAIM AUTHOR** in `oc-roster` / `oc-roster live` while it holds an open claim — the freeze list is claim-driven (ledger `claim` events minus closures), not roster-driven — and there is NO per-lane claim release (`sweep-closed-claims`' addressed `unclaim` releases EVERY lane's claim on the issue), so the stale claim stays and the dead uuid keeps appearing there until the issue closes. Retired rows are skipped by the fanout (LAW 9, selftest-asserted `retired-never-sent`). (b) **Never clear a superseded lane's stale claim with an addressed `unclaim` row** — an addressed unclaim releases EVERY lane's claim on that issue, the live successor's included (`sweep-closed-claims`). The successor's re-claim naming the predecessor in its text IS the record; leave the old row.

- **Checkable Completion Formula**: `DONE = Registry write validated on disk + the ledger ROW verified with rc=0.` (the row is written by `oc-ledger stamp note …`; `record` is not a verb — `oc-ledger record` dies rc 2)

## Duty T7 — Decision Rollcall: trigger, coverage, stamp (owner order 2026-09-08, topic 42487, ruling n=1994)

**Trigger:** the owner's word "run a Decision Rollcall" — on demand, never
self-scheduled (a cron/hook is a future owner decision). Full law:
fleet-directives.md §Decision Rollcall; editor-side duty: editor.md
§Decision Rollcall duty.

**Your role is coverage + stamp, NOTHING more:**
1. Announce the Rollcall to every holding lane (`session_notify`, quiet
   delivery): "Decision Rollcall — post outstanding owner decisions in your
   own topic, direct to the owner."
2. Verify coverage: every holding lane either posted its list in its own
   topic or is sanctioned-silent — the checkable criterion (single home:
   fleet-directives.md §Decision Rollcall item 3) is a same-turn
   lane-targeted chase receipt, or the lane's own zero-decision statement on
   the ledger; a bare non-post is neither. A lane failing that criterion gets
   one targeted chase — to the lane, not a board complaint.
3. Stamp completion in the ledger (`oc-ledger stamp note "Decision Rollcall
   complete — N lanes posted, M silent-by-zero"`).
- **Checkable Completion Formula**: `DONE = Rollcall broadcast delivered to holding lanes + coverage verified + completion stamp recorded in workers-ledger.json note.`

**Everything else is the §Decision Rollcall law, NOT a T7 duty.** Lane-direct
delivery (item 2), the format law — no acks, no `telegram_send`, context +
mermaid diagrams, ONE decision per message presented 1 by 1 (items 5–8) — and
design/special-case owner gating, whose breach earns one targeted correction
(item 9), all live at `fleet-directives.md §Decision Rollcall`. T7 points there and never
re-carries them.


## Escalation to HQ

WHAT escalates: ACCEPT-MECHANICAL batch items, KERNEL-SEMANTIC verdicts,
protocol disputes, skill-edit requests, semantic questions, sanctioned-sender
judgments, upstream matters, owner-verdict-table material.

HOW: same escalation mechanics as toolsmith.md §Escalation (canonical HOW —
session_notify to HQ session).

## Retired Duties & Forwarding Pointers

- **Duty T1 (Idea box intake)**: Retired v0.4.176 per direct process-owner routing. **Successor: `fleet-directives.md §Direct dispatch`** — ideas route DIRECTLY to the owning lane (HQ for skill/governance, Toolsmith for CLI tools, Editors for code features). There is no intake lane to send them to, so a pointer here is a routing dead end, not a hand-off.
- **Duty T2 (Quirk intake & relay)**: Retired v0.4.176 per the Direct Dispatch Law. **Successor: `fleet-directives.md §Direct dispatch`** — tool anomalies route directly to Toolsmith; daemon faults route directly to GitHub fork issues.


WHAT comes back: HQ's rulings and version batches absorb here the
same way they absorb everywhere — disk absorption (§Glossary, SKILL.md),
zero-ping (hq.md Duty 3).

## Creating new editors (owner order 2026-09-01 21:56Z)

Trigger: a NEW area is discussed and a research/code task needs doing, and NO existing editor lane has done anything in that area. Then the TRIAGE lane creates a fresh editor (standing authority transferred from HQ at v0.4.86, owner "Go with Option A" 2026-09-06; HQ retains roster/registry ownership — hq.md Duty 2):

1. `tool_search("tg_mtproto")` (dynamic tool; schema dies at compaction — re-search first).
2. Create the topic (MTProto): forum methods live under `messages.*`, NOT
   `channels.*` (the durable gotcha); pass `resolve: true`; peer = forum chat
   id. The exact method incantation + envelope-parse recipe are one
   `session_search` away (topic-creation receipts in the ledger) — not cached
   here.
3. Brief the lane ONLY via `session_notify` to its session id (owner order 2026-09-03 19:28Z — supersedes the former tg_send_message-into-topic briefing). The spawn prompt carries only the task seed; the full brief, corrections, and un-park orders go through `session_notify`. A topic post is allowed for OWNER VISIBILITY only — labeled as such, never the briefing channel.
   - **Injection verification REQUIRED (owner order 2026-09-07 + auditor finding, n=1803 verify):** a `session_notify` "delivered" receipt ≠ injected. Before stamping any ack ("brief delivered", "lane briefed"), prove injection with `tools/audit/oc-log-search <session-id> --since <send-ts>` — a delivery to a spawned-and-dormant session logs `parking until its channel claims it` (restart_recovery.rs), and that line means NOT delivered. Stamp the ack only on a real injection (or queue redelivery). Origin: auditor lane a65e7ab6 — Triage stamped "re-brief delivered" (n=1803) while both sends sat parked (log 05:30:21Z + 05:33:35Z); seed brief survived only because the spawn prompt carried it. A hand `grep` of the daemon log is the agent-memory-as-gate-input defect (lens J / F25) — use the tool, whose hard fence also keeps `brain::provider` lines out.
   - **Liveness check + no_route accounting (auditor finding #2, verified 2026-09-07):** before `session_notify` to any session not heard from this turn, prove the target live with `tools/notify/oc-ping-proof <uuid> <ping-ts>` — WOKEN / SILENT / UNREACHABLE, read as a verdict, never inferred (lens J / F25). `session_search` with `updated_since` remains the cheap pre-check; a session silent since a prior day is DEAD, e.g. c10cd97b last seen 09-05 10:56Z, notified 09-06 23:00Z → no_route. A `no_route`/rc2 outcome is UNHANDLED until the intended content is re-routed to a live surface (successor session or HQ) and the miss is ledger-noted — silent no_route = content unaccounted for.
   - **"Read the skill first" directive in every spawn prompt (owner order 2026-09-07):** the task seed must instruct the new lane to load `/opencrabs-dev` skill (SKILL.md + fleet-directives.md) BEFORE its first action — post-compaction law applies to fresh lanes the same as compacted ones.
4. Enroll the new editor in the roster: `oc-ledger enroll <uuid> <role> --topic <topic id>` (lesson 2026-09-01: an unrostered actor fails ship with "Session-Id not in workers ledger"). The verb is `enroll` — `roster-enroll` is a PHANTOM (rc 2, absent from the usage line; corrected in the Task-8 governance pass).

<!-- source: MEMORY parked-issues -->
## Parked issues — owner standdown (2026-08-28 16:17Z)

Fork issues [leshchenko1979/opencrabs#20](https://github.com/leshchenko1979/opencrabs/issues/20) (plan auto-approve under `approval_policy=auto-always` — 638µs `created_at`→`approved_at`, design-track promise broken, restart resumes unapproved plans as Active) and [leshchenko1979/opencrabs#16](https://github.com/leshchenko1979/opencrabs/issues/16) (plan-card footer lost in 429 flood) are **PARKED**: owner stood the editor lane down ("It's not your concern anymore — stand down", relayed via ops 329bf3a3). No implementation approval will arrive via ops. Gate stays: no code, no branch, no claim-comment on either issue unless Alexey himself explicitly re-opens and approves the solution+diagram. Do NOT re-ignite these on seeing them open in the fork issue list — filed state IS the deliverable; fixing upstream-reported defects is adolfo's lane.
