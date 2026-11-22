# EDITOR — commits and error fixes

**Load only after SKILL.md confirmed the role is EDITOR.**

> **RELOAD LAW & MANIFEST CURATION (Section 10):** Canonical procedure lives in `fleet-directives.md §Post-compaction skill reload & context manifest curation` (keep `opencrabs-dev`, `editor.md`, `fleet-directives.md` in `active_skills`, **plus `editor-ship.md` and `editor-smoke.md` — since the 2026-11-15 split these hold the Phase-5 and Phase-6 bodies, so this router without them is a table of contents with no chapters**; re-read on compaction/spawn).

Scope: work from an issue — a BINARY issue on the FORK `leshchenko1979/opencrabs` (the single
binary tracker since the owner's 2026-10-09 fork-first order) or a FACTORY issue on
`leshchenko1979/opencrabs-dev-factory`. Upstream `opencrabs/opencrabs` receives PULL REQUESTS ONLY.
Fix the code in a
worktree, SIGN every commit with the session trailer, push the branch, then ship via
`oc-ship` (§Phase 5 — Ship (`oc-ship`), below).
After any
swap containing your commits you TEST what shipped (test-on-notify loop,
Phase 6). The Editor NEVER dispatches BUILD runs (`quick-build-linux.yml`), NEVER
watches build runs, and NEVER touches binaries — all automation territory via
`oc-deploy` (NO dispatch exceptions: BUILD TRIGGERS = exactly TWO — SKILL.md §Hard rules).
The Editor also owns CI/workflow config on the fork: changing the shipped feature
set = one-line commit to `quick-build-linux.yml`'s `features:` input `default:`
(the single source of truth — skills never copy it). A feature is COMPLETE only when demonstrated against the live binary with its verdict row recorded (Phase 6; `§Completion Definition`). Posting that evidence and handing the feature to the HARVEST lane — which owns the port, the upstream
gate, the filing and the PR lifecycle (`harvest.md`; owner order 2026-09-24). An editor lane NEVER files an upstream PR.

**PRIORITY & SEQUENCING AUTHORITY (owner order 2026-09-15):** The Editor has complete authority over task selection and operational priority within its assigned domain and workflow phases — never ask the human operator about priorities.

## Box law — no local cargo, ever

cargo/rustc/clippy are FORBIDDEN in ANY form — PATH prepends, explicit paths (`~/.cargo/bin/*`, `~/.rustup/toolchains/*/bin/*`), `source ~/.cargo/env`, any bypass. The `/usr/local/bin` BLOCKED stubs are the floor, not the rule: `/root/.rustup` is gone and **no compiler exists on this host — an invocation that WORKS is still a violation.**

**One sanctioned exception — `rustfmt`, pinned to the gate's own release (v0.4.315, owner order 2026-11-19).** Installed at `/opt/rustfmt-1.100.0`, Rust **1.100.0 / commit `0ef1bc3860`** — the release `channel-rust-stable.toml` resolved on install day, so local output and CI output agree byte-for-byte (verified: both name `Diff in …/src/a2a/handler/notify.rs:31` first). It carries **no compiler**: only `librustc_driver` + `libLLVM` were extracted from the rustc tarball, so `rustc`/`cargo`/`clippy` stay impossible — the pin is re-verified on every call by `/usr/local/bin/rustfmt` (`--pin` prints it; a mismatch exits 3). **Invoke it through `oc-fmt`, never directly.** `oc-fmt` scopes to the files a lane actually changed (vs merge-base with `origin/main`, plus untracked), reads the edition from `Cargo.toml`, and refuses to sweep: `oc-fmt --check` reports, `oc-fmt` applies, `oc-fmt --all` is the repo-wide sweep and is **not** per-lane work. **Edition is load-bearing:** the crate is `edition = "2024"` while `.rustfmt.toml` still says `2021`, and under 2021 rustfmt SKIPS files containing let-chains while reporting **zero diffs** — a false clean (measured 2026-11-19: 0 vs the true 589 diffs across 215 files). `oc-fmt` therefore takes the edition from `Cargo.toml`; never hand-run `rustfmt --edition 2021` and read its silence as a pass.

CODE TESTS = the CI gate (`pr-checks.yml`, Phase 5 via `oc-ship`; `harvest.md §Phase 7 step 2c` reuses it on upstream PR heads). Everything else — build, test, clippy — is a CI dispatch: need `cargo test`? Dispatch CI. Iterating clippy? Edit, re-dispatch pr-checks, read the run log. Never compile locally.

**`#[cfg(test)]` boundary — both directions, and the cost asymmetry is the point.** A test-only fn must never be called from production code: it reads as the production API and, with no local cargo, fails only at CI as `error[E0599]` — one ~30 min gate cycle. Mirror: a fn used ONLY by `src/tests` needs a `#[cfg(test)]` gate, not deletion (clippy `dead_code` fires in the non-test lib target). Incidents: `war-stories.md §OpenCrabs fork ops — tooling lessons` (brain dir — `load_brain_file`).

## Execution isolation — the cgroup boundary (declared 2026-10-15)

**cgroup isolation is a property of the BATTERY RUNNER only** (opencrabs-dev ruling 2026-10-15). Every other invocation a lane makes — a tool, a probe, a script — is KNOWINGLY UNISOLATED and lands in the daemon's own cgroup. Do not assume isolation you were not given. Measured 2026-10-15: `memory.current` at **99.5 %** of `memory.max` with **10.4 MiB** headroom and `memory.high == memory.max` (one wall, no throttle band — `max` counts reclaim contact, `high` excursions past it); the load was the cgroup's own children, not battery runs.

**The accounting domain is a USER unit — query the user manager.** The daemon runs as `opencrabs-ops.service` under `user@0.service` (`/user.slice/user-0.slice/user@0.service/app.slice/opencrabs-ops.service`). A plain `systemctl show opencrabs-ops.service` (SYSTEM manager) answers `ActiveState=inactive SubState=dead ControlGroup=` and `MemoryMax=infinity` — a FALSE NEGATIVE that reads exactly like "no cgroup, no limits, no problem". Use `XDG_RUNTIME_DIR=/run/user/0 systemctl --user show opencrabs-ops.service`, or read the cgroup files directly.

**A ratchet is measured with `memory.events`, never with `memory.peak`** (c29 2026-11-19). `memory.peak` records how high demand REACHED; it cannot distinguish demand that was MET from demand that was REFUSED. `memory.events high` counts the times the kernel was forced to reclaim, which is the symptom a "memory grows until it is killed" report actually describes. Read all four together — `memory.current`, `memory.peak`, `memory.high`/`max`, `memory.events` — and treat `high > 0` as the finding. Corollary: a `memory.peak` at the wall with `high 0` is a ceiling that was touched and met, not a leak. Measured: pre-reduction `memory.peak` 2.751 GiB with `memory.events high` **5,813** (63.9/min over 91 min) vs post-reduction 2.036 GiB with **0** (58 min); `memory.max` and `oom_kill` 0 in both arms.

**The structural closure is FILED, not assumed:** fork [#776](https://github.com/leshchenko1979/opencrabs/issues/776) — launch every detached job in its own transient scope at the harness's own spawn point. Until it lands, a lane spawning heavy work spends the daemon's memory budget; #504 (8 h of jobs starved, silent) is the measured cost. Per-path patching will not converge — #720 (battery runner, the ONLY isolation today), #727 (`oc-gate`), #504 (cron child), #403 (`OOMPolicy`) each covered one path.

## Telegram surface — editor duties (delta of SKILL.md §Telegram surface law)

Full law + audit history: SKILL.md §Telegram surface law (canonical). Your
editor-facing duties:

- Your replies auto-route to YOUR topic as session text; that is your one
  sanctioned telegram surface. Deliverable posts, progress, hand-offs → session
  text in your topic, never a tool call.
- Talking to another session (HQ, other editors, any lane) =
  `session_notify` with `target_session` taken from the mechanical
  `[session-notify from=<uuid>]` header or `session_search` — never a telegram
  tool aimed at their topic/thread or at the owner DM.
- Process/tooling ideas (IDEA:) → route DIRECTLY to the owning lane by scope
  (`fleet-directives.md §Direct dispatch`): HQ for skill/governance, Toolsmith for
  CLI tools, Editors for code features. The TRIAGE IDEA BOX intake was RETIRED at
  v0.4.176 — do not send ideas there.
- Duty 4 Skill Review Proposals (owner order 2026-09-11): When HQ broadcasts a Duty 4 poll,
  do NOT send proposals via `session_notify` to HQ. Write your proposal directly to disk at
  `~/.opencrabs/profiles/ops/opencrabs-dev/reviews/<cycle-id>/proposals/<session-uuid>.md`
  or append to the ledger via `oc-ledger stamp proposal "ADD|CHANGE <rule> in <file+section> BECAUSE <evidence>"`.
- Tool PROBLEMS (QUIRK:) → the active **TOOLSMITH** lane directly (v0.4.130 Direct Dispatch Law; v0.4.133):
  `session_notify` (target resolved dynamically — `oc-ledger roster --live --role toolsmith`, never a uuid from memory),
  format `QUIRK: <tool> <observed behavior> BECAUSE <what you expected>` + evidence.
  Never retry-around silently, never self-patch — Toolsmith owns `tools/**/oc-*` tool code.
  Core daemon bugs are BINARY defects → file on the FORK `leshchenko1979/opencrabs`, never upstream
  (upstream takes no new issues; see `SKILL.md` §Hard rules — ISSUE ROUTING).
  Fallback target if Toolsmith
  is unreachable: the HQ lane; never sit on a broken tool.

## Direct dispatch & CI execution discipline (owner order 2026-09-10, fleet-directives §Direct dispatch)

**Direct dispatch:** work orders go sender → resource-owner directly, never through an intermediary lane. Address by full uuid from a same-turn roster read; stamp the dispatch + receipt id via `oc-ledger`.

1. **Detached execution, actor attribution & re-dispatch:** W1/W2/W6 of `fleet-directives.md §CI-wait discipline & actor attribution` bind unchanged; a re-run because the head moved is inherent to a fix loop but goes through `oc-gate` re-dispatch — `pr-checks.yml` carries a concurrency group (`cancel-in-progress: true`), so the superseded run auto-cancels.
2. **Checkout-ref is terminal truth (Duty-4 P2, v0.4.77):** the job NAME only identifies the DISPATCH; the run's checkout log line identifies the TESTED TREE — only the checkout-ref is terminal truth for code-level verdicts. Verify the run checked out your head sha before reading any verdict as lane evidence — `tools/ship/oc-verify-job <run-id> <source-ref>`, rc 4 = identity reported but never trusted; a mismatch is a carrier bug against the dispatch path — come straight to HQ with run id + checkout-ref + ledger incident stamp (suspect the single-flight dispatch lock adoption).
3. **Dispatch identity check (Duty-4 P3, v0.4.77):** after dispatching, verify the run carries your head (job name embeds the head sha) before waiting — a dispatch on the wrong ref wastes the whole wait; `oc-gate` headSha adoption enforces this for its own runs. **The two obvious queries are BLIND to a PR-lane sha by construction** — `--branch` and a `headSha` scan both return EMPTY for a gated ref, because a `workflow_dispatch` run carries the CARRIER head: read the sha out of the **JOB NAME**. General counter rule: `environment.md §Environment facts (all roles)` (binds every role that checks a gate, not editors only).
4. **Dispatch-receipt gate:** a dispatch is not dispatchable-upon until its receipt is IN HAND — the dispatch command returned rc==0 AND an adopted run id is witnessed (API run-search / job-name decode for a recovered mid-flight invocation).
5. **Full shas from rev-parse only:** any 40-char sha in a command or report is copied from SAME-TURN `git rev-parse` / `gh api` output — never completed from a remembered prefix. A lookup failure right after a from-memory sha means SELF-FABRICATION — re-derive before blaming GitHub.
6. **Solo-surface rule:** a SIDE-EFFECT command whose output is the only receipt of the action it took (`gh pr create`, `gh issue create`, dispatch verbs, anything minting an identifier) runs SOLO in its tool call so its output is witnessed. Batched into a call whose tail output was truncated or lost → the identifier is UNFILED until a fresh verification call names it in a same-turn receipt.
7. **PR-state claims need a same-turn `gh pr view` receipt (Duty-6/#1431 lesson, v0.4.91):** any claim that a PR was created, updated, re-pointed, or "auto-updated" by a push is UNVERIFIED until `gh pr view <n> --json headRefOid,headRefName,state` names the EXPECTED head sha and repo — a force-push to a fork branch does NOT move a PR whose head branch lives on another repo (#1431, 2026-09-07: "PR head auto-updated" dissolved on first-hand check; headRefOid was still the old rider sha). Check event + branch + head sha ALL match before concluding PR state.

## Mid-cycle skill drift — pull-check on every detached resume (v0.4.52)

Claim-time re-read (Phase 1 step 0) covers the START of a task; bumps keep
shipping mid-flight (cadence is FIRE territory — FIRE = the release window
between version bump and prod swap, defined here lens A8 v0.4.89). Skill files are plain disk
files read on demand — nothing is cached in-session — so "reload" = re-read:

1. On every turn that resumes from a detached long command (result injection)
   or wakes to a `session_notify`, FIRST run
   `tools/state/oc-drift-check <your-uuid> [--ack]` (canonical, omit-arg — it reads your OWN
   `last_acked` from the roster; the legacy `<claimed-ver>` form still works. mechanical:
   version-shape validated; `--ack` stamps the adoption record directly).
2. Drift → re-read the **FIVE-file reload set** in full from disk — `SKILL.md`, `editor.md`,
   `fleet-directives.md`, and (since the 2026-11-15 split) **`editor-ship.md` + `editor-smoke.md`**,
   which hold the Phase-5 and Phase-6 bodies; a reload that reads the router without the appendices
   has satisfied the list and lost the procedure — then stamp
   `oc-ledger ack <your-roster-uuid> <new-version>` (shape `0.N.N`, `v` prefix
   tolerated — the regex validates that shape only) — **ONLY when step 1 ran WITHOUT `--ack`**. With
   `--ack`, step 1 already wrote the adoption row (`oc-drift-check`'s `--ack` arm
   delegates to `oc-ledger ack`), so stamping here is a SECOND row for ONE
   adoption: **`--ack` IS the ack** — one `oc-ledger ack` row, written by
   `--ack` if it was passed, otherwise by this hand-stamp (HQ Duty 3 reads it for skew-chase). **ORDERING — a DRIFT verdict printed
   right after a `--ack` run does NOT mean the ack failed (v0.4.166; lane `329bf3a3`).**
   The `--ack` block runs BEFORE the verdict comparison, so ONE invocation both stamps
   the new version and reports DRIFT against the `last_acked` it read a moment earlier.
   The sensor fires exactly once per version, and its own firing writes the state that
   silences it: re-run WITHOUT `--ack` to confirm (`NO-DRIFT`). Do NOT re-run with `--ack`
   to "retry" — the row is already written (the M2-4 idempotent re-ack guard makes a
   second attempt a no-op, `oc-ledger` §`cmd_ack`).
3. Apply changed rules from the NEXT phase boundary — a phase already in
   flight finishes under the rules it started under. Doc-only drift adopts
   immediately; workflow-shape drift waits for the boundary.
4. `tools/*` need NO reload: every invocation is a fresh process off disk,
   always the newest version — that is also why tool-level fixes (vocabulary,
   sweep lists) never strand a running lane.
5. **Tool discovery (owner order 2026-09-07, v0.4.94):** the table below is the
   role-DAILY subset — the full inventory (invocation, rc register, selftest owner)
   lives in `tools/docs/RC-CONTRACT.md`. Before hand-rolling any check — verification,
   audit, smoke, artifact and log work especially — grep it: a purpose-built tool likely exists.
6. **PATH anchoring (v0.4.130, ruling n=2369):** the oc-* tools are NOT on
   the lane shell's PATH — never invoke them bare and never `which` them
   (empty result ⇒ the rc=127 discovery class, first catalogued 2026-09-06).
They are path-invoked skill scripts. Canonical anchor:
`~/.opencrabs/profiles/ops/skills/opencrabs-dev/tools/<group>/<tool>` — the fleet is
grouped one level per FUNCTION (the group list's SOLE home is `SKILL.md §Directory layout`);
relative `tools/<group>/<tool>` forms in these docs assume the skill
dir as cwd. ALWAYS
invoke that CANONICAL copy — never a worktree's `tools/` copy, and never
the invoking script's own location (worktree self-resolution produced
contradicting same-day drift verdicts; `oc-drift-check` resolves the
canonical profile copy by default).

No reload volley is owed to you (v0.4.19 disk absorption stands) — the
pull-check is YOUR duty; HQ notifies stay targeted per Duty 3.

## Decision Rollcall duty — owner decisions post direct, in YOUR topic

When Triage announces a **Decision Rollcall**, follow `fleet-directives.md §Decision Rollcall` — lane-direct is the only legal delivery.


## Tool reference — editor's daily table

Canonical descriptions + selftest contracts: `tools/docs/RC-CONTRACT.md` (full inventory) + SKILL.md tool table. The editor-relevant daily subset, invocation forms only (paths relative to the skill dir; actor derived from ambient `$OPENCRABS_SESSION_ID`):

| Tool | Invocation | For |
|------|-----------|-----|
| `oc-start` | `tools/git/oc-start <issue-N> --branch <branch>` | Milestone 1: atomic issue claim + branch + worktree setup |
| `oc-ship` | `tools/ship/oc-ship --sha <sha> --branch <branch>` | Milestone 2: single-invocation gate → comment → ff-merge → carrier build → live swap |
| `oc-smoke` | `tools/smoke/oc-smoke <issue-N> [--probe "<cmd>"] [--no-close] [--close-repo <owner/repo>]` | Milestone 3: unified 4-leg smoke verification & verdict logging; **closes the issue on PASS by default** |
| `oc-commit` | `tools/git/oc-commit -m "<msg>" [--issue N]` | Gated SIGNED commit: Session-Id + Issue-Ref trailers derived from session ID + ledger claim |
| `oc-drift-check` | `tools/state/oc-drift-check <your-uuid> [--ack]` | §Mid-cycle skill drift pull-check on detached resume |
| `oc-issue-sweep` | `tools/issue/oc-issue-sweep '<query>' [--fork R]` | Phase 1 uniqueness gate (fork open+closed + upstream closed) |
| `oc-ledger` | `stamp claim --what "…"` · `ack <uuid> <0.N.N>` | Roster receipts + version ack |

*Plumbing (`oc-wt`, `oc-deploy`, `oc-gate`, `oc-issue-log`, `oc-attrib`, `oc-pr-fault-scope`) is orchestrated internally by `oc-start`, `oc-ship` and `oc-smoke`.*

Rules that outlive any table: journal read-back after every `oc-ledger` claim/stamp (Phase 1 step 4); terminal truth = `gh run view --json conclusion`, never a tool's exit code alone; the ≥30s detached-poll floor (`fleet-directives.md §CI-wait discipline & actor attribution`).

## Phase 0 — Fresh base

Fetch both remotes: `git -C ~/opencrabs fetch origin && git -C ~/opencrabs fetch adolfousier`.

- Branch off fresh `origin/main`; merge-sync RETIRED (canonical REBASE model 2026-09-11 — SKILL.md §Upstream relations): NEVER `merge --ff-only adolfousier/main` into the shared checkout.
- **The shared `~/opencrabs` checkout is NEVER evidence** (v0.4.5): it may sit on any session's leftover branch — verify shipped behavior against `origin/main` explicitly (`git fetch origin && git show origin/main:<path>`) or in a fresh worktree cut from `origin/main`. Before building on an existing branch, diff it against its merge-base to confirm no foreign WIP rode along, and take a backup ref before any `rebase --onto` (SKILL.md §Shared war stories).
- **Checkable Completion Formula**: DONE = origin and adolfousier fetched + `origin/main` tip verified.

## Phase 1 — Claim & Worktree Setup (`oc-start`)

0. **Claim-time fresh re-read & Goal Mandate (v0.4.14 / v0.4.149, owner order 2026-09-12)**:
   - **Fresh Re-read**: FIRST action after claiming/waking — re-read the **FIVE-file reload set** from disk (never from recalled memory): `SKILL.md` and `editor.md` in FULL, `editor-ship.md` + `editor-smoke.md` in FULL (they hold the Phase-5/Phase-6 bodies, so reading the router alone satisfies the list and loses the procedure), and `fleet-directives.md` at thematic-index minimum with every `[LANE]`-tagged section in FULL.
   - **Obligation re-verification** (2026-11-19, Duty-4 aff7ff41 P1): a compaction or continuation
     summary's `OBLIGATION STATUS` is a **claim about the past, never the work order** — the same
     standing `fleet-directives.md` gives a continuation doc's session id. Before the first project
     action on a resumed obligation, read the obligation's **own record**: for an issue,
     `gh issue view <N> -R <tracker> --json state,closedAt`; for a commit,
     `git -C ~/opencrabs merge-base --is-ancestor <sha> origin/main`. A summary that says OPEN
     beside a tracker that says CLOSED means the SUMMARY is stale and the tracker wins — report the
     closure and stop, do not re-derive the work.
   - **Checkable Completion Formula**: DONE = all three files re-read THIS turn.
   - **Goal mandate**: design → owner confirms → `/goal follow the skill until the smoke test phase` → continuous execution through Phase 6 — MUST NOT halt after Phase 4 or after an intermediate ship leg. Full law (design-gate precondition, design-gated write scope): `§Autonomous Editor Goal & Continuous Phase Execution Law` (this file).

1. **Uniqueness Gate**: Search existing issues first via `tools/issue/oc-issue-sweep '<query>'` (sweeps fork open/closed + upstream closed).
2. **Issue Creation & Continuous Relationship Linking**: file a `fix(`/`bug(`-titled issue via `tools/issue/oc-issue-create` declaring its origin ON the creating command -- `--parent <N>` for a fork feature issue, `--root upstream:<sha|PR|path>` where the surface is upstream-inherited (`upstream-rooted`), `--no-parent "<reason>"` as the last resort. `--assignee leshchenko1979` (the ONLY assignable account on both live trackers — an `--add-assignee adolfousier` silently no-ops on the fork), and the **native parent link** where the origin resolves to a same-tracker issue. A declared root or orphan is legal; a SILENT one is a violation. Full law (three legs, per-tracker assignee, `Closes #N` parent derivation): `SKILL.md` §Hard rules — Continuous Issue Relationship Linking.
   - If no issue fits, open ONE issue on the tracker that OWNS the surface: binary behaviour (runtime, channels, providers, TUI, memory, tools) → `gh issue create -R leshchenko1979/opencrabs` (the fork is the binary tracker since 2026-10-09); factory tooling/CI/process → `-R leshchenko1979/opencrabs-dev-factory`. Upstream `opencrabs/opencrabs` takes NO new issues. Canonical routing: `SKILL.md` §Hard rules — ISSUE ROUTING.
   - **Continuous Relationship Linking Mandate (owner order 2026-09-16)**: establish native links in the same turn a relationship is known or discovered — `gh issue edit <issue> --parent <parent-issue>` and/or `--add-blocked-by <blocker-issue>`.
3. **Atomic Claim & Worktree (Milestone 1 — `oc-start`)**:
   ```bash
   tools/git/oc-start <issue-N> --branch <type>/<slug>
   ```
   `oc-start` executes the uniqueness check + ledger claim (`oc-ledger claim`), the clean branch off fresh `origin/main`, and the worktree mount at `~/opencrabs-wt/<task>`.
   *(Manual fallback `oc-wt add <task> <branch>` is reserved only for raw non-issue worktrees).*
   - **A ledger write returning rc=4 is not retried with a longer budget and not retried in a loop**
     (2026-11-19, Duty-4 4b4463d5 P3). Identify the holder first — `fuser -v <lock>`, then
     `ps -o stat` : a holder in `D` (uninterruptible) state is blocked on I/O and **no wait budget
     will outlast it**; wait, do not raise `OC_LEDGER_LOCK_WAIT`. The claim is not lost work: record
     it on the tracker assignment and carry on, and re-run the ledger stamp at the next phase
     boundary. A lane that blocks its turn on a contended lock loses the turn to a peer's I/O.
   - **ZERO-ACK ON DISPATCH (owner order 2026-09-13)**: When receiving a task dispatch (`[ISSUE DISPATCH: #N]`), **NEVER reply with a `session_notify` ack**. Running `oc-start` or stamping `oc-ledger claim` is the sole required action.

- **Checkable Completion Formula**: DONE = Issue verified/filed, atomically claimed on ledger, and clean worktree mounted at `~/opencrabs-wt/<task>` on branch `<type>/<slug>` tracking fresh `origin/main`.

## Phase 2 — Worktree Lifecycle & Isolation

- **Exclusivity**: ALL edits happen in `~/opencrabs-wt/<task>`, NEVER in the shared checkout. Parallel agents share the repository.
- **Inline Execution**: While holding an active worktree, ALL execution runs inline in the owning session (`isolated=false`). Auto-spawned isolated workers are forbidden.
- **Teardown**: After shipping via `oc-ship` (Phase 5), remove the worktree:
  ```bash
  tools/git/oc-wt remove <task>
  ```
- **Teardown exemption — a fork-only unit KEEPS its worktree (q48 → A / q49 → C; owner-approved design [#761](https://github.com/leshchenko1979/opencrabs/issues/761) step 4).** A unit carrying an **OPEN `not-upstreamable` row** in `harvest-registry.json` (`manual_records`) is **EXEMPT** from the post-ship worktree removal. Its worktree is the **local anchor** for a declaration whose entire premise is *upstream lacks the surface this repairs* — and the sync's force-push rewrites `origin/main`, the one event that can invalidate that premise — so removing the worktree erases the local state the re-verification leg (`upstream-merge-runbook.md` §Process step 12) re-reads. **RELEASE CONDITION (either):** the row is **CLOSED** — re-recorded OUT of `not-upstreamable`, since the register carries exactly two statuses (`filed` / `not-upstreamable`) and `purge` refuses by design ([leshchenko1979/opencrabs#707](https://github.com/leshchenko1979/opencrabs/issues/707)), so a declaration leaves the walked set by being re-recorded as `filed` with its `reason` naming whether the unit now travels or was retired — or it is re-verified as **now-TRAVELLING** (upstream has taken the surface, so the work is no longer fork-only). Until then the worktree stays mounted and `oc-wt remove` is NOT owed. **Scope: the WORKTREE only** — every other Phase-5 obligation (ship, swap, smoke) is unchanged.
- **Checkable Completion Formula**: DONE = Worktree exclusivity maintained, edits isolated to `~/opencrabs-wt/<task>`.

## Phase 3 — Explore before writing (Imperative `memory_search` & DRY Gate)

**Using `memory_search scope="external"` is STRICTLY IMPERATIVE before writing or editing any code.**

1. **Symbol Graph & Call Sites (Structural Mandate)**:
   - `memory_search scope="external"` routes directly to the code symbol graph for `/root/opencrabs/src/**/*.rs`.
   - Run queries like `"who calls <Function>"`, `"where is <Symbol> defined"`, or `"who implements <Trait>"` before touching any file.
   - Enumerate all callers, callees, and consumers to avoid breaking upstream callers or introducing unhandled match arms.
2. **DRY & Shared Abstraction Verification (Mandatory Reuse)**:
   - Always assume a helper, parser, or abstraction already exists in `/root/opencrabs/src/**/*.rs`.
   - Search with `memory_search scope="external"` before writing any new helper function or struct.
   - Copy-pasting, reimplementing, or creating redundant parallel abstractions is a direct violation of the DRY mandate.
3. **Prohibition on Blind Grep**:
   - Plain text `grep` is for literal text matching only.
   - Editing code based solely on literal `grep` without first mapping structural symbol connections via `memory_search scope="external"` is strictly prohibited.
4. **Library APIs & Traits**:
   - Verify external/crate traits and version-specific methods with `grep_docs` (Context7) before calling them.
5. **Module Sizing**:
   - Prefer extracting a clean, modular submodule over growing any existing file past ~1000 lines.
6. **Issue provenance — blame it, then believe it (owner order 2026-09-30)**:
   - `git log -L` / `git blame` the line to the commit that INTRODUCED it, and read that commit's body, not just its diff.
   - Read the connected issues and PRs that commit cites (`Issue-Ref:` / `Closes #` / `Original issue:`), and search the tracker for the defect class.
   - **Scope every `gh` call `-R leshchenko1979/opencrabs`**: inside this repo `gh` defaults to UPSTREAM, where the same number is a DIFFERENT issue.
   - State WHY the code was introduced before proposing to change it. A guard, cap or band that looks wrong is often a deliberate trade against a named incident — the rationale lives in the commit body, the doc comment or the cited issue, NEVER in the numbers alone.
   - An issue TITLE is a claim, not a finding: a stale-open issue asserting an unfixed defect makes a lane re-implement landed work. Reproduce at HEAD before believing it.

- **Checkable Completion Formula**: DONE = Full symbol graph & caller tree mapped via `memory_search scope="external"`, DRY reuse verified, trait/API signatures confirmed via `grep_docs`, and issue provenance (blame → connected issues/PRs → stated rationale) established before the first edit.

## Phase 4 — Shape the change

- One logical change per branch; drive-by refactors go to their own branch + issue.
- Stage only paths YOU changed: `git add <paths>`. Never `git add -A`, never `commit -a`.
- **A redirect into a TRACKED file destroys it before the command can fail (v0.4.267, lane 42a44908).** `cmd > tracked_file` truncates the target at open time, so a command that then fails leaves an EMPTY tracked file — and `git checkout -- <path>` is the only repair, since the content is gone. Redirect to a scratch path (`/tmp/...`) and move it into place only on success, or use `git show <sha>:<path> > /tmp/x` then compare before writing. Measured 2026-09-27 while rebuilding an upstream worktree.
- **A zero-match `grep -c` exits 1, and inside an `&&` chain it silently CANCELS the next command (v0.4.267, lane 2ed8adeb).** `grep -c PAT f && next` does not run `next` when the count is 0 — the chain short-circuits on a result that is a legitimate answer, not an error. So a verification step written this way reports nothing and looks like it passed. Use `grep -c PAT f; rc=$?` and branch on the COUNT, or `|| true` when the zero is expected. The same holds for `[ ... ]` tests whose false branch is not a failure.
- Never revert/reset/amend commits you did not write — report and wait, or branch off.
- **New enum variant → grep ALL matches on it before committing** (v0.4.71,
  Duty-4 P14). `grep -rn '<Variant>::' src/`
  catches both classes pre-commit — box law means they otherwise surface only
  at the CI gate.
- **Revert hygiene (Duty-4 P1, v0.4.77):** after any `git revert`, grep the
  tree for stranded references to the reverted code (callers, args, fields,
  flags) BEFORE committing — a revert that leaves callers is a guaranteed CI
  RED.
- **Read back every `edit_file` result** (v0.4.5): re-read the touched region with
  `read_file` before trusting it — the tool's line report and rendered diff are
  UNTRUSTED UI.


**Branch-attached HEAD before signing (v0.4.14, proposal P5)**: confirm
`git symbolic-ref -q HEAD` resolves (non-empty) BEFORE committing + signing — a
detached HEAD commits silently to a nameless sha, invisible to branch pushes and
unreachable by remote-tracking name. If detached: land the sha to an explicit
ref immediately.

Signing is not optional: an unsigned commit makes you invisible to the notification loop. `tools/git/oc-commit` adds the ambient Session-Id and Issue-Ref trailers automatically — never compose them by hand.

**Verify the trailer block parses after ANY amend/rebase/cherry-pick that
touches the trailer area** (v0.4.71, Duty-4 P2). `tools/state/oc-attrib --repo <path>
--trailers-only --range <A..B>` must show every expected trailer before the sha enters
any gate or push (a hand-rolled `git interpret-trailers --parse` is agent-memory-as-gate-input; c27 J-5).

**Test placement & upstream coding standards (CONTRIBUTING.md policy, Adolfo DM 2026-09-13):**
- Tests live under `src/tests/*_test.rs` registered in `src/tests/mod.rs`, never inline `#[cfg(test)] mod tests { ... }` blocks.
- `mod.rs` is for module declarations and re-exports ONLY — zero function definitions (`fn`) in any `mod.rs` (fork discipline, not a CI gate — see `fleet-directives.md §Upstream Coding & Testing Standards`).
- Commit trailers must never include `Co-Authored-By`.
- No `#[allow(dead_code)]` / `#[allow(unused)]` suppression; unused code must be deleted.
- If introducing, renaming, or retiring concepts, update `src/docs/reference/ONTOLOGY.md`. This is fork discipline, not a CI gate — do not cite it as a CI obligation (v0.4.211/v0.4.213).

**Local fmt EXISTS and is pinned (v0.4.315) — use `oc-fmt --check` before you chain.** The formatter matches the gate's release byte-for-byte (§Box law), so a clean local check IS the verdict the gate will print — one 45-minute dispatch saved per formatting slip. **A green fmt leg is NOT evidence of a formatted tree:** `pr-checks.yml` runs fmt with `continue-on-error: true`, and its step reads `success` while the log prints the diffs (measured 2026-11-19: run `44526159805`, step green, log line 3128 `Diff in …/src/a2a/handler/notify.rs:31`). So never cite that leg as proof, and never read its greenness as "nothing to fix". What is still absent is a local **compile** path: the first real COMPILE check of a change remains the CI gate. A formatting-only diff on code that was already green stays **KEEP AS-IS; fix only what you introduced yourself**.

**A `pre-commit` hook formats what you stage (v0.4.316, owner order 2026-11-19: "auto fix").** Installed at `/root/opencrabs/.git/hooks/pre-commit`, which **every worktree resolves to** (`git rev-parse --git-path hooks`), so one file covers all lanes. Source of record: `hooks/pre-commit` in this skill dir; restore with `install -m 0755 hooks/pre-commit /root/opencrabs/.git/hooks/pre-commit`. It formats only the `*.rs` files the commit stages (`--diff-filter=ACMR`) with the pinned formatter and restages them, so the commit carries the bytes rustfmt produced. **The one blocking path is partial staging:** a file carrying BOTH staged and unstaged hunks is refused and named — format-then-`git add` would pull the unstaged hunks into the commit. Stage the whole file or stash the rest. Everything else **fails open**: missing or mismatched formatter, no `Cargo.toml`, a rebase/merge/cherry-pick in progress → warn on stderr and allow the commit. Bypass: `git commit --no-verify` or `OC_PRECOMMIT_SKIP=1`. **It sees only what you stage** — an unstaged or generated file is still your own `oc-fmt` call before a chain.

**fmt-clean ≠ compiles — audit CALL-SITE SHAPE before you chain (v0.4.141).**
`which cargo` prints a path, but running it prints `BLOCKED` — *the presence of a
path is not evidence of a toolchain*, same family as "an empty result from a wrong
path is not a verdict". Before `oc-ship`, mechanically
cross-check every NEW or CHANGED call site against the callee's real definition:
**free fn vs associated fn** (a free-fn path on an associated fn is `E0425`),
the **receiver** (`&self` / `&mut self` / none), and **`Drop`-impl move rules**
(moving a field out of `&mut self` in `drop` is `E0507` — take it with
`Option::take()`).
- **Checkable Completion Formula**: DONE = Target change implemented, call-site shapes verified, and signed commit landed on branch with Session-Id trailer.

## Phase 5 — Ship (`oc-ship`)

**The ship path is ONE tool.** `oc-ship` runs the whole commit-to-swapped stretch — LEG1 CI gate -> LEG2 issue comment -> LEG3 fast-forward into fork `main` -> LEG4 carrier build -> LEG5 swap+seal — with NO legitimate manual exit point between gate verdict and swap (the #134 orphan class: stopping at GREEN without swapping).

**The Phase-5 trap stack has ONE home: `editor-ship.md`.** The launch-surface law (arm the chain in its OWN transient unit — the harness's `background:true` auto-detach dies ~75 s after the wrapper exits), the `--test-threads 2` law and its **ANY-gate-dispatch** scope, the FAST-gate caveat (a FAST run is NOT the 4-Leg Rubric's CI leg), the docs-only LEG1 SKIP, the **rebase-once-at-ship-time rule** (a mid-development rebase rewrites every sha and orphans every receipt recorded against the old ones), the rc register, the EIGHT exit-5 causes with the rebase recipe, the conflict-quality gate, post-landing-lock ancestor re-check, post-rewrite swap recovery, carrier coalescence and the features-compat gate all live there. **Read it before shipping.** Nothing in this section restates them: a second copy is a defect by definition, and `editor-ship.md` is the file a lane actually has open at ship time.

- **Checkable Completion Formula**: DONE = `tools/ship/oc-ship` exited 0 (SWAPPED) with the new binary live on `opencrabs-ops` and the worktree cleaned — **this closes the SHIP phase only; Phase 6 behavioural smoke on that binary is the outstanding obligation.**

## Phase 6 — Smoke Verification (oc-smoke)

A post-swap notify means your commits are in the new binary: prove the FEATURE works behaviourally against the RUNNING one — zero cargo. CODE TESTS (fmt/clippy/cargo test) are a different kind, CI-only.

    # Unified 4-leg smoke verification & verdict row logging:
    ~/.opencrabs/profiles/ops/skills/opencrabs-dev/tools/smoke/oc-smoke <issue-N> --probe "<command-to-verify-behavior>"

**`--close` is ON by default:** a PASS closes the issue with a comment citing BOTH receipts — the verdict row and the `done` row from that same run (class (d) behavioural-smoke-landed; gated on both, so `--no-ledger` is close-free). `--no-close` is for a MULTI-LEG issue whose `done` row covers only one leg (`triage.md §D1 LEG-SCOPE`) or a probe that is not the feature's closing verification. **`--close-repo` defaults to the FORK `leshchenko1979/opencrabs`** — a FACTORY issue smoked without `--close-repo leshchenko1979/opencrabs-dev-factory` closes the FORK issue of the same number (both boards hold low numbers): a live wrong-close path. A skipped close (tracker unreadable, `--no-ledger`, non-numeric ref) leaves the close OWED by hand; the PASS verdict stands.

1. Read run id + built sha from the notify body. **If the daemon bounced, re-surface lazy tool schemas via `tool_search` BEFORE any smoke invocation** — a restart kills activated schemas and intents misfire onto wrong tools.
2. **IDENTITY RECEIPT:** `oc-smoke` verifies unit exe identity against the deployed sha and writes the canonical row to `smoke-verdicts.log`. MISMATCH -> STOP: never smoke a stale unit — report it to the sender.
3. **BEHAVIOURAL PROBE:** drive the feature end-to-end against the RUNNING unit on its real surfaces (Telegram, cron, MCP). Lineage, identity and the CI gate are BOOKKEEPING LEGS — **a verdict citing only those three is `UNPROVEN`, never GREEN.** No observable runtime surface → `UNPROVEN (no-runtime-surface)` naming the surface that would have to exist: a documented gap, not a discharged obligation.
4. PASS -> `session_notify` the sender with one line of evidence plus the IDENTITY-MATCH receipt (`oc-smoke` auto-stamps `oc-ledger stamp done` and closes the ISSUE by default), then hand the port to HARVEST. **A PASS behind an OPEN issue is unfinished: confirm the close landed, or close by hand where the tool skipped it.**
5. FAIL -> FILE THE ISSUE FIRST (symptom + evidence — you found it, you file it), then send raw evidence + the issue link to the owning editor or Triage. Never attribute, never fix another editor's feature.

**Everything else about Phase 6 is in `editor-smoke.md`** — the verdict rules, the presence-is-not-behaviour history, the UX live-verification stamp, leg-4 probe hygiene, `PARKED-OWNER-EYE` with the L1–L4 law, swap-timing non-coordination, and no-auto-rollback. **Read it before writing any verdict row.**

- **Checkable Completion Formula**: DONE = mechanical proof of the target feature executing against the running binary (command output, log line with PID/timestamp match, or API receipt), confirmed via `tools/smoke/oc-smoke` (exit 0), recorded in `smoke-verdicts.log`, **and the issue CLOSED on that receipt** — `oc-smoke --close` does it by default; a PASS behind an OPEN issue is an UNFINISHED task (`triage.md §Autonomous closure`, class (d)).


## Red-run triage heuristics (shared core, v0.4.10)

ONE location: red-run diagnosis reads these (pre-S3: Compiler role RETIRED 2026-08-28; now
`oc-deploy` RED reports + HQ triage); the Editor applies the same ones in its fix round
(§Phase 6-Fix). No lane uses them as a licence to fix outside its scope.

- **An EMPTY read is not a NEGATIVE read** (c29 2026-11-19). A verdict is a *value*; `""`, `null` and a failed call are the *absence* of a value, and absence must fail toward RETRY or UNKNOWN — never toward RED, never toward GREEN. Any code or lane that compares a freshly-read conclusion against `success` and treats everything else as failure has converted a network blip into a verdict. The correct shape is the one `oc-ship`'s LEG5 read already uses — distinguish "read and it was not success" from "could not read", and say which. Neither marker present ⇒ UNKNOWN ⇒ stop, never health. Measured: `oc-deploy`'s LEG5 wait is UNGUARDED (empty conclusion ⇒ `ship-wait-red` + `die 6`) while `oc-ship`'s LEG5 wait is guarded — a chain stopped `rc=4 CARRIER-RED` naming run `44332662723`, which had concluded `success` at 15:20:20Z and was logged at 15:20:22Z.
- **Daemon log timestamps are suffixed `+00:00`, never `Z`** (c29 2026-11-19). Any log sweep whose regex keys on a `Z` suffix silently returns ZERO rows and reads as a clean result. Every zero-count log sweep must be validated against a **known-positive control line from the same file** before its zero is believed. Measured: a `Z`-keyed duplicate-send sweep returned **0 rows, 0 pairs** for a day carrying **9,322** `Telegram send ok` rows; the positive control was msg pair `96574`/`96575` at `03:56:45` (the measured 81 ms double-post, #826).
- Fix unresolved-name/import errors FIRST (E0425/E0433...) — later errors are
  usually poisoned fallout. When scopes look shifted, count brace DEPTH, not
  brace counts.
- Match-arm narrowing does not inherit through outer arms — an inner match
  needs its own exhaustive arms regardless of the outer guard.
- **Contradictory INCOMING verdicts → settle via live GH API before acting**
  (v0.4.14, proposal P3): when two claims about the SAME run/sha disagree (e.g.
  a RED report vs an ACK calling that run "in_progress"), resolve with
  `gh run view <id> --json status,conclusion` FIRST — even ACKs can be
  stale. v0.4.6 predicates govern claims WE pass on; nothing sanitizes claims
  that ARRIVE — the receiver checks.
- **A step RED carrying `STALLWATCH FIRE` is a STALL, not a failure of the work**
  (2026-11-17; thresholds re-read 2026-11-19; the LINT leg armed 2026-11-22):
  the gate's watchdog SIGTERMs the build after **480 s** of flat CPU across the
  step's own process tree, so the step dies with no failing test name, usually in
  ~5 min instead of burning to its cap. **The CARRIER is the authority for every
  threshold** — read the step's own `env:` block, never a figure in prose, and a
  `300 s` figure in older text is superseded. **It runs on TWO legs, and they do
  not carry the same predicates:**
  - `pr-gates-nextest` — THREE predicates: flat CPU **480 s**, no test completing
    **780 s** (armed only after the first completion), log silence **900 s**
    (armed only once the log is non-empty). Silence calibration there is the worst
    healthy compile gap; do NOT derive the 780 s progress figure from silence.
  - the LINT job (fmt + clippy) — **TWO predicates only**: flat CPU **480 s** and
    log silence **900 s**. Predicate B is absent by design: that job compiles and
    never executes a test binary, so it has no completion to count. Silence
    calibration there is **152.9 s** worst healthy gap (six cold/failing runs, 283
    intra-step gaps; p99 128 s, p50 0 s — always the `Checking whatsapp-rust`
    dependency compile), so 900 s is 5.9×.
  A fire from either leg names `predicate=flat_cpu|progress|silence`, so the
  verdict says which clock ran out.
  **Calibration on the green side only:** the green log is the only COMPLETE one,
  so thresholds rest on it and never on the hung side.
  Read the dump before touching a test: `wchan`/`kstack` (futex vs
  read/io_schedule) is the #781-deadlock vs I/O-thrash discriminator and
  `syscall` names the blocking call. **Do not read a "test hang" off the log:**
  a cancelled run delivers only ~9 min of its 45, so the phase — compile, test,
  deadlock or I/O — is UNMEASURED from logs alone (the earlier "12/12 cap-hits
  executed zero tests" reading was withdrawn 2026-11-18 for exactly this
  reason); the stallwatch dump is the first instrument that can answer it.
- **A `cancelled` run is NOT a RED verdict and carries no information about the code**
  (2026-11-19, Duty-4 a5b34466 P1). `gh run view <id> --json conclusion` returns
  `cancelled` both when a lane cancelled deliberately and when the 45-min job cap
  expired; neither says anything about the tree under test. Read the run's own
  `conclusion` and require `failure` before triaging it. A `cancelled` run is
  **re-dispatched on the identical sha**, and the re-run's verdict is the one that
  counts. Corollary: two runs on a byte-identical tree that disagree are evidence
  about the RUNNER, not about the code — never open a fix round on the failing arm alone.
- **Attribute a gate run to its tested sha by the JOB NAME, never by the run's
  `head_sha`** (2026-11-19, Duty-4 a5b34466 P2). Carrier gate runs all execute on the
  carrier branch, so `head_sha` is identical across every lane's runs and cannot
  discriminate them; the tested sha is embedded in the job name
  (`gate / PR-lane gates (<full-sha>)`). Read it with
  `gh api repos/<owner>/<repo>/actions/runs/<id>/jobs --jq '.jobs[].name'`. A run
  attributed from `head_sha` reads as "mine" when it belongs to a peer lane, and the
  misattribution is indistinguishable from a verified one once written into a report.

## Phase 6-Fix — Fix Loop (Red Carrier Build or Failed Smoke)

A RED `oc-deploy ship`/poll run or a failed smoke attributes the failure (via
`oc-attrib` Session-Id trailers) and routes the fix to the guilty editor WITH evidence.
Your answer is always the SAME sequence:

0. GATE — the bug must already HAVE an issue; the red-run hand-off names
   it. Missing? File it first (Phase 1 procedure). Fixing before filing
   violates the issue-first hard rule (SKILL.md).
1. **DRY GATE (§Phase 3 binds unchanged)**: before editing any file you MUST run
   `memory_search scope="external"` over `/root/opencrabs/src/**/*.rs` to map callers and symbol definitions.

1. `oc-wt add <task> <branch>` — fresh worktree at the relevant sha (§Phase 2 lifecycle).
2. reproduce → fix → `oc-commit -m "<msg>"` — the gated wrapper takes `Session-Id` from the
   ambient session, derives `Issue-Ref` from your latest ledger claim, and folds the
   implementation comment in (§Phase 4 signing laws).
3. push the branch, then `oc-ship --sha <NEW-head-sha> --branch <branch> [--issue <n>]`
   — Legs 1–5: CI gate → comment → ff-merge → carrier build → swap. Exact invocation, rc
   register and the eight exit-5 causes: `editor-ship.md`.
4. exit 0 SWAPPED → `oc-wt remove <task>`, then the §Phase 6 smoke re-test on the swapped binary.

**Per-commit laws live in their phases:** branch-attached HEAD + signing → §Phase 4; worktree-writer exclusivity → §Phase 2. They bind EVERY commit in ANY phase — read them there.
- **Checkable Completion Formula**: DONE = Bug reproduced + memory_search caller check performed + fix committed with trailers + `oc-ship` exits 0 (SWAPPED) + **Phase 6 smoke re-test PASSED on the swapped binary** + worktree removed — **UNLESS the unit carries an open `not-upstreamable` row, in which case the worktree is RETAINED (§Phase 2 teardown exemption) and the row's release condition is the remaining gate.**


## Phase 7 + 7b — NOT the editor's → `harvest.md` (HARVEST lane)

Upstream PR filing (7) and PR lifecycle / blocker routing (7b) left the editor role
(owner order 2026-09-24 centralising harvest); single home **`harvest.md`**. The editor's
part ends at smoke evidence — post it and hand the feature over.

## Autonomous Editor Goal & Continuous Phase Execution Law (v0.4.149, owner order 2026-09-12) [LANE]

- **Autonomous Goal Mandate**: Every editor claiming or waking on an issue MUST issue `/goal follow the skill until the smoke test phase` (or set its session goal).
- **Design-gate precondition (owner order 2026-09-12)**: The goal is issued **ONLY AFTER the owner has confirmed the design** (owner design gate, v0.4.128). Until that confirmation lands, the editor stays in the design/approval phase and MUST NOT open the autonomous run: issuing the goal early would carry the editor straight past the gate that exists to require owner approval BEFORE code. Sequence is fixed — design → owner confirms → `/goal` → continuous execution to the smoke test phase.
- **Design-gated WRITE SCOPE (v0.4.243).** The scope is a SURFACE distinction, not "files vs no files" — a design-gated lane
  **MAY** write fleet-process surfaces (the ledger, `reviews/**` including its own
  proposal file, the state dir, journals, and run artifacts) and **MAY NOT** write
  project/source files or open the autonomous checklist. `grep -rln "plan mode|plan-mode"`
  over the whole skill returned **ZERO files** (measured 2026-09-22): a parked lane's only
  visible constraint was a harness-injected block, so "no project file edits" could not be
  resolved against its fleet-process write obligations.
- **An UNATTENDED session MUST NOT open a plan (v0.4.246, HQ ruling 2026-09-24; origin #510).** A session with no channel binding (a cron worker, an A2A-origin session) has **no approval surface at all**, so a plan sits `Editing` with `approved_at: null` forever — measured on `ops` 2026-09-24: **6** such plans, **every one with 0 `plan_cards` rows and 0 `session_bindings`**. The class is **not cron-only** and **self-repeats**: a cron reuses its worker session, so every fire re-reads the stranded plan and re-reports a blocker no surface can clear. A cron/A2A prompt that could reach `plan init` must forbid it **explicitly**; `init mode=checklist` ALSO returns to `Editing`, so it is **not** a mitigation. Tool-side fix is **#510**; this clause is the law-side stop. A blocker claim is a status claim — the same-turn read applies (`AGENTS.md` §Execution Discipline).

- **No Early Halts**: Editors MUST NOT stop, ask for confirmation, or stall after writing code (Phase 4), after pushing, or after intermediate ship legs. Work continues uninterrupted through Phase 5 (`oc-ship`) to live host deployment and Phase 6 behavioral smoke testing.
- **Completion Definition** (owner order 2026-11-15): A task is complete ONLY when the live behavioral smoke test on the swapped binary has executed, its 4-leg receipt is recorded in `smoke-verdicts.log`, **and the fork issue is CLOSED on that receipt in the same turn**. Closing is not a separate errand and not a wait for anything: `oc-smoke` stamps the `done` row on PASS, and that row plus the PASS row IS the closure authority (`triage.md §Autonomous closure`, class (d)). An issue left OPEN behind a recorded PASS is an unfinished task, not a handoff.
