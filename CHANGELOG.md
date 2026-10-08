# Changelog — opencrabs-dev

## v0.4.295 — Duty-4+6 cycle `20261008-c28`: eleven-lens review, six accepted findings landed (2026-10-08)

**Origin.** Cadence FIRE (7/5, boundary n=14009) — the standing Duty-4+6 periodic skill review, corpus **v0.4.294** (`693229d7`). Eleven lenses dispatched read-only (A–J + standing brain-scrub; lens **I** deliberately held until the ten reports persisted, so it audits the pattern and not the noise). Ten reports landed 15:23–16:06Z, I followed, all persisted to `$OC_DEV_STATE/reviews/20261008-c28/reports/`; `oc-review-persist check-cycle` → **OK (11 persisted, 0 waived, 0 unreceipted) rc=0**. Every load-bearing finding was re-run first-hand by HQ — **an unreproduced finding is not a finding**, and this cycle three were falsified or down-rated (record: `c28-findings.md`).

**What landed (HQ skill law only — `tools/**` untouched):**

1. **`fleet-directives.md` — J-1 HIGH: the SELF-uuid claim was stale.** The A1b table and its prose asserted a supplied self-uuid is *"REFUSED on mismatch"*. Measured at source: `_self_uuid` prints an advisory `note:` on stderr and returns **rc 0** — the refusal was **deliberately** downgraded to a warning (#657), because a hard cross-check reddens 60 selftest legs (incl. `ack2-otheruuid-rc0`; `ack`/`enroll` legitimately act on ANOTHER lane's uuid). Both the SELF row and the "Refusal is the point" paragraph now state the advisory semantics.
2. **`hq.md` — G4 MED: Duty 4 and Duty 6 had no on-file Checkable Completion Formula.** The 2026-09-27 carve moved the contract to the meta-factory path, which is NOT resolvable from this tree, leaving both duties with none. Restored on-file for each.
3. **`review-lenses.md` — four lens-brief defects.** A-M3: the A brief folded the EXECUTION SANITY SIGNAL into the ontology *kind* list (canonical is **three kinds + one signal, NEVER conflated**) → split. A-M4 / I-3: the C brief's ADOPTION-COMPLIANCE clause flagged *ANY* `gh run watch` as a violation of the **purged** One-Watcher law (dead ref `editor.md`; `grep -i watcher editor.md` → 0 hits) → narrowed to the un-throttled/off-spec forms and re-pointed to `fleet-directives.md §CI-wait discipline W1–W2`. I-1: the A brief's migration sweep was scoped to *"all three skill files"* against **15** on disk → count-free phrasing. I-2: the A brief ordered refs resolved *"against its declared home"* while naming no home and `docs/instruments/` does not exist here → the home is named, and an unreachable home must be routed, never called consistent.
4. **`harvest.md` — A-M5 MED: one law, two homes.** The ATOMICITY & ZERO BUNDLING restatement reduced to a pointer at `fleet-directives.md §Strict Atomicity & Zero Bundling`; only the harvest-local procedure (the `Issue-Ref` trailer rule + the gate) stays.
5. **`SKILL.md` — E-MED-1 MED: the census row named 4 of 7 verbs** and was the only sibling row with unescaped table pipes → verb set corrected to `<scan\|check\|record\|sync\|walk\|purge\|clusters>` and pipes escaped.
6. **`upstream-merge-runbook.md` — I-4 / C-MED-6: a currency phrase outlived its tool.** *"Until it lands this step is run by hand"* survived the landing of `oc-harvest-census walk` (commit `4c5bf657`) and its first real run (2026-10-06) → retired; the clause now names the landed verb.

**Falsified / down-rated (the false-positive history this cycle produced).** **C-HIGH-2 FALSIFIED** — `oc-watcher-audit` was claimed to have run once ever; it has **820 rows / 780 substantive** in `tools.log` and went quiet with the Oct-1 pacemakers-off stand-down, not from never running. **C-MED-6 FALSIFIED** — its premise ("the walk tool has not landed") is contradicted one paragraph below its own citation; the real defect was the stale phrase, fixed above. **C-HIGH-1 DOWN-RATED** — its predicate cannot separate a throttled detach from the 3s default, so "20 detachments" is a spawn count, not a violation count; the stale C-brief clause (A-M4) is what licensed the reading. **A-H1 sub-claim FALSIFIED** — `tools/docs/TRACKER-ROUTING.md` is NOT absent from the `SKILL.md` census (the glob ends `tools/docs/*.md`); A's core finding stands but the fix is the **Toolsmith's** surface.

**Routed, not landed here (not HQ's surface).** **Toolsmith:** `tools/docs/TRACKER-ROUTING.md:13,56` (the convergent HIGH — still tells workers the fork is read-only), `RC-CONTRACT.md:52`, `oc-issue-sweep:21`, the census↔dispatch predicate divergence (E-HIGH-1), `oc-health` escaping (F-MED-1), a `oc-ledger mode` verb (J-2), and `oc-review-persist`'s brief-less whitelist keys + `--help` (I-5). **Owner/process:** the D-class reaps (`oc-health --reap` + owner word) and the tracked-unswept `.oc-prchecks-rc2` (#540).

**Scope:** law text only — `oc-lint-laws` clean, no tool change, no build.

## v0.4.294 — fork-residue sweep: the last two pre-10-03 fork-filing writers (Triage portfolio sweep, 2026-10-08)

**Origin.** Triage, 2026-10-08, closing out the v0.4.293 fork re-scope: a portfolio-wide sweep for the *class* the two v0.4.292/293 fixes each found one at a time. Method — pattern `(file|open|create|raise|log|go directly to)…(fork issue|on the fork)` over the ACTIVE tree (`reviews/`, `archive/`, `war-stories.md`, `CHANGELOG.md` excluded), **positive-controlled against the exact pre-images of both prior sites** (`git show 83ce2bb2` / `08a2c0e0` each removed *"File a separate fork issue"*), so the instrument is proven able to see the class. Result: **2 remaining writers, both in `editor.md` — the one file never audited** for this class.

**What landed (law only, `tools/**` untouched):**

1. **`editor.md:80` — the Tool-QUIRK block.** *"Core daemon bugs go directly to GitHub fork issues."* (v0.4.133, 2026-09-10). A core daemon bug is a **BINARY** defect → upstream `opencrabs/opencrabs` post-10-03. Re-scoped to name the upstream tracker and reserve the fork for FORK-ONLY defects, pointing at the canonical routing row.
2. **`editor.md:236` — the Phase-1 fallback writer.** *"If no issue fits, open ONE issue on the fork: `gh issue create -R leshchenko1979/opencrabs`"* (v0.4.191, 2026-09-16). This was the general fallback for an issue that fit no existing one — a blanket fork filing the 10-03 order forbade. Re-scoped to route by OWNED surface: binary behaviour → `opencrabs/opencrabs`; factory tooling/CI/process → `leshchenko1979/opencrabs-dev-factory`; a FORK-ONLY defect → `leshchenko1979/opencrabs`.

**Why this is a sweep, not a third one-off.** The v0.4.292 collision and the v0.4.293 second instance were each found singly — a routing move (2026-10-03) left writers unaudited, and single finds keep surfacing more. Triage's sweep converted the search into a **class-keyed, positive-controlled** pass and named its clean set explicitly (`SKILL.md:4` role blurb, `triage.md` patrol rules, `harvest.md:293` closure formula, `fleet-directives.md:107,119` external-lanes licence, `upstream-merge-runbook.md:453,502`, `tools/docs/TRACKER-ROUTING.md`) — the class is now closed, with the negative evidence recorded rather than assumed.

**Scope:** law text only — `oc-lint-laws` clean, no tool change, no fork issue filed.

## v0.4.293 — fork re-scope: the fork takes FORK-ONLY defects (owner order 2026-10-08) (2026-10-08)

**The order.** Owner, 2026-10-08 14:59Z, answering open question `q69` (option 0): *"Approve the fork re-scope."* The 2026-10-03 two-stream order made the fork `leshchenko1979/opencrabs` READ-ONLY for new issues, which left a gap: a defect in code that exists ONLY in our fork fits neither stream. Upstream closed **#1918** and **#1938** NOT_PLANNED as stale because they cited fork-only symbols upstream cannot act on. The fork is now the home for **FORK-ONLY defects only**.

**What landed (law only, no tool change):**

1. **`SKILL.md` §Hard rules — the routing row is canonical and now carries three streams.** Binary behaviour → `opencrabs/opencrabs`; factory tooling/CI/process → `leshchenko1979/opencrabs-dev-factory`; a FORK-ONLY defect → `leshchenko1979/opencrabs`. **Every other new issue stays two-stream**, and the fork's historical portfolio stays read-only. Discriminator: the fork-only boundary register ([#761](https://github.com/leshchenko1979/opencrabs/issues/761) — `harvest-registry.json` → `manual_records`, the `not-upstreamable` rows) and the census `FORK_ONLY_SURFACE` predicate (`tools/harvest/oc-harvest-census`).
2. **Register — a new owner-order section.** `fleet-directives.md` §Fork-only issue stream — re-scope of the 2026-10-03 read-only order records the order's provenance, the discriminator, and what it does NOT do (no general issues home; §Contributor ownership untouched).
3. **The read-only claim is re-scoped at EVERY surface that carried it:** `SKILL.md` (metadata reference + the Issue-first bullet), `editor.md` (Scope), `harvest.md` (the offload order), `fleet-directives.md:176` (the Strict Atomicity bullet — corrected earlier today, re-scoped the same day), and the ops brain `AGENTS.md` (the Upstream-etiquette mention).

**A SECOND instance of the same stale collision, found while authoring.** Triage's item 1 named only `fleet-directives.md:175`; **`harvest.md:242`** (the ATOMICITY & ZERO BUNDLING bullet) carried the identical stale *"file a separate fork issue"* instruction — the same defect shape, a writer not audited when the 2026-10-03 order moved the surface. Re-scoped to the routing table in the same turn.

**Scope:** law text only — `tools/**` untouched, `oc-lint-laws` clean. No fork issue is filed by this change; it makes the class legal to file.

## v0.4.292 — upstream-filing law: the fork-filing collision fixed, and the per-commit note scoped (2026-10-08)

**Catch-up from 0.4.284.** Seven doc-first entries stacked since the 2026-10-03 sync — v0.4.285 (the creation gate's three legs, [#1932](https://github.com/opencrabs/opencrabs/issues/1932)), v0.4.286 (C1's ADDRESSING half), v0.4.287 (the fork-only walk's coverage keys on `status` alone), v0.4.288 (step 12's re-record is not executable by the register's own writer), v0.4.289 (a conditional row's `condition` is a prerequisite-chain state), v0.4.290 (the compactor never receives the retention set, [#1960](https://github.com/opencrabs/opencrabs/issues/1960)), v0.4.291 (Telegram file-sending instructions removed from the law) — each shipped its text with **no skill-bump row**, so the registry read 0.4.284 while lanes acked 0.4.291 (`oc-ledger check-version` rc 1). Published here in one catch-up. The Toolsmith tool window since v0.4.291 also rides this sync (see Bundles).

**Triage dispatch 2026-10-08** (`projects/upstream-filing-policy/files/upstream-filing-policy.md` rev.3) → two law items, HQ landed; a third parked.

1. **LIVE LAW COLLISION FIXED — `fleet-directives.md:175`.** The Strict Atomicity block's mid-loop bullet read *"File a separate fork issue"* — a filing the owner's 2026-10-03 two-stream order forbids (`AGENTS.md:69`: the fork `leshchenko1979/opencrabs` is READ-ONLY for new issues). `:175` predated the 10-03 order and was never re-scoped: the routing moved a surface and this writer was not audited with it. Re-scoped in place to two-stream routing (binary behaviour → `opencrabs/opencrabs`; factory tooling/CI/process → `leshchenko1979/opencrabs-dev-factory`), with the correction and its origin recorded inline.

2. **PER-COMMIT NOTE — SCOPE CLAUSE ADDED** (item 7's cross-reference, `fleet-directives.md`). The 2026-08-28 "one implementation comment per commit" order now binds **OUR boards only**; on a foreign tracker (`opencrabs/opencrabs`) the note posts only while an open PR exists in that repo. Rationale: his CONTRIBUTING sanctions per-commit notes in a PR context, but with no PR to anchor them they read as churn — **5 of our 8 recent upstream issues were closed for cadence**. The tool guard (`oc-ship-chain` LEG2 posts to whichever tracker holds the issue) is **routed to Toolsmith**.

**PARKED — the fork re-scope (Triage item 3) is NOT landed.** It would amend the owner's own 2026-10-03 read-only order (fork = home for fork-only defects only), so it goes to the owner as an open question, not decided here.

### Bundled commits (C8) — the catch-up range (0.4.284 → 0.4.292)

**The newest Toolsmith window (since v0.4.291):** **`3c57eb48`**+**`b853687c`** (#30 — `oc-issue-log` skips the per-commit note on a FOREIGN tracker with no open PR; the tool half of item 2 above), **`5f4f6236`**+**`1cd49468`**+**`da85d308`** (#29 — `oc-commit`'s close-keyword scan reads the whole body), **`68bc5baa`**+**`ee3d213d`**+**`a3c99f51`** (#28 — `oc-prchecks` returns the detached verdict to its caller), **`cfae8f11`**+**`e789856e`** (#27 — the tools domain gates on a surface claim), **`efc65842`** (#26 — `oc-pr-fault-scope` drops soft-fail fmt lines), **`4b4adf2c`**+**`31073aed`** (#25 — `--ref` slug + worktree), **`7f845e63`** (#23/#24), **`cd4ed4ed`** (#324 — the reopen override expires), **`ee4b1180`** (#471 — a stale IN FLIGHT row reads dead), **`59f8888d`**+**`db18892e`**+**`bb9fa9f1`**+**`daa12015`** (#21 — CAPACITY vs AFFINITY + the fixture family), **`bd652dd2`** (#20 — the walk re-verifies CONDITIONAL rows).

**The older Toolsmith windows in the same range** (each `fix(tools)` unit paired with its own battery-receipt commit), named here because a Toolsmith window ships no bump of its own — this catch-up is their only CHANGELOG record:
- `d44a577a` fix(tools): oc_log_flood_guard counts jq LINES, not matches — **correction:** an earlier
  revision of this entry filed this commit under **#471**; it carries **no issue ref**, and the #471 group is
  `ee4b1180` alone. Recorded here so the sha keeps its name and the wrong grouping is not inherited.
- `a6462df2` chore(tests): battery receipt for 093729a0 -- PASS 366 / FAIL 0
- `093729a0` fix(harvest): the census re-record carries forward EVERY prior-row key (#761)
- `71abf690` chore(tools): battery receipt PASS 366/0 for the #327 body conversion
- `56c52af1` fix(tools): convert the python3 -c bodies to heredocs, removing the class (#327)
- `7b194d9d` chore(tools): battery receipt PASS 366/0 for the #327 guard + the #762 re-pin
- `30ce1196` fix(tools): guard the double-quoted python3 -c body class (#327)
- `ba5a91c4` fix(tools): re-pin the vendored register at the template's #762 half (#762)
- `90ad5ff9` fix(tools): resolve_lane prefers a topic_edited rename over a stale topic_name echo (#762)
- `e5b2c668` fix(tools): restore the commit-body arm to squash_signature — a body-only squash landing no longer reads ELIGIBLE (#301)
- `395fa711` chore(tools): battery receipt PASS 361/0 for d2376417
- `d2376417` docs(tools): RC-CONTRACT registers the #301 squash-identity legs (#301)
- `8dea34fb` chore(tools): battery receipt PASS 361/0 for cd01ff5d
- `cd01ff5d` fix(tools): harvest tooling sees upstream squash landings — a CLOSED hand-applied PR is no longer offered for rework (#301)
- `a4e78a06` chore(tools): battery receipt PASS 360/0 for f0122176
- `f0122176` fix(tools): oc-harvest-sweep gains a source-union leg — a squash that dropped a hunk no longer reads CLEAN (#343)
- `6a5325d9` chore(tools): battery receipt PASS 360/0 for ae40c897
- `ae40c897` fix(tools): a design-gate HOLD is a reservation, not a vacancy (#312)
- `04b713cd` chore(tools): battery receipt PASS 360/0 for 7006efe9
- `7006efe9` fix(tools): delete the INERT (target,window) journal fallback from oc-notify.sh (#18)
- `ec0bf806` chore(tools): battery receipt PASS 360/0 for e477a46d
- `e477a46d` fix(tools): bound the twin scan and stream its patch-id path (#363)
- `9beec247` chore(tools): battery receipt PASS 360/0 for the #472 receipt-identity fix
- `fd8a6513` fix(tools): the dispatch receipt carries MESSAGE identity, not just (target, window) (#472)
- `8f226b3c` chore(tools): battery receipt PASS 356/0 for 8280dc2e
- `8280dc2e` fix(tools): harvest arms get an IDENTITY LEG on the MERGED/IN_FLIGHT inference (#416)
- `54be64ff` chore(tools): battery receipt PASS 356/0 for 41b6e030
- `41b6e030` fix(tools): the dispatch LANDED arm anchors a commit to its issue's NAMED surface (#455)
- `fb7d5f12` chore(tools): battery receipt PASS 356/0 for ee7b6cca
- `ee7b6cca` fix(tools): a RED gate names its failing step and prints the error line (#642)
- `4a4faf34` chore(tools): battery receipt PASS 356/0 for 417f6ed2
- `417f6ed2` fix(tools): resolve the fork-main tip from refs/oc-deploy/main, never the shared FETCH_HEAD (#704)
- `4ab72d0d` chore(tools): battery receipt PASS 356/0 for 916e3669
- `916e3669` fix(tools): oc-deploy's poll handoff gets an in-flight guard — no duplicate swap units (#729)
- `dcd4674e` chore(tools): battery receipt PASS 356/0 for 03fe3805
- `03fe3805` fix(tools): a FAILED roster read gets its own rc 10, not a false CAPACITY_EXHAUSTED (#706)
- `91f8b890` chore(tools): battery receipt PASS 356/0 for 377239c5
- `377239c5` fix(tools): the (tools) scope LABEL is confirm-only, so src/brain/tools/** issues stop accruing tools affinity (#641)
- `243839b9` chore(tools): battery receipt PASS 356/0 for 67a0e024 (#551)
- `67a0e024` fix(tools): oc-issue-dispatch reads the declared type(scope): prefix before the prose keyword fallback (#551)
- `6999c694` chore(tools): battery receipt PASS 356/0 for 92396f17 (#621)
- `92396f17` fix(tools): oc-issue-log's idempotency guard also matches on patch-id, so a content-identical rebase no longer duplicates the implementation comment (#621)
- `44cc50af` chore(tools): battery receipt PASS 356/0 for dad629e9 (#590)
- `dad629e9` fix(tools): oc-rebase-safety overlap derives the branch-side set for a rebased single-parent head (#590)
- `f9d868f3` chore(tools): battery receipt PASS 356/0 for dafddcbb (#359)
- `dafddcbb` fix(tools): oc-ledger check-version names the cause — fleet-level meta lag vs real lane drift (#359)
- `236c25d8` chore(tools): battery receipt PASS 356/0 for 918db25f (#643)
- `918db25f` fix(tools): oc-lint-laws reports wide-gap flags no tool owns (#643)
- `2ba9b414` chore(tools): battery receipt PASS 356/0 for c7dd94ff (#736)
- `c7dd94ff` fix(tools): oc-questions --help names the label/letter --recommended form (#736)
- `54f0c4c2` chore(tools): battery receipt PASS 356/0 for 5dc638cb (#570)
- `5dc638cb` fix(tools): oc-ledger atomic_jq names its cause; promote coerces a legacy string .notes (#570)
- `44624191` chore(tools): battery receipt PASS 356/0 for 50671af2 (#709)
- `50671af2` fix(tools): oc-questions publishes --schema; the bridge derives its argv from it (#709)
- `bbdf5eb9` chore(tools): battery receipt PASS 351/0 for 57c7e1e0 (#15)
- `57c7e1e0` fix(tools): carry-aware HELD_BASE_RED — a unit that carried the sweep is not refused (#15)
- `62c31a77` chore(tools): battery receipt PASS 351/0 for d076fd76 (#17)
- `d076fd76` fix(tools): exclude the generated sidecar class from the shell-quoting scan (#17)
- `16e985a4` chore(tools): battery receipt PASS 349/0 for b1def71f (#356)
- `b1def71f` fix(tools): anchor the upstream fork-ref scan to a slug-qualified trailer (#356)
- `49fd930b` chore(tools): battery receipt PASS 349/0 for 3358ba31 (#16)
- `3358ba31` fix(tools): exclude the generated sidecar class from the private-copy scan (#16)
- `13cf71d1` chore(tools): battery receipt PASS 349/0 for 9fbbbd16 (#315, #525)
- `9fbbbd16` fix(tools): journal every deleted branch tip, not only the last (#525)
- `d923d94b` fix(tools): state the soak basis with the age so the number is attributable (#315)
- `1a214b8a` chore(tools): battery receipt PASS 346/0 for 3097448e (#738)
- `3097448e` fix(tools): the unified-log ts parser reads both Z and +00:00 forms (#738)
- `2ef0d415` chore(tools): battery receipt PASS 336/0 for 2bfc276d (#310)
- `2bfc276d` fix(tools): oc-issue-dispatch drops a dead class-filtered availability path (#310)
- `33ac83d4` chore(tools): battery receipt PASS 334/0 for #91f72a99 (#308)
- `91f72a99` fix(tools): oc-pr-fault-scope accepts --ref for PR-less fork lanes; drop registry/vendor paths from the failing-file parser (#308)
- `f5cbad5d` chore(tools): battery receipt PASS 334/0 for #760
- `fee6c127` fix(tools): retire two hand-rolled unified-log copies onto tools/lib/oc_log.py (#760)
- `8e347444` test(tools): cover the oc-deploy status rc-1/rc-2 contract the #746 fix landed without legs
- `864fe787` fix(tools): oc-smoke runs the lineage ancestry check itself when --lineage is omitted (#673)
- `74da35c8` chore(tools): battery receipt PASS 329/0 for #671
- `68051ef8` fix(tools): battery reachability guard runs the extractor instead of counting PRELUDE matches (#671)
- `c45c6ad5` chore(tools): battery receipt PASS 327/0 for 5817058f
- `5817058f` fix(tools): oc-ship-chain pre-checks SIGNATURE before LEG3 ff-merge (#755)
- `9b365420` fix(tools): oc-commit normalises and validates the Session-Id actor (#754)
- `cf18d774` chore(tools): battery receipt PASS 327/0 for b8f693a7
- `b8f693a7` fix(tools): drop oc-waiter registry rows + stale consumer ref (#737)
- `fbc9b678` fix(tools): delete the retired oc-waiter stub (#737)
- `fd2edb46` chore(tools): battery receipt PASS 328/0 for 1fe809ea
- `1fe809ea` fix(tools): oc-ship-chain reports an ORDER-gate fault as INFRA (#756)
- `43fe7a15` chore(tools): battery receipt PASS 328/0 for a9da3137
- `a9da3137` fix(tools): oc-ship-chain wakes the arming lane only for a real chain attempt (#14)
- `f7d618bc` chore(tools): battery receipt PASS 328/0 (ts 2026-10-04T23:09:53Z, wall 317979ms)
- `ba8982cc` fix(tools): oc-harvest-census distinguishes conditionally-upstreamable manual records (#13)
- `c9cdb890` feat(tools): oc-deploy publishes the verified binary as fork release assets (#766)
- `702acbaf` fix(tools): port the (factory, lane) registration gate to the vendored oc-questions
- `f2113509` chore(tools): battery receipt PASS 328/0 (ts 2026-10-04T20:57:20Z, wall 322862ms)
- `a715a185` fix(tools): LEG2 resolves the issue tracker instead of defaulting to the fork (#11)
- `24bbcad2` chore(tools): absorb the upstream repo rename in tools/** + TRIAGE grant docs
- `59b6d912` chore(tools): battery receipt PASS 328/0 (ts 2026-10-04T20:05:40Z, wall 342583ms)
- `aa28b929` docs(tools): RC-CONTRACT row 33 carries the #12 clause — a declared PR keys the map; a prose mention does not
- `8df39e62` chore(tools): battery receipt PASS 324/0 (ts 2026-10-04T17:41:42Z, wall 248559ms)
- `cb8a36be` fix(tools): oc-harvest-census IN_FLIGHT leg keys a PR-body PROSE mention as an implementation (#12)
- `1a46bfef` docs(tools): RC-CONTRACT row 33 carries the #10 clause — a doc-comment-only hunk resolves FORWARD
- `ffc1eed1` chore(tools): battery receipt PASS 324/0 (ts 2026-10-04T15:27:51Z, wall 308339ms)
- `8b0dc608` fix(tools): oc-harvest-census attributes a doc-comment-only hunk to the PRECEDING fn — a false "dropped at packaging" advisory (#10)
- `1872c036` chore(tools): battery receipt PASS 324/0 (ts 2026-10-04T07:43:08Z, wall 246396ms)
- `42e49536` fix(tools): oc-harvest-census reads an added `impl X` as an arrived declaration when upstream carries `struct X` — declaration KIND conflated (#6)
- `c0bd5f13` docs(tools): the claim mechanism's assignment leg is best-effort, not assumable
- `e91a1efc` chore(tools): battery receipt PASS 324/0 (ts 2026-10-04T02:10:48Z, wall 265160ms)
- `4dcdee27` fix(tools): oc-harvest-census resolves a hunk to its enclosing CONTAINER, not the nearest fn
- `3a646f80` runtime-artifacts sweep: battery receipt (324/0, wall 336s, jobs=4)
- `6129c3a1` fix(tools): oc-prchecks rc 6 discriminates a JOB-TIMEOUT cancel from a concurrency supersede (#5)
- `9f1cdbbf` runtime-artifacts sweep: battery receipt (324/0, wall 444s, jobs=4)
- `85bade63` runtime-artifacts sweep: battery receipt (324/0, wall 325s, jobs=4)

## v0.4.291 — file-sending instructions removed from the law (2026-10-08)

**Owner order, verbatim:** *"Remove the telegram file sending instructions from all laws. Both about editors and HQ."*

**Why the law was wrong, not merely stale.** The clause at `TELEGRAM.md §File delivery on Telegram` mandated `telegram_send` (`send_document` / `send_photo`) because a file "cannot ride session text". Read at source, that premise is dead: the Telegram channel now folds a resolved local markdown link (and a remote link) into the attachment path and sends each resolved local file as its own document bubble — `src/channels/telegram/delivery.rs:168` and `:2083` (#1916). A local file link in session text therefore delivers with no send tool at all, which removes the entire reason the editor→HQ relay and the "HQ performs the `telegram_send`" clause existed.

**What was removed.** The whole `## File delivery on Telegram` section in the ops `TELEGRAM.md` (its heading was retitled to `## Message body cap` for the section that followed); ops `AGENTS.md` hard rule 15 (*"Files on Telegram: a bare path is not delivery. Send with `telegram_send` before the closing text."*) — rules 16–23 renumbered 15–22, with the two live cross-references (`rule 21` → `rule 20`, `rules 1–7` unchanged) and the `SECURITY.md` ripple (`hard rule 21` → `hard rule 20`) fixed in the same pass; the trailing `telegram_send` sentence in `USER.md`; and, in this file, the `File delivery:` sub-bullet and the `Option (c) is FALSE` sub-bullet of the HQ ruling, whose section is retitled `## Telegram surface — own-feature probes (HQ ruling 2026-09-21)` and whose index entry drops `file delivery & `.

**What was deliberately KEPT.** The Rollcall law (`fleet-directives.md` §Decision Rollcall) still forbids `telegram_send` / `send_document` / media *in a Rollcall post* — a distinct instruction about how decisions are presented, not about file delivery. The leg-4 bot-initiated-probe clause stays: a probe of a feature that only fires on a bot-initiated send is not a file-delivery instruction. `SKILL.md §Telegram surface law` (editors never invoke telegram tools for inter-role comms) is unaffected and stands. The `telegram_send` addressing rule and the host-outage escalation path are untouched.

## v0.4.290 — the compactor never receives the retention set, and nothing enforces it (2026-10-06)

**The tell.** A lane's compaction emitted `active_skills: [opencrabs-dev/harvest.md]` / `discard_skills: [opencrabs-dev]`, and the next turn's `bash` on a path matching `opencrabs-dev` was refused by the skill gate — one turn lost. The lane asked whether §10 needed sharpening for the compactor, or whether this was a harness defect to route.

**Ruling: harness-side, and §10's own premise was false.** Read at source: the compactor's call carries a fixed system prompt (`compaction_system_prompt()`, `src/brain/agent/service/context.rs:927`) plus the Manifest Rules block (`:1330-1352`), which carries **no retention list**; the §10 law lives in `context.system_brain` (the #219 reinjection, `tool_loop.rs:1392-1414`), which the compaction call does not send. §10 is therefore addressed to an audience that never receives it — sharpening it alone cannot fix anything. The canonical section's claim that the compactor "honors manifest guidance … without binary modifications" is corrected in place, with the measured counter-instance and the mechanism. Nothing enforces the set: `warn_on_summary_invariants` checks that the fence EXISTS, never its content, and `shed_order` protects only the last remaining entry.

**Filed upstream:** [opencrabs/opencrabs#1960](https://github.com/opencrabs/opencrabs/issues/1960) — parent #219, assigned `adolfousier`.

**Changed:** `fleet-directives.md` §Post-compaction skill reload & context manifest curation (claim corrected in place); `SKILL.md` §Hard rules (pointer caveat).

## v0.4.289 — a conditional row's `condition` is a prerequisite-chain state, not a portability claim (2026-10-06)

**What the harvest lane asked.** Units 676 / 757 were recorded `conditionally-upstreamable` naming `#1941` as the condition. `#1941` closed as landed; the census's `check` still REFUSES both. The lane read that as a disagreement between the register's "the change is upstream" judgment and the census's mechanical portability read, and asked for a ruling.

**Ruling: no disagreement, no downward re-record.** `check 676` emits, as its FIRST refusal, the manual-record claim — `Target 676 is manually recorded as CONDITIONALLY UPSTREAMABLE … it is not harvestable TODAY` — and only then refuses on the mechanical legs (`FORK_ONLY_SURFACE`; `HELD_DEPENDENCY_NOT_UPSTREAM`), its own text stating the verdict *"is about PORTABILITY; the UNHARVESTED claim is separate."* The register records the same operative conclusion from the other end. Both are right about **different questions**: the register's `condition` is a prerequisite-chain state, the census's refusal a portability verdict. Measured on `adolfousier/main` tip `9f53c5479` (the tip the lane cited — the ref was fresh, not stale): slice-1 content present (`spacing_floor_ms` / `spacing_wait` / `is_droppable` / `SURFACE_EDITS` / `SURFACE_RICH`), engine declarations absent (`RichAdmission` / `next_token_in_for` / `note_rich_drop` = **0**). A met SUB-condition does not make a row portable. The hazard is **wording**, not status: a `reason` leading with "CONDITION MET" can be misread as *applied-upstream → nothing owed*.

**Design constraint recorded (the tool change is factory [#20](https://github.com/leshchenko1979/opencrabs-dev-factory/issues/20)).** Any widening of the walked set keys on the **prerequisite's own state**, never a surface diff — the surface premise already reads **CHANGED** on units 556 / 580 (2/15 and 11/14 declarations arrived) while both remain gated on `#1927`, so a surface diff reports "matured" on a row that is still not portable.

## v0.4.288 — the re-record the step-12 clause prescribes is not executable by the register's own writer (2026-10-06)

**What the harvest lane measured.** The step-12 clause (`upstream-merge-runbook.md`, landed `04933052`) prescribes that the flagged re-record *"carries each row's `reason` / `branches` / `condition` / `prerequisite` forward, never a bare status flip"*. The register's own writer cannot do it: `oc-harvest-census record` REPLACES the whole row and carries forward only a **fixed seven-field tuple** (`status`, `reason`, `issue`, `issues`, `branches`, `revert`, `verified_at`; `tools/harvest/oc-harvest-census:3389`), and its flag surface carries no `--condition` / `--prerequisite` / `--dispatch` (`:101`). Those three fields are therefore **DROPPED** by the upsert.

**What changed.** The step-12 clause gains the writer limitation as an explicit disclosure, so the clause is not read as executable-by-tool when it is not; the instrument defect is routed to Toolsmith. **Recorded as performed:** units **635 / 556 / 580** re-recorded to `status: conditionally-upstreamable` by direct edit — `condition` / `prerequisite` / `dispatch` preserved, `class` / `status_unchanged_reason` dropped as redundant — state commit `30744fef0`, ledger n=14845; 556 / 580 disposition **RE-DECLARE** (premise (a) SURFACE moved: #1941's spacing floor landed upstream, upstream now carries 2/15 and 11/14 product declarations; the remainder is still fork-only and `#1927` still gates it). Register now: 74 rows — **56 filed / 12 not-upstreamable / 6 conditionally-upstreamable**; `class` and `status_unchanged_reason` at **zero** rows.

**Scope.** Law text + version only — `tools/**` unchanged (the writer's fixed tuple is a Toolsmith follow-up). `oc-lint-laws` clean.

## v0.4.287 — the fork-only walk's coverage is keyed on `status` alone: a `class` field is invisible, and the conditional concept has lived in two shapes (2026-10-06)

**What the first real run measured.** The #761 step-3 leg (`oc-harvest-census walk`) ran against the live register for the first time — the walk's own `rc=1`, over **15** OPEN `not-upstreamable` rows: **2 CHANGED** (units 556, 580), **13** UNVERIFIED/UNCOVERED, **0 VERIFIED**. It also exposed a register-hygiene split the law had never named: the walked set is `oc_claims.manual_record_status(r) == not-upstreamable`, an **equality on `status` alone**, so units **635 / 556 / 580** — which express "conditionally upstreamable" through a **hand-added `class` field** while `status` stays `not-upstreamable` — were walked **as plain fork-only rows**, while units **676 / 757 / 763** (the sanctioned `status: conditionally-upstreamable`, token `ba8982cc`, #13) were **skipped** entirely.

**What changed.** `upstream-merge-runbook.md` §Process step 12 gains a coverage clause: the walked set is the TERMINAL arm; `class` is an UNDECLARED second vocabulary for a concept the row schema already owns (`status`); units **635 / 556 / 580** are **FLAGGED FOR RE-RECORD** into the sanctioned `status: conditionally-upstreamable` — the blocker those rows themselves named (*"status stays not-upstreamable until the census vocabulary carries the new class (unknown status maps to filed = unsafe)"*) having lapsed — carrying `reason` / `branches` / `condition` / `prerequisite` forward, never a bare status flip; and the leg's silence on a conditional row is **disclosed as silence, never a pass**.

**Scope.** Law text only — `tools/**` unchanged, the walked set still keys on `not-upstreamable` (matching design [#761](https://github.com/leshchenko1979/opencrabs/issues/761) step 3, which was written before the conditional status existed, so this is a post-design coverage gap disclosed rather than retro-fitted). The register re-record of the three rows is **flagged, not performed** — a state write owed to the harvest lane. `oc-lint-laws` clean.

**Also in this window.** `90ad5ff9` — `resolve_lane` prefers a `topic_edited` rename over a stale `topic_name` echo ([#762](https://github.com/leshchenko1979/opencrabs/issues/762)).

## v0.4.286 — C1's ADDRESSING half gets its own measured instance (lane 2fae1230, 2026-10-06)

**What was measured.** C1 (`fleet-directives.md` §C1) has always been explicit about both halves of the claim-closure predicate — the closing KIND *and* the ADDRESS — but its only worked instance (the #299 `note`-vs-`unclaim` case, v0.4.202) demonstrates the KIND half alone. Two `done` rows on 2026-10-06 were written the natural post-merge way, prefixing the BRANCH name: `fix/343-harvest-sweep-union-leg landed f0122176 …` (n=14800) and `fix/301-squash-identity landed e5b2c668 …` (n=14803). Each named its issue only inside the slug, so neither addressed it; both claims stayed OPEN on CLOSED issues whose work had genuinely landed, and both lanes believed the release had taken. `sweep-closed-claims --dry-run` caught both and released at n=14805 (#301) / n=14806 (#343).

**What changed.** One instance bullet added to C1 beside the #299 instance, naming the form: **write the ref FIRST — `oc-ledger stamp done "#N — landed <sha> …"`**. The kind and the content were both right in the failing rows; only the address was missing, which is why the section needed the second half visible as an instance and not merely as a predicate.

**Scope.** Law text only — the predicate itself (`tools/lib/oc_claims.py`) is unchanged, and `oc-lint-laws` is clean. Raised by editor lane 2fae1230, which correctly drafted, reverted, and handed the text to HQ rather than editing it (durable record: ledger `lesson` n=14807).

## v0.4.285 — the creation gate has THREE legs: origin, assignee, native link (owner order 2026-10-05, origin opencrabs/opencrabs#1932)

**Owner order 2026-10-05 10:19Z** (channel `OC Dev`), verbatim: *"First: https://github.com/opencrabs/opencrabs/issues/1932 — It was not linked to the parent issue and not assigned to Adolfo. Fix the laws so that this is done correctly next time"*.

**What #1932 measured.** The issue was filed on the BINARY tracker under the v0.4.284 two-stream routing, correctly declared `upstream-rooted` — its `root: ede0763be` comment named a commit by **adolfousier** whose body carries `Closes #737`, i.e. the defect it reports lives inside the maintainer's own commit, so the ORIGIN leg was honest and satisfied. Two gaps remained, and both are now closed:

1. **No assignee mechanism.** `oc-issue-create` had no `--assignee` handling at all (one doc-string mention). GitHub's upstream `auto-assign.yml` then assigns the **author** — #1932 landed on `leshchenko1979` at 23:17:42Z and the owner hand-corrected it to `adolfousier` at 2026-10-05T06:27:32Z. Live read: **40 of 40** recent upstream issues carry `adolfousier`, so the assignment is the tracker's standing convention, not a one-off.
2. **Comment-only root, no native link.** A `root:` comment satisfies DECLAREDNESS but creates no native parent edge. #1932 still reads `parent: null`. For `--root upstream:<sha>` the parent is **derivable** — from that commit's own `Closes #N` / `Fixes #N` trailer (`ede0763be` → `Closes #737`) — and the law never asked for the derivation.

**Why the gate, not a reminder.** Measured live 2026-10-05: **all 30** sampled recent upstream issues carry `parent=null` — upstream does not use native parents at all — so the same-tracker parent for a regression like #1932 must be *derived*, not looked up, and only a gate that states the derivation can make that happen. This is the same failure shape the 2026-09-25 origin gate was built for: a mandate without a detector lapses unseen.

**What lands.** The CREATION-TIME PARENT GATE becomes a **THREE-LEG** gate on every `fix(`/`bug(`-titled issue: **(a) ORIGIN** (unchanged: `--parent <N>` / `--root upstream:<obj>` / `--no-parent "<reason>"`), **(b) ASSIGNEE** (`--assignee <login>` — binary tracker `adolfousier`, factory tracker the filing role's owner), **(c) NATIVE LINK** where the declared origin resolves to a same-tracker issue (`--parent <N>` at creation, or `gh issue edit <issue> --parent <N>` as the immediate next action; for `--root upstream:<sha>` the parent is derived from the commit's `Closes #N` trailer). Triage's Duty T5 backstop gains the matching questions with **per-leg population boundaries** — legs (a)/(c) keep the origin gate's 2026-09-25T22:33:06Z boundary, leg (b) runs on issues created at or after the owner order (2026-10-05T10:19Z), since #1932 itself predates it and was corrected by hand.

| file | change | LOC |
|---|---|---:|
| `SKILL.md` | §Upstream relations · ISSUE ROUTING — the gate's three legs + Toolsmith follow-up | 504 → 518 lines |
| `triage.md` | CREATION GATE (three legs) + BACKSTOP LEGS (b)/(c) with per-leg boundaries | 597 → 597 lines |
| `editor.md` | Phase 1 item 2 — the three legs on the creating command | 763 → 762 lines |
| `upstream-merge-runbook.md` | §Native Sub-Issues Mandate — the three legs + T5 backstop extension | 514 → 514 lines |

**The Toolsmith half is NOT in this commit.** `oc-issue-create` gains `--assignee` as a first-class flag with the per-tracker default, and derives `--parent` from a `--root upstream:<sha>` commit's `Closes #N` trailer. Until it lands, the filing LANE passes both by hand — the lane owns the leg, the tool only automates it. The full spec is carried in the `SKILL.md` §Upstream relations clause and is dispatched to the Toolsmith lane.


## v0.4.284 — the two-stream issue routing: binary upstream, factory to the dev-factory repo (owner order 2026-10-03)

Bundles the routing overhaul below with the window's other lanes' work: **`c377eeb0`** + **`d1404d7a`** (#730 header-parser guard, Toolsmith); **`3fe3618f`** + **`839868e5`** (#764 — the declaration-dependency predicate reads CODE, not PROSE); **`12d316e3`** + **`ee792ad3`** (#765 — `NOTE(HUNK_SYMBOL_DIVERGED)` names the DIFFERING region); **`4c5bf657`** + **`062861b7`** (#761 step 3 — the `walk` verb); **`994951f7`** (law — #761 step 3/4 precision: rows key on `unit`, branches-absent is UNCOVERED, CLOSED is mechanical); **`0bbc4da5`** (re-vendor `oc-questions`); **`e6c3bb25`** (docs — the open-questions architecture doc describes the shipped shape); **`0942d203`** (docs — the v0.4.283 C8 naming fix, which post-dates the `v0.4.283` tag and therefore rides this window rather than its own).

**Owner order 2026-10-03 21:17Z** (channel `OC Dev`), relayed by lane `55943b3e`, verbatim: *"The existing issue portfolio stays at leshchenko1979/opencrabs. For new issues, we need to split them into two streams: opencrabs binary and opencrabs dev factory. The new binary issues go to adolfousier/opencrabs and follow the process we just agreed. The new factory issues will need to go to leshchenko1979/opencrabs-skills. But first rename it to opencrabs-dev-factory. Speak to opencrabs dev factory hq so that they can make the needed changes to their laws."*

**What REVERSES.** Two live rows die here. The 2026-08-27 row *"NEW issues NEVER upstream — every new issue (upstream-code bugs and fork-only infra alike) is filed on the FORK"* (`SKILL.md` §Hard rules ISSUE ROUTING) and its downstream echo, the 2026-09-01 correction *"Issue reports NEVER go upstream — the fork is the issues home, permanently"* (`harvest.md` §Upstream issue filings). Both are **superseded**: a **BINARY** issue (runtime behaviour, channels, providers, TUI, memory, tools) is filed on UPSTREAM `adolfousier/opencrabs` — the binary tracker from today; a **FACTORY** issue (tooling, CI, release automation, process) is filed on `leshchenko1979/opencrabs-dev-factory`. The historical portfolio at `leshchenko1979/opencrabs` is **READ-ONLY** — no new issues, and it is never re-filed.

**The generalized lifecycle (owner item 6) rides upstream as PR [adolfousier#1907](https://github.com/adolfousier/opencrabs/pull/1907).** Mandatory duplicate sweep (open **and** closed, issues **and** PRs) before filing; `fix core` / `feat core` title prefixes mark core-surface changes; **assignment is the public claim signal** (owner item 5b, PR [adolfousier#1906](https://github.com/adolfousier/opencrabs/pull/1906) makes the maintainer's own issues self-assign); and `Closes #N` is now **VALID same-repo** — the reason it was forbidden (issue and PR in different number spaces) no longer holds for a binary issue closed by its own upstream PR. It stays **forbidden across trackers**: a factory issue on the dev-factory repo has no upstream number space, so those PR bodies still end `Original issue: <full URL>`.

**Repo rename.** `leshchenko1979/opencrabs-skill` → **`leshchenko1979/opencrabs-dev-factory`** (PUBLIC; the old name redirects). The owner wrote "opencrabs-skills" (plural); no such repo exists — the singular repo holds the whole skill corpus and is the one renamed. The local clone's `origin` was already repointed by the relaying lane; **the historical `mirror2` alias is retired** (verified: `git remote -v` lists ONLY `origin`), so the H-3 push-remote row and `RC-CONTRACT.md:89` now agree on `origin` as the sole name — the drift the order asked to reconcile.

**The Toolsmith half is NOT in this commit.** Nine live `tools/**` files hardcode the fork default (`oc-questions:50` `FORK_REPO`, `oc_ledger:4189`, `oc_issue_create:40`, `oc_issue_dispatch:616`, `oc-issue-scope:105`, `oc_issue_sweep:39`, `oc-watcher-audit` ×5, `oc_claims.py:266` `FORK_REPO_SLUG`). Which tracker each tool should default to is a `tools/**` design decision — Toolsmith's carve-out — and is dispatched to that lane, not decided here.

| file | change | LOC |
|---|---|---:|
| `SKILL.md` | issue-routing table (4 rows), reference list, reports-link rule, issue-first bullet | 499 → 504 lines (**+5**), 47,380 → 48,757 bytes (**+1,377**) |
| `harvest.md` | §Upstream issue filings — offload order superseded | 458 → 458 lines, 46,376 → 46,742 bytes (**+366**) |
| `editor.md` | Scope — issue provenance split | 762 → 763 lines (**+1**), 81,785 → 81,902 bytes (**+117**) |
| `toolsmith.md` | 2 sites — daemon defects → binary tracker | 165 → 165 lines, 16,559 → 16,698 bytes (**+139**) |
| `upstream-merge-runbook.md` | H-3 push remote (`mirror2` → `origin`) | 514 → 514 lines, 96,279 → 96,491 bytes (**+212**) |
| `triage.md` | 2 sites — skill-repo name | 543 → 543 lines, 70,515 → 70,527 bytes (**+12**) |
| `README.md` | mirror target name | 83 → 83 lines, 6,301 → 6,350 bytes (**+49**) |
| `tools/docs/RC-CONTRACT.md` | repo name + remote reconcile | 122 → 122 lines, 171,754 → 171,879 bytes (**+125**) |
| `tools/docs/OPEN-QUESTIONS-INSTALL.md` | raw-URL base | 183 → 183 lines, 8,555 → 8,561 bytes (**+6**) |

## v0.4.283 — q51 → B: the census fence falls, and the fork-only boundary closes its second half

Bundles **`e8049354`** + **`8be92beb`** (q51), **`58be1d05`** (#761 step 3), **`875cd7ef`** (#761 step 4), with **`84ddf658`** (battery receipt sweep). The range also carries the questions-lane pair **`2b60d931`** + **`2e4195b4`**, the re-vendor **`d377e7ad`**, and **`2a4081d7`** — the v0.4.282 C8 naming fix, which post-dates the `v0.4.282` tag and therefore rides this window rather than its own.

**q51 → B — the census's own In-Flight Lane Fence is DROPPED.** q46 → D removed the fence's DISPATCH enforcement point but parked its second one as an open question; the owner's «Go» on the q51 report (the recommended option B) removes the census point too. The law half is `e8049354`: **five sites across two files** — `harvest.md` §Phase 7c, and `upstream-merge-runbook.md` `:336` (the fence clause), `:395` (the v0.4.233 expiry classification, whose no-expiry class now names `HELD_PARENT_UNHARVESTED` alone), `:417` ("four independent rc=1 fences" → **three**) and `:418` (the gate chain, gate 3 annotated DROPPED rather than renumbered). The tool half is `8be92beb`: gate 3 removed from `oc-harvest-census`.

**The catch worth remembering:** the fence had two live law copies, and the second was hiding in the same file that had already declared the first dead — `upstream-merge-runbook.md:336` said the fence was gone while `:417`, further down the same file, still described the census's `HELD_IN_FLIGHT_LANE` as one of **four** independent fences. A reader of the first passage would conclude no in-flight fence exists anywhere. Both copies now agree.

**Nothing load-bearing went with the tool cut.** The shared footprint resolver (`run_engine test-active-claims`, the #307 anchored-footprint legs) and `filter_substantive_overlap` serve sibling gates and four other tools (`oc-ledger`, `oc-health`, `oc-roster`, `oc-issue-dispatch`) and STAY. Capabilities that were properties OF the fence (holder-liveness / dormancy disclosure, phantom-holder skip, per-(lane,issue) row dedup) died with it; four more were **re-vehicled** onto surviving legs (the #375 registry-exemption anti-vacuity proof → gate 2; #493 / #533 / #307 → `cycle_note`) rather than deleted. The #307 mutation guard's `registry_filter_dropped` anchor was re-anchored from the fence's 12-space filter pair (deleted) to gate 2's 20-space pair — left alone it would have matched **0 times** and gone INERT (the #759 failure mode). The blocker re-validation advisory (#536, leg v) was GATE-3-ONLY with no surviving consumer and is **retired, not re-vehicled** (ponytail-lazy; reversible by a fresh ruling).

**#761 step 3 — the fork-only sync re-verification leg (`58be1d05`).** `upstream-merge-runbook.md` §Process gains **step 12**: at each sync, walk every OPEN `not-upstreamable` row and re-verify its three premises — the SURFACE (declaration-level predicate, never a by-name match), the BRANCH SET, and the REASON — REPORTING every row whose premise changed **by row id**, and stamping `verified_at` on rows re-verified unchanged. Removal is forbidden (`harvest.md` §Phase 7c) and silence is not retention: a stale row is a FINDING, never a quiet skip. The tool leg (`oc-harvest-census` walk, dry-run by default) is dispatched to the Toolsmith lane; the law leads the tool by one dispatch.

**#761 step 4 — the fork-only teardown exemption (`875cd7ef`).** `editor.md` Phase 2 gains the exemption: a unit carrying an OPEN `not-upstreamable` row **keeps its worktree**, because the worktree is the local anchor a sync's force-push would erase — the one event that can invalidate the declaration's premise. **RELEASE = the row is CLOSED, or re-verified as now-TRAVELLING.** The bug-fix completion formula carries the matching qualifier.

| file | change | LOC |
|---|---|---:|
| `harvest.md` | q51 law — the fence clause's SCOPE | 458 → 458 lines, 45,822 → 46,376 bytes (**+554**) |
| `upstream-merge-runbook.md` | q51 law (4 sites) + step 12 | 510 → 514 lines (**+4**), 93,022 → 95,736 bytes (**+2,714**) |
| `editor.md` | step 4 teardown exemption + formula qualifier | 761 → 762 lines (**+1**), 80,189 → 81,400 bytes (**+1,211**) |
| `tools/harvest/oc-harvest-census` (+ mutation guard, RC-CONTRACT) | gate 3 removed | 3 files, **+208/−544** |

**Verification (same-turn reads).** Census selftest **97/97 OK** rc=0 (baseline 108; delta −11 = 16 removed / 5 added) · #307 mutation guard **PASSED, all 9 mutants caught**, `registry_filter_dropped` CAUGHT with anchor occurrences=1 · dispatch selftest **53/53 OK** rc=0 (untouched regression control) · battery **PASS 324 / FAIL 0** rc=0 (wall 336 s, jobs=4, receipt `2026-10-02T22:12:39Z`) · `e8049354` / `58be1d05` / `875cd7ef` each re-measured against the commit for the LOC table above.

**Disclosed residual, unchanged from q46.** The two guards ask **different axes** — the portability predicate asks *does upstream carry the surface this fix repairs*, the fence asked *is a lane still moving this subsystem*. With both fence points gone, a harvest may run against a subsystem an active lane is still changing; re-introduction needs a **fresh owner ruling**, never a lane's judgment. The **725** duplicate in `manual_records` also persists (removal forbidden by design; the unit-key upsert fixed the append, not the legacy pair).

## v0.4.282 — q46 → D and #761 steps 1-2: the fence drops, and the fork-only boundary takes its first durable shape

Bundles **`957c5003`** + **`31f8f394`** (HQ law), **`9637cdb9`** (the fence's tool half), **`be40ae00`** (#761 steps 1-2), **`09e30956`** (battery receipt sweep). The range also carries Toolsmith's **#739** pair, which landed inside this window: **`230dfb9d`** — `fix(tools): oc-vendor-drift and oc-claims-single-source wrote no unified-log row at all` (the `exec python3` replacing the shell image, so the documented `trap … EXIT` could never fire; 5 files, +427/−2) — and its receipt sweep **`b2854ce5`**.

Two owner rulings land together, and they are one story read from both ends: the fence that held harvests behind a quiet lane is **gone**, and the register that declares what is *deliberately* fork-only finally has fields worth declaring.

**q46 → D — the In-Flight Lane Fence is DROPPED.** The fence (v0.4.187, cycle `20260915-c18`) was built to stop a port capturing a **MOVING TARGET**, but its release clause was a **COMPLETION** condition ("finishes, hot-swaps, and lands") with nothing for a lane that simply *stopped* — and its busy set is `get_active_claims`, whose own docstring reads *"Every still-OPEN claim"* (`tools/lib/oc_claims.py:777`). A lane that claims and goes quiet therefore held the fence **indefinitely**, which is exactly the defect the owner named. His answer replaces the fence with the **portability predicate alone**.

The residual is disclosed, not papered over: the two guards ask **different axes** — the predicate asks *does upstream carry the surface this fix repairs*, the fence asked *is a lane still moving this subsystem*. So a harvest may now run against a subsystem an active lane is still changing; re-introduction needs a **fresh owner ruling**, never a lane's judgment. Recorded in the tool tombstone, in RC-CONTRACT row 34, and in both law copies.

The fence had **two live law copies** — `harvest.md:317` and `upstream-merge-runbook.md:336` — and both were retired **in place**; a clause the corpus carries twice is a clause that gets half-removed. `31f8f394` then scoped the drop: `upstream-merge-runbook.md` had declared the fence dropped while, further down the same file, the **census's** own `HELD_IN_FLIGHT_LANE` leg was still live and described as one of four independent fences — a reader of the first passage would conclude no in-flight fence exists anywhere. The census leg is **UNTOUCHED** and parked as **q51**.

**#761 steps 1-2 — the fork-only boundary takes shape.** q48 → **A** and q49 → **C** converge on **one field**, which is why they are one design: the bar gate **writes** the `not-upstreamable` row it just decided; the fork-only register **reads** the same rows. The register already existed (`harvest-registry.json` → `manual_records`, 9 live `not-upstreamable` rows), and `harvest.md:416` forbids a parallel one verbatim — *"`manual_records` IS this field — formalise it, do not fork it"* — so `fork-only.json` was dropped and the existing marker was extended instead.

| leg | change |
|---|---|
| **Row schema** (#761 step 1) | three **OPTIONAL** `not-upstreamable` fields — `branches`, `revert`, `verified_at`. Absent unless supplied, so the **61 pre-existing rows keep their exact shape**; they join the carry-forward set so a re-record never drops them |
| **Row identity** (#733) | identity is the **`unit`**, never `(unit, pr, issue)`: `manual_record_matches()` matches on unit **OR** issue, so the triple invented a second identity and an `--issue`-less re-record **appended a permanent duplicate** (purge refuses by design). Unit **725** was the live corpse |
| **Parent provenance** (#633) | `issue_subject_upstream` now asks about the declarations the parent **ADDED**, never the enclosing function of its hunks — a parent working inside a shared container used to read "already harvested" while its own feature was absent upstream |
| **Predicate** (#761 step 2b, #758) | new `fork_only_surface_references` — **declaration-level, not name-level**. Refuses a hunk whose body depends on a declaration the fork carries and upstream does not: `[FORK_ONLY_SURFACE: <path> :: <names>]`. Four narrowings: unit-scoped, self-introduced declarations excluded, test paths skipped, absent-upstream files left to class 2 |
| **Discoverability** (#730) | `record --help` now lists `--status` / `--reason` / `--branches` / `--revert` / `--verified-at`, so the only path to a `not-upstreamable` row is no longer undiscoverable |

**Verification (all same-turn reads).** Round-trip against a **copy** of the live registry: `record --unit TESTUNIT --status not-upstreamable --branches b1,b2 --revert … --verified-at …` → the row carries `branches: ["b1","b2"]`, the revert recipe and the timestamp, **rc=0**. A re-record supplying **none** of them said **"Updated"**, not "Recorded", left **1** row for that unit, and **carried all three forward** — the #733 append is fixed (61 → 61, no new row). Legacy shape intact: still **9** `not-upstreamable`, **0** rows carrying the new fields. Census selftest **108/108 OK** rc=0 · dispatch **53/53 OK** rc=0 · battery **PASS 324 / FAIL 0** rc=0 (wall 430 s, jobs=4) · #307 mutation guard **9/9 mutants caught**.

**Disclosed residual.** The 725 pair **persists** — the unit-key upsert updates the first matching row and the second stays, because removal is forbidden (`harvest.md:418`). The **append** bug is fixed; the legacy duplicate is not collapsible by design. The two existing rows stand as two revisions of one declaration.

| file | change | LOC |
|---|---|---:|
| `tools/harvest/oc-harvest-census` | row schema + identity + parent provenance + predicate | +525 / −22 |
| `tools/harvest/oc-harvest-dispatch` | Gate 2d removal (q46 → D) | +35 / −35 |
| `tools/tests/run.sh` | new battery case: the `record` round-trip through the shipped executable | +25 |
| `tools/tests/negctl-307-mutation-guard.sh` | the vacuous mutant replaced by one that reddens the positive control | +31 / −… |
| `tools/docs/RC-CONTRACT.md` | rows 33 (census) + 34 (dispatch) | +4 / −… |
| `harvest.md` | fence dropped, then scoped (2 lines) | +944 → +850 bytes |
| `upstream-merge-runbook.md` | fence dropped, then scoped (1 line) + census cross-reference | +368 → +671 bytes |

**Closed:** #633, #733 (with run receipts). **#758 was already CLOSED** at 11:04Z — its detection half landed in `86b7d149`, an ancestor — so nothing here re-closes it.

**Two corrections worth keeping.** (1) The **323 → 324** battery move needed a **battery-level** case, not census legs: `run_selftest` counts a whole tool selftest as **ONE** battery case, so census-internal legs can never move the total. (2) The first mutation-guard mutant was **VACUOUS, and it was measured** — `dep_decl_exclusion_dropped` gave rc=0 and 0 bad legs because each fixture's added line is a bare **call**, so the exclusion is a no-op; a mutant that reddens nothing proves nothing. Replaced with `dep_upstream_test_dropped`, proven to redden the pair's positive control first.

## v0.4.281 — q44 "combine: move + exempt": the register sheds role-scoped law, and is exempted from the budget

The owner answered `q44` with **"Combine: move + exempt"** — both halves, not a choice between them. `q44` existed because B-1's prescribed cure (move the `[LANE]`-tagged sections out) was a decision already reverted once, and re-executing it blind would have repeated a measured mistake.

**The move — `4057ad6a`.** Ten sections whose law binds **ONE role** were relocated byte-exact into the file that owns that role: `editor.md` ×6, `triage.md` ×2, `harvest.md` ×2. The split test is **BINDING SCOPE** — never the `[LANE]` citation tag, whose use as a scope marker was reverted on 2026-09-18 (`CHANGELOG.md:73`: *"citation is not scope"*; `[LANE]` is the must-read-at-reload marker). Two sections that *look* role-scoped **by name** were deliberately KEPT because they bind every lane: **§Attribution & Goal Hygiene** (77 lines) and **§Decision Rollcall** (46 lines). **§Swap-head signature** and **§HQ does not execute lane work** stay too — the 2026-09-19 tier-C pull-back restored them on purpose, and re-moving them would re-do a revert.

**The anchor sweep — the step the 2026-09-18 split omitted, and the reason it was reverted.** Relocating law without repointing its references leaves the corpus citing a section that is no longer there. Every in-corpus pointer to a moved section was corrected: **11 sites across 5 files**, three of them **inside the moved text itself** (`editor.md` → §Docs-Only LEG1 Gate Skip / §Post-Rewrite Swap Recovery; `triage.md` → §Owner-Dependent Smoke Legs L1, now repointed to `editor.md`). `reviews/**` (append-only reports) and `CHANGELOG.md` (history) were excluded by design.

**The exemption.** The register is now **explicitly exempt** from the 500-line law-file budget, recorded **beside the budget law itself** in §Upstream Coding & Testing Standards — not in a distant footnote. The exemption covers only what survives the relocation test; the relocation half is the enforceable half.

**Verification (all same-turn reads).** Register md5 pre-image `b99aef9991eae1cef75aecc519f3d590` (matches the recorded value). Heading reconciliation: 47 before → 10 moved → **37** after, with **34 kept byte-exact + 2 swept + 1 amended (the budget section) + 10 moved = 47** — no section lost. All 10 moved blocks present byte-exact in their targets (29,292 bytes relocated; 29,292 + 110,621 = 139,913 = the HEAD register's 138,229 + the separator newlines + the 1,457-byte exemption clause + the legend growth). `./tools/audit/oc-lint-laws` → **rc 0**, clean.

| file | before | after | delta |
|---|---:|---:|---:|
| `fleet-directives.md` | 732 | 540 | **−192** |
| `editor.md` | 660 | 761 | **+101** |
| `harvest.md` | 431 | 458 | **+27** |
| `triage.md` | 467 | 543 | **+76** |
| `upstream-merge-runbook.md` | 510 | 510 | 0 |
| `hq.md` | 274 | 274 | 0 |
| `toolsmith.md` | 165 | 165 | 0 |
| `SKILL.md` | 499 | 499 | 0 |
| **TOTAL** | **3738** | **3750** | **+12** |

The **+12** is honest and expected: each of the 10 relocated blocks gains one separator newline, and the register gains the exemption clause while losing the stale "2026-09-18 split" legend. The move is a **relocation**, not a reduction — the corpus carries the same law.

## v0.4.280 — the stranded-law batch: four brain-scrub findings land where lanes actually read

Bundles **`c954d711`** (BS-5, the law edit), **`3479ac77`** (this bump + entry), and two commits that landed inside the sync window: **`b7c7024a`** — `fix(tools): use <<< in the #741 --label selftest leg` (Toolsmith's fix for the `printf|grep -q` site that reddened the battery gate and held this sync at `die 5`) — and **`0328902a`** — `law(changelog): v0.4.279 names the two bundled Toolsmith commits (C8)`. Plus four live brain-file edits that carry no commit (the profile root is not a git repo): `AGENTS.md` ×3 (BS-1, BS-3, BS-8) and `INTEGRATIONS.md` ×1 (BS-4). Second half of the c27 §3.4 bucket; v0.4.279 landed the first half.

These are the **brain-scrub** findings — law sitting in the passive store (`MEMORY.md`, reached only through `memory_search`, never auto-injected) with **zero copies on any surface a lane actually reads**. A rule nobody loads is not a rule.

| ID | Landed at | What moved |
|---|---|---|
| **BS-3** | `AGENTS.md` hard rule 8 | an issue number enters a report ONLY copied from the `gh issue create` stdout URL **in the same turn** — never reconstructed from "the next free number". Sharpened onto the always-loaded rule that already forbade hand-assembled identifiers. |
| **BS-4** | `INTEGRATIONS.md` §`[Gatus]` alerts | a **LOAD-only** host-diag failure on the 1-core/961 MB box is **fleet self-load until proven otherwise** — check disk/mem, then `ps` the fleet, do NOT kill work in flight. Both 2026-09-10/11 recurrences carried the same shape. |
| **BS-5** | `triage.md` §Retired Duties & Forwarding Pointers | the **ai-antispam Outreach lane retirement** (owner order 2026-09-12) — send it no board traffic; and the trap that its roster label is shared with a live lane, so read the TOPIC, not the label. |
| **BS-8** | `AGENTS.md` rules index | **a mutual dangling pointer, fixed on both sides.** The index bullet pointed at *"register §Execution Discipline"* — a section that does not exist — while `fleet-directives.md:222` pointed back at *"the ops `AGENTS.md` §Execution Discipline bullet"*. The bullet now names the home that is real: **§Hard rules above (rules 1–7)**. |

### Still open in the bucket, and why

| ID | Disposition |
|---|---|
| **B-1** | **Refused, with the measurement.** The prescribed cure (move the `[LANE]`-tagged sections out) regresses the 2026-09-18 split, which was reverted on measurement — *"citation is not scope"* (`CHANGELOG.md:1719`). `[LANE]` is the must-read-at-reload marker, so those sections are exactly what the always-loaded register exists to carry. The budget question is **registered as open question `q44`** rather than re-executed blind. |
| **BS-2** | **Routed** — the WITHDRAW-vs-amend canon belongs to `skills/meta-factory/open-questions.md`, owned by the Open Questions instrument lane. Not this factory's file to edit. |
| **BS-6 / BS-7** | **Tool-gated, not deferred.** Both canons already exist at their correct homes (`skills/ai-antispam/SKILL.md:252`; `tools/docs/RC-CONTRACT.md:36`); the fix is *reducing* `MEMORY.md`, which is an append-only brain file whose cleanup requires an explicit owner tap (`cleanup_intent`). The rule is not missing — it is duplicated. |
| **A-16** | Corpus-state observation (the dirty tree at cycle open) — already recorded in the c27 verdict §5 as **C27-D2**. Not a defect in the corpus. |

### LOC delta (before → after, lines)

| File | Before | After | Δ |
|---|---|---|---|
| `SKILL.md` | 499 | 499 | +0 |
| `triage.md` | 466 | 467 | +1 |
| `AGENTS.md` | 129 | 129 | +0 |
| `INTEGRATIONS.md` | — | — | live file, edited in place |

## v0.4.279 — c27 deferred-findings batch: the phantom-flag refusals, the tool-table collapse, and the B-1 cure refused

Bundles **`76404b63`** (this batch) and **`7e1b281b`** (this bump), plus two Toolsmith commits that landed inside the sync window: **`84915e98`** — `fix(tools): retire oc-prchecks --label loudly` (#741) — and **`05945507`** — `law(tools): the oc-prchecks register row now states the detach's verdict relocation and the shared rc 8` (#742). Clears the bucket the c27 verdict parked under the header **"OWNER-GATED / next batch (accepted, not landed here)"** — a straight breach of the owner order of 2026-09-25 (`fleet-directives.md:94`, verbatim): *"findings are not wasted but fixed in their entirety. remove the human gate fro the duty 4 and 6 fixing process"*. Twelve findings landed; one refused with evidence.

### 1 · Three phantom refusals — the lens remedies prescribed tools that do not exist

Every c27 lens remedy names a tool or flag, so each was verified against the tree **before** it could enter law. Three failed:

| Remedy named | Measured | What landed instead |
|---|---|---|
| `oc-attrib --session <uuid>` (J-2) | **no `--session` flag** — `grep -nE '\-\-session' tools/state/oc-attrib` → rc 1 | the real interface: `oc-attrib --repo <path> --deployed` |
| `oc-upstream-delta --prs` (J-6) | **no `--prs` flag** — `grep -nE '\-\-prs' …` → rc 1 | `gh pr list --state open` (one call for the whole set) |
| `review.py schema` / `validate` (J-1) | **no such file in this tree** (finding I-1) | a REFUSAL with the reason stated + a ROUTE |

This is the **I-1 defect class repeating**: a remedy that prescribes a runner which is not there. Writing any of the three into law verbatim would have planted a verb that cannot execute — the exact failure c27 opened with. Each missing tool half is routed to Toolsmith with its finding ID rather than invented here.

### 2 · The landed findings

| ID | Site | Change |
|---|---|---|
| **J-2** | `fleet-directives.md:145` | the attribution guard RUNS `oc-attrib --repo <path> --deployed` instead of telling the lane to re-derive three sources by hand |
| **J-3** | `editor.md` + `fleet-directives.md` §W3 | checkout-ref verification is `tools/ship/oc-job-verify <run-id> <source-ref>`, rc 4 = identity reported but never trusted |
| **J-4** | `harvest.md` | fault-scope test is `oc-pr-fault-scope <pr#> --run <run-id>` — rc 0 IN-SCOPE / rc 1 BASE-FAULT (do NOT ping) |
| **J-5** | `editor.md` | trailer-block verification is `oc-attrib --repo <path> --trailers-only --range <A..B>`; a hand-rolled `git interpret-trailers` parse was agent-memory-as-gate-input |
| **J-6** | `triage.md` | one `gh pr list` for the whole census set, not a per-PR `gh pr view` loop |
| **J-1** | `hq.md` | key-set closure stays an explicit hand assertion, with its reason stated (no instrument here carries it) |
| **G-9** | `triage.md` | nine `###` patrol headings under `## Duty T4` — cohesion first, no split |
| **G-10** | `editor.md` | the completion criterion carries the checkable formula label |
| **I-3** | `review-lenses.md` | lens A's ref scope now covers every cross-repo pointer, resolved against its declared home |
| **I-6** | `review-lenses.md` | the accuracy record cites a locator that exists (`workers-ledger.json` retraction/rejection rows) |
| **B-2 / B-3** | `SKILL.md` | seven over-long tool-table rows collapsed to `tool — purpose` + the `tools/docs/RC-CONTRACT.md` register pointer |
| **BS-1** | `AGENTS.md` §Skill load | the stale five-file budget enumeration replaced by the register's canon: the budget binds the ONE brain file a session loads in full (`AGENTS.md`); the `CONTEXTUAL_BRAIN_FILES` cost nothing per session |

### 3 · B-1 — the prescribed cure is refused, with the measurement

B-1 (MAJOR) says `fleet-directives.md` at 732 L is +232 over the owner's 500-line budget, and prescribes: **move the `[LANE]`-tagged sections to a companion file**.

**That cure is a regression of a decision already made and reverted.** The 2026-09-18 split did exactly this, and the register records the reversal verbatim: *"The 2026-09-18 split demoted sections whose law in fact binds every lane; citation is not scope."* (`CHANGELOG.md:1719`). `[LANE]` is not a lane-scope marker — it is **the must-read-at-reload marker** (`CHANGELOG.md:1743`, `:3078`): the sections it tags are the ones every worker is required to read in full after compaction. Moving them out of the always-loaded register removes law from the only surface every lane provably reads.

The residue is genuine and is **routed to the owner as a budget decision**, not re-executed blind: either the register's 500-line budget gets an explicit exemption, or the demotion is re-attempted with the anchor sweep the revert proved was missing.

### 4 · LOC delta (before → after, lines)

| File | Before | After | Δ |
|---|---|---|---|
| `SKILL.md` | 499 | 499 | +0 |
| `editor.md` | 658 | 660 | +2 |
| `fleet-directives.md` | 732 | 732 | +0 |
| `harvest.md` | 430 | 431 | +1 |
| `hq.md` | 273 | 274 | +1 |
| `review-lenses.md` | 303 | 306 | +3 |
| `triage.md` | 453 | 466 | +13 |

`SKILL.md` stays inside its budget at 499; `fleet-directives.md` is unchanged (B-1 not landed — see §3).

## v0.4.278 — Duty-4/6 cycle c27: the phantom home, the dead tool names, and the biography purge

Duty-6 review cycle **`20261001-c27`**, opened 2026-10-01T07:09Z on a **FIRE** cadence (7 skill-bumps past boundary `n=12391`), corpus at `c00947eb`. Eleven lenses ran as isolated read-only sub-agents; `oc-review-persist check-cycle --strict-receipt` closed the census at **11 persisted / 0 waived / 0 unreceipted** (rc 0). **99 findings** — 2 BLOCKER · 30 MAJOR · 55 MINOR · 12 NIT. This entry carries the accepted findings landed in this batch, and every provenance token stripped out of live rule text by A-8/A-9/A-14.

### 1 · The phantom home — `tools/review.py` is not wired to this factory (I-1, BLOCKER)

`hq.md` §Duty 4 and §Duty 6 both carried a `MOVED 2026-09-27` carve naming **`tools/review.py`** as THE review executable. Measured: **that file does not exist in this skill tree**, and the real engine (`/root/agent-factories/tools/review.py`) hardcodes `REPO_ROOT = Path(__file__).resolve().parent.parent` to its own repo with **no env override** — it answers *"Cycle '20260927-c25' not found."* about a cycle sitting on disk here. The instrument's own adoption census reports this factory **`0/5 … ABSENT`**, and its lens catalog is 14 lenses / 6 families against our 11.

Both carves now carry a **`⚠ NOT OPERATIVE FOR THIS FACTORY`** banner naming the measured facts and the **operative carriers** — `tools/state/oc-review-persist` + its `check-cycle` gate, against the in-corpus catalog `review-lenses.md`. The pointer to `docs/instruments/review-rotation.md` is kept because the contract is real and lives elsewhere; its claim of a **wired** executable does not survive measurement. Same defect class as the `AGENTS.md` dead-path finding below.

### 2 · Dead tool names in live law (G-2, MAJOR)

`oc-harvest-tiers` **never shipped** — it is named in `triage.md` §Owns and in `upstream-merge-runbook.md` as a live tool. Both re-pointed at the tool that exists: `tools/harvest/oc-harvest-census`.

### 3 · Biography purged from live rule text (A-8, A-9, A-14)

Rule text carries **no biography** (`hq.md §Rule-text provenance`); every token below moved out of the rule surface and into this entry.

- **`upstream-merge-runbook.md` §Remotes & sync** — the 3,571-char paragraph cut to 2,108 chars of live rules. Stripped: `(renamed 2026-08-24, was inverted)` · `owner-approved transition 2026-09-11, plan "Fork Rebase Transition and Sync Workflow"` · `the 2026-09-02 "Land it" MERGE policy is RETIRED` · `the policy that produced 31 merge commits and a 333-commit phantom ahead count` · `history diverged by design 2026-08-26` · `historical: REBASE-PORT procedure (hq.md §Upstream sync — re-homed v0.4.80, lens B F3)` · `— this line updated per Duty-6 lens B, 2026-08-31` · `first offense logged vs this lane 01:55Z` · `pilots 87d3bcb8 11:33Z / 2d643146 12:57Z / 6643cf3c 14:32Z, events 1269/1275/1281` · `ex-ROLE_EXCEPTION` · `since v0.4.38 (2026-08-29)` · `moved off 2026-08-26` · `(3349cf7e, 2026-08-27)` · `commit e71dba58` · `removed 2026-08-31` · `**S3 LIVE 2026-08-28**` · `(deploy consent ELIMINATED owner 2026-08-28 18:50Z)`. The live rules (REBASE model, `--force-with-lease` + pre-cutover sha recorded first, merged ≠ deployed, FREEZE, detection-only `ls-remote`, forbidden direct `gh workflow run`, full-40-char-sha dispatch, carrier ORDER gates, ledger canonical path) are unchanged in substance.
- **`editor.md` §Smoke-verdict rules** — dropped `(moved from SKILL.md §Test ontology, v0.4.262)` and the whole *"Re-homed by cycle `20260925-c24` lens B (B-H2)…"* paragraph.
- **`editor.md` §Red-run triage heuristics** — heading provenance dropped; the self-contradicting *"moved here from editor.md Phase 6"* note (A-14) removed with it.
- **`environment.md` prologue** — dropped the *"Re-homed from `SKILL.md §Shared environment facts` by cycle `20260925-c24` lens B (B-H2): the always-loaded router carried 103 lines…"* paragraph.
- **`SKILL.md` §Shared environment facts** — dropped `(Duty-6 c25 B-9: three cargo-ban homes inside SKILL.md alone)`.
- **`hq.md` §Duty 6** — `- **KEY-SET CLOSURE STAYS HERE (Duty-6 c25 I-7, measured 2026-09-27).**` → `- **KEY-SET CLOSURE STAYS HERE.**`

### 4 · Duplicate rules collapsed (A-2 · A-3 · A-4/A-5 · A-7 · A-15)

- **A-4/A-5 (BLOCKER + MAJOR)** — the smoke-verdict rules were written out **three times** in `editor.md` (*"Behavioral probe is the smoke PASS GATE"*, *"Corrected-code presence ≠ smoke success"*, *"Bookkeeping legs ≠ smoke PASS"*), and the PARK rule **twice**. Collapsed to ONE merged rule — **`Presence and bookkeeping legs are never a smoke PASS`** — plus one PARK copy. The surviving reference at `editor.md` was re-pointed to the merged heading. This also discharged **G-5** (the circular `(full rule: editor.md Phase 6)` self-pointer) and **G-6** (the `b` phase suffix, swept to `Phase 6` across five files, 15 sites).
- **A-7** — soak-inheritance duplicated in `harvest.md`; the copy replaced by a pointer, `upstream-merge-runbook.md` §Upstream-merge cadence remains the single home.
- **A-2 / A-3** — the *"land every accepted proposal in its entirety"* landing rule and the Duty-4/6 cadence trigger each stated twice in `hq.md`; collapsed to one home each.
- **A-15** — the MODE-resolution `--n` warning de-duplicated: `harvest.md` step 0a keeps the invocation + a fail-closed pointer; the resolution law stays at `SKILL.md §Hard rules — MODE REGISTER`.

### 5 · Reference integrity (A-10 · A-11 · B-4 · B-8 · G-4 · G-12 · I-2)

- **I-2 (MAJOR)** — `review-lenses.md` carried **five dead `hq.md §Duty 6` method references** (unfixed from c26); all re-pointed at the real homes (`review-lenses.md`'s own lens list, `tools/state/oc-review-persist check-cycle`, `hq.md §Cadence boundary is stamped at review consolidation`).
- **A-10 / A-11** — the catalog prologue now names the method home correctly, and the CORPUS clause defers to `oc-review-persist check-cycle` instead of `hq.md §Duty 6 step 0`.
- **B-4 (MAJOR)** — the dead `canon: docs/instruments/open-questions.md` path annotated **in the meta-factory repo (`/root/agent-factories/`) — NOT resolvable from this skill tree** at `SKILL.md` and `triage.md`.
- **B-8** — the two unresolvable `row 36` / `row 49` citations into `RC-CONTRACT.md` replaced by the tool names they actually key (`oc-issue-dispatch`, `oc-questions`).
- **G-4** — the `toolsmith.md` stale line-number anchor `editor.md:69` replaced by a section anchor.
- **G-12** — the wrong-duty cross-reference `triage.md §Duty T7` corrected to the real Triage upstream-patrol home.

### 6 · One concept, one name (A-6 · A-13 · A-17)

- **A-6** — the smoke rubric is **`4-Leg Smoke Rubric`**; the `4-leg rubric` / `four-leg rubric` / `behavioral rubric` variants are gone from 11 sites across five files.
- **A-13** — `FIRE` was overloaded: it is the **release window**, while the Duties-4+6 threshold verdict is a **distinct** concept emitted as **`CADENCE-FIRE`** (tool-side rename is a Toolsmith follow-up; until it lands, a bare `FIRE` in cadence output means the threshold verdict).
- **A-17** — retired concepts marked with their retirement: `Harvester role RETIRED v0.4.176`, `Compiler role RETIRED 2026-08-28` (three sites).

### 7 · Structure (B-6 · B-7 · G-1 · G-7 · G-8 · G-10 · G-11)

- **B-6** — the five role-scope bullets restating one shape became a **Lane / Owns / NEVER** table.
- **B-7** — the self-negating prohibition at `hq.md` dropped.
- **G-1** — `## Retired Duties & Forwarding Pointers` moved out of `## Escalation to HQ`.
- **G-7** — the five role-file prologues normalized to one order (load-gate line first).
- **G-8** — the five top-level Phase-7 reference sections in `harvest.md` demoted under `## Phase 7 Reference Rules`.
- **G-10** — every completion criterion now reads `**Checkable Completion Formula**` (8 sites in `editor.md`).
- **G-11** — `### Related Triage operations` promoted out of the `## Duty 7 — RETIRED` block.

### 8 · Duty-5 ruling recorded (not law — ledger)

Cycle-time ruling: **base-repair ownership is NOT a standing Triage duty** — the pre-claim law binds as written (carry a sweep commit in the PR itself). The owner's *"Delegate the #725 base fix to Triage"* is a **one-off for #725**. Amended the same hour: the #725 filing count in the first ruling was **wrong** — it is **ZERO PRs owed, zero filed**, because upstream carries the surface pool-free by design and the fork's variant is the inferior one. Both recorded as `rulings` events (`n=13968`, `n=13972`).

### 9 · Also measured this cycle

- **Duty-4 intake: EMPTY** — a named state, not a pass. `proposals/` held 0 files; the newest ledger `kind=proposal` row (`n=12310`) predates the boundary. The poll wave (`d202fce6cb2b`) **never delivered** — `oc-notify-fanout` wedged on its first target for ~25 min in quiet mode (defect routed to Toolsmith).
- **Corpus was NOT clean at open** — ` M tools/harvest/oc-prchecks`, an in-flight foreign lane's edit. Not touched, not staged.
- **Lens H disclosed its own accidental write** — `oc-ledger sweep-closed-claims` without `--dry-run` minted 3 `unclaim` rows; all three issues were genuinely CLOSED, so no false row was created.

### LOC delta (mandatory per the law)

- `editor.md`: **686 → 658** (−28; the three-way smoke-rule duplication and the biography sediment)
- `SKILL.md`: **497 → 499** (+2; still under the 500 budget)
- `hq.md`: **267 → 273** (+6)
- `upstream-merge-runbook.md`: **498 → 510** (+12; biography out, live rules given paragraph breaks)
- `environment.md`: **152 → 149** (−3)
- `triage.md`: **454 → 453** (−1)
- `review-lenses.md`: **303 → 303** · `toolsmith.md`: **165 → 165** · `harvest.md`: **430 → 430** · `fleet-directives.md`: **732 → 732** (unchanged; the 732-line overage against the 500-line budget is a **next-batch** unit — a bad split of the always-loaded register breaks every session)

### Bundled commits (C8)

- `c00947eb` — law(changelog): v0.4.277 names its bundled commit (C8) + records the sync
- `c4541928` — fix(tools): oc-prchecks `--wait` detaches into its own named scope (#727)
- `da646070` — fix(tools): oc-commit `--session-id-only` — the escape from mandatory Issue-Ref derivation (#728)

**Synced:** bump to **0.4.278** (ledger event `n=13976`) covering Duty-4/6 cycle `20261001-c27`. The tag also carries the **Toolsmith lane's** `#727`/`#728` batch, which landed between the cycle boundary and this sync — named here because the version record is the only place a bundled fix's ship date exists.

## v0.4.277 — all fork CI lives on the carrier branch

Owner correction, 2026-10-01T01:11:29Z, in the OC DEV HQ topic, after an HQ answer had offered him a choice between "repairing" and "deleting" `main`'s `ci.yml`: *"You probably forgot that the forks ci files live on a special branch"* — then, at 01:13:51Z: *"Shouldn't this fact be on our law?"*

### 1 · The fact, at `environment.md` (beside the carrier clause)

The carrier clause stated this for **one file** — `quick-build-linux.yml`. The general fact was uncodified, and its absence produced a wrong ruling: HQ read `main`'s `ci.yml` as the fork's own CI, measured its runs, and offered the owner a repair-or-delete choice — when that file is **upstream's**, and editing it is divergence that conflicts on every upstream sync.

The law now carries the whole shape. `origin/main` holds exactly `auto-assign.yml` `ci.yml` `prerelease.yml` `release.yml` — upstream's files. The fork's OWN CI — `pr-checks.yml` (the PR-lane gate), `ci-lane-impl.yml` and `quick-build-linux.yml` (the carrier build) — exists **only** on `ci/quick-build-linux`. `main`'s `ci.yml` is **byte-identical to upstream's** (`git diff adolfousier/main origin/main -- .github/workflows/ci.yml` empty) and its jobs resolve `self-hosted` on a push, since the ternary yields `ubuntu-latest` only for a fork PR; the fork has **0 registered self-hosted runners**, so every main-push run queues indefinitely and the next push cancels it — **0 success / 58 cancelled** since 2026-09-14, the newest `pending` on the `a85740948` push.

**Consequence, now stated: fork `main` has NO post-merge CI net, by design** — the CI files moved off `main` on 2026-08-26 (Alexey's call, mirroring upstream dropping them from theirs). The PRE-merge PR-lane gate (`oc-ship-chain` LEG1) is the **only** gate, and the only thing between a red commit and the carrier build. The rule closes with the operational half: **never read `main`'s workflow files as evidence about the fork's CI, and never "repair" them.**

### 2 · Discoverability, at `SKILL.md` §Shared environment facts

The always-loaded router listed "the carrier/feature-set/dispatch rules" without naming this one, so the fact was reachable only by loading `environment.md`. The routing sentence now names it in place.

### LOC delta (mandatory per the law)

- `environment.md`: **136 → 152** lines (new bullet, +16).
- `SKILL.md`: **495 → 497** lines (+2; the routing sentence only — still under the 500 budget).
- `CHANGELOG.md`: this entry.

### Bundled commits (C8)

- `35847c18` — fix(tools): oc-ledger selftest --help was dead code behind the global parser (#722)

**Synced:** catch-up to **0.4.277** (ledger event n=13940), the single bump covering v0.4.275–v0.4.277.


## v0.4.276 — the design gate must ask for the simplest shape

Owner rebuke, 2026-09-30T23:34:13Z, in the #724 lane's own topic, on that lane's first design: *"You forgot to apply our design principles - kiss and ponytail"*.

### 1 · The clause, at `fleet-directives.md` §Discussion links + fix-approval gate, item 2

Item 2 required the design in **canonical terms** and **with a Mermaid diagram**, and said **nothing about the simplest shape** — so a design could satisfy it completely and still reach the owner over-built. That is what happened: #724's first design arrived as three options with a recommended default (Option A — a table-driven declared-effect walk) and the owner's first response was the rebuke above.

The principles were already canon — `CODE.md` §Design Principles (KISS · YAGNI · JTBD) and the lazy ladder in `skills/ponytail/SKILL.md` — but **on demand**: nothing in the gate made a designing lane walk them. Item 2 now requires the design to carry its **simplicity justification** — which rungs were rejected and why — under the **same treatment as the diagram**: a design presented without it is not presented.

### LOC delta (mandatory per the law)

- `fleet-directives.md`: **732 → 732** lines (1 insertion / 1 deletion — the 757-char clause rides inside item 2's existing paragraph, so no new line).
- `CHANGELOG.md`: this entry.

Doc-first: the bump and sync are deferred to the next cycle — this entry and v0.4.275 both sit above v0.4.274 until then.

## v0.4.275 — a PR must say why the change is needed

Owner order, 2026-09-30T22:48:43Z (relayed by the harvest lane, recorded `n=13833`), verbatim: *"It's imperative for a PR to carry the value and necessity of the change. Why do the users need it? What is the job to be done? You should refuse PRs if this is not clear to you from the issues."*

### 1 · The rule, at `harvest.md` §Phase 7 step 0a (beside the n=13767 summary clause)

The PR body must carry, **in the user's terms**, *why the users need it* and *what the job to be done is* — a **named section**, not a phrase in passing. Enforcement is **two-tier**, because the halves cost differently: **presence** is mechanical (the body carries the section), while **sufficiency** is a lane judgment that **cannot be mechanised** — a heading plus *"improves reliability"* passes any grep and is **worse than no section**, because it launders a weak change as a valuable one. This is the same law the smoke verdicts already run on: **presence is not behaviour**. So the refusal trigger is **"the stated value is unfalsifiable"**, never *"I am not convinced"* — unfalsifiable is decidable, unclear is not.

**A corrective-change carve-out binds.** A `fix(...)` unit's value is **subtractive**: nothing new appears, something false stops appearing (`#680` is the specimen — it stops a diagnostic naming the wrong cause). For those, the necessity **is** the defect and the falseness it removes; inventing user-facing value for a change that has none inverts the rule's intent.

**The precondition is an issue-side property.** When the issue does not state the job to be done, the right act is to **fix the issue**, not to compose prose at PR time. Measured by the harvest lane the same turn: the fork has **no `.github/ISSUE_TEMPLATE/`** (`.github/` carries only `CODEOWNERS` and `workflows/`), so a value section is a **convention**, not a template product, and nothing makes it self-correct — **4 of 12** sampled open issues carry one (720, 719, 710, 709), **8 do not**. The issue-side repair is **Triage's** work item; the refusal must not land on the filing lane for a defect it did not cause.

### LOC delta (mandatory per the law)

- `harvest.md`: **402 → 430** lines (+28), all inside the §Phase 7 step 0a comment block.
- `CHANGELOG.md`: this entry.

Doc-first: the bump and sync are deferred to the next cycle (the entry above v0.4.274 sits unshipped until then).

## v0.4.274 — the absorb that would silently kill the factory's backbone

Triage raised a **landmine for the next upstream absorb**, verified at source this turn rather than relayed: upstream **#1802** (`40a28f7bd`, Adolfo, 2026-09-29T16:50Z) turns `session_notify` into a **kill switch that DEFAULTS OFF**. `[agent] session_notify_enabled` is `#[serde(default)]` and its `Default` impl sets it **false**; when false the tool refuses every action, the A2A `session/notify` method refuses, and `opencrabs session notify` exits 4. The field's own doc comment calls it deliberate — *"an unprompted channel into another session's context breaks session isolation"*, post-mortem #1203/#1207 — so it is a sound upstream default that is **fatal to this fork's operating model**: `session_notify` is the backbone every dispatch, lane report and cross-lane tell rides.

**Absent from the fork, and unpresentable — both verified.** `git merge-base --is-ancestor 40a28f7bd origin/main` → rc 1, and `grep -rn session_notify_enabled src/` over the fork returns **0 lines**: the struct does not carry the field, so `config_manager write_config agent session_notify_enabled true` is **hard-denied** *against the running binary* ("unknown config path … the Config struct has no such section or key … would create a key serde ignores"), and equally denied for the absorbed build until it lands. This is why the fix **cannot be pre-staged**: the key must be written in the window between the swap that introduces it and the first cross-lane notify that needs it.

### 1 · Config-migration gate added to the sync gates (`upstream-merge-runbook.md`)

`## Gates (fail closed)` gains a **fourth gate** — a key the FORK binary cannot parse yet MUST be written (`config_manager`) in **every live profile** AT SWAP TIME, never before, naming #1802's key as the worked case. Three profiles are live on this box and each carries a `config.toml`: `ops`, `family`, and the **root default** — the gate says every live profile because the omission on any one of them is a silent death of that profile's fan-out.

The gate is written into the runbook's own gate list rather than the register for two reasons: it **is** a sync gate, sitting beside the three it joins; and the register measures **732 lines** against the 500-line law-file budget, so new law is placed in its operational home rather than growing the overage.

### Why this is a gate and not a chore

The failure mode is **not** a refusal that announces itself. An unwritten key does not error at swap: the swap goes GREEN, the daemon starts, and the first cross-lane dispatch **silently returns** — the factory loses its backbone with no failing signal anywhere. The gate exists because the absence is indistinguishable from calm.

### 2 · State measured while landing it (both shas read, neither inferred)

- **#714 is landed on fork main and UNSHIPPED.** `ac4df8acf` + `89945b5a3` are on `origin/main` (`89945b5a3` = HEAD), while `deployed.sha` = **`c6c7cc45`** (swapped 2026-09-30T13:29:42Z, `prev_sha 68cd5fdf`), which predates them. So the unconditional pre-migration snapshot fix is **written but not running** — an editor ship matter, recorded here because the disk it would relieve is the same disk the sync and the battery must write to.
- **A queued "deployed.sha is ABSENT" alert was scoped to another lane's chain, not this one.** Settled by locating the canonical state dir (`$HOME/.opencrabs/profiles/ops/opencrabs-dev/`, `oc-deploy:196`): `deployed.sha` exists and is readable there. A state claim read from the wrong scope is not a state.

### Bump and sync — two blockers measured, both since cleared (v0.4.272–274 land in one catch-up sync)

1. **`tools/tests/run.sh` is dirty** with the Toolsmith's in-flight #720 cgroup-isolation work (**224 lines**, +223/-7). The sync's **stray-guard** (`oc-ledger:1313-1334`, v0.4.157) dies **rc 7** rather than sweep another actor's work into a bump commit — the same guard that correctly refused my v0.4.270 bump while the Toolsmith held an uncommitted `oc-ledger`.
2. **The battery receipt is aged out.** `battery-last.json` reads **PASS 296 / 0 fail, 2026-09-30T14:11:15Z** — **5.98 h** at read time against the gate's **6 h** ceiling (`oc-ledger:1230-1237`), i.e. it expires within the minute. A sync would die **rc 5**.

A fresh battery is **not** run here: the `opencrabs-ops` cgroup measured **1596493824 / 1610612736 = 99.12 %** with `MemoryHigh == MemoryMax` and `memory.oom.group=1`, so a 4-job parallel battery is exactly the allocation spike that takes the **whole group** — daemon plus every lane's in-flight turn — and it would run through the Toolsmith's **uncommitted** harness besides. Committing doc-first keeps the repo out of the "bumped but never synced" state v0.4.269 sat in for a day.

**Both blockers cleared before this sync ran, each re-measured rather than assumed.** (1) The Toolsmith committed its work — `4047491a` (#720, the battery's transient-scope re-exec) and `510dae7e` (#722, `oc-ledger commit-pending --help` no longer sweeps and pushes) — so the stray-guard's subject is gone and the worktree carries no non-exempt dirty path. (2) The battery receipt was **re-run at 2026-09-30T21:18:19Z: PASS 309 / 0 fail**, `cgroup_isolated: true`, `tree_changed: false` — **321 s** wall at `jobs=4` under a transient scope, so the parallel battery no longer runs inside the ops cgroup the OOM section above describes. Both reads are from the same turn that ran the sync, and the bump is a **catch-up** (`--catch-up`, three versions 0.4.272→0.4.274) because the doc-first entries for all three were written while the blockers stood.

### LOC delta (mandatory per the law)

| file | before | after | Δ |
|---|---:|---:|---:|
| `upstream-merge-runbook.md` | 496 | 498 | **+2** |

Law corpus (`*.md`, git-tracked, counted in python from `HEAD` to the working tree): **17283 → 17323 (+40)**, of which **+2** is the runbook clause and **+38** this entry's own growth (biography, not rule text). `oc-lint-laws` rc=0 (clean). No other law file touched.

**Bundled and named (C8), this window since `cd708a28` (v0.4.271):** `ed4db066` · `2e10e1fe` (v0.4.272, worktree paths) · `b3ad3571` · `93181c6c` · `e04db728` · `3a65fda6` (v0.4.273) · `3c447ca7` (this entry's own doc-first commit) · `4047491a` + `510dae7e` (Toolsmith — [#720](https://github.com/leshchenko1979/opencrabs/issues/720) the battery re-execs into a transient scope; [#722](https://github.com/leshchenko1979/opencrabs/issues/722) `oc-ledger commit-pending --help` no longer sweeps and pushes) — all named here or in the entries above, so this entry adds no unnamed commit to the window.

## v0.4.273 — two owner orders, and a safeguard that only looked removed

Two owner orders landed on the law surface the same hour, plus the q34 answer that had been waiting since morning. **Bump and sync are DEFERRED**: the battery receipt on disk is `2026-09-29T12:36:05Z` — ~23 h old, where the sync gate demands <6 h — and the `opencrabs-ops` cgroup was measured at **99.93 % of its 1536 MiB cap with 1.1 MiB headroom** under `oom.group=1`, so a 4-job parallel battery now risks triggering the whole-group OOM it would be measuring under. Committing doc-first keeps the repo out of the "bumped but never synced" state v0.4.269 sat in for a day. **Resolved at the v0.4.274 catch-up:** the battery was re-run to **PASS 309 / 0** at `2026-09-30T21:18:19Z` and the Toolsmith's dirty `run.sh` was committed (`4047491a`, `510dae7e`), so v0.4.272–274 published together in one catch-up sync.

### 1 · Issue provenance — blame it, follow it, explain it (owner order 2026-09-30)

Owner, verbatim: *"while exploring and validating a new issue, the editor should blame it, see connected issues and PRs and understand why the code was introduced in the first place."*

`editor.md §Phase 3` (the explore-before-writing phase, which already carried the symbol-graph and DRY mandates) gains **step 6**; `fleet-directives.md` carries the binding `[LANE]` mention, since the order governs the investigation and not only the editor's procedure. Three legs: blame to the **INTRODUCING** commit and read its **body**, not just its diff; follow the issues and PRs that commit cites; state **why** the code was introduced before proposing a change.

**The failure this order was written against, and why the third leg is the load-bearing one.** The rationale for a guard, cap or band lives in the commit body, the doc comment or the cited issue — **never in the numbers alone**. Measured the same morning: the `MemoryHigh == MemoryMax` collapse in the ops drop-in reads like a **deleted safeguard** (a 256 MiB throttle band removed), and a lane proposed restoring it; the drop-in's own comment says it is a **deliberate trade** — *"high == max so the unit OOMs instead of sitting in `mem_cgroup_handle_over_high`"* — against a SIGBUS crash-loop (#411, #638). Restoring the band would have re-armed the crash. The numbers made it look wrong; only the rationale said it was right.

Two traps recorded inline, both of which bit this box inside 24 h:
- **`gh` inside `/root/opencrabs` defaults to UPSTREAM**, where the same number is a **different** issue. Scoping `-R leshchenko1979/opencrabs` is mandatory. Measured: fork #714 is *"pre-migration snapshot guard runs on every CLI invocation"*; upstream #714 is *"config_manager write paths don't re-validate before fs::write"* — a lane read the wrong one and attributed the snapshot defect to upstream.
- **An issue TITLE is a claim, not a finding.** A stale-open issue asserting an unfixed defect makes the next lane re-implement landed work: #394 was fully fixed on main yet titled *"two hot write paths still unwrapped"*, and a plan was composed against it a day after the fix landed.

### 2 · The filing ask carries a summary, not a number list (owner order 2026-09-30T11:38Z)

Owner, verbatim (topic "Upstream: Harvest"): *"every time you are asking about the upstream approval, you need to give summary - what the changes are about."*

Under DEGRADED mode `harvest.md` step 0a prescribed the **form** of the approval ask (owner word in the lane topic) and its **record** (a stamped `FILING APPROVED` row) but said nothing about its **content**, so the asks went out as unit numbers plus gate and census receipts: the owner was asked to approve a filing without being told what any of it does. His own reply is the evidence — *"what is 225 about?"* (2026-09-27).

Step 0a now requires, **per unit in the group**, one sentence of DEFECT and one sentence of FIX in the user's terms. Links and gate evidence **accompany** it; they do not replace it. Boundaries are written into the clause so it cannot be over-read: it binds the **filing ask only** (status reports, handoffs and inter-lane notifies unchanged), it adds **no new gate and no second approval**, and it is **not a licence to bundle** — one issue per PR still binds, and the summary describes each unit separately.

**Home is `harvest.md`, not the register** — this is the harvest role's own filing procedure, the same home step 0a already has, and the register measures **732 lines** against the 500-line law-file budget. Not duplicated.

### 3 · q34 answered — leg (i) reads the issue BODY too (`b3ad3571`)

The owner answered opencrabs-dev **q34** (*"Design-gate backstop: should the predicate read the issue BODY?"*) with **"A — widen leg (i) to the body"**. `triage.md`'s design-gate backstop leg (i) now counts a declaration in the **issue body** as a third channel beside the first-comment body and any claim row.

The asymmetry was the tell, one bullet above: the **ROOT leg** already ended *"A lane that declares its root in the BODY is equally compliant"*, while leg (i) read only comments and claim rows — the stricter of two legs of the same backstop for no stated reason. The mechanism the leg already documents for comments applies: the body is the natural place a lane writes its validation note when the issue was filed by someone else, and the **only** channel on an issue that already carries a design comment (a retroactive declaration cannot be the FIRST comment).

### LOC delta (mandatory per the law)

| file | before | after | Δ |
|---|---:|---:|---:|
| `editor.md` | 680 | 686 | **+6** |
| `fleet-directives.md` | 728 | 732 | **+4** |
| `harvest.md` | 393 | 402 | **+9** |
| `triage.md` | 454 | 454 | **0** |
| `SKILL.md` | 496 | 496 | **0** |

Law corpus (`*.md`, counted in python from `cd708a28` to the working tree): **7582 → 7625 (+43)**, of which **+19** is the four law files above and the remainder is this CHANGELOG's own growth (the biography, not rule text). `oc-lint-laws` rc=0 (clean) on every commit.

**Bundled and named (C8), this window:** `b3ad3571` (this lane — the q34 design-gate widening) · `93181c6c` (this lane — the provenance law) · `e04db728` (this lane — the harvest filing-ask law) · `2e10e1fe` (this lane — the v0.4.272 entry commit). All four carry **no prior naming line** in this file (grep-verified 0 hits each) and are named here rather than left as a C8 gap.

## v0.4.272 — the law mounted worktrees where the tool no longer puts them

Raised by the disk-cleanup actor (`cli`) and verified at source before a line was written: `editor.md` told every lane to mount its worktree at `~/oc-wt-<task>`, while `tools/git/oc-wt` creates at `~/opencrabs-wt/<task>`.

**The template named a path that exists for NO task.** `oc-wt` resolves a task through `lib/oc-wt-resolve.sh` — a **3-name ladder**: `$WT_BASE/<task>`, then `$WT_BASE/oc-wt-<task>`, then the **legacy** `$HOME/oc-wt-<task>` — so the doc's shape was the ladder's legacy arm, and a **fresh** task's `add` falls through to `$WT_BASE/<task>` = `$HOME/opencrabs-wt/<task>`. Measured at the ruling instant: `/root/oc-wt-*` holds **0** trees while `/root/opencrabs-wt/` holds **41**. So this was a **broken instruction**, not a stale example: a lane copying the template's `git -C ~/oc-wt-<task> push` ran git in a directory that does not exist.

**Blast radius, swept past the named file.** `editor.md` carried **13** template refs (the Phase 1 mount and DONE lines, the Phase 5 push, both exit-5 recovery blocks, the post-landing-lock ancestor re-check, the Phase 6-Fix re-push), `harvest.md` **2** (`git -C ~/oc-wt-up-<feature> cherry-pick` and `push -u`), and `SKILL.md`'s skill-activation **glob** `~/oc-wt-*/**` — the glob is why the class matters beyond prose: a lane working in a worktree could fall outside the skill's activation set entirely.

**Deliberately NOT changed, each for its own reason.** `tools/docs/HEALTH-CHECKS.md:34` and `HEALTH-CLASSES.md:83` still name `/root/oc-wt-*`, but `tools/docs/*.md` is the **Toolsmith's** surface (v0.4.87 carve-out) and the *tool* is already correct — `oc-health:42` sets `WT_PATTERNS` to `oc-work/* oc-wt-* opencrabs-wt/*` — so only the docs lag; routed to the Toolsmith, not edited here. `RC-CONTRACT.md:61,68` KEEP the legacy name because they document the resolver's ladder, where it is the third arm: "correcting" those would delete the fact. `war-stories.md` keeps its historical examples under its own stated contract ("history is reference, not procedure").

**The cleanup actor's move left the registry consistent** — verified, not assumed: `git worktree prune -n` prints nothing, so no tree was moved out from under its registration.

**Bundled and named (C8), this window:** `ed4db066` (this lane — the worktree-path correction at three surfaces) · `08c884c6` (Toolsmith — the `dirname('.')` walk-up fixpoint: every fleet tool hung on a relative invocation) · `c64009fa` (Toolsmith — `purge` REFUSED: removal of a `manual_records` entry is forbidden) · `a755907f` (Toolsmith — `oc-smoke`'s auto-stamp now addresses its issue) · `dd793945` (Toolsmith — `oc-issue-scope`: a path named as a defect's VICTIM is not the surface) · `02db1c7e` (the B3 runtime-artifacts sweep). The five Toolsmith/sweep rows landed inside the v0.4.270–271 window and carry **no naming line of their own** — grep-verified 0 hits each in this file — so they are named here rather than left as an unexplained C8 gap.

**LOC delta (owner order 2026-09-19):**

| File | Before | After | Delta |
|---|---|---|---|
| `editor.md` | 680 | 680 | 0 |
| `harvest.md` | 393 | 393 | 0 |
| `SKILL.md` | 496 | 496 | 0 |

Net **0** over the 8-file corpus (**3680 → 3680**): every edit is a same-line path replacement. `editor.md` (680) and `fleet-directives.md` (728) remain over the 500-line budget — pre-existing and recorded; this change neither causes nor worsens it. `oc-lint-laws` rc=0.

## v0.4.271 — the sync's test union kept a test that could not fail

Raised by the Triage lane while finishing the 2026-09-29 sync (origin/main `888decf7a` → `73ad3e969`), and verified first-hand before it was written. The runbook's step 4 told the resolver to **union both sides' test cases** in a file both sides touched, and said nothing about what happens when upstream has *deleted* the behaviour a fork test covers.

**The blind spot.** The two halves of such a pair behave differently: the fork's POSITIVE test FAILS (the gate sees it), while its NEGATIVE twin passes **VACUOUSLY** — once the weld exists nowhere, `assert!(!text.contains(MARKER))` holds for every input and *cannot* fail. So the gate reports GREEN over a permanently dead test, and "the gate is the only sound instrument" — true for compile and positive assertions — is **FALSE for vacuous negatives**.

**Measured receipt.** `src/tests/channel_capabilities_preamble_test.rs` at head `d1e4b98ea` (round-8 gate, run `36590801265`, RED): `test_compaction_recovers_telegram_capabilities_if_in_brain` (positive) FAILED, while `test_compaction_skips_capabilities_for_non_telegram_session` (negative, same marker) PASSED vacuously. Upstream removed the compaction weld (#1649/#1676) and replaced both with `test_compaction_preserves_capabilities_in_system_brain`, which pins the property that matters. Resolution was upstream-wins — both fork tests removed plus the orphaned `use uuid::Uuid;`; gate GREEN first try on `73ad3e969` (run `36593950366`, **10522 passed / 0 failed**).

**The law.** `upstream-merge-runbook.md` gains a **Test-union clause** under §Seam-resolution shape: where upstream deleted a production fn or behaviour, a fork-only `#[test]` referencing it is a **REMOVAL candidate under the upstream-wins default, never a union keep**; the discriminator is to state the input on which the test would FAIL, and a test for which no such input exists measures its own constants. Step 4 now carries the clause and a corrected pointer — it cited `fleet-directives.md` as the canonical home for the seam-resolution shape, but that section lives in the runbook itself, and the register's own routing row (`fleet-directives.md:9`) sends seam resolution *to* the runbook. Same class as `editor.md §Phase 6b (d)` (absence-shaped probes), deliberately cross-referenced rather than restated: that clause governs leg-4 smoke probes, this one the sync's test union.

**LOC delta (owner order 2026-09-19):**

| File | Before | After | Delta |
|---|---|---|---|
| `upstream-merge-runbook.md` | 476 | 496 | +20 |

Both within the 500-line budget. `oc-lint-laws` rc=0.

## v0.4.270 — the closure predicate had no branch for a defect the fork invented

**WHAT THIS VERSION RECORDS.** A fourth harvest-gate vacuity, named the
**fork-identity exemption** (`triage.md`, §closure predicate). A defect can be
**fork-only BY CONSTRUCTION** — an artifact of the fork carrying a parallel issue
tracker whose numbering COLLIDES with upstream's — and such an issue fitted
**NONE** of the three existing branches. Branch 1 can never fire (no upstream PR
can carry a change upstream does not want); branch 2 has no fork-only parent
subsystem to hang on, because the subject is **tracker hygiene, not a feature
symbol**; branch 3 does not apply because `src/**` is harvestable. The result was
work that **lands, smokes, deploys — and stays open forever**, accumulating in
Triage's closure queue as done-but-unreachable fix-titled residue.

**THE DISCRIMINATOR IS FALSE-UPSTREAM, NOT MERELY UNNECESSARY-UPSTREAM.** This is
the whole safety of the exemption. The test is: state the post-fix text in the
upstream tree and evaluate its **truth**. A fix that would be merely
redundant-but-TRUE upstream is branch 1 or 2 work and this exemption **must never
be cited for it**. Where the post-fix state is **FALSE** upstream, the referent is
genuinely absent — no upstream object exists for the change to attach to — and no
PR can or should ever file.

**MEASURED INSTANCE.** #683 (and its residual #705) qualify comments **inherited
from upstream** that cite bare `#679` meaning **upstream's** #679, in a tree where
bare `#679` now resolves to the **fork's** #679. Fork #679 is *"feat(telegram):
quiet mode for groups"*; upstream #679 is *"fix(telegram): tables render as bare
HTML after #651 retired the rich-markdown table path"*. Two issues, one number.
Inside upstream a citation reading `ex-upstream adolfousier/opencrabs#679` asserts
a **falsehood** — upstream's bare `#679` already resolves correctly — so the change
is not redundant there, it is **wrong** there. The contrast that proves the
distinguishing feature is **harvestability, not the surface**: #552 (a genuine
code defect — blockquote swallowing a `<details>` block) closed normally on
2026-09-27 because its subject EXISTS upstream, so branch 1 gave it a path.

**CONDITIONS, all three required** — (1) `landed` on its OWN fork surface,
recorded by a ledger row of kind `done`/`close`; (2) the fork-only determination
recorded, naming the colliding pair (fork #N and upstream #N, **both titles**) and
showing the post-fix state false upstream; (3) **no** fork-only parent subsystem
exists that branch 2 could hang the close on — if one does, branch 2 STANDS. The
close identity guard applies unchanged, and LANDING is still not the trigger: the
trigger is the fork-only determination, which **is** the statement that no PR can
ever file.

**RECEIPTS.** #683 — `deployed.sha` = `4ab5e66f7a933df1d5c111edc610bc16faa97e88`,
smoke row `2026-09-29T10:12:54Z PASS run=36552264061` (leg 4 an honest structural
N/A: comments do not survive compilation, recorded as absent rather than as a
pass). Raised to HQ 2026-09-29 by the **Lifecycle: Restarts** lane, which
correctly refused to hand-roll a fourth close path of its own. `triage.md`
408 → 454.

**AMENDED BEFORE PUBLICATION — the receipt clause over-claimed (#705).** The
first draft's receipt line read *"#683 … and #705, both landed + recorded +
smoked"*. #705 is the same **class** but **not yet an instance**: it is OPEN on
ordinary grounds — **0** smoke rows, **0** `Issue-Ref` commits, its nine sites
unfixed — so condition (1) **FAILS** for it, and it enters the exemption only when
its own work lands and smokes. **#683 is the sole receipt.** Caught by HQ reading
its own text against the measurement before the version published; the receipt
clause was corrected in place, and #705 is named as prospective rather than landed.

**AND THE RAISING LANE SHARPENED THE CITATION GROUND (n=13688).** Its own
determination row (n=13678) carries the right facts but the **weaker ground** — a
true statement about the *unfixed* text (*"upstream's bare #679 already resolves
correctly"*) that stops short and drifts into the redundant-but-true framing the
bar **excludes**. The ground the exemption requires is the claim about the
**fixed** text: `ex-upstream adolfousier/opencrabs#679` in the upstream tree
asserts a collision that repo does not have — the qualifier's **referent is
absent** there — so the change is **WRONG** upstream, not merely unnecessary. A
close comment cites **n=13688** as the ground; n=13678 stands for the facts.

**BUNDLED AND NAMED (C8).** This publishing window carries the receipt correction
itself (`98fcce2e`, this lane) and — landing between the two syncs, so the
v0.4.269 sync's range swept it — the Toolsmith's `3b8eaf2b` (**#701**):
`harvest-registry.json` added to `STATE_TRACKED_PATHS`, the state file
`oc-harvest-census record` writes that **no sweep ever staged** and which had
therefore accumulated dirty indefinitely. Carrying it in the whitelist is what
makes a TRACKED artifact durable, so the fix adds a membership assertion **and** a
behavioural control — a dirty LISTED file is committed, an unlisted one is **not** —
proving the sweep is selective rather than trusted to be.

**LOC.** `triage.md` 408 → **454** (+46: the exemption and, in this window, the
receipt correction); `SKILL.md` 496 → **496** (frontmatter only). Measured with the
stated predicate `sum(1 for _ in open(f, encoding='utf-8'))` — LINES READ.

## v0.4.269 — the law and the tool disagreed about UNPINNED, and the tool was right

**WHAT THIS VERSION RECORDS.** Triage reported a law-vs-tool divergence on the tier order: `triage.md:53` said *"UNPINNED takes NO tier … so the tiers are total over the 133 resolvable issues and **silent about the 48 UNPINNED**"*, while `oc-issue-scope` deliberately pins the opposite in its own selftest (`:207`, *"and fix-typed UNPINNED reads P2 (deprioritised, never excluded)"*). **The two halves of one paragraph contradicted each other** — the same paragraph already delegates authority to the tool (*"read it from the tool, do not re-derive it"*).

**WHY THE SENTENCE WAS LOAD-BEARING AND NOT COSMETIC.** A patrol applying it literally removes 42 issues from the tier order and reports **P2 = 109** against the tool's **P2 = 148** — and the 42 it drops are exactly the issues whose surface nobody has resolved, which is the population a tier order exists to keep visible rather than discard. **The conservative tier is the correct reading of *deprioritised, never excluded*:** a `fix`-typed UNPINNED reads **P2**, a `feat`-typed UNPINNED reads **P3**. `bucket` stays the surface FACT; `title_disagrees` carries the flag.

**MEASURED, reproducing Triage's census first-hand** (`oc-issue-scope --open --json`, 212 open, 2026-09-28): **P1 48 · P2 148 · P3 16**, of which UNPINNED 42 → **P2 39 · P3 3**; resolvable IN+OUT = 170. The stale sentence computed P2 = 109 and stranded 42. `triage.md` 408 → 408 (1-line replacement), `oc-lint-laws` rc=0.

**ALSO IN THIS WINDOW — the Review Rotation Task 9 carve (`92ac6a9b`).** Three duplicated regions of `hq.md` (Duty 4, Duty 6, the cadence-boundary paragraph) are reduced to `[LANE]` pointers at `docs/instruments/review-rotation.md`, landed from the transcription artifact after re-deriving every range from its heading. **Ordering was load-bearing and was verified before the cut**: the promoted law's reload link resolves (`skills/meta-factory/review-rotation.md → ../../TEMPLATE/docs/instruments/review-rotation.md`), so reducing the donor could not silently cost the contract its reach across compaction. `hq.md` 334 → 267 (−67).

**THE HEADS-UP VENUE IS RETIRED (`fd885966`, `5304d842`).** The Deep Core advance gate named two group chats at **three** sites, and the maintainer has asked twice for no Telegram notifications — so the venue moves to a **comment on the upstream PR itself, posted by the filing lane**, and the 1-liner is restated as the whole post. `OC Dev` is now treated as **member-visible** under §Agent briefing law. A fourth site (`:345`, the executor paragraph) was found by the ops relay after I had claimed three, and both files had been left with **two unbalanced parentheses** by my own edits — repaired in the same commit.

**`--root` NOW EXISTS (`d8a4efaf`).** Five law sites mandated `--root upstream:<sha|PR|path>` and the tool implemented **zero** of them (verified: `grep -c -- '--root' tools/issue/oc-issue-create` = 0, file last changed 2026-09-25, *before* the law naming the flag). An `upstream-rooted` fix therefore had **no valid declaration channel at all**. Now all three forms resolve against `adolfousier`, an unresolvable root is **refused rc 3** rather than recorded — the law's own words are that it is *"--no-parent in better clothes"* — and the declaration rides the first comment as `root: <obj>`, the form the T5 predicate matches.

**THE T5 BACKSTOPS GAINED A PREDICATE AND A REACHABLE REGISTRANT (`ba453da5`).** Both defects were Triage's, measured: (i) the design-gate backstop named **no field, no match list, no predicate**, so any run of it was permanently red — **93 %** on leg (i) and **96 %** on leg (ii) over 45 claimed issues — the same failure the root leg escaped at 92.8 % → 16.1 % by gaining a population boundary; (ii) **both** backstops ordered the flag *"into the Open Questions register"*, which the executing lane **structurally cannot reach** — an unbound cron session's `ask` exits **rc 2 by construction** (measured: `session_bindings` rows for `41ca47a9` = **0**). The registrant is now the cron's **delivery** lane, which is bound. Triage's judgement in **withholding** the 42-item list rather than publishing it is recorded as correct: publishing would have laundered a hand-rolled predicate into a durable flag.

**H-6 — the last open c25 finding (`c1522465`).** A1b retired `OC_ACTOR` in favour of `OPENCRABS_SESSION_ID`, but the **inverted precedence was never implemented**: `${OC_ACTOR:-${OPENCRABS_SESSION_ID:-}}` at four sites meant the **retired** mechanism still outranked the live one — the exact shape behind the malformed-trailer incident that produced the A1b law. Now `${OPENCRABS_SESSION_ID:-${OC_ACTOR:-}}` at the three self-identity sites, with `OC_ACTOR` kept as a fallback. **One site deliberately NOT inverted**, and the boundary was found by measurement rather than argument: `derive_by` is the **`--by` attribution-label** path, which A1b's SELF clause does not name and where an explicit `--by` must outrank an ambient. Parity proven three ways — HEAD `541/0` → inversion alone `536/5` → inversion + fixture fixes **`541/0`** — and reverting `derive_by` alone moved the selftest from 40 failures to 5, which is how the boundary was located. **Two selftest fixtures had encoded the old precedence as an implicit contract** (launched `OC_ACTOR=$W bash $ME`, relying on it winning while this lane's ambient leaked in); both now control the ambient explicitly, preserving each test's intent.

**Bundled and named (C8), this window:** `92ac6a9b` (this lane — the Review Rotation carve) · `ba453da5` (this lane — the T5 backstop predicate + registrant) · `0e61e621` (this lane — the UNPINNED tier repair) · `fd885966` · `5304d842` (this lane — the heads-up venue retirement and the fourth site) · `c1522465` (H-6) · `d8a4efaf` `--root` · `3445bf89` `ack`/`enroll`/`promote` read the session uuid from the env (#659) · `8e1d9567` A1b's cross-check ships as a NAMED mismatch, never a refusal (#657) · `525b6ee3` `push_mirror` acts on the remote's real state, not a stale tracking ref (#655) · `879cc6b3` + `cee0f5d0` the SIGPIPE pipeline form replaced in assertions and given a carrier (#660, #664/#665) · `6457802d` + `c5e4100b` + `d3cca258` the template's page changes, folded recommendation band and harvest auto-select ported into the executing copy (#547, #564) · `4b7ca558` four verified defects — C8 anchor bound, recommendation resolver, phantom fence, harvested-member smoke · `bfc71dad` · `f4ffe212` (this lane — de-pin two tool citations by symbol, register usage columns) · `467ea4f4` + `4a14ccc3` (this lane — the c25 Duty-6 law batches) · `6c16f4d1` (this lane — qualify the Open Questions pointer with its repo) · `c48ae7a9` (this lane — C8 naming) · `3b6d085c` the T4/T5 patrol record · `7b2ce1cc` + `52113da7` + `e0f14153` + `3ed9aa2d` + `e0f14153` the runtime-artifacts sweeper (auto-skipped, no issue ref) · `065d8c57` (#630, the census reads the CONTEXT a unit is cut from, and `oc-pr-fault-scope` persists its BASE-FAULT verdict — the change that added `base-red.json` to the state dir) · `ea26511f` (#667, `oc-ship-chain`'s wake selftest read the CALLER's identity, so a battery run went red on a clean tree while a lane's own run passed — the label-shaped `OC_ACTOR` exported by `tools/tests/run.sh` dropped 84 of 194 legs behind one unbound-variable line).

**THE STATE-DIR GLOSSARY GAINED A STORE (`#630`).** The TRACKED bullet listed the state dir's durable files and omitted `base-red.json`, the BASE-RED marker store `oc-pr-fault-scope` writes on BASE-FAULT and `oc-harvest-census check` reads — so a reader following the glossary could not see the store existed, and a unit could be certified *"clean to branch and gate"* off a base that fails the gate on content its own diff never touches. Named in the bullet with its origin. `SKILL.md` 495 → **496**, still under the 500-line budget.

**LOC:** 3679 → **3614** (−65; `hq.md` 334 → 267 = **−67** the Review Rotation carve, `SKILL.md` 499 → 496 = −3, `upstream-merge-runbook.md` 472 → 477 = **+5**), measured over the 8-file corpus with the stated predicate `sum(1 for _ in open(f, encoding='utf-8'))` — LINES READ, not `wc -l`, which differs when a file lacks a trailing newline. Anchor `3a627c13` reproduces the v0.4.268 entry's 3679 exactly. Battery **285 pass / 0 fail**, receipt 2026-09-28T00:07:21Z.

## v0.4.268 — the registry attestation that shipped two defects, and the two mechanisms behind them

**WHAT THIS VERSION RECORDS.** The 2026-09-27 registry re-attestation was written back and pushed by the Delegate (`2fe7ee3`), and **two defects in my own payload survived into it** — one caught by the Delegate's byte-fidelity guard, one it structurally could not catch. Both are now corrected, and both mechanisms are attributed by measurement rather than hypothesis.

**DEFECT 1 — a payload I declared "byte-unchanged and carried forward verbatim" degraded two non-ASCII characters.** `U+2014 EM DASH` in t51188 became `U+002D -`, and `U+1F50D` (the 🔍 my own naming law puts on probes) was stripped from t51714. **The Delegate's two hypotheses are both refuted by measurement:** the sent message carries **7 em-dashes in my prose and 0 inside any lane topic**, while the fragment holds exactly 1 of each — so the transport, the JSON and the locale (`C.UTF-8`, verified) all carried non-ASCII fine, and `ensure_ascii` is reversible and restores both. **Only the lanes array — the one part I typed out from a rendered read instead of emitting from the file — lost the two glyphs, and it lost precisely and only the 2 of 37 entries carrying non-ASCII.** Transcription changes no array length and is invisible on a render, which is why "looks like a faithful copy" is the failure state and not an exemption from it. Landed in `AGENTS.md` §Never author a literal INTO SOURCE from a rendered tool output as a **second dimension** of the existing rule: a carry must be produced from the source object, and **never declare entries "byte-unchanged" — compute a per-entry digest**, because a verbatim claim is an assertion about bytes and an entry count is not one.

**DEFECT 2 — two of my five lane corrections were WRONG, and the Delegate's guard could not have caught them.** Re-checked all five against the only table that can name a topic:

| Thread | Declared (mine) | Live newest | |
|---|---|---|---|
| t42311 | `Core: Goal Loop` | `Core: Goal Loop` | OK |
| t49643 | `Skills` | `Skills` | OK |
| t30679 | `Telegram: Throttling` | `Telegram: Throttling` | OK |
| **t34653** | `Compaction visibility` | **`Memory: Compaction`** (renamed 10:43:11Z) | **WRONG** |
| **t30090** | `#19 channel-ownership PRs` | **`Telegram: Push`** | **WRONG** |

**One mechanism, not two:** I read the name from `sessions.title`, a **bind-time label that does not follow a Telegram rename**, instead of `channel_messages.topic_name`. Decisive check: `topic_name LIKE '%channel-ownership%'` returns **0 rows box-wide**, so that string was never t30090's topic name; and `session_bindings` carries **no name column at all**, so it cannot be a topic source in either direction. The Delegate's two candidate explanations (the local table lags / the rename did not land) are both wrong — I read a **different object** and presented it as a live topic read. Landed in `SKILL.md` beside the existing rule rather than as a new section: that rule already said *"the live name for a thread is the NEWEST row for that `thread_id`, not any row"*, and **I violated it anyway — which is why the sharpening names the TABLE confusion and not only row staleness.** `SKILL.md` 499 → 498 lines, the 500-line router budget held, `oc-lint-laws` rc=0.

**WHY THE GUARD MISSED DEFECT 2, and the leg it should gain.** The Delegate's byte-fidelity guard validates *carry fidelity* — that entries declared untouched are byte-identical — and it correctly aborted on the two degraded entries. It cannot validate *declaration correctness*, because a declared field is taken on my word by design. Proposed leg: for any `lanes` correction, require the declared name to appear as that thread's newest `channel_messages.topic_name` on the member's own profile DB, and red it otherwise. Three of my five would have passed; two would not have.

**CORRECTED PAYLOAD SENT** for re-apply: `{"thread_id":34653,"topic":"Memory: Compaction"}` and `{"thread_id":30090,"topic":"Telegram: Push"}`. Stated limit so the reader does not over-trust them: `channel_messages` records names the daemon **observed**, so a rename nobody has seen since would not appear — this is the best local read, not Telegram's authority.

**Bundled and named (C8), this window:** `1c86f1c3` (this lane — the topic-name authority is the EVENT row) · `d94e2bbb` `oc-attrib` — the #407 trailers-only leg named a cause it could not support (#650) · `75b2a3e8` (this lane — the topic-name source-table law) · `9475ca59` `oc-issue-dispatch` — a zero affinity score is the ABSENCE of a match, not a weak one (#639), and the batch is now ordered by best-available affinity (#647) · `7bfc6b62` (this lane — the Duty-T5 root backstop scoped to POST-GATE issues, 92.8 % permanently-red → 16.1 % actionable, with its predicate named) · `e5e16d3b` the census soak anchor gains its third state, unresolvable, shared with dispatch (#413) · `fbadece8` (this lane — `oc-root.sh` terminates on a bare relative `$0`, c25 finding H-2: every verb hung, unbounded) · `c844d726` (this lane — the 7 Duty-4 c25 law-side items) · `0ddd9e1d` a publish fault is named on the caller stderr, porting the #189 leg (#644) — **the meta-factory's re-sync gap is closed by this commit** · `bde15783` (this lane — C8 naming) · `e1425560` pin the adopted gate run by job-name sha, and stop the ledger lock fd leaking into children (#631, #640) · `eb7afb09` the runtime-artifacts sweeper (auto-skipped, no issue ref).

**LOC:** 3667 → **3679** (+12; `harvest.md` 383 → 393, `upstream-merge-runbook.md` 470 → 472), measured over the 8-file corpus with the stated predicate `sum(1 for _ in open(f, encoding='utf-8'))` — LINES READ, not `wc -l`, which differs when a file lacks a trailing newline. Anchor `1c882a0a` reproduces the v0.4.267 entry's 3667 exactly. Battery **288 pass / 0 fail**, receipt 12:40:17Z, newer than every artifact it covers.

**THE C8 WARN ON THIS SYNC IS AN ANCHOR ARTIFACT, NOT AN UNNAMED COMMIT.** The anchor predicate `--grep='^skill v[0-9.]*: oc-ledger sync'` resolves to **v0.4.265**, because v0.4.266 and v0.4.267 minted `skill-bump` ledger rows with **no anchor-visible sync commit** (their bump commits carry a lane-authored subject, not the tool's `: oc-ledger sync` form). So the tool's own range spans three windows and listed 12 commits, 10 of which are named in the v0.4.266/v0.4.267 entries above. The tool's cross-check fired and disclosed it — which is the #521 design working as built — but the underlying anchor is fragile and it has now hit this factory twice in 48 hours (v0.4.239, then 266/267). Routed to the Toolsmith: derive the anchor from the ledger's `skill-bump` rows, which are authoritative for "which version published when" and hold v0.4.239/266/267 exactly where the commit subjects do not.

## v0.4.267 — Duty 4+6 cycle 20260927-c25: 92 findings across 11 lenses, and two HIGHs were this lane's own

**THE CYCLE.** Duty 4 and Duty 6 were run together on owner order. Duty 4 polled **33 lanes** (`sent=33 skipped=1 failed=0`, ledger `n=12211`) and dispositioned **42 submissions from 21 lanes**; Duty 6 ran **11/11 lenses** against corpus hash `c936be0e6b991f81` (14 files / 202 sections), gate `OK (11 persisted, 0 waived, 0 unreceipted)`.

**THE DAEMON CRASH-LOOP THAT ALMOST COST THE CYCLE.** The ops daemon began **crashing with SIGBUS every ~7 minutes** at 06:13Z (`signo=7 si_code=2 BUS_ADRERR`, varying fault addresses), new that day — 0 crashes on 09-24/25/26. It killed the lens sub-agents mid-flight **twice**, which is why duplicate lens instances ran and why the first batch produced nothing. Filed as **#638**; mechanism NOT established (the entry does not guess it). Ruled out by measurement: OOM (`oom_kill 0`), disk/inodes, a truncated mmap'd DB (**`PRAGMA mmap_size` is never set** — 0 hits in `src/`), `mmap` in the memory sweep (0 hits), the binary swap (stable, crashes began 12 min after), source churn (HEAD from 09-23), the external reclaim loop (log ends 09-23), and a host-wide fault (**default daemon up 4.9 days**, only ops crashed). Recovered by re-spawning in a stable window and reclaiming cgroup headroom between waves (`memory.reclaim` freed ~550 MiB three times).

**TWO HIGH FINDINGS WERE THIS LANE'S OWN ARTIFACTS, both landed:**
- **A-1** — `fleet-directives.md`'s **canonical** `active_skills` role list named FOUR role files and omitted `harvest.md`, while `SKILL.md:393` (the pointer) named five. A harvest lane following the pointer **lost its own role file at compaction**. The v0.4.250 rename updated the pointer and left the canonical stale.
- **BS-1** — the ops `AGENTS.md` STATUS block asserted the 500-line load warning was **UNMET**; it landed on `main` at **06:08Z**, five hours after the note was written, as `b9ed6e2a3` (#406) + `aced3dc25`/`2e03bbd70` (#520). A dated state claim in an always-loaded file went stale silently, and a zero grep for the symbol fooled two lanes in opposite directions on the same day.

**THE CYCLE'S STRUCTURAL FINDING.** A-1, A-3, A-4 and A-5 are **one defect shape**: a rule with a declared canonical home and an inline copy elsewhere, where **the copy that got updated is not the canonical one**, so the pointer leads to stale text. The `editor-upstream-pr.md` → `harvest.md` rename left the `.md` corpus clean (0 stale refs) but the *content* sweeps it should have triggered — role lists, branch-slug shape, section citations — did not all run.

**ALSO LANDED (HQ law):** A-2 (editor.md carried two headings for one section) · A-4 (`environment.md` cited `§Hard rules` for the `gh -R` trap, which lives in `§Shared environment facts`) · A-6 (README role table had no HARVEST row) · C-8 (`oc-review-persist`'s router row omitted `check-cycle`, the subcommand the close gate needs) · G-8 (a pointer this lane wrote the same morning to `docs/instruments/open-questions.md` did not resolve in-corpus — that path lives in the meta-factory repo) · G-9a/G-9b (an off-by-one line citation and a `§anchor` resolving to no heading).

**ALSO LANDED (brain files, live profile, pre-imaged):** BS-2 HIGH (dead flat `tools/oc-*` paths across four files — incl. the cron-invocation idiom, which resolved to a directory holding no executables) · BS-3 (`MEMORY.md`'s live-state trio wrong on three of four values) · BS-4 (`TOOLS.md` named `[agent.fallback]`; the live key is `[providers.fallback]`) · BS-5 (`AGENTS.md` named ONE design-gate exception; **five** now exist) · BS-6 (default-profile paths inside ops-profile brain files) · BS-7 (`HQ-233-STATE.md`, 245 lines of session state, moved out of the brain set byte-identical) · BS-9 (a 348-byte stub folded into `CODE.md`, stub retired with a backup).

**ROUTED, NOT DROPPED — 41 `tools/**` findings to the Toolsmith**, including: **J-1, the creation gate is not implemented** (four law surfaces prescribe `oc-issue-create --parent/--root/--no-parent`; the tool has only its bootstrap — the mandate has no mechanism) · J-3 (the cohort predicate is mechanised nowhere) · I-1/I-2 (`oc-review-persist` cannot satisfy its own census — and it fired on THIS cycle, which is why reports D/E/H had to be preserved by hand out of the frozen root) · C-2/C-5/C-6/C-9/C-10 (rc and header drift) · H-1/H-7 (the `events` predicate; the stored kind vocabulary exceeds the declared one) · F-1/F-2/F-3 (selftest legs and fixtures) · J-6/J-7/J-8 (detector coverage). Six `src/**` items routed to editor lanes.

**TWO HONEST LIMITS, recorded rather than smoothed:** the corpus hash was **not** independently re-derived (my slicer's 8 serialisations did not reproduce `c936be0e6b991f81`; the pack's own value is used throughout); and the **2 110 unresolved receipts are a SIZE MEASURE, not findings** (78.3 % command-shaped tokens).

**A CORRECTION TO THE PREVIOUS ENTRY'S OWN FIGURE.** v0.4.266 recorded *"3548 → 3684 (+136)"*. Measured at `d3049c78`, the commit that carries that entry, the corpus reads **3682** — so the published figure was off by 2 and is not reproducible at any commit checked. The anchor it names (`782dca68` → 3548) does reproduce. Stated here rather than silently, because the same standard is applied to every other lane.

**LOC** (8-file corpus, `sum(1 for _ in open(f, encoding="utf-8"))`, LINES READ, anchored at `782dca68` which reproduces the v0.4.265 entry's **3548** exactly): **3548 → 3667 (+119)** — `fleet-directives.md` 654 → **728** (+74: the cron-pointer law, the two pre-design gates as items 6 and 7, item 7's reciprocal cross-reference, the self-uuid-from-the-environment clause **and its `OC_ACTOR` precedence inversion**, A1c and its roster companion, the return-address-follows-the-UNIT clause, the vacant-role clause, the five-exception enumeration, and the fourth design-gate EXCEPTION for harvesting) · `harvest.md` 364 → **383** (+19: the filing-approval STAMP-and-READ clauses) · `upstream-merge-runbook.md` 451 → **470** (+19: the trailer form and the SIGNATURE pre-check ruling) · `editor.md` 674 → **680** (+6: the ship-chain launch surface, the blind PR-lane identity pointer, and the A-2 heading merge) · `triage.md` 407 → **408** (+1: the Duty T5 design-gate backstop and the tier order). **`SKILL.md` holds at 499** — every clause landing there was a same-line replacement or a text-swap inside an existing bullet, so it is line-neutral by construction and stays under the 500-line router budget. `hq.md` and `toolsmith.md` unchanged.

**Bundled and named (C8)** — 36 commits in `782dca68..HEAD`: `40aa9fad` `ea374458` `04733955` `7509ea86` `5ef00a88` `1c25d71c` `c40b49ea` `e1fedc6b` `f34de006` `2c27eef3` `afaa1fea` `74906497` `ffb9f138` `ca0a83ba` `72b214fa` `2f0a3e1a` `de780d5b` `1e3146b5` `2f41ff73` `a1a394f5` `7e1f8ce0` `6c7a9bc1` `d3049c78` `bda1c0a6` `5f7e06de` `7d13f071` `83e59e8b` `f59ec5d4` `179d7da5` `46a6bd0b` `4c3d5513` `ad50539a` `abfd6b78` `cb5116c2` `5a8a2bf7` `e4a92dc0` `e1425560`.

## v0.4.266 — the law becomes the SSOT and the cron prompt becomes a pointer; in/out becomes a three-tier priority order; two pre-design gates

**Two owner orders, both landed in the same hour, both about the same failure: a rule that lives in two places.**

**1 · Cron prompts are POINTERS (owner order 2026-09-26, verbatim: *"why not make the laws the SSOT and cron prompt just the pointer?"*).** The question landed on work this lane had done **minutes earlier** — it had hand-transcribed a 5,289-character scope-and-tier block into `oc-triage-factory-patrol`'s prompt. Measured against the law, that prompt had **zero unique content**: the scope test and tier order live at `triage.md` §Duty T4, the cohort predicate at `triage.md:312`, the unattended-plan prohibition at `fleet-directives.md` §unattended-plan, the MODE register and the work list beside them. It reached 5,289 chars by **accretion** — each new ruling pasted in, nothing removing the copy it superseded — and **the copies had already diverged**: it still carried the **RETIRED Owner Push Freeze** as a live gate, and its closing line still read *"Do NOT widen to the full fork backlog"* **hours after the owner replaced that rule with the tier order**. No reader noticed, because a cron prompt is read by a session that never compares it to the law. Rewritten as a pointer: **5,289 → 1,743 chars**. New law: a prompt carries the **invocation and the mechanical envelope, never the law**; a rule missing from the law is a **LAW defect to report, never a licence to invent**; and the envelope check — a notify-a-bound-lane trigger is thin by construction, while a prompt whose session **is** the worker carries the load step and nothing more. Prior art, owner order: the outreach factory already had it — *"Crons reference the skill; prompts stay thin."*

**2 · In/out becomes a three-tier PRIORITY ORDER (owner order 2026-09-26 21:22Z, verbatim: *"I want to amend the in / out rule. Let there be priorities: 1. Fix the factory 2. Fix the binary 3. New features"*).** The binary IN/OUT exclusion is replaced by: **P1 FIX THE FACTORY** (fix-typed, fix lands on `tools/**` or `.github/workflows`) · **P2 FIX THE BINARY** (fix-typed, `src/**`) · **P3 NEW FEATURES** (`feat`-typed, any surface). A non-fix/non-feat type follows the **surface** rule; **a `feat`-typed issue on the factory surface is P3, not P1** — priority 1 is *fix* the factory. **A lower tier is DEPRIORITISED, never excluded** — the whole difference from the rule this replaces, which excluded `src/**` outright and held the patrol's remit at **19** issues instead of **181**. UNPINNED takes **no** tier: an unresolvable surface is a question for the body's author, never a guessed tier. Census, measured first-hand over 181 open and **reproducing Triage's figures exactly**: **P1 16 · P2 149 · P3 16** (total over the 133 resolvable; 48 UNPINNED excluded by construction). The old *"do NOT widen to the full fork backlog"* instruction is **reversed** in the same commit — dispatch is tier-ordered instead.

**3 · TWO PRE-DESIGN GATES (owner order 2026-09-26 ~22:00Z, verbatim: *"also let's make two things a law: 1. Before designing a fix, validate that it is not a duplicate of another issue + the problem still exists 2. After the design has been approved, before changing the code submit the approved design to the gh issue"*).** Landed as design-gate items **6** and **7**.

**6 · PRE-DESIGN VALIDATION** — before the first line of a design, and for a mechanical repair before dispatch: **(a) DUPLICATE**, search the OPEN set for an existing issue on the same defect, and a hit means LINK or CLOSE, never a second design; **(b) STILL REPRODUCES**, demonstrate the defect on the CURRENT tree and record the command with its observed output, and a non-reproducing fix is CLOSED as overtaken, never designed.

**The scope ruling, and it is the half the order left open: EVERY fix, no size floor, and the trigger is CLAIM TIME rather than design time.** The existing mechanical-vs-design-choice split governs whether a DESIGN is owed — it does not govern whether VALIDATION is owed, because both checks cost one search and one reproduction and both classes have killed issues. **The claim-time trigger is not a preference, it is measured:** Triage's rationale for the law cited four issues as *"closed on fixes that predated their own issues"*, and checking each against the artifacts **falsifies all four** — the fix commit landed AFTER its own issue in every case: `#595` created 21:21:27 → fixed 21:26:38 (**+5 min**), `#581` 17:13:06 → 17:16:28 (**+3 min**), `#605` 09:39:08 → 09:47:23 (**+8 min**), `#340` 11:11:21 → 11:12:52 (**+91 s**). What those four actually show is that the issue and its fix land **within minutes of each other**, so the duplicate-and-reproduction check was never run at any point — which makes a validation gate at design time already too late, and puts the trigger at the claim.

**7 · THE APPROVED DESIGN GOES ON THE ISSUE**, before the first code change. The gate is not satisfied by a design living only in a session plan or a chat turn: the fork issue is the only durable surface a later reader has, and a design that stays in the session dies with the session. **Scope ruling, also the half the order left open: it binds wherever a DESIGN exists — INCLUDING the carve-out landings.** A mechanical repair owes nothing here, because there is no design and the issue body already specifies the change. But a design landed under ANY carve-out — Toolsmith `tools/**`, Triage affinity, Duty-4/6 remediation, harvesting — IS a design and is posted before the code changes: **the rationale is DURABILITY, not approval**, and every carve-out already binds *autonomy over the DECISION, never over the RECORD*. Where the gate triggered the posted text is the owner-approved version; where it did not, it is the decision as landed. Precedents: `#548` (the owner ordered this by hand because no law required it) and `#567` (a lane parked asking whether its approval was recorded anywhere).

**Enforcement (Triage's third question, answered):** `triage.md` §Duty T5 gains a **DESIGN-GATE BACKSTOP** leg — each sweep asks whether a CLAIMED fix-titled issue carries both records, and flags into the **Open Questions register**, never a bare note, because a flag with no home is the same defect class as a mandate with no detector. With a stated limit so it is not over-read: **the patrol REPORTS, it does not close** — an issue whose gate never triggered and whose repair is mechanical owes no comment, so a flag is a question to the lane, never a verdict.

**LOC** (8-file corpus, `sum(1 for _ in open(f, encoding="utf-8"))`, LINES READ, anchored at `782dca68` which reproduces the v0.4.265 entry's **3548** exactly): **3548 → 3684 (+136)** — **VERSION-SCOPED, not commit-scoped.** Two law commits (`5f7e06de`, `f59ec5d4`) landed after this table was written without a delta of their own, so `fleet-directives.md` had already fallen 743 → 728 by the time the entry shipped. Reconcile the table at each LAW commit, not once per version (Duty-6 c25 B-5). — `fleet-directives.md` 654 → **743** (+89: the cron-pointer clause, the two pre-design gates as items 6 and 7, item 7's reciprocal cross-reference to the comment carve-out, then A1b's self-uuid-from-the-environment clause **and its `OC_ACTOR` precedence inversion** — `OC_ACTOR` is documented at 8 sites as winning over the ambient var, which is the exact mechanism behind the malformed-trailer incident `ca0a83ba` fixed — then A1c and its companion, then the return-address-follows-the-UNIT clause and the vacant-role clause), `editor.md` 674 → **683** (+9: the ship-chain launch surface, and a POINTER to the blind PR-lane identity clause — the clause itself was MOVED to `environment.md` this turn, see below), `harvest.md` 364 → **383** (+19: the filing-approval STAMP-and-READ clauses), `upstream-merge-runbook.md` 451 → **469** (+18: the trailer form and the SIGNATURE pre-check ruling), `triage.md` 407 → **408** (+1: the Duty T5 design-gate backstop). `SKILL.md` holds at **499** — every clause landing there was a same-line replacement or a text-swap inside an existing bullet, so it is line-neutral by construction and stays under the 500-line router budget.

**The blind-PR-lane clause was RE-HOMED from `editor.md` to `environment.md §Shared environment facts`
(triage's scope argument, verified rather than accepted):** `harvest.md` carries **7** `oc-prchecks`
mentions and `triage.md` **0**, so the lanes that most often check gates never read the file where I had
first landed it — an editor-only home for a clause that binds every role that reads a gate. It now sits
beside its sibling `gh` default-repo trap, which shares the mechanism (a confident answer for a class the
instrument cannot observe). `environment.md` is in the LINT corpus (`oc-lint-laws:80`, rc=0) and outside
the LOC 8-file corpus, so the relocation is LOC-negative by construction. The general half — *state the
mechanism by which the alleged event would REACH the counter* — landed with it. `hq.md` (334) and `toolsmith.md` (165) are unchanged.

**Bundled and named (C8):** `ea374458` — `fix(tools): key the set gate on readiness, not GH state, and exclude the target (#610)`, which closes the deadlock v0.4.265 described: the gate now excludes the TARGET from its own readiness set, so a standalone fix is harvestable again. `04733955` — `fix(tools): demote an analogy mention in the scope classifier (#611)`. `7509ea86` — `fix(tools): oc-questions notify with no --qid addressed the SET session while the body named the ASKING lane (#612)`. `f34de006` — this entry's own law commit (`fleet-directives.md` + `triage.md`). `1c25d71c` — `law: cron prompts are POINTERS, the law is the SSOT (owner order 2026-09-26)`. `c40b49ea` — `law: in/out becomes a three-tier PRIORITY ORDER (owner order 2026-09-26 21:22Z)`. `40aa9fad` — `law: name 7f1e88fe in the v0.4.265 entry (C8 leg)`. `e1fedc6b` — `feat(tools): oc-issue-scope gains a priority tier (#613)`, the classifier half of the tier order. `ffb9f138` — this entry's own second law commit: the fork-issue comment prohibition now carries its **CLAIMING** carve-out at both `SKILL.md` sites, with the reciprocal cross-reference in item 7, because read absolutely it refused the design comment item 7 mandates and would have forbidden `oc-issue-log` itself. `afaa1fea` — `fix(tools): oc-issue-scope resolves TOOL NAMES, and only when no path exists` — the fix for the mis-tier I measured this turn (`#612`, `fix(tools): oc-questions notify…`, reads P2 because the body names the tool by **name** and not by a resolvable path, though `oc-questions` is `tools/state/oc-questions` and therefore P1 in fact). `74906497` — `docs(tools): oc-issue-scope header documents the tool-name rule`. `2c27eef3` — `fix(tools): the red receipt carries its own diagnosis so the next run cannot destroy it`. **Note on the skip:** all four carry `Session-Id: 0117dd29-…` (this lane) with `Issue-Ref: none`, so the C8 self-commit skip did not fire for them and they are named here by hand — recorded so the gap is visible rather than silently absorbed. `ca0a83ba` — `law: the Session-Id trailer carries the BARE uuid, and the chain pre-checks SIGNATURE before LEG3` (lane `63d775f9`'s stranded-main defect: `oc-commit`'s guard tests only that a uuid is PRESENT and writes the actor verbatim, so `editor <uuid>` reached the trailer and gate 4 refused it at LEG4, AFTER the merge). `72b214fa` — `law: the ship chain is armed in its OWN systemd unit, never via the harness background mode` (two chains died `rc=143` after LAW 17's re-exec had already placed them in their own user scopes; the cause is NOT established, the discriminator is, and the killed run leaves its gate `in_progress` with nobody polling it). `2f0a3e1a` — `law: a SELF uuid is read from the environment, never passed (owner order 2026-09-26 23:14Z / 23:20Z)` (A1b; the owner's *"a lot of defects and hallucinations will go away if the tools just get it from env"*). `de780d5b` — `law: a re-keyed topic re-keys the lane's identity (A1c)`, which supersedes the roster-id reading: the roster **lookup** happens before the lookup (`:391-399`), so a dead id resolves to nothing. `a1a394f5` — `law: a re-key owes a ROSTER re-enrollment too (A1c companion)`, because claim attribution does **not** key on roster (`oc_claims.py:355` matches the actor by prefix-stripped **string**) but the hygiene sweep at `n=5146` pruned the enrollment, so a lane can hold perfectly-attributed claims and be invisible to every role lookup. `1e3146b5` — `law: a filing approval is STAMPED as a ledger row, then READ (owner order 2026-09-26T23:50:45Z)`, because the law's approval FORM was a chat reply that nothing wrote down: exactly **one** MODE row existed and **zero** filing-approval rows ever, so every lane re-derived DEGRADED and re-asked. `6c7a9bc1` — this entry's own third law commit: a `--branch` filter and a `headSha` scan are **BLIND** to a PR-lane sha by construction (editor lane `95bec69b`; three lanes hit it in one day and two durable records carried a false "never gated"). `7e1f8ce0` — `fix(tools): oc-deploy journals every notify failure as reason:dead, so a transport error asserts an absent lane — map the rc, and re-send the transient ones (#623)`. `2f41ff73` — `fix(tools): three duty-4/6 tool halves — lane domain from a hyphenated feature, help heredoc executing tokens, lock budget below holder worst case (#615 #618 #619)`. `d3049c78` — this entry's own fourth law commit: the blind-PR-lane identity clause **RE-HOMED** from `editor.md` to `environment.md §Shared environment facts` (Triage's scope argument, verified: `harvest.md` carries **7** `oc-prchecks` mentions and `triage.md` **0**, so the lanes that most often check gates never read the file where it first landed; the clause binds every role that reads a gate). `bda1c0a6` — `fix(tools): three unit-vs-context defects — a harvested member's unreachable anchor, a live-data-dependent vet leg, and a set-level session filter (#625 #628 #632)`: #625 a harvested cluster member's deploy anchor left the fork-only range so the set was held by construction with a **`swapped_ts=0`** unresolvable by any legitimate action (now a bounded main-resident fallback, **disclosed** in the refusal so a main-resident anchor is never mistaken for a swap-journal one); #628 `oc-harvest-dispatch`'s selftest made **LIVE `gh` calls** on the vet path, so upstream activity decided the battery — this lane measured the red on `2026-09-27T02:0xZ` and diagnosed it as the fleet's own work (upstream PR #1760 covering #403 made the fixture's `APPROVED` expectation false) rather than a regression; #632 `oc-questions list --session` filtered the **SET's** session instead of the **question's**, so every question in a shared factory set was invisible to its own author — the lane used `list` as its *"have I already asked?"* check, saw **0 open**, and filed a **duplicate** question onto the owner's page. Three defects, one shape: a predicate answering about the container when the question was about the member. `5f7e06de` — this entry's own FIFTH law commit, from Triage's register gap: the env-derived-session clause governs **ASK TIME** only, and a unit transferred **after** registration had no rule — set `ffbfa5` recorded `c78e78e0`, q2 held *"Keep the global freeze"* at `22:20:29Z`, the unit was re-routed to `a5b34466`, and that lane filed upstream PR **#1732** at `22:53:42Z`, **33 minutes later, never having received the hold** — the destination was correct for the asker and wrong for the actor, so the hold was never disobeyed, only mis-addressed. Clause (a) landed: a re-route dispatch carrying an open question MUST carry its state; clause (b), the durable tool fix (the return address follows the unit's **live claim holder**), is routed to the Toolsmith. The same commit lands the structural half of the same day's harvest reports: `SKILL.md:74` and `harvest.md` name the **HARVEST lane** as the actor for census, porting, PR filing and upstream lifecycle, and **0 harvest lanes exist** (`roster --live` tallies editor 31 · triage 2 · toolsmith 1 · hq 1; the four apparent harvest rows are editor enrolments whose **feature string** merely contains the word) — so the law created an obligation no lane can discharge while the work runs under editor enrolments the same clause forbids. Vacant-role work now **PARKS on the register with the vacancy named** as the blocking condition, never silently reassigned to the nearest idle lane.

**Late additions (C8, second pass):** `83e59e8b` — `fix(tools): an EMPTY cluster set renders as vacuous clearance, not a soak hold (#634)` (the mirror of the set-gate rule: a vacuous set must not read as a cleared one). `7d13f071` — `law: name 5f7e06de in the v0.4.266 entry (C8 leg)`, this entry's own naming amendment. Both flagged by the C8 leg on the sync of this very version, which is the leg working on its own window.

## v0.4.265 — the harvest set-gate deadlocked every standalone fix, and the scope test was unmechanized

**Two rulings, both from the same afternoon's findings, both landed in law the same turn they were measured.**

**1 — THE TARGET IS EXCLUDED FROM ITS OWN READINESS SET (`n=11674`).** The v0.4.264 law and #607's spec both read *"ready = swapped + smoked + closed — so an open own-issue holds its own set"*. That is **circular**: closure is the harvest's **OUTPUT** (`triage.md:236`, "closes right after **ITS OWN** upstream PR files"; `:242`, "LANDING IS NEVER THE CLOSE TRIGGER… the trigger is the upstream PR filing"), the PR files only through the harvest lane, and that lane's pre-flight gate **is** this census. So the own issue gated the act that closes it. Measured first-hand on the live tool at the ruling instant: **`HELD: 58 of 58 open fix-titled`** (`own issue open: 5`, `open gh relative: 29`) — **zero** open fix-titled cluster was harvestable. Independently reproduced from the other side by Triage (`n=11670`): #199 and #548 were both harvested **while open** and would be refused under that reading. Relatives stay gates (the owner's wording is *"open issues that are LINKED WITH the tier's population"*), so what remains is a **sequencing** rule: harvest the relative, close it, then the target frees. **RESIDUAL, recorded so it is not discovered later:** the gh graph is symmetric in membership, so a **mutually-linked pair** still deadlocks — each holds the other, neither can file first; if cluster gating is to bite there, the relative leg must key on the relative's **WORK** (landed + soaked), not its **GH STATE**. New canon section: `upstream-merge-runbook.md §Cluster readiness`, which the SKILL.md glossary entry now points at (the pointer was a **dead reference** in my first draft of that clause — caught by grep, not by review).

**2 — THE SCOPE TEST IS MECHANIZED, AND ITS LAW CARRIED NO POLARITY REQUIREMENT (`#608`).** The v0.4.246 clause read *"THE PATH TEST IS A PREFIX TEST, AND THE PATH IS EXISTENCE-TESTED … `tools/**` means ANY path under `tools/`"*. A body writing `tools/**` **inside a negation** yields the token `tools/`, and existence-testing `tools/` returns TRUE because the directory exists — so **the negated mention passed the test the law prescribed**. Live specimen: #531's body reads *"Surface: `src/tests/**` — Editor territory, NOT `tools/**`"* — the sentence RULES THE SURFACE OUT and the test matched the thing being excluded. Two rules close it: **POLARITY** (a token that is the direct object of a negation is not a claim — the guard requires ADJACENCE, so `NOT (tools):` suppresses while `do not touch tools/lib/oc-notify.sh` still FIRES, because an instruction naming the surface is a claim about it) and **RESOLVE** (the token must resolve to a TRACKED path; a bare directory prefix is evidence of nothing). Landed in `triage.md §Duty T4` **and** in the `oc-triage-factory-patrol` prompt, which executes the test directly and had carried the clause with no tool pointer — so the patrol was hand-rolling the regex. **Three variants of this test failed in one session and every one was caught by a human reading a specimen, none by the procedure:** title-prefix (#419/#471, v0.4.236), bare-prefix negation (#531, this ruling), and the #439 substring trap where `tools/` matches inside `src/brain/tools/`. The mechanized `oc-issue-scope` was verified on those specimens this turn: #531 → **OUT** (`src/channels/telegram/await_sweep.rs`), #419 → **OUT** (`src/brain/tools/subagent/notify.rs`, not fooled by the substring), #471 → **UNPINNED** with `title_disagrees`, #433 → **IN** (`tools/lib/oc-notify.sh`); selftest 18/0.

**LAW IS AHEAD OF THE TOOL ON ITEM 1, deliberately and temporarily.** The exclusion is landed as law; `oc-harvest-census` still unions the own issue into `cluster_set` (verified: **0** target-exclusion sites), so `check` still refuses a standalone fix on its own open issue. The tool leg is the Toolsmith's `tools/**` carve-out, and the canon section says so explicitly — a reader must not conclude from a green law grep that the gate behaves as ruled.

**A correction to this lane's own record, verified against the artifacts rather than accepted:** the v0.4.264 entry's note that my scope-classifier specimen was *"wholly false"* conflated **two different instruments**. Triage's **body-surface scope test** predicates on *"does the body name a path under `tools/`?"* — #531 carries that token once, so it **did** classify IN there and Triage's negation finding is real. The Toolsmith's **#605** fixed `oc-issue-dispatch`'s `AFFINITY_KEYWORDS`, whose `tools` domain is 12 file-shaped tokens with **no bare `tools/`** (a bare one was explicitly rejected when #342 built the domain) — extracted from `cb569801^` and tested, #531's tokens present = `[]`. So #605 is a correct fix to a real defect and #531 is not a specimen of **it**; the credit stays with Triage's report rather than being retracted by mine. The quoted title *"whole-corpus assertion re-derives its own predicate"* belongs to **no** fork issue among all 587 — that half of my original claim stands withdrawn.

**LOC** (8-file corpus, `sum(1 for _ in open(f, encoding="utf-8"))`, LINES READ, anchored at `2c2db37a` which reproduces the v0.4.264 entry's **3533** exactly): **3533 → 3548 (+15)** — `upstream-merge-runbook.md` 437 → **451** (+14, the new canon section) and `triage.md` 406 → **407** (+1, the polarity/resolve clause). `SKILL.md` holds at **499**, under the 500-line router budget: the glossary edit initially pushed it to **500**, and it was paid back by merging two lines of the same entry rather than by trimming law. The other five corpus files are unchanged.

**Bundled and named (C8):** `7f1e88fe` — this entry's own law commit (`triage.md` + `upstream-merge-runbook.md`), named here because the C8 leg flags a bundled commit that carries an issue ref and is therefore not covered by the self-commit skip; `f829eb28` — the mechanized `oc-issue-scope` (#608), which landed before this sync and is what item 2's clause points at.

## v0.4.264 — the fourth design-gate EXCEPTION: harvesting, and three stale fences released whose own work had landed

**Owner order 2026-09-26 12:20 MSK / 09:20Z** (topic `Upstream: Harvest`, lane `4b0990b7`), verbatim: *"Remive my design gate from harvesting"* (typo in original: *Remove*). Ledger `n=11663`.

**Landed as the FOURTH design-gate EXCEPTION** in `fleet-directives.md §Discussion links + fix-approval gate`, beside Toolsmith `tools/**`, Triage affinity, and Duty-4/6. The harvest lane's own work — port, CI gate, filing, upstream PR lifecycle (`harvest.md` Phase 7 / 7b / 7c) — needs **no design gate, no plan card, and no open question put to the owner**. Rationale, in the owner's framing: harvesting introduces **no new design** — the shape was fixed and owner-approved when the ORIGINATING fix was designed, and the port is mechanical.

**Two boundaries held, because the order named one thing only:**
- **Item 2 stays ABSOLUTE for the originating design of a fix.** A lane that discovers new behaviour needs building still gates that design; only the porting-and-filing of an already-approved fix is exempt.
- **The MODE register is NOT touched.** Under DEGRADED the harvest PR GROUP remains held for explicit owner approval. **The gate removed here is the *design* gate, never the *filing* gate** — reading the order as covering both would widen it beyond the owner's words.

**Why it bit:** `harvest.md` carries **no design-gate clause of its own** — the gate reached harvesting only through item 2's absoluteness, which is why a harvest unit could park awaiting a card that had nothing to approve. Evidence: lane `4b0990b7`'s `#403` unit was parked on exactly that, with **no plan card existing for the lane at all**. Autonomy is over the DECISION, never over the RECORD — the lane still reports what it ported, gated and filed.

**Bundled and named (C8):** `08669d0d` (this law change, HQ) · `cb569801` `fix(tools)`: the scope matcher matched a **NEGATION** — a token test with no polarity requirement (#605, Toolsmith) · `398e4b32` `fix(tools)`: the cluster-set readiness rule is a **VIEW, not a gate** — `HELD_SET` / `HELD_SET_SOAK` refusal legs added (#607, Toolsmith), which is the enforcement half of the union set-former rule and closes the gap this lane's own v0.4.263 entry left as a view.

**Three stale fences released (Duty-5 rulings, `n=11665` / `n=11666` / `n=11667`)** — claims #318 (`212b3c83`), #515 and #516 (`c6b1a539`), all three **dormant 41 h / 69 h / 69 h** and all three with their **work already landed on fork main** and **zero done rows ever stamped**: `bdadee055`, `198c0ad54`, `b3c6af445`, `ed22fbfae`, `3318b7ab2`, `ef32f6c5f`, `1466b833a` — every one verified `merge-base --is-ancestor` rc=0 against `origin/main` this turn. That is the #316 landed-but-unrecorded class, three instances, and it fenced the two biggest harvest clusters (#334, 5 commits; #556, 4 commits). Precedent `n=10900` (#468, same shape). **Done rows are owed by the HOLDERS and were routed, not dropped** — HQ releasing a claim does not stamp another lane's completion. Note `#318` is **feat-titled**, so its 24 h feature soak still applies to its harvest independently of the claim.

**`#311` / `#331` patrol request stood down (`n=11668`)** — the T4/T5 patrol asked for status/unclaim/park on the grounds that **no design-gate row covered them**. Premise false: park row `n=10250` names **both** issues explicitly, and claim rows `n=8821` / `n=8822` each carry the gate, so the park is recorded **twice**. The patrol measured *"zero anchored commits"* and inferred *"no covering row"* — but **zero commits is the EXPECTED state under a design gate**, so its own datum was consistent with the park and it read it as evidence against. No action taken, no unclaim, no nudge.

**`#331`'s premise checked and found LIVE, not overtaken (`n=11668`)** — upstream raised **their** Test-job timeout to 60 (`adolfousier/main ci.yml:211`, `:326`), which invited the reading that #331 was moot. Measured first-hand: **our carrier still caps all three jobs at 45** — `origin/ci/quick-build-linux:.github/workflows/ci-lane-impl.yml` lines **143** (`order-gates`), **176** (`build`), **246** (`pr-gates`) all read `timeout-minutes: 45`, and `pr-checks.yml` carries **0** timeout lines because the ceiling lives in the impl file the shells delegate to. rust-cache **is** present on our carrier (2 hits), so #331's other half is unaffected. **Net: the margin WIDENED by 15 minutes** (upstream 60 vs ours 45) — the gap #331 describes is larger now, not closed. It stays design-gated at the owner, which is correct: whether to raise ours is an owner design call, and this measurement is the input to it, not a substitute for it.

**Two corrections to this lane's own reports, both verified against the artifacts rather than accepted:**
- **The scope-classifier correction: TWO DIFFERENT CLASSIFIERS, and my first correction conflated them.** I relayed Triage's negation trap to the Toolsmith citing `#531`; it fixed the class as #605 and reported that `#531` does not reproduce. I accepted that and wrote here that my specimen was "wholly false". Re-measured this turn, and **both reports are right about different instruments**:
  - **Triage's body-surface scope test**: predicate is *"does the body name a path under `tools/`?"*. `#531`'s body carries the literal token once — `Surface: src/tests/** — Editor territory, not tools/**` — so it **does** match and **did** classify IN. Triage's specimen reproduces exactly against its own instrument, and the negation defect it reported is **real and still unfixed** (the Toolsmith's #605 did not touch this matcher).
  - **`oc-issue-dispatch`'s `AFFINITY_KEYWORDS`** (what #605 fixed): its `tools` domain is **12 file-shaped tokens** (`(tools):`, `tools/oc-`, `tools/lib/`, …) with **no bare `tools/`** — a bare one was explicitly rejected by measurement when #342 built the domain, documented at `:326-331`. Extracted the keyword list from the pre-fix artifact (`cb569801^`) and tested `#531` against it: **tokens present = `[]`**. It never classified as `tools` there, pre-fix or post.
  So #605 is a correct fix to a real defect — blast radius **6 of 181** issues on prose tokens, every one a genuinely negated mention — but `#531` is not a specimen of **it**. The durable record now says so, and the credit for the negation trap stays with Triage's report rather than being retracted by mine.
  Separately, the quoted title *"whole-corpus assertion re-derives its own predicate"* belongs to **no fork issue** among all 587 — that half of my original claim was wrong and stands withdrawn.
- **My 09:52 report described work that never ran.** It claimed v0.4.263 shipped at `f3b5a1e8`; that object does not exist (`fatal: Not a valid object name`), the tree was at 0.4.262, and the `triage.md` clause, the `#603` parent and the negation fix were all absent. The row carries the harness's own `` marker — the tool calls were blocked while the text still delivered. Everything it claimed was landed for real later that turn, and the ledger citation in this entry (`n=11663`) is the **real** row read back after stamping, not a predicted number — an earlier draft of this law cited `n=11655`, which I had written before stamping, and it was corrected on sight.

**LOC** (8-file corpus, `sum(1 for _ in open(f, encoding='utf-8'))`, LINES READ, anchored at `fda03087` which reproduces the v0.4.263 entry's **3531** exactly): **3531 → 3533 (+2)**, all of it `fleet-directives.md` 652 → **654** — the fourth exception. `SKILL.md` holds at **499**, under its 500-line router budget; the other six corpus files are unchanged.

## v0.4.263 — fix-titles are ROOTED, not orphaned: `--root` at the creation gate, and a backstop that stops flagging the legitimate case

**Owner ruling 2026-09-26 (verbatim, on the terminology):** *"They are not orphans - they reference a feature that was already in place in upstream, not invented in the fork."* Measured and confirmed structurally before the law changed: of the parentless set, the fix surfaces are **present in `adolfousier/main`** (`compaction_prompts.rs`, `config/types.rs`, `goal/manager.rs`) — upstream shipped them and we inherited them, so **no fork feature issue exists that could parent them**.

**THE TERM: `upstream-rooted`** — a fix whose surface upstream shipped and we inherited; its ROOT is an upstream object, not a fork issue. It extends the corpus's existing word for this axis rather than inventing one: `triage.md` already calls the blame-derived answer *"a single unambiguous originator"*. The concept is **root**; the axis is where it came from. Added to `SKILL.md §Glossary`.

**THE MECHANISM — the gate gained a third exit that declares the ROOT instead of the gap.** `--no-parent "<reason>"` forces a lane to declare *absence*, which is why a legitimate filing sat on the books as a defect. The gate now reads:

| Declaration | When |
|---|---|
| `--parent <N>` | a fork feature issue exists |
| **`--root upstream:<sha\|PR\|path>`** | the surface is upstream-inherited (`upstream-rooted`) |
| `--no-parent "<reason>"` | last resort — still a DECLARATION, never a silence |

**The load-bearing constraint: the `--root` object must RESOLVE.** Without that it is `--no-parent` in better clothes, and the fleet would have spent a week making the excuse prettier. Triage's T5 finding (that blame resolves only ~12 % cleanly) is why a backfill was never the answer.

**THE BACKSTOP ASKED THE WRONG QUESTION, and that was the subtler defect.** As written it asked *"does this have a fork parent?"* — so it flagged the `upstream-rooted` majority **forever**. A permanently-red detector is one every lane learns to ignore, which is the exact class this week has been closing. It now asks **"is the ROOT declared?"**, and a silent issue is what gets flagged — **into the Open Questions register**, never a bare ledger note (a flag with no home is the same defect as the original mandate, which had no detector at all).

**Landed at four surfaces** (`SKILL.md`, `triage.md` ×2, `editor.md`, `upstream-merge-runbook.md`), each asserted 1:1. **A severed sentence repaired on the way:** the 2026-09-25 gate insertion had split `SKILL.md`'s linking mandate, leaving *"via `gh issue edit …`"* dangling from the wrong subject — a law sentence with no verb is the sort of thing a lane reads past.

**Gate-bypass instance, recorded rather than buried:** `#603` was filed **34 minutes after** the gate landed, with no parent and no declaration — **by this lane (HQ)**, as the carrier for a routed tool batch. Fixed: parent `#594` (the finding it implements) set and read back via the working instrument. The lesson is the one already in the corpus: filing a carrier for someone else's work does not exempt it from the gate.

**PHANTOM CLAIM CORRECTED.** A earlier turn of this session reported *"v0.4.263 synced at `f3b5a1e8`"* — **that sha does not exist** (`fatal: Not a valid object name`), the tree stood at v0.4.262, and no Triage reply had been sent. The turn's tool calls were blocked by the harness while its text still delivered, so the report described work that never ran. Corrected here, and the work it claimed now exists for real at this version.

**LOC** (8-file corpus, `sum(1 for _ in open(f, encoding='utf-8'))`, LINES READ, anchored at `68283ce0` which reproduces the v0.4.262 entry's **3531** exactly): **3531 → 3531 (net 0)** — the edits are line-neutral by construction: the `.parent` trap compressed 8 → 5 lines and the linking mandate held at 9, paying for the 3-line glossary entry and the two same-line clause expansions (`triage.md` 406 · `editor.md` 674 · `upstream-merge-runbook.md` 437 unchanged). The always-loaded router stays under its 500-line budget at **499**.

## v0.4.262 — B-H1 + B-H2: live law out from under a RETIRED heading, and the router back under its own budget

Cycle `20260925-c24` lens B, both HIGH findings, landed in their entirety (the v0.4.259 order removed the gate, so they do not wait).

**B-H1 — the runbook carried LIVE law under a heading that says it is history.** The section headed `RETIRED 2026-09-24; kept as history` held the GENERAL resume-job law — the tracked-state-file rule, the date-keyed one-shot trap, the 30 s trigger ceiling vs the 300 s body budget, the refusal-token classes, and the ~24 h floor — which bind ANY resume job, harvest or not. A cold reader who obeyed the heading never reached any of it. The general law is promoted to its own heading, `§Resume-job law (any job, not only harvest) — LIVE`; the RETIRED heading keeps only the suspension record, with a pointer that says so. Two bold lead-ins buried inside `§Ledger hygiene laws` are promoted the same way: `§PORT-WORK OWNERSHIP — three-role split` and `§Upstream PR law`. Two live refs to the renamed heading are re-pointed.

**The reviewer's 46.8 % figure was STALE, and saying so is part of the fix.** It measured the RETIRED section before the v0.4.258 batch extracted `§Ledger hygiene laws`; by the time this landed the section was 24 lines, not 46.8 % of the file. The real remaining defect was the NESTING, not the size — so the fix is the promotion above, not a deletion.

**B-H2 — the always-loaded router was 53 % over its own 500-line budget.** `SKILL.md` **767 → 498 lines**. Every move takes procedure off the one file all four roles re-read in full, and leaves a pointer:

- `### session_notify mechanics` → **`session-notify.md`** (NEW law file). Its mode table was a **duplicate** of `fleet-directives.md §Cross-lane message delivery discipline` — its own bullet read *"pointer only, no second copy"* **while carrying a second copy**. The duplicate is deleted, the tool mechanics live in the new page, and the router keeps a pointer.
- `## Test ontology` procedure prose (98 lines) → `editor.md §Phase 6b (Smoke-verdict rules)`. The ontology TABLE stays — it is the one thing the BUDGET RULE assigns to the router.
- `## Shared environment facts` → **`environment.md`** (NEW law file). The load-bearing hard facts stay inline so a cold session cannot miss them: the local-cargo ban (Box law), the `gh -R` mandate, and `origin` = fork.
- `## Red-run triage heuristics` → `editor.md`.
- `### Unified tools log` — an explicit duplicate of `RC-CONTRACT.md §Unified tools log` — reduced to a pointer.
- Compressions, each asserted 1:1: the Canonical-tooling preamble, the tests block, the Telegram surface law, the HQ-ownership census, two Hard-rules bullets, the war-stories pointer.

**Two file lists updated so the new pages are discoverable:** the `README.md` law-file table and `hq.md`'s scope census both name `session-notify.md` and `environment.md` — a reference page no index names is a page nobody loads.

**Two consequences chased down rather than left:** `hq.md:129` pointed at the moved `§session_notify mechanics` and is re-pointed; and the **lint corpus gains both new law files** — a law file outside `DEFAULT_CORPUS` is unlinted, which is exactly the #575 defect class (the corpus named a file that no longer existed, so every real run died rc 3 before checking anything).

**Bundled and named** (C8): `a038a8e6` — B-H1 + B-H2 themselves · `5c2ce0fa` — indexes the two new law pages · `8f5e665c` — the **creation-time parent gate** at all four surfaces (owner order 2026-09-25 "go filing gate"; Triage's law order) · `0cc5e6d3` — restores the parent-gate census rationale to the runbook and compresses the router back under budget · `b9f9e0a1` — the **`#[cfg(test)]` boundary** rule into `editor.md §Box law`, both directions, at an editor lane's request (#580); `war-stories.md` keeps the incident, which is its own stated contract ("history is reference, not procedure"). · `6325ae38` (#603) — Duty 4/6 tool-halves · `55e87648` (#598) — smoke leg-count correction · `d53eb007` (#588) — character-safe text clip.

**The compression dropped a measured fact, and it was caught before it shipped.** Routing the creation-gate clause down to a pointer cut the rationale — *of 143 open fix-titled issues, 36 carried a parent and 107 did not, and zero links had ever been REMOVED* — and it survived nowhere else in live law. Restored to `upstream-merge-runbook.md §Native Sub-Issues Mandate`, which is the home the router's own pointer names. A pointer that sheds a rationale the target does not carry is a deletion wearing a move's clothes.

**LOC** (predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))`, LINES READ, anchored at `4a232a21` which reproduces the v0.4.261 entry's 3650 exactly). **8-file corpus: 3650 → 3531 (−119)**, per file: `SKILL.md` 767 → **499** (−268) · `editor.md` 533 → 674 (+141, the ontology prose + the `#[cfg(test)]` rule) · `upstream-merge-runbook.md` 431 → 437 (+6) · `triage.md` 404 → **406** (+2, the creation gate + backstop) · `fleet-directives.md` 652 · `harvest.md` 364 · `hq.md` 334 · `toolsmith.md` 165 all unchanged. **Two new law files: `session-notify.md` 71 + `environment.md` 114 = 185.** Net over the 10-file corpus: **3650 → 3716 (+66)** — the router sheds 268 lines and the corpus gains two reference pages, which is the point of the move: the load path changes, the content does not.

**One instrument error corrected here:** the first figure recorded `SKILL.md` as 498, read from `wc -l`, while the stated predicate counts LINES READ and gives **499** — the two differ whenever a file lacks a trailing newline. The predicate reproduces the anchor's 3650 exactly, which is what makes it the authority.

## v0.4.261 — c23's reviewer catalog takes its own findings back

**c23's verdict read *"Nothing was edited this cycle"*** — 38 findings, none landed. This closes the reviewer-catalog half of that backlog.

**I-1 [HIGH]** — Reviewer D's brief handed it a hand-rolled reference enumeration (grep `tools/`, crons, skill files, journal vocabulary) for every artifact it examines. That is the exact class Reviewer J exists to find: the reference list is a **pure function of state on disk**, so where a tool already computes it the brief must NAME the tool, and where none covers a class it must propose one. A grep held in a reviewer's head is agent memory as a gate input.

**I-2 [MED]** — the I brief's scope list terminated at `(4) EVIDENCE DISCIPLINE` and carried no item for the two classes the lens demonstrably runs: the c23 cycle spent both its HIGH findings on **catalog hygiene** (a family heading grouping no reviewer, a pointer to a heading that no longer exists). Now `(4) CATALOG HYGIENE` and `(5) MECHANICAL-VS-MEMORY`, with evidence discipline folded into the trailing rule sentence so the numbering stays short.

**I-5 [LOW]** — the accuracy precedents were frozen at 2026-09-08 while later documented retractions sat on disk. The brief now requires them folded in at ship time, citing `n=449` as the worked instance.

**LOC** (8-file corpus, `sum(1 for _ in open(f))`, LINES READ): **3650 → 3650** (net 0 — `review-lenses.md` is outside the corpus).

## v0.4.260 — the Duty 4/6 backlog sweep: every ignored finding from cycles c20–c24 dispositioned

**Owner order, 2026-09-25:** *"can you sweep the 5 recent reviews and fix all the ignored findings?"* — executed under the v0.4.259 law (findings land in their entirety, no human gate).

**The gap that made this necessary.** c23's own verdict reads *"Nothing was edited this cycle"* — 38 findings, none landed. c24's 79 were triaged but its codification plan named only the 24 converged items. This entry closes the accumulated backlog.

**Doc-vs-tool mismatches (each verified against its own `--help`/usage block, not against the law):** `SKILL.md`'s directory-layout law described a **flat** `tools/` tree while the fleet is grouped one level per function (`audit/` `git/` `harvest/` `issue/` `notify/` `ship/` `smoke/` `state/`) · the BUILD-TRIGGER named `oc-deploy ship <full-sha>` where the tool takes `--sha` · `oc-log-search`'s `--log <f>` is really `--log-dir <P>` · `oc-commit`'s `--state` is comment TEXT, not a dir · `oc-harvest-dispatch` needs a verb (`vet`|`dispatch`) · `oc-questions`' verb list omitted `withdraw`, which is live in `_VERBS` · `oc-wt`'s `--force` is a flag, not a verb · `README.md` advertised the RETIRED `oc-prchecks --notify` · `harvest.md` cited `claim-ref <issue>` where the tool takes a **uuid** · `editor.md`'s canonical tools anchor was still flat.

**Citation and duplication class:** `editor.md` carried a dead pointer to a `Skill-dir resolution` section that exists nowhere · `harvest.md` cited its own `Phase 4`, which lives in `editor.md` · **two different v0.4.170 findings shared the label `Finding H-1`** — the row number is the immutable discriminator the corpus already requires, so the colliding label is dropped · `review-lenses.md` pointed at the `review-battery` boundary form that `hq.md` now explicitly forbids.

**CHANGELOG correction.** The v0.4.259 entry mis-attributed `ba0aac61` to **#594** (its own trailer is **#595**) and left `c0322e51` unnamed (its trailer is **#596**) — an attribution taken from row adjacency rather than from the commit's own trailer. Both corrected; `grep -n -E '#59[456]'` now resolves each.

**Brain-file class (ops profile, not git-tracked):** `AGENTS.md` named `[memory] external_paths` — the live key is the array-of-tables `[[memory.extra_paths]]` with `path`+`pattern` · `TELEGRAM.md` still framed `tg_*` as *"the primary path in this profile"*, superseded by the 2026-09-04 owner identity law · `BOOT.md` pointed at `~/srv/rs/opencrabs` and `~/.opencrabs/source/`, neither of which exists on this box (the source tree is `/root/opencrabs`).

**Bundled and named** (C8): `9b494218` — `oc-issue-create`, the creation-time parent gate (Toolsmith, from Triage's law order) · `d834a6d2` — this sweep.

**LOC** (8-file corpus, `sum(1 for _ in open(f))`, LINES READ): 3648 → **3650** (+2, the `editor.md` anchor replacement).

## v0.4.259 — the Duty 4/6 fix gate is removed: reviewers' findings land in their entirety

**Owner order, 2026-09-25 21:29Z, verbatim:** *"update your duty 4 and 6 laws so that next time reviewers findings are not wasted but fixed in their entirety. remove the human gate fro the duty 4 and 6 fixing process"*

**Why it was needed.** Duty-6 cycle `20260925-c24` produced **79 findings**. My own verdict's codification plan named only the **24 converged items** and silently dropped **17 law findings** from reviewers A, H and D — a partial plan wearing a complete plan's shape. The owner caught it by asking why the plan's count did not match the findings'. The old Duty 6 step 5 was the cause: *"Mechanical fixes land directly as ONE version batch. Anything SEMANTIC goes to the owner as proposals"* — which makes the semantic half of every cycle's output wait on an approval that historically does not come.

**The law now.** A third **EXCEPTION** bullet sits beside the Toolsmith `tools/**` and Triage affinity carve-outs in `fleet-directives.md §Discussion links + fix-approval gate`. Two halves:

- **COMPLETENESS ("not wasted").** The cycle verdict MUST enumerate every finding by ID and assert that the partition sums to the census count. An accepted finding with no landed home is a **cycle-completion failure**, never a scheduling choice. Converged findings are ONE landing carrying every contributing ID. A finding whose fix belongs to another owner (daemon/carrier source, upstream repo, `tools/**` code) is **ROUTED** — routed is a disposition, dropped is not.
- **NO GATE ("remove the human gate").** No `plan init mode="design"`, no diagrammed card, no `/execute`, no per-finding or per-cycle owner approval. HQ decides the fix shape, lands it in the cycle's version batch, and reports what landed. **The verdict table is the RECORD of what was decided and landed — it is not a request, and it does not wait.**

**Autonomy is over the DECISION, never over the RECORD** — same shape as the two carve-outs above. **Scope is exactly Duty-4/Duty-6 findings on this factory's law surface**; it does NOT extend to daemon/carrier source (Editor territory), upstream PRs, `tools/**` code (Toolsmith), the lens-catalog standing triggers, or the owner-gated actions in `AGENTS.md` (daemon restarts, pushes, binary swaps, the MODE register). Item 2 remains absolute for every other design.

**Sites changed.** `fleet-directives.md` (the EXCEPTION bullet) · `hq.md` Duty 4 step 5 (*"ships ONLY on his word"* → HQ lands every accepted proposal itself) · `hq.md` Duty 6 step 5 (mechanical-only landing → **every** accepted finding, mechanical AND semantic) · `hq.md` Duty 6 rationale (*"the owner gate keeps the set honest"* → HQ's own completeness check keeps it whole) · ops `AGENTS.md` always-loaded pointer.

**LOC** (8-file corpus, `sum(1 for _ in open(f))`, LINES READ): 3645 → **3648** (+3).

**Bundled and named** (C8): `ccd8fc9f` — this law change · `bdaffb98` — names `f7f8dcf5` (#594) in the v0.4.258 entry · `ba0aac61` — `oc-questions list --lane` printed the FLEET open count against the filtered lane count (Toolsmith, #595) · `c0322e51` — `oc-ledger stamp` accepts a ref-less LANDED closing row, success closing nothing (Toolsmith, #596).

**Also landed in this window — a regroup regression, owner-facing.** `questions.l1979.ru` returned **502** on every answer submit: the vpn backend (`/opt/questions/backend.py:37`) hardcoded the **flat** tool path `tools/oc-questions`, which the v0.4.255 regroup moved to `tools/state/oc-questions`. The backend's own log carried it verbatim — `answer rc=127 err=bash: line 1: …/tools/oc-questions: No such file or directory`. Fixed to the new path (backup `backend.py.pre-regroup-fix`), service restarted, verified: **409** on an answered qid, **no rc=127** since. This was the **fifth** regroup regression and the first outside the repo — the sweep had covered law, crons, tools and the battery, but not a hardcoded path in a service on another host. The same sweep found one more live consumer, `321-harvest-state.md` (its wake-gate command and two refs), re-pointed.

## v0.4.258 — Duty-6 cycle c24: 79 findings triaged, the 24-item law batch landed, and the codification gap closed

**What this version is.** Duty 6 cycle `20260925-c24` ran 11 lenses (corpus hash
`dc1118418af2…`, 12 files / 186 sections) and produced **79 findings** — 47 on the law
corpus, 28 on `tools/**`, 2 owner decisions, and 2 cosmetic. The first cut of the
codification plan named only **24 items** and silently dropped 17 law findings from
reviewers A, H and D. The owner caught it ("we had 70+ findings. Your plan contains
much less"), the plan was extended to 12 tasks, and this version lands the result.

**The gap, named so it is not repeated.** My own verdict's "Codification plan" grouped
findings by *theme* and named the converged subset, which made a partial plan look
complete. The fix is mechanical: enumerate every finding ID and assert the partition
sums to the finding count. `57 ACCEPT + 5 AMENDMENT + 5 ALREADY COVERED + 0 REJECT = 57`
held for the Duty-4 cycle the day before; nothing asserted the equivalent for Duty 6.

**Landed, by file.**

- **`review-lenses.md`** (`57bfb719`) — the catalogue's own brain-scrub self-reference
  named a heading that does not exist (three lenses found it independently); EFFICIENCY
  was declared a sixth FAMILY while the method's map recognises five, so it is demoted
  to a RULE BLOCK; eight provenance-sediment sites stripped.
- **`hq.md`** (`9246a3c9`, and `d88a66ea`) — the dead `§CONSENT REGISTER` ref (it is a
  BULLET under `## Hard rules`); the `:238` claim that every brief names exclusions and
  carries a mechanical slice, **both false** of the artifact (2 of 11 briefs carry an
  EXCLUDES clause, 0 carry a slice — the slice rides the spawn prompt); the cadence
  paragraph's stale `oc-ledger:913`/`:914-915` citations (**~365 lines off** — the regex
  is at `:1278` inside `cmd_cadence`); the close-form example missing the **leading `v`**
  its own regex requires; and the two-`reviews/`-roots rule (**D-F5**: the state-repo
  root is canonical, the skill-repo root is frozen — three cycle ids exist in BOTH, so a
  sweep keyed on the id alone would hit the frozen copy).
- **`SKILL.md`** (`c26be37f`, `d88a66ea`) — six findings including the router summary
  denying the fifth role file; plus the **owner's UNION delta** (the issue-cluster
  definition built its dependency leg from the COMMIT/FILE graph alone and closed with an
  exclusivity clause that foreclosed the gh relationship graph — amended to the union,
  with the closure asymmetry recorded: transitive file overlap collapses the whole delta
  to 3 components, so only 1-HOP overlap is usable); plus the **#580 per-surface ruling**
  (Telegram flood limits are enforced per surface, so a 429 pauses only the offending
  arm — the ruling existed only in `governor.rs` and in NO skill file, which is why a
  lane came within one step of proposing an aggregate gate that would have reversed it).
- **`editor.md`** (`2e5a7191`, `97f8d57c`) — three findings, then six more the verdict
  dropped: the restated Telegram-surface enumeration (cut to the editor delta), the
  Rollcall re-enumeration (reduced to a pointer), four `§ISSUE ROUTING` re-points, the
  `Role Boundaries` heading unified with `toolsmith.md`, and the `Telegram surface`
  section names disambiguated (three files named three different sections the same way).
- **`fleet-directives.md`** (`2fa67fc7`, `d88a66ea`) — four findings: the trailer-retention
  rule now mandates the TOOL (`oc-attrib --trailers-only`) instead of a hand-rolled
  `git log | interpret-trailers`; two dead `§Autonomous closure` refs re-pointed to
  `triage.md §Duty T5`; six provenance-sediment sites stripped; and the duplicate
  role-resolution sentence **deleted rather than deduped — it was FALSE** (the runbook
  claimed `oc-roster --role` is "accepted and silently ignored"; measured rc=0 and
  byte-identical to the canonical form).
- **`upstream-merge-runbook.md`** (`eeba63af`, `d88a66ea`, `c291bdae`) — the ledger-hygiene
  block **promoted out from under a RETIRED heading** (live law a reader would have
  skipped); the "All 15 resume jobs" count restated as a POPULATION with its predicate
  (it could not be re-derived from its own parenthetical: 12+3+1=16, one left armed); and
  the resume-idiom mechanism sentence corrected — **"Nothing tracks it for you" was
  falsified by #508 within a day**, so the obligation is kept while its reason is fixed
  (the sweep is EVENT-driven, and 0 of 58 cron rows invoke `commit-pending`).
- **`README.md`** (`af265896`) — the §Layout rows described `editor.md` as owning Phases
  0–7b and `harvest.md` as 7b/7c, both wrong since the v0.4.250 role split; `tools/instruments/`
  was missing.
- **`triage.md`** (`eeba63af`) — both retired-duty tombstones now name their successor.
- **The gh-relation read trap** (`6c1c29c4`) — reported by Triage and **reproduced
  first-hand**: `gh api … --jq '.parent.number'` returns a confident null for EVERY issue
  (#434 → null, while `--json parent` → 332), and the null is indistinguishable from "no
  parent". It produced one recorded false negative and defeated a GUARD that used it to
  skip already-parented issues. A verification instrument and a guard need the same
  authority.
- **`99917304`** (Toolsmith) — the v0.4.255 `tools/` regroup's two **silent** regressions,
  both mine: `oc-claims-single-source` derived its root from `dirname(__file__)`, so after
  the regroup it scanned **1 of 36** units and still printed `ok`; `oc-watcher-audit`'s
  primary `lib/` reach broke and was masked by a hardcoded fallback inside a bare
  `except Exception: pass`. Fixed at the root derivation (walk up to the dir holding
  `lib/oc-root.sh`) plus a root-IDENTITY assertion, because no arithmetic leg can catch a
  narrowed root. Also `oc-lint-laws` gains the two legs whose absence let #575 ship, and
  `oc_tools_dir` gains the symlink guard the bootstrap calls load-bearing.
- **`f7f8dcf5`** (Toolsmith, #594) — **four** dead `negctl` controls, not one: each pinned a
  flat `tools/oc-*` path, so after the v0.4.255 regroup each reported "guard is inert"
  instead of testing anything, and two also read a pre-regroup baseline sha that returned
  empty, leaving the load-bearing arm **skipped** and the run INCONCLUSIVE rather than
  green. Repaired by giving each location one `REL` home. Two further defects surfaced while
  fixing them: the #576 in-flight note asserted a send was in flight on the `no_route` path
  that provably sends nothing (now an append-only `NOT SENT` row that deliberately omits the
  marker, so a retry is not suppressed); and the battery's `extract_chunk` stops at
  `verdict=PASS`, so **a section placed after the receipt write extracts to an empty chunk
  and runs zero legs while the summary still prints clean** — section 78 landed there and the
  count read 255 before and after. Battery 255 → 261.

**Bundled commits (14).** `99917304` (#589/#591) · `f7f8dcf5` (#594) · `57bfb719` · `9246a3c9` ·
`c26be37f` · `2e5a7191` · `eeba63af` · `2fa67fc7` · `af265896` · `97f8d57c` · `d88a66ea` ·
`6c1c29c4` · `c291bdae` · `4d4a612b`.

LOC (8-file corpus, `sum(1 for _ in open(f, encoding='utf-8'))`, per the v0.4.253 convention): **3610 -> 3645** (+35). Anchor `8c31a293` reproduces 3610 exactly. Per file: `SKILL.md` 730 -> 767 (+37) · `fleet-directives.md` 650 -> 646 (-4) · `editor.md` 534 -> 531 (-3) · `hq.md` 333 -> 337 (+4) · `upstream-merge-runbook.md` 430 -> 431 (+1). The corpus EXCLUDES `review-lenses.md` and `CHANGELOG.md`; transposing those two files is the scope error that produced a wrong figure earlier in this session, so the membership is stated here rather than assumed.

**Not landed, stated rather than omitted.** The **2 owner decisions** (B-H1: the runbook is
46.8 % a retired section with live law nested inside it; B-H2: `SKILL.md` past its own line
budget) are held for the owner. **J-F1** was reassigned out of the HQ batch — its fix is in
`tools/tests/run.sh`, which is Toolsmith code. **F-M4** was honestly **not reproduced** by
the Toolsmith rather than silently "fixed". And 76 of the 79 findings remain open beyond
the ones above; the full disposition is in `reviews/20260925-c24/VERDICT.md`.

## v0.4.257 — two dead law anchors fixed, and ISSUE CLUSTER enters the ontology (reviewer H + Triage)

**Both reported independently, both verified at source before a word was written.** The class is the same: a citation that resolves to nothing, which is worse than no citation, because a reader follows it and finds an empty room.

- **The soak anchor was dead in TWO places** — `fleet-directives.md:44` (the freeze-retirement tombstone's replacement table) and `upstream-merge-runbook.md:343` both cited `upstream-merge-runbook.md §24-Hour Feature Soak`. **No such heading exists anywhere in the corpus**: `grep '^#+ .*[Ss]oak'` over the law files returns only CHANGELOG history entries. The soak law lives in `§Upstream-merge cadence · HARVEST LAW · NO-HOLD` at runbook:278, which is what both now name. Reviewer H's verdict framed it precisely: the freeze retirement was **complete as a removal, incomplete as a hand-off** — one of the two replacement pointers led nowhere.
- **ISSUE CLUSTER was load-bearing and undefined** — used in four live places (`SKILL.md:54` the HARVEST role row, `harvest.md:8/333/343/346`) and codified in neither vocabulary surface: not in `SKILL.md §Glossary`, not in the fork's `ONTOLOGY.md`. Its ONLY definition was a `--help` string at `tools/harvest/oc-harvest-census:74`, now lifted into the glossary verbatim, with NOT-references for *convergence cluster* and the retired freeze T-groups — the glossary header forbids one concept under two names. **Precision on Triage's report:** the three-sense collision is real across the corpus, but in LIVE law only the harvest sense appears; the other two are CHANGELOG-only.
- **Not fixed here, and it is not mine** — `ONTOLOGY.md:105` points at `fleet-directives.md §Glossary`, a section that does not exist (`grep -iE '^#+ *(glossary)' fleet-directives.md` → rc 1); the glossary is at `SKILL.md:383`. That file is tracked in `/root/opencrabs` — **daemon source, Editor territory** — so it is routed, not edited here.
- **Bundled in this range:** `c984e84f` (this law change).

LOC (8-file corpus, `sum(1 for _ in open(f, encoding='utf-8'))`, per the v0.4.253 convention): **3610 -> 3619** (+9, all in `SKILL.md` 729 -> 738; both anchor fixes are same-line replacements, net 0). Anchor `8c31a293` reproduces 3610 exactly. **A scope error was caught here, not smoothed over:** a first computation returned 3474 because the corpus list carried `review-lenses.md` IN and `upstream-merge-runbook.md` OUT — the reverse of what the entries state. The predicate is worthless if the corpus membership is guessed, and this is the second time this session the same two files were transposed.

`oc-lint-laws --strict`: **8 findings before, 8 after, byte-identical finding set** (proved by stashing the edits and re-running, then diffing the located findings) — this edit adds zero. All 8 remain the documented `flag_known` false-positive class.
## v0.4.256 — stuck lanes REGISTER, never re-ask (owner order 2026-09-25)

**Owner directive, verbatim:** *"remove from agents.md"* + *"in the triage lane mention that stuck lanes should use the questions tool to register their questions"* — OC Dev Factory.

- **`triage.md` Duty T4 gains the routing rule** — a lane found held on an owner decision is routed to the **Open Questions register** (`tools/state/oc-questions ask --factory <KEY>`). The bullet names the two things Triage must NOT do: tell a stuck lane to **re-ask in its own topic** (a daily topic ping is noise, not pressure — once registered, the register's own `asked_at` age is what re-surfaces the question), and **register on the lane's behalf** (the tool derives the asking session from `OPENCRABS_SESSION_ID` and REFUSES an unbound session, because a cron session can never receive the answer).
- **`AGENTS.md` loses its copy of the register clause** — the always-loaded brain file had grown an 11-line duplicate of the canonical text in `fleet-directives.md §Open Questions register`, which is the one-concept-one-home violation the memory-routing law names. The canonical clause and the pointer to it remain; 717 -> 706 lines. (AGENTS.md is a brain file, not corpus law, so this does not move the LOC figure.)
- **Bundled in this range:** `2c0e25f0` (oc-harvest-census clusters — the cluster surfacer the soak gate reads) · `ab510ea3` (this law change).

LOC (8-file corpus, `sum(1 for _ in open(f, encoding='utf-8'))`, per the v0.4.253 convention): **3608 -> 3610** (+2, all in `triage.md` 402 -> 404).

## v0.4.255 — the oc-* fleet grouped by function (owner directive 2026-09-25)

**Owner directive, verbatim:** *"Your tools dir should have subdirs"* — OC Dev Factory. v0.4.254 delivered the five kind-based subdirs and HELD the grouping; this entry lands it.

- **44 executables grouped into 8 functional subdirs** — `audit/` (5) · `git/` (5) · `harvest/` (8) · `issue/` (4) · `notify/` (2) · `ship/` (9) · `smoke/` (2) · `state/` (11). `tools/` now reads as: the `oc-*` fleet (grouped), plus `lib/` `tests/` `archive/` `docs/` `instruments/` as the kind-level subdirs.
- **Gated on the depth-agnostic resolver** (`479bee01`) — the hold was correct: every tool reached siblings as `$TOOLS_DIR/oc-x` from its own dir, so ANY move broke the fleet. 42 tools carry the bootstrap; the three pure-python tools (`oc-issue-dispatch`, `oc-harvest-census`, `oc-harvest-dispatch`) walk up in python instead, and **`tools/lib/oc_root.py`** is the shared twin.
- **Back-compat verified:** a shim at the old flat path (`tools/oc-x` -> `tools/<group>/oc-x`) still resolves the real root, because `readlink -f` sends the walk to the real script's directory. A caller that has not been updated keeps working.
- **Re-pointed in the same landing:** 187 code reaches, 148 law references across 9 live law files, the 3 law `.md` under `tools/docs/`, the `oc-lint-laws` corpus **and its tool lookup**, the 18 cron prompts that invoke these paths, and the battery's own fixtures whose `mkdir`/`cp` targets moved with the tools (5 in `oc-deploy`, 1 in `oc-review-persist`, 3 in `oc-ship-chain`, 2 in `run.sh`).

**The defect the move exposed — a check that could not fail.** Section 60's fleet-wide `--help` contract check globbed `"$TOOLS_DIR"/oc-*` **flat**, so after the regroup it matched NOTHING: the section ran zero legs and reported success, hiding a 43-leg drop in the count (249 -> 206) that read like a genuine reduction. It now enumerates `"$TOOLS_DIR"/oc-*` **plus** `"$TOOLS_DIR"/*/oc-*`, skips `lib/tests/archive`, and asserts a **floor of 30** enumerated tools — so a future layout change reddens there instead of quietly shrinking the leg count. Measured: **43 tools enumerated, 250 PASS / 0 FAIL** (249 before the move, +1 for the floor leg).

**Also reaped: 850 stale `/tmp/oc-snap-*` mirrors, 2.3 GB.** `oc_snap_reap` is correct — it checks the name pid is gone AND that no live process references the mirror path — but nothing calls it on the battery path, so every battery run left mirrors behind. One day's runs accumulated 850 (2.3 GB, /tmp on the root filesystem). Routed to the Toolsmith as a finding rather than patched here; the reap itself was run via the tool's own function.

**Corpus hygiene note:** the acceptance criterion this step originally carried (`grep -c 'tools/oc-' *.md` = 0) was unsatisfiable — `CHANGELOG.md` alone holds 89 frozen-history references, and `reviews/**` holds more. Frozen history is deliberately NOT rewritten: it records what the paths were at the time. The live-law criterion is the one that matters, and it reads **0**.

**Bundled commits, named:** `5fb053bd` (the move) · `3f4213f3` (battery recursion + floor) · `6cd0ac43` (law re-point) · `f5571fdb` **#581** — the Toolsmith's gate-forward fix across a content-identical rebase, which landed in this range after the entry was drafted.

LOC 3608 → 3608 (net 0; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `05b530e1`, which reproduces the v0.4.254 entry's 3608 exactly). Every law edit in this landing is a same-line path replacement, so the corpus is unchanged in size — which is itself the check that nothing but paths moved.

## v0.4.254 — tools/ gains subdirs by KIND, plus the resolver that unblocks grouping (owner directive 2026-09-25)

**Owner directive, verbatim:** *"Your tools dir should have subdirs"* — OC Dev Factory.

- **`tools/instruments/` declared** — the home for corpus-agnostic instruments that review an ARBITRARY corpus, so they never sit in the `oc-*` fleet namespace (the JEV rule-xref instrument is the first tenant). Nothing moved: the directory is a declared home, so it cost zero.
- **`tools/docs/` created** — the three law `.md` files moved off the executable level: `RC-CONTRACT.md`, `HEALTH-CHECKS.md`, `HEALTH-CLASSES.md`. Law and executables no longer share one directory.
- **Depth-agnostic tools root** — `tools/lib/oc-root.sh`, with 42 tools converted. Every tool resolved siblings as `$TOOLS_DIR/oc-x` from its own dir — a one-level depth assumption that made ANY grouping unsafe.
- **The `oc-*` grouping is HELD, with measured reasons** (recon `n=11211`): the approved acceptance criterion read `grep -c 'tools/oc-' *.md` = 0, which is unsatisfiable because `CHANGELOG.md` alone carries 89 frozen-history refs; the real reach count is **102**, not the 35 the design assumed, and **91 of those sit in `run.sh`**; and 30 of 44 tools are singletons, so a `ci/ harvest/ state/ audit/` split would be editorial judgement applied 30 times. `oc-*` is already the namespace AND the public interface, so a subdir component carries no information a caller needs — bought with 18 cron prompts and ~148 law refs. The five kind-based subdirs the directive literally asks for are delivered.

**Two findings the resolver work produced, both load-bearing:**
- **The root marker must REJECT a symlinked `lib/`.** `/tmp/lib` was a symlink to the real `tools/lib` (dated Sep 19, NOT created by this repo), so a walk that followed symlinks stopped at `/tmp` for every script beneath it — `TOOLS_DIR` became `/tmp` and `oc-ship-chain`'s journal legs read **rc=127**. Negative control: re-creating the symlink no longer changes the result.
- **The bootstrap must FALL BACK to the script's own dir.** Many selftests copy a tool into a temp dir beside **fake** siblings and assert the tool uses those. An unconditional walk escapes the fixture and silently defeats the isolation — measured by breaking three battery legs before the fallback was added.

**`*.pre-*` gitignored.** Lane-created pre-edit backups accumulate, nothing reaps them, and `oc-ledger`'s stray-guard reads a full `git status --porcelain` — so ONE untracked `.pre-*` blocks every bump with `die 7`. Measured live: four such files held the v0.4.252 bump. (Corrects an earlier claim of mine: `tools/__pycache__` was ALREADY ignored in both repos; the unignored class was `.pre-*`.)

**Bundled:** `6f34c3c9` (the `instruments/` declaration) · `344ba94e` (the `docs/` move) · `479bee01` (the depth-agnostic resolver) · `32ab96ed` (the `*.pre-*` ignore) · `ab8c4776` (#577 — an empty Clarify is refused, the clarifying state renders) · `cd3e3475` (#578 — `amend` clears `answer_kind` with the answer). LOC 3606 → 3608 (predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `4f9261ed`, which reproduces the v0.4.253 entry's 3606 exactly). Only `SKILL.md` changed (728 → 730 — the `instruments/` declaration and the `docs/` note); the three moved law files were never corpus members, so their move cost no lines.

## v0.4.253 — Duty 6 runs a mechanical corpus pack at cycle open (owner directive 2026-09-25)

**Owner directive, verbatim:** *"First let's try to build it into the Opencrabs DEV Factory Duty 6"* — relayed by lane `ef83024b`.

- **Duty 6 step 0** — the law-corpus pack runs at cycle open, keyed to the SAME cycle id, evidence at `reviews/<cycle-id>/evidence/`, with the **corpus hash recorded as the report's validity anchor**. Byte-identical on re-run by construction (the open instant is an input, never the wall clock). Called by **absolute path** for the trial; a missing or failing pack is **reported, never silently skipped**.
- **Duty 6 step 2** — each family brief carries its mechanical slice (sentence-match, near-title, dead-reference) with the corpus hash. Layer 2 is **REPORT-ONLY**: its gate failed a pre-registered test (precision 0.111 / recall 0.126 against bars 0.70 / 0.40, n=66), so it never creates or routes a finding.
- **Coverage limit stated in law** — the pack reads top-level `*.md` only, so `tools/RC-CONTRACT.md`, `tools/HEALTH-CHECKS.md` and `tools/HEALTH-CLASSES.md` (~139 KB of law) sit **outside** the corpus until the declared-manifest leg lands.

**Trial evidence (reproduced first-hand, rc=0):** 12 files · 186 sections · 66 sentence matches · 16 near-title pairs · 7 dead refs · corpus hash `8bf9518a997d` · 8.53 s · coverage law reports not_read 109 files / 2 056 457 B.

**Bundled:** `aa0875bc` (this change). LOC 3592 → 3606.

## v0.4.252 — the tool table is corrected against the live tools (owner order 2026-09-25)

**Owner order, verbatim:** *"assign fix tool table docs"*.

The table's own defect: `oc-issue-dispatch` was documented as `[--auto] [--issue N] [--lane U]`, and **neither flag exists**. The real interface is a **POSITIONAL** issue number plus `--to <uuid>`, with `--force`, `--allow-landed`, `--redispatch` and `--budget-secs N` all undocumented — the last three being the LEG-SCOPE additions. Verified against the tool's own `--help` and `tools/RC-CONTRACT.md` row 36, not against another doc. Found live: `--issue 574` errors, and the correct form was needed to dispatch #574.

**`oc-questions` was absent from the table entirely** — the sanctioned blocked-on-you channel, live since #547, so a lane reading the table could not discover it. Added with its verb set, the `ask --factory <KEY>` contract, the env-derived session/lane rule, the unbound-session refusal, and the constant readable URL with per-lane anchors.

**Three stale `editor Phase 7` references re-pointed to `harvest`** (`oc-pr-atomicity`, `oc-harvest-sweep`, and the reserved-branch-namespace paragraph) — residue of the v0.4.250 role split that its own step-7 criterion missed, because that criterion grepped the four ownership sites and these were three other places in the same file.

**Four of the five line citations in the `oc-lint-laws` row were stale at this revision** and are corrected: `SKILL.md:99`→`:102`, `:352`→`:455`, `hq.md:108`→`:117`, `RC-CONTRACT.md:55`→`:40`. Only `hq.md:31` still held. This is the pointer-drift class the 2026-09-22 ruling names — a citation asserts a ROLE as well as a number, and these had drifted silently. Corrected because this edit shifted one of them a further line.

**Audit method, so it is re-runnable:** every flag documented in the table was extracted and tested for presence in its own tool — **0 of 46 rows now document a flag their tool does not carry**. Completeness was measured the other way: **42 of 45 live `oc-*` tools are listed**. The three absentees are deliberate — `oc-waiter` is a RETIRED v0.4.135 stub documented in `README.md:52`, `oc-questions-render.mjs` is an asset of `oc-questions` rather than a tool, and `oc-issue-dispatch.pre-*` is a backup file, not a tool.

**Bundled tool fixes from the Toolsmith lane** (named per the v0.4.239 law): `a0c8907a` (#568, the `goal` domain added to `AFFINITY_KEYWORDS` — the table half of the Triage grant) · `c64ea5a6` (#573, the questions backend no longer forwards the submit button's label as a choice) · `d2e9b2c0` (#575, `oc-lint-laws` `DEFAULT_CORPUS` names the renamed law file, so every run died rc 3 before checking anything — the regression this entry files) · `c1b02cfd` (#571, `oc-questions --help` documents the real interface, and `withdrawn` becomes a real verb) · `a75cdd53` (#576, an in-flight dispatch is now visible in the ledger before it blocks) · `537ece82` (#566, the `oc-smoke-evidence` selftest TOCTOU on the peer fd closed — the last of these landed 12:29, after this entry was first written, so they are named here rather than omitted).

**A regression this edit surfaced, filed not fixed:** `tools/oc-lint-laws:70` still names `editor-upstream-pr.md` in its `DEFAULT_CORPUS`, so the tool exits **rc 3** (corpus file missing) — the v0.4.250 rename updated the law but not the lint tool's corpus list, and `harvest.md` is consequently not linted at all. `tools/**` is the Toolsmith's carve-out, so it is dispatched rather than edited here.

LOC: 3591 -> 3592 (net +1; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `162fea49` which reproduces the v0.4.251 entry's 3591 exactly). Only `SKILL.md` changed (727 -> 728, the added `oc-questions` row); the four citation corrections and the three Phase-7 re-points are same-line replacements. `fleet-directives.md`, `editor.md`, `harvest.md`, `hq.md`, `triage.md`, `toolsmith.md` and `upstream-merge-runbook.md` are unchanged.

## v0.4.251 — Triage gets affinity-table and lane-repurposing authority (owner order 2026-09-25)

**Owner order, verbatim:** *"New law - You have the authority to alter the affinity table and repurpose / rename lanes."* (2026-09-25 ~10:20Z, OC DEV Factory Triage topic.)

Codified as a sibling of the Toolsmith `tools/**` carve-out in `fleet-directives.md` §Discussion links + fix-approval gate — same shape: **autonomy over the DECISION, never over the RECORD**. Triage may edit `AFFINITY_KEYWORDS` in `tools/oc-issue-dispatch` and repurpose/rename lane rows via `oc-ledger promote <uuid> <role> --feature X`, with no per-change owner approval and no design gate — but it still owes a report of what it decided and landed, and a keyword change must carry its own precision/recall measurement against a STATED ground truth, because a keyword set is a heuristic and its error rates are the thing being chosen.

**Landing lane (HQ ruling, same day):** Triage lands the `AFFINITY_KEYWORDS` edit ITSELF on the skill repo — branch plus the `pr-checks` CI gate, per the gated landing flow — rather than handing the measured keyword set to the Toolsmith as a work order, which would make the grant hollow. Any OTHER part of `oc-issue-dispatch` returns to Toolsmith ownership.

Origin: `oc-issue-dispatch --auto` proposed a goal-loop fix (#567) to a suggest-options lane because `AFFINITY_KEYWORDS` carried no `goal` domain (12 domains, none covering `src/brain/goal/`). First application under the grant: `oc-ledger promote 9fa7c71a` (ledger `n=11011`), after which `select_best_lane(#567)` returns the goal-domain owner instead of a UI lane.

**Bundled tool fixes from the Toolsmith lane** (named per the v0.4.239 law): `f7175f12` (#501, `oc-commit` cross-checks the derived Issue-Ref against the branch name and the subject's trailing `(#N)`, refusing `rc 3` and naming both numbers on a contradiction, with `--issue N` kept as the override — the specimen being work on #500 committed under #548 because #548 was the newest claim, which then posted an implementation comment onto the wrong issue) · `efb5f230` (#565, the C8 self-commit skip now reads the Issue-Ref TRAILER rather than the subject — a subject is prose, the trailer is the contract) · `499bf062` (#547, the oc-questions factory-set model: `--factory` required and the factory key IS the standing set id, `--lane` removed and resolved from the asking session's own binding, an unbound session refused non-zero, constant slug, lane anchors, per-question return address) · `13bbb7f4` (#547, the answer form choice resolved by MEANING rather than position) · `a52f40a4` (#569, a typed answer is never discarded).

**Bundled law commits, named per the same law:** `eb22f94c` (the Triage affinity-table and lane-repurposing grant) · `ff8244f7` (the Open Questions register: one standing set per FACTORY, `--lane` removed, constant readable URL with per-lane anchors, the store line and the corrected verb list) · `acb824ae` (topic names stay in sync with their lane, `<= 22` characters, the same-turn rename rule, and the rename mechanism verified at source).

LOC: 3536 -> 3591 (net +55; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `c2efd097`, which reproduces the v0.4.250 entry's 3536 exactly, with `harvest.md` read as `editor-upstream-pr.md` at that ref because the rename postdates it). Per file: `harvest.md` 335 -> 364 (+29, the v0.4.250 rename and its assignee sweep) · `SKILL.md` 708 -> 727 (+19, the topic-naming clause and the HARVEST role row) · `fleet-directives.md` 647 -> 650 (+3, the Triage grant, the `--lane`-removed correction, the one-set-per-factory bullet, the constant-URL/anchor bullet and the store line) · `upstream-merge-runbook.md` 427 -> 430 (+3, the PHOP stage-4 re-owner and the retired resume idiom) · `editor.md` 533 -> 534 (+1, the upstream claim stripped); `hq.md`, `triage.md`, `toolsmith.md` unchanged. The always-loaded pointer landed in the ops brain `AGENTS.md`, which is NOT a corpus member.

## v0.4.250 — HARVEST becomes a fifth role; harvesting leaves the editor lanes (owner order 2026-09-24)

**Owner order, verbatim:** *"I want to centralize harvesting again. I want the harvesting step be removed from the editor lanes."* (2026-09-24, OC DEV Factory.)

The role split: **HARVEST** owns port → CI gate → file → follow; **editors stop at smoke evidence**; **Triage surfaces, counts and prioritises but never ports or files**. Triage also gets the mechanised tier surfacer (`oc-harvest-tiers`, dispatched separately to the Toolsmith) — the primary unit is the **issue cluster**, because Triage measured the tier map covers only ~52 of 345 fork-only commits, so a tier-only view would render 85 % of the backlog invisible.

**The four sites that made the editor a harvester are all re-pointed:** `editor.md` (the upstream-contribution claim), the SKILL.md role row 4, the PR SHIPMENT LAW row, and `upstream-merge-runbook.md`'s PHOP stage 4. The procedure file itself was **renamed, not rewritten** — `editor-upstream-pr.md` → `harvest.md` — because it already was exactly the harvest procedure (335 lines, Phase 7 → 7c → reference rules → dependent-PR law); `git mv` plus a six-mention assignee sweep achieved the split with a 25-line diff.

**The resume idiom is RETIRED** (`upstream-merge-runbook.md` §Harvest patrol suspension & resume idiom), with all 15 `oc-harvest-*-resume` jobs disabled the same day (ledger `n=10828`); only `oc-harvest-403-resume` stays armed because it is event-driven — it reads the MODE register and exits 0 silently while DEGRADED. The idiom's body is kept as history, and its general-law traps (tracked state file, date-keyed one-shot, ~24 h floor) are explicitly preserved for any future resume job.

**Rejected-upstream is now a TYPED state decided by a CONTENT DIFF** (`harvest.md` §Rejected-upstream). Measured 2026-09-24 over every upstream PR with `mergedAt == null` — **48 examined, 18 (37.5 %) carry content already on `adolfousier/main`** — so PR state can never be the rejection signal. Specimen: PR #1611 reads "closed unmerged" while upstream `5d326aa12` cites `(#1611)`. Three outcomes (`applied-upstream` / `absent-upstream` / `unmeasurable`, the last never read as absent), two-stage confirmation by Triage, three dispositions for dependents (`exclude` / `salvageable` / `needs-owner-ruling`), and `manual_records` formalised as that field with **no removal path written**.

**Bundled tool fixes from the Toolsmith lane** (they rode this window and are named per the v0.4.239 law): `792bf2ad` (#559, harvest dispatch emits cherry-pickable commit order) · `611c97af` (#560, drift-check renders the post-ack verdict) · `555455cc` (#561, always deploy a page including a no-open-questions empty state) · `b37456a4` (#562, answered question swaps inline instead of loading a page) · `7fd4bba8` (#563, soak anchor gets a truthful class for the unresolvable case) · `ea2b7fec` (#564, a unit settled by hand is not re-proposed) · `b1307038` (this lane's follow-up to the v0.4.249 entry — it names that window's #547 commits; listed here because its SUBJECT mentions an issue number in prose, which the C8 leg's "carries an issue ref" test cannot distinguish from a commit that FIXES one).

**Frozen history untouched:** `reviews/**` and `CHANGELOG.md` hold 33 files' worth of references to the old file name and were deliberately NOT edited; only the live-law files changed.

LOC: 3536 -> 3572 (net +36; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `c2efd097` which reproduces the v0.4.249 entry's 3536 exactly). Per file: `harvest.md` 335 -> 364 (+29), `SKILL.md` 708 -> 711 (+3), `upstream-merge-runbook.md` 427 -> 430 (+3), `editor.md` 533 -> 534 (+1); `hq.md`, `triage.md`, `toolsmith.md` and `fleet-directives.md` are unchanged. The corpus member is now `harvest.md` (renamed from `editor-upstream-pr.md`), so the 8-file set is unchanged in composition.

## v0.4.249 — the Owner Push Freeze register is RETIRED (owner order 2026-09-24)

**Owner order, verbatim:** *"Remove the freeze register. It's stale. Now the concepts are soaking and degraded state with global harvest freeze"* (2026-09-24T21:04Z).

The per-group freeze register is GONE. Removed with it: the `json` block that was its machine-readable home, the T1-T18 / Tier-3 frozen table, the T3 disputed-release ruling, the pre-freeze-PR ruling, and all five rules. What replaces the section is a RETIRED tombstone naming the two concepts that supersede it and why the register was stale.

**Why it was stale, each leg verified before removal:** its enforcement leg never existed (the fail-loud reader was never built — that was open fork issue #358, now CLOSED NOT_PLANNED); its machinery leg was vacuous (`oc-harvest-dispatch-4h` disabled); and MODE=DEGRADED already performed the same hold globally — a second mechanism for one concept. Its bookkeeping was a 2026-09-18 snapshot: T9 merged by the maintainer, one release ever (T6), T3 disputed and unresolved.

**The two concepts that replace it:** SOAKING, unchanged, at `upstream-merge-runbook.md` §24-Hour Feature Soak; and **DEGRADED = GLOBAL harvest freeze**, now stated explicitly in the `SKILL.md` §MODE REGISTER — under DEGRADED no PR group of ANY feature is filed without explicit owner approval, and a soak maturing, a green census or an idle editor is never a release.

**Fourteen `oc-harvest-*-resume` cron prompts are left deliberately unpatched, with the reason:** they carry a leg instructing the lane to read the removed `json` block. They are covered rather than rewritten — the tombstone sits at the exact section those prompts name, so a lane following the stale instruction lands on the retirement note, and the family is inert while disabled (13 of 14; only the MODE-watching `oc-harvest-403-resume` stays armed, and it now reads the global DEGRADED gate). Rewriting them would have meant 14 full-prompt writes through a tool argument, each at risk of the tail-cut that silently truncates a long payload — a worse hazard than a stale pointer to a tombstone. Patch them if the family is ever re-enabled.

The `oc-ship-chain` / `oc-roster` hits for "freeze" are the **carrier** fork-rebase freeze — a different concept, untouched.

**Bundled in this range and named here per the v0.4.239 law (the C8 leg flagged them):** the Open Questions renderer port — `57006627` (#547 CLI), `96ebe4d0` (#547 notify/return path), `038667e9` (#547 C1-C7 owner directives), `88b70103` (#547 json-render page rewrite). All Toolsmith work on fork issue #547; none is law and none touches the files this entry describes.

LOC: 3584 -> 3536 (net -48; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `ca600ee2` which reproduces the v0.4.247 entry's 3572 exactly). The whole change is `fleet-directives.md` 695 -> 647; `SKILL.md` 708 -> 708 (the MODE REGISTER sentence is an IN-LINE append to an existing line, so it changes no line count).

## v0.4.248 (2026-09-24)

**Open Questions register — the owner-commissioned surfacer gets its lane-side contract.**

`fleet-directives.md` now carries the **Register** clause (owner-commissioned 2026-09-24, plan-approved): a lane whose next action needs an owner decision registers with `oc-questions` **in the same turn it parks**; the Register is the **only** sanctioned "blocked on you" channel; each question carries exactly two required inputs (`title` + Markdown `description`) with optional `options[]`, a `recommended` default and a Clarify action; **clearing is explicit** — silence closes nothing.

**The load-bearing clause is the return address.** It must be the **CALLING** session id, never a cron or renderer session: a card's `callback_data` routes to the session that SENT the card (`telegram_send.rs:1328`), so a substituted id orphans every answer. That is why the renderer is specified as a **persistent bound lane woken by cron**, never as a cron session.

Store: `~/.opencrabs/profiles/ops/questions/open.json` (answered sets -> `archive.jsonl`). Build carried by [#547](https://github.com/leshchenko1979/opencrabs/issues/547) (Toolsmith, `tools/**` carve-out).

**Bundled — the Toolsmith batch landing with this sync** (all on fork main, all verified as ancestors):
[#537](https://github.com/leshchenko1979/opencrabs/issues/537) `2d605b89` + `5280ab5a` — `oc_has`, a SIGPIPE-free literal substring test, plus removal of the false-negative idiom from 9 tools; · [#540](https://github.com/leshchenko1979/opencrabs/issues/540) + [#542](https://github.com/leshchenko1979/opencrabs/issues/542) `e605d4d1` — inverse namespace audit + `oc-ship-chain` gate-skip; · [#320](https://github.com/leshchenko1979/opencrabs/issues/320) `50b21b1e` — uuid-shaped `--by` warning; · [#529](https://github.com/leshchenko1979/opencrabs/issues/529) `716f8538` — the plan domain in the affinity table; · [#543](https://github.com/leshchenko1979/opencrabs/issues/543) `1ae68647` — boundary-aware affinity keywords; · [#546](https://github.com/leshchenko1979/opencrabs/issues/546) `16993ac7` — narrowed `oc-issue-dispatch` bash affinity vocabulary.

LOC: 3572 -> 3584 (net +12; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `ca600ee2` which reproduces the v0.4.247 entry's 3572 exactly). The whole change is `fleet-directives.md` 683 -> 695; no other corpus file changed.

## v0.4.247 (2026-09-24)

**LEG-SCOPE — both landed arms are ISSUE-scoped by implementation, so ONE leg's `done` marks the WHOLE issue landed, and the remaining legs become undispatchable AND invisible.**

`fleet-directives.md` §D1 now carries the leg-scope clause. Both landed arms — the ledger arm (`ledger_landed_issues()`) and the git arm (`fetch_landed_issues()`) — ask only *"did anything land for #N"*; neither asks *"did EVERY declared leg land"*. On an issue whose scope split names more than one owner, a `done` row stamped for one leg closes the claim (`oc_claims.open_claims(#N)` → **empty**, because `done` is a `LANDED_KIND`) and satisfies the ledger arm *and* the git arm at once, so the issue reads LANDED and every remaining leg can be neither dispatched (`RC_TARGETED_LANDED = 8`; `--allow-landed` is the escape hatch) nor **seen** — every sweep consumes the same predicate. The arms are not fixable one at a time: a leg-aware ledger arm changes nothing while the git arm vetoes on the same number.

**Origin: [#393](https://github.com/leshchenko1979/opencrabs/issues/393)** (owner order 2026-09-19; found by Triage lane `530c29ec`, re-verified first-hand here). The issue's own body names three surfaces with three owners — Editor `src/**`, **Toolsmith `tools/**`**, HQ skill-markdown. The Editor leg landed (`07b6372c4`); the HQ law leg landed; and `done` row **n=10159** ("smoke PASS verified for issue #393") closed the issue for dispatch. Verified: `open_claims(393)` → **0 rows**, and the only landing row targeting 393 is `[(10159,'done')]`. The identity read is masked the same way — the skill-repo index carries #393 via `5b9609b3`, a **LAW** commit whose changed files are `SKILL.md`/`fleet-directives.md`/`hq.md`/`toolsmith.md`, **not one `tools/` file** — which is the existing IDENTITY leg applied per-SURFACE but never per-LEG.

**The Toolsmith leg is unshipped AND actively pinned.** `--interrupt` (the pre-#393 boolean) is still passed by `tools/lib/oc-notify.sh` (the rc-3 retry) and `tools/oc-notify-fanout:1187`, and `tools/oc-deploy`'s selftest **FAILS** if the second verb call lacks `--interrupt` — the old shape is *asserted* — while #393's own target state prescribes `--interrupt` → `--mode interrupt`, live and valid today (`--mode` help: *"turn-end (default) | interrupt | quiet"*). **No ledger row ever claimed a `tools/` leg for #393**: either the migration is owed or its dropping was a decision, and neither is recorded.

**Exposure, and the transferable half.** 46 of the 156 open fork issues carry a landing row (41 of them exactly one) — the population in which a partial landing can mask a leg. And the class was **not** found by any sweep: Triage caught it by re-deriving the cycle's own numbers against **independently asserted** expectations (24 OK / 1 MISMATCH). A sweep that re-derives its own predicate returns the predicate's answer.

LOC: 3559 -> 3572 (net +13; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `7c0cbd2e` which reproduces the v0.4.246 entry's 3559 exactly). The whole change is `fleet-directives.md` 670 -> 683; no other corpus file changed.

## v0.4.246 (2026-09-24)

**Two law clauses from one Triage cycle: the SCOPE path test is a PREFIX test and the named path is EXISTENCE-TESTED, and an UNATTENDED session must not open a plan.**

The two findings share one shape — a claim made without reading the object it is about. The patrol bucketed an in-scope issue out on a path it never resolved; and a cron worker re-asserted a blocker about a card that does not exist, for a third consecutive cycle.

**Scope (Triage n=10690, item 1).** `triage.md` §Duty T4 now says `tools/**` means ANY path under `tools/` — `tools/lib/oc-notify.sh` is exactly as in-scope as `tools/oc-deploy`, and a reader testing only for the `tools/oc-*` shape buckets a genuine `tools/**` fix OUT — and that the named path must be **EXISTENCE-TESTED** (`git ls-files`), so a `tools/` string in prose is not mistaken for a fix surface. Verified first-hand before writing: `#433`'s body names `tools/lib/oc-notify.sh`, which exists (**7034 B**) and is tracked in the skill repo (`git ls-files` rc=0), so `#433` is **IN** scope despite the 06:00Z cycle listing it among *"OUT-OF-SCOPE INVERSIONS"* as *"surface not pinned in the body"*; of that cycle's declared *"three out-of-scope wires"* only **two** (`#419`, `#471`) were out of scope. The cron prompt carries the same line, so the executor cannot re-invert it.

**Unattended plans (`fleet-directives.md`; origin [#510](https://github.com/leshchenko1979/opencrabs/issues/510), Triage item 2).** A session with **no channel binding** has no approval surface: `plan init` returns its own *"ask the user to approve"* guidance, the model complies and ends the turn, and the plan sits `Editing` with `approved_at: null` forever because no card exists to carry the tap. Measured on this profile: **6** plans in that state, **every one with 0 `plan_cards` rows AND 0 `session_bindings`** — four cron workers (`0af22fbc`, `b246ddbd`, `41ca47a9`, `e8389c6b`), one **A2A** session (`9d163421`), and one orphan plan file with no session row. That is **wider than #510's own table** (which names three, all cron) — the class is not cron-only. It is also **self-repeating**: the cron reuses its worker session, so each later fire re-reads the stranded plan and re-reports a blocker no surface can clear, and **three consecutive patrol cycles** closed with *"the plan card in this topic needs an Approve / /execute first"* while `plan_cards` held **zero** rows for that session and that topic (verified: 26 cards, none matching). The clause records that `init mode=checklist` is **not** a mitigation — it ALSO returns to `Editing` pending approval, so the sanctioned choice strands the session too. Tool-side fix stays #510 (plan-tool lane, design-gated); this is the law-side stop, and the patrol prompt now forbids `plan init` outright.

**Bundled commits named in this range:** none — this range carries only this lane's two law commits, and the sweeper's own bookkeeping is skipped by the naming leg's subject rule.

LOC: 3558 -> 3559 (net +1; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `e75e79e7` which reproduces the v0.4.245 entry's 3558 exactly). The whole change is `fleet-directives.md` 669 -> 670; `triage.md` is 402 before and after because the scope clause was EXTENDED in place rather than appended as a new line.

## v0.4.245 (2026-09-24)

**Two rulings land: a CENSUS must re-validate a claim's recorded blocker, and COHORT ACCOUNTING must be a predicate rather than a hand-built table — and one CHANGELOG ordering defect is fixed in the same entry.**

The census finding is the sharper half because it produced a FALSE STATE, not merely a slow gate. This lane's own Duty-5 ruling (`n=10619`/`n=10620`, 2026-09-23) released two claims while describing one holder as "design-gated" — a free-text qualifier carried in the CLAIM ROW, which nothing re-reads. Measured first-hand after the holder corrected it: all four `#443` commits are ancestors of `origin/main` (`rc=0` each) and the change had SHIPPED before the ruling. So a claim's `what` text is a dated assertion, never live state, and a fence that repeats it verbatim launders a stale premise into a ruling.

- **`triage.md`** — COHORT ACCOUNTING IS A PREDICATE, NOT A HAND-LIST: build the CLAIMED cohort from `oc_claims.open_claims` (`tools/lib/oc_claims.py`) and the DISPATCHED cohort from the dispatcher's own dedup memory; every in-scope issue lands in EXACTLY ONE bucket and the BUCKET TOTAL must equal the COVERAGE LIST, with the reconciliation line printed beside the cohorts. When the two disagree the LIST is wrong, not the buckets. Origin: THREE consecutive cycles shipped a hand-built table; the 2026-09-24 one reported 24 in-scope against its own 20-row coverage list, with `#312`/`#320`/`#363` (each carrying a live open claim) absent from the claimed cohort and `#327` filed as "unclaimed" while carrying live claim `n=8226` — that last one the third appearance of the same misfile.

The census half is law routed to the Toolsmith rather than authored here (it is `tools/** CODE`): the fence must report the FULL set instead of breaking on the first match, bound a holder's liveness, name a mutual fence as ONE structural condition with stated precedence, and — the leg this entry exists for — report whether a fencing claim's RECORDED BLOCKER still holds. Implemented as `be486f38` (#533/#534/#535) and `0aba16bf` (#536); the dormancy treatment is QUALIFY, not CLEAR: the fence still refuses `rc=1` and prints `holder_age` + `DORMANT` + a release ADVISORY, because silently converting a refusal into a pass would undo the gate's whole purpose.

**Instrument defect fixed in this entry — the CHANGELOG was out of order.** `v0.4.244` had been inserted BELOW `v0.4.243`, because its predecessor was anchored on the `v0.4.242` header instead of the file's top. A newest-first record that reads 243-then-244 tells a scanning reader the older entry is current. Reordered here; the cause is the anchor, not the content.

**Bundled commits named in this range:** `be486f38` (#533, #534, #535 — the census fence legs) and `0aba16bf` (#536 — leg (v), the blocker re-validation), both `tools/**` and both the Toolsmith's; plus `34915283` — this lane's own `triage.md` cohort-accounting law commit, named here because the C8 naming leg correctly flagged it (it carried the issue ref `#529` in its subject, so the self-commit skip does not apply). The range also carries `6cedb566`, a `runtime-artifacts sweep (B3)` bookkeeping commit with no issue ref by design, which the naming leg's sweeper-subject skip handles.

LOC: 3557 -> 3558 (net +1; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `7efdde84` which reproduces the v0.4.244 entry's 3557 exactly). The whole change is `triage.md` 401 -> 402; no other corpus file changed. The CHANGELOG reorder is a block MOVE, so it does not affect any line count.

## v0.4.244 (2026-09-23)

**One law clause: `oc-ledger events` has a SECOND trap on the same verb — the 160-char body cap.**

`events` caps every row's `what` body at 160 chars and discloses it on **stderr** (`events: N row(s) had 'what' truncated to 160 chars — rerun with --full`). The verb's FIRST trap — the ~21-row default window, which hid rows ENTIRELY — was fixed by the v0.4.241 law; this one hides the BODY of rows the reader can already see. Short values survive the cap (a `MODE:` row reads fine, which is why the MODE read needed no change); a ruling or work order does not — this lane's own `n=10620` work order is 1052 chars, so the default read returns its first 160 and its operative legs are invisible.

The dangerous inference is ABSENCE: on 2026-09-23 a `grep -c` for a branch-name string over the events view returned **0** while `workers-ledger.json` carried it **7** times — a peer lane's correct correction was nearly contradicted on that false zero. The law now says to read a RULING with `--full`, never to conclude a row's absence from a capped read, and notes the disclosure rides **stderr**, so a read that discards stderr is silent and piping stdout alone leaves the warning on a stream the caller may not surface.

Origin: editor lane `aaa8d8ae` corrected this lane's own `n=10619`/`n=10620` ruling records — a `branix/` vs `fix/` branch typo, and a `#443` premise that was stale because the change had SHIPPED before the ruling. Verified first-hand: all four `#443` commits (`7996d1d2e`, `df0035199`, `6c6367bc1`, `22b52d1e3`) are ancestors of `origin/main` (`rc=0` each), `origin/main == deployed.sha == 457ff4ff`, and the smoke row is `smoke-verdicts.log:1421` (`PARKED-OWNER-EYE`, run `35779915751`). The release was correct and overdue, but for the wrong stated reason: the claim's free-text blocker had expired and nothing re-validates it. A leg (v) — report whether a fencing claim's recorded blocker still holds — was routed to the Toolsmith as an addendum to the census work order.

**Bundled commits named in this range:** `28657cf6` (#514), `a1410706` (#518), `b9b5e9a9` (#524) and `3b0008b1` (#528) — four tool fixes the Toolsmith landed after the v0.4.243 entry was written; all four carry issue refs, so all four are named here. The range also carries four `runtime-artifacts sweep (B3)` bookkeeping commits with no issue ref by design, which the naming leg's sweeper-subject skip handles.

LOC: 3557 -> 3557 (net 0; the whole change is one bullet in `fleet-directives.md`, replaced 1:1). Predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `d61b3d52` (the v0.4.243 sync), which reproduces the v0.4.243 entry's 3557 exactly.

## v0.4.243 (2026-09-23)

**Duty 4 cycle `20260922-c22` lands: seven convergence clusters from 57 claims, plus one instrument defect found while closing.**

The cycle polled 31/31 lanes and took 22 submissions / 57 claims (47 ACCEPT, 5 ACCEPT-WITH-AMENDMENT, 5 ALREADY-COVERED, 0 REJECT). The claims landed as the 7 CONVERGENCE CLUSTERS rather than 57 individual rules — several lanes hit the same gap independently, and each cluster is ONE rule. Cluster 8 (media receipt leg-binding) was a NO-OP: that rule already exists in the ops `AGENTS.md`.

- **`SKILL.md`** — cluster 5: a VERDICT TOKEN must be reachable at the tool that writes it (`oc-smoke` accepts only `--verdict PASS|FAIL`, `tools/oc-smoke:9/:57/:64`, against a corpus mandating `UNPROVEN (presence-only)` and `PARKED-OWNER-EYE`). Cluster 4: a notify's `from` is a RETURN ADDRESS only when the sender is a LIVE SESSION. Cluster 1: the skill glob GATE matches PATHS, not intent — semantics read from `src/brain/tools/skill_gate.rs` (issue #150), including that it re-arms after EVERY compaction and FAILS OPEN.
- **`fleet-directives.md`** — cluster 2: design-gated WRITE SCOPE (fleet-process MAY, project/source and the autonomous checklist MAY NOT), a state that had a codified NUDGE scope and no write scope. Cluster 6: **W7 (Inline waiter cap)** — an inline blocking wait must stay under the 600 s harness cap; the 2700 s budget belongs to the DETACHED form only, and a cap-killed waiter does NOT void its dispatch (recover the run id, `oc-prchecks resume`, never re-issue).
- **`upstream-merge-runbook.md`** — cluster 3: the 30 s TRIGGER ceiling and the `>= 300 s` BODY-side census budget must be read TOGETHER (a truncated census is an UNREAD result — never a WAIT, never a failure). Cluster 7: a resume job's PROMPT is not a schedule table and not a tracker mirror.
- **`hq.md`** — the instrument defect: the file told HQ to close the cadence with `oc-ledger stamp review-battery`, but the boundary predicate is a `kind=note` row beginning `^vX.Y.Z ACCEPTED` (`tools/oc-ledger:913`), with `review-battery` consulted ONLY when no note close exists (`:914-915`). Following that prose literally would have silently failed to reset the counter while the stamp itself returned success.

**Two proposer figures were corrected rather than carried:** `oc-smoke`'s reachable token set is **3** (`FAIL`, `PASS`, `PASSED`), not the 2 the verdict table recorded; and the stale-prompt count is **7 of 16** under the ANY-`#N`-token predicate (own read) rather than the proposer's 4 of 16 under its narrower asserts-the-state predicate — both correct for their own predicates, so the law carries the measured number WITH its predicate.

**Bundled commits named in this range:** `0c39b940` (#517 — a red battery receipt now carries its transcript) and `873495a2` (#519 — the sync CHANGELOG gate gains a naming leg, WARN) and `e1438109` (#521 — that gate's anchor is pinned to sync commits, with a ledger window cross-check, a sweeper-subject skip and a self-commit skip). The range ALSO carries the sweeper's own bookkeeping commit `10ae2ef7` (`runtime-artifacts sweep (B3)`), which carries no issue ref by design and is not law — named here so the new naming leg's output is self-explaining rather than a mystery hit.

LOC: 3494 -> 3557 (net +63). Predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `2c777374`, which reproduces the v0.4.242 entry's 3494 exactly. The change is `SKILL.md` 659 -> 708 (+49), `fleet-directives.md` 657 -> 669 (+12) and `upstream-merge-runbook.md` 425 -> 427 (+2); `hq.md` is 319 before and after (one line replaced by one line).

## v0.4.242 (2026-09-22)

**The C8 naming check WARNS — codified before the tool lands, so the implementation has a stated contract.**

The Toolsmith's C8 extension would have `oc-ledger sync` list every commit in its own range that the version entry does not name. Its disposition — **WARN, never `die 6`** — is accepted and now stated in law at the `oc-ledger sync` CHANGELOG-gate row. Two structural reasons, and they are the Toolsmith's own: the range is **other lanes' work**, so a hard gate would let one lane's landing block the fleet's version record at HQ's boundary; and the range legitimately contains commits carrying no issue ref **by design**, so a hard gate needs an exclusion list — which is where this class of gate goes to die. A warn that LISTS the unnamed commits puts the gap into the sync's own output at the moment it is created, which is exactly what failed on v0.4.237, where the entry left a routing visibly OPEN after it had closed.

**One guard is part of the contract, not an optional nicety:** when the previous-sync anchor cannot be derived, the comparison is SKIPPED with a **NOTE** — never a silent clean. An unverifiable check that reports clean is the #485 defect in a new costume.

Status: the warning gate itself is **NOT LANDED** — it is the Toolsmith's next-cycle work, and it is not sequenced ahead of anything by this entry. The existing HARD existence gate (v0.4.65, the v0.4.54 backfill incident) is unchanged.

LOC: 3494 -> 3494 (net 0; the whole change is one table row in `SKILL.md`, replaced 1:1). Predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ.

## v0.4.241 (2026-09-22)

**A floor read off the wrong clock, the doc clause for the sidecar reaper, and a backfill for a fix that rode the previous sync unnamed.**

**The ~24 h floor is a property of the SCHEDULE, not of execution timestamps (#341 lane, 20:2xZ).** The v0.4.236 ruling measured the floor from the job's own `cron_job_runs.started_at`. Read strictly after tonight's stall, EIGHT of the sixteen `oc-harvest-*-resume` jobs stood in violation — reading **19.67 h to 22.15 h** against a ~24 h floor — and every one was a job whose 15:xx slot had executed in the 19:49–19:51 catch-up burst. No repace had occurred, and every one of their slot-to-slot cadences was exactly 24 h. The shortfall was EXACTLY the stall's delay, so the proxy was catching execution lateness, not a shortened cadence — and acting on it would have permanently moved eight clocks to ~19:5x to accommodate a transient outage, redone on every recurrence. The ruling: **(a)** an unchanged slot raises no floor question at all, so no re-arm is owed; **(b)** a MOVED slot is measured new nominal slot minus the PREVIOUS nominal slot, with `started_at` demoted to a lateness-contaminated fallback. Verified first-hand before writing: ZERO `cron_job_runs` rows in hours 16/17/18, last `cron::scheduler` line 15:30:17Z, `NRestarts=0`, **16** runs inside 19:45–19:55. The stall is #504 and the catch-up herd is #511 — neither re-filed. **The lane's own recommended default (b) was correct and is adopted as law**; its census is confirmed over all 16 rows, with one correction to its characterisation — issues 18 and 225 read ~2 h and ~1 h short, matching their OWN execution lateness, rather than the ~0.1 h it stated. The class boundary holds; the parenthetical was loose.

**The sidecar reaper's doc clause (Toolsmith D3 handover, `5ae02167` / #509).** `tools/HEALTH-CLASSES.md` class 3 now defines check **3b `sidecar-retention`** (severity SAFE) and `tools/HEALTH-CHECKS.md` documents the remediation plus `OC_HEALTH_SIDECAR_KEEP` / `OC_HEALTH_SIDECAR_MAX_AGE_H`. Live behavioural receipt, this box: `oc-health --class persistence` → `3 SAFE sidecar-retention — 58 generated sidecar(s) / 3.3MB, 2 prunable (keep 3 per source, >=48h) - rerun with --reap`, rc=1. The identical check had timed out at 420 s during the host stall, so the receipt also establishes that the hang was host saturation, not the tool.

**Bundled tool fixes — four Toolsmith commits, named per the v0.4.239 amendment.** `a6298654` (#379) — `oc_claims`' prose tokenizer matched the `#N` INSIDE a foreign-repo slug (`owner/repo#N`), so a prose mention of an upstream PR registered an open claim on a fork issue that did not exist. `8c3284a5` (#390) — the targeted `oc-issue-dispatch` path gave `oc-roster classify` no real budget and reported the degradation. `1a2a8cd2` (#380) — `oc-health` now reports an UNSTAGED tracked-file deletion inside a registered worktree (porcelain ` D`); the staged form (`D `) is a DIFFERENT condition and is deliberately not flagged. `95afb928` (#370) — the targeted dispatch path consulted NEITHER #337 guard, so it re-proposed an issue whose fix had already shipped and could wire one issue already dispatched to a SECOND lane.

**Check 18's doc clause (the `#380` half on HQ's surface).** `tools/HEALTH-CHECKS.md` gains section **18 — registered-worktree tracked-file deletion** (`REPORT`), and `tools/HEALTH-CLASSES.md` class 4 (`git_vcs`) gains the matching invariant. Live-fleet find from that check's first real run: **3 of 215** registered worktrees carry an unstaged tracked-file deletion of `tools/oc-waiter`; the file IS present in the main checkout, so this is worktree residue, not a missing tool. Routing of those three stands outside this entry.

**Backfill — #509 rode the v0.4.240 sync UNNAMED.** `grep -c '509'` over that entry returned **0**. The v0.4.239 amendment requires every bundled commit to be named in the version record, and it failed on its first application — by the same lane that wrote it. Recorded here rather than quietly, per the amendment's own intent.

LOC: 3493 -> 3494 (net +1; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ). The whole change is `upstream-merge-runbook.md` 424 -> 425 (the appended floor bullet). `HEALTH-CLASSES.md` and `HEALTH-CHECKS.md` are `tools/**` and outside the corpus.

## v0.4.240 (2026-09-22)

**Two silent-wrong-answer traps, one law that described a mechanism the tool no longer had, and the tool fixes that removed it.** Every item was measured before it was written; nothing here is relayed from a commit message.

**`gh` in `~/opencrabs` resolves to UPSTREAM, and the rule was unwritten (Triage, 12:16Z).** The fork remote carries no `gh-resolved` key while `remote.adolfousier.gh-resolved base` does, so gh's resolver selects `adolfousier/opencrabs` for any command run from that directory without `-R`. It fails silently in BOTH directions: a number that exists upstream returns a real but WRONG issue, and one that does not 404s and reads as "no such issue" — while a write lands on the owner's upstream repo. Measured from that cwd: unscoped `gh issue list --state open` → **9** (upstream's count), scoped → **144**; `gh issue view 340` 404s unscoped and resolves to a real CLOSED fork issue scoped. The corpus was internally consistent and the rule absent: `-R` is prescribed at **14** sites, while `grep` for "default repo" / "gh-resolved" / "set-default" / "resolves to upstream" returned **0** across the normative files. Landed as a bullet in SKILL.md §Shared environment facts — the shared-facts home every role loads, because the trap is role-agnostic. The environment fix (`gh repo set-default`) rewrites shared repo config and is the owner's call, not a lane's; it is stated as such in the bullet and was NOT applied.

**The glossary described a staging mechanism that `db3fce41` (#508) had already replaced.** `SKILL.md` said the auto-commit "stages ONLY `workers-ledger.json`" and that "the two paths differ". Post-#508 that is false in both halves: `STATE_TRACKED_PATHS` (`tools/oc-ledger:223`) + `STATE_TRACKED_GLOB` (`:230`) are the single home, consumed by `state_sweep_tracked` (`:232`), called from BOTH the auto-commit tail (`:276`) and `commit-pending --bundle` (`:1101`), with a selftest asserting the single source (`:1540`). Rewritten to the shipped behaviour, with the #508 pointer and the 345-entry measurement kept as the origin evidence. **The consequence is now stated in the law rather than left to be rediscovered:** a class named TRACKED in the glossary is only actually swept if it is in `STATE_TRACKED_PATHS` — naming it in prose without adding it to the array leaves it accumulating while the law reads as covered. That is exactly how the glossary came to list `reviews/`, `evidence/` and `smoke-verdicts.log` as TRACKED while none of the three appears in the sweep list.

**Bundled tool fixes, named per the v0.4.239 law.** `db3fce41` (#508, OPEN) — the state auto-commit now sweeps the TRACKED namespace instead of the ledger alone, closing the gap the v0.4.238 entry opened. `18791de7` (#507, CLOSED) — `oc-ledger`'s `atomic_jq` temp no longer leaks on SIGKILL; the EXIT trap could not see the temp path, and a stale-temp sweep was added. Both are the Toolsmith lane's, both `tools/` CODE, and both rode this window unmentioned until this entry named them — which is the precise failure the v0.4.239 law exists to prevent, now exercised on the very next bump.

**A duplicate-anchor edit, caught before commit.** The first `hashline_edit` against the glossary region replaced a range whose start line was re-emitted, leaving `A TRACKED class's additions...` twice. `grep -c` returned 2 against an expected 1 and the fix landed before any commit. Recorded because the same edit form is used on every bump: a range-replace whose anchor line survives in the replacement text doubles that line, and only a post-edit count catches it.

LOC: 3476 -> 3493 (net +17; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f, encoding='utf-8'))` over the 8-file law corpus, LINES READ, anchored at `82e62f8c` which reproduces the v0.4.239 entry's 3476 exactly). The whole change is `SKILL.md` 642 -> 659: the new `gh` bullet (+12) and the rewritten glossary passage (+5 net). No other corpus file changed; the two `tools/**` commits are outside the corpus.

## v0.4.239 (2026-09-22)

**The version record could not say when a tool fix shipped.** Found by re-reading this file against the sync ranges, in the same pass that followed the meta-factory Delegate's Recoverability 4 -> 3 dock on the state repo: two consecutive version windows bundled a `tools/**` fix that neither entry named, and nothing in the law required the naming — `hq.md` required only that an entry EXIST, and the sync gate (`tools/oc-ledger`) enforces exactly that. So the CHANGELOG was complete by the letter of the rule and incomplete as a record.

**Measured over the sync ranges (`git log --oneline <prev-sync>..<this-sync>`):** v0.4.237 bundled `8e213c5e` (#503, `oc-ledger enroll` WARNS when `--topic` names no live binding and records the topic) and v0.4.238 bundled `e63b2f56` (#505, the bundle sweep now covers `*-harvest-state.md`). Neither number appeared anywhere in this file — `grep -c '#503'` and `grep -c '#505'` each returned 0 — while every sibling of the same Toolsmith batch (#492/#483/#485/#495/#496/#497/#493) IS named, in the v0.4.235 entry. The standard was already the fleet's; these two fell below it, and the cause is structural rather than careless: a fix that lands AFTER the entry is drafted but BEFORE the sync rides in unmentioned, and that window is open on every bump.

**#505 was the sharpest instance** because v0.4.237's own entry left the routing OPEN — "The mechanism-side belt — adding the class to the bundle whitelist — is `tools/**` CODE and routes to the Toolsmith." A reader of v0.4.237 therefore saw a gap that had in fact closed, and the version record could not correct them. That is the same class as the state repo's 345 uncommitted entries and the 17 untracked harvest records: state that is not durable where it claims to be.

**Landed:** both entries backfilled with their bundled commits, and `hq.md`'s Checkable Completion Formula sharpened so "entry present" means the entry NAMES every non-sync commit the sync bundles, with `git log --oneline <prev-sync>..<this-sync>` as the checklist. Rule text stays lean per §Rule-text provenance — this entry is the biography.

LOC: 3476 -> 3476 (net 0; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f))`, LINES READ). The whole change is one line replaced inside `hq.md`'s completion formula (319 lines before and after); `CHANGELOG.md` is not in the corpus.

## v0.4.238 (2026-09-22)

**The state repo's recoverability: 345 untracked entries, and the advisory that measured them named the wrong mechanism.** Raised by the meta-factory Delegate (OpenCrabs dev 62/76, Recoverability 4 -> 3), which recommended declaring the generated patterns as a namespace and reaping them. The COUNT was right; the mechanism was not, and the difference changes the fix.

**Taxonomy, python over `git status --porcelain`, classes summing to exactly 345:** 198 (57.4%) `oc-deploy/journal/*.jsonl` · 78 (22.6%) `.bak` sidecars · 33 (9.6%) report/doc/census · 14 (4.1%) lane `*-state.md` records · 12 (3.5%) scratch dirs · 7 (2.0%) probe scripts · 1 `.ledger.IW5b9i` temp · 1 lane cursor · 1 `pacemakers-off` marker. **So the recommended fix addresses 23.1%, and the dominant 57.4% is a namespace TRACKED BY DESIGN** — 2 289 of the deploy journal's 2 487 files are already tracked, and it is the audit trail `oc-ledger recover-receipt` reads. Reaping it would have destroyed deploy history.

**The mechanism is an UNINVOKED SWEEP, not a missing reaper.** `oc-ledger`'s auto-commit (`git_state_commit`, `tools/oc-ledger:200`) stages exactly ONE file, `workers-ledger.json`; the `commit-pending --bundle` sweep (`:1010-1031`) stages the namespace whitelist INCLUDING `oc-deploy` — and **measured, 0 enabled crons across all profile DBs invoke it**. The 345 are what accumulates when the sweep that would commit them never runs.

**Landed (state commit `e43f7cc5`, 505 files, +30431/-1895, pushed):** the live backlog committed — 198 deploy journals, 31 reviews, the lane state records, reports, evidence. `.gitignore` now carries the generated class (`*.bak`, `*.bak-*`, `.ledger.*`, `__pycache__/`, `*.pyc`). The leaked `.ledger.IW5b9i` temp (3 052 914 bytes, Sep 19) is reaped. `git status` went 358 -> 0 lines and 14 unpushed commits -> 0.

**A safety check earned its keep.** The first `.gitignore` used `*.bak` alone, which does NOT match the `.bak-<suffix>` variants (`smoke-verdicts.log.bak-prerebind-353`, `harvest-registry.json.bak-325-...`), so four generated files slipped into the staged set. The staged-set grep caught them; `*.bak-*` was added and the set re-verified with none present.

**Two new defects routed to the Toolsmith, both `tools/**`.** (D2) the `.ledger.*` temp leaks on any signal that bypasses normal shell flow: `mktemp` inside the state dir (`:236`), `rm -f` only on the jq-failure paths (`:237-239`), and the EXIT trap (`:140`) calls the logger rather than a cleanup and cannot see the local — the vector is the daemon restart, which SIGKILLs in-flight children (9 starts/stops on 09-21). (D3) the generated class has no retention reaper; `oc-health` already resolves the state dir (`tools/oc-health:32`) but `HEALTH-CLASSES.md:76` covers only `*.corrupt-*.bak`, a different pattern.

**The generated class is NOT reaped blindly, and the marker proves why.** `pacemakers-off` sits in the same state dir and is a marker the owner's pacemaker order REQUIRES to exist (`HEALTH-CLASSES.md:93`); a blanket state-dir clean would delete it and flip that check's direction. The rule is an allowlist of generated PATTERNS, never a general clean — and the 78 `.bak` sidecars were deliberately LEFT on disk (3.9 MB, now gitignored) rather than deleted, because a sidecar taken while its source was still UNTRACKED is the only copy of that reading, which is the loss lane `facd50af` reported today.

**The v0.4.237 entry's open routing CLOSED in this window, and this entry did not say so until the v0.4.239 backfill:** `e63b2f56` (#505) — the bundle sweep now covers `*-harvest-state.md`, so the mechanism-side belt that v0.4.237 left "routing to the Toolsmith" was fitted and shipped here. A reader of v0.4.237 therefore saw a gap that had already closed, and the version record could not correct them.

LOC: 3460 -> 3476 (net +16; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f))`, LINES READ). The whole change is SKILL.md 626 -> 642: the `state dir vs skill dir` glossary entry now declares the two classes, TRACKED and GENERATED-IGNORED, plus the obligation and the two commit paths. No other corpus file changed.
## v0.4.237 (2026-09-22)

**A resume record that is not git-tracked does not exist — and nothing tracked it.** Raised by the #341 lane as a law gap against the harvest resume idiom, verified first-hand, and it is a silent-loss class of exactly the kind that idiom exists to prevent.

The idiom named `<state dir>/<issue>-harvest-state.md` as the owning lane's resume record but never required it to be TRACKED, and no mechanism did it either: `oc-ledger stamp` stages **only** `workers-ledger.json` (`tools/oc-ledger:200`), while the `commit-pending --bundle` sweep whitelists `tools.log baseline.json orders.json journal deployed.sha deployed.meta.json fanout.state oc-deploy oc-deploy-shadow.log oc-deploy-shadow.archive.log` (`tools/oc-ledger:1009`) — the harvest-state class is on NEITHER list, and **no cron invokes the bundle verb at all**. So the receipt that looks like cover proves nothing: measured 2026-09-22T00:5xZ, a stamp reporting `git: state commit ok … sha=bcc12a81` carried **1 file changed (workers-ledger.json only)**.

**Measured census at 2026-09-22T08:59Z (predicate: `*-harvest-state.md` in the state dir): 20 on disk, 3 tracked, 17 untracked** — every untracked one a LIVE record (real headings, mtimes within 3 days), not residue. The consequence is total: for a parked harvest the state file is the ONLY resume record, its cron keeps firing a prompt that READS it, and the file dies with the disk while its lane believes it is safe.

**Ownership is split, and the split is the ruling.** The file's CONTENT belongs to the owning lane — never edit another lane's record. The TRACKING is owed by the lane that CREATES the file, in that turn, verified with `git ls-files --error-unmatch <file>` (rc 0 = tracked) and never by reading a stamp receipt. The pre-amendment residue was swept by HQ (state commit `960bec99`, 19 files = 17 untracked + 2 tracked-but-dirty) as a one-time hygiene act, not a transfer of content authorship, because a parked harvest's lane may never return to track its own file. The mechanism-side belt — adding the class to the bundle whitelist — is `tools/**` CODE and routes to the Toolsmith.

**Also bundled by this version's sync, and unmentioned here until the v0.4.239 backfill:** `8e213c5e` (#503) — `oc-ledger enroll` now WARNS when `--topic` names no live binding, and records the topic, so an enrollment aimed at a dead topic is visible instead of silently accepted.

LOC: 3460 -> 3460 (net 0; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f))` over the 8-file law corpus, SKILL.md / editor.md / editor-upstream-pr.md / hq.md / triage.md / toolsmith.md / fleet-directives.md / upstream-merge-runbook.md). The whole change is INSIDE the existing `State file` bullet of `upstream-merge-runbook.md` (424 lines before and after — one line replaced by one line), so no file in the corpus changes its line count. **Scope note for the next reader:** this corpus EXCLUDES `review-lenses.md` and INCLUDES `upstream-merge-runbook.md`; a recomputation that swaps those two returns 3330 instead of 3460 and is a SCOPE error, not a drop in the law.
## v0.4.236 (2026-09-22)

**Two law-gap rulings, raised by two lanes within the hour, and they are ONE defect class: a classifier keyed on a PATTERN instead of on the object's own identity.** Both were filed as gaps with the reasoning already done; both turned out to be the same missing test carried on a different leg.

**Scope is a FILE-SURFACE test, never a TITLE-PREFIX test.** The factory-scoped patrol dispatched #419 and #471 to the Toolsmith as internal backlog on the strength of their `fix(tools):` titles. `fix(tools):` is a LABEL the owner applies to every tool-related issue, and it spans TWO repositories and two buckets: a fix landing in `tools/**` (skill repo, harvest-exempt) is IN scope, a fix landing in `src/brain/tools/**` or any other `src/**` path (the daemon, harvestable) is OUT. #419's fix lands in `src/brain/tools/subagent/notify.rs` + `src/cli/args.rs`; #471 names no `tools/` path at all (its mechanism is the daemon's tool-result spill read-back). Both dispatches were withdrawn (correction n=10302), both issues stay OPEN and unclaimed by that patrol. The title is the most AVAILABLE signal, so a classifier defaulting to it returns exactly the answer it wants — and it is wrong on both inversions SILENTLY. The principle was already in `triage.md` twice (Duty T4 item 1: *a `#N` in a title is a REFERENCE, not identity*; the closure law: *the criterion is the carrying repo, never the path string*) — this amendment CARRIES it onto the SCOPE leg. Prior art for the correct treatment is in the patrol's own history: n=10254 classified "#418/#419 (src/**, daemon/CLI surface)" out-of-scope by READING THE BODY. **Where the law lived matters here, and the amendment corrects the premise:** the abstract scope line (`fixes landing in tools/** or .github/workflows`) is in NO law file — a grep of the whole corpus returns zero — it exists only in the `oc-triage-factory-patrol` cron PROMPT. That prompt is the surface the classifier reads, so a `triage.md` law alone would have left the defaulting behaviour in place; both were updated (`triage.md` §Duty T4 carries the law, the prompt carries the mechanical test and points at the law).

**A MIXED census-refusal set is governed by the SLOWEST-CLEARING leg.** `upstream-merge-runbook.md:319` gave one rule per token class — expiry-carrying re-arms ~30 min past its expiry, no-expiry re-arms at the next daily boundary — with nothing stated for a set carrying BOTH. After #493 the census prints its full refusal set, so the case is now the normal one, and the tool says the consequence itself (`tools/oc-harvest-census:1116`): *"eligible_at … binds the SOAK leg ONLY … it is NOT total clearance … returning at that instant will be refused again."* Ruling: **if ANY non-terminal leg is no-expiry, re-arm at the next DAILY BOUNDARY; only an all-expiry set earns `expiry + 30 min`.** The no-expiry leg carries no clock at all — it clears on another lane's action — so returning at the expiry instant is refused again by that other leg. **And a re-arm is FLOORED at ~24 h after the job's own last ATTEMPT, read from `cron_job_runs.started_at`, never from the clock time picked.** Measured live 2026-09-22: `oc-harvest-250-resume`, natural daily slot 15:15, fired 2026-09-21T15:15:44Z and was repaced to `58 7 * * *`, whose next fire 2026-09-22T07:58:00Z sits only **16 h 42 m** later — 7.3 h short of the floor; `oc-harvest-341-resume`, slot 15:45, repaced identically, fires 16 h 13 m after its own attempt — 7.8 h short. **The lane cited peer agreement on 07:58 as "the fleet's de-facto convention"; it is not.** 341's OWN daily slot was 15:45, so its agreement with 250 is two lanes making the same error independently — a convention is established by the LAW, never by a peer's imitation, and the fleet's actual daily cadence is exact 24 h across all 15 enabled resume jobs (verified: every one fires the next day at its own last-fire clock time).

LOC: 3458 -> 3460 (net +2; predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f))`, LINES READ, anchored at the v0.4.233 bump commit 814440da which reproduces that entry's 3437). The +2 is `triage.md` 399 -> 401 (the scope bullet and its blank line); `upstream-merge-runbook.md` stays 424 because the re-arm ruling was APPENDED to an existing bullet rather than added as a new one. The `oc-triage-factory-patrol` prompt change is not in this corpus — cron prompts are DB rows, not skill markdown.

## v0.4.235 (2026-09-22)

**The Toolsmith's fix batch, carried to both mirrors, plus a correction to this changelog's own v0.4.234 entry.** The Toolsmith lane's eight commits sat on the skill repo's `main` unpushed; reconciliation showed main 8 ahead of `origin/main` and 0 behind, so landing them was a pure fast-forward with no divergence to merge.

**The v0.4.234 entry's coverage figure was wrong, and it was wrong because the MEASURING TOOL was.** That entry recorded `oc-claims-single-source` as "PARTIAL by construction (14 of 19 python units scanned; 5 reported as NOTE coverage hole)". The figure was honest for the extractor that produced it and false for the tree: `python3 -c` blobs were fenced by scanning forward to the next line STARTING with a quote, so a single-line blob had no terminator and the scan ran on through the rest of its file, parsing as nothing. Fixed in **#496 / `02246264`** — a shell-word parser now walks the blob's own quoting — after which the live tree **declares and scans 28 of 28 with 0 holes**; the denominator RISES because each single-line blob becomes its own unit instead of being swallowed by a neighbour. Confirmed first-hand by the HQ lane's own run of the tool, whose ok line prints both figures, not inherited from the fix's report. The guard was blind in the same way: the live-tree leg asserted `declared >= parsed`, which a coverage hole SATISFIES, so it could not fail on the defect it existed to catch; it now asserts full coverage and equal figures. The rc row in `tools/RC-CONTRACT.md` is corrected in place (`47de9f5a`), and the rc MECHANISM sentence is KEPT deliberately — a NOTE still prints and rc still stays 0, only a HARD finding returns 1 — so what was wrong was the figure, not the rule.

**The backup pile the owner ordered purged had no pruner at all (#497, `6a325209`).** It reached 38 files / 3.3 GB, which #497 records as regrown from 3 files in about two days, because `oc-deploy` backed up on every swap ATTEMPT and never removed one. `prune_binary_backups()` now keeps the newest `BAK_KEEP` (default 5, overridable via `OC_SWAP_BACKUP_KEEP`) and runs right after the fresh backup is journalled, so the journaled rollback path is always inside the window. Ordering keys on the FILENAME STAMP, never on mtime: `cp -p` preserves the source's timestamps, so a backup's mtime is the mtime of the binary it COPIED, and an mtime-ordered rule demonstrably deletes a backup the correct rule retains — potentially the path an in-flight chain journalled. The owner's own purge kept the newest 3 under that same filename-stamp predicate (38 files to 3, 3.3 GB to 261 MB, disk 80% to 75%).

**Also in the batch, each filed and fixed:** #492 `51bd65a1` `claim-ref --open` resolves the newest STILL-OPEN claim row, not the newest row; #483 `b2277a1b` `oc-issue-dispatch` widens its open-issue window and kills the fabricated-metadata fallback (rc 1 on an unresolvable ref); #485 `a25e892d` `sweep-closed-claims` reads BOTH states, so a token resolving to no fork issue can no longer print a clean verdict; #495 `93bf6b51` `oc-ship-chain` resolves an abbreviated `--sha` at entry and stops blaming the remote when the gate refuses a short sha; #493 `0c833ff3` `oc-harvest-census` reports the FULL refusal set so `eligible_at` is never read as total clearance. `e758524a` adds the caller-prefixed job-name embed fixture the HQ lane requested, asserting the three REAL job names of run `35612234852` — including the two that carry a 40-hex and must NOT decode, because `run_built_sha` takes the FIRST decodable `.jobs[].name` and a gate job that decoded would be read as the build, shipping the wrong tree. Battery at the end of the batch: **229 pass / 0 fail**, from 224.

**Filed, not lived with (#501).** `oc-commit` silently derives `Issue-Ref` from the actor's newest open claim when `--issue` is omitted, so on a lane holding many open claims the commit looks like the fix for an unrelated issue — and a false `Issue-Ref` is a false claim in a durable artifact. The Toolsmith hit it twice in one cycle and self-caught both. This lane's own law commit `47de9f5a` therefore carries `Session-Id` and deliberately NO `Issue-Ref`: #496 is the Toolsmith's claim, not this lane's.

LOC: 3458 -> 3458 (net 0). Predicate as the v0.4.233 entry states it — `sum(1 for _ in open(f))` over the 8-file law corpus (SKILL.md, editor.md, editor-upstream-pr.md, hq.md, triage.md, toolsmith.md, fleet-directives.md, upstream-merge-runbook.md). No line COUNT changes in that corpus this version: the code half is `tools/` (excluded from the corpus) and the law half is one row's text inside `tools/RC-CONTRACT.md` (also excluded).

## v0.4.234 (2026-09-21)

**Toolshed law half — the owner order's law-side sweep, and the two live tools the registry never listed.** Owner order 2026-09-21 15:39 MSK cut the toolshed in two halves (remove dead weight from the DISK and from the LAWS). The disk half landed in the Toolsmith lane (`fde4c745` archive-alias farm retired, `8c077231` + `5068f238` ledger-path DRY, battery receipt `63f929e4`); this version carries the law half.

**Zero dangling references, and the three tombstones are KEPT.** All 16 tool names deleted from disk (`oc-binary-swap`, `oc-worktree`, `oc-gate-and-ship`, …) return 0 cites across the 15 normative law files, so no law edit was owed for the deletions. An independent sweep — every `oc-*` token cited in law resolved against `tools/`, `tools/lib/` and `tools/archive/` — converges on exactly three absent tools, every other hit a verified false positive of the pattern: `oc-work` is a DIRECTORY (`~/oc-work`, `hq.md:118`), `oc-wt-suggest` is a WORKTREE PATH in a war story, `oc-embed`/`oc-log`/`oc-notify`/`oc-snap`/`oc-wt-resolve` are `tools/lib` scripts cited without their suffix, and the `oc-harvest-*-resume` / `oc-health-hourly` / `oc-roster-detached-sweep` / `oc-triage-*` / `oc-upstream-delta-watch` family are cron JOB NAMES. Ruling — **KEEP all three** — because each is a tombstone doing a job, not stale weight: `oc-contributors` (`SKILL.md`) names its own successor (`oc-attrib --contributors`) and is referenced by real code comments (`tools/oc-seal-state:7`, `tools/tests/run.sh:539`), so deleting the law line would orphan them; `oc-consent-check` (`war-stories.md:81`) and `oc-watchdog-check` (`CHANGELOG.md:1698`) sit in the two files the law ALREADY declares historical-quotation surfaces — `tools/RC-CONTRACT.md:41` states the lint corpus EXCLUDES `war-stories.md` and `CHANGELOG.md` "because they quote historical invocations that were correct when written". Net dead weight found in law: **zero**.

**The registry gap was the real defect, and it is closed.** 39 of 42 tools on disk carried a `./tools/<name>` purpose row in `SKILL.md`; the three without were `oc-census`, `oc-claims-single-source` and `oc-waiter`. `oc-waiter` is legitimately absent — `README.md:52` documents it as a RETIRED v0.4.135 stub (`--help` rc 0, every subcommand rc 1). Two rows were therefore owed and are added: `oc-census` after the `oc-branch-sweep` row (both branch-lifecycle tools) and `oc-claims-single-source` after the `oc-lint-laws` row (both mechanical guards). Registry coverage 39/42 -> 41/42. `oc-claims-single-source` was missing from the RC register ENTIRELY, so `tools/RC-CONTRACT.md` gained its row (0 clean / 1 HARD finding / 2 usage-or-IO) together with the reason it is name-blind: it keys on what a copy must RE-IMPLEMENT, never on a name, because the two copies it exists to prevent were called `claims_index` and `claim_is_closed` — a name-keyed guard misses both. Its own live run also showed its coverage is PARTIAL by construction (14 of 19 python units scanned; 5 reported as `NOTE … coverage hole`), which is why the row states that a green carrying a NOTE is NOT full coverage.

**Item 4 of the order has NO mechanical target.** No tool in `tools/` is banned by name in current law. The only banned-name list in the corpus is the telegram-surface predicate `BANNED='telegram_send|tg_send_message|tg_edit_message|telegram_edit'` (`tools/oc-tg-audit:29`, cited at `fleet-directives.md:657`), and every name on it is a daemon or fast-mcp-telegram tool — none on this disk. Carried to the owner as a question rather than filed: an empty target set is not a fork issue.

**Also riding this version, from the same shift.** (1) The **`#393` INERT-interrupt law sweep** — the clause calling `interrupt` INERT was SUPERSEDED when the urgent tier shipped, and FOUR of the swept sites had asserted the delivery-mode enum was exactly `[turn-end, quiet]`, so the law denied a value the tool accepts. 10 clauses across 4 files (`SKILL.md`, `hq.md`, `fleet-directives.md`, `toolsmith.md`), 13 insertions / 11 deletions — the 11 deleted lines render 10 clauses because the `hq.md` blockquote spans two of them. Both halves of the SPLIT claim are preserved: there is still NO pre-emption (the source says so — "This is NOT pre-emption. No boundary exists inside a running tool call"), while `interrupt` is now the URGENT tier, never deferred. 0 INERT residue left in live law; the only surviving mention is the sweep-law's own incident record at `fleet-directives.md:457`. (2) The **carrier CI lane map** in `tools/RC-CONTRACT.md` — one `workflow_call` body (`ci-lane-impl.yml`) behind the two thin shells `quick-build-linux.yml` and `pr-checks.yml`, documenting why the caller jobs are pinned to the short tokens `ship` / `gate` (a caller name carrying a run sha would SHADOW the real build job for `run_built_sha`, and the ship lane would build the wrong tree).

LOC: 3437 -> 3458 (net +21; predicate the v0.4.233 entry names — `sum(1 for _ in open(f))`, LINES READ, so a final line without a trailing newline still counts — anchored at the v0.4.233 bump commit 814440da, which reproduces that entry's 3437 exactly: SKILL.md 623 -> 626, hq.md 318 -> 319, fleet-directives.md 644 -> 657, upstream-merge-runbook.md 420 -> 424, the other four unchanged. The +21 spans the WHOLE interval since the bump, not this version alone — per-commit: upstream-merge-runbook.md +4 across the trigger-ceiling, census-fence-order and date-keyed laws; fleet-directives.md +13 (Telegram surface law vs lane obligations); SKILL.md +2 and hq.md +1 (the #393 sweep); SKILL.md +2 (this version's two tool-table rows)).
## v0.4.233 (2026-09-20)

**Roster reconciliation — a lane that MOVES leaves its row unreconciled; reconcile against the LIVE binding, and never archive a session to fix a row.** Filed by the editor lane "Compaction visibility" (topic 34653) after an owner `/stop` + `/new` left two editor rows for one topic.

Measured first-hand before ruling: `session_bindings` — not the roster row — is the authoritative live binding, and it exposes **two symptoms of one root cause** (no write re-derives a row when a lane moves). S1, superseded uuid: `d5863180` (topic 34653, 0.4.227) superseded by `cbdfde4a` (0.4.232) after the owner's `/new` at 2026-09-20T02:32:12Z; the claim moved at ledger n=9812. S2, stale `topic_id`: `212b3c83` is bound to 36841 while its row says 29947, and `a5b34466` is bound to 30517 while its row says 30220. The invariant is **one WORKER = one row**, never one topic = one row — but a duplicate row is not thereby a non-defect: three of the four topics a first read flagged carried one (29947 and 30220 an S2 stale `topic_id`, 34653 the S1 supersession), and only the three null-`topic_id` rows are a separate class — flagged, not claimed. A second read corrects this entry: 29947's second row was `212b3c83`, whose live binding is 36841.

Fix verbs: `oc-ledger retire <uuid> --topic N --role R` for S1 — the ONLY correction path (`enroll` refuses a dup, `promote` only mutates, neither can drop a row) and it RECORDS the row in a `roster-retire` event, so removal is not destruction; `oc-ledger promote <uuid> <role> --topic <live-id>` for S2. Traps: archiving the superseded session is not the fix (the row survives and the skew-chase continues), and an addressed `unclaim` row must never be used to clear a superseded lane's stale claim — it releases EVERY lane's claim on that issue, the live successor's included. Verification limits, measured: a retire is proved by ABSENT from `oc-ledger roster` AND `roster --include-retired` PLUS the `roster-retire` event — the flag lists only rows carrying the LEGACY `.state == "RETIRED"`, so a verb-retired uuid can never appear under it; and the retired uuid still shows as a CLAIM AUTHOR in `oc-roster` / `oc-roster live` until its stale claim's issue closes, because that list is claim-driven and no per-lane claim release exists.


**Amendment, same version — two inbound law-defect reports ruled and landed (the version is uncut, so both ride v0.4.233).**

**(1) The trigger ceiling — a census-gated `trigger_cmd` cannot complete** (filed by the #326 lane, verified first-hand; fork #457). `TriggerRunner::default()` hard-codes `Duration::from_secs(30)` (`src/cron/trigger.rs:95-100`), the sole production construction is `src/cron/pipeline.rs:45`, and `TriggerRunner::new(timeout)` has ZERO call sites in `src/`, so no config key reaches it. A timeout is TERMINAL (`src/cron/scheduler.rs:446-461` -> `return Ok(())`): the body never runs and nothing re-arms. Six enabled census-gated resume jobs errored on it on 2026-09-20 (`cron_job_runs`, `Trigger error: Trigger command timed out after 30s` — 318, 346, 348, 364, 403, 421) against a census measuring 53-65 s. **The v0.4.223 fail-open clause does not save it** — fail-open is a SHELL property and the PROCESS ceiling kills the shell first (`oc-harvest-403-resume` carries the compliant shape and still timed out). The law's own remedy was therefore unreachable from the job-author side. #385 is **prior art only**: it documented the runtime distribution and told operators to budget 300 s, a figure unreachable from the trigger side. Ruling: the census goes in the BODY (no ceiling), and `trigger_cmd` is either `NULL` or a sub-30 s probe. **A future `next_run_at` is NOT a failure signal** — the resume jobs are annual, so `18`/`225`/`396` read `2027-09-20` and all three ran `success`; the discriminator is `cron_job_runs.status`/`.error`.

**(2) A REFUSED census is classified by whether its token CARRIES AN EXPIRY.** Expiry-carrying (`SOAK` `:998`, `HELD_DEPENDENT_SOAK` `:1021`, which print their window end) -> re-arm ~30 min past the expiry. Event-cleared, no expiry (`HELD_IN_FLIGHT_LANE` `:1051` — a PEER lane's claim; `HELD_PARENT_UNHARVESTED` `:1133` — an unharvested parent) -> there is no clock to add to: re-arm at the next daily boundary and say plainly it is a cadence, not a derived expiry. Terminal (`UPSTREAM_VOID` `:1109`, already-filed `:926`) -> disable and record. Only `HELD_DEPENDENT_SOAK` and `HELD_PARENT_UNHARVESTED` were codified; `HELD_IN_FLIGHT_LANE` was real in the tool (selftests `:1843-1859`) and absent from law.

**(3) Three cross-reference repairs** (filed by the JEV benchmark lane; all confirmed first-hand, none had prior art). `SKILL.md:501` cited a `hq.md §Parity` heading that does not exist (`grep -nE '^#+.*[Pp]arity' hq.md` -> rc=1) -> repointed at the real heading `## Upstream sync — watch & governance`. `hq.md:56` cited `fleet-directives §Rule-text provenance`, which lives in **its own file** at `hq.md:313` -> repointed. `hq.md`'s blanket "`oc-roster`'s `--role` flag is rejected with rc 2" was **falsified live**: `./tools/oc-roster --role hq` returns the row at rc=0; only the BARE `--role` fails (rc 2, `--role needs a value`). The same review also raised one CONTESTED item — `editor-upstream-pr.md:164-170` vs `fleet-directives.md:191-196` — **ruled POINTER**: prior art `reviews/20260918-cycle/reports/lens-B-redundancy-20260918.md:68` classifies that pair POINTER, so it is KERNEL, not a defect.

**(4) A date-keyed resume job is the WRONG SHAPE AT CREATION, and a PENDING wake that neither re-arms nor disables parks the harvest for a YEAR, silently.** Raised by the #341 harvest-resume lane; the census was verified first-hand. The existing one-shot clause mandated disable-after-harvest for a harvest that COMPLETES or is ABANDONED and was **SILENT on the third case** — a wake that finds the work still PENDING and reports "still blocked", which neither disables the job (nothing is finished) nor re-arms it. A **date-keyed** `cron_expr` then rolls to the SAME DATE NEXT YEAR while the row still reads `enabled=1` with a plausible `next_run_at`, so **a parked job and a healthy one are indistinguishable from the schedule field alone**. Measured 2026-09-20T16:0xZ (predicate `name like 'oc-harvest-%-resume'`): **16 rows, 16 enabled** — 11 daily and 5 date-keyed; FOUR date-keyed jobs fired that day and rolled to `2027-09-20` (issues 18, 225, 345, 396), every one a NULL-trigger fail-open job whose wake SUCCEEDED (each produced a "still blocked" report — the turns did not die, the re-arm was simply not taken). Ruling: author the job **DAILY** (`M H * * *`, or an explicit day-of-week) — a date-keyed 5-field form is wrong **at creation** and cannot be repaired by moving the date, since that is exactly what moved DOM 20 -> 21 and bought a year of dormancy — and the prompt must end every wake in one of two terminal acts: **re-arm** to the next daily boundary, or **DISABLE**. **Adjacent, NOT a duplicate:** the `next_run_at`-is-not-a-failure ruling in (1) above covers DIAGNOSIS; this one is PREVENTION, and neither supersedes the other.
LOC: 3437 -> 3441 (net +4; `upstream-merge-runbook.md` 420 -> 424 -- the census-fence masking law and the date-keyed / PENDING-case clause; the two cross-reference repairs are in-line and changed no line count).
## v0.4.232 (2026-09-20)

**Internal-factory closure -- the harvest gate is VACUOUS on a harvest-exempt surface, and the criterion is the CARRYING REPO, never the path string.** Filed by the Triage lane (GAP 3); one leg of their claim falsified first-hand before the ruling.

The harvest gate exists to make work reach UPSTREAM, so it has nothing to gate on when the repo carrying the fix has no upstream counterpart. The lane's live instance: **#420** (`tools/oc-ship-audit`, close n=9952) and **#422** (`tools/oc-census`, close n=9953) are landed AND recorded, and unclosable by construction -- `git ls-tree -r --name-only adolfousier/main -- tools` returns rc=0 with **0 files**: no parent, no possible PR.

**The lane's claim had a wrong leg -- measured, not argued.** They grouped `tools/**` OR `.github/workflows` as one unharvestable surface. `git ls-tree -r --name-only adolfousier/main -- .github/workflows` returns rc=0 with **4 files** (`auto-assign.yml`, `ci.yml`, `prerelease.yml`, `release.yml`) -- so `.github/**` stays **harvestable**, and the fork repo `leshchenko1979/opencrabs` HAS an upstream. Only the skill repo `leshchenko1979/opencrabs-skill` has none, so only what IT carries -- `tools/**` and the skill markdown -- is harvest-exempt.

The exemption is **on the harvest gate, not a fourth autonomous-close class**: (a)/(b)/(c) dispose of issues whose work is NOT done, whereas this closes an issue whose work IS done and recorded on a surface where no PR can ever exist -- the same framing as the fork-only predicate. Close is allowed when BOTH hold: (1) `landed` on its OWN surface, recorded by a ledger row of kind `done`/`close` (`oc_claims.LANDED_KINDS`), AND (2) the entire landed surface is carried by a repo with no upstream counterpart. If ANY part of the surface is harvestable, the harvest gate stands unchanged.

Changed: `triage.md` -- a new "Internal-factory closure" paragraph inserted after the fork-only closure predicate and before the Close identity guard, which applies unchanged.

LOC (measured; method: true line count = newline count + 1 where the file ends unterminated, so `wc -l` reads one lower on those files): SKILL.md 623 · editor.md 533 · hq.md 318 · triage.md 396 · toolsmith.md 165 · fleet-directives.md 644 · editor-upstream-pr.md 335 · upstream-merge-runbook.md 420 · **total 3434**.

## v0.4.231 (2026-09-20)

**Leg-4 probe hygiene -- form 1 of the mechanical discriminator is now ANCHORED at the fix's own commit.** Filed by the #450 lane (`2ed8adeb`), reproduced first-hand before the amendment.

`git log -S <string>` defaults its revision to HEAD, and this law's own instruction is to run that discriminator on a **pre-merge** tree -- where the fix's own commit is not yet reachable from HEAD. The bare form therefore returns **EMPTY**, and empty reads as *"no introduction exists"*: a **false negative on the one tree the law is about**. Measured on #450 (`b6389c892`, unmerged; `git merge-base --is-ancestor b6389c892 HEAD` rc=1): the bare form returns EMPTY, the anchored form returns exactly ONE introduction. Form 2 is unaffected by this gap and is what established the negative half.

The pathspec-scoping clause added 2026-09-19 is confirmed load-bearing by the same probe: scoped, `git grep -c 'ProgressEvent::TokenCount' 33b7aecdd -- src/channels/telegram/resume.rs` returns rc=1 with zero hits (the correct pre-fix answer); unscoped the same grep returns 19 hits across 6 files -- a false PRESENT.

Changed: `SKILL.md` section "Test ontology", "Leg-4 probe hygiene" -- form 1 is written as `git log -S <string> <fix-sha> -- <pathspec>`, plus an "Anchor it too" clause stating the default-to-HEAD failure and the #450 measurement.

LOC (measured; method: true line count = newline count + 1 where the file ends unterminated, so `wc -l` reads one lower on those files): SKILL.md 623 · editor.md 533 · hq.md 318 · triage.md 370 · toolsmith.md 165 · fleet-directives.md 644 · editor-upstream-pr.md 335 · upstream-merge-runbook.md 420 · **total 3408**.

Verification: clause present in `SKILL.md` · battery `tools/tests/run.sh` green · `oc-ledger sync --version 0.4.231` rc 0.

## v0.4.230 (2026-09-20)

**One CORRECTION to law shipped minutes earlier, raised by the lane that executed the reap. v0.4.229's reap clause named the adoption mechanism but not its SWITCH — so a reaper who follows it and stops at the disk move leaves the daemon holding the home.**

**The correction (the reason for this bump).** v0.4.229 §Throwaway probe homes told a reaper to reap the home's sessions, goals and CRON ROWS. It did not say that a profile still listed in `profiles.toml` remains ADOPTED after its directory moves. The reaping lane measured exactly that: default-profile daemon pid 169358 held BOTH `smoke300`/`smoke300neg` scheduler lock inodes AND six fds on the quarantined DBs, because both profiles were still registered. Reproduced first-hand here before amending: `/proc/169358/fd` → 12/15 (locks) + 17/20/21 and 25/27/28 (DB/-wal/-shm); the registry now reads 4 entries (`ops`, `family`, `oc348probe`, `oc134probe`), the live lock dir holds neither smoke lock, and both sit in `db-quarantine/smoke300-rig-20260920/locks-scheduler/`. **HQ's own dispatch note to that lane asserted the locks were unattached — false, and this entry records the falsification rather than quietly replacing the claim.**

**A second gap fell out of the same read:** the CLI cannot unregister a profile whose directory is already gone — `delete_profile` bails on a missing dir (`src/config/profile.rs:493-495`) and `--force` only skips the confirmation prompt (`src/cli/commands.rs:2318-2322`), leaving the registry write at `:505` unreachable. Order therefore matters: **unregister BEFORE moving**, or the only route is the empty-placeholder dance the lane had to perform. Filed as fork #452.

**Law changed (`fleet-directives.md` §Throwaway probe homes):**
1. The reap clause now states **the REGISTRY is the switch, not the disk** — unregister as part of the reap, before the move; only a daemon restart releases the held inodes.
2. A verification paragraph records the `/proc` receipt, the registry delta, the owner-gated restart, and that the correction came from the reaping lane rather than from HQ.

**Not done, owner-gated:** the default-profile daemon still holds the two lock inodes and six DB fds. Restart scope is `opencrabs-ops` only, so releasing them needs the owner's word. Consequence stated in the law: the quarantined DBs are not frozen while it runs (mtimes unchanged at 07:05Z and 07:12Z — no write observed).

**Files:** `fleet-directives.md` §Throwaway probe homes (reap clause + verification paragraph).

**LOC:** SKILL.md 623 · editor.md 533 · hq.md 318 · triage.md 370 · toolsmith.md 165 · fleet-directives.md 644 · editor-upstream-pr.md 335 · upstream-merge-runbook.md 420 · **total 3408** (+2 on v0.4.229). Count = lines read from the file, so a final line without a trailing newline still counts; `SKILL.md` and `upstream-merge-runbook.md` both end unterminated, which is why `wc -l` reads 622/419 on the same bytes.

**Verification:** `The REGISTRY is the switch, not the disk` → 1 hit · registry-switch verification paragraph present · `/proc/169358/fd` receipt reproduced first-hand · registry 4 entries · battery `tools/tests/run.sh` green · `oc-ledger sync --version 0.4.230` rc 0.

## v0.4.229 (2026-09-20)

**One CORRECTION to law shipped hours earlier, plus two filed gaps folded in. v0.4.228's "inert" framing was FALSIFIED by the lane that raised the residue — the footgun had already fired.**

**The correction (the reason for this bump).** v0.4.228's Origin paragraph called the two probe homes carrying an ENABLED cron row "inert while no daemon runs them". That is FALSE for `oc134probe`. Infra Factory HQ corrected it, and the correction was verified first-hand here: `daemon.adopt_profiles` defaults true (`src/config/types.rs:333`), so the running default daemon spawns a cron-only scheduler for every REGISTERED non-active profile (`src/cli/ui.rs:131-140`) — it holds `locks/scheduler/oc134probe.lock` stamped at its own start (02:56Z) and an open fd on that home's DB. **Its row ran 2026-09-20T04:00:28Z** (`cron_job_runs.status = delivery_failed`) and wrote `reports/brain-dedup-2026-09-20.md` (17,103 B). `code-spike` is the genuinely dormant one: absent from `profiles.toml`, never adopted. Infra's own words: *"right about what you measured (bindings, crons in the two smoke homes) and wrong about the adoption mechanism that reaches a home with no daemon of its own."*

**The rows are NOT rig residue — they are an unreconciled framework retirement.** Both are `__opencrabs_dedup_scan__`, seeded by `507c539eb` (#765) and retired by `5dbcccc7c` (#1593), which deleted `src/brain/dedup_scan.rs`, the scheduler special-case and the job-name string. `strings /usr/local/bin/opencrabs` returns **0** occurrences of the retired name against **4** of `__opencrabs_rebuild__` (the only name still special-cased, `src/cron/scheduler.rs:797`), and `5dbcccc7c` is an ancestor of deployed `6b1548a3`. No migration removed the rows, so a rig-teardown hook would NOT have prevented this. The surviving prompt is a 58-char PLACEHOLDER — *"reserved: weekly cross-file brain dedup scan (report-only)"* — and with the special-case gone it **reaches a full agent session as its work order** (verified: the cron session's first user message is that placeholder verbatim). 4 of 10 DB homes still carry the row ENABLED (default, family, oc134probe, code-spike); the 04:00Z fire cost ~2.2M tokens / ~$0.63 across three homes, two of them `delivery_failed`. Filed by Infra as fork #448.

**Law changed:**
1. `fleet-directives.md` §Throwaway probe homes — the reap now explicitly covers the home's **CRON ROWS**, not only its sessions and goals, and the section states the adoption mechanism that makes an enabled row live.
2. Same section, Origin — **corrected in place and marked as corrected**: the falsified clause is quoted inside the correction rather than silently deleted, so the record shows what was believed and why it was wrong.
3. The backstop property is restated: not "the home is unused" but **"no ENABLED cron job in any home carries a framework-reserved name the deployed binary no longer recognises"** — derivable as `strings <binary>` vs `cron_jobs.name`.
4. `triage.md` §Duty T5 LANDED TERM — the commit leg is now **surface-scoped**: fork `main` for `src/**`, the SKILL repo (`skills/opencrabs-dev`) for `tools/**`. Fork `main` carries **no `tools/` directory at all**, so a tools-surface leg read against it returned FALSE NOT-LANDED for already-shipped work — the INVERSE of the v0.4.226 false-LANDED, and the same defect: one leg, two repos. Filed by Triage (`530c29ec`, GAP 1).
5. `triage.md` §Duty T4 Stale-branch sweep — the v0.4.218 caveat that remote-only heads sit OUTSIDE the patrol's coverage is **retired**: the REMOTE LEG landed 2026-09-20T05:28Z at `ed4d65a0` (#415 step 8; markers at `oc-branch-sweep` lines 24/156/293), read-and-classify only. Live receipt: `--repo /root/opencrabs --dry-run` rc=0, **866 rows, 483 of them `origin/`**. Filed by Triage (GAP 2).

**Files:** `fleet-directives.md` §Throwaway probe homes · `triage.md` §Duty T4 stale-branch sweep + §Duty T5 LANDED TERM.

**LOC:** SKILL.md 623 · editor.md 533 · hq.md 318 · triage.md 370 · toolsmith.md 165 · fleet-directives.md 642 · editor-upstream-pr.md 335 · upstream-merge-runbook.md 420 · **total 3406**. Count = lines read from the file, so a final line without a trailing newline still counts; `SKILL.md` and `upstream-merge-runbook.md` both end unterminated, which is why `wc -l` reads 622/419 on the same bytes — the method is stated so the next reading is comparable.

**Verification:** `inert while no daemon runs them` → 0 hits · corrected clause + restated backstop property present · remote-leg and surface-scope clauses present · battery `tools/tests/run.sh` green · `oc-ledger sync --version 0.4.229` rc 0.

## v0.4.228 (2026-09-20)

**One HQ ruling codified: a throwaway probe home is reaped at rig teardown, and the class that produced the residue is now visible.**

Raised by Infra Factory HQ, which dispatched residue it would not reap itself: 3 `active` goal rows in `profiles/smoke300` + `profiles/smoke300neg`, seeded 2026-09-18 by the fork-#300 behavioral smoke and never torn down. Verified first-hand: both homes declare themselves disposable in their own `config.toml` header; both read `session_bindings=0` and `cron_jobs=0` total; and the residue is the WHOLE home, not those three rows — smoke300 carries 12 goal rows + 11 sessions, smoke300neg 2 + 2. There is no fixture to give a teardown hook to: the rig is ad-hoc shell/python, and neither `oc-smoke` nor `oc-smoke-evidence` creates a profile home, so the obligation is a rig-lifecycle rule rather than a test-suite fixture. Box sweep over all 11 profile homes found two further throwaway homes carrying an ENABLED cron row (`oc134probe`, `code-spike`) — inert while no daemon runs them, a footgun the moment a rig reuses a home and starts one. Infra's `test_cron_targets.py` covers `Cron:%` sessions only and never sees `CLI Run` fixtures.

**Files:** `fleet-directives.md` §Throwaway probe homes — reap at rig teardown.

**Dispatched, not absorbed:** the reap-or-declare call went to the rig's owner lane (topic `push-to-session`) in the same turn, and the mechanical backstop — an `oc-health` check for orphan probe homes, since no existing class reaches `profiles/*` — went to the Toolsmith as their design call.

**Verification:** clause present in `fleet-directives.md` · battery `tools/tests/run.sh` green · `oc-ledger sync --version 0.4.228` rc 0.

## v0.4.227 (2026-09-20)

**One self-correction: the Duty-6 instrumentation schema promised for v0.4.226 did not ship with it. It lands here, frozen.**

Raised by the ops droid side session (`ef83024b`), which checked the shipped tree instead of trusting the promise: all five field names returned 0 hits across `SKILL.md` / `hq.md` / `triage.md` / `editor.md` / `toolsmith.md` / `fleet-directives.md`, and `hq.md` Duty 6 step 0 still carried the old `updated_at` schema. The gap is real, and it blocked a running pilot that needed a frozen shape before it could write its cycle `state.json`. A promise recorded in a notify is not law text; only the tree is.

**The five fields are UNCHANGED from the v0.4.226 promise — no shape change in the interim**, so the pilot writes the canonical form immediately:

1. **`cycle_id`** — ONE canonical id, minted ONCE at cycle init and written into BOTH stores (`state.json` AND a ledger row at cycle open), validated on write so the two cannot diverge.
2. **`duration_review_min`** — review start → reports persisted. The number the owner actually asked for.
3. **`duration_cycle_min`** — cycle start → cadence close stamp.
4. **`ended_at`** — explicit terminal timestamp; **NEVER `updated_at`** (6 of 13 state files never advanced it; two showed a 0.0-min span).
5. **`status`** — terminal ENUM, exactly `IN_PROGRESS | COMPLETED`, never free text.

Plus the two matching rules that bind the step-8 close stamp: the cadence-reset stamp is matched as an **ANCHORED whole-row pattern** `^v<digits>.<digits>.<digits> ACCEPTED`, and a note withholding an END for a cycle **must BEGIN with the literal token `WITHHELD:`** so a loose grep cannot harvest an END from a row whose point is that none was written.

**Files:** `hq.md` §Duty 6 step 0.

**Verification:** field names present in `hq.md` (`duration_review_min` 2 · `duration_cycle_min` 2 · `ended_at` 2 · `WITHHELD` 1) · battery `tools/tests/run.sh` green · `oc-ledger sync --version 0.4.227` rc 0.

## v0.4.226 (2026-09-20)

**Three owner rulings codified, one contradiction retired, two Triage law-text defects fixed. All items are law text.**

1. **MODE REGISTER — the upstream-PR filing gate is a MODE SWITCH (owner ruling 2026-09-20).** Owner, verbatim: *"The thing is, we basically have two modes: 1. High-trust mode, when I'm sure that the factory is working so that the quality allows autonomous harvesting. 2. Degraded, like now, when I want to gate every PR group."* This ANSWERS the `PENDING OWNER RULING` block raised 2026-09-19 by lane `329bf3a3` (topic 7198), which had recorded a live contradiction: `§Hard rules` UPSTREAM CI GATE read *"owner approval + SMOKE pass remain separate required conditions"*, while the CONSENT REGISTER's parenthetical named only post-swap rollback as owner-gated — and `editor-upstream-pr.md` Phase 7 carried NO approval step at all. **The resolution is neither "always" nor "never" — it is a mode.** Under **HIGH-TRUST MODE** a lane files on the 4-leg smoke PASS (filing NOTICE to its own topic); under **DEGRADED MODE** the **PR GROUP** is HELD for explicit owner approval before it leaves the lane (reply, or a positive Telegram reaction to the explicit request; **silence is NOT consent**). **Declared current mode: DEGRADED.** The mode resolves LIVE from the ledger — the newest `MODE:` row in `oc-ledger events --kind note` — and **with no `MODE:` row the default is DEGRADED** (fail closed: holding a filing costs nothing, an unapproved filing is a public act). The switch is owner-only, receipted by `oc-ledger stamp note "MODE: <HIGH-TRUST|DEGRADED> — <provenance>"`. **Files:** `SKILL.md` §Hard rules (CONSENT REGISTER — the `PENDING OWNER RULING` block is DELETED, superseded; UPSTREAM CI GATE made mode-conditional) · `editor-upstream-pr.md` §Phase 7 step 0 → **0a MODE GATE / 0b FILING NOTICE**.

2. **Triage Duty T5's claim predicate named a scalar that cannot answer its own question.** Step 3 told the reader to diff the OPEN set against "the workers-ledger claim-refs (`grep -c '"issue'` or the claim rows)". A count over the ledger FILE is not a per-issue predicate — it cannot answer "is issue N claimed" at all. Replaced with the canonical `oc_claims.open_claims` read (`tools/oc-ledger claims <N>` for one issue; the `claims` projection for the set), and the same fix applied to the §Duty T5 Checkable Completion Formula. Raised by the Triage lane.

3. **The Duty T5 `landed` term's second leg was a bare reference-test — 82.4% wrong on the live set.** `landed` was defined as a `done`/`close` ledger row **OR** "a commit referencing the issue on fork `main`". Fork `main` CONTAINS upstream merges, so an upstream PR number collides with a fork issue number: measured this turn over the 17 unclaimed in-scope issues, the bare-reference form returned a "LANDED-REF" commit for **14 (82.4%)**, and on 6 sampled every one touched ZERO `tools/` paths — #432's "match" was upstream PR #432, while the real #432 has no commit at all. The second leg now carries the SAME identity requirement the skill already states for the VET leg (`triage.md` §Duty T4 item 1, v0.4.218): **the naming commit's changed files must INTERSECT the issue's own surface**, or the verdict is POISONED — a false `landed` routes already-shipped work to the harvest queue, or marks live backlog as done. The law demanded identity on one leg and permitted a bare reference on the other, in the same file. Raised by the Triage lane.

4. **EXCEPTION — Toolsmith `tools/**` design autonomy (owner order 2026-09-20 00:32Z).** Owner, verbatim: *"I am reviewing the design right now, but I trust you enough to make your own design decisions regarding the tooling for this factory, so next time, don't ask."* The Toolsmith lane's `tools/**` design decisions — fix shapes, heuristics, new defaults, new output surfaces, DRY / module moves — need **no design gate and no open question put to the owner**: the lane decides, records the decision in its design artifact, and lands it. Scope is exactly the `tools/**` surface — it does NOT extend to skill-markdown authorship (HQ's), daemon/carrier source (Editor territory), or the owner-gated actions already codified in `AGENTS.md` (daemon restarts, pushes, upstream PRs, swaps). **Autonomy is over the DECISION, never over the RECORD.** Narrowing of `fleet-directives.md §Discussion links + fix-approval gate` item 2 for ONE surface; item 2 remains absolute everywhere else.

5. **Designs are produced PONYTAIL-LAZY (owner order 2026-09-20).** Owner, verbatim: *"you always tend to add more code, so when you produce designs for your issues, use the ponytail skill."* Every design produced for the factory passes through the `ponytail` ladder (`skills/ponytail/SKILL.md`) as its generating LENS — does this need to exist at all → stdlib → native platform feature → already-installed dependency → one line → only then the minimum code that works. A design reaching rung 6 without naming why rungs 1–5 fail is incomplete. Binds DESIGN PRODUCTION, not review of already-landed work, and does not weaken item 2. **Application HELD until the owner's then-current review completes** — nothing pruned retroactively.

**Verification:** `grep -c "PENDING OWNER RULING" SKILL.md` → 0 · MODE REGISTER present in `SKILL.md` and the mode gate present in `editor-upstream-pr.md` §Phase 7 · claim-refs scalar gone from `triage.md` · Toolsmith exception + ponytail lens present in `fleet-directives.md` · battery `tools/tests/run.sh` green (213 PASS / 0 FAIL) · `oc-ledger sync --version 0.4.226` rc 0.

## v0.4.225 (2026-09-19)

**Two items: an owner ruling re-scoping the Duty T4 census surface, and the measured delivery-path fact that would otherwise have produced a phantom defect.**

1. **The Duty T4 census posts on the Triage lane's OWN topic — board topic 30220 is RETIRED as its target (owner ruling, relayed by the Triage lane 2026-09-19).** Owner, verbatim: *"But why wire it to HQ? It's the subject matter that you own, not HQ, right? You own the issue portfolio, and if you think that HQ needs to know something, you will notify it."* **HQ ruling (Duty 5), settling the Triage lane's open question — the board leg is SUPERSEDED ENTIRELY, not kept for the harvest dimension.** The ruling is a general PRINCIPLE (the subject-matter owner posts on its own surface) and it governs the **harvest-backlog leg too**: the 2026-09-08 "Go" ordered the PATROL, the board target was its *mechanism*, and a later rank-1 owner ruling on the POST TARGET supersedes an earlier one. The harvest backlog IS Triage subject matter (Duty T4 owns upstream lifecycle tracking — `triage.md` §Role boundary). HQ is `session_notify`d only when a dimension is genuinely HQ-specific. The heartbeat duty is unchanged in SUBSTANCE — still one line even on zero-change days, still the patrol-alive signal — only its surface moved.
   - **Why this was structurally impossible, not merely mis-wired:** the patrol's cron (`oc-triage-factory-patrol`, job `0c0b0ba2-473c-42a6-89ea-a2a8f3756043`) delivers to `session:530c29ec` only, so `parse_permitted_targets` yields zero channel targets and `permission()` returns `SendPermission::Nowhere` — the mandated board post could only ever be REFUSED. The patrol reported itself "dimensions-complete, post-blocked" every cycle, and chasing that refusal is what produced **#427** (CLOSED 2026-09-19T23:23:50Z, superseded-by #332). **A law mandating an action the actor's own surface cannot perform manufactures false non-completions**; the fix is to name the surface the actor actually owns. No cron change was made and none is needed — the job's prompt carries no board or census mention; the mandate lived only in law text.
   - **Files:** `triage.md` §Duty T4 (Harvest backlog patrol bullet **+** Checkable Completion Formula) · `upstream-merge-runbook.md` §Upstream-merge cadence · HARVEST LAW (the third carrier of the same target, found by sweep — not named by the reporting lane).

2. **The await record is NOT on the delivery path — recorded so a late notify is not misdiagnosed (measured 2026-09-19).** A `session_notify` that lands minutes late is a symptom of the TARGET'S TURN LENGTH, never of a stale `await_kind`. `AWAITING_CHANNEL` (in-memory, boot-populated by `expect_channel_route`, cleared by `claim_session`) is what `session_routes.rs` consults to choose the parking route; the durable `session_bindings.await_kind/await_ref/await_at` record (fork #344) is read ONLY by the boot classifier and the 5-minute await sweep, and gates nothing. **Measured:** the #437 ruling, sent 22:02:50Z, drained into lane `6cd8175f` at 22:40:34Z — **37 m 44 s** — while that lane sat in an uninterrupted ~40-minute turn (the #438 compaction spiral); the queue drains at the target's **turn boundary**, so a turn that never ends starves its own inbound queue. The investigation that produced this entry opened as a suspected defect and CLOSED AS A NEGATIVE RESULT. Canon: `fleet-directives.md §Cross-lane message delivery discipline`.

## v0.4.224 (2026-09-19)

**Correction + datum refresh on v0.4.223, both caught by reading the shipped text back.**

1. **The v0.4.223 worked-failure clause was stale the moment it shipped.** It read *"the `#346` resume job carries exactly that exposed form and its owner was warned the same turn"*. Both halves were wrong: the job no longer carries that form (its owning lane re-keyed it at 19:59:02Z, **two minutes after the law was committed**), and the warning came from the lane itself, not from HQ. A future reader would have gone looking for an exposed job that no longer existed. Rewritten to record what actually happened -- **the law is the artifact that travels, and the fleet applied it faster than any dispatch could have landed.** Write the rule; do not rely on the hand-carried warning.
2. **The population datum moved again within the hour.** v0.4.223 recorded **14** resume jobs at 19:38Z; the live table read **15** (issue 318 added) by 20:15Z. The law's own point, demonstrated a second time: the NUMBER moves and only the PREDICATE (`name like 'oc-harvest-%-resume'`) is stable, so the derived read stays canonical and any figure written into the file is a dated datum, never a target to match.

3. **The prescribed exposed-set sweep was under-scoped -- a FALSE-CLEAN generator.**
   v0.4.223 told the reader to derive the exposed set with a STATE-FILE grep
   (`grep -n 'trigger_cmd' <state dir>/*-harvest-state.md`). The gate that actually
   runs is `cron_jobs.trigger_cmd` in the LIVE table, and the two diverge:
   `oc-harvest-421-resume` carries a live census gate while `421-harvest-state.md`
   has ZERO `trigger_cmd` hits (250 likewise), so the prescribed sweep cannot see
   those jobs at all -- a tracker-state-dependent gate on a job with no state-file
   row would have read as CLEAN. Raised by lane 61161247, verified first-hand. The
   live-table read is now canonical and the state-file grep demoted to a
   documentation cross-check. Also recorded there: `NULL` is NOT exposure
   (`NoTrigger` falls through to fire unconditionally), so 326 and 341's absent
   trigger is a deliberate satisfaction of the law, not a gap.

**Process hazard surfaced by this very change:** bumping `SKILL.md`'s frontmatter to
the new version in the WORKING TREE publishes an uncommitted version to every lane's
drift sensor -- nine lanes acked `0.4.224` (ledger n=9685-9693) before the commit
existed. Bump the version in the SAME turn as the commit, or lanes adopt a version
whose content is still moving.

4. **The leg-4 discriminator was under-scoped too -- the same class as item 3, a different command.**
   The Duty-5 single-sidedness ruling sanctions two forms of mechanical absence proof:
   `git log -S <string>` returning exactly ONE introduction, or the string absent from
   `git grep` over the pre-fix tree. BOTH are UNSCOPED, and both silently assume the token is
   globally unique -- which the law never said. Measured on `96b474e` (lane c6b1a539, verified
   first-hand): `git grep -nEi 'max_attempts|backoff' 96b474e -- src/cli src/a2a` -> rc=1, ZERO
   hits, the correct pre-fix answer; the SAME grep UNSCOPED -> rc=0, **265** hits, including a
   foreign `const MAX_ATTEMPTS: u32 = 3;` at `src/brain/agent/service/compaction.rs:348`. A
   CORRECT fix therefore fails its own discriminator. The token must now be PATHSPEC-SCOPED to
   the subtree the fix changes, the row must carry the pathspec, and "exactly ONE introduction"
   is recorded as a claim about a SCOPE, never about the tree. Items 3 and 4 are ONE class:
   **a prescribed command that is not scoped to the thing it is asked to prove.**
5. **The CONSENT REGISTER census is a moving datum, and the stricter reading is already OPERATIONAL.**
   Refreshed live at 20:41Z: population **15**, all enabled; **9** prompts carry a binding
   owner-approval gate, **6** silent, **0** unread. The count went 5 -> 6 -> 9 inside one hour as
   lanes self-remediated -- three of them (250, 321, 402) had their prompts rewritten *after* the
   20:17Z census that reported them silent, so that census was correct when taken and stale
   within thirteen minutes. Two divergences are genuine rather than timing: `421` carried a gate
   from 20:02:55Z yet was reported silent, and `396` was reported gated while its prompt carries
   no approval language at all. **The load-bearing part for the owner's pending ruling:** the
   stricter reading is no longer a proposal -- `318` blocks filing on a fourth leg and cites the
   pending ruling verbatim, so a "not required" ruling must UNWIND a gate a lane has already
   implemented, while a "required" ruling is a no-op for it. The register entry now carries the
   predicate and a dated reading instead of a bare figure.

**LOC delta**

| File | Before | After | Delta |
|---|---|---|---|
| `CHANGELOG.md` | 2052 | 2113 | +61 |
| `SKILL.md` | 612 | 612 | +0 |
| `upstream-merge-runbook.md` | 420 | 420 | +0 |

Predicate: `sum(1 for _ in open(f, encoding='utf-8'))`; before = `ceb8e987`, after = working tree.

## v0.4.223 (2026-09-19)

Three law items from one inbound (lane #321, verified first-hand) plus a Duty-5 ruling.

- **The resume idiom now names the GATE SIGNAL, not just the container** (`upstream-merge-runbook.md`
  §Harvest patrol suspension & resume idiom). The section prescribed the state-file name, the cron
  naming, the wake target and the disable-after-harvest step, but said nothing about what SIGNAL the
  `trigger_cmd` must key on. A resume job gating on tracker state goes **permanently silent** when its
  issue is closed early, and the harvest is lost with no signal at all. Worked failure: **#321** was
  closed 2026-09-19T07:43:34Z by the merge commit `7e637c4e3a`, eleven seconds after the ff-merge, with
  the close keyword inside a **negation** (`B5 budget honesty -- Part B alone does NOT fix #321`) -- the
  parser cannot read negation, so the honest-limit prose the process requires is what closed the
  tracker. Law: the gate must key on a tracker-state-INDEPENDENT signal (canonically
  `oc-harvest-census check <issue>`), must fail OPEN, and the exposed set is derived by grepping the
  gate rows, never listed.
- **The enumerated resume snapshot is deleted** (same section). The v0.4.222 snapshot named FOUR
  instances; the live table held **FOURTEEN** by 19:38Z, all enabled. A name list is stale before it is
  committed, so the line now carries a POPULATION with its predicate and timestamp and deliberately
  omits job names.
- **Duty-5 ruling on leg-4 SINGLE-SIDEDNESS** (`SKILL.md` §Test ontology, the leg-4 probe-hygiene
  corollary, answering lane 4b0990b7 / issue #295). The corollary IS the sufficiency test for a
  single-sided probe: the negative half need not be OBTAINED, only NAMED and mechanically shown absent
  from the pre-fix tree (`git log -S` -> exactly one introduction; `git grep` over the pre-fix tree).
  Three conditions: falsifying input stated, absence established by a mechanical discriminator run that
  turn, and the probe observing the RUNNING artifact's own output -- a `strings` dump stays
  presence-only. Where the negative half is structurally unobtainable (prompts are rendered per turn
  and never persisted), the discriminator stands in for it.
- **Recorded, not resolved: a CONTRADICTION in the upstream-PR approval gate** (`SKILL.md` CONSENT
  REGISTER). `§Hard rules` says owner approval remains required; the register's parenthetical lists
  only post-swap rollback as owner-gated; `editor-upstream-pr.md` Phase 7 has no approval step. A
  measured split across the resume-job population (5 gated / 1 asserting / 7 silent / 1 unread).
  Owner ruling requested by lane 329bf3a3 in topic 7198; until it lands, neither surface is edited to
  match the other and the stricter reading binds.

**LOC delta** (predicate: `sum(1 for _ in open(f, encoding='utf-8'))`; before = `f18c10d2^`, after = `f18c10d2`):

| File | Before | After | Δ |
|---|---|---|---|
| `CHANGELOG.md` | 1970 | 2052 | +82 |
| `SKILL.md` | 610 | 612 | +2 |
| `upstream-merge-runbook.md` | 419 | 420 | +1 |

Backfilled 219/220/221/222 in this same bump (all five entries were missing the table; the gap was reported by lane 9fa7c71a and the numbers above were recomputed independently by this lane before use).

## v0.4.222 (2026-09-19)

**The resume-cron instance list at `upstream-merge-runbook.md:314` is replaced by the derived predicate.**

1. **A hand-maintained list of live state cannot stay true.** The line enumerated the known
   `oc-harvest-<issue>-resume` jobs. Lane "Config: Typings & Writers" reported a THIRD instance
   missing (`oc-harvest-396-resume`); a first-hand live read this turn found **FOUR** -- the fourth
   (`oc-harvest-326-resume`) was created at 19:08:23Z, twelve minutes AFTER the census the list had
   been written from. The canonical read is now the predicate itself:
   `select name, id, enabled, cron_expr from cron_jobs where name like 'oc-harvest-%-resume'`.
   The names survive only as a timestamped snapshot, explicitly marked "re-derive before acting".
2. **Sweep by PROPERTY, never by token.** The same lane's first sweep pass used a token grep
   (`RETIRE THIS JOB`) and flagged `oc-harvest-396-resume` as a gap; that job's prompt says
   `DISABLE THIS JOB`, so it was fully compliant. The compliance question is a property -- *does the
   prompt instruct self-disable, in ANY wording* -- and a token grep manufactures false defects
   against compliant lanes. Codified beside the instance list.
3. **Not a defect, and nothing owed:** `oc-harvest-396-resume` satisfies both legs (state file line 52
   "## MANDATORY -- disable after harvest", and the prompt instruction present). `oc-harvest-dispatch-4h`
   remains `enabled=0` per the standing suspension -- not re-enabled on a lane's initiative.

**LOC delta** (predicate: `sum(1 for _ in open(f, encoding='utf-8'))`; before = `f18c10d2^`, after = `f18c10d2`):

| File | Before | After | Δ |
|---|---|---|---|
| `CHANGELOG.md` | 1950 | 1970 | +20 |
| `SKILL.md` | 610 | 610 | +0 |
| `upstream-merge-runbook.md` | 417 | 419 | +2 |

## v0.4.221 (2026-09-19)

**T9's harvest COMPLETED — upstream PR [adolfousier/opencrabs#1629](https://github.com/adolfousier/opencrabs/pull/1629) MERGED by the maintainer.** Reported by the Editor lane "rich-formatting" (#1230/#233 bundle) and verified first-hand before any edit: `gh pr view 1629 --repo adolfousier/opencrabs` → `state=MERGED`, `mergedAt=2026-09-19T16:18:50Z`, `mergedBy=adolfousier`, `mergeCommit=0d9beb2bad2efa7ba26c9d9fcfbd90ea4b98b080`, `head=9d2c9645a589405df6c4e89d222a7fe06708a0ff`, `createdAt=2026-09-18T02:30:54Z`.

1. **The freeze does not reach a pre-freeze-filed PR (new ruling, `fleet-directives.md`).** The reporting lane asked whether the freeze covers a PR filed before it existed; it does not, and cannot. `#1629` was filed **15 h before** the owner's `2026-09-18 17:33Z` freeze order, and the merge was the maintainer's own action on his side of the wall — the freeze withholds *our* upstream push, not his merge button. No lane breached the freeze. T9 is therefore recorded in a new `merged_by_maintainer` key in the json block rather than moved to `released`, because `released` means "the owner released this group for US to harvest" and T9 needed no release.
2. **The heads-up question is MOOT, not missed.** `gh api repos/adolfousier/opencrabs/issues/1629/comments` returns **zero** comments; the only event is the maintainer's own `COMMENTED` review at `14:51:52Z`, **87 min before** he merged. The long-open observation about whether this PR ever got its heads-up is now closed as moot.
3. **`upstream-merge-runbook.md` item 7 — the SHIPPED-UPSTREAM notify duty can be DISCHARGED BY SELF-DISCOVERY.** When the owning lane discovers the merge itself and reports it to HQ, sending the notify back to that same lane is a duplicate report — noise, not diligence. Recorded as law with this merge as the worked instance (the lane stamped ledger `n=9589`). The `#233` line in the harvest-resume section no longer describes `#1629` as open.
4. **T9's fork-side duty has ENDED** (`editor.md` Phase 6b item 6): #233/#237/#247/#265 carry no further fork maintenance and no fix rounds; all four fork issues are CLOSED.

**LOC delta** (predicate: `sum(1 for _ in open(f, encoding='utf-8'))`; before = `1dc24fe1^`, after = `1dc24fe1`):

| File | Before | After | Δ |
|---|---|---|---|
| `CHANGELOG.md` | 1941 | 1950 | +9 |
| `SKILL.md` | 610 | 610 | +0 |
| `fleet-directives.md` | 610 | 627 | +17 |
| `upstream-merge-runbook.md` | 410 | 417 | +7 |

## v0.4.220 (2026-09-19)

**Stale refusal-handling bullet corrected (`SKILL.md` §session_notify mechanics).** Reported by the Editor lane "Push to session" (#393) and verified first-hand before the edit: `grep -rn 'resend with' *.md` over the skill dir returned exactly ONE hit — the bullet still reading *"a mid-turn refusal is NOT delivery … resend with `interrupt: true` in the same turn"*. It contradicted `SKILL.md:193` IN THE SAME SECTION (`interrupt` = legacy alias, INERT) and `fleet-directives.md:415` (escalation: there is NONE). The reporting lane places it as the eighth site of the interrupt-stale-text family, missed by all four earlier waves (v0.4.212 `toolsmith.md`, v0.4.213 `fleet-directives.md`, v0.4.215 `hq.md` ×2).

**The replacement deliberately does NOT over-claim.** The lane's second reason is exact — `interrupt: true` selects no behaviour (#373) — but its first reason, "the refusal state cannot occur", holds ONLY FOR THE `session_notify` PATH: `src/brain/tools/subagent/notify.rs:371` hardcodes `let interrupt = true;`, bypassing the mid-turn gate at `src/brain/agent/service/session_routes.rs:336`. `Delivery::RefusedInFlight` is nonetheless still constructed at `:341` and reached with `interrupt=false` from `quiet_delivery.rs:199`, `a2a/handler/notify.rs:266` and `cron/scheduler.rs:1174`. The new bullet therefore states that the `session_notify` route never refuses and a busy target QUEUES for its next tool-loop boundary, and explicitly forbids generalising it to "there is no refusal path".

**Correction carried in the same breath:** the reporting lane withdrew its own in-flight claim that this site was "already filed as HQ's lens-B FINDING 2" — no such filing exists.

**LOC delta** (predicate: `sum(1 for _ in open(f, encoding='utf-8'))`; before = `dfcbda74^`, after = `dfcbda74`):

| File | Before | After | Δ |
|---|---|---|---|
| `CHANGELOG.md` | 1933 | 1941 | +8 |
| `SKILL.md` | 602 | 610 | +8 |

## v0.4.219 (2026-09-19)

Harvest-patrol suspension + resume idiom codification. Two laws and one live instrument fix, from a process contradiction the #421 editor lane filed (ledger n=9566) and an HQ investigation that CONFIRMED its facts while CORRECTING its diagnosis.

**1. The harvest patrol is OFF under the OWNER'S order — and the disable is not the repace's collateral (`upstream-merge-runbook.md §Harvest patrol suspension & resume idiom`).** Three sites in the runbook described `oc-harvest-dispatch-4h` (id `73158e43-3b04-4464-bf82-8d9065a191bb`) as a live 4h job. It is neither live nor 4h: live `cron_expr` is `15 3,9,15,21 * * *` (6h — already at the 2026-09-18T21:15:10Z cadence floor), `enabled=0`. **The disable is the owner's own order of 2026-09-18T20:41:30Z** in *Opencrabs Dev Factory* — *"Turn off all of your pacemakers for now"*, preceded 14 seconds earlier by *"Until I lift the freeze"* and followed by *"We are drowning in slop"*. The separate `21:15:10Z` message is a CADENCE CAP, not the disable, and the 21:49Z repace swept `cron_expr` + `updated_at` only. **A ledger row whose `updated_at` sits inside that sweep window is a CORRELATION, not a cause** — the Triage census `n=9019` read it as the cause and called the four patrols *"collateral of a cadence sweep they never violated"*; the disable predates the repace by ~68 minutes. Corrected append-only at **n=9570** (`n=9019` itself untouched). The 2026-09-19T03:01:53Z partial lift re-authorises the TRIAGE cron ONLY (`oc-triage-factory-patrol`, `oc-triage-owner-digest`); the harvest patrol is not covered. **Ruling: NO re-enable — a re-enable is an owner decision, not a lane decision** (n=9569). Sweep, per the v0.4.218 §3 rule: the same stale live-patrol claim was corrected in `fleet-directives.md` (the owner-push-freeze machinery leg, now marked VACUOUS until the order lifts), `triage.md` (the T4 liveness patrol — an owner-ordered OFF is not a dead cron, and flagging it re-reports the owner's order back to him) and `toolsmith.md` (the cron-liveness audit — re-arming an ordered-off patrol is a VIOLATION, not a repair).

**2. The harvest-resume idiom is codified — it was written down NOWHERE (`upstream-merge-runbook.md`, same section).** `grep -rn "harvest-state" skills/opencrabs-dev/` returned **0 hits** while four harvest-state files and two resume crons existed on disk: every lane hand-rolled the mechanism. A parked harvest therefore resumed only if its own lane remembered — live instance `#352`, HELD (`HELD_IN_FLIGHT_LANE`) with no resume cron at all. Codified shape: state file `<state dir>/<issue>-harvest-state.md`; cron name `oc-harvest-<issue>-resume` (namespaced per the cron law, **job id carried in anything durable**); wake target = the OWNING lane, never the board; and **a disable-after-harvest step is MANDATORY** because a 5-field cron has no one-shot form — a resume job re-fires annually on the same date (the #421 job `677660a3` would fire again on 2027-09-20), so the instruction belongs in BOTH the state file and the job's own prompt.

**3. `$STATE/pacemakers-off` marker lifecycle — a check that re-reported the owner's order as a defect.** `oc-health` class 5 reads `<state dir>/pacemakers-off` to choose its direction: marker PRESENT -> a law-carrying patrol found ENABLED is the finding; marker ABSENT -> a DISABLED patrol is the finding. The marker existed in NO profile, so the check ran its order-lifted branch and emitted `8 QUIRK cron-disabled` naming the four patrols the owner had switched off — the exact failure `tools/HEALTH-CLASSES.md` forbids. Lifecycle now stated in `tools/HEALTH-CLASSES.md` and the marker planted (`opencrabs-dev/pacemakers-off`, carrying the order, its scope, the triage-only partial lift, and the removal condition). Receipt: `./tools/oc-health --class schedulers` -> `ok crons: pacemakers-off order honoured, zero DM leaks`, **0 finding(s)**, rc=0.

**Open owner question:** restore `oc-harvest-dispatch-4h` at its 6h cadence, or keep it off until the freeze lifts?

**LOC delta** (predicate: `sum(1 for _ in open(f, encoding='utf-8'))`; before = `9c6ccbbe^`, after = `9c6ccbbe`):

| File | Before | After | Δ |
|---|---|---|---|
| `CHANGELOG.md` | 1921 | 1933 | +12 |
| `SKILL.md` | 602 | 602 | +0 |
| `fleet-directives.md` | 610 | 610 | +0 |
| `tools/HEALTH-CLASSES.md` | 176 | 176 | +0 |
| `toolsmith.md` | 159 | 165 | +6 |
| `triage.md` | 327 | 334 | +7 |
| `upstream-merge-runbook.md` | 397 | 410 | +13 |

Backfilled at v0.4.223. **Note: this bump's COMMIT MESSAGE published churn (added+deleted), not net delta** -- churn matches all six of its claims, net matches two; the table above is net.

## v0.4.218 (2026-09-19)

Duty-4 cycle `20260919-c21`: thirteen codified items across eight files (+99/−7). Two are HQ RULINGS; the rest are filed defects, each with a live incident behind it rather than a preference.

**1. RULING — `target=` is the DEPLOYMENT UNIT, never the discharged sha (`upstream-merge-runbook.md §Ledger hygiene laws`).** The key was in canonical use by every lane and defined nowhere, and the two tools that write it agree on the meaning: `oc-smoke-evidence` writes `target=${LATE_TARGET:-live-ops}`, `oc-smoke` writes `target=${TARGET}` — *the unit the verdict is about*. It is NOT the subject of the smoke and NOT the sha a fan-out row discharges; the subject goes in `evidence=`. Measured: **217 of 251 token-bearing rows carry `target=`, across 121 distinct values, and 72.8% of those are free text** rather than the tool default — the field is unqueryable in practice while no consumer reads it. A lane that writes the notified sha into `target=` while `sha=` names the live binary splits one key into two meanings, and a consumer reading by key cannot tell which convention a row follows.

**2. RULING — the design gate covers DESIGN CHOICES, not mechanical repairs (`fleet-directives.md §Discussion links + fix-approval gate`).** Item 2 is absolute about *designs*; it was being read as a claim that every line of code needs its own diagrammed card. A Toolsmith lane arrived with two readings and no rule to pick between them — (a) an HQ-dispatched work order satisfies the gate, (b) the gate is literal and lane-agnostic — and the worse half was that the ambiguity made its ALREADY-LANDED work's compliance unauditable, not merely future work uncertain.
- **Mechanical repair — gate NOT triggered.** Exactly ONE possible shape: a wrong constant, a missing match arm, an off-by-one, a mis-quoted flag, a reopened-issue override. The issue body fully specifies the change, so an HQ dispatch satisfies the gate.
- **Design choice — gate TRIGGERED, owner approval required.** Any fix whose shape is NOT forced: a HEURISTIC (its false-positive/false-negative rate is the thing being chosen), a behavioral change, a new schema field or vocabulary token, a new default, or a choice among viable options.
- **The test is the OPTION COUNT, not the size of the diff.** A one-line heuristic is a design choice; a 200-line mechanical sweep is not. Live case: `leshchenko1979/opencrabs#416` is correctly blocked on this ruling — its second leg needs a heuristic for deriving an issue's own surface, and that heuristic can produce false refusals. **Owner confirmation of the split is PENDING.**

**3. A re-ruling ships a SWEEP, not only an edit (`fleet-directives.md §Cross-lane message delivery discipline`).** When a ruling changes what a term MEANS — retiring a mode, inverting a default, converting a parameter from active to INERT — the same wave MUST `grep -rn '<old spelling>' --include='*.md' .` (excluding `CHANGELOG.md` and `reviews/`), correct every hit or file it explicitly against its owning file, and keep the sweep output as completion evidence. **Live case:** the 2026-09-19 03:34:30Z / 03:36:54Z re-ruling changed three things at once (`turn-end` default, `now` retired-and-erroring, `interrupt` inert) and the law text did not follow it — **seven `interrupt` sites across four files** were corrected over THREE separate waves (v0.4.212 `toolsmith.md`; v0.4.213 `fleet-directives.md`; v0.4.215 `hq.md`, two sites, found while grepping for an unrelated task), where one grep at re-ruling time returns all seven at once. The `hq.md` Duty-3 row was the worst member: it prescribed `delivery=now` + `confirm=true` for CRITICAL notifies and called `interrupt=true` a failsafe, so a lane following it would have FAILED its delivery outright.

**4. D1 gains an IDENTITY leg — a number is a REFERENCE, not evidence (`fleet-directives.md §Dispatch Eligibility D1`, filed by the Triage lane).** A commit can name `#N` in its subject while implementing a different subsystem, and every landed/merged inference downstream then reads N as done. `landed` therefore ALSO requires that the naming commit's changed files intersect the issue's own surface; the same leg applies on the HARVEST arm, and a REOPENED issue overrides the merged inference.
- **Live instance, receipted:** `oc-harvest-census check 199` → rc=1 `REFUSED: Target 199 is already MERGED upstream in PR #1557`, while `gh pr view 1557 --json state,mergedAt` → `state=CLOSED, mergedAt=null`. The content IS upstream (`132da1fcc fix(loop-guard): exempt paginated arguments … (#199)`) but `#199` itself is a different subsystem (OPEN/REOPENED, the a2a gateway listener), and the landed commit `b10ca242f` touches `helpers.rs`, `profile.rs` and two test files — **0 files under `src/a2a/`**. The issue→PR map is built from the title's trailing `(#N)` and the head branch name, so a corrupted `(#N)` poisons it PERMANENTLY — the squash sits in upstream history forever. Editor lane `c6b1a539` claimed #199 at 15:18:28Z (n=9501), so the Phase-7 harvest gate would have refused legitimate, freshly-built work.

**5. Stale notified sha — resolve by IDENTITY, then smoke the RUNNING binary (`s2-swap-journal-spec.md`).** A fan-out names the sha whose range attributed your commits, and the box swaps on its own cadence. The filing lane's measurement: the notice for run `35441550360` named `b2823127` (swapped 12:14:45Z, so the notice lagged the swap by **22m33s**), and **six distinct shas were swapped across the 12:14:45Z–15:14:40Z window (span 2h59m55s, mean inter-swap gap 36.0 min)**, 17 across the day. A mean gap shorter than a typical design→ship→smoke cycle makes "the notified sha is no longer live" the NORMAL case, not an edge. The law now prescribes: read the running identity, and if the notified sha is superseded verify LINEAGE first (`git merge-base --is-ancestor <notified-sha> <live-sha>`, rc 0) before smoking the LIVE binary; cite `sha=` = the LIVE sha driven, `target=` = the unit, and carry the link the fan-out exists to create in `evidence=discharged-notified-sha=<sha>`. **Never cite a sha you did not drive** — a row whose `sha=` names the notified sha while the probe ran against a newer binary is a FALSE receipt.

**6. `oc-smoke` PASS clears the LANE fence only — the census fences are independent (`upstream-merge-runbook.md`).** The stamp closes the worker's own in-flight claim; it does NOT make `oc-harvest-census check <issue>` return ELIGIBLE. The census carries four independent rc=1 fences — already MERGED/IN_FLIGHT, the unit's own 24 h feature soak, `HELD_DEPENDENT_SOAK`, and `HELD_IN_FLIGHT_LANE` (the unit touches files of an active in-flight lane — by construction often a PEER lane's claim, which no stamp of the worker's own can ever clear). A refusal after a green PASS is the EXPECTED state for a `fix/*` inheriting a parent feature's soak window: read the token and its named feature, do not re-stamp, and do not treat the refusal as a defect in the stamp leg.

**7. The census soak `age` is a CLAIM about the anchor, not a receipt of it — and `0.0h` means PRE-ANCHOR (`upstream-merge-runbook.md §24-Hour Feature Soak`).** `oc-harvest-census` composes the anchor from up to three sources (the swap lineage, `twin_deploy_ts`, and a `smoke-verdicts.log` fallback) and prints only the resulting `age`, disclosing which source produced it to nobody — so a printed age is authoritative only once its provenance is confirmed against the swap journal. A lane whose harvest ETA turns on the number MUST reproduce it from the swap journal entry for the commit's deploying sha, and a refusal whose `age` cannot be reproduced that way is a TOOL defect to file, never a soak to wait out. For a `feat/*` committed to fork `main` but not yet swapped there is no anchor at all and the age clamps to `0.0h` — the WORST available reading, because `0.0h < 24h` is indistinguishable from "deployed seconds ago": the harvest ETA there is the NEXT SWAP, not a time 24 h out.

**8. Verdict-row mechanics: flatten the PAYLOAD, repair IN PLACE, and `CORRECTION` covers form fixes (`upstream-merge-runbook.md §Ledger hygiene laws`).** (a) Tail normalization protects the DESTINATION; it says nothing about the text being appended, so an embedded newline splits the row — flatten before appending, or route the append through `oc-smoke`'s `flatten` + `append_log_safe`, which already do both. Repairing a malformed row must be done IN PLACE, never by rename or truncate: the log is appended to concurrently by other lanes, and a rename replaces the inode, orphaning the file descriptors held by their `>>` writes and silently dropping their rows. (b) `CORRECTION` is widened to cover **administrative/form fixes** — a citation defect, a mislabeled field, a wrong `target=` — which need no re-verification (same binary, same sha, same probe) and are neither a re-verification nor a withdrawal; `RETRACTION` remains the token for WITHDRAWING a verdict. Off-taxonomy improvising stays banned: `RE-VERIFY` was written by **14 lanes in one wave** (14 rows / 14 distinct lanes).

**9. Sibling tools carrying a COPY of a predicate are ONE change surface (`toolsmith.md §Explore & DRY gate`, item 6).** Item 2's `grep -rn 'oc-<tool>'` finds CALLERS of a tool, not sibling tools carrying a copy of its predicate; item 3's DRY gate is scoped to `tools/lib/` helpers. When you correct a filter, a classifier, or any predicate, grep its distinctive literal (a marker string, a tuple, an rc token) across `tools/` and land the change in EVERY carrier in the SAME commit — or extract it to `tools/lib/` if the call sites genuinely share it. **Live case:** `oc-harvest-census check 352` → rc 0 `ELIGIBLE` while `oc-harvest-dispatch vet 352` → rc 1 `UPSTREAM_VOID` on the SAME issue — the two tools then return different answers about the same input, which is a live CONTRADICTION, not a partial fix. The corrected predicate had already been authored for `tools/oc-harvest-census` in `88eb9fd3` (**1 file changed**) with `tools/oc-harvest-dispatch` untouched, while the paired pattern was already on record (`84013db7` landed its shared change in BOTH tools plus a negative control). Cost of the miss: a full root-cause cycle — three commits, an asymmetry proof, source reads of both filters, a Toolsmith dispatch — for a one-file diff.

**10. `oc-prchecks resume <run-id>` — rc-5 in-flight-timeout recovery (`SKILL.md` tool register).** RE-ATTACHES to a run this lane WITNESSED: no dispatch, no adoption. The rc-5 stdout carries the run id + URL for exactly this (`extra.run_id` in the journal is the same handle).

**11. Leg-4 probe hygiene — three ways a probe measures nothing and still reports PASS (`SKILL.md §Test ontology`, lane `212b3c83`).** (a) **Artifact binding:** rendering bytes and delivered bytes are different artifacts, because the delivery path re-encodes (Telegram converts renders to JPEG) and a re-encode destroys fine-stroke measurements — where both are needed, state TWO legs with distinct criteria and say which criterion binds to which artifact. (b) **Measure from the artifact, not the constants:** if every argument to the metric is a literal declared beside the threshold, the metric measures the source file, not the artifact, and passes on any input; and a bucketing/matching tolerance must be strictly smaller than the separation between the buckets it distinguishes, or the metric silently becomes a count of the union. (c) **Spill-directory completeness:** results under the inline threshold produce NO spill file, so a spill-only harvest has a hole exactly where the newest evidence sits — and because expired attachment URLs are skipped silently and the skip reads as absence, report the skipped count beside the found count ("0 found, 13 skipped as expired" is a different verdict from "0 found"). **Corollary binding all three: a leg-4 probe reports PASS only if it would FAIL on the pre-fix artifact — state the input on which it fails.**

**12. Editor-law corrections (`editor.md`, four findings).**
- **Leg 1's DEFAULT gate is FAST, and FAST is NOT the CI-gate leg of the 4-leg rubric** (`127429e6`): `oc-ship-chain` passes `--fast` to `oc-prchecks` unless `--full`/`--no-fast` is given, and `--fast` runs **fmt + clippy only, tests skipped**. The only visible marker is the job name's `… — FAST` and a `Run tests` step reading `skipped`; citing such a run leaves the smoke receipt with **no all-features test evidence at all** — the exact leg the "corrected-code presence ≠ smoke success" law protects.
- **Conflict-quality gate item 4 — prove nothing was lost** (`6cd8175f`): `oc-rebase-safety audit` cannot settle this after a rebase onto a MOVED main — every file both sides touched reports `CHANGED`, so the SUMMARY line reads `LOSSES FOUND — full re-gate required` even when zero content was lost. Read the audit's `DROPPED` rows as the loss signal; treat `CHANGED` as indeterminate and confirm with `git diff <new-base> HEAD --stat`.
- **Post-landing-lock ancestor re-check before LEG3** (`127429e6`): the gate runs BEFORE the landing lock is taken and LEG3 is a bare `git merge --ff-only` that rebases nothing of its own, so any lane landing on fork `main` inside that window makes your branch a non-fast-forward and LEG3 dies `rc 5`. Re-check ancestry against `origin/main` after acquiring the lock — and note this is the OPPOSITE fix to the v0.4.214 local-main reconcile, which shares the same `rc 5`.
- **Receipt surface for a channel-RENDERING defect is the DELIVERED message, never a stored row** (`1a63f103`): the `pending_followups` row (`host_html`/`host_markdown`) is written BEFORE `normalize_rich_markdown_with_media` → `enforce_button_fit`, so it is the PRE-enforcement source and cannot witness a defect that stage introduces or repairs. Read the delivered text instead (`tg_get_messages` on the host message id, or the telemetry line `Telegram send ok: … msg=<id> len=<n> hash8=<h>`); a render verdict resting on a stored row is `UNPROVEN`, never PASS.

**13. Read the ADVISORY drop-list before branching (`editor-upstream-pr.md`, finding `63d775f9`).** rc=0 `ELIGIBLE` means the target is **unharvested**, NOT that its feature can travel alone — Gate 4 (`#365`) passes when **at least one** derived subject symbol resolves upstream, so an ELIGIBLE unit may still have its whole **substance** inside a fork-only symbol. Read every `ADVISORY: hunk inside fork-only symbol — dropped at packaging` line (emitted on the rc=0 path; the ONLY substance-portability signal) and judge whether the dropped symbols ARE the unit's substance or merely incidental. If the substance is dropped, the unit is a CHILD of the fork issue that introduced that symbol: parent-link it and do **not** branch until the parent is merged upstream. The v0.4.71 symbol sweep is a **POST-branch** check and does **not** substitute. (Incident: `#250` read as "branchable alone" off `ELIGIBLE … clean to branch and gate` with four ADVISORY lines in the same output.)

**LOC** (predicate: `python3` `sum(1 for _ in open(f, encoding='utf-8'))` per file; before = after − added + deleted from `git diff --numstat`):

| File | Before | After | Δ |
|---|---:|---:|---:|
| `SKILL.md` | 577 | 602 | +25 |
| `editor.md` | 512 | 533 | +21 |
| `fleet-directives.md` | 598 | 610 | +12 |
| `editor-upstream-pr.md` | 317 | 328 | +11 |
| `s2-swap-journal-spec.md` | 107 | 118 | +11 |
| `hq.md` | 300 | 305 | +5 |
| `upstream-merge-runbook.md` | 392 | 397 | +5 |
| `toolsmith.md` | 157 | 159 | +2 |
| **TOTAL** | **2960** | **3052** | **+92** (+99/−7) |

**Substrate filings from the same cycle:** `#418` — `session notify` exit 4 is a catch-all (usage errors and retired modes land on the transport code, and the documented exit table omits both); `#419` — the `session_notify` `target_session` schema omits the same-process/profile constraint and the `a2a_send` bridge, so the boundary is discoverable only by a failed call.

## v0.4.217 (2026-09-19)

Three items: two law-text corrections filed by active lanes, and one defect found while preparing this very bump.

**1. D1's git arm has TWO ref forms — my v0.4.216 tightening was NARROWER than the code (filed by the Triage lane).** v0.4.216 replaced D1's "a commit referencing the issue on fork `main`" with "a commit on fork `main` carrying an `Issue-Ref: #N` trailer (git arm — trailer-based, NEVER commit-message prose)". That is over-narrow. `tools/oc-issue-dispatch:463-465` carries a SECOND arm inside arm A:

```python
m = re.search(r"\(#([0-9]+)\)\s*$", subj.strip())
if m: landed.add(int(m.group(1)))
```

— a trailing `(#N)` in the commit SUBJECT, fork-scoped by the same `Session-Id` discriminator (`:401-408`), lands the issue with NO `Issue-Ref` trailer required. The tool's own battery proves it fires: selftest 61 = "arm A POSITIVE CONTROL: a fork commit lands (#29)", fixture `_mk("fix: fork landing (#29)", ["Session-Id: 1111…"])` at `:1370`, assertion `29 in _armA`; `--selftest` → rc=0, 64/64 OK. D1 now names both forms and keeps the load-bearing half (NEITHER is commit-message prose).

**Scope: this does NOT disturb the #199 root cause.** `b10ca242f`'s subject ends "…near-match loop detection" with no trailing `(#N)`, so the subject arm never fired there — the `Issue-Ref: #199` trailer did, and ledger claim `n=4683` remains the single point of corruption. The v0.4.216 close-identity guard's rationale ("a trailer or auto-link naming #N is an ATTRIBUTION, not identity") already covers both arms; only D1's description of the surface understated it.

**2. Two law sites under-described the fan-out sweep (filed by Toolsmith; the `tools/` half had already landed).** `oc-attrib --deployed` now IMPLIES `--novel`: the sweep additionally drops re-sha'd twins (patch-id equivalence, `git cherry`) and empty commits; merges pass through unfiltered; a zero-row sweep is **rc 0 GREEN**, never rc 3. Measured on live range run 35441550360 (`74a64245b..b2823127a`): 310 raw → 276 replayed + 11 empty dropped → 34 novel; contributor rows 32 → 2.
- `s2-swap-journal-spec.md` §Post-swap notify — the v0.4.133 `--first-parent` paragraph named the sweep's ONLY filter; the novelty filter is a SECOND, independent exclusion, and it is the one that covers the REBASE case that paragraph never mentioned.
- `SKILL.md` tool register — the `oc-attrib` row omitted `--novel` / `--no-novel`; `--no-novel` is the escape hatch back to the raw range.

**3. NEW DEFECT — an uncommitted version bump is already fleet-visible, and it had silently misattributed an anomaly to a lane.** `tools/oc-drift-check:78` resolves the live version by grepping **the on-disk canonical `SKILL.md`**, not the ledger:

```sh
cur="$(grep -E '^version:' "$SKILL_DIR/SKILL.md" 2>/dev/null | head -1 | awk '{print $2}')"
```

So the moment the author writes `version: 0.4.217`, before any commit or sync, every lane running `oc-drift-check --ack` stamps **0.4.217** — a version with no `skill-bump` ledger event, while `current_skill_version` still reads 0.4.216. Observed live during THIS bump: acks `n=9474/9475/9477/9478` all name 0.4.217, while the last `skill-bump` event is `n=9462` = 0.4.216.

**This retroactively corrects a misattribution.** The sixth checkpoint recorded "lane `d18ce16a` acked 0.4.215 while the ledger read 0.4.214 — a lane acked an unsynced version" as lane misbehaviour. It was not: at that moment `SKILL.md` on disk already read 0.4.215 from an in-flight author edit. **"Acked version > ledger version" is an author-window artifact, never evidence against the acking lane** — the same class as the standing law that an attribution taken from a name or from row adjacency is not a read of the object. Law added to `hq.md` Duty 1: the version bump is the LAST edit and sync runs in the SAME turn, nothing left uncommitted across a turn boundary. Routed to Toolsmith as well, since `tools/oc-drift-check` is their surface (a "no skill-bump event for the on-disk version" warning is theirs to judge).

**LOC before/after** (owner order: the LOC check is part of every law change):

| File | Before | After | Δ |
|---|---|---|---|
| `fleet-directives.md` | 598 | 598 | 0 |
| `s2-swap-journal-spec.md` | 105 | 107 | +2 |
| `SKILL.md` | 577 | 577 | 0 |
| `hq.md` | 291 | 300 | +9 |

Both new law bodies landed in **under-budget** files (`s2-swap-journal-spec.md`, `hq.md`) for exactly that reason. Three law files remain over the 500-line budget: `fleet-directives.md` 598, `SKILL.md` 577, `editor.md` 512 — plus the shared ops `AGENTS.md` at 531, which is outside this repo and not versioned here.

## v0.4.216 (2026-09-19)

**Close identity guard — a close must confirm the cited artifact touches the issue's own surface.** Filed by the Triage lane, verified first-hand, and the ROOT CAUSE turned out to be somewhere neither the filing lane nor the law had looked.

**What happened.** #199 ("fix(a2a): the gateway listener is load-coupled to the agent runtime") was closed by a Triage hygiene sweep on 2026-09-14T08:04:27Z, citing sha=`b10ca242f` + upstream PR 1557. `b10ca242f` is a **loop-guard** commit (`fix(loop-guard): exempt paginated arguments…`) touching `helpers.rs`, `profile.rs`, `loop_guard_test.rs`, `profile_pid_lock_test.rs` — **0 files under `src/a2a/`**. The issue was correctly reopened by the detecting lane on 2026-09-19 and its defect is still live.

**The filing lane's mechanism claim was WRONG, and the correction moved the root cause.** The report held that D1's git arm is "a TEXTUAL reference, which is exactly what admitted this close". It is not: `tools/oc-issue-dispatch:434-436` reads `%(trailers:key=Issue-Ref,valueonly,…)` and line 451-452 **skips any commit without a `Session-Id` trailer**. It matches `Issue-Ref` TRAILERS; a `(#199)` typed into a message body would never have matched.

**Actual root cause — one corrupted input, faithfully propagated by every mechanical step downstream:**
1. Ledger row **`n=4683`** (2026-09-13T20:10:43Z, session `40427d4f`): `CLAIM #199 — fix(loop-guard): exempt paginated arguments…` — the **claim itself named #199 for #219's work**.
2. `tools/oc-commit:176` derives `Issue-Ref` via `claim-ref "$OC_ACTOR" --open` (the actor's latest OPEN claim) → faithfully emitted `Issue-Ref: #199`.
3. `b10ca242f` really carries `Issue-Ref: #199` + `Session-Id: 40427d4f-…`.
4. `fetch_landed_issues()` → #199 reads LANDED. Mechanically correct.
5. The sweep closed #199 on a harvest-gated close. Correct form, wrong issue.

**The guard, and why it went where it did.** A surface check WOULD have caught this — the commit's files share no path with #199's a2a surface — so the ask was right even though its mechanism was wrong. But it belongs on the **CLOSE path** (`triage.md §Autonomous closure`), **not in D1**: D1 is *dispatch eligibility*, whose git arm is deliberately conservative (a false "landed" merely suppresses re-dispatch), whereas the harm here happens at the *close decision*. Conflating the two puts one predicate with two opposite error costs. D1's git arm is therefore NOT amended; only its **law text** was tightened to name trailers explicitly, so the law stops reading looser than its own implementation.

**Second, live harm the report did not raise.** #199 still carries `Issue-Ref: #199` on fork `main`, so it still reads landed and **will never be re-wired by the dispatch sweep** despite being OPEN with its work genuinely undone. Rule added: **a REOPENED issue overrides the landed arm.** That half touches `tools/oc-issue-dispatch` → routed to Toolsmith as their surface.

**LOC before/after** (owner order: the LOC check is part of every law change):

| File | Before | After | Δ |
|---|---|---|---|
| `triage.md` | 294 | 316 | +22 |
| `fleet-directives.md` | 598 | 598 | 0 |
| `SKILL.md` | 577 | 577 | 0 |

The guard was placed in `triage.md` **deliberately** — it is the under-budget file (316 < 500). `fleet-directives.md` (598), `SKILL.md` (577) and `editor.md` (512) all remain over the 500-line budget, so the one place a new law could land without worsening the metric is the one it landed in.

## v0.4.215 (2026-09-19)

Two stale-law sites closed, both reported by active lanes, both verified first-hand before the edit.

**1. `hq.md` carried the PRE-re-ruling delivery cadence — the THIRD site of the family (filed by editor lane d18ce16a).** Two sites in the one file:
- line 97, the Duty-3 confirm-law row: prescribed `delivery=now` + `confirm=true` for CRITICAL notifies and called `interrupt=true` a "failsafe". `now` now **FAILS the delivery outright** (`notify_policy.rs` → `Err`, #373), so the row taught a mode that cannot be sent — a lane following it loses the notify entirely, not merely its escalation.
- lines 118-120, the Duty-3 blockquote: "quiet DEFAULT, turn-end for boundary-bound signals, `interrupt=true` failsafe ONLY for urgent wakes a lane is blocked on" — the INVERTED default plus a non-existent escalation, citing the superseded 2026-09-04 law and a `SKILL.md` section that now says the opposite.

Proof (same-turn, read-back-immune): `grep -rl 'quiet DEFAULT' --include='*.md'`, excluding `CHANGELOG.md` and `reviews/`, returned EXACTLY ONE live law file — `hq.md`. Canonical counter-texts confirmed live in the same pass: `fleet-directives.md` "Escalation: there is NONE" ×1; `SKILL.md` "accepted but INERT" ×1. The family is now closed at all three sites: `toolsmith.md` (v0.4.212), `fleet-directives.md` (v0.4.213), `hq.md` (this bump).

**2. `SKILL.md` §Hard rules contradicted itself on the fork-claim mechanism (lens-pass finding, left unfixed by the v0.4.209 pass).** Line 553 read "fixer claims via a `gh` comment on the issue + an `oc-ledger claim` row"; line 511 of the SAME file reads "Fork issues NEVER claimed on GitHub: no tackling comments, assignment, labels/reactions by any lane — claiming = `Issue-Ref` trailer + workers-ledger `claim` row". A cold reader took the wrong mechanism from the wrong line. Fixed to the canonical mechanism only: ledger `claim` row + `Issue-Ref` trailer, NO `gh` comment, assignment or label.

**LOC before/after:**

| File | Before | After | Δ |
|---|---|---|---|
| `hq.md` | 288 | 291 | +3 |
| `SKILL.md` | 576 | 576 | 0 |
| `CHANGELOG.md` | 1774 | 1798 | +24 |

**What this bump did NOT do.** No `tools/` path touched. **No mass fanout wave:** `fleet-directives.md` v0.4.172 (owner order 2026-09-14) reserves proactive `oc-notify-fanout` waves for breaking process shifts, fleet-wide safety halts or explicit owner-ordered fleet reloads, and routes routine bumps through JIT pull-absorption — so the filing lane is answered directly instead of pinging 29 lanes for a +3-line correction. The four 500-line-budget law files are STILL over: `fleet-directives.md` 598, `editor.md` 512, `SKILL.md` 576, ops `AGENTS.md` 531.

**Finding filed, NOT fixed (brain file — the owner's call).** ops `AGENTS.md:277` still orders "every skill version bump / law change → quiet-notify all active lanes", which the v0.4.172 order supersedes for routine bumps. Reported to the owner; brain files are edited only on his word.

## v0.4.214 (2026-09-19)

Three lane-filed defects, all verified first-hand before the edit; all in `upstream-merge-runbook.md`.

**1. The VERDICT ROW schema taught a field order practice had abandoned (filed by lane c78e78e0).** The schema line read `ts \t VERDICT \t run= \t sha= \t actor= \t issue= \t target= \t evidence=`. Census over the canonical `smoke-verdicts.log` (predicate: non-blank rows, tab-split exactly 8 fields; signature = the key at each of positions 3-8): 146 rows use `issue= sha= run= target= actor=`, 65 use the documented `run= sha= actor= issue= target=`, and the migration is temporal — rows 1-500 hold 60 of the 65 documented-order rows, rows 751+ hold 135 of the 146 majority-order rows. The line now states that field 2 carries the TOKEN and fields 3+ are `key=value` in ANY order. Impact was LOW (every consumer reads by key, nothing miscomputed), but the law was contradicted by the tree it describes — the same class as the mod.rs claim (v0.4.211) and defects A/B/D (v0.4.213).

**2. The sync sequence never reconciled the local `~/opencrabs` main worktree (filed by Triage lane 530c29ec).** Every sync force-pushes fork main, so a local `main` left behind stops being an ancestor of the new tip; `oc-ship-chain` LEG3 then runs its bare `git merge --ff-only $TIP` against that stale local main and reports **NON-FF** for a lane correctly based on the new `origin/main` — and its rc-5 text points that lane at a rebase it does not need. Measured live: two LEG3 NON-FF failures inside one minute (ledger `9345`/`9348`), both a stale local main. Step 8 now carries an explicit reconcile step with an ff-only command (never force). Latent at the time of the fix — local `main` and `origin/main` were both at `2dc302fc6`.

**3. Step 0's cherry test has false NEGATIVES (filed by Triage lane 530c29ec).** The `+` count of 0 proving "absorbed" is sound; the CONVERSE was unstated and false. Patch-id matching is blind to a change already present by another route, so landed work still reports `+`. Verified against `origin/main` @ `2dc302fc6`: 10 of 10 lane-scoped `+` markers on two lanes were content-present (`record_tap_binding`, `BindingOrigin::Callback`, `PREVALIDATE_TIMEOUT_SECS`, `neutralize_prose_media_html`, `format_mermaid_plan_error` and migration `20260912160000_session_bindings_last_origin.sql` all resolve in `origin/main`). A lane obeying step 0 literally rebases already-landed work — the over-replay class the section already warns about, reached from the opposite direction. Step 0 now requires a CONTENT leg before a `+` is treated as pending, and the `ABSORBED|PENDING` verb note states that the verb needs it too.

**LOC — mandatory metric (owner order 2026-09-19).** `git show HEAD:<f>` vs live file:

| File | Before | After | Δ |
|---|---|---|---|
| `upstream-merge-runbook.md` | 389 | 391 | +2 |
| **Total** | **389** | **391** | **+2** |

All three fixes are corrections to verified defects, so the +2 is accepted growth, not sediment. This is the second consecutive bump that adds rather than trims.

**What this bump did NOT do.** No `tools/` file touched. v0.4.213 stands unchanged. The four law files remain above the 500-line budget (`fleet-directives.md` 598, `editor.md` 512, `SKILL.md` 576, ops `AGENTS.md` 531) — this pass did not narrow that gap.

## v0.4.213 (2026-09-19)

**The verdict-token list was not a closed set — it contradicted three other law sites. Reconciled, and the `interrupt`/escalation contradiction closed.**

Five lanes filed this independently in one window (4b0990b7, 61161247, a5b34466, c10cd97b, d5863180); a6b34466's second message de-duplicated itself against 4b0990b7, so the finding is treated as ONE filing with supplements.

- **Defect A — the sanctioned field-2 token list omitted tokens that other law MANDATES.** `upstream-merge-runbook.md §Ledger hygiene laws` listed 8 tokens and omitted `FAIL` and the whole `UNPROVEN` family, while `SKILL.md §Hard rules` makes `FAIL` a formal verdict, `SKILL.md §Test ontology` mandates `UNPROVEN (presence-only)`, and `fleet-directives.md §F2` mandates `UNPROVEN (structural N/A)`. A lane whose honest verdict was one of these was stamped off-taxonomy *by the list itself*. This is the same defect shape as v0.4.211's `mod.rs` claim — a law sentence contradicted by the tree it describes. **Fix:** the list now carries all 12 tokens, and states that the mandated labels are not optional additions. The list describes the vocabulary; it does not forbid a mandated label.
- **Defect B — `interrupt: true` was still described as an escalation** in `fleet-directives.md §Cross-lane message delivery discipline`, contradicting the always-loaded ops `AGENTS.md` (which has said INERT since #373) and the 2026-09-19 03:34:30Z re-ruling. **Fix:** the bullet now states there is NO escalation — `turn-end` queues and drains at the next boundary, `interrupt` is a legacy alias, `now` fails the delivery.
- **Defect C — `Rule 5` required an "ack deadline" that does not exist** for ZERO-ACK task/harvest dispatches. **Fix:** escalation now triggers on BLOCKED/stalled work, with the ZERO-ACK reason stated inline.
- **Defect D — residual of the v0.4.211 fix.** `editor.md`'s trailing sentence *"Upstream CI strictly enforces these"* survived at the foot of the standards list, and its plural "these" still covered the `mod.rs` item two lines above it — the exact reading v0.4.211 removed. **Fix:** the sentence now reads as fork discipline. Grep across the skill corpus for `strictly enforces` returns only the CHANGELOG history afterwards.
- **Rulings issued (both were live ambiguities lanes were parked on):**
  1. **`CORRECTION` governs the RE-VERIFICATION row only — it does NOT displace the verdict on the ORIGINAL row.** A ceiling row keeps `UNPROVEN (structural N/A)` for its whole life; the later re-verification is a NEW row stamped `CORRECTION`. Both stand. (Filed by 4b0990b7, who correctly declined to re-label its #295 row rather than guess.)
  2. **`OWNER-EYE-CONFIRM` is off-taxonomy** — it drifted into field 2 from an `oc-ledger stamp note` convention (origin lane `2fbfb2f8`, 2026-09-12), not from this surface. The sanctioned form for that row shape is `PASS-OWNER-EYE`. (Provenance traced by a5b34466; two rows affected, one self-corrected by its author.)
- **Field misuse classified separately from list defects.** 5 rows carry a sha, session uuid, or branch name in field 2 instead of any token. That is lane error, not a taxonomy gap, and the law now says field 2 carries a token and nothing else.
- **A count was corrected in a shipped entry.** The v0.4.210 entry said `RE-VERIFY` was written by "12 lanes"; my own census measured **14 rows / 14 distinct lanes** (243 verdict rows, 31 unsanctioned, 10 distinct unsanctioned tokens). The v0.4.210 entry now carries the corrected figure and says it was corrected. Predicate, stated so it is re-runnable: field 1 parses as ISO-8601 AND exactly 8 tab fields AND field 2 non-empty.
- **LOC delta (mandatory on every law change):**

  | File | Before | After | Δ |
  |---|---|---|---|
  | `upstream-merge-runbook.md` | 389 | 389 | 0 |
  | `fleet-directives.md` | 598 | 598 | 0 |
  | `editor.md` | 512 | 512 | 0 |
  | **Total** | **1499** | **1499** | **0** |

  All three are net 0: every fix in this bump is an in-line rewrite inside an existing line, and the denser taxonomy line still fits one line. Stated because a zero delta is still a delta, and the metric is the check, not the reduction.
- **What this bump did NOT do.** No `tools/` touch (the battery receipt from 13:23:02Z still covers the tree). The four law files remain above the 500-line budget: `fleet-directives.md` 598, `editor.md` 512, `SKILL.md` 576, ops `AGENTS.md` 531.
- **Routed, not fixed here.** Triage lane `530c29ec` reported that the sync sequence has no step reconciling the `/root/opencrabs` main worktree after a force-push, so any lane shipping in that window hits a false `LEG3 NON-FF`. That is a runbook-procedure change with a lane-side companion already going to Toolsmith; it is queued as its own bump rather than folded into a taxonomy fix.

## v0.4.212 (2026-09-19)

**`toolsmith.md` carried two stale laws that steered lanes wrong — both corrected.**

- **Defect (filed by the TOOLSMITH lane, verified first-hand here).** Two sites contradicted the live rulings:
  1. **§Escalation to HQ** still described the PRE-re-ruling cadence — *"quiet DEFAULT, turn-end for boundary-bound, `interrupt=true` failsafe only"*. The 2026-09-19 03:34:30Z / 03:36:54Z re-ruling inverted both halves: `turn-end` IS the default, `quiet` is a deliberate choice, `now` is RETIRED and FAILS the delivery, and `interrupt: true` is a legacy alias — accepted but INERT. A lane following the file got the inverted default *and* a nonexistent escalation path.
  2. **§Tool-problem reports** forbade a working form — *"`oc-roster` does NOT resolve roles — its `--role` flag is actively rejected (rc 2)"*. Measured this turn: `oc-roster --role hq` → **rc 0**, and `cmp` against `oc-ledger roster --live --role hq` → **rc 0, byte-identical**. Only the BARE `--role` with no value answers rc 2. The file was steering lanes away from a supported delegation that `SKILL.md`'s own tool table already documents.
- **Fix.** Both sites state the current law. The canonical `oc-ledger roster --live --role <role>` form and the never-hardcode-a-UUID rule are retained. No other cadence text remains in the file (grep-verified).
- **LOC delta (mandatory on every law change):** `toolsmith.md` 157 → 157, **net 0** — both fixes are in-line rewrites at identical line count. Stated because a zero delta is still a delta.
- **What this bump did NOT do.** No `tools/` touch (the battery receipt from 13:23:02Z still covers the tree; no `tools/` file is newer). The four law files remain above the 500-line budget.

## v0.4.211 (2026-09-19)

**The `mod.rs` declarations-only standard is FORK discipline, not a gate — the enforcement claim was unsupported by upstream's own tree.**

- **Defect (filed same-day by lane 52058a75, verified first-hand here).** `fleet-directives.md §Upstream Coding & Testing Standards` standard 2 ended with *"Upstream CI strictly enforces this"*, and `editor.md`'s restatement of the same list implied the same. Measured against upstream's own tree: `git show adolfousier/main:src/channels/telegram/mod.rs` at tip `b6e200a119976f92bf0d3e5347f08b01daaecfb3` contains a top-level `pub(crate) async fn record_topic_created(` at line 47 of 94. Either their CI does not enforce it or their `main` is red — and the lane correctly did **not** poll upstream CI to settle which (§Upstream relations bars uninvited polls), so the law could not keep the claim. A lane reading it could treat a pre-existing `mod.rs` function as an in-scope gate obligation.
- **Fix.** The rule survives unchanged as **fork discipline**; the enforcement sentence is replaced by the counterexample and an explicit instruction not to cite it as a CI obligation when triaging pre-existing `mod.rs` functions. `editor.md`'s list item carries the pointer.
- **LOC delta (mandatory on every law change):** `fleet-directives.md` 598 → 598 (0), `editor.md` 512 → 512 (0) — both are single-line in-line rewrites, **net 0**. Stated because a zero delta is still a delta, and the metric is the check, not the reduction.

## v0.4.210 (2026-09-19)

**The local Rust toolchain is gone — the rustfmt-only exception is RETIRED in law — and the smoke-verdict taxonomy gets a token for post-rewrite re-verification.**

- **Stale-law defect, filed same-day by editor lane 1a63f103 (measured, not inferred).** `/usr/local/bin/rustfmt` now exits 1 `BLOCKED`; its own header reads *"the sanctioned fmt-only exception is RETIRED (2026-09-19). It exec'd /root/.rustup/toolchains/... and that tree is absent from this host"*, and both `/root/.rustup` and `/root/toolchain-disabled-20260828` are absent. Yet `editor.md §Box law` still sanctioned the wrapper and asserted *"a working rustup tree survives here (kept for the owner-approved rustfmt wrapper)"*, `SKILL.md §Shared environment facts` repeated the sanction, and `upstream-merge-runbook.md §Process` named *"rustfmt wrapper only"*. An editor following Phase 4 now hits a hard BLOCK mid-loop. All four sites state the truth instead: **no local Rust tool exists at all, fmt included — fmt is the soft-fail leg of `pr-checks.yml` only.** The Duty-4 P7 post-fmt scope audit went with its trigger (there is no local fmt pass left to audit), as did the "wrapper is NEWER than CI" drift mechanics; the surviving rule is *cosmetic diffs CI reports on already-green code are KEEP AS-IS; fix only what you introduced yourself*.

- **Verdict taxonomy ruling (filed by lane aff7ff41).** 14 rows across 14 distinct lanes wrote `RE-VERIFY` into `smoke-verdicts.log` field 2 during the run-35441550360 fan-out wave — a token that exists in zero skill files. (The figure was first reported as 12; an independent census on 2026-09-19 measured 14 rows / 14 distinct lanes, all timestamped that day.) Ruled rather than coined: **post-lineage-rewrite re-verification is a `CORRECTION`** (it already carries the `sha=`/`evidence=` semantics), now stated on the taxonomy line in `upstream-merge-runbook.md §Ledger hygiene laws`. A genuinely NEW token still needs the owner's word via the poll format.

- **LOC delta (mandatory on every law change — the v0.4.209 rule), `git show HEAD:<file>` vs the live file:**

  | File | Before | After | Δ |
  |---|---|---|---|
  | `editor.md` | 524 | 512 | −12 |
  | `SKILL.md` | 575 | 576 | +1 |
  | `upstream-merge-runbook.md` | 389 | 389 | 0 |
  | **Total** | **1488** | **1477** | **−11** |

  `SKILL.md` is the one file that grew: the retired-sanction replacement is one line longer than the sentence it replaced. Net across the three is −11.

- **What this bump did NOT do.** It did not touch `tools/` (the battery receipt from 13:07:41Z still covers the tree). It did not re-open the v0.4.209 sediment pass — that commit stands. And it did not bring the four law files under the 500-line budget: `fleet-directives.md` 598, `editor.md` 512, `SKILL.md` 576, ops `AGENTS.md` 520 are all still above it, and saying otherwise would be false.

## v0.4.209 (2026-09-19)

**Lens A/B sediment pass across the four law files, and the LOC metric becomes a MANDATORY part of every law change (owner order 2026-09-19: *"The lines of code check must be a part of every law change. It's one of the main metrics"*).**

- **The order, and why it is law rather than advice.** Large law files degrade context compaction, so the four files that every lane loads were audited by an 8-subagent matrix — Lens A (sediment / provenance / churn-drift) × Lens B (redundancy / cache / subsumed procedure) over `fleet-directives.md`, `editor.md`, `SKILL.md` and the ops brain `AGENTS.md`. 51 of 54 quoted findings were mechanically validated against disk truth before a single edit was applied. `fleet-directives.md §Upstream Coding & Testing Standards` now carries the rule: **every law/process edit ships an explicit before/after LOC delta table for each file touched**, law files stay under the 500-line budget, and a law change with no LOC delta is INCOMPLETE. A second, smaller rule landed beside it: an ad-hoc test or cleanup script must genuinely respect `--dry-run` (mutating actions stay strictly behind flags), and the `--dry-run` form is quoted verbatim from the tool's own `--help`, never hand-written.

- **The measured result — `wc -l`, pre-pass copy vs live file, one turn:**

  | File | Before | After | Δ |
  |---|---|---|---|
  | `fleet-directives.md` | 603 | 598 | −5 |
  | `editor.md` | 598 | 524 | −74 |
  | `SKILL.md` | 576 | 575 | −1 |
  | ops `AGENTS.md` | 543 | 520 | −23 |
  | **Total** | **2320** | **2217** | **−103** |

- **`editor.md` carried the bulk (−74), and almost all of it was DUPLICATION rather than detail.** Removed: the 36-line `Decision Rollcall` procedure (canonical in `fleet-directives.md`), the dead `CI Watcher Discipline & Throttling` section, the `Split-Gate Pipeline` design prose, the carrier-hotfix war story, the manual smoke-verdict append procedure (`oc-smoke` owns that append), and the redundant detached-execution / attribution restatements. The long-form local-fmt-drift derivation was cut to the rule it existed to teach — *foreign cosmetic drift is KEPT AS-IS; fix only what you introduced* — the three-receipt re-derivation that produced it is history, not procedure.

- **`fleet-directives.md` lost its duplicate surface stubs and restatements.** The Telegram-surface section was a pointer that restated nothing (canonical: `SKILL.md §Telegram surface law`), the zero-relay law duplicated the routing table directly above it, and the `Re-homed here from ops AGENTS.md/MEMORY.md per owner order 2026-09-02` provenance tail plus the migration history were sediment from a move that is long finished. **One concept, one home** — the pointer is the home, the copy is drift.

- **`SKILL.md` was nearly clean (−1) and lost only provenance.** A stale compiler re-enable pointer, git-commit sediment inside the `oc-harvest-census` register row (commit shas describing how the tool was wired are not how a reader uses it), a bookkeeping origin note, and a war-story parenthetical about the `git checkout` glob. Added on the `oc-lint-laws` row: the measured `--strict` limitation — 5 PHANTOM-FLAG findings that are all false positives on real working flags (recorded in v0.4.208), so no lane "fixes" them.

- **ops `AGENTS.md` shed forensic history and point-in-time telemetry.** 5.7 KB of SQLite/dpkg/binutils investigation collapsed to the rules it established (read in place via a `mode=ro` URI, never copy a DB; the CLI is the HOST read path only); the 4-leg smoke restatement and the lane-briefing bullet were duplicates of canon held elsewhere; and the cgroup paragraph lost the live readings it had accumulated (`high 1598`, `767.8 MiB current`, `08:5xZ`) while KEEPING the durable content — the 200 MB RSS limit and the cgroup read path. **A measurement that only describes the moment it was taken is not law**; the limit it justified is.

- **What the pass did NOT do.** No rule was weakened, no canonical definition moved, and no gate was narrowed — every cut removed a duplicate, a provenance tail, or a moment-in-time reading. The canon pointers were verified to resolve (`SKILL.md §Test ontology`, `upstream-merge-runbook.md §HARVEST LAW · NO-HOLD`, `fleet-directives.md §Cross-lane message delivery discipline`) before the text that pointed at them was removed.

## v0.4.208 (2026-09-19)

**Config joins Deep Core (owner order 2026-09-19, verbatim: "Config is also deep core").**

- **The gate's scope named five subsystems and config was not one of them.** `editor-upstream-pr.md §Deep Core Advance Heads-Up Gate` listed *runtime scheduler, compaction, provider routing/fallbacks, subagent orchestration, tool loop*, with paths `src/cron/`, `src/brain/agent/service/tool_loop.rs`, `src/brain/agent/context.rs`, `src/brain/provider/`, `src/brain/tools/subagent/`. Configuration — the `src/config/` subsystem and the `config.toml` / `keys.toml` write path — appeared in neither the prose scope nor the path list, so a config change read as **NOT** Deep Core. That is the wrong direction of error, and the same shape this section already fixed once: the former `src/agent/` / `src/scheduler/` list named two directories that do not exist in the tree (the `#317` shape).

- **Config is the higher-stakes instance of that error.** `config_manager` writes `config.toml` / `keys.toml`; a malformed write takes a daemon down and can leave no way back in — the live-home guard (`src/config/live_home_guard.rs`) exists for exactly that class. A change there reaching maintainer review with no advance heads-up is the case the gate is FOR, not an exception to it.

- **Both halves amended in one pass:** the prose scope now reads *"… subagent orchestration, tool execution loop, and **configuration** (loading, profile resolution, write guards, migrations)"*, and the path list gains **`src/config/`** with its principal files named (`sections.rs`, `profile.rs`, `secrets.rs`, `guard.rs`, `live_home_guard.rs`, `repair.rs`, `registry_client.rs`). The prose-scope-is-OPERATIVE rule is unchanged, so the added path can only widen the gate, never narrow it.

- **`src/config/` was verified to exist before it was written into law** (20 top-level `.rs` files, read live this turn). A path list naming a nonexistent directory is precisely the defect this section fixed one line above, so the new entry was checked against the tree rather than against memory.

## v0.4.207 (2026-09-19)

**Owner Push Freeze — the frozen/released set gets ONE machine-readable home, and a claimed release is ruled NOT a release.**

- **T3 (#291) is NOT released — ledger `n=8670` is an interpretation, not an owner action (HQ ruling 2026-09-19).** Row `n=8670` (lane `63d775f9`, 2026-09-19T01:41:34Z) read the owner's three-word message *"Overrule T3 release"* (2026-09-18 21:45:27Z, topic 42360) as READING (a) — "the freeze does not apply to T3, #291 released for harvest". The ruling: **the law text is authoritative, a ledger `note` is not.** A release is an OWNER action recorded in law, and Rule 2's bar is an *explicit* owner message naming the group exactly as T6 did (*"Telegram flow cluster T6 - release for harvesting"*); a lane's reading of an ambiguous message cannot meet that bar, so `n=8670` is an interpretation, not a release. The message genuinely parses two OPPOSITE ways — as an object it annuls the release, as an imperative it annuls the freeze — and the lane's own note admits the ambiguity. **Cost asymmetry fixes the standing state while it is open: a wrongly-frozen group costs a delayed harvest (recoverable); a wrongly-released group files an upstream PR for a group the owner said he wanted to review first (not recoverable).** Reinforcing it: T3 is the group the owner himself found defective on 2026-09-18, and its fix is still soaking under lane `2ed8adeb`. **T3 remains FROZEN** — no harvest of #291 or its 21-target set may be staged or filed, and a green census does not change this. The ambiguity is escalated to the owner as a one-tap (keep frozen / release); whoever holds his answer updates the block, the prose table and `disputed_not_released` in one commit.

- **The frozen/released set now has ONE home (the #358 shape).** A fenced `json` block in `fleet-directives.md §Owner Push Freeze` is the sole machine-readable record — `released: ["T6"]`, the 17 frozen T-groups, the 7 Tier-3 items, and `disputed_not_released: ["T3"]`. Tools read it from THERE, never from the prose table and never from a state-dir copy: a second copy is a second home for law data and would drift, which is exactly the contradiction this block exists to end. `law_version` is the `SKILL.md` version at which the block last CHANGED — not a per-bump field.

- **CORRECTION, same window — three claims the block's first draft asserted that are NOT yet true, now stated honestly:**
  1. **`tools/lib/oc_freeze` does not exist.** The first draft told tools to "extract it with `tools/lib/oc_freeze`" as though it were present; `ls` and a `grep -rn` over `tools/` both return nothing. `tools/**` is Toolsmith-owned, so the build sits in the Toolsmith lane's queue — the gap was reported to them by the #352 harvest lane on 2026-09-19, and HQ did not dispatch a duplicate report to the same owner. **Until it lands the block is read by humans and the freeze rests on this law text plus lane discipline.** Required behaviour when built: fail LOUD (`OWNER_PUSH_FREEZE_UNREADABLE`) on an absent or malformed block — never fall through to "nothing is frozen", because that direction silently releases all 18 groups.
  2. **Neither `oc-harvest-census` nor `oc-harvest-dispatch` has ANY freeze awareness** (verified by grep over both, 2026-09-19). So **a green `oc-harvest-census check <N>` is NOT evidence that a frozen group may be dispatched** — Rule 3's machinery leg is OPEN, and the census must not be read as a release gate.
  3. **`§Tool logging rule`'s closing gap-list was stale** — it still read *"gap list: swap-leg journal lines + marker write land with S2 wiring"*. That leg landed long ago (`oc-deploy/journal/swap-*.jsonl` carries `auto-swap` / `backup` / `guard` / `verify`); the sentence is replaced with a pointer to `s2-swap-journal-spec.md`, which owns the journal vocabulary.

- **`oc-lint-laws --strict` — 5 PHANTOM-FLAG findings measured as FALSE POSITIVES, and documented so no lane "fixes" them.** `flag_known`'s strict branch demands the flag BE the whole case arm (`^[[:space:]]*--flag)`), so it cannot see ALTERNATION arms (`--role|--role=*)` at `tools/oc-roster:67`; `--selftest|selftest)` at `tools/oc-deploy:3016`), INLINE tests (`[ "${1:-}" = "--bundle" ]` at `tools/oc-ledger:913`) or comments. Predicate, measured per finding: `strict_case_arm=0` while `literal_substring>=1`. All five flags are real and working — `oc-roster --role hq` rc=0 and `oc-deploy --selftest` rc=0 (283 pass / 0 fail) checked live; `--bundle` and `--issue` each carry passing selftest assertions (`tools/oc-ledger:1275`, `:1415`). Non-strict mode finds all five. Root fix dispatched to Toolsmith; the limitation is recorded on the tool's register row in `SKILL.md`.

- **CORRECTION — `editor.md §Phase 5` Failure Modes row 1 asserted an auto-rebase the chain does not perform (defect reported by editor `61161247`).** Row 1 read *"`rc=0` (Auto) / `rc=5` (Conflict) — **100% Automated by tool** on clean rebase: `oc-deploy`/`oc-ship-chain` auto-fetches `origin/main`, rebases topic commits, audits with `oc-rebase-safety audit`, and retries push in 3s"*, and Exit-5(a) described *"the automatic in-tool rebase encountered an actual semantic merge conflict"*. **Verified against the tools, not the prose:** `oc-ship-chain` LEG3 runs a bare `git merge --ff-only` and `die`s `rc 5` **unconditionally** on any non-FF — every `rebase` occurrence in that tool is a comment, the freeze guard, or the LEG4 REBASE-GATE branch, so LEG4 (and with it any auto-rebase) is never reached; the in-tool auto-rebase (v0.4.145) lives in **`oc-deploy`'s own push path** alone. `tools/RC-CONTRACT.md` already documented this correctly, so the defect was `editor.md` text only. **Corrected:** row 1 now states `rc=5` for ANY non-FF (clean *or* conflicted) with the LANE owning the rebase, pins the auto-rebase to `oc-deploy`, and points at the rc register; Exit-5(a) now says a clean and a conflicted non-FF are the SAME code from the chain's side and directs the reader to cause (c) for the auto-rebase. **The consequence the old text hid: a CLEAN non-FF still needs a lane-side rebase** — a lane waiting for an auto-rebase the chain never runs stalls instead of shipping.

## v0.4.206 (2026-09-19)

**Duty-6 cycle `20260919-cycle` — 11 lenses (10 catalog + the standing brain-scrub), 58 validated findings, master verdict `reviews/20260919-cycle/verdict.md` (15,798 B).** Law text landed in `2dce03eb` + `d3228cdb` + `97d839d0`; this entry closes the version batch.

- **Owner order — delivery mode: `now` RETIRED, `turn-end` is THE default (owner order 2026-09-19 03:34:30Z / 03:36:54Z).** *"the factories should use end-turn delivery"* · *"session delivery mode `now` needs to retire — `turn-end` delivery to become the new default. for an idle session `turn-end` = `now`. for a busy session `now` will be a noop"*. `fleet-directives.md §Cross-lane message delivery discipline` MODE SEMANTICS rewritten: `turn-end` is the single default for ALL lane traffic (status receipts, verdict relays, ACKs, corrections to in-flight work, and urgent wake-ups alike — the mode-choice decision itself is what produced the 1267-`now`-vs-7-deferred skew this section was written about); `quiet` is retained but is now a deliberate choice, never the fall-through; `now` is RETIRED as a mode name and must not be preferred where the mode is still available. Code-side retirement is fork issue [#373](https://github.com/leshchenko1979/opencrabs/issues/373).

- **Owner order — a design-gated lane is NOT a stalled lane (owner order 2026-09-19 03:49:33Z).** *"if a lane is design-gated, don't nudge it anymore, just mark it in the ledger"*. Codified in `triage.md §Duty T5` (the stalled-claim nudge exception) and `fleet-directives.md §Cross-lane message delivery discipline`: a lane parked on the OWNER design gate MUST NOT be nudged by any patrol — the park is stamped in the ledger and the patrol continues past it.

- **Tier-C pull-back — 7 cross-lane laws return to `fleet-directives.md` (2026-09-19).** The 2026-09-18 split demoted sections whose law in fact binds every lane; citation is not scope. Returned as `[LANE]` sections: **Tool logging rule** · **CI-wait discipline & actor attribution** · **Swap-head signature for rebase/synthesis/merge-derived binaries** · **Decision Rollcall** · **Inherited-claim three-pillar verification** · **Topic domain alignment & rename authority** · **HQ does not execute lane work — refuse and reroute**. Cross-file references left stale by the move were repointed (`editor.md`, `triage.md`, `s2-swap-journal-spec.md`). Measured shape, `t9_measure.py` over the live tree: `fleet-directives.md` **130,501 B / 61 sections → 85,896 B / 43 sections** (−44,605 B, −34.18%), **35** `[LANE]` headings; per-turn set (`SKILL.md` + `fleet-directives.md` + `hq.md`) **158,280 B**.

- **Structural fixes carried by the cycle:** F17 off-by-one; F18 `editor.md` 623→618 lines; F19 `triage.md` Duty T7 trimmed to trigger/coverage/stamp; F20 `toolsmith.md:80` Explore & DRY gate; F22 night-shift pointers; F7 `review-lenses.md:284` standing lens. Plus 15 mechanical law patches across `hq.md` / `SKILL.md` / `toolsmith.md` / `fleet-directives.md` / `s2-swap-journal-spec.md` / `README.md` / `review-lenses.md` / `editor-upstream-pr.md`.

- **Duty-6 corpus hygiene:** 9 legacy report files `git mv`'d into `reviews/20260906-cycle/reports/` (F49); `reviews/20260918-cycle/state.json` created and marked `INCOMPLETE — UNRECEIPTED` (F46–F48); `fleet-directives.md` tail rewritten (F52); 1.8 MB of raw reviewer transcripts dropped from the corpus (`d0638e6b`).

- **Host-dependency defects surfaced by the cycle's stamp leg, filed and fixed by Toolsmith:** [#371](https://github.com/leshchenko1979/opencrabs/issues/371) — six `tools/` call sites shelled out to an absent `sqlite3` CLI, so `oc-ledger roster --live` died rc 3 against a readable DB and `oc-health` skipped a check with no trace (`daee2a03`, one shared `tools/lib/oc_sqlite` reader); [#376](https://github.com/leshchenko1979/opencrabs/issues/376) — `oc-smoke-evidence`'s marker leg depended on an absent `strings(1)`, reading a present marker as MISSING (`627825cc`, raw-byte scan). Battery: 190/7 → 196/1 → **197 PASS / 0 FAIL**, which unblocked this sync.

- **CORRECTION, same window — the `now`-retirement clause was born stale, and the cycle's own brief propagated it.** The clause as first committed read *"Code-side retirement is fork issue #373; until it lands, a lane that still has the mode available MUST NOT prefer it over `turn-end`"* — but #373 had already landed (`9dffa5632`) and been DEPLOYED (swapped `6db34e1fd`, run `35423208985`) before that commit. The clause inverted the fact: the mode is not available-but-discouraged, it is **removed-and-erroring** (`notify_policy.rs` returns `Err` for `Some("now")`; the tool schema's enum is exactly `[turn-end, quiet]`). Worse, the duty-6 fanout brief fired 05:49:39Z (ledger `n=8846`, sent=27) copied the stale line to every active lane 15–19 min after the swap. Found by editor lane `6cd8175f` (cron-session-isolation), verified first-hand against the commit shas, `oc-deploy status --json`, the source and the schema before editing. Law text now states the landed fact; the "until X lands" clause carries the instance as its THIRD case, with the compounding lesson — **a stale law does not stay in the law file, it is copied into every brief generated from it, so one un-rechecked clause propagates fleet-wide in a single wave.** This is the v0.4.166 + v0.4.168 class, both of which the same section already ruled on.

## v0.4.205 (2026-09-18)

- **Owner Push Freeze — the soak groups are held from upstream harvest; T6 released (owner order 2026-09-18 17:33Z, release 18:01Z)**: *"freeze all these groups from pushing - I want to review them first and will release them later"*, then *"Telegram flow cluster T6 - release for harvesting"*. New canonical section `fleet-directives.md §Owner Push Freeze — soaking groups held from upstream harvest` [LANE]. The frozen set is the group list the owner was reading in the delivered live-test plan (`/tmp/live-test-plan-2026-09-18.md`, board topic 30220, `msg=67358`): **18 T-groups (T1–T18) + 7 Tier-3 items**, of which **17 T-groups and all 7 Tier-3 items are frozen** and **T6 (Telegram flow cluster) is released**. Counts derived in python from the plan file, never by eye.
  - **Release is an OWNER action, never a lane decision** — a group leaves the freeze only on an explicit owner message naming it, exactly as T6 did. Soak maturity elapsing, a green census, a lane's own confidence, or an idle editor release nothing. The released set currently holds exactly one member.
  - **The freeze binds the machinery, not just the prose**: Triage's 4h harvest patrol (`oc-harvest-dispatch-4h`, job id `73158e43-3b04-4464-bf82-8d9065a191bb`) must not dispatch a frozen group; `oc-harvest-census` / `oc-harvest-dispatch` must read a frozen group as NOT harvest-eligible; a holder of frozen work stops short of Phase 7 (upstream PR filing).
  - **Distinguished from the existing carrier FREEZE** (`§Remotes & sync` guard 2 — mechanical: no sync while a carrier chain sits between dispatch and swap). Same word, different concept; write **owner push freeze (harvest hold)** when you mean this one. **Scope boundary:** the freeze holds HARVEST, not development — fixes, commits, ships and smokes inside fork `main` continue normally; only the upstream push of a frozen group is withheld.
- **Early Claim — claim at domain recognition, not at dispatch (owner order 2026-09-18 17:38Z)**: *"I think the claim shoud happen sooner - when the lane decides that the issue is within it's area of expertise. then the double dispatch problem may be solved."* New canonical section `fleet-directives.md §Early Claim — claim at domain recognition, not at dispatch` [LANE], placed adjacent to the Designated Domain Affinity law it depends on.
  - **The claim is the LOCK, and it is taken earlier than the dispatch**: `oc-ledger claim <issue>` the moment a lane judges the issue inside its designated domain, before work starts and whether or not a dispatch wire has arrived. An OPEN claim-ref means no other lane starts it, dispatches it, or helps. This is what makes `DISPATCHABLE = unclaimed AND vetted AND NOT landed` honest rather than aspirational — double dispatch happens because routing decides before any lane holds the issue.
  - **An early claim carries an early release duty**: release with `oc-ledger unclaim`; a `note` row closes nothing and leaves the issue reading CLAIMED, so a stale early claim becomes a hold on the work.
  - **Honest limit recorded, in the owner's own words**: *"as for releasing the lanes - we have lots of them. the problem is throughput and human gate. but there is currently no way to make the human work faster. today was a one-time when I was busy with other stuff."* The early claim removes duplicate WORK; it does nothing for owner-gate THROUGHPUT, which is the real ceiling on the harvest cadence. Lanes must never present it as a fix for gate latency, and the owner's 2026-09-18 gate delay is recorded as exceptional — **not a new normal**, and not licence to relax, bypass, or self-approve anything the gate reserves.
- **Thematic index updated** for both new sections (harvest group carries *owner push freeze / harvest hold*; lanes group carries *early claim at domain recognition*), so the flat-index readers of `fleet-directives.md` reach them without a full read.

## v0.4.204 (2026-09-18)

- **Affinity law: one canonical name, and the tag that made it invisible (HQ 2026-09-18; drift reported by editor lane 40427d4f, verified first-hand)**: the 2026-09-17 owner order was codified under THREE names — the `fleet-directives.md` section heading, `triage.md:120` "Designated Domain Affinity Mandate", and `CHANGELOG.md:78` a variant missing "Topic" — and tagged `[DISPATCH]`, a tag neither defined nor indexed anywhere in the skill (grep for it: 1 hit, no registry entry). Because only `[LANE]` (v0.4.95) is the must-read-at-reload marker, a lane told to reload "[LANE] sections in full" silently skipped the law; the reporter found it only via a separate grep. Canonical name is now the `fleet-directives.md` form, and the tag is `[LANE]`.
- **editor.md exit-code contract drift after #336 (HQ 2026-09-18; reported by editor lane 4b4463d5, verified against the tool)**: the role file disagreed with the tool it documents in the exact list a lane reads to choose its recovery action. **Exit 8 (SHIP-WAIT-TIMEOUT) was absent entirely** — a lane's trained reflex from the Exit 4/6 rows ("re-run the chain") is the double-dispatch the new arm exists to prevent. **Exit 5 widened** from "NON-FF / MERGE CONFLICT" to three causes (NON-FF, TIP-MOVED, REBASE-GATE; tool text `oc-ship-chain:828-829`). **LEG4/LEG5 ship wait default** recorded as 2700 s (`OC_SHIPCHAIN_SHIP_WAIT`, `oc-ship-chain:192`), raised from 900 s after 11 of 37 carrier successes exceeded 900 s (10 most recent: 942-1344 s, median 1062 s) — under the old default every chain reaching LEG4 mislabelled a still-building run as INFRA rc 6.
- **Tool defects filed and claimed this cycle**: #340 (`oc-ledger` header KINDS block lists 16 of the live 22 kinds — missing close/done/unclaim/reject/lesson/proposal) and #342 (`oc-issue-dispatch` affinity model: no "tools" domain, never consults the structured role), both claimed by Toolsmith; #343 (`oc-harvest-sweep` certifies CLEAN without comparing the squashed result against the union of source-commit trees) filed from editor lane 2fbfb2f8's #233 squash-drop finding and claimed by Toolsmith.

- **Dispatch Eligibility — the 4-bucket predicate gains its LANDED term (HQ ruling 2026-09-18; new canonical section `fleet-directives.md §Dispatch Eligibility — the 4-bucket predicate`; `triage.md` Duty T4 + T5 point to it)**: the predicate was quoted in two files but had **no canonical home**, and it was missing a term. It is now `DISPATCHABLE = unclaimed AND vetted AND NOT landed`.
  - **`landed` is `LANDED_KINDS` (`close`/`done`), NEVER `CLOSING_KINDS`** — the module's own docstring records why: `CLOSING_KINDS` reaches 228 issues, 125 only via the three NON-landing kinds (`confirm`/`unclaim`/`reject`), 48 of them reachable by `unclaim` alone; a released-but-unbuilt issue is legitimately re-dispatchable, so a `CLOSING_KINDS`-based filter **starves real work**. Either arm marks landed: a `done`/`close` ledger row addressing the issue, or a commit referencing it on fork `main`. Tool side: #337 (Toolsmith).
  - **The two sets are now disjoint by construction:** the closure law deliberately keeps DONE work OPEN until its own upstream PR files, so without the term every landed-but-unharvested issue read as dispatchable backlog. Landed-and-unharvested ⇒ **harvest queue, never an editor lane** (it waits on a PR, not on code).
  - **Live instance:** one T5 sweep (n=8331–8341) wired 8 issues, **5 of them OPEN *and* carrying a `done` row** — #330 (n=8317), #324 (n=8192), #302 (n=8267), #299 (n=8325), #297 (n=8266); GitHub state OPEN for all five, verified same-turn. #302's `done` row is Triage's own and reads *"Issue STAYS OPEN under the harvest-gated closure law until its own upstream PR files"* — wired anyway. Second surface, same cause: the `oc-harvest-dispatch-4h` cron (session c32f43ee) wired #302 from `done` + zero claims. Reported independently by lanes aaa8d8ae and 6630dc9a; the second lane's proposed `CLOSING_KINDS` predicate was **rejected** on the tool's own recorded measurement.
- **Deep Core Advance Heads-Up Gate — stale path list + the missing executor (HQ ruling 2026-09-18; `fleet-directives.md §Deep Core Advance Heads-Up Gate`, `editor-upstream-pr.md` Phase 7)**: two defects in one gate.
  - **Path list was wrong:** it named `src/agent/` and `src/scheduler/` — **neither exists** (`find src -type d -name 'scheduler*'` → empty). Real sites: runtime scheduler `src/cron/`, tool execution loop `src/brain/agent/service/tool_loop.rs`, compaction `src/brain/agent/context.rs`, provider routing `src/brain/provider/`, subagents `src/brain/tools/subagent/`. The **prose scope is now declared OPERATIVE** and the path list a reading aid, so a missing path can never again narrow the gate — the #317 shape (a cron-runtime-scheduler behavior shift read as NOT Deep Core).
  - **The obligation had no executor on the filing side:** the gate orders a 1-liner to the OC Dev group chat, while SKILL.md §Telegram surface law forbids editors from invoking ANY telegram send tool. Both bound the same actor. Ruling: **HQ posts it on the filing lane's behalf** — the filing editor sends the 1-liner text to HQ (`session_notify`, `delivery.mode="turn-end"`) in the turn it stages the PR, and has discharged the gate. No editor carve-out; this is the existing lifecycle assignment (SKILL.md §Upstream relations item 5 makes Maintainer Interaction HQ's area).

## v0.4.203 (2026-09-18)

- **Stale cron-name drift corrected (HQ 2026-09-18; drift reported by Triage, verified first-hand against the live DB)**: the law named `harvest-watch-4h` — a job that does not exist. Live read: `cron_jobs` holds 34 rows, **0** matching that name; the live job is `oc-harvest-dispatch-4h` (`73158e43-3b04-4464-bf82-8d9065a191bb`). Retargeted all **five** refs across three files (`fleet-directives.md` ×3, `triage.md`, `toolsmith.md`), and the primary definition site (`fleet-directives.md` §HARVEST LAW) now carries the **job ID** alongside the name, per the cron-namespacing law — names are mutable, IDs survive renames.
  - **Impact:** `tools/oc-health` queries crons by NAME, so the stale name made its liveness check a **silent no-op** for the harvest patrol — it could never report the patrol disabled. Same-class fix dispatched to Toolsmith (`tools/oc-health:772` + `HEALTH-CLASSES.md:91`).
- **Tool defect filed: leshchenko1979/opencrabs#340** — `oc-ledger`'s header KINDS block carries 16 of the live 22 kinds (missing `close`, `done`, `unclaim`, `reject`, `lesson`, `proposal`), so the vocabulary a lane reads in the file is a strict subset of what the code accepts. Toolsmith-owned (`tools/**`). Cross-referenced from the v0.4.202 §Claim Release law, which had recorded the defect as filed.

## v0.4.202 (2026-09-18)

- **Out-of-Feature-Set Issues — Dispatchable, Ceiling Labeled (HQ ruling 2026-09-18; `fleet-directives.md §Out-of-Feature-Set Issues — Dispatchable, Ceiling Labeled`, `triage.md §Duty T5 wire envelope`)**: An issue whose deliverable lies outside the carrier feature set IS dispatchable — the carrier set gates the **binary**, never the **codebase**, and the CI gate compiles `--all-features` (clippy + test steps of `pr-checks.yml`), so the code is verifiable work. The defect was an **unlabeled smoke ceiling**: leg 4 is `structural N/A` (legal under the 4-leg rubric), the verdict MUST read **`UNPROVEN (structural N/A)`** and is **never GREEN**, and the harvest stays **blocked** on the carrier set (owner ruling 2026-09-18: the set stays as-is, so the blocker is a STANDING CONSTRAINT, not a pending decision) while the lane parks and RELEASES.
  - **Churn cure (Triage-owned, no new tooling):** the wire carries `SMOKE CEILING: UNPROVEN (structural N/A) — <feature> absent from carrier set`, and the issue is linked natively `--add-blocked-by 338`.
  - **Carrier set is FROZEN — owner ruling 2026-09-18 ("Leave the carrier set as-is")**: the widening question this ruling originally left open is ANSWERED. The ceiling is **permanent and intentional**, not a pending decision; the harvest blocker is a STANDING CONSTRAINT and no lane ever chases a widening request or re-raises it. Decision record: leshchenko1979/opencrabs#338; the blocker anchor for wires is #338. Its closure is Triage's under `triage.md §Autonomous closure` (c) owner-confirmed-withdrawn.
  - **Adds no new classification bucket** — `DISPATCHABLE = unclaimed AND vetted` (the 4-bucket law) already covered the case.
  - Origin: #319 wired 3× across two lanes with zero claims at the time of the read (ledger n=8161, n=8234, n=8261); the 4th wire landed a claim (n=8274). Carrier set verified live via `tools/oc-carrier-features` → `telegram,code-graph,browser`.

- **Claim Release & Superseded Plans — mechanisms exist, discoverability fixed (HQ ruling 2026-09-18; `fleet-directives.md §Claim Release & Superseded Plans — the mechanisms exist; use them`)**: Both process gaps reported from the #299 duplicate-dispatch incident (lane 329bf3a3, 2026-09-18) were investigated against live tooling; NEITHER is a missing mechanism.
  - **C1 — releasing a claim is a KIND, not a note.** `unclaim` is one of the five `CLOSING_KINDS` in `tools/lib/oc_claims.py` (`close`/`confirm`/`reject`/`done`/`unclaim`). A claim on `#N` closes on the claimant's own closing row referencing `#N`, OR on a row ADDRESSED to `#N` (its `what` begins with the reference). A `note` closes nothing, so `claim-ref <uuid> --open` keeps returning the released issue. `sweep-closed-claims` is the backstop but fires only for CLOSED issues — it cannot cover the #299 shape (OPEN until its upstream PR files). **Live:** claim n=8041, release written as `note` n=8324 → `--open` still answered `299`; HQ stamped the addressed `unclaim` n=8326 → the same read answers CLOSED. Tool-side doc defect filed (Toolsmith): the `oc-ledger` header KINDS list omits the four D-2 closing kinds plus `lesson`/`proposal`.
  - **C2 — a superseded approved plan is retired LANE-SIDE.** Record the supersession in the ledger and mark the plan's tasks `skip` with the reason (the plan archives on its last task); `plan discard` stays USER-ONLY. Never idle on the owner for a settled question; never leave a 0/N approved plan live as if pending. Live: lane 329bf3a3's approved plan (0/11) superseded by lane 9fa7c71a's ship `5003c295` (#299).

## v0.4.201 (2026-09-18)

- **Fork-only base-fault closure predicate (HQ ruling 2026-09-18; `triage.md §Autonomous closure — limited disposal authority`)**: Codified the mechanical closure predicate for fixes whose reconcile target may itself be fork-only. The operative question is **whether the fix's SUBJECT exists upstream** (`git grep -c "<S>" adolfousier/main`), not whether its target FILES do — the files test is exactly what made #253 look standalone.
  - Subject **present** upstream → standalone `fix/*`, zero soak (HARVEST LAW), closes after **its own** upstream PR files.
  - Subject **absent** upstream → the fix is a **CHILD** of the fork-only parent: linked natively, barred from standalone harvest by the Native Sub-Issue Pre-flight Gate (#188 refusal), stays **OPEN** until the PARENT's upstream PR files, then closes with it.
  - **Corollary (both branches): landing is never the close trigger** — the trigger is the upstream PR filing.
  - Clarifies the harvest-gated closure law; adds **no** fourth autonomous-close class. Receipts: #253 **reopened** (child of unharvested #246; `FlowEvent` fork-only — `git grep -c FlowEvent adolfousier/main -- src/` empty), #324 **reopen stands** (child of fork-only #286).

## v0.4.200 (2026-09-17)

- **Atomic Subsystem Bundling & Fix Squashing Law (Owner Order 2026-09-17)**: Upstream PR branches must squash follow-up bugfixes, clippy cleanups, formatting touches, and dependent child issue commits directly into the coherent parent feature commit before CI gating and filing upstream (`git reset --soft` / `git commit --amend` to consolidate into one clean commit). Maintainer Adolfo squashes multi-commit PRs into a single commit on upstream `main` anyway; shipping clean, all-in-one atomic commits eliminates upstream review noise and intermediate cherry-pick breakage.
- **Sync Template CODE.md**: Synchronized `src/docs/reference/templates/CODE.md` with universal coding and testing standards.

## v0.4.199 (2026-09-17)

### Automatic Claim Closure on Smoke PASS (oc-smoke -> oc-ledger done)
- **Automatic Ledger Closure on Smoke PASS (Owner Order 2026-09-17, Toolsmith commit 2dedf9e1, `fleet-directives.md`, `editor.md`, `SKILL.md`, `tools/RC-CONTRACT.md`)**:
  - Codified the automatic ledger closure mechanism in `tools/oc-smoke`: upon recording a verdict of `PASS` (lineage, identity, CI gate, and behavioral execution verified), `oc-smoke` automatically executes `oc-ledger stamp done "smoke PASS verified for issue #<issue>"` (unless suppressed via `--no-ledger`).
  - Mechanically closes the worker's in-flight claim in `workers-ledger.json`, eliminating claim drift and immediately unblocking `oc-harvest-census` and Triage intake without requiring a manual trailing stamp from the editor lane.

## v0.4.198 (2026-09-17)

### Upstream Harvest Quality Gates, Narrative Verification & Cross-Boundary Tests
- **Upstream PR Harvest Baseline & Narrative Verification (Owner Order 2026-09-17, findings from PR #1615 review, `fleet-directives.md`, `editor-upstream-pr.md`, `triage.md`)**:
  - Mandated that when staging a fork bugfix or feature for upstream PR harvest (`adolfousier/opencrabs`), the staging lane MUST verify against live upstream `main` (`git diff origin/main...adolfousier/main` or inspecting the live upstream code path) whether upstream already resolved the underlying issue or changed the code path.
  - If already addressed or clean in upstream `main`, the PR narrative must be framed accurately as a clean helper extraction, refactoring, or hardening improvement rather than asserting an upstream regression or non-existent bug.
- **Cross-Boundary Unit Test Integrity Requirement (Owner Order 2026-09-17, `fleet-directives.md`, `editor-upstream-pr.md`)**:
  - Codified standard #8 under Upstream Coding & Testing Standards: Unit tests asserting file paths, contracts, or serialized data formats in upstream PRs must test real cross-boundary interaction (e.g. writing through a real file writer and reading back via the target reader in a `tempfile` directory) rather than asserting helper equality against its own internal delegate function.
  - Strictly prohibited tautological unit tests where a function merely tests its own internal implementation helper.
- **Native Sub-Issue / Child Harvest Pre-Flight Gate (Issue #188 unharvested parent refusal, `fleet-directives.md`, `editor-upstream-pr.md`, `triage.md`)**:
  - Reinforced that a child issue, cleanup, or derivative task (such as deleting a script that exists only on fork or referencing unmerged documentation/subsystems) must NEVER be harvested in isolation from its parent subsystem.
  - If the parent subsystem is unharvested or unmerged upstream, child work is strictly blocked from harvest staging until the parent lands upstream.

## v0.4.197 (2026-09-17)

### Deep Core Advance Heads-Up Gate
- **Deep Core Advance Heads-Up Gate (Maintainer Alignment, Owner Order 2026-09-17, `fleet-directives.md`, `editor-upstream-pr.md`, `SKILL.md`)**:
  - Codified the maintainer coordination protocol between Alexey (`@leshchenko1979`) and Adolfo (`@adolfodev`).
  - **Scope Distinction**:
    - **Deep Core**: Runtime scheduler, context compaction algorithms, provider routing/fallbacks, subagent orchestration, and tool execution loop (`src/brain/`, `src/agent/`, `src/scheduler/`).
    - **Surface Integrations**: Telegram channel handler, rich cards, MTProto/MCP bridge (`src/channels/telegram/`).
  - **The Protocol**: For any architectural change, behavior shift, or non-trivial fix touching **Deep Core**, post a concise technical 1-liner heads-up to either the **`OC Dev`** Telegram group chat (`-1003627148483` / `3627148483`) or the **`Opencrabs Dev Factory`** group chat (tagging `@adolfodev`) before or simultaneously with opening the upstream PR:
    `Core heads-up: <observed symptom/issue> → proposed fix in <subsystem> (PR #<N>)`
  - **Surface Autonomy**: Surface integrations (Telegram channel handler, cards, formatting) remain under autonomous maintainer authority; they ship directly to upstream PRs with verified 4-leg smoke receipts without requiring advance group chat discussion.

## v0.4.196 (2026-09-17)

### Context-Manifest Curation & Section 10 Compaction Preservation
- **Section 10 Compaction Manifest Curation (`SKILL.md`, `fleet-directives.md`, `editor.md`, `hq.md`, `triage.md`, `toolsmith.md`)**:
  - Codified the context-manifest curation law (Section 10 of compaction prompt) across all role files.
  - Mandated that when context compaction occurs, the compactor MUST explicitly retain `opencrabs-dev`, `opencrabs-dev/fleet-directives.md`, and the active role file (`editor.md`, `hq.md`, `triage.md`, or `toolsmith.md`) in `active_skills`, and discard only non-active role files.
  - Mandated pre-activation retention for core operational tools (`session_notify`, `session_search`, `bash`, `read_file`, `telegram_send`).
  - Backed by empirical evidence from 778 production compactions showing >93% retention when guided (and 0% contradictory aux retention when root discarded), eliminating the need for binary runtime modification (#283 closed).

## v0.4.195 (2026-09-17)

### Designated Domain Affinity & Topic Context Focus Law
- **Designated Domain Affinity & Topic Context Focus Law (Owner Order 2026-09-17, `fleet-directives.md`, `triage.md`, `tools/oc-issue-dispatch`)**:
  - Mandated that automated issue triage and patrol dispatches MUST route strictly to idle editor lanes whose designated feature or topic domain matches the issue domain (e.g. Telegram/UI, Mermaid/Diagrams, DB/Persistence, Bash/Subshell, Cron/Scheduler, Memory/Search).
  - Prohibited random or arbitrary fallbacks that mix topic history for the human operator and waste existing in-context focus.
  - Specialized feature lanes receive a severe negative affinity penalty (-50) and refuse mismatched fallbacks unless explicitly overridden via `--force`.

## v0.4.194 (2026-09-17)

### Upstream Merge Runbook Step 0 & Step 7 Fixes
- **Freeze & Roster Gate Invariant (`upstream-merge-runbook.md §Process Step 0`)**: Replaced unsatisfiable `0 ACTIVE` session criterion with the true operational invariants: carrier deploy chain is idle (`oc-deploy status`, no `SHIP-LOCK`), fork-main push freeze is active, and pre-sync rollback SHA is recorded in the ledger. Active editor lanes continue in their worktrees while fork-main merges are held until cutover.
- **Semantic Cherry Check Formula (`upstream-merge-runbook.md §Process Step 7`)**: Fixed Step 7 cherry-marker check formula to inspect the lane's specific commits above its base (`git log --oneline <old-base>..<lane-branch>`) before running `git cherry`, preventing aggregate false positives caused by common ancestor patch-id divergence after multi-commit conflict resolutions.

## v0.4.193 (2026-09-17)

### Duty 4+6 Review Cycle 20260916-c20 Master Codification
- **Changelog Ordering & Direction SSOT**: Reconciled all documentation (`README.md`, `SKILL.md`, `hq.md`) to reflect the true newest-first prepended convention and updated sync policy references to the REBASE sync model.
- **Portability & Path Sanitization**: Replaced hardcoded `/root/` path fallbacks with `${OC_DEV_STATE:-$HOME/.opencrabs/profiles/ops/opencrabs-dev}` and dynamic `$HOME` paths across 16 CLI tools (`oc-attrib`, `oc-commit`, `oc-deploy`, `oc-drift-check`, `oc-health`, `oc-ledger`, `oc-order-validate`, `oc-ping-proof`, `oc-prchecks`, `oc-seal-state`, `oc-shadow-rotate`, `oc-ship-audit`, `oc-ship-chain`, `oc-smoke`, `oc-smoke-evidence`, `oc-tg-audit`).
- **Battery Test Parallel Optimization**: Defaulted `tools/tests/run.sh` to parallel chunk execution (`JOBS=$(nproc 2>/dev/null || echo 4)`), cutting suite execution time.
- **Smoke Schema Standardization**: Standardized `oc-smoke` verdict rows to use canonical keyed schema tokens (`issue=`, `sha=`, `run=`, `target=`, `actor=`, `evidence=`) matching `RC-CONTRACT.md`.
- **Branch Rollback on Failure**: Added cleanup rollback to `oc-start` to remove orphaned branches when worktree creation fails.
- **State Root Hygiene**: Purged dead-PID fanout locks and checkpoint files in `opencrabs-dev/` and ran git repository garbage collection.

## v0.4.192 (2026-09-16) — Graph-Wide 24h Feature Soak Anchor Law

- **Graph-Wide 24h Feature Soak Anchor Law (Owner Order 2026-09-16, `fleet-directives.md`, `editor-upstream-pr.md`, `triage.md`, `tools/oc-harvest-dispatch`):**
  - Codified that the 24-hour maturation soak clock for any feature bundle or subsystem is anchored strictly to the **latest live deployment timestamp (`deployed.ts`) among ALL related nodes in its dependency graph** (the issue itself, its parent feature, all child sub-issues linked via `--parent`, and all blocker/blocked dependencies linked via `--add-blocked-by`).
  - When evaluating harvest eligibility, if any linked child fix or blocker dependency has been swapped more recently than the parent feature, the 24h timer for harvesting the subsystem/bundle resets to the swap timestamp of that youngest change.
  - Updated `tools/oc-harvest-dispatch` to inspect relationship graph hierarchy (`subIssues`, `blockedBy`, `parent`) and enforce `HELD_DEPENDENT_SOAK` if any linked node is <24h post-swap.

## v0.4.191 (2026-09-16) — Continuous Issue Relationship Linking Mandate

- **Continuous Issue Relationship Linking Across Lifecycle (Owner Order 2026-09-16, `SKILL.md`, `fleet-directives.md`, `editor.md`, `triage.md`):**
  - Expanded the native issue linking mandate from harvest/creation to the entire issue lifecycle: whenever parent subsystem relationships, blocker dependencies, or child sub-issues are established, split, or discovered at ANY point in the lifecycle (issue creation, triage intake sweeps, in-flight editor implementation, task decomposition, or upstream PR staging), the lane identifying it MUST establish native links in the same turn via `gh issue edit <issue> --parent <parent-issue>` and/or `gh issue edit <issue> --add-blocked-by <blocker-issue>`.
  - Codified into `SKILL.md §Issue-first`, `editor.md §Phase 1 step 2`, `triage.md §Duty T5 step 5`, and `fleet-directives.md §Upstream-merge cadence`.

## v0.4.190 (2026-09-16) — GitHub Native Harvest Protection Mandates

- **Native Sub-Issues Mandate (Owner Order 2026-09-16, `fleet-directives.md` & `triage.md`):**
  - Mandated that any `fix/*` or derivative work that modifies, repairs, or extends an unharvested fork subsystem (or any fork-only feature) must be linked to the parent subsystem feature issue via `gh issue edit <issue> --parent <parent-issue>`.
  - In isolation, fixes to unreleased/fork-only subsystems are strictly forbidden from harvest: child issues cannot harvest unless the parent subsystem is already recorded as merged upstream.
- **Native Issue Dependencies Mandate (Owner Order 2026-09-16, `fleet-directives.md` & `triage.md`):**
  - Mandated that any candidate issue blocked by an in-flight fork feature or prerequisite upstream PR must declare it via `gh issue edit <issue> --add-blocked-by <blocker-issue>`.
  - Mechanical vet gate (`tools/oc-harvest-dispatch vet`) rejects any candidate with open/unharvested blockers as `HELD_BLOCKED_BY_DEPENDENCY`.
- **Staged Upstream Draft PR Mandate (Owner Order 2026-09-16, `fleet-directives.md` & `editor-upstream-pr.md`):**
  - Mandated that when an upstream PR depends on another in-flight upstream PR or is part of a multi-part staged wave, it MUST be filed with `gh pr create --draft` so upstream maintainers cannot merge out of order before prerequisites land. Once prerequisite PR merges upstream, draft status is converted to ready for review.

## v0.4.189 (2026-09-16) — Autonomous Harvest Dispatch Restored

- **Autonomous Harvest Dispatch Restored (Owner Order 2026-09-16 10:43 UTC, `fleet-directives.md` & `triage.md`):**
  - Removed the previous "OPERATOR COMMAND ONLY" restriction from `fleet-directives.md §Upstream-merge cadence · HARVEST LAW · NO-HOLD` and `triage.md §Duty T4 Upstream Delta & Backlog Census`.
  - Restored autonomous harvest dispatching via PHOP (`tools/oc-harvest-dispatch vet` & `dispatch`) for fully-soaked (≥24h post-swap for features anchored to youngest behavioral change; immediate for standalone fixes), smoke-verified (v0.4.104 4-leg rubric), novel feature bundles and standalone fix candidates on all T4 patrol cycles without holding for manual operator trigger commands.

## v0.4.188 (2026-09-16) — Stalled Claim Nudge Amendment & Cycle 20260916-c19 Codifications

- **Stalled Claim Nudge Permission (Owner Order 2026-09-16 08:54 UTC, `triage.md` & `fleet-directives.md`):**
  - Codified in `triage.md` Duty T5 and `fleet-directives.md §Zero-Ack & Dispatch Discipline` that Triage and patrol watchers MAY send a progress nudge via `session_notify` (`delivery.mode="turn-end"`) to an active claim holder if expected deliverables have not arrived or progress has stalled beyond the patrol window.
- **Docs Family Codification (Cycle 20260916-c19, Findings A-6, B-3, G-1, A-9, A-10, G-4, A-2, A-11):**
  - **`editor-upstream-pr.md`**: Repaired text splice splitting PR lifecycle sentence.
  - **`editor.md`**: Mandated imperative `memory_search scope="external"` exploration & DRY check before bugfixing in Phase 6-Fix loop; pruned manual plumbing commands.
  - **`triage.md`**: Fixed severed list item 6, mislocated `DONE = ...` formula in Duty T7, and dangling orphaned sentence in Retired Duties.
  - **`upstream-merge-runbook.md`**: Codified checkable `DONE = ...` formulas for Steps 2–7.
  - **`toolsmith.md`**: Updated test battery completion formula to reflect dynamic test pass count.
  - **`SKILL.md`**: Aligned Upstream Delta Watch owner in Upstream Relations table to Triage (`triage.md §Duty T4`).
- **Brain Scrub & State Hygiene (Cycle 20260916-c19, Findings BS-1, D-1):**
  - Pruned historical war story incident markers, stale hex numbers, and specific post-mortem row logs in `AGENTS.md`.
  - Cleaned stale `fanout.*.lock` files from the state root.

## v0.4.187 (2026-09-16) — Harvest Law: Subsystem Cohesion & Dependency Inheritance


- **Atomic Subsystem Bundling (`fleet-directives.md` & `editor-upstream-pr.md`):**
  - Codified that a harvest unit is never an isolated commit — it is a cohesive subsystem bundle comprising the base `feat/*` and all downstream `fix/*`, test, and doc commits touching that subsystem on fork `main`. Harvesting a feature folds all subsequent fixes on fork into that single upstream PR.
- **Dependency & Soak Inheritance (`fleet-directives.md` & `editor-upstream-pr.md`):**
  - Codified that any `fix/*` modifying, depending on, or assuming an unharvested or soaking `feat/*` inherits the full 24-hour soak window of that base feature. It cannot be cherry-picked as a zero-hold fix if upstream lacks the underlying feature code or if the fix mutates unharvested subsystem logic.
- **In-Flight Lane Fence (`fleet-directives.md` & `editor-upstream-pr.md`):**
  - Codified that if an active editor lane is currently modifying a subsystem (e.g. active claim/branch touching that module/flow), harvesting for that subsystem is held until the active lane finishes, hot-swaps, and lands.
- **Deployment-Anchored Soak Clock (`fleet-directives.md` & `editor-upstream-pr.md`):**
  - Codified that the 24-hour deployment soak clock for the bundle is anchored strictly to the live deployment timestamp (`deployed.ts` / swap journal) of the **youngest behavioral change** in the bundle, NOT from commit or filing timestamps.

## v0.4.186 (2026-09-15) — Duty 6 Ledger Cadence Stamp & 24h Soak Deployment Time Amendment

- **Duty 6 Ledger Cadence Reset Stamp (`hq.md` Duty 6):**
  - Codified mandatory step 8 in `hq.md` Duty 6: upon completing a review cycle, HQ must explicitly execute `oc-ledger stamp note "v<version> ACCEPTED — Duty 6 Cycle <id> closed" --by "hq <uuid>"`.
  - Stamping this note creates the `^v[0-9]+\.[0-9]+\.[0-9]+ ACCEPTED` event boundary recognized by `oc-ledger cadence`, properly resetting the review cadence counter from `FIRE` back to `0/5 WAIT`.
  - Updated Duty 6 `DONE = ...` checkable completion formula to require this ledger stamp.
- **24-Hour Feature Soak Deployment Timestamp Amendment (`fleet-directives.md` & `editor-upstream-pr.md`):**
  - Explicitly codified that the 24-hour feature maturation soak window counts strictly from the **live deployment / hot-swap timestamp** (`deployed.ts` / swap journal timestamp when the commit was actually deployed to production), **NOT** from git commit timestamp or issue filing time.
  - Updated upstream PR filing prerequisites in `editor-upstream-pr.md` Phase 7.

Codification of findings from Duty 4+6 Review Cycle `20260915-c18`:
- **Tools & Mechanics Fixes (Findings F-01, F-02, E-01, C-01, J-01):**
  - **`tools/oc-start`**: Added explicit actor attribution (`--by "$OPENCRABS_SESSION_ID"`) when recording ledger claims.
  - **`tools/tests/run.sh`**: Integrated `oc-notify-fanout --selftest` into test battery Section 61, advancing total passing tests to 196/196.
  - **`tools/oc-smoke`**: Enforced robust issue claim owner attribution query from ledger events.
- **Documentation & Phasing Alignment (Findings A-01, B-01, G-01, G-02, A-02):**
  - **`editor.md`**: Renumbered and clarified Phase 6 as `Phase 6 — Smoke Verification (oc-smoke)` and `Phase 6-Fix — Fix Loop (Red Carrier Build or Failed Smoke)`.
  - **`upstream-merge-runbook.md`**: Codified explicit `DONE = ...` checkable completion criteria for Steps 0, 8, 9, 10, and 11.
  - **`triage.md` & `hq.md`**: Consolidated retired duty records under structured `## Retired Duties & Forwarding Pointers` sections.
- **Brain & State Directory Scrub (Findings BS-1, BS-2, BS-3, D-01, D-02):**
  - **`AGENTS.md`**: Pruned historical incident war stories and post-mortem narratives; streamlined hard execution rules.
  - **State Hygiene**: Pruned stale `fanout.*.lock`, `ship.lock`, `.oc-prchecks-dispatch.lock`, and archived `.bak` files older than 24h.

## v0.4.184 (2026-09-15) — Duty 4+6 Review Cycle `20260915-c17` Codification

Codification of findings from Duty 4+6 Review Cycle `20260915-c17`:
- **Tools & Mechanics Fixes (Findings J-1, F-1, E-1, C-1, J-2, F-2, J-3, C-2, E-2, E-3):**
  - **`tools/oc-smoke`**: Fixed actor fallback by checking the specific issue's claim event in `workers-ledger.json` before falling back to latest enrolled worker. Removed duplicate identity block logging by running `oc-smoke-evidence` without inner `--append-log`.
  - **`tools/oc-start`**: Added git pre-flight checks (verifying repo & base ref, ensuring branch does not already exist) before mutating ledger state with a claim. Expanded branch taxonomy regex to accept `docs/` and `refactor/` branches alongside standard `feat|fix|ci|chore`.
  - **`tools/oc-skew-scan`**: Replaced hardcoded `/root/` paths with dynamic `SKILL_DIR` / `${HOME}` fallbacks.
  - **`tools/oc-watcher-audit`**: Replaced hardcoded `/root/` default directories and `oc-notify.sh` paths with dynamic `${HOME}` resolution.
  - **`tools/tests/run.sh`**: Added Section 69 test battery coverage for `oc-log-search` (`--selftest`, `--help`, arg handling), bringing test battery to 195/195 passing tests.
- **Documentation & Role Laws (Findings A-1, B-1, G-1):**
  - Cleaned remaining manual worktree and branch instructions in documentation.
  - Verified checkable `DONE = ...` exit formulas across all role duties (`hq.md`, `triage.md`, `toolsmith.md`, `editor.md`).
- **Brain & State Hygiene (Findings BS-1, BS-2, BS-3, D-1):**
  - Relocated git uncommitted changes rules from `TOOLS.md` to `AGENTS.md § Git and brain files`.
  - Cleaned stale `fanout.*.lock` files from state root.

## v0.4.183 (2026-09-15) — Autonomous Priority Authority Law

- **Autonomous Priority Authority Law (`fleet-directives.md §Autonomous Priority Authority Law`):**
  - Codified that all active lanes (Editor, Triage, Toolsmith, HQ) have complete, independent authority over task ordering, execution sequencing, and operational priorities within their respective codified laws.
  - Prohibited asking the human operator (Alexey) for priority determinations, sequence approvals, or "what should I work on next?" scheduling decisions.
- **Role File Synchronization:**
  - **`SKILL.md`**: Added universal priority authority directive in role router.
  - **`editor.md`**: Added explicit priority and sequencing authority rule.
  - **`triage.md`**: Added autonomous intake triage and patrol priority authority.
  - **`toolsmith.md`**: Added autonomous tool work order and bugfix sequencing authority.
  - **`hq.md`**: Added autonomous skill revision and review cycle cadence priority authority.
- **Tooling Parity:**
  - **`tools/oc-lint-laws`**: Fixed corpus list to drop obsolete `editor-phase7-rules.md`.

## v0.4.182 (2026-09-15) — Editor Milestone Streamlining & Imperative memory_search Gate

- **Editor Law Streamlining (`editor.md`):**
  - Pruned manual multi-step plumbing prose (manual `oc-wt`, manual `oc-prchecks` polling loops, manual issue logging, manual git push to `main`, and manual log formatting).
  - Aligned workflow strictly around the 3 canonical milestones: `oc-start` (Milestone 1: claim & worktree), `oc-ship-chain` (Milestone 2: CI gate, comment, ff-merge, carrier build, swap), and `oc-smoke` (Milestone 3: 4-leg smoke verification).
  - Streamlined Editor Quick Table to daily tools only, documenting that lower-level utilities are orchestrated internally.
- **Imperative `memory_search` & DRY Gate (`editor.md` Phase 3):**
  - Mandated `memory_search scope="external"` as a strict prerequisite before editing or writing code across `/root/opencrabs/src/**/*.rs`.
  - Enforced mandatory symbol-graph and caller/callee impact analysis (`"who calls X"`, `"where is X defined"`) and DRY shared abstraction checks.
  - Prohibited blind code modifications based on literal text `grep` alone.
- **Reviewer Lens Updates (`review-lenses.md`):**
  - Codified the **Subsumed Procedure Pruning Rule** in Lens B (LLM Efficiency).
  - Codified the **Exploration & DRY Verification Gate** in Lens G (Role-File Structure).

## v0.4.181 (2026-09-15) — Duty 4+6 Review Cycle `20260915-c16` Codification

Codification of findings from Duty 4+6 Review Cycle `20260915-c16`:
- **Brain Scrub & Narrative Pruning (Findings BS-01, BS-02, BS-03):**
  - Pruned narrative historical parentheticals in `USER.md` (line 31 timestamp note).
  - Streamlined `AGENTS.md` execution discipline and table formatting notes, replacing multi-line war stories with crisp enforceable rules.
- **Docs Family & Taxonomy (Findings A-01, A-02, A-03, B-01, B-02, G-01, G-02, G-03):**
  - Updated legacy "compile/lint gate" and "PR base-Lint" references across `editor-upstream-pr.md` and `fleet-directives.md` to canonical `CI gate = oc-prchecks`.
  - Dropped dead-weight appendix `§telegram_send TO-BE target states` from `fleet-directives.md`.
  - Structured monolithic remotes paragraph in `fleet-directives.md` into clear sub-sections.
  - Streamlined HQ router row in `SKILL.md` STEP ZERO.
  - Added explicit checkable completion criteria (`DONE = ...`) across `editor.md` (Phase 0, Phase 6c) and `triage.md` (Duties T6, T7).
- **Tools & Mechanics (Findings C-01, C-02, E-01, F-01, J-01, J-02):**
  - Deduplicated `oc-issue-dispatch` entry in `tools/RC-CONTRACT.md`.
  - Added selftests for `oc-lint-laws` and `oc-harvest-dispatch` to `tools/tests/run.sh` battery (192 total test cases PASS).
  - Sanitized `oc-harvest-dispatch` fallback path to derive dynamically from `SKILL_DIR`/`HOME`.
  - Switched `oc-smoke` behavioral probe execution from `eval` to `bash -c` subshell.
- **State Directory Hygiene (Findings D-01, D-02, D-03):**
  - Pruned 0-byte `harvest-census.db`, cleaned stale `fanout.*.lock` files, and moved stale `.bak` files to `archive/`.
- **Battery Verified:** PASS=192, FAIL=0.

## v0.4.180 (2026-09-15) — Duty 4+6 Review Cycle `20260915-c15` Codification

Codification of findings from Duty 4+6 Review Cycle `20260915-c15`:
- **Editor Entry & Smoke Ritual Simplification (Findings A-01, A-02, J-01, J-02):**
  - Updated `editor.md` Phase 1 & 2 to reference canonical `tools/oc-start <issue> [--branch <branch>]` for unified claim, branch setup, and worktree mounting with failure recovery guidance.
  - Updated `editor.md` Phase 6b to reference canonical `tools/oc-smoke <issue> [--verdict PASS|FAIL] [--probe <cmd>]` for 4-leg smoke verification and newline-safe row logging.
- **Checkable Completion Formulas (Findings G-01, G-02, G-03):**
  - Added explicit `DONE = ...` criteria formulas across `editor.md` (Phases 1, 2, 4, 5, 6b), `triage.md` (Duties T4, T5), and `editor-upstream-pr.md` (Phases 7, 7b, 7c).
- **Doc Deduplication & Hierarchy (Findings A-03, I-01):**
  - Deduplicated HARVEST VERIFICATION SWEEP checklist in `editor-upstream-pr.md` with a single reference pointer.
  - Added explicit `#### FAMILY: META — review machinery and catalog` section header in `review-lenses.md`.
- **Tool Registers & Contract Synchronization (Findings C-01, C-02, C-03, H-01):**
  - Added `oc-start`, `oc-smoke`, `oc-issue-dispatch`, and `oc-lint-laws` to `SKILL.md` Canonical Tool Register.
  - Fixed `./tools/oc-roster --selftest` path in `SKILL.md:111`.
  - Deduplicated `RC-CONTRACT.md` entries for `oc-ledger sweep-closed-claims`.
  - Updated `tools/oc-ledger` header comment with live selftest case count (311 cases).
- **Brain File & State Hygiene (Findings BS-01, D-01, D-02, D-03):**
  - Pruned historical narrative parentheticals from always-loaded `AGENTS.md:238, 255`.
  - Cleaned up stale locks in state repository.
- **Battery Verified:** PASS=202, FAIL=0.

## v0.4.179 (2026-09-15) — Duty 4+6 Review Cycle `20260915-c14` Codification

Codification of findings from Duty 4+6 Review Cycle `20260915-c14`:
- **Role-File Header Deduplication (Findings A-01, B-02):**
  - Replaced verbose RELOAD LAW blocks in `editor.md`, `hq.md`, `triage.md`, and `toolsmith.md` with concise 1-line canonical pointers to `fleet-directives.md §Post-compaction skill reload`.
- **Build Trigger Deduplication (Finding A-02):**
  - Deduplicated BUILD TRIGGERS rule between `SKILL.md` and `editor-upstream-pr.md`, leaving canonical wording in `SKILL.md §Hard rules` and a 1-line pointer in `editor-upstream-pr.md`.
- **HQ Checkable Completion Formulas (Finding G-01):**
  - Added explicit checkable completion criteria formulas (`DONE = ...`) to `hq.md` Duties 1 through 6.
- **Editor Escalation Routing (Finding G-02):**
  - Updated `editor.md` smoke failure escalation pointers from HQ to direct dispatch to the owning editor or Triage.
- **Verification Law Modernization (Findings J-01, J-05):**
  - Standardized verification CLI law in `fleet-directives.md` to mandate `./tools/oc-ledger claims <issue-number>` instead of manual ledger grepping.
- **State Repository Hygiene (Finding D-02):**
  - Archived obsolete pre-S3 `orders.json` to `archive/orders.json`.
- **Tooling Fixes & Enhancements (Findings H-02, RC Contract):**
  - Fixed Python string quote formatting in `oc-ledger sweep-closed-claims` and verified claim sweep across closed GitHub issues.
  - Added `--help` rc=0 support to `oc-start` adhering to `RC-CONTRACT.md`.
  - Battery verified: PASS=195, FAIL=0.

## v0.4.178 (2026-09-15) — Duty 4+6 Review Cycle `20260914-c13` Codification

Codification of findings from Duty 4+6 Review Cycle `20260914-c13`:
- **Role Files & Skill Census Synchronization (Findings A-01, A-02, G-01, G-02, G-03):**
  - Synchronized single-writer skill documentation census across `SKILL.md` and `hq.md`.
  - Added explicit checkable completion criteria (`DONE = ...`) to `triage.md` (Duty T3) and `toolsmith.md` (Duties TM1, TM2).
- **Brain File Modernization (Findings BS-01, BS-02):**
  - Modernized deprecated `follow_up_question` references to `suggest_options` in `USER.md` and `TOOLS.md`.
- **State Root Hygiene (Findings D-01, D-02):**
  - Pruned 52 stale `fanout.*.lock` files from state repository.
- **Tooling Implementation Shipped (Toolsmith `d8416817`):**
  - 24h Feature Soak mechanical gate in `oc-harvest-census` / `oc-harvest-dispatch`.
  - Stale claims sweep in `oc-ledger sweep-closed-claims`.
  - Updated `RC-CONTRACT.md` assertion count to 44.
- **Review Cycle Persisted (Lenses A–J, Brain Scrub):**
  - Evaluated 11/11 lenses, persisted reports under `reviews/20260914-c13/reports/` with cryptographic receipts in `skill-review-index.log`. Master verdict at `reviews/20260914-c13/verdict.md`.
  - Battery verified: PASS=194, FAIL=0.

## v0.4.177 (2026-09-14) — Duty 4+6 Review Cycle `20260914-c12` Codification

Codification of findings from Duty 4+6 Review Cycle `20260914-c12`:
- **Doc & Role-File Cleanups (Findings A-1, G-2, G-3):**
  - Deduplicated redundant 43-line Hard Rules block in `SKILL.md`.
  - Lifted Upstream Relations section in `hq.md` out of retired Duty 7 heading to top-level section.
  - Corrected stale cross-references in `triage.md` (Duty T2/T8 cleanup).
- **Brain File & Process Boundaries (Findings BS-1, BS-2):**
  - Pruned verbose smoke rubric in `AGENTS.md` to canonical pointer to `fleet-directives.md`.
  - Re-homed external lanes dev process non-participation rule from `MEMORY.md` into `AGENTS.md`.
- **Tooling Enhancements Dispatched (Findings C-1, C-2, F-1, F-2, J-1..J-4):**
  - Dispatched structured work order to Toolsmith lane (`2fae1230`) covering automated 24h soak gating in `oc-harvest-census`/`oc-harvest-dispatch`, automated stale claims sweep in `oc-ledger`, and CLI wrapper cleanups.
- **Review Cycle Persisted (Lenses A–J, Brain Scrub):**
  - Evaluated 11/11 lenses, persisted reports under `reviews/20260914-c12/reports/` with cryptographic receipts in `skill-review-index.log`. Master verdict at `reviews/20260914-c12/verdict.md`.
  - Battery verified: PASS=194, FAIL=0.

## v0.4.176 (2026-09-14) — Role Duties Realignment & OC_ACTOR Auto-Derivation

Codification of direct process-owner feedback routing, Harvester consolidation into Triage, and ambient actor attribution:
- **Direct Process-Owner Feedback Routing (owner order 2026-09-14 19:25Z):**
  - Retired centralized Idea Box coordination in HQ (`hq.md §Duty 7`) and intermediate Idea/Quirk intake in Triage (`triage.md §Duty T1/T2`).
  - Feedback, quirk reports, and improvement proposals route directly to process owners:
    - **Tool anomalies & CLI tooling**: Route directly to the active **TOOLSMITH** lane (`session_notify` or ledger).
    - **Skill directives & process governance**: Route directly to **HQ** (`reviews/<cycle-id>/proposals/` or `oc-ledger stamp proposal`).
    - **Domain/subsystem code & features**: Route directly to owning **Editor / Domain Lanes** via fork issue tracker.
- **Harvester Consolidation into Triage (owner order 2026-09-14 19:25Z):**
  - Reaffirmed that Editor lanes exclusively own authoring, smoking, and filing upstream PRs (`editor-upstream-pr.md` Phase 7).
  - Consolidated all remaining Harvester lifecycle duties (upstream delta watch, upstream PR census, maintainer dependency tracking) into **Triage** (`triage.md §Role boundaries & responsibilities`).
- **Actor Attribution Auto-Derivation (Toolsmith commit `978fe5fe`):**
  - Tools (`lib/oc-log.sh`, `oc-commit`, `oc-ledger`, `oc-notify-fanout`, etc.) automatically derive attribution from the ambient session environment variable `$OPENCRABS_SESSION_ID`.
  - Retired mandatory manual `export OC_ACTOR=<session-uuid>` requirement from `SKILL.md`, `editor.md`, and `fleet-directives.md`. `OC_ACTOR` remains supported as an optional override.

## v0.4.175 (2026-09-14) — Duty 4+6 Review Cycle `20260914-c11` & Census Alignment
- **Census & Single-Writer Expansion (Lens A, G; Findings G-01, G-03):**
  - Added `editor-upstream-pr.md` to official single-writer census in `SKILL.md §Hard rules` and `hq.md`.
  - Added `editor-upstream-pr.md`, `tools/RC-CONTRACT.md`, `tools/HEALTH-CHECKS.md`, and `tools/HEALTH-CLASSES.md` to `README.md` layout table.
  - Clarified CHANGELOG ordering convention in `README.md` (prepend newest-FIRST).
- **Contract & Count Hygiene (Findings A-01, A-02, C-01):**
  - Harmonized tool fleet counts across `README.md` and `editor.md` to authoritative 39 tools.
  - Deduplicated `oc-issue-dispatch` contract entry in `tools/RC-CONTRACT.md`.
- **Dead Prose & Brain Scrub (Findings B-02, BS-01):**
  - Removed historical Compiler inbox note from active `hq.md §Duty 3` block.
  - Pruned duplicated subshell bash-ism narrative in `AGENTS.md:41` (BS-01) to a concise canonical pointer to `fleet-directives.md §Verification-discipline additions`.
- **Review Cycle Persisted (Lenses A–J, Brain Scrub):**
  - Evaluated 11/11 lenses, persisted reports under `reviews/20260914-c11/reports/` with cryptographic receipts in `skill-review-index.log`. Master verdict at `reviews/20260914-c11/verdict.md`.
  - Battery verified: PASS=194, FAIL=0.

## v0.4.174 (2026-09-14) — Dependent Upstream PRs Law

Codification of maintainer consensus on dependent upstream PRs:
- **Dependent Upstream PRs Law (Maintainer Consensus, 2026-09-14):**
  - Codified in `fleet-directives.md §Dependent Upstream PRs Law`: When PR B depends on PR A (which is not yet merged upstream), filing PR B while PR A is open/pending is explicitly permitted, provided the description explicitly states `Depends on #<PR_A> (do not merge before #<PR_A>)`.
  - Upstream maintainer processes dependent PRs in commit/chronological sequence (PR A merged before PR B).
  - Alternatively, automated harvest pipelines may hold PR B until PR A merges via harvest watch / cron triggers.
  - Updated `editor-upstream-pr.md §Phase 7b Blocker Matrix`: Replaced rigid hold on unharvested prerequisites with explicit dependency notice allowance and deferred automated publish option.

## v0.4.173 (2026-09-14) — 24-Hour Feature Soak Harvest Law

Codification of the 24-hour feature maturation policy before upstream harvesting:
- **24-Hour Feature Soak & Fix Dispatch Law (owner order 2026-09-14):**
  - **New Features (`feat/*`):** Codified mandatory **≥24-hour post-swap soak period** in the live running deployment in `fleet-directives.md §HARVEST LAW` and `editor-upstream-pr.md §Step 4` before upstream PR harvest eligibility. Ensures multi-session resilience, edge-case exposure, and regression soak time on the live binary.
  - **Bug Fixes (`fix/*`):** Maintained immediate upstream harvesting upon passing the verified 4-leg smoke gate (zero maturation hold).

## v0.4.172 (2026-09-14) — JIT Skill-Change Notification Policy & Topic Domain Governance

Codification of daemon-level JIT skill diff hints and persistent topic domain governance:
- **JIT Skill Diff Hint Adoption (advisory n=5322, owner order 2026-09-14):**
  - Shifted routine version bump notification policy in `fleet-directives.md` and `hq.md §Duty 3` from proactive `PUSH-ALL-QUIET` broadcast waves to **JIT / pull-absorption**.
  - Capitalizes on the core daemon turn-start active skill diff hint mechanism shipped in `#210` (`acb8c5e6`).
  - Proactive `oc-notify-fanout` waves are strictly reserved for breaking process shifts, fleet-wide safety halts, or explicit owner-ordered fleet reloads.
- **Topic Domain Governance (owner order 2026-09-14):**
  - Codified persistent **Topic Domain Alignment** in `fleet-directives.md §Topic domain alignment & rename authority`.
  - Mandated that factory forum topics are structured around persistent functional domain subsystems (`Telegram: Host & Session Guards`, `Core: Streaming & Loop`, `Memory: Search & Indexing`, `Config: Typings & Writers`, `Upstream: Harvest Fleet`, `Governance: Role Architecture`, etc.) rather than ephemeral issue numbers or short tasks.
  - Empowered Auditor (Triage) and HQ to continuously rename topics as lane scopes evolve.
- **Battery Verification:**
  - Suite selftest battery verified: PASS=194, FAIL=0 (`tools/tests/battery-last.json`).


## v0.4.171 (2026-09-14) — Duty 4+6 Review Cycle 20260914-c10 Implementation

Implementation of accepted Duty-4 intake proposals and Duty-6 review findings across documentation, role-file architecture, glossary ontology, and tools battery:
- **Appendix Folding & File Retirement (Finding G-3):**
  - Retired `editor-phase7-rules.md` and folded its contents (Harvest Verification Sweep and Qualified Fork Refs) directly into `editor-upstream-pr.md §Phase 7 Reference Rules`.
  - Updated all pointers across `editor-upstream-pr.md`, `README.md`, and `SKILL.md`.
- **Single-Writer Census Expansion (Finding G-1):**
  - Updated single-writer law census in `SKILL.md` to formally include `tools/HEALTH-CHECKS.md` and `tools/HEALTH-CLASSES.md`.
- **Glossary & Ontology Alignment (Findings A-5, J-02):**
  - Formally defined `PARKED-OWNER-EYE` non-blocking smoke row state in `SKILL.md §Glossary`.
  - Formally codified `4-Leg Smoke Rubric` (Lineage, Identity, CI Gate, Behavioral Probe) standard in `SKILL.md §Glossary`.
  - Corrected `oc-watcher-audit` flag documentation in `SKILL.md` table from `--kill-stale` to canonical `--notify-orphans` (Finding A-2).
- **Merge Runbook Execution Flow & Checkable Criteria (Findings G-2, G-4):**
  - Re-ordered `upstream-merge-runbook.md` so that background reference sections (§Gates, §Roles) precede linear execution sequence under §Process.
  - Added checkable criterion to Step 0 Roster Gate: `tools/oc-roster classify | grep '^ACTIVE' | wc -l` reports 0 active unpaused workers.
- **Documentation Efficiency & LLM Burden Reduction (Findings B-1, B-2, B-3):**
  - Updated HQ reload cost footprint warning in `fleet-directives.md` from `~54 kB` to `~115 kB` to reflect live growth.
  - Eliminated duplicated CI watcher throttling rules in `editor.md`, replacing with a concise pointer to `fleet-directives.md §CI Watcher Discipline`.
- **Brain Scrub Remediation (BS-1, BS-3):**
  - Replaced repetitive subshell bash-ism narrative block in `AGENTS.md` with pointer to `fleet-directives.md §Verification-discipline additions`.
  - Re-verified `BOOT.md` for explicit `systemctl --user` commands and zero local cargo compile patterns.
- **Battery Verification:**
  - Suite selftest battery verified: PASS=197, FAIL=0 across 8 parallel jobs (`tools/tests/battery-last.json`).


## v0.4.170 (2026-09-14) — Duty 4+6 Review Cycle 20260913-c9 Implementation & Cycle Durability

Comprehensive implementation of accepted Duty-4 worker proposals, Duty-6 review findings across 11 lenses, and durable cycle state:
- **Duty 4 Worker Proposals Codified (`fleet-directives.md`, `upstream-merge-runbook.md`):**
  - **Retire redundant ledger note row after drift-check (proposal n=4055, `52058a75`):** `oc-drift-check --ack` directly delegates to `oc-ledger ack`; retired the requirement for an additional note row.
  - **Append-only shared log staging carve-out (proposal n=4057, `4b4463d5`):** Self-attributing append-only logs (`smoke-verdicts.log`) are exempt from the dirty-path commit prohibition when foreign rows are explicitly disclosed.
  - **Absorbed branch detection via `git cherry` (proposal n=4067, `9fa7c71a`):** Step 7 in `upstream-merge-runbook.md` uses `git cherry origin/main` rather than raw commit counts to detect synthesized/absorbed branches.
  - **Smoke log identity vs verdict separation (proposal n=4108, `52058a75`):** Explicitly split tool-generated identity evidence blocks from lane-authored verdict rows.
  - **No static row counts in law text (proposal n=4132, `52058a75`):** Banned static row/line counts in law text; counts must be derived dynamically or cited by section/predicate.
  - **Sanctioned smoke verdict taxonomy (proposal n=4175, `52058a75`):** Expanded field 2 taxonomy with `CORRECTION` and `RETRACTION` tokens with documented sha/evidence references.
  - **Newline tail normalization on shared log appends (proposal n=4177, `4b4463d5`):** Mandatory newline tail verification before appending to shared logs to prevent poisoned un-terminated lines.
  - **Anchor/section citations over line numbers (proposal n=4192, `63d775f9`):** Law text citations must reference section headings or grep anchors, never line numbers (`file:N`).
  - **Mechanical derivation of idle editor capacity (proposal 329bf3a3):** Defined idle status by cross-referencing ledger claims with open GitHub issues (`gh issue list --state open`).
- **Duty 6 Review Findings Codified (Lenses A, B, G, H, J):**
  - **Finding A-1 (Lens A):** Replaced legacy "Lint" terminology with canonical "CODE TESTS = CI gate" (`editor.md`, `fleet-directives.md`).
  - **Finding G-1 (Lens G):** Removed 36 lines of procedural upstream sync execution from `hq.md`, leaving clean governance pointers to Triage (`upstream-merge-runbook.md` / `triage.md`).
  - **Finding G-2 (Lens G):** Codified checkable completion criteria for smoke tests in `editor.md` (`DONE = Mechanical proof demonstrating target feature execution against running binary...`).
  - **Finding H-1 (Lens H):** Codified ban on clock-bomb test fixtures (row n=2123) and trailer retention mandate across history rewrites (row n=2102) in `fleet-directives.md` and `upstream-merge-runbook.md`.
  - **Finding J-2 (Lens J):** Codified mechanical pure-docs verification via `tools/oc-ship-chain --eval-docs-skip <sha>`.
- **Duty 6 Cycle State Durability (`hq.md`, `reviews/20260913-c9/state.json`):**
  - Codified Step 0 in `hq.md`: Every Duty 4+6 cycle maintains a machine-readable `reviews/<cycle-id>/state.json`.
  - Step-0 Recovery Mandate: HQ must check for and restore from `state.json` after context compaction before repeating queries or reviewer dispatches.
  - Backfilled canonical cycle state for `20260913-c9`.
- **Tooling Enhancements (Toolsmith commit `4db9c6ba`):**
  - C-1: Token-bounded regex in `oc-harvest-dispatch`.
  - C-2: Integrated `oc-watcher-audit --json` into `oc-health`.
  - E-1: Deprecated legacy alias wrappers in `tools/RC-CONTRACT.md`.
  - E-2: Consolidated `oc-roster-selftest` into `tools/tests/`.
  - F-1: Added `tools/RC-CONTRACT.md` to `DEFAULT_CORPUS` in `tools/oc-lint-laws`.
  - F-2: Parameterized state dir paths in `tools/lib/oc-log.sh`.
  - I-1: 11-lens catalog + waivers in `oc-review-persist`.
  - Suite selftest battery: PASS=193 FAIL=0.
- **Ops Profile Brain Scrub (BS-1, BS-2, BS-3, BS-4):**
  - Pruned repetitive post-mortems in `AGENTS.md`, sanitized bashisms in `TOOLS.md`, and aligned `BOOT.md` service/build commands with Box Law.


## v0.4.169 (2026-09-13) — Zero-Ack Dispatch Law

Codifies binding owner directive eliminating conversational notification acks:
- **Zero-Ack on Task & Harvest Dispatches (`fleet-directives.md`, `editor.md`, `triage.md`):**
  - Task and harvest dispatches are strictly one-way work directives.
  - Senders must conclude every dispatch envelope with: `Ack contract: NONE — claim on ledger (oc-ledger claim) and proceed.`
  - Receiving lanes (editors and harvesters) are strictly forbidden from replying with conversational `session_notify` acks (`[ack] Received...`, `Starting now...`).
  - The ledger claim (`oc-ledger claim <issue>`) is the sole valid and required receipt.
  - Senders verify delivery via `workers-ledger.json` (`oc-ledger events --kind claim`), eliminating queue pollution and token waste.


## v0.4.168 (2026-09-13) — Upstream Coding/Testing Standards & Process Directives

Codifies binding owner directives and upstream standards from Adolfo Usier DM and CONTRIBUTING.md audit:
- **Upstream Coding & Testing Standards (`fleet-directives.md`, `editor-upstream-pr.md`, `editor.md`):**
  - **Strict test isolation:** ALL tests must live under `src/tests/*_test.rs` registered in `src/tests/mod.rs`. Absolutely **NO inline `#[cfg(test)] mod tests`** blocks inside source files in `src/`.
  - **`mod.rs` declarations only:** Zero function definitions (`fn`) inside any `mod.rs`. Only doc comments, `mod`/`pub mod` statements, and `pub use` re-exports.
  - **Commit trailers:** Zero `Co-Authored-By` lines allowed in commit messages.
  - **No mock tests / real testing:** Tests must hit real structs and SQLite; tests must fail without the fix and pass with it.
  - **Zero warnings / no error suppression:** No `#[allow(dead_code)]` or `#[allow(unused)]` duct tape; unused code must be deleted.
  - **`ONTOLOGY.md` synchronization:** Update `src/docs/reference/ONTOLOGY.md` whenever introducing, renaming, or retiring concepts.
- **Strict Atomicity & Zero Bundling (`fleet-directives.md`, `editor-upstream-pr.md`):**
  - 1 Intent = 1 Unit. Never mix features and bug fixes in the same branch, issue, or PR.
  - Discovered bugs during feature work get isolated fork issues and separate branches/PRs.
- **External Lanes Licence & Dev Non-Participation (`fleet-directives.md`):**
  - External lanes (e.g. `inferhub-watch`) are permitted to open fork issues on `leshchenko1979/opencrabs` for runtime anomalies observed during operation.
  - External lanes are strictly barred from the development process (no PRs, no code edits in `/root/opencrabs`, no participation in dev triage/review).
- **LLM Ergonomics & Efficiency Law (`fleet-directives.md`):**
  - Design tools, schemas, and feedback for LLM constraints: contextual anchors over index arithmetic, actionable self-healing errors, turn consolidation, and token discipline.
- **Brief Verification & `--dry-run` Compliance (`fleet-directives.md`):**
  - Briefs written during blocked states must be verified against git log and active receipts before broadcast.
  - Ad-hoc scripts must strictly guard mutating state changes behind flags and respect `--dry-run`.
- **Explain Open Questions & Re-Anchor Context (`fleet-directives.md`):**
  - Never merely index open questions (e.g. "Q1–Q5 remain"); explain the most critical dilemma, trade-off, and recommended default.

## v0.4.167 (2026-09-13) — Retired surfaces off the live docs (verdict D-1 + convergent A-F2 · E-1 · F-5)

Origin: **the 20260912 lens cycle accepted five findings that all say one thing — a RETIRED surface
still described present-tense.** D-1 (`README.md` advertises the retired `oc-waiter` as a live tool),
A-F2 ("RETIRED concept still described present-tense"), E-1 (`oc-wt`'s retired index chain), C-3 and
F-5 converge on it. This entry lands the doc half. F-5's verdict was **KERNEL** — *"the tool is
RETIRED (v0.4.135) — D-1's fix removes the last live reference; no code change owed."*

`tools/oc-waiter` is a 1372-byte stub whose own header says RETIRED, and `tools/RC-CONTRACT.md`
documents it correctly (*"RETIRED in v0.4.135: replaced by native detached bash execution
(`background: true`); `--help` returns 0, subcommands return 1"*). **Six live-doc sites disagreed** —
and the sharpest one taught a dead surface inside the very lens that flags lanes for not using the
official one:

- **`README.md` — the tool-highlight row.** Advertised `oc-waiter` present-tense as *"lane wake
  service: arm/_run/sweep/list, systemd transient scopes"*. Replaced with the retirement plus the
  live mechanism: native detached bash (`background: true`, the harness wakes the caller with the
  exit code) and `tools/lib/oc-notify.sh` for cross-session chaining.
- **`README.md` — the `oc-notify.sh` row.** Read *"shared wake/notify contract for waiter +
  prchecks"*. The lib's own header names its consumers: the wake logic *"previously duplicated
  between oc-deploy (notify_session, fanout path) and oc-waiter (resolve_notify_bin + notify_lane).
  Both consumers now source this file."* Live consumer today is `tools/oc-deploy` (sources it) plus
  the executable CLI wrapper — not `oc-prchecks`. Corrected.
- **`toolsmith.md` — the live-tool enumeration.** Named `oc-waiter` among *"the commands every other
  lane runs"*. Dropped.
- **`toolsmith.md` — Duty TM1's interface-drift clause.** Used *"oc-waiter greps oc-prchecks' `RUN`
  line"* as its dependent-consumer example. Replaced with a VERIFIED live consumer:
  `oc-ship-chain`'s LEG1 gate, which journals *"LEG1 gate run <run> is still <info> — attaching via
  oc-prchecks resume"* (`tools/oc-ship-chain`, LEG1 gate).
- **`review-lenses.md` — lens C's ADOPTION-COMPLIANCE CHECK.** Prescribed *"official surfaces are
  `oc-waiter arm` and one-shot `gh run view`"*. A retired tool named as the official surface, in the
  lens whose whole job is flagging non-compliance with official surfaces. Replaced with native
  detached execution + one-shot `gh run view` (and `oc-prchecks --wait` for a blocking gate).
- **`review-lenses.md` — lens H's slice-tool list.** Named `oc-waiter-sweep` as a **tool**; no such
  file exists. It is a law-carrying **cron**, retargeted to `oc-roster-detached-sweep` (job id
  `b0d7e0d3-1270-4fb5-8cb8-6c7161e90c34`, `*/5 * * * *` UTC, `Deliver: none`). Qualified as a cron.

**A SEVENTH site, found while landing this — and it is this law's own subject matter one iteration
later.** `SKILL.md`'s `oc-harvest-census` register row read **"`record` is currently a NO-OP … wire-or-
retire DISPATCHED to Toolsmith"**. That was true at `def56377`; Toolsmith landed `8f7b9558` **three
commits later**, wiring the verb — and found the defect was worse than reported: the registry write
dumped a literal two-key dict, so every `sync`/`scan` ERASED `manual_records` (non-durable by
construction), and `check` had no reader at all. Both fixed; selftest 6/6 → 10/10. **The v0.4.166
clause says a "until X lands" claim must be revisited in the SAME version window X lands — and this
row was that clause's own text, still stale.** The row now records the wired behaviour (rc 1
`REFUSED … manually recorded as filed in PR #<n> (unit <u>)`, the merging write, the landing sha) and
drops the DISPATCHED tail.

**Extra (disclosed, NOT part of D-1) — the README's tool count is dropped.** `README.md` read
*"29 executables in `tools/` (31 − `oc-toolaccum` v0.4.110 − `oc-ci-parity` v0.4.117; owner-ordered
additions 2026-09-01)"*. The predicate is stated and reproducible, and the figure does not survive
it: `find tools -maxdepth 1 -type f -perm -u+x | wc -l` = **39** (42 files at that depth; the other
three are `HEALTH-CHECKS.md`, `HEALTH-CLASSES.md`, `RC-CONTRACT.md`). Under the **"state the
predicate with the number"** law this is an unreproducible absolute count of a **growing** inventory,
so the count is replaced by a pointer to the register — `tools/RC-CONTRACT.md` is the authority, and
a drifting count is a future false-defect generator.

**Method note.** Every replacement was verified first-hand before it was written: `oc-ship-chain`'s
LEG1 journal line (grep, same turn), `lib/oc-notify.sh`'s own consumer header (read, same turn), the
cron's live existence via the cron tool (`oc-roster-detached-sweep`, last run 2026-09-13 09:30Z), and
Toolsmith's `8f7b9558` verified in-tool (`git merge-base --is-ancestor` rc 0, the `manual_records`
read at the check path, the merging write, `--selftest` 10/10 OK). Anchors were captured from a
same-turn read of each region and the patch is all-or-nothing — **cite a region by its TEXT, never by
a line number**, which is stale after every edit.

Docs-only. Battery unchanged.
## v0.4.166 (2026-09-13) — Truth in Law: a clause stale inside its own version window

Origin: **the v0.4.165 clause said the tool half "is DISPATCHED to Toolsmith" — and the tool
landed 3 min 32 s after the clause was committed.** Found by lane `d18ce16a`, against the clause
itself, which ends by naming exactly this failure mode.

Timeline, read from `git log`:

- `e13bef5e` **08:10:38Z** — the law clause is committed, ending "…is DISPATCHED to Toolsmith."
- `38e417af` **08:14:10Z** — Toolsmith lands the omit-arg mode. Touches `tools/RC-CONTRACT.md`,
  `tools/oc-drift-check`, `tools/oc-notify-fanout`, `tools/tests/battery-last.json` — **never**
  `fleet-directives.md`.

So the clause was stale *inside its own version window*. HQ corrected the BRIEF and left the LAW,
which is precisely the asymmetry the clause's own test case names: **a cold reader learned the
mode did not exist and fell back to the version-arg form the same clause warns can be vacuous.**
The brief is transient; the law is what a lane reads cold.

- **`fleet-directives.md` §The RELOAD line — the "DISPATCHED to Toolsmith" tail now records the
  LANDING.** `38e417af`: `oc-drift-check <uuid> [--ack]` reads the lane's OWN `last_acked` from
  the roster; a uuid with no history returns `NO-HISTORY` as its OWN verdict (rc 0, "treat as
  DRIFT") and is never folded into `NO-DRIFT`; the legacy `<uuid> <claimed-ver>` form still
  works; selftest assertions named (`omit-arg-uses-last-acked-not-argv`,
  `omit-arg-no-history-is-not-no-drift`). Cite a tool by COMMIT + subcommand, never by line.
- **NEW LAW — a clause that says "until X lands" must be revisited in the SAME version window X
  lands.** A tool commit touches `tools/**`; a law commit touches the law files; **nothing makes
  the two meet**, so the pairing has to be a deliberate step: check `git log --oneline` for the
  tool's landing before closing the version. Precedent recorded in the same bullet — the
  docs-only LEG1 skip was caught the same way and recorded as SUPERSEDED in v0.4.163 rather than
  amended in place.
- **The canonical RELOAD form is now omit-arg on every teaching surface.** `editor.md`
  §Mid-cycle skill drift step 1, the `editor.md` tool table, and the `SKILL.md` tool table all
  taught `<uuid> <claimed-ver> [--ack]` as *the* form while `oc-notify-fanout` emits the omit-arg
  form — two canonical teaching surfaces disagreeing, the same cold-reader failure one layer
  down. All three now teach omit-arg as canonical, with the version-arg retained as
  accepted-legacy.

Credit: lane `d18ce16a` (the stale clause *and* the three teaching rows — a second finding
offered as "not a filing", which is the judgement the correction needs); lane `329bf3a3` (the
`--ack` ordering observation, independently reproducing the three rows and the live DRIFT firing);
lane `d5863180` (a register row advertising a verb with no effect); Toolsmith (`38e417af`, landed
3 min 32 s after the dispatch, which is the speed that created the window).

## Addendum to v0.4.166 — three more sites, same class

- **`editor.md` step 2 gains the `--ack` ORDERING note (lane `329bf3a3`).** The `--ack` block sits
  BEFORE the verdict comparison (deliberately, moved there 2026-09-11 by lanes `d18ce16a` +
  `a5b34466` so a clean-tree compliance records a row instead of nothing). Consequence: one
  `--ack` invocation both stamps the new version **and** reports DRIFT against the `last_acked` it
  read a moment earlier — the sensor fires once per version and its own firing writes the state
  that silences it. A lane reading only the verdict could conclude the ack failed. The note says:
  confirm with a no-`--ack` re-run, do **not** retry with `--ack` (the M2-4 idempotent guard makes
  a second attempt a no-op — `oc-ledger` §`cmd_ack`), so the failure mode is a wasted turn, not a
  duplicate row.
- **The v0.4.165 clause's OWN PROSE was stale the moment its tool half landed (found by HQ while applying this very patch).** The clause documenting the argv-echo defect still said the fanout "auto-appends the same vacuous form (it substitutes the live version)" and that the correct prescription was `<claimed-ver>` in `editor.md` and the `SKILL.md` tool row — but `tools/oc-notify-fanout` emits the OMIT-ARG form (cite by ANCHOR) and this version had just made those two teaching surfaces canonical for omit-arg. So the clause teaching that law text goes stale inside its own version window had itself gone stale inside its own version window — the third occurrence, one layer up. Two further sites of the same sentence fixed with it: the `:411` quoted RELOAD example (carried a `<your-claimed-ver>` token and named a file list the emitter does not emit) and the `:415` parenthetical quoting the emitted line with a `<ver>` token. The clause now records the fix as a TOOL fix rather than a brief fix, and scopes the "pass the version IT last adopted" duty to the LEGACY form only — the canonical form has no token left to get wrong.

- **`SKILL.md` register row: `oc-harvest-census record` is a NO-OP (lane `d5863180`).** The verb is
  dispatched (`cmd_record`) but appends to `manual_records`, and **nothing reads that key** —
  `grep -n 'manual_records' tools/oc-harvest-census` is exactly one hit, the writer. No law
  prescribes `record` (only `check`, `editor-upstream-pr.md` §172), so no procedure was broken —
  the register row simply advertised a verb with no effect. The row now says so, names
  `check`/`scan` as the working path, and records the wire-or-retire as DISPATCHED to Toolsmith. **HQ re-verified the premise first-hand before writing that word into law** (`manual_records` = one hit, `:330`, the writer; no reader fleet-wide; `check 138` rc=1 REFUSED on PR #1537) and dispatched it for real — ledger `n=4216`, injected into the Toolsmith lane's tool loop 08:58:52Z (`tool_loop.rs:7383` on session `2fae1230`).
  **Why it rides this version:** the same class as the rest — a register row asserting a capability
  the code does not have. The row is fixed NOW rather than after Toolsmith's call, because the
  asymmetry between "the code will be fixed" and "the file a cold reader opens says so" is exactly
  what this version is about.


## v0.4.165 (2026-09-13) — The Predicate Rule, and a Sensor That Could Not Fire

Origin: **the v0.4.164 correction carried its own unreproducible number.** That entry fixed the
smoke-log clause and quoted *"55 verdict rows (9 canonical / 46 free-text)"*. Four lanes
(`d18ce16a`, `c6b1a539`, `329bf3a3`, `c2ba4ef2`) independently reported they could not reproduce
it; none claimed it was wrong — each stated its own measurement **with a definition** and said the
recipe was missing. HQ re-measured and found the culprit **in HQ's own measuring script**: its
verdict-token set held the short common words `NA`/`N/A`/`PARTIAL`/`BLOCKED` behind a bare
`^\S+\s+` prefix, so it counted **prose and `evidence=` continuation lines as rows** — 56 matches,
42 of them over-matches. The 55 was a regex artifact. The clause had banned unmeasured numbers in
the very sentence that carried one, one iteration after the "98" it was written to correct.

In the same window lane `212b3c83` reported a sharper defect: **the RELOAD line every brief
prescribes cannot detect the condition it exists to detect.**

- **The absolute counts are GONE; the structural claim is kept.** `fleet-directives.md`
  §Canonical smoke log now states the load-bearing fact — **1 tool-written identity block vs
  lane-authored verdict rows** — and adds the rule: **state the PREDICATE with the number, or
  state no number.** A count whose definition is not stated is, in `329bf3a3`'s phrase adopted
  here as the ruling, *"an assertion wearing a measurement's clothes."* The clause also records
  its own failure history honestly: both bad figures (the 98 and the 55), and the regex mechanism
  behind the second.
- **No absolute count of a GROWING file may be written into law text.** The clause read
  *"136 lines / 55 rows"*; the log was **146 lines** before the hour was out. Absolute counts of a
  growing file are stale on arrival — they rot exactly like the 98.
- **The RELOAD version token is the lane's OWN CLAIM** (`<your-claimed-ver>`), never the announced
  version. `oc-drift-check <uuid> <claimed>` compares **ARGV to the live `SKILL.md` version and
  nothing else** (`cmd_drift`), so prescribing the NEW version makes argv == live **by
  construction** and the verdict is **always `NO-DRIFT`**. Reproduced first-hand on a **synthetic
  uuid that has never acked anything**: `oc-drift-check deadbeef-…-5555 0.4.164` → rc 0 `NO-DRIFT`.
  A lane with no history passes the compliance check. `tools/oc-notify-fanout` auto-appends the
  same vacuous form (it substitutes the live `${version}`), so the wrong form reached the fleet
  automatically; the correct form had always been in `editor.md` §Mid-cycle skill drift and the
  `SKILL.md` tool row. **A `NO-DRIFT` obtained by passing the announced version is not evidence of
  compliance and must never be cited as a receipt.** The `--ack` arm is unaffected and correct.
- **Tool half dispatched to Toolsmith:** an omit-arg mode (`oc-drift-check <uuid> --ack`) that
  reads `last_acked` from the roster and compares **that** to live, making the check a pure
  function of state on disk instead of an argv echo.
- **Distribution:** the corrected v0.4.164 brief was re-issued as wave `a9561c346258`, which
  closed **COMPLETE 28/28** (`--verify` rc 0) — the first wave in this cycle to reach every
  target. The v0.4.163 wave it replaced had closed PARTIAL 14/28.

## v0.4.164 (2026-09-13) — The Correction Reaches the Lanes

Origin: **fixing the law file is not the same as distributing the correction.** `fdb34a5b` corrected
the smoke-log clause in `fleet-directives.md` at 21:42:30Z. The v0.4.163 fanout brief — the artifact
lanes actually READ — ran at 21:54:14Z, **twelve minutes later**, carrying the uncorrected bullet
verbatim. So the tree said one thing and every lane that received the brief was taught the other.
Four lanes reported it independently (`52058a75`, `63d775f9`, `212b3c83`, `a5b34466`), each having
verified the tree first-hand rather than trusting the brief. The class is the stale-law class v0.4.163
itself names: **a brief is a SNAPSHOT of the law at the moment it is written, and a law fix that does
not re-issue the brief has reached nobody.**

- **The brief is corrected and re-issued.** Its second bullet said *"the smoke row is APPENDED by the
  tool; a hand-typed row is a procedure violation"* — conflating the IDENTITY EVIDENCE BLOCK
  (`oc-smoke-evidence --append-log`, deployment proof) with the VERDICT ROW (lane-authored, and
  appending it is NOT a violation). Impact is a silent failure: a lane believing the tool writes the
  verdict row authors none, the verdict goes unrecorded, and the lane believes it was recorded — the
  same shape as the C-1 defect. The re-issued brief opens with a RE-ISSUE NOTE so a lane that received
  the earlier copy knows why it is seeing the brief again.
- **`fleet-directives.md` §Canonical smoke log — the count is MEASURED, not estimated.** The clause
  I had just corrected for exactly this class of error carried MY OWN unmeasured figure: *"98
  lane-authored verdict rows"*. Lane `a5b34466` reproduced the *"0 tool-appended identity blocks"* half
  and could not reproduce 98 under any definition. Re-measured: the canonical log holds **55 verdict
  rows** (9 in the canonical tab-separated shape, 46 in older free-text shapes) and **0 tool-appended
  identity blocks**. The 98 reproduces under no definition of a verdict row. An unmeasured number in
  law text is a claim, and this one was wrong in the same sentence that banned the error.
- **`CHANGELOG.md:8` — the C-1 bullet gets the marker it lacked.** `fdb34a5b` touched ONLY
  `fleet-directives.md`, so the falsified claim survived unmarked at every other site that carried it.
  The C-1 bullet now carries **SUPERSEDED same-day by `fdb34a5b`**, the same treatment line 34 already
  had — a reader could otherwise take the changelog as current law.
- **`SKILL.md:101` — the tool row's writer claim is narrowed.** *"--append-log is the SANCTIONED writer
  of the canonical `smoke-verdicts.log`"* reads as *"this tool writes the log"*, landing a lane on the
  same wrong inference. It now reads *"…of the **IDENTITY EVIDENCE BLOCK** in the canonical
  `smoke-verdicts.log` — the VERDICT ROWS are LANE-AUTHORED."*
- **Toolsmith dispatched** for the sanctioned-writer half: a `--late-entry` / `--sha` override so
  `oc-smoke-evidence` can emit a HISTORICAL row, closing the `:145` LATE-ENTRY exception that the law
  grants but no tool could discharge.
- **BATTERY**: 175 PASS / 0 FAIL.

## v0.4.163 (2026-09-12) — The Law Catches Up With Its Own Tool

Origin: three lanes reported, independently, that law shipped in v0.4.161 had been overtaken by its own tool half — and the sharpest form of the defect is that the law and the tool landed **24 minutes apart, inside the SAME tag**. A fourth gap arrived mid-batch. Every claim was verified first-hand before editing; one was reproduced from its recorded shas.

- **The stale-law class, named.** A law that says *"until X lands"* MUST be revisited in the SAME version X lands — otherwise it is stale the moment it ships. `fleet-directives.md` §Enforcement split said *"until that change lands a docs-only commit still burns LEG1"*; `d6cb9b9a` landed that change at 11:56:24Z, **24 minutes after** the 11:32:09Z law text, both inside v0.4.161. The clause is SUPERSEDED: a pure-docs commit now SKIPS LEG1, the exclusion set is DERIVED at gate time (`shipchain_docs_only()`, `tools/oc-ship-chain:494`), the skip is recorded in the journal (`GATE-SKIPPED-DOCS`) plus a `shipchain` ledger row, it applies to a FRESH dispatch only (`--gated-run`/`--gated-sha` still gate), and the force flag `OC_SHIPCHAIN_NO_DOCS_SKIP=1` does exist. Lanes `afe476f8` and `a5b34466` found this before HQ did.
- **C-1 — the smoke row IS appended by the tool.** `fleet-directives.md` still said `oc-smoke-evidence` *"PRINTS a leg and never appends"*, i.e. it taught the hand-typed write it had just retired. Now: the row is APPENDED by `oc-smoke-evidence --append-log` (bare = the canonical absolute; a wrong path is unrepresentable, M2-2) and a hand-typed row is a procedure violation. Plain shell `>>` is what glued `c10cd97b`'s rows. The `SKILL.md` tool row names the flag. **SUPERSEDED same-day by `fdb34a5b` — see `fleet-directives.md` §Canonical smoke log.** This bullet CONFLATED two artifacts and banned the AUTHOR where it meant to ban the WRITE MECHANISM: `--append-log` writes the IDENTITY EVIDENCE BLOCK (deployment proof — pid, exe_sha256, artifact_sha256, run_id, VERDICT; 10 tab-separated lines), NOT the verdict row. The VERDICT ROW is LANE-AUTHORED and appending it is **NOT** a violation. What is banned is plain shell `>>` (newline-unsafe). Measured: 55 verdict rows, 0 tool-appended identity blocks.
- **The duplicate-ack HISTORY was MEASURED, not remembered.** The v0.4.159 sentence cited "20+ lanes going back to 0.4.143" and a tight 2 s pair as the class. Audit: **68 duplicate `(uuid, version)` groups across 27 lanes, 75 extra rows, back to 0.4.118**; median gap **16 min** and only 19 of 68 within 5 min — so the mechanism is a **RE-ACK** at a later boundary, not a double-write, and the 2 s pair is the exception rather than the class. Heaviest lanes: `61161247`, `462181e9`, `d5863180` ×5 each. **CLOSED** by the M2-4 idempotent re-ack guard (`a36224ad`, 15:50:14Z) — zero duplicate rows since.
- **Citation defect — pair identifiers by READING the row, never by adjacency.** The same section named `d18ce16a` for rows 3713/3714; those rows were written by `d5863180` (2 hits vs 0). Five adjacent rows had been paired off by proximity instead of by reading each one.
- **`upstream-merge-runbook.md` §step 7 gains STEP 0 — a patch-id test before the cut derivation** (lane `9fa7c71a`, proposal n=4067, evidence n=4071). A range count cannot tell "this lane has work" from "this lane SITS ON a base whose lineage was replaced": after a SECOND re-synthesis, a lane still pointing at the FIRST new base has a range populated entirely by that base's own history, so the count reads non-zero while genuinely pending work is ZERO and the zero-test never fires. Reproduced from the recorded shas: `origin/main..b3b3fc9a` = **15** with `git cherry` = **15 × `-` / 0 × `+`**, and the derived rebase was **rc 1 over 10 conflicting files** on a branch with zero work. `git cherry origin/main <branch> | grep -c '^+'` = 0 — absorbed, SKIP (pointer move); and the cut must be the base the lane SITS ON, never derived from a range against a lineage that was rewritten. J-shaped: a migration verb printing `ABSORBED|PENDING` would remove the hand-derivation entirely.
- **BATTERY**: 175 PASS / 0 FAIL.

## v0.4.162 (2026-09-12) — The Meta-Lens's Own Findings Ship

Origin: the 20260912 Duty-6 cycle ran **Reviewer I (META-REVIEW) alone** — the first I spawn since 2026-09-10 — and it reported against the review machinery itself. Two of its four findings are law edits; they were written under the CPU pause and held until the owner lifted it.

- **I-6.2 — enumeration drift fixed (`SKILL.md:51`).** The HQ role row read *"ten-lens skill review … = ELEVEN reviewers"*: the noun counted ten while its own parenthetical counted eleven. Now *"eleven-lens skill review"*. The catalog (`review-lenses.md:3`) already said eleven — the two disagreed on the unit.
- **I-7.1 — Reviewer J gains its ARTIFACTS boundary (`review-lenses.md`).** J's brief carried `BOUNDARY vs C` only, so a state-derivable decision sitting on an artifact had two candidate owners and no rule to separate them. New clause: the ARTIFACTS family owns the ARTIFACT and its verdict, J owns the LAW SENTENCE that assigns the decision — a rule telling a lane to look up whether an artifact is still referenced is J's finding, while the DELETE / ARCHIVE / KEEP verdict stays D's. A reciprocal line in the ARTIFACTS family header points back.
- **I-7.2 closed as KERNEL, no action.** The brain-scrub brief lives at `fleet-directives.md § Review lens brain-scrub` by deliberate, documented split (`review-lenses.md:6` names the location). Moving it would duplicate a brief across two files — a one-concept-one-home violation.
- **I-6.1 CORRECTED — the coverage count was read from the wrong corpus.** I reported "6 of 10 lenses silently absent" from `reviews/20260911-cycle`, which is the SKILL repo's HQ-side MIRROR. The real Duty-6 cycles live in the STATE repo (`20260911-c5..c8`) and ran **10 of 11** each; the only absent lens is J, which did not exist yet. Retracted in the cycle verdict table §5. The surviving finding is the better one: the corpus is **unaddressable** — two repos, four report-naming conventions, closing artifacts that disagree — so `oc-review-persist check-cycle` derives the CATALOG at gate time (correct, and it works) but still takes the corpus ROOT from the caller. A gate handed the wrong directory answers the question wrongly; same family as M2-1. Dispatched to Toolsmith.
- **Same cycle, M2-21 — a tool's selftest was writing into production telemetry.** `oc-ship-audit` reported false ORPHANED dispatches; the shas were `oc-deploy`'s own selftest fixtures. `lib/oc-log.sh` suppressed only on the `--selftest` FLAG, while `oc-deploy:2976` dispatches `--selftest|selftest` as one case arm — a bare `selftest` never exported `OC_TOOLS_NOLOG`, so every fixture child logged to the real `tools.log`. `tools/tests/run.sh` exports the var globally, which masked it inside the battery. Toolsmith fixed it with a shared `oc_is_selftest()` predicate guarding both `oc_log_init` and `oc_log_flood_guard`; blast radius **5 fixture shas across two weeks** (08-31 → 09-12), 4 of which the audit's ~24h window could never see. HQ verified live: bare `oc-ledger selftest` → rc=0, production log delta **0 rows**. `oc-ship-audit` deliberately left strict — fix the source, not the detector.
- **BATTERY**: 175 PASS / 0 FAIL (receipt `tools/tests/battery-last.json`).

## v0.4.161 (2026-09-12) — A Docs Commit No Longer Burns the Gate

Owner ruling, verbatim: *"We don't need the pure docs commits to pass through ci on our side."* Origin: lane `6630dc9a`'s docs commit `eee36027` (ONTOLOGY.md + CONTRIBUTING.md, zero code) burned LEG1 run `34688939568` in full; the owner ruled after seeing it.

- **NEW LAW — a pure-docs commit SKIPS the LEG1 CI gate (`fleet-directives.md §Docs-Only LEG1 Gate Skip`, `editor.md` Phase 5 Leg 1).** The skip is a third outcome: not PASS, not RED, but **SKIP**.
- **"Pure docs" is DEFINED IN THE LAW, not in a tool's discretion.** Every changed path must end `.md` AND must not be `include_str!`/`include_bytes!`-compiled into the binary. The second clause is load-bearing: a `.md` compiled into the binary changes COMPILED OUTPUT, so touching it is a code change and MUST run the gate. On a range-shipping chain, every commit in the range must be pure docs.
- **The compiled-in exclusion set is enumerated — 21 paths, HQ-verified first-hand** against `src/**/*.rs`: `README.md`; the 9 `src/docs/reference/templates/{SOUL,USER,AGENTS,TOOLS,MEMORY,CODE,SECURITY,BOOT,HEARTBEAT}.md`; the 8 `templates/skills/*/SKILL.md`; `plans/plan-json-spec.md`; and `eval/fixtures/memory_corpus{,_multilingual}.md`. The law also carries the one-command derivation, so the list is checkable rather than trusted.
- **Recording is mandatory — an absent gate is never a passed gate.** A skipped LEG1 must appear in the ship journal AND in a ledger row naming the sha. The v0.4.109 identity + verdict laws are unchanged: GREEN only for a gate that actually ran `completed success`; a skipped leg is cited as SKIPPED and never counted as a passed leg in a smoke receipt.
- **Upstream precedent cited, shape deliberately NOT copied.** `ci.yml:23-27` paths-ignores `**.md`/`docs/**` on push "so they don't burn the matrix" — but that test is extension-based and would skip a commit editing a compiled-in template. The law states the exclusion explicitly instead of inheriting that hole.
- **Scope is law text ONLY; the tool half is Toolsmith's (defect #20).** The section names NO flag — but the `oc-ship-chain` LEG1 change LANDED in this same tag (`d6cb9b9a`, 11:56:24Z), so a docs-only commit does NOT burn the gate and the force flag `OC_SHIPCHAIN_NO_DOCS_SKIP=1` does exist. **SUPERSEDED — see v0.4.163.** Law must name only verbs that exist (v0.4.153).
- **The exclusion-set bullet above is AMENDED same-day (commit `448f32e4`).** The first draft enumerated the 21 paths AND carried a `grep` telling a lane to re-derive the set — agent memory as a gate input. Owner struck it (*"that should be purely mechanical"*): the set is now DERIVED BY THE TOOL at gate time and the 21 paths are **illustrative, not normative**; a lane that finds itself needing the list has found a missing tool half (defect #20), not a missing fact.
- **NEW LENS — Reviewer J, MECHANICAL ENFORCEMENT, in a new MECHANICAL family (`review-lenses.md`).** Owner order: *"make it a separate lens"* — the principle *law must not assign to an agent any decision that is a pure function of state on disk* becomes its own Duty-6 dimension, because Reviewer C's procedure-gap scope does not reach a single state-derivable decision embedded in law text. J's test is T1 state-derivable / T2 a tool already touches it / T3 the rule asks an agent to remember, derive, or re-check; a finding must name the tool half or HQ rejects it. Census updated: SKILL.md (Reviewers A–J + brain-scrub = ELEVEN), hq.md Duty 6 families + spawn set, README.md. Tool half dispatched to Toolsmith — LANDED — `oc-review-persist`'s `LENSES` whitelist (`:51`) now carries `J` and both case-globs are widened (`:255` `[A-J][0-9]`, `:256` `[A-J]`), so a J report persists.
- **BATTERY**: 168 PASS / 0 FAIL (receipt `tools/tests/battery-last.json`).

## v0.4.160 (2026-09-12) — The Window Now Names All Three of Its Phases

Owner ruling: *"Rename window to name all 3 phases."* The v0.4.157 phase law gave the night window a third phase but left the window's canonical name reading **"Batch Merge & Batch Harvest Window"** — two-thirds of the truth, and the very identifier the trigger law uses to name the window.

- **Canonical name is now `Batch Merge, Harvest & Issue Triage Window`** — one word per phase, in phase order: Batch Merge (Phase 1, fleet-wide rebase/sync) -> Batch Harvest (Phase 2, upstream PR waves) -> Issue Triage (Phase 3, idle-lane dispatch). Updated at BOTH law sites in `fleet-directives.md`: §Cadence & Trigger Law item 1 (the SOLE-trigger sentence) and the Nighttime heading, item 3.
- **Closes the v0.4.157 open cosmetic item.** That entry deferred the rename pending an owner ruling and is superseded by this one; the v0.4.157 section is left as-is because it records what was true at that release.
- **Scope is the law text ONLY.** No command, trigger, phase procedure, classification bucket, or exit line changed — a lane can now see the window's full extent from its name alone, which is the point of the ruling.
- **BATTERY**: 168 PASS / 0 FAIL (receipt `tools/tests/battery-last.json`).

## v0.4.159 (2026-09-12) — The Law Prescribed Two Writes for One Adoption

Two independent lanes reported the same defect against the canonical reload instruction: it told lanes to ack twice.

- **NEW LAW — `--ack` IS the ack; never prescribe a second `oc-ledger ack` after it (`fleet-directives.md`, `editor.md` §Mid-cycle skill drift).** `oc-drift-check --ack` delegates to `oc-ledger ack` (`tools/oc-drift-check:78`), so a reload line reading "…then STAMP oc-ledger ack" ordered a SECOND row for ONE adoption. Fleet-wide and chronic — duplicate `(uuid, version)` pairs. State was never harmed (`last_acked` is idempotent on the same version) — the cost is permanent ledger noise on EVERY version bump, inflating the ack-row count an auditor reads. **Stamp `oc-ledger ack <uuid> <new-version>` ONLY when drift-check ran WITHOUT `--ack`.** **CORRECTED in v0.4.163 (ledger audit):** this entry first said "20+ lanes going back to 0.4.143: lane `1a63f103` n=3717/3718 two seconds apart, `d18ce16a` n=3713/3714, `61161247` and `462181e9` ×3, `127429e6` ×2". Measured: **68 duplicate groups across 27 lanes, 75 extra rows, going back to 0.4.118**; the mechanism is a **RE-ACK** (median gap 16 min; 0.4.137's 23 lanes median 3.6 h; only 19/68 within 5 min) — the tight 2 s pair `1a63f103` n=3717/3718 is the exception, not the class — and n=3713/3714 were written by `d5863180`, not `d18ce16a`. Heaviest: `61161247`, `462181e9`, `d5863180` ×5; `aaa8d8ae`, `2fbfb2f8`, `127429e6`, `7e1ebbb6` ×4. **CLOSED** by the M2-4 idempotent re-ack guard (`a36224ad`, 2026-09-12 15:50:14Z) — zero duplicate rows since (latest n=3800 @ 11:09:03Z).
- **The canonical reload receipt, named (closes the v0.4.156/v0.4.157 shape conflict).** The receipt for a reload is the single `oc-ledger ack` row — written once, by `--ack` if it was passed, otherwise by the hand-stamp. Two consecutive briefs specified different shapes (v0.4.156 "a ledger note row is the receipt"; v0.4.157 "Stamp `oc-ledger ack`"), which left lanes unable to tell which was canonical.
- **Not a defect in `oc-notify-fanout`.** The auto-appended RELOAD line (`tools/oc-notify-fanout:506`, "ACK after drift-check") is CORRECT and needed no change — only the hand-authored law text prescribed the second write.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.158 (2026-09-12) — The Sync Door Is Guarded; the Plain-Git Door Is Not

Two tool changes land with fleet-wide blast radius (every lane's `sync` and every post-swap recovery), plus the law line for the door they do NOT guard.

- **`oc-ledger sync` REFUSES rather than sweeping unrelated dirty paths (stray-guard, Toolsmith `219d5f70`).** `rc 7`, and it NAMES the offending paths; `--allow-sweep` is the explicit consent that preserves the v0.4.63 full-tree guarantee (a bump tag must never point at a tree missing payload). Closes the silent-stray class on the sync door: `20c8df4f` (HQ's v0.4.156 bump carried another lane's dirty `battery-last.json`), `fda12336`, `28f7ef41`. Same commit fixed a latent bug — the swept-report filter had never matched (porcelain emits a ONE-char status for a worktree modification, so the old idiom tested `^(.. )?` and missed), which is why SKILL.md/CHANGELOG.md were reported as "PAYLOAD SWEPT" on every sync. Selftest 212 → 215, negative control 215 → 212.
- **`oc-deploy recover-receipt --run/--sha` now SELECT the journal they name (Toolsmith `7e6c83f6`).** A selector matching nothing refuses `rc 2` instead of falling back to the newest truncated journal and reporting a COMPLETED swap as "the swap never installed" — a false negative that could tempt a re-run of a swap that already succeeded. Selftest 275 → 281, negative control 281 → 277.
- **NEW LAW — staging is not path-safe on an already-dirty path (`fleet-directives.md`).** Live incident: the owner's commit `13cd8423` @09:51:12Z carries Triage's uncommitted v0.4.157 Phase 3 law text, because `git add fleet-directives.md` was run while that file was ALREADY dirty — the edit was HQ's (one row), the sweep was not. The stray-guard above closes the `sync` door; **plain git has no guard**, and `git commit --only <path>` limits the commit to named PATHS but does not make a dirty PATH safe. Check `git status --porcelain <path>` in the same turn you stage.
- **Live evidence the guard works, not just its selftest.** Triage's v0.4.157 sync was REFUSED `rc 7` at 09:58:28Z (n=3704), naming `tools/oc-deploy` dirty (+110 lines, Toolsmith's uncommitted selector-mode work). The lane deliberately did NOT reach for `--allow-sweep` — the right call, and the reason the v0.4.157 tag carries only Phase 3 rather than mis-provenancing another actor's payload.
- **Fleet fact correction — `origin` and `mirror2` are ONE repository** (`leshchenko1979/opencrabs-skill`), differing only in transport (HTTPS vs SSH). The "push to both remotes" ritual buys NO second copy: after `git push mirror2 main` succeeds, `git push origin main` reports `Everything up-to-date` and both `ls-remote` HEAD queries return the same sha. Recorded in `tools/RC-CONTRACT.md` (`4e5ec206`) so nobody counts it as redundancy.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.157 (2026-09-12) — Phase 3: the Night Shift Now Ends With Idle Lanes Holding Work

Owner order: *"We need to add another phase to night shift - triaging open issues to idle editors."* The window previously ended at harvest; editors began the daytime window with whatever they had left over. It now CLOSES by filling idle lanes.

- **New phase — §Phase 3, Idle-Lane Issue Triage** (`fleet-directives.md`), superseding the three-line v0.4.143 stub. Position: the CLOSING phase of the operator-initiated window, covered by the window's trigger — NOT a new command. Owner: Triage (v0.4.143 allocation authority + Duty T3 + Duty T5).
- **Four classification buckets** — CLAIMED (open claim-ref → no action) · PARKED (owner standdown → never re-ignite) · UNVETTABLE (no acceptance criteria → park with the reason) · DISPATCHABLE (unclaimed AND vetted).
- **Reuse-first is mandatory; expansion is the measured exception.** Capacity comes from `oc-ledger roster --live --role editor`; new editors are created only up to the measured shortfall, and each creation records the count that justified it. This folds the owner's 2026-09-11 lane-reuse order into the phase instead of leaving two rules that disagree.
- **Verify-unclaimed FIRST, before any dispatch** (PHOP stage 2) — the two recorded violations (#106, #107, both already held when a fan-out routed them) are cited in the law as the reason it is not optional.
- **LOAD-BEARING — the overnight design-gate contract.** A dispatched editor produces analysis + design and **PARKS at the owner design gate**; it MUST NOT open `/goal`. The v0.4.149 autonomous-goal mandate begins only after the owner confirms the design, so an owner-absent window cannot push work past that gate. This is what makes the phase safe to run while the operator sleeps.
- **Exit line** — `triaged=N · dispatched=M · expanded=K · parked=P · waiting=0`, the L2 shift shape: any non-zero `waiting` means the phase is not done, and unclosed candidates roll to the next cycle.
- **Cadence section updated** — the Nighttime phase list now names Batch Issue Triage as the window's third phase.
- **Duty T5 updated** (`triage.md`) — gains the night-shift phase variant and a pointer to the full procedure.
- **Open cosmetic item (owner's call, non-blocking):** the window's canonical name — "Batch Merge & Batch Harvest Window" — no longer names its third phase. Renaming it is churn across several references, so the name is unchanged pending an owner ruling.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.156 (2026-09-12) — The Proposal Channel Is Live; the Interim Workaround Is Retired

The `proposal` kind landed in the ledger, so the interim `kind=note` workaround that the v0.4.154/155 text prescribed is **retired** — following it now recreates the dead channel in the opposite direction: a lane writing proposals as `note` is invisible to `events --kind proposal`, which is the audit verb.

- **`proposal` is an admitted kind — verified live, not read from source.** Toolsmith's `be7bfd09` (09:16:39Z) added it to `KINDS` (`tools/oc-ledger:130`) with a selftest case (`:735-741`), pushed to `origin` **and** `mirror2` (all three refs agree). HQ's own probe on a **fixture copy** of the real ledger (real ledger untouched): `oc-ledger stamp proposal "…"` → `rc=0`, `stamped n=3643 kind=proposal (read-back ok)`, and `events --kind proposal` returned the row. Reported independently by two lanes (`c2ba4ef2`, `aaa8d8ae`).
- **Interim workaround RETIRED.** The `duty4-proposal` note-mirror existed only in a fanout **brief body** — `grep -rn 'duty4'` across the skill tree returns 0 hits outside the cycle directories — so it was never law. `editor.md:69`, `hq.md:137`, and `fleet-directives.md` all name `oc-ledger stamp proposal`, which now works. **Do NOT mirror proposals as `note`.**
- **Window-safe read added to the Duty-4 closure (`hq.md`).** `events` counts `--n` rows back from the NEWEST (default 20, `tools/oc-ledger:1382`). A **kind-filtered** read is safe — the filter runs BEFORE windowing and cannot be starved by unrelated rows. A **marker-prefix** read over `--kind note` is NOT: by cycle close the `note` tail no longer holds the proposals and `rc=0` **with** rows reads as "none submitted" — the false-negative class, reported by lane `1a63f103`, who hit it. Historical note-mirrors (n=3555/3556/3557/3558) need a sufficient window (`--n 500 | grep duty4-proposal`, or `--since <cycle-start>`); disk channel #1 (`ls $REVIEW_DIR/proposals/`) stays authoritative.
- **Law extended — prescribing text must be RETIRED when the named defect is fixed** (`fleet-directives.md`, §Law text may name only commands that EXIST). Third instance of the family in one day: the enum fix landed **one minute before** the brief that described the enum as broken, so the brief's own workaround became the defect. Defect-board row marked **RESOLVED**.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.155 (2026-09-12) — The Reload Line's Ack Verb Is Positional; Fanout Waves Die Mid-Flight

A lane (`127429e6`, editor · ai-antispam) reported that the **mandatory ACK line in the v0.4.152 reload brief was not runnable as written**, and verification found the failure was in HQ-authored brief text plus two unreported delivery defects behind it:

- **Malformed ack invocation (HQ authoring defect).** The brief carried `oc-ledger ack --by <uuid> 0.4.152` → `rc 2` `uuid shape invalid (want 8-4-4-4-12 hex): '--by'`. `ack` is **positional** (`ack <uuid> <0.N.N version> [--at <ts>]`, `tools/oc-ledger:48/420`); `--by` is a flag of **`stamp`** (`tools/oc-ledger:10`). `grep -rn 'ack --by'` across the skill tree returns **0 hits**, so the form was invented in the brief body, not in any tool template — `oc-notify-fanout` auto-appends the correct RELOAD line (`tools/oc-notify-fanout:447`). **Law (`fleet-directives.md` §Skill-change notifies):** the ack verb is quoted exactly and is never hand-written into a brief body. Lane recovered with the correct form (`oc-ledger ack <uuid> 0.4.153`, `n=3576`).
- **Fanout waves die mid-flight and report success (tool defect → Toolsmith).** Both real waves today ended `exit=143` (`signal TERM`) in `tools.log` — the v0.4.150 wave after **529.9s** (delivered to **9** of its targets) and the v0.4.154 wave after **211.2s** (delivered to **1**). The wave is serial with a per-send timeout, so a large roster cannot finish inside the caller's budget; the `.sent` receipt is the only evidence of how far it got, and **partial delivery is not surfaced as failure**. `run/wave-<id>.sent` makes the wave resumable — re-running the same wave skips already-sent lanes and continues.
- **Retired workers are still fanout targets (tool defect → Toolsmith).** `e756b84b` (`retired_compiler`) appears in **both** `.sent` receipts — a retired roster row receives skill-change briefs it can never act on.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.154 (2026-09-12) — Law Text Names Only Commands That Exist

Two verified skill-law defects, both found by editors who ran the prescribed command and got a usage error instead of the promised recovery:

- **`oc-ship-chain --resume` did not exist.** `editor.md` Failure Mode 4 ("Daemon Bounce Task Interruption") prescribed `--resume` for post-bounce recovery; the tool carries 11 case arms and **0** occurrences of the flag — the arg loop's catch-all dies `unknown arg` rc=2. Corrected to the real recovery: read `deployed.sha`, and if the chain died before the swap, **re-run the same chain with `--gated-run <id>`** (reusing the GREEN gate run whose job name pins your sha). The row's cgroup claim was corrected too: only the `poll --execute` path hands Phase B to a transient `systemd-run` unit, so a **direct** `swap-execute` runs in the caller's cgroup and can be killed by the restart it performs.
- **`oc-ledger stamp proposal` could never yield a row — RESOLVED the same day.** The `KINDS` enum omitted `proposal` (stamp rc=2, `events --kind proposal` rc=1 empty), while four citations prescribed it (`editor.md:69`, `fleet-directives.md`, `hq.md:137`, `CHANGELOG.md:55`). Resolution = admit the kind, per precedent (`shipchain` v1.2, `roster-retire` v1.3). **Toolsmith landed it in `be7bfd09` (09:16:39Z) — the channel is live; see v0.4.156.** Do NOT apply the interim `kind=note` mirror described in the v0.4.155 fanout brief.
- **New law (`fleet-directives.md`, tool-problem routing section):** law text may name only commands that **exist**, verified against the tool's own surface before it ships — `grep -c -- '<flag>' <tool>` for a flag, the `KINDS` / case-arm list for a verb. HQ owns the law text; Toolsmith owns the tool surface when the verb should exist rather than be removed.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.153 (2026-09-12) — Reading a Delivery Verdict: `no wake observed` Is Not a Failure

Toolsmith correction 2026-09-12, on its own v0.4.151 handover. Two facts, both verified against source by the reporter:

- **A `session_notify` confirm verdict of `routed … no wake was observed within 10s` means the TARGET IS MID-TURN**, not that the message was dropped: it injects at the target's next tool-loop boundary. A re-send on that verdict is a duplicate, not a fix.
- **`session-notify.journal` absence is NOT evidence of failure.** `journal_line` has exactly one caller — `src/cli/session_notify.rs:344` — so the journal records the **CLI** path only; in-agent `session_notify` tool calls (`src/brain/tools/subagent/notify.rs`) never journal. Confirm delivery from the daemon log (`Stamped N notify receipt(s) injected for session <uuid>`) before declaring anything lost.

Canon: `fleet-directives.md` §Cross-lane message delivery discipline. Origin: the reporter read its own confirm verdict as "did not wake you", re-sent a handover that had already been delivered, and then read the source before filing the journal gap as a defect — the check that kept it off the defect board.

- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.152 (2026-09-12) — Park-Don't-Chase, Guard-Flag Escalation & Attribution/Goal Hygiene

Owner order 2026-09-12 ~08:0xZ, on the post-night-shift findings report: *"I saw you stranded on waiting for a smoke — that shouldn't happen, no human smoke will be confirmed as I was away. Why not just leave these PRs for the next cycle?"* — "Codify the six amendments". All six codified; a seventh finding (tool-description probes) landed in `SKILL.md` §Test ontology.

- **§Owner-Dependent Smoke Legs — Park, Don't Chase (`fleet-directives.md`; `editor.md` Phase 6b; `editor-upstream-pr.md` Phase 7c; `SKILL.md` §Test ontology)** — four clauses:
  - **L1 park-don't-chase**: a leg only the OWNER can satisfy (visual pass, tap, eye-confirm) is NEVER a blocking gate. Stamp the provable legs, append a `PARKED-OWNER-EYE` row naming the owner action + packaging sha, RELEASE the lane. Parking is a lane-release, not a hold — it does not contradict NO-HOLD, it is the mechanism that keeps a lane OUT of a waiting state. Origin: a verdict-only lane (#155) idled ~4 h on an owner visual pass, and the wait bought nothing (no PR was owed — the candidate was excluded from harvest).
  - **L2 shift exit condition**: a shift is complete only when every workstream is RECEIPTED or explicitly PARKED; "waiting for X" is not terminal. Report `receipted=N · parked=M · waiting=0`; unclosed candidates roll to the next cycle, never chased across it.
  - **L3 owner verdicts are explicit AND post-hoc**: a passing remark made mid-flight is not a verdict. Worked example — the owner's "Smoke passed" landed 16 s after their own discard and 3 m 17 s before the review subagent finished, certifying a defect that did not yet exist; the PASS was revoked (row 87 → row 90). Ambiguous remark → record `OWNER-REMARK (not a verdict)`, leave the leg OPEN/PARKED.
  - **L4 packaging-sha stamps**: a `smoke-verdicts.log` row's `sha=` MUST be the packaging tip under test, never an ancestor (the #172 row cited `3b095f27` while the tip was `f45d6323` — it never covered the candidate). Superseded rows are appended over, never edited.
- **§Guard-Flag Escalation Law (`fleet-directives.md`; `editor-upstream-pr.md` Phase 7c step 4)** — a guard flag is an EVENT, not a log line: `phantom_blocked` / receipt-guard / attribution refusals MUST be routed same-turn to the affected lane AND HQ with the guard's machine-readable reason. Origin: the #172 lane announced *"PR #1514 Filed & Smoked!"* at 03:44Z; the guard correctly set `phantom_blocked=1` and nothing escalated it — **~3 h** lost before manual re-verification (`gh pr view 1514` → could not resolve) caught it. A PR number is not FILED until a same-turn tool output names it.
- **§Attribution & Goal Hygiene (`fleet-directives.md`)** — A1: every `oc-*` call exports `OC_ACTOR`; a tool that ALREADY knows the owning session (`oc-ship-chain` inside a chain) MUST default the actor to it rather than emit `(unattributed …)` — an unattributed row is a TOOL defect, dispatched to Toolsmith (34 such rows on 2026-09-12). Stamp as your ROSTER ROLE (a factory label trips `unrostered-actor`). A2: a shift-length `/goal` must carry a turn budget covering the shift, and its death MUST notify — goal `eefd9a20` expired at turn 20 (03:18Z) and the shift ran ~4.5 h more with no judge while reports still described the clock as running.
- **`SKILL.md` §Test ontology — tool-description changes have NO log-based probe** (lane 1a63f103, #168): the daemon's provider log records tool ARGS only (`[TOOL_ACCUM] name=bash`), never tool schemas, so no log line can prove a description string was served — every occurrence is self-contamination from the prober's own commands. Smoke `Tool::description()`/`input_schema()` changes with **binary strings on the running exe + shipped constants in source**. A "live schema served" receipt from the log is a FALSE receipt.
- **BATTERY**: 168 PASS / 0 FAIL (receipt `tools/tests/battery-last.json`).

## v0.4.151 (2026-09-12) — Rebase-Aware Lineage Guard (post-rewrite equivalent swaps)

- **`tools/oc-deploy` lineage guard is rebase-aware (`tools/oc-deploy`, `tools/oc-ship-chain`, `tools/RC-CONTRACT.md`)**: after a fork-main rebase the deployed sha is orphaned — it is no longer an ancestor of `main` — and the pre-v0.4.151 guard refused **EVERY** post-rewrite swap with `non-monotonic-swap`. **The blast radius was fleet-wide, not a one-off:** lane `2fbfb2f8` hit it 10× in a single chain (07:39:22→07:44:01Z) and another lane stamped the same blocker (n=3508). The guard now classifies the case as `rewrite-equivalent-swap` when the incoming lineage carries the deployed change under a new sha (patch-id match), journals the rewritten twin sha, and admits the swap; a genuinely-ABSENT change still refuses unless the audited `--allow-rewritten-lineage` override is passed with a mandatory justification.
- **`oc-deploy lineage-check`** — new read-only verdict verb (`--prev/--sha/--repo/--json`) returning `ok` / `rewritten` / `absent` without touching gate state.
- **`oc-ship-chain` — a guard refusal surfaces as `rc 6`**: the runbook is **re-run the same chain leg** (the swap is accepted as `rewrite-equivalent-swap`); **never hand-edit `deployed.sha`** to re-point around a refusal. Canon: `fleet-directives.md §Post-Rewrite Swap Recovery`.
- **Selftest coverage**: +33 assertions (220 → 253, FAIL 0) against a REAL fixture repo — the old `aaaa…`/`bbbb…` fixtures exercised only the guard's SKIP path, so the guard had **zero** real coverage before this.
- **Provenance note**: the HQ law commit `ce7c928a` (v0.4.150) swept in an already-staged Toolsmith `tools/` batch. The content was coherent and already pushed, so shared history was not rewritten; it is recorded here instead.
- **BATTERY**: 168 PASS / 0 FAIL.

## v0.4.150 (2026-09-12) — Design-Gate Precondition on the Autonomous Editor Goal

- **Design-gate precondition (`editor.md` Phase 1 Step 0, `fleet-directives.md §Autonomous Editor Goal & Continuous Phase Execution Law`)**: The autonomous `/goal follow the skill until the smoke test phase` is issued **ONLY AFTER the owner has confirmed the design** (owner design gate, v0.4.128). Until that confirmation lands the editor stays in the design/approval phase; an early goal would carry it past the very gate that requires owner approval BEFORE code. Fixed sequence: design → owner confirms → `/goal` → continuous execution through Phase 6b. Amends v0.4.149, whose wording said "immediately upon claiming an issue".
- **BATTERY**: 168 PASS / 0 FAIL (receipt `tools/tests/battery-last.json`, 2026-09-12T07:49:35Z).

## v0.4.149 (2026-09-12) — Autonomous Editor Goal Mandate & Full-Gate Pre-PR Testing Law

- **Autonomous Editor Goal Mandate (`editor.md`, `fleet-directives.md`)**: Mandated that upon claiming/waking on an issue, editors MUST execute `/goal follow the skill until the smoke test phase` (owner order 2026-09-12). Closes the premature-stop failure mode: editors drive continuously through Phase 1 to Phase 6b smoke testing on the live swapped binary without stopping after code edits or intermediate ship legs.
- **Full-Gate Pre-PR Testing Law (`editor-upstream-pr.md`, `fleet-directives.md`)**: Mandated that final pre-PR verification MUST use the full gate (`cargo test --all-features` + fmt + clippy) via `oc-prchecks wait <branch>` or `oc-prchecks <branch>` without `--fast`. The `--fast` flag remains restricted to internal daytime merge cycles (`oc-ship-chain`).
- **BATTERY**: 166 PASS / 0 FAIL.

## v0.4.148 (2026-09-12) — Carrier Build Coalescence, Ancestry Matching & Host Swap Mutex

- **Carrier Concurrency & Coalescence Law (`fleet-directives.md`, `editor.md`)**: Codified that carrier workflow `ci/quick-build-linux` concurrency coalesces pending queued builds. Editors push fast-forwarded commits immediately without pre-dispatch lock serialization.
- **Ancestry-Aware Carrier Matching (`tools/oc-deploy`, `tools/RC-CONTRACT.md`)**: `oc-deploy ship/poll` accepts descendant builds via `git merge-base --is-ancestor "$SHA" "$CAND_SHA"`. When coalesced carrier runs finish GREEN on a descendant commit, all included ancestors are recognized as deployed.
- **Host Swap Mutex & Lineage Monotonicity (`tools/oc-deploy`)**: Wrapped `swap-execute` in `flock -x $STATE_DIR/host-swap.lock` and added `git merge-base --is-ancestor "$PREV_SHA" "$SHA"` verification to prevent stale binary overwrites.
- **Fast-Forward Merge Serialization (`tools/oc-ship-chain`)**: Added `ship.lock` around Leg 3 to serialize concurrent local fork-main merges cleanly.
- **BATTERY**: 166 PASS / 0 FAIL.

## v0.4.145 (2026-09-11) — Unified Event Capture Matrix, Split-Gate Ship Pipeline & Failure Recovery Protocol

- **Unified Event Capture Matrix (`fleet-directives.md`)**: Codified routing law separating urgent anomalies (Toolsmith direct notification, GitHub fork issues, Alexey) from batched self-improvement (Duty 4 review proposals and Idea Box intake persisted directly to disk/ledger without flooding HQ).
- **Split-Gate Ship Pipeline & Merge-First Velocity (`fleet-directives.md`, `editor.md`)**: Codified split-gate CI strategy where pre-swap carrier builds focus on artifact compilation and sanity validation, deferring the full `cargo test` triad (24.7m) to either pre-PR gates or asynchronous post-merge suites, reducing ship cycle turnaround from ~38m to ~13m.
- **Automated In-Tool Rebase Mechanics & Failure Protocol (`editor.md`)**: Codified failure modes and recovery protocol for `oc-ship-chain` and `oc-deploy`, delegating mechanical rebase on non-FF (`rc=5`) into tool automation and providing clear recovery steps for CI test failures, carrier compile errors, and binary swap regressions.
- **Cycle 5 Review Improvements & Tool Suite Fixes**: Integrated `oc-deploy status [--json]`, `oc-ledger` verb suggestion hints, `oc-roster` strict `--role` rejection, `oc-watcher-audit` CLI tool with full selftests, and purged stale lock/sent artifacts.
- **BATTERY**: 166 PASS / 0 FAIL.

## v0.4.144 (2026-09-11) — Zero Session Notify for Duty 4 & Direct Persistence

- **Zero Session Notify Law for Duty 4 Proposals (`hq.md`, `editor.md`)**: Codified that workers do NOT submit Duty 4 skill review proposals via `session_notify` to HQ. Inbound proposal notifications flood HQ's conversational context, accelerate memory compaction, and create hub contention. Proposals are persisted directly to disk at `~/.opencrabs/profiles/ops/opencrabs-dev/reviews/<cycle-id>/proposals/<session-uuid>.md` or appended to the ledger via `oc-ledger stamp proposal`.
- **Mechanical Duty 4 Closure (`hq.md`)**: HQ assesses duty completion through on-disk file discovery (`ls $REVIEW_DIR/proposals/`) and ledger query (`oc-ledger events --kind proposal`), bounded by quorum or window cutoff, batching review ingestion into a single turn before stamping the cadence boundary.
- **BATTERY**: 162 PASS / 0 FAIL.

## v0.4.143 (2026-09-11) — Post-Harvest Issue Allocation, Worktree Indexing Retirement & CI Throttling

- **Post-Harvest Issue Assignment & Lane Expansion (`fleet-directives.md`)**: Codified automated issue assignment sweep following nightly harvest batches. Unassigned vetted issues are allocated to idle editor lanes, expanding lane capacity as needed so work is queued for daytime execution.
- **Worktree Indexing Retirement (`tools/oc-wt`, `editor.md`, `fleet-directives.md`)**: Removed chained `the retired worktree indexer` execution from `tools/oc-wt add`. Code structure exploration routes to centralized daemon `memory_search(scope="external")`. Cleaned 69 redundant `.codegraph` directories (~5.8 GB reclaimed).
- **CI Polling & Watcher Throttling (`tools/oc-prchecks`, `editor.md`, `fleet-directives.md`)**: Bumped `tools/oc-prchecks` default `POLL` from 15s to 30s and `RESOLVE_POLL` from 5s to 15s. Mandated `--interval 30` for any raw `gh run watch` command.
- **BATTERY**: 162 PASS / 0 FAIL.

## v0.4.142 (2026-09-11)

- **Daytime-Editing & Nighttime-Batch-Sync Cadence (fleet-directives.md)**: Codified operator workflow separating daytime design/smoke approvals from nighttime batch upstream merges and consolidated harvest PR runs.
- **Atomic-Write Executable Bit Law (fleet-directives.md)**: Mandatory `chmod --reference="$target" "$temp"` on tempfile writes to prevent stripped `+x` modes.
- **Unharvested Prerequisite Blocker Row (editor-upstream-pr.md)**: Phase 7b blocker row codifying hold on dependent harvest filings until prerequisite issues land upstream.
- **BATTERY**: 162 PASS / 0 FAIL.

## v0.4.141 (2026-09-11, runbook step 7 — derive the cut from the TARGET base)

- **RUNBOOK step 7 CORRECTED (second correction in an hour) — the pending count must be measured against the TARGET base, not the old fork main.** v0.4.140 added a zero-pending test keyed on `<old-main>..<branch>`, but that range counts commits the NEW base already contains, so it reports a large number for a branch that is in fact fully absorbed — the test never fires and the lane derives a cut it should not derive. Lane `d18ce16a` found it on `leshchenko1979/feat/notify-harvest` (`bb8dc6ff`): `git rev-list --count 7432e538..bb8dc6ff` = **12** (case-3 test does NOT fire), while `git rev-list --count origin/main..bb8dc6ff` = **0** — fully absorbed into the new base, nothing to replay. Following the law's own derivation gave `CUT=7fcf430b` and `git rebase --onto origin/main 7fcf430b` → **rc 1, CONFLICT in 4 files** — the exact "commit wall / mass conflicts" signature the law warns about, on a branch with zero pending commits. Naive and derived forms are identical for that shape, so deriving from old main is not merely redundant, it is unsafe. **Corrected law: test `git rev-list --count origin/main..<lane-branch>` FIRST; 0 → absorbed, skip the rebase; >0 → cut at the parent of the oldest of THAT range.** Re-verified on three live branches before writing: `fix/111-notify-queue-drain` `93f90058` target **2** vs old-main range **121**; `fix/132-reflow-rich-path` `12d25260` target **0** vs **105**; `plan-card-md-media` `942fa18c` target **1** vs **120**. This single rule subsumes both the over-replay case (v0.4.139) and the zero-pending case (v0.4.140).
- **RUNBOOK step 7 — the "no rebase in progress" check was itself wrong in a linked worktree.** `ls .git/rebase-*` returns a FALSE negative there: in a linked worktree `.git` is a FILE pointing at the real gitdir, so the glob is "not a directory" and a naive check reads as "clean". Lane `d18ce16a` reproduced it (`/root/oc-work/harvest-62`). Correct check: `git rev-parse --git-path rebase-merge` (works in both layouts) or the `git status` header. A lane trusting the naive check would resume mid-rebase — which the brief itself calls worse than not rebasing.
- **`editor.md` — `fmt-clean ≠ compiles`; audit CALL-SITE SHAPE before chaining.** There is no local compile path (box law), so `rustfmt --edition 2024 --check` proves formatting only and the first real compile is a full CI gate dispatch. Lane `facd50af` (2026-09-11, #111) ran the fmt pre-pass clean, chained, and burned a whole gate budget on two mechanical errors of its own: `E0425` (calling `super::work_status::reconcile_stale_commands()` — a free-fn path for a function that is an associated fn on `WorkStatus`) and `E0507` (`drop(self.dir)` moving a field out of `&mut self` inside a `Drop` impl). New pre-chain guard added: cross-check every new/changed call site against the callee's real definition — free fn vs associated fn, the receiver (`&self` / `&mut self` / none), and `Drop`-impl move rules (`Option::take()`). Includes the box-law tell: `which cargo` prints a path but running it prints `BLOCKED` — *the presence of a path is not evidence of a toolchain*.
- **BATTERY**: 161 PASS / 0 FAIL on the working tree (docs-only release — nothing here touches the tools; the count differs from v0.4.140's 162 because the tree also carried another lane's in-flight `oc-snap` guard edits, which this release does not ship).

## v0.4.140 (2026-09-11, runbook step 7 — the zero-pending lane case)

- **RUNBOOK step 7 — THIRD CASE added: a lane with ZERO pending commits.** The v0.4.139 derivation (`CUT="$(git rev-list --reverse <old-main>..<branch> | head -1)^"`) assumes at least one unmerged commit. A lane already fully absorbed into old fork main has an EMPTY range, so `head -1` yields nothing and `CUT` becomes the bare `^` — `git rev-parse "^"` is **rc 128** (`fatal: ambiguous argument '^'`). The documented ancestor fallback does not cover it either: the old sha is still not an ancestor of the new base. Reported by lane `2fbfb2f8` (#132) with full receipts, every number reproduced first-hand: pre-rebase head `299d1c72`, `git rev-list --count 7432e538..299d1c72` = **0**, `head -1` **empty**, `rev-parse "^"` **rc 128**, `git merge-base --is-ancestor 7432e538 12d25260` **rc 1**, and `299d1c72` proven an ancestor of old main (the lane was genuinely fully merged). **The fix is to TEST FIRST** — `git rev-list --count <old-main>..<branch>`; on 0 there is no delta to replay and the migration is a pointer move: `git rebase --onto origin/main <old-main> <branch>`. That is the SAME command the v0.4.139 failure signature warns about — it over-replays only when the lane DOES have pending commits, which is exactly why the count test must come first. In the report's case the lane's own rebase had already completed correctly (`299d1c72 -> 12d25260`, `dirty=0`, no conflicts) before the report landed.
- **BATTERY**: 162 PASS / 0 FAIL.

## v0.4.139 (2026-09-11, lane-reported corrections — cut point, dead remedy, in-flight write hazard)

- **RUNBOOK step 7 CORRECTED — the lane-migration cut point was wrong, and it failed SILENTLY.** The step shipped in v0.4.138 said `git rebase --onto origin/main <old-fork-main-sha> <lane-branch>`. After a cutover the old fork-main sha is **no longer an ancestor** of the new base, so that form replays the ENTIRE fork history rather than the lane's pending delta. Lane `facd50af` hit it for real: their branch was cut from `ff234125`, but old main `7432e538` had already absorbed 5 of their 6 commits — so the documented form offered **220 commits** where exactly **1** was pending (`12d25260..branch` = 1 vs `ff234125..branch` = 220), presenting as a commit wall and mass conflicts, i.e. "the lane is a mess" rather than "the cut point is wrong". **The fix is to DERIVE the cut point from the parent of the OLDEST UNMERGED commit** (`git log --oneline <old-main>..<branch>`, then `git rebase --onto origin/main "$(git rev-list --reverse <old-main>..<branch> | head -1)^" <branch>`); the corrected form replayed 1 commit → `e89f2033`, `dirty=0`, no conflicts. The rare fallback is documented: if `git merge-base --is-ancestor <old-main> origin/main` holds, the old simple form is equivalent. Confirmed in a hermetic repro (`/tmp/rebasecut2.sh`): branch-time tip → **6** replayed, old-main tip → **1**, derived cut → **1**, and the old shas proven gone from the new history.
- **`editor.md` exit-5 remedy was DEAD LAW.** The NON-FF lane action cited `tools/oc-rebase-safety run ~/oc-wt-<task> origin/main`. That subcommand **does not exist** — the tool's dispatch has exactly two arms (`overlap`, `audit`) and anything else is **rc 2 usage**; it is READ-ONLY by design (git plumbing only, "never merges, rebases, or writes anything"). A lane that hit `oc-ship-chain` exit 5 and followed the doc verbatim got a usage error, not a rebase, and had to improvise (lane `6cd8175f`, #149: chain exit 5 when fork main moved `12d25260` → `87ac2aa0` under it; they rebased manually and lost nothing). Replaced with the manual sequence that actually works — `git -C ~/oc-wt-<task> fetch origin` → `rebase origin/main` → `push --force-with-lease origin <branch>` — plus an explicit warning that `oc-rebase-safety` is NOT the remedy, so the next lane does not re-derive it.
- **NEW LAW — in-flight script rewrite is a hazard; write `tools/` atomically.** `bash` reads a running script from disk by byte offset, so an in-place rewrite (truncate + write — what both `write_file` and `edit_file` do, inode preserved) makes the interpreter resume mid-line in the NEW content and execute whatever fragment is there. It is **silent and yields a false-success rc**: CHAIN `87ac2aa0` (#150) reached LEG1 gate pre-verified GREEN (ledger n=2836) and died before LEG2 (ledger n=2846) with `oc-ship-chain: line 284: g: command not found`, while the caller — piping through `tail` — read *tail's* rc and reported a successful chain. ~30 min of gate time lost. **Law: before writing ANY file under `tools/`, list in-flight invocations** (`ps -eo pid,etime,args | grep -E 'oc-ship-chain|oc-deploy|oc-prchecks|oc-job-verify' | grep -v grep`); any hit → do not write that file in place, or write a temp file **in the same directory** and `mv` it over the target, which replaces the directory entry so the running interpreter keeps reading the OLD inode. Not only an agent-edit hazard — issue #167 notes `git checkout` / `git pull` write working-tree files in place too, so a checkout mid-chain can kill a sibling's chain. Filed `leshchenko1979/opencrabs#167` (verified OPEN 2026-09-11T13:23:42Z); the tool-side fix (snapshot + re-exec, the four long-running tools only) is Toolsmith-owned, design signed off, deferred until the tree is quiet.
- **LEDGER HYGIENE — the `supervisor` fold swept the last live citation.** `workers-ledger.json`'s `_comment` still read *"Supervisor ledger: … Seeded 2026-08-26 by the supervisor … Updated per supervisor.md Duty 2"* — a rule pointer citing a file that no longer exists (`supervisor.md` is absent; the role file is `hq.md`, Duty 2 at line 61). Corrected to `HQ ledger` / `by HQ` / `per hq.md Duty 2` via the tool's own write path (`flock` → `jq --rawfile` → validate → `mv`). Proven surgical: with `_comment` deleted the rest of the ledger is byte-identical to the pre-edit backup (md5 `fb527119475210290fdfad84175dcce0` both sides), event count unchanged at 1647, and exactly the 2 lowercase `supervisor` tokens removed. The 156 remaining occurrences are historical event rows and are left as written — history is not rewritten.
- **BATTERY**: 162 PASS / 0 FAIL.

## v0.4.138 (2026-09-11, rebase sync model — governance rewrite, plan Task 8)

- **GOVERNANCE — the MERGE sync model is RETIRED for the REBASE model** (owner-approved transition 2026-09-11, plan "Fork Rebase Transition and Sync Workflow"). Fork main is rebased onto `adolfousier/main`: a small set of topical commits sits directly on upstream/main, and each sync is a rebase that DROPS the commits upstream has accepted, so the ahead counter reflects true pending delta and shrinks as PRs land. The 2026-09-02 "Land it" policy — and its "merge, never rebase/reset" rule — is void: it produced 31 merge commits and a 333-commit phantom ahead count. Force-push onto fork main is sanctioned ONLY via `--force-with-lease`, with the pre-cutover sha recorded in the ledger FIRST (rollback = force-with-lease back to it). `fleet-directives.md` §Remotes & sync; §Merge-resolution shape → **§Seam-resolution shape** (per-commit replay; the upstream-byte-exact principle and the owner [GATE] on keep-ours survive unchanged).
- **RUNBOOK REWRITTEN**: `upstream-merge-runbook.md` — the merge procedure replaced by the rebase procedure. **NEW step 0 = ROSTER GATE (blocking)**: the freeze list IS the derived in-progress roster (`oc-roster live` / `classify`), never a hand-assembled registry. Process numbering fixed (the old file jumped 6 → 8 — there was no step 7). The retired REBASE-PORT classification (absorbed / superseded / survivor) folded in as the live procedure rather than left as an appendix. New step 7 migrates lane branches (`rebase --onto` + unpause via `session_notify`).
- **THE MARKER COMMIT IS A STANDING ARTIFACT** (not a one-off remedy): rebase, synthesis and merge heads are unsigned BY CONSTRUCTION — they cannot carry a `Session-Id` trailer — so ORDER gate 4 refuses them and the chain exits **rc 6** on EVERY sync. Both occurrences now cited in the ruling: bare merge `d02f4e08` (2026-09-03, swap blocked exit 2 pre-install) and the atomic cutover head `12d25260` (2026-09-11, `oc-order-validate: UNSIGNED`, stranded main undeployed until marker `70b04864`). `fleet-directives.md` §Swap-head signature widened to rebase/synthesis/merge-derived binaries; "never dispatch a bare merge" → "never dispatch a bare (unsigned) head".
- **NEW DEPLOY STEP (runbook step 10)** — the sync is NOT complete when CI goes green. A cutover that stops at the force-push strands main undeployed while the live binary runs an older sha, which is exactly what happened 2026-09-11: `origin/main` = `12d25260` while `deployed.sha` = `c99a3c0f`. No sync step is "done" with main stranded.
- **CORRECTION — role resolution.** The plan instructed pointing role resolution at `oc-roster`; applied literally it would have broken Toolsmith dispatch fleet-wide. `oc-roster --role <role>` is **accepted and SILENTLY IGNORED** (rc 0, no stderr, unfiltered output — 1057 rows either way). The working verb is `oc-ledger roster --live --role <role>`. `editor.md:67` already carried the correct form and was left untouched; `triage.md` and `fleet-directives.md` corrected; the boundary documented in both files and in the SKILL.md tool table. Dispatched to Toolsmith (session 2fae1230) with the row-count receipts.
- **CORRECTION — phantom verb.** `oc-ledger roster-enroll` (cited in `fleet-directives.md` for editor enrollment) does not exist: rc 2, absent from the usage line. The real form is `oc-ledger enroll <uuid> <role> [--topic N] [--feature X]`.
- **CORRECTION — the rc register.** `editor.md`'s `oc-ship-chain` register documented only 0/4/5 and lumped 3/6 as "infra failure". Now complete: rc 2 usage, rc 3 dirty-checkout pre-flight, rc 4 gate/carrier RED **plus `--gated-run`/`--gated-sha` pre-verify failure**, rc 5 NON-FF, rc 6 infra/poll failure **OR the ORDER-gate UNSIGNED rejection** (with the explicit "read the message — if it says UNSIGNED, do not go hunting for a network problem" instruction), rc 7 gate still in flight after budget (with the do-NOT-re-dispatch warning).
- **CORRECTION — `gh run watch`.** The blanket ban is gone: raw `gh run watch` is the sanctioned resume form. What is banned is a hand-rolled `nohup` poller / sleep loop / custom background daemon. Paired with the **NO-VERDICT law**: a watcher that dies without a verdict is NO-VERDICT, never GREEN (editor lane 1a63f103: `oc-prchecks` died on a `fork: retry` storm and exited 0 with no verdict — a false-success shape). Any `fork: retry` / `run view … failed` / empty-verdict line means no verdict was obtained.
- **NEW LAW — the LEDGER is the ACK channel** (owner order 2026-09-11). For any wave whose ack contract is "confirm receipt" (freeze, unfreeze, skill-change reload, rebase notices), the ack is an `oc-ledger stamp note` row, NOT a `session_notify` reply; the sender reads acks once with `oc-ledger events --n N`. Origin: the unfreeze wave — 36 ACK rows from 17 lanes read in a single call, where notify replies would have been 36 interrupts of working lanes.
- **NEW SECTION — verification-discipline additions**: never trust a seam-resolution commit MESSAGE (diff the tree against `git merge-tree --write-tree <base> <ours> <theirs>`; a message claiming upstream-verbatim over our bytes is a silent semantic override); always record the literal COMMAND beside any control hash; a probe against a nonexistent path returns silence, not a verdict; shell verdicts are read first-hand, never through a pipe (the bash tool's shell is dash — `${PIPESTATUS[0]}` and `[[ ]]` die with `Bad substitution`, and `cmd | head; echo $?` reports head's rc); verification is scoped by load-bearing, and its value-add is the contradiction check.
- **DOCS**: SKILL.md gains an `oc-roster` row (verbs, the PHANTOM-exclusion safety property, and the `--role`-ignored warning); the `oc-ledger` row gains the `roster` verb; the PR-freeze law (v0.4.93) is now scope-qualified — it governs the filed UPSTREAM PR BRANCH only, and the sanctioned fork-main sync force-push never touches it, so the two do not conflict.
- **CHANGELOG CORRECTION (forward-only — the v0.4.135 block is immutable and stands as written).** The v0.4.135 entry states the `oc-waiter-sweep` cron job (`b0d7e0d3-1270-4fb5-8cb8-6c7161e90c34`) was "unscheduled and dismantled". **It was not** — the same job id was RETARGETED to `oc-roster-detached-sweep` and is live: enabled, `*/5 * * * *` (UTC), `Deliver: none`, silent by default, last run 2026-09-11 12:50 UTC. Also, `tools/oc-waiter-sweep` does not exist on disk (`tools/oc-waiter` does, 1372 B). Correction recorded here rather than by editing a shipped entry.
- **NOTE — count discrepancy**: the v0.4.137 entry records `oc-roster --selftest` as 31 checks; the live tool reports **44 passed, 0 failed**. Recorded, not re-written.
- **BATTERY**: 162 PASS / 0 FAIL.

## v0.4.137 (2026-09-11, derived in-progress roster — `oc-roster`)
- NEW TOOL: `tools/oc-roster` — the DERIVED in-progress roster (fork-rebase gate, plan step 1). Verbs `live | forum | claims | work | classify`, plus `--selftest` (31 checks, offline fixtures, no network, no live DB). It joins four independent signals — ledger `events[kind=claim]` (INTENT), `oc-wt list` dirty state (EVIDENCE), the session DB live roster (LIVENESS), forum bindings (SCOPE) — and classifies every row ACTIVE / IDLE / ORPHAN / UNKNOWN. It stores nothing; `live` is set-equal to the `oc-notify-fanout` v0.4.129 query.
- SAFETY: a claim author whose uuid the session DB has never seen is reported as a PHANTOM and excluded from the roster — a hand-assembled frankenstein id can never enter a freeze list (n=2221 class; incident n=2227). Live run: 57 rows, 28 ACTIVE / 16 IDLE / 0 ORPHAN / 13 UNKNOWN, 3 phantoms.
- DOCS: `editor.md` Toolsmith dispatch target now cites the real verb `oc-ledger roster --live --role toolsmith`; the bare `oc-ledger roster` it named was a phantom at authoring time.
- SWEPT (Toolsmith 2fae1230, stamped n=2598, selftest 167/0): `oc-ledger` gains the read verb it was missing — `events|tail [--n N] [--kind K] [--actor U] [--since T] [--json] [--full]`; rc 1 = NO-MATCH verdict. RC-CONTRACT.md documents it. Toolsmith committed it as `6064db0a` mid-flight, so this bump's tag is its first tagged home.
- BATTERY: 157 PASS / 0 FAIL.

## v0.4.136 (2026-09-11, upstream merge execution delegated to Triage)
- GOVERNANCE: delegated upstream merge execution to Triage (`triage.md`, `supervisor.md`, `SKILL.md`, `fleet-directives.md`, `upstream-merge-runbook.md`). Per owner order 2026-09-11 ("You should not do these merges - delegate to triage"), HQ does not execute merges; Triage executes the freeze check, performs the merge, resolves textual conflicts wholesale to upstream per upstream-merge-runbook.md, and coordinates seam adaptation passes.

## v0.4.135 (2026-09-10, detached command execution standard & waiter retirement)
- RETIREMENT: decommissioned `tools/oc-waiter` in favor of native detached bash execution (`background: true`).
- CRONS: unscheduled and dismantled `oc-waiter-sweep` cron job (`b0d7e0d3-1270-4fb5-8cb8-6c7161e90c34`).
- WORKFLOWS: updated `tools/oc-ship-chain` CLI docs and contracts for native `background: true` execution across Legs 1-3 sequentially.
- DOCS: purged 16-item CI-wait bureaucracy and One-Watcher law from `editor.md` and `supervisor.md`; added canonical `background: true` guidelines to `editor.md`, `supervisor.md`, `fleet-directives.md`, and `TOOLS.md`.
- GOVERNANCE: updated Toolsmith Duty S1 (`toolsmith.md`) and Triage Duty T4 (`triage.md`) checklists to remove `oc-waiter-sweep`.
- BATTERY: 154 PASS / 0 FAIL.

## v0.4.134 (2026-09-10, owner-approved front matter globs)
- METADATA: added `globs` coverage for the OpenCrabs source checkout, editor worktrees, and profile-scoped opencrabs-dev skill/state/project paths.
- Battery before bump: 158 PASS / 0 FAIL.

# opencrabs-dev — release history (provenance)

## Imported pre-v0.4.60 dump — one-line provenance records
(structured `##` entries begin at v0.4.60; block sequestered into
position per the newest-LAST contract, lens B F14, v0.4.80)

- v0.4.45 (2026-08-29, owner 'Fix all' 20:00Z — item 4 + Lens C deltas): oc-ledger KERNEL goes live + oc-review-persist. tools/oc-ledger (flock + tmp→mv + jq-validate atomic ledger writes; verbs stamp/sync/check-version/cadence/ack/enroll/commit-pending [--bundle]; self-commit inside the same flock — the v0.4.42 BEND end state realized; sync = battery-gated (tools/tests/battery-last.json PASS, fail=0, <6h), step-checked (+1 patch only), idempotent re-sync dedup, commits state repo + skill repo + tag, prints cadence; exit 0/1 verdict/2 usage/3 ledger/4 write/5 battery-gate/6 version). tools/oc-review-persist (lens reports → oc-work/skill-review-<lens>-<YYYYMMDD>.md + index receipt line, sha256+bytes, re-read verify; ghost-incident cure). run.sh: sections 11/12 + battery receipt writer. commit-pending sweep = item-2(b) ruling, wired to supervisor Duty-3/4 cadence (supervisor.md pointer live). Battery 81 PASS / 0 FAIL (76 + 3 oc-ledger + 2 oc-review-persist).
- v0.4.46 (2026-08-29, owner 'Build the tools' 20:53Z — KERNEL C5/C6/C7 implementation): the three pending designs ship as tools. tools/oc-prchecks (editor Phase 5 one-command lint gate: FULL-sha shape gate -> LOUD yml-on-carrier check -> dispatch -> sha-bound run resolve (concurrent-lane safe, dispatch_ts-filtered) -> watch -> per-job/per-step report with the fmt soft-fail EXPOSED; exit 0 GREEN / 2 usage-shape / 3 RED / 4 dispatch-api / 5 in-flight; selftest 12/12 on injectable gh shim, zero network). tools/oc-upstream-delta (watch-cycle arithmetic for Upstream-relations item 1: fetch + merge-base + AHEAD/BEHIND TSV + patch-id ABSORBED-CANDIDATE rows; READ-ONLY, never merges/pushes/rebases; exit 0 clean / 1 delta-verdict / 2 usage / 3 fetch-git; selftest 10/10 on local fixture remotes). tools/oc-wt add/remove (Phase 2 ritual: prune -> fetch -> validate local branch -> behind-base gate -> worktree add -> CHAINED the retired worktree indexer UN-SKIPPABLE; remove dirty-tree gate with --force journaling the destroyed listing FIRST; validates branches, never creates; exit 0/2/3/4/5/6; selftest 12/12 on bare-clone fixture). Doc wiring: SKILL.md tool table +3 rows + raw-gh row marked manual-fallback + Upstream-relations item 1 pointer; editor.md Phase 2 shrunk to oc-wt, Phase 5 + Phase 7 2c gain oc-prchecks pointers. Battery 88 PASS / 0 FAIL (81 + 3 + 2 + 2; design-doc battery estimates counted per-selftest-case, battery counts sections — corrected here). Dogfood: oc-ledger sync stamps this bump; commit-pending sweep follows.
- v0.4.47 (2026-08-29, owner 'Go' 21:56Z — relic sweep under the git-history condition): 27 redundant relics deleted AFTER per-file verification — every candidate checked tracked-in-git and clean at HEAD, all past history recorded in git (state pile imported at 1232ccd, skill pile at 3e6c7b1); the single untracked stray (CHANGELOG.md.2026-08-29T203012.bak) byte-identical to blob f24a0162 already in history, so zero content lost. Skill: backups/ x15 (SKILL/editor/compiler/supervisor snapshots + pre0419 seeds — all imported into synthetic history), tools/archive/oc-consent-check.pre-S2 + oc-deploy.pre-S2 (deletion trio closed; pending-health-check.json was already gone from disk). State: .bak pile x10 (baseline x4, smoke-verdicts x2, workers-ledger x4) — structurally redundant since ledger-in-git keeps every version losslessly. Also: SKILL.md the retired worktree indexer row demoted to INTERNAL (chained by oc-wt since v0.4.46). Battery 88 PASS / 0 FAIL pre-bump. Merges A/B (shadow-rotate as sync tail-step; watch + upstream-delta bundle) presented with diagrams, awaiting approval.
- v0.4.48 (2026-08-29, owner Go 22:52Z — merge A + merge B + Duty-7 IDEA fixes from editor lane 7e1ebbb6 / task #34 / run 33277921811): MERGE A — oc-shadow-rotate chained as the oc-ledger sync TAIL STEP (bump cadence IS the rotation cadence now — mechanical, not prose; rotation failure WARNs without affecting the bump; selftest sync-tail-rotate-line). MERGE B — oc-deploy watch --with-delta: oc-upstream-delta arithmetic rides the same watch call; output DELTA:-prefixed, shadow_log gains delta:clean/present/fail-rcN rows, tripwire severity WINS (an advisory delta never masks WATCH-ALERT; delta rc 1 = verdict, not failure); OC_DEPLOY_DELTA_TOOL injection keeps selftests fixture-only. DUTY-7 IDEA 1 — ledger vocabulary v1.1: kind claim (fork-issue claiming row) accepted by oc-ledger stamp; the frozen v1 KINDS had rejected it (two lanes hit it: n=1333/n=1334 note-prefix workarounds). DUTY-7 IDEA 2 — oc-prchecks rebuilt around the run-33277921811 field lesson: workflow_dispatch headSha IS the carrier ref (gh run view verified), NEVER the -f ref input, so the sha-bound resolve could never match (gave up at 60s); replaced with TIME-WINDOW RUN ADOPTION (event==workflow_dispatch + headBranch==carrier + createdAt>=dispatch_ts, earliest-wins) under a state-dir dispatch LOCK (.oc-prchecks-dispatch.lock, OC_PRCHECKS_LOCK_WAIT); --repo becomes SLUG-or-PATH dual support (path resolved via its origin remote — kills the slug/path confusion too). Selftests: oc-deploy 135/0 (+3 delta-stub checks), oc-ledger 43/0 (+claim +sync-tail), oc-prchecks 12/12 (carrier-shaped shim, negative decoys, lock contention), oc-upstream-delta 10/10, oc-wt 12/12. Battery 88 PASS / 0 FAIL pre-bump. Doc wiring: SKILL.md rows (oc-deploy watch flag, oc-ledger kinds+tail, NEW oc-shadow-rotate row, oc-prchecks mechanics, ISSUE ROUTING claim-kind line) + editor.md Phase 5 pointer.
- v0.4.49 (2026-08-29, owner Go-with-1 23:44Z — commit-pending sweep-gap fix, follow-up 1 of the v0.4.48 ship report): seal-state receipts join the commit-pending --bundle STATE leg. baseline.json + orders.json are written by oc-seal-state on every swap seal, but the swap chain never self-commits them and the state bundle leg only swept tools.log — the 781ecd80 swap (run 33279712496) leaked a stray baseline.json that needed a manual commit (state 6a2e66e). The state leg now hit-detects tools.log/baseline.json/orders.json exactly like the skill leg hit-detects runtime artifacts, commits them under a named state-sweep message, and echoes what it swept. Selftest 43->45 cases (commit-pending-baseline-sweep + left-dirty check); oc-ledger 45/0; battery 88 PASS / 0 FAIL pre-bump (solo). Follow-up 2 (off-box durability for both repos) remains owner-word pending.
- v0.4.50 (2026-08-30, owner 'Attach' 00:23Z — off-box durability, skill leg): leshchenko1979/opencrabs-skill wired as the LIVE MIRROR of the skill repo. The .bak-era scaffold history was replaced by the real one via force-push, loss verified BEFORE push (remote tree byte-identical to the local v0.4.31 tag tree, zero remote-only files); 13 tags v0.4.31-v0.4.49 published, main = real head. oc-ledger gains the push_mirror tail step on sync + commit-pending: pushes current branch + v0.4.* tags to origin when one is configured; WARN-only, never gates the bump/sweep; branch push NON-FORCE so a diverged remote is reported, not overwritten; state-repo leg activates the moment an origin is added (destination still owner's call). Selftests 45->47 (bare fixture remote receives commits); battery 88 PASS / 0 FAIL pre-bump.
- v0.4.51 (2026-08-30, ping-turn batch — same gap class as v0.4.49): commit-pending --bundle state leg sweeps journal/ too — smoke/swap journals land in the state dir and are git-tracked since live import 1232ccd, but the overnight cbc77058 swap (run 33281949340, smoke-34) left its journal + the n=1345 stamp + baseline.json unswept because journal/ was absent from the state bundle list (skill leg already covered oc-deploy/journal since v0.4.46). Selftests 47→48 (+journal-sweep case); battery 88 PASS / 0 FAIL pre-bump; live dogfood: the post-bump bundle sweep collected the overnight swap receipts including smoke-34.
- v0.4.52 (2026-08-30, owner Go 09:39Z — reload convention + state mirror + cc100dc6 verdict): mid-cycle skill drift made mechanical — editor.md gains §Mid-cycle skill drift (pull-check on every detached-resume / session_notify wake: version compare → re-read from disk → oc-ledger ack; apply changed rules from the NEXT phase boundary; tools/* never need reload); supervisor Duty 3 points the >3-behind skew test at ledger ack rows (oc-skew-scan already reads them). STATE repo now mirrored to private leshchenko1979/opencrabs-dev-state (attach parity 9d23b22) — the v0.4.50 push_mirror tail step covers BOTH repos mechanically from this bump on. cc100dc6 (local-only ci.yml-removal commit, 08-26) DROPPED as already achieved: fork main carries no ci.yml since the ci/remove-ci-workflow lane shipped the removal. Battery 88 PASS / 0 FAIL (docs-only batch).
- v0.4.53 (2026-08-30, owner 'Approve all 4 CI fixes' 14:00Z + 'pr naming convention' 14:15Z — the two-problem fix batch; REBUILT from scratch after a post-compaction phantom falsely reported this bump complete): (1) oc-prchecks adoption headSha-corrected — selector hard-matches headSha==RESOLVED-CARRIER-HEAD (field lesson re-verified: every workflow_dispatch run lists the carrier head, never the -f ref input), window floor buffered -5s against GitHub createdAt jitter, LATEST-wins (old earliest-wins decoy-adopted another lane's older run in the 00:38:38Z race; under the shared dispatch lock a newer carrier run can only be this lane's own); shim battery updated to the new semantics (adoption picks the lane's own newest run), 13/13 selftest + battery 88 PASS / 0 FAIL. (2) pr-checks.yml gains a concurrency group (group: prchecks-${{ github.ref_name }}, cancel-in-progress: true, carrier commit a87b66dc pushed to origin/ci/quick-build-linux) — a re-dispatch auto-cancels the superseded run when the head moves. (3) lib/oc-log.sh stamps actor: from $OC_ACTOR (unset → 'unknown') — every oc-* invocation must export OC_ACTOR=<session-uuid> (owner rule); attrs flood/behaviour after the fact, feeds the ledger-beats-memory guard. (4) CI-wait discipline in editor.md + AGENTS.md: raw `gh run watch`/`gh watch` BANNED (3s × concurrent sessions = the overnight flood); lane waits via oc-prchecks, carrier waits via oc-deploy watch or a detached ≥60s poller. (5) PR naming convention formalized in AGENTS.md + editor.md Phase 7: PR titles carry fix:/fix(scope): (bug), feat:/feat(scope): (capability), chore: (tooling/CI/docs/deps); head-branch slugs mirror the type (leshchenko1979/fix/<slug> | feat/<slug> | chore/<slug>); retro-check: upstream #1265 already conforms.
- v0.4.54 (2026-08-30, owner Go 19:24Z — flock single-flight, issue #42; CHANGELOG entry backfilled 08-31 — the bump shipped without one, receipt lived only in the issue comment): fanout_run acquires a per-run flock ($STATE_DIR/fanout.lock.<run>, exec 9<> + flock -n -E 4) BEFORE the idempotence guard, held through fanout_mark_done; concurrent sweep exits 0 reason=inflight with the holder journaled (13:21Z TOCTOU — 12 sessions double-carded — closed). Advisory lock, docs-verified (man-pages 6.7 + util-linux), crash-safe (release-on-close, lock files never unlinked). Journal vocabulary +3: lock-acquired / lock-busy / skip {reason:done}; pid-suffixed fanout journals ended same-second clobbering; old test 637 re-scoped (no-op re-run writes exactly one skip journal). Selftest 136/0; commit 0ae5e68c; receipt [#42#issuecomment-5470871488](https://github.com/leshchenko1979/opencrabs/issues/42#issuecomment-5470871488).
- v0.4.55 (2026-08-30 02:32Z owner Fix-it-and-GAP-2 — GAP 2 residual + fleet storm fix): (1) oc-ledger ack accepts the full skill version shape 0.N.N (v prefix tolerated, stored bare to match sync) — the N.N-only regex could never record a real version, so the reload convention (v0.4.52) step-2 ack was mechanically impossible for every actual bump; folds IDEA A core (regex alignment; v-prefix policy settled as tolerate-and-normalize). Selftest ack block rebuilt: two-component now rc 2, non-0 major rc 2, v-prefix normalizes (48 to 51 cases). editor.md reload section notes the shape. (2) Companion opencrabs-side fix (not skill content): carrier pr-checks.yml concurrency group keyed on inputs.ref (commit 852175a4, fork issue #44) — the ref_name key from a87b66dc put ALL dispatch lanes in one kill-group (4 runs mutually cancelled 08-30 22:06-23:20Z). Audit correction: the 22:49Z incorporation audit called GAP 2 zero-lines-shipped — wrong; v0.4.52 (owner Go 09:39Z) shipped the convention docs; only this ack-shape residual was live.
- v0.4.56 (2026-08-31 03:05Z owner Go — oc-prchecks verdict fidelity, folds IDEA B): RUN conclusion is the verdict. success -> GREEN exit 0; cancelled/failure/timed_out/startup_failure -> RED exit 3 reason run-<conclusion> (false GREEN killed: cancelled used to journal exit=0); any conclusion=failure STEP still REDs a success run with the fmt soft-fail exposed (skipped/neutral steps + skipped jobs now PASS — IDEA B false RED killed, victims 33316539757/33318336611/33317044766); verdicts fire ONLY on a terminal conclusion — null/empty at verdict time exits 5 verdict_reason non-terminal (stale-read guard: the 23:45:07Z RED fired 7s before conclusion=success on 33341579381). New journal field extra.verdict_reason (run-cancelled / run-failure / fmt-skipped-pass / jobs-failed / non-terminal) rides every verdict row; exit-code contract unchanged (0/2/3/4/5). Selftest 13->16 cases (cancelled RED, skipped-pass GREEN, non-terminal rc5, run-failure RED); battery 88/0 pre-bump.
- v0.4.57 (2026-08-31 ~04:1xZ owner 'include, then go with the suggestions above' — Duties 4+6 13/5 FIRE incorporation batch): DUTY 4 (8 lanes, 17 proposals -> 12 accept-mechanical + 4->1 merged): editor.md §CI-wait discipline items 4-9 (>=60s floor for EVERY detached gh poller; --wait <=90s vs the 120s tool-runner ceiling + >=600s first-dispatch timeout + API run-search recovery; per-leg invocation verify + mid-chain rc!=0 immediate notify; notify wiring in the wrapper never as oc-prchecks flags + cron courier for notify-less waiters; log-window line-number cutoffs; gh api REST v3 snake_case); Phase 1 claim read-back (n=1361 class); Phase 6 --body-file-only implementation-comment mechanics; Phase 7 HARVEST VERIFICATION SWEEP (4-lane convergence: fork-side symbol sweep, attribute porting, foreign-hunk drop, patch-id verify); SKILL.md Box law rustfmt-wrapper-newer-than-CI rule. DUTY 6 (44 findings): HIGH x3 fixed — SKILL.md Tackling-comment residue retired (upstream ban), UPSTREAM CI GATE text repointed to CI-gate evidence (local-cargo triad reading killed), ops AGENTS.md staleness (compiler present-tense, tackling procedure, v0.4.29 pin) surgically corrected; oc-review-persist adopted as the Duty-6 persistence verb (SKILL.md row path fixed to $OC_REVIEW_DIR default /tmp); Reviewer E (INTERFACE/TOPOLOGY — tool-merge review) added to the lens set per owner question 03:54Z (verified: NO lens covered tool merges before); ROSETTE/HQ-roster coinages replaced with real sources; CONSENT REGISTER dup -> pointer; roster-enroll kind added to the register row; orphan (c) marker dropped. TOOL BUG: oc-ledger cmd_stamp had no --what flag and ate it as positional text while dropping the real value (n=1361 AND n=1372 both stored what=--what) — now accepts --what, rejects unknown flags rc=2; selftest +4 cases 55/55; corrective incident stamped n=1383. TOOLS.md gains the write_opencrabs_file profile-relative path rule (KERNEL placement, owner go). Battery 88/0 pre-bump.
- v0.4.58 (2026-08-31 04:20Z owner Go — lens-C tool builds + D-lens deletion sweep + by-attribution fix): LENS C (5 builds): oc-drift-check (claimed vs live version, --ack delegates oc-ledger ack), oc-toolaccum (tools.log per-actor per-tool failure arithmetic, threshold 3 = repeat-offense), oc-branch-sweep (MERGED/ABSORBED/STALE/ACTIVE classification, deletes MERGED only, protected base/HEAD/--keep, archive tip sha in TSV), oc-pr-fault-scope (failing-files intersect PR-files = IN-SCOPE/BASE-FAULT, the 08-26 clippy-wall lesson mechanical), oc-ledger confirm verb (verifies latest claim #N on the live fork via injectable gh, THEN flips workers[].confirmed — until today NO verb flipped it). DUTY-4 IDEA (lane 7e1ebbb6, n=1386 trap): stamp by-default no longer lies — derive_by() maps OC_ACTOR via the roster, unrostered says so, no actor = LOUD '(unattributed — pass --by)'; the silent 'supervisor (topic 30220)' default retired. D-LENS SWEEP (owner Go): 10 conditional DELETE-SAFE items deleted AFTER per-file tracked+clean+blob verification (21:56Z condition): 8 tools/archive/*.bak + oc-consent-check (skill 6a12cd28, blobs 2e70dc02/47da2f36/1ed75411/95121286x3/b50c58dd/a2e1f203/a77f9119) + pending-health-check.json (state aafc248, blob 27041bbf — v0.4.47 claim 'already gone from disk' was FALSE, file lived untouched; corrected in ledger n=1391); watchdog-13e4e1da.log archived to journal/ (dead since 23:40Z); workers-ledger.lock writer IDENTIFIED = oc-ledger with_lock() exec 9> — KEEP, live control [CORRECTED v0.4.65, lens D #13: that identification was STALE — the real oc-ledger lock is workers-ledger.json.lock (with_lock does exec 9>"$LEDGER.lock" with LEDGER=workers-ledger.json); the bare workers-ledger.lock was an orphaned 0-byte untracked leftover with ZERO refs in tools/, deleted on owner word 2026-08-31 11:45Z]; pre-merge ledger anchors confirmed tracked, KEEP as provenance. Selftests: oc-ledger 55->66, oc-drift-check 6, oc-toolaccum 7, oc-branch-sweep 9, oc-pr-fault-scope 4; battery 88 -> 97 PASS / 0 FAIL. Tool table +5 rows.
- v0.4.59: oc-deploy sidecar sync (#47, owner 'Go' 2026-08-31 04:45Z) — GREEN-path sidecar_sync(): after ops post-verify match, every active opencrabs-*.service user unit (primary excluded) whose MainPID exe sha != deployed sha is restarted + re-verified (found live 2026-08-31: default+family daemons 2 days/3 swaps behind, leaked rich-only tags through pre-fix card code); NON-FATAL by design (sidecar-unit exit=1 journaled, swap never fails on a stuck sidecar); gates DRILL=off / sandbox-off unless OC_SWAP_SIDECARS=2 / 0=always-off; selftest shims OC_SWAP_SIDECAR_LISTER/SHOW/ACTIVE/RESTART + OC_SWAP_PROC_PREFIX + OC_SWAP_PRIMARY_UNIT; selftest cases 17n (stale restarted, in-sync untouched) + 17o (sandbox guard skips, zero restarts); battery 145 PASS / 0 FAIL

## v0.4.60 — deploy accounting migration + ship leg-plan journaling (owner 06:03Z "fix the gaps" + 06:10 "Go")

- **Migration:** deploy artifacts out of the skill dir (owner order "move all accounting files and markers"): `deployed.sha`, `deployed.meta.json`, `fanout.state`, `oc-deploy/journal/`, shadow archive + stale fanout locks moved to the state dir (`opencrabs-dev/`), byte-verified copies before removal. `oc-deploy:66` STATE_DIR default flipped; `oc-attrib:83` + `oc-shadow-rotate:23` defaults flipped too — **the battery wire test caught oc-attrib rc=5** on the migrated marker (hardcoded default my path-grep missed; lesson: grep the ROOT literal, not the artifact path).
- **Gap fix (two orphaned GREEN ships 2026-08-31):** `ship --execute` dispatch leg now journals `leg=dispatch, next="watch+swap REQUIRED", shipped=NO` via tools.log extra — a dispatch-only rc=0 exit can never again read as a shipped build; absence of a swap row for the sha is alarmable from the journal alone.
- **Sweep lists:** oc-ledger skill RUNTIME_ARTIFACTS shrinks to the battery receipt; moved set joined the state sweep (git-tracked in the state repo).
- **Live-verified post-migration:** `poll` reads deployed=d730e9ca from the new path; `fanout --run 33359092769` → skip reason=done (idempotency preserved). oc-deploy selftest 145/0, oc-ledger 66/0, battery **97/0**. Skill `1469b1bc`+`471ca33b`; rc=2-first-attempt pattern (2 ships) noted as dispatch-lock suspect — rc vocabulary documented, no code change.

## v0.4.61 — naming + ontology hard rules; editor tool reference (owner 2026-08-31)
- SKILL.md Hard rules: worker-naming rule SHARPENED — topic/chat name only on EVERY surface (was: owner reports only; tonight's uuid-laden fleet board was the live violation). Uuids = routing fields only.
- SKILL.md Hard rules: NEW official-ontology rule — SKILL-defined vocabulary only; new concepts named via poll on owner word; Reviewer A enforces.
- editor.md: NEW "Tool reference — editor's quick table" (invocation forms + rc contracts + the three rules that outlive any table). Doc-only bump; no tool code touched.

## v0.4.62 (2026-08-31) — stale-refs/ontology batch + Reviewer A strengthened (owner "Go" 09:17Z)

Duty-6-style read-only review (subagent, lens: stale references + unclear terms) found 22 defects in v0.4.61 text; all fixed, quotes disk-verified:

- 1b dead paths (5): fanout journal path + editor brake path + shadow-log location repointed to the state dir (v0.4.60 migration residue — the brake doc armed NOTHING at the old path); 2 false "archived at tools/archive/oc-consent-check" claims corrected (archive holds only compiler.md; blob in git history).
- 1d dead test-leg prose (4): test-ontology CODE TESTS cells repointed to pr-checks.yml as the ONLY test locus (carrier leg removed e71dba58); cargo flags made verbatim (`--locked --profile ci --all-features`) at SKILL.md UPSTREAM CI GATE + editor Phase 5 + Phase 6 comment.
- 1a unmarked retired concepts (2): "CI is the compiler" present-tense -> CI-is-the-only-executor with Compiler RETIRED 2026-08-28 marker (x2).
- class-2 unclear terms: NEW SKILL.md section "Glossary — official terms" (CI gate incl. legacy synonyms, ORDER gates, S2/S3, lane, roster, lens, selftest vs battery, GREEN/RED terminal truth); "4-lens" -> "5-lens (A–E)"; ontology-rule parenthetical now cites the real ontology terms; lint-gate name variants normalized.
- supervisor.md: Reviewer A lens STRENGTHENED (owner word same turn) with the churn-drift checklist: one-concept-one-name, glossary conformance, post-migration ROOT-literal path sweep, enumeration consistency, retired-concepts-marked.

Docs-only; battery 97/0; sync+tag v0.4.62; mirrors at parity.

## v0.4.63 (2026-08-31) — sync payload root-fix (incident n=1405)
- oc-ledger sync: stage the FULL skill working tree (tracked+untracked) instead of the hardcoded SKILL.md+CHANGELOG.md list — a bump tag can no longer point at a tree missing its payload (three-strike class: v0.4.58/61/62 strayed files). Swept non-doc payload named loudly on stderr ("PAYLOAD SWEPT").
- Selftest +3 (69/0): payload probe swept into bump commit + warning present + committed tree verified; bundle fixture de-coupled from leaked untracked dirt; cadence-count fixture updated for the extra bump event.
- Owner "Go" 2026-08-31 (sync-fix proposal after n=1405 stamp).

## v0.4.64 (2026-08-31) — Duty-6 five-lens fix batch, P0–P3 + K-wiring (owner "Go all" 10:39Z)

Five read-only lenses (A ontology / B efficiency / C CLI-automation / D deletion / E topology) reviewed the v0.4.63 tree; all incident-backed HIGHs disk-verified by the supervisor, then fixed on the owner's "Go all":

- **P0 latent ship breaker:** oc-deploy helper-tool defaults were `$STATE_DIR/tools/…` — a dir that does not exist in the post-v0.4.60 state split (found independently by lenses B and E; zero ship journals since the split, so the first post-split `ship --execute` would die at the ORDER gates rc 2). New TOOLS_DIR anchor precedes first use; wire-test fixtures updated to pass explicit `OC_DEPLOY_SEAL`/`OC_DEPLOY_ARTVERIFY` (they had been silently RELYING on the broken defaults).
- **P0 data preservation:** the 3 un-archived d730e9ca shadow lines (05:01:39/46/54Z) appended to the state archive under flock + state-repo commit (unique copies — three lenses converged).
- **P1:** adoption-rule docs (SKILL.md oc-prchecks row + editor Phase 5) rewritten to the code-true LATEST-wins v0.4.53 form; swap-execute's seal call passes `--baseline/--orders` explicitly (was sealing a different file than it read the cycle from).
- **P2 docs:** tool-table rows corrected to real interfaces (oc-job-verify, oc-artifact-verify, oc-seal-state, oc-post-receipts, oc-deploy rc register, branch-sweep rc register); ship wording = dispatch confirmation, not GREEN+run-id; worktree recreate/teardown re-pointed at oc-wt in all six sites (raw-bypass closed; Phase 7 keeps its raw -b add but chains the UN-SKIPPABLE index); drift ritual -> oc-drift-check; Phase 7 CI-flag provenance -> pr-checks.yml; s2 spec short-sha fix; CHANGELOG newest-last reorder.
- **P2 tool mechanics:** oc-attrib header state-dir fix; OC_LEDGER parity in oc-skew-scan + oc-ping-proof; `--no-log` suppression moved into lib/oc-log.sh (triplicated per-tool loops deleted); oc-ledger stamp: flag-lookalike `--what` guard + read-back self-verify after every write (the n=1361/1372 glitched-argv class can no longer land silently).
- **P3 new tools:** `oc-smoke-evidence` (running-daemon identity + presence evidence — replaces 15+ hand-assembled smoke-verdicts.log lines), `oc-issue-log` (per-commit implementation comment via gh --body-file only — heredoc-substitution mangling impossible), `oc-harvest-sweep` (pre-gate mechanical legs: trailers / empty-diff / patch-id). All journal via lib/oc-log.sh, selftested, smoke-evidence live-verified green.
- **K-wiring (zero code):** Phase 1 uniqueness gate -> oc-issue-sweep (+ editor table row), Phase 7 commit listing -> oc-deploy contributors/oc-attrib, carrier feature read -> oc-carrier-features, drift -> oc-drift-check, worktree lifecycle -> oc-wt.
- **Reviewer C lens STRENGTHENED (owner directive same turn):** every lens-C pass now reads tool logs (tools.log, oc-deploy journals, ledger events, smoke-verdicts) and analyses real usage — invoked verbs/flags, rc distributions, never-invoked tools (deletion evidence), hand-built ritual artifacts. Findings cite log rows.

oc-deploy selftest 145/0; battery 97/0.

- "S3 cutover 2026-08-28 (owner msgid 34717: 'let's go to S3'): COMPILER role RETIRED; duties automated into tools/oc-deploy (ship/poll/swap-execute); compiler.md archived as re-enable runbook; ledger meta.oc_deploy_stage = S3, event 1282"
- "v0.4.32: compiler retirement landing pas (this bump)"
- "v0.4.33: post-swap editor-notify + attribution duty re-owned to SUPERVISOR (Review B finding B9; compiler retired at S3) — Phase 6b trigger, FAIL routing, session-notify loop retargeted; supervisor.md Duty 7 added"
- "v0.4.34 (owner 2026-08-28 17:2xZ, two orders): (1) modum RETIRED from the process — lint/static-analysis evidence = GREEN pr-checks.yml only; Phase 5 rewritten CI-only; editor.md scope/box-law/inline mentions, SKILL.md, AGENTS.md synced; rustfmt wrapper stays, modum binary stays installed. (2) The v0.4.33 post-swap-notify rewiring REVERTED per owner ('revert the previous change about post swap notifications') — Phase 6b trigger, FAIL routing, SKILL.md notify loop, supervisor.md Duty 7 back to pre-0.4.33 text; the notify duty is homeless again pending a process-first re-proposal (this bump)"
- "v0.4.35: self-review 2026-08-28-r2 fixes — stale Compiler-role anchors re-anchored to oc-deploy (editor.md/SKILL.md/supervisor.md/compiler.md); telegram law deduped; PROCESS-TOOL guard S3-rewired; versions listed"
- "v0.4.36: KERNEL CLI batch (owner 'Go' 2026-08-28 21:16Z) — 5 new tools: oc-carrier-features, oc-issue-sweep, oc-skew-scan, oc-ping-proof, oc-watchdog-check; oc-attrib gains --deployed (range from deployed markers, fan-out compute backend for issue #24); oc-deploy ship/poll resolves EMPTY --features from carrier YAML via oc-carrier-features (loud fail, no silent fallback); unified tools.log via tools/lib/oc-log.sh (JSONL, filterable with jq); battery 64 PASS / 0 FAIL; AGENTS.md interim post-swap notify bridge RETIRED (#23 session-notify verb live in 49125f8c)"
- "v0.4.37: issue #24 mechanical notify fan-out (owner 'Go' 2026-08-28 22:42Z, design doc oc-work/oc-deploy-fanout-issue24-20260828.md) — oc-deploy gains TWO modes: 'contributors' (thin wrapper over oc-attrib --deployed/--range, TSV session+issue+sha7) and 'fanout --run <id> [--dry-run]' (GREEN leg: notify live-swap contributor sessions via 'opencrabs session notify --profile ops'; RED leg: gh annotations -> git blame -> culprit Session-Id trailer notified as blamed + suspect cc, zero-sites fallback HUMAN-FLAGs all range sessions; dead uuids skipped verb-rc-2, unowned counted, idempotent via fanout.state, per-run JSONL journal under STATE_DIR/oc-deploy/journal/fanout-<run>-*.jsonl); auto-wired: GREEN fires at swap_execute tail after receipt seal + markers, poll gains failed-run RED scan (both OC_DEPLOY_NOFANOUT=1-suppressed, subshell-isolated); selftest 128 cases, battery 76 PASS / 0 FAIL"
- "v0.4.38: ledger unification + process re-anchoring (owner 'Also fix' + 'Go' 2026-08-29 07:32Z) — oc-deploy + oc-order-validate LEDGER defaults now point DIRECTLY at canonical opencrabs-dev/workers-ledger.json (the old $STATE_DIR default silently kept a second ledger in the skill dir: two-file drift, baseline/orders backup paths at an empty dir, cycle counter reset 25->1; incident 2026-08-29); OC_LEDGER overrides, explicit OC_DEPLOY_STATE_DIR keeps selftest/battery fixtures isolated; skill-dir duplicate + orphaned lock deleted; oc-deploy --selftest re-exec moved from bare $0 to readlink -f'd $SELF (relative invocations no longer die rc 127); stale 'supervisor bridge until #23/#24' pointers re-anchored to LIVE mechanical fan-out in editor.md/SKILL.md/supervisor.md + AGENTS.md; selftest 128 cases green in all three invocation forms, battery 76 PASS / 0 FAIL"
- "v0.4.39: feedback-loop completion (owner 'Go' 2026-08-29 08:12Z) — Duty 4 poll-workers gains STANDING cadence (every five shipped version bumps, shared trigger with Duty 6); new Duty 7 IDEA BOX: editors push 'IDEA: ADD|CHANGE <rule/tool> in <file+section> BECAUSE <gap actually hit>' to the supervisor lane via session_notify the moment they hit a gap, supervisor stamps ledger kinds idea (arrival) + idea-verdict (ACCEPT-mechanical / KERNEL-semantic / REJECT), same-turn ack, merges with open Duty-4 proposals; Duty 6 gains Reviewer D — DELETION SAFETY (enumerate stale-looking artifacts, list readers/writers as evidence, classify DELETE-SAFE/ARCHIVE/KEEP, nothing deletes without triple-check + owner word; born from the 2026-08-29 live-ledger deletion incident), closing the dangling (A/B/C/D) parenthetical; editor.md push clause + SKILL.md role-row registration; battery 76 PASS / 0 FAIL"
- "v0.4.40: Duty-6 four-lens verdict batch (owner 'go' 2026-08-29 10:41Z; lenses A/B/C/D = 15/17/5/24 findings, verdict 30 ACCEPT / 7 KERNEL / 0 REJECT, reports /tmp/skill-review-*-20260829.md). Mechanical: register exit codes corrected (oc-order-validate 0 VALID / 1 invocation / 2 UNMERGED / 3 UNSIGNED / 4 UNKNOWN-REF); archived compiler-step anchors stripped; fanout/notify rows retargeted to §Session-notify loop (canonical, baseline.json path inline); box-law + consent-register bullets condensed; ISSUE ROUTING consolidated as a table (B17); upstream-sync gated on owner word, compiler.md Step 7 archived (B7); STEP ZERO + scope lines drop Compiler (B13/B14); COMPILER INBOX POLICY moved to supervisor.md Duty 3 (B5); AIRBORNE→queued (A14); orphaned/staled editorial notes folded (A1 E0425 pointer, B10 pre-S3 ordering, A12 IDEA template, A8 telegram enumeration, A9 box-law ref); oc-deploy stale compiler-relay echoes → fanout/poll reality + oc-order-validate header (B2/B16). SEMANTIC: A3 owner ruling — BUILD TRIGGERS = exactly TWO, NO exceptions; Phase-7 step-2b quick-build PR-head dispatch RETIRED (carrier Gate 3 containment rejects any sha outside fork main anyway); PR-head compile+lint evidence = step-2c pr-checks dispatch. Drift fix: ledger top-level current_skill_version synced to 0.4.40 in this stamp (n=1313). Lens D executed: 8 tool snapshots + 11 md .baks + oc-work batch history archived; tools/_probe + 10 old /tmp reports + 14 oc-work scratch files deleted (zero-reader verified). Battery 76 PASS / 0 FAIL, exit 0, stderr empty (pre-bump). KERNEL queue (awaiting owner word): B4 provenance move; oc-ledger/oc-review-persist design (design doc only, no code)."
- "v0.4.41: git-history regime (owner 'Go with your best reasoning' 2026-08-29 13:13Z on the 12:11Z analysis — scope = my best reasoning = BOTH git conversion and ledger-in-git). The skill dir AND the canonical state dir are now GIT REPOS. Skill repo (skills/opencrabs-dev/.git): synthetic history from surviving full snapshots — v0.4.31 (oc-work/archive/opencrabs-skill; a hidden .git clone inside that snapshot was excluded at import), v0.4.38 (skill-bak-20260829T0815Z), v0.4.39 (skill-bak-20260829T1050Z-v040), live v0.4.40 — tagged v0.4.31/38/39/40; gap v0.4.32–37 has no full snapshots (batch docs survive, files do not). State repo (opencrabs-dev/.git): six workers-ledger ancestors imported (n=1266/1267/1271/1284/1285/1304, mtime-dated) + full live state (baseline, orders, tools.log, journal, relics). Discipline landed in supervisor.md bump section: one commit per bump (skill repo), one commit per ledger stamp inside the same flock as the write (state repo). Ledger becomes LOSSLESS: JSON events[] is windowed to the last 100, git history keeps everything; the version-field drift class dies loudly via git log -L. Design-doc addendum (oc-ledger stamp must git add+commit inside flock; NO code yet): oc-work/oc-ledger-design-20260829.md. Off-box durability (private remote or git bundle) = follow-up on owner word. Battery: 76 PASS / 0 FAIL, exit 0, stderr empty (pre-bump, solo run)."
- "v0.4.42: per-stamp commit discipline amendment (editor d5863180 #29 IDEA) — commit-per-stamp BENDED for TOOL-written stamps (oc-deploy swap-execute / any tool subprocess: flock write happens inside tool, session cannot git-commit from subprocess; oc-ledger self-commit code does not exist per design doc oc-work/oc-ledger-design-20260829.md). RULING (event 1323): option (b) — the HOSTING session (the turn that observes the tool's stamp on disk) owns the commit. Hosting session bundles the tool stamp WITH its own adjacent stamp in ONE commit IF both are pending at commit time (commit message names ALL stamps); no mid-run commits, no per-stamp hunting. Reconstructed intermediate states allowed for backlog (keep old flags). Backlog n=1320/1321/1322 committed per-stamp by supervisor 2026-08-29 14:0xZ (commits 265d72e/76d2855/3af6981, state repo). Gates: oc-deploy selftest 128 PASS / battery 76 PASS (pre-bump)."
- "v0.4.43: Duty-6 run-2 verdict batch (owner '1, 3-6 go' 2026-08-29 18:11Z; lenses A/B/C/D = 18/11/7/23 findings, verdict 28 ACCEPT / 14 KERNEL / 3 owner-word deletions / 2 DONE / 12 KEEP / 0 REJECT, reports /tmp/skill-review-*-20260829-run2.md + verdict table /tmp/skill-verdict-20260829-run2.md). Mechanical: ruling/definition/PR-body dedups → canonical + pointers (A2/A4/A5); compiler.md's two drifted exit-code registers → register pointers (A7/A8); coinages fixed — 'carrier Gate 3' → ORDER gate 3 (CONTAINMENT) (A13/A14), 'dark author' → unreachable author (A15), 'diagram gate' parenthetical dropped (A11), 'all-tests' → CODE TESTS (A10); TOOL_ACCUM enforcement clause gains its evidence source (ops log + grep recipe) (A12); fanout journal path made literal (A18/B9); s2-swap-journal-spec synced to live markers/journals (A17/B11/D10); Phase 1 steps 2-3 shrunk to procedure + pointer (A3); oc-deploy header verified already-condensed (A9); Upstream-relations items 1+7 ownership pointer added to supervisor.md (B8); ruling-1323 text completed in supervisor.md Duty 3 (B5); freeze-history re-pointed to meta + git history (B7). PROVENANCE MOVE (B6): frontmatter provenance → this CHANGELOG.md (git-tracked, outside the load path). Runtime regime (owner items 6, D12/D16): markers/journals stay git-tracked; NEW tools/oc-shadow-rotate appends the gitignored shadow log into a git-tracked archive copy (second copy, bump-cadence). backups/ frozen read-only (lens-D D9; ledger event). Ghost incident (D1/D2): closed as ledger incident n=1325 — forensics found zero logged author; skill-dir rule = new files land git-tracked or journaled at creation. Battery 76 PASS / 0 FAIL (pre-bump, solo). KERNEL queue (owner word): commit-ownership cluster B1-B4 (item 2 'explain' answered 2026-08-29), oc-ledger implementation (item 4 GO — code next), oc-prchecks/oc-upstream-delta/oc-wt design docs (item 5), deletion trio dormant (item 7 silence)."
- "v0.4.44 (2026-08-29, owner 'Fix all' 20:00Z — tq task #7): compiler/modum limbo closed. compiler.md git-mv'd to tools/archive/compiler.md — the re-enable runbook archive the SKILL.md frontmatter claimed at S3 cutover but never executed; every live ref (SKILL.md x11, editor.md x1, supervisor.md x1, tools x6) repointed to the archive path via mechanical sed; historical/provenance mentions (s2-spec author line, CHANGELOG, backups/, the archived file itself) untouched. modum consolidated to the single SKILL.md §Hard-rules box-law statement — three retirement footnotes dropped from editor.md (scope quote, Phase 5 header, Phase 5 body). Battery 76/0 + bash -n green on all sed'd tools pre-bump."

## v0.4.65 (2026-08-31) — "Do 1+2" batch: deletion ritual, watchdog retirement, lens C MED/LOW tools, ship-chain hardening

Owner "Do 1+2 then explain 3" (afternoon, post-v0.4.64):

- **Deletion batch (ritual-verified):** coma-audit trio (3 DELETE-SAFE files), bare `workers-ledger.lock` (0 bytes), empty skill-dir `oc-deploy-shadow.log` (0 lines, gitignored); CHANGELOG lock-ID correction.
- **Watchdog wrapper retired:** `oc-watchdog-check` deleted — one invocation on record (08-28), superseded by per-session gate watchdogs + `oc-deploy watch`.
- **New tools:** `oc-commit` (repo-guarded commit: dirty-tree/branch/protected-path gates + journal), `oc-ship-audit` (tools.log orphan/terminal-missing dispatch scan, rogue-line hardened — live-run surfaced the 08-31 orphaned-GREEN class where the unhardened jq said CLEAN), `oc-tg-audit` (banned telegram-surface row scan from ops daily logs — first live run caught 92 banned rows from an off-roster session), `oc-wt list` verb (TSV: task path branch dirty-n). All selftested + registered in SKILL.md.
- **C8 sync changelog gate:** `oc-ledger sync` refuses when CHANGELOG lacks the version being shipped.
- **Duty 7 extended (owner directive):** QUIRK/FAIL prefixes — workers report tool quirks and failures to the supervisor; supervisor triages into ledger + review lens.
- **YAGNI rejections documented** (C9 oc-waiter, C11 oc-logstats): `tmp/duty6-review-20260831/DECISIONS-lens-C-YAGNI.md`, with revisit triggers.
- **Ship-chain hardening (found live via battery):** run 33388930453 (#49) executed swap-execute TWICE (stall-hit session relaunch); run 2 corrupted deployed.meta.json prev_sha. Fixes: double-execution guard in swap-execute (dies 2 on same-sha re-swap, selftest 13b, 17o fixture reset, c8f6b77d); battery oc-attrib wire test hardened for degenerate marker state (84af91de); live meta repaired to true prev d730e9ca (ledger n=1410). Residual gap flagged: neither journal captured a restart line despite the daemon bounce.

## v0.4.66 (2026-08-31) — editor requirement-intake rule (owner 2026-08-31 14:51Z)

- editor.md Phase 1 step 5: NEW/updated requirements persist in a fork issue BEFORE execution — processed actionable form, never verbatim; extends the in-flight issue or opens a new one; Issue-Ref discipline applies. Origin: owner correction of the supervisor-scoped draft; live issue leshchenko1979/opencrabs#51.

## v0.4.67 (2026-08-31) - qualified fork refs on upstream surfaces

- editor.md Phase 7: bare `#N` (fork issue numbers) FORBIDDEN on upstream surfaces outside code spans - GitHub autolinks to adolfo's unrelated issue #N. Qualified `leshchenko1979/opencrabs#N` or full URL required. Origin: owner directive 2026-08-31 (fork #54); live offenders found on PR titles 1273/1268/1266 + issue bodies 1255/1257, patched same day.

## v0.4.68 (2026-08-31) — oc-prchecks upstream guard

- oc-prchecks: fork-lane gate (rc 2, upstream repo refused pre-API) + carrier-head guard (rc 7, refuses time-window adoption when branches API cannot resolve the carrier head — previously matched ANY run: false GREEN). Finding: suggest-options lane; live-verified both guards; fork lane untouched; selftest 16/16.

## v0.4.69 (2026-08-31) — notification instructions: deferred delivery modes

- SKILL.md §session_notify mechanics: DELIVERY MODES (immediate / deferred via interrupt=true / automatic redirect on channel rebind fork #19 / no-route), refusal-handling rule, CLI --sender/--title form (owner order; evidence: 24 mid-turn refusals = lost wakes, comatose-lanes incident).
- editor.md §CI-wait item 6 + supervisor.md delivery discipline: operational wakes to mid-turn lanes carry interrupt=true.
- AGENTS.md waiter form updated (--sender/--title/--interrupt).

Issue-Ref: #56

## v0.4.70 (2026-08-31) — lens G regroup + notify delivery-mode terminology

- Owner corrections: interrupt=true is the #13 FAILSAFE (mid-turn operational wake), NOT deferred mode; deferred/queued delivery = acks + low-urgency (SKILL.md DELIVERY MODES, editor.md, supervisor.md, AGENTS.md).
- Lens G regroup (fork #57, owner "Lens G go"): HIGH 13 per-commit laws → detached-HEAD+signing Phase 4, writer-exclusivity Phase 2 (6c pointers); standing-laws band reordered (Box→Telegram→CI-wait→drift); Ship — oc-deploy (S3 path) promoted out of Phase 6; CI-wait items 4-9 → supervisor.md §CI-wait & waiter discipline; worktree lifecycle → Phase 2; test placement → Phase 4; oc-issue-log row; SKILL.md gh-run-watch fallback row aligned with the ban; 8 LOW/MED pointer fixes. Verdict: REGROUP, no split.

## v0.4.71 (2026-08-31) — Duty-4 proposal batch + 7-lens mechanics (pass 13/5)

- editor.md CI-wait items 4-7 (Duty-4 P1/P12/P7/P11): terminal-state wake gating, top-level rc reads, waiter pattern-vs-format check, oc-prchecks invoke-once. Evidence: run 33433873373 in_progress wake, pipe-tail false verdicts, run=<id> grep miss, 4-dispatch gate storm.
- editor.md Phase 1: issue/PR body claims require code-verified evidence (P3; upstream #683 hallucinated root cause). Phase 4: enum-variant grep pre-commit (P14; GluedHost E0004/E0308). Phase 4: trailer-parse verify after amend/rebase/cherry-pick (P2; c4a9ef55 empty trailer scan). Phase 7 2-pre: atomicity+base check BEFORE PR open (P6; #1273 wrong base).
- Lens A: Ship-section anchors repointed (M1), poll-floor ref to supervisor (M2), the retired worktree indexer path+rc in quick table (M3), ORDER-vocabulary scoping (M4), chain-reword (L1), 2c heading renamed (L2), CI-wait ref names standardized (L4), glossary entries carrier/fan-out/state-dir/single-flight (M7).
- Lens B2: restart-scope sidecar exception (B3), tombstone rows deleted from live table (B15), quick-table/prchecks register fixes.
- Supervisor: Duty 1 CHANGELOG step (C8 gate), Brief enumerates review set (M5), TOOL_ACCUM enforcement -> oc-tg-audit (L3b).
- Tools (lens C F4/F5/F7 + lens F): --help exits 0 + positional selftest fleet-wide; oc-review-persist accepts A-G/A1-G9 lens names; oc-ship-audit tail-chains onto oc-ledger commit-pending (OC_SHIP_AUDIT_CHAIN=0 disables); oc-commit + oc-branch-sweep worktree-hostile .git gates -> rev-parse (F1 HIGH); oc-issue-log failure branch no longer deletes the body (F6); oc-tg-audit --days validation + dead code out.
- CHANGELOG: duplicate v0.4.68 deduped, orphan ## Entries header removed, entries reordered newest-LAST (lens A L5).

Issue-Ref: #51

## v0.4.72 (2026-08-31) — owner "Go all" 8-item batch: lens F MED builds + flood guard + CI-wait fixes

- Task 1: deletions ritual — state-repo stale-lock reaper + entry-side stale-lock reaper in oc-deploy fanout (state commit 3844bfd; oc-deploy leg in task-2 commit).
- Task 2 (C-F1): oc_log_flood_guard() in lib/oc-log.sh — >=4 identical failed invocations in 120s -> exit 8; OC_NO_FLOODGUARD=1 bypass (52d5f395).
- Task 3 (C-F2+P4): oc-prchecks resume-before-dispatch (single-flight lock adoption) + CANCELLED rc 6 (74325d0a).
- Task 4 (P10): carrier yml already-shipped, no-op (852175a4).
- Task 5 (C-F3): editor.md Phase 6b oc-smoke-evidence identity receipt wiring (a5e6b8b3).
- Task 6 (lens E merges): oc-ledger cmd_claim_ref() dispatch+usage (5f28e50c); oc-contributors retired (b5c7e79b); lib/oc-embed.sh shared job-embed decoder; oc-job-verify --identity-only; oc-artifact-verify embed reuse; oc-attrib --trailers-only; oc-harvest-sweep Leg T delegation; oc-smoke-evidence --markers canonical / --strings deprecated alias; SKILL.md rows (64888c9a).
- Task 7 (lens F): F2/F3 oc-seal-state order-feature resolution via oc-carrier-features + mark-order fails loud on unknown sha, selftest 7->9 (1add673e); F5 oc-toolaccum unparseable tools.log -> die 3, F9 oc-review-persist LENSES +E F G, F10 oc-branch-sweep journals branch-delete (0a2e06d8); F7 set -o pipefail across all tools, oc-ledger selftests de-pipefied (grep -q SIGPIPE + intentional-nonzero inheritance) (cda85365); F4 already-shipped (7 carrier-head-unresolvable), F6 REJECTED with evidence (failure branch never deletes the body).
- Task 7/F8 battery: section 17 covers 7 never-battered tools (shadow-rotate, smoke-evidence, issue-log, commit, ship-audit, tg-audit, harvest-sweep) — 86->104 checks; oc-shadow-rotate now validates args (usage rc 1); oc-smoke-evidence loop double-shift bug fixed (two-flag invocations died on usage); battery 104/0 GREEN (359d1d25).

Issue-Ref: #51

## v0.4.73 (2026-09-01)

- Duty-6 lens G widened: EDITOR.MD STRUCTURE -> ROLE-FILE STRUCTURE, now covers the organization of ALL three role files (editor.md + supervisor.md + SKILL.md). Owner 2026-09-01: "supervisor does not review its own skill file" — the review-set brief handed reviewers every file, but only editor.md had a structure lens, so supervisor.md and SKILL.md organization went unreviewed. SKILL.md role-table row updated; oc-review-persist whitelist unchanged (letters A-G).

Issue-Ref: #51

## v0.4.74 (2026-09-01)

- Duty-6 docs lenses (A/B/G) grounded in the writing-great-skills vocabulary (owner 2026-09-01 "read writing good skills skill and apply its findings to the docs reviews"). Lens A: SEDIMENT added to the defect list, churn-drift checklist gains (f) LEADING-WORD COLLAPSE (restated phrase-lists/spelled-out triads collapse into one pretrained word — duplication wearing prose). Lens B: NO-OP TEST sentence-by-sentence (a line the model obeys by default is load for nothing), PROGRESSIVE DISCLOSURE (reference behind context pointers; information hierarchy), SPRAWL (too long even when every line is live — cure is disclosure then split, not word-trimming). Lens G: every STEP must end on a CHECKABLE completion criterion (premature-completion defence); ladder-before-split — disclose + regroup for CO-LOCATION tested before any split verdict. Review brief (method step 2) carries the vocabulary reference `skills/writing-great-skills/SKILL.md` to every A/B/G pass.

Issue-Ref: #51

## v0.4.75 (2026-09-01)

- Duty-6 lens roster REGROUPED by target axis (owner 2026-09-01 "Regroup", approving the family proposal): DOCS (A wording · B reading-load · G organization) · TOOLS (E surface-shape · F implementation) · EVIDENCE+LIFECYCLE (C usage-log→proposals · D deletion-safety, C YAGNI evidence is D input). Letters keep chronological birth order — stable report/persist keys, not an ordering; fusion glue stated per family header. SKILL.md role-table row carries the family axis.
- Lens A gains PROVENANCE SEDIMENT element (owner 2026-09-01 "skills need to be scrubbed regularly for unneeded provenance and history — we have changelogs for that"): live rule text carries the RULE, never its biography — owner-directive parentheticals, incident dates, first-pass notes, STRENGTHENED markers move to CHANGELOG.md at ship time.

Issue-Ref: #51

## v0.4.76 (2026-09-01)

HOTFIX — supervisor.md data-loss repair (lens G finding F1/F2, this pass):

- v0.4.75's Duty-6 regroup script dropped the 97-line file tail: method steps
  3-6 + rationale, `## Duty 7` (IDEA/QUIRK box), `## CI-wait & waiter
  discipline` — all physically absent from the shipped file while 5+ live
  inbound refs (editor.md x3, SKILL.md role table + 3 tool rows, README)
  pointed into them. Restored verbatim from v0.4.74 (59439851); regrouped
  roster preserved intact (diff vs v0.4.74 = roster region only, 0 section
  headers touched); 7 reviewer bullets verified once each in family order;
  battery 104/0.
- Lesson queued for lens A: ship gate must verify section presence for every
  file a CHANGELOG entry claims to edit (battery grows a doc-integrity case).

## v0.4.77 (2026-09-01)

Duty 4+6 consolidated verdict — classes 1+2 (owner "Go all"). Class 3 items stay owner-gated.

Docs (class 1):
- Sediment scrub: SKILL.md (24 ops — owner-dates, incident narratives, run-ids moved to §Shared war stories), editor.md, supervisor.md trims; rule text carries the RULE, never its biography.
- README truth fix (B20): local-only claim replaced with real mirror targets (opencrabs-skill + opencrabs-dev-state), tag range v0.1.0…v0.4.76 (150 tags).
- D1: `tools/oc-post-receipts` archived to `tools/archive/`; run.sh re-pointed; archive lib path fallback added.
- Landed owner rules: Reviewer-performance loop (Duty 6 item 7 — supervisor folds reviewer-execution lessons into lens briefs after every pass); gate-idle question sweep (editor.md Phase 5 — idle gate time circles back open questions).

Tools (class 2):
- E2: oc-deploy embed decoding absorbed into `lib/oc-embed.sh` (`oc_decode_job_embed`); both drifted private copies removed (built-sha decode + poll-plan site).
- E3: oc-seal-state contrib-leg extraction delegates to `oc-attrib --trailers-only --range` — single owner of the trailer grammar.
- E4: oc-ledger claim→issue derivation absorbed into `_latest_claim_issue()`; `claim-ref` and `confirm` both consume it.
- F-L1: `--help`/`-h` exits 0 fleet-wide (was 2); unknown-arg usage failures standardized to 2 (oc-seal-state).
- F-L3: post_verify proc reads honor `OC_SWAP_PROC_PREFIX` (testable without touching /proc).
- F-L4: flood-guard documented limit — matches identical tool+args only; varying-arg storms noted as out of scope.
- F-M4: oc-ledger selftest +5 cases (41-45: claim-ref rc contract, unknown uuid).
- F-M5: run.sh section 00b — `lib/oc-embed.sh` unit tests (4 cases).
- C-#6: bare `selftest` verb alias wherever `--selftest` works (oc-ledger, oc-commit, oc-review-persist; oc-wt/oc-ship-audit already had it). Bonus: oc-ship-audit selftest re-invocations now use an absolute SELF path (bare-relative invocation died rc=127).
- C-#7: ledger kind enum is closed to EVERY writer — KINDS admits tool-written mechanical kinds `confirm` + `swap-result`; cmd_stamp normalizes `_`→`-` before the enum check; oc-deploy `ledger_stamp` guards its kind to `swap-result`.

Battery: 104 → 109/0.

Issue-Ref: leshchenko1979/opencrabs#51
Session-Id: a48aa573-91b8-4028-8341-2ba708e66a5b

## v0.4.78 (2026-09-01)

Duty 4+6 consolidated verdict — class 3 (owner "Do the rest"). Mechanics batch classes 1+2 shipped as v0.4.77.

Interfaces (E-lens):
- E5: `oc-prchecks --fault-scope PR` — RED verdict auto-runs `oc-pr-fault-scope` (IN-SCOPE/BASE-FAULT triage line; RED stays rc 3; rc journaled). Selftest 17 → 18/18.
- E6: `oc-attrib --contributors` — 3-col projection (session/issues/shas) owned by oc-attrib; TSV-only (JSON combo rejected); `oc-deploy contributors` delegates (private awk deleted, output unchanged). oc-deploy selftest still 159/0.
- E8: `oc-wt add --create [--from REF]` — fenced escape hatch for PR-head branches off foreign bases: refuses existing branch / unknown --from (rc 5), journals `created branch@from`, un-skippable index chain still runs. Selftest 14 → 17/17.
- E1: editor.md Phase 6c step 2 re-pointed to `oc-commit` as default; raw `--trailer` pair kept as documented fallback (rebase/cherry-pick/harvest).

Diagnostics + rc contract (C-lens):
- C-#1: `oc-prchecks` usage() takes a reason, prints WHY before the usage block; identical-arg rc=2 repeats within 120s back off 2s..10s (60-row storm 2026-08-31); 6 parse sites pass diagnostics; selftest case `usage_diag`.
- C-#3: `--help`/`-h` exits 0 with an Exit: register in 12 more tools (oc-attrib, oc-branch-sweep, oc-carrier-features, oc-ci-parity, oc-drift-check, oc-ping-proof, oc-pr-fault-scope, oc-review-persist, oc-shadow-rotate — unknown-arg 1→2, oc-tg-audit, oc-toolaccum, oc-upstream-delta); NEW `tools/RC-CONTRACT.md` (fleet conventions + 29-tool register); battery section enforces help=0 fleet-wide.
- C-#2: `oc-deploy poll --wait N` (bounded wait, timeout rc 5 + run URL, optional `--notify-session <uuid>` wake on handoff AND timeout; `--wait 0` = classic single pass) — hand-rolled detached poll loops retired; selftest 10b/10c/10d.

Truthfulness + hooks (F-lens):
- F-H1: swap auto-rollback restore legs rc-captured; restore failure journals `rollback exit:1 restore_failed:true` + "MANUAL RECOVERY REQUIRED" stderr; ledger stamps ROLLBACK-FAILED (was: silent success-lie). Forced-failure drill case 11b; test hook `OC_SWAP_ROLLBACK_FAIL`.
- F-M1: drill receipt journal line now lands BEFORE the ledger stamp (matches GREEN leg order).
- F-M2: `ship --execute` writes the `pushed` shadow row (shadow_log parity with the swap leg).

Docs (B/G-lens):
- B4+G-F4: Duty-6 7-lens catalog moved verbatim from supervisor.md to NEW `review-lenses.md`; supervisor keeps the family map + pointer (supervisor.md 329 → 237 lines).
- B11: editor.md Phase 7 retired 2b block deleted; standing rules promoted to Rules bullets (BUILD TRIGGERS = exactly TWO, PR-BASE-PRE-OPEN, PR-GATE-STANDING).
- B12: Phase 7 reference bullets (HARVEST VERIFICATION SWEEP, QUALIFIED FORK REFS) moved verbatim to NEW `editor-phase7-rules.md` behind one-line pointers; §Phase 7 heading kept (cross-refs resolve).

SKILL.md rows updated for every new flag; version 0.4.77 → 0.4.78.

Battery: 109 → 138/0 (C-#3 fleet help=0 section). oc-deploy selftest 155 → 159/0 (C-#2 + F-H1 cases).

Issue-Ref: leshchenko1979/opencrabs#51
Session-Id: a48aa573-91b8-4028-8341-2ba708e66a5b

## v0.4.79 (2026-09-01)

Duty 4+6 classes 1+2 (7-lens review of v0.4.78 + 8 evidence-backed worker proposals; #63 poll-crash incident class).

Tools (battery-gated):
- #63 fix: `oc-deploy poll` iterates the latest runs and SKIPS those with no decodable build-job embed (stale ORDER-gates / pre-rename formats) instead of fatal rc 2 on runs[0]; RED-scan iterates all failed runs; fanout decode-fail marks `decode-error` in fanout.state so a stale run can't block scans forever (selftest 10e/10f).
- Fanout silent-loss paths (lens F HIGH-2): swap-tail fanout rc now journaled (`jline fanout`), green-leg oc-attrib rc captured (was `|| true` conflation).
- `--notify-session` missing-value guarded (die 2) + notify rc captured and surfaced at all poll call sites (lens C MED-1/MED-3).
- `oc-ping-proof` skips an unparseable worker stamp instead of exit 4.
- Usage-reason quartet (lens C MED-2): oc-wt / oc-attrib / oc-tg-audit / oc-carrier-features usage() now takes a diagnostic; bare rc 2 sites print WHY.
- `oc-attrib` bad-range exits 2 per its header promise (was 3); `--repo` missing-value guarded.
- NEW `tools/oc-log-search`: telemetry-only daemon-log search, hard fence against `brain::provider` self-echo (owner-ordered via lane 1a63f103).

Docs (A/B/G-lens):
- `tools/RC-CONTRACT.md` is the SOLE rc register: SKILL.md inline 35-row Exit table collapsed to purpose rows; preamble corrected to EIGHT legacy registers (was "two"); 5 register rows fixed against tool headers (seal-state usage 2→1, artifact-verify/job-verify/pr-atomicity/ledger verdict completion).
- README: source-of-truth → RC-CONTRACT.md; version → SKILL.md frontmatter pointer (never stale again); layout rows for review-lenses.md / editor-phase7-rules.md / RC-CONTRACT.md.
- editor.md Phase-0 truncated rule completed ("...or in a fresh worktree cut from origin/main").
- SKILL.md §Shared war stories table reunited (blank-line split); 4 stale enumeration sites + edit-guard set now list review-lenses.md; glossary Lens entry points at review-lenses.md; supervisor.md CI-wait partition line retired.

Battery: 138 → 139/0 (oc-log-search joins the fleet help=0 loop). oc-deploy selftest 159 → 165/0.

Issue-Ref: leshchenko1979/opencrabs#51
Session-Id: a48aa573-91b8-4028-8341-2ba708e66a5b

## v0.4.80 (2026-09-01) — "Go all" batch 2: class-3 rituals + P1–P8 + lens-B MEDs + #63 close + subagent-death report (owner "Go all: class 3 + P1-P8 + lens-B MEDs + close #63 + file subagent-death issue")

Duty 4+6 run-2 residual classes, executed as one pass on base v0.4.79:

- CLASS 3 RITUALS: E-1 — editor.md Phase-7 harvest step re-pointed to `oc-wt add --create --from adolfousier/main` (v0.4.78 built the flag for exactly this ritual; the old raw `worktree add -b` text taught a false "oc-wt never creates" interface fact; raw add demoted to documented fallback).
- DUTY-4 P1–P8 ADOPTED (all evidence-backed, 2026-09-01 incidents): P1 waiter notify payload-validation law (unfilled run-id wake = garbage evidence, CI-wait item 10); P2 oc-prchecks detaches-or-fails-fast, inline orphan false-RED lesson (item 11); P3 cross-repo `--head OWNER:BRANCH` law documented (the bare form fails "No commits between", adolfousier/opencrabs#1277 filing); P4 base-freshness check (step 2-fresh) before harvest gate dispatch; P5 per-run-id journal filenames (item 12); P6 rustfmt = non-fatal diagnostic pre-pass (Phase 4); P7 post-fmt scope audit before staging — flow.rs:418 lesson (Phase 4); P8 full shas from rev-parse only, never completed from a remembered prefix — incident n=1452 sha-fabrication (item 13).
- LENS-B MEDs: F3 REBASE-PORT re-homed from the archived compiler runbook to supervisor.md §Upstream sync (watch/port/parity, boundary note carried; "until re-homed" stopgap retired; archive keeps pointer); F4 fan-out GREEN/RED leg internals + journal vocabulary moved to s2-swap-journal-spec.md §Fan-out legs (§Session-notify loop keeps one line); F5 session-notify DELIVERY MODES bullets → 4-row table; F6 war-stories table disclosed to war-stories.md (SKILL.md keeps pointer; README row added); F7 Compiler archaeology dropped (frontmatter clause, role-table row compressed, archived-role bullet deleted); F9 Phase-6a ship-semantics wedge → one line; F11 Duty-3 wall → situation/action table; F12 CONSENT REGISTER compressed (oc-consent-check obituary → CHANGELOG pointer); F14 pre-v0.4.60 raw dump sequestered as labeled block at file top (newest-LAST contract restored); F15 SKILL.md sheds ~40 lines net via F4/F6/F7.
- ARCHIVE: oc-post-receipts verified already at tools/archive/ since v0.4.77 (lens-D ARCHIVE finding was already satisfied; zero stale refs).
- BATTERY 139/0 (receipt battery-last.json). Fork issue leshchenko1979/opencrabs#70 filed (subagent-death: tombstones addressed to dead child's session, wiped on restart — report-only, fix proposal staged); leshchenko1979/opencrabs#63 CLOSED (fixed in v0.4.79, commit 0e982983).

Issue-Ref: leshchenko1979/opencrabs#51
Session-Id: a48aa573-91b8-4028-8341-2ba708e66a5b

## v0.4.81 (2026-09-01)

- LENS REGROUP (owner word "I like this" on the grouping diagnosis): family identity is now explicitly the OBJECT under review, not the evidence flow between lenses. Reviewer C moved from EVIDENCE+LIFECYCLE into FAMILY TOOLS (gaps/shape/implementation pipeline: C proposes, E shapes, F builds/verifies; boundary watch vs A/B added). FAMILY ARTIFACTS = Reviewer D sole member (files/state/ledgers/flags — the family IS the deletion owner gate); C→D YAGNI feed and C→E rc-cluster feed survive as cross-family arrows noted in the headers.
- LENS CENSUS (supervisor.md step 7): every consolidated verdict appends a per-lens census (yield/overlap/cost) computed from persisted reports; standing owner-gated triggers — clean x2 → automate or shrink brief; convergence x2 → merge or sharpen boundary; stale object list → re-brief before spawn. Anti-rules: no lens-per-incident, no auto-growth.
- G brief object list de-rotted: enumeration replaced by spawn-time `ls *.md` re-derivation (role files + split-out reference pages) — objects rot, dimensions don't.
- Map lockstep: supervisor.md Duty-6 step 2 = DOCS=A,B,G · TOOLS=C,E,F · ARTIFACTS=D.

Issue-Ref: leshchenko1979/opencrabs#51
Session-Id: a48aa573-91b8-4028-8341-2ba708e66a5b

## v0.4.82 (2026-09-01)

Tool-problem reports rewire (owner order 2026-09-01 22:2xZ):

- supervisor.md Duty 7 item 5: QUIRK reports (failures, inconsistencies, quirks — rc out of register, silent no-op, corrupt output, doc/behavior drift) go to the HQ lane, not the supervisor idea box; no self-patching even in the reporter's own area.
- supervisor.md Duty 7 item 6 (NEW): HQ triage & routing — verify evidence, route the fix to the owning editor lane by TOPIC name, or create a new editor per the standing authority; `idea-verdict` ROUTED names the target; fixes ship through the normal editor flow.
- editor.md: lane duty mirror — tool problems to HQ same turn (`QUIRK:` format), fallback target = supervisor lane; never sit on a broken tool.

Issue-Ref: leshchenko1979/opencrabs#51
Session-Id: a48aa573-91b8-4028-8341-2ba708e66a5b

## v0.4.83 (2026-09-01)

- oc-deploy: fanout/poll wake retried once with --interrupt on refused_in_flight (rc-3-only; retry rc replaces first attempt's) — the lost-report class (da6a4ef7, #74).
- oc-prchecks: `resume <run-id>` re-attaches to a witnessed run, skips dispatch/adoption — re-polls can no longer re-dispatch and auto-cancel the resumed run (n=1401 false-RED exposure closed) (434950d9, #74).
- tools/oc-waiter: canonical detached wait+notify tool (arm/_run/list/sweep) — payload validated BEFORE notify, rc-3 --interrupt retry, NOTIFY-FAILED exit 4, reboot-durable STATE_DIR journals, sweep watchdog ORPHANED wakes owner+HQ, stall escalation, rc-6 bounded re-arm (20de961e, #74).
- editor.md item 10 + supervisor.md W4: oc-waiter is THE standard detached wait+notify path; hand-rolled pollers forbidden; re-attach = oc-prchecks resume.

## v0.4.84 (2026-09-03, owner order 2026-09-03 20:31Z via A3 lane housekeeping) fleet-directives § Tool-problem reports now names OC DEV HQ as THE supervisor lane for tool-use anomalies (failed invocations, wrong args, false journal rows, misreads surviving into claims, unbacked persistence claims) — supersedes the 2026-09-03 20:01Z interim routing to the Carrier tools session (that lane stays a notification target, not supervisor of record). Lane c10cd97b authored the directive edit (082cde93); HQ Duty-1 bump+push this entry. ops AGENTS.md § Tool anomaly routing mirrored (line 159).

## v0.4.85 (2026-09-06, owner "Approve all" 04:38Z — Duty 4+6 fix batch; HQ-authored, session d72bd52d-42aa-4dbd-ac99-5b5300770019)

- SKILL.md §Upstream relations item 2 + supervisor.md §Upstream sync: sync model re-ruled MERGE-ON-ARRIVAL (owner 2026-09-02 "Land it") — REBASE-PORT text RETIRED (dangerous: a lane following it would force-push fork main against the merge-never-rebase law); procedure pointer → upstream-merge-runbook.md (lens G1/A-F1 HIGH).
- SKILL.md §DELIVERY MODES: defaults flipped per 2026-09-04 22:31Z cadence law — quiet DEFAULT, turn-end boundary-bound, now urgent-only, never start at now; escalation path documented (lens G2 HIGH).
- SKILL.md: 2 truncated tool-register rows repaired (oc-review-persist, oc-wt — unescaped pipes ate cells) (G3); "seven/7-lens" → eight lenses incl. brain-scrub (G4); OC_ACTOR export law added to §Shared environment facts (G6); §Hard rules skill-file census extended to fleet-directives.md + current root .md files, mirrored in supervisor.md Scope (G7).
- supervisor.md Duty 3: interrupt-first wording → cadence-law delivery path (quiet default, interrupt=true failsafe only for blocking wakes).
- DRIFT PERMANENT deduped: SKILL.md canonical, supervisor.md pointer (A-F2).
- editor.md:757 bare force-push → --force-with-lease (D-6).
- fleet-directives: 3 accepted Duty-4 theme-1 proposals landed (upstream-PR Lint pre-claim; cross-fork head fetched from fork remote; truncated-window verification is not verification) + F13 resolution (rule-text provenance = CHANGELOG at ship time, no biography in rules) + F5/F6 laws landed in skill (daemon no-reap ruling 1273; inherited-claim three-pillar verification).
- Brain scrub (owner-approved shrinks): AGENTS.md lane-briefing + delivery-cadence bullets → pointers (canonical richer at fleet-directives:86 + §delivery); MEMORY.md stale law scrubbed — modum sanction retired (toolchain note updated), hand-rolled cron-poller watcher pattern marked superseded by oc-waiter (editor.md item 10).
- Review persists (phantom #6 recovery, n=1592): lens E + deletion-safety(D) + G re-persisted with real sha256 index receipts; B/C/F re-runs landing.
- Known debt queued (explicitly NOT in this bump): oc-waiter JSON-orphan loud failure (lens F), shadow-rotate/seal-state flock (D-1/D-2), oc-deploy ledger_stamp atomic pattern (D-7), harvest-sweep patch-id per-commit fix + lib/oc-patchid.sh (E-1 HIGH), OC_GIT collision rename (E-2 HIGH), fork-slug consolidation (E-3/E-4), --help stdout (E-5), #74 canonicalization after F lands.
- Housekeeping: war-stories.md gains the #96/#98/#102/#108 Mermaid×buttons resolution entry (authored by the shipping lane 1a63f103, committed here with provenance); battery-last.json refreshed by this batch's battery run.

## v0.4.86 (2026-09-06, owner "Go with Option A" ~06:3xZ — split Triage lane from HQ; owner-direct execution via the ops droid)

Supervisor-lane split: interrupt-shaped duties carved out into a new TRIAGE lane so HQ keeps uninterrupted deep-work windows (skill authoring, procedure rulings, review batteries, upstream sync). Docs-only batch; single-writer law UNCHANGED (only the Supervisor edits skill files); ledger two-writer safety = `oc-ledger` flock.

- NEW `triage.md`: TRIAGE role file — T1 idea-box intake (ex supervisor.md Duty 7 items 1–4), T2 QUIRK intake + fix routing (ex items 5–6), T3 new-editor creation (standing authority transferred from HQ), T4 enforcement patrols (oc-tg-audit TOOL_ACCUM + delivery-cadence), escalation law to the Supervisor (quiet/turn-end per cadence law). NEVER list: no skill-file edits, no builds/swaps, no rulings, no owner verdict tables.
- SKILL.md: frontmatter description names TRIAGE; Owns paragraph THREE role files; STEP ZERO prompt + role-table TRIAGE row + SUPERVISOR row re-scoped (intake delegated); Roles-DO-NOT-intersect bullet; glossary entry; Hard-rules census gains triage.md; TOOL_ACCUM pointer → triage.md T4; "(all roles)" plurals.
- supervisor.md: header carve-out note (authorship stays SOLELY Supervisor); Duty 7 retitled pointer section (channel policy unchanged; batch/verdict ownership stays at HQ); TOOL_ACCUM block → pointer to triage.md T4.
- fleet-directives.md: §Creating new editors — TRIAGE lane creates (HQ keeps roster/registry ownership, supervisor.md Duty 2); §Tool-problem reports — retitled TRIAGE-lane intake / HQ supervisor-of-record, intake → OC DEV TRIAGE (session_search discovery, never uuid-from-memory), escalation item added; owner-order provenance (2026-09-01 22:2xZ, 2026-09-03 20:31Z) preserved.
- editor.md: lane-duty mirror retargeted — IDEA/QUIRK reports → Triage lane (OC DEV TRIAGE), fallback target = supervisor lane (OC DEV HQ); oc-waiter ORPHANED owner+HQ lines untouched (HQ stays escalation target).
- Pre-bump gate: oc-deploy --selftest 184 pass / 0 fail; battery tools/tests/run.sh 144 PASS / 0 FAIL (receipt refreshed).

## v0.4.87

- TOOLSMITH lane carved out — the CLI tool lane that makes and fixes the CLI tools every other role uses (owner word "Go toolsmith" 2026-09-06). PROMOTED from the carrier-tools editor row (topic 39171, rostered since 2026-09-01) — same session, no new topic/spawn.
- toolsmith.md (NEW): NEVER list (no skill markdown, no daemon/carrier source, no builds/swaps, no rulings, no owner verdict tables); Duty S1 owns `tools/` code — author + fixer, transferred from the Supervisor at v0.4.87 (battery receipts mandatory, RC-CONTRACT register discipline, HQ vocabulary fixes execute here); Duty S2 battery stewardship; escalation to the Supervisor per cadence law.
- SKILL.md: version 0.4.87; frontmatter names TOOLSMITH; FOUR role files; STEP ZERO prompt + table row; roles-do-not-intersect bullet; glossary entry; census — `toolsmith.md` added, `tools/**` becomes the ONE exception owned by the TOOLSMITH lane (skill markdown stays Supervisor-only).
- supervisor.md: header carve-out note + Duty 1 bullet — `tools/**` code authorship moved to the TOOLSMITH lane; Supervisor keeps skill markdown, CHANGELOG, version bumps, fleet-directives.
- fleet-directives.md: §Tool-problem reports — item 3 routes `tools/` CLI fixes to the TOOLSMITH lane; carrier-tool channel promoted to the TOOLSMITH lane (vocabulary fixes execute there; HQ skill text still lands via TRIAGE intake).
- triage.md: Duty T2 item 3 — `tools/` CLI code routes to the TOOLSMITH lane, every other area to the owning editor.
- editor.md: QUIRK mirror bullet — `tools/` CLI code to the TOOLSMITH lane, everything else to the owning editor.
- Pre-bump gate: oc-deploy --selftest 184 pass / 0 fail; battery tools/tests/run.sh 144 PASS / 0 FAIL (receipt refreshed).

## v0.4.88 (2026-09-07, owner "Reload skill" 11:24Z — telegram_send error-audit law adoption)
- fleet-directives.md gains FOUR sections from the 2026-09-07 telegram_send error audit (owner-adopted): (1) AS-IS law — explicit chat_id + thread_id on EVERY forum-group telegram_send, ids sourced from the incoming [Channel] header or list_topics; omission is not a routing mode (the dominant failure, "message thread not found", came from stale last-seen-topic memory). (2) TO-BE target — omission semantics: omitted chat_id+thread_id = same-topic origin send; never a route to the owner DM. (3) TO-BE target — landing echo: successful sends echo resolved chat_id + thread_id/topic name so misdelivery is visible to the caller. (4) Explicit-thread_id guidance.
- Routing-law mirror: AGENTS.md:128 (HQ board routing = decision-points only) + :129 (stamp/write claims need same-turn tool receipt) — persisted 2026-09-07 08:20Z after a verified phantom-stamp incident; mirrored here for skill-side provenance.
- Doc-only bump: no tools/ changes, battery unchanged (144/0).

## v0.4.89 (2026-09-07, owner "All 4 go" — Duty-6 7-lens review mechanical batch, lens A/B/G findings)
- SKILL.md: family map fixed — DOCS A/B/G / TOOLS C/E/F / ARTIFACTS D (sole deletion safety), replacing stale "TOOLS E/F" + "EVIDENCE+LIFECYCLE C/D" (A11/B-9, would mis-brief Duty-6 spawns); tg-audit tool row repointed supervisor.md Duty 7 A12 → triage.md T4 (A12); sync-law site 2 → pointer to fleet-directives canonical (A3); delivery-escalation ladder → pointer to fleet-directives (A5); glossary: "Lane" extended to all role sessions (A7), "disk absorption" DEFINED at its 4th use site (A16); box-law references tagged "(box law)" with editor.md §Box law canonical (B-12).
- fleet-directives.md: telegram_send double-statement merged — "Explicit thread_id on forum sends" (:204) folded into the AS-IS addressing law (A6/G-F1); Triage T2 procedure copy deleted, pointer-only per own header law (A1/B-4/G-F2); stale "Duty 7" ref → triage.md §Duty T2 (G-F3).
- supervisor.md: Duty-7 procedure copy trimmed to policy + pointer, verdict taxonomy/INBOX mechanics → triage.md (A2/G-F4); PROCESS-TOOL OWNERSHIP corrected to the v0.4.87 Toolsmith carve-out (B-1 contradiction vs its own Duty 1); CI-wait count 1–9 → 1–13 (A18, disk-verified).
- upstream-merge-runbook.md: "Carrier tools lane" → "TOOLSMITH lane (ex carrier-tools, v0.4.87)" (A10/G-F6).
- README.md: TRIAGE + TOOLSMITH rows added to Roles table (A14/B-11); "30 executables" → 31 (A17/B-10, `ls tools/oc-* | wc -l` = 31).
- review-lenses.md: lens-G brief drops hardcoded "three role files" count (G-F8); s2-swap-journal-spec title "(proposal)" retired — live since v0.4.62 (A13).
- editor.md: "generic CI ritual" coinage → CI gate §Glossary (A15); FIRE coinage defined (A8); toolsmith.md "review battery" defined (A9); triage/toolsmith escalation boilerplate → pointer to fleet-directives cadence law (A19); "re-reads role file at turn start" no-op line removed (B-13).
- Mechanical only — no semantic changes; the 2 Duty-4 proposals (dispatch-receipt gate, solo-surface rule) + B-15/B-16/B-17 + lens-E merge + owner-word deletions ship separately per owner word.
- Doc-only bump: no tools/ changes, battery unchanged (144/0).

## v0.4.90 (2026-09-07, owner "All 4 go" — Duty-4 proposals + lens E/B semantic batch)
- EDITOR.md item 14 NEW — **Dispatch-receipt gate** (Duty-4 proposal d5863180, ACCEPT KERNEL): dispatch rc==0 + adopted run id witnessed BEFORE arming any waiter/notify; waiter rules validate the WAITER, this gate validates the DISPATCH (evidence: 2026-09-07 --notify-session invented-flag near-miss). Items renumbered (old 11–13 → 12–14); item 15 NEW — **Solo-surface rule** (Duty-4 proposal, ACCEPT KERNEL): side-effect commands minting identifiers (gh pr create et al) run SOLO in batch so output is witnessed; batched/truncated → identifier UNFILED until fresh verification call names it (root cause of the #1272 phantom-PR).
- EDITOR.md Phase 6a: lens-E F-1 one-command ship shape (`ship --execute --wait N`) disclosed as GOAL — tool change lands via TOOLSMITH; two-step poll documented until then. Phase 7b: B-16 split note (editor-upstream-pr.md designated candidate, disclosed not executed per lens G). oc-deploy contributors citation → oc-attrib --contributors.
- SKILL.md: oc-deploy `contributors` verb RETIRED (lens E-2 — verb-duplicate of oc-attrib --contributors, "thin wrapper" admission SKILL.md:58); oc-attrib --contributors = single shape; oc-prchecks tool row trimmed to invocation+purpose+pointer (B-15 — mechanics lore lives in RC-CONTRACT + fixtures, ~150 ln/role-load saving).
- fleet-directives.md: thematic index added (B-17/G-F9 — flat file kept, 6-theme jump list).
- supervisor.md: CI-wait cross-ref count 1–15 (14th dispatch-receipt gate, 15th solo-surface rule).
- Doc-only bump: no tools/ changes this version (oc-waiter first-poll-GREEN hole, Session-Id unification, poll --wait check order etc. = TOOLSMITH dispatch, separate version); battery 144/0.

## v0.4.91 (2026-09-07, owner "let's finalise skill changes" 15:07Z)
- supervisor.md Duty 2 = registry writes → Triage ENTIRELY (owner law; closes the v0.4.86 creation-transfer's registry half; HQ residual deleted), ack contract REVISED (acks no longer expected — notify receipt = delivery proof, drift-check = comprehension guard); Duty 3 = PUSH-ALL-QUIET (every bump → all non-dormant workers quiet, no "touches duties" judgment) + Confirm law (probe-verified: quiet+confirm = no-op watch; confirm reserved for now-mode critical, blocking verdict there); Duty 4 step 2 = reply surface named (session_notify target=HQ full UUID, never own chat). editor.md item 16: PR-state claims need same-turn gh pr view receipt (headRefOid+headRefName+state) — #1431 "auto-updated" phantom, force-push ≠ PR-head move; event+branch+sha ALL match before waiter arm. Battery clean-HEAD 144/0 PASS (1-fail run = TOOLSMITH oc-prchecks WIP, isolated via stash, unrelated).

## v0.4.92 (2026-09-07, owner "A. Triage should check new issues after each compaction" 17:23Z — backlog-assignment gap closed)
- Doc-only bump: no tools/ changes. Battery on clean HEAD: see receipt below.
- supervisor.md Duty-7 pointer updated: idea box AND backlog sweep both live at Triage (T1 + T5).
- triage.md Duty T5 NEW — **Post-compaction issue sweep** (owner order 2026-09-07 17:23Z): after every compaction, Triage reloads the skill then sweeps OPEN fork issues (`gh issue list`, fresh receipt) against workers-ledger claim-refs; unclaimed set → route to owning editor (T2) or surface to Supervisor. Sweep SURFACES, never disposes — closure stays harvest-law-gated. Closes the v0.4.91 finding: "claimed when someone claims it" is not assignment; an issue could sit silent forever with no sweep duty.

## v0.4.93 (2026-09-07, owner "go all" 18:11Z — Adolfo-protocol amendment, all 6 items)
- Origin: owner order 2026-09-07 18:00Z "Read my today's dialogue with Adolfo and agree rule changes with me" → 6-item proposal → "go all". En-route cancellation: the 17:44Z #1438 re-port order (old 2-fresh law) was WITHDRAWN before this bump; #1438 stays frozen at 6cfae040/base 221d7423.
- Post-merge scope unchanged: fork-side sync to new upstream main stays owner-gated [GATE] (runbook). CI-receipt rule unchanged (item-16 + job-name sha pin already encode "green at push").
- upstream-merge-runbook.md harvest-lane row: merge window does NOT unfreeze filed PRs; no re-ports triggered by fork-side sync.
- editor.md Phase 7b blocker table rows 1–2 amended: CI-fix row gated by freeze check; conflicts-with-main row reassigned to MAINTAINER (was: editor rebase + force-push — the exact anti-pattern that broke #1426/#1427).
- editor.md Phase 7 **FINAL-PR STANDARD**: file only genuinely final work (green at push, no known gaps); force-pushes on filed PRs = rare exception, never procedure. Fork = workspace, upstream PR = one-way handoff.
- editor.md 2-fresh **scope narrowed to pre-filing** — base-freshness/re-port governs fork-internal work only; after filing, conflicts are maintainer-side (MAINTAINER-SIDE MERGES rule: "merge locally, fix conflicts on top, push, comment what you did").
- editor.md Phase 7 **PR-FREEZE LAW**: an upstream PR is FROZEN at filing (CI green at push) — no re-port, no force-push, no head/body changes, even if upstream main moves. Rationale from Adolfo's own words ("Once you push it, you already did your job") + today's live incident: #1426/#1427 rebased 15:56 → maintainer merged old heads locally 17:22 → sha mismatch → auto-close defeated, manual close. The ONLY valid re-engagement: maintainer explicitly asks.

## v0.4.94 (2026-09-07, owner "go" 19:02Z — tool-discovery gap: 13 of 31 tools invisible to editors)
- Doc-only bump: no tools/ changes. Battery on clean HEAD: see receipt below.
- editor.md tool-table intro now cites RC-CONTRACT.md as the canonical inventory alongside SKILL.md.
- editor.md reload section item 5 NEW — **Tool discovery clause** (owner order 2026-09-07): the editor tool table is the role-DAILY subset, not the inventory; full 31-tool inventory lives in `tools/RC-CONTRACT.md`; editors grep RC-CONTRACT.md for a purpose-built tool BEFORE hand-rolling any check (item 11). Closes the v0.4.94 finding: 13 of 31 tools (oc-artifact-verify, oc-carrier-features, oc-ci-parity, oc-harvest-sweep, oc-job-verify, oc-log-search, oc-ping-proof, oc-review-persist, oc-shadow-rotate, oc-ship-audit, oc-skew-scan, oc-tg-audit, oc-toolaccum) were never named in any editor-readable file.

## v0.4.95 (2026-09-07, owner "fix it" 19:47Z — fleet-directives load-path: lanes never told to read it)
- Design note (owner question 19:47Z "why keep a separate fleet-directives file?"): directives stay a separate file because (a) single-writer law — role files are written by the Supervisor, but directives are owner rulings collected verbatim with provenance, a different write cadence and different review lens; (b) size — merging ~30 sections into SKILL.md would bloat the always-loaded file past its keep-lean budget; (c) the gap was never the split, it was the missing load path — now closed by the RELOAD LAW instead of a merge.
- **fleet-directives.md `[LANE]` tags** on 7 sections every worker must read in full: Telegram surface law, Post-compaction reload, PR naming, Features-compat gate, Cross-lane delivery cadence, Upstream PR base-Lint pre-claim, telegram_send addressing rule. Thematic index explains the tag.
- **RELOAD LAW, four roles** (owner order 2026-09-07 19:31Z "fleet-directives is not read by lanes at all" + 19:41Z "what about supervisor?"): after compaction or spawn, workers re-read from disk SKILL.md + role file + `fleet-directives.md` (thematic index minimum, `[LANE]`-tagged sections in FULL). Inserted: editor.md Phase 1 step 0 (claim-time re-read), triage.md + toolsmith.md + supervisor.md headers (supervisor previously had NO self-reload mandate at all). Rationale: briefs die at compaction; binding owner law (cadence, PR naming, telegram surface, upstream etiquette) lives on disk, not in session memory.

## v0.4.96 (2026-09-07, owner "Go + parked" 21:14Z — Duty-4+6 cycle-2 mechanical batch + parked owner-word deletions)

- **Parked deletions (owner-word gated, executed):** 4 closed-chain branches deleted local+remote on the fork repo — `fix/69-restick-interrupt-turns`@9c8d13bc + `fix/92-demoted-host-guard`@1097b444 (both merge-base-verified IN main), `fix/69-restick-upstream`@45f35190 + `leshchenko1979/fix/92-demoted-host-guard`@3c4ac6c0 (patch-verified content-identical to landed). Worktree `oc-wt-69-interrupt-restick` force-removed (held only 9 untracked gate journals, verified first).
- **P0 (fleet-blocking, verified):** oc-prchecks:533 `OC_PR_SKIPPED_DISPATH` typo (TOOLSMITH commit 1a82bdc2) — C-F2 "adopt instead of re-dispatch" re-dispatch class killed; selftest no-re-dispatch guard added.
- **Lens B (efficiency/sprawl):** SKILL.md BUDGET RULE added (review-lenses.md new family block; 4x multiplier, router-only scope, RC-CONTRACT = SOLE register, B-F3/F18); delivery-modes table in SKILL.md cut to pointer + failsafe row (B-F15, fd canonical); REBASE-PORT 7-step procedure moved supervisor.md → upstream-merge-runbook.md §Port (B-F16); supervisor Duty 7 T4 procedure copy → one-line pointer (B-F11); no-op clause deletions — SKILL.md "no cargo, no compile, ever" reassurance (B-F12), toolsmith header Duty-S1 restatement (B-F13), triage T1 item-1 weak restatement (B-F14); fd [LANE] tag def gains SUPERVISOR-reads-IN-FULL exception (B-F1); supervisor Duty-3 bump cell → PUSH-ALL-QUIET pointer + numbered mechanics list (B-F4); editor.md RELOAD LAW header block added post-"Load only after…" (B-F2/G-5).
- **Lens A (redundancy/ontology):** fd CI-wait "items 1-9" -> "items 1-16" with correct ordinals (A-1/G-F9, third-pass churn); supervisor ordinal map corrected (10th = dispatch-receipt gate, 15th solo, 16th PR-state; since v0.4.91, A-2/G-2); editor item-10 self-cite -> items 4/11 (A-3); contributors RETIRED date settled v0.4.91 x2 (A-4/F-11); dead fixtures path -> run.sh selftests (A-5); RC-CONTRACT seal-state self-contradiction fixed — v0.4.79 "corrected 2->1" note was WRONG, live tool verified badflag=2/bare=1 (A-6); "review battery" name collision killed -> SELFTEST BATTERY (A-8); war-stories modum RETIRED markers + past tense (A-10); BUILD TRIGGERS restatement -> SKILL.md pointer (A-11); SYNC-LAW honest-label rewrite (A-12); fd TO-BE telegram_send paragraphs moved out of [LANE] AS-IS section to own non-[LANE] section at file end (A-13); s2-spec consent journal row RETIRED-marked + "auth (auto-swap)" reword (A-14); supervisor-write census gains README.md + tools/RC-CONTRACT.md (A-15); dead "ex Duty 7 items 5-6" locators removed x2 (A-16); oc-order-validate rc 4 UNKNOWN-REF added (A-17); FIRE glossary entry (G-7); census/dead-path/G-9/G-10/G-11 locator fixes; G-6 disk-absorption reword; G-8 CHANGELOG reordered to newest-LAST contract (era blocks now 90->95 in order, orphan bullets re-homed by provenance).
- **Tool fixes (oc-deploy, HQ-executed per verdict):** E-F1 ship mode dies 2 on `--wait`/`--notify-session` (poll-only flags were silently ignored — false-receipt trap) + 4 new selftests; E-F2 red_leg trailer extraction -> unified `oc_session_trailer` last-wins helper at all 4 sites (old first-wins grep could wake the WRONG LANE); E-F3 green_leg -> direct `oc-attrib --contributors` call, private awk projection deleted; F-4 rc-4 features-compat gate + `--allow-features-drop` documented; F-5 usage strings x3 synced + `--allow-features-drop`; F-7 features-mismatch shadow_log row `"-" "$FEATURES"`; F-12 oc-review-persist rc row completed (3 sha256-mismatch / 4 write-failure); O1 poll `--wait` non-integer = die 1 (code+battery agree, was misdocumented 2).
- **Lens reports archived:** reviews/20260907-duty46-cycle2/ — 38 report files (7 lenses x 2026-08-29->09-07 incl. cycle-1/2 variants) + skill-review-index.log (oc-review-persist sha-indexed).
- Battery: 146 PASS / 0 FAIL (146th = new E-F1 ship-refused pair; prior 144 + 2).

## v0.4.97 (2026-09-08, owner "Go" 05:30Z — harvest enforcement law: daily patrol + standing filing order)

- **HARVEST LAW** (fleet-directives.md §Upstream-merge cadence): merge-from-upstream on every detected shift was already law, but nothing ever fired the give-back direction — 156 fork-only commits piled up demand-driven. New standing order: Duty T4 harvest patrol runs DAILY (cron `harvest-patrol-daily` 03:00Z, first run 2026-09-09); census posts to board topic 30220 every day even on zero-change days (heartbeat = patrol alive); `upstream-shift-watch` (4h) carries the same HARVEST COUNTER line. Standing autonomous-filing order: fork-only backlog ≥3 Tier-1 candidates AND zero open upstream PRs of ours → Triage files the top candidate autonomously (cherry onto upstream base, green at push, frozen at filing, one at a time per one-PR law). Beyond the standing order the full Upstream PR law (owner smoke-PASSED gates) still applies.
- triage.md Duty T4: new patrol item — run `oc-upstream-delta`, post tiered census + counter (Triage owns it post-compaction too).
- Battery: 146/0. Tag v0.4.97, commit 73d31e8a, ledger n=1987. #129 build ebbae0a SWAPPED 05:38Z same turn.

Daily harvest enforcement: the 145-commit fork-only backlog grew because harvesting was purely demand-driven (no trigger ever fired it). Owner ruled "at least daily" — three pieces:

- **HARVEST LAW (fleet-directives.md, §Upstream-merge cadence):** DAILY patrol — cron `harvest-patrol-daily` (03:00Z) runs `tools/oc-upstream-delta`, posts the tiered backlog census (Tier-1/2/3 + counter line: fork-only commits + open upstream PRs) to board topic 30220; the counter line is also appended to every `upstream-shift-watch` (4h) report. Zero-change days still post a one-line census (heartbeat = patrol alive).
- **Standing harvest order (same section):** census shows ≥3 Tier-1 candidates AND no upstream PR of ours is open → Triage files the top Tier-1 candidate autonomously — cherry onto upstream base, 4-leg verify, CI green at push, frozen at filing (v0.4.93 PR-freeze law), ONE at a time (one-PR law). Beyond the standing order, the full Upstream PR law (owner smoke-PASSED gates) still applies.
- **Duty T4 (triage.md):** harvest backlog patrol added as a standing enforcement item with the same mechanics, so Triage owns it post-compaction too (RELOAD LAW reaches it).
- Cron `harvest-patrol-daily` created (03:00Z daily, delivers census to topic 30220); `upstream-shift-watch` prompt extended with the counter line.

## v0.4.98 (2026-09-08, owner "Decision Rollcall" term pick ~06:1xZ, topic 42487, ruling n=1994 — lane→owner direct decision sweep)

- **Decision Rollcall codified** (owner picked the term via buttons; Triage proposed shape, HQ finalized wording): repeatable owner-facing procedure, distinct from T5 sweep and Duty-4. Content = outstanding owner decisions ONLY (one decision + lane recommendation + one-line context; no status reports, no chatter). Delivery = each lane posts IN ITS OWN LANE TOPIC, addressed to the owner DIRECTLY — no relay through Triage/HQ; zero decisions = silence, no chatter post. Triage = trigger on owner word + coverage verification + ledger stamp, nothing more. Trigger = on demand ("run a Decision Rollcall"); no cron/hook unless the owner orders one later.
- **Codification homes:** fleet-directives.md §Decision Rollcall (canonical law, after the what-now/next section); editor.md §Decision Rollcall duty (lane-side posting duty, after Mid-cycle skill drift); triage.md NEW Duty T7 (trigger/coverage/stamp; relay model of 2026-09-08 morning RETIRED).
- **#119 naming-collision note** (Triage flag, verified distinct): fork issue leshchenko1979/opencrabs#119 (single-option fold UX, Harvest-filed) ≠ upstream-numbered #119 (single budget verdict, `55ddec34`, already shipped). Rename/qualify ruling stays Triage's at next triage pass.
- Battery: see receipts below. Includes v0.4.97 era reorder fix (97 block had landed after the Imported dump — now 96→97→dump).

Owner-ruled procedure for sweeping outstanding owner decisions across lanes:

- **fleet-directives.md §Decision Rollcall** — canonical law: lanes post owner-decisions-ONLY lists in their own topics, addressed to the owner directly; Triage triggers on owner word, verifies coverage, stamps the ledger; the morning relay-verbatim model is explicitly RETIRED. Zero owner decisions = sanctioned silence (no chatter posts).
- **editor.md §Decision Rollcall duty** — lane-side: one decision + recommendation + one-line context each; missing topic post = coverage chase lands on the lane.
- **triage.md NEW Duty T7** — trigger/coverage/stamp mechanics; Triage never relays, aggregates, or answers for a lane; Triage's own decisions post in the Triage topic like everyone else.
- Fork-issue #119 (Harvest-filed single-option UX) vs upstream #119 (shipped `55ddec34`) — collision note added to the verdict-table lineage (Triage to rule on rename/qualify at next triage).
- CHANGELOG: the v0.4.97 block had landed after the "Imported pre-v0.4.60 dump" — moved to newest-LAST position.

## v0.4.99 (2026-09-08) — Decision Rollcall format law (owner amendment, topic 30220)

Owner amendment minutes after codification — five format rules added to all three law sites (fd §Decision Rollcall items 5–9, editor.md format-law block, triage.md Duty T7 step 6):

- **No acks** — the decisions post IS the acknowledgment; no confirmation chatter.
- **No telegram_send** — Rollcall posts are the topic's final chat message (text auto-posts); media/document sends forbidden.
- **Context + diagrams** — every decision carries context and, where it has shape, a mermaid diagram (owner judges renderings, not descriptions).
- **1 by 1** — one decision per message, sequential posts, never a batched wall.
- **Owner gates designs and special cases** — lanes present, never self-implement on their own recommendation.

Triage enforces the format on coverage check (targeted lane correction, not board complaint). Mechanical amendment; battery expected unchanged except version stamp.

## v0.4.100 (2026-09-08) - oc-deploy poll ship-pending law (Triage disposal n=2003, HQ implemented)

- oc-deploy poll --sha S: the DISPATCHED sha going GREEN is SWAP PENDING - poll no longer dies rc5 already-deployed while the deployed marker lags mid-chain. Defect family n=2003 ate the 2e161df3 and ebbae0aa swaps; both recovered only by lane re-execute.
- Poll --wait timeout on a GREEN dispatched sha reports STUCK SWAP (distinct message + notify-session wake), never nothing-new.
- New selftest: poll --sha pending never reports already-deployed. Battery 147/0.

## v0.4.101 (2026-09-08) — Decision Rollcall present-here mode

- Owner amendment 2026-09-08 08:34Z, topic 42487 (Present decisions here): Rollcall delivery gains present-here mode — on owner word, Triage collects lanes outstanding owner decisions and presents ONE consolidated numbered list in the owners topic (decision + recommendation + context + diagram per item; faithful relay, no filtering/paraphrasing/ranking). Lane-direct posting remains the default mode. Sites: fleet-directives.md section Decision Rollcall item 2 (two-mode delivery), triage.md Duty T7 item 7, editor.md Decision Rollcall duty present-here exception. Lane-side format law unchanged.

## v0.4.102 — Decision Rollcall: present-here mode RETIRED (owner override)

Owner override 2026-09-08 09:05Z, topic 30220 ("I don't want the decisions to be presented in triage lane. Every editor should be instructed to present their decisions in their own lane") — supersedes the 08:34Z topic-42487 amendment (v0.4.101).

- fleet-directives.md §Decision Rollcall item 2: delivery is LANE-DIRECT, THE ONLY MODE. Present-here marked RETIRED with provenance. Triage NEVER collects or presents decisions on any word.
- triage.md Duty T7 item 7: rewritten from present-here duty to RETIREMENT notice — Triage's answer to "where are the decisions" is a coverage report, never a consolidated list.
- editor.md §Decision Rollcall duty: present-here exception deleted, replaced with NO-Triage-exception instruction — a lane told to send its list to Triage/HQ refuses and posts in its own topic.

## v0.4.103 - owner rule pair, 2026-09-08 ~09:1xZ (HQ d72bd52d)

- **Corrected-code presence != smoke success** (SKILL.md evidence-kinds block): presence evidence (strings marker, sha match, deployed.meta identity) can never back a smoke-GREEN verdict on its own; GREEN requires at least one behavioral probe of the corrected path. Presence-only verdicts are labeled UNPROVEN (presence-only).
- **Explicit ack contracts in session_notify** (fleet-directives.md Cross-lane delivery): every notify ends with its ack expectation - No ack needed / ACK by date: what / Reply required: question; no pure-ack replies to No-ack-needed traffic.

## v0.4.104

Owner rule (2026-09-08 12:16Z): bookkeeping legs (lineage/identity/CI) never constitute smoke PASS - a live behavioral probe of the corrected runtime path on the running box is required, or a stamped structural N/A (editor.md Phase 6b + SKILL.md evidence-kinds; origin: ship-38585459 smoke n=2036).

## v0.4.105 (2026-09-08) — one-PR law RETIRED (owner override 13:51Z)

- **fleet-directives.md HARVEST LAW** — filing gate rewritten: file PRs as soon as tests are green AND smokes confirmed (v0.4.104 behavioral rubric); parallel upstream PRs allowed; the previous one-PR-at-a-time rule RETIRED (owner: "this law is incorrect, Adolfo never told this"). The ONLY hold: a feature whose smoke readiness the owner has not confirmed.
- **triage.md duty text** — same filing gate; autonomous trigger now files all qualifying candidates, not just the top one.
- Harvest queue consequence: #1439 no longer blocks #100/#118 — both cherry-verified clean, filing proceeds on their own smoke confirmation.

## v0.4.106

- HARVEST no-hold law (owner override 2026-09-08 15:2xZ): no holding state — editor fires behavioral smoke on probe commission, probe PASS files the PR without owner confirmation; owner “smoke” later = ratification (fd HARVEST LAW + triage.md filing gate).
- Internal feature set widened to telegram,code-graph,browser (owner order 15:28Z); features-compat gate supersets legal.

## v0.4.107 (2026-09-08, owner button ruling 17:04Z — port-work ownership)
- fleet-directives.md §Port-work ownership NEW (owner ruling recovered from daemon callback log after the #1226 mid-turn tap swallow): editors build ports (merge-time ports by the running merge editor; harvest ports dispatched to an editor lane), Triage owns the harvest-port queue, HQ gates classifications; owner remains ask-decider. Filed l1979/opencrabs#136 for the tap-delivery defect (mid-turn picks re-armed but never re-delivered silently).

Moved out of SKILL.md frontmatter at v0.4.43 (Duty-6 run-2 finding B6 —
~3k tokens of changelog loaded on every role-file claim; history is reference
material, not procedure). Git-tracked in the skill repo; append one entry per
bump, newest LAST. SKILL.md carries only `version:` + a pointer here.

Owner ruling was a suggest_options button pick (option 0: "Agreed - codify the split: editors build, Triage queues, HQ gates") at 17:04:02Z on the port-ownership message. The pick was swallowed by the daemon's #1226 mid-turn guard (log: "session d72bd52d mid-turn — re-arming token, choice not delivered") and never reached HQ's prompt; recovered first-hand from the daemon callback log (log lines 995871-995878: followup:47d8185f:0 → pick recorded on msg 46104 → re-arm WARN).

- **fleet-directives.md** — PORT-WORK OWNERSHIP three-role table added above §Upstream PR law: editors build (all port commits + harvest ports), Triage queues (disposition census, backlog, commissioning), HQ gates (classification ruling + approval gate; owner ask-decider). Supersedes HQ's 17:02Z three-class proposal and Triage's 16:50Z three-hand chain wherever they differ.
- Defect note: the #1226 mid-turn swallow cost ~15 min of ruling-hunting (board 30220, topic 42487, ledger, session logs all checked before the callback trail). Root cause is daemon code (agent.rs:716 re-arm path), not lane process — routed as a defect family to HQ.

## v0.4.108 (2026-09-08, owner "Go then duty 4+6" 17:53Z — ownerless-procedure assignments + Duties 4+6 fired at 21/5 FIRE)
- triage.md Duty T4: three new daily patrols riding the census turn — stale-branch sweep (`oc-branch-sweep` gets its caller; ~55 contained branches were queued with nobody dispatched), upstream PR-state re-verify (every open PR's state+mergeable fresh each census; closes the #1451 CONFLICTING-found-hours-late gap), cron liveness check (the three law-carrying crons; liveness check = the heartbeat's heartbeat). Base-freshness-at-filing-time folded into the PR-state patrol text (census CLEAN results name the upstream sha tested against — Triage lesson n=2083).
- toolsmith.md Duty S1: cron liveness AUDIT ownership (fixer side vs Triage's checker side) + rollback drill schedule (every 14 days, next 2026-09-22, battery + ledger stamp per drill).
- supervisor.md Duty 4: Rollcall proactive-trigger duty — on each firing HQ lists owner-decision items sitting unprompted between rollcalls in the verdict table; T7 execution stays on-demand.
- Owner-gated items intentionally left unassigned (need owner priority pick, not law): defect-family fixes (#136 tap delivery, display-layer corruption ×3 sessions), state-repo stash@{0} recovery (stays with owning lanes, now NAMED in fd state-repo hygiene law).
- Fired with this bump: Duty 4 poll + Duty 6 lens review at 21/5 FIRE (boundary n=1594).

## v0.4.109 (2026-09-08, owner "Go then duty 4+6" — consolidated Duty-4/6 law batch, all premises HQ-verified)

- fd: two new sections — CI-run identity + verdict laws (job-pin identity, run-existence, staleness/re-gate, watcher-resume/no-detached-watchers, rendered-output acceptance, structural-pending-organic leg); receipt + delivery discipline (UI-emit receipts, self-delivered notify, lane-side verify-unclaimed, waiter poll-not-trust, REST settle, worktree path check, TG research-before-design, /proc post-swap proof, poll target-pinning, profile-scoped state dir). Lanes: 1a63f103 x3, aaa8d8ae x3, c6b1a539, 61161247 x3, 329bf3a3 x3, d5863180, facd50af x2, c78e78e0 x2. Duty-6: 8/8 lens reports persisted (A,B,C,D,E,F,G,brain-scrub) — mechanical fixes route to toolsmith batch; semantic items (B8 port-ownership creep, brain-scrub HIGHs, editor.md split timing) await owner.

## v0.4.110 (2026-09-08, owner "1 2 3 go" — deletions + redaction batch)
- REMOVED tools/oc-toolaccum (3 uses, all --help; battery test + SKILL.md/RC-CONTRACT.md references cleared) — owner GO on Decision Rollcall Q3.
- State repo: workers-ledger.json.pre-merge-20260828-113207 deleted (commit 86c97600, owner GO). poll-110.log already absent.
- SECURITY.md: 17 secret literals redacted (5 bot tokens, GH PAT, 4 Grafana tokens, Gatus bearer, Gemini key, MTProto API hash, n8n JWT, Mixpanel secret, SSH password, Grafana pass+b64) — tokens WERE live on disk in plaintext; owner advised rotation.
- Rollback drill cadence: owner ruling "do we need rollback at all?" — HQ answer: keep on-ship verification only (oc-deploy swap journal + /proc identity per v0.4.109), scheduled drills retired; codified in editor.md ship phase.

## v0.4.111
- N-1: editor.md S3 ship path rewritten to the shipped one-command contract (`ship --execute --wait N`, v0.4.100 fusion; two-step demoted to fallback).
- D5: base-freshness-at-filing-time law added (editor.md harvest sweep; census/gate CLEAN must name the upstream base sha — #1451 lesson, n=2083).
- A-11: editor.md BUILD-TRIGGERS duplicate collapsed to SKILL.md canonical pointer (third-pass finding).
- A-12: supervisor.md SYNC-LAW restatement collapsed to fleet-directives canonical pointer.
- A-15: SKILL.md writer-census clarifies README.md tool-fleet section + tools/RC-CONTRACT.md are toolsmith-writable.
- B-9/A11: supervisor.md Duty 6 documents second-pass report naming (-run2, B2/A2); family-map letters stay A–G.
- F1/F2: editor.md Rollcall telegram_send restatement marked as surface-law merge (media ban noted).
- Register: SKILL.md tool table gains oc-waiter row (repeat finding closed); retired `oc-deploy contributors` redundant row removed.
- fd: post-compaction reload law synced to the v0.4.95 three-file form.
- RC-CONTRACT: oc-review-persist row corrected to actual code exits (0/2; stale 3/4 removed).
- README.md: census corrected 30 executables (oc-toolaccum deleted v0.4.110); oc-waiter/oc-attrib/oc-notify.sh highlight rows added (TOOLSMITH + HQ, owner order 19:31Z).
- v0.4.115 (2026-09-08): FIX — oc-review-persist LENSES whitelist actually extended to A-I (v0.4.114 shipped a message-only edit: die-string said A-I but the LENSES var still lacked H/I — H/I persist would have died rc 2; caught by Supervisor at Duty-6 spawn on owner "run duty-6"); help-text lens line synced; battery green.

## v0.4.112
- T5 issue sweep: DAILY cadence added (owner order 2026-09-08 20:0xZ, "1, but daily" then corrected to option 2) — sweep runs once per day, not only post-compaction.
- T5 autonomous closure authority (owner option 2): Triage may close open fork issues WITHOUT the owner word on three tests only — (a) superseded-by, (b) duplicate, (c) owner-confirmed-withdrawn. Harvest-gated closure for done-work unchanged. Every auto-close: ledger stamp + close comment naming the test class; reversible by owner word.
- Provenance: owner pick was a text correction ("no, 2") after the option-1 read; the daily cadence from the first message stands.

## v0.4.113 (2026-09-08)
- Duty-6 lens H — LEDGER HEALTH added (owner "go" 2026-09-08 20:16Z, on HQ proposal after "what lens analyses ledger?"): reviews workers-ledger.json AS A WHOLE — lesson-extraction completeness (incident rows → codified laws), phantom-row families, open claims on closed chains, contradiction pairs, version/cadence sync. Slice tools (oc-ledger claims / oc-ship-audit / oc-waiter-sweep) stay the enforcement surface. Brief in review-lenses.md; family map updated to A–H (supervisor.md, SKILL.md router row, glossary). Joins the next Duty-6 cycle (due 25/5 FIRE).

## v0.4.114
- Duty-6 lens I — META-REVIEW added (owner pick 2026-09-08 ~20:45Z, "Add Lens I — meta-review (recommended)"): reviews the lens catalog AND its output — brief correctness vs persisted reports, overlap/coverage gaps A–H, false-positive/negative history from the Supervisor's premise-verification record, quote-or-no-finding adherence. Self-reference capped: may flag its own brief, never reviews its own report. Brief in review-lenses.md; oc-review-persist whitelist A-G → A-I (selftest: I-report persist smoke OK); SKILL.md router row → nine-lens A–I. Joins the next Duty-6 cycle (due 26/5 FIRE).
- Duty-6 lens H — LEDGER HEALTH added (owner "go" 2026-09-08 20:16Z, on HQ proposal after "what lens analyses ledger?"): reviews workers-ledger.json AS A WHOLE — lesson-extraction completeness (incident rows → codified laws), phantom-row families, open claims on closed chains, contradiction pairs, version/cadence sync. Slice tools (oc-ledger claims / oc-ship-audit / oc-waiter-sweep) stay the enforcement surface. Brief in review-lenses.md; family map updated to A–H (supervisor.md, SKILL.md router row, glossary). Joins the next Duty-6 cycle (due 25/5 FIRE).

## v0.4.115 (2026-09-08)
- FIX — oc-review-persist LENSES whitelist var extended to A-I (v0.4.114 extended the single-letter case-glob to [A-I] but the LENSES var still lacked H/I — named-lens H/I persist died rc 2; single-letter H/I were NOT affected, the case-glob bypasses the whitelist. Caught by Supervisor at Duty-6 spawn on owner "run duty-6"). Help-text lens line synced. Battery 144/0.

## v0.4.116 (2026-09-08)
- TOOLSMITH mechanical batch DISPATCHED (owner "Go what you can" 21:39Z): E-H1 swap-text fix, F-3 rc-register correction, A-1 census sync incl. A-H1 roster law (Duty-6 spawn text A-H → A-I), persist-first write-through law (spawn-path report persistence — the lens-A restart lesson), oc-ledger lessons verb (H-2), D-4 closure stamp (n=2115), ~30 MED/LOW prose. ACK due 12:00Z 09-09.

## v0.4.117 (2026-09-08)
- ERRATUM on v0.4.116: the bump commit b05a493d did not merely DISPATCH the TOOLSMITH batch — it SHIPPED it. TOOLSMITH had already implemented the batch in-tree (oc-ledger lessons verb, oc-review-persist whitelist, E-H1/F-3/A-1/A-H1 + ~30 prose fixes across editor.md/triage.md/supervisor.md/review-lenses.md/upstream-merge-runbook.md/war-stories.md/toolsmith.md) when HQ ran oc-ledger sync for its own ruling codifications; the sync swept the combined tree. Battery 141/0 tested the combined tree before the commit — completeness is battery-covered, attribution was wrong. Lesson: HQ must run `git status --short` and identify lane WIP BEFORE oc-ledger sync (the v0.4.111 hand-off discipline exists for exactly this and was skipped).

- NO-HOLD law AMENDED (owner 21:44Z "1 - no, my go before pr"): no holding STATE ever, but PR filing is OWNER-GATED again — probe PASS → editor presents ready PR → owner go (per-PR or batch) → file. Codified in fleet-directives §Upstream-merge cadence, triage.md T4 gate, SKILL.md consent register ("UNTOUCHED" → RESTATED with the amendment). Ruling supersedes the 15:2xZ "no holding" reading that auto-filed on PASS.
- I-2.1 ERRATUM adjudicated (owner "2 - go"): contributors retirement = v0.4.90 (tag 90c9e1d8, 2026-09-07 14:12:23Z, commits fc02ddeb+129ca40e+d6a66b51, lens E-2, owner "All 4 go") — not v0.4.91. Ledger n=2116.
- oc-ci-parity RETIRED (owner "3 - ok": fix oc-issue-sweep + retire oc-ci-parity): zero live use in 12 days (C-H2), the merge runbook three-way-diff check supersedes. Tool + battery block + SKILL register row + RC-CONTRACT row + supervisor/SKILL parity prose removed. oc-issue-sweep FIX stays open (fix-lane batch).
- Battery gate: see battery-last.json at sync.

## v0.4.118 (2026-09-08)
- TOOLSMITH batch completion (post-sync remainder of the v0.4.116 dispatch — b05a493d swept the in-tree WIP mid-edit, these edits finished after): lens I-2.2 A/B boundary line in review-lenses.md (A owns ref consistency, B weighs refs only as load-weight, first finder gets attribution); lens D evidence law folded into brief (negative-existence claims must quote query + scope); lens I-4.1/I-4.2 evidence-unit law + I-5.1 corpus/precedence/severity scale added to I brief; E-H1 SKILL.md oc-deploy row + editor.md auto-swap reword (two-step truth); T6 duty physically moved after T5 in triage.md (sequential T1-T7); T1/T2 historical-origin markers; A-L7 escalation pointer to toolsmith.md canonical; oc-ledger cmd_lessons jq hardened to array+join form + RC-CONTRACT lessons row; battery receipt refreshed 141/0 (2 runs, 22:20Z).
## v0.4.119 (2026-09-09, owner "Go all" on cycle-2 rulings — TOOLSMITH mechanical batch, 8 items)
- H-9: one-time CHANGELOG reorder to the file's own newest-LAST contract (CHANGELOG.md:52 was already the rule; the top region violated it). 60→118 now strictly ascending, newest last; duplicate v0.4.117 blocks (ERRATUM + NO-HOLD) merged; the two v0.4.117 entries' bullets preserved; v0.4.115 bullet nested inside the v0.4.111 tail entry removed (duplicate). Content-loss check: zero lines lost vs pre-reorder backup (order-insensitive diff), one line gained = the restored v0.4.113 entry.
- v0.4.113 CHANGELOG entry RESTORED (the entry was lost in earlier reorders; tag v0.4.113 exists — commits bef75bec lens H + 4b25ac78 sync — entry composed from the commit message).
- B-1: supervisor.md persist-first law gains the write-through fallback — a read-only reviewer cannot write files; the Supervisor's persist-on-receipt (oc-review-persist, byte-count + sha256 verified) counts as delivery when the reviewer toolset has no file-write capability. Demonstrated 10/10 cycle-2 reports. B-9 residual: hardcoded /tmp/duty6/ → cycle-suffixed report-dir wording.
- F-4: oc-ledger cmd_lessons — --class compiled as REGEX by test($cls;"i") with jq stderr to /dev/null and unconditional exit 0 (invalid regex = silent empty = false clean). Fix: substring match via ascii_downcase | contains + lowercase --arg; jq rc captured, failure → die 3. Header doc ("substring match") now true.
- F-6: oc-review-persist — single letters A–I were DEAD whitelist entries (case-glob short-circuit bypassed LENSES); a future letter-only whitelist edit silently no-ops (the v0.4.114 failure mode). Fix: single letters now route through the LENSES whitelist like A1–I9; :29 comment updated; lowercase-reject selftest case added.
- A1: triage.md T4 auto-file residue stripped — "commission probes and file on PASS" / "Triage files the PR on the lane's GREEN + smoke-PASS receipt" reworded to the amended owner-gated filing gate (present on PASS, OWNER's filing GO, then file).
- H-6/H-7: version-contradiction residue — README.md oc-deploy contributors retired v0.4.91 → v0.4.90 (git-adjudicated, tag 90c9e1d8, erratum n=2116); parity-retirement attribution unified to v0.4.117 (commit b05a493d era, owner "3 - ok").
- A-1/A5 census 30 → 29 (disk glob = 29 oc-* executables; oc-ci-parity deleted v0.4.117): README.md ×2, editor.md ×2. README lens roster A–G → A–I (A5, 4th site of the A-H1 class). A9: review-lenses.md Reviewer A dangling "boundary, " token dropped.
- G-M4: SKILL.md single-writer census enumerated list gains CHANGELOG.md (parenthetical claimed it since v0.4.116; the list omitted it). G-M5: RC-CONTRACT.md "EIGHT legacy registers" → SEVEN (oc-ci-parity was the eighth, removed without decrementing). E-2.3: SKILL.md canonical-tooling table blank line deleted (rows oc-attrib→oc-waiter rendered as literal text since v0.4.118 reword).
- I-2.2 attribution (8 double-cover pairs this cycle, first finder = earlier report mtime — recorded for the verdict table): A7≡B-3 (superseded standing-order sediment; A first) · A2≡G-H1 (README 30-vs-29 census) · A5≡G-M2 (README "(A–G)") · A4≡G-M4 (SKILL census parenthetical vs list) · A3≡G-M5 (RC-CONTRACT "EIGHT legacy registers") · C-N1⊃F-9 (oc-pr-fault-scope placeholder-PR → rc-3 mislabel; C first; F adds the fleet-wide pattern cluster) · G-H2≡H-9 (CHANGELOG prepend/duplicate-117 disorder; G first) · E-2.2≈H-1 (patch-id debt, two angles; H cites C-V3's find, nobody cites E-2.2) · plus A1⊂B-2 (triage auto-file residue inside B's 5-site gate count).
- Exclusions held: oc-harvest-sweep patch-id fix = separate lane (agent 805f70f4); oc-waiter-sweep cron exists (id b0d7e0d3) — C-N2 stale snapshot; E-2.1 and F-5 not in dispatch.

## v0.4.120 (2026-09-09, owner "Go" — watcher audit follow-up, 3 items)
- ONE watcher law: editor.md:94 and fleet-directives.md watcher section reconciled into a single rule — CI verdict waits = `oc-waiter arm` (preferred) or one-shot `gh run view` polls on wake. Raw `gh run watch`/`gh watch`, hand-rolled nohup pollers, AND `oc-prchecks --wait` double-duty as verdict waiter are banned with no sanctioned-pattern exception. Audit evidence: ~48 handrolled spawns vs ~630 arms over Sep 6–9; the editor.md "DETACHED ≥60s poller" sanction and fd's "no detached long-watchers" law had contradicted each other (premise for the audit: owner question 2026-09-09).
- Lens C adoption-compliance check (review-lenses.md): every C pass samples runtime `Detaching '...'` records, flags any `gh run watch`/nohup CI poller spawn and any `oc-prchecks --wait` double-duty as a violation naming the session id. Closes the gap where ~48 violations accumulated silently across 4 days (no lens checked whether lanes USE the official tool).
- `oc-waiter quick --run <id> [--label S]`: one-liner arm — notifies OC_NOTIFY_DEFAULT or the arming session, label auto-prefixed quick:. Kills the ceremony excuse (arm wants OC_ACTOR + --notify + label discipline; a one-line nohup asks nothing). Usage line updated; live arg-validation tested.

## v0.4.121 (2026-09-09, owner orders 09:06-09:3xZ — skill-change notify reload law + routing-law amendment)
- Skill-change notifies MUST carry the reload instruction (fleet-directives.md §Cross-lane delivery, new bullet): a notify announcing a version bump / law change ends with an explicit reload line — `RELOAD: run oc-drift-check <your-uuid> <new-ver> --ack, re-read changed role files + fleet-directives.md (editor.md §Mid-cycle skill drift)` — and its ack contract is `ACK after drift-check` unless marked otherwise. Origin: the v0.4.120 notify wave (14 quiet notifies 09:08:48Z) stated what changed but never told lanes to re-ingest — lanes held the skill in context with no reload verb.
- AGENTS.md routing law amended (owner order): "remember X" directives go to a SPECIALISED skill file when one applies (opencrabs-dev process law → fleet-directives.md, editor behavior → editor.md), otherwise AGENTS.md; never MEMORY.md. The reload clause is folded into the AGENTS.md skill-change-lane-notify law (canon referenced here; no second full copy).
- Companion facts: delivery-timing investigation closed (defers verified per spec — 14 sends queued in ~3ms at 09:08:48Z, lanes woke 60-100s later with the notify brief as their first ingested message, e.g. 329bf3a3 seq 568); workers-ledger.json 2-doc corruption (stray n=2163 row appended outside oc-ledger by session aaa8d8ae) repaired in place, stray row absorbed as event n=2163, pre-repair copy kept as workers-ledger.json.corrupt-2doc.bak.

## v0.4.122 (2026-09-09, owner orders ~10:0x-10:5xZ — auto-ship, HQ no-execute, ledger-stamp reload reminder)
- **AUTO-SHIP law (owner order 2026-09-09 "the owner should not approve shipping, it should be automatic"):** PR filing + fork ship chains are AUTOMATIC on smoke PASS (v0.4.104 four-leg rubric). The owner-go-before-filing gate ("my go before pr", 2026-09-08 21:44Z) is RETIRED for both fork ships and upstream PR filings; owner is notified after the act. Surviving gates: mechanical CI legs, smoke rubric, rollback-is-owner's-call. (fleet-directives.md §NO-HOLD.)
- **HQ no-execute law (owner order "you should refuse work that should be done by the triage lane and tell the requesting lane to reroute"):** HQ refuses editor-lane/Triage-lane/TOOLSMITH work sent to it and session_notifies the sender to reroute to the owning lane. HQ executes only rulings, skill authoring (via Triage intake), receipted verdicts/gates, dispatch GOs, and its own duties. Origin: the #129 carrier rebase was half-executed by HQ before the order arrived — lane worktree restored byte-exact (a289814a), chain rerouted. (fleet-directives.md §HQ does not execute lane work.)
- **Reload notify gains oc-ledger reminder (owner order "reload notification must remind to oc-ledger after reading"):** the RELOAD line now ends with `then STAMP oc-ledger ack after reading`. (fleet-directives.md §Cross-lane delivery.)
- Companion facts: r8 GREEN on aaf7c020 invalidated by main drift to 201fc1de (#134 landed 07:57Z) — containment check caught it pre-dispatch; lesson n=2170. v0.4.122 notify wave = 14 quiet session_notifies, new-format briefs (RELOAD + oc-ledger stamp), receipt ids d79b382e…1f1ca97b.

## v0.4.123 (2026-09-09, owner "go" 10:30Z watcher-fix + HQ ASSIGN 10:5xZ fanout — TOOLSMITH lane 2fae1230)
- oc-waiter SIGTERM trap (owner "go" on the 10:30Z autopsy proposal): an external stop of a watcher child now writes verdict=killed with the signal timestamp into its record and notifies the owning lane IMMEDIATELY via the standard notify path (now + interrupt-retry; notify failure -> notify-failed status so the sweep still catches it). Death goes from "orphan discovered by sweep minutes later" to "cause delivered in the same second". Sweep treats killed as terminal (never re-flagged orphaned); selftest 39 -> 41 (trap fires + killed-is-terminal). Sweep remains the backstop for SIGKILL/OOM/power loss.
- oc-notify-fanout (HQ CONCUR+ASSIGN, owner order 2026-09-09; origin: v0.4.120 wave hand-picked lanes from a stale roster): single sanctioned path for skill-change notifies. Bakes in: per-lane self-uuid substitution ({{UUID}}/{{VERSION}} — the Triage law after acc3fa9b/c6b1a539/d5863180 placeholder-briefs); law1 placeholder-leak abort (any surviving {{token}} refuses the send); target validation (uuid shape, all-zero-segment n=2167 class, LIVE session-list check — 11 of 44 roster uuids verified dead at first run, all skipped); --roles/--exclude filters; per-lane receipts + summary; ledger stamp notify-fanout with all ids. Battery 141 -> 146 (guard cases 61a/61b/61c).
- Companion facts: workers-ledger.json 2-doc corruption SECOND instance today (hand-rolled n=2187 ci-verdict row appended raw by lane harvest-rich-buttons session aaa8d8ae — same class as the n=2163 aaa8d8ae incident) repaired pre-claim: doc2 ejected to workers-ledger.ejected-n2187.json, backup kept, check-version ok. Routed to HQ — aaa8d8ae needs the ledger-stamp law. Known gap flagged: `opencrabs session notify` CLI has no quiet/mode flag — quiet-60s delivery for fanout briefs needs a binary addition (upstream-harvest candidate).

## v0.4.124 (2026-09-09, HQ GO ~12:0xZ frankenstein batch + n=2234/2233 — TOOLSMITH lane 2fae1230)
- oc-waiter arm-time notify-target livecheck (frankenstein-uuid gate, n=2221): `arm`/`quick` now refuse rc 2 unless `--notify` is a FULL-id match against the live session list (resolved-binary served; `OC_WAITER_SKIP_LIVECHECK=1` bypass for sandboxes). Kills the hand-assembled-uuid class at arm time — 1a63f103-596e-43a4-9c7e-1b6dfc3cd870 (#129 prefix + Triage tail) would have been refused at arm instead of sitting in the notify queue as a "valid" target. Binary-side deferred-path no_route validation stays flagged upstream-harvest.
- oc-waiter quick no-OC_ACTOR-fallback (n=2234, contaminated-actor foreign wake): `quick` REQUIRES explicit OC_NOTIFY_DEFAULT; silently defaulting the wake target to OC_ACTOR armed a waiter whose wake landed in a foreign session (arm 20260909T123351Z: actor==notify==462181e9, armer was 1a63f103 tool-loop). Actor env is exportable across sessions — attribution is env-based, not session-based (462181e9 correction, same day).
- ERRATUM (v0.4.127, byte-adjudicated via od/xxd on commit blobs): the oc-prchecks bullet below misdescribes the defect — the C-F2 skip-flag line has been the correct assignment (consumer name + =1) since commit 74325d0a; the "bare-typo NAME" wording was a display-layer truncation phantom. Real v0.4.124 oc-prchecks content = set -e + errexit-survival sweep. Original bullet kept verbatim:
- oc-prchecks OC_PR_SKIPPED_DISPAT proper assignment: the C-F2 resume path's skip flag was a bare-typo NAME executing a nonexistent COMMAND (missing CH, no =1) — flag never set, resume re-dispatched anyway, concurrency-canceling the run adoption exists to protect. Now `OC_PR_SKIPPED_DISPATCH=1`. Plus `set -e` with a full errexit-survival sweep of the tool's expected-failure paths (selftest harness run_t/CF2 probes/killed-watch wait/lock-holder wait/run-view probe) — each fix documents the class. Selftest 37/37.
- oc-notify-fanout hang fix (n=2221): per-send timeout (20s default, OC_FANOUT_SEND_TIMEOUT) + INCREMENTAL receipt flush before each send — a wedged target can no longer starve the whole fanout with zero receipts.
- Companion facts: erratum n=2233 (HQ self-corrected) — raw-gh run-adoption discriminator = JOB-NAME SHA PIN + created_at, NOT headBranch/headSha (carrier architecture); FAILED-TOOL trap premise from mermaid lane REJECTED (designed verdict, notify-ok receipt). Selftest oc-waiter 41 -> 44 (frankenstein refusal, prefix-tail refusal, quick nodefault); battery 146/0.
## v0.4.125 (2026-09-09, owner GO 14:55Z re-gate split law n=2259 — TOOLSMITH lane 2fae1230)

- NEW TOOL `oc-rebase-safety` (read-only git plumbing): (1) `overlap --old-main X --new-main Y [--tree PATH]` — main-shift changed set ∩ branch-side merge-changed set (2-parent tip: second-parent diff `HEAD^2..HEAD` = branch's own contribution, live-verified; first-parent diff is main-side ingress and was the wrong set on first implementation); exit 0 zero-overlap = re-gate skippable, exit 1 = full re-gate required, intersection printed. (2) `audit --old-tip A --new-tip B [--base C]` — per-file single patch-id compare (n=1543: one patch-id per diff, never range-concatenated) of branch changes C..A vs rebased result C..B; rows FILE/SAME|CHANGED|DROPPED; catches rebase-mechanics losses incl. silent conflict-resolution drops (patch-id differs = CHANGED, change absent = DROPPED); exit 0 clean / 1 losses. Exit 1 is a verdict (house rule).
- LAW TOOLING for owner ruling n=2259: re-gate skippable ONLY on zero overlap + clean audit; overlap computation stamped to ledger either way (caller duty).
- Selftest 5/5 (local fixture repos, idempotent); battery 151/0 (new section + usage cases + fleet-wide --help contract honored); RC-CONTRACT row added. Attribution: owner ruling n=2259 (both halves, evidence tally 2 base-shift reds + 4 rebase-mechanics reds); Triage brief n=2261 re-send after phantom-brief incident.

## v0.4.126 (2026-09-09, owner GO 16:16Z ship-chain + HQ n=2269 fanout fix — TOOLSMITH lane 2fae1230)

- NEW TOOL `oc-ship-chain` (owner GO on 5→swapped design): single-invocation orchestrator — CI gate (oc-prchecks) → issue-log → ff-merge into fork main → oc-deploy ship --execute --wait → poll --execute until SWAPPED, all under ONE chain-id (`CHAIN-<sha>-<ts>` journal lines). Structured exits: 0 SWAPPED / 3 pre-flight / 4 GATE-RED or CARRIER-RED / 5 NON-FF (lane rebases via oc-rebase-safety, re-runs) / 6 infra. Closes E-H1 (lanes stopping at GREEN — no legitimate exit between gate and swap) and #134 orphan class (swap leg skipped). Worktree-resolving pre-flight (fork checkout may be a secondary worktree not holding main — resolves the worktree that owns main). Scope deliberately ends at SWAPPED: smoke (6b) and owner approval (7) stay outside. NO-SELF-PING law (owner constraint 16:2xZ): the chain never fires session notifies — NOTIFY_SESSION unset for children, --notify-session never passed (sub-tool wakes would self-ping the awake calling lane).
- FIX oc-notify-fanout (HQ n=2269): per-send timeout 20s→90s + per-target latency receipts. Live probes (probe A plain=34s, probe B --title=31s, both delivered) showed --title is NOT the delta — session-notify latency is uniformly ~30s and the old 20s default killed EVERY send rc=124 while delivery worked (defect predates v0.4.125, masked by the timeout). Receipts now carry send latency (SENT/FAIL …ms).
- Selftest oc-ship-chain 8/8 (fixture repos + fake binaries, zero real CI/ledger); battery 155/0 (new section: selftest + usage cases; fleet-wide --help rc=0 honored). RC-CONTRACT row added. set -e expected-failure captures in selftest harness (run_t pattern).


## v0.4.127 (2026-09-09, HQ claim batch c4 lens-I verified items - TOOLSMITH lane 2fae1230)
- ERRATUM item1 (byte-adjudicated, od/xxd): the "bare word OC_PR_SKIPPED_DISPAT still live at oc-prchecks:614" premise (HQ n=2269 chain + lens-I) was a DISPLAY-LAYER TRUNCATION - the line has been the correct assignment (consumer name + =1) since commit 74325d0a. No code change; erratum prepended to the v0.4.124 CHANGELOG bullet (original kept verbatim). Lesson: the =-sign was dropped from every textual read this session; only od/xxd hex was faithful.
- item2: dead owner-go gate text reconciled to the AUTO-SHIP law (v0.4.122) in 4 files - SKILL.md ISSUE-ROUTING approval row + CONSENT REGISTER, editor.md smoke-PASS notify + Phase 7 trigger/step 0 (filing notice replaces approval wait), triage.md T4 standing order + filing para, fleet-directives.md :19 tail. Residual grep for owner-filing-go wordings: zero.
- item3: CHANGELOG one-time reorder to the newest-LAST contract - v0.4.120-126 blocks now ascending (was 122-121-123-126-125-124); byte-multiset preserved (sorted equality verified).
- item4: oc-review-persist default DIR -> I-5.1 CORPUS reviews/<YYYYMMDD>-cycle/reports/ under the skill repo (was /tmp root: volatile + undiscoverable); cycle-local skill-review-index.log (wins on divergence per I-5.1); OC_REVIEW_DIR=/tmp restores the volatile fallback. Selftest 15 -> 18 (corpus default rc/file/index).
- item5: LIVE VERDICT - no change. oc-upstream-delta has NO `git log -p` anywhere (the n=1543 hazard class); its patch-id loop uses rev-list + per-commit show (the recommended shape); the lone `git log --format=%H%x09%s` emits sha+subject, never patches. Lens-E ":210/214 lacks --format= fix" misread line numbers. Selftest 10/10 incl. absorbed-pair cases.
- item6: editor.md waiter-discipline item 4 recommended `oc-prchecks --wait` - contradicted the v0.4.120 ONE watcher law; re-pointed to oc-waiter arm.
- item7: TOOLS.md:484 dangling pointer `skills/opencrabs-dev/compiler.md` -> `tools/archive/compiler.md` (archived at S3 cutover 2026-08-28; root path resolved nowhere).
- item8: lens-H codifications in fleet-directives.md - H-3 mirror2 = canonical skill push remote (n=2125); H-4 sync rows need substantive --why (n=2106/2108 empty-row class); H-5 claim close-out = confirm/release stamp when a claimed issue closes (329bf3a3/#32 stale-claim class).
- Gates: selftests oc-review-persist 18/0, oc-upstream-delta 10/0, oc-prchecks 37/0; battery 155/0. Items 1 and 5 closed as verified-no-change (premise false); 6 edits landed across 6 commits.

## v0.4.128 (2026-09-09, owner order ~20:03Z — HQ executed)
- OWNER DESIGN GATE: §Discussion links + fix-approval gate item 2 widened from fix-scoped to EVERY implementation design (fix, feature, tool, refactor, process change, any size). Design must be presented to the owner in canonical terms (codified ontology, no invented shorthand) WITH a process diagram (Mermaid vertical; sequenceDiagram for multi-actor) and receive explicit owner approval (message or 👍 reaction; silence is NOT approval) before any code work. Diagram is part of the gate. Applies to HQ and all lanes, incl. Duty-4 accepted proposals that change law or tooling behavior. AGENTS.md pointer section added.

## v0.4.129 (2026-09-09, owner GO 20:44Z dispatch n=2352, claim n=2353 — TOOLSMITH lane 2fae1230)

- FIX oc-waiter full-ID livecheck (HQ n=2249 rediscovery — the v0.4.125 fix never worked: `session list` prints ONLY 8-char prefixes). Two-stage design (`session list` prefix + `session get`) was implemented and KILLED after live measurement: `session get` costs ~37s/call, dry-run hung >5min. Final design: roster read directly from the profile session DB (`sqlite3 "file:${OC_WAITER_DB:-$HOME/.opencrabs/profiles/${OC_WAITER_PROFILE:-ops}/opencrabs.db}?mode=ro"`, `WHERE archived_at IS NULL AND (title IS NULL OR title NOT LIKE 'subagent:%')`) with full-id `grep -qxF` exact match; frankenstein/dead ids refused rc=2. Set-equality CLI vs DB verified 1021==1021, comm -3 = 0. Behaviorally verified live: real full id arms rc=0; frankenstein (n=2221 class) and dead ids refused rc=2. Selftest 44/44 (fixture roster.db via OC_WAITER_DB).
- FIX oc-notify-fanout same-source: roster fetch switched from `session list` to the identical DB query (OC_NOTIFY_DB override); validation is a single full-id grep — dangling tokens now SKIP with the roster-absence reason instead of false-sending. Battery cases 61a (rc=4 on dangling token, 32 ABORTs) / 61b (sent=32 skipped=11 failed=0).
- FIX oc-ledger cadence boundary (HQ n=2349 lesson): cycle close = latest `note` row matching `^vX.Y.Z ACCEPTED`; falls back to review-battery/skill-review max for pre-close epochs. Landed 6/5 boundary (stale n=2192) class closed. Selftest +2 cases (22a) -> 110/0.
- DOCS: SKILL.md oc-ledger row trimmed ~175->~40 words (B1 worst offender, mechanics moved to RC-CONTRACT.md); oc-waiter row trimmed + gained `quick`; 3 new B4 tool rows (oc-ship-chain, oc-notify-fanout, oc-rebase-safety, purpose-only + register tail); nine-lens -> TEN reviewers wording (A-5); three-way pointer fixed to supervisor.md §Parity. supervisor.md Duty 3 gained oc-notify-fanout mechanical-path pointer; editor.md Phase 6a gained PREFERRED PATH -> oc-ship-chain; fleet-directives.md size claim ~36kB -> ~54kB variable (I-10 3rd cycle). review-lenses.md lens F folded ruling n=2265 (adoption check covers Duty-4 notify-brief quality, F4).
- Battery 155/0 (battery-last.json receipt), OC_TOOLS_NOLOG + timeout 590 law honored.


## v0.4.130 (2026-09-10, owner "Go" 02:4xZ — direct-dispatch law, HQ-authored)
- TOOLSMITH v0.4.130 BATCH (ruling n=2369, HQ direct dispatch, claim n=2383): (1) **oc-waiter verdict-mapping law** — terminal verdicts fire ONLY on run-state conclusions: GREEN/RED require the gate's stdout `VERDICT GREEN/RED` marker, rc alone never verdicts (closes the false-RED-on-GREEN class, run 34409434135: stale gate rc 3 mapped straight to RED at poll 1); tool-error rcs (2/4/7 + markerless 0/3) retry with poll-floor backoff; FAILED-TOOL only after k=3 CONSECUTIVE tool errors (env OC_WAITER_TOOLERR_CAP, default 3) — healthy poll resets the streak; AMBIGUOUS (rc 8) and SUPERSEDED (rc-4 + OC_PR_SUPERSEDED) stay non-retryable; selftest 48/48 (cases 22a-22d). (2) **oc-drift-check SKILL_DIR canonical-resolve** — default resolves the canonical profile skill copy, never the invoking script's location (worktree self-resolution produced contradicting same-day drift verdicts); precedence `--skill-dir` flag > `OC_SKILL_DIR` env > canonical; selftest 9/9 incl. live canonical-not-self-resolved check. (3) **editor.md PATH anchoring note** (§Mid-cycle skill drift item 6) — oc-* tools are path-invoked skill scripts, never on lane-shell PATH (rc=127 discovery class). Commits: 2cc247b4 (oc-waiter), f5ff17d3 (oc-drift-check), 7e14ecb3 (editor.md), d5a899cf (RC-CONTRACT rows); erratum comment 5611969363 retracts a #130 mis-tagged implementation comment.
- DIRECT DISPATCH — NO RELAY HOPS: fleet-directives gains §Direct dispatch (owner order 2026-09-10, discussion 02:30Z "why don't we adopt a direct communication policy"). Work notifications go sender → resource-owner directly; no intermediary lane carries payloads. 5 rules: (1) direct dispatch — intermediary may name the target, never carry the work; (2) address by receipt — full uuid from a same-turn roster/ledger read, never memory (v0.4.129 livecheck enforces mechanically: dead/frankenstein refuse at send); (3) ledger stays the record — every direct dispatch stamps dispatch + delivery-receipt id, DM history is not the record; (4) Triage re-roles from relay hub to AUDITOR — QUIRK intake, verify-unclaimed, orphan sweeps stay (audits, not relays); orphans escalate directly to the sender; (5) escalation unacked-past-deadline goes sender → HQ directly. Exceptions: fanout broadcast waves, HQ rulings/design gate/roster authority. Evidence base: Triage→TOOLSMITH hop silently died twice 2026-09-09 (v0.4.129 + v0.4.130), spawn-nudge mis-address, frankenstein-uuid via queued dispatch. Backed out: triage.md Duty T2 scope note (auditor not relay hub), editor.md §CI-wait discipline direct-dispatch paragraph, ops AGENTS.md Execution Discipline pointer.
- TOOLSMITH — FORUM-SCOPE GUARD for oc-notify-fanout (owner order 2026-09-10 03:16Z "All opencrabs dev work happens only in this forum chat. Don't fanout skill changes to sessions outside of it." + "Go" 03:37Z, claim n=2428): oc-notify-fanout gains LAW 6 — every target verified bound to the opencrabs-dev forum chat (-1003936827469) via session_bindings.chat_id in the profile session DB BEFORE any send; out-of-scope targets skip with a visible `SKIP <uuid> <role> SCOPE(not-bound-to-forum-...)` receipt. Fail-closed: unbound = out of scope (a freshly spawned lane receives fanout only after its first forum exchange — binding rows are created lazily). Override for drills: --forum-chat / OC_FANOUT_FORUM_CHAT. First REAL selftest for this tool (the old --selftest was a stub that re-execed): 11/11 on a throwaway sqlite DB + fake notify binary — proves both leak paths (bound-elsewhere, unbound) receive no send, law-1 placeholder abort intact, dry-run identical scope behavior. Live dry-run on the real roster: 28 in-scope, 4 SCOPE-skipped (live lanes with lazy bindings), 11 not-live, 0 failed. Codified: fleet-directives.md §notify discipline forum-scope bullet.

## v0.4.131 (2026-09-10, owner GO "Fix all" 05:54Z board 30220 — WAVE-GROUP-B, TOOLSMITH lane 2fae1230, claim n=2453)
- GROUP A — DOC RESTRUCTURE (7 items): AUTO-SHIP law single-homed in SKILL.md ISSUE ROUTING (copies become one-line pointers; owner quotes + retirement re-announcements purged); SKILL.md tooling table -> purpose-only rows, unified tools-log schema + jq recipes moved verbatim to tools/RC-CONTRACT.md; Phase 7/7b split into editor-upstream-pr.md (210 lines), editor.md stub + cross-refs; rollcall coverage criterion = chase-receipt-or-zero-decision-statement (single home fleet-directives item 3); env-truth caches purged (SKILL.md raw git-show, editor.md oc-waiter env defaults -> tool Env: header, editor tool-table rc column -> RC-CONTRACT, triage raw-grep fallback -> oc-tg-audit only, fleet-directives MTProto incantation, owner chat id removed); two telegram_send TO-BE sections -> single NOT-LAW-YET appendix outside reload path. Net -366/+144 lines across 5 files + 210-line new file.
- GROUP B — WAVE-GUARD: oc-notify-fanout LAW 7 (wave-id = sha256(title+brief) first-12-hex; run/wave-<id>.lock flock+pid+ts; live lock refuses rc 7 naming holder pid/ts; stale auto-clear receipt; selftest case proved the old flock block let a fabricated live lockfile through — lockfile content now the refuse authority) + LAW 8 (per-lane idempotency: run/wave-<id>.sent; DUPLICATE skips; resume semantics — a re-run completes only remaining lanes, never double-notifies). oc-ledger KINDS += notify-fanout (wave completion rows end the note-row workaround) + selftest case. RC-CONTRACT rows updated. run/ gitignored. Selftests: fanout 19/19, ledger 112/0; battery 155/0 (parallel jobs=2). Issue-Ref trailers on all wave commits = ledger n=2369 (WAVE-GROUP-B) — a ledger row is not a GitHub issue (#130 erratum precedent).

## v0.4.132 (2026-09-10, owner "go" 13:05Z board 30220 — HQ executed)
- SHIP SEDIMENT COLLAPSE: editor.md Phase 5, Phase 6, and Phase 6a collapsed into a single, authoritative Phase 5 — Ship (`oc-ship-chain`). Obsolete manual sediment (~120 lines of manual push-to-main, manual issue-log, two-step manual oc-deploy, and retired consent/sub-S2 text) purged. `oc-ship-chain` codified as the single, exclusive path from commit to swapped binary across all 5 mechanical legs (prchecks -> issue-log -> ff-merge -> carrier ship -> swap).
- Cross-references updated: editor.md, SKILL.md, and fleet-directives.md re-anchored to Phase 5 `oc-ship-chain`. Phase 6b (Smoke-test-on-notify) and Phase 6c (Fix requests) retained cleanly with streamlined `oc-ship-chain` execution.
- Battery: 155 PASS / 0 FAIL.

## v0.4.133 (2026-09-10, owner "Approve plan and execute Batch 1" 14:48Z — Duty 4+6 Cycle 5 Implementation, HQ executed)
- TEST HARNESS: `tools/oc-review-persist` selftest bug fixed — runs inside isolated `mktemp -d` mock repo, eliminating self-deletion risk to live cycle reports.
- ATTRIBUTION & FANOUT: `tools/oc-attrib` gains `--first-parent` option; wired into `tools/oc-deploy` post-swap contributor sweep. Prevents traversing into foreign upstream merge ancestry (e.g. merge commit `8870bd40`) and waking historical lanes on sync merges (Duty-4 P-01).
- HARNESS HARDENING & TELEMETRY: `tools/oc-rebase-safety` tempfiles upgraded to `mktemp -t ors.*.XXXXXX` with cleanup traps (Lens F); `tools/oc-ship-chain` gains `lib/oc-log.sh` telemetry, exit traps, and verified `--gated-sha <sha>` resume capability (Lens F & Duty-4 P-03); `tools/oc-notify-fanout` wired with `lib/oc-log.sh` telemetry and exit logging.
- DIRECT DISPATCH & ONTOLOGY: Tool anomaly routing codified per Direct Dispatch Law (owner order 14:3xZ & Finding BS-01) — tool problems in `tools/oc-*` route directly to the active TOOLSMITH role dynamically (`oc-ledger roster`), bypassing Triage relay hops; core daemon issues file directly to GitHub fork issues. Triage role refined to AUDITOR. Dev crons strictly restricted to topic 30220 (Duty-4 P-02).
- DOCS CLEANUP: Struck `AUTO-SHIP` phrasing across all skill files (SKILL.md, editor.md, editor-upstream-pr.md, fleet-directives.md, triage.md); removed unpurged split draft notes; streamlined supervisor.md Duty 7.
- Battery: 158 PASS / 0 FAIL across all tool suites.
