# TRIAGE — interrupt lane: fix routing, enforcement

**Load only after SKILL.md confirmed the role is TRIAGE.** This is the OC DEV
TRIAGE session's standing role — carved out of the HQ lane at v0.4.86
(owner word "Go with Option A" 2026-09-06). Interrupt-shaped duties moved HERE
so HQ keeps uninterrupted deep-work windows: skill
authoring, procedure rulings, review batteries. **Upstream sync: delegated to
Triage (owner order 2026-09-11 "You should not do these merges - delegate to triage") —
Triage executes the rebase sync, resolves textual conflicts per upstream-merge-runbook.md,
and coordinates seam adaptation passes. HQ does NOT execute these syncs.**

**RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `triage.md`, `fleet-directives.md` in `active_skills`; re-read on compaction/spawn).

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
- **Upstream lifecycle tracking**: Harvester role RETIRED v0.4.176; its lifecycle duties are consolidated in Triage (upstream delta watch, upstream PR census, maintainer dependency tracking). **Triage SURFACES, COUNTS and PRIORITISES, and owns the tier/cluster surfacer (`tools/harvest/oc-harvest-census`) — it NEVER ports, NEVER files an upstream PR, and NEVER follows one.** Editors end at smoke evidence; the HARVEST lane ports, gates and files per `harvest.md` Phase 7 (owner order 2026-09-24 centralising harvest).
- **Priority authority (owner order 2026-09-15)**: Triage has complete, independent authority over intake triage, patrol sequence, and backlog sorting — never ask the human operator about priorities.

## Duty T3 — Create a new editor (standing authority, transferred from HQ at v0.4.86)

Procedure = triage.md §Creating new editors, unchanged: topic FIRST
(messages.CreateForumTopic), THEN spawn the session with a task-seed spawn
prompt ("Load opencrabs-dev skill. You are an editor." + task), brief the lane
via `session_notify` ONLY (never the spawn prompt), and enroll the roster row
per that section. Owner veto overrides retroactively, as with rulings.

- **Checkable Completion Formula**: `DONE = Forum topic created + Editor session spawned & enrolled in ledger + task brief delivered via session_notify (target_session confirmed woke).`

## Duty T4 — Enforcement patrols

### PHOP & Pre-Dispatch Vetting (v0.4.136, 2026-09-10; Native GitHub Protection 2026-09-16)
  When orchestrating harvest work, Triage MUST mechanically vet candidate packages before dispatching harvest work orders to editor lanes:
  1. Run `tools/harvest/oc-harvest-dispatch vet <issue-or-commits>` to verify upstream absence (tree-diff non-empty, patch-id unmerged, not already merged upstream, not superseded). **A `#N` named in a commit subject or a PR title is a REFERENCE, not identity** (v0.4.218, filing `530c29ec` P1): the naming commit's changed files must intersect the issue's own surface, or the verdict is poisoned — a `(#N)` corrupted in a squash subject maps a DIFFERENT subsystem's work onto this issue, and the refusal is then PERMANENT because the squash sits in upstream history forever. Canon: `§Dispatch Eligibility D1` (this file) (IDENTITY leg); live case `#199`.
  2. **Native Sub-Issues & Blockers Check (owner order 2026-09-16; strengthened v0.4.198):** `vet` (item 1) already evaluates BOTH legs and returns the verdict code — read that code; do NOT re-derive either by hand (a hand re-check of a tool verdict is the agent-memory-as-gate-input defect, lens J / F24).
     - Sub-issues / child cleanups → `HELD_PARENT_UNHARVESTED`: parent unmerged, or a touched path introduced by an unharvested fork issue. Issue #188 unharvested-parent refusal.
     - Blockers declared via `gh issue edit <issue> --add-blocked-by <blocker-issue>` → `HELD_BLOCKED_BY_DEPENDENCY` until blockers land upstream.
     - Upstream baseline (path already clean, or differently structured on `adolfousier/main`) is `vet`'s own tree-diff leg — item 1, not a separate manual check.
  3. Verify target editor lane availability using `tools/harvest/oc-harvest-dispatch dispatch <issue> <commits> [--to <uuid>]`. If target lane is busy with an active claim, the tool refuses dispatch (rc 4); Triage must select an idle editor or commission a dedicated harvest worker.
  4. **Landed-term gate (v0.4.204, HQ ruling 2026-09-18):** before wiring, confirm the issue is NOT already landed — a `done`/`close` row addressing it, or a commit referencing it on fork `main`. This patrol runs from a cron (`oc-harvest-dispatch-4h`) that wired #302 while #302 carried Triage's own `done` row (n=8267) and zero claims: `done` + zero claims satisfied the old two-term predicate. A landed-but-unharvested issue is HARVEST-queue work, never a fresh editor dispatch. Canon: `§Dispatch Eligibility — the 4-bucket predicate` (this file).
  5. Never dispatch unvetted candidates or busy editors. (Worktree creation belongs to the Editor lane per `upstream-merge-runbook.md §PHOP`).
  6. **Authorship gate (§D4, owner order 2026-10-04):** before wiring, confirm the defect is **OURS to fix**. A defect in a feature or fix we did not author is **reported, never dispatched for implementation** on our fork — the fix belongs to its author. `oc-issue-dispatch` does NOT implement this leg, so it is applied by hand. → `§D4 — AUTHORSHIP`.

### Factory-scoped patrol — SCOPE IS A FILE-SURFACE TEST, NEVER A TITLE-PREFIX TEST (v0.4.236, HQ ruling 2026-09-22; raised self-caught by the Triage lane)

The patrol triages **EVERY open fork issue** (owner order 2026-09-26: coverage 19 → 181) and buckets each by **the file surface its FIX lands on, read out of the issue BODY, per-issue, BEFORE any dispatch** — never by the `fix(...)` scope in its title. **THE PATROL'S POPULATION IS TWO SETS, NOT ONE (owner order 2026-10-04):** the fork's open issues, as just described, **AND every OPEN issue on the binary tracker assigned to us** — `gh issue list -R opencrabs/opencrabs --state open --assignee leshchenko1979`. The second set is **NOT** bucketed by the P1/P2/P3 surface tiers below (those are a fork-dispatch priority order); it is dispositioned **DISPATCH-or-REPORT** by **§Upstream-assigned patrol** (next section), which owns that population. `fix(tools):` is a **LABEL the owner applies to every tool-related issue, and it spans TWO repositories and therefore two buckets**: a fix landing in `tools/**` (skill repo, harvest-exempt) is the **FACTORY bucket**, while a fix landing in `src/brain/tools/**` or any other `src/**` path (the daemon binary, harvestable) is the **BINARY bucket**. **THE BUCKET IS A PRIORITY TIER, NOT AN INCLUSION GATE (owner order 2026-09-26 21:22Z; v0.4.266).** The owner replaces the binary IN/OUT exclusion with a three-tier priority order: **P1 — FIX THE FACTORY** (fix-typed, fix lands on the factory surface: `tools/**` or `.github/workflows`) · **P2 — FIX THE BINARY** (fix-typed, fix lands on `src/**`) · **P3 — NEW FEATURES** (`feat`-typed, ANY surface). A non-fix/non-feat type (docs/chore/test/refactor/ci/style/perf) follows the SURFACE rule: factory → P1, else P2. **A `feat`-typed issue on the factory surface is P3, not P1** — priority 1 is *fix* the factory, and a new factory feature is a new feature. **Work P1 first; P2 only when P1 has no dispatchable residue; P3 last. A lower tier is DEPRIORISED, never excluded** — that is the whole difference from the rule this replaces, which excluded `src/**` outright and held the patrol's remit at 19 issues instead of 181. Measured 2026-09-26 (181 open): **P1 16 · P2 149 · P3 16**. **UNPINNED TAKES THE TIER ITS TYPE IMPLIES — IT IS NEVER EXCLUDED (v0.4.269, HQ ruling 2026-09-28).** An unresolvable surface is a flag for the body's author, never a licence to drop the issue: a `fix`-typed UNPINNED reads **P2** and a `feat`-typed UNPINNED reads **P3** — the conservative tier, which is what *deprioritised, never excluded* means for an issue whose surface cannot be resolved. `bucket` stays the surface FACT; `title_disagrees` carries the flag. **Measured 2026-09-28 (212 open): P1 48 · P2 148 · P3 16**, of which UNPINNED 42 → **P2 39 · P3 3**; resolvable (IN+OUT) = 170. Reading the old *“UNPINNED takes NO tier”* literally computes **P2 = 109 and strands 42 issues** — the tool's rule IS the law. **`oc-issue-scope` emits `priority` on every row: read it from the tool, never re-derive it.** The title is the most AVAILABLE signal, so a classifier defaulting to it returns exactly the answer it wants — and it is wrong on **both inversions, silently**: a `fix(tools):` issue whose fix is `src/**` reads as in-scope, and a `fix(src):`-prefixed issue whose fix is a `tools/` path reads as out-of-scope, with no signal in either direction. This is the SAME identity requirement this file already states twice — Duty T4 item 1 *"A `#N` named in a commit subject or a PR title is a REFERENCE, not identity"* (the VET leg) and the internal-factory closure law *"the criterion is the carrying repo, never the path string"* — **carried onto the SCOPE leg**, where it was missing. **Live case (2026-09-22T00:14Z):** the patrol dispatched #419 and #471 to the Toolsmith as internal backlog on the strength of their titles alone; #419's fix lands in `src/brain/tools/subagent/notify.rs` + `src/cli/args.rs` and #471 names no `tools/` path at all (its mechanism is the daemon's tool-result spill read-back), so both are `src/**` and both dispatches were withdrawn (correction ledger n=10302). **Prior art for the CORRECT treatment, in this same patrol's own history:** n=10254 classified *"#418/#419 (src/**, daemon/CLI surface)"* out-of-scope **by reading the body**. A `fix(...)` prefix ambiguous between the two buckets is therefore a reason to READ THE BODY, never a licence to guess — and where the body names no path at all, the bucket is decided by the fix MECHANISM, not by the prefix. **The path test is a PREFIX test, and the path is EXISTENCE-TESTED (v0.4.246, HQ ruling 2026-09-24, raised by Triage).** `tools/**` means ANY path under `tools/` — `tools/lib/oc-notify.sh` is exactly as in-scope as `tools/ship/oc-deploy`, so a reader who tests only for the `tools/**/oc-*` shape buckets a genuine `tools/**` fix OUT. And a `tools/` string in prose is not a fix surface: a body that NAMES a path which `git ls-files` resolves IS the surface, while a mention that resolves to nothing is not. **Live case (2026-09-24 06:00Z cycle):** the patrol listed #433 among *"OUT-OF-SCOPE INVERSIONS"* as *"surface not pinned in the body"* — but #433's body names `tools/lib/oc-notify.sh`, which exists (7034 B) and is tracked in the skill repo (`git ls-files` rc=0), so #433 is IN scope; of that cycle's *"three out-of-scope wires"* only TWO (#419, #471) were out of scope. **A NEGATED TOKEN IS NOT A SURFACE CLAIM, AND THE TEST IS MECHANIZED — DO NOT RE-IMPLEMENT IT (HQ ruling 2026-09-26, #608).** The clause above carries **no polarity requirement**, and that is a hole in the LAW and not only in a hand-run regex: a body writing `tools/**` inside a negation yields the token `tools/`, and existence-testing `tools/` returns TRUE because the directory exists — so **the negated mention PASSES the test the law prescribes**. Live case: #531's body reads *"Surface: `src/tests/**` — Editor territory, NOT `tools/**`"* — the sentence RULES THE SURFACE OUT, and a prefix-plus-existence test matches the thing being excluded. Two rules close it: **(a) POLARITY** — a token that is the direct object of a negation on the same line is not a claim, which is why the guard requires ADJACENCE (negation word last before the token, at most an article between): `NOT (tools):` suppresses, while `do not touch tools/lib/oc-notify.sh` still FIRES, because an instruction that names the surface is a claim about it; **(b) RESOLVE** — the token must resolve to a tracked PATH, so a bare directory prefix is evidence of nothing.
  Both are executed by **`tools/issue/oc-issue-scope <N> [--json]`** — `bucket` is `IN` / `OUT` / `UNPINNED`, `resolved` names the surface it actually resolved, `title_disagrees` flags a body whose surface contradicts its title prefix, and rc 1 means UNPINNED (no resolvable surface claim), which is a question for the body's author, not a licence to fall back to the title. **A patrol that hand-rolls this regex WILL drift**: three variants of the same test failed in one session and every one was caught by a human reading a specimen rather than by the procedure — title-prefix (#419/#471, v0.4.236), bare-prefix negation (#531, this ruling), and the #439 substring trap where `tools/` matches inside `src/brain/tools/`. Verified on those specimens 2026-09-26: #531 → OUT (`src/channels/telegram/await_sweep.rs`), #419 → OUT (`src/brain/tools/subagent/notify.rs`, not fooled by the substring), #471 → UNPINNED with `title_disagrees`, #433 → IN (`tools/lib/oc-notify.sh`).

### Legacy upstream-assigned patrol — MIGRATION ONLY since the fork-first order (owner order 2026-10-04; SUPERSEDED 2026-10-09)

**SUPERSEDED 2026-10-09 — this patrol is now a MIGRATION, not a standing population.** The fork-first order (owner 2026-10-09) makes the FORK `leshchenko1979/opencrabs` the binary tracker and sends upstream `opencrabs/opencrabs` no new issues; the two open upstream issues we authored (#2003, #2004) are closed with a pointer and reopened at the fork. So the set below is **read once per cycle ONLY until it empties**, each member being closed-with-pointer and reborn at the fork — it is never replenished. **Legacy population, read LIVE every cycle — never a remembered count:** `gh issue list -R opencrabs/opencrabs --state open --assignee leshchenko1979`. Measured 2026-10-04: exactly **4** — #1916, #1917, #1918, #1921, all authored by the owner, all OPEN.

**Why they were invisible — two INDEPENDENT blind spots, both measured 2026-10-04 (Triage lane, first-hand; re-verified at source by HQ):**
1. **LAW SCOPE** — the patrol's written population was *"EVERY open fork issue"*, drafted before the two-stream routing (owner order 2026-10-03) and before the binary-tracker TRIAGE grant (2026-10-04). Upstream issues were outside the remit, so **no sweep ever visited them**.
2. **TOOL** — `tools/issue/oc-issue-dispatch` **cannot filter by assignee at all**: `grep -c assignee` → **0**; `ISSUE_JSON_FIELDS` (line 575) = `number,title,labels,body,stateReason,state` — the field is not even FETCHED; and `DEFAULT_TRACKER` (line 128) is `factory`, so a bare `--auto` never looks upstream. **Precision, so the tool is not over-read:** `--tracker binary` IS supported (`--tracker` takes `factory|binary|fork`) — what is missing is the *assignee* filter and an upstream read that does not have to be asked for. **Measured consequence:** `--auto --tracker binary --dry-run` reported 7 dispatched / 14 queued — the 7 were issues assigned to **upstream's own maintainer**, while **all four of ours stayed QUEUED**. The tool dispatches issues that are not ours and cannot see the ones that are. **The tool leg is the TOOLSMITH lane's (their carve-out); the law leg is this section.**

**An upstream assignment is a SIGNAL, not a work order.** The maintainer assigning us an issue puts it on us to *disposition* it — never to build it. **Every issue in this population takes one of TWO dispositions, and a silent skip is the violation:**

| Disposition | Condition | What it means |
|---|---|---|
| **DISPATCH** | the defective surface is **OURS** — §D4 AUTHORSHIP passes (fork work, absent from upstream `main`) | wire it to the owning lane by the normal path (`oc-issue-dispatch`, claim row, `Issue-Ref` trailer). The fix lands on our fork. **A wire is COMPLETE only on the TARGET's CLAIM ROW — a send returning rc=0 is NOT a delivery, and a target REFUSAL leaves the dispatcher's dedup row standing, so `--auto` will not re-send and `--redispatch` is required** (both halves measured 2026-10-04 on #1921). Zero-ack law: `fleet-directives.md:357`. |
| **REPORT** | the surface is **upstream's own** — §D4 fails | the issue is a defect report; its fix belongs to its author and **nothing is built here**. Record the disposition **on the issue itself** (a comment), so a later reader cannot find it standing silently against an owner ruling. |

**A REPORT whose fork fix the owner has DECLINED is PARKED on his word** — not re-dispatched, not withdrawn; it waits, and the wait is stated. (Live case: `opencrabs/opencrabs#1917` §1, declined in q41 on 2026-10-01; its §2 stands on its own merits.)

**§D4 is applied BY HAND on this population too** — the tool does not implement it. Read the surface from the **ARTIFACT** (is the defective code fork work absent from upstream `main`?), never from the tracker the issue happens to live on: an issue on the binary tracker whose surface is OURS is dispatchable, and one on our own fork whose surface is upstream's is not.

**Live dispositions, 2026-10-04 (the four):** #1916 → DISPATCH, lane done (ledger n=14339) · #1918 → DISPATCH, in flight (n=14389/14390, branch `fix/1918-file-link-marker`) · #1921 → DISPATCH, **wire RECEIPTED** — the first attempt to the rich-formatting lane was REFUSED (occupied: mid-ship-chain on #1918, so its n=14395/14396 are SEND notes, never a delivery), re-dispatched to the idle telegram lane `a5b34466` (n=14398/14399) and completed by that lane's claim **n=14401** — its surface is our own #289 work (`is_valid_telegram_photo_url` / `ORPHAN_MEDIA_SCHEMES` / `MediaKind`, commits `010bace66`/`73381aa20`/`8cdc7a7b7`/`91890ffe1`), absent from upstream `main`, so §D4 passes · #1917 → REPORT, §1 parked on the owner (q41), §2 standing.

### Stuck-lane routing — a stuck lane REGISTERS, it does not re-ask (owner order 2026-09-25)

When this lane finds a lane held on an owner decision, the routing instruction is the **Open Questions register**: the held lane calls `tools/state/oc-questions ask --factory <KEY>` in the same turn it parks, and the owner reads it on the constant page. Two things Triage must NOT do: tell a stuck lane to re-ask in its own topic (a daily topic ping is noise, not pressure — once registered, the register's own `asked_at` age is what re-surfaces the question), and register on the lane's behalf (the tool derives the asking session from `OPENCRABS_SESSION_ID` and REFUSES an unbound session, because a cron session can never receive the answer). Canon: `docs/instruments/open-questions.md` in the meta-factory repo (`/root/agent-factories/`) — NOT resolvable from this skill tree; tool `tools/state/oc-questions` (`ask · answer · amend · notify · list · publish · lint · gc`).

### Stale-branch sweep patrol (owner 2026-09-08 "Go then duty 4+6", v0.4.108 — DAILY, rides the T4 census turn)

run
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
### Telegram-law TOOL_ACCUM enforcement (v0.4.43, A12)

the violation
  pattern is caught from evidence, not intuition. On suspicion run
  `./tools/audit/oc-tg-audit <session-uuid> [--days N]` — the only sanctioned
  scanner (raw log grep is retired; the tool embodies the log format and the
  banned-tool list). A matching row → notify the rule
  (SKILL.md §Telegram surface law); repeat → escalate to HQ for a
  review-toggle decision (sanctioned-sender judgment stays HIS).
### Delivery-cadence patrol (2026-09-04 law)

lanes defaulting to
  `now`-mode for receipts/ACKs violate the cadence law — flag with evidence,
  route the correction to the offending lane, escalate repeat offenders to the
  HQ.
### Harvest backlog patrol (owner 2026-09-08 "Go", v0.4.97 — DAILY; census TARGET RE-SCOPED by owner ruling 2026-09-19, v0.4.225)

run
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
### Upstream PR-state patrol (owner 2026-09-08 "Go then duty 4+6", v0.4.108 — DAILY, rides the T4 census turn)

On each harvest census,
  re-verify the state of every OPEN upstream PR of ours
  (`gh pr list -R opencrabs/opencrabs --state open --json number,state,mergeable` —
  one command for the whole set, fresh receipt, never memory; a fleet census verb is
  ROUTED to Toolsmith, c27 J-6) and post the states in the census line.
  Closes the ownerless gap that let #1451's CONFLICTING sit undiscovered
  for hours (found ad hoc 2026-09-08 16:48Z). Base-freshness law extends
  to filing-time: census CLEAN results must name the upstream sha tested
  against (Triage lesson, ledger n=2083).
### Cron liveness patrol (owner 2026-09-08 "Go then duty 4+6", v0.4.108 — DAILY, rides the T4 census turn)

Verify the law-carrying
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
  **TWO orders, TWO end conditions (2026-10-04, raised by Triage `530c29ec`).** A
  second owner order — `2026-09-29T09:19:48Z`, verbatim: *"Turn off all your crons
  and set yourself a goal to finish the upstream sync. All questions requiring my
  attention should go to the open questions board. You can finish when everything
  has been resolved besides not closed open questions."* — disabled
  `oc-triage-factory-patrol` (id `0c0b0ba2`) and `oc-triage-owner-digest` (id
  `3e73d7ca`) at 09:22Z and SUPERSEDED the `2026-09-19T03:01:53Z` partial lift for
  those two jobs. The two orders lift INDEPENDENTLY: the 09-18 freeze only on the
  owner's word (*"Until I lift the freeze"*), the 09-29 order on its own completion
  criterion. Classify BOTH groups ORDER-HONOURED, and read the MARKER, never this
  enumeration alone — it carries one section per standing order.

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
   never from memory. **THE SWEEP'S POPULATION IS THE UNION, NOT THE FORK ALONE
   (owner order 2026-10-04):** also enumerate
   `gh issue list -R opencrabs/opencrabs --state open --assignee leshchenko1979`
   (**LEGACY, migration-only since the fork-first order 2026-10-09 — it only shrinks**).
   Those issues are **DISPOSITIONED** by §Legacy upstream-assigned patrol (T4) — DISPATCH
   or REPORT, or (for the two we authored, #2003/#2004) closed-with-pointer and reborn at the fork —
   and **this sweep never closes them unilaterally**: its closure authority is
   fork-only, and a legacy upstream issue is closed by its author, by our PR filing, or by the migration.
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
     `leshchenko1979/opencrabs-dev-factory`) for `tools/**` (v0.4.229, filing
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
     `§Dispatch Eligibility — the 4-bucket predicate` (this file).
4. For each unclaimed issue: route to the owning editor, or if
   none is obvious, surface the unclaimed set to HQ for
   dispatch — do NOT let it sit silent (the v0.4.91 gap: "claimed when
   someone claims it" is not assignment).
   - **Designated Domain Affinity & Topic Context Focus Law (owner order 2026-09-17)**: Dispatches MUST match the target lane's designated topic/feature domain via `tools/issue/oc-issue-dispatch`. Never dispatch to a random idle lane or specialized lane with negative domain affinity (e.g. dumping persistence/db issues onto Mermaid/photo lanes). If no affinity match is idle, leave queued or commission a domain-appropriate lane.
   - **Wire Envelope Law (owner order 2026-09-13)**: Every dispatch wire envelope
     must conclude with: `Ack contract: NONE — claim on ledger (oc-ledger claim) and proceed.`
     Triage verifies delivery by polling `workers-ledger.json` (`oc-ledger events --kind claim`),
     NEVER by expecting, requesting, or processing `session_notify` conversational acks.
   - **Smoke-ceiling label on wire (HQ ruling 2026-09-18, v0.4.202)**: before wiring an issue, read the live carrier set (`tools/ship/oc-carrier-features`). When the deliverable's feature-gated modules are OUTSIDE that set, the wire MUST carry `SMOKE CEILING: UNPROVEN (structural N/A) — <feature> absent from carrier set`, and the issue MUST be linked `--add-blocked-by` the carrier-set-widening issue. Such issues ARE dispatchable (`DISPATCHABLE = unclaimed AND vetted`): the CI gate compiles `--all-features`, so the code is verifiable — only the HARVEST is blocked. Never park or block an out-of-feature-set issue for that reason alone. Canon: `§Out-of-Feature-Set Issues — Dispatchable, Ceiling Labeled` (this file).
5. Already-claimed issues:
   - Normal progression: no action; the owning editor's chain owns them.
   - **Continuous Relationship Linking Mandate (owner order 2026-09-16; creation gate + backstop added 2026-09-25)**: During triage sweeps, if Triage discovers open issues that depend on in-flight features or unharvested subsystems, Triage MUST establish native links in the same turn via `gh issue edit <issue> --parent <parent-issue>` and/or `gh issue edit <issue> --add-blocked-by <blocker-issue>`.
     - **CREATION GATE — THREE LEGS, NOT ONE (owner order 2026-10-05, origin opencrabs/opencrabs#1932).** A `fix(`/`bug(`-titled issue MUST, ON the creating command (`tools/issue/oc-issue-create`): **(a) DECLARE ITS ORIGIN** — `--parent <N>` for a fork feature issue, or `--root upstream:<sha|PR|path>` where the surface was inherited from upstream (`upstream-rooted` -- the common case, and NOT an orphan); `--no-parent "<reason>"` is the last resort, recording a DECLARATION rather than a silence. **(b) CARRY AN ASSIGNEE** — `--assignee <login>`: on the FORK binary tracker `leshchenko1979`, on the FACTORY tracker `leshchenko1979` — the ONLY assignable account on each (measured 2026-10-10: `gh api repos/leshchenko1979/opencrabs/assignees` and `gh api repos/leshchenko1979/opencrabs-dev-factory/assignees` each return exactly that one login). **THE `adolfousier` CONSTANT IS RETIRED — it was calibrated when the binary tracker WAS upstream `opencrabs/opencrabs`, where he is the maintainer; the 2026-10-09 two-stream order moved every binary issue to the FORK, where he is not a collaborator (`collaborators/adolfousier` → 404) and `--add-assignee adolfousier` SILENTLY NO-OPS — rc 0 with the assignees set unchanged, so the failure reads as success.** The leg exists because a tracker's `auto-assign.yml` can assign the AUTHOR rather than the intended claimer: dated history, upstream's did, so #1932 landed on `leshchenko1979` and was hand-corrected to `adolfousier` (unassigned+assigned 2026-10-05T06:27:32Z). **(c) ESTABLISH THE NATIVE LINK** where the declared origin resolves to a SAME-TRACKER issue — `--parent <N>` at creation, or `gh issue edit <issue> --parent <N>` as the immediate next action; a comment-only `root:` satisfies DECLAREDNESS, never the LINK when a same-tracker parent exists. For `--root upstream:<sha>` the parent is derivable from that commit's own `Closes #N` / `Fixes #N` trailer (#1932's root commit `ede0763be` carries `Closes #737`, so #737 is its parent). Where the origin has NO same-tracker counterpart (an upstream PR or path), the comment declaration IS the link and no native link is possible. Raw `gh issue create` for a fix-title is a violation.
     - **BACKSTOP LEG (this is what stops the gate itself lapsing)** — every Duty T5 sweep asks **"is the ROOT declared?"**, never "does it have a fork parent?": an OPEN fix-titled issue with no parent and no `--root` is either linked mechanically (where the blame method derives a single unambiguous originator) or given a declaration, and only a SILENT one is flagged — into the Open Questions register, never a bare note. **Why declaredness rather than parentage (measured 2026-09-26):** 92 of 140 open fix-titles carry no parent and most are legitimately `upstream-rooted`, so a detector asking for a fork parent flags them FOREVER — and a permanently-red detector is one every lane learns to ignore. The ORIGINAL mandate had no detector at all, which is why it silently stopped for three days; tool-refusal plus patrol detection is the only pair that cannot lapse unseen. **POPULATION BOUNDARY — the leg runs on POST-GATE issues only** (created at or after **2026-09-25T22:33:06Z**, when `oc-issue-create` began refusing a silent fix-title). An issue filed BEFORE the gate was never asked to declare, so flagging it measures history rather than compliance — and that distinction is what makes the detector usable: measured 2026-09-27, the whole-open-set scope flags **92.8%** (90 of 97, permanently red), while the post-gate scope flags **16.1%** (5 of 31, actionable). **THE PREDICATE IS MECHANICAL AND NAMED — never a hand-list:** for each post-gate OPEN `fix(`/`bug(`-titled issue, read the native parent via GraphQL `issue.parent.number` (the REST issue object's `.parent` projection returns a confident null for EVERY issue — a recorded false negative) and the issue's comment set; the root counts as DECLARED if a parent exists or ANY comment's body matches one of `no parent derivable` / `root:` / `upstream-rooted` / `parent:`. Only an issue with neither is flagged. **Match the literals against ALL comments, never the FIRST (measured 2026-09-28):** a declaration posted retroactively cannot be the first comment on an issue that already carries a commit or design note, and for an existing issue a comment is the ONLY channel `oc-issue-create --root` offers (that flag is creation-time) — so a first-comment read defeats the remedy on exactly the population it must clear. Triage measured 1 of 6 declared under the first-comment read and 6 of 6 under the all-comments read, zero false positives. **Instrument, stated so it is not over-read:** `--root <obj>` IS implemented (`tools/issue/oc-issue-create`, landed #646 2026-09-27) — it resolves a sha / PR / path against the upstream repo, REFUSES an unresolvable object rc 3 rather than recording it, and rides the FIRST COMMENT as `root: <obj>`. `--no-parent "<reason>"` remains the last resort. A lane that declares its root in the BODY is equally compliant. A flag on such an issue is a question to the filing lane, never a verdict. **REGISTRANT — the flag is registered by the cron's DELIVERY lane, never the executing session:** the T5 executor is UNBOUND, so `tools/state/oc-questions ask` refuses it `rc=2` BY CONSTRUCTION and a flag assigned to it can never be filed. The cron's `deliver_to` target IS bound and is the lane that registers — the executor hands its flag list over.
     - **BACKSTOP LEGS (b) and (c) — the T5 sweep also asks the two questions the ORIGIN leg alone cannot (owner order 2026-10-05, origin opencrabs/opencrabs#1932).** Beyond "is the ROOT declared?", every Duty T5 sweep asks **(b) "does it carry an ASSIGNEE?"** — an OPEN `fix(`/`bug(`-titled issue with an empty `assignees` set is flagged, because upstream's `auto-assign.yml` puts the AUTHOR there and the author is the wrong owner for a reported defect; and **(c) "is the native link ESTABLISHED where one is possible?"** — where the declared origin resolves to a SAME-TRACKER issue (a `--parent <N>` value, or the `Closes #N` / `Fixes #N` trailer of a `--root upstream:<sha>` commit) and no native parent link exists, the issue is flagged for the link even though its `root:` comment makes it DECLARED. **POPULATION BOUNDARIES differ per leg and are stated, not inherited silently:** legs (a) and (c) share the origin gate's POST-GATE boundary (created at or after **2026-09-25T22:33:06Z**), while leg (b) runs on issues created at or after the owner order (**2026-10-05T10:19Z**) — upstream issues filed before it were never asked to assign, and #1932 itself (created 2026-10-04) was hand-corrected by the owner rather than by this leg. **The assignee read is mechanical and untrapped:** `assignees` is a real field on the REST issue object (unlike `.parent`, whose projection returns a confident null for EVERY issue), so leg (b) reads it directly with no GraphQL workaround. The registrant rule is the origin leg's: the cron's DELIVERY lane registers; the T5 executor is UNBOUND and `oc-questions ask` refuses it `rc=2` by construction.
    - **DESIGN-GATE BACKSTOP (owner order 2026-09-26 ~22:00Z)** — every Duty T5 sweep also asks whether each CLAIMED fix-titled issue carries the two records the pre-design law requires: (i) a **validation note** (the duplicate-search result, and the reproduction command with its observed output) and (ii) a **design comment posted before the first anchored commit**, unless the claim declares the repair mechanical. **POPULATION BOUNDARY — the leg runs on issues CLAIMED at or after `2026-09-26T22:00Z`**, when the pre-design law landed; an issue claimed before it was never asked, so flagging it measures history rather than compliance. Measured 2026-09-27 over the whole claimed set (45 issues): leg (i) flags **42/45 = 93%** and leg (ii) **43/45 = 96%**, with 27 of the 45 carrying ZERO comments — a permanently-red detector, and a permanently-red detector is one every lane learns to ignore. **THE PREDICATE IS MECHANICAL AND NAMED — never a hand-list:** for each in-scope CLAIMED OPEN `fix(`/`bug(`-titled issue, (i) counts as DECLARED when the FIRST COMMENT BODY **or ANY claim row for the issue or THE ISSUE BODY** carries a validation note matching one of `duplicate` / `reproduc` / `still reproduces` — **the record is per-ISSUE, never per-claim-row** (measured 2026-09-28: #544 complied at row n=11996, then was re-claimed at n=12353 with a bare start-marker, and a latest-row read made the compliant record invisible. Re-claiming is ROUTINE — the closed-claim sweep releases claims and lanes re-claim — so a latest-row read loses its content on a normal action. A lane that validated once does not un-validate by re-claiming) — **the claim row is a channel item 6(b) NAMES** (*"record the command with its observed output in the claim row or the design comment"*), so a comment-only read flags a lane that complied by the permitted route (measured 2026-09-28: #544's claim row n=11996 carries the complete duplicate sweep and reproduction measurement and was flagged anyway; its only comment is a post-hoc implementation note). **The asymmmetry was the tell** — leg (ii) already read the claim row (*"or the claim row's own text declares the repair mechanical"*) while leg (i) did not; (ii) counts as DECLARED when a comment's `createdAt` precedes the earliest fork-main commit whose `Issue-Ref` trailer names the issue, **or** the claim row's own text declares the repair mechanical. Only an issue failing BOTH is flagged. **THE VACUOUS CASE IS NAMED, so the next runner does not guess (measured 2026-09-28):** when the issue carries NO fork-main commit whose `Issue-Ref` trailer names it — the common case, 26 of 29 in-scope claimed issues at the 06:26Z patrol — leg (ii)'s referent DOES NOT EXIST, so a missing anchor reads as the ABSENCE OF THE THING MEASURED, never as a failure; the claimed-note arm still applies. The opposite reading flags 20 issues on a condition none of them can satisfy, which is the permanently-red shape this leg's population boundary exists to avoid. **REGISTRANT — the flag is registered by the cron's DELIVERY lane, never the executing session:** the T5 executor is UNBOUND, so `tools/state/oc-questions ask` refuses it `rc=2` BY CONSTRUCTION and a flag assigned to it can never be filed. The cron's `deliver_to` target IS bound and is the lane that registers — the executor hands its flag list over. **Honest limit, stated so it is not over-read:** the patrol REPORTS, it does not close — an issue whose gate never triggered and whose repair is mechanical owes no comment, so a flag is a question to the lane, never a verdict.
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
(`opencrabs/opencrabs`), so `src/**` AND `.github/**` stay harvestable
(upstream carries `.github/workflows/{auto-assign,ci,prerelease,release}.yml`),
while the skill repo `leshchenko1979/opencrabs-dev-factory` has NONE, so everything it
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

**Fork-identity exemption — the harvest gate is vacuous when the CHANGE has no
upstream referent (HQ ruling 2026-09-29).** The v0.4.232 exemption above is
vacuity of the *carrying repo*; this is vacuity of the *change*. A defect may be
**fork-only BY CONSTRUCTION** — an artifact of the fork carrying a parallel issue
tracker whose numbering COLLIDES with upstream's. Such an issue fits NONE of the
three branches: branch 1 can never fire (no upstream PR can carry a change
upstream does not want), branch 2 has no fork-only parent subsystem to hang on
(the subject is tracker hygiene, not a feature symbol), and branch 3 does not
apply because `src/**` is harvestable. Measured instance: #683 — and its residual
#705 — qualify INHERITED comments that cite bare `#679` meaning **upstream's**
#679, in a tree where bare `#679` now resolves to the **fork's** #679: fork #679
is "quiet mode for groups", upstream #679 is "tables render as bare HTML". Two
issues, one number, and the fix is meaningful only inside the fork.

**The bar is FALSE-UPSTREAM, not merely UNNECESSARY-UPSTREAM.** State the
post-fix text in the upstream tree and evaluate its truth. Inside upstream, a
citation qualified `ex-upstream opencrabs/opencrabs#679` asserts a falsehood —
upstream's bare `#679` already resolves correctly — so the change is not
redundant there, it is WRONG there. That is what makes the referent absent: no
upstream object exists for the change to attach to. A fix that would be merely
redundant-but-TRUE upstream stays in branch 1 or 2; this exemption does not reach
it, and it must never be cited for one.

An open fork issue MAY be closed autonomously when ALL hold: (1) it is `landed`
on its OWN fork surface, recorded by a ledger row of kind `done`/`close`
addressing the issue (`oc_claims.LANDED_KINDS`); (2) the fork-only determination
is recorded AND names the colliding-number pair (fork #N and upstream #N, both
titles) and shows the post-fix state FALSE upstream; (3) NO fork-only parent
subsystem exists that branch 2 could hang the close on — if one does, branch 2
STANDS and this exemption is refused. The close comment names the shipped sha(s),
the smoke row and the fork-only determination; the close identity guard below
applies unchanged. The LANDING-never-the-trigger corollary is satisfied rather
than waived: the trigger here is the fork-only determination itself, which IS the
statement that no PR can ever file.

This is an **exemption on the harvest gate, not a fourth autonomous-close
class** — the same framing as v0.4.232, and for the same reason: (a)/(b)/(c)
dispose of issues whose work is NOT done, whereas this closes an issue whose work
IS done, recorded, and smoked on a change no PR can ever carry. Receipt: #683
(deployed.sha = 4ab5e66f7a933df1d5c111edc610bc16faa97e88, smoke row
2026-09-29T10:12:54Z PASS run=36552264061, ledger `done` n=13662). The residual
#705 is the same CLASS but **not yet an instance** — it is OPEN on ordinary
grounds (0 smoke rows, 0 `Issue-Ref` commits, its nine sites unfixed), so
condition (1) FAILS for it; it enters this exemption only when its own work lands
and smokes. Raised to HQ by the Lifecycle: Restarts lane 2026-09-29.

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

WHAT comes back: HQ's rulings and version batches absorb here the
same way they absorb everywhere — disk absorption (§Glossary, SKILL.md),
zero-ping (hq.md Duty 3).

## Retired Duties & Forwarding Pointers

- **ai-antispam / Outreach lane — RETIRED from the opencrabs-dev team (owner order 2026-09-12).** Chat `-1003993000918`, topic `10780`. Send it **no** board updates, dispatches, briefs, drift-check requests, ledger expectations or status nudges — it is not a board target and owes the process nothing. Its Triage-assigned batch (#3, #6, #8, #9, #10, #11, #12) is complete and all 12 issues on `leshchenko1979/ai-antispam-outreach` are closed. **The retired lane and this one share the `ai-antispam` roster label — read the TOPIC, not the label, before treating a directive as yours.** A fork-rebase FREEZE or other opencrabs-dev fork/ship directive arriving in a topic that is actually an ai-antispam topic is not yours: check scope before stopping work, and do not send the worktree/dirty-count reply. (BS-5, c27 — moved here from the passive store; re-finding of c26 BS-8(b).)
- **Duty T1 (Idea box intake)**: Retired v0.4.176 per direct process-owner routing. **Successor: `fleet-directives.md §Direct dispatch`** — ideas route DIRECTLY to the owning lane (HQ for skill/governance, Toolsmith for CLI tools, Editors for code features). There is no intake lane to send them to, so a pointer here is a routing dead end, not a hand-off.
- **Duty T2 (Quirk intake & relay)**: Retired v0.4.176 per the Direct Dispatch Law. **Successor: `fleet-directives.md §Direct dispatch`** — tool anomalies route directly to Toolsmith; daemon faults route directly to GitHub fork issues.

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

## Out-of-Feature-Set Issues — Dispatchable, Ceiling Labeled (v0.4.202, HQ ruling 2026-09-18) [LANE]

**Origin:** Triage asked whether an issue whose deliverable lies outside the carrier feature set is dispatchable at all under the 4-Leg Smoke Rubric — raised after #319 was wired 3× across two lanes with zero claims at the time of the read (ledger n=8161, n=8234, n=8261). The churn was real. The answer is YES: the defect was an **unlabeled smoke ceiling**, not an undispatchable issue.

### F1 — Dispatchability never depends on the carrier feature set

The existing classification bucket governs — `DISPATCHABLE = unclaimed AND vetted AND NOT landed`, stated once and canonically in §Dispatch Eligibility below (the 4-bucket law). The carrier set gates the **binary**, never the **codebase**: a feature-gated module is still compiled and unit-tested by the CI gate, whose flags are `--all-features` (both the clippy and the test step of `pr-checks.yml`). Work on such an issue is therefore verifiable work and MUST NOT be parked, blocked, or skipped for being outside the built set.

### F2 — The ceiling is `structural N/A`, and the verdict MUST read `UNPROVEN (structural N/A)`

Leg 4 (behavioral probe) is unreachable when the deliverable's modules are absent from the shipped set. `structural N/A` is a legal leg-4 substitute under the 4-Leg Smoke Rubric — but per the corrected-code presence rule, presence is not behavioral proof: the verdict reads **`UNPROVEN (structural N/A)`** and is **NEVER GREEN**. The ceiling is determined mechanically, not by judgment: read the live set with `tools/ship/oc-carrier-features` and compare it against the deliverable's feature-gated modules.

### F3 — Harvest stays blocked; the lane parks and releases

A smoke PASS is required to file upstream (PR shipment law). `UNPROVEN (structural N/A)` is not a PASS for a live-testable UX feature, so the issue **stays OPEN** under the harvest-gated closure law, and its upstream filing is blocked on the carrier set. **The set stays as-is — owner ruling 2026-09-18 ("Leave the carrier set as-is")**, which answers the widening question this section originally left open: the ceiling is **permanent and intentional**, not a pending decision. A lane therefore NEVER chases a widening request or re-raises the question — the blocker is a STANDING CONSTRAINT. The lane stamps the legs it can prove, names the blocker, and **RELEASES** (`editor.md` §Owner-Dependent Smoke Legs L1, applied to a non-owner blocker). It never idles on the blocker.

### F4 — Dispatch carries the ceiling label and the native blocker link

The churn cure — both operational (Triage-owned; no new tooling, no new class):

1. When `oc-carrier-features` shows the deliverable's modules outside the set, the dispatch note carries `SMOKE CEILING: UNPROVEN (structural N/A) — <feature> absent from carrier set`, so wire 1 behaves like wire N.
2. The issue is linked natively — `gh issue edit <issue> --add-blocked-by 338` (leshchenko1979/opencrabs#338, the carrier-set **decision record** and the blocker anchor) — per the Continuous Issue Relationship Linking order. A wire carries the RELATION, so the anchor's own state never unblocks it: #338 is a RECORD whose decision is MADE (owner ruling 2026-09-18), not a live question. Its closure is Triage's call under `triage.md §Duty T5` (Autonomous closure, (c) owner-confirmed-withdrawn); no lane re-raises the question while the close is pending.

**Worked example (2026-09-18):** #319 (post-delivery re-entry for failed image delivery on Slack / Discord / WhatsApp) — carrier set `telegram,code-graph,browser`; the three channels are feature-gated modules in `Cargo.toml [features]`, compiled only under `--all-features`. The CI gate covers them; the shipped binary does not. Verdict ceiling `UNPROVEN (structural N/A)`; harvest blocked on the carrier set — **permanently**, per the owner's 2026-09-18 ruling that the set stays as-is (leshchenko1979/opencrabs#338, the decision record); lane released. The 4th wire landed a claim (n=8274) — the issue was dispatchable on wire 1.


## Dispatch Eligibility — the 4-bucket predicate, with the LANDED term (v0.4.204, HQ ruling 2026-09-18) [LANE]

**Canonical statement — THIS section is the one home; every other reference (`triage.md` T4/T5) points here.**

`DISPATCHABLE = unclaimed AND vetted AND NOT landed`

| Bucket | Predicate | Action |
|---|---|---|
| **CLAIMED** | an open claim-ref exists | no action — the owning lane's chain holds it |
| **PARKED** | owner standdown | never re-ignite |
| **UNVETTABLE** | no acceptance criteria | park, naming the reason |
| **DISPATCHABLE** | unclaimed AND vetted AND **NOT landed** | wire it |

### D1 — "landed" is `LANDED_KINDS`, NEVER `CLOSING_KINDS`

`landed` := a ledger row of kind `done` or `close` addressing the issue, **OR** a fork-space commit on `main` (fork-space = carries a `Session-Id` trailer) naming the issue by EITHER an `Issue-Ref: #N` trailer OR a trailing `(#N)` in the subject — the git arm has TWO ref forms, both fork-scoped by the `Session-Id` discriminator, and NEITHER is commit-message prose. Either arm marks it landed. Implementation: `tools/issue/oc-issue-dispatch` — `ledger_landed_issues()` (imports `oc_claims.LANDED_KINDS`) + `fetch_landed_issues()` (git arm). Tool side: leshchenko1979/opencrabs#337.

**IDENTITY — a number is a REFERENCE, not evidence; the naming commit's changed files must intersect the issue's own surface (v0.4.218, filed by Triage lane `530c29ec`).** A commit can name `#N` in its subject while implementing a different subsystem entirely, and every landed/merged inference downstream then reads N as done. `landed` therefore ALSO requires identity. A commit naming `#N` whose changed files do not touch N's subsystem is NOT evidence that N landed. The same leg applies on the HARVEST arm (`tools/harvest/oc-harvest-census check` / `oc-harvest-dispatch vet`), where the issue→PR map is built from the title's trailing `(#N)` and the head branch name — so a corrupted `(#N)` poisons the map, and the refusal is PERMANENT because the squash sits in upstream history forever. A REOPENED issue overrides the merged inference (the #414 override, which today reaches `oc-issue-dispatch` only).

**Live instance, receipted (2026-09-19 15:05–15:20Z, by the filing lane).** `oc-harvest-census check 199` → rc=1 `REFUSED: Target 199 is already MERGED upstream in PR #1557`; `gh pr view 1557 --json state,mergedAt` → `state=CLOSED, mergedAt=null`. The content IS upstream — `132da1fcc fix(loop-guard): exempt paginated arguments … (#199)` — while `#199` itself is a DIFFERENT subsystem (OPEN / REOPENED, `fix(a2a): the gateway listener is load-coupled…`), and the landed commit `b10ca242f` touches `src/brain/agent/service/helpers.rs`, `src/config/profile.rs`, `src/tests/loop_guard_test.rs`, `src/tests/profile_pid_lock_test.rs` — **0 files under `src/a2a/`**. Editor lane `c6b1a539` claimed #199 at 15:18:28Z (n=9501) on `fix/199-the-gateway-listener-is-load-couple`, so the Phase-7 harvest gate will refuse legitimate freshly-built work unless this leg lands.

**LEG-SCOPE — both landed arms are ISSUE-scoped by implementation, so ONE leg's `done` marks the WHOLE issue landed (v0.4.247, filed by Triage lane `530c29ec`, 2026-09-24).** Both arms ask only *"did anything land for #N"* — neither asks *"did EVERY declared leg land"*. On an issue whose **scope split names more than one owner/surface**, a `done` row stamped for ONE leg closes the claim (`oc_claims.open_claims(#N)` returns **empty** — `done` is a `LANDED_KIND`, so `claim_is_closed` fires) and simultaneously satisfies the ledger arm *and* the git arm, so the issue reads LANDED and every remaining leg becomes **undispatchable AND invisible**: the normal path refuses it (`RC_TARGETED_LANDED = 8`; `--allow-landed` is the escape hatch on `tools/issue/oc-issue-dispatch`), and **no sweep can see the gap, because every sweep consumes the same predicate.** Note the arms are not fixable one at a time: a leg-aware ledger arm alone changes nothing, because the git arm still vetoes on the same issue number.

Discipline this clause adds:

- A `done` row on a **multi-leg** issue MUST name the LEG it covers — the surface (or the files) actually landed, not just the issue number.
- Dispatch on a multi-leg issue whose `done` covers only part of it is a **deliberate `--allow-landed`**, never a silent refusal.
- Where an issue body names a leg at a surface, that leg is an **OBLIGATION to that surface's owner** — claimed and closed by that owner, not discharged by another leg's landing.
- A census reading `residue 0` is a statement **about the predicate**, never a statement that no in-scope work is open.

**Live instance, measured 2026-09-24 (Triage lane, re-verified first-hand by HQ).** `leshchenko1979/opencrabs#393` (owner order 2026-09-19) carries a three-surface scope split in its own body: Editor `src/**`, **Toolsmith `tools/**`**, HQ skill-markdown. The Editor leg landed (`07b6372c4`); the HQ leg landed; and `done` row **n=10159** ("smoke PASS verified for issue #393") closed the issue for dispatch — verified: `open_claims(393)` → **0 rows**, ledger rows targeting 393 → exactly `[(10159,'done')]`. The identity read is ALSO masked: the skill-repo index carries #393 via `5b9609b3`, a **LAW** commit whose changed files are `SKILL.md`/`fleet-directives.md`/`hq.md`/`toolsmith.md` — **not one `tools/` file** — which is the identity leg above applied per-SURFACE but never per-LEG. The Toolsmith leg is unshipped and **actively pinned**: `--interrupt` (the pre-#393 boolean) is still passed by `tools/lib/oc-notify.sh` (the rc-3 retry) and `tools/notify/oc-notify-fanout`, and `tools/ship/oc-deploy`'s selftest **FAILS** if the second verb call lacks `--interrupt` — asserting the old shape — while the issue's own target state prescribes `--interrupt` → `--mode interrupt`, which is live and valid (`--mode` help: *"turn-end (default) | interrupt | quiet"*). **No ledger row ever claimed a `tools/` leg for #393.** Either the migration is owed or its dropping was a decision; neither is recorded, and that is the defect.

**The transferable half: the predicate cannot audit itself.** The class was found by re-deriving the cycle's own numbers against **independently asserted** expectations (24 OK / 1 MISMATCH), not by any sweep arm — a sweep that re-derives its own predicate returns the predicate's answer.

`tools/lib/oc_claims.py` is the ONE canonical predicate — no lane re-inlines it. It carries BOTH sets, and their distinction is load-bearing:

- `LANDED_KINDS = ("close", "done")` — evidence the WORK landed.
- `CLOSING_KINDS = ("close", "confirm", "reject", "done", "unclaim")` — the kinds that can close a CLAIM. A strict superset; **NOT interchangeable**.

**Using `CLOSING_KINDS` as the landing test STARVES real work.** The module's own docstring records the measurement: over the live ledger on 2026-09-18, `CLOSING_KINDS` reaches 228 issues, 125 of them ONLY via the three non-landing kinds — and 48 were reachable by `unclaim` ALONE (a released claim whose work was still unbuilt), suppressed purely because a claim had been RELEASED. A `confirm` row flips a bookkeeping flag and ships nothing; an `unclaim` row returns the issue to the pool, unbuilt; a `reject` row means no work was done at all. **None of the three is evidence the work shipped**, and a released-but-unbuilt issue is legitimately re-dispatchable.

### D2 — Landed-but-unharvested issues are HARVEST QUEUE, not editor dispatch

The closure law (`triage.md §Duty T5` — Autonomous closure) deliberately keeps DONE work **OPEN** until its own upstream PR files. Without the landed term every such issue reads `unclaimed AND vetted` → DISPATCHABLE, so the sweep re-wires exactly the issues the closure law forbids closing. **With the term present the two sets are disjoint by construction:** an OPEN issue whose work already landed in fork `main` waits on a PR, not on code — it routes to the harvest queue and NEVER to an editor lane.

### D3 — Live instance, receipted (2026-09-18)

One T5 sweep (ledger n=8331–8341) wired 8 issues; **5 of the 8 were OPEN AND carried a ledger `done` row** — #330 (n=8317), #324 (n=8192), #302 (n=8267), #299 (n=8325), #297 (n=8266). GitHub state OPEN for all five, verified the same turn. #302's `done` row is Triage's own and says verbatim: *"Issue STAYS OPEN under the harvest-gated closure law until its own upstream PR files"* — and the sweep wired #302 anyway. A second surface, the `oc-harvest-dispatch-4h` cron (session c32f43ee), wired the same issue from the same root cause: `done` + zero claims satisfies the old predicate. Editor 127429e6 claimed #297 (n=8345) then stood it down (n=8353, "dispatch was stale, no work owed") — one wasted claim, real churn.

### D4 — AUTHORSHIP — a defect in another's feature/fix is never dispatched for implementation (owner order 2026-10-04) [LANE]

**Canonical owner-order record:** `fleet-directives.md §Contributor ownership — defects in others' features/fixes`. This subsection is the **operative dispatch law** — the gate the Triage lane applies when it decides what is wired for implementation.

Owner, verbatim: *"if we are about to file an upstream issue about a defect in a feature that was not implemented by us or in a fix that was not ours, we expect the owner of that fix/feature to fix it instead of fixing it ourselves unless I want to have an urgent fix on our fork only. This is to respect contributor ownership and to preserve their motivation and to foster their learning."*

**The gate.** An issue whose defect lies in a feature or fix **we did not author** — an upstream contributor's, another lane's, any author that is not us — is **NOT dispatchable for implementation** on our fork. It is **reported** (BINARY → the FORK `leshchenko1979/opencrabs`, FACTORY → `leshchenko1979/opencrabs-dev-factory`, per two-stream routing) and the fix belongs to **the owner of that feature/fix**. The report is the whole deliverable: **no fork fix branch, no fix PR, no editor work order** against a surface we did not author.

**Authorship is read from the artifact, never assumed from the tracker.** The defective surface's own history decides — who wrote the code (upstream vs fork), and who filed the issue. Where the surface is OURS, the normal dispatch path applies unchanged; this gate never blocks our own work.

**The one exception, and it is the OWNER's alone.** *"unless I want to have an urgent fix on our fork only"* — an urgent fork-only fix is ordered by the owner, per case. A lane never assumes it because the defect blocks us, degrades us, or looks trivial. Absent his word, the report stands alone and the fix waits on its author.

**Not mechanized (measured 2026-10-04): `oc-issue-dispatch` does NOT implement this gate.** The tool's predicate stays `unclaimed AND vetted AND NOT landed` (D1/D2 above); AUTHORSHIP is a **dispatcher-side gate applied BEFORE wiring**, so a dispatch that skips it is a **lane defect, not a tool defect**. Whether it becomes a tool leg is a `tools/**` decision (Toolsmith carve-out), not a law edit.

**Population note — the LEGACY upstream assigned-to-us set (owner order 2026-10-04; migration-only since 2026-10-09).** This gate is applied by hand to every still-OPEN issue on `opencrabs/opencrabs` assigned to us, and it is what separates that population's two dispositions: §D4 passes → **DISPATCH**; §D4 fails → **REPORT**. That population, its live enumeration and its specimen are owned by **§Legacy upstream-assigned patrol** (T4).
