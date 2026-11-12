# War stories — incident histories behind the hard rules

Disclosed from SKILL.md §Shared war stories, v0.4.80 (lens B F6): history is
reference, not procedure — load only when a rule's WHY is in question.
Version-level record: CHANGELOG.md.

| Rule | Incident |
|------|----------|
| Inputs from branch YAML, verify headSha | run #4 dispatched blind; run #2 built main |
| Distrust watcher exit codes | watchers reported success on failed runs, 3× |
| Foreign-WIP diff vs merge-base | branch carried another agent's dropped WIP |
| User-unit awareness | system-scope queries found nothing; wrong restart path nearly used |
| Inner-match exhaustiveness | E0004 cost one full CI cycle (run #5 fixed it) |
| Build fork `main`, record headSha at dispatch | 2026-08-25: swapped a binary built from pre-merge `ebf44f69` while the session-notify merge (`10c73644`) landed on fork main mid-build — feature absent from the running bot |
| `source_ref` = FULL 40-char sha, never short | run #32882515561: short sha → checkout fetched a branch literally named `<sha>*`, dead in 51 s |
| Conflict-quality gate before push | run #32879949542: a hand-merge shipped E0308 red CI (full prose: `editor-ship.md`) |
| Rebase-port, never resurrect duplicates | 2026-08-26: maintainer absorbed 4 of our PRs overnight (#1207/#1208/#1214/flood-governors); a literal 40-commit rebase would have replayed duplicate implementations against his reviewed rework — classification dropped 20+, ported 9 |
| ORDER-era triggers + bounded ROLE_EXCEPTION | 2026-08-26 07:20 UTC: compiler authored the governor.rs E0308 fix while its author (61161247) slept through the owner's night window — a silent role breach. Now builds fire only via `oc-deploy ship` or owner word (sim-validated — sim = ORDER/queue simulation, paired-seed 600 reps, run 2026-08-26), and the breach is legal only as the bounded ROLE_EXCEPTION (archived: `tools/archive/compiler.md` Step 2) |
| Two-file ledger drift | 2026-08-29: `oc-deploy` default LEDGER hit a skill-dir copy while HQ stamped canonical; the "stale duplicate" deletion proved LIVE (fresh swap stamp + fan-out reads) — restored in 6 min, zero data lost. Fix A (v0.4.38) points every tool at canonical; Reviewer D born from this |
| Telegram surface law | 2026-08-28 audit: ~1.3k telegram_send calls/day traced across lanes — every destination was the sender's own surface, but tool sends escaping the own topic read as board-wide broadcast |
| Live-API verdict settlement | 2026-08-26 cycle-18: run 32999957533 concluded failure while a Compiler ACK still called it in_progress — contradictory incoming verdicts settle via the live GH API, never memory |
| Daemon PID via MainPID | 2026-08-26 cycle-18: pgrep caught the old family daemon (Aug-25 boot) instead of the ops unit — disk-vs-proc split until MainPID settled it |
| Single-flight sha+set ordering | 2026-08-26: cycle-19 vs cycle-19b ordered the same sha with different sets — same sha, different set = DISTINCT build |

*Source of truth for procedure = these skill files. AGENTS.md carries only the pointer.*


---

# Re-homed ops lessons (from ops MEMORY.md scrub, owner order 2026-09-02)

Moved from `~/.opencrabs/profiles/ops/MEMORY.md` — still-valid dev lessons, stale sagas deleted.



## OpenCrabs Rust gotchas (from CI rounds 2026-08-25)

- **teloxide-core 0.13 setters are per-payload TRAITS** (`SendMessageSetters`, `EditMessageTextSetters`…), not inherent methods. A file importing only `SendMessageSetters` gets E0599 "bounds not satisfied / field, not a method" when calling `.parse_mode()` on an `edit_message_text` request. Fix: `use teloxide::payloads::EditMessageTextSetters;` or rely on `prelude::*`.
- **rustc error poisoning**: an E0425 (undeclared variable) inside an expression suppresses downstream method-resolution errors in that same expression — fixing the declaration can REVEAL more errors. Don't assume one fix = green.
- **Brace COUNT ≠ brace DEPTH**: equal counts mask nesting breaks. Verify edited Rust by depth-profiling against the merge-base at matched anchors.
- **Shared checkout `~/opencrabs`: other sessions switch branches mid-flight** (3 incidents in one day). Do branch work in a dedicated worktree (`git worktree add ~/oc-wt-suggest <branch>`), never in place. Before building/pushing, confirm `git branch --show-current` AND that the base contains no foreign WIP commits (`git log adolfousier/main..HEAD`).
- **`gh run watch --exit-status` exit codes lie** (reported success on failed runs 3×). Always verify via `gh run view <id> --json conclusion`.
- **quick-build-linux.yml inputs**: needs BOTH `-f source_repository=leshchenko1979/opencrabs -f source_ref=<branch>`; missing repo input → checkout defaults to upstream → fetch dies pre-compile.




## local-mermaid feature (2026-08-26) — FEATURE RETIRED (owner 2026-08-27, deleted from tree in `346bf3c2`; delivery is remote-only mermaid.ink). The four lessons below remain generally valid — cfg-gating, worker-claim reconciliation, committed Cargo.lock, reply_parameters on multipart.

Historical DONE: mermaid.ink → local mermaid-render+resvg (feature `local-mermaid`, default OFF), delivered via reqwest::multipart `attach://<id>` upload. Merged to fork main `961b41a6`, ORDER build handed to Compiler `e756b84b`. Plan archived 6/6.

Sharp lessons that cost the session:
1. **Feature-excluded code must be cfg-gated, not just unreferenced.** Once `prevalidate` (mermaid.ink URL path) was reachable only from a `#[cfg(not(feature="local-mermaid"))]` branch, it became dead under CI's `cargo clippy --locked --all-features -- -D warnings` → hard failure. Any helper used only by a cfg'd-out branch (plus its exclusive consts) needs the same `#[cfg(not(feature))]`. Verified via `modum check --baseline`. (NOTE v0.4.96: `modum` is a RETIRED tool — cited here as historical verification method only.)
2. **Plan-task subagents overclaim (3 of 6 this run, Tasks 3/4/5/6).** Every "task done" from a spawned worker was checked against the real tree once and found empty. Do the reconciling yourself; never record a verdict on a worker's word.
3. **Feature deps require a committed Cargo.lock** or CI `--locked` fails. The lock was actually refreshed on a toolchain box and committed (91c32815) — this REPLACED the earlier "lockfile stale" blocker. Verify the lock is committed before hand-off.
4. On rebase, merged my multipart fn with main's `reply_to` threading (#1230): the multipart form must also carry `reply_parameters` top-level field, else reply-targeting is dropped on the bytes path.

## Local-feature builds vs `--all-features` (learned 2026-08-26, compiler lane)

The quick-build carrier (`quick-build-linux.yml`) wires ONLY `--no-default-features --features "${{ inputs.features }}"` (line 57) — there is NO `--all-features` path. So an opt-in feature like `local-mermaid` must be dispatched as a DISTINCT feature-set build of the same sha, e.g. `features=telegram,local-mermaid`, NOT `--all-features`. It cannot run concurrently with the plain build (single-flight); it queues as a -b cycle after the relay build drains. Result: same sha, two artifacts (one per feature set). Lesson: never hand off compile with `--all-features` on this carrier — name the exact `features=` list instead.
## Renderer verification discipline (2026-08-26, burned twice in one night)

Never certify a RENDERER from telemetry — `path=sendRichMessage` proves transport, not render (two false smoke-PASS calls before owner acceptance failed the bubble). Payload dialects: sendRichMessage takes classic (`<blockquote expandable>` = flat gray quote) vs rich (`<details><summary>` = collapsible card); house law in plan_card.rs doc comments ~35–38 — rich cards are details/summary only. Stripped release binaries make symbol-name grep useless as a presence gate (shipping functions count 0) — gate by distinct string literals or runtime differentials (warn line-number fingerprint resume.rs:184-vs-176 revealed the live code path). Primary acceptance for anything Alexey sees = Alexey's eyes; telemetry stays secondary.

## #1226 round-3 hotfix — E0728 burn (2026-08-27 ~01:15Z)
- Cycle-21 RED: ab56e86a shipped `pending_followups.lock().await` inside sync `suggestion_surface_is_stale` → E0728, exit 101 (run 33028139194).
- Root cause of escape: modum (RETIRED tool) was lint-only (policy/advisory) — it CANNOT catch Rust type errors. No local cargo. Async/sync signature correctness across state accessors is hand-verified ONLY.
- Rule going forward: any new state.rs accessor that touches an async Mutex must be `async fn` end-to-end AND every caller grepped + `.await`ed BEFORE commit (signature + callers move together, verify call-site context compiles logically: let-chain `&& expr.await` is legal, postfix `.await`).
- Fixed as a0091323 (async flip + single caller await), origin/main ff'd to a0091323a972617b653eb6bacacf9cdc168ae773, worktree oc-wt-e0728 removed, fresh ORDER dispatched + validated.
- Compiler queue races itself: its dispatch notice ("in_progress") arrived AFTER its sealed RED verdict — settle contradictory compiler claims against gh run API (`conclusion: failure` was ground truth).

## Lessons — 2026-08-27 clippy sweep (session lane: compiler)
- **Worktrees do not survive compaction/cleanup.** A "continue editing worktree X" task after compaction must start with `git worktree list` + `git branch`; if gone, rebuild from the origin tip — uncommitted edits in a removed worktree are simply gone, don't chase phantom damage.
- **Batched same-file `edit_file` calls can race:** two of my edits were silently overwritten (mermaid.rs doc fix, second `#[expect]` in session_notify_test.rs) and reported success. After any batched edit, re-read the edited regions and re-apply lost writes before trusting the diff.




## OpenCrabs fork ops — tooling lessons (2026-08-28, session d18ce16a)
- `oc-deploy ship` runs git fetch/push FROM ITS CWD — it must be invoked from inside a git repo (a worktree like ~/oc-wt-*), else "fatal: not a git repository". `poll` works from anywhere (live skill dir is fine).
- Consent register (`oc-consent-check`) — RETIRED tool, historical: was ANTI-REPLAY, one Telegram message = one consent row = one sha; a "Go for both"-style multi-sha consent could not be registered twice (duplicate msgid → no-op); each later swap needed its own owner GO token.
- pr-checks is dispatch-only (no push trigger) and lives on the carrier branch: `gh workflow run pr-checks.yml -R leshchenko1979/opencrabs --ref ci/quick-build-linux -f ref=<full-sha>`. GREEN run = the lint citation.
- Flaky CI test (open wound, file an issue if it recurs): `tests::governor_gates_test::queued_final_drains_over_the_wire_through_mock_bot_api` (src/tests/governor_gates_test.rs:310) — "Expected 1 request(s) to POST .../EditMessageText but received 2". Drainer double-sends a queued final under tokio paused-clock scheduling when converge's 600ms advance spans refill + DRAIN_TICK before delivery state settles. Failed runs: 33193151135, 33197178609; passed: 33176600303, 33194370670. Unrelated to #19/#21 files — mitigation = single re-dispatch (single-flight makes it clean).
- Modum classifier proof for pre-existing findings: `git show <parent-sha>:<file> | grep <pattern>` — same call site present on parent = pre-existing (line shifts from your hunks don't count).
- Clippy dead_code on a fn used ONLY by src/tests (cfg(test) mod) fires in the non-test lib target — fix = #[cfg(test)] gate on the fn, not deletion (background_task_route_test.rs + channel_route_expectation_test.rs still exercise resolve_route post-#19).
- The CONVERSE of the entry above, and it costs a full CI cycle: a fn that is `#[cfg(test)]`-gated must NEVER be called from production code. A test-only helper performing the identical mutation reads as the production API — `Bucket::pause_arm` (governor.rs:287, doc'd "Test-only: arm the step-2 pause directly") does exactly what the field assignment it replaced did — and with no local cargo the error surfaces only at CI as `error[E0599]: no method named X found for &mut Y`. Measured on #580: replacing `slot.pause_until = Some(until)` with `ensure_bucket(...).pause_arm(until)` cost run 36197244128 (~30 min, two E0599s, no other errors); repair = set the field directly (d6230ae08). The rule this produced lives where a code-writing lane reads it: `editor.md §Box law`.




## CI-flake diagnosis: verify the TEST VERSION on the failing tree (2026-08-30)

Lesson from the #17 gate RED (run 33322902399, sha af299821) — corrected by the drainer lane (#28 owner, session 61161247):

1. **Before calling a CI failure a flake, check WHICH TEST VERSION the failing tree carries.** "Main green, same test ok" legs are invalid if main runs a hardened/different version of that test. Method: `git merge-base --is-ancestor <fix-commit> <failing-sha>` for each fix commit, or `git diff <base> <other-main> -- <test-file> | wc -l`. My tree (base 4776bee2 = upstream main tip) predated the five fork-only #28 drainer-test hardening commits (97dd5e6d / b71287ad / 2e948769 / 01320588 / 552653a2) → the RED was mode-1 of a known ~30-50% pre-hardening lottery, and the re-dispatch GREEN was a lucky draw, not stability.
2. **Standing trigger (drainer lane, verbatim):** any future "received 2" on `governor_gates_test::queued_final_drains_over_the_wire_through_mock_bot_api` → capture `gh run view <id> --log-failed` FULL stdout BEFORE grepping (the drainer's warn lines are the receipt; self-reporting instrument 00ca9d6d). On a tree that HAS 552653a2 that = sighting #1 of a genuinely residual mode → ping session 61161247 with the raw log.
3. Upstream note: adolfousier/main still carries the PRE-hardening governor test (as of 2026-08-30) — upstream PR CI Test steps are lottery-exposed until #28 is harvested upstream (drainer lane's call, PROPOSE/WAIT).




- **Attribution guard nuance (2026-08-30, run 33312747740 / 267089af):** after a rebase-port, `gh api compare` over a fanout range reports `status=diverged, ahead_by=98` and the commit list looks like days of foreign history — that is the cherry-pick lineage, not a misfire. Verify attribution by grepping the range's commit messages for your `Session-Id:` trailer (e756b84b found on 7 commits: c6661d1a, 554bdcfc, 5135ea02, 4c9db2a3, 9c899d9e, 99b2158a, fc8b337a). Trailer-present = notify legitimate; do NOT dispute on date grounds. Also observed: fanout fired TWO overlapping legs for one run (journals fanout-33312747740-1788095871 + -1788096069, both notified=12/skipped=1) — duplicate notifies are benign but fanout.state dedup did not suppress the concurrent second leg; flagged for HQ S2 wiring.



- **Log writers don't escape newlines (2026-08-30, #36 lane, post-swap smoke of `16568074`):** a `{}` display-formatted string field carrying embedded `\n` SPLITS the log line at that byte — every `[STREAM_RECONCILE]`/`[TEXT_ACCUM]` line whose `text_tail` held a paragraph break orphaned its discriminating fields (usage_*, saw_finish_reason, stop_source) onto the next line. Mid-turn text always ends `\n\n` before tool calls, so this hit constantly, silently. Fix `13e4e1da`: sanitize tails (`replace('\n', "\\n")`) + tail-last field ordering. Rule: NEVER log a raw text tail via `{}` — sanitize first, or use `{:?}` (Debug escapes control chars natively), and put volatile string fields LAST in the format so numerics survive any future split. Evidence pattern: field counts disagree (`grep -c 'saw_finish_reason='` < `grep -c 'STREAM_RECONCILE'`).


## Mermaid × buttons full chain — RESOLVED 2026-09-05 (`ed5a42f7`, eye-witnessed)

- #96 soup (html body into md pick), #98 fencesafe media edits, #102 multipart `message_id` dropped (every media edit 400'd), #108 indent fusion — all four fixed, shipped, eye+telemetry witnessed on msg 42160 (send 715B → merge 1991B → tap 2095B, image survived). Issues closed with receipts.
- **One-message law**: keyboard merges onto the LAST message of the arming turn; fence must be in that turn's final message or diagram/buttons split across bubbles.
- **Smoke hygiene**: three smokes failed on sequencing (fenceless, unarmed, split-turn) before r4 — arm panel + fence in the SAME turn, verify arm receipt before ending it.
