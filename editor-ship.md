# EDITOR — Phase 5 (Ship) appendix

**Owns:** the Phase 5 trap stack — the `oc-ship-chain` failure-mode / rc register, the exit-code lane actions, the conflict-quality gate, the post-landing-lock ancestor re-check, the docs-only LEG1 skip, post-rewrite swap recovery, carrier coalescence and the features-compat gate.

**Load when:** you are about to ship (entering `editor.md` Phase 5), or you are recovering a chain that returned non-zero. It is an APPENDIX to `editor.md`, never a second role file: the role, the phase sequence and every cross-cutting law live there, and where the two disagree `editor.md` wins and this file is the defect.

> **RELOAD LAW:** keep this file in `active_skills` for the whole ship phase and re-read it on compaction (`fleet-directives.md §Post-compaction skill reload & context manifest curation`). At claim time it is read on entering Phase 5 — not before.

## Phase 5 — Ship (`oc-ship-chain`)

**`oc-ship-chain` IS the single, exclusive ship path from commit to swapped binary (v0.4.126; manual push-to-main, manual issue-log, and manual oc-deploy sediment retired v0.4.132).**
The Editor runs `oc-ship-chain` in one detached invocation under one chain-id — **armed in its OWN transient systemd unit, never via the harness's `background:true` auto-detach**:

```bash
# 1. Push your branch first
git -C ~/opencrabs-wt/<task> push -u origin <branch>

# 2. Arm the chain in its OWN unit (resumes the session on finish)
systemd-run --user --unit=oc-ship-<issue>-$(date -u +%H%M%S) --collect \
  tools/ship/oc-ship-chain --sha <commit-sha> --branch <branch> [--issue <issue-n>] \
    --test-threads 2
```

**`--test-threads 2` IS LAW ON THE SHIP INVOCATION UNTIL #1936 IS FIXED (HQ ruling 2026-10-15, on the proposal of lane 2fbfb2f8).** Upstream #1936's four-slot deadlock hangs the gate, so a default chain re-rolls a 45-minute wall: measured fork run `38799188468` (`--full`, default threads, gate input `466e7dfb3`) was **CANCELLED** at **2722 s** against the workflow's own `timeout-minutes: 45` (**2700 s**), wedged with **zero** `test result:` lines — and `fmt` + `clippy` both read `success` on that run, so the wedge is **not** the diff. The same gate input re-dispatched with `--test-threads 2` (fork run `38806046232`) came back **GREEN in 31.4 min (1884 s)**. Tool leg: factory #39, `d514000c` — `--test-threads N` / `OC_SHIPCHAIN_TEST_THREADS=2`, forwarded to the LEG1 `oc-prchecks` dispatch. **SCOPE — read before relying on it:** the flag rides the **fresh-dispatch** path only and is **INERT on `--gated-run`** (the chain now warns loudly instead of silently dropping it, `oc-ship-chain:1145`), and it bites **only when the test leg runs** — a `--fast` gate skips tests, so the flag is a no-op there. **EXPIRY IS KEYED ON THE SYMPTOM, NEVER ON #1936's ISSUE STATE — do NOT remove this line because #1936 reads CLOSED.** Upstream closed #1936 COMPLETED on 2026-10-07 (`468711dfa`) on the **stall watchdog alone**; its own close note states *"the deadlock root cause itself is still under investigation"*. The wedge **recurred 2026-10-15** — fork run `38799188468` CANCELLED at **2722 s** with **4** tests wedged, the stuck set (`hot_write_paths_retry_test`×1 + `loop_break_test`×2 + `memory_archive_index_test`×1) **character-identical** to the 2026-10-04 21:50Z run quoted in #1936's own body. Live home for the recurrence: fork #781. **Remove this line only when a default-threads full gate completes with a real test verdict** (no `has been running for over 60 seconds` wedge).

**THE LAUNCH SURFACE IS LOAD-BEARING (measured 2026-09-26, lane 63d775f9).** Two consecutive chains armed via the harness's background mode died `rc=143` (SIGTERM) ~75 s after the wrapper exited 6 — **even though LAW 17's re-exec had already placed each in its own user scope** (`run-r02937f26c50b43bea91cb45c7ca6dc58`, `run-rd0e1dd4e3b404e09b861bb58a87a3e0a`; detached logs `747586` / `758792`, both ending `gate infra rc=143`). Swap, a peer's broad `pkill` and a ship-lock wait were each ruled out by same-turn reads. The identical chain armed with `--unit=… --collect` survives and polls. **The CAUSE is NOT established** — the discriminator is. And the cost of getting it wrong is not just a lost chain: the killed run leaves its gate **`in_progress` with nobody polling it**. Measured the same hour: `36277623534` and `36277682621`, both `status=in_progress` / `conclusion=null` — two wasted full gates.

`oc-ship-chain` executes the entire 5→swapped stretch mechanically:
1. **Leg 1 (CI Gate):** Dispatches and watches `oc-prchecks` (`pr-checks.yml` on your branch: fmt + clippy + `cargo test --locked --profile ci --all-features`). ⚠️ **The chain's DEFAULT gate is FAST, and FAST is NOT the CI-gate leg of the 4-Leg Smoke Rubric** (finding `127429e6`, cycle `20260919-c21`): `oc-ship-chain` passes `--fast` to `oc-prchecks` unless `--full`/`--no-fast` is given (the `oc-ship-chain` fast-default, its `--fast` pass-through to `oc-prchecks`), and `--fast` runs **fmt + clippy only, tests skipped** (`oc-prchecks --help`, `:704`). A FAST run's job name carries the only visible marker (`… — FAST`) and its `Run tests` step reads `skipped` — citing that run as your CI-gate evidence leaves the smoke receipt with **no all-features test evidence at all**, the exact leg the "Presence and bookkeeping legs are never a smoke PASS" law protects. Pass `--full` when the receipt needs the test leg, or dispatch `oc-prchecks` yourself without `--fast`. **Exception — a pure-docs commit SKIPS this leg** (owner ruling 2026-09-12: *"We don't need the pure docs commits to pass through ci on our side."*). "Pure docs" is defined in the law, not by the tool: every changed path ends `.md` **and** is not `include_str!`-compiled into the binary — the 21-path compiled-in exclusion set lives in `§Docs-Only LEG1 Gate Skip` (this file). A skip is recorded as **SKIPPED** and is never a passed gate: do not cite a skipped leg as GREEN, and do not count it as a passed leg in a smoke receipt.
2. **Leg 2 (Issue Log):** If `--issue <N>` is supplied, posts the per-commit implementation comment via `oc-issue-log` automatically.
3. **Leg 3 (Fast-Forward Merge):** Fetches fork `main`, verifies fast-forwardability, and pushes `<branch>:main` (serialized via `ship.lock`).
4. **Leg 4 (Carrier Ship):** Dispatches `oc-deploy ship --sha <sha> --execute` to build on `ci/quick-build-linux`.
5. **Leg 5 (Swap & Seal):** Bounded-polls carrier execution (`oc-deploy poll --execute --wait <sec>`) until the binary is live and swapped. The ship wait default is **2700 s** (`OC_SHIPCHAIN_SHIP_WAIT`, tool text: the `OC_SHIPCHAIN_SHIP_WAIT` default in `oc-ship-chain`) — raised from 900 s at #336 after 11 of 37 carrier successes exceeded 900 s (10 most recent: 942-1344 s, median 1062 s). A shorter budget mislabels a still-building run as INFRA rc 6.

**Carrier Coalescence & Ancestry Matching (v0.4.148):** editors do not serialize on a
pre-dispatch carrier lock — descendant builds are accepted via ancestry matching, and
host swaps stay serialized and monotonic via `host-swap.lock`. Full law + diagram:
`§Carrier Concurrency & Coalescence Law` (this file).

There is NO legitimate manual exit point between gate verdict and swap. The #134 orphan class (stopping at GREEN without swapping) is structurally closed.

### Failure Modes, Tool Automations & Agent Recovery Protocol (v0.4.145)

When shipping features via `oc-ship-chain` or deploying via `oc-deploy`, failures and interruptions follow the mechanical automation vs. manual resolution contract below:

| Failure Mode | Return Code / Signal | What is Mechanical (Automated by Tool) | What Requires Agent (Semantic Fix) | Tool Output & Communication |
|---|---|---|---|---|
| **1. Non-Fast-Forward Push** | `rc=5` — **any** NON-FF, clean *or* conflicted | **Mechanical only on `oc-deploy`'s own push path** (cause (c) below, v0.4.145): it auto-fetches `origin/main`, rebases, audits with `oc-rebase-safety audit`, and retries the push in 3s. **`oc-ship-chain` does NOT rebase** — LEG3 is a bare `git merge --ff-only` that dies `rc 5` **unconditionally** on any non-FF, so LEG4 (and with it the auto-rebase) is never reached. | The **LANE** rebases `$BRANCH` onto fork main and force-pushes **before** re-running the chain — a **clean** non-FF still needs this; the table does NOT mean "wait for auto". A **semantic conflict** additionally needs hand adjudication. | `NON-FF: rebase <branch> onto fork main (oc-rebase-safety) and re-run` (chain) OR `REBASE_CLEAN` / `REBASE_CONFLICT` (**only** on `oc-deploy`'s push path). Canonical rc register: `tools/docs/RC-CONTRACT.md`. |
| **2. Carrier Compilation Failure** | `rc=4` (`CARRIER-RED`) | **Auto-log extraction**: Tool automatically runs `gh run view <id> --log-failed`, parses `error[E...]` and rustc diagnostic lines, and prints the exact compiler error and file:line in tool stderr. | Agent fixes the Rust syntax, borrow checker, or missing module error in the worktree, commits, and re-runs `oc-ship-chain`. | `CARRIER-RED: the carrier build concluded RED` (rc 4) followed by the extracted compiler error block |
| **3. Daemon Boot Panic / Swap Failure** | `rc=6` (swap/poll failure) | **Auto-rollback & Auto-diag**: `oc-deploy swap-execute` **automatically rolls back** to the previous binary (`/usr/local/bin/opencrabs.bak`), restarts the service, and automatically extracts the panic backtrace from `journalctl -u opencrabs-ops.service -n 30` into tool output. | Agent inspects the auto-extracted panic trace, reproduces/fixes the startup bug or bad unwrap in the worktree, commits, and re-chains. Host remains 100% healthy. | `swap poll failed rc=<n>` / `swap not confirmed after 12 polls` (rc 6) with the extracted panic trace |
| **4. Daemon Bounce Task Interruption** | Restart signal / `[BACKGROUND TASK INTERRUPTED]` | **State file + recovery re-run** (⚠️ there is **no `--resume` flag** — `oc-ship-chain` dies `rc=2` on an unknown arg): `oc-deploy swap-execute` writes the deployment result to `/root/.opencrabs/profiles/ops/opencrabs-dev/deployed.sha`. Only the `poll --execute` path hands Phase B to a transient `systemd-run` unit, so a **direct** `swap-execute` runs in the caller's cgroup and can be killed by the very restart it performs. | **Recover by state, not by resume**: read `deployed.sha`; if the swap landed, confirm `disk==proc MATCH` and go to Phase 6. If the chain died before the swap, **re-run the same chain with `--gated-run <id>`** (reuses the GREEN gate run whose job name pins your sha) — see `upstream-merge-runbook.md`. | `SWAP_SUCCESSFUL: running binary matches deployed SHA. Ready for Phase 6 smoke.` |

**Exit codes & Lane action:**
- **Exit 0 — SWAPPED:** The new binary is running live on the host (`opencrabs-ops` user unit). Worktree can now be removed (`tools/git/oc-wt remove <task>`). Proceed immediately to Phase 6 (Smoke-test-on-notify).
- **Exit 2 — USAGE:** Bad or missing arguments (`--sha`/`--branch` are required; malformed flag). Correct the invocation and re-run — no lane state to resolve.
- **Exit 3 — DIRTY CHECKOUT:** The fork checkout has uncommitted changes (pre-flight refusal). Clean or stash it, then re-run.
- **Exit 4 — GATE-RED / CARRIER-RED:** The CI gate failed or the carrier build failed. Start a fix round (Phase 6-Fix): keep the same branch, fix in a new worktree, commit, push, and re-run `oc-ship-chain`. Triage heuristics live in `editor.md §Red-run triage heuristics` (below). **Also the `--gated-run` / `--gated-sha` pre-verify failure:** the supplied run was not `completed success` on a job pinned to the sha, or `--gated-sha` did not match `--sha`. Do NOT re-dispatch the run — re-verify it with `gh run view <id> --json status,conclusion,jobs` and re-supply the correct id.
- **Exit 5 — NON-FF / MERGE CONFLICT · TIP-MOVED · REBASE-GATE:** EIGHT distinct causes share this code, enumerated in `oc-ship-chain`'s own header from `grep -c 'die ".*" 5$'` (NON-FF, STALE-BASE, TIP-MOVED, REBASE-GATE, ALREADY-LANDED, LOCAL-MAIN-DIVERGED, LOCAL-MAIN-AHEAD, STALE-LOCAL-MAIN); full register in `tools/docs/RC-CONTRACT.md`. Three are detailed below; the other five name themselves in the tool's message. **(a) NON-FF / MERGE CONFLICT** — `oc-ship-chain` LEG3 ran `git merge --ff-only` and refused. A **clean** non-FF and a **conflicted** one are the SAME code from the chain's side: the chain performs **no rebase of its own**, so the LANE rebases `$BRANCH` onto fork main and force-pushes first; a **semantic conflict** additionally requires hand adjudication. (The automatic in-tool rebase belongs to `oc-deploy`'s own push path — that is cause **(c)**, not this one. Do not wait for an auto-rebase that the chain never runs.)
  ```bash
  git -C ~/opencrabs-wt/<task> fetch origin
  git -C ~/opencrabs-wt/<task> rebase origin/main
  # resolve conflicts in working tree
  git -C ~/opencrabs-wt/<task> push --force-with-lease origin <branch>
  ```
  ⚠️ **`oc-rebase-safety` is NOT the rebase engine** — it is a READ-ONLY safety auditor (`audit` / `overlap`). Use standard git commands to resolve conflicts, verify zero lost edits with `oc-rebase-safety audit`, and re-run `oc-ship-chain`.
  - **(b) TIP-MOVED** — the branch was force-pushed mid-gate, so `$TIP != $SHA`: LEG3 refuses rather than fast-forwarding fork main onto a tip NO GATE VALIDATED. Recovery: re-run the chain against the new tip — do NOT land the ungated tip.
  - **(c) REBASE-GATE** — `oc-deploy`'s in-tool auto-rebase refused the push (`OC_DEPLOY_GATE=rebase-conflict` / `rebase-audit-failed`). Recovery: rebase `$BRANCH` onto fork main yourself, verify with `oc-rebase-safety audit`, then re-run.
- **Exit 6 — INFRA:** dispatch or poll infrastructure failure (`oc-prchecks` rc 4/7/8, or ship rc other). ⚠️ **NOT the UNSIGNED case, and NOT a post-push ORDER-gate rejection:** an unsigned head commit is caught **BEFORE the merge** and exits **3**; a post-push ORDER-gate rejection exits **4**. Both are this section's neighbours, not infra: a head commit carrying no `Session-Id` trailer is refused by ORDER gate 4 (`oc-order-validate: UNSIGNED … attribution mandatory`). Read the message before you act — if it says UNSIGNED, do not go hunting for a network or carrier problem. Fix = land an empty trailer-signed marker commit on the head (tree-identical, forward-only; `upstream-merge-runbook.md` step 9) and re-run. Every synthesis/merge head is unsigned **by construction**, so this recurs on every sync. **A lineage-guard refusal ALSO exits 6** (`non-monotonic-swap`): the guard is rebase-aware (v0.4.151) and accepts the swap as `rewrite-equivalent-swap` — recovery is **re-run the same leg** — **NEVER hand-edit `deployed.sha`** (`§Post-Rewrite Swap Recovery`).
- **Exit 7 — GATE IN FLIGHT:** the gate was still running after the chain's budget and resume-polls (`oc-prchecks` rc 5, non-terminal). The run id is printed — do **NOT** re-dispatch (that concurrency-cancels the live run); wait for it and re-run with `--gated-run <id>`, which pre-verifies and skips dispatch.
- **Exit 8 — SHIP-WAIT-TIMEOUT:** the carrier build did not reach a terminal state within the LEG4 `--wait` budget (default 2700 s; `oc-deploy ship` rc 5 with no rebase-gate token). ⚠️ **The run is still BUILDING — do NOT re-dispatch it** (a re-dispatch concurrency-cancels the live run). Wait for it, then resume with `oc-deploy poll --sha <sha> --execute --wait <sec>`, or re-run the chain with a larger `--wait`. This code exists precisely because the Exit 4/6 reflex ("re-run the chain") is the double-dispatch this arm prevents.

**Conflict-quality gate — MANDATORY after any rebase with hand-resolved code:**
*(A hand-resolved merge shipping a crate-alias mismatch is five E0308s and a red CI round-trip)*:
1. Re-read every hand-merged function END-TO-END — not just the conflict hunk.
2. Match crate-wide type aliases: open the alias definition; the error type is usually locked by the alias.
3. Grep the tree for duplicate imports and doubled tests the resolution may have left behind.
4. **Prove nothing was lost** (finding `6cd8175f`, cycle `20260919-c21`): `git diff <new-base> HEAD --stat` must list ONLY files this branch changed. `oc-rebase-safety audit` cannot settle this after a rebase onto a MOVED main — every file both sides touched reports `CHANGED` (main's own edits sit inside `C..B`, where `C = merge-base(A,B)`), so their patch-ids can never match `C..A`, and the SUMMARY line then reads `LOSSES FOUND — full re-gate required` even when zero content was lost. Read the audit's **`DROPPED`** rows as the loss signal; treat **`CHANGED`** as indeterminate and confirm with the diff. A lane that trusts the summary hunts a loss that does not exist.

**Post-landing-lock ancestor re-check — MANDATORY before LEG3 lands (finding `127429e6`, cycle `20260919-c21`):** the gate (LEG1) runs BEFORE the landing lock is taken, so the window between "gate green" and "lock acquired" is unprotected — and LEG3 is a bare `git merge --ff-only` that performs **no rebase of its own**. Any lane landing on fork `main` inside that window makes your branch a non-fast-forward and LEG3 dies `rc 5` (cause **(a)** above). **A chain queued on `ship.lock` is already doomed if `origin/main` moved while it waited** — it will take the lock and then refuse. After acquiring the lock, re-check ancestry against the CURRENT remote tip:

```bash
git -C ~/opencrabs-wt/<task> fetch origin
git -C ~/opencrabs-wt/<task> merge-base --is-ancestor <branch> origin/main || {
  git -C ~/opencrabs-wt/<task> rebase origin/main      # hand-resolve any conflicts
  git -C ~/opencrabs-wt/<task> push --force-with-lease origin <branch>
}
```

⚠️ **Distinguish this from the v0.4.214 local-main reconcile — same `rc 5`, opposite fixes.** v0.4.214 covers LOCAL `main` being stale while the branch is *correctly* based on `origin/main`: that is a FALSE alarm and the fix is **do not rebase**. This check covers `origin/main` having genuinely MOVED during the gate: the rebase is **real and necessary**. The v0.4.214 diagnostic (`git merge-base --is-ancestor main origin/main`) does not separate the two — test against `origin/main`, never against local `main`. Automating the re-check inside the chain (pre-LEG3) is a Toolsmith call; until it lands, the LANE owes the check.

**Gate-idle question sweep:** CI gate and carrier build waits are idle time — do not sit silent on open questions. Circle back to the user in your topic with anything unresolved (scope doubts, naming, approach forks) while the chain runs; waiting is never a reason to hold a question or to guess.
- **Checkable Completion Formula**: DONE = `tools/ship/oc-ship-chain` exited 0 (SWAPPED) with the new binary live on `opencrabs-ops` and the worktree cleaned — **this closes the SHIP phase only; Phase 6 behavioural smoke on that binary is the outstanding obligation.**

## Docs-Only LEG1 Gate Skip (v0.4.161, owner ruling 2026-09-12 11:04Z) [LANE]

**Owner ruling (verbatim, 2026-09-12 11:04Z):** *"We don't need the pure docs commits to pass through ci on our side."* Origin: a lane's docs-only commit burned LEG1 in full before the ruling landed.

- **The law.** A commit whose changed paths are ALL **pure docs** SKIPS the LEG1 CI gate on the fork ship chain. A skip is neither PASS nor RED — it is a **SKIP**, and it MUST be recorded as one in the ship chain journal, never left implicit.
- **"Pure docs" is DEFINED HERE, never left to a tool's discretion.** A commit is pure docs iff **every** changed path (a) ends in `.md` **and** (b) is **NOT compiled into the binary** via `include_str!` / `include_bytes!`. Clause (b) is load-bearing: a `.md` compiled into the binary changes COMPILED OUTPUT, so touching it is a code change and MUST run the gate. A chain shipping a RANGE needs every commit in the range to be pure docs.
- **The exclusion set is DERIVED BY THE TOOL at gate time — never by hand, never carried in a lane's context.** Any such path list is **illustrative, not normative**: it rots the moment a template is added or removed, and a lane reproducing it by hand is the defect this clause prevents (owner: *"that should be purely mechanical"*). The gate resolves the compiled-in `include_str!` targets against `src/**/*.rs` at run time; lanes verify with `tools/ship/oc-ship-chain --eval-docs-skip <sha>` (Finding J-2, v0.4.170).
- **Recording is MANDATORY — an absent gate is NEVER a passed gate.** A skipped LEG1 MUST be recorded in the ship journal **and** in a `shipchain` ledger row naming the sha, the leg stated as SKIPPED. GREEN may be stated only for a gate that actually ran and returned `completed success`; a skip is cited as SKIPPED, never GREEN, and never counted as a passed leg in a smoke receipt.
- **Enforcement split.** The law text is HQ's (this section); the mechanical LEG1 behaviour is Toolsmith's and LANDED in `d6cb9b9a` (v0.4.161): pure-docs commit SKIPS LEG1, the exclusion set is DERIVED at gate time (`shipchain_docs_only()` — cite by function name, never by line), the skip is journalled (`GATE-SKIPPED-DOCS`) plus a `shipchain` ledger row, it applies to a FRESH dispatch only (`--gated-run`/`--gated-sha` still gate), and `OC_SHIPCHAIN_NO_DOCS_SKIP=1` forces the gate. Upstream's `**.md` / `docs/**` paths-ignore shape is deliberately NOT copied — it would skip a commit editing a compiled-in template. Never claim a skip the tool has not recorded.

## Post-Rewrite Swap Recovery (v0.4.151, Toolsmith brief 2026-09-12) [LANE]

**After a fork-main rebase, RE-RUN the same `oc-ship-chain` leg — never hand-edit `deployed.sha` to re-point around a refusal.**

A rebase orphans the deployed sha (it stops being an ancestor of `main`), and the pre-v0.4.151 guard refused **every** such swap with `non-monotonic-swap`. The guard is now rebase-aware: when the incoming lineage carries the deployed change under a new sha (patch-id match) it journals `rewrite-equivalent-swap` with the twin sha and admits the swap. A guard refusal surfaces as **`rc 6`** from `oc-ship-chain`; the recovery is a re-run, not a marker edit.

`oc-deploy lineage-check --prev <deployed> --sha <incoming>` returns the verdict (`ok` / `rewritten` / `absent`) read-only, without touching gate state. Re-pointing `deployed.sha` by hand leaves a false audit trail for a sha that was never built as a run and is **prohibited** (HQ ruling 2026-09-12, lane `2fbfb2f8` incident). A genuinely-absent change refuses until the audited `--allow-rewritten-lineage` override is passed with a mandatory justification.

## Carrier Concurrency & Coalescence Law (v0.4.148, Toolsmith brief 2026-09-12) [LANE]

- **Concurrency semantics:** `ci/quick-build-linux` runs under `concurrency: group: quick-build-linux` with default queuing (1 active + 1 pending; further dispatches cancel and replace the pending run). Editors push to `origin/main` immediately — no pre-dispatch carrier lock.
- **Coalescence:** `oc-deploy` and `oc-ship-chain` accept descendant builds by ancestry matching (`git merge-base --is-ancestor "$SHA" "$CAND_SHA"`), so pushes landing while a build runs coalesce into one build and every contributing editor recognises its commit as deployed without a redundant dispatch.
- **Host swap mutex:** host binary swaps stay strictly serialized and monotonic via `host-swap.lock` (`flock -x $STATE_DIR/host-swap.lock`) plus lineage verification — a stale binary cannot overwrite a newer one.
- **Merge serialization:** `oc-ship-chain` serializes Leg 3 (fast-forward merge) via `ship.lock`.

## Features-compat gate — no silent feature-loss swaps (HQ ruling 2026-09-04, MANDATORY) [LANE]

`oc-deploy swap-execute` **refuses** any artifact whose feature set drops a feature present in `deployed.meta.json` (exit 4, journal `features-drop-gate`, markers untouched) unless `--allow-features-drop` is passed explicitly. Feature *additions* pass freely; *drops* are the failure class. Enforced in-code (selftest 17p/17q). Rationale: the 06:36:06Z rogue swap (run `33844429519`, `features="telegram"` over a live `telegram,code-graph` binary) killed structural memory for 12h, and the 18:57Z f3c03269 swap was the same class. The gate would have refused both.
