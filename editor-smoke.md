# EDITOR — Phase 6 (Smoke) appendix

**Owns:** the Phase 6 verdict stack — the full smoke-verdict rules, the presence-is-not-behaviour incident history, the live-verification stamp for UX features, leg-4 probe hygiene, `PARKED-OWNER-EYE` and the L1–L4 owner-dependent-leg law, swap-timing non-coordination, and no-auto-rollback.

**Load when:** you are writing a smoke verdict, or you are deciding whether a leg can be parked. It is an APPENDIX to `editor.md`, never a second role file: the role, the phase sequence and every cross-cutting law live there, and where the two disagree `editor.md` wins and this file is the defect.

> **RELOAD LAW:** keep this file in `active_skills` for the whole smoke phase and re-read it on compaction (`fleet-directives.md §Post-compaction skill reload & context manifest curation`). At claim time it is read on entering Phase 6 — not before.

## Phase 6 — Smoke Verification (oc-smoke)

A post-swap notify announcing a new binary (mechanical fan-out — `oc-deploy
fanout`, [#24](https://github.com/leshchenko1979/opencrabs/issues/24) LIVE
since v0.4.37; `[session-notify from=<uuid>]` header) means your
commits are in it — prove the FEATURE works. This phase produces SMOKE TEST
evidence (SKILL.md Test ontology): behavioral, against the RUNNING binary,
zero cargo. CODE TESTS (fmt/clippy/cargo test) are a different kind, CI-only —
Phase 5 (`harvest.md §Phase 7 step 2c` reuses it on upstream PR heads). The binary is live
right here (`opencrabs-ops` user unit).

```bash
# Unified 4-leg smoke verification & verdict row logging:
~/.opencrabs/profiles/ops/skills/opencrabs-dev/tools/smoke/oc-smoke <issue-N> --probe "<command-to-verify-behavior>"
```

1. Read run id + built sha from the notification body. **If the daemon bounced**
   (any restart since your last turn), RE-SURFACE lazy tool schemas via
   `tool_search` BEFORE any smoke invocation — a restart kills activated schemas
   and intents misfire onto wrong tools.
2. **IDENTITY RECEIPT & BEHAVIORAL PROBE:** Run `tools/smoke/oc-smoke <issue-N> --probe "<cmd>"`
   (or manual `oc-smoke-evidence`). It verifies unit exe identity vs deployed sha,
   executes the probe command, and writes the canonical row to `smoke-verdicts.log`.
   MISMATCH → STOP: you would be smoking a binary that is not the one that was
   built — report the mismatch to the sender, do not smoke on a stale unit.
3. Drive your feature end-to-end against the RUNNING unit on its normal
   surfaces (Telegram, cron, MCP — whatever the feature touches).
   - **Checkable Completion Formula**: DONE = Mechanical proof demonstrating target feature execution against the running binary (command output, log line with PID/timestamp match, or API receipt); confirmed via `tools/smoke/oc-smoke` (exit 0) and recorded in `smoke-verdicts.log`.
   **Receipt surface for a channel-RENDERING defect is the DELIVERED message, never a stored row
   (finding `1a63f103`, cycle `20260919-c21`):** the `pending_followups` row (`host_html` /
   `host_markdown`) is written BEFORE `normalize_rich_markdown_with_media` → `enforce_button_fit`,
   so it is the PRE-enforcement source and cannot witness a defect that stage introduces or
   repairs. Read the delivered text instead: `tg_get_messages` on the host message id (own topic
   only), or the daemon telemetry line `Telegram send ok: … msg=<id> len=<n> hash8=<h>`. A render
   verdict resting on a stored row is `UNPROVEN`, never PASS — and the `smoke-verdicts.log` row
   must name the delivered message id.
4. PASS → reply to the sender (`session_notify`, `target_session` = the `from`
   header): feature OK + one line of evidence + the oc-smoke
   IDENTITY-MATCH receipt. Running `oc-smoke <issue-N>` on PASS automatically
   executes `oc-ledger stamp done` (suppressible via `--no-ledger`), mechanically
   closing the worker's in-flight claim in `workers-ledger.json` and unblocking
   `oc-harvest-census` and Triage intake. On a behavioural PASS, record
   the row, reply to the sender, and hand the port to HARVEST — the handoff is the
   last *editor* step, but the lane's obligation is discharged by the recorded
   behavioural verdict, not by the post
   (SKILL.md §Hard rules — ISSUE ROUTING bullet, PR SHIPMENT row).
5. FAIL → FILE THE ISSUE FIRST (Phase 1 procedure: symptom + evidence — you
   found it, you file it). Then send raw evidence + the issue link directly to
   the owning editor or Triage lane (`session_notify`) — do NOT attribute, do NOT fix another
   editor's feature; attribution via Session-Id trailers is MECHANICAL
   (`oc-attrib`; decision 2026-08-25 2a, mechanical fan-out above).
6. SHIPPED UPSTREAM notice (v0.4.0): if HQ (or the post-swap
   fan-out) reports your feature was
   absorbed by upstream (maintainer merged or reimplemented it), your fork-side
   duty for it ENDS — no further fork maintenance, no fix rounds. Future work
   on that feature happens upstream only: new claim via Phase 1, normal rules.

**Presence and bookkeeping legs are never a smoke PASS (owner order 2026-09-08):**
lineage (is-ancestor), identity (`oc-smoke-evidence` MATCH / artifact==exe sha) and CI gate
evidence are BOOKKEEPING LEGS — all three passing still does not constitute a successful smoke
test. Presence evidence (strings marker hit, sha match, `deployed.meta` identity) proves only
that the artifact shipped; it says nothing about behavior. A smoke PASS requires step 3 to have
TRIGGERED the fix's actual runtime path on the live box and observed it execute (real message
round-trip, real interrupt, real stamp — not CI test counts). If only presence evidence exists,
the verdict is `UNPROVEN (presence-only)` — never GREEN. If the fix has no observable runtime
surface, record `UNPROVEN (no-runtime-surface)` with the structural reason and name the surface
that would have to exist to prove it (precedent: #92 no-runtime-string finding) — a declared
N/A is a documented gap, never a discharged obligation, and never a silent skip. A verdict citing only legs 1–3 is INCOMPLETE and
gets returned to the lane. (A stripped binary that compiles the fix but crashes on the path must
FAIL — that is the exact hole this rule closes; origin: ship-38585459 smoke n=2036.)

**Owner-dependent leg → PARK, never wait (v0.4.152):** if the only remaining behavioral
evidence needs the OWNER, the leg is **NOT a blocking gate** — stamp the legs you can
prove, append a `PARKED-OWNER-EYE` row naming the exact owner action, the packaging sha
and the pre-fix control, then release the lane — **leaving the behavioural leg OPEN on the
issue until an owner verdict lands (L3).** The park releases the LANE, never the obligation.
A lane idling on an owner leg is in violation; a lane that parks and moves on is compliant. Full law, incl. the explicit-and-post-hoc verdict test
(L3): `§Owner-Dependent Smoke Legs — Park, Don't Chase` (this file).

**Swap timing is NOT coordinated with smokes** (owner decision, closing editor
proposal #8): NO advance announce, NO swap delay — deploys land whenever the
pipeline is ready, even mid-smoke; loss of in-flight in-memory state is ACCEPTED
until Alexey fixes it otherwise. If a bounce kills your smoke mid-run: re-arm tool
schemas (step 1), re-run from scratch — NEVER report the bounce itself as a feature
FAIL.

### Smoke-verdict rules

The ontology (the three kinds + the sanity signal) stays in `SKILL.md §Test ontology`; the verdict
rules live here, on the load path of the role that actually produces smoke evidence.

The ontology table lives in `SKILL.md §Test ontology`; what remains prose here:

- **SMOKE TEST** is the ONLY evidence that may back an upstream PR approval
  request (hard rule + `harvest.md` Phase 7 step 0).
- **EXECUTION SANITY SIGNAL** — the swap-path `--version` run (`oc-deploy` swap
  path; archived anchor: `tools/archive/compiler.md` Step 3) — is NONE of the three kinds: it proves only "this file is a
  runnable opencrabs binary". Not behavioral, not analytical, not presence
  evidence; never cite it as any kind of test result.

Rule: never write "tests pass" without naming the kind. A green Lint run is NOT
a smoke pass; a smoke pass says nothing about clippy; a presence hit says
nothing about behavior.

- **A VERDICT TOKEN MUST BE REACHABLE AT THE TOOL THAT WRITES IT (v0.4.243,
  cycle `20260922-c22`).** The sanctioned verdict vocabulary and the vocabulary
  the verdict WRITER can actually emit are not the same set, and nothing in the
  corpus checks the gap. Measured 2026-09-22: `oc-smoke` — the tool the
  procedure names for writing verdict rows — accepts `--verdict PASS|FAIL` and
  nothing else (`tools/smoke/oc-smoke`, the `--verdict` vocabulary), while these laws mandate
  tokens such as `UNPROVEN (presence-only)` and `PARKED-OWNER-EYE`. A lane
  ordered to stamp a mandated token through that writer therefore CANNOT: the
  row it produces says PASS or FAIL and the nuance is silently lost. So before
  citing a verdict token as *recorded* evidence, confirm the writer can emit it;
  when the mandated token is outside the writer's set, record it in the row's
  free text and STATE which form was used — never present a token the tool
  cannot produce as tool-emitted.

**Live verification stamp required for live-testable UX features (owner order 2026-09-16):**
For any UX, UI, card rendering, button interaction, or user-facing feature that is
live-testable on the running binary, static binary string probes or symbol searches alone
are STRICTLY FORBIDDEN as proof of a smoke PASS. Binary strings prove only compilation
presence, not runtime UI correctness or execution. A smoke PASS for live-testable UX
features requires an explicit live behavioral execution receipt stamped into the stamp system
(`smoke-verdicts.log` / `workers-ledger.json`). If behavioral verification cannot be fully
automated and requires the owner's visual inspection, the lane MUST record `PARKED-OWNER-EYE`
naming the exact owner action and packaging sha — never substitute a binary string probe for a
live UX verification.


**Tool-description changes have no log-based probe (lane 1a63f103, 2026-09-12):** the
daemon's provider log records tool ARGS only (`[TOOL_ACCUM] name=bash`) and NEVER tool
schemas — so no log line can prove a description string was served. Smoking a
`Tool::description()`/`input_schema()` change CANNOT be proven from the log, and
**binary strings + source constants are presence evidence, never a behavioural PASS**:
they prove the bytes shipped, not that the schema was served to a model. Record such a
change as `UNPROVEN (no-runtime-surface)` with the structural reason and name the surface
that would have to exist to prove it — a documented gap, never a discharged obligation.
Any description fragment found in the log is self-contamination from the prober's own
commands; a "live schema served" receipt from the log is a FALSE receipt.

**Leg-4 probe hygiene (lane 212b3c83, Duty-4 cycle `20260919-c21`, 2026-09-19) — three ways a leg-4 probe measures
nothing and still reports PASS.** (a) **ARTIFACT BINDING:** a criterion binds to a NAMED artifact —
rendering bytes and delivered bytes are different artifacts, because the delivery path re-encodes
(Telegram converts renders to JPEG) and a re-encode destroys fine-stroke measurements, so a criterion
that holds on the lossless render (colour type, alpha, contrast across a 1 px stroke) is **not**
thereby valid on the delivered artifact. Where both are needed, state **two legs with distinct
criteria** — the renderer leg proves the wire form is right, the delivered leg proves the user
receives the corrected output and binds on a **coarse, codec-surviving discriminator** (a large
contiguous fill region, a presence/absence inversion against a pre-fix control message) — and a
verdict resting on both must say which criterion binds to which artifact. (b) **MEASURE FROM THE
ARTIFACT, NOT THE CONSTANTS:** if every argument to the metric is a literal declared beside the
threshold, the metric measures the source file, not the artifact, and passes on any input — measure
from the loaded bytes. A **bucketing/matching tolerance must be strictly smaller than the separation
between the buckets it distinguishes**: with references `d` apart, any tolerance `>= d` merges them
and the metric silently becomes a count of the union — assign each sample to its NEAREST reference
rather than testing a radius (a merged bucket shows as a ratio that cannot exist, e.g. two bucket
counts summing past the population). (c) **SPILL-DIRECTORY COMPLETENESS:** a probe consuming tool
output must not read the spill directory as if it were complete — results under the inline threshold
are returned inline and produce **no spill file**, so a spill-only harvest has a hole exactly where
the newest evidence sits; force the spill by raising the result size, or parse the tool result inline
in the same turn. Because **expired attachment URLs are skipped silently and the skip reads as
absence**, report the skipped count beside the found count — "0 found, 13 skipped as expired" is a
different verdict from "0 found". **Corollary binding all three: a leg-4 probe reports PASS only if
it would FAIL on the pre-fix artifact — state the input on which it fails.**
**Two more ways a leg-4 probe measures nothing (Duty-4 `20260927-c25`, 2026-09-27).** **(d) AN ABSENCE-SHAPED FIX NEEDS A FIRING RECEIPT, NOT A CRITERION.** Where the fix's observable IS an absence (a message that must no longer appear, a path that must no longer be hit), a leg that checks 'it is absent' passes on a pre-fix artifact too — it cannot fail, so it proves nothing. The leg must instead show the condition FIRING on the pre-fix artifact and NOT firing after: drive the input that used to produce it and carry both readings (lane a5b34466). **(e) A PROBE OVER A MUTATING ARTIFACT OWES AN INSTANT AND AN IDENTITY RE-READ.** When the artifact can change between the probe and the report — a live store, a churning log, a page that re-renders — a bare PASS is unanchored: state the instant the probe read, and re-read the artifact's IDENTITY (hash / mtime / rowid) at report time so a later reader can tell whether they are looking at the same object. Measured 2026-09-25 on a re-rendered page: the same probe returned different results 20 minutes apart with no code change, and neither reading was wrong (lane 2ed8adeb). **Duty-5 ruling 2026-09-19 (answering lane 4b0990b7, issue #295): for a SINGLE-SIDED probe the corollary IS the sufficiency test -- the discriminating negative half need not be OBTAINED, only NAMED and mechanically shown absent from the pre-fix tree.** A positive half alone backs PASS when all three hold: (1) the falsifying input is STATED explicitly; (2) its absence on the pre-fix artifact is established by a MECHANICAL discriminator run that turn -- `git log -S <string> <fix-sha> -- <pathspec>` returning exactly ONE introduction (the fix's own commit), or the string absent from `git grep` over the pre-fix tree -- never by assertion, never by reasoning about the code; (3) the probe observes the RUNNING artifact's OWN output (a live session's rendered prompt, a real call), and the observing session itself exercises the path under test (a Telegram-bound session, for a Telegram-delivery feature) -- a `strings` dump of the binary stays presence-only and cannot back PASS for a live-testable UX feature. What the corollary forbids is a probe that cannot NAME any input it would fail on: that probe measures its own constants. Where the negative half is STRUCTURALLY unobtainable -- prompts are rendered per turn and never persisted, so a non-Telegram session's prompt cannot be read back -- the mechanical discriminator of (2) stands in for it. **Carry the discriminator's command in the row.** **And state WHICH SHAPE the fix is, because only one form applies to each:** form 1 ('exactly ONE introduction') is a claim about an ADDITION — it can only be satisfied where the fix ADDS the token. A REMOVAL-shaped fix has no introduction to find, so form 1 returns EMPTY for the correct pre-fix answer and a lane reading that empty as 'the discriminator failed' withdraws a sound probe; form 2 (absence from the pre-fix tree) is the applicable form there. Recorded 2026-09-27 (lane c6b1a539, Duty-4 `20260927-c25`): the law named both forms but never said which fix shape each covers. **Scope it, or it proves nothing:** both sanctioned forms silently assume the token is GLOBALLY UNIQUE, which this law never stated. A non-unique token -- `MAX_ATTEMPTS`, `TIMEOUT`, `retry`, `attempts` -- makes form 1 return FOREIGN introductions and form 2 a false PRESENT. Measured on `96b474e` (lane c6b1a539, verified first-hand): `git grep -nEi 'max_attempts|backoff' 96b474e -- src/cli src/a2a` returns rc=1 with ZERO hits -- the correct pre-fix answer, the retry path is absent -- while the SAME grep UNSCOPED returns rc=0 with 265 hits, including a foreign `const MAX_ATTEMPTS: u32 = 3;` at `src/brain/agent/service/compaction.rs:348`. A CORRECT fix therefore FAILS its own discriminator, and the lane may wrongly conclude its probe is unsound. So the discriminator token MUST be PATHSPEC-SCOPED to the subtree the fix changes, the row MUST carry the pathspec, and "exactly ONE introduction" is a claim about a SCOPE -- never about the tree. **Anchor it too, or it proves nothing on a pre-merge tree:** form 1's revision defaults to HEAD, and a lane runs this discriminator on a PRE-MERGE tree where the fix's own commit is not yet reachable from HEAD -- so the bare form returns EMPTY, and empty reads as "no introduction exists": a FALSE NEGATIVE on the one tree the law is about. Form 1 is therefore ANCHORED at the fix's own commit -- `git log -S <string> <fix-sha> -- <pathspec>`. Measured on #450 (lane 2ed8adeb, verified first-hand; HEAD=main, fix `b6389c892` unmerged -- `git merge-base --is-ancestor b6389c892 HEAD` rc=1): the bare form returns EMPTY, the anchored form returns exactly ONE introduction, `b6389c892`. Form 2 is unaffected by this gap and is what established the negative half for #450 -- scoped, `git grep -c 'ProgressEvent::TokenCount' 33b7aecdd -- src/channels/telegram/resume.rs` returns rc=1 with ZERO hits (the correct pre-fix answer), while the SAME grep UNSCOPED returns 19 hits across 6 files, including the fresh-turn twin at `src/channels/telegram/progress.rs:1` -- a false PRESENT.


**An UNRECOVERABLE smoke gap is a THIRD terminal state — annotate it, never dress it as a verdict (OC DEV HQ ruling 2026-10-10, answering Infra Factory Triage).** A swap whose smoke window closed with no verdict row, on a binary that has since been SUPERSEDED, can never be smoked again: the gap is **PERMANENT, not pending** — the artifact the row would cite is retired. The two terminal states above (RECEIPTED / PARKED, §Owner-Dependent Smoke Legs L2) do not cover it, so it is closed by an **explicit append-only annotation on the owning ledger subject** — L2's *"equivalently named park, with its reason"* — naming (a) the sha that went un-smoked, (b) the sha that superseded it **and the instant**, (c) the cause, and (d) that the next-cycle action is **NONE**, because no binary is left to probe. **The issue filed off the FAIL (Phase 6 step 5) does NOT discharge it:** filing records a *defect*, the row records a *verdict*, and a filing cited as coverage makes the log's silence read as coverage — the false-negative class this shop has a clause about. **FORBIDDEN: a PASS or FAIL row for the un-smoked sha.** A PASS is false, because no clean probe of the feature's own path was ever recorded; a FAIL is false *and* misattributing — it charges the defect that was filed to the feature under test, reading as a regression in a fix that is in the tree. The writer cannot carry the nuance anyway (`oc-smoke --verdict` accepts `PASS|FAIL` only — see the token-reachability clause above), which is why the annotation's home is the ledger, whose free text can. **The FEATURE, however, may not be lost — establish which, never assume:** where the un-smoked sha is still an **ancestor of the DEPLOYED binary**, the live box IS running the fix, so the feature can be probed against the **current** binary and recorded in a row citing **the sha actually under test** (L4). That cures the feature; it does NOT resurrect the gap row, and the annotation must state which of the two was done.

## No auto-rollback on smoke FAIL (owner 2026-08-28 18:50Z)

Post-swap smoke FAIL → rollback is the OWNER's call, never mechanical. The swap-chain
auto-rollback on post-bounce verify fail (crash-integrity: disk==proc mismatch → restore
backup) is UNCHANGED — that one stays automatic, and with deploy consent eliminated the
same day it is the only human gate left near the deploy pipeline.

## Owner-Dependent Smoke Legs — Park, Don't Chase (v0.4.152, owner order 2026-09-12) [LANE]

### L1 — An owner-dependent leg is NEVER a blocking gate (park, don't chase)

A smoke leg that only the OWNER can satisfy (a visual pass, a tap, an eye-confirm on a Telegram card) MUST NOT block a lane. The owning lane:

1. stamps the legs it CAN prove — lineage, identity, CI gate, and any agent-runnable behavioral probe (a live call, a forced trigger, an observed output through the new code);
2. appends a **`PARKED-OWNER-EYE`** row to `smoke-verdicts.log` naming the exact owner action required AND the packaging sha;
3. **RELEASES the lane** and moves to its next task.

`PARKED-OWNER-EYE` is a lane-release, NOT a hold: the lane goes idle and claimable, the candidate is deferred. This does not contradict the NO-HOLD law (`upstream-merge-runbook.md §Upstream-merge cadence`) — NO-HOLD forbids a *waiting state*; parking is the mechanism that keeps a lane OUT of one. A lane idling on an owner leg is in violation; a lane that parks and moves on is compliant.

### L2 — Shift exit condition: receipts or an explicit park

A shift (night or day) is COMPLETE only when every workstream sits in exactly one of two terminal states:

- **RECEIPTED** — the work is behaviourally verified: a `smoke-verdicts.log` row from a live probe of the feature's own path (plus ledger row and swap identity). A PR or issue filing is bookkeeping and never substitutes for it; or
- **PARKED** — an explicit `PARKED-OWNER-EYE` row (or an equivalently named park, with its reason) exists, naming the next-cycle action and the owner — with the behavioural leg still **OPEN** on the issue, not discharged by the park.

A workstream in state "waiting for X" is NOT terminal and blocks any completion claim. Candidates not closed inside the window **roll to the next cycle** — never chased across it. Report format: `receipted=N · parked=M · waiting=0`; any non-zero `waiting` means the shift is not done.

### L3 — An owner verdict must be explicit AND post-hoc

An owner verdict on a behavioral leg counts ONLY when it is (a) an explicit confirmation and (b) given AFTER the behaviour has finished. A passing remark made mid-flight is NOT a verdict — the behaviour may still be in progress, or about to fail in a way not yet visible.

Worked example (row 87 → row 90, 2026-09-12): the owner's "Smoke passed" landed **16 s AFTER** their own discard and **3 m 17 s BEFORE** the review subagent finished — the defect (headerless card after discard) did not yet exist on screen. The PASS was stamped, then revoked. **Rule:** if the owner's remark is not unambiguously a verdict, record `OWNER-REMARK (not a verdict)` and leave the leg OPEN/PARKED — never convert a passing remark into a PASS row.

### L4 — Smoke stamps cite the PACKAGING sha

Every `smoke-verdicts.log` verdict row's `sha=` MUST be the sha actually under test — for a harvest candidate that is the **packaging tip** (the branch head being filed), never an ancestor it was built from. A row citing an ancestor does not cover the packaging sha and cannot back a PR filing. For `CORRECTION` or `RETRACTION` rows (proposal n=4175), `sha=` names the sha of the row under correction/retraction (or the refreshed packaging sha if a fresh smoke was performed), and the retracted row identity is documented explicitly in `evidence=`.

When the packaging sha moves, the row is SUPERSEDED: append a new row, never edit the old one.
