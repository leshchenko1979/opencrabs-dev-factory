# HARVEST — upstream PR lane: port → gate → file → follow

**Load only after SKILL.md confirmed the role is HARVEST.**

**RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `harvest.md`, `fleet-directives.md` in `active_skills`; re-read on compaction/spawn).

> Single home for the upstream-PR phases. Loaded when Triage dispatches a
> READY cluster (Phase 7 trigger) or an owned PR needs lifecycle action
> (Phase 7b). Editors do NOT load this file — the editor's obligation ends at
> smoke evidence; Triage surfaces and counts, never ports or files.

## Phase 7 — Feature complete → upstream PR

Trigger: the feature is COMPLETE — merged into fork `main`, shipped inside a
green swapped build, smoke test PASS (v0.4.104 4-Leg Smoke Rubric). With tests green
and smoke confirmed, the HARVEST lane prepares the harvested PR branch, posts the smoke
evidence, and files the upstream PR. Development-time contact stays issues-only;
this PR is the ONE sanctioned exception (completed features only).

```bash
# 0a. MODE GATE (v0.4.226) — resolve the current mode LIVE, never from memory:
#       tools/state/oc-ledger events --n 2000 --kind note | grep -o 'MODE: [A-Z-]*' | head -1
#     NO `MODE:` row => DEGRADED (fail closed).
#     Resolution law + fail-closed default: SKILL.md §Hard rules — MODE REGISTER.
#       DEGRADED   -> HOLD the PR GROUP. Request owner approval in YOUR forum topic
#                     (reply or a positive reaction = approval; silence is NOT consent).
#                     File only on that approval.
#       HIGH-TRUST -> proceed to step 0b; the 4-leg smoke PASS is the gate.
#
#     AN APPROVAL IS STAMPED, THEN READ — it does not live in the chat scroll
#     (owner order 2026-09-26T23:50:45Z, landed 2026-09-27). A Telegram reply or
#     reaction is the approval FORM; a ledger row is its DURABLE RECORD, and only
#     the row is what another lane can find. Before filing under DEGRADED:
#       READ FIRST (note the --n, see below):
#         tools/state/oc-ledger events --n 3000 --kind note | grep -o 'FILING APPROVED: group [^—]*'
#       An approval covering YOUR group => file, do NOT re-ask.
#       None => request it in your topic, and THE MOMENT IT IS GIVEN, stamp it:
#         tools/state/oc-ledger stamp note "FILING APPROVED: group #N + #M — owner <ts> (\"verbatim\")"
#     The unit is the PR GROUP, not the issue — one approval covers every member and
#     a member never needs its own tap. Prefix is canonical: `FILING APPROVED: group `.
#
#     --n IS LOAD-BEARING ON THIS READ TOO, for the tail-window reason stated in
#     SKILL.md §Hard rules — MODE REGISTER: a bare `events --kind note` returns ZERO
#     FILING APPROVED rows even when they exist, and an empty read is INDISTINGUISHABLE
#     from "no approval exists" — which makes a lane re-ask the owner, the exact defect
#     this clause exists to remove.
#
#     THE ASK CARRIES A SUMMARY, NOT A NUMBER LIST (owner order 2026-09-30T11:38Z, topic
#     "Upstream: Harvest"): per unit in the group, ONE SENTENCE OF DEFECT and ONE SENTENCE
#     OF FIX, in the user's terms — not the issue number, not test names, not gate receipts.
#     Issue links, census and gate evidence ACCOMPANY it; they do not replace it. An ask that
#     names only issue numbers is INCOMPLETE: the approver cannot approve what he has not been
#     told (owner, verbatim 2026-09-27: "what is 225 about?" — asked because the ask omitted it).
#     Binds the FILING ask ONLY: no new gate, no second approval, and no licence to bundle
#     (one issue per PR still binds — the summary describes each unit separately).
#
#     THE PR CARRIES THE VALUE AND NECESSITY OF THE CHANGE (owner order 2026-09-30T22:48:43Z,
#     relayed by the harvest lane 4b0990b7; recorded n=13833). Owner, verbatim: "It's imperative
#     for a PR to carry the value and necessity of the change. Why do the users need it? What is
#     the job to be done? You should refuse PRs if this is not clear to you from the issues."
#     The PR body MUST carry, in the user's terms: WHY the users need it, and WHAT the job to be
#     done is — a named section, not a phrase in passing.
#
#     ENFORCEMENT IS TWO-TIER, because the halves cost differently (harvest lane's assessment,
#     accepted): (a) PRESENCE is mechanical and cheap — the body carries the named section;
#     (b) SUFFICIENCY is a lane judgment and CANNOT be mechanised — a heading plus "improves
#     reliability" passes any grep and is WORSE than no section, because it launders a weak change
#     as a valuable one. Presence is not behaviour — the same law the smoke verdicts already run on.
#     THE REFUSAL TRIGGER IS "THE STATED VALUE IS UNFALSIFIABLE", never "I am not convinced":
#     unfalsifiable is decidable, unclear is not. Refuse, and name the unfalsifiable sentence.
#
#     CORRECTIVE-CHANGE CARVE-OUT: a corrective fix's value is SUBTRACTIVE — nothing new appears,
#     something false stops appearing (#680 is the specimen: it stops a diagnostic naming the wrong
#     cause). For a `fix(...)` unit the necessity is the DEFECT and the falseness it removes; do NOT
#     invent user-facing value for a change that has none — that inverts the rule's intent.
#
#     THE PRECONDITION IS AN ISSUE-SIDE PROPERTY. When the issue does not state the job to be done,
#     the right act is to FIX THE ISSUE, not to compose prose at PR time. Measured 2026-09-30 by the
#     harvest lane: the fork has NO `.github/ISSUE_TEMPLATE/` (`.github/` carries only CODEOWNERS and
#     workflows/), so a value section is a CONVENTION, not a template product, and nothing makes it
#     self-correct — 4 of 12 sampled open issues carry a value section (720, 719, 710, 709), 8 do not.
#     The issue-side repair is TRIAGE's work item; the refusal must not land on the filing lane for a
#     defect it did not cause.
#
#     TWO GAPS THIS CLAUSE DOES NOT CLOSE, both recorded 2026-09-27 (lane 7e1ebbb6, Duty-4 `20260927-c25`):
#     (a) AN APPROVAL GIVEN BEFORE 2026-09-26 HAS NO READ PATH. The stamp-then-read law begins with this
#         clause, so approvals issued earlier exist only as chat scroll — the owner's 2026-09-25T21:13Z order
#         ('harvest T3 and the 6 issues') is recorded as a ROUTING NOTE, not as a `FILING APPROVED` row, and
#         binds nobody. Treat any pre-clause approval as UNSTAMPED: re-confirm it and stamp it in the same turn,
#         rather than citing the chat line.
#     (b) THE DELIVERY LEG ASKS 'was the TARGET woken?' AND NOT 'did MY PAYLOAD land?'. A `Delivered` verdict
#         proves the route; the content is settled by the target's OWN row (messages / notify_queue), never by
#         the verdict. Where the two disagree the row wins, and a mid-turn park is a delivery, not a loss.
# 0b. FILING NOTICE: post the smoke-test EVIDENCE + the filing report in
#    YOUR forum topic (what you drove, what you saw, run id + built sha + PR URL).

# 1. list fork-only commits, pick THIS feature's (trailers + touched files)
#    — mechanized: `tools/state/oc-attrib --range <old>..<new> --contributors` (3-col TSV:
#    session-uuid / issue_refs / sha7s) or `tools/state/oc-attrib --range` for
#    roster-resolved roles; the raw form:
git -C ~/opencrabs fetch adolfousier
git -C ~/opencrabs log --format='%H%x09%s%x09%(trailers:key=Session-Id,valueonly)' \
  adolfousier/main..origin/main

# 2. harvest onto a branch off UPSTREAM main — NEW worktree, usual hygiene
#    (E1, v0.4.80: `oc-wt add --create` IS the sanctioned creation path.
#     The old "oc-wt never creates" raw `worktree add -b` ritual taught a
#     false interface fact; use `--create` unless that flag is unavailable.)
tools/git/oc-wt add up-<feature> leshchenko1979/<feature> --create --from adolfousier/main --repo ~/opencrabs
git -C ~/opencrabs-wt/up-<feature> cherry-pick <sha1> <sha2> ...
# 2-fresh. BASE FRESHNESS before the gate dispatch (Duty-4 P4, v0.4.80;
#         AMENDED v0.4.93 — scope NARROWED to pre-filing only, owner "go all"
#         2026-09-07 on the Adolfo-protocol amendment):
git -C ~/opencrabs fetch adolfousier
git -C ~/opencrabs rev-parse adolfousier/main   # must equal the sha the port was cut from
#    upstream moved since the port? RE-PORT onto the new base — BEFORE filing.
#    SCOPE (v0.4.93): applies ONLY while the work is fork-internal (branch,
#    gate, pre-filing). Once the upstream PR is FILED, the PR-freeze law
#    (below) takes over: NO re-port, NO force-push, NO head/body changes —
#    a filed PR is frozen regardless of upstream main movement. Conflict
#    resolution after filing is the MAINTAINER's side of the wall (merge
#    locally, fix on top, push, comment). Post-merge, upstream main carries
#    the fix; fork-side sync stays owner-gated (upstream-merge-runbook.md).

# Phase 5 gate: pr-checks GREEN on the PR branch — zero errors in ported lines

# 2-pre. ATOMICITY + BASE check BEFORE the PR opens — standing rule
#     PR-BASE-PRE-OPEN in the Rules list below.

# 2c. CI gate (upstream triad) (v0.4.22 — encodes adolfousier/opencrabs
#     CONTRIBUTING.md: "You MUST pass all three before submitting a PR").
#     v0.4.28: the triad runs in CI via pr-checks.yml (cargo is FORBIDDEN on this box — box law);
#     a green run URL IS the citation.
#     FIRST push the head branch (step 3's command — the workflow checks the branch out from the fork).
#     MANDATORY FULL-GATE FORM (v0.4.149, owner order 2026-09-12):
#     Pre-PR testing MUST use the full gate (cargo test + fmt + clippy, NO --fast):
#       tools/harvest/oc-prchecks leshchenko1979/<feature>
#     or blocking wait form:
#       tools/harvest/oc-prchecks wait leshchenko1979/<feature>
#     (Do NOT pass --fast for final pre-PR verification. Full gate ensures 100% upstream test parity.)
#   Standing rules PR-GATE-STANDING in the Rules list below (flags verbatim
#   from pr-checks.yml; ANY red = fix cycle + re-dispatch, never a filed PR;
#   cite the green run URL in the PR body prep next to the smoke/run evidence).

# 3. push the head branch to the FORK (PR heads live there)
git -C ~/opencrabs-wt/up-<feature> push -u origin leshchenko1979/<feature>

# 4. open the upstream PR — detailed description; body rules are canonical in
#    the Rules bullet below (fork-issue link at END, `Closes #N` FORBIDDEN).
#    PR TITLE TYPE PREFIX: every upstream
#    AND fork PR title starts with fix: / fix(scope): (bug fix), feat: /
#    feat(scope): (new capability), or chore: (tooling/CI/docs/deps — zero
#    user-visible change). The head-branch slug mirrors the type:
#    leshchenko1979/fix/<slug> | feat/<slug> | chore/<slug> (existing branches
#    untouched).
#    CROSS-REPO --HEAD LAW (Duty-4 P3, v0.4.80): --head is OWNER:BRANCH —
#    `leshchenko1979:<branch>`, literal branch name kept whole. The bare
#    `--head leshchenko1979/<branch>` form fails cross-repo with
#    "No commits between" (2026-09-01, adolfousier/opencrabs#1277 filing).
#    STAGED DRAFT PR MANDATE (owner order 2026-09-16):
#    When an upstream PR depends on another in-flight upstream PR or is part of a
#    multi-part staged wave, add `--draft` so upstream maintainers cannot merge out of order.
gh pr create -R adolfousier/opencrabs --base main --head leshchenko1979:leshchenko1979/<feature> \
  --title "<fix:|feat:|chore:> <concise feature title>" \
  --body "<detailed what/why, implementation notes, green run link, smoke-test evidence. Original issue: https://github.com/leshchenko1979/opencrabs/issues/N (exactly one)>" \
  [--draft]

# 5. close the tracked FORK issue with a pointer comment
gh issue close <issue-n> -R leshchenko1979/opencrabs -c "Implemented in upstream PR adolfousier/opencrabs#<pr-number>"

# 6. remove the worktree — done (dirty-tree gate + journal via oc-wt)
tools/git/oc-wt remove up-<feature>
```

Rules:
- **PR-FREEZE LAW (v0.4.93, owner "go all" on the Adolfo-protocol amendment
  2026-09-07):** an upstream PR is FROZEN the moment it is filed with CI green
  at push. NO re-port, NO force-push, NO head changes, NO body updates — even
  if upstream main moves or conflicts appear. *"Once you push it, you already
  did your job"* (Adolfo, 2026-09-07). Rationale: force-pushing a filed PR
  changes the head under the maintainer — if he already merged locally, the
  merge sha no longer matches and auto-close breaks (2026-09-07:
  #1426/#1427 rebased at 15:56, merged locally by maintainer at 17:22, heads
  mismatched, manual close required). Base-freshness (2-fresh) applies
  PRE-filing only. The ONLY valid re-engagement: maintainer explicitly asks
  for a change.
- **MAINTAINER-SIDE MERGES (v0.4.93):** conflict resolution, rebase, and
  fixes-on-top AFTER filing are the MAINTAINER's responsibility, done at
  merge time on his side. Contributor = push final work once.
  *"Whenever you're the maintainer approving changes: merge locally, fix
  conflicts on top, push, comment what you did."*
- **FINAL-PR STANDARD (v0.4.93):** file a PR only when it is genuinely final —
  tests green at push, no known gaps, no planned follow-ups. Force-pushes on
  filed PRs are the rare exception (~1-in-10), never procedure. All iteration
  happens fork-side BEFORE filing (fork = workspace, upstream PR = one-way
  handoff).
- Fork-only commits means EXACTLY that: no adolfousier sync merges, no other
  feature's commits, no bare CI-config churn unless it IS the feature.
- Cherry-pick conflicts → resolve, re-run the Phase 5 gate (pr-checks), continue. NEVER merge fork
  `main` into the PR branch — upstream gets clean commits only.
- **HARVEST VERIFICATION SWEEP (Duty-4, v0.4.71):** Full 4-leg sweep checklist (symbols, attributes, foreign hunks, patch-ids) lives in §Phase 7 Reference Rules below.
- **BASE-FRESHNESS AT FILING TIME (Triage lesson n=2083, v0.4.111):** the
  sweep and every gate run are valid against a NAMED upstream base — record
  the `adolfousier/main` sha the verification was tested against; a census/
  gate CLEAN result that does not name its base sha is not a CLEAN receipt
  (stale-base CLEANs masked #1451's CONFLICTING for hours).
- The PR body MUST reference THE issue as a FULL FORK URL at the END of the
  description (`Original issue: https://github.com/leshchenko1979/opencrabs/issues/N`
  — EXACTLY one, atomicity rule). `Closes #N` is FORBIDDEN on upstream PR bodies:
  it resolves against adolfousier's issue space, not ours (issues live on the
  fork). WE close the fork issue (step 5) right
  after the PR is up — do not wait for the maintainer merge.
- **QUALIFIED FORK REFS (fork [#54](https://github.com/leshchenko1979/opencrabs/issues/54)):**
  no bare `#N` with FORK issue numbers on any upstream surface (PR body,
  PR title, issue body, comment) OUTSIDE a code span — write
  `leshchenko1979/opencrabs#N` or the full URL (GitHub autolinks bare `#N`
  against adolfo's issue space). Code spans exempt. Bare `#N` stays reserved
  for UPSTREAM-local references. Incident + rationale:
  §Phase 7 Reference Rules below.
- One feature = one PR; never bundle two features to save a PR.
- **DEEP CORE ADVANCE HEADS-UP GATE (owner order 2026-09-17; paths corrected + executor assigned v0.4.204, HQ ruling 2026-09-18; config added to scope by owner order 2026-09-19):** If the PR touches **Deep Core** (runtime scheduler, compaction algorithms, provider routing/fallbacks, subagent orchestration, tool loop, configuration — loading, profile resolution, write guards, migrations — the PROSE scope is operative, paths are a reading aid: `src/cron/`, `src/brain/agent/service/tool_loop.rs`, `src/brain/agent/context.rs`, `src/brain/provider/`, `src/brain/tools/subagent/`, `src/config/`), post a concise 1-liner heads-up **as a comment on the upstream PR itself, by the filing lane** (it filed the PR, so it already holds the surface), before or simultaneously with opening it: `Core heads-up: <symptom> → proposed fix in <subsystem> (PR #<N>)` — nothing else; detail belongs in the PR body. **TELEGRAM VENUES RETIRED 2026-09-27 (owner relay + maintainer request):** the former `OC Dev` / `Opencrabs Dev Factory` group-post venues are WITHDRAWN — `OC Dev` carries the maintainer (`@adolfodev`) as a NON-OPERATOR member, which makes it member-visible under §Agent briefing law, and he has asked for feedback on GitHub only. With the venue on GitHub, §Telegram surface law no longer applies and the filing lane posts it directly. Surface integrations (Telegram channel handler, cards, formatting) remain under autonomous maintainer authority and ship with 4-leg smoke receipts without advance group chat posting. Canon: `harvest.md §Deep Core Advance Heads-Up Gate`.
- **ATOMICITY & ZERO BUNDLING (owner order 2026-09-13; lane 1a63f103 proposal):** issues, PRs and commits are atomic —
  one problem per issue, one logical change per commit, one issue per PR. **1 Intent = 1 Unit.**
  Never mix features and bug fixes in the same issue, branch, or PR: a feature PR must carry exclusively
  feature commits, and a bugfix PR must carry exclusively fix commits. If a defect is found while working
  on a feature, file a separate fork issue and resolve it in an isolated branch/PR — never bundle the fix
  into the feature work. Every harvested commit carries an `Issue-Ref: #N` trailer matching EXACTLY the single
  issue the PR claims; no commit without one, no PR claiming more than one. A PR
  whose diff mixes fixed and unfixed concerns forces a binary status on a mixed bag
  and mislabels both. Gate with `./tools/harvest/oc-prchecks <branch>` and atomicity check BEFORE closing the issue.
- **PR LIFECYCLE:** One PR = one atomic change; a bug found in review is fixed
  FORWARD on the same PR or the PR is closed — no draft limbo. A MERGED PR is
  closed forever: follow-up work = new branch + new PR, NEVER extend a merged
  branch.
- **UPSTREAM CODING & TEST STANDARDS (CONTRIBUTING.md & Adolfo DM 2026-09-13):**
  - **Test isolation:** ALL tests MUST live under `src/tests/*_test.rs` registered in `src/tests/mod.rs`. Absolutely **NO inline `#[cfg(test)] mod tests`** blocks inside source files in `src/`. If an existing inline test block is found while editing a file, move it to `src/tests/` as part of the change.
  - **`mod.rs` declarations only:** Zero function definitions (`fn`) inside any `mod.rs`. Only doc comments, `mod`/`pub mod` statements, and `pub use` re-exports. Functions belong in cohesive child modules.
  - **No `Co-Authored-By`:** Never add `Co-Authored-By` trailers to commit messages.
  - **Real tests over mocks:** Hit real structs and SQLite; tests must fail without the fix and pass with it.
  - **Zero error / warning suppression:** No `#[allow(dead_code)]` or `#[allow(unused)]` duct tape. Unused code must be deleted.
  - **`ONTOLOGY.md` synchronization:** If a change introduces, renames, or retires a concept, update `src/docs/reference/ONTOLOGY.md` in the same PR.

- **BUILD TRIGGERS = exactly TWO, no exceptions:** Canonical law lives in `SKILL.md §Hard rules` (`oc-deploy ship` or owner word; CI gate = `oc-prchecks`).
- **PR-BASE-PRE-OPEN (v0.4.71, Duty-4 P6):** an upstream PR head is a harvest
  branch off `adolfousier/main` — NEVER a fork-main-based branch; base +
  atomicity check runs BEFORE the PR opens (a post-open atomicity FALSE
  (fork-divergence commits) means the base was wrong before the PR existed).
- **PR-GATE-STANDING (step 2c):** triad flags VERBATIM from pr-checks.yml
  (fmt soft-fail mirrors upstream; clippy --locked --lib --bins --tests
  --all-features -D warnings; cargo test --locked --profile ci
  --all-features) — green here predicts green on adolfo's full gate. Iterate
  by EDITING CODE and re-dispatching pr-checks — NEVER run cargo locally
  (box law); test-placement policy → `editor.md` §Phase 4.
- Pre-flight gate (step 2c) is MANDATORY (v0.4.0): read the fmt STEP outcome,
  not just the run conclusion — soft-fail hides failures from the run.
- **Harvest census pre-flight gate (Cycle 5 / Duty 4, v0.4.143):** before opening an upstream PR or creating a harvest branch, run `tools/harvest/oc-harvest-census check <issue-number-or-slug>`. Refuse to file if rc=1 (finding: already MERGED or IN_FLIGHT upstream, or blocked).
- **Read the ADVISORY drop-list before branching (v0.4.218, finding `63d775f9`, cycle `20260919-c21`):**
  rc=0 `ELIGIBLE` means the target is **unharvested**, NOT that its feature can travel alone — Gate 4
  (`#365`) passes when **at least one** derived subject symbol resolves upstream, so an ELIGIBLE unit may
  still have its whole **substance** inside a fork-only symbol. Read every `ADVISORY: hunk inside
  fork-only symbol — dropped at packaging (<file> :: <sym>)` line (emitted on the rc=0 path; the ONLY
  substance-portability signal) and judge whether the dropped symbols are the unit's substance or merely
  incidental. **If the substance is dropped, the unit is a CHILD of the fork issue that introduced that
  symbol:** parent-link it (`gh issue edit <child> --parent <parent>`) and do **not** branch until the
  parent is merged upstream. The v0.4.71 symbol sweep at §Phase 7 Reference Rules is a **POST-branch**
  check and does **not** substitute for this one. (Incident: `#250` read as "branchable alone" off
  `ELIGIBLE … clean to branch and gate` with four ADVISORY lines in the same output.)
- `leshchenko1979/<slug>` is the RESERVED PR-head namespace (`leshchenko1979/…`
  branch names stand out in the upstream branch list): branches with that
  prefix are created ONLY in this phase, never developed on, never merged into
  fork `main` — and NOT deleted while their PR is still open (GitHub needs the
  head alive).

- **Checkable Completion Formula**: `DONE = Upstream PR created + fork issue closed with pointer comment + harvest worktree removed via oc-wt.`

## Phase 7b — PR lifecycle (monitor & unblock, v0.4.0)

Every OPEN upstream PR has an owning editor: the Session-Id trailers of its
harvested commits. When a PR is not mergeable, route by BLOCKER CLASS:

| Blocker | Who acts | Action |
|---|---|---|
| fmt/clippy/test failure in THIS feature's files | Owning editor (notified with log evidence via the mechanical post-swap fan-out — `oc-deploy fanout`) | **PR-freeze check first (v0.4.93):** fixes on a FILED PR only when CI failure exists at push time or maintainer asks. Otherwise frozen. If valid: fresh worktree off the PR head → fix → Phase 5 gate (pr-checks) + conflict-quality gate → signed push to the head |
| Merge conflicts with new upstream `main` | **Maintainer (v0.4.93)** | **DO NOT rebase/force-push the filed PR** — PR-freeze law. Conflict resolution on a filed PR is the maintainer's side (he merges locally, fixes on top, pushes, comments). HARVEST action: NONE beyond a factual comment ONLY if the maintainer asks; pre-filing, 2-fresh governs |
| Prerequisite unharvested (feature depends on fork-only changes from another issue) | **HARVEST / Triage (v0.4.174; Harvester RETIRED v0.4.176)** | **Explicit dependency notice permitted (v0.4.174 Dependent Upstream PRs Law)**: Allowed to file PR B while prerequisite PR A is pending, provided PR description states: `Depends on #<PR_A> (do not merge before #<PR_A>)`. Maintainer merges in chronological sequence. Alternatively, automated harvest pipeline holds PR B until PR A merges. |
| PRE-EXISTING upstream red (base fails in files we never touched) | ❌ NO editor pings — our code is innocent | housekeeping-PR candidate: issue filed + ledger-registered first (v0.3.8), Alexey decides |
| Maintainer rejects/closes the PR | Owning editor | REOPEN the linked issues with a pointer comment; record the outcome |

Hard rules: verify the failing log names files THIS PR actually touches BEFORE
pinging anyone (identical clippy walls on every PR can live on the upstream base). Soft-fail fmt diffs are
cosmetic — NEVER ping for fmt alone. Absorption ends the lifecycle: if the
maintainer merges/reimplements the feature, the PR story closes with a SHIPPED
UPSTREAM notice (Phase 6 item 6), not more fork-side work.
Two same-turn checks (v0.4.5): (1) BEFORE any push to a gated/frozen head branch,
RE-READ live gate state — latest issue comments + HQ notifies — session-start
knowledge structurally cannot know what changed mid-turn. (2) Before preparing ANY follow-up
commit targeting an open PR, check its state via API (`gh pr view <n> --json
state,mergedAt`) — it may have been maintainer-merged under you. **The state gate ALSO spans every port /
cherry-pick round toward a PR head (v0.4.14, proposal P4)**: before investing a
round, fresh `gh pr view <n> --json state` — if MERGED/CLOSED, STOP and report,
do not invest the round.

- **Checkable Completion Formula**: `DONE = PR state checked via API + blockers routed to responsible party (maintainer or owning editor) or closed with note.`

## Phase 7c — Mechanized Harvest Execution (v0.4.136, 2026-09-10; tightened v0.4.146)

Trigger: Operator harvest command (e.g. `/goal harvest ...`) dispatched to the HARVEST lane via `session_notify` `[HARVEST DISPATCH: #N]` wire envelope from Triage.

Contract:
1. **Dedicated Worktree**: Create isolated worktree off `adolfousier/main` tip:
   `tools/git/oc-wt add up-<slug> leshchenko1979/fix/<slug> --create --from adolfousier/main`
2. **Cherry-pick & Pre-Sweep**: Cherry-pick source commits preserving trailers (`-x` / `Issue-Ref`), then verify clean lineage with `tools/harvest/oc-harvest-sweep leshchenko1979/fix/<slug> --base adolfousier/main`.
   - **Atomic Subsystem Bundling & Fix Squashing (Owner Order 2026-09-17, v0.4.200)**: A harvest unit is not a loose series of patch commits — it is a single, cohesive, self-contained atomic commit. Squash all follow-up bugfixes, clippy cleanups, test updates, and dependent child issue commits directly into the coherent parent feature commit before CI gating and filing upstream (`git reset --soft` / `git commit --amend` to consolidate into one clean commit). Maintainer Adolfo squashes multi-commit PRs into a single commit on upstream `main` anyway; shipping clean, all-in-one atomic commits eliminates upstream review noise and intermediate cherry-pick breakage.
   - **Dependency & Soak Inheritance:** canonical at `upstream-merge-runbook.md` §Upstream-merge cadence.
   - **Native Sub-Issue / Child Pre-Flight Gate (Issue #188 / v0.4.198)**: A child issue, cleanup, or derivative task (such as deleting a script that exists only on fork or referencing unmerged docs/subsystems) must NEVER be harvested in isolation from its parent subsystem. If the parent subsystem is unharvested or unmerged upstream, refuse harvest staging until the parent lands upstream.
   - **In-Flight Lane Fence (v0.4.187)**: `tools/harvest/oc-harvest-dispatch vet <issue>` enforces this mechanically — it refuses a candidate whose subsystem is held by an active editor lane (rc 4 on `dispatch`). Read the fence from `tools/state/oc-ledger claim-ref <uuid>` (it takes a SESSION uuid, not an issue number) rather than hand-reading `workers-ledger.json` (a hand ledger read is the agent-memory-as-gate-input defect, lens J / F26). If an active lane is working the subsystem, hold harvest dispatch until that lane finishes, hot-swaps, and lands.
3. **Smoke & Gate Verification (Hard Gate, v0.4.146 / v0.4.149 / v0.4.152)**:
   - **4-Leg Smoke Pass**: Verify full 4-leg smoke pass (Lineage, Identity, CI Gate, Behavioral probe) is recorded with live receipts in `smoke-verdicts.log`. NEVER file an unsmoked PR.
   - **Cross-Boundary Unit Test Standards (v0.4.198)**: Verify that all PR unit tests test real cross-boundary interactions (e.g. real file writer -> reader in tempdir) rather than tautological helper comparisons against internal delegate functions.
   - **Packaging-sha stamps (v0.4.152)**: the row's `sha=` MUST be the packaging tip being filed (the branch head), never an ancestor. A row citing an ancestor does not cover the candidate — append a fresh row after the full gate; never edit the superseded one.
   - **Owner-dependent leg → PARK, don't chase (v0.4.152, owner order 2026-09-12)**: if the remaining behavioral evidence needs the OWNER (visual pass, tap, eye-confirm), it is NOT a blocking gate. Stamp the provable legs, append `PARKED-OWNER-EYE` (owner action + packaging sha), RELEASE the lane, and let the candidate roll to the next owner-present window. Never idle on an owner leg — the owner being away is exactly when this binds. Full law: `fleet-directives.md §Owner-Dependent Smoke Legs — Park, Don't Chase`.
   - **Mandatory Full PR Gate**: Push branch to origin (`leshchenko1979/opencrabs`) and trigger full PR checks (NO `--fast` mode):
     ```bash
     # Single-command blocking full PR gate:
     tools/harvest/oc-prchecks wait leshchenko1979/fix/<slug>
     # Or standard dispatch:
     tools/harvest/oc-prchecks leshchenko1979/fix/<slug>
     ```
     `--fast` is strictly prohibited for pre-PR testing; upstream PRs require 100% full test suite verification.
4. **Ship Execution**: When gate run exits GREEN (SUCCESS) AND 4-leg smoke pass is confirmed in `smoke-verdicts.log` (and ≥24h post-swap soak completed for `feat/*` or dependent fix bundles, counted strictly from the latest live deployment timestamp `deployed.ts` of ANY related node in the relationship graph — parent, sub-issues, and blockers, per 24h Feature Soak Harvest Law), the HARVEST lane verifies upstream baseline state (`git diff origin/main...adolfousier/main`) and files the upstream PR (`gh pr create --repo adolfousier/opencrabs --base main --head leshchenko1979:leshchenko1979/fix/<slug> [--draft]`) citing the gate run ID, quoting the 4-leg smoke receipt, and linking the fork issue. If the underlying issue was already clean or resolved in upstream `main`, frame the PR narrative accurately as a clean helper extraction / refactoring / hardening rather than asserting an upstream regression (Upstream Baseline & Narrative Verification Law v0.4.198). (Note: Use `--draft` if the PR depends on another in-flight upstream PR per Staged Upstream Draft PR Mandate). **A PR number is not FILED until a same-turn `gh pr create` (or `gh pr view <N>`) output names it** — if a guard flags the claim (`phantom_blocked`) or the output was not witnessed, the PR is UNFILED: re-verify and re-dispatch (v0.4.152 §Guard-Flag Escalation Law; worked example: an announced PR #1514 that never existed cost ~3 h).
5. **Ack & Cleanup**: Remove harvest worktree, stamp completion in ledger, and notify Triage via `session_notify`.
   - **Checkable Completion Formula**: `DONE = 4-leg smoke pass in smoke-verdicts.log + full oc-prchecks green + upstream PR filed + harvest worktree cleaned up.`

## Phase 7 Reference Rules (Harvest Verification & Qualified Fork Refs)

Reference detail behind upstream PR harvesting and surfaces:

- **HARVEST VERIFICATION SWEEP (Duty-4, v0.4.71):** after
  conflict resolution on a harvested branch, BEFORE the first gate dispatch:
  (a) `git diff origin/main...HEAD` symbol sweep — grep the branch diff for
  fork-renamed/fork-only symbols and verify each has a live caller in the
  UPSTREAM tree (a write-side helper whose fork-paired read side lived in a
  renamed caller is a guaranteed clippy dead-code RED);
  (b) fork-side-only attribute sweep — diff fork-main vs PR-tree for
  `#[allow(clippy::…)]`/cfg gates on every function the PR touches, port them
  explicitly (trailer-matched cherry-picks miss attributes that rode a
  trailer-less fork commit);
  (c) foreign-hunk conflicts (a hunk on fork `main` but absent on the target
  base) resolve by DROPPING the foreign side, verified by diffstat delta vs the
  fork-side pick;
  (d) verify a rebase-ported commit by `git patch-id` before cherry-pick —
  post-port shas differ from lane records while content is identical.

- **UPSTREAM BASELINE & NARRATIVE VERIFICATION (Owner Order 2026-09-17, findings from PR #1615 review, v0.4.198):**
  When staging a fork bugfix or feature for upstream PR harvest, verify against live `adolfousier/main` whether upstream has already resolved the underlying issue or restructured the code path. If already addressed or clean upstream, frame the PR narrative accurately as a clean helper extraction, refactor, or hardening improvement rather than claiming an active upstream bug/regression.

- **CROSS-BOUNDARY UNIT TEST INTEGRITY (v0.4.198):**
  Unit tests in upstream PRs that assert file paths, contracts, or serialized formats must test real cross-boundary interaction (e.g. real file writer -> reader round-trip in a `tempfile` directory) rather than testing a helper function against its own internal delegate. Tautological unit tests provide zero regression protection across module boundaries and are rejected.

- **QUALIFIED FORK REFS on upstream surfaces (fork [#54](https://github.com/leshchenko1979/opencrabs/issues/54)):**
  a bare `#N` where N is a FORK issue number must never appear on an upstream
  surface (PR body, PR title, issue body, comment) OUTSIDE a code span — GitHub
  autolinks it against adolfousier's issue space and the tooltip points at an
  unrelated upstream issue (upstream #29 = memory-process question vs fork #29 =
  compaction signal). Write `leshchenko1979/opencrabs#N` or the full URL. Bare
  `#N` stays reserved for UPSTREAM-local references. Code spans are exempt
  (GitHub does not autolink inside backticks) — literal log-line quotes stay
  verbatim. Fork-side surfaces are unaffected (bare #N resolves correctly there).

### Deep Core Advance Heads-Up Gate (Core vs Integration Rule, Owner Order 2026-09-17)

Maintainer coordination protocol between Alexey (`@leshchenko1979`) and Adolfo (`@adolfodev`):
1. **Scope Classification**:
   - **Deep Core:** Runtime scheduler, context compaction algorithms, provider routing/fallbacks, subagent orchestration, tool execution loop, and **configuration** (loading, profile resolution, write guards, migrations). **The prose scope is OPERATIVE; the path list is a reading aid, never the definition.**
     - **Real paths (corrected v0.4.204, HQ ruling 2026-09-18; config added by owner order 2026-09-19):** runtime scheduler `src/cron/` (`scheduler.rs`, `pipeline.rs`, `trigger.rs`, `send_scope.rs`) · tool execution loop `src/brain/agent/service/tool_loop.rs` · context compaction `src/brain/agent/context.rs` · provider routing/fallbacks `src/brain/provider/` · subagent orchestration `src/brain/tools/subagent/` · **configuration `src/config/`** (`sections.rs`, `profile.rs`, `secrets.rs`, `guard.rs`, `live_home_guard.rs`, `repair.rs`, `registry_client.rs`).
     - **Defect this fixes:** the former list named `src/agent/` and `src/scheduler/`, NEITHER of which exists in the tree (`find src -type d -name 'scheduler*'` → empty). A filer reading the list as exhaustive would conclude a cron-runtime-scheduler change is NOT Deep Core — the wrong direction of error, and exactly the #317 shape.
   - **Surface Integrations:** Telegram channel handler, rich cards, MTProto/MCP bridge (`src/channels/telegram/`).
2. **The Advance Heads-Up Protocol (Venues RETIRED 2026-09-27 — group posts withdrawn: `OC Dev` is member-visible and the maintainer asked for GitHub-only; the heads-up is a comment on the upstream PR itself):**
   - For any architectural change, behavior shift, or non-trivial fix touching **Deep Core**, post a concise technical 1-liner heads-up **as a comment on the upstream PR itself, by the filing lane** (*before* or *simultaneously with* opening the upstream PR**):
     > `Core heads-up: <observed symptom/issue> → proposed fix in <subsystem> (PR #<N>)`
   - This ensures early alignment on core abstractions before or during maintainer review.
   - **WHO POSTS — the FILING LANE posts it, as a comment on its own upstream PR (amended 2026-09-27, same commit that retired the group venues).** With the venue moved off Telegram onto GitHub, the former blocker is moot: SKILL.md §Telegram surface law bars an editor from invoking telegram send/edit tools, and **a GitHub PR comment invokes none**, so the filing lane holds and discharges this gate itself, in the same turn it opens or has opened the PR. The obligation is on the CHAIN, not on HQ: a lane that has posted the comment has discharged it, and its harvest may proceed. HQ is no longer in this loop — the v0.4.204 HQ-executor assignment was a consequence of the Telegram venue and is retired with it.
3. **Surface Integrations Autonomy:**
   - Changes to Telegram, rich card rendering, formatting, and local developer tooling remain under our autonomous maintainer authority; they ship directly to upstream PRs with verified 4-leg smoke receipts without requiring advance group chat discussion.

### Dependent Upstream PRs Law (Maintainer Consensus, 2026-09-14; Draft Mandate 2026-09-16)

When PR B depends on PR A (which is not yet merged upstream):
1. **Explicit Dependency Notice Permitted:** It is explicitly allowed to file PR B while PR A is open/pending, provided the PR description clearly states:
   `Depends on #<PR_A> (do not merge before #<PR_A>)`
2. **Staged Upstream Draft PR Mandate (owner order 2026-09-16):** When an upstream PR depends on another in-flight upstream PR or is part of a multi-part staged wave, it MUST be filed with `gh pr create --draft` so upstream maintainers cannot merge out of order before prerequisites land. Once PR A merges upstream, the draft status on PR B is converted to ready for review.
3. **Maintainer Order of Processing:** Upstream maintainer tackles dependent PRs in commit/chronological sequence (PR A merged before PR B).
4. **Deferred Automated Publishing:** Alternatively, automated harvest pipelines may hold PR B until PR A merges via harvest watch / cron triggers.

### Rejected-upstream — a TYPED state decided by a CONTENT DIFF (v0.4.250, owner order 2026-09-24)

**PR state is not a rejection signal.** Measured 2026-09-24 over every upstream PR with `mergedAt == null` (**48 examined**): **18 (37.5 %)** carry content that is **already present on `adolfousier/main`** — the maintainer squashes, re-applies or reimplements, then closes our PR. Worked specimen: PR **#1611** reads "closed unmerged" while upstream `5d326aa12` cites `(#1611)` and carries the same content under a different sha. So a closed-unmerged PR is an **UNKNOWN**, never a rejection.

**The predicate is a content diff, and it has three outcomes.** For each cluster, compare the PR's added lines against `adolfousier/main`:

| Outcome | Meaning | Disposition |
|---|---|---|
| `applied-upstream` | the content is present upstream | nothing owed; record it and stop |
| `absent-upstream` | genuinely not upstream | candidate for rejection, subject to Triage confirmation |
| `unmeasurable` | the diff could not be fetched | **never read as absent** — report it and re-run |

**Rejection is two-stage, and a human confirms.** An upstream PR closed unmerged creates a **candidate**; Triage confirms **rejected** vs **superseded** vs **withdrawn** after reading the maintainer outcome. Never auto-discard on PR state alone — 37.5 % of that population would be wrongly discarded.

**A dependent cluster is never silently dropped.** It leaves the *ready* count and is retained visibly as `blocked-by-rejected-upstream`, carrying exactly one disposition:

- **`exclude`** — the change only makes sense with the rejected behaviour.
- **`salvageable`** — the dependency can be split out or rewritten; the cluster is re-workable without it.
- **`needs-owner-ruling`** — the semantic dependency is unclear, so the owner decides.

**`manual_records` IS this field — formalise it, do not fork it.** `oc-harvest-census` already carries a not-upstreamable marker, and it is **right in effect and wrong in wording**: specimen #209's record reads *"manually recorded as filed in PR #1510"* while PR 1510 **does not exist** — 1510 is an upstream **issue**, closed by direct upstream work with no PR (control: 11 sibling records name real PRs; only this one does not). The typed status above is the field that record was reaching for, so **extend the existing marker; do not add a parallel registry.**

**REMOVAL IS FORBIDDEN — there is deliberately no verb, flag or procedure that deletes a `manual_records` entry.** These records are load-bearing in the direction that PREVENTS work: #209's effect is correct even though its wording misdescribes it, and deleting it would open the way to filing a PR that is **not owed**.

### Upstream issue filings — report-only (owner 2026-08-28 15:17Z)

**Offload order — CORRECTED (owner 2026-09-01, "Wait, i was talking about prs only. Revert issues"):** "Offload to upstream" applies to **PRs only** (when we fix OpenCrabs-source bugs, the fix ships as an upstream PR per the existing PRs-only rule). **Issue reports NEVER go upstream** — the fork is the issues home, permanently. The 2026-09-01 issue-migration (adolfousier #1279–#1286 for fork 70/33/38/58/35/60/65 + TEXT_ACCUM) was misread, withdrawn same day: all 8 upstream issues closed as withdrawn, all 7 fork issues reopened, #1255 cross-link deleted. #66 remains not-upstream-eligible (upstream #1260 closed pointing back to the fork; needs owner-level follow-up with adolfo).

When the owner tells us to FILE an issue upstream (adolfousier/opencrabs), the editor does NOT fix it: the filed report is the deliverable, and fixing the upstream-reported defect is adolfo's lane. No editor lane writes fix code or opens a fix PR for an upstream-filed issue unless the owner explicitly orders the fix — follow-up REPORTING on the filed thread stays allowed (per the #1255 exception).

### Cross-fork PR inspection — fetch head from the fork remote (Duty-4 proposal, owner-approved 2026-09-06)

Inspecting a cross-fork PR (`gh pr view N -R upstream`): fetch the head branch
from the FORK remote (`git fetch origin <head>`), never from upstream — a
fork-namespaced head does not exist there (2026-09-05 #1392 404 incident).
Same root fact as ledger n=1537's `gh pr create` namespaced-head lesson.
